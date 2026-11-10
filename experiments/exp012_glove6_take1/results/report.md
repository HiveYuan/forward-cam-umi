# exp012_glove6_take1: report (variant main)

29 segments. Runs: E1, E3_da2, E3_da3m (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.50 / 1.39 | 2.83 / 7.41 | 5.17 / 11.09 | 7.62 / 16.76 | 12.55 / 17.87 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3_da2 | 0.15 / 0.54 | 0.29 / 1.01 | 0.32 / 1.05 | 0.36 / 1.03 | 0.41 / 1.28 |
| E3_da3m | 0.15 / 0.54 | 0.29 / 1.01 | 0.32 / 1.05 | 0.36 / 1.03 | 0.41 / 1.28 |

n [frame pairs]:

- static, E3_da2, E3_da3m: 0.08 s: 3485, 0.5 s: 2927, 1.0 s: 2454, 2.0 s: 1704, 6.67 s: 213
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3_da2 | oracle (tiles) | 2.32 / 8.61 | 4.55 / 17.35 | 5.13 / 17.59 | 5.67 / 15.93 | 7.17 / 20.36 |
| E3_da2 | Bsession+Acheck | 2.51 / 8.67 | 7.24 / 20.81 | 11.47 / 29.34 | 17.79 / 48.51 | 27.98 / 46.82 |
| E3_da3m | oracle (tiles) | 2.32 / 8.61 | 4.55 / 17.35 | 5.13 / 17.59 | 5.67 / 15.93 | 7.17 / 20.36 |
| E3_da3m | Bnet+Acheck | 2.40 / 8.75 | 5.26 / 17.99 | 6.82 / 21.20 | 8.98 / 21.74 | 11.58 / 30.51 |

n [frame pairs]: 0.08 s: 3485, 0.5 s: 2927, 1.0 s: 2454, 2.0 s: 1704, 6.67 s: 213

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 18.1 | 56 | 100% |
| E3_da2 | 0.26% | 16.3 | 59 | 86% |
| E3_da3m | 0.26% | 16.3 | 59 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3_da2 | Bsession+Acheck (flag \|check/primary - 1\| > 10%) | 29/29 | 29 | 22.2% | 27.1% | -22.2% | ep02, ep04, ep05, ep09, ep14, ep23 |
| E3_da2 | Bsession+Acheck, without flagged | 23/29 | 23 | 21.9% | 27.2% | -21.9% |  |
| E3_da2 | Bsession+Acheck, method Bsession (primary) | 29/29 | 29 | 22.2% | 27.1% | -22.2% |  |
| E3_da2 | Bsession+Acheck, method A (check) | 8/29 | 8 | 12.1% | 36.8% | -12.1% |  |
| E3_da3m | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 29/29 | 29 | 5.4% | 13.2% | 4.6% | ep06, ep14, ep19, ep23 |
| E3_da3m | Bnet+Acheck, without flagged | 25/29 | 25 | 6.1% | 13.3% | 5.8% |  |
| E3_da3m | Bnet+Acheck, method Bnet (primary) | 29/29 | 29 | 5.4% | 13.2% | 4.6% |  |
| E3_da3m | Bnet+Acheck, method A (check) | 8/29 | 8 | 12.1% | 36.8% | -12.1% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | oracle (tiles) | 1643 | 1.1 / 3.3 | 1.5 / 4.9 | 2.1 / 6.6 | 2.7 / 8.0 | 3.1 / 9.1 | 3.5 / 9.2 | 4.3 / 9.7 | 4.4 / 8.3 |
| E3_da2 | Bsession+Acheck | 1643 | 1.3 / 3.6 | 2.1 / 5.7 | 3.4 / 9.2 | 5.8 / 13.9 | 9.7 / 21.7 | 15.8 / 37.1 | 17.2 / 44.4 | 23.1 / 31.5 |
| E3_da3m | oracle (tiles) | 1643 | 1.1 / 3.3 | 1.5 / 4.9 | 2.1 / 6.6 | 2.7 / 8.0 | 3.1 / 9.1 | 3.5 / 9.2 | 4.3 / 9.7 | 4.4 / 8.3 |
| E3_da3m | Bnet+Acheck | 1643 | 1.2 / 3.5 | 1.7 / 5.2 | 2.5 / 7.3 | 3.7 / 9.7 | 5.1 / 13.7 | 7.5 / 18.3 | 9.3 / 22.8 | 9.7 / 15.2 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | every scale | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| E3_da3m | every scale | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3_da2 | anchors | 1619 | 1624 | 1624 | 1624 |
| E3_da2 | counted steps per anchor, median | 15 | 30 | 35 | 43 |
| E3_da2 | position [mm], oracle (tiles), mean / median | 3.7 / 2.9 | 4.3 / 3.5 | 4.6 / 3.8 | 4.9 / 4.0 |
| E3_da2 | position [mm], Bsession+Acheck, mean / median | 6.7 / 5.6 | 10.1 / 8.2 | 12.7 / 10.0 | 13.3 / 10.4 |
| E3_da2 | rotation [deg], every scale, mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| E3_da3m | anchors | 1619 | 1624 | 1624 | 1624 |
| E3_da3m | counted steps per anchor, median | 15 | 30 | 35 | 43 |
| E3_da3m | position [mm], oracle (tiles), mean / median | 3.7 / 2.9 | 4.3 / 3.5 | 4.6 / 3.8 | 4.9 / 4.0 |
| E3_da3m | position [mm], Bnet+Acheck, mean / median | 4.7 / 3.8 | 6.2 / 5.2 | 7.2 / 6.1 | 7.6 / 6.4 |
| E3_da3m | rotation [deg], every scale, mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3_da2, H=100: 43 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 265 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 678 | 0.14 / 0.44 | 2.2 / 7.0 |
| same tiles, dt 0.5 s | 462 | 0.22 / 1.14 | 3.6 / 14.2 |
| same tiles, dt 1.0 s | 297 | 0.27 / 0.93 | 4.2 / 11.7 |
| same tiles, dt 2.0 s | 174 | 0.24 / 1.19 | 3.5 / 23.2 |
| tile set changes between the ends | 795 | 0.44 / 2.06 | 6.4 / 36.4 |

## Error decomposition, run E3_da2: SLAM or tile head rotation x configured or oracle scale

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3_da2 rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bsession+Acheck) or the per-segment tile oracle (`errdecomp_E3_da2.json`). (1) SLAM rot + Bsession+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bsession+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bsession+Acheck s 9.7, (2) SLAM rot + oracle s 3.1, (3) tile rot + Bsession+Acheck s 11.1, (4) tile rot + oracle s 5.1 mm; chunk H=30 position mean: (1) SLAM rot + Bsession+Acheck s 10.1, (2) SLAM rot + oracle s 4.3, (3) tile rot + Bsession+Acheck s 11.6, (4) tile rot + oracle s 6.5 mm.

### Error decomposition, E3_da2: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 1643 | 1.3 / 3.6 | 2.1 / 5.7 | 3.4 / 9.2 | 5.8 / 13.9 | 9.7 / 21.7 | 15.8 / 37.1 | 17.2 / 44.4 | 23.1 / 31.5 |
| (2) SLAM rot + oracle s | 1643 | 1.1 / 3.3 | 1.5 / 4.9 | 2.1 / 6.6 | 2.7 / 8.0 | 3.1 / 9.1 | 3.5 / 9.2 | 4.3 / 9.7 | 4.4 / 8.3 |
| (3) tile rot + Bsession+Acheck s | 1643 | 2.1 / 5.4 | 3.1 / 8.3 | 4.7 / 11.7 | 7.3 / 16.7 | 11.1 / 23.8 | 17.0 / 38.0 | 19.3 / 45.5 | 23.4 / 32.4 |
| (4) tile rot + oracle s | 1643 | 2.0 / 5.5 | 2.6 / 7.6 | 3.6 / 10.2 | 4.6 / 12.3 | 5.1 / 14.0 | 5.8 / 14.0 | 7.7 / 16.3 | 8.5 / 16.6 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

### Error decomposition, E3_da2: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| (2) SLAM rot + oracle s | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| (3) tile rot + Bsession+Acheck s | 1643 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 1643 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

### Error decomposition, E3_da2: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | anchors | 1619 | 1624 | 1624 | 1624 |
| (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 6.7 / 5.6 | 10.1 / 8.2 | 12.7 / 10.0 | 13.3 / 10.4 |
| (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| (2) SLAM rot + oracle s | anchors | 1619 | 1624 | 1624 | 1624 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 3.7 / 2.9 | 4.3 / 3.5 | 4.6 / 3.8 | 4.9 / 4.0 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| (3) tile rot + Bsession+Acheck s | anchors | 1619 | 1624 | 1624 | 1624 |
| (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 8.2 / 7.1 | 11.6 / 10.0 | 14.2 / 11.8 | 15.0 / 12.3 |
| (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 |
| (4) tile rot + oracle s | anchors | 1619 | 1624 | 1624 | 1624 |
| (4) tile rot + oracle s | position [mm], mean / median | 5.7 / 4.7 | 6.5 / 5.5 | 7.1 / 6.0 | 7.5 / 6.5 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 |

### Error decomposition, E3_da2: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 1222, 10-30 240, 30+ 0, unknown 181; oracle scale: 0-10 1222, 10-30 240, 30+ 0, unknown 181; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | 1222 | 1.2 / 3.1 | 1.9 / 4.7 | 3.1 / 7.7 | 5.4 / 12.9 | 9.0 / 20.9 | 15.7 / 36.2 | 17.3 / 44.6 | 23.1 / 31.5 |
| 0-10 | (2) SLAM rot + oracle s | 1222 | 1.0 / 2.8 | 1.4 / 4.0 | 1.8 / 5.4 | 2.5 / 6.9 | 2.8 / 7.4 | 3.3 / 8.0 | 4.0 / 9.1 | 4.4 / 8.3 |
| 0-10 | (3) tile rot + Bsession+Acheck s | 1222 | 2.0 / 4.9 | 2.9 / 6.8 | 4.2 / 10.0 | 6.7 / 15.6 | 10.6 / 23.1 | 16.9 / 37.5 | 18.5 / 45.5 | 23.4 / 32.4 |
| 0-10 | (4) tile rot + oracle s | 1222 | 1.8 / 4.8 | 2.4 / 6.7 | 3.2 / 8.7 | 4.2 / 11.4 | 4.6 / 12.0 | 5.5 / 12.5 | 7.6 / 15.0 | 8.5 / 16.6 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | 240 | 1.7 / 5.3 | 3.1 / 8.8 | 5.3 / 12.9 | 8.0 / 20.8 | 12.6 / 24.5 | 17.3 / 27.9 | 26.0 / 36.9 | - |
| 10-30 | (2) SLAM rot + oracle s | 240 | 1.3 / 4.4 | 2.3 / 7.6 | 3.2 / 11.5 | 4.5 / 13.3 | 6.5 / 15.9 | 6.1 / 15.2 | 7.8 / 9.9 | - |
| 10-30 | (3) tile rot + Bsession+Acheck s | 240 | 2.4 / 6.7 | 4.5 / 10.4 | 7.7 / 16.0 | 10.5 / 21.5 | 13.7 / 26.0 | 20.0 / 34.1 | 27.2 / 40.1 | - |
| 10-30 | (4) tile rot + oracle s | 240 | 2.3 / 6.4 | 4.1 / 9.9 | 6.0 / 13.7 | 7.6 / 15.8 | 10.1 / 19.3 | 9.5 / 23.4 | 14.2 / 18.5 | - |
| 30+ | (1) SLAM rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | 1222 | 0.12 / 0.31 | 0.16 / 0.43 | 0.21 / 0.56 | 0.27 / 0.74 | 0.29 / 0.79 | 0.35 / 0.83 | 0.48 / 1.07 | 0.50 / 1.13 |
| 0-10 | (2) SLAM rot + oracle s | 1222 | 0.12 / 0.31 | 0.16 / 0.43 | 0.21 / 0.56 | 0.27 / 0.74 | 0.29 / 0.79 | 0.35 / 0.83 | 0.48 / 1.07 | 0.50 / 1.13 |
| 0-10 | (3) tile rot + Bsession+Acheck s | 1222 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 1222 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | 240 | 0.14 / 0.41 | 0.25 / 0.61 | 0.37 / 0.87 | 0.44 / 1.09 | 0.55 / 1.17 | 0.59 / 1.73 | 0.91 / 1.13 | - |
| 10-30 | (2) SLAM rot + oracle s | 240 | 0.14 / 0.41 | 0.25 / 0.61 | 0.37 / 0.87 | 0.44 / 1.09 | 0.55 / 1.17 | 0.59 / 1.73 | 0.91 / 1.13 | - |
| 10-30 | (3) tile rot + Bsession+Acheck s | 240 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - |
| 10-30 | (4) tile rot + oracle s | 240 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - |
| 30+ | (1) SLAM rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 6.3 / 5.4 | 10.0 / 8.1 | 13.1 / 10.5 | 13.8 / 10.8 |
| 0-10 | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.35 / 0.28 | 0.41 / 0.34 | 0.45 / 0.38 | 0.49 / 0.43 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 3.1 / 2.5 | 3.6 / 3.1 | 4.0 / 3.5 | 4.3 / 3.8 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.35 / 0.28 | 0.41 / 0.34 | 0.45 / 0.38 | 0.49 / 0.43 |
| 0-10 | (3) tile rot + Bsession+Acheck s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 7.9 / 6.8 | 11.5 / 9.8 | 14.6 / 12.0 | 15.5 / 12.5 |
| 0-10 | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.03 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 5.2 / 4.2 | 5.9 / 5.0 | 6.5 / 5.6 | 7.0 / 6.2 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.03 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 8.8 / 7.4 | 10.8 / 9.1 | 11.5 / 9.8 | 12.0 / 10.0 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.57 / 0.45 | 0.64 / 0.53 | 0.67 / 0.54 | 0.67 / 0.54 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 5.7 / 4.8 | 6.5 / 5.6 | 6.8 / 5.8 | 6.8 / 5.8 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.57 / 0.45 | 0.64 / 0.53 | 0.67 / 0.54 | 0.67 / 0.54 |
| 10-30 | (3) tile rot + Bsession+Acheck s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 10.5 / 9.2 | 12.7 / 11.1 | 13.5 / 12.5 | 14.1 / 12.7 |
| 10-30 | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.10 / 0.00 | 0.11 / 0.00 | 0.12 / 0.00 | 0.11 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 8.1 / 7.1 | 9.3 / 8.5 | 9.7 / 8.7 | 9.8 / 8.7 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.10 / 0.00 | 0.11 / 0.00 | 0.12 / 0.00 | 0.11 / 0.00 |
| 30+ | (1) SLAM rot + Bsession+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (2) SLAM rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (4) tile rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | rotation [deg], mean / median | - | - | - | - |

### Error decomposition, E3_da2: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.1 / 2.8 | 1.5 / 4.2 | 2.0 / 5.6 | 2.5 / 6.6 | 2.7 / 7.5 | 3.3 / 7.5 | 4.3 / 9.3 | 4.7 / 10.7 |
| translation part dt [mm], Bsession+Acheck s, median / p90 | 2.1 / 5.2 | 3.1 / 8.0 | 4.6 / 11.6 | 7.2 / 16.5 | 11.0 / 23.8 | 16.8 / 38.0 | 19.0 / 45.5 | 23.4 / 32.4 |
| translation part dt [mm], oracle s, median / p90 | 2.0 / 5.1 | 2.6 / 7.4 | 3.5 / 9.8 | 4.5 / 12.1 | 5.1 / 13.7 | 5.7 / 13.4 | 7.7 / 16.1 | 8.5 / 16.6 |
| cos(dR b, dt), Bsession+Acheck s, median | -0.88 | -0.83 | -0.78 | -0.70 | -0.58 | -0.45 | -0.56 | -0.44 |
| cos(dR b, dt), oracle s, median | -0.93 | -0.92 | -0.91 | -0.90 | -0.89 | -0.88 | -0.91 | -0.96 |

Checks: (1) SLAM rot + Bsession+Acheck s vs `labels_E3_da2@Bsession+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3_da2.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 72521 pairs): max |position difference| 5.0e-13 mm, max |R difference| 2.2e-15; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 72521 pairs): max |position difference| 5.6e-13 mm, max |R difference| 2.2e-15.

## Error decomposition, run E3_da3m: SLAM or tile head rotation x configured or oracle scale

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3_da3m rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bnet+Acheck) or the per-segment tile oracle (`errdecomp_E3_da3m.json`). (1) SLAM rot + Bnet+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bnet+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bnet+Acheck s 5.1, (2) SLAM rot + oracle s 3.1, (3) tile rot + Bnet+Acheck s 6.9, (4) tile rot + oracle s 5.1 mm; chunk H=30 position mean: (1) SLAM rot + Bnet+Acheck s 6.2, (2) SLAM rot + oracle s 4.3, (3) tile rot + Bnet+Acheck s 8.1, (4) tile rot + oracle s 6.5 mm.

### Error decomposition, E3_da3m: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 1643 | 1.2 / 3.5 | 1.7 / 5.2 | 2.5 / 7.3 | 3.7 / 9.7 | 5.1 / 13.7 | 7.5 / 18.3 | 9.3 / 22.8 | 9.7 / 15.2 |
| (2) SLAM rot + oracle s | 1643 | 1.1 / 3.3 | 1.5 / 4.9 | 2.1 / 6.6 | 2.7 / 8.0 | 3.1 / 9.1 | 3.5 / 9.2 | 4.3 / 9.7 | 4.4 / 8.3 |
| (3) tile rot + Bnet+Acheck s | 1643 | 2.0 / 5.6 | 2.8 / 7.8 | 3.8 / 10.5 | 5.3 / 13.2 | 6.9 / 17.9 | 9.2 / 19.7 | 12.1 / 24.7 | 12.5 / 24.5 |
| (4) tile rot + oracle s | 1643 | 2.0 / 5.5 | 2.6 / 7.6 | 3.6 / 10.2 | 4.6 / 12.3 | 5.1 / 14.0 | 5.8 / 14.0 | 7.7 / 16.3 | 8.5 / 16.6 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

### Error decomposition, E3_da3m: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| (2) SLAM rot + oracle s | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| (3) tile rot + Bnet+Acheck s | 1643 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 1643 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

### Error decomposition, E3_da3m: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | anchors | 1619 | 1624 | 1624 | 1624 |
| (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 4.7 / 3.8 | 6.2 / 5.2 | 7.2 / 6.1 | 7.6 / 6.4 |
| (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| (2) SLAM rot + oracle s | anchors | 1619 | 1624 | 1624 | 1624 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 3.7 / 2.9 | 4.3 / 3.5 | 4.6 / 3.8 | 4.9 / 4.0 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| (3) tile rot + Bnet+Acheck s | anchors | 1619 | 1624 | 1624 | 1624 |
| (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 6.5 / 5.4 | 8.1 / 6.9 | 9.2 / 8.2 | 9.7 / 8.6 |
| (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 |
| (4) tile rot + oracle s | anchors | 1619 | 1624 | 1624 | 1624 |
| (4) tile rot + oracle s | position [mm], mean / median | 5.7 / 4.7 | 6.5 / 5.5 | 7.1 / 6.0 | 7.5 / 6.5 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 |

### Error decomposition, E3_da3m: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 1222, 10-30 240, 30+ 0, unknown 181; oracle scale: 0-10 1222, 10-30 240, 30+ 0, unknown 181; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 1222 | 1.1 / 3.0 | 1.5 / 4.2 | 2.2 / 6.0 | 3.4 / 8.4 | 4.6 / 11.3 | 7.2 / 17.9 | 8.7 / 22.9 | 9.7 / 15.2 |
| 0-10 | (2) SLAM rot + oracle s | 1222 | 1.0 / 2.8 | 1.4 / 4.0 | 1.8 / 5.4 | 2.5 / 6.9 | 2.8 / 7.4 | 3.3 / 8.0 | 4.0 / 9.1 | 4.4 / 8.3 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 1222 | 2.0 / 4.9 | 2.5 / 6.8 | 3.5 / 8.9 | 4.8 / 12.2 | 6.2 / 14.6 | 8.7 / 19.1 | 11.7 / 24.8 | 12.5 / 24.5 |
| 0-10 | (4) tile rot + oracle s | 1222 | 1.8 / 4.8 | 2.4 / 6.7 | 3.2 / 8.7 | 4.2 / 11.4 | 4.6 / 12.0 | 5.5 / 12.5 | 7.6 / 15.0 | 8.5 / 16.6 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 240 | 1.6 / 4.5 | 2.8 / 7.5 | 4.4 / 11.5 | 7.3 / 17.4 | 10.6 / 21.6 | 11.7 / 31.2 | 10.4 / 15.7 | - |
| 10-30 | (2) SLAM rot + oracle s | 240 | 1.3 / 4.4 | 2.3 / 7.6 | 3.2 / 11.5 | 4.5 / 13.3 | 6.5 / 15.9 | 6.1 / 15.2 | 7.8 / 9.9 | - |
| 10-30 | (3) tile rot + Bnet+Acheck s | 240 | 2.5 / 6.5 | 4.4 / 9.9 | 6.5 / 14.3 | 9.1 / 20.2 | 12.2 / 25.6 | 13.5 / 35.1 | 15.7 / 21.0 | - |
| 10-30 | (4) tile rot + oracle s | 240 | 2.3 / 6.4 | 4.1 / 9.9 | 6.0 / 13.7 | 7.6 / 15.8 | 10.1 / 19.3 | 9.5 / 23.4 | 14.2 / 18.5 | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 1222 | 0.12 / 0.31 | 0.16 / 0.43 | 0.21 / 0.56 | 0.27 / 0.74 | 0.29 / 0.79 | 0.35 / 0.83 | 0.48 / 1.07 | 0.50 / 1.13 |
| 0-10 | (2) SLAM rot + oracle s | 1222 | 0.12 / 0.31 | 0.16 / 0.43 | 0.21 / 0.56 | 0.27 / 0.74 | 0.29 / 0.79 | 0.35 / 0.83 | 0.48 / 1.07 | 0.50 / 1.13 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 1222 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 1222 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 240 | 0.14 / 0.41 | 0.25 / 0.61 | 0.37 / 0.87 | 0.44 / 1.09 | 0.55 / 1.17 | 0.59 / 1.73 | 0.91 / 1.13 | - |
| 10-30 | (2) SLAM rot + oracle s | 240 | 0.14 / 0.41 | 0.25 / 0.61 | 0.37 / 0.87 | 0.44 / 1.09 | 0.55 / 1.17 | 0.59 / 1.73 | 0.91 / 1.13 | - |
| 10-30 | (3) tile rot + Bnet+Acheck s | 240 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - |
| 10-30 | (4) tile rot + oracle s | 240 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 4.0 / 3.4 | 5.6 / 4.7 | 6.7 / 5.6 | 7.3 / 6.1 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.35 / 0.28 | 0.41 / 0.34 | 0.45 / 0.38 | 0.49 / 0.43 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 3.1 / 2.5 | 3.6 / 3.1 | 4.0 / 3.5 | 4.3 / 3.8 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.35 / 0.28 | 0.41 / 0.34 | 0.45 / 0.38 | 0.49 / 0.43 |
| 0-10 | (3) tile rot + Bnet+Acheck s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 5.8 / 4.8 | 7.4 / 6.4 | 8.7 / 7.7 | 9.4 / 8.3 |
| 0-10 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.03 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 5.2 / 4.2 | 5.9 / 5.0 | 6.5 / 5.6 | 7.0 / 6.2 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.03 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 7.6 / 6.8 | 9.1 / 8.1 | 9.4 / 8.4 | 9.4 / 8.4 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.57 / 0.45 | 0.64 / 0.53 | 0.67 / 0.54 | 0.67 / 0.54 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 5.7 / 4.8 | 6.5 / 5.6 | 6.8 / 5.8 | 6.8 / 5.8 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.57 / 0.45 | 0.64 / 0.53 | 0.67 / 0.54 | 0.67 / 0.54 |
| 10-30 | (3) tile rot + Bnet+Acheck s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 9.7 / 8.9 | 11.4 / 10.2 | 11.9 / 10.4 | 11.9 / 10.6 |
| 10-30 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.10 / 0.00 | 0.11 / 0.00 | 0.12 / 0.00 | 0.11 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 8.1 / 7.1 | 9.3 / 8.5 | 9.7 / 8.7 | 9.8 / 8.7 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.10 / 0.00 | 0.11 / 0.00 | 0.12 / 0.00 | 0.11 / 0.00 |
| 30+ | (1) SLAM rot + Bnet+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (2) SLAM rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (4) tile rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | rotation [deg], mean / median | - | - | - | - |

### Error decomposition, E3_da3m: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.1 / 2.8 | 1.5 / 4.2 | 2.0 / 5.6 | 2.5 / 6.6 | 2.7 / 7.5 | 3.3 / 7.5 | 4.3 / 9.3 | 4.7 / 10.7 |
| translation part dt [mm], Bnet+Acheck s, median / p90 | 2.0 / 5.2 | 2.8 / 7.5 | 3.8 / 10.2 | 5.3 / 13.0 | 6.8 / 17.3 | 9.1 / 19.4 | 12.0 / 24.2 | 12.5 / 24.5 |
| translation part dt [mm], oracle s, median / p90 | 2.0 / 5.1 | 2.6 / 7.4 | 3.5 / 9.8 | 4.5 / 12.1 | 5.1 / 13.7 | 5.7 / 13.4 | 7.7 / 16.1 | 8.5 / 16.6 |
| cos(dR b, dt), Bnet+Acheck s, median | -0.91 | -0.89 | -0.86 | -0.81 | -0.71 | -0.63 | -0.67 | -0.84 |
| cos(dR b, dt), oracle s, median | -0.93 | -0.92 | -0.91 | -0.90 | -0.89 | -0.88 | -0.91 | -0.96 |

Checks: (1) SLAM rot + Bnet+Acheck s vs `labels_E3_da3m@Bnet+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3_da3m.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 72521 pairs): max |position difference| 6.7e-13 mm, max |R difference| 2.2e-15; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 72521 pairs): max |position difference| 5.6e-13 mm, max |R difference| 2.2e-15.

## Comparison with other experiments

- exp007_v2_session_scale: `exp007_v2_session_scale/results/metrics.json`
- exp009_net_scale: `exp009_net_scale/results/metrics.json`
- runs only in exp007_v2_session_scale (not shown): E3
- runs only in exp009_net_scale (not shown): E3_uniK, E3_m3d, E3_moge

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp012_glove6_take1 n | exp012_glove6_take1 median | exp012_glove6_take1 p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| static | 0.08 | 3485 | 0.50 | 1.39 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 2927 | 2.83 | 7.41 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 2454 | 5.17 | 11.09 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 1704 | 7.62 | 16.76 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 213 | 12.55 | 17.87 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - | - | - | - |
| E3_da2 | 0.08 | 3485 | 0.15 | 0.54 | - | - | - | - | - | - |
| E3_da2 | 0.5 | 2927 | 0.29 | 1.01 | - | - | - | - | - | - |
| E3_da2 | 1.0 | 2454 | 0.32 | 1.05 | - | - | - | - | - | - |
| E3_da2 | 2.0 | 1704 | 0.36 | 1.03 | - | - | - | - | - | - |
| E3_da2 | 6.67 | 213 | 0.41 | 1.28 | - | - | - | - | - | - |
| E3_da3m | 0.08 | 3485 | 0.15 | 0.54 | - | - | - | 2380 | 0.16 | 0.64 |
| E3_da3m | 0.5 | 2927 | 0.29 | 1.01 | - | - | - | 1931 | 0.36 | 1.49 |
| E3_da3m | 1.0 | 2454 | 0.32 | 1.05 | - | - | - | 1612 | 0.52 | 2.25 |
| E3_da3m | 2.0 | 1704 | 0.36 | 1.03 | - | - | - | 1248 | 0.65 | 2.60 |
| E3_da3m | 6.67 | 213 | 0.41 | 1.28 | - | - | - | 88 | 0.58 | 1.26 |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp012_glove6_take1 n | exp012_glove6_take1 median | exp012_glove6_take1 p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - | - | - | - |
| E3_da2 | oracle | 0.08 | 3485 | 2.32 | 8.61 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.5 | 2927 | 4.55 | 17.35 | - | - | - | - | - | - |
| E3_da2 | oracle | 1.0 | 2454 | 5.13 | 17.59 | - | - | - | - | - | - |
| E3_da2 | oracle | 2.0 | 1704 | 5.67 | 15.93 | - | - | - | - | - | - |
| E3_da2 | oracle | 6.67 | 213 | 7.17 | 20.36 | - | - | - | - | - | - |
| E3_da2 | configured | 0.08 | 3485 | 2.51 | 8.67 | - | - | - | - | - | - |
| E3_da2 | configured | 0.5 | 2927 | 7.24 | 20.81 | - | - | - | - | - | - |
| E3_da2 | configured | 1.0 | 2454 | 11.47 | 29.34 | - | - | - | - | - | - |
| E3_da2 | configured | 2.0 | 1704 | 17.79 | 48.51 | - | - | - | - | - | - |
| E3_da2 | configured | 6.67 | 213 | 27.98 | 46.82 | - | - | - | - | - | - |
| E3_da3m | oracle | 0.08 | 3485 | 2.32 | 8.61 | - | - | - | 2371 | 2.49 | 10.13 |
| E3_da3m | oracle | 0.5 | 2927 | 4.55 | 17.35 | - | - | - | 1931 | 5.47 | 24.24 |
| E3_da3m | oracle | 1.0 | 2454 | 5.13 | 17.59 | - | - | - | 1612 | 7.46 | 36.49 |
| E3_da3m | oracle | 2.0 | 1704 | 5.67 | 15.93 | - | - | - | 1248 | 9.87 | 46.80 |
| E3_da3m | oracle | 6.67 | 213 | 7.17 | 20.36 | - | - | - | 88 | 10.15 | 16.47 |
| E3_da3m | configured | 0.08 | 3485 | 2.40 | 8.75 | - | - | - | 2380 | 2.48 | 10.02 |
| E3_da3m | configured | 0.5 | 2927 | 5.26 | 17.99 | - | - | - | 1931 | 5.47 | 24.29 |
| E3_da3m | configured | 1.0 | 2454 | 6.82 | 21.20 | - | - | - | 1612 | 7.81 | 36.32 |
| E3_da3m | configured | 2.0 | 1704 | 8.98 | 21.74 | - | - | - | 1248 | 10.37 | 45.44 |
| E3_da3m | configured | 6.67 | 213 | 11.58 | 30.51 | - | - | - | 88 | 9.69 | 17.96 |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp012_glove6_take1 | exp007_v2_session_scale | exp009_net_scale |
|---|---|---|---|---|
| E1 | track fail | - | - | - |
| E1 | keyframes / segment | 18.1 | 14.2 | 14.2 |
| E1 | runtime s / segment | 56 | 43 | 43 |
| E1 | valid pixels | 100% | 100% | 100% |
| E3_da2 | track fail | 0.26% | - | - |
| E3_da2 | keyframes / segment | 16.3 | - | - |
| E3_da2 | runtime s / segment | 59 | - | - |
| E3_da2 | valid pixels | 86% | - | - |
| E3_da3m | track fail | 0.26% | - | 0.17% |
| E3_da3m | keyframes / segment | 16.3 | - | 12.8 |
| E3_da3m | runtime s / segment | 59 | - | 47 |
| E3_da3m | valid pixels | 86% | - | 86% |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp012_glove6_take1 | exp007_v2_session_scale | exp009_net_scale |
|---|---|---|---|---|
| E3_da2 | scale label | Bsession+Acheck | - | - |
| E3_da2 | segments with a scale | 29/29 | - | - |
| E3_da2 | compared (tile GT) | 29 | - | - |
| E3_da2 | abs err median | 22.2% | - | - |
| E3_da2 | abs err p90 | 27.1% | - | - |
| E3_da2 | bias (median) | -22.2% | - | - |
| E3_da2 | flagged | ep02, ep04, ep05, ep09, ep14, ep23 | - | - |
| E3_da2 | without flagged: abs err median / p90 | 21.9% / 27.2% | - | - |
| E3_da2 | method Bsession: segments ok, n: abs err median / p90 / bias | 29/29, n 29: 22.2% / 27.1% / -22.2% | - | - |
| E3_da2 | method A: segments ok, n: abs err median / p90 / bias | 8/29, n 8: 12.1% / 36.8% / -12.1% | - | - |
| E3_da3m | scale label | Bnet+Acheck | - | Bnet+Acheck |
| E3_da3m | segments with a scale | 29/29 | - | 30/30 |
| E3_da3m | compared (tile GT) | 29 | - | 28 |
| E3_da3m | abs err median | 5.4% | - | 3.1% |
| E3_da3m | abs err p90 | 13.2% | - | 9.4% |
| E3_da3m | bias (median) | 4.6% | - | -0.1% |
| E3_da3m | flagged | ep06, ep14, ep19, ep23 | - | ep01, ep09, ep19, ep20, ep28, ep29 |
| E3_da3m | without flagged: abs err median / p90 | 6.1% / 13.3% | - | 3.0% / 6.9% |
| E3_da3m | method Bnet: segments ok, n: abs err median / p90 / bias | 29/29, n 29: 5.4% / 13.2% / 4.6% | - | 30/30, n 28: 3.1% / 9.4% / -0.1% |
| E3_da3m | method A: segments ok, n: abs err median / p90 / bias | 8/29, n 8: 12.1% / 36.8% / -12.1% | - | 11/30, n 11: 6.8% / 19.0% / -4.6% |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp012_glove6_take1 n | exp012_glove6_take1 median | exp012_glove6_take1 p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | oracle | anchors | 1643 |  |  | - | - | - | - | - | - |
| E3_da2 | oracle | 0.07 s | 1613 | 1.1 | 3.3 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.13 s | 1583 | 1.5 | 4.9 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.27 s | 1527 | 2.1 | 6.6 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.53 s | 1416 | 2.7 | 8.0 | - | - | - | - | - | - |
| E3_da2 | oracle | 1.00 s | 1243 | 3.1 | 9.1 | - | - | - | - | - | - |
| E3_da2 | oracle | 2.00 s | 982 | 3.5 | 9.2 | - | - | - | - | - | - |
| E3_da2 | oracle | 4.00 s | 587 | 4.3 | 9.7 | - | - | - | - | - | - |
| E3_da2 | oracle | 6.67 s | 78 | 4.4 | 8.3 | - | - | - | - | - | - |
| E3_da2 | configured | anchors | 1643 |  |  | - | - | - | - | - | - |
| E3_da2 | configured | 0.07 s | 1613 | 1.3 | 3.6 | - | - | - | - | - | - |
| E3_da2 | configured | 0.13 s | 1583 | 2.1 | 5.7 | - | - | - | - | - | - |
| E3_da2 | configured | 0.27 s | 1527 | 3.4 | 9.2 | - | - | - | - | - | - |
| E3_da2 | configured | 0.53 s | 1416 | 5.8 | 13.9 | - | - | - | - | - | - |
| E3_da2 | configured | 1.00 s | 1243 | 9.7 | 21.7 | - | - | - | - | - | - |
| E3_da2 | configured | 2.00 s | 982 | 15.8 | 37.1 | - | - | - | - | - | - |
| E3_da2 | configured | 4.00 s | 587 | 17.2 | 44.4 | - | - | - | - | - | - |
| E3_da2 | configured | 6.67 s | 78 | 23.1 | 31.5 | - | - | - | - | - | - |
| E3_da3m | oracle | anchors | 1643 |  |  | - | - | - | 989 |  |  |
| E3_da3m | oracle | 0.07 s | 1613 | 1.1 | 3.3 | - | - | - | 976 | 1.2 | 3.6 |
| E3_da3m | oracle | 0.13 s | 1583 | 1.5 | 4.9 | - | - | - | 963 | 1.6 | 5.7 |
| E3_da3m | oracle | 0.27 s | 1527 | 2.1 | 6.6 | - | - | - | 937 | 2.3 | 7.3 |
| E3_da3m | oracle | 0.53 s | 1416 | 2.7 | 8.0 | - | - | - | 890 | 3.1 | 11.2 |
| E3_da3m | oracle | 1.00 s | 1243 | 3.1 | 9.1 | - | - | - | 814 | 3.9 | 13.9 |
| E3_da3m | oracle | 2.00 s | 982 | 3.5 | 9.2 | - | - | - | 676 | 5.2 | 14.8 |
| E3_da3m | oracle | 4.00 s | 587 | 4.3 | 9.7 | - | - | - | 398 | 5.9 | 15.8 |
| E3_da3m | oracle | 6.67 s | 78 | 4.4 | 8.3 | - | - | - | 55 | 5.6 | 9.7 |
| E3_da3m | configured | anchors | 1643 |  |  | - | - | - | 989 |  |  |
| E3_da3m | configured | 0.07 s | 1613 | 1.2 | 3.5 | - | - | - | 976 | 1.2 | 3.5 |
| E3_da3m | configured | 0.13 s | 1583 | 1.7 | 5.2 | - | - | - | 963 | 1.6 | 5.7 |
| E3_da3m | configured | 0.27 s | 1527 | 2.5 | 7.3 | - | - | - | 937 | 2.3 | 7.4 |
| E3_da3m | configured | 0.53 s | 1416 | 3.7 | 9.7 | - | - | - | 890 | 3.2 | 10.9 |
| E3_da3m | configured | 1.00 s | 1243 | 5.1 | 13.7 | - | - | - | 814 | 4.2 | 14.2 |
| E3_da3m | configured | 2.00 s | 982 | 7.5 | 18.3 | - | - | - | 676 | 5.4 | 16.1 |
| E3_da3m | configured | 4.00 s | 587 | 9.3 | 22.8 | - | - | - | 398 | 6.1 | 18.8 |
| E3_da3m | configured | 6.67 s | 78 | 9.7 | 15.2 | - | - | - | 55 | 5.4 | 10.4 |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp012_glove6_take1 n | exp012_glove6_take1 median | exp012_glove6_take1 p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | every scale | anchors | 1643 |  |  | - | - | - | - | - | - |
| E3_da2 | every scale | 0.07 s | 1613 | 0.13 | 0.35 | - | - | - | - | - | - |
| E3_da2 | every scale | 0.13 s | 1583 | 0.17 | 0.51 | - | - | - | - | - | - |
| E3_da2 | every scale | 0.27 s | 1527 | 0.23 | 0.66 | - | - | - | - | - | - |
| E3_da2 | every scale | 0.53 s | 1416 | 0.29 | 0.79 | - | - | - | - | - | - |
| E3_da2 | every scale | 1.00 s | 1243 | 0.32 | 0.91 | - | - | - | - | - | - |
| E3_da2 | every scale | 2.00 s | 982 | 0.37 | 0.98 | - | - | - | - | - | - |
| E3_da2 | every scale | 4.00 s | 587 | 0.51 | 1.10 | - | - | - | - | - | - |
| E3_da2 | every scale | 6.67 s | 78 | 0.50 | 1.13 | - | - | - | - | - | - |
| E3_da3m | every scale | anchors | 1643 |  |  | - | - | - | 989 |  |  |
| E3_da3m | every scale | 0.07 s | 1613 | 0.13 | 0.35 | - | - | - | 976 | 0.14 | 0.44 |
| E3_da3m | every scale | 0.13 s | 1583 | 0.17 | 0.51 | - | - | - | 963 | 0.20 | 0.61 |
| E3_da3m | every scale | 0.27 s | 1527 | 0.23 | 0.66 | - | - | - | 937 | 0.27 | 0.83 |
| E3_da3m | every scale | 0.53 s | 1416 | 0.29 | 0.79 | - | - | - | 890 | 0.36 | 1.18 |
| E3_da3m | every scale | 1.00 s | 1243 | 0.32 | 0.91 | - | - | - | 814 | 0.50 | 1.59 |
| E3_da3m | every scale | 2.00 s | 982 | 0.37 | 0.98 | - | - | - | 676 | 0.65 | 1.99 |
| E3_da3m | every scale | 4.00 s | 587 | 0.51 | 1.10 | - | - | - | 398 | 0.56 | 2.41 |
| E3_da3m | every scale | 6.67 s | 78 | 0.50 | 1.13 | - | - | - | 55 | 0.57 | 1.16 |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp012_glove6_take1 | exp007_v2_session_scale | exp009_net_scale |
|---|---|---|---|---|---|---|
| E3_da2 | every scale | anchors | 15 (1.00 s) | 1619 | - | - |
| E3_da2 | every scale | anchors | 30 (2.00 s) | 1624 | - | - |
| E3_da2 | every scale | anchors | 50 (3.33 s) | 1624 | - | - |
| E3_da2 | every scale | anchors | 100 (6.67 s) | 1624 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 50 (3.33 s) | 35 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 100 (6.67 s) | 43 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 15 (1.00 s) | 3.7 / 2.9 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 30 (2.00 s) | 4.3 / 3.5 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 50 (3.33 s) | 4.6 / 3.8 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 100 (6.67 s) | 4.9 / 4.0 | - | - |
| E3_da2 | configured | pos mm, mean / median | 15 (1.00 s) | 6.7 / 5.6 | - | - |
| E3_da2 | configured | pos mm, mean / median | 30 (2.00 s) | 10.1 / 8.2 | - | - |
| E3_da2 | configured | pos mm, mean / median | 50 (3.33 s) | 12.7 / 10.0 | - | - |
| E3_da2 | configured | pos mm, mean / median | 100 (6.67 s) | 13.3 / 10.4 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.43 / 0.31 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.48 / 0.37 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.52 / 0.40 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 100 (6.67 s) | 0.55 / 0.45 | - | - |
| E3_da3m | every scale | anchors | 15 (1.00 s) | 1619 | - | 978 |
| E3_da3m | every scale | anchors | 30 (2.00 s) | 1624 | - | 979 |
| E3_da3m | every scale | anchors | 50 (3.33 s) | 1624 | - | 979 |
| E3_da3m | every scale | anchors | 100 (6.67 s) | 1624 | - | 979 |
| E3_da3m | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | 15 |
| E3_da3m | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - | 30 |
| E3_da3m | every scale | counted steps per anchor, median | 50 (3.33 s) | 35 | - | 46 |
| E3_da3m | every scale | counted steps per anchor, median | 100 (6.67 s) | 43 | - | 49 |
| E3_da3m | oracle | pos mm, mean / median | 15 (1.00 s) | 3.7 / 2.9 | - | 4.7 / 3.2 |
| E3_da3m | oracle | pos mm, mean / median | 30 (2.00 s) | 4.3 / 3.5 | - | 6.4 / 4.2 |
| E3_da3m | oracle | pos mm, mean / median | 50 (3.33 s) | 4.6 / 3.8 | - | 7.7 / 4.9 |
| E3_da3m | oracle | pos mm, mean / median | 100 (6.67 s) | 4.9 / 4.0 | - | 9.1 / 5.5 |
| E3_da3m | configured | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.8 | - | 4.8 / 3.2 |
| E3_da3m | configured | pos mm, mean / median | 30 (2.00 s) | 6.2 / 5.2 | - | 6.6 / 4.3 |
| E3_da3m | configured | pos mm, mean / median | 50 (3.33 s) | 7.2 / 6.1 | - | 8.0 / 5.3 |
| E3_da3m | configured | pos mm, mean / median | 100 (6.67 s) | 7.6 / 6.4 | - | 9.4 / 5.8 |
| E3_da3m | every scale | rot deg, mean / median | 15 (1.00 s) | 0.43 / 0.31 | - | 0.57 / 0.39 |
| E3_da3m | every scale | rot deg, mean / median | 30 (2.00 s) | 0.48 / 0.37 | - | 0.78 / 0.51 |
| E3_da3m | every scale | rot deg, mean / median | 50 (3.33 s) | 0.52 / 0.40 | - | 0.95 / 0.58 |
| E3_da3m | every scale | rot deg, mean / median | 100 (6.67 s) | 0.55 / 0.45 | - | 1.11 / 0.59 |

### Ground-truth noise floor

| pairs | dt [s] | exp012_glove6_take1 n | exp012_glove6_take1 rot deg med / p95 | exp012_glove6_take1 trans mm med / p95 | exp007_v2_session_scale n | exp007_v2_session_scale rot deg med / p95 | exp007_v2_session_scale trans mm med / p95 | exp009_net_scale n | exp009_net_scale rot deg med / p95 | exp009_net_scale trans mm med / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 678 | 0.14 / 0.44 | 2.2 / 7.0 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 462 | 0.22 / 1.14 | 3.6 / 14.2 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 1.0 | 297 | 0.27 / 0.93 | 4.2 / 11.7 | - | - | - | - | - | - |
| same tiles | 2.0 | 174 | 0.24 / 1.19 | 3.5 / 23.2 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 795 | 0.44 / 2.06 | 6.4 / 36.4 | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

