#!/usr/bin/env python3
"""Cut a head-camera take into per-episode segments for DROID-SLAM.

Segment = [episode start - preroll, episode end], every original frame kept.
Each frame is undistorted with the calibrated intrinsics (pinhole, alpha=0 crops
to valid pixels, principal point centred), area-resized to --width, and
centre-cropped vertically to a multiple of 8. Undistortion only re-samples
pixels: the camera frame (axes and origin) is unchanged, so SLAM poses compare
directly with the tile and ball poses.

Writes <segments_dir>/epNN/:
  images/NNNNNN.jpg   SLAM input; image i is original frame frames[i].k
  calib.txt           fx fy cx cy of the output images (no distortion)
  frames.json         per image: i, original frame index k, wall time, in_episode;
                      plus the undistortion geometry (K_src, dist, K_undist, scale, crop)
  gt.npz              this segment's tile head poses (T_cam_world, tiles, rms) and
                      ball poses (both variants of ball_poses.npz), indexed by k

  python -m slam.preprocess --session yam_glove7 --episodes all --jobs 6
"""
import argparse
import bisect
import json
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

from slam import config as C


def packet_pts(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "packet=pts_time", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True).stdout.split()
    return np.array([float(x) for x in out])


def output_geometry(K, D, W, H, alpha, width):
    """Undistorted full-res camera matrix and the output-image intrinsics.

    Resize uses OpenCV's pixel-centre convention, x' = (x + 0.5) * s - 0.5, so the
    principal point is mapped that way (not just multiplied by s)."""
    newK, _ = cv2.getOptimalNewCameraMatrix(K, D, (W, H), alpha, (W, H), centerPrincipalPoint=True)
    s = width / W
    h_scaled = int(round(H * s))
    h_out = h_scaled - h_scaled % 8
    crop_top = (h_scaled - h_out) // 2
    Ko = np.eye(3)
    Ko[0, 0], Ko[1, 1] = newK[0, 0] * s, newK[1, 1] * h_scaled / H
    Ko[0, 2] = (newK[0, 2] + 0.5) * s - 0.5
    Ko[1, 2] = (newK[1, 2] + 0.5) * (h_scaled / H) - 0.5 - crop_top
    return newK, s, h_scaled, h_out, crop_top, Ko


def load_gt(session):
    s = C.session(session)
    g = C.gt_dir(session)
    cam = {d["k"]: d for d in json.load(open(g / f"{s['head_stem']}_cam_world.json"))["per_frame"]}
    ball = dict(np.load(g / "ball_poses.npz", allow_pickle=False))
    return cam, ball


def process_episode(session, e, ts, pts, a, out_root):
    s = C.session(session)
    video = C.RAW / f"{s['head_stem']}.mkv"
    intr = json.load(open(C.CALIB / s["intrinsics"]))
    K = np.array(intr["camera_matrix"], float)
    D = np.array(intr["dist_coeffs"], float).ravel()
    W, H = intr["width"], intr["height"]
    newK, sc, h_scaled, h_out, crop_top, Ko = output_geometry(K, D, W, H, a.alpha, a.width)
    m1, m2 = cv2.initUndistortRectifyMap(K, D, None, newK, (W, H), cv2.CV_16SC2)
    cam, ball = load_gt(session)

    i0 = bisect.bisect_left(ts, e["t_start"] - a.preroll)
    i1 = bisect.bisect_right(ts, e["t_end"]) - 1
    if i1 < i0:
        raise RuntimeError(f"episode {e['episode_index']} is outside the video")
    name = f"ep{e['episode_index']:02d}"
    seg = out_root / name
    tmp = out_root / f".{name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "images").mkdir(parents=True)

    # Decode exactly frames i0..i1, selected by their container pts (-copyts keeps them);
    # -frames:v stops ffmpeg after the window instead of decoding to the end of the file.
    t0, t1 = pts[i0] - 0.01, pts[i1] + 0.01
    n_want = i1 - i0 + 1
    cmd = ["ffmpeg", "-v", "error", "-copyts", "-ss", f"{max(t0 - 1, 0):.3f}", "-i", str(video),
           "-vf", f"select='between(t,{t0:.4f},{t1:.4f})'", "-fps_mode", "passthrough",
           "-frames:v", str(n_want), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    nbytes = W * H * 3
    frames, n = [], 0
    while True:
        buf = p.stdout.read(nbytes)
        if len(buf) < nbytes:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        und = cv2.remap(img, m1, m2, cv2.INTER_LINEAR)
        small = cv2.resize(und, (a.width, h_scaled), interpolation=cv2.INTER_AREA)[crop_top:crop_top + h_out]
        if not cv2.imwrite(str(tmp / "images" / f"{n:06d}.jpg"), small, [cv2.IMWRITE_JPEG_QUALITY, a.jpg_quality]):
            raise RuntimeError(f"{name}: failed to write image {n}")
        k = i0 + n
        frames.append({"i": n, "k": int(k), "wall": float(ts[k]),
                       "in_episode": bool(e["t_start"] <= ts[k] <= e["t_end"])})
        n += 1
    if p.wait() != 0:
        raise RuntimeError(f"{name}: ffmpeg exited with {p.returncode}")
    if n != n_want:
        raise RuntimeError(f"{name}: decoded {n} frames, expected {n_want}")

    (tmp / "calib.txt").write_text(f"{Ko[0,0]:.6f} {Ko[1,1]:.6f} {Ko[0,2]:.6f} {Ko[1,2]:.6f}\n")
    json.dump({"session": session, "stem": s["head_stem"], "episode": e, "preroll_s": float(e["t_start"] - ts[i0]),
               "size": [a.width, h_out], "K": Ko.tolist(),
               "undistort": {"intrinsics": s["intrinsics"], "K_src": K.tolist(), "dist": D.tolist(),
                             "src_size": [W, H], "alpha": a.alpha, "K_undist": newK.tolist(),
                             "scale": sc, "h_scaled": h_scaled, "crop_top": crop_top},
               "frames": frames},
              open(tmp / "frames.json", "w"), indent=1)

    ck = np.array([k for k in range(i0, i1 + 1) if k in cam], int)
    gt = {"cam_k": ck,
          "T_cam_world": np.array([cam[k]["T_cam_world"] for k in ck], float).reshape(-1, 4, 4),
          "cam_tiles": np.array([cam[k]["tiles"] for k in ck], int),
          "cam_rms": np.array([cam[k]["rms"] for k in ck], float)}
    for v in ("ball", "full"):
        m = (ball[f"{v}_k"] >= i0) & (ball[f"{v}_k"] <= i1)
        for f in ("k", "rvec", "tvec", "rms", "nf", "ne"):
            gt[f"{v}_{f}"] = ball[f"{v}_{f}"][m]
    np.savez(tmp / "gt.npz", **gt)

    if seg.exists():
        shutil.rmtree(seg)
    tmp.rename(seg)
    n2 = int((gt["cam_tiles"] >= 2).sum())
    return (f"{name}: frames {i0}-{i1} ({n}), in-episode {sum(f['in_episode'] for f in frames)}, "
            f"tile poses {len(ck)} (>=2 tiles {n2}), ball {len(gt['ball_k'])}, full {len(gt['full_k'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--episodes", default="all", help="comma list of episode indices, or 'all'")
    ap.add_argument("--preroll", type=float, default=5.0, help="seconds kept before episode start (actual value is stored)")
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--alpha", type=float, default=0.0, help="0 = crop to valid pixels, 1 = keep all")
    ap.add_argument("--jpg-quality", type=int, default=95)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--overwrite", action="store_true", help="redo segments that already exist")
    ap.add_argument("--out", default=None, help="default: <SLAM_WORK>/<session>/segments")
    a = ap.parse_args()

    s = C.session(a.session)
    out_root = Path(a.out) if a.out else C.segments_dir(a.session)
    out_root.mkdir(parents=True, exist_ok=True)
    ts = np.array([x["wall"] for x in json.load(open(C.RAW / f"{s['head_stem']}_ts.json"))])
    pts = packet_pts(C.RAW / f"{s['head_stem']}.mkv")
    if len(pts) != len(ts):
        raise RuntimeError(f"{len(pts)} packets vs {len(ts)} timestamps")
    if np.any(np.diff(pts) <= 0):
        raise RuntimeError("packet pts are not strictly increasing")

    eps = json.load(open(C.RAW / f"{a.session}_glove_episodes.json"))["episodes"]
    if a.episodes != "all":
        want = {int(x) for x in a.episodes.split(",")}
        eps = [e for e in eps if e["episode_index"] in want]
    todo = [e for e in eps if a.overwrite or not (out_root / f"ep{e['episode_index']:02d}").exists()]
    print(f"{len(todo)} of {len(eps)} segments to do -> {out_root}")

    t_start, failed = time.time(), []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(process_episode, a.session, e, ts, pts, a, out_root): e for e in todo}
        for f in as_completed(futs):
            try:
                msg = f.result()
            except Exception as err:  # keep going; report every failure at the end
                failed.append(futs[f]["episode_index"])
                msg = f"ep{futs[f]['episode_index']:02d}: FAILED: {err!r}"
            print(f"[{time.time() - t_start:6.0f}s] {msg}", flush=True)
    if failed:
        raise SystemExit(f"failed episodes: {sorted(failed)}")


if __name__ == "__main__":
    main()
