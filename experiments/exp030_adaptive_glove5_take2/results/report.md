# exp030_adaptive_glove5_take2: report (variant main)

66 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.26 | 2.16 / 7.35 | 4.20 / 14.28 | 7.44 / 23.10 | 13.69 / 27.92 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.13 / 0.53 | 0.27 / 1.62 | 0.37 / 2.55 | 0.47 / 4.06 | 0.51 / 6.62 |

n [frame pairs]:

- static, E3: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.02 / 9.00 | 4.35 / 28.20 | 6.01 / 48.86 | 7.20 / 92.12 | 7.86 / 114.22 |
| E3 | Bnet+Acheck | 2.04 / 8.58 | 4.64 / 26.75 | 6.98 / 44.10 | 9.48 / 71.24 | 10.60 / 131.32 |

n [frame pairs]: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 17.5 | 52 | 100% |
| E3 | 0.33% | 13.6 | 53 | 88% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 66/66 | 65 | 6.1% | 24.7% | 5.1% | ep04, ep11, ep25, ep38 |
| E3 | Bnet+Acheck, without flagged | 62/66 | 61 | 6.5% | 25.4% | 5.1% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 66/66 | 65 | 6.1% | 24.7% | 5.1% |  |
| E3 | Bnet+Acheck, method A (check) | 7/66 | 7 | 7.2% | 59.8% | -4.9% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 4616 | 0.9 / 2.9 | 1.2 / 4.7 | 1.7 / 7.0 | 2.5 / 11.3 | 3.5 / 16.2 | 4.6 / 23.9 | 5.9 / 27.4 | 5.3 / 16.7 |
| E3 | Bnet+Acheck | 4616 | 0.9 / 2.8 | 1.3 / 4.5 | 1.8 / 6.9 | 2.8 / 10.9 | 4.3 / 15.0 | 6.1 / 20.0 | 8.3 / 24.2 | 8.5 / 23.0 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 4616 | 0.11 / 0.33 | 0.15 / 0.51 | 0.20 / 0.78 | 0.28 / 1.18 | 0.38 / 1.66 | 0.49 / 2.26 | 0.59 / 2.56 | 0.56 / 1.87 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 4564 | 4571 | 4572 | 4572 |
| E3 | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3 | position [mm], oracle (tiles), mean / median | 4.5 / 2.5 | 6.1 / 3.4 | 7.3 / 4.0 | 8.1 / 4.5 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.4 / 2.8 | 6.2 / 4.0 | 7.4 / 4.7 | 8.3 / 5.6 |
| E3 | rotation [deg], every scale, mean / median | 0.51 / 0.28 | 0.69 / 0.37 | 0.81 / 0.43 | 0.88 / 0.48 |

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

