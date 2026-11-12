#!/usr/bin/env python3
"""Relative-pose LeRobot datasets from pilot_mix_gHs3 (design: P2, 2026-11-10).

Two copies of the source mix (Yosub's 378 episodes: 0-177 = pilot_head_Hgt teleop, 178-377 =
pilot_glove_HHs3 glove), identical except for the glove poses:
  <tile name>   glove pose = FK(HHs3 joints): Yosub's tile-chain labels, robot base frame
  <slam name>   glove pose = s . T_slam_cam . T_cam_body . inv(T_flange_body) at the HHs3 step times,
                in the episode's SLAM frame (metric, scale s = the segment's default scale)
Teleop (both): FK(action joints) as the target, FK(state joints) as the anchor, robot base frame.
Images, timeline, gripper, tasks and episode numbering are the source's (videos are hard-linked), so
the train / val episode lists of the paper's arms apply unchanged.

Per step:
  action             (7)  target tool pose x y z (m) + rotation vector (rad) + gripper (source action)
  observation.state  (1)  gripper (source state)
  anchor_pose        (6)  the pose the relative action starts from: x y z + rotation vector.
                          Teleop: FK(measured joints) (the action, the commanded target, leads it by
                          ~0.13 s); glove: = the action pose (HHs3 state == action).
  slam_valid         (1)  1 where the glove step has a SLAM pose (bracketing pose samples <= bridge_s
                          apart, segment scale ok); teleop 1. Same values in both datasets.
  ik_unreached       (1)  1 where HHs3's IK did not reach the glove pose, so FK is not the glove motion
                          there; teleop 0; same values in both datasets. Rule (decision 2026-11-11, option b):
                          slam.hhs3_manifest.ik_flag (a joint within ik_limit_tol of its range limit, or
                          joint 3 on the stretched-arm plateau) OR, where the IK target can be rebuilt with
                          our tile chain (slam.hhs3_manifest.TakePoses), |FK - target| > ik_residual_mm.
The flags are top-level keys (not observation.*), so LeRobot does not feed them to the policy.
Training converts each chunk to relative 10-D actions (P3) and chooses which flags mask the loss.
Invalid SLAM steps carry the nearest valid pose (finite values); use slam_valid to mask them.

  R=/home/student/miniconda3/envs/lerobot/bin/python
  PYTHONPATH=. $R -m slam.rel_dataset build experiments/exp016_rel_datasets/config.yaml
  PYTHONPATH=. $R -m slam.rel_dataset build <config> --only tile --allow-dirty --out-root <scratch>   # trial
"""
import argparse
import datetime
import filecmp
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G
from slam.hhs3_manifest import TakePoses, ik_flag
from slam.labels import interp_poses

STAT_Q = (1, 10, 50, 90, 99)


# ---------------------------------------------------------------- geometry
def rotvec(R):
    """(N, 3, 3) -> (N, 3) rotation vectors (angle in [0, pi])."""
    q = G.R_to_quat(R)                                       # x y z w
    q = q * np.where(q[:, 3:4] < 0, -1.0, 1.0)
    s = np.linalg.norm(q[:, :3], axis=1)
    ang = 2 * np.arctan2(s, q[:, 3])
    return q[:, :3] / np.maximum(s, 1e-12)[:, None] * ang[:, None]


def pose6(T):
    return np.concatenate([T[:, :3, 3], rotvec(T[:, :3, :3])], 1)


def pose6_to_T(p):
    return G.rt_to_T(p[:, 3:6], p[:, :3])


# ---------------------------------------------------------------- inputs
def load_source(root):
    import pandas as pd
    files = sorted((Path(root) / "data").glob("chunk-*/file-*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in files]).sort_values("index").reset_index(drop=True)
    return df


class SlamSession:
    """Per-frame SLAM tool poses of one take session, from an experiment's analysis view."""

    def __init__(self, session, spec, T_body_tool):
        self.session, self.spec, self.T_bt = session, spec, T_body_tool
        exp, run = spec["experiment"], spec["run"]
        self.segdir = C.WORK / "runs" / exp / "main" / "view" / session / "segments"
        res = json.load(open(C.REPO / "experiments" / exp / "results" / f"scale_{run}.json"))
        if res["label"] != spec["scale"]:
            raise ValueError(f"{exp} {run}: scale label {res['label']!r}, config says {spec['scale']!r}")
        self.scale = {r["segment"]: (float(r["s"]) if r["ok"] else None) for r in res["rows"]}

    def samples(self, take_episode):
        seg = self.segdir / f"ep{take_episode:02d}"
        if not seg.exists():
            return None, None, None
        s = self.scale.get(seg.name)
        wall = {f["k"]: f["wall"] for f in json.load(open(seg / "frames.json"))["frames"]}
        z = np.load(seg / "slam" / f"{self.spec['run']}.npz")
        g = np.load(seg / "gt.npz")
        if s is None or not len(g["full_k"]):
            return None, None, s
        ball = {int(k): T for k, T in zip(g["full_k"], G.rt_to_T(g["full_rvec"], g["full_tvec"]))}
        T_sc = {int(k): T for k, T, ok in zip(z["k"], z["T_slam_cam"], z["tracked"]) if ok}
        ks = sorted(set(ball) & set(T_sc))
        T = np.array([T_sc[k] for k in ks], float)
        T[:, :3, 3] *= s
        T = T @ np.array([ball[k] for k in ks]) @ self.T_bt[None]
        return np.array([wall[k] for k in ks]), T, s


def poses_at(t, T, tq, bridge_s):
    """Interpolated poses at tq; valid where the bracketing samples are <= bridge_s apart.
    Invalid steps get the nearest valid pose (or the nearest sample)."""
    out = np.tile(np.eye(4), (len(tq), 1, 1))
    valid = np.zeros(len(tq), bool)
    if t is None or len(t) < 2:
        return out, valid
    i = np.clip(np.searchsorted(t, tq), 1, len(t) - 1)
    valid = (tq >= t[0]) & (tq <= t[-1]) & (t[i] - t[i - 1] <= bridge_s)
    if valid.any():
        out[valid] = interp_poses(tq[valid], t, T)
        vi = np.where(valid)[0]
        for j in np.where(~valid)[0]:
            out[j] = out[vi[np.argmin(np.abs(vi - j))]]
    else:
        out[:] = T[np.clip(np.searchsorted(t, tq), 0, len(t) - 1)]
    return out, valid


# ---------------------------------------------------------------- build
def build_columns(cfg, df, fk, which):
    """New per-frame columns for the whole mix: action (N,7), state (N,), anchor (N,6), slam_valid (N,),
    ik_unreached (N,) for which in {'tile', 'slam'}; plus per-glove-episode provenance rows."""
    N = len(df)
    act = np.stack(df["action"].values).astype(float)
    st = np.stack(df["observation.state"].values).astype(float)
    ep = df["episode_index"].values
    tele = ep < cfg["source"]["glove_first_episode"]
    action = np.zeros((N, 7))
    anchor = np.zeros((N, 6))
    slam_valid = np.ones(N, bool)
    ik_lim = np.zeros(N, bool)
    action[:, 6] = act[:, 6]
    # teleop: target = FK(action), anchor = FK(measured state)
    action[tele, :6] = pose6(fk(act[tele, :6]))
    anchor[tele] = pose6(fk(st[tele, :6]))
    # glove
    glove = ~tele
    ik_lim[glove] = ik_flag(act[glove, :6], fk, cfg["ik_limit_tol"])
    prov = []
    man = {r["hhs3"]: r for r in json.load(open(C.REPO / cfg["manifest"]))["episodes"]}
    if which == "tile":
        action[glove, :6] = pose6(fk(act[glove, :6]))
    T_bt = G.inv(np.array(json.load(open(C.REPO / cfg["glove_frame"]["handeye"]))["T_flange_body"], float)[None])[0]
    T_bw = np.array(json.load(open(C.REPO / cfg["glove_frame"]["base_world"]))["T_base_world"], float)
    sessions, targets = {}, {}
    dt = 1.0 / (cfg["fps"] * cfg["slow"])
    for e in np.unique(ep[glove]):
        rows = np.where(ep == e)[0]
        h = int(e - cfg["source"]["glove_first_episode"])
        m = man[h]
        # ik_unreached, residual part: FK(HHs3 joints) vs HHs3's IK target, rebuilt with our tile chain
        # (slam.hhs3_manifest.TakePoses: the target to 0.4 mm where HHs3's IK converged) where available
        n_joint = int(ik_lim[rows].sum())
        resid = np.full(len(rows), np.nan)
        if m["t0"] is not None and m["t0_reliable"]:
            if m["session"] not in targets:
                gt = C.WORK / m["session"] / "gt"
                ok = (gt / "ball_poses.npz").exists() and (gt / f"{m['session']}_b0587b_cam_world.json").exists()
                targets[m["session"]] = TakePoses(m["session"], T_bw, T_bt) if ok else None
            P = targets[m["session"]]
            if P is not None:
                O = P.at(m["t0"] + np.arange(len(rows)) * dt)
                v = np.isfinite(O[:, 0, 0])
                F = fk(act[rows][v, :6])
                resid[v] = 1000 * np.linalg.norm(F[:, :3, 3] - O[v, :3, 3], axis=1)
        far = np.nan_to_num(resid, nan=0.0) > cfg["ik_residual_mm"]
        ik_lim[rows] |= far
        if m["session"] not in sessions:
            spec = cfg["slam"]["sources"].get(m["session"])
            try:
                sessions[m["session"]] = SlamSession(m["session"], spec, T_bt) if spec else None
            except FileNotFoundError as ex:
                if not cfg.get("_trial"):
                    raise
                print(f"TRIAL: no SLAM results for {m['session']} ({ex.filename}); slam_valid = 0 there")
                sessions[m["session"]] = None
        S = sessions[m["session"]]
        if S is None or m["t0"] is None or not m["t0_reliable"]:
            t, T, s = None, None, None
        else:
            t, T, s = S.samples(m["take_episode"])
        tq = (m["t0"] if m["t0"] is not None else 0.0) + np.arange(len(rows)) * dt
        Tq, valid = poses_at(t, T, tq, cfg["slam"]["bridge_s"])
        slam_valid[rows] = valid
        if which == "slam":
            action[rows, :6] = pose6(Tq)
        prov.append({"episode": int(e), "hhs3": h, "session": m["session"], "take_episode": m["take_episode"],
                     "source_episode": m["source_episode"], "status": m["status"], "t0": m["t0"],
                     "manifest_verified": m["verified"], "scale": s, "steps": len(rows),
                     "slam_valid": int(valid.sum()), "ik_unreached": int(ik_lim[rows].sum()),
                     "ik_unreached_joint_rule": n_joint, "ik_target_known": int(np.isfinite(resid).sum()),
                     "ik_unreached_residual_only": int((far & ~ik_flag(act[rows, :6], fk, cfg["ik_limit_tol"])).sum())})
    anchor[glove] = action[glove, :6]
    return {"action": action, "state": st[:, 6], "anchor": anchor, "slam_valid": slam_valid,
            "ik_unreached": ik_lim}, prov


def stats_of(x):
    x = np.asarray(x, float)
    x = x[:, None] if x.ndim == 1 else x
    out = {"min": x.min(0), "max": x.max(0), "mean": x.mean(0), "std": x.std(0), "count": np.array([len(x)])}
    for q in STAT_Q:
        out[f"q{q:02d}"] = np.percentile(x, q, axis=0)
    return out


def write_dataset(cfg, src_root, out_dir, df, cols, prov, which, provenance):
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists; remove it or use another --out-root")
    tmp = out_dir.with_name(out_dir.name + ".partial")
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "meta").mkdir(parents=True)
    # videos: hard links (same bytes as the source)
    for f in sorted((src_root / "videos").rglob("*.mp4")):
        dst = tmp / f.relative_to(src_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(f, dst)
        except OSError:                                    # another file system: copy
            shutil.copy2(f, dst)
    for f in (src_root / "meta").glob("*.json"):
        if f.name not in ("info.json", "stats.json"):
            shutil.copy2(f, tmp / "meta" / f.name)
    shutil.copy2(src_root / "meta" / "tasks.parquet", tmp / "meta" / "tasks.parquet")
    # data
    f32 = lambda a: [np.asarray(r, np.float32) for r in a]
    table = pa.table({
        "action": pa.array(f32(cols["action"]), type=pa.list_(pa.float32())),
        "observation.state": pa.array(cols["state"].astype(np.float32), type=pa.float32()),
        "anchor_pose": pa.array(f32(cols["anchor"]), type=pa.list_(pa.float32())),
        "slam_valid": pa.array(cols["slam_valid"].astype(np.float32), type=pa.float32()),
        "ik_unreached": pa.array(cols["ik_unreached"].astype(np.float32), type=pa.float32()),
        "timestamp": pa.array(df["timestamp"].values.astype(np.float32), type=pa.float32()),
        "frame_index": pa.array(df["frame_index"].values, type=pa.int64()),
        "episode_index": pa.array(df["episode_index"].values, type=pa.int64()),
        "index": pa.array(df["index"].values, type=pa.int64()),
        "task_index": pa.array(df["task_index"].values, type=pa.int64()),
    })
    src_files = sorted((src_root / "data").glob("chunk-*/file-*.parquet"))
    if len(src_files) != 1:
        raise NotImplementedError("source data in more than one parquet file")
    (tmp / "data/chunk-000").mkdir(parents=True)
    pq.write_table(table, tmp / "data/chunk-000/file-000.parquet")
    # info.json
    info = json.load(open(src_root / "meta/info.json"))
    feats = info["features"]
    feats["action"] = {"dtype": "float32", "shape": [7], "names": ["x", "y", "z", "rx", "ry", "rz", "gripper.pos"]}
    feats["observation.state"] = {"dtype": "float32", "shape": [1], "names": ["gripper.pos"]}
    new = {"anchor_pose": {"dtype": "float32", "shape": [6], "names": ["x", "y", "z", "rx", "ry", "rz"]},
           "slam_valid": {"dtype": "float32", "shape": [1], "names": None},
           "ik_unreached": {"dtype": "float32", "shape": [1], "names": None}}
    order = ["action", "observation.state", "anchor_pose", "slam_valid", "ik_unreached"]
    info["features"] = {**{k: (new.get(k) or feats[k]) for k in order},
                        **{k: v for k, v in feats.items() if k not in order}}
    json.dump(info, open(tmp / "meta/info.json", "w"), indent=4)
    # stats: global and per episode for the changed / new features
    vals = {"action": cols["action"], "observation.state": cols["state"], "anchor_pose": cols["anchor"],
            "slam_valid": cols["slam_valid"], "ik_unreached": cols["ik_unreached"]}
    stats = json.load(open(src_root / "meta/stats.json"))
    for k, v in vals.items():
        stats[k] = {s: np.asarray(a).tolist() for s, a in stats_of(v).items()}
    json.dump(stats, open(tmp / "meta/stats.json", "w"), indent=4)
    epf = sorted((src_root / "meta/episodes").glob("chunk-*/file-*.parquet"))
    eps = pd.concat([pd.read_parquet(f) for f in epf]).sort_values("episode_index").reset_index(drop=True)
    ep_of = df["episode_index"].values
    for k, v in vals.items():
        per = [stats_of(np.asarray(v)[ep_of == e]) for e in eps["episode_index"].values]
        for s in per[0]:
            eps[f"stats/{k}/{s}"] = [np.asarray(p[s], float) for p in per]
    (tmp / "meta/episodes/chunk-000").mkdir(parents=True)
    eps.to_parquet(tmp / "meta/episodes/chunk-000/file-000.parquet")
    json.dump({"dataset": out_dir.name, "variant": which, "source": str(src_root),
               "frames": {"teleop": "robot base, target FK(action joints), anchor FK(state joints)",
                          "glove": ("robot base, FK(HHs3 joints)" if which == "tile" else
                                    "the segment's SLAM frame, metric: s . T_slam_cam . T_cam_body . inv(T_flange_body)")},
               "flags": {"slam_valid": f"bracketing SLAM pose samples <= {cfg['slam']['bridge_s']} s apart and segment scale ok",
                         "ik_unreached": (f"HHs3 IK did not reach the glove pose: a joint within {cfg['ik_limit_tol']} rad of its range "
                                          f"limit, or joint 3 on the stretched-arm plateau (slam.hhs3_manifest.ik_flag), or "
                                          f"FK more than {cfg['ik_residual_mm']} mm from the IK target rebuilt with our tile chain")},
               "glove_episodes": prov, "provenance": provenance},
              open(tmp / "meta/relative_labels.json", "w"), indent=1)
    tmp.rename(out_dir)


# ---------------------------------------------------------------- verification
def relative_errors(A, B, valid, js):
    """Relative pose of anchor t -> t+j from A vs from B (both (N, 4, 4) poses of one episode)."""
    out = {}
    for j in js:
        i = np.where(valid[:-j] & valid[j:])[0] if j < len(A) else np.zeros(0, int)
        if not len(i):
            continue
        ra, rb = G.inv(A[i]) @ A[i + j], G.inv(B[i]) @ B[i + j]
        out[j] = (1000 * np.linalg.norm(ra[:, :3, 3] - rb[:, :3, 3], axis=1),
                  np.degrees(np.arccos(np.clip((np.trace(np.swapaxes(ra[:, :3, :3], 1, 2) @ rb[:, :3, :3],
                                                         axis1=1, axis2=2) - 1) / 2, -1, 1))))
    return out


def verify(cfg, src_root, out_root, names, df):
    """Structure checks of both datasets and the label comparison slam vs tile on the glove half."""
    import pandas as pd
    res = {}
    data = {}
    for which, name in names.items():
        d = out_root / name
        x = pd.read_parquet(d / "data/chunk-000/file-000.parquet")
        chk = {
            "frames": len(x) == len(df),
            "timeline": all(np.array_equal(x[c].values, df[c].values)
                            for c in ("frame_index", "episode_index", "index", "task_index")),
            "timestamps": bool(np.allclose(x["timestamp"].values, df["timestamp"].values)),
            "gripper_action": bool(np.allclose(np.stack(x["action"].values)[:, 6],
                                               np.stack(df["action"].values)[:, 6])),
            "gripper_state": bool(np.allclose(x["observation.state"].values,
                                              np.stack(df["observation.state"].values)[:, 6])),
            "videos_identical": all(os.path.samefile(f, src_root / f.relative_to(d))
                                    or filecmp.cmp(f, src_root / f.relative_to(d), shallow=False)
                                    for f in (d / "videos").rglob("*.mp4")),
            "finite": bool(np.isfinite(np.stack(x["action"].values)).all()
                           and np.isfinite(np.stack(x["anchor_pose"].values)).all()),
        }
        try:
            from lerobot.datasets.lerobot_dataset import LeRobotDataset
            ds = LeRobotDataset(name, root=d)
            item = ds[int(len(ds) * 0.7)]
            chk["lerobot_load"] = bool(item["action"].shape[-1] == 7 and len(ds) == len(df))
        except Exception as ex:                                   # noqa: BLE001
            chk["lerobot_load"] = f"FAILED: {ex!r}"
        res[which] = chk
        data[which] = x
    if {"tile", "slam"} <= set(data):
        fps_real = cfg["fps"] * cfg["slow"]
        js = [round(0.4 * fps_real), round(1.0 * fps_real), 99]
        ep = data["tile"]["episode_index"].values
        g0 = cfg["source"]["glove_first_episode"]
        per_sess, pooled = {}, {j: ([], []) for j in js}
        chunk = []
        prov = {p["episode"]: p for p in json.load(open(out_root / names["slam"] / "meta/relative_labels.json"))["glove_episodes"]}
        for e in np.unique(ep[ep >= g0]):
            r = np.where(ep == e)[0]
            A = pose6_to_T(np.stack(data["slam"]["action"].values[r])[:, :6].astype(float))
            B = pose6_to_T(np.stack(data["tile"]["action"].values[r])[:, :6].astype(float))
            v = (data["slam"]["slam_valid"].values[r] > 0.5) & (data["slam"]["ik_unreached"].values[r] < 0.5)
            errs = relative_errors(A, B, v, js)
            sess = prov[int(e)]["session"]
            for j, (pm, rd) in errs.items():
                pooled[j][0].append(pm)
                per_sess.setdefault(sess, {}).setdefault(j, []).append(pm)
            # chunk mean over j = 1..99 for each anchor
            ch = relative_errors(A, B, v, range(1, 100))
            if ch:
                L = len(A)
                M = np.full((L, 99), np.nan)
                for j, (pm, _) in ch.items():
                    i = np.where(v[:-j] & v[j:])[0]
                    M[i, j - 1] = pm
                ok = v & np.isfinite(M).any(1)
                chunk += list(np.nanmean(M[ok], 1))
        q = lambda a: {"n": int(len(a)), "median": float(np.median(a)), "p90": float(np.percentile(a, 90))} if len(a) else None
        res["labels_slam_vs_tile"] = {
            "steps_real_s": {str(j): round(j / fps_real, 3) for j in js},
            "pooled_pos_mm": {str(j): q(np.concatenate(pooled[j][0]) if pooled[j][0] else np.zeros(0)) for j in js},
            "per_session_pos_mm": {s: {str(j): q(np.concatenate(v)) for j, v in d.items()} for s, d in per_sess.items()},
            "chunk_mean_pos_mm": q(np.array(chunk)),
        }
    return res


# ---------------------------------------------------------------- main
def provenance_info(cfg_path, argv):
    def git(*a):
        return subprocess.run(["git", "-C", str(C.REPO), *a], capture_output=True, text=True).stdout.strip()
    from slam.robot_fk import I2RT_DIR
    import importlib.metadata as md
    pk = {p: md.version(p) for p in ("mujoco", "mink", "numpy", "pandas", "pyarrow", "lerobot")}
    return {"git_commit": git("rev-parse", "HEAD"), "git_clean": git("status", "--porcelain") == "",
            "i2rt_commit": subprocess.run(["git", "-C", str(I2RT_DIR), "rev-parse", "HEAD"], capture_output=True,
                                          text=True).stdout.strip(),
            "packages": pk, "python": sys.version.split()[0], "command": " ".join(argv), "config": str(cfg_path),
            "time": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}


def main():
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify"])
    ap.add_argument("config")
    ap.add_argument("--only", choices=["tile", "slam"])
    ap.add_argument("--out-root", help="default: the config's out_root")
    ap.add_argument("--allow-dirty", action="store_true", help="trial runs only (recorded)")
    a = ap.parse_args()
    cfg_path = Path(a.config)
    cfg = yaml.safe_load(open(cfg_path))
    cfg["_trial"] = a.allow_dirty
    exp_dir = cfg_path.parent
    out_root = Path(a.out_root or cfg["out_root"])
    src_root = Path(os.path.expanduser(cfg["source"]["root"]))
    names = {k: v for k, v in cfg["outputs"].items() if a.only in (None, k)}
    prov = provenance_info(cfg_path, sys.argv)
    if a.cmd == "build":
        if not prov["git_clean"] and not a.allow_dirty:
            raise SystemExit("work tree not clean (commit the config first, or --allow-dirty for a trial)")
        from slam.robot_fk import YamFK
        fk = YamFK()
        df = load_source(src_root)
        t0 = time.time()
        for which, name in names.items():
            cols, gprov = build_columns(cfg, df, fk, which)
            write_dataset(cfg, src_root, out_root / name, df, cols, gprov, which, prov)
            print(f"wrote {out_root / name} ({time.time() - t0:.0f} s)")
    df = load_source(src_root)
    res = verify(cfg, src_root, out_root, names, df)
    print(json.dumps(res, indent=1))
    if not a.allow_dirty and a.cmd == "build":
        (exp_dir / "results").mkdir(exist_ok=True)
        json.dump(res, open(exp_dir / "results/metrics.json", "w"), indent=1)
        runs = json.load(open(exp_dir / "run.json")) if (exp_dir / "run.json").exists() else {"invocations": []}
        runs["invocations"].append({**prov, "outputs": {k: str(out_root / v) for k, v in names.items()}})
        json.dump(runs, open(exp_dir / "run.json", "w"), indent=1)


if __name__ == "__main__":
    main()
