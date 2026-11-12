# exp022_glove5_take2_ballscale: report (variant main)

66 segments. Runs: E1, E3_da3m, E3_da2 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.26 | 2.16 / 7.35 | 4.20 / 14.28 | 7.44 / 23.10 | 13.69 / 27.92 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3_da3m | 0.13 / 0.54 | 0.26 / 1.77 | 0.36 / 3.20 | 0.47 / 5.83 | 0.50 / 6.06 |
| E3_da2 | 0.13 / 0.54 | 0.26 / 1.77 | 0.36 / 3.20 | 0.47 / 5.83 | 0.50 / 6.06 |

n [frame pairs]:

- static, E3_da3m, E3_da2: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3_da3m | oracle (tiles) | 1.99 / 8.79 | 4.21 / 29.85 | 5.84 / 52.18 | 7.18 / 94.93 | 8.14 / 101.43 |
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck | 2.04 / 10.05 | 4.53 / 33.78 | 6.94 / 62.46 | 9.76 / 96.73 | 10.60 / 125.32 |
| E3_da2 | oracle (tiles) | 1.99 / 8.79 | 4.21 / 29.85 | 5.84 / 52.18 | 7.18 / 94.93 | 8.14 / 101.43 |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck | 2.04 / 9.61 | 5.47 / 33.29 | 8.99 / 63.57 | 13.87 / 95.14 | 17.22 / 99.22 |

n [frame pairs]: 0.08 s: 8897, 0.5 s: 7720, 1.0 s: 6639, 2.0 s: 5213, 6.67 s: 1253

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 17.5 | 52 | 100% |
| E3_da3m | 0.30% | 16.3 | 56 | 88% |
| E3_da2 | 0.30% | 16.3 | 56 | 88% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck (flag \|check/primary - 1\| > 10%) | 66/66 | 65 | 6.5% | 25.3% | 5.6% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29, ep30, ep31, ep32, ep33, ep34, ep35, ep36, ep37, ep38, ep39, ep40, ep41, ep42, ep43, ep44, ep45, ep46, ep47, ep48, ep49, ep50, ep51, ep52, ep53, ep54, ep55, ep56, ep57, ep58, ep59, ep60, ep61, ep62, ep63, ep64, ep65 |
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck, without flagged | 0/66 | 0 | - | - | - |  |
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck, method Bnet (primary) | 66/66 | 65 | 6.5% | 25.3% | 5.6% |  |
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck, method A (check) | 8/66 | 8 | 7.8% | 58.4% | -6.0% |  |
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck, method B (check) | 66/66 | 65 | 17.7% | 31.6% | -17.2% |  |
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck, method Bsession (check) | 66/66 | 65 | 18.4% | 25.5% | -18.2% |  |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 66/66 | 65 | 15.8% | 26.9% | -14.6% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29, ep30, ep31, ep32, ep33, ep34, ep35, ep36, ep37, ep38, ep39, ep40, ep41, ep42, ep43, ep44, ep45, ep46, ep47, ep48, ep49, ep50, ep51, ep52, ep53, ep54, ep55, ep56, ep57, ep58, ep59, ep60, ep61, ep62, ep63, ep64, ep65 |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck, without flagged | 0/66 | 0 | - | - | - |  |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck, method Bsession (primary) | 66/66 | 65 | 15.8% | 26.9% | -14.6% |  |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck, method A (check) | 8/66 | 8 | 7.8% | 58.4% | -6.0% |  |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck, method B (check) | 66/66 | 65 | 15.9% | 33.1% | -12.9% |  |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck, method Bnet (check) | 66/66 | 65 | 76.6% | 119.9% | 76.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_da3m | oracle (tiles) | 4616 | 0.8 / 3.0 | 1.2 / 4.8 | 1.7 / 7.5 | 2.4 / 11.7 | 3.5 / 16.8 | 4.6 / 24.1 | 5.8 / 22.4 | 5.3 / 16.7 |
| E3_da3m | Bnet+Acheck+Bcheck+Bsessioncheck | 4616 | 0.9 / 3.1 | 1.3 / 5.0 | 1.9 / 8.0 | 2.9 / 12.6 | 4.4 / 19.3 | 6.4 / 27.4 | 8.8 / 28.8 | 8.5 / 24.1 |
| E3_da2 | oracle (tiles) | 4616 | 0.8 / 3.0 | 1.2 / 4.8 | 1.7 / 7.5 | 2.4 / 11.7 | 3.5 / 16.8 | 4.6 / 24.1 | 5.8 / 22.4 | 5.3 / 16.7 |
| E3_da2 | Bsession+Acheck+Bcheck+Bnetcheck | 4616 | 1.0 / 3.2 | 1.5 / 5.1 | 2.3 / 8.6 | 4.1 / 14.3 | 6.9 / 24.0 | 11.5 / 37.9 | 17.2 / 43.1 | 15.1 / 40.8 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_da3m | every scale | 4616 | 0.11 / 0.34 | 0.15 / 0.53 | 0.20 / 0.82 | 0.28 / 1.23 | 0.38 / 1.69 | 0.49 / 2.25 | 0.60 / 2.35 | 0.55 / 1.81 |
| E3_da2 | every scale | 4616 | 0.11 / 0.34 | 0.15 / 0.53 | 0.20 / 0.82 | 0.28 / 1.23 | 0.38 / 1.69 | 0.49 / 2.25 | 0.60 / 2.35 | 0.55 / 1.81 |

n [anchors counting the step]: 0.07 s: 4551, 0.13 s: 4486, 0.27 s: 4356, 0.53 s: 4121, 1.00 s: 3744, 2.00 s: 3094, 4.00 s: 1994, 6.67 s: 641

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3_da3m | anchors | 4564 | 4571 | 4572 | 4572 |
| E3_da3m | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3_da3m | position [mm], oracle (tiles), mean / median | 4.5 / 2.5 | 6.3 / 3.4 | 7.4 / 4.0 | 8.0 / 4.4 |
| E3_da3m | position [mm], Bnet+Acheck+Bcheck+Bsessioncheck, mean / median | 18.6 / 2.9 | 28.1 / 4.1 | 32.5 / 4.9 | 33.7 / 5.9 |
| E3_da3m | rotation [deg], every scale, mean / median | 0.52 / 0.28 | 0.71 / 0.37 | 0.84 / 0.43 | 0.91 / 0.48 |
| E3_da2 | anchors | 4564 | 4571 | 4572 | 4572 |
| E3_da2 | counted steps per anchor, median | 15 | 30 | 43 | 52 |
| E3_da2 | position [mm], oracle (tiles), mean / median | 4.5 / 2.5 | 6.3 / 3.4 | 7.4 / 4.0 | 8.0 / 4.4 |
| E3_da2 | position [mm], Bsession+Acheck+Bcheck+Bnetcheck, mean / median | 15.6 / 3.9 | 24.0 / 6.2 | 28.5 / 8.4 | 30.3 / 9.8 |
| E3_da2 | rotation [deg], every scale, mean / median | 0.52 / 0.28 | 0.71 / 0.37 | 0.84 / 0.43 | 0.91 / 0.48 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3_da3m, H=100: 52 of 100).

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

- exp015_glove5_take2: `exp015_glove5_take2/results/metrics.json`
- runs only in exp015_glove5_take2 (not shown): E3

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp022_glove5_take2_ballscale n | exp022_glove5_take2_ballscale median | exp022_glove5_take2_ballscale p95 | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p95 |
|---|---|---|---|---|---|---|---|
| static | 0.08 | 8897 | 0.39 | 1.26 | 8897 | 0.39 | 1.26 |
| static | 0.5 | 7720 | 2.16 | 7.35 | 7720 | 2.16 | 7.35 |
| static | 1.0 | 6639 | 4.20 | 14.28 | 6639 | 4.20 | 14.28 |
| static | 2.0 | 5213 | 7.44 | 23.10 | 5213 | 7.44 | 23.10 |
| static | 6.67 | 1253 | 13.69 | 27.92 | 1253 | 13.69 | 27.92 |
| E1 | 0.08 | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - |
| E3_da3m | 0.08 | 8897 | 0.13 | 0.54 | - | - | - |
| E3_da3m | 0.5 | 7720 | 0.26 | 1.77 | - | - | - |
| E3_da3m | 1.0 | 6639 | 0.36 | 3.20 | - | - | - |
| E3_da3m | 2.0 | 5213 | 0.47 | 5.83 | - | - | - |
| E3_da3m | 6.67 | 1253 | 0.50 | 6.06 | - | - | - |
| E3_da2 | 0.08 | 8897 | 0.13 | 0.54 | - | - | - |
| E3_da2 | 0.5 | 7720 | 0.26 | 1.77 | - | - | - |
| E3_da2 | 1.0 | 6639 | 0.36 | 3.20 | - | - | - |
| E3_da2 | 2.0 | 5213 | 0.47 | 5.83 | - | - | - |
| E3_da2 | 6.67 | 1253 | 0.50 | 6.06 | - | - | - |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp022_glove5_take2_ballscale n | exp022_glove5_take2_ballscale median | exp022_glove5_take2_ballscale p95 | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p95 |
|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - |
| E3_da3m | oracle | 0.08 | 8897 | 1.99 | 8.79 | - | - | - |
| E3_da3m | oracle | 0.5 | 7720 | 4.21 | 29.85 | - | - | - |
| E3_da3m | oracle | 1.0 | 6639 | 5.84 | 52.18 | - | - | - |
| E3_da3m | oracle | 2.0 | 5213 | 7.18 | 94.93 | - | - | - |
| E3_da3m | oracle | 6.67 | 1253 | 8.14 | 101.43 | - | - | - |
| E3_da3m | configured | 0.08 | 8897 | 2.04 | 10.05 | - | - | - |
| E3_da3m | configured | 0.5 | 7720 | 4.53 | 33.78 | - | - | - |
| E3_da3m | configured | 1.0 | 6639 | 6.94 | 62.46 | - | - | - |
| E3_da3m | configured | 2.0 | 5213 | 9.76 | 96.73 | - | - | - |
| E3_da3m | configured | 6.67 | 1253 | 10.60 | 125.32 | - | - | - |
| E3_da2 | oracle | 0.08 | 8897 | 1.99 | 8.79 | - | - | - |
| E3_da2 | oracle | 0.5 | 7720 | 4.21 | 29.85 | - | - | - |
| E3_da2 | oracle | 1.0 | 6639 | 5.84 | 52.18 | - | - | - |
| E3_da2 | oracle | 2.0 | 5213 | 7.18 | 94.93 | - | - | - |
| E3_da2 | oracle | 6.67 | 1253 | 8.14 | 101.43 | - | - | - |
| E3_da2 | configured | 0.08 | 8897 | 2.04 | 9.61 | - | - | - |
| E3_da2 | configured | 0.5 | 7720 | 5.47 | 33.29 | - | - | - |
| E3_da2 | configured | 1.0 | 6639 | 8.99 | 63.57 | - | - | - |
| E3_da2 | configured | 2.0 | 5213 | 13.87 | 95.14 | - | - | - |
| E3_da2 | configured | 6.67 | 1253 | 17.22 | 99.22 | - | - | - |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp022_glove5_take2_ballscale | exp015_glove5_take2 |
|---|---|---|---|
| E1 | track fail | - | - |
| E1 | keyframes / segment | 17.5 | 17.5 |
| E1 | runtime s / segment | 52 | 52 |
| E1 | valid pixels | 100% | 100% |
| E3_da3m | track fail | 0.30% | - |
| E3_da3m | keyframes / segment | 16.3 | - |
| E3_da3m | runtime s / segment | 56 | - |
| E3_da3m | valid pixels | 88% | - |
| E3_da2 | track fail | 0.30% | - |
| E3_da2 | keyframes / segment | 16.3 | - |
| E3_da2 | runtime s / segment | 56 | - |
| E3_da2 | valid pixels | 88% | - |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp022_glove5_take2_ballscale | exp015_glove5_take2 |
|---|---|---|---|
| E3_da3m | scale label | Bnet+Acheck+Bcheck+Bsessioncheck | - |
| E3_da3m | segments with a scale | 66/66 | - |
| E3_da3m | compared (tile GT) | 65 | - |
| E3_da3m | abs err median | 6.5% | - |
| E3_da3m | abs err p90 | 25.3% | - |
| E3_da3m | bias (median) | 5.6% | - |
| E3_da3m | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29, ep30, ep31, ep32, ep33, ep34, ep35, ep36, ep37, ep38, ep39, ep40, ep41, ep42, ep43, ep44, ep45, ep46, ep47, ep48, ep49, ep50, ep51, ep52, ep53, ep54, ep55, ep56, ep57, ep58, ep59, ep60, ep61, ep62, ep63, ep64, ep65 | - |
| E3_da3m | without flagged: abs err median / p90 | - / - | - |
| E3_da3m | method Bnet: segments ok, n: abs err median / p90 / bias | 66/66, n 65: 6.5% / 25.3% / 5.6% | - |
| E3_da3m | method A: segments ok, n: abs err median / p90 / bias | 8/66, n 8: 7.8% / 58.4% / -6.0% | - |
| E3_da3m | method B: segments ok, n: abs err median / p90 / bias | 66/66, n 65: 17.7% / 31.6% / -17.2% | - |
| E3_da3m | method Bsession: segments ok, n: abs err median / p90 / bias | 66/66, n 65: 18.4% / 25.5% / -18.2% | - |
| E3_da2 | scale label | Bsession+Acheck+Bcheck+Bnetcheck | - |
| E3_da2 | segments with a scale | 66/66 | - |
| E3_da2 | compared (tile GT) | 65 | - |
| E3_da2 | abs err median | 15.8% | - |
| E3_da2 | abs err p90 | 26.9% | - |
| E3_da2 | bias (median) | -14.6% | - |
| E3_da2 | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29, ep30, ep31, ep32, ep33, ep34, ep35, ep36, ep37, ep38, ep39, ep40, ep41, ep42, ep43, ep44, ep45, ep46, ep47, ep48, ep49, ep50, ep51, ep52, ep53, ep54, ep55, ep56, ep57, ep58, ep59, ep60, ep61, ep62, ep63, ep64, ep65 | - |
| E3_da2 | without flagged: abs err median / p90 | - / - | - |
| E3_da2 | method Bsession: segments ok, n: abs err median / p90 / bias | 66/66, n 65: 15.8% / 26.9% / -14.6% | - |
| E3_da2 | method A: segments ok, n: abs err median / p90 / bias | 8/66, n 8: 7.8% / 58.4% / -6.0% | - |
| E3_da2 | method B: segments ok, n: abs err median / p90 / bias | 66/66, n 65: 15.9% / 33.1% / -12.9% | - |
| E3_da2 | method Bnet: segments ok, n: abs err median / p90 / bias | 66/66, n 65: 76.6% / 119.9% / 76.6% | - |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp022_glove5_take2_ballscale n | exp022_glove5_take2_ballscale median | exp022_glove5_take2_ballscale p90 | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p90 |
|---|---|---|---|---|---|---|---|---|
| E3_da3m | oracle | anchors | 4616 |  |  | - | - | - |
| E3_da3m | oracle | 0.07 s | 4551 | 0.8 | 3.0 | - | - | - |
| E3_da3m | oracle | 0.13 s | 4486 | 1.2 | 4.8 | - | - | - |
| E3_da3m | oracle | 0.27 s | 4356 | 1.7 | 7.5 | - | - | - |
| E3_da3m | oracle | 0.53 s | 4121 | 2.4 | 11.7 | - | - | - |
| E3_da3m | oracle | 1.00 s | 3744 | 3.5 | 16.8 | - | - | - |
| E3_da3m | oracle | 2.00 s | 3094 | 4.6 | 24.1 | - | - | - |
| E3_da3m | oracle | 4.00 s | 1994 | 5.8 | 22.4 | - | - | - |
| E3_da3m | oracle | 6.67 s | 641 | 5.3 | 16.7 | - | - | - |
| E3_da3m | configured | anchors | 4616 |  |  | - | - | - |
| E3_da3m | configured | 0.07 s | 4551 | 0.9 | 3.1 | - | - | - |
| E3_da3m | configured | 0.13 s | 4486 | 1.3 | 5.0 | - | - | - |
| E3_da3m | configured | 0.27 s | 4356 | 1.9 | 8.0 | - | - | - |
| E3_da3m | configured | 0.53 s | 4121 | 2.9 | 12.6 | - | - | - |
| E3_da3m | configured | 1.00 s | 3744 | 4.4 | 19.3 | - | - | - |
| E3_da3m | configured | 2.00 s | 3094 | 6.4 | 27.4 | - | - | - |
| E3_da3m | configured | 4.00 s | 1994 | 8.8 | 28.8 | - | - | - |
| E3_da3m | configured | 6.67 s | 641 | 8.5 | 24.1 | - | - | - |
| E3_da2 | oracle | anchors | 4616 |  |  | - | - | - |
| E3_da2 | oracle | 0.07 s | 4551 | 0.8 | 3.0 | - | - | - |
| E3_da2 | oracle | 0.13 s | 4486 | 1.2 | 4.8 | - | - | - |
| E3_da2 | oracle | 0.27 s | 4356 | 1.7 | 7.5 | - | - | - |
| E3_da2 | oracle | 0.53 s | 4121 | 2.4 | 11.7 | - | - | - |
| E3_da2 | oracle | 1.00 s | 3744 | 3.5 | 16.8 | - | - | - |
| E3_da2 | oracle | 2.00 s | 3094 | 4.6 | 24.1 | - | - | - |
| E3_da2 | oracle | 4.00 s | 1994 | 5.8 | 22.4 | - | - | - |
| E3_da2 | oracle | 6.67 s | 641 | 5.3 | 16.7 | - | - | - |
| E3_da2 | configured | anchors | 4616 |  |  | - | - | - |
| E3_da2 | configured | 0.07 s | 4551 | 1.0 | 3.2 | - | - | - |
| E3_da2 | configured | 0.13 s | 4486 | 1.5 | 5.1 | - | - | - |
| E3_da2 | configured | 0.27 s | 4356 | 2.3 | 8.6 | - | - | - |
| E3_da2 | configured | 0.53 s | 4121 | 4.1 | 14.3 | - | - | - |
| E3_da2 | configured | 1.00 s | 3744 | 6.9 | 24.0 | - | - | - |
| E3_da2 | configured | 2.00 s | 3094 | 11.5 | 37.9 | - | - | - |
| E3_da2 | configured | 4.00 s | 1994 | 17.2 | 43.1 | - | - | - |
| E3_da2 | configured | 6.67 s | 641 | 15.1 | 40.8 | - | - | - |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp022_glove5_take2_ballscale n | exp022_glove5_take2_ballscale median | exp022_glove5_take2_ballscale p90 | exp015_glove5_take2 n | exp015_glove5_take2 median | exp015_glove5_take2 p90 |
|---|---|---|---|---|---|---|---|---|
| E3_da3m | every scale | anchors | 4616 |  |  | - | - | - |
| E3_da3m | every scale | 0.07 s | 4551 | 0.11 | 0.34 | - | - | - |
| E3_da3m | every scale | 0.13 s | 4486 | 0.15 | 0.53 | - | - | - |
| E3_da3m | every scale | 0.27 s | 4356 | 0.20 | 0.82 | - | - | - |
| E3_da3m | every scale | 0.53 s | 4121 | 0.28 | 1.23 | - | - | - |
| E3_da3m | every scale | 1.00 s | 3744 | 0.38 | 1.69 | - | - | - |
| E3_da3m | every scale | 2.00 s | 3094 | 0.49 | 2.25 | - | - | - |
| E3_da3m | every scale | 4.00 s | 1994 | 0.60 | 2.35 | - | - | - |
| E3_da3m | every scale | 6.67 s | 641 | 0.55 | 1.81 | - | - | - |
| E3_da2 | every scale | anchors | 4616 |  |  | - | - | - |
| E3_da2 | every scale | 0.07 s | 4551 | 0.11 | 0.34 | - | - | - |
| E3_da2 | every scale | 0.13 s | 4486 | 0.15 | 0.53 | - | - | - |
| E3_da2 | every scale | 0.27 s | 4356 | 0.20 | 0.82 | - | - | - |
| E3_da2 | every scale | 0.53 s | 4121 | 0.28 | 1.23 | - | - | - |
| E3_da2 | every scale | 1.00 s | 3744 | 0.38 | 1.69 | - | - | - |
| E3_da2 | every scale | 2.00 s | 3094 | 0.49 | 2.25 | - | - | - |
| E3_da2 | every scale | 4.00 s | 1994 | 0.60 | 2.35 | - | - | - |
| E3_da2 | every scale | 6.67 s | 641 | 0.55 | 1.81 | - | - | - |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp022_glove5_take2_ballscale | exp015_glove5_take2 |
|---|---|---|---|---|---|
| E3_da3m | every scale | anchors | 15 (1.00 s) | 4564 | - |
| E3_da3m | every scale | anchors | 30 (2.00 s) | 4571 | - |
| E3_da3m | every scale | anchors | 50 (3.33 s) | 4572 | - |
| E3_da3m | every scale | anchors | 100 (6.67 s) | 4572 | - |
| E3_da3m | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_da3m | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_da3m | every scale | counted steps per anchor, median | 50 (3.33 s) | 43 | - |
| E3_da3m | every scale | counted steps per anchor, median | 100 (6.67 s) | 52 | - |
| E3_da3m | oracle | pos mm, mean / median | 15 (1.00 s) | 4.5 / 2.5 | - |
| E3_da3m | oracle | pos mm, mean / median | 30 (2.00 s) | 6.3 / 3.4 | - |
| E3_da3m | oracle | pos mm, mean / median | 50 (3.33 s) | 7.4 / 4.0 | - |
| E3_da3m | oracle | pos mm, mean / median | 100 (6.67 s) | 8.0 / 4.4 | - |
| E3_da3m | configured | pos mm, mean / median | 15 (1.00 s) | 18.6 / 2.9 | - |
| E3_da3m | configured | pos mm, mean / median | 30 (2.00 s) | 28.1 / 4.1 | - |
| E3_da3m | configured | pos mm, mean / median | 50 (3.33 s) | 32.5 / 4.9 | - |
| E3_da3m | configured | pos mm, mean / median | 100 (6.67 s) | 33.7 / 5.9 | - |
| E3_da3m | every scale | rot deg, mean / median | 15 (1.00 s) | 0.52 / 0.28 | - |
| E3_da3m | every scale | rot deg, mean / median | 30 (2.00 s) | 0.71 / 0.37 | - |
| E3_da3m | every scale | rot deg, mean / median | 50 (3.33 s) | 0.84 / 0.43 | - |
| E3_da3m | every scale | rot deg, mean / median | 100 (6.67 s) | 0.91 / 0.48 | - |
| E3_da2 | every scale | anchors | 15 (1.00 s) | 4564 | - |
| E3_da2 | every scale | anchors | 30 (2.00 s) | 4571 | - |
| E3_da2 | every scale | anchors | 50 (3.33 s) | 4572 | - |
| E3_da2 | every scale | anchors | 100 (6.67 s) | 4572 | - |
| E3_da2 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_da2 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_da2 | every scale | counted steps per anchor, median | 50 (3.33 s) | 43 | - |
| E3_da2 | every scale | counted steps per anchor, median | 100 (6.67 s) | 52 | - |
| E3_da2 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.5 / 2.5 | - |
| E3_da2 | oracle | pos mm, mean / median | 30 (2.00 s) | 6.3 / 3.4 | - |
| E3_da2 | oracle | pos mm, mean / median | 50 (3.33 s) | 7.4 / 4.0 | - |
| E3_da2 | oracle | pos mm, mean / median | 100 (6.67 s) | 8.0 / 4.4 | - |
| E3_da2 | configured | pos mm, mean / median | 15 (1.00 s) | 15.6 / 3.9 | - |
| E3_da2 | configured | pos mm, mean / median | 30 (2.00 s) | 24.0 / 6.2 | - |
| E3_da2 | configured | pos mm, mean / median | 50 (3.33 s) | 28.5 / 8.4 | - |
| E3_da2 | configured | pos mm, mean / median | 100 (6.67 s) | 30.3 / 9.8 | - |
| E3_da2 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.52 / 0.28 | - |
| E3_da2 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.71 / 0.37 | - |
| E3_da2 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.84 / 0.43 | - |
| E3_da2 | every scale | rot deg, mean / median | 100 (6.67 s) | 0.91 / 0.48 | - |

### Ground-truth noise floor

| pairs | dt [s] | exp022_glove5_take2_ballscale n | exp022_glove5_take2_ballscale rot deg med / p95 | exp022_glove5_take2_ballscale trans mm med / p95 | exp015_glove5_take2 n | exp015_glove5_take2 rot deg med / p95 | exp015_glove5_take2 trans mm med / p95 |
|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 1611 | 0.14 / 1.29 | 2.3 / 23.7 | 1611 | 0.14 / 1.29 | 2.3 / 23.7 |
| same tiles | 0.5 | 1074 | 0.22 / 1.63 | 3.9 / 35.6 | 1074 | 0.22 / 1.63 | 3.9 / 35.6 |
| same tiles | 1.0 | 786 | 0.30 / 1.46 | 5.4 / 37.5 | 786 | 0.30 / 1.46 | 5.4 / 37.5 |
| same tiles | 2.0 | 579 | 0.42 / 3.20 | 8.1 / 63.4 | 579 | 0.42 / 3.20 | 8.1 / 63.4 |
| tile set changes | - | 1896 | 0.43 / 3.68 | 7.5 / 67.6 | 1896 | 0.43 / 3.68 | 7.5 / 67.6 |

