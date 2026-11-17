# col009_yuan_slam_03: report (variant main)

32 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.35 / 1.42 | 1.78 / 6.07 | 3.54 / 12.12 | 6.47 / 22.26 | 10.54 / 15.88 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.20 / 1.71 | 0.33 / 3.51 | 0.46 / 6.38 | 0.69 / 8.31 | 2.67 / 6.23 |

n [frame pairs]:

- static, E3: 0.08 s: 1490, 0.5 s: 1140, 1.0 s: 870, 2.0 s: 565, 6.67 s: 46
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.50 / 19.16 | 4.41 / 35.48 | 5.99 / 50.16 | 9.91 / 92.92 | 37.26 / 108.28 |
| E3 | Bnet+Acheck | 2.49 / 16.09 | 5.69 / 36.39 | 9.82 / 93.68 | 20.25 / 100.94 | 42.14 / 87.24 |

n [frame pairs]: 0.08 s: 1490, 0.5 s: 1140, 1.0 s: 870, 2.0 s: 565, 6.67 s: 46

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 16.2 | 36 | 100% |
| E3 | 4.09% | 13.2 | 31 | 80% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 32/32 | 31 | 31.5% | 68.1% | -28.7% | ep00, ep05, ep08, ep10, ep11, ep13, ep20, ep29, ep36 |
| E3 | Bnet+Acheck, without flagged | 23/32 | 22 | 36.8% | 66.2% | -35.0% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 32/32 | 31 | 31.5% | 68.1% | -28.7% |  |
| E3 | Bnet+Acheck, method A (check) | 11/32 | 11 | 16.7% | 30.8% | 0.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 260 | 1.2 / 7.3 | 1.7 / 9.2 | 2.0 / 11.3 | 2.6 / 13.5 | 3.7 / 14.8 | 6.4 / 16.2 | 9.8 / 15.9 | 14.8 / 14.9 |
| E3 | Bnet+Acheck | 260 | 1.2 / 7.3 | 1.7 / 9.2 | 2.2 / 10.7 | 3.6 / 12.9 | 5.9 / 14.5 | 9.6 / 17.0 | 10.1 / 17.3 | 16.2 / 16.4 |

n [anchors counting the step]: 0.07 s: 255, 0.13 s: 250, 0.27 s: 240, 0.53 s: 224, 1.00 s: 200, 2.00 s: 164, 4.00 s: 82, 6.67 s: 3

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 260 | 0.17 / 0.78 | 0.20 / 1.12 | 0.24 / 1.43 | 0.31 / 1.44 | 0.43 / 1.83 | 0.64 / 2.21 | 0.90 / 2.12 | 2.02 / 2.06 |

n [anchors counting the step]: 0.07 s: 255, 0.13 s: 250, 0.27 s: 240, 0.53 s: 224, 1.00 s: 200, 2.00 s: 164, 4.00 s: 82, 6.67 s: 3

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 256 | 257 | 257 | 257 |
| E3 | counted steps per anchor, median | 15 | 30 | 40 | 43 |
| E3 | position [mm], oracle (tiles), mean / median | 5.0 / 4.4 | 6.0 / 5.1 | 6.7 / 6.3 | 7.2 / 6.7 |
| E3 | position [mm], Bnet+Acheck, mean / median | 5.2 / 4.5 | 6.6 / 6.0 | 7.9 / 7.6 | 8.4 / 7.8 |
| E3 | rotation [deg], every scale, mean / median | 0.62 / 0.52 | 0.75 / 0.62 | 0.84 / 0.73 | 0.92 / 0.80 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 43 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 58 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 123 | 0.15 / 0.56 | 1.7 / 6.2 |
| same tiles, dt 0.5 s | 51 | 0.14 / 0.56 | 1.7 / 5.9 |
| same tiles, dt 1.0 s | 51 | 0.14 / 0.41 | 1.5 / 3.7 |
| same tiles, dt 2.0 s | 27 | 0.33 / 0.48 | 3.2 / 8.9 |
| tile set changes between the ends | 174 | 0.29 / 0.81 | 3.8 / 15.0 |

