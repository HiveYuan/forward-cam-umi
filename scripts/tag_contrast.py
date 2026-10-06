#!/usr/bin/env python3
"""Live contrast meter for the wrist camera's AprilTag 16h5 tip markers.

Why: tag decoding fails on CONTRAST, not brightness. A veiled lens (smudge,
protective film, flare) lifts the black cells toward the whites while the
frame mean still looks normal; the decoder then loses whichever tag sits a
few luma below its margin. Known-good robot wrist cam: tag blacks ~25,
whites ~248 (contrast ~220). A glove unit measured 2026-10-06 at blacks ~180,
whites 246 (contrast ~60) — tag 3 decoded in 15% of frames.

Shows, ~3x/s: frame mean, and per decoded tag its black level (p5), white
level (p95) and contrast, with a CLAHE-assisted retry so a tag that is
present but below the margin is still reported (marked '~'). Wipe/peel the
lens, re-aim, or shade it until contrast climbs well above ~100 for BOTH
tags with the jaws closed and open. Ctrl-C to stop.

Usage: python scripts/tag_contrast.py [/dev/video2 | /dev/v4l/by-path/...]
"""
import os
import sys
import time

if any(a in ("-h", "--help") for a in sys.argv[1:]):
    print(__doc__.strip())
    sys.exit(0)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uvc_ritual import apply as apply_ritual  # noqa: E402

DEV = sys.argv[1] if len(sys.argv) > 1 else "/dev/video0"
cap = cv2.VideoCapture(DEV)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
for _ in range(10):
    cap.read()
apply_ritual(DEV)
p = cv2.aruco.DetectorParameters()
p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
det = cv2.aruco.ArucoDetector(
    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16h5), p)
clahe = cv2.createCLAHE(3.0, (8, 8))


def roi(g, c):
    q = c.reshape(4, 2)
    m = np.zeros(g.shape, np.uint8)
    cv2.fillPoly(m, [q.astype(int)], 255)
    v = g[m > 0]
    return float(np.percentile(v, 5)), float(np.percentile(v, 95))


print(f"{DEV}: measuring tag contrast (Ctrl-C to stop)")
try:
    while True:
        ok, img = cap.read()
        if not ok:
            time.sleep(0.1)
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        found = {}
        corners, ids, _ = det.detectMarkers(g)
        if ids is not None:
            for i, c in zip(ids.ravel(), corners):
                found[int(i)] = (c, "")
        corners, ids, _ = det.detectMarkers(clahe.apply(g))
        if ids is not None:
            for i, c in zip(ids.ravel(), corners):
                found.setdefault(int(i), (c, "~"))   # only via CLAHE: marginal
        parts = []
        for i in sorted(found):
            c, flag = found[i]
            b, w = roi(g, c)
            parts.append(f"tag{i}{flag}: black {b:3.0f} white {w:3.0f} "
                         f"contrast {w - b:3.0f}")
        print(f"\r  mean {g.mean():5.1f} | " + ("  ".join(parts) or "no tags")
              + " " * 12, end="", flush=True)
        time.sleep(0.3)
except KeyboardInterrupt:
    print()
cap.release()
