# col016_yuan_slam_02b: report (variant main)

27 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.33 / 1.12 | 1.53 / 5.82 | 2.81 / 9.59 | 5.13 / 13.49 | 12.24 / 14.69 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.15 / 0.69 | 0.22 / 1.52 | 0.28 / 2.43 | 0.34 / 3.56 | 0.37 / 1.01 |

n [frame pairs]:

- static, E3: 0.08 s: 3224, 0.5 s: 2822, 1.0 s: 2408, 2.0 s: 1870, 6.67 s: 111
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.91 / 9.54 | 2.87 / 23.30 | 3.59 / 36.20 | 4.35 / 55.06 | 5.00 / 17.51 |
| E3 | Bpar+Acheck | 1.89 / 8.81 | 3.25 / 19.24 | 4.55 / 30.99 | 6.57 / 45.33 | 8.45 / 25.07 |

n [frame pairs]: 0.08 s: 3224, 0.5 s: 2822, 1.0 s: 2408, 2.0 s: 1870, 6.67 s: 111

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 13.8 | 34 | 100% |
| E3 | 0.37% | 11.8 | 28 | 83% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bpar+Acheck (flag \|check/primary - 1\| > 10%) | 27/27 | 27 | 10.7% | 42.8% | -5.5% | ep01, ep08, ep09, ep22, ep24, ep25, ep26, ep27 |
| E3 | Bpar+Acheck, without flagged | 19/27 | 19 | 10.7% | 59.5% | -5.5% |  |
| E3 | Bpar+Acheck, method Bpar (primary) | 27/27 | 27 | 10.7% | 42.8% | -5.5% |  |
| E3 | Bpar+Acheck, method A (check) | 12/27 | 12 | 6.9% | 19.8% | -0.9% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1205 | 1.0 / 3.9 | 1.1 / 4.4 | 1.3 / 5.7 | 1.7 / 6.8 | 2.1 / 7.9 | 2.6 / 9.3 | 3.1 / 13.5 | 3.4 / 9.9 |
| E3 | Bpar+Acheck | 1205 | 1.0 / 3.6 | 1.2 / 4.1 | 1.5 / 5.3 | 2.1 / 6.7 | 3.2 / 10.4 | 5.1 / 13.7 | 7.1 / 20.4 | 16.3 / 22.7 |

n [anchors counting the step]: 0.07 s: 1188, 0.13 s: 1171, 0.27 s: 1137, 0.53 s: 1069, 1.00 s: 956, 2.00 s: 790, 4.00 s: 425, 6.67 s: 58

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1205 | 0.12 / 0.48 | 0.14 / 0.55 | 0.17 / 0.67 | 0.21 / 0.77 | 0.26 / 0.91 | 0.30 / 1.15 | 0.37 / 1.49 | 0.43 / 0.98 |

n [anchors counting the step]: 0.07 s: 1188, 0.13 s: 1171, 0.27 s: 1137, 0.53 s: 1069, 1.00 s: 956, 2.00 s: 790, 4.00 s: 425, 6.67 s: 58

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1190 | 1192 | 1192 | 1192 |
| E3 | counted steps per anchor, median | 15 | 30 | 40 | 46 |
| E3 | position [mm], oracle (tiles), mean / median | 3.1 / 2.0 | 3.8 / 2.7 | 4.4 / 3.1 | 4.9 / 3.3 |
| E3 | position [mm], Bpar+Acheck, mean / median | 3.3 / 2.5 | 4.4 / 3.6 | 5.3 / 4.4 | 5.9 / 4.8 |
| E3 | rotation [deg], every scale, mean / median | 0.37 / 0.25 | 0.44 / 0.31 | 0.49 / 0.35 | 0.54 / 0.39 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 46 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 429 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 1047 | 0.25 / 0.65 | 3.0 / 8.0 |
| same tiles, dt 0.5 s | 705 | 0.26 / 0.78 | 3.1 / 10.2 |
| same tiles, dt 1.0 s | 519 | 0.28 / 1.04 | 3.5 / 12.3 |
| same tiles, dt 2.0 s | 402 | 0.29 / 1.63 | 3.4 / 21.0 |
| tile set changes between the ends | 1287 | 0.36 / 1.08 | 4.7 / 15.1 |

