# col011_yuan_slam_05: report (variant main)

35 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.34 / 1.19 | 1.48 / 5.44 | 2.81 / 10.02 | 5.17 / 14.55 | 8.16 / 13.60 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.17 / 0.78 | 0.23 / 1.40 | 0.27 / 2.18 | 0.33 / 2.94 | 1.54 / 3.97 |

n [frame pairs]:

- static, E3: 0.08 s: 2582, 0.5 s: 2173, 1.0 s: 1846, 2.0 s: 1437, 6.67 s: 86
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.34 / 9.24 | 3.19 / 18.21 | 3.79 / 26.61 | 4.49 / 35.48 | 22.34 / 60.12 |
| E3 | Bnet+Acheck | 2.28 / 9.23 | 3.55 / 18.41 | 4.56 / 27.28 | 5.76 / 41.65 | 21.36 / 44.85 |

n [frame pairs]:

- E3 oracle (tiles): 0.08 s: 2566, 0.5 s: 2168, 1.0 s: 1843, 2.0 s: 1437, 6.67 s: 86
- E3 Bnet+Acheck: 0.08 s: 2582, 0.5 s: 2173, 1.0 s: 1846, 2.0 s: 1437, 6.67 s: 86

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 14.2 | 32 | 100% |
| E3 | 0.97% | 11.7 | 26 | 82% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 35/35 | 29 | 20.8% | 57.8% | -17.3% | ep02, ep05, ep06, ep07, ep08, ep13, ep19, ep21, ep31, ep36, ep37 |
| E3 | Bnet+Acheck, without flagged | 24/35 | 18 | 16.0% | 61.8% | -10.1% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 35/35 | 29 | 20.8% | 57.8% | -17.3% |  |
| E3 | Bnet+Acheck, method A (check) | 14/35 | 13 | 8.9% | 21.3% | 2.4% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1250 | 1.2 / 3.5 | 1.4 / 5.0 | 1.8 / 7.3 | 2.3 / 9.3 | 2.9 / 13.7 | 3.7 / 17.9 | 3.7 / 28.3 | 4.3 / 28.5 |
| E3 | Bnet+Acheck | 1250 | 1.2 / 3.4 | 1.5 / 5.2 | 2.0 / 7.5 | 2.6 / 10.5 | 3.7 / 15.2 | 4.6 / 21.4 | 5.1 / 34.1 | 8.3 / 27.4 |

n [anchors counting the step]: 0.07 s: 1227, 0.13 s: 1204, 0.27 s: 1159, 0.53 s: 1082, 1.00 s: 1004, 2.00 s: 845, 4.00 s: 479, 6.67 s: 96

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1250 | 0.14 / 0.43 | 0.17 / 0.60 | 0.19 / 0.84 | 0.24 / 1.22 | 0.29 / 1.70 | 0.35 / 2.41 | 0.44 / 3.10 | 0.52 / 3.70 |

n [anchors counting the step]: 0.07 s: 1227, 0.13 s: 1204, 0.27 s: 1159, 0.53 s: 1082, 1.00 s: 1004, 2.00 s: 845, 4.00 s: 479, 6.67 s: 96

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1237 | 1237 | 1237 | 1237 |
| E3 | counted steps per anchor, median | 15 | 30 | 42 | 48 |
| E3 | position [mm], oracle (tiles), mean / median | 4.1 / 2.5 | 5.3 / 2.9 | 6.0 / 3.1 | 6.6 / 3.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.6 / 2.8 | 6.3 / 3.5 | 7.5 / 4.0 | 8.5 / 4.6 |
| E3 | rotation [deg], every scale, mean / median | 0.50 / 0.26 | 0.63 / 0.30 | 0.72 / 0.34 | 0.78 / 0.37 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 48 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 6 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 9 | 0.15 / 0.36 | 1.8 / 3.7 |
| tile set changes between the ends | 18 | 0.35 / 1.61 | 4.6 / 17.3 |

