# exp010_glove8

**What.** The current default scale and the candidate from exp009, side by side on glove8: 4 episodes, 2.4 min of footage, recorded 2026-10-15.
- Default (exp007): DA2 metric indoor + `Bsession` (ball correction pooled over the session).
- Candidate (exp009): DA3 metric + K, `Bnet` (the network's depth as is, no ball).
- Both carry the A cross-check at 10%.

The producers are as in exp006 / exp007: `sam3_v2` motion masks, tile masks, masked DROID-SLAM E3.
E3 is declared twice (`E3_da2`, `E3_da3m`). Same parameters mean one cache key and one DROID run,
but each alias gets its own scale, labels, evaluation and error decomposition.

**Why.** exp008 / exp009 chose DA3 + Bnet on one session (glove7). This run checks whether it holds
on another session. The cross-session summary is [`../cross_session/`](../cross_session/README.md).

**Data and ground truth** (`slam/config.py` session `yam_glove8`; prepared with
`<work>/takes/prep_gt.sh`, see the cross-session README):
- Raw files are symlinked under per-take names into `<work>/takes/data/raw`, with the take's episode
  file renumbered from 0 (`source_episode_index` keeps the original).
- Ground truth in `<work>/yam_glove8/gt`:
  - tile head poses (`scripts/head_pose_fast.py`, layout v3);
  - ball poses (`slam.ball_poses`);
  - wrist gripper widths (`slam.wrist_width`).

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp010_glove8/config.yaml
```

**Gripper widths.** glove8 never closes the glove empty in its 2.4 min. The session's own
closed-jaw separation (0.5th percentile, 32.7 mm) is therefore wrong. The widths use glove7's
16.94 mm instead (`slam.wrist_width --d0-mm`; same unit and day). This affects only the
held-object mask prompts and the label's gripper value.

## Results

The run took 33.9 min at 927beb0. Cross-session tables are in [`../cross_session/summary.md`](../cross_session/summary.md).

**Scale error vs the tile-fitted scale, per episode** (all 4 episodes have >= 3 tile keyframes):

| | ep00 | ep01 | ep02 | ep03 |
|---|---|---|---|---|
| default (DA2 + Bsession) | -11.1% | -9.6% | +11.1% | -7.9% |
| DA3 + K, Bnet | -0.7% | +0.9% | +20.1% | -0.5% |

**Labels at 1 s, median / p90** (249 anchors):
- DA3 + Bnet: 4.6 / 10.2 mm;
- default: 5.1 / 11.6 mm;
- tile-fitted scale: 5.0 / 19.6 mm.

**ep02 is a SLAM failure, not a depth one.** DROID's scale drifts within the episode: the
tile-fitted scale is 0.58 / 0.76 / 0.82 on its thirds, and the fit residual is 19.6 mm against
4-8 mm elsewhere. The network's per-keyframe scales follow that drift. The first keyframe also
has a wild ratio (20.7: DROID's depth at initialisation). Both methods are off on it.
