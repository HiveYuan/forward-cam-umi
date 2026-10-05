#!/usr/bin/env python3
"""Parallel marker detection: ffmpeg stream-copy pre-split + one
single-threaded worker per piece (cv2's internal pool buys ~10% at 128
threads; frame-parallel processes scale ~linearly, and pre-splitting
removes the 16.6 ms/frame grab-skip that capped chunk parallelism).

Detects DICT_4X4_50 (dodeca + gripper faces, ecr=1.0) and, unless
--no-16h5, AprilTag 16h5 (glove/robot tip markers) in the same decode
pass. Outputs match detect_dodeca.py's cache format:
  calib/{stem}_dodeca_detections.npz/.csv      (4x4; alias id 27 dropped
                                                — it is 16h5-id1 at
                                                Hamming 1, unassignable)
  calib/{stem}_tips16h5_detections.npz         (16h5, same layout)

Usage: detect_parallel.py VIDEO [--workers 48] [--stride 1] [--no-16h5]
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ALIAS_4X4 = {27}   # 16h5-id1 decodes as 4x4-27 under 1-bit correction


def probe_frames(path):
    return int(subprocess.run(
        ["ffprobe", "-v", "error", "-count_packets", "-select_streams",
         "v:0", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0",
         str(path)], capture_output=True, text=True).stdout.strip())


def work(args):
    seg, ordinal, stride, do16, keep27 = args
    # 4x4-27 and 16h5-1 are Hamming-1 aliases of each other. On the robot
    # rig both can be in frame (27 is unassigned there; 16h5-1 is a tip), so
    # 27 is dropped as a phantom. The GLOVE ball carries a real 27 and no
    # 16h5-1 is ever in view, so --keep-27 flips which side is the phantom.
    drop4 = set() if keep27 else ALIAS_4X4
    drop16 = {1} if keep27 else set()
    import cv2
    cv2.setNumThreads(1)
    p4 = cv2.aruco.DetectorParameters()
    p4.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
    p4.cornerRefinementWinSize = 5
    p4.errorCorrectionRate = 1.0
    d4 = cv2.aruco.ArucoDetector(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), p4)
    d16 = None
    if do16:
        p16 = cv2.aruco.DetectorParameters()
        p16.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
        d16 = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16h5),
            p16)
    cap = cv2.VideoCapture(seg)
    s4, s16 = {}, {}
    idx = -1
    while True:
        ok = cap.grab()
        if not ok:
            # corrupt frame: grab() fails but read() resyncs the decoder
            # past it (pilot3 stream-start glitch, 2026-09-14); the bad
            # frame is counted so indices stay packet-aligned (+-1)
            ok2, _ = cap.read()
            if not ok2:
                break
            idx += 1
            continue
        idx += 1
        if idx % stride:
            continue
        ok, img = cap.retrieve()
        if not ok:
            break
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        for det, store, drop in ((d4, s4, drop4), (d16, s16, drop16)):
            if det is None:
                continue
            corners, ids, _ = det.detectMarkers(gray)
            if ids is None or not len(ids):
                continue
            keep = [(int(i), c.reshape(4, 2)) for i, c in
                    zip(ids.flatten(), corners) if int(i) not in drop]
            if keep:
                store[idx] = (
                    np.array([i for i, _ in keep], np.int32),
                    np.stack([c for _, c in keep]).astype(np.float32))
    cap.release()
    return ordinal, idx + 1, s4, s16


def save(store, stem, tag, n_total):
    out = f"calib/{stem}_{tag}_detections.npz"
    np.savez_compressed(
        out,
        frame_indices=np.array(sorted(store), dtype=np.int32),
        **{f"i{k}": v[0] for k, v in store.items()},
        **{f"c{k}": v[1] for k, v in store.items()},
    )
    cnt = Counter()
    for ids, _ in store.values():
        cnt.update(ids.tolist())
    print(f"{tag}: {len(store)}/{n_total} frames with detections -> {out}")
    print(f"  per-id counts: {dict(sorted(cnt.items()))}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--no-16h5", action="store_true")
    ap.add_argument("--keep-27", action="store_true",
                    help="glove footage: the ball carries a real 4x4-27 and "
                         "16h5-1 (robot tip) is never in view; keep 27 and "
                         "drop 16h5-1 as the phantom instead")
    a = ap.parse_args()
    stem = Path(a.video).name.replace(".mkv", "")
    n = probe_frames(a.video)
    print(f"{a.video}: {n} frames, {a.workers} workers, stride {a.stride}",
          flush=True)
    with tempfile.TemporaryDirectory(prefix="detseg_") as td:
        bounds = ",".join(str(i * n // a.workers)
                          for i in range(1, a.workers))
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", a.video, "-c", "copy",
             "-f", "segment", "-segment_frames", bounds,
             "-reset_timestamps", "1", f"{td}/s%04d.mkv"], check=True)
        segs = sorted(Path(td).glob("s*.mkv"))
        print(f"pre-split into {len(segs)} pieces", flush=True)
        jobs = [(str(s), k, a.stride, not a.no_16h5, a.keep_27)
                for k, s in enumerate(segs)]
        # authoritative per-segment packet counts: offsets come from the
        # CONTAINER, not from what decoded — a corrupt frame then costs a
        # bounded detection gap (coverage gates absorb it) instead of
        # shifting every later index or failing the file
        with ProcessPoolExecutor(max_workers=min(16, a.workers)) as ex:
            seg_counts = list(ex.map(probe_frames, [str(s) for s in segs]))
        if sum(seg_counts) != n:
            print(f"WARNING: segment packets {sum(seg_counts)} != probed "
                  f"{n}; using per-segment counts as truth")
        offs = np.concatenate([[0], np.cumsum(seg_counts)[:-1]])
        results = []
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for r in ex.map(work, jobs):
                results.append(r)
    results.sort()
    lost = 0
    g4, g16 = {}, {}
    for (ordinal, decoded, s4, s16), off, sc in zip(results, offs,
                                                    seg_counts):
        if decoded < sc:
            lost += sc - decoded
            print(f"WARNING: segment {ordinal} decoded {decoded}/{sc} "
                  f"frames (corrupt data?) — frames "
                  f"[{int(off)+decoded},{int(off)+sc}) become a "
                  "detection gap")
        for k, v in s4.items():
            g4[k + int(off)] = v
        for k, v in s16.items():
            g16[k + int(off)] = v
    if lost:
        print(f"TOTAL {lost} frames undecodable "
              f"({100*lost/max(n,1):.1f}%) — label coverage gates will "
              "absorb the gap; investigate if it grows")
    n = sum(seg_counts)
    save(g4, stem, "dodeca", n)
    with open(f"calib/{stem}_dodeca_detections.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame_idx", "n_markers", "ids", "mean_side_px"])
        for k in range(0, n, a.stride):
            if k in g4:
                ids, cs = g4[k]
                side = float(np.mean([np.linalg.norm(cc[i] - cc[(i + 1) % 4])
                                      for cc in cs for i in range(4)]))
                w.writerow([k, len(ids),
                            " ".join(map(str, sorted(ids))), round(side, 2)])
            else:
                w.writerow([k, 0, "", 0.0])
    if not a.no_16h5:
        save(g16, stem, "tips16h5", n)
    print("DETECT_PARALLEL_DONE", flush=True)


if __name__ == "__main__":
    main()
