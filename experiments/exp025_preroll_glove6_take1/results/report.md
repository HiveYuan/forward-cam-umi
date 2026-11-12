# exp025_preroll_glove6_take1: report (variant main)

29 segments. Runs: E1, E3, E3p2, E3p1 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.50 / 1.39 | 2.83 / 7.41 | 5.17 / 11.09 | 7.62 / 16.76 | 12.55 / 17.87 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.15 / 0.54 | 0.29 / 1.01 | 0.32 / 1.05 | 0.36 / 1.03 | 0.41 / 1.28 |
| E3p2 | 0.16 / 0.64 | 0.33 / 1.50 | 0.38 / 2.30 | 0.42 / 3.43 | 0.68 / 6.81 |
| E3p1 | 0.17 / 0.67 | 0.37 / 1.87 | 0.45 / 3.15 | 0.51 / 5.01 | 0.64 / 7.07 |

n [frame pairs]:

- static, E3, E3p2, E3p1: 0.08 s: 3485, 0.5 s: 2927, 1.0 s: 2454, 2.0 s: 1704, 6.67 s: 213
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.32 / 8.61 | 4.55 / 17.35 | 5.13 / 17.59 | 5.67 / 15.93 | 7.17 / 20.36 |
| E3 | Bnet+Acheck | 2.40 / 8.75 | 5.26 / 17.99 | 6.82 / 21.20 | 8.98 / 21.74 | 11.58 / 30.51 |
| E3p2 | oracle (tiles) | 2.46 / 10.01 | 5.27 / 23.23 | 5.95 / 31.30 | 6.43 / 44.35 | 10.23 / 88.80 |
| E3p2 | Bnet+Acheck | 2.51 / 9.93 | 5.96 / 23.27 | 7.67 / 31.13 | 10.13 / 44.50 | 16.73 / 86.70 |
| E3p1 | oracle (tiles) | 2.66 / 10.62 | 5.91 / 27.94 | 6.85 / 44.45 | 7.50 / 65.69 | 8.34 / 90.90 |
| E3p1 | Bnet+Acheck | 2.70 / 10.68 | 6.76 / 28.12 | 9.04 / 44.29 | 11.97 / 65.09 | 15.60 / 88.15 |

n [frame pairs]: 0.08 s: 3485, 0.5 s: 2927, 1.0 s: 2454, 2.0 s: 1704, 6.67 s: 213

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 18.1 | 56 | 100% |
| E3 | 0.26% | 16.3 | 59 | 86% |
| E3p2 | 0.46% | 12.3 | 43 | 84% |
| E3p1 | 0.46% | 11.2 | 38 | 84% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 29/29 | 29 | 5.4% | 13.2% | 4.6% | ep06, ep14, ep19, ep23 |
| E3 | Bnet+Acheck, without flagged | 25/29 | 25 | 6.1% | 13.3% | 5.8% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 29/29 | 29 | 5.4% | 13.2% | 4.6% |  |
| E3 | Bnet+Acheck, method A (check) | 8/29 | 8 | 12.1% | 36.8% | -12.1% |  |
| E3p2 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 29/29 | 29 | 7.6% | 13.6% | 4.2% | ep14, ep19, ep23, ep25 |
| E3p2 | Bnet+Acheck, without flagged | 25/29 | 25 | 7.9% | 12.3% | 4.2% |  |
| E3p2 | Bnet+Acheck, method Bnet (primary) | 29/29 | 29 | 7.6% | 13.6% | 4.2% |  |
| E3p2 | Bnet+Acheck, method A (check) | 6/29 | 6 | 23.7% | 44.8% | -23.7% |  |
| E3p1 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 29/29 | 29 | 5.8% | 14.5% | 4.8% | ep14 |
| E3p1 | Bnet+Acheck, without flagged | 28/29 | 28 | 6.0% | 14.6% | 4.8% |  |
| E3p1 | Bnet+Acheck, method Bnet (primary) | 29/29 | 29 | 5.8% | 14.5% | 4.8% |  |
| E3p1 | Bnet+Acheck, method A (check) | 3/29 | 3 | 3.3% | 24.5% | -0.3% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1643 | 1.1 / 3.3 | 1.5 / 4.9 | 2.1 / 6.6 | 2.7 / 8.0 | 3.1 / 9.1 | 3.5 / 9.2 | 4.3 / 9.7 | 4.4 / 8.3 |
| E3 | Bnet+Acheck | 1643 | 1.2 / 3.5 | 1.7 / 5.2 | 2.5 / 7.3 | 3.7 / 9.7 | 5.1 / 13.7 | 7.5 / 18.3 | 9.3 / 22.8 | 9.7 / 15.2 |
| E3p2 | oracle (tiles) | 1643 | 1.1 / 3.6 | 1.6 / 5.2 | 2.2 / 6.9 | 2.9 / 9.1 | 3.5 / 10.8 | 3.8 / 13.9 | 4.6 / 11.1 | 4.9 / 25.1 |
| E3p2 | Bnet+Acheck | 1643 | 1.2 / 3.6 | 1.7 / 5.3 | 2.6 / 7.3 | 4.0 / 10.3 | 5.8 / 14.1 | 8.6 / 20.1 | 9.9 / 21.5 | 12.6 / 27.7 |
| E3p1 | oracle (tiles) | 1643 | 1.2 / 4.0 | 1.7 / 5.8 | 2.4 / 7.8 | 3.3 / 10.7 | 4.0 / 15.0 | 4.4 / 20.5 | 5.3 / 13.1 | 5.0 / 28.5 |
| E3p1 | Bnet+Acheck | 1643 | 1.3 / 4.0 | 1.8 / 5.8 | 2.8 / 7.9 | 4.5 / 11.5 | 6.8 / 16.9 | 9.3 / 25.0 | 10.0 / 27.6 | 16.4 / 27.6 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| E3p2 | every scale | 1643 | 0.13 / 0.38 | 0.18 / 0.54 | 0.25 / 0.72 | 0.32 / 0.92 | 0.38 / 1.15 | 0.43 / 1.29 | 0.57 / 1.22 | 0.68 / 5.94 |
| E3p1 | every scale | 1643 | 0.14 / 0.45 | 0.19 / 0.63 | 0.27 / 0.89 | 0.36 / 1.31 | 0.44 / 2.13 | 0.52 / 3.33 | 0.63 / 1.64 | 0.66 / 6.58 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1619 | 1624 | 1624 | 1624 |
| E3 | counted steps per anchor, median | 15 | 30 | 35 | 43 |
| E3 | position [mm], oracle (tiles), mean / median | 3.7 / 2.9 | 4.3 / 3.5 | 4.6 / 3.8 | 4.9 / 4.0 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.7 / 3.8 | 6.2 / 5.2 | 7.2 / 6.1 | 7.6 / 6.4 |
| E3 | rotation [deg], every scale, mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| E3p2 | anchors | 1619 | 1624 | 1624 | 1624 |
| E3p2 | counted steps per anchor, median | 15 | 30 | 35 | 43 |
| E3p2 | position [mm], oracle (tiles), mean / median | 4.0 / 3.1 | 4.8 / 3.7 | 5.3 / 4.0 | 5.6 / 4.2 |
| E3p2 | position [mm], Bnet+Acheck, mean / median | 4.9 / 4.0 | 6.5 / 5.4 | 7.6 / 6.6 | 8.0 / 7.1 |
| E3p2 | rotation [deg], every scale, mean / median | 0.48 / 0.33 | 0.58 / 0.39 | 0.66 / 0.44 | 0.69 / 0.46 |
| E3p1 | anchors | 1619 | 1624 | 1624 | 1624 |
| E3p1 | counted steps per anchor, median | 15 | 30 | 35 | 43 |
| E3p1 | position [mm], oracle (tiles), mean / median | 4.7 / 3.4 | 5.8 / 4.2 | 6.4 / 4.5 | 6.6 / 4.8 |
| E3p1 | position [mm], Bnet+Acheck, mean / median | 5.5 / 4.5 | 7.5 / 6.0 | 8.8 / 6.9 | 9.2 / 7.2 |
| E3p1 | rotation [deg], every scale, mean / median | 0.58 / 0.36 | 0.72 / 0.44 | 0.81 / 0.49 | 0.83 / 0.51 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 43 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 265 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 678 | 0.14 / 0.44 | 2.2 / 7.0 |
| same tiles, dt 0.5 s | 462 | 0.22 / 1.14 | 3.6 / 14.2 |
| same tiles, dt 1.0 s | 297 | 0.27 / 0.93 | 4.2 / 11.7 |
| same tiles, dt 2.0 s | 174 | 0.24 / 1.19 | 3.5 / 23.2 |
| tile set changes between the ends | 795 | 0.44 / 2.06 | 6.4 / 36.4 |

