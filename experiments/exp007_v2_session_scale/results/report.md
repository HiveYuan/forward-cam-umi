# exp007_v2_session_scale: report (variant main)

30 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3 | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |

n [frame pairs]:

- static, E3: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3 | Bsession+Acheck | 2.46 / 10.02 | 5.68 / 24.35 | 8.34 / 35.86 | 11.82 / 46.05 | 11.61 / 24.13 |

n [frame pairs]:

- E3 oracle (tiles): 0.08 s: 2371, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E3 Bsession+Acheck: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 14.2 | 43 | 100% |
| E3 | 0.17% | 12.8 | 47 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | Bsession+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 7.8% | 17.4% | -7.3% | ep09, ep19 |
| E3 | Bsession+Acheck, without flagged | 28/30 | 26 | 7.8% | 16.7% | -7.3% |  |
| E3 | Bsession+Acheck, method Bsession (primary) | 30/30 | 28 | 7.8% | 17.4% | -7.3% |  |
| E3 | Bsession+Acheck, method A (check) | 11/30 | 11 | 6.8% | 19.0% | -4.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3 | Bsession+Acheck | 989 | 1.2 / 3.5 | 1.6 / 5.7 | 2.3 / 7.7 | 3.3 / 11.3 | 4.5 / 15.0 | 6.2 / 18.1 | 6.6 / 22.3 | 7.6 / 17.2 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3 | anchors | 978 | 979 | 979 | 979 |
| E3 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3 | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3 | position [mm], Bsession+Acheck, mean / median | 4.9 / 3.3 | 7.0 / 4.6 | 8.6 / 5.9 | 10.1 / 6.6 |
| E3 | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3, H=100: 49 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 40 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles, dt 0.5 s | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles, dt 2.0 s | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes between the ends | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

## Error decomposition, run E3: SLAM or tile head rotation x configured or oracle scale

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3 rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bsession+Acheck) or the per-segment tile oracle (`errdecomp_E3.json`). (1) SLAM rot + Bsession+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bsession+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bsession+Acheck s 4.5, (2) SLAM rot + oracle s 3.9, (3) tile rot + Bsession+Acheck s 8.2, (4) tile rot + oracle s 7.3 mm; chunk H=30 position mean: (1) SLAM rot + Bsession+Acheck s 7.0, (2) SLAM rot + oracle s 6.4, (3) tile rot + Bsession+Acheck s 12.6, (4) tile rot + oracle s 12.1 mm.

### Error decomposition, E3: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 989 | 1.2 / 3.5 | 1.6 / 5.7 | 2.3 / 7.7 | 3.3 / 11.3 | 4.5 / 15.0 | 6.2 / 18.1 | 6.6 / 22.3 | 7.6 / 17.2 |
| (2) SLAM rot + oracle s | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| (3) tile rot + Bsession+Acheck s | 989 | 2.2 / 6.3 | 3.1 / 9.2 | 4.2 / 12.4 | 5.7 / 17.6 | 8.2 / 25.4 | 11.8 / 30.1 | 9.8 / 33.7 | 11.5 / 22.7 |
| (4) tile rot + oracle s | 989 | 2.1 / 6.3 | 3.1 / 9.1 | 4.1 / 12.2 | 5.5 / 17.3 | 7.3 / 25.0 | 9.6 / 29.9 | 9.3 / 33.7 | 10.2 / 14.0 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

### Error decomposition, E3: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| (2) SLAM rot + oracle s | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| (3) tile rot + Bsession+Acheck s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

### Error decomposition, E3: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | anchors | 978 | 979 | 979 | 979 |
| (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 4.9 / 3.3 | 7.0 / 4.6 | 8.6 / 5.9 | 10.1 / 6.6 |
| (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| (2) SLAM rot + oracle s | anchors | 978 | 979 | 979 | 979 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| (3) tile rot + Bsession+Acheck s | anchors | 978 | 979 | 979 | 979 |
| (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 8.9 / 6.0 | 12.6 / 8.6 | 15.4 / 10.3 | 18.1 / 10.6 |
| (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.01 / 0.00 |
| (4) tile rot + oracle s | anchors | 978 | 979 | 979 | 979 |
| (4) tile rot + oracle s | position [mm], mean / median | 8.7 / 5.9 | 12.1 / 8.0 | 14.8 / 9.2 | 17.5 / 9.5 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.01 / 0.00 |

### Error decomposition, E3: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 756, 10-30 155, 30+ 0, unknown 78; oracle scale: 0-10 756, 10-30 155, 30+ 0, unknown 78; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | 756 | 1.0 / 3.0 | 1.4 / 4.2 | 1.9 / 5.7 | 2.6 / 7.4 | 3.7 / 11.1 | 5.6 / 15.9 | 6.6 / 22.7 | 6.2 / 17.3 |
| 0-10 | (2) SLAM rot + oracle s | 756 | 1.0 / 2.9 | 1.4 / 4.2 | 1.8 / 5.6 | 2.4 / 7.1 | 3.3 / 10.5 | 4.9 / 12.6 | 5.9 / 16.4 | 5.6 / 9.8 |
| 0-10 | (3) tile rot + Bsession+Acheck s | 756 | 1.9 / 5.8 | 2.7 / 7.8 | 3.4 / 10.8 | 4.9 / 14.6 | 6.7 / 20.9 | 9.9 / 27.6 | 9.9 / 33.9 | 11.4 / 22.8 |
| 0-10 | (4) tile rot + oracle s | 756 | 1.9 / 5.7 | 2.7 / 7.8 | 3.4 / 10.9 | 4.7 / 14.6 | 6.4 / 20.2 | 9.0 / 26.0 | 9.4 / 34.5 | 10.4 / 14.0 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | 155 | 2.1 / 5.5 | 3.4 / 9.3 | 5.3 / 13.3 | 7.9 / 16.5 | 12.0 / 44.8 | 13.3 / 96.1 | - | - |
| 10-30 | (2) SLAM rot + oracle s | 155 | 2.1 / 5.4 | 3.5 / 9.3 | 5.4 / 12.2 | 8.3 / 16.8 | 11.2 / 44.8 | 13.8 / 95.9 | - | - |
| 10-30 | (3) tile rot + Bsession+Acheck s | 155 | 3.4 / 8.8 | 5.5 / 15.8 | 8.4 / 20.9 | 12.8 / 38.0 | 18.6 / 103.7 | 21.1 / 212.4 | - | - |
| 10-30 | (4) tile rot + oracle s | 155 | 3.2 / 8.8 | 5.5 / 15.8 | 8.4 / 21.3 | 12.5 / 38.0 | 16.6 / 103.6 | 22.0 / 212.1 | - | - |
| 30+ | (1) SLAM rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | 756 | 0.13 / 0.40 | 0.18 / 0.54 | 0.23 / 0.69 | 0.31 / 1.02 | 0.42 / 1.27 | 0.60 / 1.86 | 0.57 / 2.42 | 0.60 / 1.17 |
| 0-10 | (2) SLAM rot + oracle s | 756 | 0.13 / 0.40 | 0.18 / 0.54 | 0.23 / 0.69 | 0.31 / 1.02 | 0.42 / 1.27 | 0.60 / 1.86 | 0.57 / 2.42 | 0.60 / 1.17 |
| 0-10 | (3) tile rot + Bsession+Acheck s | 756 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 756 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | 155 | 0.20 / 0.64 | 0.32 / 1.12 | 0.49 / 1.81 | 0.77 / 2.64 | 1.05 / 6.55 | 1.39 / 13.05 | - | - |
| 10-30 | (2) SLAM rot + oracle s | 155 | 0.20 / 0.64 | 0.32 / 1.12 | 0.49 / 1.81 | 0.77 / 2.64 | 1.05 / 6.55 | 1.39 / 13.05 | - | - |
| 10-30 | (3) tile rot + Bsession+Acheck s | 155 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - | - |
| 10-30 | (4) tile rot + oracle s | 155 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - | - |
| 30+ | (1) SLAM rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 3.9 / 2.7 | 5.5 / 4.1 | 7.4 / 5.3 | 9.3 / 6.1 |
| 0-10 | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.47 / 0.34 | 0.64 / 0.47 | 0.83 / 0.56 | 1.05 / 0.57 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 3.7 / 2.6 | 5.1 / 3.7 | 6.6 / 4.7 | 8.4 / 5.1 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.47 / 0.34 | 0.64 / 0.47 | 0.83 / 0.56 | 1.05 / 0.57 |
| 0-10 | (3) tile rot + Bsession+Acheck s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 7.4 / 5.0 | 10.3 / 7.5 | 13.5 / 9.8 | 17.1 / 10.1 |
| 0-10 | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 7.2 / 5.0 | 9.9 / 7.2 | 13.0 / 8.9 | 16.5 / 9.3 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 10.4 / 7.7 | 15.2 / 10.2 | 16.0 / 10.2 | 16.0 / 10.2 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 1.11 / 0.71 | 1.64 / 0.81 | 1.75 / 0.84 | 1.75 / 0.84 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 10.0 / 7.2 | 14.4 / 9.3 | 15.2 / 9.6 | 15.2 / 9.6 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 1.11 / 0.71 | 1.64 / 0.81 | 1.75 / 0.84 | 1.75 / 0.84 |
| 10-30 | (3) tile rot + Bsession+Acheck s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 17.6 / 11.1 | 26.4 / 13.9 | 28.1 / 13.9 | 28.1 / 13.9 |
| 10-30 | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 17.3 / 10.7 | 26.0 / 13.0 | 27.7 / 13.2 | 27.7 / 13.2 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 |
| 30+ | (1) SLAM rot + Bsession+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (2) SLAM rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (4) tile rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | rotation [deg], mean / median | - | - | - | - |

### Error decomposition, E3: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.3 / 4.3 | 1.9 / 5.8 | 2.5 / 7.7 | 3.4 / 11.1 | 4.4 / 15.5 | 6.0 / 20.9 | 5.0 / 24.0 | 5.6 / 8.0 |
| translation part dt [mm], Bsession+Acheck s, median / p90 | 2.2 / 6.2 | 3.1 / 9.2 | 4.2 / 12.3 | 5.7 / 17.6 | 8.2 / 25.3 | 11.8 / 30.1 | 9.8 / 33.7 | 11.5 / 22.7 |
| translation part dt [mm], oracle s, median / p90 | 2.1 / 6.2 | 3.1 / 9.1 | 4.1 / 12.3 | 5.5 / 17.3 | 7.3 / 24.9 | 9.6 / 29.9 | 9.3 / 33.7 | 10.2 / 14.0 |
| cos(dR b, dt), Bsession+Acheck s, median | -0.91 | -0.90 | -0.90 | -0.92 | -0.93 | -0.88 | -0.84 | -0.85 |
| cos(dR b, dt), oracle s, median | -0.91 | -0.91 | -0.90 | -0.92 | -0.94 | -0.92 | -0.90 | -0.85 |

Checks: (1) SLAM rot + Bsession+Acheck s vs `labels_E3@Bsession+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 48735 pairs): max |position difference| 4.4e-13 mm, max |R difference| 7.2e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 48735 pairs): max |position difference| 3.9e-13 mm, max |R difference| 7.2e-16.

## Comparison with other experiments

- exp005_session_scale: `exp005_session_scale/results/metrics.json`
- exp006_sam3_v2: `exp006_sam3_v2/results/metrics.json`
- runs only in exp005_session_scale (not shown): E2

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp005_session_scale n | exp005_session_scale median | exp005_session_scale p95 | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| static | 0.08 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | 2380 | 0.24 | 1.26 | 2380 | 0.24 | 1.26 |
| E1 | 0.5 | - | - | - | 1931 | 0.60 | 4.46 | 1931 | 0.60 | 4.46 |
| E1 | 1.0 | - | - | - | 1612 | 0.85 | 7.88 | 1612 | 0.85 | 7.88 |
| E1 | 2.0 | - | - | - | 1248 | 1.11 | 14.80 | 1248 | 1.11 | 14.80 |
| E1 | 6.67 | - | - | - | 88 | 0.98 | 8.62 | 88 | 0.98 | 8.62 |
| E3 | 0.08 | 2380 | 0.16 | 0.64 | 2380 | 0.16 | 0.63 | 2380 | 0.16 | 0.64 |
| E3 | 0.5 | 1931 | 0.36 | 1.49 | 1931 | 0.36 | 1.52 | 1931 | 0.36 | 1.49 |
| E3 | 1.0 | 1612 | 0.52 | 2.25 | 1612 | 0.52 | 2.17 | 1612 | 0.52 | 2.25 |
| E3 | 2.0 | 1248 | 0.65 | 2.60 | 1248 | 0.64 | 2.67 | 1248 | 0.65 | 2.60 |
| E3 | 6.67 | 88 | 0.58 | 1.26 | 88 | 0.73 | 1.21 | 88 | 0.58 | 1.26 |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp005_session_scale n | exp005_session_scale median | exp005_session_scale p95 | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | 2371 | 3.63 | 17.91 | 2371 | 3.63 | 17.91 |
| E1 | oracle | 0.5 | - | - | - | 1931 | 9.92 | 65.90 | 1931 | 9.92 | 65.90 |
| E1 | oracle | 1.0 | - | - | - | 1612 | 13.93 | 117.98 | 1612 | 13.93 | 117.98 |
| E1 | oracle | 2.0 | - | - | - | 1248 | 17.19 | 209.69 | 1248 | 17.19 | 209.69 |
| E1 | oracle | 6.67 | - | - | - | 88 | 12.66 | 158.28 | 88 | 12.66 | 158.28 |
| E3 | oracle | 0.08 | 2371 | 2.49 | 10.13 | 2371 | 2.47 | 9.73 | 2371 | 2.49 | 10.13 |
| E3 | oracle | 0.5 | 1931 | 5.47 | 24.24 | 1931 | 5.52 | 25.17 | 1931 | 5.47 | 24.24 |
| E3 | oracle | 1.0 | 1612 | 7.46 | 36.49 | 1612 | 8.19 | 34.71 | 1612 | 7.46 | 36.49 |
| E3 | oracle | 2.0 | 1248 | 9.87 | 46.80 | 1248 | 9.98 | 43.87 | 1248 | 9.87 | 46.80 |
| E3 | oracle | 6.67 | 88 | 10.15 | 16.47 | 88 | 10.88 | 17.42 | 88 | 10.15 | 16.47 |
| E3 | configured | 0.08 | 2380 | 2.46 | 10.02 | 2380 | 2.48 | 9.64 | 2380 | 2.45 | 9.83 |
| E3 | configured | 0.5 | 1931 | 5.68 | 24.35 | 1931 | 5.78 | 25.15 | 1931 | 5.80 | 25.13 |
| E3 | configured | 1.0 | 1612 | 8.34 | 35.86 | 1612 | 8.72 | 34.56 | 1612 | 8.90 | 40.37 |
| E3 | configured | 2.0 | 1248 | 11.82 | 46.05 | 1248 | 11.87 | 44.16 | 1248 | 12.05 | 53.74 |
| E3 | configured | 6.67 | 88 | 11.61 | 24.13 | 88 | 12.93 | 25.45 | 88 | 9.90 | 17.67 |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp007_v2_session_scale | exp005_session_scale | exp006_sam3_v2 |
|---|---|---|---|---|
| E1 | track fail | - | 1.93% | 1.93% |
| E1 | keyframes / segment | 14.2 | 14.2 | 14.2 |
| E1 | runtime s / segment | 43 | 43 | 43 |
| E1 | valid pixels | 100% | 100% | 100% |
| E3 | track fail | 0.17% | 0.21% | 0.17% |
| E3 | keyframes / segment | 12.8 | 13.0 | 12.8 |
| E3 | runtime s / segment | 47 | 48 | 47 |
| E3 | valid pixels | 86% | 85% | 86% |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp007_v2_session_scale | exp005_session_scale | exp006_sam3_v2 |
|---|---|---|---|---|
| E3 | scale label | Bsession+Acheck | Bsession+Acheck | B+Acheck |
| E3 | segments with a scale | 30/30 | 30/30 | 30/30 |
| E3 | compared (tile GT) | 28 | 28 | 28 |
| E3 | abs err median | 7.8% | 6.3% | 6.6% |
| E3 | abs err p90 | 17.4% | 17.7% | 21.7% |
| E3 | bias (median) | -7.3% | -5.9% | -5.2% |
| E3 | flagged | ep09, ep19 | ep19, ep24 | ep01, ep12, ep15, ep20 |
| E3 | without flagged: abs err median / p90 | 7.8% / 16.7% | 6.1% / 17.4% | 5.2% / 16.6% |
| E3 | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 7.8% / 17.4% / -7.3% | 30/30, n 28: 6.3% / 17.7% / -5.9% | - |
| E3 | method A: segments ok, n: abs err median / p90 / bias | 11/30, n 11: 6.8% / 19.0% / -4.6% | 14/30, n 14: 4.4% / 16.5% / -1.6% | 11/30, n 11: 6.8% / 19.0% / -4.6% |
| E3 | method B: segments ok, n: abs err median / p90 / bias | - | - | 30/30, n 28: 6.6% / 21.7% / -5.2% |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp005_session_scale n | exp005_session_scale median | exp005_session_scale p90 | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle | anchors | 989 |  |  | 989 |  |  | 989 |  |  |
| E3 | oracle | 0.07 s | 976 | 1.2 | 3.6 | 976 | 1.2 | 3.6 | 976 | 1.2 | 3.6 |
| E3 | oracle | 0.13 s | 963 | 1.6 | 5.7 | 963 | 1.7 | 5.7 | 963 | 1.6 | 5.7 |
| E3 | oracle | 0.27 s | 937 | 2.3 | 7.3 | 937 | 2.3 | 7.8 | 937 | 2.3 | 7.3 |
| E3 | oracle | 0.53 s | 890 | 3.1 | 11.2 | 890 | 3.2 | 11.3 | 890 | 3.1 | 11.2 |
| E3 | oracle | 1.00 s | 814 | 3.9 | 13.9 | 814 | 4.3 | 14.6 | 814 | 3.9 | 13.9 |
| E3 | oracle | 2.00 s | 676 | 5.2 | 14.8 | 676 | 5.5 | 14.7 | 676 | 5.2 | 14.8 |
| E3 | oracle | 4.00 s | 398 | 5.9 | 15.8 | 398 | 5.9 | 17.0 | 398 | 5.9 | 15.8 |
| E3 | oracle | 6.67 s | 55 | 5.6 | 9.7 | 55 | 5.8 | 8.7 | 55 | 5.6 | 9.7 |
| E3 | configured | anchors | 989 |  |  | 989 |  |  | 989 |  |  |
| E3 | configured | 0.07 s | 976 | 1.2 | 3.5 | 976 | 1.2 | 3.6 | 976 | 1.2 | 3.6 |
| E3 | configured | 0.13 s | 963 | 1.6 | 5.7 | 963 | 1.7 | 5.6 | 963 | 1.7 | 6.0 |
| E3 | configured | 0.27 s | 937 | 2.3 | 7.7 | 937 | 2.4 | 7.9 | 937 | 2.5 | 8.7 |
| E3 | configured | 0.53 s | 890 | 3.3 | 11.3 | 890 | 3.4 | 11.4 | 890 | 3.8 | 13.3 |
| E3 | configured | 1.00 s | 814 | 4.5 | 15.0 | 814 | 4.8 | 15.6 | 814 | 5.7 | 18.7 |
| E3 | configured | 2.00 s | 676 | 6.2 | 18.1 | 676 | 6.4 | 18.3 | 676 | 7.7 | 26.4 |
| E3 | configured | 4.00 s | 398 | 6.6 | 22.3 | 398 | 6.3 | 21.8 | 398 | 7.3 | 36.7 |
| E3 | configured | 6.67 s | 55 | 7.6 | 17.2 | 55 | 8.4 | 18.6 | 55 | 6.1 | 13.4 |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp005_session_scale n | exp005_session_scale median | exp005_session_scale p90 | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | anchors | 989 |  |  | 989 |  |  | 989 |  |  |
| E3 | every scale | 0.07 s | 976 | 0.14 | 0.44 | 976 | 0.14 | 0.44 | 976 | 0.14 | 0.44 |
| E3 | every scale | 0.13 s | 963 | 0.20 | 0.61 | 963 | 0.20 | 0.60 | 963 | 0.20 | 0.61 |
| E3 | every scale | 0.27 s | 937 | 0.27 | 0.83 | 937 | 0.27 | 0.86 | 937 | 0.27 | 0.83 |
| E3 | every scale | 0.53 s | 890 | 0.36 | 1.18 | 890 | 0.36 | 1.23 | 890 | 0.36 | 1.18 |
| E3 | every scale | 1.00 s | 814 | 0.50 | 1.59 | 814 | 0.52 | 1.62 | 814 | 0.50 | 1.59 |
| E3 | every scale | 2.00 s | 676 | 0.65 | 1.99 | 676 | 0.62 | 2.06 | 676 | 0.65 | 1.99 |
| E3 | every scale | 4.00 s | 398 | 0.56 | 2.41 | 398 | 0.57 | 1.91 | 398 | 0.56 | 2.41 |
| E3 | every scale | 6.67 s | 55 | 0.57 | 1.16 | 55 | 0.71 | 1.12 | 55 | 0.57 | 1.16 |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp007_v2_session_scale | exp005_session_scale | exp006_sam3_v2 |
|---|---|---|---|---|---|---|
| E3 | every scale | anchors | 15 (1.00 s) | 978 | 978 | 978 |
| E3 | every scale | anchors | 30 (2.00 s) | 979 | 979 | 979 |
| E3 | every scale | anchors | 50 (3.33 s) | 979 | 979 | 979 |
| E3 | every scale | anchors | 100 (6.67 s) | 979 | 979 | 979 |
| E3 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | 15 | 15 |
| E3 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | 30 | 30 |
| E3 | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | 46 | 46 |
| E3 | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | 49 | 49 |
| E3 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | 4.8 / 3.3 | 4.7 / 3.2 |
| E3 | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | 6.6 / 4.4 | 6.4 / 4.2 |
| E3 | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | 7.8 / 5.2 | 7.7 / 4.9 |
| E3 | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | 8.9 / 5.4 | 9.1 / 5.5 |
| E3 | configured | pos mm, mean / median | 15 (1.00 s) | 4.9 / 3.3 | 5.0 / 3.4 | 5.5 / 3.8 |
| E3 | configured | pos mm, mean / median | 30 (2.00 s) | 7.0 / 4.6 | 7.1 / 4.8 | 8.0 / 5.4 |
| E3 | configured | pos mm, mean / median | 50 (3.33 s) | 8.6 / 5.9 | 8.5 / 5.9 | 9.9 / 6.4 |
| E3 | configured | pos mm, mean / median | 100 (6.67 s) | 10.1 / 6.6 | 9.6 / 6.2 | 11.7 / 7.1 |
| E3 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | 0.56 / 0.40 | 0.57 / 0.39 |
| E3 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | 0.77 / 0.52 | 0.78 / 0.51 |
| E3 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | 0.91 / 0.59 | 0.95 / 0.58 |
| E3 | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | 1.03 / 0.60 | 1.11 / 0.59 |

### Ground-truth noise floor

| pairs | dt [s] | exp007_v2_session_scale n | exp007_v2_session_scale rot deg med / p95 | exp007_v2_session_scale trans mm med / p95 | exp005_session_scale n | exp005_session_scale rot deg med / p95 | exp005_session_scale trans mm med / p95 | exp006_sam3_v2 n | exp006_sam3_v2 rot deg med / p95 | exp006_sam3_v2 trans mm med / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 2.0 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

### Mask comparison (per frame, pooled over every frame of every segment)

Rows: the mask comparisons of every experiment (<candidate>_vs_<reference>); details in each experiment's report.md and masks_*.md.

| comparison | quantity | exp007_v2_session_scale | exp005_session_scale | exp006_sam3_v2 |
|---|---|---|---|---|
| motion_vs_sam2 | reference / candidate | - | - | sam2 / motion |
| motion_vs_sam2 | dilate [px] | - | - | 8 |
| motion_vs_sam2 | segments / frames | - | - | 30 / 8972 |
| motion_vs_sam2 | IoU median / p10 | - | - | 0.942 / 0.875 |
| motion_vs_sam2 | recall median / p10 | - | - | 0.969 / 0.933 |
| motion_vs_sam2 | precision median / p10 | - | - | 0.979 / 0.923 |
| motion_vs_sam2 | extra area (candidate only) median / p90 [% of frame] | - | - | 0.14% / 0.67% |
| motion_vs_sam2 | missed area (reference only) median / p90 [% of frame] | - | - | 0.21% / 0.44% |
| motion_vs_sam2 | DROID-cell IoU median / p10 | - | - | 0.979 / 0.888 |
| motion_vs_sam2 | mean area reference / candidate [% of frame] | - | - | 7.20% / 7.19% |
| motion_vs_sam2 | part area: rig [% of frame] | - | - | 2.72% |
| motion_vs_sam2 | part area: hand_track [% of frame] | - | - | 3.39% |
| motion_vs_sam2 | part area: held [% of frame] | - | - | 0.14% |
| motion_vs_sam2 | part area: hand [% of frame] | - | - | 2.49% |
| motion_vs_sam2 | part area: arm [% of frame] | - | - | 3.47% |
| motion_vs_sam2 | part area: cable [% of frame] | - | - | 0.63% |
| motion_vs_sam2 | segments with IoU median < 0.8 | - | - | 0 |
| motion_vs_sam2 | worst segments (IoU median) | - | - | ep20 0.888, ep12 0.902, ep00 0.905, ep09 0.912, ep21 0.926 |

