#!/usr/bin/env python3
"""Export the SLAM head-camera trajectories of the HHs3 glove episodes (for Yosub, 2026-11-18).

One npz per pilot_glove_HHs3 episode (= pilot_mix_gHs3 episode 178 + hhs3), from the SLAM sources of a
rel_dataset config (default exp045, the one behind pilot_mix_gHs3_rel_slam_v3 / D2a). Two time bases:

  frame_*  every head-camera frame DROID processed (the segment: ~5 s preroll + the episode, ~26 fps)
  step_*   the HHs3 timeline, row j = dataset frame_index j, wall time t0 + j / (fps * slow)

Poses are 4x4, metres, NaN where unavailable:
  frame_T_slam_cam_unscaled  DROID camera pose in the segment's SLAM frame, as estimated (no metric scale)
  scale                      the segment's metric scale s (Bnet on DA3 metric); metric = translation * s
  frame_T_cam_tool           tool pose in the head camera from the glove's marker ball (metric, no SLAM)
  frame_T_base_cam_tile      head camera in the robot base from the workspace tiles (ground truth, not tile-free)
  step_T_slam_cam            metric camera pose in the SLAM frame, interpolated to the HHs3 steps
  step_T_slam_tool           s . T_slam_cam . T_cam_tool: the glove pose of pilot_mix_gHs3_rel_slam_v3
  step_T_cam_tool            tool in the camera, interpolated
  step_T_base_cam_tile       tile camera pose, interpolated
  step_T_base_tool_fk        FK(HHs3 joints): Yosub's tile labels
  step_slam_valid            the dataset's slam_valid (SLAM pose bracketed within bridge_s, scale ok)
The tool frame is i2rt's grasp_site (FK frame), as in the datasets.

  R=/home/student/miniconda3/envs/lerobot/bin/python
  PYTHONPATH=. $R -m slam.export_traj experiments/exp045_rel_datasets_head/config.yaml --out <dir>
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from slam import config as C
from slam import geometry as G
from slam.hhs3_manifest import BRACKET_S, MIN_TILES, RMS_MAX, raw_dir
from slam.rel_dataset import SlamSession, poses_at

NAN44 = np.full((4, 4), np.nan)


def interp(t, T, tq, bridge):
    """poses_at, NaN where not bracketed."""
    out, ok = poses_at(t, T, tq, bridge)
    out[~ok] = np.nan
    return out, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    from slam.robot_fk import YamFK
    fk = YamFK()
    src = Path(cfg["source"]["root"]).expanduser()
    df = pd.concat([pd.read_parquet(f) for f in sorted(src.glob("data/**/*.parquet"))])
    g0 = cfg["source"]["glove_first_episode"]
    df = df[df["episode_index"] >= g0].sort_values("index")
    man = {r["hhs3"]: r for r in json.load(open(C.REPO / cfg["manifest"]))["episodes"]}
    T_bt = G.inv(np.array(json.load(open(C.REPO / cfg["glove_frame"]["handeye"]))["T_flange_body"], float)[None])[0]
    T_bw = np.array(json.load(open(C.REPO / cfg["glove_frame"]["base_world"]))["T_base_world"], float)
    dt = 1.0 / (cfg["fps"] * cfg["slow"])
    bridge = cfg["slam"]["bridge_s"]
    sessions, tiles, index = {}, {}, []

    for e, rows in df.groupby("episode_index"):
        h = int(e - g0)
        m = man[h]
        n = len(rows)
        q = np.stack(rows["action"].values).astype(float)[:, :6]
        rec = {"episode": int(e), "hhs3": h, "session": m["session"], "take_episode": m["take_episode"],
               "manifest_status": m["status"], "t0": m["t0"], "t0_reliable": bool(m["t0_reliable"]), "steps": n}
        d = {"step_frame_index": rows["frame_index"].values.astype(np.int64),
             "step_T_base_tool_fk": fk(q),
             "step_wall": (m["t0"] if m["t0"] is not None else np.nan) + np.arange(n) * dt}
        empty = np.tile(NAN44, (n, 1, 1))
        for k in ("step_T_slam_cam", "step_T_slam_tool", "step_T_cam_tool", "step_T_base_cam_tile"):
            d[k] = empty.copy()
        d["step_slam_valid"] = np.zeros(n, bool)
        s = None

        if m["session"] not in sessions:
            spec = cfg["slam"]["sources"].get(m["session"])
            sessions[m["session"]] = SlamSession(m["session"], spec, T_bt) if spec else None
            cw = C.WORK / m["session"] / "gt" / f"{m['session']}_b0587b_cam_world.json"
            wall = np.array([x["wall"] for x in json.load(open(raw_dir(m["session"]) / f"{m['session']}_b0587b_ts.json"))])
            tiles[m["session"]] = ({d_["k"]: np.array(d_["T_cam_world"], float).reshape(4, 4)
                                    for d_ in json.load(open(cw))["per_frame"]
                                    if d_["rms"] <= RMS_MAX and d_["tiles"] >= MIN_TILES}, wall)
        S = sessions[m["session"]]
        seg = S.segdir / f"ep{m['take_episode']:02d}" if S is not None else None
        if seg is not None and seg.exists():
            s = S.scale.get(seg.name)
            fr = json.load(open(seg / "frames.json"))["frames"]
            ks = np.array([f["k"] for f in fr])
            fw = np.array([f["wall"] for f in fr])
            z = np.load(seg / "slam" / f"{S.spec['run']}.npz")
            g = np.load(seg / "gt.npz")
            Tsc = {int(k): T for k, T, ok in zip(z["k"], z["T_slam_cam"], z["tracked"]) if ok}
            ball = {int(k): T for k, T in zip(g["full_k"], G.rt_to_T(g["full_rvec"], g["full_tvec"]))}
            cam, _ = tiles[m["session"]]
            d["frame_k"] = ks
            d["frame_wall"] = fw
            d["frame_in_episode"] = np.array([f["in_episode"] for f in fr])
            d["frame_T_slam_cam_unscaled"] = np.array([Tsc.get(int(k), NAN44) for k in ks])
            d["frame_T_cam_tool"] = np.array([ball[int(k)] @ T_bt if int(k) in ball else NAN44 for k in ks])
            d["frame_T_base_cam_tile"] = np.array([T_bw @ G.inv(cam[int(k)][None])[0] if int(k) in cam else NAN44
                                                   for k in ks])
            tq = d["step_wall"]
            ok_c = np.isfinite(d["frame_T_slam_cam_unscaled"][:, 0, 0])
            if s is not None and m["t0"] is not None and m["t0_reliable"] and ok_c.sum() >= 2:
                Tm = d["frame_T_slam_cam_unscaled"][ok_c].copy()
                Tm[:, :3, 3] *= s
                d["step_T_slam_cam"], _ = interp(fw[ok_c], Tm, tq, bridge)
                t, T, _ = S.samples(m["take_episode"])
                d["step_T_slam_tool"], d["step_slam_valid"] = interp(t, T, tq, bridge)
            ok_b = np.isfinite(d["frame_T_cam_tool"][:, 0, 0])
            if ok_b.sum() >= 2:
                d["step_T_cam_tool"], _ = interp(fw[ok_b], d["frame_T_cam_tool"][ok_b], tq, bridge)
            ok_t = np.isfinite(d["frame_T_base_cam_tile"][:, 0, 0])
            if ok_t.sum() >= 2:
                d["step_T_base_cam_tile"], _ = interp(fw[ok_t], d["frame_T_base_cam_tile"][ok_t], tq, BRACKET_S)
        rec["scale"] = s
        rec["slam_valid_steps"] = int(d["step_slam_valid"].sum())
        rec["frames"] = int(len(d.get("frame_k", [])))
        np.savez_compressed(out / f"hhs3_ep{h:03d}.npz", scale=np.nan if s is None else s,
                            meta=json.dumps(rec), **d)
        index.append(rec)
        print(f"hhs3 {h:3d} {m['session']:18s} steps {n:4d} slam_valid {rec['slam_valid_steps']:4d} "
              f"frames {rec['frames']:4d} scale {s}")
    json.dump({"config": a.config, "slam_sources": cfg["slam"]["sources"], "fps": cfg["fps"], "slow": cfg["slow"],
               "bridge_s": bridge, "tile_bracket_s": BRACKET_S, "episodes": index},
              open(out / "index.json", "w"), indent=1)


if __name__ == "__main__":
    main()
