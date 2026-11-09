"""Motion masks with SAM3 (transformers, facebook/sam3): text prompts + point prompts.

Mask only what moves on its own (design doc, "Masks"). SAM3 is used in two ways:
  text   Sam3VideoModel with text prompts for body parts ("hand", "arm", "cable"): open-vocabulary
         detection + tracking, no per-scene tuning. One object per detected instance; all
         instances of a prompt are OR-ed into that prompt's part.
  points Sam3TrackerVideoModel (the SAM2-style promptable tracker of SAM3) with points given in
         the glove's body frame and projected with the per-frame ball pose, exactly like the
         SAM2 masks (slam.masks.segment_masks, reused unchanged): the glove rig (ball, handle,
         gripper fingers) and the object while it is held. SAM3's text prompts do not find this
         custom rig ("glove", "gripper", "robot gripper" detect nothing on yam_glove7;
         2026-11-08 sweep), so the rig is located from the ball pose instead.
The mask is the union of all parts. SAM3's video post-processing (NMS, hole filling, sprinkle
removal) needs the hub kernel kernels-community/cv-utils (package `kernels`, torch >= 2.10);
whether it was loaded is recorded in the meta.

Output (written by slam.pipeline.impl_masks_sam3): masked.npz {masked: packbits (T, H, W),
parts: packbits (T, P, H, W), part_names, obj_frac (T, P), meta} and qa.jpg.
"""
import json
from pathlib import Path

import cv2
import numpy as np

PART_COLORS = [(255, 60, 60), (255, 160, 0), (60, 120, 255), (60, 200, 60), (220, 60, 220), (0, 220, 220)]


def load(model, revision, dtype, dev="cuda"):
    """(video model, video processor, tracker model, tracker processor) from one SAM3 repo."""
    from transformers import (Sam3TrackerVideoModel, Sam3TrackerVideoProcessor, Sam3VideoModel,
                              Sam3VideoProcessor)
    from slam.masks import torch_dtype
    kw = {"revision": revision}
    td = torch_dtype(dtype)
    vm = Sam3VideoModel.from_pretrained(model, **kw).to(dev, dtype=td).eval()
    vp = Sam3VideoProcessor.from_pretrained(model, **kw)
    tm = Sam3TrackerVideoModel.from_pretrained(model, **kw).to(dev, dtype=td).eval()
    tp = Sam3TrackerVideoProcessor.from_pretrained(model, **kw)
    return vm, vp, tm, tp


def postprocess_kernel_loaded():
    """True if SAM3's video post-processing kernel (NMS, hole filling) is active."""
    try:
        from transformers.models.sam3_video import modeling_sam3_video as MV
        MV._load_cv_utils_kernel_once()
        return bool(MV.cv_utils_kernel)
    except Exception:
        return False


def text_masks(model, proc, imgs, prompts, dev, dtype):
    """Per-prompt masks of a frame list: (T, P, H, W) bool, instances per frame (T, P), and the
    mean detection score per prompt (over frames with an instance)."""
    import torch
    from slam.masks import torch_dtype
    n, (H, W) = len(imgs), imgs[0].shape[:2]
    sess = proc.init_video_session(video=imgs, inference_device=dev, video_storage_device="cpu",
                                   processing_device="cpu", dtype=torch_dtype(dtype))
    proc.add_text_prompt(sess, list(prompts))
    per = np.zeros((n, len(prompts), H, W), bool)
    nobj = np.zeros((n, len(prompts)), int)
    score = np.full((n, len(prompts)), np.nan)
    seen = np.zeros(n, bool)
    with torch.inference_mode():
        for out in model.propagate_in_video_iterator(inference_session=sess, max_frame_num_to_track=n):
            pp = proc.postprocess_outputs(sess, out)
            ids = pp["object_ids"].tolist()
            masks = pp["masks"].cpu().numpy()
            scores = pp["scores"].float().cpu().numpy()
            i = out.frame_idx
            seen[i] = True
            for j, p in enumerate(prompts):
                sel = [ids.index(o) for o in pp["prompt_to_obj_ids"].get(p, []) if o in ids]
                if sel:
                    per[i, j] = masks[sel].any(0)
                    nobj[i, j] = len(sel)
                    score[i, j] = float(scores[sel].mean())
    if not seen.all():
        raise RuntimeError(f"SAM3 text propagation skipped {int((~seen).sum())} frames")
    mean_score = {p: (float(np.nanmean(score[:, j])) if np.isfinite(score[:, j]).any() else None)
                  for j, p in enumerate(prompts)}
    return per, nobj, mean_score


def point_masks(model, proc, seg, session, every, prompts, dev, dtype, model_name, scratch):
    """Point-prompted SAM3 tracker masks through slam.masks.segment_masks (unchanged SAM2 code
    path): (T, n_objects, H, W) bool per object is not exposed there, so each object is run
    separately and the npz it writes is read back. Returns (masks (T, O, H, W), names, metas)."""
    from slam import masks as M
    out, names, metas = [], [], []
    for name in sorted(prompts):
        npz = Path(scratch) / f"points_{name}.npz"
        meta = M.segment_masks(model, proc, seg, session, every, dev, prompts={name: prompts[name]},
                               dtype=dtype, model_name=model_name, out_npz=npz,
                               out_qa=Path(scratch) / f"points_{name}.jpg")
        fj = json.load(open(seg / "frames.json"))
        m = np.unpackbits(np.load(npz)["masked"], axis=-1, count=fj["size"][0]).astype(bool)
        out.append(m)
        names.append(name)
        metas.append(meta)
    return np.stack(out, 1), names, metas


def qa_grid(name, imgs, parts, part_names, path, k=6):
    """k frames with every part in its own colour, and a legend."""
    n = len(imgs)
    tiles = []
    for i in np.linspace(0, n - 1, k).astype(int):
        ov = imgs[i].astype(float)
        for j in range(len(part_names)):
            m = parts[i, j]
            ov[m] = 0.55 * ov[m] + 0.45 * np.array(PART_COLORS[j % len(PART_COLORS)])
        ov = ov.astype(np.uint8)
        cv2.putText(ov, f"{name} i={i}", (10, 30), 0, 1, (255, 255, 255), 2)
        tiles.append(cv2.resize(ov, (480, 268)))
    grid = np.vstack([np.hstack(tiles[j:j + 3]) for j in range(0, len(tiles), 3)])
    leg = np.zeros((34, grid.shape[1], 3), np.uint8)
    x = 8
    for j, p in enumerate(part_names):
        cv2.rectangle(leg, (x, 8), (x + 18, 26), PART_COLORS[j % len(PART_COLORS)], -1)
        cv2.putText(leg, p, (x + 24, 25), 0, 0.6, (255, 255, 255), 1)
        x += 150
    cv2.imwrite(str(path), cv2.cvtColor(np.vstack([leg, grid]), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
