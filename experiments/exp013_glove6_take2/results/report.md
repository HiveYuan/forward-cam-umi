# exp013_glove6_take2: report (variant main)

19 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.55 / 1.59 | 3.11 / 9.09 | 5.83 / 15.98 | 9.99 / 22.61 | 10.38 / 14.40 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.57 | 0.37 / 1.22 | 0.49 / 1.61 | 0.55 / 1.82 | 0.62 / 1.27 |

n [frame pairs]:

- static, E3: 0.08 s: 2213, 0.5 s: 1915, 1.0 s: 1633, 2.0 s: 1215, 6.67 s: 72
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.51 / 9.15 | 6.01 / 18.35 | 7.97 / 25.66 | 9.25 / 25.79 | 10.56 / 20.47 |
| E3 | Bnet+Acheck | 2.56 / 9.02 | 6.20 / 18.71 | 8.45 / 25.49 | 10.45 / 26.66 | 10.19 / 20.13 |

n [frame pairs]: 0.08 s: 2213, 0.5 s: 1915, 1.0 s: 1633, 2.0 s: 1215, 6.67 s: 72

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 19.9 | 86 | 100% |
| E3 | 0.14% | 18.7 | 89 | 87% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 19/19 | 19 | 3.8% | 13.0% | 2.6% | ep12, ep18 |
| E3 | Bnet+Acheck, without flagged | 17/19 | 17 | 3.4% | 10.7% | 2.2% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 19/19 | 19 | 3.8% | 13.0% | 2.6% |  |
| E3 | Bnet+Acheck, method A (check) | 2/19 | 2 | 35.2% | 44.7% | -35.2% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1212 | 1.1 / 3.4 | 1.8 / 5.4 | 2.5 / 7.3 | 3.8 / 9.6 | 4.7 / 12.7 | 5.4 / 13.9 | 5.7 / 13.9 | 4.6 / 10.4 |
| E3 | Bnet+Acheck | 1212 | 1.2 / 3.4 | 1.8 / 5.4 | 2.6 / 7.6 | 3.9 / 10.0 | 5.5 / 14.1 | 6.5 / 16.3 | 7.3 / 15.7 | 3.7 / 10.0 |

n [anchors counting the step]: 0.07 s: 1196, 0.13 s: 1180, 0.27 s: 1148, 0.53 s: 1084, 1.00 s: 974, 2.00 s: 774, 4.00 s: 389, 6.67 s: 13

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 1212 | 0.14 / 0.39 | 0.21 / 0.57 | 0.29 / 0.81 | 0.39 / 0.98 | 0.51 / 1.33 | 0.59 / 1.45 | 0.61 / 1.65 | 0.65 / 1.36 |

n [anchors counting the step]: 0.07 s: 1196, 0.13 s: 1180, 0.27 s: 1148, 0.53 s: 1084, 1.00 s: 974, 2.00 s: 774, 4.00 s: 389, 6.67 s: 13

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 1197 | 1198 | 1198 | 1198 |
| E3 | counted steps per anchor, median | 15 | 30 | 40 | 43 |
| E3 | position [mm], oracle (tiles), mean / median | 4.4 / 3.8 | 5.4 / 4.7 | 5.8 / 5.1 | 6.0 / 5.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.7 / 4.0 | 5.9 / 5.2 | 6.7 / 6.2 | 6.9 / 6.5 |
| E3 | rotation [deg], every scale, mean / median | 0.48 / 0.40 | 0.58 / 0.50 | 0.63 / 0.55 | 0.65 / 0.57 |

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

## Comparison with other experiments

- exp009_net_scale: `exp009_net_scale/results/metrics.json`
- runs only in exp009_net_scale (not shown): E3_uniK, E3_m3d, E3_da3m, E3_moge

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp013_glove6_take2 n | exp013_glove6_take2 median | exp013_glove6_take2 p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|
| static | 0.08 | 2213 | 0.55 | 1.59 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 1915 | 3.11 | 9.09 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 1633 | 5.83 | 15.98 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 1215 | 9.99 | 22.61 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 72 | 10.38 | 14.40 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - |
| E3 | 0.08 | 2213 | 0.16 | 0.57 | - | - | - |
| E3 | 0.5 | 1915 | 0.37 | 1.22 | - | - | - |
| E3 | 1.0 | 1633 | 0.49 | 1.61 | - | - | - |
| E3 | 2.0 | 1215 | 0.55 | 1.82 | - | - | - |
| E3 | 6.67 | 72 | 0.62 | 1.27 | - | - | - |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp013_glove6_take2 n | exp013_glove6_take2 median | exp013_glove6_take2 p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - |
| E3 | oracle | 0.08 | 2213 | 2.51 | 9.15 | - | - | - |
| E3 | oracle | 0.5 | 1915 | 6.01 | 18.35 | - | - | - |
| E3 | oracle | 1.0 | 1633 | 7.97 | 25.66 | - | - | - |
| E3 | oracle | 2.0 | 1215 | 9.25 | 25.79 | - | - | - |
| E3 | oracle | 6.67 | 72 | 10.56 | 20.47 | - | - | - |
| E3 | configured | 0.08 | 2213 | 2.56 | 9.02 | - | - | - |
| E3 | configured | 0.5 | 1915 | 6.20 | 18.71 | - | - | - |
| E3 | configured | 1.0 | 1633 | 8.45 | 25.49 | - | - | - |
| E3 | configured | 2.0 | 1215 | 10.45 | 26.66 | - | - | - |
| E3 | configured | 6.67 | 72 | 10.19 | 20.13 | - | - | - |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp013_glove6_take2 | exp009_net_scale |
|---|---|---|---|
| E1 | track fail | - | - |
| E1 | keyframes / segment | 19.9 | 14.2 |
| E1 | runtime s / segment | 86 | 43 |
| E1 | valid pixels | 100% | 100% |
| E3 | track fail | 0.14% | - |
| E3 | keyframes / segment | 18.7 | - |
| E3 | runtime s / segment | 89 | - |
| E3 | valid pixels | 87% | - |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp013_glove6_take2 | exp009_net_scale |
|---|---|---|---|
| E3 | scale label | Bnet+Acheck | - |
| E3 | segments with a scale | 19/19 | - |
| E3 | compared (tile GT) | 19 | - |
| E3 | abs err median | 3.8% | - |
| E3 | abs err p90 | 13.0% | - |
| E3 | bias (median) | 2.6% | - |
| E3 | flagged | ep12, ep18 | - |
| E3 | without flagged: abs err median / p90 | 3.4% / 10.7% | - |
| E3 | method Bnet: segments ok, n: abs err median / p90 / bias | 19/19, n 19: 3.8% / 13.0% / 2.6% | - |
| E3 | method A: segments ok, n: abs err median / p90 / bias | 2/19, n 2: 35.2% / 44.7% / -35.2% | - |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp013_glove6_take2 n | exp013_glove6_take2 median | exp013_glove6_take2 p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3 | oracle | anchors | 1212 |  |  | - | - | - |
| E3 | oracle | 0.07 s | 1196 | 1.1 | 3.4 | - | - | - |
| E3 | oracle | 0.13 s | 1180 | 1.8 | 5.4 | - | - | - |
| E3 | oracle | 0.27 s | 1148 | 2.5 | 7.3 | - | - | - |
| E3 | oracle | 0.53 s | 1084 | 3.8 | 9.6 | - | - | - |
| E3 | oracle | 1.00 s | 974 | 4.7 | 12.7 | - | - | - |
| E3 | oracle | 2.00 s | 774 | 5.4 | 13.9 | - | - | - |
| E3 | oracle | 4.00 s | 389 | 5.7 | 13.9 | - | - | - |
| E3 | oracle | 6.67 s | 13 | 4.6 | 10.4 | - | - | - |
| E3 | configured | anchors | 1212 |  |  | - | - | - |
| E3 | configured | 0.07 s | 1196 | 1.2 | 3.4 | - | - | - |
| E3 | configured | 0.13 s | 1180 | 1.8 | 5.4 | - | - | - |
| E3 | configured | 0.27 s | 1148 | 2.6 | 7.6 | - | - | - |
| E3 | configured | 0.53 s | 1084 | 3.9 | 10.0 | - | - | - |
| E3 | configured | 1.00 s | 974 | 5.5 | 14.1 | - | - | - |
| E3 | configured | 2.00 s | 774 | 6.5 | 16.3 | - | - | - |
| E3 | configured | 4.00 s | 389 | 7.3 | 15.7 | - | - | - |
| E3 | configured | 6.67 s | 13 | 3.7 | 10.0 | - | - | - |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp013_glove6_take2 n | exp013_glove6_take2 median | exp013_glove6_take2 p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3 | every scale | anchors | 1212 |  |  | - | - | - |
| E3 | every scale | 0.07 s | 1196 | 0.14 | 0.39 | - | - | - |
| E3 | every scale | 0.13 s | 1180 | 0.21 | 0.57 | - | - | - |
| E3 | every scale | 0.27 s | 1148 | 0.29 | 0.81 | - | - | - |
| E3 | every scale | 0.53 s | 1084 | 0.39 | 0.98 | - | - | - |
| E3 | every scale | 1.00 s | 974 | 0.51 | 1.33 | - | - | - |
| E3 | every scale | 2.00 s | 774 | 0.59 | 1.45 | - | - | - |
| E3 | every scale | 4.00 s | 389 | 0.61 | 1.65 | - | - | - |
| E3 | every scale | 6.67 s | 13 | 0.65 | 1.36 | - | - | - |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp013_glove6_take2 | exp009_net_scale |
|---|---|---|---|---|---|
| E3 | every scale | anchors | 15 (1.00 s) | 1197 | - |
| E3 | every scale | anchors | 30 (2.00 s) | 1198 | - |
| E3 | every scale | anchors | 50 (3.33 s) | 1198 | - |
| E3 | every scale | anchors | 100 (6.67 s) | 1198 | - |
| E3 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3 | every scale | counted steps per anchor, median | 50 (3.33 s) | 40 | - |
| E3 | every scale | counted steps per anchor, median | 100 (6.67 s) | 43 | - |
| E3 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.4 / 3.8 | - |
| E3 | oracle | pos mm, mean / median | 30 (2.00 s) | 5.4 / 4.7 | - |
| E3 | oracle | pos mm, mean / median | 50 (3.33 s) | 5.8 / 5.1 | - |
| E3 | oracle | pos mm, mean / median | 100 (6.67 s) | 6.0 / 5.4 | - |
| E3 | configured | pos mm, mean / median | 15 (1.00 s) | 4.7 / 4.0 | - |
| E3 | configured | pos mm, mean / median | 30 (2.00 s) | 5.9 / 5.2 | - |
| E3 | configured | pos mm, mean / median | 50 (3.33 s) | 6.7 / 6.2 | - |
| E3 | configured | pos mm, mean / median | 100 (6.67 s) | 6.9 / 6.5 | - |
| E3 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.48 / 0.40 | - |
| E3 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.58 / 0.50 | - |
| E3 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.63 / 0.55 | - |
| E3 | every scale | rot deg, mean / median | 100 (6.67 s) | 0.65 / 0.57 | - |

### Ground-truth noise floor

| pairs | dt [s] | exp013_glove6_take2 n | exp013_glove6_take2 rot deg med / p95 | exp013_glove6_take2 trans mm med / p95 | exp009_net_scale n | exp009_net_scale rot deg med / p95 | exp009_net_scale trans mm med / p95 |
|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 1200 | 0.13 / 0.40 | 2.0 / 6.3 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 951 | 0.22 / 1.09 | 3.6 / 17.1 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 1.0 | 648 | 0.25 / 1.00 | 4.5 / 14.4 | - | - | - |
| same tiles | 2.0 | 141 | 0.35 / 1.16 | 6.3 / 15.6 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 1305 | 0.33 / 1.64 | 5.1 / 24.1 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

