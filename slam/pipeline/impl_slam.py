"""SLAM step: any registered backend (slam.backends) on each segment.

Inputs: the preprocess entry (frames) and the configured mask entries (OR-ed, in config
order). Output: <cache>/slam/<key>/epNN/traj.npz (slam.backends.base.save_output).
"""
import json

from slam.backends import base as B


def run_slam(job):
    mask_names = [e["name"] for e in job.inputs.values() if e["step"] == "masks"]
    backend = B.get(job.node["impl"])
    results = {}
    for seg in job.todo():
        view = job.input_view(seg)
        inp = B.load_input(view, mask_names)
        job.log(f"{seg}: {len(inp)} frames, masks {mask_names or 'none'}")
        out = backend.run(inp, job.params)
        tmp = job.tmp(seg)
        meta = B.save_output(tmp / "traj.npz", out, inp, job.node["impl"], job.params)
        (tmp / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
        job.publish(seg, tmp)
        keep = ("n_frames", "n_tracked", "n_keyframes", "runtime_s", "peak_gpu_gb", "peak_reserved_gb",
                "valid_frac", "masks_used")
        results[seg] = {k: meta.get(k) for k in keep}
        job.log(f"{seg}: " + json.dumps(results[seg], default=str))
    return results
