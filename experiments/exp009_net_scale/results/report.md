# exp009_net_scale: report (variant main)

30 segments. Runs: E1, E3_uniK, E3_m3d, E3_da3m, E3_moge (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3_uniK | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_m3d | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_da3m | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_moge | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |

n [frame pairs]:

- static, E3_uniK, E3_m3d, E3_da3m, E3_moge: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3_uniK | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_uniK | Bnet+Acheck | 2.51 / 10.19 | 5.70 / 24.58 | 8.23 / 36.07 | 10.63 / 49.29 | 11.57 / 32.52 |
| E3_m3d | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_m3d | Bnet+Acheck | 2.55 / 10.31 | 5.78 / 24.95 | 8.35 / 37.81 | 11.92 / 54.41 | 12.75 / 41.33 |
| E3_da3m | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_da3m | Bnet+Acheck | 2.48 / 10.02 | 5.47 / 24.29 | 7.81 / 36.32 | 10.37 / 45.44 | 9.69 / 17.96 |
| E3_moge | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_moge | Bnet+Acheck | 2.49 / 10.19 | 5.55 / 24.37 | 7.80 / 35.74 | 10.06 / 47.77 | 11.16 / 28.31 |

n [frame pairs]:

- E3_uniK oracle (tiles), E3_m3d oracle (tiles), E3_da3m oracle (tiles), E3_moge oracle (tiles): 0.08 s: 2371, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E3_uniK Bnet+Acheck, E3_m3d Bnet+Acheck, E3_da3m Bnet+Acheck, E3_moge Bnet+Acheck: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 14.2 | 43 | 100% |
| E3_uniK | 0.17% | 12.8 | 47 | 86% |
| E3_m3d | 0.17% | 12.8 | 47 | 86% |
| E3_da3m | 0.17% | 12.8 | 47 | 86% |
| E3_moge | 0.17% | 12.8 | 47 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3_uniK | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 6.7% | 17.0% | 6.5% | ep01, ep09, ep15, ep20, ep26, ep28, ep29 |
| E3_uniK | Bnet+Acheck, without flagged | 23/30 | 21 | 6.1% | 10.7% | 6.1% |  |
| E3_uniK | Bnet+Acheck, method Bnet (primary) | 30/30 | 28 | 6.7% | 17.0% | 6.5% |  |
| E3_uniK | Bnet+Acheck, method A (check) | 11/30 | 11 | 6.8% | 19.0% | -4.6% |  |
| E3_m3d | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 10.0% | 14.1% | 9.5% | ep01, ep09, ep15, ep20, ep24, ep26, ep28, ep29 |
| E3_m3d | Bnet+Acheck, without flagged | 22/30 | 20 | 8.4% | 13.3% | 8.4% |  |
| E3_m3d | Bnet+Acheck, method Bnet (primary) | 30/30 | 28 | 10.0% | 14.1% | 9.5% |  |
| E3_m3d | Bnet+Acheck, method A (check) | 11/30 | 11 | 6.8% | 19.0% | -4.6% |  |
| E3_da3m | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 3.1% | 9.4% | -0.1% | ep01, ep09, ep19, ep20, ep28, ep29 |
| E3_da3m | Bnet+Acheck, without flagged | 24/30 | 22 | 3.0% | 6.9% | 0.2% |  |
| E3_da3m | Bnet+Acheck, method Bnet (primary) | 30/30 | 28 | 3.1% | 9.4% | -0.1% |  |
| E3_da3m | Bnet+Acheck, method A (check) | 11/30 | 11 | 6.8% | 19.0% | -4.6% |  |
| E3_moge | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 4.2% | 11.0% | 2.0% | ep09, ep15, ep19, ep20, ep28, ep29 |
| E3_moge | Bnet+Acheck, without flagged | 24/30 | 22 | 4.1% | 10.1% | 2.6% |  |
| E3_moge | Bnet+Acheck, method Bnet (primary) | 30/30 | 28 | 4.2% | 11.0% | 2.0% |  |
| E3_moge | Bnet+Acheck, method A (check) | 11/30 | 11 | 6.8% | 19.0% | -4.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_uniK | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_uniK | Bnet+Acheck | 989 | 1.2 / 3.7 | 1.7 / 5.9 | 2.4 / 7.6 | 3.3 / 11.7 | 4.7 / 16.3 | 6.4 / 18.3 | 7.4 / 32.6 | 8.8 / 25.0 |
| E3_m3d | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_m3d | Bnet+Acheck | 989 | 1.2 / 3.8 | 1.8 / 6.1 | 2.4 / 8.0 | 3.3 / 13.0 | 4.6 / 19.4 | 6.6 / 23.6 | 7.2 / 41.4 | 7.7 / 34.2 |
| E3_da3m | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_da3m | Bnet+Acheck | 989 | 1.2 / 3.5 | 1.6 / 5.7 | 2.3 / 7.4 | 3.2 / 10.9 | 4.2 / 14.2 | 5.4 / 16.1 | 6.1 / 18.8 | 5.4 / 10.4 |
| E3_moge | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_moge | Bnet+Acheck | 989 | 1.2 / 3.6 | 1.6 / 5.8 | 2.3 / 7.4 | 3.1 / 11.3 | 4.1 / 15.5 | 5.3 / 16.7 | 6.3 / 28.6 | 6.7 / 20.6 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_uniK | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_m3d | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_da3m | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_moge | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3_uniK | anchors | 978 | 979 | 979 | 979 |
| E3_uniK | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_uniK | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_uniK | position [mm], Bnet+Acheck, mean / median | 5.1 / 3.4 | 7.2 / 4.7 | 8.9 / 5.8 | 10.7 / 6.4 |
| E3_uniK | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_m3d | anchors | 978 | 979 | 979 | 979 |
| E3_m3d | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_m3d | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_m3d | position [mm], Bnet+Acheck, mean / median | 5.5 / 3.5 | 7.8 / 4.8 | 9.7 / 6.0 | 11.6 / 6.8 |
| E3_m3d | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_da3m | anchors | 978 | 979 | 979 | 979 |
| E3_da3m | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_da3m | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_da3m | position [mm], Bnet+Acheck, mean / median | 4.8 / 3.2 | 6.6 / 4.3 | 8.0 / 5.3 | 9.4 / 5.8 |
| E3_da3m | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_moge | anchors | 978 | 979 | 979 | 979 |
| E3_moge | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_moge | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_moge | position [mm], Bnet+Acheck, mean / median | 4.9 / 3.2 | 6.8 / 4.2 | 8.3 / 5.1 | 10.0 / 5.8 |
| E3_moge | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3_uniK, H=100: 49 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 40 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles, dt 0.5 s | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles, dt 2.0 s | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes between the ends | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

## Error decomposition, run E3_da3m: SLAM or tile head rotation x configured or oracle scale

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3_da3m rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bnet+Acheck) or the per-segment tile oracle (`errdecomp_E3_da3m.json`). (1) SLAM rot + Bnet+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bnet+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bnet+Acheck s 4.2, (2) SLAM rot + oracle s 3.9, (3) tile rot + Bnet+Acheck s 7.6, (4) tile rot + oracle s 7.3 mm; chunk H=30 position mean: (1) SLAM rot + Bnet+Acheck s 6.6, (2) SLAM rot + oracle s 6.4, (3) tile rot + Bnet+Acheck s 12.2, (4) tile rot + oracle s 12.1 mm.

### Error decomposition, E3_da3m: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 989 | 1.2 / 3.5 | 1.6 / 5.7 | 2.3 / 7.4 | 3.2 / 10.9 | 4.2 / 14.2 | 5.4 / 16.1 | 6.1 / 18.8 | 5.4 / 10.4 |
| (2) SLAM rot + oracle s | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| (3) tile rot + Bnet+Acheck s | 989 | 2.2 / 6.3 | 3.1 / 9.2 | 4.1 / 12.2 | 5.7 / 17.3 | 7.6 / 25.1 | 9.9 / 29.9 | 9.8 / 33.1 | 9.4 / 17.5 |
| (4) tile rot + oracle s | 989 | 2.1 / 6.3 | 3.1 / 9.1 | 4.1 / 12.2 | 5.5 / 17.3 | 7.3 / 25.0 | 9.6 / 29.9 | 9.3 / 33.7 | 10.2 / 14.0 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

### Error decomposition, E3_da3m: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| (2) SLAM rot + oracle s | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| (3) tile rot + Bnet+Acheck s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

### Error decomposition, E3_da3m: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | anchors | 978 | 979 | 979 | 979 |
| (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 4.8 / 3.2 | 6.6 / 4.3 | 8.0 / 5.3 | 9.4 / 5.8 |
| (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| (2) SLAM rot + oracle s | anchors | 978 | 979 | 979 | 979 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| (3) tile rot + Bnet+Acheck s | anchors | 978 | 979 | 979 | 979 |
| (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 8.7 / 6.0 | 12.2 / 8.1 | 14.9 / 9.3 | 17.7 / 9.7 |
| (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.01 / 0.00 |
| (4) tile rot + oracle s | anchors | 978 | 979 | 979 | 979 |
| (4) tile rot + oracle s | position [mm], mean / median | 8.7 / 5.9 | 12.1 / 8.0 | 14.8 / 9.2 | 17.5 / 9.5 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.01 / 0.00 |

### Error decomposition, E3_da3m: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 756, 10-30 155, 30+ 0, unknown 78; oracle scale: 0-10 756, 10-30 155, 30+ 0, unknown 78; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 756 | 1.0 / 2.9 | 1.4 / 4.3 | 1.8 / 5.6 | 2.4 / 7.1 | 3.4 / 10.0 | 4.9 / 13.7 | 6.2 / 18.9 | 5.3 / 10.5 |
| 0-10 | (2) SLAM rot + oracle s | 756 | 1.0 / 2.9 | 1.4 / 4.2 | 1.8 / 5.6 | 2.4 / 7.1 | 3.3 / 10.5 | 4.9 / 12.6 | 5.9 / 16.4 | 5.6 / 9.8 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 756 | 1.9 / 5.7 | 2.7 / 8.0 | 3.4 / 10.9 | 4.7 / 14.7 | 6.3 / 20.1 | 9.0 / 26.7 | 9.8 / 34.3 | 9.5 / 17.5 |
| 0-10 | (4) tile rot + oracle s | 756 | 1.9 / 5.7 | 2.7 / 7.8 | 3.4 / 10.9 | 4.7 / 14.6 | 6.4 / 20.2 | 9.0 / 26.0 | 9.4 / 34.5 | 10.4 / 14.0 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 155 | 2.2 / 5.4 | 3.6 / 9.2 | 5.4 / 12.7 | 8.2 / 16.7 | 11.5 / 44.8 | 13.8 / 96.1 | - | - |
| 10-30 | (2) SLAM rot + oracle s | 155 | 2.1 / 5.4 | 3.5 / 9.3 | 5.4 / 12.2 | 8.3 / 16.8 | 11.2 / 44.8 | 13.8 / 95.9 | - | - |
| 10-30 | (3) tile rot + Bnet+Acheck s | 155 | 3.3 / 8.8 | 5.5 / 15.7 | 8.3 / 21.5 | 12.8 / 37.9 | 17.3 / 103.7 | 19.9 / 212.4 | - | - |
| 10-30 | (4) tile rot + oracle s | 155 | 3.2 / 8.8 | 5.5 / 15.8 | 8.4 / 21.3 | 12.5 / 38.0 | 16.6 / 103.6 | 22.0 / 212.1 | - | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 756 | 0.13 / 0.40 | 0.18 / 0.54 | 0.23 / 0.69 | 0.31 / 1.02 | 0.42 / 1.27 | 0.60 / 1.86 | 0.57 / 2.42 | 0.60 / 1.17 |
| 0-10 | (2) SLAM rot + oracle s | 756 | 0.13 / 0.40 | 0.18 / 0.54 | 0.23 / 0.69 | 0.31 / 1.02 | 0.42 / 1.27 | 0.60 / 1.86 | 0.57 / 2.42 | 0.60 / 1.17 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 756 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 756 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 155 | 0.20 / 0.64 | 0.32 / 1.12 | 0.49 / 1.81 | 0.77 / 2.64 | 1.05 / 6.55 | 1.39 / 13.05 | - | - |
| 10-30 | (2) SLAM rot + oracle s | 155 | 0.20 / 0.64 | 0.32 / 1.12 | 0.49 / 1.81 | 0.77 / 2.64 | 1.05 / 6.55 | 1.39 / 13.05 | - | - |
| 10-30 | (3) tile rot + Bnet+Acheck s | 155 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - | - |
| 10-30 | (4) tile rot + oracle s | 155 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 3.8 / 2.6 | 5.2 / 3.8 | 6.8 / 4.8 | 8.6 / 5.5 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.47 / 0.34 | 0.64 / 0.47 | 0.83 / 0.56 | 1.05 / 0.57 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 3.7 / 2.6 | 5.1 / 3.7 | 6.6 / 4.7 | 8.4 / 5.1 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.47 / 0.34 | 0.64 / 0.47 | 0.83 / 0.56 | 1.05 / 0.57 |
| 0-10 | (3) tile rot + Bnet+Acheck s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 7.3 / 5.0 | 10.0 / 7.1 | 13.1 / 9.0 | 16.7 / 9.5 |
| 0-10 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 7.2 / 5.0 | 9.9 / 7.2 | 13.0 / 8.9 | 16.5 / 9.3 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 10.1 / 7.4 | 14.6 / 9.9 | 15.5 / 9.9 | 15.5 / 9.9 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 1.11 / 0.71 | 1.64 / 0.81 | 1.75 / 0.84 | 1.75 / 0.84 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 10.0 / 7.2 | 14.4 / 9.3 | 15.2 / 9.6 | 15.2 / 9.6 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 1.11 / 0.71 | 1.64 / 0.81 | 1.75 / 0.84 | 1.75 / 0.84 |
| 10-30 | (3) tile rot + Bnet+Acheck s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 17.4 / 11.2 | 26.0 / 13.6 | 27.7 / 13.6 | 27.7 / 13.6 |
| 10-30 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 17.3 / 10.7 | 26.0 / 13.0 | 27.7 / 13.2 | 27.7 / 13.2 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 |
| 30+ | (1) SLAM rot + Bnet+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (2) SLAM rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (4) tile rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | rotation [deg], mean / median | - | - | - | - |

### Error decomposition, E3_da3m: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.3 / 4.3 | 1.9 / 5.8 | 2.5 / 7.7 | 3.4 / 11.1 | 4.4 / 15.5 | 6.0 / 20.9 | 5.0 / 24.0 | 5.6 / 8.0 |
| translation part dt [mm], Bnet+Acheck s, median / p90 | 2.2 / 6.2 | 3.1 / 9.2 | 4.1 / 12.2 | 5.7 / 17.3 | 7.6 / 25.1 | 9.9 / 29.9 | 9.7 / 33.1 | 9.4 / 17.5 |
| translation part dt [mm], oracle s, median / p90 | 2.1 / 6.2 | 3.1 / 9.1 | 4.1 / 12.3 | 5.5 / 17.3 | 7.3 / 24.9 | 9.6 / 29.9 | 9.3 / 33.7 | 10.2 / 14.0 |
| cos(dR b, dt), Bnet+Acheck s, median | -0.91 | -0.91 | -0.91 | -0.93 | -0.94 | -0.91 | -0.91 | -0.86 |
| cos(dR b, dt), oracle s, median | -0.91 | -0.91 | -0.90 | -0.92 | -0.94 | -0.92 | -0.90 | -0.85 |

Checks: (1) SLAM rot + Bnet+Acheck s vs `labels_E3_da3m@Bnet+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3_da3m.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 48735 pairs): max |position difference| 5.0e-13 mm, max |R difference| 7.2e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 48735 pairs): max |position difference| 3.9e-13 mm, max |R difference| 7.2e-16.

## Comparison with other experiments

- exp007_v2_session_scale: `exp007_v2_session_scale/results/metrics.json`
- exp008_depth_models: `exp008_depth_models/results/metrics.json`
- runs only in exp007_v2_session_scale (not shown): E3
- runs only in exp008_depth_models (not shown): E3_da2, E3_uni, E3_dproK, E3_dpro

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| static | 0.08 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - | - | - | - |
| E3_uniK | 0.08 | 2380 | 0.16 | 0.64 | - | - | - | 2380 | 0.16 | 0.64 |
| E3_uniK | 0.5 | 1931 | 0.36 | 1.49 | - | - | - | 1931 | 0.36 | 1.49 |
| E3_uniK | 1.0 | 1612 | 0.52 | 2.25 | - | - | - | 1612 | 0.52 | 2.25 |
| E3_uniK | 2.0 | 1248 | 0.65 | 2.60 | - | - | - | 1248 | 0.65 | 2.60 |
| E3_uniK | 6.67 | 88 | 0.58 | 1.26 | - | - | - | 88 | 0.58 | 1.26 |
| E3_m3d | 0.08 | 2380 | 0.16 | 0.64 | - | - | - | 2380 | 0.16 | 0.64 |
| E3_m3d | 0.5 | 1931 | 0.36 | 1.49 | - | - | - | 1931 | 0.36 | 1.49 |
| E3_m3d | 1.0 | 1612 | 0.52 | 2.25 | - | - | - | 1612 | 0.52 | 2.25 |
| E3_m3d | 2.0 | 1248 | 0.65 | 2.60 | - | - | - | 1248 | 0.65 | 2.60 |
| E3_m3d | 6.67 | 88 | 0.58 | 1.26 | - | - | - | 88 | 0.58 | 1.26 |
| E3_da3m | 0.08 | 2380 | 0.16 | 0.64 | - | - | - | 2380 | 0.16 | 0.64 |
| E3_da3m | 0.5 | 1931 | 0.36 | 1.49 | - | - | - | 1931 | 0.36 | 1.49 |
| E3_da3m | 1.0 | 1612 | 0.52 | 2.25 | - | - | - | 1612 | 0.52 | 2.25 |
| E3_da3m | 2.0 | 1248 | 0.65 | 2.60 | - | - | - | 1248 | 0.65 | 2.60 |
| E3_da3m | 6.67 | 88 | 0.58 | 1.26 | - | - | - | 88 | 0.58 | 1.26 |
| E3_moge | 0.08 | 2380 | 0.16 | 0.64 | - | - | - | 2380 | 0.16 | 0.64 |
| E3_moge | 0.5 | 1931 | 0.36 | 1.49 | - | - | - | 1931 | 0.36 | 1.49 |
| E3_moge | 1.0 | 1612 | 0.52 | 2.25 | - | - | - | 1612 | 0.52 | 2.25 |
| E3_moge | 2.0 | 1248 | 0.65 | 2.60 | - | - | - | 1248 | 0.65 | 2.60 |
| E3_moge | 6.67 | 88 | 0.58 | 1.26 | - | - | - | 88 | 0.58 | 1.26 |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - | - | - | - |
| E3_uniK | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - | 2371 | 2.49 | 10.13 |
| E3_uniK | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - | 1931 | 5.47 | 24.24 |
| E3_uniK | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - | 1612 | 7.46 | 36.49 |
| E3_uniK | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - | 1248 | 9.87 | 46.80 |
| E3_uniK | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - | 88 | 10.15 | 16.47 |
| E3_uniK | configured | 0.08 | 2380 | 2.51 | 10.19 | - | - | - | 2380 | 2.46 | 9.82 |
| E3_uniK | configured | 0.5 | 1931 | 5.70 | 24.58 | - | - | - | 1931 | 5.69 | 25.45 |
| E3_uniK | configured | 1.0 | 1612 | 8.23 | 36.07 | - | - | - | 1612 | 8.59 | 40.02 |
| E3_uniK | configured | 2.0 | 1248 | 10.63 | 49.29 | - | - | - | 1248 | 12.78 | 57.07 |
| E3_uniK | configured | 6.67 | 88 | 11.57 | 32.52 | - | - | - | 88 | 11.75 | 26.97 |
| E3_m3d | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - | 2371 | 2.49 | 10.13 |
| E3_m3d | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - | 1931 | 5.47 | 24.24 |
| E3_m3d | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - | 1612 | 7.46 | 36.49 |
| E3_m3d | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - | 1248 | 9.87 | 46.80 |
| E3_m3d | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - | 88 | 10.15 | 16.47 |
| E3_m3d | configured | 0.08 | 2380 | 2.55 | 10.31 | - | - | - | 2380 | 2.45 | 9.86 |
| E3_m3d | configured | 0.5 | 1931 | 5.78 | 24.95 | - | - | - | 1931 | 5.60 | 24.70 |
| E3_m3d | configured | 1.0 | 1612 | 8.35 | 37.81 | - | - | - | 1612 | 8.26 | 38.57 |
| E3_m3d | configured | 2.0 | 1248 | 11.92 | 54.41 | - | - | - | 1248 | 11.31 | 50.54 |
| E3_m3d | configured | 6.67 | 88 | 12.75 | 41.33 | - | - | - | 88 | 9.11 | 18.94 |
| E3_da3m | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - | 2371 | 2.49 | 10.13 |
| E3_da3m | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - | 1931 | 5.47 | 24.24 |
| E3_da3m | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - | 1612 | 7.46 | 36.49 |
| E3_da3m | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - | 1248 | 9.87 | 46.80 |
| E3_da3m | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - | 88 | 10.15 | 16.47 |
| E3_da3m | configured | 0.08 | 2380 | 2.48 | 10.02 | - | - | - | 2380 | 2.47 | 9.71 |
| E3_da3m | configured | 0.5 | 1931 | 5.47 | 24.29 | - | - | - | 1931 | 6.43 | 28.26 |
| E3_da3m | configured | 1.0 | 1612 | 7.81 | 36.32 | - | - | - | 1612 | 9.91 | 48.26 |
| E3_da3m | configured | 2.0 | 1248 | 10.37 | 45.44 | - | - | - | 1248 | 14.63 | 76.27 |
| E3_da3m | configured | 6.67 | 88 | 9.69 | 17.96 | - | - | - | 88 | 14.62 | 49.89 |
| E3_moge | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - | 2371 | 2.49 | 10.13 |
| E3_moge | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - | 1931 | 5.47 | 24.24 |
| E3_moge | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - | 1612 | 7.46 | 36.49 |
| E3_moge | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - | 1248 | 9.87 | 46.80 |
| E3_moge | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - | 88 | 10.15 | 16.47 |
| E3_moge | configured | 0.08 | 2380 | 2.49 | 10.19 | - | - | - | 2380 | 2.47 | 9.70 |
| E3_moge | configured | 0.5 | 1931 | 5.55 | 24.37 | - | - | - | 1931 | 6.49 | 28.07 |
| E3_moge | configured | 1.0 | 1612 | 7.80 | 35.74 | - | - | - | 1612 | 10.20 | 48.11 |
| E3_moge | configured | 2.0 | 1248 | 10.06 | 47.77 | - | - | - | 1248 | 15.06 | 74.54 |
| E3_moge | configured | 6.67 | 88 | 11.16 | 28.31 | - | - | - | 88 | 13.33 | 48.27 |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp009_net_scale | exp007_v2_session_scale | exp008_depth_models |
|---|---|---|---|---|
| E1 | track fail | - | - | - |
| E1 | keyframes / segment | 14.2 | 14.2 | 14.2 |
| E1 | runtime s / segment | 43 | 43 | 43 |
| E1 | valid pixels | 100% | 100% | 100% |
| E3_uniK | track fail | 0.17% | - | 0.17% |
| E3_uniK | keyframes / segment | 12.8 | - | 12.8 |
| E3_uniK | runtime s / segment | 47 | - | 47 |
| E3_uniK | valid pixels | 86% | - | 86% |
| E3_m3d | track fail | 0.17% | - | 0.17% |
| E3_m3d | keyframes / segment | 12.8 | - | 12.8 |
| E3_m3d | runtime s / segment | 47 | - | 47 |
| E3_m3d | valid pixels | 86% | - | 86% |
| E3_da3m | track fail | 0.17% | - | 0.17% |
| E3_da3m | keyframes / segment | 12.8 | - | 12.8 |
| E3_da3m | runtime s / segment | 47 | - | 47 |
| E3_da3m | valid pixels | 86% | - | 86% |
| E3_moge | track fail | 0.17% | - | 0.17% |
| E3_moge | keyframes / segment | 12.8 | - | 12.8 |
| E3_moge | runtime s / segment | 47 | - | 47 |
| E3_moge | valid pixels | 86% | - | 86% |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp009_net_scale | exp007_v2_session_scale | exp008_depth_models |
|---|---|---|---|---|
| E3_uniK | scale label | Bnet+Acheck | - | Bsession+Bcheck+Bnetcheck |
| E3_uniK | segments with a scale | 30/30 | - | 30/30 |
| E3_uniK | compared (tile GT) | 28 | - | 28 |
| E3_uniK | abs err median | 6.7% | - | 9.4% |
| E3_uniK | abs err p90 | 17.0% | - | 13.8% |
| E3_uniK | bias (median) | 6.5% | - | -9.4% |
| E3_uniK | flagged | ep01, ep09, ep15, ep20, ep26, ep28, ep29 | - | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_uniK | without flagged: abs err median / p90 | 6.1% / 10.7% | - | - / - |
| E3_uniK | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 6.7% / 17.0% / 6.5% | - | 30/30, n 28: 6.7% / 17.0% / 6.5% |
| E3_uniK | method A: segments ok, n: abs err median / p90 / bias | 11/30, n 11: 6.8% / 19.0% / -4.6% | - | - |
| E3_uniK | method Bsession: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 9.4% / 13.8% / -9.4% |
| E3_uniK | method B: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 9.1% / 21.3% / -9.1% |
| E3_m3d | scale label | Bnet+Acheck | - | Bsession+Bcheck+Bnetcheck |
| E3_m3d | segments with a scale | 30/30 | - | 30/30 |
| E3_m3d | compared (tile GT) | 28 | - | 28 |
| E3_m3d | abs err median | 10.0% | - | 6.2% |
| E3_m3d | abs err p90 | 14.1% | - | 11.7% |
| E3_m3d | bias (median) | 9.5% | - | -5.7% |
| E3_m3d | flagged | ep01, ep09, ep15, ep20, ep24, ep26, ep28, ep29 | - | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_m3d | without flagged: abs err median / p90 | 8.4% / 13.3% | - | - / - |
| E3_m3d | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 10.0% / 14.1% / 9.5% | - | 30/30, n 28: 10.0% / 14.1% / 9.5% |
| E3_m3d | method A: segments ok, n: abs err median / p90 / bias | 11/30, n 11: 6.8% / 19.0% / -4.6% | - | - |
| E3_m3d | method Bsession: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 6.2% / 11.7% / -5.7% |
| E3_m3d | method B: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 8.2% / 21.1% / -7.4% |
| E3_da3m | scale label | Bnet+Acheck | - | Bsession+Bcheck+Bnetcheck |
| E3_da3m | segments with a scale | 30/30 | - | 30/30 |
| E3_da3m | compared (tile GT) | 28 | - | 28 |
| E3_da3m | abs err median | 3.1% | - | 18.4% |
| E3_da3m | abs err p90 | 9.4% | - | 23.3% |
| E3_da3m | bias (median) | -0.1% | - | -18.4% |
| E3_da3m | flagged | ep01, ep09, ep19, ep20, ep28, ep29 | - | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_da3m | without flagged: abs err median / p90 | 3.0% / 6.9% | - | - / - |
| E3_da3m | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 3.1% / 9.4% / -0.1% | - | 30/30, n 28: 3.1% / 9.4% / -0.1% |
| E3_da3m | method A: segments ok, n: abs err median / p90 / bias | 11/30, n 11: 6.8% / 19.0% / -4.6% | - | - |
| E3_da3m | method Bsession: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 18.4% / 23.3% / -18.4% |
| E3_da3m | method B: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 15.8% / 32.8% / -15.8% |
| E3_moge | scale label | Bnet+Acheck | - | Bsession+Bcheck+Bnetcheck |
| E3_moge | segments with a scale | 30/30 | - | 30/30 |
| E3_moge | compared (tile GT) | 28 | - | 28 |
| E3_moge | abs err median | 4.2% | - | 19.7% |
| E3_moge | abs err p90 | 11.0% | - | 25.6% |
| E3_moge | bias (median) | 2.0% | - | -19.7% |
| E3_moge | flagged | ep09, ep15, ep19, ep20, ep28, ep29 | - | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_moge | without flagged: abs err median / p90 | 4.1% / 10.1% | - | - / - |
| E3_moge | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 4.2% / 11.0% / 2.0% | - | 30/30, n 28: 4.2% / 11.0% / 2.0% |
| E3_moge | method A: segments ok, n: abs err median / p90 / bias | 11/30, n 11: 6.8% / 19.0% / -4.6% | - | - |
| E3_moge | method Bsession: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 19.7% / 25.6% / -19.7% |
| E3_moge | method B: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 17.8% / 31.4% / -17.8% |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3_uniK | oracle | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_uniK | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - | 976 | 1.2 | 3.6 |
| E3_uniK | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - | 963 | 1.6 | 5.7 |
| E3_uniK | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - | 937 | 2.3 | 7.3 |
| E3_uniK | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - | 890 | 3.1 | 11.2 |
| E3_uniK | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - | 814 | 3.9 | 13.9 |
| E3_uniK | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - | 676 | 5.2 | 14.8 |
| E3_uniK | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - | 398 | 5.9 | 15.8 |
| E3_uniK | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - | 55 | 5.6 | 9.7 |
| E3_uniK | configured | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_uniK | configured | 0.07 s | 976 | 1.2 | 3.7 | - | - | - | 976 | 1.2 | 3.6 |
| E3_uniK | configured | 0.13 s | 963 | 1.7 | 5.9 | - | - | - | 963 | 1.6 | 5.9 |
| E3_uniK | configured | 0.27 s | 937 | 2.4 | 7.6 | - | - | - | 937 | 2.4 | 8.3 |
| E3_uniK | configured | 0.53 s | 890 | 3.3 | 11.7 | - | - | - | 890 | 3.4 | 13.0 |
| E3_uniK | configured | 1.00 s | 814 | 4.7 | 16.3 | - | - | - | 814 | 4.9 | 18.6 |
| E3_uniK | configured | 2.00 s | 676 | 6.4 | 18.3 | - | - | - | 676 | 6.7 | 27.0 |
| E3_uniK | configured | 4.00 s | 398 | 7.4 | 32.6 | - | - | - | 398 | 6.8 | 27.6 |
| E3_uniK | configured | 6.67 s | 55 | 8.8 | 25.0 | - | - | - | 55 | 7.9 | 25.4 |
| E3_m3d | oracle | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_m3d | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - | 976 | 1.2 | 3.6 |
| E3_m3d | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - | 963 | 1.6 | 5.7 |
| E3_m3d | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - | 937 | 2.3 | 7.3 |
| E3_m3d | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - | 890 | 3.1 | 11.2 |
| E3_m3d | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - | 814 | 3.9 | 13.9 |
| E3_m3d | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - | 676 | 5.2 | 14.8 |
| E3_m3d | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - | 398 | 5.9 | 15.8 |
| E3_m3d | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - | 55 | 5.6 | 9.7 |
| E3_m3d | configured | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_m3d | configured | 0.07 s | 976 | 1.2 | 3.8 | - | - | - | 976 | 1.2 | 3.5 |
| E3_m3d | configured | 0.13 s | 963 | 1.8 | 6.1 | - | - | - | 963 | 1.6 | 5.6 |
| E3_m3d | configured | 0.27 s | 937 | 2.4 | 8.0 | - | - | - | 937 | 2.4 | 7.8 |
| E3_m3d | configured | 0.53 s | 890 | 3.3 | 13.0 | - | - | - | 890 | 3.3 | 11.9 |
| E3_m3d | configured | 1.00 s | 814 | 4.6 | 19.4 | - | - | - | 814 | 4.6 | 15.8 |
| E3_m3d | configured | 2.00 s | 676 | 6.6 | 23.6 | - | - | - | 676 | 6.1 | 20.2 |
| E3_m3d | configured | 4.00 s | 398 | 7.2 | 41.4 | - | - | - | 398 | 6.7 | 22.6 |
| E3_m3d | configured | 6.67 s | 55 | 7.7 | 34.2 | - | - | - | 55 | 6.2 | 14.9 |
| E3_da3m | oracle | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_da3m | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - | 976 | 1.2 | 3.6 |
| E3_da3m | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - | 963 | 1.6 | 5.7 |
| E3_da3m | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - | 937 | 2.3 | 7.3 |
| E3_da3m | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - | 890 | 3.1 | 11.2 |
| E3_da3m | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - | 814 | 3.9 | 13.9 |
| E3_da3m | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - | 676 | 5.2 | 14.8 |
| E3_da3m | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - | 398 | 5.9 | 15.8 |
| E3_da3m | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - | 55 | 5.6 | 9.7 |
| E3_da3m | configured | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_da3m | configured | 0.07 s | 976 | 1.2 | 3.5 | - | - | - | 976 | 1.2 | 3.7 |
| E3_da3m | configured | 0.13 s | 963 | 1.6 | 5.7 | - | - | - | 963 | 1.8 | 6.3 |
| E3_da3m | configured | 0.27 s | 937 | 2.3 | 7.4 | - | - | - | 937 | 2.7 | 10.0 |
| E3_da3m | configured | 0.53 s | 890 | 3.2 | 10.9 | - | - | - | 890 | 4.2 | 16.3 |
| E3_da3m | configured | 1.00 s | 814 | 4.2 | 14.2 | - | - | - | 814 | 6.6 | 25.9 |
| E3_da3m | configured | 2.00 s | 676 | 5.4 | 16.1 | - | - | - | 676 | 9.1 | 42.5 |
| E3_da3m | configured | 4.00 s | 398 | 6.1 | 18.8 | - | - | - | 398 | 9.0 | 45.6 |
| E3_da3m | configured | 6.67 s | 55 | 5.4 | 10.4 | - | - | - | 55 | 11.8 | 49.6 |
| E3_moge | oracle | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_moge | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - | 976 | 1.2 | 3.6 |
| E3_moge | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - | 963 | 1.6 | 5.7 |
| E3_moge | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - | 937 | 2.3 | 7.3 |
| E3_moge | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - | 890 | 3.1 | 11.2 |
| E3_moge | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - | 814 | 3.9 | 13.9 |
| E3_moge | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - | 676 | 5.2 | 14.8 |
| E3_moge | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - | 398 | 5.9 | 15.8 |
| E3_moge | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - | 55 | 5.6 | 9.7 |
| E3_moge | configured | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_moge | configured | 0.07 s | 976 | 1.2 | 3.6 | - | - | - | 976 | 1.2 | 3.7 |
| E3_moge | configured | 0.13 s | 963 | 1.6 | 5.8 | - | - | - | 963 | 1.8 | 6.3 |
| E3_moge | configured | 0.27 s | 937 | 2.3 | 7.4 | - | - | - | 937 | 2.6 | 10.0 |
| E3_moge | configured | 0.53 s | 890 | 3.1 | 11.3 | - | - | - | 890 | 4.1 | 16.0 |
| E3_moge | configured | 1.00 s | 814 | 4.1 | 15.5 | - | - | - | 814 | 6.4 | 26.6 |
| E3_moge | configured | 2.00 s | 676 | 5.3 | 16.7 | - | - | - | 676 | 8.8 | 41.6 |
| E3_moge | configured | 4.00 s | 398 | 6.3 | 28.6 | - | - | - | 398 | 9.4 | 43.9 |
| E3_moge | configured | 6.67 s | 55 | 6.7 | 20.6 | - | - | - | 55 | 10.4 | 47.9 |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3_uniK | every scale | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_uniK | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - | 976 | 0.14 | 0.44 |
| E3_uniK | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - | 963 | 0.20 | 0.61 |
| E3_uniK | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - | 937 | 0.27 | 0.83 |
| E3_uniK | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - | 890 | 0.36 | 1.18 |
| E3_uniK | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - | 814 | 0.50 | 1.59 |
| E3_uniK | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - | 676 | 0.65 | 1.99 |
| E3_uniK | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - | 398 | 0.56 | 2.41 |
| E3_uniK | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - | 55 | 0.57 | 1.16 |
| E3_m3d | every scale | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_m3d | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - | 976 | 0.14 | 0.44 |
| E3_m3d | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - | 963 | 0.20 | 0.61 |
| E3_m3d | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - | 937 | 0.27 | 0.83 |
| E3_m3d | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - | 890 | 0.36 | 1.18 |
| E3_m3d | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - | 814 | 0.50 | 1.59 |
| E3_m3d | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - | 676 | 0.65 | 1.99 |
| E3_m3d | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - | 398 | 0.56 | 2.41 |
| E3_m3d | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - | 55 | 0.57 | 1.16 |
| E3_da3m | every scale | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_da3m | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - | 976 | 0.14 | 0.44 |
| E3_da3m | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - | 963 | 0.20 | 0.61 |
| E3_da3m | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - | 937 | 0.27 | 0.83 |
| E3_da3m | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - | 890 | 0.36 | 1.18 |
| E3_da3m | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - | 814 | 0.50 | 1.59 |
| E3_da3m | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - | 676 | 0.65 | 1.99 |
| E3_da3m | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - | 398 | 0.56 | 2.41 |
| E3_da3m | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - | 55 | 0.57 | 1.16 |
| E3_moge | every scale | anchors | 989 |  |  | - | - | - | 989 |  |  |
| E3_moge | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - | 976 | 0.14 | 0.44 |
| E3_moge | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - | 963 | 0.20 | 0.61 |
| E3_moge | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - | 937 | 0.27 | 0.83 |
| E3_moge | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - | 890 | 0.36 | 1.18 |
| E3_moge | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - | 814 | 0.50 | 1.59 |
| E3_moge | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - | 676 | 0.65 | 1.99 |
| E3_moge | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - | 398 | 0.56 | 2.41 |
| E3_moge | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - | 55 | 0.57 | 1.16 |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp009_net_scale | exp007_v2_session_scale | exp008_depth_models |
|---|---|---|---|---|---|---|
| E3_uniK | every scale | anchors | 15 (1.00 s) | 978 | - | 978 |
| E3_uniK | every scale | anchors | 30 (2.00 s) | 979 | - | 979 |
| E3_uniK | every scale | anchors | 50 (3.33 s) | 979 | - | 979 |
| E3_uniK | every scale | anchors | 100 (6.67 s) | 979 | - | 979 |
| E3_uniK | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | 15 |
| E3_uniK | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - | 30 |
| E3_uniK | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - | 46 |
| E3_uniK | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - | 49 |
| E3_uniK | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - | 4.7 / 3.2 |
| E3_uniK | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - | 6.4 / 4.2 |
| E3_uniK | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - | 7.7 / 4.9 |
| E3_uniK | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - | 9.1 / 5.5 |
| E3_uniK | configured | pos mm, mean / median | 15 (1.00 s) | 5.1 / 3.4 | - | 5.2 / 3.4 |
| E3_uniK | configured | pos mm, mean / median | 30 (2.00 s) | 7.2 / 4.7 | - | 7.5 / 4.9 |
| E3_uniK | configured | pos mm, mean / median | 50 (3.33 s) | 8.9 / 5.8 | - | 9.3 / 6.1 |
| E3_uniK | configured | pos mm, mean / median | 100 (6.67 s) | 10.7 / 6.4 | - | 10.8 / 7.5 |
| E3_uniK | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - | 0.57 / 0.39 |
| E3_uniK | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - | 0.78 / 0.51 |
| E3_uniK | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - | 0.95 / 0.58 |
| E3_uniK | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - | 1.11 / 0.59 |
| E3_m3d | every scale | anchors | 15 (1.00 s) | 978 | - | 978 |
| E3_m3d | every scale | anchors | 30 (2.00 s) | 979 | - | 979 |
| E3_m3d | every scale | anchors | 50 (3.33 s) | 979 | - | 979 |
| E3_m3d | every scale | anchors | 100 (6.67 s) | 979 | - | 979 |
| E3_m3d | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | 15 |
| E3_m3d | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - | 30 |
| E3_m3d | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - | 46 |
| E3_m3d | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - | 49 |
| E3_m3d | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - | 4.7 / 3.2 |
| E3_m3d | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - | 6.4 / 4.2 |
| E3_m3d | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - | 7.7 / 4.9 |
| E3_m3d | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - | 9.1 / 5.5 |
| E3_m3d | configured | pos mm, mean / median | 15 (1.00 s) | 5.5 / 3.5 | - | 4.9 / 3.4 |
| E3_m3d | configured | pos mm, mean / median | 30 (2.00 s) | 7.8 / 4.8 | - | 7.0 / 4.5 |
| E3_m3d | configured | pos mm, mean / median | 50 (3.33 s) | 9.7 / 6.0 | - | 8.5 / 5.5 |
| E3_m3d | configured | pos mm, mean / median | 100 (6.67 s) | 11.6 / 6.8 | - | 9.9 / 6.4 |
| E3_m3d | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - | 0.57 / 0.39 |
| E3_m3d | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - | 0.78 / 0.51 |
| E3_m3d | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - | 0.95 / 0.58 |
| E3_m3d | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - | 1.11 / 0.59 |
| E3_da3m | every scale | anchors | 15 (1.00 s) | 978 | - | 978 |
| E3_da3m | every scale | anchors | 30 (2.00 s) | 979 | - | 979 |
| E3_da3m | every scale | anchors | 50 (3.33 s) | 979 | - | 979 |
| E3_da3m | every scale | anchors | 100 (6.67 s) | 979 | - | 979 |
| E3_da3m | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | 15 |
| E3_da3m | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - | 30 |
| E3_da3m | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - | 46 |
| E3_da3m | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - | 49 |
| E3_da3m | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - | 4.7 / 3.2 |
| E3_da3m | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - | 6.4 / 4.2 |
| E3_da3m | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - | 7.7 / 4.9 |
| E3_da3m | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - | 9.1 / 5.5 |
| E3_da3m | configured | pos mm, mean / median | 15 (1.00 s) | 4.8 / 3.2 | - | 6.3 / 4.2 |
| E3_da3m | configured | pos mm, mean / median | 30 (2.00 s) | 6.6 / 4.3 | - | 9.6 / 6.2 |
| E3_da3m | configured | pos mm, mean / median | 50 (3.33 s) | 8.0 / 5.3 | - | 12.0 / 7.4 |
| E3_da3m | configured | pos mm, mean / median | 100 (6.67 s) | 9.4 / 5.8 | - | 14.0 / 9.5 |
| E3_da3m | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - | 0.57 / 0.39 |
| E3_da3m | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - | 0.78 / 0.51 |
| E3_da3m | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - | 0.95 / 0.58 |
| E3_da3m | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - | 1.11 / 0.59 |
| E3_moge | every scale | anchors | 15 (1.00 s) | 978 | - | 978 |
| E3_moge | every scale | anchors | 30 (2.00 s) | 979 | - | 979 |
| E3_moge | every scale | anchors | 50 (3.33 s) | 979 | - | 979 |
| E3_moge | every scale | anchors | 100 (6.67 s) | 979 | - | 979 |
| E3_moge | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | 15 |
| E3_moge | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - | 30 |
| E3_moge | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - | 46 |
| E3_moge | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - | 49 |
| E3_moge | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - | 4.7 / 3.2 |
| E3_moge | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - | 6.4 / 4.2 |
| E3_moge | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - | 7.7 / 4.9 |
| E3_moge | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - | 9.1 / 5.5 |
| E3_moge | configured | pos mm, mean / median | 15 (1.00 s) | 4.9 / 3.2 | - | 6.3 / 4.1 |
| E3_moge | configured | pos mm, mean / median | 30 (2.00 s) | 6.8 / 4.2 | - | 9.6 / 6.1 |
| E3_moge | configured | pos mm, mean / median | 50 (3.33 s) | 8.3 / 5.1 | - | 12.0 / 7.3 |
| E3_moge | configured | pos mm, mean / median | 100 (6.67 s) | 10.0 / 5.8 | - | 13.8 / 9.1 |
| E3_moge | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - | 0.57 / 0.39 |
| E3_moge | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - | 0.78 / 0.51 |
| E3_moge | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - | 0.95 / 0.58 |
| E3_moge | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - | 1.11 / 0.59 |

### Ground-truth noise floor

| pairs | dt [s] | exp009_net_scale n | exp009_net_scale rot deg med / p95 | exp009_net_scale trans mm med / p95 | exp007_v2_session_scale n | exp007_v2_session_scale rot deg med / p95 | exp007_v2_session_scale trans mm med / p95 | exp008_depth_models n | exp008_depth_models rot deg med / p95 | exp008_depth_models trans mm med / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 2.0 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

