# exp033_adaptive_glove7: report (variant main)

30 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.69 | 0.37 / 1.53 | 0.53 / 2.36 | 0.65 / 2.80 | 0.42 / 0.86 |

n [frame pairs]:

- static, E3: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.51 / 10.91 | 5.65 / 24.24 | 7.76 / 35.58 | 9.77 / 45.07 | 7.17 / 13.76 |
| E3 | Bnet+Acheck | 2.50 / 10.89 | 5.75 / 24.34 | 8.15 / 35.99 | 10.25 / 45.44 | 9.69 / 14.91 |

n [frame pairs]:

- E3 oracle (tiles): 0.08 s: 2371, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E3 Bnet+Acheck: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 14.2 | 43 | 100% |
| E3 | 0.17% | 12.5 | 45 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 3.2% | 9.4% | 0.2% | ep01, ep09, ep19, ep20, ep28 |
| E3 | Bnet+Acheck, without flagged | 25/30 | 23 | 3.0% | 10.6% | 0.3% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 30/30 | 28 | 3.2% | 9.4% | 0.2% |  |
| E3 | Bnet+Acheck, method A (check) | 11/30 | 11 | 6.8% | 16.4% | -4.0% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 989 | 1.2 / 3.9 | 1.7 / 5.9 | 2.3 / 7.6 | 3.2 / 11.3 | 4.0 / 14.3 | 5.2 / 15.4 | 6.0 / 20.5 | 4.6 / 7.9 |
| E3 | Bnet+Acheck | 989 | 1.2 / 3.9 | 1.7 / 5.8 | 2.3 / 7.5 | 3.2 / 11.5 | 4.3 / 14.6 | 5.4 / 17.5 | 6.3 / 26.7 | 5.4 / 13.9 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 989 | 0.14 / 0.46 | 0.20 / 0.64 | 0.28 / 0.84 | 0.37 / 1.22 | 0.52 / 1.59 | 0.65 / 2.14 | 0.58 / 2.67 | 0.46 / 0.76 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 978 | 979 | 979 | 979 |
| E3 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3 | position [mm], oracle (tiles), mean / median | 4.8 / 3.2 | 6.5 / 4.3 | 7.9 / 5.0 | 9.3 / 5.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.9 / 3.3 | 6.8 / 4.5 | 8.2 / 5.4 | 9.8 / 5.8 |
| E3 | rotation [deg], every scale, mean / median | 0.58 / 0.40 | 0.80 / 0.51 | 0.96 / 0.57 | 1.12 / 0.58 |

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

