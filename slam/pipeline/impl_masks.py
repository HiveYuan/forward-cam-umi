"""Masks step, implementation sam2_points (env sam2): slam.masks on each segment.

SAM2 video propagation from points given in the glove's body frame, projected with the
per-frame ball pose every `prompt_every` frames (slam.masks.segment_masks, unchanged).
Input: the preprocess entry (images/, frames.json, gt.npz). Output per segment
(view.py contract): masked.npz {masked (packbits), obj_frac (T, n_objects), meta} + qa.jpg.

torch/transformers are imported inside run_sam2_points (this module is imported by the
orchestrator's environment too).
"""
NAMED_POINTS = ("ball", "flange")


def _prompts(prompts):
    """Validated prompts, objects sorted by name. SAM2 object ids follow the dict order but the
    cache key hashes params with sorted keys, so the order is fixed here (legacy: glove, hand)."""
    if not isinstance(prompts, dict) or not prompts:
        raise ValueError(f"params.prompts: non-empty mapping object -> points, got {prompts!r}")
    for name, pts in prompts.items():
        ok = isinstance(pts, list) and pts and all(
            p in NAMED_POINTS if isinstance(p, str) else
            (isinstance(p, list) and len(p) == 3 and all(isinstance(x, (int, float)) for x in p))
            for p in pts)
        if not ok:
            raise ValueError(f"params.prompts.{name}: list of {NAMED_POINTS} or [x, y, z] (m), got {pts!r}")
    return {k: prompts[k] for k in sorted(prompts)}


def run_sam2_points(job):
    p = job.params
    prompts = _prompts(p["prompts"])
    if not isinstance(p["prompt_every"], int) or p["prompt_every"] < 1:
        raise ValueError(f"params.prompt_every: positive integer, got {p['prompt_every']!r}")
    todo = job.todo()
    if not todo:
        return {}
    import torch
    from slam import masks as M
    dev = "cuda"
    job.log(f"loading {p['model']}@{p['revision']} ({p['dtype']})")
    model, proc = M.load_model(p["model"], revision=p["revision"], dtype=p["dtype"], dev=dev)
    results = {}
    for seg in todo:
        view = job.input_view(seg)
        tmp = job.tmp(seg)
        meta = M.segment_masks(model, proc, view, job.session, p["prompt_every"], dev, prompts=prompts,
                               dtype=p["dtype"], model_name=p["model"],
                               out_npz=tmp / "masked.npz", out_qa=tmp / "qa.jpg",
                               meta_extra={"revision": p["revision"], "dtype": p["dtype"]})
        job.publish(seg, tmp)
        results[seg] = {k: meta[k] for k in ("prompt_frames", "frac_mean", "masked_frac_mean")}
        job.log(f"{seg}: masked {100 * meta['masked_frac_mean']:.1f}% "
                f"({', '.join(f'{k} {100 * v:.1f}%' for k, v in meta['frac_mean'].items())}), "
                f"{len(meta['prompt_frames'])} prompt frames")
        torch.cuda.empty_cache()
    return results
