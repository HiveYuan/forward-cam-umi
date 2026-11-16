#!/usr/bin/env python3
"""Relative-action LeRobot shards of collected glove sessions and the training mix (slam.ingest stages 5-7).

A collected session (docs/SLAM_COLLECTION.md) after `slam.collect prep` and its SLAM experiment (slam.run) becomes
one *shard*: a LeRobot v3 dataset with exactly the features of slam.rel_dataset's datasets, so that it can be
appended to one of them (default pilot_mix_gHs3_rel_slam_v3) without touching its episodes:
  timeline           step j at t_start + j / (fps * slow) s of the recording (15 fps declared, slow 2.5: the
                     HHs3 convention), up to t_end
  observation.images the head frame nearest in wall clock, resized (INTER_AREA) to the base's size, RGB, not
                     undistorted (Yosub's build_dataset recipe)
  action / anchor    tool pose s . T_slam_cam . T_cam_body . T_body_tool from the experiment's analysis view
                     (slam.rel_dataset.SlamSession / poses_at, the unit's handeye_glove_<unit>.json), anchor = action
  slam_valid         bracketing pose samples <= bridge_s apart and the segment's scale ok (slam.rel_dataset rule)
  ik_unreached       0 (there is no IK on the glove side)
  gripper            gt/gripper_head.npz (head camera, gripper command units), median-filtered over
                     gripper_median_s, interpolated at the steps; action[6] = observation.state (HHs3: state == action)
  meta/collected.json         provenance and the per-episode gate rows
  meta/cam_tool_rows.npz      T_cam_tool per row (ball pose . T_body_tool), merged into the mix's cam_tool_pose.npz
Gates (batch `gates`, ingest design 2026-11-16, thresholds as exp016):
  episode dropped    no SLAM pose at all, its scale failed, or gripper coverage (a head-width sample within
                     grip_label_tol_s, build_dataset's label_tol) below grip_coverage_min (build_dataset's min_coverage)
  session held       median 1 s label error vs the tile GT above label_err_1s_mm_max (sessions with tiles only),
                     slam_valid over the kept steps below slam_valid_min, or more than max_rejected_fraction of its
                     configured episodes dropped. A held session is not mixed until the batch lists it in accept_held.

  L=/home/student/miniconda3/envs/lerobot52/bin/python        # lerobot 0.5.2 (aggregate), cv2, pandas
  PYTHONPATH=. $L -m slam.collect_dataset export --batch <batch.yaml> --session <ds> --exp <colNNN_...>
  PYTHONPATH=. $L -m slam.collect_dataset mix    --batch <batch.yaml> --shards <shard dir> ...
  PYTHONPATH=. $L -m slam.collect_dataset verify --batch <batch.yaml>
Exit codes: 0 done, 3 the session is held by a gate (export) / verification failed (verify).
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G

BUILDER_VERSION = 1
FEATURES = ("action", "observation.state", "anchor_pose", "slam_valid", "ik_unreached")
HELD = 3


# ---------------------------------------------------------------- small helpers
def load(p):
    with open(p) as f:
        return json.load(f)


def medfilt(v, n):
    """Running median over n samples (odd), edges padded with the end values (scipy's mode='nearest')."""
    v = np.asarray(v, float)
    if n <= 1 or len(v) < 2:
        return v.copy()
    n |= 1
    p = n // 2
    return np.median(np.lib.stride_tricks.sliding_window_view(np.pad(v, p, mode="edge"), n), axis=1)


def timeline(t_start, t_end, fps, slow):
    """Step times of an episode: t_start + j / (fps * slow) while < t_end (build_dataset's np.arange)."""
    return np.arange(t_start, t_end, 1.0 / (fps * slow))


def nearest_dist(ts, tq):
    """Distance from each tq to the nearest of the sorted samples ts (inf when there are none)."""
    ts = np.asarray(ts, float)
    if len(ts) == 0:
        return np.full(len(tq), np.inf)
    if len(ts) == 1:
        return np.abs(tq - ts[0])
    i = np.clip(np.searchsorted(ts, tq), 1, len(ts) - 1)
    return np.minimum(np.abs(tq - ts[i - 1]), np.abs(tq - ts[i]))


def nearest_index(ts, tq):
    ts = np.asarray(ts, float)
    i = np.clip(np.searchsorted(ts, tq), 1, len(ts) - 1)
    return np.where(np.abs(tq - ts[i - 1]) <= np.abs(ts[i] - tq), i - 1, i)


def gripper_series(t, v, tq, median_s, label_tol_s):
    """(gripper at tq, coverage): the head-width samples median-filtered over median_s (window in samples at
    their median rate), linearly interpolated (clamped at the ends); coverage = share of steps with a sample
    within label_tol_s."""
    t, v = np.asarray(t, float), np.asarray(v, float)
    if len(t) < 2:
        return np.full(len(tq), np.nan), 0.0
    rate = 1.0 / max(np.median(np.diff(t)), 1e-6)
    f = medfilt(v, int(round(median_s * rate)) | 1) if median_s > 0 else v
    return np.interp(tq, t, f), float(np.mean(nearest_dist(t, tq) <= label_tol_s))


def gate_session(rows, label_err_mm, gates):
    """rows: per configured episode {episode, steps, slam_valid, scale_ok, grip_coverage}; label_err_mm: the
    session's median 1 s label error vs the tile GT (None without tiles). Returns (kept episodes, per-row reasons,
    session verdict {held: bool, reasons: [...]})."""
    kept, reasons = [], {}
    for r in rows:
        why = []
        if not r["scale_ok"]:
            why.append("scale failed")
        if r["slam_valid"] == 0:
            why.append("no SLAM pose")
        if r["grip_coverage"] < gates["grip_coverage_min"]:
            why.append(f"gripper coverage {r['grip_coverage']:.2f} < {gates['grip_coverage_min']}")
        reasons[r["episode"]] = why
        if not why:
            kept.append(r["episode"])
    held = []
    n = len(rows)
    rejected = n - len(kept)
    if n and rejected / n > gates["max_rejected_fraction"]:
        held.append(f"{rejected}/{n} episodes dropped (> {gates['max_rejected_fraction']:.0%})")
    steps = sum(r["steps"] for r in rows if r["episode"] in kept)
    valid = sum(r["slam_valid"] for r in rows if r["episode"] in kept)
    frac = valid / steps if steps else 0.0
    if frac < gates["slam_valid_min"]:
        held.append(f"slam_valid {frac:.3f} < {gates['slam_valid_min']}")
    if label_err_mm is not None and label_err_mm > gates["label_err_1s_mm_max"]:
        held.append(f"label error at 1 s {label_err_mm:.1f} mm > {gates['label_err_1s_mm_max']} mm")
    if not kept:
        held.append("no episode left")
    return kept, reasons, {"held": bool(held), "reasons": held, "slam_valid": frac, "steps": steps,
                           "label_err_1s_mm": label_err_mm}


# ---------------------------------------------------------------- session inputs
def view_dir(exp):
    return C.WORK / "runs" / exp / "main" / "view"


def scale_label(exp, run):
    return load(C.REPO / "experiments" / exp / "results" / f"scale_{run}.json")["label"]


def label_errors(ds, exp, run, label, horizon=100, step=15):
    """Median and per-episode 1 s label error (mm) of the experiment's labels vs its tile labels
    (slam.labels.anchor_errors on the experiment's analysis view)."""
    from slam import labels as L
    seg_root = view_dir(exp) / ds / "segments"
    orig = C.segments_dir
    C.segments_dir = lambda name: seg_root if name == ds else orig(name)
    try:
        per, allv = {}, []
        for seg, _, e in L.anchor_errors(ds, f"{run}@{label}", horizon):
            for j, pos, _rot in e:
                if j == step:
                    per.setdefault(seg, []).append(pos)
                    allv.append(pos)
    finally:
        C.segments_dir = orig
    return (float(np.median(allv)) if allv else None,
            {s: {"median_mm": float(np.median(v)), "n": len(v)} for s, v in per.items()})


def head_walls(ds):
    stem = C.session(ds)["head_stem"]
    return np.array([x["wall"] for x in load(C.COLLECT_REPO / "data/raw" / f"{stem}_ts.json")], float)


def ball_track(ds):
    z = np.load(C.gt_dir(ds) / "ball_poses.npz")
    walls = head_walls(ds)
    t = walls[z["full_k"].astype(int)]
    T = G.rt_to_T(z["full_rvec"], z["full_tvec"])
    o = np.argsort(t)
    return t[o], T[o]


def T_body_tool(unit):
    return G.inv(np.array(load(C.CALIB / f"handeye_glove_{unit}.json")["T_flange_body"], float)[None])[0]


def session_columns(ds, exp, d):
    """Per configured episode of experiment `exp`: step times, the label columns and the gate inputs."""
    from slam.rel_dataset import SlamSession, poses_at, pose6
    cfg = __import__("yaml").safe_load(open(C.REPO / "experiments" / exp / "config.yaml"))
    if cfg["data"]["session"] != ds:
        raise SystemExit(f"{exp} is session {cfg['data']['session']}, not {ds}")
    run = d["slam_run"]
    label = scale_label(exp, run)
    unit = C.session(ds)["glove"]
    T_bt = T_body_tool(unit)
    S = SlamSession(ds, {"experiment": exp, "run": run, "scale": label}, T_bt)
    S.segdir = view_dir(exp) / ds / "segments"
    marks = {e["episode_index"]: e for e in load(C.COLLECT_REPO / "data/raw" / f"{ds}_glove_episodes.json")["episodes"]}
    grip = np.load(C.gt_dir(ds) / "gripper_head.npz")
    tb, Tb = ball_track(ds)
    walls = head_walls(ds)
    out = []
    for e in cfg["data"]["episodes"]:
        m = marks[e]
        tq = timeline(m["t_start"], m["t_end"], d["fps"], d["slow"])
        t, T, s = S.samples(e)
        Tq, valid = poses_at(t, T, tq, d["bridge_s"])
        if f"g{e}_t" in grip.files:
            g, cov = gripper_series(grip[f"g{e}_t"], grip[f"g{e}_v"], tq, d["gripper_median_s"], d["grip_label_tol_s"])
        else:
            g, cov = np.full(len(tq), np.nan), 0.0
        Tc, cvalid = poses_at(tb, Tb, tq, d["bridge_s"])
        k = nearest_index(walls, tq)
        out.append({"episode": int(e), "t": tq, "action": np.c_[pose6(Tq), g], "anchor": pose6(Tq),
                    "slam_valid": valid, "gripper": g, "grip_coverage": cov, "scale": s, "scale_ok": s is not None,
                    "cam6": pose6(Tc @ T_bt[None]), "cam_valid": cvalid, "frame_k": k,
                    "frame_dt": np.abs(walls[k] - tq), "t_start": m["t_start"], "t_end": m["t_end"]})
    return out, run, label


# ---------------------------------------------------------------- video
class ColorFrames:
    """Wanted frames of an mkv in increasing index order, colour, full size. Frame k is entry k of <stem>_ts.json,
    so frames are counted by sequential grab, never seeked (scripts/field_qc.py's Frames, in colour). JPEG packets
    are read raw and decoded only when wanted where they decode on their own (macOS recordings)."""

    def __init__(self, path):
        import cv2
        self.cv2, self.path = cv2, str(path)
        self.cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open {path}")
        self.raw = bool(self.cap.set(cv2.CAP_PROP_FORMAT, -1))
        self.idx, self.pending = -1, None
        if self.raw:
            ok = self.cap.grab()
            okr, buf = self.cap.retrieve() if ok else (False, None)
            img = self._imdecode(buf) if okr else None
            if img is None:
                self.cap.release()
                self.cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
                self.raw = False
            else:
                self.pending = img

    def _imdecode(self, buf):
        if buf is None or buf.size == 0:
            return None
        return self.cv2.imdecode(np.asarray(buf).reshape(-1), self.cv2.IMREAD_COLOR)

    def read(self, wanted):
        """Yields (k, BGR image) for the sorted unique wanted indices, all > the last index read."""
        wanted = sorted(set(int(k) for k in wanted))
        j = 0
        while j < len(wanted):
            if self.idx == -1 and self.pending is not None:
                self.idx, img = 0, self.pending
                self.pending = None
            else:
                if not self.cap.grab():
                    ok, _ = self.cap.read()
                    if not ok:
                        return
                    self.idx += 1
                    continue
                self.idx += 1
                img = None
            while j < len(wanted) and wanted[j] < self.idx:
                j += 1
            if j < len(wanted) and wanted[j] == self.idx:
                if img is None:
                    ok, buf = self.cap.retrieve()
                    img = (self._imdecode(buf) if self.raw else buf) if ok else None
                if img is not None:
                    yield self.idx, img
                j += 1


# ---------------------------------------------------------------- export
def base_info(d):
    return load(Path(d["base"]["root"]) / "meta" / "info.json")


def image_key(info):
    keys = [k for k, v in info["features"].items() if v["dtype"] == "video"]
    if len(keys) != 1:
        raise SystemExit(f"base dataset must have one camera, has {keys}")
    return keys[0]


def task_string(d):
    if d["task"] != "base_glove":
        return d["task"]
    import pandas as pd
    root = Path(d["base"]["root"])
    tasks = pd.read_parquet(root / "meta" / "tasks.parquet")
    df = pd.concat([pd.read_parquet(f, columns=["episode_index", "task_index"])
                    for f in sorted((root / "data").glob("chunk-*/file-*.parquet"))])
    ti = int(df[df["episode_index"] >= d["base"]["glove_first_episode"]]["task_index"].mode().iloc[0])
    return str(tasks.index[tasks["task_index"] == ti][0])


def shard_name(ds, exp, d, kept):
    keys = ("fps", "slow", "bridge_s", "gripper_median_s", "grip_label_tol_s", "slam_run", "task")
    h = hashlib.sha256(json.dumps({"v": BUILDER_VERSION, "episodes": kept, **{k: d[k] for k in keys},
                                   "base": d["base"]["repo"]}, sort_keys=True).encode()).hexdigest()[:8]
    return f"{ds}__{exp}__{h}"


def write_shard(ds, cols, kept, out_dir, d, provenance):
    from lerobot.configs.video import VideoEncoderConfig
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    import cv2
    info = base_info(d)
    ik = image_key(info)
    vinfo = info["features"][ik].get("info") or {}
    H, W = info["features"][ik]["shape"][:2]
    feats = {k: {"dtype": info["features"][k]["dtype"], "shape": tuple(info["features"][k]["shape"]),
                 "names": info["features"][k]["names"]} for k in (*FEATURES, ik)}
    enc = VideoEncoderConfig(vcodec={"av1": "libsvtav1"}.get(vinfo.get("video.codec"), "libsvtav1"),
                             pix_fmt=vinfo.get("video.pix_fmt", "yuv420p"), g=vinfo.get("video.g", 2),
                             crf=vinfo.get("video.crf", 30), preset=vinfo.get("video.preset", 12))
    tmp = out_dir.with_name(out_dir.name + ".partial")
    if tmp.exists():
        shutil.rmtree(tmp)
    ds_out = LeRobotDataset.create(repo_id=out_dir.name, fps=int(d["fps"]), features=feats, root=tmp,
                                   robot_type=info.get("robot_type"), use_videos=True, image_writer_threads=4,
                                   camera_encoder=enc)
    task = task_string(d)
    reader = ColorFrames(C.COLLECT_REPO / "data/raw" / f"{C.session(ds)['head_stem']}.mkv")
    by_ep = {c["episode"]: c for c in cols}
    cam_rows, n_img_gap = [], 0
    order = sorted(kept, key=lambda e: by_ep[e]["t_start"])         # recording order: the reader only goes forward
    provenance["episodes"] = order                                  # shard episode i = session episode order[i]
    for e in order:
        c = by_ep[e]
        imgs = dict(reader.read(c["frame_k"]))
        missing = sorted(set(int(k) for k in c["frame_k"]) - set(imgs))
        if missing:
            raise SystemExit(f"{ds} ep{e}: {len(missing)} frames could not be read (first {missing[:5]})")
        n_img_gap += int(np.sum(c["frame_dt"] > d["grip_label_tol_s"]))
        f32 = np.float32
        for j in range(len(c["t"])):
            img = imgs[int(c["frame_k"][j])]
            img = cv2.cvtColor(cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
            ds_out.add_frame({"action": c["action"][j].astype(f32),
                              "observation.state": np.array([c["gripper"][j]], f32),
                              "anchor_pose": c["anchor"][j].astype(f32),
                              "slam_valid": np.array([float(c["slam_valid"][j])], f32),
                              "ik_unreached": np.array([0.0], f32),
                              ik: img, "task": task})
        ds_out.save_episode()
        cam_rows.append((c["cam6"], c["cam_valid"]))
    ds_out.finalize()
    np.savez(tmp / "meta" / "cam_tool_rows.npz", pose6=np.concatenate([p for p, _ in cam_rows]),
             valid=np.concatenate([v for _, v in cam_rows]))
    provenance["image_steps_beyond_label_tol"] = n_img_gap
    json.dump(provenance, open(tmp / "meta" / "collected.json", "w"), indent=1)
    tmp.rename(out_dir)


def cmd_export(a):
    from slam.ingest import load_batch, batch_dir
    b = load_batch(a.batch)
    d = b["dataset"]
    ds, exp = a.session, a.exp
    cols, run, label = session_columns(ds, exp, d)
    err, per_ep = label_errors(ds, exp, run, label) if not a.no_label_check else (None, {})
    rows = [{"episode": c["episode"], "steps": len(c["t"]), "slam_valid": int(c["slam_valid"].sum()),
             "scale_ok": c["scale_ok"], "scale": c["scale"], "grip_coverage": round(c["grip_coverage"], 4),
             "label_err_1s_mm": (per_ep.get(f"ep{c['episode']:02d}") or {}).get("median_mm")} for c in cols]
    kept, reasons, verdict = gate_session(rows, err, b["gates"])
    for r in rows:
        r["dropped"] = reasons[r["episode"]]
    accepted = ds in b["accept_held"]
    out = {"session": ds, "experiment": exp, "slam_run": run, "scale": label, "gates": b["gates"],
           "verdict": verdict, "accepted_by_review": accepted, "kept": kept, "rows": rows,
           "builder_version": BUILDER_VERSION, "time": time.strftime("%F %T")}
    sdir = batch_dir(b) / "sessions"
    sdir.mkdir(parents=True, exist_ok=True)
    print(f"{ds}: {len(kept)}/{len(rows)} episodes kept; slam_valid {verdict['slam_valid']:.3f}; "
          f"label error 1 s {err if err is None else round(err, 2)} mm; held: {verdict['reasons'] or 'no'}")
    if verdict["held"] and not accepted:
        json.dump(out, open(sdir / f"{ds}.json", "w"), indent=1)
        print(f"HELD: {ds} ({'; '.join(verdict['reasons'])}). Review, then list it under accept_held in the batch "
              f"file to mix it anyway, or drop it from `sessions`.")
        return HELD
    name = shard_name(ds, exp, d, kept)
    shard = Path(d["shard_root"]) / name
    if not shard.exists():
        prov = {"session": ds, "experiment": exp, "slam_run": run, "scale": label, "unit": C.session(ds)["glove"],
                "episodes": kept, "params": {k: d[k] for k in ("fps", "slow", "bridge_s", "gripper_median_s",
                                                               "grip_label_tol_s")},
                "handeye": f"handeye_glove_{C.session(ds)['glove']}.json", "builder_version": BUILDER_VERSION,
                "rows": rows}
        write_shard(ds, cols, kept, shard, d, prov)
    out["shard"] = str(shard)
    json.dump(out, open(sdir / f"{ds}.json", "w"), indent=1)
    print(f"shard {shard}")
    return 0


# ---------------------------------------------------------------- mix
def val_split(n, fraction):
    """Positions (0..n-1, recording order) of a session's held-out episodes: round(fraction * n), at least one
    when fraction > 0 and n >= 2, evenly spread over the session (the middle of n_val equal parts)."""
    if fraction <= 0 or n < 2:
        return []
    k = min(n - 1, max(1, int(round(fraction * n))))
    return sorted({int((i + 0.5) * n / k) for i in range(k)})


def staged_copy(root, dst):
    """A hard-linked copy of a LeRobot v3 dataset whose episode metadata points at the files that exist.
    slam.rel_dataset wrote its datasets' meta/episodes into one parquet but kept the source's
    meta/episodes/{chunk,file}_index columns (pilot_mix_gHs3_rel_slam_v3: file_index 0-5, one file), which
    lerobot's aggregate_datasets follows. The base itself is left untouched."""
    import pandas as pd
    root, dst = Path(root), Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    for f in root.rglob("*"):
        if f.is_dir() or f.relative_to(root).parts[:2] == ("meta", "episodes"):
            continue
        t = dst / f.relative_to(root)
        t.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(f, t)
        except OSError:
            shutil.copy2(f, t)
    eps = pd.concat([pd.read_parquet(f) for f in sorted((root / "meta/episodes").glob("chunk-*/file-*.parquet"))])
    eps = eps.sort_values("episode_index").reset_index(drop=True)
    eps["meta/episodes/chunk_index"] = 0
    eps["meta/episodes/file_index"] = 0
    (dst / "meta/episodes/chunk-000").mkdir(parents=True)
    eps.to_parquet(dst / "meta/episodes/chunk-000/file-000.parquet")
    return dst


def cmd_mix(a):
    import pandas as pd
    from lerobot.datasets.aggregate import aggregate_datasets
    from slam.ingest import load_batch, batch_dir
    b = load_batch(a.batch)
    d = b["dataset"]
    base_root = Path(d["base"]["root"])
    shards = [Path(s) for s in a.shards]
    out_dir = Path(d["out_root"]) / d["out"]
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists")
    tmp = out_dir.with_name(out_dir.name + ".partial")
    if tmp.exists():
        shutil.rmtree(tmp)
    staged = staged_copy(base_root, out_dir.with_name(out_dir.name + ".base_staged"))
    try:
        aggregate_datasets(repo_ids=[d["base"]["repo"]] + [s.name for s in shards], aggr_repo_id=out_dir.name,
                           roots=[staged] + shards, aggr_root=tmp, concatenate_videos=False)
    finally:
        shutil.rmtree(staged, ignore_errors=True)
    # the base's own extras (its episodes keep their indices: they come first)
    for f in ("val_episodes.json", "val_episodes_glove.json"):
        if (base_root / "meta" / f).exists():
            shutil.copy2(base_root / "meta" / f, tmp / "meta" / f)
    df = pd.concat([pd.read_parquet(f, columns=["index", "episode_index", "frame_index"])
                    for f in sorted((tmp / "data").glob("chunk-*/file-*.parquet"))]).sort_values("index")
    n_base_eps = load(base_root / "meta" / "info.json")["total_episodes"]
    new_eps = sorted(e for e in df["episode_index"].unique() if e >= n_base_eps)
    # shards' episodes in order -> mix episode indices
    collected, pose, valid, idx, e_next = [], [], [], [], n_base_eps
    for s in shards:
        prov = load(s / "meta" / "collected.json")
        rows = np.load(s / "meta" / "cam_tool_rows.npz")
        sinfo = load(s / "meta" / "info.json")
        n = sinfo["total_episodes"]
        mix_eps = list(range(e_next, e_next + n))
        e_next += n
        if len(prov["episodes"]) != n:
            raise SystemExit(f"{s.name}: {n} episodes, provenance lists {len(prov['episodes'])}")
        sdf = df[df["episode_index"].isin(mix_eps)].sort_values(["episode_index", "frame_index"])
        if len(sdf) != len(rows["pose6"]):
            raise SystemExit(f"{s.name}: {len(sdf)} rows in the mix vs {len(rows['pose6'])} cam rows")
        idx.append(sdf["index"].values)
        pose.append(rows["pose6"])
        valid.append(rows["valid"])
        # write_shard saved the episodes in recording order (prov["episodes"] is that order)
        collected.append({"shard": s.name, "session": prov["session"], "experiment": prov["experiment"],
                          "mix_episodes": {int(m): int(e) for m, e in zip(mix_eps, prov["episodes"])},
                          "params": prov["params"], "unit": prov["unit"]})
    if e_next != n_base_eps + len(new_eps):
        raise SystemExit(f"episode count mismatch: shards {e_next - n_base_eps}, mix {len(new_eps)}")
    # cam_tool_pose.npz: the base's rows + the shards'
    bc = base_root / "meta" / "cam_tool_pose.npz"
    if bc.exists():
        z = np.load(bc)
        meta = json.loads(str(z["meta"]))
        meta["collected"] = "glove from the ball (gt/ball_poses.npz full) . T_body_tool, slam.collect_dataset"
        np.savez(tmp / "meta" / "cam_tool_pose.npz", index=np.concatenate([z["index"], *idx]),
                 pose6=np.concatenate([z["pose6"], *pose]), valid=np.concatenate([z["valid"], *valid]),
                 meta=json.dumps(meta))
    rl = load(base_root / "meta" / "relative_labels.json") if (base_root / "meta" / "relative_labels.json").exists() else {}
    rl.update({"dataset": out_dir.name, "base": {"repo": d["base"]["repo"], "root": str(base_root),
                                                 "episodes": n_base_eps}, "collected": collected,
               "collected_flags": {"slam_valid": f"bracketing SLAM pose samples <= {d['bridge_s']} s apart and the "
                                                 "segment's scale ok", "ik_unreached": "0: no IK on the glove side"},
               "batch": b["batch"], "time": time.strftime("%F %T")})
    # train / val split of the collected episodes, per session (mix episodes are in recording order)
    split = {}
    for c in collected:
        eps = sorted(int(k) for k in c["mix_episodes"])
        val = [eps[i] for i in val_split(len(eps), d["val_fraction"])]
        split[c["session"]] = {"train": [e for e in eps if e not in val], "val": val}
    rl["collected_val"] = {"fraction": d["val_fraction"], "rule": "per session, evenly spread in recording order "
                                                                  "(slam.collect_dataset.val_split)"}
    json.dump(rl, open(tmp / "meta" / "relative_labels.json", "w"), indent=1)
    json.dump(split, open(tmp / "meta" / "collected_episodes.json", "w"), indent=1)
    json.dump({"val_episodes": sorted(e for s in split.values() for e in s["val"]),
               "rule": rl["collected_val"]["rule"], "fraction": d["val_fraction"],
               "per_session": {s: v["val"] for s, v in split.items()}},
              open(tmp / "meta" / "val_episodes_collected.json", "w"), indent=1)
    tmp.rename(out_dir)
    json.dump({"dataset": str(out_dir), "base_episodes": n_base_eps, "new_episodes": len(new_eps),
               "shards": [s.name for s in shards]}, open(batch_dir(b) / "mix.json", "w"), indent=1)
    print(f"mix {out_dir}: {n_base_eps} base + {len(new_eps)} collected episodes")
    return 0


# ---------------------------------------------------------------- verify
def cmd_verify(a):
    import cv2
    import pandas as pd
    from slam.ingest import load_batch, batch_dir
    from slam.relative_dataset import RelChunkDataset, load_episode_list
    b = load_batch(a.batch)
    d = b["dataset"]
    root, base_root = Path(d["out_root"]) / d["out"], Path(d["base"]["root"])
    problems, res = [], {"dataset": str(root)}
    read = lambda r, cols=None: pd.concat([pd.read_parquet(f, columns=cols) for f in
                                           sorted((r / "data").glob("chunk-*/file-*.parquet"))]).sort_values("index")
    mix, base = read(root), read(base_root)
    n_base = len(base)
    # 1. the base's rows are unchanged
    for k in ("index", "episode_index", "frame_index", "task_index"):
        if not np.array_equal(mix[k].values[:n_base], base[k].values):
            problems.append(f"base column {k} changed")
    for k in FEATURES:
        A = np.stack(mix[k].values[:n_base]).astype(float) if mix[k].dtype == object else mix[k].values[:n_base]
        B = np.stack(base[k].values).astype(float) if base[k].dtype == object else base[k].values
        if not np.array_equal(np.asarray(A, float), np.asarray(B, float)):
            problems.append(f"base column {k} changed")
    # 2. the new rows are finite, flags in {0, 1}, gripper in range
    new = mix.iloc[n_base:]
    act = np.stack(new["action"].values).astype(float)
    if not np.isfinite(act).all():
        problems.append("non-finite actions in the collected episodes")
    for k in ("slam_valid", "ik_unreached"):
        if not set(np.unique(new[k].values)) <= {0.0, 1.0}:
            problems.append(f"{k} not 0/1")
    g = act[:, 6]
    res["collected"] = {"episodes": int(new["episode_index"].nunique()), "steps": len(new),
                        "slam_valid": float(new["slam_valid"].mean()),
                        "gripper_p1_p50_p99": np.percentile(g, [1, 50, 99]).round(3).tolist()}
    bg = base[base["episode_index"] >= d["base"]["glove_first_episode"]]
    res["base_glove"] = {"gripper_p1_p50_p99": np.percentile(np.stack(bg["action"].values)[:, 6], [1, 50, 99]).round(3).tolist()}
    # 3. motion statistics: 1 s of glove time in the start tool frame (the tool-frame convention check)
    from slam.rel_dataset import pose6_to_T

    def motion(df):
        dd = []
        for _, x in df.groupby("episode_index"):
            x = x.sort_values("frame_index")
            T = pose6_to_T(np.stack(x["action"].values)[:, :6].astype(float)[x["slam_valid"].values > 0.5])
            if len(T) > 15:
                dd.append((G.inv(T[:-15]) @ T[15:])[:, :3, 3])
        dd = np.concatenate(dd) * 1000
        nrm = np.linalg.norm(dd, axis=1)
        u = dd[nrm > 20] / nrm[nrm > 20, None]
        return {"median_mm": float(np.median(nrm)), "p90_mm": float(np.percentile(nrm, 90)),
                "mean_direction": u.mean(0).round(3).tolist()}
    res["motion_1s"] = {"base_glove": motion(bg), "collected": motion(new)}
    # 4. RelChunkDataset over a few base and collected episodes, with the first training arm's settings
    arm = (b.get("train") or [None])[0]
    if arm:
        tcfg = __import__("yaml").safe_load(open(C.REPO / "experiments" / arm["template"] / "config.yaml"))
        rel = tcfg.get("relative") or {}
        eps = [int(x) for x in load_episode_list(C.REPO / tcfg["dataset"]["episodes"])[-2:]]
        eps += sorted(int(e) for e in new["episode_index"].unique())[:2]
        stats = load(C.REPO / rel["stats"]) if rel.get("stats") else None
        rd = RelChunkDataset(d["out"], root, eps, stats, masks=tuple(rel.get("masks", ())),
                             anchor=rel.get("anchor", "anchor_pose"), state=rel.get("state", "gripper"))
        items = [rd[i] for i in np.linspace(0, len(rd) - 1, 6).astype(int)]
        bad = [i for i, it in enumerate(items) if not all(np.isfinite(np.asarray(it[k])).all()
                                                           for k in ("action", "observation.state"))]
        if bad:
            problems.append(f"RelChunkDataset items with non-finite values: {bad}")
        res["rel_chunk_check"] = {"episodes": eps, "anchors": rd.num_frames,
                                  "state_dim": int(np.asarray(items[0]["observation.state"]).shape[-1]),
                                  "action_shape": list(np.asarray(items[0]["action"]).shape)}
    # 5. contact sheet: base glove frames (top) vs collected frames (bottom)
    try:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        info = load(root / "meta" / "info.json")
        ik = image_key(info)
        rng = np.random.default_rng(0)
        pick = lambda eps: [int(e) for e in rng.choice(eps, size=min(6, len(eps)), replace=False)]
        rows = []
        for eps in (pick(sorted(bg["episode_index"].unique())), pick(sorted(new["episode_index"].unique()))):
            tiles = []
            for e in eps:
                ds = LeRobotDataset(d["out"], root=root, episodes=[e])
                img = np.asarray(ds[len(ds) // 2][ik])            # (3, H, W) float RGB in [0, 1]
                tiles.append(np.ascontiguousarray((img.transpose(1, 2, 0) * 255).astype(np.uint8)[:, :, ::-1]))
            rows.append(np.concatenate([cv2.resize(t, (320, 180)) for t in tiles], 1))
        w = max(r.shape[1] for r in rows)
        sheet = np.concatenate([np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0))) for r in rows], 0)
        out = batch_dir(b) / "frames_base_vs_collected.jpg"
        cv2.imwrite(str(out), sheet)
        res["contact_sheet"] = str(out)
    except Exception as ex:                      # the sheet is a convenience; report, do not fail
        res["contact_sheet_error"] = f"{type(ex).__name__}: {ex}"
    res["problems"] = problems
    json.dump(res, open(batch_dir(b) / "verify.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
    return HELD if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("export")
    p.add_argument("--batch", required=True); p.add_argument("--session", required=True)
    p.add_argument("--exp", required=True)
    p.add_argument("--no-label-check", action="store_true", help="skip the tile-GT label error (no tiles)")
    p = sub.add_parser("mix")
    p.add_argument("--batch", required=True); p.add_argument("--shards", nargs="+", required=True)
    p = sub.add_parser("verify")
    p.add_argument("--batch", required=True)
    a = ap.parse_args()
    sys.exit({"export": cmd_export, "mix": cmd_mix, "verify": cmd_verify}[a.cmd](a))


if __name__ == "__main__":
    main()
