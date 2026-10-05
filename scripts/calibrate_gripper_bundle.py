#!/usr/bin/env python3
"""Calibrate the fixed transforms of gripper BASE markers (rigid to the
gripper body) into the dodeca body frame, so they can serve as extra bundle
members for the fused pose when the ball is occluded (e.g. transport).

Per frame with a fused >=2-face dodeca pose AND a base marker visible:
T_marker->body = T_cam->body o T_marker->cam. Robustly averaged over the
session (median translation, outlier-gated quaternion mean — IPPE's flipped
solutions land far from the rotation mode and are rejected).

Writes calib/gripper_bundle.json {"markers": {id: 4x4}, "edge_mm": ...}.

Usage: python scripts/calibrate_gripper_bundle.py <stem> [intrinsics]
  e.g. python scripts/calibrate_gripper_bundle.py yam_sess1_b0587
"""
import json
import sys

import cv2
import numpy as np

sys.path.insert(0, "scripts")
import labels_lib as L  # noqa: E402

STEM = sys.argv[1]
INTR = "calib/B0587_intrinsics.json"
BUNDLE = "calib/dodeca_bundle_ideal.json"     # robot ball; glove: --bundle=
OUT = "calib/gripper_bundle.json"
for a in sys.argv[2:]:
    if a.startswith("--bundle="):
        BUNDLE = a.split("=")[1]
    elif a.startswith("--out="):
        OUT = a.split("=")[1]
    elif a.startswith("--marker-map="):     # glove epoch: base ids/sizes
        mm = json.load(open(a.split("=")[1]))
        L.TAILS = {int(k): v for k, v in mm["tails"].items()}
        L.BASES = {int(k): v for k, v in mm["bases"].items()}
        L.TIPS = {int(k): v for k, v in mm["tips"].items()}
    elif not a.startswith("--"):            # legacy positional intrinsics
        INTR = a
K, dist = L.load_intrinsics(INTR)
T_body, dobj = L.load_bundle(BUNDLE)
print(f"bases {sorted(L.BASES)} ({next(iter(L.BASES.values()))} mm) in the "
      f"body frame of {BUNDLE}")
det = np.load(f"calib/{STEM}_dodeca_detections.npz")

samples = {i: [] for i in L.BASES}
for k in sorted(int(x) for x in det["frame_indices"]):
    ids, cs = det[f"i{k}"], det[f"c{k}"]
    op, ip, bases_here = [], [], {}
    for i, cc in zip(ids, cs):
        i = int(i)
        if i in T_body:
            P = (T_body[i] @ np.hstack([dobj, np.ones((4, 1))]).T).T[:, :3]
            op.append(P)
            ip.append(cc.reshape(4, 2).astype(np.float64))
        elif i in L.BASES:
            bases_here[i] = cc
    if len(op) < 2 or not bases_here:
        continue
    ok, rvec, tvec = cv2.solvePnP(np.concatenate(op), np.concatenate(ip),
                                  K, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        continue
    proj, _ = cv2.projectPoints(np.concatenate(op), rvec, tvec, K, dist)
    if np.sqrt(((proj.reshape(-1, 2) - np.concatenate(ip)) ** 2)
               .sum(1).mean()) > 3.0:
        continue
    Rb, _ = cv2.Rodrigues(rvec)
    tb = tvec.ravel()
    for i, cc in bases_here.items():
        ok2, rv2, t2 = cv2.solvePnP(L.marker_obj(L.BASES[i]),
                                    cc.reshape(4, 2).astype(np.float64),
                                    K, dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if not ok2:
            continue
        R2, _ = cv2.Rodrigues(rv2)
        R_mb = Rb.T @ R2
        t_mb = Rb.T @ (t2.ravel() - tb)
        samples[i].append((R_mb, t_mb))

out = {}
for i, ss in samples.items():
    if len(ss) < 100:
        print(f"base {i}: n={len(ss)} (too few — skipped)")
        continue
    ts = np.array([t for _, t in ss])
    t_med = np.median(ts, axis=0)
    keep = np.linalg.norm(ts - t_med, axis=1) < 0.008   # 8 mm gate
    # rotation mode: quaternion mean of translation-inliers, then a 15 deg
    # gate (IPPE flips are ~180 deg off and fall out here)
    def q_of(R):
        w = np.sqrt(max(1 + R[0, 0] + R[1, 1] + R[2, 2], 1e-12)) / 2
        return np.array([w, (R[2, 1] - R[1, 2]) / (4 * w),
                         (R[0, 2] - R[2, 0]) / (4 * w),
                         (R[1, 0] - R[0, 1]) / (4 * w)])
    qs = np.array([q_of(R) for (R, _), k in zip(ss, keep) if k])
    qs[qs @ qs[0] < 0] *= -1
    qm = qs.mean(0)
    qm /= np.linalg.norm(qm)
    ang = 2 * np.degrees(np.arccos(np.clip(np.abs(qs @ qm), -1, 1)))
    good = ang < 15
    qf = qs[good].mean(0)
    qf /= np.linalg.norm(qf)
    w, x, y, z = qf
    Rf = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    tf = np.median(ts[keep], axis=0)
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = Rf, tf
    out[str(i)] = T.tolist()
    print(f"base {i}: n={len(ss)}  inliers t={keep.sum()} R={good.sum()}  "
          f"pos {np.round(tf * 1000, 1)} mm  rot-spread "
          f"{np.median(ang[good]):.1f} deg")

json.dump({"markers": out, "edge_mm": next(iter(L.BASES.values())),
           "source": f"{STEM} co-visible fused-pose frames",
           "bundle": BUNDLE},
          open(OUT, "w"), indent=1)
print(f"wrote {OUT} ({len(out)} base markers)")
