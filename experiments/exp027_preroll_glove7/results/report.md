# exp027_preroll_glove7: report (variant main)

30 segments. Runs: E1, E3, E3p2, E3p1 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3p2 | 0.17 / 0.74 | 0.39 / 1.62 | 0.57 / 2.52 | 0.75 / 3.42 | 0.56 / 1.54 |
| E3p1 | 0.17 / 0.65 | 0.38 / 1.42 | 0.54 / 1.95 | 0.68 / 2.53 | 0.40 / 0.94 |

n [frame pairs]:

- static, E3, E3p2, E3p1: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3 | Bnet+Acheck | 2.48 / 10.02 | 5.47 / 24.29 | 7.81 / 36.32 | 10.37 / 45.44 | 9.69 / 17.96 |
| E3p2 | oracle (tiles) | 2.53 / 10.46 | 5.91 / 24.47 | 8.50 / 36.81 | 11.38 / 50.44 | 10.31 / 22.17 |
| E3p2 | Bnet+Acheck | 2.55 / 10.35 | 5.99 / 23.78 | 8.86 / 35.32 | 12.35 / 50.73 | 9.89 / 31.59 |
| E3p1 | oracle (tiles) | 2.61 / 9.70 | 5.79 / 22.29 | 7.83 / 28.78 | 10.00 / 35.73 | 7.78 / 16.09 |
| E3p1 | Bnet+Acheck | 2.59 / 9.89 | 6.09 / 22.58 | 8.69 / 29.91 | 11.99 / 36.45 | 10.57 / 16.59 |

n [frame pairs]:

- E3 oracle (tiles), E3p2 oracle (tiles): 0.08 s: 2371, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E3 Bnet+Acheck, E3p2 Bnet+Acheck, E3p1 Bnet+Acheck: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E3p1 oracle (tiles): 0.08 s: 2347, 0.5 s: 1921, 1.0 s: 1603, 2.0 s: 1248, 6.67 s: 88

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 14.2 | 43 | 100% |
| E3 | 0.17% | 12.8 | 47 | 86% |
| E3p2 | 0.42% | 10.4 | 34 | 85% |
| E3p1 | 0.00% | 9.9 | 29 | 85% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 3.1% | 9.4% | -0.1% | ep01, ep09, ep19, ep20, ep28, ep29 |
| E3 | Bnet+Acheck, without flagged | 24/30 | 22 | 3.0% | 6.9% | 0.2% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 30/30 | 28 | 3.1% | 9.4% | -0.1% |  |
| E3 | Bnet+Acheck, method A (check) | 11/30 | 11 | 6.8% | 19.0% | -4.6% |  |
| E3p2 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 24 | 6.1% | 19.5% | -1.2% | ep09, ep10, ep12, ep29 |
| E3p2 | Bnet+Acheck, without flagged | 26/30 | 20 | 5.6% | 17.1% | -1.2% |  |
| E3p2 | Bnet+Acheck, method Bnet (primary) | 30/30 | 24 | 6.1% | 19.5% | -1.2% |  |
| E3p2 | Bnet+Acheck, method A (check) | 10/30 | 10 | 6.9% | 28.4% | -1.3% |  |
| E3p1 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 23 | 3.8% | 15.6% | 1.3% | ep15, ep25, ep27 |
| E3p1 | Bnet+Acheck, without flagged | 27/30 | 20 | 3.7% | 15.5% | 1.6% |  |
| E3p1 | Bnet+Acheck, method Bnet (primary) | 30/30 | 23 | 3.8% | 15.6% | 1.3% |  |
| E3p1 | Bnet+Acheck, method A (check) | 5/30 | 5 | 23.5% | 29.7% | 15.4% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3 | Bnet+Acheck | 989 | 1.2 / 3.5 | 1.6 / 5.7 | 2.3 / 7.4 | 3.2 / 10.9 | 4.2 / 14.2 | 5.4 / 16.1 | 6.1 / 18.8 | 5.4 / 10.4 |
| E3p2 | oracle (tiles) | 989 | 1.2 / 3.7 | 1.6 / 5.6 | 2.3 / 7.9 | 3.3 / 11.2 | 4.6 / 14.2 | 6.5 / 17.0 | 6.6 / 18.2 | 5.6 / 12.5 |
| E3p2 | Bnet+Acheck | 989 | 1.2 / 3.7 | 1.7 / 5.9 | 2.3 / 7.8 | 3.4 / 11.1 | 4.9 / 16.4 | 7.4 / 19.5 | 7.7 / 24.5 | 5.9 / 20.3 |
| E3p1 | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.3 | 2.3 / 7.3 | 3.1 / 9.6 | 4.3 / 13.0 | 5.7 / 14.1 | 6.4 / 12.6 | 4.9 / 8.4 |
| E3p1 | Bnet+Acheck | 989 | 1.2 / 3.6 | 1.7 / 5.3 | 2.4 / 7.3 | 3.4 / 10.5 | 4.9 / 13.4 | 7.0 / 16.0 | 7.5 / 18.1 | 7.2 / 12.3 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3p2 | every scale | 989 | 0.14 / 0.43 | 0.20 / 0.64 | 0.28 / 0.91 | 0.41 / 1.28 | 0.59 / 1.78 | 0.81 / 2.45 | 0.69 / 2.61 | 0.57 / 1.31 |
| E3p1 | every scale | 989 | 0.13 / 0.39 | 0.20 / 0.58 | 0.27 / 0.76 | 0.36 / 1.07 | 0.49 / 1.39 | 0.65 / 1.82 | 0.69 / 1.41 | 0.49 / 0.91 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 978 | 979 | 979 | 979 |
| E3 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3 | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.8 / 3.2 | 6.6 / 4.3 | 8.0 / 5.3 | 9.4 / 5.8 |
| E3 | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3p2 | anchors | 978 | 979 | 979 | 979 |
| E3p2 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3p2 | position [mm], oracle (tiles), mean / median | 4.8 / 3.3 | 6.3 / 4.9 | 7.2 / 5.6 | 7.9 / 6.0 |
| E3p2 | position [mm], Bnet+Acheck, mean / median | 4.9 / 3.6 | 6.5 / 5.3 | 7.6 / 6.3 | 8.5 / 7.0 |
| E3p2 | rotation [deg], every scale, mean / median | 0.57 / 0.42 | 0.75 / 0.56 | 0.83 / 0.61 | 0.90 / 0.64 |
| E3p1 | anchors | 978 | 979 | 979 | 979 |
| E3p1 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3p1 | position [mm], oracle (tiles), mean / median | 4.2 / 3.2 | 5.4 / 4.4 | 6.1 / 5.4 | 6.5 / 5.8 |
| E3p1 | position [mm], Bnet+Acheck, mean / median | 4.6 / 3.4 | 6.0 / 4.9 | 7.0 / 6.0 | 7.7 / 6.9 |
| E3p1 | rotation [deg], every scale, mean / median | 0.48 / 0.37 | 0.60 / 0.49 | 0.67 / 0.55 | 0.71 / 0.59 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 49 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 40 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles, dt 0.5 s | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles, dt 2.0 s | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes between the ends | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

