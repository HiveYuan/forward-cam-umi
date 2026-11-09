"""Analysis step mask_compare (venv, CPU): candidate mask sets vs a reference mask set.

Runs like the other analysis steps on the analysis view (slam.config.WORK =
<work>/runs/<exp>/<variant>/view, legacy layout): per segment it reads frames.json, images/
and masks/<name>.npz (view.py contract: masked = packbits of (T, H, W) bool along the last
axis, True = do not use; SAM3 masks also carry parts = packbits (T, P, H, W) and part_names).

Per frame, with R the reference's masked pixels, X the candidate's and N the frame's pixels:
  iou          |R & X| / |R | X|
  recall       |R & X| / |R|      fraction of the reference covered by the candidate
  precision    |R & X| / |X|      fraction of the candidate inside the reference
  area_ref     |R| / N,  area_cand |X| / N
  extra_area   |X & ~R| / N       candidate-only pixels
  missed_area  |R & ~X| / N       reference-only pixels
  cells_iou    IoU of the DROID-invalid 1/8 cells of R and of X, each dilated by dilate_px
               (the rule of slam.droid_masked.valid_grid / slam.scale._valid_cells: dilate at
               full resolution, a cell is invalid if any of its 64 pixels is masked)
  part area    |part| / N per candidate part
A ratio whose denominator is empty is 1 (two empty masks agree: IoU 1; an empty reference
has nothing to miss, recall 1; an empty candidate has nothing extra, precision 1), so every
stat has n = frames.

Outputs per candidate <cand> (job.out_dir = <work>/runs/<exp>/<variant>/results):
  masks_<cand>_vs_<ref>.json  {"reference", "candidate", "dilate_px", "parts",
                               "segments": {seg: {"frames", "iou", "recall", "precision",
                                  "area_ref", "area_cand", "extra_area", "missed_area",
                                  "cells_iou", "part_area": {part: mean}, "worst_frames": [[i, iou]] (5)}},
                               "summary": {the same pooled over all frames of all segments,
                                  "segments_iou_median_below_0.8", "worst_segments": [[seg, iou median]] (5)}}
                              stat = {"n", "median", "p10", "p90", "mean"} over frames; area_* and
                              part_area are means over frames
  masks_<cand>_vs_<ref>.md    one table row per segment + the pooled summary
  <out_dir>/../overlays/<cand>_vs_<ref>/<seg>_<i:06d>.jpg + index.json (big; not in results/):
                              overlays_per_segment frames per segment, half evenly spaced, half
                              the lowest-IoU frames (no duplicates); candidate parts filled in
                              colour (legend), reference outlined in white, title "<seg> i=<i> IoU=<x>"
"""
import json
import shutil
from pathlib import Path

import numpy as np

from slam import config as C

METRICS = ("iou", "recall", "precision", "extra_area", "missed_area", "cells_iou")
N_WORST = 5                    # worst_frames per segment, worst_segments in the summary
IOU_BELOW = 0.8
BELOW_KEY = "segments_iou_median_below_0.8"   # summary: segments with IoU median < IOU_BELOW
CHUNK = 32                     # frames unpacked at a time
OVERLAY_W = 960
JPG_QUALITY = 85
# RGB, the colours of slam.masks_sam3.PART_COLORS (qa.jpg), so a part looks the same in both
PART_COLORS = [(255, 60, 60), (255, 160, 0), (60, 120, 255), (60, 200, 60), (220, 60, 220), (0, 220, 220)]


# ---------------------------------------------------------------------- numbers
def stat(x):
    """{"n", "median", "p10", "p90", "mean"} of the finite values of x (None when there are none)."""
    x = np.asarray(x, float).ravel()
    x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0, "median": None, "p10": None, "p90": None, "mean": None}
    return {"n": int(len(x)), "median": float(np.median(x)), "p10": float(np.percentile(x, 10)),
            "p90": float(np.percentile(x, 90)), "mean": float(np.mean(x))}


def ratio(num, den):
    """num / den elementwise; 1 where den == 0 (0 / 0: nothing to agree on)."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    out = np.ones(np.broadcast(num, den).shape)
    np.divide(num, den, out=out, where=den > 0)
    return out


def invalid_cells(masked, dilate_px):
    """(T, H, W) bool -> (T, H/8, W/8) bool, True = DROID-invalid cell. The negation of
    slam.scale._valid_cells (= slam.droid_masked.valid_grid): dilate by dilate_px at full
    resolution with a (2 d + 1)^2 square, then a 1/8 cell is invalid if any pixel is masked."""
    import cv2
    T, H, W = masked.shape
    if H % 8 or W % 8:
        raise ValueError(f"frame size {W}x{H} is not a multiple of 8")
    k = np.ones((2 * dilate_px + 1, 2 * dilate_px + 1), np.uint8)
    out = np.empty((T, H // 8, W // 8), bool)
    for i in range(T):
        m = cv2.dilate(masked[i].astype(np.uint8), k)
        out[i] = m.reshape(H // 8, 8, W // 8, 8).max((1, 3)) > 0
    return out


def _unpack(packed, W):
    return np.unpackbits(packed, axis=-1, count=W).astype(bool)


def load_mask(path, T, H, W):
    """masked.npz -> (packed masked (T, H, ceil(W/8)), packed parts (T, P, H, .) or None, part names)."""
    z = np.load(path)
    masked = z["masked"]
    if masked.shape != (T, H, (W + 7) // 8):
        raise ValueError(f"{path}: masked {masked.shape}, expected {(T, H, (W + 7) // 8)} "
                         f"(packbits of {T} frames of {W}x{H})")
    if "parts" not in z.files:
        return masked, None, []
    parts = z["parts"]
    if parts.ndim != 4 or parts.shape[0] != T or parts.shape[2:] != masked.shape[1:]:
        raise ValueError(f"{path}: parts {parts.shape} does not match masked {masked.shape}")
    names = ([str(s) for s in z["part_names"]] if "part_names" in z.files
             else [f"part{j}" for j in range(parts.shape[1])])
    if len(names) != parts.shape[1]:
        raise ValueError(f"{path}: {len(names)} part names for {parts.shape[1]} parts")
    return masked, parts, names


def compare_segment(seg_dir, ref, cand, dilate_px):
    """Per-frame numbers of one segment: {"i" (frame ids), metric: (T,), "area_ref", "area_cand",
    "part_names", "part_area": (T, P)}."""
    seg_dir = Path(seg_dir)
    fj = json.load(open(seg_dir / "frames.json"))
    W, H = fj["size"]
    ids = np.array([f["i"] for f in fj["frames"]], int)
    T = len(ids)
    r_p, _, _ = load_mask(seg_dir / "masks" / f"{ref}.npz", T, H, W)
    x_p, parts_p, names = load_mask(seg_dir / "masks" / f"{cand}.npz", T, H, W)
    cnt = {k: np.zeros(T, np.int64) for k in ("r", "x", "rx", "cr", "cx", "crx", "cu")}
    part_area = np.zeros((T, len(names)))
    for a in range(0, T, CHUNK):
        b = min(T, a + CHUNK)
        R, X = _unpack(r_p[a:b], W), _unpack(x_p[a:b], W)
        cnt["r"][a:b] = np.count_nonzero(R, axis=(1, 2))
        cnt["x"][a:b] = np.count_nonzero(X, axis=(1, 2))
        cnt["rx"][a:b] = np.count_nonzero(R & X, axis=(1, 2))
        cr, cx = invalid_cells(R, dilate_px), invalid_cells(X, dilate_px)
        cnt["crx"][a:b] = np.count_nonzero(cr & cx, axis=(1, 2))
        cnt["cu"][a:b] = np.count_nonzero(cr | cx, axis=(1, 2))
        if parts_p is not None:
            part_area[a:b] = np.count_nonzero(_unpack(parts_p[a:b], W), axis=(2, 3)) / float(H * W)
    N = float(H * W)
    r, x, rx = cnt["r"], cnt["x"], cnt["rx"]
    return {"i": ids, "size": (W, H),
            "iou": ratio(rx, r + x - rx), "recall": ratio(rx, r), "precision": ratio(rx, x),
            "extra_area": (x - rx) / N, "missed_area": (r - rx) / N,
            "cells_iou": ratio(cnt["crx"], cnt["cu"]),
            "area_ref": r / N, "area_cand": x / N, "part_names": names, "part_area": part_area}


def _worst(iou, ids, n=N_WORST):
    order = np.argsort(iou, kind="stable")[:n]
    return [[int(ids[k]), float(iou[k])] for k in order]


def segment_summary(f):
    """JSON block of one segment from compare_segment's per-frame numbers."""
    out = {"frames": int(len(f["i"]))}
    for k in ("iou", "recall", "precision"):
        out[k] = stat(f[k])
    out["area_ref"] = _mean(f["area_ref"])
    out["area_cand"] = _mean(f["area_cand"])
    for k in ("extra_area", "missed_area", "cells_iou"):
        out[k] = stat(f[k])
    out["part_area"] = {p: _mean(f["part_area"][:, j]) for j, p in enumerate(f["part_names"])}
    out["worst_frames"] = _worst(f["iou"], f["i"])
    return out


def _mean(x):
    return float(np.mean(x)) if len(x) else None


def pooled_summary(per_seg, segs):
    """Summary block pooled over all frames of `segs` (per_seg: {seg: per-frame numbers})."""
    cat = {k: np.concatenate([per_seg[s][k] for s in segs]) if segs else np.zeros(0)
           for k in METRICS + ("area_ref", "area_cand")}
    out = {"frames": int(sum(len(per_seg[s]["i"]) for s in segs))}
    for k in ("iou", "recall", "precision", "extra_area", "missed_area", "cells_iou"):
        out[k] = stat(cat[k])
    out["area_ref"] = _mean(cat["area_ref"])
    out["area_cand"] = _mean(cat["area_cand"])
    tot, n = {}, {}
    for s in segs:                                   # frame-weighted, over the segments having the part
        for j, p in enumerate(per_seg[s]["part_names"]):
            tot[p] = tot.get(p, 0.0) + float(per_seg[s]["part_area"][:, j].sum())
            n[p] = n.get(p, 0) + len(per_seg[s]["i"])
    out["part_area"] = {p: tot[p] / n[p] if n[p] else None for p in tot}
    med = {s: stat(per_seg[s]["iou"])["median"] for s in segs}
    out[BELOW_KEY] = [s for s in segs if med[s] is not None and med[s] < IOU_BELOW]
    ranked = sorted((m, s) for s, m in med.items() if m is not None)
    out["worst_segments"] = [[s, m] for m, s in ranked[:N_WORST]]
    return out


# ---------------------------------------------------------------------- overlays
def select_overlays(iou, n):
    """Row indices to draw: n // 2 evenly spaced (bin centres) then the lowest-IoU frames not
    already taken, up to min(n, T) frames. -> [(row, "even" | "worst")]."""
    T = len(iou)
    n = min(int(n), T)
    n_even = n // 2
    even = sorted({min(T - 1, int((j + 0.5) * T / n_even)) for j in range(n_even)}) if n_even else []
    out, taken = [(k, "even") for k in even], set(even)
    for k in np.argsort(iou, kind="stable"):
        if len(out) >= n:
            break
        if int(k) not in taken:
            out.append((int(k), "worst"))
            taken.add(int(k))
    return out


def _bgr(rgb):
    return tuple(int(c) for c in rgb[::-1])


def _text_box(img, text, org, scale=0.7, thick=2):
    """White text on a dark box, top-left corner at org; returns the box's bottom-right."""
    import cv2
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    x, y = org
    cv2.rectangle(img, (x, y), (x + tw + 10, y + th + base + 10), (0, 0, 0), -1)
    cv2.putText(img, text, (x + 5, y + th + 5), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thick,
                cv2.LINE_AA)
    return x + tw + 10, y + th + base + 10


def render_overlay(img, ref_mask, fills, names, ref_name, title):
    """img (H, W, 3) BGR; fills (P, H, W) bool candidate parts (or its union, P = 1), drawn in
    PART_COLORS with names in a legend; ref_mask (H, W) bool outlined in white. -> BGR image,
    resized to OVERLAY_W wide."""
    import cv2
    ov = img.astype(np.float32)
    for j in range(len(fills)):
        m = fills[j]
        ov[m] = 0.55 * ov[m] + 0.45 * np.array(_bgr(PART_COLORS[j % len(PART_COLORS)]), np.float32)
    ov = np.clip(ov + 0.5, 0, 255).astype(np.uint8)
    cnt = cv2.findContours(ref_mask.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[-2]
    cv2.drawContours(ov, cnt, -1, (255, 255, 255), 2, cv2.LINE_AA)
    H, W = ov.shape[:2]
    if W != OVERLAY_W:
        ov = cv2.resize(ov, (OVERLAY_W, int(round(H * OVERLAY_W / W))), interpolation=cv2.INTER_AREA)
        H, W = ov.shape[:2]
    # title in a band above the frame, legend in a band below it: no frame pixel is covered
    top = np.zeros((34, W, 3), np.uint8)
    _text_box(top, title, (4, 2))
    bot = np.zeros((30, W, 3), np.uint8)
    items = [(n, PART_COLORS[j % len(PART_COLORS)], True) for j, n in enumerate(names)]
    items.append((f"{ref_name} (reference)", (255, 255, 255), False))
    sc, th = 0.55, 1
    widths = [cv2.getTextSize(n, cv2.FONT_HERSHEY_SIMPLEX, sc, th)[0][0] + 34 for n, _, _ in items]
    y0 = 4
    x = 12
    for (n, col, filled), w in zip(items, widths):
        cv2.rectangle(bot, (x, y0 + 2), (x + 16, y0 + 18), _bgr(col), -1 if filled else 2)
        cv2.putText(bot, n, (x + 22, y0 + 16), cv2.FONT_HERSHEY_SIMPLEX, sc, (255, 255, 255), th, cv2.LINE_AA)
        x += w
    return np.vstack([top, ov, bot])


def write_overlays(seg_dir, seg, f, ref, cand, n, out_dir):
    """Overlay jpgs of one segment into out_dir -> index entries."""
    import cv2
    seg_dir = Path(seg_dir)
    W, H = f["size"]
    T = len(f["i"])
    r_p, _, _ = load_mask(seg_dir / "masks" / f"{ref}.npz", T, H, W)
    x_p, parts_p, names = load_mask(seg_dir / "masks" / f"{cand}.npz", T, H, W)
    entries = []
    for k, kind in select_overlays(f["iou"], n):
        i = int(f["i"][k])
        img = cv2.imread(str(seg_dir / "images" / f"{i:06d}.jpg"))
        if img is None:
            raise FileNotFoundError(seg_dir / "images" / f"{i:06d}.jpg")
        if parts_p is not None:
            fills, labels = _unpack(parts_p[k], W), names
        else:
            fills, labels = _unpack(x_p[k:k + 1], W), [cand]
        iou = float(f["iou"][k])
        ov = render_overlay(img, _unpack(r_p[k], W), fills, labels, ref, f"{seg} i={i} IoU={iou:.3f}")
        name = f"{seg}_{i:06d}.jpg"
        cv2.imwrite(str(out_dir / name), ov, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])
        entries.append({"file": name, "segment": seg, "i": i, "iou": iou, "kind": kind})
    return entries


# ---------------------------------------------------------------------- report
def _f(x, nd=3):
    return "-" if x is None else f"{x:.{nd}f}"


def markdown(res, overlay_rel):
    ref, cand, d = res["reference"], res["candidate"], res["dilate_px"]
    sm = res["summary"]
    parts = ", ".join(res["parts"]) if res["parts"] else "none"
    L = [f"# Masks: {cand} vs {ref}", "",
         f"Reference `{ref}`, candidate `{cand}` (parts: {parts}); {len(res['segments'])} segments, "
         f"{sm['frames']} frames. Fractions, not percent. Per frame: IoU = |R&X|/|R|X|, recall = |R&X|/|R| "
         f"(reference covered), precision = |R&X|/|X| (candidate inside the reference), extra = |X-R| / frame, "
         f"missed = |R-X| / frame, cells IoU = IoU of the DROID-invalid 1/8 cells after dilating each mask by "
         f"{d} px; an empty denominator counts 1. Medians over the frames of the segment.", "",
         "| segment | frames | IoU | IoU p10 | recall | precision | area ref | area cand | extra | missed "
         "| cells IoU | worst frame (IoU) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]

    def row(name, b, worst):
        return (f"| {name} | {b['frames']} | {_f(b['iou']['median'])} | {_f(b['iou']['p10'])} "
                f"| {_f(b['recall']['median'])} | {_f(b['precision']['median'])} | {_f(b['area_ref'])} "
                f"| {_f(b['area_cand'])} | {_f(b['extra_area']['median'])} | {_f(b['missed_area']['median'])} "
                f"| {_f(b['cells_iou']['median'])} | {worst} |")
    for seg, b in res["segments"].items():
        w = b["worst_frames"][0] if b["worst_frames"] else None
        L.append(row(seg, b, f"{w[0]} ({w[1]:.3f})" if w else "-"))
    L.append(row("**all**", sm, "-"))
    L += ["", "## Summary (pooled over all frames)", "",
          "| metric | n | median | p10 | p90 | mean |", "|---|---:|---:|---:|---:|---:|"]
    for k in METRICS:
        s = sm[k]
        L.append(f"| {k} | {s['n']} | {_f(s['median'])} | {_f(s['p10'])} | {_f(s['p90'])} | {_f(s['mean'])} |")
    L += ["", f"Mean area: reference {_f(sm['area_ref'])}, candidate {_f(sm['area_cand'])}."]
    if sm["part_area"]:
        L.append("Candidate part area (mean fraction of the frame): "
                 + ", ".join(f"{p} {_f(v)}" for p, v in sm["part_area"].items()) + ".")
    below = sm[BELOW_KEY]
    L.append(f"Segments with IoU median < {IOU_BELOW}: {', '.join(below) if below else 'none'}.")
    L.append("Worst segments (IoU median): "
             + (", ".join(f"{s} {m:.3f}" for s, m in sm["worst_segments"]) or "-") + ".")
    L.append(f"Overlays (reference outlined in white, candidate parts filled): `{overlay_rel}/` (index.json).")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------- step
def _check_params(p):
    ref, cands = p["reference"], list(p["candidates"])
    names = [ref] + cands
    if not cands or not all(isinstance(x, str) and x for x in names) or len(set(names)) != len(names):
        raise ValueError(f"mask_compare: reference and candidates must be distinct mask names, got {names}")
    for k in ("dilate_px", "overlays_per_segment"):
        if isinstance(p[k], bool) or not isinstance(p[k], int) or p[k] < 0:
            raise ValueError(f"mask_compare.params.{k}: a non-negative integer, got {p[k]!r}")
    return ref, cands


def run_mask_compare(job):
    p = job.params
    ref, cands = _check_params(p)
    d, n_ov = p["dilate_px"], p["overlays_per_segment"]
    seg_root = C.segments_dir(job.session)
    out_dir = Path(job.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for cand in cands:
        tag = f"{cand}_vs_{ref}"
        per_seg, segs, parts = {}, [], []
        for seg in job.segments:
            per_seg[seg] = compare_segment(seg_root / seg, ref, cand, d)
            segs.append(seg)
            parts += [x for x in per_seg[seg]["part_names"] if x not in parts]
            job.log(f"{tag} {seg}: IoU median {_f(stat(per_seg[seg]['iou'])['median'])}")
        res = {"reference": ref, "candidate": cand, "dilate_px": d, "parts": parts,
               "segments": {s: segment_summary(per_seg[s]) for s in segs},
               "summary": pooled_summary(per_seg, segs)}
        ov_dir = out_dir.parent / "overlays" / tag
        if ov_dir.exists():
            shutil.rmtree(ov_dir)
        ov_dir.mkdir(parents=True)
        index = []
        for s in segs:
            index += write_overlays(seg_root / s, s, per_seg[s], ref, cand, n_ov, ov_dir)
        with open(ov_dir / "index.json", "w") as fh:
            json.dump(index, fh, indent=1, allow_nan=False)
        with open(out_dir / f"masks_{tag}.json", "w") as fh:
            json.dump(res, fh, indent=1, allow_nan=False)
        (out_dir / f"masks_{tag}.md").write_text(
            markdown(res, f"overlays/{tag}/ in the work run directory {out_dir.parent} (not in git)"))
        sm = res["summary"]
        result[cand] = {"json": f"masks_{tag}.json", "segments": len(segs), "frames": sm["frames"],
                        "iou_median": sm["iou"]["median"], "recall_median": sm["recall"]["median"],
                        "precision_median": sm["precision"]["median"],
                        "cells_iou_median": sm["cells_iou"]["median"],
                        BELOW_KEY: sm[BELOW_KEY],
                        "overlays": len(index), "overlay_dir": str(ov_dir)}
        job.log(f"{tag}: {len(segs)} segments, {sm['frames']} frames, IoU median {_f(sm['iou']['median'])}, "
                f"recall {_f(sm['recall']['median'])}, precision {_f(sm['precision']['median'])}, "
                f"cells IoU {_f(sm['cells_iou']['median'])}; {len(index)} overlays in {ov_dir}")
    return result
