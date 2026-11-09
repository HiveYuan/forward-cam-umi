"""Masks step, implementation sam3_text_points (env sam3): slam.masks_sam3 on each segment.

Union of SAM3 text-prompted parts (body parts: hand, arm, cable) and SAM3-tracker parts
prompted with glove body-frame points projected with the ball pose (the rig and the held
object, as in sam2_points). Input: the preprocess entry (images/, frames.json, gt.npz).
Output per segment (view.py contract): masked.npz {masked, parts, part_names, obj_frac, meta}
and qa.jpg. Kept in its own module so the sam2_points code (and its cache keys) is untouched.
"""
import json

from slam.pipeline.impl_masks import _prompts


def _text_prompts(t):
    if not isinstance(t, list) or not all(isinstance(x, str) and x.strip() for x in t) or len(set(t)) != len(t):
        raise ValueError(f"params.text_prompts: list of distinct non-empty strings, got {t!r}")
    return list(t)


def run_sam3_text_points(job):
    p = job.params
    text = _text_prompts(p["text_prompts"])
    points = _prompts(p["point_prompts"]) if p["point_prompts"] else {}
    if not text and not points:
        raise ValueError("sam3_text_points: give text_prompts and/or point_prompts")
    if not isinstance(p["prompt_every"], int) or p["prompt_every"] < 1:
        raise ValueError(f"params.prompt_every: positive integer, got {p['prompt_every']!r}")
    todo = job.todo()
    if not todo:
        return {}
    import cv2
    import numpy as np
    import torch
    from slam import masks_sam3 as S3
    dev = "cuda"
    job.log(f"loading {p['model']}@{p['revision']} ({p['dtype']})")
    vm, vp, tm, tp = S3.load(p["model"], p["revision"], p["dtype"], dev)
    kernel = S3.postprocess_kernel_loaded()
    if p["require_postprocess"] and not kernel:
        raise RuntimeError("SAM3 post-processing kernel (kernels-community/cv-utils) not loaded; "
                           "install `kernels` and torch >= 2.10 in the sam3 env, or set require_postprocess: false")
    results = {}
    for seg in todo:
        view = job.input_view(seg)
        fj = json.load(open(view / "frames.json"))
        imgs = [cv2.cvtColor(cv2.imread(str(view / "images" / f"{f['i']:06d}.jpg")), cv2.COLOR_BGR2RGB)
                for f in fj["frames"]]
        parts, names, nobj, meta_parts = [], [], {}, {}
        if text:
            per, n_inst, score = S3.text_masks(vm, vp, imgs, text, dev, p["dtype"])
            parts.append(per)
            names += text
            for j, t in enumerate(text):
                meta_parts[t] = {"kind": "text", "frames_with_instance": int((n_inst[:, j] > 0).sum()),
                                 "instances_mean": float(n_inst[:, j].mean()), "score_mean": score[t]}
        if points:
            scratch = job.scratch / "points" / seg
            scratch.mkdir(parents=True, exist_ok=True)
            pm, pnames, pmetas = S3.point_masks(tm, tp, view, job.session, p["prompt_every"], points, dev,
                                                p["dtype"], p["model"], scratch)
            parts.append(pm)
            names += pnames
            for n_, m_ in zip(pnames, pmetas):
                meta_parts[n_] = {"kind": "points", "points": points[n_], "prompt_frames": m_["prompt_frames"]}
        parts = np.concatenate(parts, 1)
        masked = parts.any(1)
        frac = parts.mean((2, 3))
        meta = {"model": p["model"], "revision": p["revision"], "dtype": p["dtype"], "parts": names,
                "text_prompts": text, "point_prompts": points, "prompt_every": p["prompt_every"],
                "postprocess_kernel": kernel, "part_info": meta_parts,
                "frac_mean": {n_: float(frac[:, j].mean()) for j, n_ in enumerate(names)},
                "masked_frac_mean": float(masked.mean())}
        tmp = job.tmp(seg)
        np.savez_compressed(tmp / "masked.npz", masked=np.packbits(masked, axis=-1),
                            parts=np.packbits(parts, axis=-1), part_names=np.array(names),
                            obj_frac=frac, meta=json.dumps(meta))
        S3.qa_grid(seg, imgs, parts, names, tmp / "qa.jpg")
        job.publish(seg, tmp)
        results[seg] = {"frac_mean": meta["frac_mean"], "masked_frac_mean": meta["masked_frac_mean"]}
        job.log(f"{seg}: masked {100 * meta['masked_frac_mean']:.1f}% ("
                + ", ".join(f"{k} {100 * v:.1f}%" for k, v in meta["frac_mean"].items()) + ")")
        del parts, masked
        torch.cuda.empty_cache()
    return results
