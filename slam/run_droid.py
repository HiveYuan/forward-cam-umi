#!/usr/bin/env python3
"""Run (masked) DROID-SLAM on one preprocessed segment.

Input  <segment>/images, calib.txt, frames.json, and for masked runs
       <segment>/masks/<name>.npz (key 'masked', packbits of (T, H, W) bool,
       True = do not use; see slam/masks.py). Several names are OR-ed.
Output <segment>/slam/<run>.npz (slam.backends.base.save_output format):
  k (N,) original frame index, i (N,) image index,
  T_slam_cam (N, 4, 4) camera pose in the SLAM frame (up to scale), tracked (N,), metric,
  kf_t, kf_pose_cw, kf_disp: keyframes (image index, world->cam [t q], 1/8 inverse depth),
  x_pose7 (N, 7) DROID's raw poses (was 'pose7'),
  meta (json): run, args, masks, dilate, runtime, peak GPU memory, number of keyframes,
  valid_frac, backend, params, ...

The work is done by slam.backends.droid.DroidBackend (also used by the experiment framework,
slam.pipeline.impl_slam). Native resolution, every frame, DROID demo defaults otherwise;
E1-E3 differ only in masks.

  conda run -n droid python -m slam.run_droid --segment <work>/yam_glove7/segments/ep10 --run E1
  ... --run E3 --masks motion,tiles
"""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from slam.backends import base as B  # noqa: E402
from slam.backends.droid import DroidBackend, image_stream, pose7_to_T, sha256_file  # noqa: E402,F401
from slam.droid_masked import DROID_ROOT  # noqa: E402


def registry_weights():
    """The weights {path, sha256} of the registry's 'slam/droid' implementation."""
    from slam.pipeline import registry
    return registry.get("slam", "droid").params["weights"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segment", required=True)
    ap.add_argument("--run", required=True, help="output name, e.g. E1")
    ap.add_argument("--masks", default="", help="comma list of mask names (empty = no masks)")
    ap.add_argument("--dilate", type=int, default=8, help="full-res mask dilation [px]")
    ap.add_argument("--weights", default=str(DROID_ROOT / "droid.pth"))
    ap.add_argument("--weights_sha256", default="",
                    help="expected sha256 of --weights (default: the registry's for the default "
                         "weights file, else the file's own, i.e. not checked)")
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
    ap.add_argument("--seed", type=int, default=0, help="torch.manual_seed")
    a = ap.parse_args()

    seg = Path(a.segment)
    names = [x for x in a.masks.split(",") if x]
    sha = a.weights_sha256
    if not sha:
        reg = registry_weights()
        sha = reg["sha256"] if Path(a.weights).resolve() == Path(reg["path"]).resolve() else sha256_file(a.weights)
    params = {"weights": {"path": a.weights, "sha256": sha}, "dilate_px": a.dilate, "buffer": a.buffer,
              **{k: getattr(a, k) for k in ("beta", "filter_thresh", "warmup", "keyframe_thresh",
                                            "frontend_thresh", "frontend_window", "frontend_radius",
                                            "frontend_nms", "backend_thresh", "backend_radius",
                                            "backend_nms")},
              "seed": a.seed}

    inp = B.load_input(seg, names)
    out = DroidBackend().run(inp, params)
    # legacy meta keys: run, and args = the CLI arguments + DROID's namespace
    out.meta["run"] = a.run
    out.meta["args"] = {"segment": a.segment, "run": a.run, "masks": a.masks, "dilate": a.dilate,
                        **out.meta["droid_args"]}
    (seg / "slam").mkdir(exist_ok=True)
    meta = B.save_output(seg / "slam" / f"{a.run}.npz", out, inp, "droid", params)
    print(json.dumps({k: meta[k] for k in ("run", "masks", "runtime_s", "peak_gpu_gb", "n_frames",
                                           "n_keyframes", "valid_frac")}))


if __name__ == "__main__":
    main()
