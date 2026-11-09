# exp006_sam3_v2

**What.** exp003 with new SAM3 motion masks, `sam3_v2` (`slam/masks_sam3v2.py`,
`slam/pipeline/impl_masks_sam3v2.py`). Masked DROID-SLAM E1 (no masks, as in exp001/exp003) and E3
(motion + tile masks), scale B with an A cross-check, labels and evaluation as before. exp001's SAM2
masks are computed alongside (a cache hit) as the reference of `mask_compare`. Compared with
exp001 (SAM2) and exp003 (SAM3 v1).

**Why.** The region audit of v1 (`experiments/audits/2026-11-08_sam3_vs_sam2_regions/`) found that
v1 (1) masks static things through its text prompts (walls, the bin, desk cables: 73 of 74 static
regions, 170% of a frame), (2) misses the rig or its fine parts (40 moving regions SAM2 covers),
(3) like SAM2, does not cover a block while it is held. Mask rule unchanged: cover what moves on its
own, nothing static, no colour or object-specific rules.

```
HF_TOKEN_PATH=~/.config/yuanliu/hf_token $V -m slam.run experiments/exp006_sam3_v2/config.yaml
$V experiments/exp006_sam3_v2/audit_eval.py --masks sam2=<cache>/masks/86471818888012b6 \
    v1=<cache>/masks/44820ccc66cd62ec v2=<cache>/masks/<motion key>      # audit-set numbers below
```

## What changed vs v1, and why

Same model (facebook/sam3, same revision), same text prompts `hand`, `arm`, `cable`.

1. **Text instances are filtered; v1 OR-ed all of them.** Each SAM3 text detection is a masklet (an
   object id tracked over the segment); v2 judges every masklet on every frame:
   - **leak** (`leak_ratio` 3.0): drop it where its area is more than 3x its lower-quartile area over
     the segment. The audit's walls and bins are mostly masklets that sit on the arm or cable for a
     while and then balloon onto the wall or bin next to it (e.g. ep14 `cable` masklet: 2-6 k px,
     then 46 k px on the bin; ep12 `cable`: 2 k px, then 53 k px on the bin; ep27 `arm`:
     10-29 k px, then 61-73 k px with the wall).
   - **attach** (`attach_px` 8): keep only what is attached to the tracked wearer (rig, hand, held
     object), transitively; `cable` never seeds. Drops desk cables and other detections away from the
     wearer.
   - **components** (`split_components`): each connected part of an instance is judged on its own
     (one `cable` instance held the glove cable and, apart from it, a desk cable).
   - **border seeds** (`border_px`, `seed_prompts`): hand/arm instances touching the image edge as
     extra seeds (the wearer's arm enters from the edge) were implemented and evaluated, but they only
     added static regions (walls at the left edge are detected as `hand`/`arm`), so they are off
     (`border_px: -1`).
2. **Rig prompts.** v1 prompted `ball` + `flange` every 30 frames. The flange point lies on the
   hand/arm in 57% of the frames (v1 text parts at the projected point, 1700 frames), so v1's "rig"
   object was often the hand and missed the black gripper (audit: ep00, ep04, ep16, ep18, ep23, ep29).
   v2 prompts every 10 frames with the ball centre and three points on the gripper body (on the
   hand/arm in 0-0.5% of the frames, inside SAM2's mask in 98-100%), projected with the ball pose
   (`rig_points`, from `calib/glove_yosub_gripper_bundle.json` markers 40/46, 41/47 and the tool
   point of `calib/handeye_glove_yosub.json`; checked on images). A negative point on the back of the
   hand (`rig_negative_points`) was tried and dropped: it cut off the finger cube next to the thumb.
3. **Tracked hand.** A second tracker object for hand + forearm (`hand_points`): SAM2's hand point
   and a point offset by (0, 0.06, 0.03) m in the body frame, the farthest point of a grid around the
   hand point that still lands on the hand/arm in >= 98% of the frames; the second point raised the
   SAM2 pixels covered by the tracker objects from 0.84 to 0.90 (ep06) and 0.66 to 0.71 (ep00). It is
   also the anchor that keeps the arm instances.
4. **Held object.** A third tracker object prompted with a point between the fingertips (`held_points`:
   tool point + 2 cm along the finger axis; on the block in 12/12 inspected held frames, on the closed
   fingers in 8/8 closed-empty frames) on frames where the gripper is closed: width
   (`gt/gripper_wrist.npz`, command units) <= `held_width_max` 0.45, and only after the gripper was
   open in the episode (`held_after_open`: the gripper is closed at rest at the start of 27 of 30
   episodes, and there the point selected a block lying next to the fingers, ep28). Its mask is used only
   on those frames, so the object is not masked before the grasp or after the release (the tracker
   follows the block into the bin; gated out). Object-agnostic: no colour, no block model.

## Audit-set numbers

`audit_eval.py` (see its docstring), all 30 segments. v2 = the configured parameters; its masks were
computed from SAM3 outputs dumped per segment (text instances, tracker objects) and
`slam.masks_sam3v2.combine`, which is bit-identical to the `sam3_v2` worker output (checked on ep06
and ep12: masked, every part and the dropped area equal; scratch run of this config, key
`c3e0eb05f1ac613a`).

| 154 agreed regions (80 moving, 74 static) | SAM2 | SAM3 v1 | SAM3 v2 |
|---|---|---|---|
| moving regions covered (good) | 40 | 40 | **54** |
| moving area covered, % of a frame (of 83.4) | 61.1 | 22.3 | **68.5** |
| static regions covered (bad) | **1** | 73 | 10 |
| static area covered, % of a frame (of 170.6) | **0.2** | 170.3 | 21.9 |
| held block covered, 4 held frames (ep06/07/12/16 240-270) | 0.00 0.00 0.02 0.42 | 0.11 0.00 0.01 0.00 | **0.99 0.98 0.99 0.99** |
| block in the opening gripper (ep02 270 / ep19 270) | 0.12 / 0.00 | 0.08 / 0.51 | 0.05 / 0.91 |
| block not held, 6 frames (bad), mean | 0.14 | 0.01 | 0.16 |
| IoU with SAM2, median / p10 over 8972 frames | 1 | 0.932 / 0.715 | 0.942 / 0.875 |
| SAM2 pixels covered, median / p10 | 1 | 0.969 / 0.936 | 0.969 / 0.933 |
| frames with < 80% of SAM2's pixels covered | 0 | 3.8% | 1.7% |
| masked area, mean | 7.2% | 7.6% | 7.2% |

The not-held block frames: v2 covers the block in the bin after the release in ep05 300 (0.38, the
rig object) and next to the closed fingers at the start of ep28 (0.55, the rig object; the held object
is gated off there); 0.00-0.04 on the other four. Blocks on the table are otherwise untouched.

**What was tried (same 30 segments, the v2 tracker; moving / static regions covered, area in % of a
frame; frames with < 80% of SAM2 covered):**

| text instances | moving | static | < 80% SAM2 |
|---|---|---|---|
| none (tracker objects only) | 31 (59.2) | 1 (0.1) | 11.7% |
| all, attached to the wearer (idea 1 as specified: + border seeds) | 62 (78.1) | 51 (157.8) | 0.0% |
| attached, per connected component | 62 (78.1) | 37 (129.7) | 0.0% |
| + leak 2.0 | 47 (64.3) | 7 (7.9) | 3.9% |
| + leak 2.5 | 51 (66.4) | 9 (15.6) | 2.3% |
| **+ leak 3.0 (chosen)** | **54 (68.5)** | **10 (21.9)** | **1.7%** |
| + leak 4.0 | 59 (77.0) | 16 (28.7) | 0.9% |
| leak 3.0 with border seeds (`border_px` 4) | 54 (68.5) | 13 (26.6) | 1.6% |
| leak 3.0 without the component split | 54 (68.5) | 18 (28.5) | 1.6% |
| leak 3.0 without the held object | 54 (68.5) | 10 (21.9) | 1.7%; held block 0.47 |

Also tried and dropped (first 6-23 segments): a "near" rule (keep an attached instance only if
>= 50-70% of it lies within 25-40 px of the tracked wearer) removed walls but also the forearm and the
cable along it whenever the hand object stopped at the wrist (moving 8-13 of 17); a leak reference
that follows the masklet's last 5-20 frames instead of its whole-segment quartile let walls that
appear gradually back in (leak 2.0, 23 segments: static 10-16 of 56 regions vs 1, and no fewer frames
with SAM2 pixels missed). Tracker variants on ep06/ep00 (SAM2 pixels covered by the tracker
objects): v1's points every 10 frames + hand + held 0.92 / - (the flange point is on the hand in 57%
of the frames, so its rig object is often the hand), four rig points with a negative hand point
0.82 / 0.61, without it 0.84 / 0.66, plus the second hand point 0.90 / 0.71 (chosen). With v1's prompts (ball, flange, every 30) the tracker code reproduces v1's `glove` part
bit-identically (ep12).

Overlays (SAM2 | v1 | v2; v2 parts: rig green, tracked hand orange, held cyan, text magenta, dropped
text outlined white) were inspected on ep00 18/270, ep03 28, ep04 290, ep06 240, ep09 120/298, ep10 273,
ep12 169/255, ep13 268, ep14 292, ep16 270/300, ep20 184, ep27 297, ep28 120. Most of v1's large
wall, bin and desk-cable masks are gone (static regions in the audit: 10 instead of 73), the rig is
covered where v1 lost it (ep00, ep04, ep16, before the first ball pose in ep03), and held blocks are
covered. Static masks that touch the arm still remain in several segments: in the audit set ep09,
ep12, ep20, ep21, ep25, ep26; on frames outside it the independent check also found wall or bin
masklets in ep10, ep11, ep13, ep14 and ep27, and about 4% of frames carry more than 1% of the frame
in text-only area beyond SAM2. The mask_compare overlays of the full run will show where.

## Runtime

155-161 s per segment in the worker (scratch run, ep06 259 frames and ep12 293 frames). Over the 30
segments (dumps on the shared RTX 3090): SAM3 text 84-149 s (mean 103 s; the same computation as v1),
tracker with three objects every 10 frames 50-81 s (v1's single object every 30 frames: ~50 s on ep12),
the CPU filter ~3 s. About 85 min for 30 segments. Peak GPU memory (torch allocated): text up to 13.2
GB (ep15), tracker up to 11.0 GB; `gpu_gb` is 14.

## Open issues

- Leak rule false positives: an arm or cable masklet that grows more than 3x as the arm enters the
  view is dropped on those frames (e.g. the lower forearm and the glove cable in ep06 240, the cable
  in ep16 300); the tracked hand covers hand and upper forearm. 1.7% of the frames have less than 80%
  of SAM2's pixels covered (v1 3.8%).
- Static masklets that touch the arm are kept when they do not grow 3x: a wall or bin that is
  detected as hand/arm from its first frame (left wall in ep20 120/184), and static parts that
  touch the arm in ep09-ep14, ep21, ep25-ep27 (see the paragraph on overlays above).
- The released block: the held mask is gated off as soon as the gripper opens past 0.45, so a block
  dropping from the opening jaws is covered only when the rig object holds it (ep02 270: 0.05).
  Raising the threshold to 0.55 would cover it but also gate on during the approach of some episodes
  (open widths 0.52-0.57).
- Second hands (one audit region, ep00 18) are not covered: border seeds would add them but add
  walls more often.
- Fingertip marker cubes and thin slivers along the fingers remain the most frequent small misses.
- The judges' "held" frames ep20 184, ep26 180, ep28 120 have an open gripper or a closed one at
  rest (widths 0.68, 0.68, 0.20); the images agree with the widths, so they are counted as not held.

## Gallery

[`gallery/README.md`](gallery/README.md) ("glove7 SAM3 v2 Masks", rendered by GitHub): 120 frames of
SAM2 (exp001) against SAM3 (this experiment's `sam3_v2` masks), 4 per segment. Two are evenly spaced
(the typical frames of exp002's gallery). The other two are the frames where SAM3 and SAM2 disagree
most (lowest IoU, at least 15 frames apart). Colours: green = both, cyan = SAM2 only, magenta = SAM3
only. The page also gives the mask setups, the region-audit table and the agreement over all frames.
Rebuild it from the cache with `make_gallery.py`; its table numbers come from `stats.json`.
