"""Depth step, implementation hf_depth (env sam2): slam.depth on the keyframes of a SLAM run.

Inputs: the preprocess entry (images/) and the slam entry (traj.npz key kf_t). Output per
segment (view.py contract): depth.npz {kf_t, depth (n_kf, H, W) float16 metres, model (repo)},
the same arrays as the legacy <segment>/depth/<run>_<model>.npz.

torch/transformers are imported inside run_depth (this module is imported by the
orchestrator's environment too).
"""
from pathlib import Path


def run_depth(job):
    p = job.params
    import numpy as np
    from slam import depth as D
    if p["model"] not in D.MODELS:
        raise ValueError(f"params.model: {p['model']!r} is not a slam.depth model; known {sorted(D.MODELS)}")
    if p["repo"] != D.MODELS[p["model"]]:
        raise ValueError(f"params.repo {p['repo']!r} does not match slam.depth.MODELS[{p['model']!r}] = "
                         f"{D.MODELS[p['model']]!r}")
    todo = job.todo()
    if not todo:
        return {}
    import torch
    pre, slam = Path(job.input_of("preprocess")["dir"]), Path(job.input_of("slam")["dir"])
    job.log(f"loading {p['repo']}@{p['revision']}")
    proc, net = D.load(p["repo"], revision=p["revision"])
    results = {}
    for seg in todo:
        kf = np.load(slam / seg / "traj.npz")["kf_t"]
        if len(kf) == 0:
            raise RuntimeError(f"{seg}: the slam run has no keyframes")
        depth = D.depth_stack(proc, net, [pre / seg / "images" / f"{int(i):06d}.jpg" for i in kf])
        tmp = job.tmp(seg)
        np.savez_compressed(tmp / "depth.npz", kf_t=kf, depth=depth, model=p["repo"])
        job.publish(seg, tmp)
        d = depth.astype(float)
        results[seg] = {"n_kf": int(len(kf)), "median_m": float(np.median(d)),
                        "p5_m": float(np.percentile(d, 5)), "p95_m": float(np.percentile(d, 95))}
        job.log(f"{seg}: {len(kf)} keyframes, depth median {results[seg]['median_m']:.2f} m "
                f"(p5 {results[seg]['p5_m']:.2f}, p95 {results[seg]['p95_m']:.2f})")
        torch.cuda.empty_cache()
    return results
