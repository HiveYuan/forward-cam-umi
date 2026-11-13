# exp031_adaptive_glove6_take1: report (variant main)

29 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.50 / 1.39 | 2.83 / 7.41 | 5.17 / 11.09 | 7.62 / 16.76 | 12.55 / 17.87 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.15 / 0.54 | 0.29 / 1.02 | 0.34 / 1.09 | 0.38 / 1.11 | 0.44 / 1.20 |

n [frame pairs]:

- static, E3: 0.08 s: 3485, 0.5 s: 2927, 1.0 s: 2454, 2.0 s: 1704, 6.67 s: 213
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.32 / 8.55 | 4.58 / 17.58 | 5.29 / 17.95 | 5.89 / 16.69 | 6.65 / 18.77 |
| E3 | Bnet+Acheck | 2.37 / 8.76 | 5.06 / 18.13 | 6.44 / 20.76 | 8.17 / 21.64 | 10.05 / 20.43 |

n [frame pairs]: 0.08 s: 3485, 0.5 s: 2927, 1.0 s: 2454, 2.0 s: 1704, 6.67 s: 213

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 18.1 | 56 | 100% |
| E3 | 0.23% | 15.0 | 57 | 85% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 29/29 | 29 | 4.8% | 10.4% | 4.5% | ep06, ep14, ep19, ep23 |
| E3 | Bnet+Acheck, without flagged | 25/29 | 25 | 4.8% | 11.5% | 4.8% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 29/29 | 29 | 4.8% | 10.4% | 4.5% |  |
| E3 | Bnet+Acheck, method A (check) | 8/29 | 8 | 12.1% | 36.8% | -12.1% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1643 | 1.1 / 3.3 | 1.5 / 4.9 | 2.1 / 6.6 | 2.7 / 8.0 | 3.1 / 9.1 | 3.5 / 9.6 | 4.1 / 10.4 | 4.5 / 8.3 |
| E3 | Bnet+Acheck | 1643 | 1.1 / 3.4 | 1.6 / 5.2 | 2.3 / 7.2 | 3.4 / 9.5 | 4.6 / 12.7 | 6.7 / 16.8 | 7.9 / 20.0 | 9.0 / 13.7 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.67 | 0.30 / 0.81 | 0.34 / 0.96 | 0.38 / 1.07 | 0.52 / 1.27 | 0.46 / 1.13 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1619 | 1624 | 1624 | 1624 |
| E3 | counted steps per anchor, median | 15 | 30 | 35 | 43 |
| E3 | position [mm], oracle (tiles), mean / median | 3.7 / 2.9 | 4.3 / 3.5 | 4.7 / 3.8 | 4.9 / 4.0 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.5 / 3.5 | 5.8 / 4.7 | 6.6 / 5.5 | 7.0 / 6.1 |
| E3 | rotation [deg], every scale, mean / median | 0.43 / 0.31 | 0.49 / 0.38 | 0.54 / 0.41 | 0.56 / 0.45 |

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

