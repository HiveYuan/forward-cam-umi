"""Audit-set evaluation of motion-mask sets (experiments/audits/2026-11-08_sam3_vs_sam2_regions).

  python experiments/exp006_sam3_v2/audit_eval.py --masks sam2=<cache>/masks/86471818888012b6 \
      v1=<cache>/masks/44820ccc66cd62ec v2=<cache>/masks/<exp006 motion key> [--json out.json]

Each mask set is a masks cache entry (epNN/masked.npz, packbits along the last axis, True = masked).
Numbers:
  regions   the audit's disagreement regions between SAM2 (86471818888012b6) and SAM3 v1
            (44820ccc66cd62ec), rebuilt with the audit's prep.py rules (connected components >= 400 px
            of SAM2-only / v1-only pixels on its 60 frames) and checked against regions.json; only the
            154 regions both judges agree on. A region is covered if >= 50% of its pixels are masked.
            moving covered = good, static covered = bad; counts and area (sum over regions, % of
            one frame).
  block     the red block on the frames the judges listed under "missed by both", segmented for
            this evaluation only by colour (red HSV pixels, the connected component nearest the
            projected fingertip point; checked by eye): fraction of its pixels masked. Frames are
            grouped by the gripper state seen on the images and in the gripper width: held, releasing
            (gripper opening, block still in the jaws), not held (block on the table / in the bin).
  vs SAM2   on every frame of the audit's 30 segments: IoU with SAM2, SAM2 pixels covered (recall),
            masked area; median and p10 over frames.
The colour rule is for evaluation only; no mask method uses colour.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
AUDIT = REPO / "experiments/audits/2026-11-08_sam3_vs_sam2_regions"
CACHE = Path("/home/student/yuanliu-hawaii/work/cache")
PRE = CACHE / "preprocess/65ab0510375aa8cd"
REF_SAM2 = CACHE / "masks/86471818888012b6"
REF_V1 = CACHE / "masks/44820ccc66cd62ec"
W, H = 960, 536
SEGMENTS = [f"ep{k:02d}" for k in range(30)]
# judge-listed "missed by both" frames: state from the images and the gripper width (command units)
BLOCK_FRAMES = {"ep06": (240, "held"), "ep07": (240, "held"), "ep12": (255, "held"), "ep16": (270, "held"),
                "ep02": (270, "releasing"), "ep19": (270, "releasing"), "ep05": (300, "not_held"),
                "ep20": (184, "not_held"), "ep26": (180, "not_held"), "ep28": (120, "not_held"),
                "ep22": (177, "not_held"), "ep24": (210, "not_held")}
FINGERTIP = np.array([-0.0943, -0.1071, 0.0855])      # glove body frame, as held_points of sam3_v2


def load(entry, seg):
    z = np.load(Path(entry) / seg / "masked.npz")
    return np.unpackbits(z["masked"], axis=-1, count=W).astype(bool)


def regions():
    """[(seg, i, rid, kind, verdict, mask)] for the regions both judges agree on."""
    R = json.load(open(AUDIT / "regions.json"))
    J = collections.defaultdict(dict)
    for b in json.load(open(AUDIT / "verdicts.json")):
        for f in b["frames"]:
            for r in f["regions"]:
                J[(f["segment"], f["i"], r["region"])][b["judge"]] = r["verdict"]
    ref = {(r["segment"], r["i"], r["region"]): r for r in R}
    out, cache = [], {}
    for s, i in sorted(set((r["segment"], r["i"]) for r in R)):
        if s not in cache:
            cache = {s: (load(REF_SAM2, s), load(REF_V1, s))}
        a, b = cache[s][0][i], cache[s][1][i]
        rid = 0
        for kind, m in (("sam2_only", a & ~b), ("sam3_only", b & ~a)):
            n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
            for c in range(1, n):
                if st[c, cv2.CC_STAT_AREA] < 400:
                    continue
                rid += 1
                r = ref[(s, i, rid)]
                assert r["kind"] == kind and r["area_px"] == st[c, cv2.CC_STAT_AREA], (s, i, rid)
                d = J[(s, i, rid)]
                if len(d) == 2 and d[1] == d[2]:
                    out.append((s, i, rid, kind, d[1], lab == c))
    return out


def block_gt():
    """{(seg, i): (state, red block mask)} (evaluation only, colour-based)."""
    from slam import geometry as G
    out = {}
    for seg, (i, state) in BLOCK_FRAMES.items():
        fj = json.load(open(PRE / seg / "frames.json"))
        gt = np.load(PRE / seg / "gt.npz")
        pose = {int(k): G.rt_to_T(r, t)[0] for k, r, t in zip(gt["full_k"], gt["full_rvec"], gt["full_tvec"])}
        T = pose[fj["frames"][i]["k"]]
        x, y, z = np.array(fj["K"]) @ (T[:3, :3] @ FINGERTIP + T[:3, 3])
        u, v = x / z, y / z
        hsv = cv2.cvtColor(cv2.imread(str(PRE / seg / "images" / f"{i:06d}.jpg")), cv2.COLOR_BGR2HSV)
        red = (((hsv[..., 0] < 8) | (hsv[..., 0] > 172)) & (hsv[..., 1] > 110) & (hsv[..., 2] > 50)).astype(np.uint8)
        red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(red, 8)
        best, bd = 0, 1e9
        for c in range(1, n):
            if st[c, cv2.CC_STAT_AREA] < 150:
                continue
            ys, xs = np.nonzero(lab == c)
            d = np.min(np.hypot(xs - u, ys - v))
            if d < bd:
                best, bd = c, d
        out[(seg, i)] = (state, lab == best if best and bd < 120 else np.zeros((H, W), bool))
    return out


def evaluate(entry, regs, blocks):
    res = {"moving": [0, 0.0, 0, 0.0], "static": [0, 0.0, 0, 0.0]}
    per, ious, rec, area = [], [], [], []
    by_seg = collections.defaultdict(list)
    for r in regs:
        by_seg[r[0]].append(r)
    blk = {}
    for s in SEGMENTS:
        m = load(entry, s)
        for _, i, rid, kind, v, rm in by_seg.get(s, []):
            c = float(m[i][rm].mean())
            e = res[v]
            e[2] += 1
            e[3] += rm.sum() / (W * H)
            if c >= 0.5:
                e[0] += 1
                e[1] += rm.sum() / (W * H)
            per.append({"segment": s, "i": i, "region": rid, "kind": kind, "verdict": v, "covered": round(c, 3)})
        if s in BLOCK_FRAMES:
            i = BLOCK_FRAMES[s][0]
            state, g = blocks[(s, i)]
            blk[f"{s}_{i}"] = {"state": state, "covered": float(m[i][g].mean()) if g.any() else None,
                               "px": int(g.sum())}
        ref = load(REF_SAM2, s)
        inter = (m & ref).sum((1, 2))
        uni = (m | ref).sum((1, 2))
        nr = ref.sum((1, 2))
        ious += list(np.where(uni > 0, inter / np.maximum(uni, 1), 1.0))
        rec += list(np.where(nr > 0, inter / np.maximum(nr, 1), 1.0))
        area += list(m.mean((1, 2)))
    mean_by = {st: [b["covered"] for b in blk.values() if b["state"] == st and b["covered"] is not None]
               for st in ("held", "releasing", "not_held")}
    return {"regions": {v: {"covered": res[v][0], "n": res[v][2], "area_covered_pct": 100 * res[v][1],
                            "area_pct": 100 * res[v][3]} for v in res},
            "block": blk, "block_mean": {k: (float(np.mean(v)) if v else None) for k, v in mean_by.items()},
            "vs_sam2": {"frames": len(ious), "iou_median": float(np.median(ious)), "iou_p10": float(np.percentile(ious, 10)),
                        "recall_median": float(np.median(rec)), "recall_p10": float(np.percentile(rec, 10)),
                        "recall_lt80_frac": float((np.asarray(rec) < 0.8).mean()),
                        "masked_frac_mean": float(np.mean(area))},
            "per_region": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masks", nargs="+", required=True, help="name=<masks cache entry dir>")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    regs, blocks = regions(), block_gt()
    out = {}
    print(f"{len(regs)} agreed regions; moving covered (good) / static covered (bad): count, area % of a frame")
    for spec in a.masks:
        name, entry = spec.split("=", 1)
        r = evaluate(entry, regs, blocks)
        out[name] = r
        g, b, v = r["regions"]["moving"], r["regions"]["static"], r["vs_sam2"]
        bm = r["block_mean"]
        print(f"{name:8s} moving {g['covered']:2d}/{g['n']} ({g['area_covered_pct']:5.1f}/{g['area_pct']:.1f}%)  "
              f"static {b['covered']:2d}/{b['n']} ({b['area_covered_pct']:5.1f}/{b['area_pct']:.1f}%)  "
              f"block held {bm['held']:.2f} releasing {bm['releasing']:.2f} not-held {bm['not_held']:.2f}  "
              f"IoU(SAM2) {v['iou_median']:.3f} p10 {v['iou_p10']:.3f}  SAM2 recall {v['recall_median']:.3f} "
              f"p10 {v['recall_p10']:.3f}  frames <80% of SAM2 covered {100 * v['recall_lt80_frac']:.1f}%  "
              f"area {100 * v['masked_frac_mean']:.1f}%")
        print("         block: " + ", ".join(f"{k} {x['state']} {x['covered']:.2f}" for k, x in r["block"].items()))
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
