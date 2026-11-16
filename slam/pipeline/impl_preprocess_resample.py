"""Preprocess step (undistort_crop_resample): undistort_crop, then resample each segment to `target_fps`.

The yuan head camera records 1920x1080@60 (4K@25 bands under 60 Hz LED light). Every SLAM default (DROID's
thresholds and memory, SAM3's prompt cadence, the adaptive preroll) was validated on the paper's 4K head camera
at 26.27 fps, and a 60 fps segment is ~2.3x the frames (it would not fit DROID's buffer on the 3090). So the
segment keeps, for each point of a target_fps time grid, the frame nearest to it (60 -> 26.27 fps: strides of
2 and 3 frames). A source at or below 1.1 x target_fps is left as it is (identical to undistort_crop).

Images are renumbered consecutively; frames.json keeps each kept frame's original index `k` and wall time, so
gt.npz (keyed by k), tile detection (decodes the original frames k0..k1 and stores det_k) and every consumer
that matches by k are unchanged. frames.json gains {"resample": {...}}.
"""
import json
import os
import shutil
from pathlib import Path

import numpy as np

from slam.pipeline.impl_preprocess import run_preprocess


def grid_keep(walls, target_fps):
    """Indices into `walls` (sorted) of the frames nearest to a target_fps grid from walls[0] (unique, sorted)."""
    walls = np.asarray(walls, float)
    if len(walls) < 3:
        return np.arange(len(walls))
    src_fps = (len(walls) - 1) / (walls[-1] - walls[0])
    if src_fps <= 1.1 * target_fps:
        return np.arange(len(walls))
    grid = walls[0] + np.arange(int(np.floor((walls[-1] - walls[0]) * target_fps)) + 1) / target_fps
    j = np.clip(np.searchsorted(walls, grid), 1, len(walls) - 1)
    j = np.where(np.abs(walls[j - 1] - grid) <= np.abs(walls[j] - grid), j - 1, j)
    return np.unique(j)


def resample_segment(seg, target_fps):
    """Resample a published segment directory in place (via a temporary rename, so a crash leaves it missing and
    the framework recomputes it, never half-resampled). Returns a one-line summary."""
    seg = Path(seg)
    fj = json.load(open(seg / "frames.json"))
    if "resample" in fj:
        return f"{seg.name}: already resampled"
    fr = fj["frames"]
    keep = grid_keep([f["wall"] for f in fr], target_fps)
    tmp = seg.with_name(f".{seg.name}.rs.tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    os.rename(seg, tmp)
    img = tmp / "images"
    names = [img / f"{f['i']:06d}.jpg" for f in fr]
    kept = set(int(j) for j in keep)
    for j, p in enumerate(names):
        if j not in kept:
            p.unlink()
    out = []
    for new_i, j in enumerate(keep):                 # ascending, and new_i <= j: renaming never overwrites
        f = dict(fr[int(j)])
        if new_i != j:
            os.rename(names[int(j)], img / f"{new_i:06d}.jpg")
        f["i"] = new_i
        out.append(f)
    walls = np.array([f["wall"] for f in fr])
    src_fps = (len(walls) - 1) / (walls[-1] - walls[0]) if len(walls) > 1 else float("nan")
    fj["frames"] = out
    fj["resample"] = {"target_fps": target_fps, "source_fps": round(float(src_fps), 3),
                      "kept": len(out), "of": len(fr), "rule": "nearest frame to each target_fps grid point"}
    json.dump(fj, open(tmp / "frames.json", "w"), indent=1)
    os.rename(tmp, seg)
    return f"{seg.name}: {len(out)}/{len(fr)} frames kept ({src_fps:.1f} -> {target_fps} fps)"


def run_preprocess_resample(job):
    todo = job.todo()
    out = run_preprocess(job)                        # publishes epNN with every frame
    for stale in job.out_dir.glob(".ep[0-9][0-9].rs.tmp"):
        shutil.rmtree(stale, ignore_errors=True)
    for seg in todo:
        msg = resample_segment(job.out_dir / seg, float(job.params["target_fps"]))
        out[seg] = f"{out.get(seg, '')}; {msg}"
        job.log(msg)
    return out
