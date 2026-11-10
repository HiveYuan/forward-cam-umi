# Scale across sessions

**What.** The current default scale and the candidate of exp009, on every glove session run so far:
- default: DA2 metric indoor + `Bsession`, the ball correction pooled per session (exp007);
- candidate: DA3 metric + K, `Bnet`, the network's depth as is, with no ball.

| session | episodes | experiments |
|---|---|---|
| glove7 | 30 | exp007 (default), exp009 (DA3) |
| glove8 | 4 | exp010 |
| glove6, take 1 | 29 (the false start ep00 left out) | exp012; exp011 failed on ep00 |

glove6 take 2 and glove5 (2 takes, 115 episodes, a different day) were not run. The user cut the
scope to two more sessions because the full set takes about 13 h of GPU. To add one, copy
exp012's config, change the `data` block to `yam_glove6_take2` or `yam_glove5_take{1,2}`, and
prepare its ground truth first (below).

[`summary.md`](summary.md) is produced by `summarize.py` (read only: each experiment's results and
analysis view). The labels are recomputed per anchor with `slam.labels.anchor_errors`, so they
pool across sessions. On glove7 alone it reproduces exp007 and exp009 exactly.

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
PYTHONPATH=. $V experiments/cross_session/summarize.py
```

## Results (61 episodes with a tile-fitted scale, 2881 label anchors)

| | scale \|err\| median / p90 | bias | episodes > 10% / > 20% | labels 1 s median / p90 | 2 s | chunk H = 100 mean |
|---|---|---|---|---|---|---|
| tile-fitted scale | - | - | - | 3.5 / 11.2 mm | 4.2 / 12.7 | 6.8 |
| default (DA2 + Bsession) | 14.2 / 26.2% | -14.2% | 38 / 22 | 7.2 / 19.8 mm | 11.4 / 30.8 | 11.7 |
| **DA3 + K, Bnet** | **4.0 / 13.2%** | **+1.3%** | **9 / 3** | **4.8 / 13.8 mm** | **6.4 / 17.6** | **8.1** |

Per session:

| session | default \|err\| median, bias | DA3 Bnet \|err\| median, bias | labels 1 s median: default / DA3 / tile-fitted |
|---|---|---|---|
| glove6 take 1 | 22.2%, -22.2% | 5.4%, +4.6% | 9.7 / 5.1 / 3.1 mm |
| glove7 | 7.8%, -7.3% | 3.1%, -0.1% | 4.5 / 4.2 / 3.9 mm |
| glove8 | 10.4%, -8.8% | 0.8%, +0.2% | 5.1 / 4.6 / 5.0 mm |

**Reading.**
- **DA3 + K without the ball is better on every session**, in scale and in labels. It needs no
  marker.
- **The default fails on glove6** (-22%) because the ball is held closer to the camera there:
  median 0.39 m, against 0.49 m in glove7. DA2's ball correction depends on distance
  (k 0.455 vs 0.566), while the background needs about the same in both (0.588 vs 0.611). Its
  error follows how the glove is held.
- **DA3's bias varies by session:** +4.6% on glove6, about 0 on glove7 and glove8. Within a
  session the spread is 5-9% (sd of log).
- **Outliers are SLAM-side.** glove8 ep02: DROID's scale drifts 40% within the episode, and
  neither method can fit one scale to it.
- **Still untested:** another day (glove5), another scene, another camera. All three sessions
  here were recorded on 2026-10-15 at the same workspace.

## Data preparation of the other sessions

- **Per-take sessions** (`slam/config.py`):
  - `yam_glove8`, and `yam_glove6_take1/2`, `yam_glove5_take1/2` (`_take1` = the `.take1` files,
    `_take2` = the plain files).
  - Their raw files are symlinked under per-take names into `<work>/takes/data/raw`. The take's
    episode file is renumbered from 0; `source_episode_index` keeps the original.
  - Run the CLI tools with `HEADCAM_DATA_REPO=<work>/takes`.
- **Ground truth** (`<work>/takes/prep_gt.sh <session>...`):
  - `scripts/detect_parallel.py` on the head stream with `--keep-27 --no-16h5`. Its 4x4 (ball)
    output is bit-identical to the run with 16h5 (checked on glove8, 4997 arrays) and 3.1x
    faster. The wrist stream keeps 16h5 for the tips.
  - `scripts/head_pose_fast.py --stride 1 --raw-dir ...` with layout v3.
  - `slam.ball_poses`, then `slam.wrist_width --write-log`.
- **Closed-jaw separation.** If a session's value is more than 2 mm off glove7's (16.94 mm, same
  unit), the widths are recomputed with `--d0-mm 16.94` (glove8 32.7 mm, glove6 take 1 20.7 mm).
  The widths matter only for the held-object mask prompts and the gripper label.
