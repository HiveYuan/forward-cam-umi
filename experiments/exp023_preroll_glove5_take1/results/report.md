# exp023_preroll_glove5_take1: report (variant main)

49 segments. Runs: E1, E3, E3p2, E3p1 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.37 / 1.11 | 2.17 / 6.40 | 4.34 / 12.38 | 8.03 / 19.67 | 14.29 / 26.71 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.12 / 0.50 | 0.23 / 1.68 | 0.30 / 2.95 | 0.38 / 4.90 | 0.53 / 6.77 |
| E3p2 | 0.13 / 0.60 | 0.29 / 1.96 | 0.40 / 3.38 | 0.53 / 5.77 | 0.72 / 9.78 |
| E3p1 | 0.15 / 0.60 | 0.35 / 2.31 | 0.48 / 4.26 | 0.58 / 7.77 | 0.65 / 10.99 |

n [frame pairs]:

- static, E3, E3p2, E3p1: 0.08 s: 8477, 0.5 s: 7538, 1.0 s: 6707, 2.0 s: 5505, 6.67 s: 1614
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.78 / 6.97 | 3.68 / 26.22 | 4.86 / 45.90 | 5.79 / 80.11 | 7.42 / 96.79 |
| E3 | Bnet+Acheck | 1.83 / 7.19 | 4.29 / 25.42 | 6.37 / 44.58 | 9.21 / 73.33 | 14.97 / 96.65 |
| E3p2 | oracle (tiles) | 1.95 / 9.72 | 4.29 / 29.92 | 5.96 / 49.49 | 7.43 / 83.40 | 10.26 / 130.36 |
| E3p2 | Bnet+Acheck | 1.97 / 8.76 | 4.90 / 28.35 | 7.39 / 47.76 | 10.83 / 83.38 | 17.88 / 123.46 |
| E3p1 | oracle (tiles) | 2.21 / 9.33 | 5.24 / 34.51 | 7.09 / 62.16 | 8.58 / 111.58 | 8.76 / 149.93 |
| E3p1 | Bnet+Acheck | 2.21 / 8.48 | 5.63 / 32.99 | 8.67 / 59.01 | 12.23 / 104.12 | 15.65 / 152.46 |

n [frame pairs]: 0.08 s: 8477, 0.5 s: 7538, 1.0 s: 6707, 2.0 s: 5505, 6.67 s: 1614

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 19.5 | 58 | 100% |
| E3 | 0.22% | 18.6 | 63 | 85% |
| E3p2 | 0.25% | 13.1 | 43 | 84% |
| E3p1 | 0.20% | 11.1 | 39 | 83% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 49/49 | 49 | 8.7% | 34.6% | 8.3% | ep03, ep04, ep06, ep16, ep22, ep25, ep28, ep32, ep35, ep38 |
| E3 | Bnet+Acheck, without flagged | 39/49 | 39 | 8.7% | 40.4% | 8.3% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 49/49 | 49 | 8.7% | 34.6% | 8.3% |  |
| E3 | Bnet+Acheck, method A (check) | 14/49 | 14 | 9.1% | 26.0% | -8.8% |  |
| E3p2 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 49/49 | 49 | 8.3% | 26.9% | 4.9% | ep03, ep06, ep16, ep20, ep22, ep25, ep27, ep28, ep38, ep41 |
| E3p2 | Bnet+Acheck, without flagged | 39/49 | 39 | 8.3% | 26.9% | 4.9% |  |
| E3p2 | Bnet+Acheck, method Bnet (primary) | 49/49 | 49 | 8.3% | 26.9% | 4.9% |  |
| E3p2 | Bnet+Acheck, method A (check) | 13/49 | 13 | 13.2% | 46.4% | -10.9% |  |
| E3p1 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 49/49 | 49 | 10.7% | 25.2% | -0.4% | ep06, ep25, ep38 |
| E3p1 | Bnet+Acheck, without flagged | 46/49 | 46 | 10.7% | 24.2% | -1.6% |  |
| E3p1 | Bnet+Acheck, method Bnet (primary) | 49/49 | 49 | 10.7% | 25.2% | -0.4% |  |
| E3p1 | Bnet+Acheck, method A (check) | 5/49 | 5 | 13.5% | 22.1% | 2.5% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 4734 | 0.8 / 2.9 | 1.2 / 4.5 | 1.6 / 7.3 | 2.3 / 11.8 | 3.1 / 18.0 | 3.5 / 30.5 | 4.5 / 42.9 | 4.2 / 41.1 |
| E3 | Bnet+Acheck | 4734 | 0.9 / 2.8 | 1.3 / 4.5 | 1.9 / 7.2 | 2.9 / 11.8 | 4.5 / 17.8 | 7.1 / 29.0 | 9.3 / 42.6 | 11.0 / 38.0 |
| E3p2 | oracle (tiles) | 4734 | 0.9 / 3.6 | 1.3 / 5.2 | 1.9 / 8.2 | 2.7 / 12.9 | 3.6 / 19.7 | 4.4 / 29.6 | 5.8 / 34.6 | 6.2 / 46.3 |
| E3p2 | Bnet+Acheck | 4734 | 1.0 / 3.2 | 1.5 / 5.0 | 2.2 / 7.9 | 3.3 / 12.9 | 5.1 / 19.3 | 8.0 / 29.2 | 11.7 / 31.3 | 15.5 / 35.6 |
| E3p1 | oracle (tiles) | 4734 | 1.0 / 3.6 | 1.5 / 5.8 | 2.2 / 9.5 | 3.2 / 15.7 | 4.4 / 24.7 | 5.4 / 38.4 | 5.8 / 48.6 | 6.4 / 51.1 |
| E3p1 | Bnet+Acheck | 4734 | 1.0 / 3.4 | 1.6 / 5.4 | 2.3 / 8.8 | 3.6 / 15.2 | 5.5 / 23.7 | 8.3 / 37.2 | 11.0 / 42.4 | 13.3 / 43.1 |

n [anchors counting the step]: 0.07 s: 4671, 0.13 s: 4609, 0.27 s: 4485, 0.53 s: 4256, 1.00 s: 3881, 2.00 s: 3238, 4.00 s: 2192, 6.67 s: 858

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 4734 | 0.10 / 0.33 | 0.14 / 0.49 | 0.18 / 0.75 | 0.24 / 1.10 | 0.31 / 1.64 | 0.39 / 2.45 | 0.50 / 2.78 | 0.52 / 3.49 |
| E3p2 | every scale | 4734 | 0.12 / 0.39 | 0.16 / 0.61 | 0.23 / 0.96 | 0.32 / 1.56 | 0.43 / 2.61 | 0.57 / 4.22 | 0.73 / 6.56 | 0.72 / 7.70 |
| E3p1 | every scale | 4734 | 0.13 / 0.41 | 0.19 / 0.66 | 0.26 / 1.10 | 0.38 / 1.93 | 0.51 / 3.32 | 0.63 / 5.96 | 0.72 / 9.25 | 0.63 / 9.19 |

n [anchors counting the step]: 0.07 s: 4671, 0.13 s: 4609, 0.27 s: 4485, 0.53 s: 4256, 1.00 s: 3881, 2.00 s: 3238, 4.00 s: 2192, 6.67 s: 858

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 4682 | 4690 | 4692 | 4692 |
| E3 | counted steps per anchor, median | 15 | 30 | 44 | 56 |
| E3 | position [mm], oracle (tiles), mean / median | 4.1 / 2.3 | 5.8 / 2.8 | 7.2 / 3.2 | 8.1 / 3.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.4 / 2.9 | 6.5 / 4.1 | 8.3 / 4.9 | 9.5 / 5.4 |
| E3 | rotation [deg], every scale, mean / median | 0.44 / 0.24 | 0.59 / 0.31 | 0.71 / 0.35 | 0.79 / 0.39 |
| E3p2 | anchors | 4682 | 4690 | 4692 | 4692 |
| E3p2 | counted steps per anchor, median | 15 | 30 | 44 | 56 |
| E3p2 | position [mm], oracle (tiles), mean / median | 4.6 / 2.5 | 6.4 / 3.2 | 7.5 / 3.6 | 8.4 / 4.0 |
| E3p2 | position [mm], Bnet+Acheck, mean / median | 4.9 / 3.2 | 7.2 / 4.6 | 8.9 / 5.7 | 10.0 / 6.4 |
| E3p2 | rotation [deg], every scale, mean / median | 0.57 / 0.31 | 0.81 / 0.39 | 1.01 / 0.44 | 1.20 / 0.48 |
| E3p1 | anchors | 4682 | 4690 | 4692 | 4692 |
| E3p1 | counted steps per anchor, median | 15 | 30 | 44 | 56 |
| E3p1 | position [mm], oracle (tiles), mean / median | 5.5 / 3.0 | 7.9 / 3.8 | 9.7 / 4.3 | 10.7 / 4.6 |
| E3p1 | position [mm], Bnet+Acheck, mean / median | 5.5 / 3.4 | 8.1 / 4.8 | 10.1 / 5.9 | 11.5 / 6.4 |
| E3p1 | rotation [deg], every scale, mean / median | 0.68 / 0.36 | 1.01 / 0.44 | 1.30 / 0.50 | 1.51 / 0.52 |

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

