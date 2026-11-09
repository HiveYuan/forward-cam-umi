"""Tiles step (apriltag_36h11) and the tile_geometry masks implementation, over slam.tiles.

  run_tile_detect    slam.tiles.detect_segment on each segment -> <cache>/tiles/<key>/epNN/tiles.npz
  run_tile_geometry  slam.tiles.segment_tile_masks on each segment ->
                     <cache>/masks/<key>/epNN/masked.npz (masked = packbits(T, H, W) along the
                     last axis, True = do not use; meta = json of the parameters and the
                     frame counts per pose source)
"""
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from slam.pipeline import worker as W


def run_tile_detect(job):
    from slam import tiles as T
    from slam.pipeline.impl_preprocess import load_stream
    todo = job.todo()
    if not todo:
        return {}
    ts, pts = load_stream(job.session)
    p = job.params
    job.log(f"{len(todo)} segments, detect_scale {p['detect_scale']}, subpix_win {p['subpix_win']}")
    t_start, failed, out = time.time(), [], {}
    with ProcessPoolExecutor(max_workers=int(job.exec.get("jobs", 8)), initializer=W.configure,
                             initargs=(job.spec,)) as ex:
        futs = {}
        for seg in todo:
            view, tmp = job.input_view(seg), job.tmp(seg)
            f = ex.submit(T.detect_segment, job.session, view, pts, ts, detect_scale=p["detect_scale"],
                          subpix_win=p["subpix_win"], out=tmp / "tiles.npz")
            futs[f] = (seg, tmp)
        for f in as_completed(futs):
            seg, tmp = futs[f]
            try:
                msg = f.result()
                job.publish(seg, tmp)
            except Exception as err:            # keep going; report every failure at the end
                failed.append(seg)
                msg = f"{seg}: FAILED: {err!r}"
            out[seg] = msg
            job.log(f"[{time.time() - t_start:6.0f}s] {msg}")
    if failed:
        raise RuntimeError(f"failed segments: {sorted(failed)}")
    return out


def run_tile_geometry(job):
    from slam import tiles as T
    p = job.params
    fb = p["slam_fallback"]
    if fb:
        e = job.input_of("slam", fb)             # the view names it slam/<run>.npz
        job.log(f"slam fallback: run {fb} (key {e['key']})")
    out = {}
    for seg in job.todo():
        view = job.input_view(seg)
        if fb and not (view / "slam" / f"{fb}.npz").exists():
            raise FileNotFoundError(f"{seg}: slam fallback {view / 'slam' / f'{fb}.npz'} missing")
        masked, meta = T.segment_tile_masks(view, job.session, margin_mm=p["margin_mm"],
                                            max_gap_s=p["max_gap_s"], grow_mm_per_s=p["grow_mm_per_s"],
                                            slam_fallback=fb, slam_margin_mm=p["slam_margin_mm"])
        tmp = job.tmp(seg)
        np.savez_compressed(tmp / "masked.npz", masked=np.packbits(masked, axis=-1), meta=json.dumps(meta))
        job.publish(seg, tmp)
        out[seg] = {**{k: meta[k] for k in ("frames_pose", "frames_near_pose", "frames_slam",
                                            "frames_no_pose")},
                    "masked_frac": float(masked.mean())}
        job.log(f"{seg}: " + json.dumps(out[seg]))
    return out
