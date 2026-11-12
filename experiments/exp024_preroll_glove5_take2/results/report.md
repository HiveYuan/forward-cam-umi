# exp024_preroll_glove5_take2: report (variant main)

66 segments. Runs: E1, E3, E3p2, E3p1 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.26 | 2.16 / 7.35 | 4.20 / 14.28 | 7.44 / 23.10 | 13.69 / 27.92 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.13 / 0.54 | 0.26 / 1.77 | 0.36 / 3.20 | 0.47 / 5.83 | 0.50 / 6.06 |
| E3p2 | 0.13 / 0.61 | 0.29 / 2.22 | 0.42 / 3.88 | 0.54 / 6.70 | 0.55 / 11.15 |
| E3p1 | 0.13 / 0.56 | 0.29 / 1.66 | 0.40 / 2.58 | 0.53 / 3.92 | 0.50 / 2.10 |

n [frame pairs]:

- static, E3, E3p2, E3p1: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.99 / 8.79 | 4.21 / 29.85 | 5.84 / 52.18 | 7.18 / 94.93 | 8.14 / 101.43 |
| E3 | Bnet+Acheck | 2.04 / 10.05 | 4.53 / 33.78 | 6.94 / 62.46 | 9.76 / 96.73 | 10.60 / 125.32 |
| E3p2 | oracle (tiles) | 2.08 / 10.11 | 4.66 / 35.40 | 6.61 / 61.44 | 8.16 / 99.80 | 8.15 / 166.72 |
| E3p2 | Bnet+Acheck | 2.13 / 9.47 | 5.03 / 34.78 | 7.54 / 58.98 | 9.86 / 99.74 | 10.53 / 173.85 |
| E3p1 | oracle (tiles) | 2.08 / 9.14 | 4.67 / 27.97 | 6.56 / 45.89 | 7.91 / 78.76 | 7.34 / 37.22 |
| E3p1 | Bnet+Acheck | 2.09 / 8.48 | 5.11 / 26.34 | 7.89 / 43.08 | 10.58 / 65.68 | 12.16 / 41.37 |

n [frame pairs]:

- E3 oracle (tiles), E3 Bnet+Acheck, E3p2 Bnet+Acheck, E3p1 Bnet+Acheck: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253
- E3p2 oracle (tiles), E3p1 oracle (tiles): 0.08 s: 8896, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 17.5 | 52 | 100% |
| E3 | 0.30% | 16.3 | 56 | 88% |
| E3p2 | 0.28% | 12.1 | 41 | 88% |
| E3p1 | 0.34% | 11.3 | 37 | 87% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 66/66 | 65 | 6.5% | 25.3% | 5.6% | ep04, ep11, ep25, ep28, ep38 |
| E3 | Bnet+Acheck, without flagged | 61/66 | 60 | 6.6% | 25.1% | 5.7% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 66/66 | 65 | 6.5% | 25.3% | 5.6% |  |
| E3 | Bnet+Acheck, method A (check) | 8/66 | 8 | 7.8% | 58.4% | -6.0% |  |
| E3p2 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 66/66 | 63 | 7.1% | 28.7% | 2.9% | ep09 |
| E3p2 | Bnet+Acheck, without flagged | 65/66 | 62 | 7.2% | 29.6% | 3.0% |  |
| E3p2 | Bnet+Acheck, method Bnet (primary) | 66/66 | 63 | 7.1% | 28.7% | 2.9% |  |
| E3p2 | Bnet+Acheck, method A (check) | 4/66 | 4 | 10.7% | 15.3% | -10.7% |  |
| E3p1 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 66/66 | 63 | 7.8% | 28.3% | 4.3% | ep09, ep15, ep38 |
| E3p1 | Bnet+Acheck, without flagged | 63/66 | 60 | 7.7% | 27.9% | 4.7% |  |
| E3p1 | Bnet+Acheck, method Bnet (primary) | 66/66 | 63 | 7.8% | 28.3% | 4.3% |  |
| E3p1 | Bnet+Acheck, method A (check) | 4/66 | 4 | 15.6% | 49.4% | -15.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 4616 | 0.8 / 3.0 | 1.2 / 4.8 | 1.7 / 7.5 | 2.4 / 11.7 | 3.5 / 16.8 | 4.6 / 24.1 | 5.8 / 22.4 | 5.3 / 16.7 |
| E3 | Bnet+Acheck | 4616 | 0.9 / 3.1 | 1.3 / 5.0 | 1.9 / 8.0 | 2.9 / 12.6 | 4.4 / 19.3 | 6.4 / 27.4 | 8.8 / 28.8 | 8.5 / 24.1 |
| E3p2 | oracle (tiles) | 4616 | 0.9 / 3.4 | 1.3 / 5.4 | 1.8 / 8.4 | 2.7 / 13.3 | 3.8 / 20.4 | 4.9 / 26.6 | 5.9 / 34.6 | 5.7 / 44.2 |
| E3p2 | Bnet+Acheck | 4616 | 0.9 / 3.3 | 1.4 / 5.3 | 1.9 / 8.5 | 3.1 / 13.7 | 4.5 / 22.5 | 6.1 / 29.0 | 7.9 / 31.8 | 7.8 / 52.0 |
| E3p1 | oracle (tiles) | 4616 | 0.9 / 3.1 | 1.3 / 5.0 | 1.8 / 7.5 | 2.7 / 11.8 | 3.8 / 17.7 | 4.6 / 26.0 | 5.5 / 28.7 | 5.0 / 10.2 |
| E3p1 | Bnet+Acheck | 4616 | 0.9 / 2.8 | 1.4 / 4.6 | 2.0 / 7.1 | 3.2 / 11.2 | 5.0 / 16.2 | 7.3 / 23.0 | 9.8 / 25.2 | 9.4 / 20.6 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 4616 | 0.11 / 0.34 | 0.15 / 0.53 | 0.20 / 0.82 | 0.28 / 1.23 | 0.38 / 1.69 | 0.49 / 2.25 | 0.60 / 2.35 | 0.55 / 1.81 |
| E3p2 | every scale | 4616 | 0.11 / 0.41 | 0.17 / 0.64 | 0.23 / 0.99 | 0.33 / 1.63 | 0.47 / 2.51 | 0.59 / 3.65 | 0.70 / 4.71 | 0.65 / 9.34 |
| E3p1 | every scale | 4616 | 0.11 / 0.35 | 0.16 / 0.53 | 0.22 / 0.83 | 0.31 / 1.30 | 0.43 / 1.81 | 0.55 / 2.61 | 0.60 / 2.77 | 0.54 / 1.36 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 4564 | 4571 | 4572 | 4572 |
| E3 | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3 | position [mm], oracle (tiles), mean / median | 4.5 / 2.5 | 6.3 / 3.4 | 7.4 / 4.0 | 8.0 / 4.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 18.6 / 2.9 | 28.1 / 4.1 | 32.5 / 4.9 | 33.7 / 5.9 |
| E3 | rotation [deg], every scale, mean / median | 0.52 / 0.28 | 0.71 / 0.37 | 0.84 / 0.43 | 0.91 / 0.48 |
| E3p2 | anchors | 4564 | 4571 | 4572 | 4572 |
| E3p2 | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3p2 | position [mm], oracle (tiles), mean / median | 5.0 / 2.7 | 7.0 / 3.6 | 8.1 / 4.1 | 8.9 / 4.6 |
| E3p2 | position [mm], Bnet+Acheck, mean / median | 5.1 / 3.1 | 7.2 / 4.1 | 8.6 / 4.8 | 9.4 / 5.4 |
| E3p2 | rotation [deg], every scale, mean / median | 0.60 / 0.33 | 0.84 / 0.43 | 1.01 / 0.49 | 1.12 / 0.52 |
| E3p1 | anchors | 4564 | 4571 | 4572 | 4572 |
| E3p1 | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3p1 | position [mm], oracle (tiles), mean / median | 4.7 / 2.6 | 6.5 / 3.5 | 7.8 / 4.1 | 8.6 / 4.5 |
| E3p1 | position [mm], Bnet+Acheck, mean / median | 4.6 / 3.1 | 6.5 / 4.6 | 8.0 / 5.6 | 8.9 / 6.7 |
| E3p1 | rotation [deg], every scale, mean / median | 0.52 / 0.31 | 0.71 / 0.40 | 0.83 / 0.47 | 0.89 / 0.51 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 52 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 632 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 1611 | 0.14 / 1.29 | 2.3 / 23.7 |
| same tiles, dt 0.5 s | 1074 | 0.22 / 1.63 | 3.9 / 35.6 |
| same tiles, dt 1.0 s | 786 | 0.30 / 1.46 | 5.4 / 37.5 |
| same tiles, dt 2.0 s | 579 | 0.42 / 3.20 | 8.1 / 63.4 |
| tile set changes between the ends | 1896 | 0.43 / 3.68 | 7.5 / 67.6 |

