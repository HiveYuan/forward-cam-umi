# exp015_glove5_take2: report (variant main)

66 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.26 | 2.16 / 7.35 | 4.20 / 14.28 | 7.44 / 23.10 | 13.69 / 27.92 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.13 / 0.54 | 0.26 / 1.77 | 0.36 / 3.20 | 0.47 / 5.83 | 0.50 / 6.06 |

n [frame pairs]:

- static, E3: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 1.99 / 8.79 | 4.21 / 29.85 | 5.84 / 52.18 | 7.18 / 94.93 | 8.14 / 101.43 |
| E3 | Bnet+Acheck | 2.04 / 10.05 | 4.53 / 33.78 | 6.94 / 62.46 | 9.76 / 96.73 | 10.60 / 125.32 |

n [frame pairs]: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 17.5 | 52 | 100% |
| E3 | 0.30% | 16.3 | 56 | 88% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 66/66 | 65 | 6.5% | 25.3% | 5.6% | ep04, ep11, ep25, ep28, ep38 |
| E3 | Bnet+Acheck, without flagged | 61/66 | 60 | 6.6% | 25.1% | 5.7% |  |
| E3 | Bnet+Acheck, method Bnet (primary) | 66/66 | 65 | 6.5% | 25.3% | 5.6% |  |
| E3 | Bnet+Acheck, method A (check) | 8/66 | 8 | 7.8% | 58.4% | -6.0% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 4616 | 0.8 / 3.0 | 1.2 / 4.8 | 1.7 / 7.5 | 2.4 / 11.7 | 3.5 / 16.8 | 4.6 / 24.1 | 5.8 / 22.4 | 5.3 / 16.7 |
| E3 | Bnet+Acheck | 4616 | 0.9 / 3.1 | 1.3 / 5.0 | 1.9 / 8.0 | 2.9 / 12.6 | 4.4 / 19.3 | 6.4 / 27.4 | 8.8 / 28.8 | 8.5 / 24.1 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 4616 | 0.11 / 0.34 | 0.15 / 0.53 | 0.20 / 0.82 | 0.28 / 1.23 | 0.38 / 1.69 | 0.49 / 2.25 | 0.60 / 2.35 | 0.55 / 1.81 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 4564 | 4571 | 4572 | 4572 |
| E3 | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3 | position [mm], oracle (tiles), mean / median | 4.5 / 2.5 | 6.3 / 3.4 | 7.4 / 4.0 | 8.0 / 4.4 |
| E3 | position [mm], Bnet+Acheck, mean / median | 18.6 / 2.9 | 28.1 / 4.1 | 32.5 / 4.9 | 33.7 / 5.9 |
| E3 | rotation [deg], every scale, mean / median | 0.52 / 0.28 | 0.71 / 0.37 | 0.84 / 0.43 | 0.91 / 0.48 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 52 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 632 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 1611 | 0.14 / 1.29 | 2.3 / 23.7 |
| same tiles, dt 0.5 s | 1074 | 0.22 / 1.63 | 3.9 / 35.6 |
| same tiles, dt 1.0 s | 786 | 0.30 / 1.46 | 5.4 / 37.5 |
| same tiles, dt 2.0 s | 579 | 0.42 / 3.20 | 8.1 / 63.4 |
| tile set changes between the ends | 1896 | 0.43 / 3.68 | 7.5 / 67.6 |

## Comparison with other experiments

- exp009_net_scale: `exp009_net_scale/results/metrics.json`
- runs only in exp009_net_scale (not shown): E3_uniK, E3_m3d, E3_da3m, E3_moge

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|
| static | 0.08 | 8897 | 0.39 | 1.26 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 7720 | 2.16 | 7.35 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 6639 | 4.20 | 14.28 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 5213 | 7.44 | 23.10 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 1253 | 13.69 | 27.92 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - |
| E3 | 0.08 | 8897 | 0.13 | 0.54 | - | - | - |
| E3 | 0.5 | 7720 | 0.26 | 1.77 | - | - | - |
| E3 | 1.0 | 6639 | 0.36 | 3.20 | - | - | - |
| E3 | 2.0 | 5213 | 0.47 | 5.83 | - | - | - |
| E3 | 6.67 | 1253 | 0.50 | 6.06 | - | - | - |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - |
| E3 | oracle | 0.08 | 8897 | 1.99 | 8.79 | - | - | - |
| E3 | oracle | 0.5 | 7720 | 4.21 | 29.85 | - | - | - |
| E3 | oracle | 1.0 | 6639 | 5.84 | 52.18 | - | - | - |
| E3 | oracle | 2.0 | 5213 | 7.18 | 94.93 | - | - | - |
| E3 | oracle | 6.67 | 1253 | 8.14 | 101.43 | - | - | - |
| E3 | configured | 0.08 | 8897 | 2.04 | 10.05 | - | - | - |
| E3 | configured | 0.5 | 7720 | 4.53 | 33.78 | - | - | - |
| E3 | configured | 1.0 | 6639 | 6.94 | 62.46 | - | - | - |
| E3 | configured | 2.0 | 5213 | 9.76 | 96.73 | - | - | - |
| E3 | configured | 6.67 | 1253 | 10.60 | 125.32 | - | - | - |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp015_glove5_take2 | exp009_net_scale |
|---|---|---|---|
| E1 | track fail | - | - |
| E1 | keyframes / segment | 17.5 | 14.2 |
| E1 | runtime s / segment | 52 | 43 |
| E1 | valid pixels | 100% | 100% |
| E3 | track fail | 0.30% | - |
| E3 | keyframes / segment | 16.3 | - |
| E3 | runtime s / segment | 56 | - |
| E3 | valid pixels | 88% | - |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp015_glove5_take2 | exp009_net_scale |
|---|---|---|---|
| E3 | scale label | Bnet+Acheck | - |
| E3 | segments with a scale | 66/66 | - |
| E3 | compared (tile GT) | 65 | - |
| E3 | abs err median | 6.5% | - |
| E3 | abs err p90 | 25.3% | - |
| E3 | bias (median) | 5.6% | - |
| E3 | flagged | ep04, ep11, ep25, ep28, ep38 | - |
| E3 | without flagged: abs err median / p90 | 6.6% / 25.1% | - |
| E3 | method Bnet: segments ok, n: abs err median / p90 / bias | 66/66, n 65: 6.5% / 25.3% / 5.6% | - |
| E3 | method A: segments ok, n: abs err median / p90 / bias | 8/66, n 8: 7.8% / 58.4% / -6.0% | - |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3 | oracle | anchors | 4616 |  |  | - | - | - |
| E3 | oracle | 0.07 s | 4551 | 0.8 | 3.0 | - | - | - |
| E3 | oracle | 0.13 s | 4486 | 1.2 | 4.8 | - | - | - |
| E3 | oracle | 0.27 s | 4356 | 1.7 | 7.5 | - | - | - |
| E3 | oracle | 0.53 s | 4121 | 2.4 | 11.7 | - | - | - |
| E3 | oracle | 1.00 s | 3744 | 3.5 | 16.8 | - | - | - |
| E3 | oracle | 2.00 s | 3094 | 4.6 | 24.1 | - | - | - |
| E3 | oracle | 4.00 s | 1994 | 5.8 | 22.4 | - | - | - |
| E3 | oracle | 6.67 s | 641 | 5.3 | 16.7 | - | - | - |
| E3 | configured | anchors | 4616 |  |  | - | - | - |
| E3 | configured | 0.07 s | 4551 | 0.9 | 3.1 | - | - | - |
| E3 | configured | 0.13 s | 4486 | 1.3 | 5.0 | - | - | - |
| E3 | configured | 0.27 s | 4356 | 1.9 | 8.0 | - | - | - |
| E3 | configured | 0.53 s | 4121 | 2.9 | 12.6 | - | - | - |
| E3 | configured | 1.00 s | 3744 | 4.4 | 19.3 | - | - | - |
| E3 | configured | 2.00 s | 3094 | 6.4 | 27.4 | - | - | - |
| E3 | configured | 4.00 s | 1994 | 8.8 | 28.8 | - | - | - |
| E3 | configured | 6.67 s | 641 | 8.5 | 24.1 | - | - | - |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3 | every scale | anchors | 4616 |  |  | - | - | - |
| E3 | every scale | 0.07 s | 4551 | 0.11 | 0.34 | - | - | - |
| E3 | every scale | 0.13 s | 4486 | 0.15 | 0.53 | - | - | - |
| E3 | every scale | 0.27 s | 4356 | 0.20 | 0.82 | - | - | - |
| E3 | every scale | 0.53 s | 4121 | 0.28 | 1.23 | - | - | - |
| E3 | every scale | 1.00 s | 3744 | 0.38 | 1.69 | - | - | - |
| E3 | every scale | 2.00 s | 3094 | 0.49 | 2.25 | - | - | - |
| E3 | every scale | 4.00 s | 1994 | 0.60 | 2.35 | - | - | - |
| E3 | every scale | 6.67 s | 641 | 0.55 | 1.81 | - | - | - |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp015_glove5_take2 | exp009_net_scale |
|---|---|---|---|---|---|
| E3 | every scale | anchors | 15 (1.00 s) | 4564 | - |
| E3 | every scale | anchors | 30 (2.00 s) | 4571 | - |
| E3 | every scale | anchors | 50 (3.33 s) | 4572 | - |
| E3 | every scale | anchors | 100 (6.67 s) | 4572 | - |
| E3 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3 | every scale | counted steps per anchor, median | 50 (3.33 s) | 43 | - |
| E3 | every scale | counted steps per anchor, median | 100 (6.67 s) | 52 | - |
| E3 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.5 / 2.5 | - |
| E3 | oracle | pos mm, mean / median | 30 (2.00 s) | 6.3 / 3.4 | - |
| E3 | oracle | pos mm, mean / median | 50 (3.33 s) | 7.4 / 4.0 | - |
| E3 | oracle | pos mm, mean / median | 100 (6.67 s) | 8.0 / 4.4 | - |
| E3 | configured | pos mm, mean / median | 15 (1.00 s) | 18.6 / 2.9 | - |
| E3 | configured | pos mm, mean / median | 30 (2.00 s) | 28.1 / 4.1 | - |
| E3 | configured | pos mm, mean / median | 50 (3.33 s) | 32.5 / 4.9 | - |
| E3 | configured | pos mm, mean / median | 100 (6.67 s) | 33.7 / 5.9 | - |
| E3 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.52 / 0.28 | - |
| E3 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.71 / 0.37 | - |
| E3 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.84 / 0.43 | - |
| E3 | every scale | rot deg, mean / median | 100 (6.67 s) | 0.91 / 0.48 | - |

### Ground-truth noise floor

| pairs | dt [s] | exp015_glove5_take2 n | exp015_glove5_take2 rot deg med / p95 | exp015_glove5_take2 trans mm med / p95 | exp009_net_scale n | exp009_net_scale rot deg med / p95 | exp009_net_scale trans mm med / p95 |
|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 1611 | 0.14 / 1.29 | 2.3 / 23.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 1074 | 0.22 / 1.63 | 3.9 / 35.6 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 1.0 | 786 | 0.30 / 1.46 | 5.4 / 37.5 | - | - | - |
| same tiles | 2.0 | 579 | 0.42 / 3.20 | 8.1 / 63.4 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 1896 | 0.43 / 3.68 | 7.5 / 67.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

