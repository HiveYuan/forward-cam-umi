#!/usr/bin/env python3
"""Live focus tuner for BARREL-focused cameras (B0587: the lens focuses
mechanically only — the UVC focus_absolute control is accepted but INERT).

Opens a window with the live image so you see what the barrel does:
  top     the whole frame, downscaled, with the 1:1 crop box and any decoded
          marker outlined (click anywhere to move the crop box there)
  bottom  the crop at 1:1 — ACTUAL sensor pixels, no scaling — so blur is
          visible as blur, next to the numbers

Two numbers, both measured at the camera's RECORDING resolution (4K):
  edge px   width of the black/white transition on decoded marker edges
            (36h11 tiles, 4x4 ball/tail faces). Resolution-independent and
            comparable across cameras: a sharp B0587 reads 2-3 px on a tile
            at 1 m; 6-7 px is the soft unit we chased on 2026-10-06. This is
            the number to minimise; it needs a marker in view.
  sharp     centre-crop Laplacian variance, with a session peak-hold. Scene-
            dependent (texture, light), so only compare against itself while
            you turn — dial past the peak and come back to it.

Why 4K: at 1080p the ISP's downscale hides a 6 px blur as a 3 px one and
the meter happily peaks on a lens that is soft at the resolution we record.

Pass --ref <dev> to open a second (known-good) camera: its 1:1 crop and edge
px are shown beside yours, so "as sharp as the forward cam" is a comparison
you make by eye and by number, on the same target, at the same moment.

Keys: q / Esc quit, r reset peak, click = move crop.  Ctrl-C also quits.

Usage:
  python scripts/focus_tune.py /dev/v4l/by-path/<head>
  python scripts/focus_tune.py /dev/v4l/by-path/<head> --ref /dev/v4l/by-path/<forward>
"""
import argparse
import subprocess
import sys
import time

import cv2
import numpy as np

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("dev", nargs="?", default="/dev/video0")
ap.add_argument("--ref", help="second camera shown beside the first for "
                              "comparison (e.g. the forward cam)")
ap.add_argument("--size", default="3840x2160",
                help="capture size; keep the RECORDING size (default 4K)")
args = ap.parse_args()
W, H = (int(x) for x in args.size.lower().split("x"))

BASE = ("auto_exposure=1,exposure_time_absolute=2,gain=0,sharpness=0,"
        "backlight_compensation=0")


def open_cam(dev):
    cap = cv2.VideoCapture(dev)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {dev}")
    for _ in range(8):
        cap.read()
    for kv in BASE.split(","):        # controls latch only mid-stream
        subprocess.run(["v4l2-ctl", "-d", dev, "-c", kv], capture_output=True)
    return cap


p36 = cv2.aruco.DetectorParameters()
p36.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
p4 = cv2.aruco.DetectorParameters()
p4.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
p4.errorCorrectionRate = 1.0
DETS = [cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), p36),
        cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), p4)]


def edge_px(g, quad):
    """Median 10%->90% transition width (px) across a marker's four sides,
    from intensity profiles sampled perpendicular to each side."""
    q = quad.reshape(4, 2)
    widths = []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        nv = b - a
        L = np.linalg.norm(nv)
        if L < 12:
            continue
        nrm = np.array([-nv[1], nv[0]]) / L
        for t in np.linspace(0.25, 0.75, 5):
            c = a + t * nv
            ts = np.arange(-8, 9)
            pts = c[None, :] + ts[:, None] * nrm[None, :]
            x, y = pts[:, 0], pts[:, 1]
            if (x.min() < 1 or y.min() < 1 or x.max() >= g.shape[1] - 1
                    or y.max() >= g.shape[0] - 1):
                continue
            prof = cv2.remap(g, x.astype(np.float32)[None, :],
                             y.astype(np.float32)[None, :],
                             cv2.INTER_LINEAR)[0].astype(float)
            lo, hi = prof.min(), prof.max()
            if hi - lo < 40:
                continue
            nz = (prof - lo) / (hi - lo)
            widths.append(int(((nz > 0.1) & (nz < 0.9)).sum()))
    return float(np.median(widths)) if widths else float("nan")


def measure(img, crop_xy, crop_wh):
    """-> (gray, sharp, edge, markers[(quad, edge)]).  Markers are FOUND at
    half resolution (a full-res 4K pass is ~1.5 s, too slow to turn a barrel
    against) and then RE-DETECTED inside a full-res window around each, so
    the corners used for the edge width are full-res. 'edge' is the median
    over 36h11 tiles when any are decoded — big and static — else over the
    4x4 faces (small, often moving)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cx, cy = crop_xy
    cw, ch = crop_wh
    c = g[max(0, cy - ch // 2): cy + ch // 2, max(0, cx - cw // 2): cx + cw // 2]
    sharp = float(cv2.Laplacian(c, cv2.CV_64F).var())
    small = cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    markers, by_dict = [], []
    for det in DETS:
        corners, ids, _ = det.detectMarkers(small)
        found = []
        if ids is not None:
            for q in corners:
                q2 = q.reshape(4, 2) * 2.0
                x0, y0 = q2.min(0)
                x1, y1 = q2.max(0)
                m = 0.4 * max(x1 - x0, y1 - y0)
                xa, ya = int(max(0, x0 - m)), int(max(0, y0 - m))
                xb, yb = int(min(g.shape[1], x1 + m)), int(min(g.shape[0], y1 + m))
                cr, ci, _ = det.detectMarkers(g[ya:yb, xa:xb])
                if ci is None:
                    continue
                q2 = cr[0].reshape(4, 2) + np.array([xa, ya], np.float32)
                e = edge_px(g, q2)
                markers.append((q2, e))
                if not np.isnan(e):
                    found.append(e)
        by_dict.append(found)
    edges = by_dict[0] or by_dict[1]
    edge = float(np.median(edges)) if edges else float("nan")
    return g, sharp, edge, markers


def panel(img, g, markers, crop_xy, crop_wh, label, sharp, peak, edge,
          view_w):
    """Downscaled full view (with overlays) stacked over the 1:1 crop."""
    h, w = g.shape
    s = view_w / w
    view = cv2.resize(img, (view_w, int(h * s)), interpolation=cv2.INTER_AREA)
    for q, e in markers:
        pts = (q * s).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(view, [pts], True, (0, 255, 0), 1)
        if not np.isnan(e):
            cv2.putText(view, f"{e:.0f}px", tuple((q[0] * s).astype(int)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    cx, cy = crop_xy
    cw, ch = crop_wh
    x0, y0 = max(0, cx - cw // 2), max(0, cy - ch // 2)
    cv2.rectangle(view, (int(x0 * s), int(y0 * s)),
                  (int((x0 + cw) * s), int((y0 + ch) * s)), (0, 200, 255), 1)
    crop = img[y0: y0 + ch, x0: x0 + cw]
    if crop.shape[1] != cw or crop.shape[0] != ch:
        pad = np.zeros((ch, cw, 3), np.uint8)
        pad[: crop.shape[0], : crop.shape[1]] = crop
        crop = pad
    crop = crop.copy()
    etxt = "edge n/a (no marker)" if np.isnan(edge) else f"edge {edge:.1f} px"
    cv2.putText(crop, f"{label}: {etxt}   sharp {sharp:.0f} (peak {peak:.0f})",
                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
    cv2.putText(crop, f"{label}: {etxt}   sharp {sharp:.0f} (peak {peak:.0f})",
                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(crop, "1:1 pixels", (8, ch - 10), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 255, 255), 1)
    return np.vstack([view, crop])


class Tuner:
    def __init__(self, dev, label):
        self.dev, self.label = dev, label
        self.cap = open_cam(dev)
        self.crop_xy = [W // 2, H // 2]
        self.peak = 0.0

    def tick(self, crop_wh):
        ok = False
        for _ in range(3):                      # drain; stay current
            ok, img = self.cap.read()
        if not ok:
            return None
        g, sharp, edge, markers = self.measure_at(img, crop_wh)
        self.peak = max(self.peak, sharp)
        return img, g, sharp, edge, markers

    def measure_at(self, img, crop_wh):
        return measure(img, self.crop_xy, crop_wh)


VIEW_W = 960 if args.ref else 1280           # per-camera column width
CROP = (VIEW_W, 360)                           # 1:1 crop size (w, h)
main = Tuner(args.dev, "THIS")
ref = Tuner(args.ref, "REF") if args.ref else None
win = "focus_tune  (q quit, r reset peak, click = move crop)"
cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)


def on_mouse(ev, x, y, flags, _):
    if ev != cv2.EVENT_LBUTTONDOWN:
        return
    col = x // VIEW_W                          # which camera column
    t = ref if (ref and col == 1) else main
    s = W / VIEW_W
    if y < H / s:                              # click in the full view
        t.crop_xy = [int((x - col * VIEW_W) * s), int(y * s)]


cv2.setMouseCallback(win, on_mouse)
print(f"{args.dev}: turn the focus barrel by hand. Minimise 'edge px' on a "
      "marker (2-3 px = sharp B0587 at 1 m); 'sharp' peaks at best focus.\n"
      "Ctrl-C / q when parked on the peak.\n")
try:
    while True:
        cols = []
        line = []
        for t in (main, ref) if ref else (main,):
            r = t.tick(CROP)
            if r is None:
                continue
            img, g, sharp, edge, markers = r
            cols.append(panel(img, g, markers, t.crop_xy, CROP, t.label,
                              sharp, t.peak, edge, VIEW_W))
            etxt = "  n/a" if np.isnan(edge) else f"{edge:5.1f}"
            line.append(f"{t.label} edge {etxt}px sharp {sharp:7.1f} "
                        f"(peak {t.peak:7.1f})")
        if cols:
            cv2.imshow(win, np.hstack(cols))
            print("\r  " + " | ".join(line) + " " * 8, end="", flush=True)
        k = cv2.waitKey(30) & 0xFF
        if k in (ord("q"), 27):
            break
        if k == ord("r"):
            main.peak = 0.0
            if ref:
                ref.peak = 0.0
except KeyboardInterrupt:
    pass
finally:
    main.cap.release()
    if ref:
        ref.cap.release()
    cv2.destroyAllWindows()
print(f"\n\npeak sharp {main.peak:.1f} — park the barrel there, add a witness "
      "mark, then calibrate:")
print(f"  python scripts/calibrate_uvc.py {args.dev} --name <camera>")
