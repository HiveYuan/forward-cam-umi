# exp032_adaptive_glove6_take2: report (variant main)

19 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.55 / 1.59 | 3.11 / 9.09 | 5.83 / 15.98 | 9.99 / 22.61 | 10.38 / 14.40 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.57 | 0.38 / 1.22 | 0.49 / 1.64 | 0.55 / 1.82 | 0.62 / 1.27 |

n [frame pairs]:

- static, E3: 0.08 s: 2213, 0.5 s: 1915, 1.0 s: 1633, 2.0 s: 1215, 6.67 s: 72
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.50 / 9.09 | 6.15 / 18.14 | 7.93 / 25.56 | 8.96 / 26.21 | 10.56 / 20.47 |
| E3 | Bnet+Acheck | 2.54 / 8.98 | 6.24 / 19.02 | 8.63 / 26.57 | 10.59 / 26.37 | 10.19 / 20.13 |

n [frame pairs]: 0.08 s: 2213, 0.5 s: 1915, 1.0 s: 1633, 2.0 s: 1215, 6.67 s: 72

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 19.9 | 86 | 100% |
| E3 | 0.14% | 15.6 | 60 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 19/19 | 19 | 2.7% | 12.2% | 2.7% | ep12, ep18 |
| E3 | Bnet+Acheck, without flagged | 17/19 | 17 | 2.6% | 9.3% | 2.6% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 19/19 | 19 | 2.7% | 12.2% | 2.7% |  |
| E3 | Bnet+Acheck, method A (check) | 2/19 | 2 | 35.2% | 44.7% | -35.2% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1212 | 1.1 / 3.4 | 1.8 / 5.3 | 2.5 / 7.3 | 3.7 / 9.6 | 4.6 / 12.7 | 5.2 / 14.1 | 6.0 / 13.9 | 4.6 / 10.4 |
| E3 | Bnet+Acheck | 1212 | 1.2 / 3.4 | 1.8 / 5.4 | 2.6 / 7.6 | 3.9 / 10.3 | 5.5 / 14.1 | 6.4 / 15.7 | 7.2 / 15.7 | 3.7 / 10.0 |

n [anchors counting the step]: 0.07 s: 1196, 0.13 s: 1180, 0.27 s: 1148, 0.53 s: 1084, 1.00 s: 974, 2.00 s: 774, 4.00 s: 389, 6.67 s: 13

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1212 | 0.14 / 0.40 | 0.21 / 0.57 | 0.29 / 0.80 | 0.41 / 0.99 | 0.52 / 1.36 | 0.58 / 1.46 | 0.64 / 1.66 | 0.65 / 1.36 |

n [anchors counting the step]: 0.07 s: 1196, 0.13 s: 1180, 0.27 s: 1148, 0.53 s: 1084, 1.00 s: 974, 2.00 s: 774, 4.00 s: 389, 6.67 s: 13

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1197 | 1198 | 1198 | 1198 |
| E3 | counted steps per anchor, median | 15 | 30 | 40 | 43 |
| E3 | position [mm], oracle (tiles), mean / median | 4.4 / 3.7 | 5.3 / 4.6 | 5.8 / 5.0 | 5.9 / 5.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.7 / 4.0 | 5.9 / 5.2 | 6.6 / 6.1 | 6.8 / 6.4 |
| E3 | rotation [deg], every scale, mean / median | 0.48 / 0.41 | 0.58 / 0.52 | 0.63 / 0.56 | 0.65 / 0.58 |

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

