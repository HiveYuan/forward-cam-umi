"""Motion masks with SAM3, v2 (impl sam3_v2): text instances kept only if attached to the tracked
wearer and not leaked, better ball-pose prompts for the rig plus a tracked hand, and the held
object from the gripper width.

Mask only what moves on its own (design doc, "Masks"): the hand and arm, the glove rig with its
fingers and marker cubes, its cable, and an object WHILE it is held; nothing static, no colour or
object-specific rules. v1 (slam.masks_sam3, impl sam3_text_points) unions every text detection
of "hand", "arm", "cable" with a SAM3-tracker object prompted from the ball pose. The audit
(experiments/audits/2026-11-08_sam3_vs_sam2_regions) found three failure modes; v2 addresses each:

  text instances   v1's text prompts also fire on static things: "cable" on desk cables hanging
                   from the static robot, "hand"/"arm" on walls, tiles, the bin. Most of the wall /
                   bin area comes from SAM3 masklets that are right on the arm or cable for a while
                   and then leak onto the wall or bin next to it (their area jumps several-fold).
                   v2 (combine):
                   - leak_flags: drops an instance (one masklet on one frame) whose area exceeds
                     leak_ratio x the lower-quartile area of its masklet over the segment;
                   - attach_filter: keeps an instance only if it is attached to the wearer: seeds
                     are the tracker objects (rig, hand, held object) and the seed-prompt instances
                     ("hand", "arm") touching the image border (the wearer's arm enters from the
                     frame edge; border_px -1 disables); an instance within attach_px of the kept
                     region is kept, transitively; "cable" is never a seed;
                   - split_components: each connected part of an instance is judged on its own (one
                     instance can hold the glove cable and, apart from it, a desk cable).
  rig prompts      v1 prompted the tracker every 30 frames with the ball centre and the virtual
                   flange; the flange point lies on the hand in ~57% of the frames, so the "rig"
                   object was often the hand and missed the gripper. v2 prompts every prompt_every
                   frames with points that lie on the rig (rig_points: ball centre + three points on
                   the gripper body) and tracks the hand + forearm as its own object (hand_points),
                   as sam2_points does.
  held object      neither SAM2 nor v1 covered a block while held. v2 adds a tracker object
                   prompted with a body-frame point between the fingertips (held_points) on frames
                   where the gripper is closed (gripper width <= held_width_max, from
                   <gt_dir>/gripper_wrist.npz); its mask is used only on those frames, so the
                   object is not masked before the grasp or after the release, and the point never
                   lands on the table while the gripper is open. Object-agnostic: whatever is
                   between the fingertips of a closed gripper moves with the rig.

Pure parts (projection, width gating, prompt schedule, instance filter) are numpy/cv2 only and
unit-tested (slam.tests.test_masks_sam3v2); the GPU parts (text_instances, tracker_masks) import
torch lazily. Output (slam.pipeline.impl_masks_sam3v2): masked.npz {masked, parts, part_names,
obj_frac, dropped, held_gate, width, meta} and qa.jpg.
"""

import cv2
import numpy as np

NAMED_POINTS = ("ball", "flange")
TRACKER_PARTS = ("rig", "hand_track", "held")   # tracker objects, obj ids 1, 2, 3; the text prompts follow
LEAK_QUANTILE = 0.25                             # reference area of a masklet for leak_flags


# ---------------------------------------------------------------------------- geometry

def load_gripper_wrist(path):
    """{episode: (t, width)} from <gt_dir>/gripper_wrist.npz (slam.wrist_width), parsed like
    slam.labels.load_gripper; kept here so the masks' cache key does not depend on slam.labels."""
    from pathlib import Path
    if not Path(path).exists():
        return {}
    z = np.load(path)
    return {int(k[1:-2]): (z[k], z[k[:-2] + "_v"]) for k in z.files if k.endswith("_t")}

def body_points(points, T_body_flange):
    """[(3,) body-frame points]: 'ball' = origin (ball centre), 'flange' = the virtual flange
    (translation of T_body_flange = inv(T_flange_body)), [x, y, z] in metres as given."""
    out = []
    for p in points:
        if isinstance(p, str):
            if p not in NAMED_POINTS:
                raise ValueError(f"unknown named point {p!r}; known {NAMED_POINTS}")
            out.append(np.zeros(3) if p == "ball" else np.asarray(T_body_flange, float)[:3, 3].copy())
        else:
            out.append(np.asarray(p, float).reshape(3))
    return out


def project(T_cam_body, K, pts_body, size, margin=5.0, z_min=0.05):
    """Pixel coordinates of body-frame points seen with the pose cam->body, dropping points
    behind / too close to the camera (z <= z_min) or within margin px of the image border
    (the rule of slam.masks.prompt_points). -> list of [x, y]."""
    W, H = size
    T = np.asarray(T_cam_body, float)
    K = np.asarray(K, float)
    uv = []
    for p in pts_body:
        pc = T[:3, :3] @ p + T[:3, 3]
        if pc[2] <= z_min:
            continue
        x, y, z = K @ pc
        if margin <= x / z < W - margin and margin <= y / z < H - margin:
            uv.append([float(x / z), float(y / z)])
    return uv


def ball_poses(gt):
    """{frame k: 4x4 cam->body} from a segment's gt.npz (full_k, full_rvec, full_tvec)."""
    from slam import geometry as G
    return {int(k): G.rt_to_T(r, t)[0] for k, r, t in zip(gt["full_k"], gt["full_rvec"], gt["full_tvec"])}


# ---------------------------------------------------------------------------- held object gating
def frame_widths(wall, t, v, tol_s):
    """Gripper width at the frame times `wall` (linear interpolation of the series t, v); NaN
    where no width sample lies within tol_s (outside the series, or in a gap)."""
    wall = np.asarray(wall, float)
    t = np.asarray(t, float)
    v = np.asarray(v, float)
    out = np.full(len(wall), np.nan)
    if len(t) == 0:
        return out
    o = np.argsort(t)
    t, v = t[o], v[o]
    j = np.clip(np.searchsorted(t, wall), 1, max(len(t) - 1, 1))
    near = np.minimum(np.abs(wall - t[j - 1]), np.abs(wall - t[np.minimum(j, len(t) - 1)]))
    ok = near <= tol_s
    out[ok] = np.interp(wall[ok], t, v)
    return out


def held_gate(width, max_width, after_open=False):
    """Frames where the gripper is closed (width <= max_width): whatever is between the
    fingertips is held. NaN widths (no measurement) are not held; max_width None disables.
    after_open: only once the gripper has been open (width > max_width) earlier in the series,
    i.e. after a grasp; a gripper closed at rest from the start holds nothing (its fingertip
    point would select whatever lies next to the closed fingers)."""
    w = np.asarray(width, float)
    if max_width is None:
        return np.zeros(len(w), bool)
    closed = np.isfinite(w) & (w <= max_width)
    if after_open:
        opened = np.isfinite(w) & (w > max_width)
        closed &= np.cumsum(opened) > 0
    return closed


# ---------------------------------------------------------------------------- tracker prompts
def prompt_schedule(frames, poses, K, size, every, objects):
    """Tracker prompts {frame index i: {obj_id: (points [[x, y]], labels [1|0])}}.

    frames   frames.json 'frames' (dicts with i, k)
    poses    {k: cam->body}
    objects  [(obj_id, positive body points, negative body points, gate or None)]; an object is
             prompted on frames with i % every == 0, a ball pose, its gate True (if given) and at
             least one positive point inside the image; negatives are added only alongside."""
    out = {}
    for f in frames:
        i = f["i"]
        if i % every or f["k"] not in poses:
            continue
        T = poses[f["k"]]
        objs = {}
        for oid, pos, neg, gate in objects:
            if gate is not None and not gate[i]:
                continue
            p = project(T, K, pos, size)
            if not p:
                continue
            n = project(T, K, neg, size) if neg else []
            objs[oid] = (p + n, [1] * len(p) + [0] * len(n))
        if objs:
            out[i] = objs
    return out


# ---------------------------------------------------------------------------- instance filter
def touches_border(m, px):
    """True if the mask has a pixel within px of the image border."""
    if px < 0:
        return False
    k = int(px) + 1
    return bool(m[:k].any() or m[-k:].any() or m[:, :k].any() or m[:, -k:].any())


def dilate(m, px):
    if px <= 0:
        return m.astype(bool)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(px) + 1, 2 * int(px) + 1))
    return cv2.dilate(m.astype(np.uint8), k).astype(bool)


def attach_filter(masks, labels, anchor, seed_labels, attach_px, border_px):
    """Keep flags for the text instances of one frame.

    masks   (N, H, W) bool, one per instance; labels: N prompt strings
    anchor  (H, W) bool: the tracked wearer (rig, hand, held object; always a seed region), or None
    Seeds: anchor, and instances whose label is in seed_labels and that touch the image border
    (within border_px; border_px -1 = no border seeds). Then grow: an instance whose mask, dilated
    by attach_px, overlaps the kept region is kept, until nothing changes (the kept region only
    grows, so the result does not depend on the instance order). Labels not in seed_labels
    (e.g. 'cable') are kept only by attachment."""
    n = len(masks)
    keep = np.zeros(n, bool)
    if n == 0:
        return keep
    H, W = masks[0].shape
    region = np.zeros((H, W), bool) if anchor is None else anchor.astype(bool).copy()
    for j in range(n):
        if labels[j] in seed_labels and masks[j].any() and touches_border(masks[j], border_px):
            keep[j] = True
            region |= masks[j]
    if not region.any():
        return keep
    grown = [None] * n
    changed = True
    while changed:
        changed = False
        for j in range(n):
            if keep[j] or not masks[j].any():
                continue
            if grown[j] is None:
                grown[j] = dilate(masks[j], attach_px)
            if (grown[j] & region).any():
                keep[j] = True
                region |= masks[j]
                changed = True
    return keep


def leak_flags(obj, area, ratio, quantile=LEAK_QUANTILE):
    """True for instances whose area exceeds ratio x the `quantile` area of their masklet (same
    obj id over the segment): a SAM3 masklet that balloons has leaked onto something else (a wall
    or bin next to the arm). ratio <= 0 disables."""
    obj = np.asarray(obj)
    area = np.asarray(area, float)
    out = np.zeros(len(obj), bool)
    if ratio <= 0:
        return out
    for o in np.unique(obj):
        sel = obj == o
        out[sel] = area[sel] > ratio * np.quantile(area[sel], quantile)
    return out


def components(m):
    """Connected components (8-connectivity) of a mask, as a list of masks."""
    n, lab = cv2.connectedComponents(m.astype(np.uint8), connectivity=8)
    return [lab == c for c in range(1, n)]


def combine(inst, prompts, trk, held_ok, seed_labels, attach_px, border_px, leak_ratio=0.0,
            split_components=False):
    """Per-frame parts of the v2 mask.

    inst     text instances {'frame' (N,), 'prompt' (N,) index into prompts, 'masks' (N, H, W)
             [, 'obj' (N,) masklet ids, needed for leak_ratio > 0]}
    trk      (T, len(TRACKER_PARTS), H, W) tracker masks (rig, hand_track, held)
    held_ok  (T,) bool: frames whose held-object mask is used (the gripper is closed)
    -> parts (T, len(TRACKER_PARTS) + len(prompts), H, W) [rig, hand_track, held, *prompts],
       keep flags (N,) of the text instances (any of it kept), dropped (T, H, W) = text area not kept.
    The anchor of the instance filter on a frame is the union of the tracker parts. Instances
    flagged by leak_flags (leak_ratio > 0) are dropped first (they cannot attach others).
    split_components: attach_filter judges each connected component of an instance on its own
    (one SAM3 instance can hold the glove cable and, apart from it, a desk cable)."""
    T, nt, H, W = trk.shape
    if nt != len(TRACKER_PARTS):
        raise ValueError(f"tracker masks: {nt} objects, expected {len(TRACKER_PARTS)}")
    parts = np.zeros((T, nt + len(prompts), H, W), bool)
    dropped = np.zeros((T, H, W), bool)
    n = len(inst["frame"])
    keep = np.zeros(n, bool)
    parts[:, :nt] = trk
    held = TRACKER_PARTS.index("held")
    parts[~np.asarray(held_ok, bool), held] = False
    leak = (leak_flags(inst["obj"], inst["masks"].reshape(n, -1).sum(1), leak_ratio) if leak_ratio > 0 and n
            else np.zeros(n, bool))
    by_frame = {}
    for j, i in enumerate(inst["frame"]):
        by_frame.setdefault(int(i), []).append(j)
    for i, idx in by_frame.items():
        pieces, owner = [], []
        for j in idx:
            if leak[j]:
                continue
            for c in (components(inst["masks"][j]) if split_components else [inst["masks"][j]]):
                pieces.append(c)
                owner.append(j)
        if pieces:
            k = attach_filter(np.stack(pieces), [prompts[int(inst["prompt"][j])] for j in owner],
                              parts[i, :nt].any(0), seed_labels, attach_px, border_px)
            for c, j, kk in zip(pieces, owner, k):
                if kk:
                    keep[j] = True
                    parts[i, nt + int(inst["prompt"][j])] |= c
        for j in idx:
            dropped[i] |= inst["masks"][j]
        dropped[i] &= ~parts[i, nt:].any(0)
    return parts, keep, dropped


# ---------------------------------------------------------------------------- SAM3 (GPU)
def text_instances(model, proc, imgs, prompts, dev, dtype):
    """Every SAM3 text detection of a frame list, per instance (the masklets that
    slam.masks_sam3.text_masks ORs per prompt): {'frame' (N,), 'obj' (N,) masklet id,
    'prompt' (N,) index into prompts, 'score' (N,), 'masks' (N, H, W) bool}."""
    import torch
    from slam.masks import torch_dtype
    n = len(imgs)
    sess = proc.init_video_session(video=imgs, inference_device=dev, video_storage_device="cpu",
                                   processing_device="cpu", dtype=torch_dtype(dtype))
    proc.add_text_prompt(sess, list(prompts))
    fr, ob, pr, sc, ms = [], [], [], [], []
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
                for o in pp["prompt_to_obj_ids"].get(p, []):
                    if o in ids:
                        k = ids.index(o)
                        fr.append(i)
                        ob.append(o)
                        pr.append(j)
                        sc.append(float(scores[k]))
                        ms.append(masks[k].astype(bool))
    if not seen.all():
        raise RuntimeError(f"SAM3 text propagation skipped {int((~seen).sum())} frames")
    H, W = imgs[0].shape[:2]
    return {"frame": np.array(fr, int), "obj": np.array(ob, int), "prompt": np.array(pr, int),
            "score": np.array(sc, float),
            "masks": np.stack(ms) if ms else np.zeros((0, H, W), bool)}


def tracker_masks(model, proc, imgs, schedule, n_obj, dev, dtype):
    """SAM3-tracker (SAM2-style) video masks of n_obj objects (ids 1..n_obj) from point prompts
    {frame: {obj_id: (points, labels)}} (prompt_schedule), propagated forward and backward from
    the first prompted frame as in slam.masks.segment_masks. -> (T, n_obj, H, W) bool; an object
    never prompted stays empty."""
    import torch
    from slam.masks import torch_dtype
    n, (H, W) = len(imgs), imgs[0].shape[:2]
    out = np.zeros((n, n_obj, H, W), bool)
    if not schedule:
        return out
    sess = proc.init_video_session(video=imgs, inference_device=dev, video_storage_device="cpu",
                                   dtype=torch_dtype(dtype))
    with torch.inference_mode():
        for fi, objs in sorted(schedule.items()):
            # all objects of a frame in ONE call (the processor replaces its list of objects with
            # new inputs on every call); objects with fewer points are padded with their first
            # (positive) point, as slam.masks.segment_masks pads with a repeated point
            oids = sorted(objs)
            n_pts = max(len(objs[o][0]) for o in oids)
            pts = [objs[o][0] + [objs[o][0][0]] * (n_pts - len(objs[o][0])) for o in oids]
            labels = [objs[o][1] + [1] * (n_pts - len(objs[o][1])) for o in oids]
            proc.add_inputs_to_inference_session(inference_session=sess, frame_idx=fi, obj_ids=oids,
                                                 input_points=[pts], input_labels=[labels])
            model(inference_session=sess, frame_idx=fi)
        first = min(schedule)
        done = np.zeros(n, bool)
        for rev in (False, True):
            for o in model.propagate_in_video_iterator(sess, start_frame_idx=first, reverse=rev):
                m = proc.post_process_masks([o.pred_masks], original_sizes=[[H, W]], binarize=True)[0][:, 0]
                m = m.cpu().numpy()
                for j in range(len(m)):
                    oid = sess.obj_idx_to_id(j)
                    out[o.frame_idx, oid - 1] = m[j]
                done[o.frame_idx] = True
    if not done.all():
        raise RuntimeError(f"SAM3 tracker: {int((~done).sum())} frames without output")
    return out
