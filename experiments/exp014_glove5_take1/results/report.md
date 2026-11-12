# exp014_glove5_take1: report (variant main)

49 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.37 / 1.11 | 2.17 / 6.40 | 4.34 / 12.38 | 8.03 / 19.67 | 14.29 / 26.71 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.12 / 0.50 | 0.23 / 1.68 | 0.30 / 2.95 | 0.38 / 4.90 | 0.53 / 6.77 |

n [frame pairs]:

- static, E3: 0.08 s: 8477, 0.5 s: 7538, 1.0 s: 6707, 2.0 s: 5505, 6.67 s: 1614
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.78 / 6.97 | 3.68 / 26.22 | 4.86 / 45.90 | 5.79 / 80.11 | 7.42 / 96.79 |
| E3 | Bnet+Acheck | 1.83 / 7.19 | 4.29 / 25.42 | 6.37 / 44.58 | 9.21 / 73.33 | 14.97 / 96.65 |

n [frame pairs]: 0.08 s: 8477, 0.5 s: 7538, 1.0 s: 6707, 2.0 s: 5505, 6.67 s: 1614

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 19.5 | 58 | 100% |
| E3 | 0.22% | 18.6 | 63 | 85% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 49/49 | 49 | 8.7% | 34.6% | 8.3% | ep03, ep04, ep06, ep16, ep22, ep25, ep28, ep32, ep35, ep38 |
| E3 | Bnet+Acheck, without flagged | 39/49 | 39 | 8.7% | 40.4% | 8.3% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 49/49 | 49 | 8.7% | 34.6% | 8.3% |  |
| E3 | Bnet+Acheck, method A (check) | 14/49 | 14 | 9.1% | 26.0% | -8.8% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 4734 | 0.8 / 2.9 | 1.2 / 4.5 | 1.6 / 7.3 | 2.3 / 11.8 | 3.1 / 18.0 | 3.5 / 30.5 | 4.5 / 42.9 | 4.2 / 41.1 |
| E3 | Bnet+Acheck | 4734 | 0.9 / 2.8 | 1.3 / 4.5 | 1.9 / 7.2 | 2.9 / 11.8 | 4.5 / 17.8 | 7.1 / 29.0 | 9.3 / 42.6 | 11.0 / 38.0 |

n [anchors counting the step]: 0.07 s: 4671, 0.13 s: 4609, 0.27 s: 4485, 0.53 s: 4256, 1.00 s: 3881, 2.00 s: 3238, 4.00 s: 2192, 6.67 s: 858

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 4734 | 0.10 / 0.33 | 0.14 / 0.49 | 0.18 / 0.75 | 0.24 / 1.10 | 0.31 / 1.64 | 0.39 / 2.45 | 0.50 / 2.78 | 0.52 / 3.49 |

n [anchors counting the step]: 0.07 s: 4671, 0.13 s: 4609, 0.27 s: 4485, 0.53 s: 4256, 1.00 s: 3881, 2.00 s: 3238, 4.00 s: 2192, 6.67 s: 858

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 4682 | 4690 | 4692 | 4692 |
| E3 | counted steps per anchor, median | 15 | 30 | 44 | 56 |
| E3 | position [mm], oracle (tiles), mean / median | 4.1 / 2.3 | 5.8 / 2.8 | 7.2 / 3.2 | 8.1 / 3.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 4.4 / 2.9 | 6.5 / 4.1 | 8.3 / 4.9 | 9.5 / 5.4 |
| E3 | rotation [deg], every scale, mean / median | 0.44 / 0.24 | 0.59 / 0.31 | 0.71 / 0.35 | 0.79 / 0.39 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 56 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 1032 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 2658 | 0.11 / 0.45 | 1.8 / 9.4 |
| same tiles, dt 0.5 s | 1716 | 0.16 / 0.88 | 2.6 / 17.6 |
| same tiles, dt 1.0 s | 1161 | 0.19 / 0.92 | 3.1 / 19.6 |
| same tiles, dt 2.0 s | 714 | 0.25 / 0.90 | 4.0 / 18.0 |
| tile set changes between the ends | 3096 | 0.31 / 1.91 | 5.0 / 36.3 |

## Comparison with other experiments

- exp009_net_scale: `exp009_net_scale/results/metrics.json`
- runs only in exp009_net_scale (not shown): E3_uniK, E3_m3d, E3_da3m, E3_moge

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp014_glove5_take1 n | exp014_glove5_take1 median | exp014_glove5_take1 p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|
| static | 0.08 | 8477 | 0.37 | 1.11 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 7538 | 2.17 | 6.40 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 6707 | 4.34 | 12.38 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 5505 | 8.03 | 19.67 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 1614 | 14.29 | 26.71 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - |
| E3 | 0.08 | 8477 | 0.12 | 0.50 | - | - | - |
| E3 | 0.5 | 7538 | 0.23 | 1.68 | - | - | - |
| E3 | 1.0 | 6707 | 0.30 | 2.95 | - | - | - |
| E3 | 2.0 | 5505 | 0.38 | 4.90 | - | - | - |
| E3 | 6.67 | 1614 | 0.53 | 6.77 | - | - | - |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp014_glove5_take1 n | exp014_glove5_take1 median | exp014_glove5_take1 p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - |
| E3 | oracle | 0.08 | 8477 | 1.78 | 6.97 | - | - | - |
| E3 | oracle | 0.5 | 7538 | 3.68 | 26.22 | - | - | - |
| E3 | oracle | 1.0 | 6707 | 4.86 | 45.90 | - | - | - |
| E3 | oracle | 2.0 | 5505 | 5.79 | 80.11 | - | - | - |
| E3 | oracle | 6.67 | 1614 | 7.42 | 96.79 | - | - | - |
| E3 | configured | 0.08 | 8477 | 1.83 | 7.19 | - | - | - |
| E3 | configured | 0.5 | 7538 | 4.29 | 25.42 | - | - | - |
| E3 | configured | 1.0 | 6707 | 6.37 | 44.58 | - | - | - |
| E3 | configured | 2.0 | 5505 | 9.21 | 73.33 | - | - | - |
| E3 | configured | 6.67 | 1614 | 14.97 | 96.65 | - | - | - |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp014_glove5_take1 | exp009_net_scale |
|---|---|---|---|
| E1 | track fail | - | - |
| E1 | keyframes / segment | 19.5 | 14.2 |
| E1 | runtime s / segment | 58 | 43 |
| E1 | valid pixels | 100% | 100% |
| E3 | track fail | 0.22% | - |
| E3 | keyframes / segment | 18.6 | - |
| E3 | runtime s / segment | 63 | - |
| E3 | valid pixels | 85% | - |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp014_glove5_take1 | exp009_net_scale |
|---|---|---|---|
| E3 | scale label | Bnet+Acheck | - |
| E3 | segments with a scale | 49/49 | - |
| E3 | compared (tile GT) | 49 | - |
| E3 | abs err median | 8.7% | - |
| E3 | abs err p90 | 34.6% | - |
| E3 | bias (median) | 8.3% | - |
| E3 | flagged | ep03, ep04, ep06, ep16, ep22, ep25, ep28, ep32, ep35, ep38 | - |
| E3 | without flagged: abs err median / p90 | 8.7% / 40.4% | - |
| E3 | method Bnet: segments ok, n: abs err median / p90 / bias | 49/49, n 49: 8.7% / 34.6% / 8.3% | - |
| E3 | method A: segments ok, n: abs err median / p90 / bias | 14/49, n 14: 9.1% / 26.0% / -8.8% | - |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp014_glove5_take1 n | exp014_glove5_take1 median | exp014_glove5_take1 p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3 | oracle | anchors | 4734 |  |  | - | - | - |
| E3 | oracle | 0.07 s | 4671 | 0.8 | 2.9 | - | - | - |
| E3 | oracle | 0.13 s | 4609 | 1.2 | 4.5 | - | - | - |
| E3 | oracle | 0.27 s | 4485 | 1.6 | 7.3 | - | - | - |
| E3 | oracle | 0.53 s | 4256 | 2.3 | 11.8 | - | - | - |
| E3 | oracle | 1.00 s | 3881 | 3.1 | 18.0 | - | - | - |
| E3 | oracle | 2.00 s | 3238 | 3.5 | 30.5 | - | - | - |
| E3 | oracle | 4.00 s | 2192 | 4.5 | 42.9 | - | - | - |
| E3 | oracle | 6.67 s | 858 | 4.2 | 41.1 | - | - | - |
| E3 | configured | anchors | 4734 |  |  | - | - | - |
| E3 | configured | 0.07 s | 4671 | 0.9 | 2.8 | - | - | - |
| E3 | configured | 0.13 s | 4609 | 1.3 | 4.5 | - | - | - |
| E3 | configured | 0.27 s | 4485 | 1.9 | 7.2 | - | - | - |
| E3 | configured | 0.53 s | 4256 | 2.9 | 11.8 | - | - | - |
| E3 | configured | 1.00 s | 3881 | 4.5 | 17.8 | - | - | - |
| E3 | configured | 2.00 s | 3238 | 7.1 | 29.0 | - | - | - |
| E3 | configured | 4.00 s | 2192 | 9.3 | 42.6 | - | - | - |
| E3 | configured | 6.67 s | 858 | 11.0 | 38.0 | - | - | - |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp014_glove5_take1 n | exp014_glove5_take1 median | exp014_glove5_take1 p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3 | every scale | anchors | 4734 |  |  | - | - | - |
| E3 | every scale | 0.07 s | 4671 | 0.10 | 0.33 | - | - | - |
| E3 | every scale | 0.13 s | 4609 | 0.14 | 0.49 | - | - | - |
| E3 | every scale | 0.27 s | 4485 | 0.18 | 0.75 | - | - | - |
| E3 | every scale | 0.53 s | 4256 | 0.24 | 1.10 | - | - | - |
| E3 | every scale | 1.00 s | 3881 | 0.31 | 1.64 | - | - | - |
| E3 | every scale | 2.00 s | 3238 | 0.39 | 2.45 | - | - | - |
| E3 | every scale | 4.00 s | 2192 | 0.50 | 2.78 | - | - | - |
| E3 | every scale | 6.67 s | 858 | 0.52 | 3.49 | - | - | - |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp014_glove5_take1 | exp009_net_scale |
|---|---|---|---|---|---|
| E3 | every scale | anchors | 15 (1.00 s) | 4682 | - |
| E3 | every scale | anchors | 30 (2.00 s) | 4690 | - |
| E3 | every scale | anchors | 50 (3.33 s) | 4692 | - |
| E3 | every scale | anchors | 100 (6.67 s) | 4692 | - |
| E3 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3 | every scale | counted steps per anchor, median | 50 (3.33 s) | 44 | - |
| E3 | every scale | counted steps per anchor, median | 100 (6.67 s) | 56 | - |
| E3 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.1 / 2.3 | - |
| E3 | oracle | pos mm, mean / median | 30 (2.00 s) | 5.8 / 2.8 | - |
| E3 | oracle | pos mm, mean / median | 50 (3.33 s) | 7.2 / 3.2 | - |
| E3 | oracle | pos mm, mean / median | 100 (6.67 s) | 8.1 / 3.4 | - |
| E3 | configured | pos mm, mean / median | 15 (1.00 s) | 4.4 / 2.9 | - |
| E3 | configured | pos mm, mean / median | 30 (2.00 s) | 6.5 / 4.1 | - |
| E3 | configured | pos mm, mean / median | 50 (3.33 s) | 8.3 / 4.9 | - |
| E3 | configured | pos mm, mean / median | 100 (6.67 s) | 9.5 / 5.4 | - |
| E3 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.44 / 0.24 | - |
| E3 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.59 / 0.31 | - |
| E3 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.71 / 0.35 | - |
| E3 | every scale | rot deg, mean / median | 100 (6.67 s) | 0.79 / 0.39 | - |

### Ground-truth noise floor

| pairs | dt [s] | exp014_glove5_take1 n | exp014_glove5_take1 rot deg med / p95 | exp014_glove5_take1 trans mm med / p95 | exp009_net_scale n | exp009_net_scale rot deg med / p95 | exp009_net_scale trans mm med / p95 |
|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 2658 | 0.11 / 0.45 | 1.8 / 9.4 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 1716 | 0.16 / 0.88 | 2.6 / 17.6 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 1.0 | 1161 | 0.19 / 0.92 | 3.1 / 19.6 | - | - | - |
| same tiles | 2.0 | 714 | 0.25 / 0.90 | 4.0 / 18.0 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 3096 | 0.31 / 1.91 | 5.0 / 36.3 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

