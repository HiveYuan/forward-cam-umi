#!/usr/bin/env python3
"""Motion masks with SAM2 video segmentation (transformers Sam2VideoModel, SAM2.1 Hiera-L).

Mask only what moves on its own (design doc, "Masks"): the glove with ball and
gripper, the hand and forearm, the wrist-camera cable, and the object while held.
SAM2 tracks two objects through each segment:
  glove  prompts: ball centre + gripper (flange) point      -> glove, ball, gripper, held object
  hand   prompt : back of the hand                          -> hand, forearm (and the cable along it)
Prompts are points given in the glove's body frame (config SESSIONS[...]['sam2_prompts'], or
the `prompts` argument), projected with the per-frame ball pose every --prompt-every frames.
They are a per-task setting; the pipeline (SAM2 video propagation, union, packbits) stays the
same. The DROID runner dilates the union further (8 px) before using it.

Output <segment>/masks/motion.npz: masked = packbits of (T, H, W) bool (True = do not
use), meta (prompt frames, per-object pixel fractions). QA overlays in masks/qa_motion.jpg.
(segment_masks(..., out_npz=, out_qa=) writes them elsewhere, e.g. into a pipeline cache entry.)

  /home/student/miniconda3/envs/sam2/bin/python -m slam.masks --session yam_glove7
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from slam import config as C
from slam import geometry as G

MODEL = "facebook/sam2.1-hiera-large"
DTYPE = "bfloat16"


def load_model(model=MODEL, revision=None, dtype=DTYPE, dev="cuda"):
    """(Sam2VideoModel on dev in dtype, Sam2VideoProcessor) of a transformers SAM2 repo.
    revision=None is the repo's main branch (the legacy behaviour)."""
    from transformers import Sam2VideoModel, Sam2VideoProcessor
    kw = {} if revision is None else {"revision": revision}
    net = Sam2VideoModel.from_pretrained(model, **kw).to(dev, dtype=torch_dtype(dtype))
    proc = Sam2VideoProcessor.from_pretrained(model, **kw)
    return net, proc


def torch_dtype(dtype):
    """'bfloat16' -> torch.bfloat16 (a torch.dtype passes through)."""
    if isinstance(dtype, torch.dtype):
        return dtype
    t = getattr(torch, str(dtype), None)
    if not isinstance(t, torch.dtype) or not t.is_floating_point:
        raise ValueError(f"unknown floating-point torch dtype {dtype!r}")
    return t


def prompt_points(seg, fj, session, every, prompts=None):
    """{image index: {obj_id: [[x, y], ...]}} from the body-frame prompt points.
    prompts: {object name: [point, ...]} (default: the session's 'sam2_prompts'); a point is
    'ball', 'flange' or [x, y, z] in the glove's body frame. Object ids follow the dict order."""
    cfg = C.session(session)["sam2_prompts"] if prompts is None else prompts
    he = json.load(open(C.CALIB / f"handeye_glove_{C.session(session)['glove']}.json"))
    T_bf = G.inv(np.array(he["T_flange_body"], float)[None])[0]
    named = {"ball": np.zeros(3), "flange": T_bf[:3, 3]}
    K = np.array(fj["K"])
    W, H = fj["size"]
    gt = np.load(seg / "gt.npz")
    pose = {int(k): G.rt_to_T(r, t)[0] for k, r, t in zip(gt["full_k"], gt["full_rvec"], gt["full_tvec"])}
    out = {}
    for f in fj["frames"]:
        if f["i"] % every or f["k"] not in pose:
            continue
        T = pose[f["k"]]
        objs = {}
        for oid, (name, pts) in enumerate(cfg.items(), start=1):
            uv = []
            for p in pts:
                p = named[p] if isinstance(p, str) else np.array(p, float)
                pc = T[:3, :3] @ p + T[:3, 3]
                if pc[2] <= 0.05:
                    continue
                x, y, z = K @ pc
                if 5 <= x / z < W - 5 and 5 <= y / z < H - 5:
                    uv.append([float(x / z), float(y / z)])
            if uv:
                objs[oid] = uv
        if objs:
            out[f["i"]] = objs
    return out, list(cfg)


def segment_masks(model, proc, seg, session, every, dev, prompts=None, dtype=DTYPE, model_name=MODEL,
                  out_npz=None, out_qa=None, meta_extra=None):
    """SAM2 motion masks of one segment directory (legacy layout: images/, frames.json, gt.npz).
    Writes out_npz (default <seg>/masks/motion.npz) and the QA grid out_qa (default
    qa_motion.jpg next to out_npz); returns the meta written into the npz. meta_extra is
    merged into the meta (nothing by default)."""
    out_npz = seg / "masks" / "motion.npz" if out_npz is None else Path(out_npz)
    out_qa = out_npz.parent / "qa_motion.jpg" if out_qa is None else Path(out_qa)
    fj = json.load(open(seg / "frames.json"))
    W, H = fj["size"]
    imgs = [cv2.cvtColor(cv2.imread(str(seg / "images" / f"{f['i']:06d}.jpg")), cv2.COLOR_BGR2RGB)
            for f in fj["frames"]]
    prompts, names = prompt_points(seg, fj, session, every, prompts)
    if not prompts:
        raise RuntimeError(f"{seg.name}: no frame with a ball pose to prompt from")
    sess = proc.init_video_session(video=imgs, inference_device=dev, video_storage_device="cpu",
                                   dtype=torch_dtype(dtype))
    for fi, objs in sorted(prompts.items()):
        n = max(len(v) for v in objs.values())
        pad = [v + [v[-1]] * (n - len(v)) for v in objs.values()]
        proc.add_inputs_to_inference_session(inference_session=sess, frame_idx=fi, obj_ids=list(objs),
                                             input_points=[pad], input_labels=[[[1] * n for _ in pad]])
        model(inference_session=sess, frame_idx=fi)
    first = min(prompts)
    per_obj = np.zeros((len(imgs), len(names)), bool)
    masked = np.zeros((len(imgs), H, W), bool)
    frac = np.zeros((len(imgs), len(names)))
    for rev in (False, True):
        for o in model.propagate_in_video_iterator(sess, start_frame_idx=first, reverse=rev):
            m = proc.post_process_masks([o.pred_masks], original_sizes=[[H, W]], binarize=True)[0][:, 0]
            m = m.cpu().numpy()
            ids = [sess.obj_idx_to_id(j) for j in range(len(m))]
            for j, oid in enumerate(ids):
                frac[o.frame_idx, oid - 1] = m[j].mean()
                per_obj[o.frame_idx, oid - 1] = True
            masked[o.frame_idx] = m.any(0)
    if not per_obj.any(1).all():
        raise RuntimeError(f"{seg.name}: {int((~per_obj.any(1)).sum())} frames without SAM2 output")
    out_npz.parent.mkdir(exist_ok=True)
    meta = {"model": model_name, "objects": names, "prompt_frames": sorted(prompts), "prompt_every": every,
            "frac_mean": {n: float(frac[:, j].mean()) for j, n in enumerate(names)},
            "masked_frac_mean": float(masked.mean())}
    meta.update(meta_extra or {})
    np.savez_compressed(out_npz, masked=np.packbits(masked, axis=-1),
                        obj_frac=frac, meta=json.dumps(meta))
    qa(seg, imgs, masked, prompts, out_qa)
    return meta


def qa(seg, imgs, masked, prompts, path=None):
    n = len(imgs)
    tiles = []
    for i in np.linspace(0, n - 1, 6).astype(int):
        ov = imgs[i].copy()
        ov[masked[i]] = (0.5 * ov[masked[i]] + [127, 0, 0]).astype(np.uint8)
        for pts in prompts.get(i, {}).values():
            for x, y in pts:
                cv2.circle(ov, (int(x), int(y)), 6, (255, 255, 0), -1)
        cv2.putText(ov, f"{seg.name} i={i}", (10, 30), 0, 1, (255, 255, 255), 2)
        tiles.append(cv2.resize(ov, (480, 268)))
    grid = np.vstack([np.hstack(tiles[j:j + 3]) for j in (0, 3)])
    path = seg / "masks" / "qa_motion.jpg" if path is None else path
    cv2.imwrite(str(path), cv2.cvtColor(grid, cv2.COLOR_RGB2BGR))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--episodes", default="all")
    ap.add_argument("--prompt-every", type=int, default=30, help="prompt every N frames (with a ball pose)")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    dev = "cuda"
    model, proc = load_model(MODEL, dev=dev)
    segs = sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]"))
    if a.episodes != "all":
        want = {f"ep{int(x):02d}" for x in a.episodes.split(",")}
        segs = [s for s in segs if s.name in want]
    t0 = time.time()
    for seg in segs:
        if (seg / "masks" / "motion.npz").exists() and not a.overwrite:
            continue
        meta = segment_masks(model, proc, seg, a.session, a.prompt_every, dev)
        print(f"[{time.time() - t0:6.0f}s] {seg.name}: masked {100 * meta['masked_frac_mean']:.1f}% "
              f"({', '.join(f'{k} {100 * v:.1f}%' for k, v in meta['frac_mean'].items())}), "
              f"{len(meta['prompt_frames'])} prompt frames", flush=True)
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
