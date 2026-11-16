# exp040_adaptive_head_glove5_take2: report (variant main)

66 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.26 | 2.16 / 7.35 | 4.20 / 14.28 | 7.44 / 23.10 | 13.69 / 27.92 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.13 / 0.56 | 0.27 / 1.86 | 0.37 / 3.23 | 0.48 / 5.10 | 0.49 / 4.75 |

n [frame pairs]:

- static, E3: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.04 / 9.49 | 4.30 / 30.65 | 5.95 / 56.53 | 7.41 / 101.35 | 7.79 / 78.07 |
| E3 | Bnet+Acheck | 2.05 / 8.85 | 4.62 / 29.59 | 6.92 / 56.09 | 9.64 / 99.40 | 10.35 / 94.33 |

n [frame pairs]: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 17.5 | 52 | 100% |
| E3 | 0.39% | 13.5 | 53 | 88% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 66/66 | 65 | 5.9% | 24.9% | 4.7% | ep04, ep11, ep25, ep38 |
| E3 | Bnet+Acheck, without flagged | 62/66 | 61 | 6.0% | 25.8% | 5.3% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 66/66 | 65 | 5.9% | 24.9% | 4.7% |  |
| E3 | Bnet+Acheck, method A (check) | 7/66 | 7 | 8.4% | 61.7% | -4.5% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 4508 | 0.9 / 3.3 | 1.2 / 5.1 | 1.7 / 7.9 | 2.5 / 12.5 | 3.5 / 19.0 | 4.8 / 28.8 | 6.1 / 32.0 | 5.4 / 14.9 |
| E3 | Bnet+Acheck | 4508 | 0.9 / 3.1 | 1.3 / 4.9 | 1.8 / 7.6 | 2.8 / 12.3 | 4.3 / 17.5 | 6.1 / 24.5 | 8.7 / 26.6 | 8.5 / 23.7 |

n [anchors counting the step]: 0.07 s: 4445, 0.13 s: 4382, 0.27 s: 4256, 0.53 s: 4029, 1.00 s: 3666, 2.00 s: 3037, 4.00 s: 1946, 6.67 s: 612

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 4508 | 0.11 / 0.36 | 0.16 / 0.56 | 0.20 / 0.91 | 0.28 / 1.41 | 0.38 / 2.06 | 0.50 / 2.79 | 0.60 / 3.69 | 0.55 / 1.87 |

n [anchors counting the step]: 0.07 s: 4445, 0.13 s: 4382, 0.27 s: 4256, 0.53 s: 4029, 1.00 s: 3666, 2.00 s: 3037, 4.00 s: 1946, 6.67 s: 612

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 4458 | 4464 | 4465 | 4465 |
| E3 | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3 | position [mm], oracle (tiles), mean / median | 5.4 / 2.5 | 7.7 / 3.4 | 9.3 / 4.0 | 10.1 / 4.5 |
| E3 | position [mm], Bnet+Acheck, mean / median | 5.3 / 2.8 | 7.6 / 3.9 | 9.3 / 4.7 | 10.4 / 5.5 |
| E3 | rotation [deg], every scale, mean / median | 0.57 / 0.29 | 0.78 / 0.37 | 0.92 / 0.44 | 1.03 / 0.48 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 52 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 632 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 1611 | 0.14 / 1.29 | 2.3 / 23.7 |
| same tiles, dt 0.5 s | 1074 | 0.22 / 1.63 | 3.9 / 35.6 |
| same tiles, dt 1.0 s | 786 | 0.30 / 1.46 | 5.4 / 37.5 |
| same tiles, dt 2.0 s | 579 | 0.42 / 3.20 | 8.1 / 63.4 |
| tile set changes between the ends | 1896 | 0.43 / 3.68 | 7.5 / 67.6 |

