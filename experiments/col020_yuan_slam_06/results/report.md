# col020_yuan_slam_06: report (variant main)

42 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.36 / 1.14 | 1.71 / 5.25 | 3.29 / 9.33 | 6.56 / 14.30 | 9.95 / 14.67 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 1.23 | 0.20 / 1.92 | 0.24 / 2.34 | 0.30 / 3.18 | 0.31 / 2.21 |

n [frame pairs]:

- static, E3: 0.08 s: 2973, 0.5 s: 2504, 1.0 s: 2119, 2.0 s: 1656, 6.67 s: 128
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.09 / 14.00 | 2.79 / 23.03 | 3.49 / 27.10 | 4.19 / 32.39 | 5.86 / 29.82 |
| E3 | Bpar+Acheck | 2.09 / 15.87 | 3.05 / 25.28 | 3.98 / 29.95 | 5.27 / 35.37 | 5.96 / 29.31 |

n [frame pairs]: 0.08 s: 2973, 0.5 s: 2504, 1.0 s: 2119, 2.0 s: 1656, 6.67 s: 128

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 13.2 | 28 | 100% |
| E3 | 3.09% | 11.0 | 24 | 82% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bpar+Acheck (flag \|check/primary - 1\| > 10%) | 42/42 | 34 | 10.4% | 50.5% | -6.3% | ep00, ep04, ep05, ep20, ep22, ep24, ep32, ep33, ep35, ep42 |
| E3 | Bpar+Acheck, without flagged | 32/42 | 25 | 9.9% | 50.5% | -6.3% |  |
| E3 | Bpar+Acheck, method Bpar (primary) | 42/42 | 34 | 10.4% | 50.5% | -6.3% |  |
| E3 | Bpar+Acheck, method A (check) | 21/42 | 20 | 11.2% | 26.1% | 6.0% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1730 | 1.1 / 4.2 | 1.3 / 5.9 | 1.5 / 7.8 | 1.9 / 9.4 | 2.5 / 14.8 | 3.1 / 16.1 | 3.3 / 18.7 | 5.0 / 22.0 |
| E3 | Bpar+Acheck | 1730 | 1.1 / 4.2 | 1.3 / 5.8 | 1.7 / 7.6 | 2.2 / 9.1 | 3.1 / 14.7 | 4.4 / 17.5 | 5.5 / 18.2 | 7.8 / 21.3 |

n [anchors counting the step]: 0.07 s: 1696, 0.13 s: 1665, 0.27 s: 1604, 0.53 s: 1503, 1.00 s: 1367, 2.00 s: 1147, 4.00 s: 663, 6.67 s: 130

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1730 | 0.14 / 0.58 | 0.16 / 0.85 | 0.18 / 1.05 | 0.21 / 1.14 | 0.26 / 1.70 | 0.33 / 1.86 | 0.38 / 1.84 | 0.35 / 2.10 |

n [anchors counting the step]: 0.07 s: 1696, 0.13 s: 1665, 0.27 s: 1604, 0.53 s: 1503, 1.00 s: 1367, 2.00 s: 1147, 4.00 s: 663, 6.67 s: 130

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1711 | 1711 | 1712 | 1712 |
| E3 | counted steps per anchor, median | 15 | 30 | 42 | 48 |
| E3 | position [mm], oracle (tiles), mean / median | 5.0 / 2.1 | 6.4 / 2.5 | 7.0 / 2.8 | 7.2 / 2.9 |
| E3 | position [mm], Bpar+Acheck, mean / median | 5.4 / 2.4 | 6.8 / 3.2 | 7.5 / 3.9 | 7.8 / 4.2 |
| E3 | rotation [deg], every scale, mean / median | 0.71 / 0.24 | 0.89 / 0.29 | 0.94 / 0.33 | 0.91 / 0.35 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 48 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 16 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 27 | 0.24 / 0.57 | 2.7 / 5.9 |
| tile set changes between the ends | 48 | 0.78 / 1.32 | 8.2 / 15.9 |

