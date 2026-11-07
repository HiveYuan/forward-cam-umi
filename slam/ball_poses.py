#!/usr/bin/env python3
"""Per-frame ball (dodeca body) pose in the head camera, cam_k -> body_k.

Same solve and gates as labels_lib.body_frames (used by build_dataset), with the
same running-track warm start, but keeps every accepted frame and its face counts.
Two variants:
  ball : dodeca faces only, needs >= 2 faces
  full : + calibrated gripper-back markers (the build_dataset glove setting)

Output <gt_dir>/ball_poses.npz with, per variant v in {ball, full}:
  v_k (N,) original frame index, v_rvec (N,3), v_tvec (N,3) [m], v_rms (N,) px
  (-1 for single-marker frames), v_nf (N,) faces used, v_ne (N,) extra markers used

  python -m slam.ball_poses --session yam_glove7
"""
import argparse
import json
import sys

import numpy as np

from slam import config as C

sys.path.insert(0, str(C.REPO / "scripts"))
import labels_lib as L  # noqa: E402


def solve_track(det, n_frames, K, dist, T_body, dobj, extra):
    last, rows = None, []
    for k in sorted(int(x) for x in det["frame_indices"]):
        if k >= n_frames:
            continue
        r = L.solve_body_pose(det[f"i{k}"], det[f"c{k}"], K, dist, T_body, dobj,
                              extra=extra, last=last)
        if r is None:
            continue
        rv, tv, rms, nf, ne = r
        last = (rv, tv)
        rows.append((k, *np.ravel(rv), *np.ravel(tv), rms, nf, ne))
    return np.array(rows, float).reshape(-1, 10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    a = ap.parse_args()
    s = C.session(a.session)
    stem = s["head_stem"]

    K, dist = L.load_intrinsics(C.CALIB / s["intrinsics"])
    T_body, dobj = L.load_bundle(C.CALIB / f"glove_{s['glove']}_dodeca_bundle.json")
    extra_b = L.load_gripper_bundle(str(C.CALIB / f"glove_{s['glove']}_gripper_bundle.json"))
    det = np.load(C.DET_CACHE / f"{stem}_dodeca_detections.npz")
    n_frames = len(json.load(open(C.RAW / f"{stem}_ts.json")))

    out = {}
    for name, extra in (("ball", None), ("full", extra_b)):
        a_ = solve_track(det, n_frames, K, dist, T_body, dobj, extra)
        out.update({f"{name}_k": a_[:, 0].astype(int), f"{name}_rvec": a_[:, 1:4],
                    f"{name}_tvec": a_[:, 4:7], f"{name}_rms": a_[:, 7],
                    f"{name}_nf": a_[:, 8].astype(int), f"{name}_ne": a_[:, 9].astype(int)})
        print(f"{name}: {len(a_)} of {n_frames} frames ({100 * len(a_) / n_frames:.1f}%)")
    dst = C.gt_dir(a.session)
    dst.mkdir(parents=True, exist_ok=True)
    np.savez(dst / "ball_poses.npz", **out)
    print("wrote", dst / "ball_poses.npz")


if __name__ == "__main__":
    main()
