"""Preprocess step (undistort_crop): slam.preprocess.process_episode on each segment.

Output per segment (<cache>/preprocess/<key>/epNN/): images/NNNNNN.jpg, frames.json,
calib.txt, gt.npz, exactly as `python -m slam.preprocess` writes them. process_episode
publishes epNN itself by renaming its own temporary directory (.epNN.tmp) inside the
cache entry, so a directory named epNN is always complete.
"""
import json
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from slam import config as C
from slam.pipeline import worker as W


def load_stream(session):
    """Wall times and container pts of the head video, checked like slam.preprocess.main."""
    from slam.preprocess import packet_pts
    s = C.session(session)
    ts = np.array([x["wall"] for x in json.load(open(C.RAW / f"{s['head_stem']}_ts.json"))])
    pts = packet_pts(C.RAW / f"{s['head_stem']}.mkv")
    if len(pts) != len(ts):
        raise RuntimeError(f"{len(pts)} packets vs {len(ts)} timestamps")
    if np.any(np.diff(pts) <= 0):
        raise RuntimeError("packet pts are not strictly increasing")
    return ts, pts


def run_preprocess(job):
    from slam.preprocess import process_episode
    p = job.params
    a = SimpleNamespace(preroll=p["preroll_s"], width=p["width"], alpha=p["alpha"],
                        jpg_quality=p["jpg_quality"])
    out_root = job.out_dir
    out_root.mkdir(parents=True, exist_ok=True)
    for stale in out_root.glob(".ep[0-9][0-9].tmp"):          # legacy temp dirs of a killed run
        shutil.rmtree(stale, ignore_errors=True)
    todo = job.todo()
    if not todo:
        return {}
    eps = json.load(open(C.RAW / f"{job.session}_glove_episodes.json"))["episodes"]
    by_seg = {f"ep{e['episode_index']:02d}": e for e in eps}
    unknown = [s for s in todo if s not in by_seg]
    if unknown:
        raise RuntimeError(f"segments not in the episode marks: {unknown}")
    ts, pts = load_stream(job.session)
    gt_dir = Path(job.data["gt_dir"])
    job.log(f"{len(todo)} segments -> {out_root}")
    t_start, failed, out = time.time(), [], {}
    # children re-apply the experiment's slam.config (also under spawn/forkserver)
    with ProcessPoolExecutor(max_workers=int(job.exec.get("jobs", 8)), initializer=W.configure,
                             initargs=(job.spec,)) as ex:
        futs = {ex.submit(process_episode, job.session, by_seg[s], ts, pts, a, out_root, gt_dir): s
                for s in todo}
        for f in as_completed(futs):
            seg = futs[f]
            try:
                msg = f.result()
            except Exception as err:            # keep going; report every failure at the end
                failed.append(seg)
                msg = f"{seg}: FAILED: {err!r}"
            out[seg] = msg
            job.log(f"[{time.time() - t_start:6.0f}s] {msg}")
    if failed:
        raise RuntimeError(f"failed segments: {sorted(failed)}")
    return out
