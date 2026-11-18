# col013_yuan_slam_01: report (variant main)

8 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.43 / 1.84 | 1.80 / 10.26 | 3.67 / 15.17 | 7.35 / 17.17 | 7.07 / 8.18 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.19 / 1.14 | 0.27 / 5.38 | 0.38 / 8.35 | 0.49 / 11.91 | 4.86 / 8.98 |

n [frame pairs]:

- static, E3: 0.08 s: 485, 0.5 s: 362, 1.0 s: 270, 2.0 s: 114, 6.67 s: 38
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.95 / 10.01 | 3.06 / 45.96 | 3.80 / 69.56 | 4.83 / 100.31 | 39.88 / 80.65 |
| E3 | Bpar+Acheck | 2.23 / 18.95 | 3.23 / 78.98 | 4.22 / 166.73 | 5.43 / 201.68 | 101.37 / 130.61 |

n [frame pairs]: 0.08 s: 485, 0.5 s: 362, 1.0 s: 270, 2.0 s: 114, 6.67 s: 38

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 18.4 | 50 | 100% |
| E3 | 2.27% | 15.4 | 53 | 78% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bpar+Acheck (flag \|check/primary - 1\| > 10%) | 8/8 | 8 | 9.4% | 115.8% | 2.3% | ep03, ep07 |
| E3 | Bpar+Acheck, without flagged | 6/8 | 6 | 5.6% | 178.3% | 2.3% |  |
| E3 | Bpar+Acheck, method Bpar (primary) | 8/8 | 8 | 9.4% | 115.8% | 2.3% |  |
| E3 | Bpar+Acheck, method A (check) | 4/8 | 4 | 4.6% | 21.1% | 4.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors |
|---|---|---|
| E3 | oracle (tiles) | 0 |
| E3 | Bpar+Acheck | 0 |

n [anchors counting the step]: 

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90

| run | scale | anchors |
|---|---|---|
| E3 | oracle (tiles) | 0 |
| E3 | Bpar+Acheck | 0 |

n [anchors counting the step]: 

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 0 | 0 | 0 | 0 |
| E3 | position [mm], oracle (tiles), mean / median | - / - | - / - | - / - | - / - |
| E3 | position [mm], Bpar+Acheck, mean / median | - / - | - / - | - / - | - / - |
| E3 | rotation [deg], every scale, mean / median | - / - | - / - | - / - | - / - |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the number of counted steps per anchor is not recorded in labels_*.json (the by-step tables' n says how many anchors count step j).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 1 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| tile set changes between the ends | 3 | 2.26 / 2.48 | 28.9 / 46.5 |

