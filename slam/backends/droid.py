"""DROID-SLAM backend: masked DROID-SLAM (slam.droid_masked) behind slam.backends.base.

Exactly what slam.run_droid did before the framework (and still does, through this class):
native resolution, every frame tracked, global BA at the end (backend 7 then 12 iterations),
then the trajectory filler over a second pass of the frames. Masks (SlamInput.masked, OR of
the configured mask sets) are dilated by dilate_px at full resolution and reduced to the 1/8
grid (slam.droid_masked.valid_grid); they zero BA weights (valid source cell x valid matched
cell) and are left out of the keyframe flow mean. Images are not changed.

params (registry 'slam/droid'): weights {path, sha256} (checked before anything runs),
dilate_px, buffer (0 = frames + 32), the DROID demo parameters beta, filter_thresh, warmup,
keyframe_thresh, frontend_{thresh,window,radius,nms}, backend_{thresh,radius,nms}, and seed
(torch.manual_seed; the CUDA kernels are not bitwise deterministic, so repeated runs differ
slightly).

Output: monocular, up to scale (metric False); every frame gets a pose (tracked = finite);
keyframes kf_t / kf_pose_cw / kf_disp as DROID returns them; extra pose7 = DROID's raw
(N, 7) float32 camera poses in the SLAM frame, lietorch [t q] (T_slam_cam = pose7_to_T(pose7)
in float64), saved as x_pose7 (the legacy file called it pose7; nothing reads it).
meta: runtime_s, peak_gpu_gb / peak_reserved_gb = torch.cuda.max_memory_allocated /
max_memory_reserved over the run [GiB] (reserved includes the caching allocator's free
blocks, i.e. what the process held on the GPU), n_keyframes, valid_frac, dilate, droid_args;
masks_used is left at its default (DROID applies every configured mask).

torch and DROID are imported inside the functions that need them, so this module imports in
any environment; running it needs the droid conda env and a GPU.
"""
import argparse
import hashlib
import os
import time
from pathlib import Path

import numpy as np

from slam.backends.base import SlamBackend, SlamOutput

# read by the CUDA caching allocator at its first allocation (slam.run_droid set it at import)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# DROID's own parameters, in the order slam.run_droid's argparse declared them
DROID_PARAMS = ("beta", "filter_thresh", "warmup", "keyframe_thresh", "frontend_thresh",
                "frontend_window", "frontend_radius", "frontend_nms", "backend_thresh",
                "backend_radius", "backend_nms")
PARAMS = ("weights", "dilate_px", "buffer") + DROID_PARAMS + ("seed",)


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def check_weights(weights):
    """weights = {path, sha256}: the file must exist and have that sha256. Returns the path."""
    if not isinstance(weights, dict) or set(weights) != {"path", "sha256"}:
        raise ValueError(f"weights must be {{path, sha256}}, got {weights!r}")
    path = Path(weights["path"])
    if not path.is_file():
        raise FileNotFoundError(f"DROID weights not found: {path}")
    got = sha256_file(path)
    if got != str(weights["sha256"]).lower():
        raise ValueError(f"DROID weights {path}: sha256 {got} != expected {weights['sha256']}")
    return str(path)


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


def image_stream(images, K):
    """(i, (1, 3, H, W) uint8 BGR tensor, [fx fy cx cy]) for every image path, i = position."""
    import cv2
    import torch
    intr = torch.as_tensor([K[0][0], K[1][1], K[0][2], K[1][2]], dtype=torch.float)
    for i, p in enumerate(images):
        img = cv2.imread(str(p))
        if img is None:
            raise FileNotFoundError(f"cannot read image {p}")
        yield i, torch.as_tensor(img).permute(2, 0, 1)[None], intr


def droid_args(params, size, n_frames, weights_path):
    """The args namespace MaskedDroid / DroidFrontend / DroidBackend read (same attributes
    and values as slam.run_droid's argparse result)."""
    a = argparse.Namespace(weights=weights_path, buffer=int(params["buffer"]) or n_frames + 32)
    for k in DROID_PARAMS:
        setattr(a, k, params[k])
    a.upsample, a.stereo, a.disable_vis = False, False, True
    a.image_size = [size[1], size[0]]
    return a


def check_params(params):
    missing = [k for k in PARAMS if k not in params]
    unknown = sorted(set(params) - set(PARAMS))
    if missing or unknown:
        raise KeyError(f"droid params: missing {missing}, unknown {unknown}")


class DroidBackend(SlamBackend):
    name = "droid"

    def run(self, inp, params):
        check_params(params)
        weights = check_weights(params["weights"])
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        import torch
        from slam.droid_masked import MaskedDroid, valid_grid

        n = len(inp)
        a = droid_args(params, inp.size, n, weights)
        torch.manual_seed(int(params["seed"]))
        valid = None
        if inp.masked is not None:
            valid = valid_grid(inp.masked, params["dilate_px"]).cuda()

        torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        droid = MaskedDroid(a, valid=valid)
        for i, img, intr in image_stream(inp.images, inp.K):
            droid.track(i, img, intr)
        traj, kf = droid.terminate(image_stream(inp.images, inp.K))
        runtime = time.time() - t0
        if len(traj) != n:
            raise RuntimeError(f"{len(traj)} poses for {n} frames")
        peak = torch.cuda.max_memory_allocated() / 2**30
        peak_reserved = torch.cuda.max_memory_reserved() / 2**30       # incl. the allocator's cache
        valid_frac = float(valid.mean()) if valid is not None else 1.0
        del droid, valid
        torch.cuda.empty_cache()

        T = pose7_to_T(traj.astype(np.float64))
        meta = {"runtime_s": runtime, "peak_gpu_gb": peak, "peak_reserved_gb": peak_reserved,
                "n_keyframes": int(len(kf["kf_t"])),
                "valid_frac": valid_frac,
                "dilate": params["dilate_px"] if inp.masked is not None else 0,
                "droid_args": {k: v for k, v in vars(a).items() if isinstance(v, (int, float, str, list))}}
        return SlamOutput(T_slam_cam=T, tracked=np.isfinite(T).all((1, 2)), metric=False,
                          kf_t=kf["kf_t"], kf_disp=kf["kf_disp"], kf_pose_cw=kf["kf_pose_cw"],
                          extra={"pose7": traj}, meta=meta)
