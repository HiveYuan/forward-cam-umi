#!/usr/bin/env python3
"""Live focus meter for BARREL-focused cameras (B0587: the lens focuses
mechanically only — the UVC focus_absolute control is accepted but INERT).

Point the camera at a TEXTURED target AT THE WORKING DISTANCE (the ChArUco
board is ideal), run this, and turn the barrel by hand: the meter prints
center-crop Laplacian sharpness ~3x/s with a session peak-hold, so you dial
past the peak and come back to it. Ctrl-C when parked on the peak, then
witness-mark the barrel and calibrate — intrinsics are focus-dependent, and
any later barrel turn means recalibrate.

Usage: python scripts/focus_tune.py /dev/video18
"""
import sys
import time

import cv2
import numpy as np

DEV = sys.argv[1] if len(sys.argv) > 1 else "/dev/video0"

import subprocess

BASE = ("auto_exposure=1,exposure_time_absolute=2,gain=0,sharpness=0,"
        "backlight_compensation=0")

cap = cv2.VideoCapture(DEV)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FPS, 30)
if not cap.isOpened():
    raise SystemExit(f"cannot open {DEV}")
for _ in range(8):
    cap.read()
for kv in BASE.split(","):        # controls latch only mid-stream
    subprocess.run(["v4l2-ctl", "-d", DEV, "-c", kv], capture_output=True)

print(f"{DEV}: turn the focus barrel by hand; maximize the number. "
      "Ctrl-C when parked on the peak.\n")
peak = 0.0
try:
    while True:
        for _ in range(6):        # drain to stay current at ~3 Hz
            ok, img = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = g.shape
        c = g[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
        s = cv2.Laplacian(c, cv2.CV_64F).var()
        peak = max(peak, s)
        bar = "#" * int(min(s, 480) / 8)
        print(f"\r  sharpness {s:7.1f}  (peak {peak:7.1f}) {bar:<60}",
              end="", flush=True)
except KeyboardInterrupt:
    pass
finally:
    cap.release()
print(f"\n\npeak seen: {peak:.1f} — park the barrel there, add a witness "
      "mark, then calibrate:")
print(f"  python scripts/calibrate_uvc.py {DEV} --name B0587b")
