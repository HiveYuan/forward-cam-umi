#!/usr/bin/env python3
"""Run (masked) DROID-SLAM on one preprocessed segment.

Input  <segment>/images, calib.txt, frames.json, and for masked runs
       <segment>/masks/<name>.npz (key 'masked', packbits of (T, H, W) bool,
       True = do not use; see slam/masks.py). Several names are OR-ed.
Output <segment>/slam/<run>.npz:
  k (N,) original frame index, i (N,) image index,
  T_slam_cam (N, 4, 4) camera pose in the SLAM frame (up to scale),
  kf_t, kf_pose_cw, kf_disp: keyframes (image index, world->cam [t q], 1/8 inverse depth),
  meta (json): args, masks, runtime, peak GPU memory, number of keyframes.

Native resolution, every frame, DROID demo defaults otherwise; E1-E3 differ only in masks.

  conda run -n droid python -m slam.run_droid --segment <work>/yam_glove7/segments/ep10 --run E1
  ... --run E3 --masks motion,tiles
"""
import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

from slam.droid_masked import DROID_ROOT, MaskedDroid, valid_grid  # noqa: E402


def load_masks(seg, names, n, size):
    masked = np.zeros((n, size[1], size[0]), bool)
    for name in names:
        z = np.load(seg / "masks" / f"{name}.npz")
        m = np.unpackbits(z["masked"], axis=-1, count=size[0]).astype(bool)
        if m.shape != masked.shape:
            raise ValueError(f"mask {name}: shape {m.shape} != {masked.shape}")
        masked |= m
    return masked


def image_stream(seg, frames, K):
    intr = torch.as_tensor([K[0][0], K[1][1], K[0][2], K[1][2]], dtype=torch.float)
    for f in frames:
        img = cv2.imread(str(seg / "images" / f"{f['i']:06d}.jpg"))
        yield f["i"], torch.as_tensor(img).permute(2, 0, 1)[None], intr


def pose7_to_T(p):
    """lietorch [tx ty tz qx qy qz qw] -> 4x4."""
    t, q = p[:, :3], p[:, 3:]
    x, y, z, w = q.T
    R = np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                  2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                  2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1).reshape(-1, 3, 3)
    T = np.tile(np.eye(4), (len(p), 1, 1))
    T[:, :3, :3], T[:, :3, 3] = R, t
    return T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segment", required=True)
    ap.add_argument("--run", required=True, help="output name, e.g. E1")
    ap.add_argument("--masks", default="", help="comma list of mask names (empty = no masks)")
    ap.add_argument("--dilate", type=int, default=8, help="full-res mask dilation [px]")
    ap.add_argument("--weights", default=str(DROID_ROOT / "droid.pth"))
    ap.add_argument("--buffer", type=int, default=0, help="keyframe buffer (0 = frames + 32)")
    # DROID demo defaults
    ap.add_argument("--beta", type=float, default=0.3)
    ap.add_argument("--filter_thresh", type=float, default=2.4)
    ap.add_argument("--warmup", type=int, default=8)
    ap.add_argument("--keyframe_thresh", type=float, default=4.0)
    ap.add_argument("--frontend_thresh", type=float, default=16.0)
    ap.add_argument("--frontend_window", type=int, default=25)
    ap.add_argument("--frontend_radius", type=int, default=2)
    ap.add_argument("--frontend_nms", type=int, default=1)
    ap.add_argument("--backend_thresh", type=float, default=22.0)
    ap.add_argument("--backend_radius", type=int, default=2)
    ap.add_argument("--backend_nms", type=int, default=3)
    a = ap.parse_args()
    a.upsample, a.stereo, a.disable_vis = False, False, True

    seg = Path(a.segment)
    fj = json.load(open(seg / "frames.json"))
    frames, size, K = fj["frames"], fj["size"], fj["K"]
    a.image_size = [size[1], size[0]]
    a.buffer = a.buffer or len(frames) + 32
    names = [x for x in a.masks.split(",") if x]

    torch.manual_seed(0)
    valid = None
    if names:
        valid = valid_grid(load_masks(seg, names, len(frames), size), a.dilate).cuda()

    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    droid = MaskedDroid(a, valid=valid)
    for i, img, intr in image_stream(seg, frames, K):
        droid.track(i, img, intr)
    traj, kf = droid.terminate(image_stream(seg, frames, K))
    runtime = time.time() - t0
    if len(traj) != len(frames):
        raise RuntimeError(f"{len(traj)} poses for {len(frames)} frames")

    out = seg / "slam"
    out.mkdir(exist_ok=True)
    meta = {"run": a.run, "masks": names, "dilate": a.dilate if names else 0,
            "runtime_s": runtime, "peak_gpu_gb": torch.cuda.max_memory_allocated() / 2**30,
            "n_frames": len(frames), "n_keyframes": int(len(kf["kf_t"])),
            "valid_frac": float(valid.mean()) if valid is not None else 1.0,
            "args": {k: v for k, v in vars(a).items() if isinstance(v, (int, float, str, list))}}
    np.savez(out / f"{a.run}.npz", k=np.array([f["k"] for f in frames]), i=np.arange(len(frames)),
             T_slam_cam=pose7_to_T(traj.astype(np.float64)), pose7=traj, meta=json.dumps(meta), **kf)
    print(json.dumps({k: meta[k] for k in ("run", "masks", "runtime_s", "peak_gpu_gb", "n_frames",
                                           "n_keyframes", "valid_frac")}))


if __name__ == "__main__":
    main()
