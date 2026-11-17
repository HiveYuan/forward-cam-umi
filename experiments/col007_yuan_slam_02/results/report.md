# col007_yuan_slam_02: report (variant main)

10 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.27 / 0.96 | 1.04 / 4.61 | 2.14 / 7.10 | 4.97 / 12.01 | 12.09 / 12.85 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.15 / 0.71 | 0.22 / 1.08 | 0.30 / 1.82 | 0.44 / 4.29 | 0.75 / 6.52 |

n [frame pairs]:

- static, E3: 0.08 s: 1023, 0.5 s: 882, 1.0 s: 729, 2.0 s: 559, 6.67 s: 70
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.79 / 7.98 | 3.01 / 25.69 | 4.06 / 48.41 | 5.91 / 74.14 | 9.51 / 78.01 |
| E3 | Bnet+Acheck | 1.74 / 8.08 | 3.13 / 13.01 | 4.59 / 21.18 | 7.28 / 47.86 | 13.61 / 70.98 |

n [frame pairs]: 0.08 s: 1023, 0.5 s: 882, 1.0 s: 729, 2.0 s: 559, 6.67 s: 70

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 13.7 | 29 | 100% |
| E3 | 3.23% | 11.5 | 28 | 81% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 10/10 | 10 | 14.0% | 160.5% | -2.5% | ep07, ep08, ep09 |
| E3 | Bnet+Acheck, without flagged | 7/10 | 7 | 8.1% | 509.0% | -6.4% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 10/10 | 10 | 14.0% | 160.5% | -2.5% |  |
| E3 | Bnet+Acheck, method A (check) | 5/10 | 5 | 26.0% | 740.6% | 26.0% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 204 | 1.3 / 3.5 | 1.4 / 3.9 | 1.8 / 4.9 | 2.4 / 7.2 | 3.2 / 10.2 | 6.6 / 18.6 | 15.5 / 24.0 | 4.8 / 31.8 |
| E3 | Bnet+Acheck | 204 | 1.2 / 3.4 | 1.4 / 3.8 | 1.8 / 4.7 | 2.5 / 6.6 | 3.4 / 10.0 | 6.2 / 17.5 | 13.5 / 22.0 | 8.5 / 27.6 |

n [anchors counting the step]: 0.07 s: 199, 0.13 s: 194, 0.27 s: 184, 0.53 s: 164, 1.00 s: 132, 2.00 s: 120, 4.00 s: 70, 6.67 s: 45

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 204 | 0.15 / 0.42 | 0.18 / 0.49 | 0.24 / 0.61 | 0.33 / 0.84 | 0.49 / 1.54 | 0.96 / 3.82 | 1.89 / 4.91 | 0.69 / 6.43 |

n [anchors counting the step]: 0.07 s: 199, 0.13 s: 194, 0.27 s: 184, 0.53 s: 164, 1.00 s: 132, 2.00 s: 120, 4.00 s: 70, 6.67 s: 45

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 200 | 202 | 202 | 202 |
| E3 | counted steps per anchor, median | 15 | 21 | 33 | 51 |
| E3 | position [mm], oracle (tiles), mean / median | 3.3 / 2.5 | 4.5 / 3.3 | 5.8 / 3.4 | 7.7 / 3.5 |
| E3 | position [mm], Bnet+Acheck, mean / median | 3.2 / 2.5 | 4.4 / 3.2 | 5.7 / 4.4 | 7.6 / 5.4 |
| E3 | rotation [deg], every scale, mean / median | 0.47 / 0.34 | 0.67 / 0.46 | 0.91 / 0.47 | 1.32 / 0.48 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 51 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 93 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 228 | 0.22 / 0.46 | 2.3 / 5.5 |
| same tiles, dt 0.5 s | 102 | 0.21 / 0.46 | 2.7 / 5.2 |
| same tiles, dt 1.0 s | 57 | 0.27 / 0.50 | 3.1 / 5.8 |
| same tiles, dt 2.0 s | 21 | 0.29 / 0.45 | 2.8 / 5.8 |
| tile set changes between the ends | 279 | 0.31 / 0.61 | 3.9 / 7.4 |

