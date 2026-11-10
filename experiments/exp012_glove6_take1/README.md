# exp012_glove6_take1

**What.** The current default scale and the candidate from exp009, side by side on glove6, take 1 (`.take1` files): 29 episodes (source 1-29; ep00 left out, see below), 11.5 min, 2026-10-15.
- Default (exp007): DA2 metric indoor + `Bsession` (ball correction pooled over the session).
- Candidate (exp009): DA3 metric + K, `Bnet` (the network's depth as is, no ball).
- Both carry the A cross-check at 10%.

The producers are as in exp006 / exp007: `sam3_v2` motion masks, tile masks, masked DROID-SLAM E3.
E3 is declared twice (`E3_da2`, `E3_da3m`). Same parameters mean one cache key and one DROID run,
but each alias gets its own scale, labels, evaluation and error decomposition.

**Why.** exp008 / exp009 chose DA3 + Bnet on one session (glove7). This run checks whether it holds
on another session. The cross-session summary is [`../cross_session/`](../cross_session/README.md).

**Data and ground truth** (`slam/config.py` session `yam_glove6_take1`; prepared with
`<work>/takes/prep_gt.sh`, see the cross-session README):
- Raw files are symlinked under per-take names into `<work>/takes/data/raw`, with the take's episode
  file renumbered from 0 (`source_episode_index` keeps the original).
- Ground truth in `<work>/yam_glove6_take1/gt`:
  - tile head poses (`scripts/head_pose_fast.py`, layout v3);
  - ball poses (`slam.ball_poses`);
  - wrist gripper widths (`slam.wrist_width`).

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp012_glove6_take1/config.yaml
```

**ep00 left out.** It is the take's 1.8 s false start, with no ball pose and no tile pose. exp011
failed on it, because sam3_v2 needs a ball pose to prompt the glove.

**Gripper widths.** The session's closed-jaw separation is 20.7 mm, 3.8 mm off glove7's 16.94 mm
(same unit and day). The widths use 16.94 mm (`--d0-mm`), as for glove8.

**GPU memory.** The first invocation (see `run.json`) ran out of memory in SAM3's text tracking
on ep01: 19.1 GB, with about 3.4 GB of the card held by other users. The rerun used
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. This setting changes the allocator only, not
the results, and it is recorded in run.json.

## Results

The run took 152.4 min at 18922ab. Cross-session tables are in [`../cross_session/summary.md`](../cross_session/summary.md).

**Scale error vs the tile-fitted scale** (29 episodes, all with >= 3 tile keyframes):

| | \|err\| median / p90 | bias | spread (sd log) | episodes > 10% / > 20% |
|---|---|---|---|---|
| default (DA2 + Bsession) | 22.2 / 27.1% | -22.2% | 6.9% | 28 / 21 |
| **DA3 + K, Bnet** | **5.4 / 13.2%** | +4.6% | 6.4% | 5 / 1 |

**Labels, position error** (1643 anchors; median / p90):

| | 1 s | 2 s | chunk H = 100 mean |
|---|---|---|---|
| tile-fitted scale | 3.1 / 9.1 mm | 3.5 / 9.2 mm | 4.9 mm |
| default | 9.7 / 21.7 mm | 15.8 / 37.1 mm | 13.3 mm |
| **DA3 + Bnet** | **5.1 / 13.7 mm** | **7.5 / 18.3 mm** | **7.6 mm** |

**Why the default fails here: the ball is held closer to the camera.**
- Ball depth median: 0.39 m here, against 0.49 m in glove7.
- DA2's over-estimate grows towards the camera, so the ball's correction drops to k = 0.455
  (glove7 0.566).
- What the background needs is about the same in both sessions: 0.588 here, 0.611 in glove7.

The default's error therefore follows how the collector holds the glove. DA3 + Bnet does not use
the ball. Its bias here is +4.6%, against about 0 on glove7, and that difference is its
session-to-session variation.
