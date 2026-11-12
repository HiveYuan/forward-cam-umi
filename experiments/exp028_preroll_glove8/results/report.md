# exp028_preroll_glove8: report (variant main)

4 segments. Runs: E1, E3, E3p2, E3p1 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.59 / 1.65 | 3.30 / 9.34 | 5.89 / 13.22 | 8.36 / 25.32 | - / - |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.17 / 0.53 | 0.39 / 1.02 | 0.44 / 1.18 | 0.56 / 1.21 | - / - |
| E3p2 | 0.21 / 0.62 | 0.49 / 1.82 | 0.66 / 3.92 | 0.86 / 5.52 | - / - |
| E3p1 | 0.20 / 0.73 | 0.54 / 2.57 | 0.76 / 3.87 | 1.26 / 6.40 | - / - |

n [frame pairs]:

- static, E3, E3p2, E3p1: 0.08 s: 431, 0.5 s: 334, 1.0 s: 283, 2.0 s: 222, 6.67 s: 0
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.79 / 9.30 | 7.05 / 22.23 | 7.88 / 30.19 | 8.69 / 59.91 | - / - |
| E3 | Bnet+Acheck | 2.76 / 9.42 | 6.44 / 18.42 | 6.75 / 23.40 | 8.56 / 21.76 | - / - |
| E3p2 | oracle (tiles) | 3.36 / 10.29 | 8.48 / 29.01 | 11.35 / 61.01 | 15.33 / 81.58 | - / - |
| E3p2 | Bnet+Acheck | 3.39 / 9.88 | 8.40 / 28.93 | 11.73 / 59.71 | 15.97 / 78.89 | - / - |
| E3p1 | oracle (tiles) | 3.27 / 13.07 | 10.20 / 39.81 | 13.78 / 61.96 | 18.69 / 99.94 | - / - |
| E3p1 | Bnet+Acheck | 3.24 / 11.54 | 9.21 / 35.86 | 13.88 / 52.19 | 21.85 / 83.85 | - / - |

n [frame pairs]: 0.08 s: 431, 0.5 s: 334, 1.0 s: 283, 2.0 s: 222, 6.67 s: 0

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 20.5 | 91 | 100% |
| E3 | 0.00% | 15.0 | 63 | 84% |
| E3p2 | 0.00% | 13.5 | 49 | 84% |
| E3p1 | 0.46% | 11.8 | 37 | 84% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 4/4 | 4 | 0.8% | 14.4% | 0.2% | - |
| E3 | Bnet+Acheck, method Bnet (primary) | 4/4 | 4 | 0.8% | 14.4% | 0.2% |  |
| E3 | Bnet+Acheck, method A (check) | 0/4 | 0 | - | - | - |  |
| E3p2 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 4/4 | 4 | 6.1% | 8.8% | -2.0% | - |
| E3p2 | Bnet+Acheck, method Bnet (primary) | 4/4 | 4 | 6.1% | 8.8% | -2.0% |  |
| E3p2 | Bnet+Acheck, method A (check) | 0/4 | 0 | - | - | - |  |
| E3p1 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 4/4 | 4 | 19.9% | 34.3% | 7.2% | - |
| E3p1 | Bnet+Acheck, method Bnet (primary) | 4/4 | 4 | 19.9% | 34.3% | 7.2% |  |
| E3p1 | Bnet+Acheck, method A (check) | 0/4 | 0 | - | - | - |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 249 | 1.4 / 4.0 | 2.1 / 6.1 | 3.1 / 7.7 | 4.1 / 9.5 | 5.0 / 19.6 | 5.7 / 37.6 | 9.4 / 31.0 |
| E3 | Bnet+Acheck | 249 | 1.3 / 3.7 | 2.1 / 6.0 | 2.8 / 7.1 | 3.7 / 7.5 | 4.6 / 10.2 | 4.6 / 11.4 | 6.0 / 16.0 |
| E3p2 | oracle (tiles) | 249 | 1.7 / 4.5 | 2.7 / 7.1 | 3.9 / 11.5 | 5.6 / 17.3 | 8.2 / 24.7 | 11.7 / 35.1 | 13.0 / 58.5 |
| E3p2 | Bnet+Acheck | 249 | 1.7 / 4.3 | 2.8 / 6.9 | 3.9 / 11.0 | 5.7 / 16.9 | 8.5 / 26.8 | 15.0 / 38.2 | 18.7 / 55.1 |
| E3p1 | oracle (tiles) | 249 | 1.9 / 4.8 | 3.0 / 7.5 | 4.4 / 12.0 | 6.2 / 21.1 | 7.8 / 34.6 | 8.8 / 35.0 | 12.3 / 45.9 |
| E3p1 | Bnet+Acheck | 249 | 1.7 / 4.2 | 2.7 / 6.5 | 3.9 / 10.2 | 6.1 / 15.6 | 8.8 / 20.8 | 13.0 / 33.6 | 21.0 / 29.1 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| E3p2 | every scale | 249 | 0.19 / 0.47 | 0.32 / 0.79 | 0.44 / 1.24 | 0.65 / 1.96 | 0.84 / 3.21 | 1.07 / 5.22 | 0.82 / 9.48 |
| E3p1 | every scale | 249 | 0.19 / 0.56 | 0.30 / 0.82 | 0.46 / 1.22 | 0.67 / 2.04 | 0.88 / 2.80 | 1.24 / 3.57 | 1.38 / 6.94 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 246 | 246 | 246 | 246 |
| E3 | counted steps per anchor, median | 15 | 26.5 | 35.5 | 41.5 |
| E3 | position [mm], oracle (tiles), mean / median | 5.3 / 4.1 | 7.8 / 5.2 | 9.7 / 5.2 | 9.8 / 5.3 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.4 / 3.6 | 5.2 / 4.2 | 5.5 / 4.3 | 5.9 / 5.1 |
| E3 | rotation [deg], every scale, mean / median | 0.46 / 0.39 | 0.52 / 0.46 | 0.57 / 0.53 | 0.58 / 0.55 |
| E3p2 | anchors | 246 | 246 | 246 | 246 |
| E3p2 | counted steps per anchor, median | 15 | 26.5 | 35.5 | 41.5 |
| E3p2 | position [mm], oracle (tiles), mean / median | 7.2 / 5.3 | 9.5 / 6.2 | 11.1 / 6.5 | 12.0 / 7.3 |
| E3p2 | position [mm], Bnet+Acheck, mean / median | 7.3 / 5.5 | 10.1 / 7.1 | 12.0 / 9.2 | 12.9 / 10.1 |
| E3p2 | rotation [deg], every scale, mean / median | 0.84 / 0.56 | 1.14 / 0.63 | 1.38 / 0.66 | 1.51 / 0.64 |
| E3p1 | anchors | 246 | 246 | 246 | 246 |
| E3p1 | counted steps per anchor, median | 15 | 26.5 | 35.5 | 41.5 |
| E3p1 | position [mm], oracle (tiles), mean / median | 7.7 / 5.4 | 9.9 / 6.3 | 10.7 / 7.2 | 11.2 / 7.5 |
| E3p1 | position [mm], Bnet+Acheck, mean / median | 6.9 / 5.7 | 9.5 / 7.8 | 11.3 / 9.5 | 11.8 / 9.8 |
| E3p1 | rotation [deg], every scale, mean / median | 0.84 / 0.61 | 1.05 / 0.79 | 1.19 / 0.97 | 1.24 / 0.90 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 41.5 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 9 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 21 | 0.10 / 0.18 | 1.6 / 4.1 |
| tile set changes between the ends | 27 | 0.44 / 1.12 | 6.7 / 20.0 |

