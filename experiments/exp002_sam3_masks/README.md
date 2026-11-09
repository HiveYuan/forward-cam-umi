# exp002_sam3_masks

**What.** SAM3 motion masks on yam_glove7, compared with exp001's SAM2 masks: per-frame IoU,
coverage of SAM2's pixels, area SAM3 adds or misses, agreement of the DROID-invalid cells after
the 8 px dilation, and overlay images (in `<work>/runs/exp002_sam3_masks/main/overlays/`).

**Why.** Decision of 2026-11-08: SAM3 replaces SAM2 because it takes text prompts natively.
The mask principle is unchanged: mask only what moves on its own, with no colour or
object-specific rules.

**Masks (`sam3_text_points`, decided with the user on 2026-11-08):**
- **Text prompts:** `hand`, `arm`, `cable`. These are open-vocabulary body parts.
- **SAM3 tracker point prompts** for the glove rig (ball, handle, gripper fingers) and the object
  while it is held. The points are given in the glove body frame (ball centre, flange point) and
  projected with the per-frame ball pose every 30 frames, as in SAM2. A prompt sweep found that
  SAM3's text prompts do not detect this custom rig: `glove`, `gripper`, `robot gripper`,
  `handheld gripper`, `tool held in hand` and `held object` found nothing. `black device` found
  it but also the static robot arm.
- **Post-processing:** SAM3's official NMS and hole filling, which needs the hub kernel
  `kernels-community/cv-utils`, torch 2.10 in the `sam3` env.

```
HF_TOKEN_PATH=~/.config/yuanliu/hf_token $V -m slam.run experiments/exp002_sam3_masks/config.yaml
```

**Result (2026-11-08, commit 3e1c086).**
- Over 8972 frames: IoU with SAM2 median 0.93 (p10 0.72), SAM2 pixels covered 0.97, DROID-cell
  IoU 0.97 (p10 0.69).
- Agreement is not accuracy. The region-by-region audit of the 60 most-disagreeing frames
  (`experiments/audits/2026-11-08_sam3_vs_sam2_regions/`) shows where SAM3 goes wrong:
  - it misses the glove rig, or its fine parts, where its tracker loses it;
  - `cable` and `hand`/`arm` cover static things: desk cables, walls, tiles, the bin.
- SAM3 does cover the glove cable and a second hand better.
- Neither method reliably covers a block while it is held.
