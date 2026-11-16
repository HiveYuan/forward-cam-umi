# col003_yuan_pilot_01c: report (variant main)

8 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.64 / 1.80 | 3.27 / 10.51 | 6.76 / 17.93 | 10.26 / 23.93 | - / - |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.20 / 0.75 | 0.34 / 1.01 | 0.42 / 0.99 | 0.44 / 1.10 | - / - |

n [frame pairs]:

- static, E3: 0.08 s: 632, 0.5 s: 553, 1.0 s: 467, 2.0 s: 285, 6.67 s: 0
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.22 / 8.53 | 4.18 / 12.13 | 5.08 / 12.99 | 5.59 / 12.24 | - / - |
| E3 | Bnet+Acheck | 2.30 / 8.51 | 4.84 / 12.65 | 6.08 / 15.53 | 7.24 / 17.75 | - / - |

n [frame pairs]: 0.08 s: 632, 0.5 s: 553, 1.0 s: 467, 2.0 s: 285, 6.67 s: 0

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 18.1 | 38 | 100% |
| E3 | 0.16% | 14.6 | 36 | 82% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 8/8 | 8 | 6.0% | 16.0% | -4.5% | ep00, ep01, ep02, ep05 |
| E3 | Bnet+Acheck, without flagged | 4/8 | 4 | 6.0% | 7.5% | -3.6% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 8/8 | 8 | 6.0% | 16.0% | -4.5% |  |
| E3 | Bnet+Acheck, method A (check) | 4/8 | 4 | 14.0% | 28.3% | 11.0% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 149 | 1.3 / 4.3 | 1.7 / 5.1 | 2.2 / 6.4 | 3.3 / 7.0 | 3.4 / 7.0 | 3.9 / 8.3 | 2.6 / 7.9 |
| E3 | Bnet+Acheck | 149 | 1.3 / 4.3 | 1.7 / 5.3 | 2.3 / 6.5 | 3.7 / 7.4 | 4.6 / 8.4 | 6.6 / 9.7 | 4.9 / 9.8 |

n [anchors counting the step]: 0.07 s: 147, 0.13 s: 145, 0.27 s: 141, 0.53 s: 133, 1.00 s: 119, 2.00 s: 89, 4.00 s: 29

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 149 | 0.17 / 0.60 | 0.22 / 0.72 | 0.29 / 0.87 | 0.39 / 0.99 | 0.39 / 0.94 | 0.50 / 0.93 | 0.29 / 0.95 |

n [anchors counting the step]: 0.07 s: 147, 0.13 s: 145, 0.27 s: 141, 0.53 s: 133, 1.00 s: 119, 2.00 s: 89, 4.00 s: 29

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 147 | 147 | 147 | 147 |
| E3 | counted steps per anchor, median | 15 | 30 | 37 | 37 |
| E3 | position [mm], oracle (tiles), mean / median | 3.5 / 3.3 | 4.0 / 3.8 | 4.2 / 3.9 | 4.2 / 3.9 |
| E3 | position [mm], Bnet+Acheck, mean / median | 3.9 / 3.6 | 4.9 / 4.5 | 5.3 / 4.9 | 5.3 / 4.9 |
| E3 | rotation [deg], every scale, mean / median | 0.47 / 0.42 | 0.53 / 0.47 | 0.55 / 0.47 | 0.56 / 0.48 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 37 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 164 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 432 | 0.50 / 1.29 | 6.2 / 15.3 |
| same tiles, dt 0.5 s | 318 | 0.53 / 1.51 | 7.1 / 18.7 |
| same tiles, dt 1.0 s | 222 | 0.59 / 1.51 | 8.3 / 19.7 |
| same tiles, dt 2.0 s | 108 | 0.58 / 1.42 | 9.1 / 17.3 |
| tile set changes between the ends | 492 | 0.63 / 1.60 | 8.9 / 20.4 |

