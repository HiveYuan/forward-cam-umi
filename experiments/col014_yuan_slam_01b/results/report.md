# col014_yuan_slam_01b: report (variant main)

23 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.37 / 1.48 | 1.88 / 8.08 | 3.66 / 12.95 | 7.39 / 19.40 | 9.63 / 14.64 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.81 | 0.27 / 1.44 | 0.37 / 2.08 | 0.52 / 5.46 | 0.34 / 1.93 |

n [frame pairs]:

- static, E3: 0.08 s: 2323, 0.5 s: 1971, 1.0 s: 1659, 2.0 s: 1175, 6.67 s: 126
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.14 / 9.55 | 3.51 / 17.48 | 4.95 / 25.08 | 6.66 / 40.04 | 5.12 / 26.95 |
| E3 | Bpar+Acheck | 2.11 / 8.77 | 3.63 / 16.75 | 5.43 / 25.20 | 6.70 / 43.47 | 8.51 / 27.43 |

n [frame pairs]: 0.08 s: 2323, 0.5 s: 1971, 1.0 s: 1659, 2.0 s: 1175, 6.67 s: 126

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 15.7 | 48 | 100% |
| E3 | 0.90% | 13.7 | 37 | 81% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bpar+Acheck (flag \|check/primary - 1\| > 10%) | 23/23 | 23 | 6.6% | 17.5% | 1.5% | ep03, ep04, ep22 |
| E3 | Bpar+Acheck, without flagged | 20/23 | 20 | 6.6% | 22.5% | 2.9% |  |
| E3 | Bpar+Acheck, method Bpar (primary) | 23/23 | 23 | 6.6% | 17.5% | 1.5% |  |
| E3 | Bpar+Acheck, method A (check) | 9/23 | 9 | 4.7% | 27.1% | 3.2% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 596 | 1.1 / 3.9 | 1.4 / 4.8 | 1.9 / 5.8 | 2.7 / 9.2 | 4.0 / 13.8 | 4.8 / 24.0 | 4.4 / 37.3 | 1.5 / 2.3 |
| E3 | Bpar+Acheck | 596 | 1.2 / 4.1 | 1.5 / 5.1 | 2.0 / 6.7 | 2.9 / 12.2 | 4.4 / 19.2 | 5.6 / 49.9 | 6.7 / 64.7 | 2.2 / 2.8 |

n [anchors counting the step]: 0.07 s: 588, 0.13 s: 580, 0.27 s: 564, 0.53 s: 533, 1.00 s: 486, 2.00 s: 386, 4.00 s: 176, 6.67 s: 6

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 596 | 0.14 / 0.49 | 0.17 / 0.66 | 0.22 / 0.83 | 0.31 / 1.15 | 0.43 / 1.76 | 0.59 / 5.18 | 0.41 / 16.88 | 0.17 / 0.26 |

n [anchors counting the step]: 0.07 s: 588, 0.13 s: 580, 0.27 s: 564, 0.53 s: 533, 1.00 s: 486, 2.00 s: 386, 4.00 s: 176, 6.67 s: 6

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 589 | 589 | 589 | 589 |
| E3 | counted steps per anchor, median | 15 | 30 | 43 | 43 |
| E3 | position [mm], oracle (tiles), mean / median | 5.0 / 3.2 | 6.5 / 4.2 | 7.4 / 4.7 | 7.8 / 5.0 |
| E3 | position [mm], Bpar+Acheck, mean / median | 5.9 / 3.5 | 8.2 / 4.9 | 9.8 / 5.4 | 10.6 / 5.7 |
| E3 | rotation [deg], every scale, mean / median | 0.78 / 0.36 | 1.12 / 0.48 | 1.37 / 0.55 | 1.47 / 0.54 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 43 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 313 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 729 | 0.27 / 1.03 | 3.3 / 13.1 |
| same tiles, dt 0.5 s | 498 | 0.32 / 1.18 | 4.0 / 14.7 |
| same tiles, dt 1.0 s | 402 | 0.33 / 1.19 | 4.3 / 16.3 |
| same tiles, dt 2.0 s | 237 | 0.35 / 1.38 | 4.2 / 19.2 |
| tile set changes between the ends | 939 | 0.41 / 1.83 | 5.5 / 23.5 |

