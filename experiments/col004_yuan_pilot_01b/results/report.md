# col004_yuan_pilot_01b: report (variant main)

8 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.73 / 2.58 | 2.69 / 12.71 | 5.07 / 20.79 | 9.90 / 28.91 | 10.33 / 14.38 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.27 / 1.23 | 0.42 / 1.43 | 0.49 / 1.73 | 0.57 / 2.04 | 0.80 / 1.98 |

n [frame pairs]:

- static, E3: 0.08 s: 707, 0.5 s: 540, 1.0 s: 417, 2.0 s: 279, 6.67 s: 40
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 3.41 / 15.16 | 6.22 / 18.82 | 6.79 / 20.29 | 8.17 / 25.20 | 10.53 / 28.74 |
| E3 | Bnet+Acheck | 3.39 / 15.43 | 6.73 / 21.16 | 8.51 / 29.06 | 11.90 / 38.11 | 19.29 / 29.71 |

n [frame pairs]: 0.08 s: 707, 0.5 s: 540, 1.0 s: 417, 2.0 s: 279, 6.67 s: 40

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 18.6 | 41 | 100% |
| E3 | 0.57% | 16.9 | 37 | 83% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 8/8 | 8 | 10.4% | 14.3% | -8.4% | ep00, ep03, ep05 |
| E3 | Bnet+Acheck, without flagged | 5/8 | 5 | 9.0% | 12.5% | -5.9% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 8/8 | 8 | 10.4% | 14.3% | -8.4% |  |
| E3 | Bnet+Acheck, method A (check) | 6/8 | 6 | 6.4% | 22.0% | 4.5% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 263 | 1.7 / 6.5 | 2.2 / 7.3 | 2.7 / 9.8 | 3.9 / 11.7 | 3.5 / 12.3 | 3.8 / 15.2 | 4.3 / 16.1 | 8.5 / 18.2 |
| E3 | Bnet+Acheck | 263 | 1.7 / 6.4 | 2.1 / 7.5 | 2.9 / 9.2 | 4.3 / 11.0 | 4.5 / 13.5 | 6.2 / 17.6 | 11.1 / 19.6 | 11.9 / 18.4 |

n [anchors counting the step]: 0.07 s: 254, 0.13 s: 245, 0.27 s: 230, 0.53 s: 200, 1.00 s: 163, 2.00 s: 121, 4.00 s: 113, 6.67 s: 24

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 263 | 0.25 / 0.92 | 0.30 / 1.04 | 0.36 / 1.29 | 0.41 / 1.30 | 0.41 / 1.37 | 0.69 / 1.96 | 0.64 / 1.88 | 1.04 / 2.35 |

n [anchors counting the step]: 0.07 s: 254, 0.13 s: 245, 0.27 s: 230, 0.53 s: 200, 1.00 s: 163, 2.00 s: 121, 4.00 s: 113, 6.67 s: 24

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 258 | 260 | 260 | 260 |
| E3 | counted steps per anchor, median | 15 | 20 | 29 | 44 |
| E3 | position [mm], oracle (tiles), mean / median | 4.9 / 3.9 | 5.5 / 4.3 | 6.1 / 4.8 | 6.8 / 5.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 5.3 / 4.3 | 6.6 / 4.6 | 7.7 / 6.1 | 9.0 / 7.6 |
| E3 | rotation [deg], every scale, mean / median | 0.62 / 0.44 | 0.69 / 0.49 | 0.77 / 0.60 | 0.83 / 0.71 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 44 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 195 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 537 | 0.42 / 1.22 | 5.2 / 14.8 |
| same tiles, dt 0.5 s | 453 | 0.46 / 1.21 | 5.5 / 14.9 |
| same tiles, dt 1.0 s | 366 | 0.45 / 1.18 | 5.4 / 14.1 |
| same tiles, dt 2.0 s | 231 | 0.47 / 1.20 | 5.8 / 16.0 |
| tile set changes between the ends | 585 | 0.60 / 1.65 | 8.2 / 21.8 |

