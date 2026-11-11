# exp014_glove5_take1

**What.** The current defaults (`experiments/README.md`, "Current defaults") on glove5 take 1: source episodes 0-48 (49 episodes, 26 min), recorded 2026-10-08:
`sam3_v2` motion masks, tile masks, masked DROID-SLAM E3, scale `Bnet` on DA3 metric + K (no ball)
with the A check at 10%. Producer parameters are exp012's; only the default scale is run.

**Why.** The relative-pose datasets use all four glove sessions, as the paper's
`pilot_glove_HHs3` does (decision 2026-11-10: align with the paper). glove8, glove7 and glove6
take 1 already have SLAM runs (exp010, exp009, exp012). This run covers the first part of HHs3's glove5 segments (83-199).

**Data and ground truth** (`slam/config.py` session `yam_glove5_take1`): raw files symlinked into
`<work>/takes/data/raw` with the take's episode file renumbered from 0 (`source_episode_index` keeps
the original); ground truth in `<work>/yam_glove5_take1/gt` from `<work>/takes/prep_gt.sh` (tile head poses
with layout v3, ball poses, wrist widths; closed-jaw separation overridden with glove7's 16.94 mm if
the take's own is more than 2 mm off, as for glove8 and glove6 take 1).

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp014_glove5_take1/config.yaml
```
