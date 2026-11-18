#!/usr/bin/env python3
"""Export SLAM head-camera trajectories of glove episodes, one npz per episode (for Yosub, 2026-11-18).

  hhs3       the 200 pilot_glove_HHs3 episodes (= pilot_mix_gHs3 episode 178 + hhs3), from the SLAM sources of a
             rel_dataset config (exp045: the runs behind pilot_mix_gHs3_rel_slam_v3 / D2a)
  collected  the collected episodes of a mix built by slam.collect_dataset (pilot_mix_gHs3_yuan_rel_slam_v1: the
             134 yuan kitchen episodes, mix episodes 378+), from the shards' experiments (col015-col020)

Two time bases:
  frame_*  every head-camera frame DROID processed (the segment: ~5 s preroll + the episode, ~26 fps)
  step_*   the dataset timeline, row j = dataset frame_index j, wall time t_start + j / (fps * slow)

Poses are 4x4, metres, NaN where unavailable; the tool frame is the datasets' (i2rt grasp_site, the FK frame):
  frame_T_slam_cam_unscaled  DROID camera pose in the episode's SLAM frame, as estimated (no metric scale)
  scale                      the episode's metric scale s; metric = translation * s
  frame_T_cam_tool           tool pose in the head camera from the glove's marker ball (metric, no SLAM)
  frame_T_<ref>_cam_tile     head camera from the workspace tiles (ground truth, not tile-free); ref = base (robot
                             base, HHs3) or world (the tile layout frame, collected sessions: no robot there)
  step_T_slam_cam            metric camera pose in the SLAM frame, interpolated to the steps
  step_T_slam_tool           s . T_slam_cam . T_cam_tool: the dataset's glove pose (anchor_pose)
  step_slam_valid            the dataset's slam_valid (SLAM pose bracketed within bridge_s, scale ok)
  step_T_cam_tool, step_T_<ref>_cam_tile   interpolated
  step_T_base_tool_fk        (hhs3) FK of the HHs3 joints: Yosub's tile labels

  R=/home/student/miniconda3/envs/lerobot/bin/python
  PYTHONPATH=. $R -m slam.export_traj hhs3 experiments/exp045_rel_datasets_head/config.yaml --out <dir>
  PYTHONPATH=. $R -m slam.export_traj collected <work>/lerobot/pilot_mix_gHs3_yuan_rel_slam_v1 --out <dir>
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from slam import config as C
from slam import geometry as G
from slam.hhs3_manifest import BRACKET_S, MIN_TILES, RMS_MAX
from slam.rel_dataset import SlamSession, poses_at

NAN44 = np.full((4, 4), np.nan)


def interp(t, T, tq, bridge):
    """poses_at, NaN where not bracketed."""
    out, ok = poses_at(t, T, tq, bridge)
    out[~ok] = np.nan
    return out, ok


def tile_cams(cam_world_json):
    """{k: T_cam_world} of the frames with a good tile solve (TakePoses' filter)."""
    return {d["k"]: np.array(d["T_cam_world"], float).reshape(4, 4) for d in json.load(open(cam_world_json))["per_frame"]
            if d["rms"] <= RMS_MAX and d["tiles"] >= MIN_TILES}


def episode_arrays(S, take_episode, tq, T_bt, cams, T_ref_world, ref, bridge, timeline_ok=True):
    """The frame_* and step_* arrays of one episode; S is a SlamSession with its segdir set."""
    n = len(tq)
    d = {f"step_T_{k}": np.tile(NAN44, (n, 1, 1)) for k in ("slam_cam", "slam_tool", "cam_tool", f"{ref}_cam_tile")}
    d["step_wall"] = tq
    d["step_slam_valid"] = np.zeros(n, bool)
    seg = S.segdir / f"ep{take_episode:02d}" if S is not None else None
    if seg is None or not seg.exists():
        return d, None
    s = S.scale.get(seg.name)
    fr = json.load(open(seg / "frames.json"))["frames"]
    ks = np.array([f["k"] for f in fr])
    fw = np.array([f["wall"] for f in fr])
    z = np.load(seg / "slam" / f"{S.spec['run']}.npz")
    g = np.load(seg / "gt.npz")
    Tsc = {int(k): T for k, T, ok in zip(z["k"], z["T_slam_cam"], z["tracked"]) if ok}
    ball = {int(k): T for k, T in zip(g["full_k"], G.rt_to_T(g["full_rvec"], g["full_tvec"]))}
    d["frame_k"] = ks
    d["frame_wall"] = fw
    d["frame_in_episode"] = np.array([f["in_episode"] for f in fr])
    d["frame_T_slam_cam_unscaled"] = np.array([Tsc.get(int(k), NAN44) for k in ks])
    d["frame_T_cam_tool"] = np.array([ball[int(k)] @ T_bt if int(k) in ball else NAN44 for k in ks])
    d[f"frame_T_{ref}_cam_tile"] = np.array([T_ref_world @ G.inv(cams[int(k)][None])[0] if int(k) in cams else NAN44
                                            for k in ks])
    ok_c = np.isfinite(d["frame_T_slam_cam_unscaled"][:, 0, 0])
    if s is not None and timeline_ok and ok_c.sum() >= 2:
        Tm = d["frame_T_slam_cam_unscaled"][ok_c].copy()
        Tm[:, :3, 3] *= s
        d["step_T_slam_cam"], _ = interp(fw[ok_c], Tm, tq, bridge)
        t, T, _ = S.samples(take_episode)
        d["step_T_slam_tool"], d["step_slam_valid"] = interp(t, T, tq, bridge)
    ok_b = np.isfinite(d["frame_T_cam_tool"][:, 0, 0])
    if ok_b.sum() >= 2:
        d["step_T_cam_tool"], _ = interp(fw[ok_b], d["frame_T_cam_tool"][ok_b], tq, bridge)
    ok_t = np.isfinite(d[f"frame_T_{ref}_cam_tile"][:, 0, 0])
    if ok_t.sum() >= 2:
        d[f"step_T_{ref}_cam_tile"], _ = interp(fw[ok_t], d[f"frame_T_{ref}_cam_tile"][ok_t], tq, BRACKET_S)
    return d, s


def save(out, name, d, s, rec):
    rec["scale"] = s
    rec["slam_valid_steps"] = int(d["step_slam_valid"].sum())
    rec["frames"] = int(len(d.get("frame_k", [])))
    np.savez_compressed(out / f"{name}.npz", scale=np.nan if s is None else s, meta=json.dumps(rec), **d)
    print(f"{name} {rec['session']:18s} steps {rec['steps']:4d} slam_valid {rec['slam_valid_steps']:4d} "
          f"frames {rec['frames']:4d} scale {s}")


def read_frames(root, first):
    df = pd.concat([pd.read_parquet(f) for f in sorted(Path(root).expanduser().glob("data/**/*.parquet"))])
    return df[df["episode_index"] >= first].sort_values("index")


def cmd_hhs3(a, out):
    cfg = yaml.safe_load(open(a.src))
    from slam.robot_fk import YamFK
    fk = YamFK()
    g0 = cfg["source"]["glove_first_episode"]
    df = read_frames(cfg["source"]["root"], g0)
    man = {r["hhs3"]: r for r in json.load(open(C.REPO / cfg["manifest"]))["episodes"]}
    T_bt = G.inv(np.array(json.load(open(C.REPO / cfg["glove_frame"]["handeye"]))["T_flange_body"], float)[None])[0]
    T_bw = np.array(json.load(open(C.REPO / cfg["glove_frame"]["base_world"]))["T_base_world"], float)
    dt = 1.0 / (cfg["fps"] * cfg["slow"])
    sessions, cams, index = {}, {}, []
    for e, rows in df.groupby("episode_index"):
        h = int(e - g0)
        m = man[h]
        n = len(rows)
        if m["session"] not in sessions:
            spec = cfg["slam"]["sources"].get(m["session"])
            sessions[m["session"]] = SlamSession(m["session"], spec, T_bt) if spec else None
            cams[m["session"]] = tile_cams(C.WORK / m["session"] / "gt" / f"{m['session']}_b0587b_cam_world.json")
        tq = (m["t0"] if m["t0"] is not None else np.nan) + np.arange(n) * dt
        ok = m["t0"] is not None and bool(m["t0_reliable"])
        d, s = episode_arrays(sessions[m["session"]], m["take_episode"], tq, T_bt, cams[m["session"]], T_bw, "base",
                              cfg["slam"]["bridge_s"], ok)
        d["step_frame_index"] = rows["frame_index"].values.astype(np.int64)
        d["step_T_base_tool_fk"] = fk(np.stack(rows["action"].values).astype(float)[:, :6])
        rec = {"episode": int(e), "hhs3": h, "session": m["session"], "take_episode": m["take_episode"],
               "manifest_status": m["status"], "t0": m["t0"], "t0_reliable": bool(m["t0_reliable"]), "steps": n}
        save(out, f"hhs3_ep{h:03d}", d, s, rec)
        index.append(rec)
    return {"config": a.src, "slam_sources": cfg["slam"]["sources"], "fps": cfg["fps"], "slow": cfg["slow"],
            "bridge_s": cfg["slam"]["bridge_s"], "tile_bracket_s": BRACKET_S, "pose_ref": "robot base",
            "episodes": index}


def cmd_collected(a, out):
    from slam.collect_dataset import T_body_tool, head_walls, scale_label, timeline, view_dir
    root = Path(a.src)
    rl = json.load(open(root / "meta" / "relative_labels.json"))
    df = read_frames(root, min(int(k) for c in rl["collected"] for k in c["mix_episodes"]))
    val = {int(e) for v in json.load(open(root / "meta" / "collected_episodes.json")).values() for e in v["val"]}
    index = []
    for c in rl["collected"]:
        ds, exp, p = c["session"], c["experiment"], c["params"]
        shard = json.load(open(C.WORK / "lerobot" / "shards" / c["shard"] / "meta" / "collected.json"))
        T_bt = T_body_tool(c["unit"])
        S = SlamSession(ds, {"experiment": exp, "run": shard["slam_run"], "scale": scale_label(exp, shard["slam_run"])},
                        T_bt)
        S.segdir = view_dir(exp) / ds / "segments"
        cams = tile_cams(C.gt_dir(ds) / f"{C.session(ds)['head_stem']}_cam_world.json")
        marks = {e["episode_index"]: e for e in json.load(open(C.COLLECT_REPO / "data/raw" / f"{ds}_glove_episodes.json"))["episodes"]}
        for me, e in sorted((int(k), v) for k, v in c["mix_episodes"].items()):
            rows = df[df["episode_index"] == me]
            m = marks[e]
            tq = timeline(m["t_start"], m["t_end"], p["fps"], p["slow"])
            if len(tq) != len(rows):
                raise SystemExit(f"{ds} ep{e}: {len(tq)} steps vs {len(rows)} rows in mix episode {me}")
            d, s = episode_arrays(S, e, tq, T_bt, cams, np.eye(4), "world", p["bridge_s"])
            d["step_frame_index"] = rows["frame_index"].values.astype(np.int64)
            rec = {"episode": me, "session": ds, "take_episode": e, "experiment": exp, "unit": c["unit"],
                   "collected_val": me in val, "t_start": m["t_start"], "t_end": m["t_end"], "steps": len(tq)}
            save(out, f"{ds}_ep{e:02d}", d, s, rec)
            index.append(rec)
    return {"dataset": str(root), "shards": [c["shard"] for c in rl["collected"]], "tile_bracket_s": BRACKET_S,
            "pose_ref": "tile layout frame (no robot in these sessions)", "episodes": index}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("hhs3", "collected"))
    ap.add_argument("src", help="hhs3: a rel_dataset config; collected: the mix dataset directory")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    index = cmd_hhs3(a, out) if a.what == "hhs3" else cmd_collected(a, out)
    json.dump(index, open(out / "index.json", "w"), indent=1)


if __name__ == "__main__":
    main()
