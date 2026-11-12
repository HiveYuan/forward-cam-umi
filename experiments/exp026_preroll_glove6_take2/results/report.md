# exp026_preroll_glove6_take2: report (variant main)

19 segments. Runs: E1, E3, E3p2, E3p1 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.55 / 1.59 | 3.11 / 9.09 | 5.83 / 15.98 | 9.99 / 22.61 | 10.38 / 14.40 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.57 | 0.37 / 1.22 | 0.49 / 1.61 | 0.55 / 1.82 | 0.62 / 1.27 |
| E3p2 | 0.16 / 0.54 | 0.35 / 1.17 | 0.44 / 1.54 | 0.53 / 1.54 | 0.71 / 2.43 |
| E3p1 | 0.22 / 0.89 | 0.58 / 3.06 | 0.85 / 5.56 | 1.09 / 9.93 | 0.84 / 3.07 |

n [frame pairs]:

- static, E3, E3p2, E3p1: 0.08 s: 2213, 0.5 s: 1915, 1.0 s: 1633, 2.0 s: 1215, 6.67 s: 72
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.51 / 9.15 | 6.01 / 18.35 | 7.97 / 25.66 | 9.25 / 25.79 | 10.56 / 20.47 |
| E3 | Bnet+Acheck | 2.56 / 9.02 | 6.20 / 18.71 | 8.45 / 25.49 | 10.45 / 26.66 | 10.19 / 20.13 |
| E3p2 | oracle (tiles) | 2.41 / 8.51 | 5.47 / 18.27 | 7.04 / 22.65 | 8.13 / 22.33 | 12.32 / 36.41 |
| E3p2 | Bnet+Acheck | 2.53 / 8.68 | 5.93 / 22.50 | 8.00 / 39.56 | 9.88 / 35.86 | 11.94 / 38.36 |
| E3p1 | oracle (tiles) | 3.33 / 14.71 | 9.05 / 48.52 | 12.49 / 83.90 | 15.07 / 154.96 | 12.74 / 46.80 |
| E3p1 | Bnet+Acheck | 3.36 / 14.38 | 9.72 / 47.52 | 14.95 / 83.52 | 21.02 / 151.21 | 13.46 / 45.48 |

n [frame pairs]: 0.08 s: 2213, 0.5 s: 1915, 1.0 s: 1633, 2.0 s: 1215, 6.67 s: 72

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 19.9 | 86 | 100% |
| E3 | 0.14% | 18.7 | 64 | 87% |
| E3p2 | 0.09% | 13.9 | 44 | 85% |
| E3p1 | 0.45% | 11.5 | 37 | 84% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 19/19 | 19 | 3.8% | 13.0% | 2.6% | ep12, ep18 |
| E3 | Bnet+Acheck, without flagged | 17/19 | 17 | 3.4% | 10.7% | 2.2% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 19/19 | 19 | 3.8% | 13.0% | 2.6% |  |
| E3 | Bnet+Acheck, method A (check) | 2/19 | 2 | 35.2% | 44.7% | -35.2% |  |
| E3p2 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 19/19 | 19 | 3.9% | 12.8% | 2.3% | ep12, ep18 |
| E3p2 | Bnet+Acheck, without flagged | 17/19 | 17 | 3.7% | 12.4% | -1.0% |  |
| E3p2 | Bnet+Acheck, method Bnet (primary) | 19/19 | 19 | 3.9% | 12.8% | 2.3% |  |
| E3p2 | Bnet+Acheck, method A (check) | 2/19 | 2 | 35.1% | 42.5% | -35.1% |  |
| E3p1 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 19/19 | 19 | 10.7% | 16.2% | 3.7% | ep12 |
| E3p1 | Bnet+Acheck, without flagged | 18/19 | 18 | 10.0% | 16.3% | 3.2% |  |
| E3p1 | Bnet+Acheck, method Bnet (primary) | 19/19 | 19 | 10.7% | 16.2% | 3.7% |  |
| E3p1 | Bnet+Acheck, method A (check) | 1/19 | 1 | 26.1% | 26.1% | -26.1% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1212 | 1.1 / 3.4 | 1.8 / 5.4 | 2.5 / 7.3 | 3.8 / 9.6 | 4.7 / 12.7 | 5.4 / 13.9 | 5.7 / 13.9 | 4.6 / 10.4 |
| E3 | Bnet+Acheck | 1212 | 1.2 / 3.4 | 1.8 / 5.4 | 2.6 / 7.6 | 3.9 / 10.0 | 5.5 / 14.1 | 6.5 / 16.3 | 7.3 / 15.7 | 3.7 / 10.0 |
| E3p2 | oracle (tiles) | 1212 | 1.0 / 3.1 | 1.6 / 5.0 | 2.3 / 7.0 | 3.2 / 9.0 | 4.2 / 11.4 | 5.1 / 12.2 | 5.5 / 11.5 | 3.1 / 8.0 |
| E3p2 | Bnet+Acheck | 1212 | 1.1 / 3.5 | 1.8 / 5.6 | 2.6 / 8.6 | 3.6 / 12.4 | 4.9 / 16.3 | 6.1 / 18.7 | 6.7 / 16.5 | 2.8 / 7.7 |
| E3p1 | oracle (tiles) | 1212 | 1.5 / 5.5 | 2.4 / 8.8 | 3.7 / 12.6 | 5.3 / 20.5 | 7.6 / 31.7 | 10.9 / 43.6 | 13.3 / 39.2 | 14.8 / 22.2 |
| E3p1 | Bnet+Acheck | 1212 | 1.6 / 5.2 | 2.4 / 8.2 | 3.8 / 12.2 | 5.8 / 18.9 | 9.5 / 28.9 | 14.0 / 41.2 | 14.3 / 39.1 | 15.4 / 20.3 |

n [anchors counting the step]: 0.07 s: 1196, 0.13 s: 1180, 0.27 s: 1148, 0.53 s: 1084, 1.00 s: 974, 2.00 s: 774, 4.00 s: 389, 6.67 s: 13

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1212 | 0.14 / 0.39 | 0.21 / 0.57 | 0.29 / 0.81 | 0.39 / 0.98 | 0.51 / 1.33 | 0.59 / 1.45 | 0.61 / 1.65 | 0.65 / 1.36 |
| E3p2 | every scale | 1212 | 0.13 / 0.36 | 0.19 / 0.56 | 0.27 / 0.77 | 0.36 / 0.94 | 0.45 / 1.28 | 0.56 / 1.30 | 0.58 / 1.28 | 0.37 / 0.86 |
| E3p1 | every scale | 1212 | 0.20 / 0.62 | 0.30 / 0.96 | 0.44 / 1.45 | 0.63 / 2.55 | 0.90 / 4.46 | 1.11 / 7.41 | 1.53 / 6.62 | 2.24 / 3.16 |

n [anchors counting the step]: 0.07 s: 1196, 0.13 s: 1180, 0.27 s: 1148, 0.53 s: 1084, 1.00 s: 974, 2.00 s: 774, 4.00 s: 389, 6.67 s: 13

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1197 | 1198 | 1198 | 1198 |
| E3 | counted steps per anchor, median | 15 | 30 | 40 | 43 |
| E3 | position [mm], oracle (tiles), mean / median | 4.4 / 3.8 | 5.4 / 4.7 | 5.8 / 5.1 | 6.0 / 5.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.7 / 4.0 | 5.9 / 5.2 | 6.7 / 6.2 | 6.9 / 6.5 |
| E3 | rotation [deg], every scale, mean / median | 0.48 / 0.40 | 0.58 / 0.50 | 0.63 / 0.55 | 0.65 / 0.57 |
| E3p2 | anchors | 1197 | 1198 | 1198 | 1198 |
| E3p2 | counted steps per anchor, median | 15 | 30 | 40 | 43 |
| E3p2 | position [mm], oracle (tiles), mean / median | 4.1 / 3.3 | 4.9 / 4.4 | 5.3 / 4.9 | 5.5 / 5.2 |
| E3p2 | position [mm], Bnet+Acheck, mean / median | 5.4 / 3.6 | 7.3 / 4.9 | 8.2 / 5.7 | 8.4 / 6.2 |
| E3p2 | rotation [deg], every scale, mean / median | 0.45 / 0.37 | 0.54 / 0.47 | 0.58 / 0.51 | 0.59 / 0.52 |
| E3p1 | anchors | 1197 | 1198 | 1198 | 1198 |
| E3p1 | counted steps per anchor, median | 15 | 30 | 40 | 43 |
| E3p1 | position [mm], oracle (tiles), mean / median | 8.2 / 5.2 | 11.7 / 7.0 | 13.9 / 7.7 | 14.4 / 7.9 |
| E3p1 | position [mm], Bnet+Acheck, mean / median | 8.3 / 5.8 | 12.1 / 8.4 | 14.4 / 9.3 | 14.9 / 9.6 |
| E3p1 | rotation [deg], every scale, mean / median | 1.02 / 0.62 | 1.51 / 0.75 | 1.85 / 0.82 | 1.87 / 0.83 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 43 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 435 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 1200 | 0.13 / 0.40 | 2.0 / 6.3 |
| same tiles, dt 0.5 s | 951 | 0.22 / 1.09 | 3.6 / 17.1 |
| same tiles, dt 1.0 s | 648 | 0.25 / 1.00 | 4.5 / 14.4 |
| same tiles, dt 2.0 s | 141 | 0.35 / 1.16 | 6.3 / 15.6 |
| tile set changes between the ends | 1305 | 0.33 / 1.64 | 5.1 / 24.1 |

