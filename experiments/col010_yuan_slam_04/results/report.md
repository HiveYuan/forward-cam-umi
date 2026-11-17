# col010_yuan_slam_04: report (variant main)

33 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.31 / 1.03 | 1.49 / 5.31 | 3.07 / 9.70 | 6.11 / 16.00 | 8.52 / 21.81 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.66 | 0.23 / 1.65 | 0.30 / 2.60 | 0.39 / 4.24 | 0.57 / 6.75 |

n [frame pairs]:

- static, E3: 0.08 s: 3396, 0.5 s: 2946, 1.0 s: 2533, 2.0 s: 1948, 6.67 s: 268
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.11 / 8.18 | 3.37 / 20.24 | 4.31 / 33.14 | 5.73 / 56.15 | 7.52 / 75.48 |
| E3 | Bnet+Acheck | 2.10 / 7.95 | 4.03 / 19.49 | 5.84 / 32.97 | 8.30 / 55.36 | 9.12 / 69.83 |

n [frame pairs]:

- E3 oracle (tiles): 0.08 s: 3394, 0.5 s: 2945, 1.0 s: 2533, 2.0 s: 1948, 6.67 s: 268
- E3 Bnet+Acheck: 0.08 s: 3396, 0.5 s: 2946, 1.0 s: 2533, 2.0 s: 1948, 6.67 s: 268

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 15.1 | 34 | 100% |
| E3 | 1.30% | 12.0 | 30 | 83% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 33/33 | 30 | 28.4% | 71.9% | -21.0% | ep12, ep15, ep18, ep21, ep27, ep36, ep38, ep42 |
| E3 | Bnet+Acheck, without flagged | 25/33 | 22 | 27.2% | 70.9% | -21.0% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 33/33 | 30 | 28.4% | 71.9% | -21.0% |  |
| E3 | Bnet+Acheck, method A (check) | 10/33 | 10 | 9.3% | 38.6% | 8.2% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1742 | 1.2 / 3.8 | 1.4 / 5.1 | 1.7 / 7.9 | 2.2 / 12.1 | 3.0 / 19.6 | 3.7 / 26.8 | 4.5 / 41.6 | 4.7 / 38.8 |
| E3 | Bnet+Acheck | 1742 | 1.2 / 3.6 | 1.5 / 4.8 | 2.1 / 7.2 | 3.0 / 10.9 | 4.6 / 16.4 | 6.8 / 22.5 | 8.7 / 28.5 | 7.0 / 33.2 |

n [anchors counting the step]: 0.07 s: 1705, 0.13 s: 1670, 0.27 s: 1607, 0.53 s: 1513, 1.00 s: 1384, 2.00 s: 1151, 4.00 s: 627, 6.67 s: 163

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1742 | 0.13 / 0.46 | 0.16 / 0.63 | 0.20 / 0.89 | 0.26 / 1.38 | 0.34 / 1.98 | 0.44 / 3.20 | 0.51 / 4.24 | 0.52 / 5.52 |

n [anchors counting the step]: 0.07 s: 1705, 0.13 s: 1670, 0.27 s: 1607, 0.53 s: 1513, 1.00 s: 1384, 2.00 s: 1151, 4.00 s: 627, 6.67 s: 163

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1719 | 1723 | 1723 | 1723 |
| E3 | counted steps per anchor, median | 15 | 30 | 41 | 46 |
| E3 | position [mm], oracle (tiles), mean / median | 5.1 / 2.4 | 6.7 / 3.0 | 7.8 / 3.5 | 9.0 / 3.8 |
| E3 | position [mm], Bnet+Acheck, mean / median | 7.8 / 3.1 | 10.5 / 4.7 | 11.4 / 6.0 | 12.4 / 6.6 |
| E3 | rotation [deg], every scale, mean / median | 0.66 / 0.30 | 0.85 / 0.40 | 1.00 / 0.47 | 1.16 / 0.52 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 46 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 115 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 249 | 0.22 / 0.54 | 2.7 / 6.8 |
| same tiles, dt 0.5 s | 108 | 0.24 / 0.49 | 3.0 / 6.1 |
| same tiles, dt 1.0 s | 138 | 0.27 / 0.63 | 3.1 / 7.3 |
| same tiles, dt 2.0 s | 66 | 0.25 / 0.56 | 3.1 / 6.2 |
| tile set changes between the ends | 345 | 0.50 / 1.06 | 6.2 / 14.4 |

