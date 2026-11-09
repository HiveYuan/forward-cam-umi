"""Overlay gallery of the exp006 motion masks: SAM2 (exp001) vs SAM3 (sam3_v2, exp006), as a
Markdown page GitHub renders (README.md next to this script) with its images in img/.

  V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
  $V experiments/exp006_sam3_v2/gallery/make_gallery.py

Frames, 4 per segment (120): the 2 evenly spaced frames of exp002's gallery ("typical") and the 2
frames where SAM3 and SAM2 disagree most (lowest IoU, at least 15 frames apart and not one of the
typical frames). Colours: green = both, cyan = SAM2 only, magenta = SAM3 only. The numbers in the
tables come from stats.json (region audit: audit_eval.py; agreement: results/masks_motion_vs_sam2.md).
Reads the cache only (masks, preprocessed images); writes img/*.jpg and README.md.
"""
import json
from pathlib import Path

import cv2
import numpy as np

CACHE = Path("/home/student/yuanliu-hawaii/work/cache")
KEYS = {"sam2": "86471818888012b6", "sam3": "93ead78627ecc88e"}     # exp001 sam2_points, exp006 sam3_v2
PRE = "65ab0510375aa8cd"                                             # exp001/exp006 preprocess
EVEN = Path("/home/student/yuanliu-hawaii/work/runs/exp002_sam3_masks/main/overlays/sam3_vs_sam2/index.json")
HERE = Path(__file__).resolve().parent
W_OUT, MIN_SEP = 800, 15
COLOURS = {"sam2_only": (255, 230, 0), "sam3_only": (255, 0, 220), "both": (40, 190, 40)}   # BGR


def load(name, seg):
    z = np.load(CACHE / "masks" / KEYS[name] / seg / "masked.npz")
    return np.unpackbits(z["masked"], axis=-1, count=960).astype(bool)


def iou(a, b):
    u = (a | b).sum((-2, -1))
    return np.where(u == 0, 1.0, (a & b).sum((-2, -1)) / np.maximum(u, 1))


def overlay(img, ref, cand):
    o = img.astype(np.float32)
    for m, col in ((ref & ~cand, COLOURS["sam2_only"]), (cand & ~ref, COLOURS["sam3_only"]),
                   (ref & cand, COLOURS["both"])):
        o[m] = 0.45 * o[m] + 0.55 * np.array(col, np.float32)
    h = round(img.shape[0] * W_OUT / img.shape[1])
    return cv2.resize(o.astype(np.uint8), (W_OUT, h), interpolation=cv2.INTER_AREA)


def main():
    even = {}
    for e in json.load(open(EVEN)):
        if e["kind"] == "even":
            even.setdefault(e["segment"], []).append(e["i"])
    (HERE / "img").mkdir(exist_ok=True)
    for old in (HERE / "img").glob("*.jpg"):
        old.unlink()
    rows = []
    for seg in sorted(even):
        a, b = load("sam2", seg), load("sam3", seg)
        per = iou(a, b)
        picks = [(i, "typical") for i in sorted(even[seg])]
        for i in np.argsort(per, kind="stable"):
            if len(picks) == 4:
                break
            if all(abs(int(i) - j) >= MIN_SEP for j, _ in picks):
                picks.append((int(i), "most different"))
        for i, kind in picks:
            img = cv2.imread(str(CACHE / "preprocess" / PRE / seg / "images" / f"{i:06d}.jpg"))
            name = f"{seg}_{i:06d}.jpg"
            cv2.imwrite(str(HERE / "img" / name), overlay(img, a[i], b[i]), [cv2.IMWRITE_JPEG_QUALITY, 80])
            rows.append({"segment": seg, "i": i, "kind": kind, "iou": float(per[i]), "file": f"img/{name}"})
    st = json.load(open(HERE / "stats.json"))
    write_page(rows, st)
    print(f"{len(rows)} images -> {HERE / 'img'}, page {HERE / 'README.md'}")


def write_page(rows, st):
    A, g, d = st["audit"], st["agreement"], st["droid"]
    L = ["# glove7 SAM3 v2 Masks", "",
         "Motion masks on yam_glove7 (30 episode segments, 8,972 frames): SAM2 (exp001) against SAM3 "
         "(`sam3_v2`, exp006). Each image overlays both masks on the undistorted head-camera frame:", "",
         "- green: masked by both;",
         "- cyan: SAM2 only;",
         "- magenta: SAM3 only.", "",
         "Judge each colour by what the pixels are: everything that moves on its own (hand, arm, glove rig, its "
         "cable, a held block) should be masked, and static things should not.", "",
         "## Mask setups", "",
         "Both masks are dilated by 8 px before DROID, and masked pixels get zero weight in its bundle adjustment.", "",
         "- **SAM2** (`facebook/sam2.1-hiera-large`, video propagation): every 30 frames, two objects are "
         "prompted with points projected from the ball pose: the glove (ball centre and flange) and the hand "
         "(one point on the back of the hand).",
         "- **SAM3** (`facebook/sam3`): the text prompts \"hand\", \"arm\" and \"cable\" give tracked instances. "
         "An instance is kept only where it lies within 8 px of the tracked wearer and has not grown to more "
         "than 3x its usual size. Every 10 frames, three tracker objects are prompted with points projected from "
         "the ball pose: the gripper (ball centre and three points on its body), the hand and forearm (two "
         "points), and a held object (a point between the fingertips, used only while the gripper is closed "
         "after it was open). The mask is the union of all parts.", "",
         "## Region audit", "",
         "In the 60 frames where SAM2 and an earlier SAM3 setup disagreed most, two independent reviewers judged "
         "each of the 159 disagreement regions as moving or static and agreed on 154 (97%) "
         "(`experiments/audits/2026-11-08_sam3_vs_sam2_regions/`). SAM3's thresholds were tuned on these "
         "regions, so the audit favours SAM3.", "",
         "| measure | SAM2 | SAM3 |", "|---|---|---|",
         f"| moving regions covered, of 80 (area, % of a frame) | {A['sam2']['moving']} | {A['sam3']['moving']} |",
         f"| static regions masked, of 74 (area, % of a frame) | {A['sam2']['static']} | {A['sam3']['static']} |",
         f"| held block covered, 4 frames | {A['sam2']['held']} | {A['sam3']['held']} |", "",
         "## All frames", "",
         f"Agreement of SAM3 with SAM2 over all {g['frames']:,} frames (agreement, not accuracy): IoU median "
         f"{g['iou_median']:.2f} (p10 {g['iou_p10']:.2f}); on DROID's 1/8 cells median {g['cells_median']:.2f} "
         f"(p10 {g['cells_p10']:.2f}); masked area {100 * g['area_sam3']:.1f}% of the frame (SAM2 "
         f"{100 * g['area_sam2']:.1f}%).", "",
         f"DROID E3 (motion + tile masks): head rotation error at 1 s, median {d['rot_1s_sam3']} deg with SAM3 "
         f"and {d['rot_1s_sam2']} deg with SAM2; tracking failure {d['fail_sam3']} and {d['fail_sam2']}.", "",
         "## Frames", "",
         "Four frames per segment: two evenly spaced (typical) and the two where SAM3 and SAM2 disagree most "
         "(lowest IoU, at least 15 frames apart).", ""]
    segs = sorted({r["segment"] for r in rows})
    L.append(" · ".join(f"[{s}](#{s})" for s in segs))
    L.append("")
    for s in segs:
        L += [f"### {s}", ""]
        for r in [r for r in rows if r["segment"] == s]:
            L += [f"![{s} frame {r['i']}]({r['file']})", "",
                  f"{s}, frame {r['i']}, {r['kind']}: IoU {r['iou']:.2f}", ""]
    L += ["---", "", "Made by `make_gallery.py` from the cached masks (keys "
          f"sam2 `{KEYS['sam2']}`, sam3 `{KEYS['sam3']}`).", ""]
    (HERE / "README.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
