#!/usr/bin/env python3
"""Monocular metric depth on the SLAM keyframes of each segment (input of scale method B).

The network sees the undistorted SLAM input images (960x536, the same pixels DROID used) and
predicts metric depth per pixel; its global bias is corrected later by the ball (slam.scale B).
Models (MODELS, --model): Depth Anything V2 Metric Indoor Large (default) or Apple Depth Pro,
both through transformers.

Output <segment>/depth/<run>_<model>.npz: kf_t (image indices of the run's keyframes),
depth (n_kf, H, W) float16 metres.

  /home/student/miniconda3/envs/sam2/bin/python -m slam.depth --session yam_glove7 --run E3
"""
import argparse
import json
import time

import cv2
import numpy as np
import torch

from slam import config as C

MODELS = {"da2-metric-indoor-large": "depth-anything/Depth-Anything-V2-Metric-Indoor-Large-hf",
          "depth-pro": "apple/DepthPro-hf"}
from slam.scale import DEPTH_MODELS  # noqa: E402
assert set(MODELS) == set(DEPTH_MODELS), "keep slam.scale.DEPTH_MODELS in sync"


def load(model, revision=None):
    """(image processor, network on cuda in eval mode). model: a short name (key of MODELS)
    or a transformers repo id; revision=None is the repo's main branch (the legacy behaviour)."""
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    repo = MODELS.get(model, model)
    kw = {} if revision is None else {"revision": revision}
    proc = AutoImageProcessor.from_pretrained(repo, **kw)
    net = AutoModelForDepthEstimation.from_pretrained(repo, **kw).to("cuda").eval()
    return proc, net


@torch.no_grad()
def predict(proc, net, rgb):
    inp = proc(images=rgb, return_tensors="pt").to("cuda")
    out = net(**inp)
    H, W = rgb.shape[:2]
    d = proc.post_process_depth_estimation(out, target_sizes=[(H, W)])[0]["predicted_depth"]
    return d.float().cpu().numpy()


def depth_stack(proc, net, image_paths):
    """(n, H, W) float16 metric depth [m] of the given images (BGR files, fed as RGB)."""
    deps = []
    for p in image_paths:
        bgr = cv2.imread(str(p))
        if bgr is None:
            raise FileNotFoundError(f"cannot read image {p}")
        deps.append(predict(proc, net, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).astype(np.float16))
    return np.stack(deps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--run", default="E3")
    ap.add_argument("--model", default="da2-metric-indoor-large", choices=sorted(MODELS))
    ap.add_argument("--episodes", default="all")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    proc, net = load(a.model)
    segs = sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]"))
    if a.episodes != "all":
        want = {f"ep{int(x):02d}" for x in a.episodes.split(",")}
        segs = [s for s in segs if s.name in want]
    t0 = time.time()
    for seg in segs:
        dst = seg / "depth" / f"{a.run}_{a.model}.npz"
        if dst.exists() and not a.overwrite:
            continue
        kf = np.load(seg / "slam" / f"{a.run}.npz")["kf_t"]
        depth = depth_stack(proc, net, [seg / "images" / f"{int(i):06d}.jpg" for i in kf])
        dst.parent.mkdir(exist_ok=True)
        np.savez_compressed(dst, kf_t=kf, depth=depth, model=MODELS[a.model])
        d = depth.astype(float)
        print(f"[{time.time() - t0:5.0f}s] {seg.name}: {len(kf)} keyframes, depth median {np.median(d):.2f} m "
              f"(p5 {np.percentile(d, 5):.2f}, p95 {np.percentile(d, 95):.2f})", flush=True)


if __name__ == "__main__":
    main()
