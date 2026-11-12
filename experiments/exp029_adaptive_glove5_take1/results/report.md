# exp029_adaptive_glove5_take1: report (variant main)

49 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.37 / 1.11 | 2.17 / 6.40 | 4.34 / 12.38 | 8.03 / 19.67 | 14.29 / 26.71 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.12 / 0.55 | 0.24 / 1.83 | 0.31 / 3.14 | 0.39 / 5.62 | 0.51 / 7.85 |

n [frame pairs]:

- static, E3: 0.08 s: 8477, 0.5 s: 7538, 1.0 s: 6707, 2.0 s: 5505, 6.67 s: 1614
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.78 / 8.12 | 3.61 / 26.72 | 4.73 / 44.73 | 5.74 / 76.24 | 6.92 / 109.29 |
| E3 | Bnet+Acheck | 1.83 / 7.89 | 4.08 / 27.11 | 5.98 / 47.26 | 8.58 / 81.67 | 13.51 / 106.25 |

n [frame pairs]: 0.08 s: 8477, 0.5 s: 7538, 1.0 s: 6707, 2.0 s: 5505, 6.67 s: 1614

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 19.5 | 58 | 100% |
| E3 | 0.27% | 14.5 | 58 | 85% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 49/49 | 49 | 8.7% | 15.3% | 7.6% | ep03, ep06, ep16, ep22, ep25, ep28, ep35, ep38 |
| E3 | Bnet+Acheck, without flagged | 41/49 | 41 | 9.1% | 15.4% | 7.6% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 49/49 | 49 | 8.7% | 15.3% | 7.6% |  |
| E3 | Bnet+Acheck, method A (check) | 13/49 | 13 | 8.3% | 24.7% | -7.7% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 4734 | 0.8 / 2.9 | 1.1 / 4.4 | 1.6 / 6.8 | 2.2 / 10.4 | 3.0 / 14.9 | 3.6 / 22.0 | 4.4 / 24.9 | 4.2 / 27.5 |
| E3 | Bnet+Acheck | 4734 | 0.8 / 2.9 | 1.2 / 4.5 | 1.8 / 6.9 | 2.8 / 10.5 | 4.2 / 15.1 | 6.5 / 21.5 | 8.4 / 24.8 | 10.6 / 29.0 |

n [anchors counting the step]: 0.07 s: 4671, 0.13 s: 4609, 0.27 s: 4485, 0.53 s: 4256, 1.00 s: 3881, 2.00 s: 3238, 4.00 s: 2192, 6.67 s: 858

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 4734 | 0.10 / 0.35 | 0.15 / 0.55 | 0.19 / 0.86 | 0.25 / 1.24 | 0.32 / 1.86 | 0.40 / 3.10 | 0.49 / 3.38 | 0.51 / 5.32 |

n [anchors counting the step]: 0.07 s: 4671, 0.13 s: 4609, 0.27 s: 4485, 0.53 s: 4256, 1.00 s: 3881, 2.00 s: 3238, 4.00 s: 2192, 6.67 s: 858

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 4682 | 4690 | 4692 | 4692 |
| E3 | counted steps per anchor, median | 15 | 30 | 44 | 56 |
| E3 | position [mm], oracle (tiles), mean / median | 3.7 / 2.2 | 5.1 / 2.8 | 6.0 / 3.2 | 6.6 / 3.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.2 / 2.7 | 6.1 / 3.9 | 7.6 / 4.6 | 8.6 / 5.1 |
| E3 | rotation [deg], every scale, mean / median | 0.47 / 0.25 | 0.65 / 0.32 | 0.79 / 0.36 | 0.89 / 0.40 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 56 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 1032 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 2658 | 0.11 / 0.45 | 1.8 / 9.4 |
| same tiles, dt 0.5 s | 1716 | 0.16 / 0.88 | 2.6 / 17.6 |
| same tiles, dt 1.0 s | 1161 | 0.19 / 0.92 | 3.1 / 19.6 |
| same tiles, dt 2.0 s | 714 | 0.25 / 0.90 | 4.0 / 18.0 |
| tile set changes between the ends | 3096 | 0.31 / 1.91 | 5.0 / 36.3 |

