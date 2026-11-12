"""SLAM step, impl droid_preroll: the droid backend on the segment's frames from preroll_s before the
episode start only (2026-11-11).

The segments keep preprocess's 5 s preroll (frames, masks and tile masks are shared with the droid
runs), but the backend gets only the frames with wall time >= t_start - preroll_s. Why: in glove5 the
collector often turns the head fast during the 5 s before an episode (looking away and back, e.g. from
the terminal where episodes are marked); DROID then initializes on that turn, and every episode whose
scale was off by more than 50% against the tiles had such a turn (exp014/exp015, 2026-11-11).

The output keeps the segment's full frame list, so every downstream step reads it unchanged: frames
before the cut have no pose (tracked False, NaN), keyframe indices are shifted to the segment's index
space, per-frame extras are padded with NaN. meta records preroll_s and the first frame given.
Parameters: the droid backend's (registry entry `droid`) + preroll_s.
"""
import json
from dataclasses import replace

import numpy as np

from slam.backends import base as B


def subset(inp, i0):
    return replace(inp, images=inp.images[i0:], k=inp.k[i0:], t=inp.t[i0:],
                   masked=None if inp.masked is None else inp.masked[i0:])


def expand(out, n, i0):
    """SlamOutput of frames i0.. -> SlamOutput of all n frames of the segment."""
    T = np.full((n, 4, 4), np.nan)
    T[i0:] = out.T_slam_cam
    tracked = np.zeros(n, bool)
    tracked[i0:] = out.tracked
    extra = {}
    for k, v in out.extra.items():
        v = np.asarray(v)
        if v.ndim and len(v) == n - i0:
            pad = np.full((n,) + v.shape[1:], np.nan, dtype=np.result_type(v.dtype, np.float32))
            pad[i0:] = v
            v = pad
        extra[k] = v
    kf_t = None if out.kf_t is None else np.asarray(out.kf_t).astype(np.int64) + i0
    return replace(out, T_slam_cam=T, tracked=tracked, kf_t=kf_t, extra=extra)


def run_slam_preroll(job):
    params = dict(job.params)
    preroll = float(params.pop("preroll_s"))
    if preroll < 0:
        raise ValueError(f"preroll_s must be >= 0, got {preroll}")
    mask_names = [e["name"] for e in job.inputs.values() if e["step"] == "masks"]
    backend = B.get("droid")
    results = {}
    for seg in job.todo():
        view = job.input_view(seg)
        inp = B.load_input(view, mask_names)
        t_start = json.load(open(view / "frames.json"))["episode"]["t_start"]
        keep = inp.t >= t_start - preroll - 1e-6
        if not keep.any():
            raise RuntimeError(f"{seg}: no frame after t_start - {preroll} s")
        i0 = int(np.argmax(keep))
        job.log(f"{seg}: {len(inp)} frames, backend gets {len(inp) - i0} (from {preroll} s before the episode), "
                f"masks {mask_names or 'none'}")
        out = expand(backend.run(subset(inp, i0), params), len(inp), i0)
        out.meta.update({"preroll_s": preroll, "first_frame": i0})
        tmp = job.tmp(seg)
        meta = B.save_output(tmp / "traj.npz", out, inp, job.node["impl"], job.params)
        (tmp / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
        job.publish(seg, tmp)
        keep_k = ("n_frames", "n_tracked", "n_keyframes", "runtime_s", "peak_gpu_gb", "peak_reserved_gb",
                  "valid_frac", "masks_used", "preroll_s", "first_frame")
        results[seg] = {k: meta.get(k) for k in keep_k}
        job.log(f"{seg}: " + json.dumps(results[seg], default=str))
    return results
