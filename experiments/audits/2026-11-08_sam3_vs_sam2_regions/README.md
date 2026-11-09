# Audit: SAM3 vs SAM2 masks where they disagree (2026-11-08)

The question is which mask covers what moves on its own more accurately: hands, arms, glove
rig, its cable, a held block, and nothing static. IoU between the two masks (exp002) only
measures agreement, so this audit judges the disagreements one by one.

**Method**
- **Frames.** For each of the 30 segments, the 2 frames with the most SAM2/SAM3 disagreement,
  at least 15 frames apart: 60 frames in total. The masks are exp001's SAM2 (cache
  `masks/86471818888012b6`) and exp002's SAM3 (`masks/44820ccc66cd62ec`). See `prep.py`.
- **Regions.** Every connected region of 400 px or more that only one method masks: 159
  regions, 45 SAM2-only and 114 SAM3-only (`regions.json`).
- **Judging.** Each region was judged by two independent vision agents, which saw the original
  frame and the numbered regions. Verdicts: `moving`, `static` or `unclear` (`verdicts.json`).
  A region counts only when both agree, which they did on 154 of 159 (97%).
- **Bias.** The frames are the worst-disagreement ones, so this audit is biased towards
  failures. On typical frames the two masks agree closely (IoU median 0.93).

**Result (154 agreed regions; area = sum over regions, % of one frame)**

| finding | regions | area |
|---|---|---|
| SAM3 missed something moving (SAM2 right) | 40 | 61% |
| SAM2 missed something moving (SAM3 right) | 40 | 22% |
| SAM3 masked something static (SAM3 wrong) | 73 | 170% |
| SAM2 masked something static (SAM2 wrong) | 1 | 0.3% |

- **SAM3 misses:** the glove rig, either whole or its fine parts (fingers, marker cubes). This
  happens when the SAM3 tracker loses the rig, e.g. before the first ball-pose prompt or at the
  image edge.
- **SAM3 false positives:**
  - `cable` picks up static desk cables, such as those hanging from the PCB on the static robot;
  - `hand` / `arm` spread onto walls, tiles and the bin next to the hand.
- **SAM2 misses:** mostly the glove cable along the forearm, a second hand, and some rig parts.
- **Missed by both:** the block while it is held in the gripper, in several segments (ep06, ep12,
  ep16, ep24, ep28).
