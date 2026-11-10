"""Depth step, implementations unidepth_v2 / metric3d_v2 / da3_metric / moge2 (env mdepth) and
depth_pro_f (env sam2): slam.depth_models on the keyframes of a SLAM run, with the run's camera K.

Inputs: the preprocess entry (images/, frames.json: K and size of the undistorted SLAM input) and
the slam entry (traj.npz key kf_t). Output per segment (view.py contract, plus diagnostics):
depth.npz {kf_t, depth (n_kf, H, W) float16 metres, model (repo), fx_used (n_kf,), fx_pred (n_kf,)
(NaN where the network has no own focal)}. fx_used is the focal [px of the input image] that set
the metric scale: K's fx where the network takes K, else the network's own estimate.

torch and the model packages are imported inside run_depth_model (this module is imported by the
orchestrator's environment too).
"""
import json
import re
from pathlib import Path

FAMILY = {"unidepth_v2": "unidepth", "metric3d_v2": "metric3d", "da3_metric": "da3metric",
          "moge2": "moge2", "depth_pro_f": "depthpro"}
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def run_depth_model(job):
    p = job.params
    import numpy as np
    if not LABEL_RE.match(p["model"]):
        raise ValueError(f"params.model {p['model']!r}: a file label (letters, digits, '.', '_', '-')")
    todo = job.todo()
    if not todo:
        return {}
    import cv2
    import torch
    from slam import depth_models as DM
    pre, slam = Path(job.input_of("preprocess")["dir"]), Path(job.input_of("slam")["dir"])
    family = FAMILY[job.node["impl"]]
    params = {k: v for k, v in p.items() if k != "model"}
    job.log(f"loading {family}: {p['repo']}@{p['revision']}")
    pred = DM.load(family, params)
    results = {}
    for seg in todo:
        kf = np.load(slam / seg / "traj.npz")["kf_t"]
        if len(kf) == 0:
            raise RuntimeError(f"{seg}: the slam run has no keyframes")
        fj = json.load(open(pre / seg / "frames.json"))
        K = np.array(fj["K"], float)
        deps, fx_used, fx_pred = [], [], []
        for i in kf:
            bgr = cv2.imread(str(pre / seg / "images" / f"{int(i):06d}.jpg"))
            if bgr is None:
                raise FileNotFoundError(f"{seg}: cannot read image {int(i):06d}.jpg")
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            if tuple(fj["size"]) != (rgb.shape[1], rgb.shape[0]):
                raise RuntimeError(f"{seg}: frames.json size {fj['size']} != image {rgb.shape[1::-1]}")
            d, info = pred.predict(rgb, K)
            if not np.isfinite(d).all():
                raise RuntimeError(f"{seg} frame {int(i)}: non-finite depth")
            deps.append(d.astype(np.float16))
            fx_used.append(info["fx_used"])
            fx_pred.append(np.nan if info.get("fx_pred") is None else info["fx_pred"])
        depth = np.stack(deps)
        tmp = job.tmp(seg)
        np.savez_compressed(tmp / "depth.npz", kf_t=kf, depth=depth, model=p["repo"],
                            fx_used=np.array(fx_used, float), fx_pred=np.array(fx_pred, float))
        job.publish(seg, tmp)
        d = depth.astype(float)
        results[seg] = {"n_kf": int(len(kf)), "median_m": float(np.median(d)),
                        "p5_m": float(np.percentile(d, 5)), "p95_m": float(np.percentile(d, 95)),
                        "fx_used_median": float(np.median(fx_used))}
        job.log(f"{seg}: {len(kf)} keyframes, depth median {results[seg]['median_m']:.2f} m "
                f"(p5 {results[seg]['p5_m']:.2f}, p95 {results[seg]['p95_m']:.2f}), fx used {np.median(fx_used):.1f}")
        torch.cuda.empty_cache()
    return results
