"""Masks step, implementation sam3_v2 (env sam3): slam.masks_sam3v2 on each segment.

Per segment: SAM3 text instances (text_prompts), minus masklet leaks (leak_ratio), kept (per
connected component with split_components) if attached to the wearer (attach_px; border seeds:
seed_prompts within border_px of the image edge, -1 = none); SAM3-tracker objects prompted from the
ball pose every prompt_every frames: the rig (rig_points, rig_negative_points), the hand + forearm
(hand_points) and the held object (held_points, only on frames where the gripper width from
<gt_dir>/gripper_wrist.npz is <= held_width_max, with held_after_open only after the gripper was
first open). See slam/masks_sam3v2.py.
Input: the preprocess entry (images/, frames.json, gt.npz). Output per segment (view.py contract):
masked.npz {masked, parts, part_names, obj_frac, dropped, held_gate, width, meta} and qa.jpg.
Kept in its own module so sam2_points and sam3_text_points (and their cache keys) are untouched.
"""
import json
import time

from slam.pipeline.impl_masks import NAMED_POINTS


def _points(name, pts):
    """A list (possibly empty) of 'ball' / 'flange' / [x, y, z] (metres, glove body frame)."""
    ok = isinstance(pts, list) and all(
        p in NAMED_POINTS if isinstance(p, str) else
        (isinstance(p, list) and len(p) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                                     for x in p))
        for p in pts)
    if not ok:
        raise ValueError(f"params.{name}: list of {NAMED_POINTS} or [x, y, z] (m), got {pts!r}")
    return list(pts)


def _strings(name, t, allow_empty=False):
    if (not isinstance(t, list) or not all(isinstance(x, str) and x.strip() for x in t) or len(set(t)) != len(t)
            or (not t and not allow_empty)):
        raise ValueError(f"params.{name}: list of distinct non-empty strings, got {t!r}")
    return list(t)


def check_params(p):
    """Validated parameters -> (text prompts, seed prompts, {rig, rig_neg, hand, held} point lists)."""
    text = _strings("text_prompts", p["text_prompts"], allow_empty=True)
    seeds = _strings("seed_prompts", p["seed_prompts"], allow_empty=True)
    if not set(seeds) <= set(text):
        raise ValueError(f"params.seed_prompts {seeds} must be a subset of text_prompts {text}")
    from slam.masks_sam3v2 import TRACKER_PARTS
    if set(text) & set(TRACKER_PARTS):
        raise ValueError(f"params.text_prompts: {sorted(set(text) & set(TRACKER_PARTS))} are tracker part names")
    pts = {k: _points(k, p[k]) for k in ("rig_points", "rig_negative_points", "hand_points", "held_points")}
    if not pts["rig_points"]:
        raise ValueError("params.rig_points: at least one point on the rig")
    for k in ("prompt_every",):
        if not isinstance(p[k], int) or isinstance(p[k], bool) or p[k] < 1:
            raise ValueError(f"params.{k}: positive integer, got {p[k]!r}")
    if not isinstance(p["attach_px"], int) or isinstance(p["attach_px"], bool) or p["attach_px"] < 0:
        raise ValueError(f"params.attach_px: integer >= 0, got {p['attach_px']!r}")
    if not isinstance(p["border_px"], int) or isinstance(p["border_px"], bool) or p["border_px"] < -1:
        raise ValueError(f"params.border_px: integer >= -1 (-1: no border seeds), got {p['border_px']!r}")
    if not isinstance(p["leak_ratio"], (int, float)) or isinstance(p["leak_ratio"], bool) or p["leak_ratio"] < 0:
        raise ValueError(f"params.leak_ratio: number >= 0 (0: off), got {p['leak_ratio']!r}")
    if p["held_points"] and not (isinstance(p["held_width_max"], (int, float)) and p["held_width_max"] > 0):
        raise ValueError(f"params.held_width_max: positive number with held_points, got {p['held_width_max']!r}")
    if not isinstance(p["split_components"], bool):
        raise ValueError(f"params.split_components: bool, got {p['split_components']!r}")
    if not isinstance(p["held_after_open"], bool):
        raise ValueError(f"params.held_after_open: bool, got {p['held_after_open']!r}")
    if not (isinstance(p["width_tol_s"], (int, float)) and p["width_tol_s"] > 0):
        raise ValueError(f"params.width_tol_s: positive number, got {p['width_tol_s']!r}")
    return text, seeds, pts


def run_sam3_v2(job):
    p = job.params
    text, seeds, pts = check_params(p)
    todo = job.todo()
    if not todo:
        return {}
    import cv2
    import numpy as np
    import torch
    from slam import config as C
    from slam import geometry as G
    from slam import masks_sam3 as S3
    from slam import masks_sam3v2 as S
    dev = "cuda"
    job.log(f"loading {p['model']}@{p['revision']} ({p['dtype']})")
    vm, vp, tm, tp = S3.load(p["model"], p["revision"], p["dtype"], dev)
    kernel = S3.postprocess_kernel_loaded()
    if p["require_postprocess"] and not kernel:
        raise RuntimeError("SAM3 post-processing kernel (kernels-community/cv-utils) not loaded; "
                           "install `kernels` and torch >= 2.10 in the sam3 env, or set require_postprocess: false")
    he = json.load(open(C.CALIB / f"handeye_glove_{C.session(job.session)['glove']}.json"))
    T_bf = G.inv(np.array(he["T_flange_body"], float)[None])[0]
    body = {k: S.body_points(v, T_bf) for k, v in pts.items()}
    grip = S.load_gripper_wrist(C.gt_dir(job.session) / "gripper_wrist.npz") if pts["held_points"] else {}
    results = {}
    for seg in todo:
        t0 = time.time()
        view = job.input_view(seg)
        fj = json.load(open(view / "frames.json"))
        imgs = [cv2.cvtColor(cv2.imread(str(view / "images" / f"{f['i']:06d}.jpg")), cv2.COLOR_BGR2RGB)
                for f in fj["frames"]]
        n = len(imgs)
        if text:
            inst = S.text_instances(vm, vp, imgs, text, dev, p["dtype"])
        else:
            H, W = imgs[0].shape[:2]
            inst = {"frame": np.zeros(0, int), "obj": np.zeros(0, int), "prompt": np.zeros(0, int),
                    "score": np.zeros(0), "masks": np.zeros((0, H, W), bool)}
        t_text = time.time() - t0
        series = grip.get(fj["episode"]["episode_index"])
        if pts["held_points"] and series is None:
            job.log(f"{seg}: no gripper width for episode {fj['episode']['episode_index']}: held object off")
        wall = [f["wall"] for f in fj["frames"]]
        width = (S.frame_widths(wall, series[0], series[1], p["width_tol_s"]) if series is not None
                 else np.full(n, np.nan))
        gate = (S.held_gate(width, p["held_width_max"], p["held_after_open"]) if pts["held_points"]
                else np.zeros(n, bool))
        objects = [(1, body["rig_points"], body["rig_negative_points"], None)]
        if body["hand_points"]:
            objects.append((2, body["hand_points"], [], None))
        if body["held_points"]:
            objects.append((3, body["held_points"], [], gate))
        poses = S.ball_poses(np.load(view / "gt.npz"))
        sched = S.prompt_schedule(fj["frames"], poses, fj["K"], fj["size"], p["prompt_every"], objects)
        if not sched:
            raise RuntimeError(f"{seg}: no frame with a ball pose to prompt from")
        trk = S.tracker_masks(tm, tp, imgs, sched, len(S.TRACKER_PARTS), dev, p["dtype"])
        parts, keep, dropped = S.combine(inst, text, trk, gate, seeds, p["attach_px"], p["border_px"], p["leak_ratio"],
                                         p["split_components"])
        del trk
        names = list(S.TRACKER_PARTS) + text
        masked = parts.any(1)
        frac = parts.mean((2, 3))
        prompted = {name: sorted(i for i, objs in sched.items() if oid in objs)
                    for oid, name in enumerate(S.TRACKER_PARTS, start=1)}
        meta = {"model": p["model"], "revision": p["revision"], "dtype": p["dtype"], "parts": names,
                "text_prompts": text, "seed_prompts": seeds, "attach_px": p["attach_px"], "border_px": p["border_px"],
                "leak_ratio": p["leak_ratio"], "split_components": p["split_components"],
                "points": pts, "prompt_every": p["prompt_every"], "postprocess_kernel": kernel,
                "prompt_frames": prompted, "held_width_max": p["held_width_max"],
                "held_after_open": p["held_after_open"],
                "held_frames": int(gate.sum()), "width_frames": int(np.isfinite(width).sum()),
                "text_instances": {t: {"total": int((inst["prompt"] == j).sum()),
                                       "kept": int(keep[inst["prompt"] == j].sum()),
                                       "masklets": int(len(set(inst["obj"][inst["prompt"] == j].tolist())))}
                                   for j, t in enumerate(text)},
                "frac_mean": {n_: float(frac[:, j].mean()) for j, n_ in enumerate(names)},
                "dropped_frac_mean": float(dropped.mean()), "masked_frac_mean": float(masked.mean()),
                "runtime_s": {"text": round(t_text, 1), "total": round(time.time() - t0, 1)}}
        tmp = job.tmp(seg)
        np.savez_compressed(tmp / "masked.npz", masked=np.packbits(masked, axis=-1),
                            parts=np.packbits(parts, axis=-1), part_names=np.array(names), obj_frac=frac,
                            dropped=np.packbits(dropped, axis=-1), held_gate=gate, width=width,
                            meta=json.dumps(meta))
        S3.qa_grid(seg, imgs, parts, names, tmp / "qa.jpg")
        job.publish(seg, tmp)
        results[seg] = {"frac_mean": meta["frac_mean"], "masked_frac_mean": meta["masked_frac_mean"],
                        "held_frames": meta["held_frames"], "runtime_s": meta["runtime_s"]}
        job.log(f"{seg}: masked {100 * meta['masked_frac_mean']:.1f}% ("
                + ", ".join(f"{k} {100 * v:.1f}%" for k, v in meta["frac_mean"].items())
                + f"), dropped text {100 * meta['dropped_frac_mean']:.1f}%, held frames {meta['held_frames']}, "
                f"{meta['runtime_s']['total']:.0f} s")
        del parts, masked, dropped, inst
        torch.cuda.empty_cache()
    return results
