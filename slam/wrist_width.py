#!/usr/bin/env python3
"""Gripper width from the session's own wrist camera, calibrated from repo files only.

The glove's width estimators are normally calibrated per unit with caliper width holds
(<dataset>_glove_log.json, kept by the data owner, not archived). Without them the width
is derived geometrically:

  separation d   distance between the two fingertip 16h5 tags (calib/marker_map_glove_<unit>.json
                 sizes), each localised by PnP in the wrist fisheye (calib/fisheye_glove_<unit>_
                 intrinsics.json); detections from scripts/detect_parallel.py on <session>_fish.mkv
  jaw gap        gap = d - d0: the jaws translate in parallel, so the tags move one-for-one with
                 the gap; d0 = separation with the jaws fully closed, taken from this session
                 (--closed-percentile of all frames: the operator closes the glove empty)
  actuator       calib/gap_to_actuator.json (robot bench fit, caliper mm -> gripper actuator)
  command        calib/width_to_cmd_glove_v2.json (the paper's glove width -> robot command map)

Output <work>/<session>/gt/gripper_wrist.npz in gt/gripper.npz's layout (g<e>_t, g<e>_v per
episode, wall clock, command units) for every marked episode, plus meta. If gt/gripper.npz
(widths from the built glove dataset, slam.glove_width) exists, it is used only to report
agreement; nothing is fitted to it.

  python -m slam.wrist_width --session yam_glove7
  ... --write-log   # also gt/glove_log_from_wrist.json: these widths as build_dataset --log
                    # e8_meas events, so build_dataset --grip-from-wrist calibrates from them
"""
import argparse
import json
import sys

import numpy as np

from slam import config as C

sys.path.insert(0, str(C.REPO / "scripts"))
import labels_lib as L  # noqa: E402


def separation(session):
    s = C.session(session)
    mm = json.load(open(C.CALIB / f"marker_map_glove_{s['glove']}.json"))
    L.TIPS = {int(k): v for k, v in mm["tips"].items()}
    a, b = sorted(L.TIPS)
    Kw, dw = L.load_intrinsics(C.CALIB / mm["wrist_cam"]["intrinsics"].replace("calib/", ""))
    stem = f"{session}_fish"
    det = np.load(C.DET_CACHE / f"{stem}_tips16h5_detections.npz")
    ts = json.load(open(C.RAW / f"{stem}_ts.json"))
    rows = L.body_frames(det, ts, Kw, dw, None, None, L.TIPS)
    rows = [r for r in rows if a in r["pb"] and b in r["pb"]]
    t = np.array([r["t_wall"] for r in rows])
    d = np.array([np.linalg.norm(np.asarray(r["pb"][a]) - np.asarray(r["pb"][b])) for r in rows])
    return t, d, len(ts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--closed-percentile", type=float, default=0.5)
    ap.add_argument("--write-log", action="store_true")
    a = ap.parse_args()
    t, d, n_frames = separation(a.session)
    d0 = float(np.percentile(d, a.closed_percentile))
    g2a = json.load(open(C.CALIB / "gap_to_actuator.json"))
    w2c = json.load(open(C.CALIB / "width_to_cmd_glove_v2.json"))
    gap = np.clip(d - d0, 0, None)
    act = g2a["a"] * gap + g2a["b"]
    cmd = np.interp(act, np.array(w2c["x_width"]), np.array(w2c["y_cmd"]))
    block_act = float(w2c["x_width"][1])                          # closed-on-block anchor
    block_gap = (block_act - g2a["b"]) / g2a["a"]
    print(f"tips in {len(t)}/{n_frames} wrist frames; separation p0.5/p50/p99 "
          f"{np.percentile(d, [0.5, 50, 99]).round(1).tolist()} mm; closed d0 = {d0:.1f} mm")

    eps = json.load(open(C.RAW / f"{a.session}_glove_episodes.json"))["episodes"]
    out, info = {}, {}
    for e in eps:
        m = (t >= e["t_start"] - 0.5) & (t <= e["t_end"] + 0.5)
        if m.sum() < 2:
            continue
        out[f"g{e['episode_index']}_t"], out[f"g{e['episode_index']}_v"] = t[m], cmd[m]

    ref = C.gt_dir(a.session) / "gripper.npz"
    agree = None
    if ref.exists():
        z = np.load(ref)
        err, rv, wv, blk = [], [], [], []
        for k in z.files:
            if not k.endswith("_t") or k not in out:
                continue
            w = np.interp(z[k], out[k], out[k[:-2] + "_v"])
            err.append(w - z[k[:-2] + "_v"])
            rv.append(z[k[:-2] + "_v"])
            wv.append(w)
            sep = np.interp(z[k], t, d)
            blk.append(sep[(z[k[:-2] + "_v"] > 0.2) & (z[k[:-2] + "_v"] < 0.24)])
        e, rv, wv = np.abs(np.concatenate(err)), np.concatenate(rv), np.concatenate(wv)
        agree = {"episodes": len(err), "median_abs_err": float(np.median(e)), "p95_abs_err": float(np.percentile(e, 95)),
                 "corr": float(np.corrcoef(rv, wv)[0, 1]),
                 "block_grasp_separation_mm": float(np.median(np.concatenate(blk))),
                 "implied_closed_separation_mm": float(np.median(np.concatenate(blk)) - block_gap)}
        print(f"vs the built glove dataset's widths ({agree['episodes']} episodes, no fitting): median |err| "
              f"{agree['median_abs_err']:.3f}, p95 {agree['p95_abs_err']:.3f}, corr {agree['corr']:.3f}")
        print(f"cross-check: block-grasp separation {agree['block_grasp_separation_mm']:.1f} mm and the map's "
              f"block gap {block_gap:.1f} mm imply d0 = {agree['implied_closed_separation_mm']:.1f} mm "
              f"(session closed value {d0:.1f} mm)")
    meta = {"method": "tip separation - closed separation -> gap_to_actuator -> width_to_cmd_glove_v2",
            "d0_mm": d0, "closed_percentile": a.closed_percentile, "n_frames_with_tips": int(len(t)),
            "agreement_with_dataset_widths": agree}
    np.savez(C.gt_dir(a.session) / "gripper_wrist.npz", meta=json.dumps(meta), **out)
    print(f"wrote {C.gt_dir(a.session) / 'gripper_wrist.npz'}: {len(out) // 2} episodes")
    if a.write_log:
        ev = sorted(({"event": "e8_meas", "t_wall": float(x), "gripper_pos": float(v)}
                     for k in out if k.endswith("_t") for x, v in zip(out[k], out[k[:-2] + "_v"])),
                    key=lambda e: e["t_wall"])
        dst = C.gt_dir(a.session) / "glove_log_from_wrist.json"
        json.dump({"source": "slam.wrist_width (wrist-camera geometry + repo calibration)",
                   "units": "command", "events": ev}, open(dst, "w"))
        print(f"wrote {dst}: {len(ev)} e8_meas events")


if __name__ == "__main__":
    main()
