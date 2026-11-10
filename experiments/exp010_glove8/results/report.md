# exp010_glove8: report (variant main)

4 segments. Runs: E1, E3_da2, E3_da3m (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.59 / 1.65 | 3.30 / 9.34 | 5.89 / 13.22 | 8.36 / 25.32 | - / - |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3_da2 | 0.17 / 0.53 | 0.39 / 1.02 | 0.44 / 1.18 | 0.56 / 1.21 | - / - |
| E3_da3m | 0.17 / 0.53 | 0.39 / 1.02 | 0.44 / 1.18 | 0.56 / 1.21 | - / - |

n [frame pairs]:

- static, E3_da2, E3_da3m: 0.08 s: 431, 0.5 s: 334, 1.0 s: 283, 2.0 s: 222, 6.67 s: 0
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3_da2 | oracle (tiles) | 2.79 / 9.30 | 7.05 / 22.23 | 7.88 / 30.19 | 8.69 / 59.91 | - / - |
| E3_da2 | Bsession+Acheck | 2.74 / 9.21 | 6.99 / 19.98 | 7.99 / 25.08 | 11.36 / 34.37 | - / - |
| E3_da3m | oracle (tiles) | 2.79 / 9.30 | 7.05 / 22.23 | 7.88 / 30.19 | 8.69 / 59.91 | - / - |
| E3_da3m | Bnet+Acheck | 2.76 / 9.42 | 6.44 / 18.42 | 6.75 / 23.40 | 8.56 / 21.76 | - / - |

n [frame pairs]: 0.08 s: 431, 0.5 s: 334, 1.0 s: 283, 2.0 s: 222, 6.67 s: 0

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 20.5 | 91 | 100% |
| E3_da2 | 0.00% | 15.0 | 91 | 84% |
| E3_da3m | 0.00% | 15.0 | 91 | 84% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3_da2 | Bsession+Acheck (flag \|check/primary - 1\| > 10%) | 4/4 | 4 | 10.4% | 11.1% | -8.8% | - |
| E3_da2 | Bsession+Acheck, method Bsession (primary) | 4/4 | 4 | 10.4% | 11.1% | -8.8% |  |
| E3_da2 | Bsession+Acheck, method A (check) | 0/4 | 0 | - | - | - |  |
| E3_da3m | Bnet+Acheck (flag \|check/primary - 1\| > 10%) | 4/4 | 4 | 0.8% | 14.4% | 0.2% | - |
| E3_da3m | Bnet+Acheck, method Bnet (primary) | 4/4 | 4 | 0.8% | 14.4% | 0.2% |  |
| E3_da3m | Bnet+Acheck, method A (check) | 0/4 | 0 | - | - | - |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | oracle (tiles) | 249 | 1.4 / 4.0 | 2.1 / 6.1 | 3.1 / 7.7 | 4.1 / 9.5 | 5.0 / 19.6 | 5.7 / 37.6 | 9.4 / 31.0 |
| E3_da2 | Bsession+Acheck | 249 | 1.4 / 3.7 | 2.1 / 5.6 | 2.9 / 7.2 | 4.0 / 8.3 | 5.1 / 11.6 | 7.0 / 18.8 | 11.5 / 18.1 |
| E3_da3m | oracle (tiles) | 249 | 1.4 / 4.0 | 2.1 / 6.1 | 3.1 / 7.7 | 4.1 / 9.5 | 5.0 / 19.6 | 5.7 / 37.6 | 9.4 / 31.0 |
| E3_da3m | Bnet+Acheck | 249 | 1.3 / 3.7 | 2.1 / 6.0 | 2.8 / 7.1 | 3.7 / 7.5 | 4.6 / 10.2 | 4.6 / 11.4 | 6.0 / 16.0 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | every scale | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| E3_da3m | every scale | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3_da2 | anchors | 246 | 246 | 246 | 246 |
| E3_da2 | counted steps per anchor, median | 15 | 26.5 | 35.5 | 41.5 |
| E3_da2 | position [mm], oracle (tiles), mean / median | 5.3 / 4.1 | 7.8 / 5.2 | 9.7 / 5.2 | 9.8 / 5.3 |
| E3_da2 | position [mm], Bsession+Acheck, mean / median | 4.7 / 4.0 | 6.1 / 5.0 | 7.2 / 5.8 | 7.6 / 5.9 |
| E3_da2 | rotation [deg], every scale, mean / median | 0.46 / 0.39 | 0.52 / 0.46 | 0.57 / 0.53 | 0.58 / 0.55 |
| E3_da3m | anchors | 246 | 246 | 246 | 246 |
| E3_da3m | counted steps per anchor, median | 15 | 26.5 | 35.5 | 41.5 |
| E3_da3m | position [mm], oracle (tiles), mean / median | 5.3 / 4.1 | 7.8 / 5.2 | 9.7 / 5.2 | 9.8 / 5.3 |
| E3_da3m | position [mm], Bnet+Acheck, mean / median | 4.4 / 3.6 | 5.2 / 4.2 | 5.5 / 4.3 | 5.9 / 5.1 |
| E3_da3m | rotation [deg], every scale, mean / median | 0.46 / 0.39 | 0.52 / 0.46 | 0.57 / 0.53 | 0.58 / 0.55 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3_da2, H=100: 41.5 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 9 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 21 | 0.10 / 0.18 | 1.6 / 4.1 |
| tile set changes between the ends | 27 | 0.44 / 1.12 | 6.7 / 20.0 |

## Error decomposition, run E3_da2: SLAM or tile head rotation x configured or oracle scale

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3_da2 rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bsession+Acheck) or the per-segment tile oracle (`errdecomp_E3_da2.json`). (1) SLAM rot + Bsession+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bsession+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bsession+Acheck s 5.1, (2) SLAM rot + oracle s 5.0, (3) tile rot + Bsession+Acheck s 8.0, (4) tile rot + oracle s 8.2 mm; chunk H=30 position mean: (1) SLAM rot + Bsession+Acheck s 6.1, (2) SLAM rot + oracle s 7.8, (3) tile rot + Bsession+Acheck s 9.4, (4) tile rot + oracle s 10.8 mm.

### Error decomposition, E3_da2: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 249 | 1.4 / 3.7 | 2.1 / 5.6 | 2.9 / 7.2 | 4.0 / 8.3 | 5.1 / 11.6 | 7.0 / 18.8 | 11.5 / 18.1 |
| (2) SLAM rot + oracle s | 249 | 1.4 / 4.0 | 2.1 / 6.1 | 3.1 / 7.7 | 4.1 / 9.5 | 5.0 / 19.6 | 5.7 / 37.6 | 9.4 / 31.0 |
| (3) tile rot + Bsession+Acheck s | 249 | 2.4 / 5.8 | 3.8 / 8.9 | 5.2 / 12.4 | 6.9 / 14.8 | 8.0 / 20.1 | 11.0 / 26.5 | 15.7 / 25.1 |
| (4) tile rot + oracle s | 249 | 2.4 / 5.6 | 3.8 / 9.1 | 5.4 / 12.9 | 7.1 / 16.1 | 8.2 / 25.2 | 8.8 / 41.8 | 12.9 / 35.9 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

### Error decomposition, E3_da2: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| (2) SLAM rot + oracle s | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| (3) tile rot + Bsession+Acheck s | 249 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 249 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

### Error decomposition, E3_da2: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | anchors | 246 | 246 | 246 | 246 |
| (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 4.7 / 4.0 | 6.1 / 5.0 | 7.2 / 5.8 | 7.6 / 5.9 |
| (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.46 / 0.39 | 0.52 / 0.46 | 0.57 / 0.53 | 0.58 / 0.55 |
| (2) SLAM rot + oracle s | anchors | 246 | 246 | 246 | 246 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 5.3 / 4.1 | 7.8 / 5.2 | 9.7 / 5.2 | 9.8 / 5.3 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.46 / 0.39 | 0.52 / 0.46 | 0.57 / 0.53 | 0.58 / 0.55 |
| (3) tile rot + Bsession+Acheck s | anchors | 246 | 246 | 246 | 246 |
| (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 7.6 / 6.5 | 9.4 / 8.2 | 10.9 / 9.0 | 11.3 / 9.7 |
| (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.09 / 0.00 | 0.08 / 0.00 | 0.07 / 0.00 | 0.07 / 0.00 |
| (4) tile rot + oracle s | anchors | 246 | 246 | 246 | 246 |
| (4) tile rot + oracle s | position [mm], mean / median | 8.1 / 6.9 | 10.8 / 8.5 | 12.9 / 8.8 | 13.2 / 8.8 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.09 / 0.00 | 0.08 / 0.00 | 0.07 / 0.00 | 0.07 / 0.00 |

### Error decomposition, E3_da2: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 170, 10-30 48, 30+ 0, unknown 31; oracle scale: 0-10 170, 10-30 48, 30+ 0, unknown 31; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | 170 | 1.3 / 3.0 | 1.8 / 4.6 | 2.7 / 5.1 | 3.8 / 7.0 | 4.8 / 7.4 | 6.9 / 17.3 | 11.2 / 18.3 |
| 0-10 | (2) SLAM rot + oracle s | 170 | 1.3 / 2.9 | 1.9 / 4.6 | 2.9 / 5.5 | 3.7 / 8.4 | 4.6 / 9.7 | 5.0 / 35.3 | 8.2 / 22.8 |
| 0-10 | (3) tile rot + Bsession+Acheck s | 170 | 2.3 / 4.9 | 3.4 / 7.9 | 4.6 / 9.4 | 6.1 / 12.3 | 6.9 / 14.5 | 10.1 / 24.2 | 13.1 / 23.0 |
| 0-10 | (4) tile rot + oracle s | 170 | 2.2 / 5.0 | 3.4 / 7.9 | 4.7 / 9.1 | 6.0 / 12.7 | 6.5 / 15.2 | 7.5 / 38.7 | 11.6 / 29.2 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | 48 | 1.5 / 5.9 | 2.5 / 10.4 | 3.9 / 14.1 | 4.5 / 20.3 | 8.9 / 26.3 | 6.0 / 8.1 | 10.4 / 12.7 |
| 10-30 | (2) SLAM rot + oracle s | 48 | 1.7 / 5.2 | 2.8 / 9.7 | 5.1 / 15.6 | 5.6 / 26.1 | 7.4 / 32.2 | 5.0 / 13.1 | 6.4 / 13.0 |
| 10-30 | (3) tile rot + Bsession+Acheck s | 48 | 3.2 / 11.7 | 5.7 / 14.9 | 9.0 / 17.0 | 11.6 / 22.4 | 15.8 / 26.8 | 8.0 / 20.2 | 21.0 / 28.4 |
| 10-30 | (4) tile rot + oracle s | 48 | 3.3 / 12.5 | 5.7 / 16.5 | 10.5 / 18.9 | 11.8 / 26.7 | 14.4 / 33.5 | 10.3 / 15.8 | 12.8 / 17.2 |
| 30+ | (1) SLAM rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | 170 | 0.15 / 0.32 | 0.21 / 0.46 | 0.28 / 0.55 | 0.35 / 0.67 | 0.40 / 0.87 | 0.48 / 1.01 | 0.66 / 1.03 |
| 0-10 | (2) SLAM rot + oracle s | 170 | 0.15 / 0.32 | 0.21 / 0.46 | 0.28 / 0.55 | 0.35 / 0.67 | 0.40 / 0.87 | 0.48 / 1.01 | 0.66 / 1.03 |
| 0-10 | (3) tile rot + Bsession+Acheck s | 170 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 170 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | 48 | 0.18 / 0.83 | 0.33 / 1.02 | 0.49 / 1.16 | 0.59 / 1.18 | 0.80 / 1.22 | 0.66 / 1.12 | 1.09 / 1.49 |
| 10-30 | (2) SLAM rot + oracle s | 48 | 0.18 / 0.83 | 0.33 / 1.02 | 0.49 / 1.16 | 0.59 / 1.18 | 0.80 / 1.22 | 0.66 / 1.12 | 1.09 / 1.49 |
| 10-30 | (3) tile rot + Bsession+Acheck s | 48 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (4) tile rot + oracle s | 48 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 30+ | (1) SLAM rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bsession+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bsession+Acheck s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 3.9 / 3.6 | 5.2 / 4.9 | 6.7 / 5.8 | 7.2 / 5.9 |
| 0-10 | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.38 / 0.34 | 0.47 / 0.44 | 0.53 / 0.50 | 0.55 / 0.53 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 4.1 / 3.6 | 6.1 / 4.8 | 8.6 / 4.9 | 8.8 / 5.0 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.38 / 0.34 | 0.47 / 0.44 | 0.53 / 0.50 | 0.55 / 0.53 |
| 0-10 | (3) tile rot + Bsession+Acheck s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 6.3 / 5.8 | 8.3 / 7.5 | 10.1 / 8.7 | 10.7 / 9.4 |
| 0-10 | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.04 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.04 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 6.4 / 5.9 | 8.9 / 7.6 | 11.7 / 8.2 | 12.0 / 8.3 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.04 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.04 / 0.00 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | position [mm], mean / median | 7.4 / 4.8 | 7.8 / 5.6 | 8.0 / 5.6 | 8.1 / 5.6 |
| 10-30 | (1) SLAM rot + Bsession+Acheck s | rotation [deg], mean / median | 0.65 / 0.57 | 0.68 / 0.58 | 0.70 / 0.58 | 0.71 / 0.59 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 8.6 / 5.2 | 9.3 / 5.7 | 9.4 / 5.9 | 9.5 / 6.0 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.65 / 0.57 | 0.68 / 0.58 | 0.70 / 0.58 | 0.71 / 0.59 |
| 10-30 | (3) tile rot + Bsession+Acheck s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (3) tile rot + Bsession+Acheck s | position [mm], mean / median | 12.3 / 10.5 | 12.7 / 10.6 | 12.9 / 10.6 | 13.2 / 10.6 |
| 10-30 | (3) tile rot + Bsession+Acheck s | rotation [deg], mean / median | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 13.2 / 11.0 | 13.7 / 11.2 | 13.7 / 11.2 | 13.8 / 11.3 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
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

### Error decomposition, E3_da2: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.4 / 3.0 | 2.1 / 4.5 | 2.7 / 6.0 | 3.3 / 7.0 | 4.1 / 9.3 | 4.5 / 11.0 | 6.2 / 10.6 |
| translation part dt [mm], Bsession+Acheck s, median / p90 | 2.4 / 5.8 | 3.8 / 8.7 | 5.2 / 12.3 | 6.9 / 14.8 | 8.0 / 20.7 | 11.0 / 26.6 | 15.7 / 25.0 |
| translation part dt [mm], oracle s, median / p90 | 2.4 / 5.6 | 3.8 / 9.1 | 5.4 / 12.9 | 7.0 / 16.3 | 8.2 / 25.2 | 8.8 / 42.8 | 12.9 / 35.0 |
| cos(dR b, dt), Bsession+Acheck s, median | -0.92 | -0.93 | -0.93 | -0.91 | -0.92 | -0.90 | -0.76 |
| cos(dR b, dt), oracle s, median | -0.92 | -0.93 | -0.93 | -0.91 | -0.86 | -0.85 | -0.79 |

Checks: (1) SLAM rot + Bsession+Acheck s vs `labels_E3_da2@Bsession+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3_da2.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 10222 pairs): max |position difference| 3.3e-13 mm, max |R difference| 6.5e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 10222 pairs): max |position difference| 3.3e-13 mm, max |R difference| 6.5e-16.

## Error decomposition, run E3_da3m: SLAM or tile head rotation x configured or oracle scale

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3_da3m rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bnet+Acheck) or the per-segment tile oracle (`errdecomp_E3_da3m.json`). (1) SLAM rot + Bnet+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bnet+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bnet+Acheck s 4.6, (2) SLAM rot + oracle s 5.0, (3) tile rot + Bnet+Acheck s 7.2, (4) tile rot + oracle s 8.2 mm; chunk H=30 position mean: (1) SLAM rot + Bnet+Acheck s 5.2, (2) SLAM rot + oracle s 7.8, (3) tile rot + Bnet+Acheck s 8.4, (4) tile rot + oracle s 10.8 mm.

### Error decomposition, E3_da3m: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 249 | 1.3 / 3.7 | 2.1 / 6.0 | 2.8 / 7.1 | 3.7 / 7.5 | 4.6 / 10.2 | 4.6 / 11.4 | 6.0 / 16.0 |
| (2) SLAM rot + oracle s | 249 | 1.4 / 4.0 | 2.1 / 6.1 | 3.1 / 7.7 | 4.1 / 9.5 | 5.0 / 19.6 | 5.7 / 37.6 | 9.4 / 31.0 |
| (3) tile rot + Bnet+Acheck s | 249 | 2.5 / 5.8 | 3.6 / 8.7 | 5.1 / 12.0 | 6.2 / 15.0 | 7.2 / 19.3 | 8.7 / 18.2 | 10.5 / 20.5 |
| (4) tile rot + oracle s | 249 | 2.4 / 5.6 | 3.8 / 9.1 | 5.4 / 12.9 | 7.1 / 16.1 | 8.2 / 25.2 | 8.8 / 41.8 | 12.9 / 35.9 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

### Error decomposition, E3_da3m: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| (2) SLAM rot + oracle s | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| (3) tile rot + Bnet+Acheck s | 249 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 249 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

### Error decomposition, E3_da3m: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | anchors | 246 | 246 | 246 | 246 |
| (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 4.4 / 3.6 | 5.2 / 4.2 | 5.5 / 4.3 | 5.9 / 5.1 |
| (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.46 / 0.39 | 0.52 / 0.46 | 0.57 / 0.53 | 0.58 / 0.55 |
| (2) SLAM rot + oracle s | anchors | 246 | 246 | 246 | 246 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 5.3 / 4.1 | 7.8 / 5.2 | 9.7 / 5.2 | 9.8 / 5.3 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.46 / 0.39 | 0.52 / 0.46 | 0.57 / 0.53 | 0.58 / 0.55 |
| (3) tile rot + Bnet+Acheck s | anchors | 246 | 246 | 246 | 246 |
| (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 7.2 / 6.2 | 8.4 / 7.7 | 9.0 / 7.9 | 9.5 / 8.6 |
| (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.09 / 0.00 | 0.08 / 0.00 | 0.07 / 0.00 | 0.07 / 0.00 |
| (4) tile rot + oracle s | anchors | 246 | 246 | 246 | 246 |
| (4) tile rot + oracle s | position [mm], mean / median | 8.1 / 6.9 | 10.8 / 8.5 | 12.9 / 8.8 | 13.2 / 8.8 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.09 / 0.00 | 0.08 / 0.00 | 0.07 / 0.00 | 0.07 / 0.00 |

### Error decomposition, E3_da3m: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 170, 10-30 48, 30+ 0, unknown 31; oracle scale: 0-10 170, 10-30 48, 30+ 0, unknown 31; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 170 | 1.3 / 3.0 | 1.9 / 4.4 | 2.5 / 4.9 | 3.3 / 6.2 | 4.1 / 7.8 | 4.4 / 11.7 | 5.9 / 18.5 |
| 0-10 | (2) SLAM rot + oracle s | 170 | 1.3 / 2.9 | 1.9 / 4.6 | 2.9 / 5.5 | 3.7 / 8.4 | 4.6 / 9.7 | 5.0 / 35.3 | 8.2 / 22.8 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 170 | 2.3 / 5.0 | 3.4 / 7.8 | 4.3 / 9.1 | 5.6 / 11.6 | 5.6 / 14.9 | 7.2 / 18.0 | 10.0 / 20.5 |
| 0-10 | (4) tile rot + oracle s | 170 | 2.2 / 5.0 | 3.4 / 7.9 | 4.7 / 9.1 | 6.0 / 12.7 | 6.5 / 15.2 | 7.5 / 38.7 | 11.6 / 29.2 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 48 | 1.7 / 6.0 | 2.5 / 12.8 | 4.4 / 14.1 | 5.5 / 17.6 | 7.0 / 23.0 | 5.4 / 12.4 | 6.1 / 12.3 |
| 10-30 | (2) SLAM rot + oracle s | 48 | 1.7 / 5.2 | 2.8 / 9.7 | 5.1 / 15.6 | 5.6 / 26.1 | 7.4 / 32.2 | 5.0 / 13.1 | 6.4 / 13.0 |
| 10-30 | (3) tile rot + Bnet+Acheck s | 48 | 3.1 / 12.6 | 5.7 / 16.6 | 10.3 / 18.6 | 11.0 / 18.8 | 14.0 / 24.4 | 10.7 / 15.7 | 12.3 / 17.7 |
| 10-30 | (4) tile rot + oracle s | 48 | 3.3 / 12.5 | 5.7 / 16.5 | 10.5 / 18.9 | 11.8 / 26.7 | 14.4 / 33.5 | 10.3 / 15.8 | 12.8 / 17.2 |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 170 | 0.15 / 0.32 | 0.21 / 0.46 | 0.28 / 0.55 | 0.35 / 0.67 | 0.40 / 0.87 | 0.48 / 1.01 | 0.66 / 1.03 |
| 0-10 | (2) SLAM rot + oracle s | 170 | 0.15 / 0.32 | 0.21 / 0.46 | 0.28 / 0.55 | 0.35 / 0.67 | 0.40 / 0.87 | 0.48 / 1.01 | 0.66 / 1.03 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 170 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 170 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 48 | 0.18 / 0.83 | 0.33 / 1.02 | 0.49 / 1.16 | 0.59 / 1.18 | 0.80 / 1.22 | 0.66 / 1.12 | 1.09 / 1.49 |
| 10-30 | (2) SLAM rot + oracle s | 48 | 0.18 / 0.83 | 0.33 / 1.02 | 0.49 / 1.16 | 0.59 / 1.18 | 0.80 / 1.22 | 0.66 / 1.12 | 1.09 / 1.49 |
| 10-30 | (3) tile rot + Bnet+Acheck s | 48 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (4) tile rot + oracle s | 48 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 3.5 / 3.1 | 4.5 / 4.0 | 4.7 / 4.1 | 5.2 / 4.8 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.38 / 0.34 | 0.47 / 0.44 | 0.53 / 0.50 | 0.55 / 0.53 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 4.1 / 3.6 | 6.1 / 4.8 | 8.6 / 4.9 | 8.8 / 5.0 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.38 / 0.34 | 0.47 / 0.44 | 0.53 / 0.50 | 0.55 / 0.53 |
| 0-10 | (3) tile rot + Bnet+Acheck s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 5.9 / 5.3 | 7.4 / 6.6 | 8.2 / 7.3 | 8.8 / 8.2 |
| 0-10 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.04 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.04 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 170 | 170 | 170 | 170 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 6.4 / 5.9 | 8.9 / 7.6 | 11.7 / 8.2 | 12.0 / 8.3 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.04 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.04 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 7.1 / 5.2 | 7.6 / 5.7 | 7.6 / 5.8 | 7.7 / 5.9 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.65 / 0.57 | 0.68 / 0.58 | 0.70 / 0.58 | 0.71 / 0.59 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 8.6 / 5.2 | 9.3 / 5.7 | 9.4 / 5.9 | 9.5 / 6.0 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.65 / 0.57 | 0.68 / 0.58 | 0.70 / 0.58 | 0.71 / 0.59 |
| 10-30 | (3) tile rot + Bnet+Acheck s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 11.8 / 11.1 | 12.1 / 11.0 | 12.1 / 11.0 | 12.2 / 11.0 |
| 10-30 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 48 | 48 | 48 | 48 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 13.2 / 11.0 | 13.7 / 11.2 | 13.7 / 11.2 | 13.8 / 11.3 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
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

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.4 / 3.0 | 2.1 / 4.5 | 2.7 / 6.0 | 3.3 / 7.0 | 4.1 / 9.3 | 4.5 / 11.0 | 6.2 / 10.6 |
| translation part dt [mm], Bnet+Acheck s, median / p90 | 2.4 / 5.9 | 3.6 / 8.6 | 5.0 / 11.8 | 6.2 / 15.0 | 7.0 / 18.9 | 8.5 / 17.9 | 10.4 / 20.1 |
| translation part dt [mm], oracle s, median / p90 | 2.4 / 5.6 | 3.8 / 9.1 | 5.4 / 12.9 | 7.0 / 16.3 | 8.2 / 25.2 | 8.8 / 42.8 | 12.9 / 35.0 |
| cos(dR b, dt), Bnet+Acheck s, median | -0.92 | -0.93 | -0.95 | -0.93 | -0.88 | -0.91 | -0.89 |
| cos(dR b, dt), oracle s, median | -0.92 | -0.93 | -0.93 | -0.91 | -0.86 | -0.85 | -0.79 |

Checks: (1) SLAM rot + Bnet+Acheck s vs `labels_E3_da3m@Bnet+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3_da3m.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 10222 pairs): max |position difference| 3.3e-13 mm, max |R difference| 6.5e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 10222 pairs): max |position difference| 3.3e-13 mm, max |R difference| 6.5e-16.

## Comparison with other experiments

- exp007_v2_session_scale: `exp007_v2_session_scale/results/metrics.json`
- exp009_net_scale: `exp009_net_scale/results/metrics.json`
- runs only in exp007_v2_session_scale (not shown): E3
- runs only in exp009_net_scale (not shown): E3_uniK, E3_m3d, E3_moge

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp010_glove8 n | exp010_glove8 median | exp010_glove8 p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| static | 0.08 | 431 | 0.59 | 1.65 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 334 | 3.30 | 9.34 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 283 | 5.89 | 13.22 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 222 | 8.36 | 25.32 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 0 | - | - | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - | - | - | - |
| E3_da2 | 0.08 | 431 | 0.17 | 0.53 | - | - | - | - | - | - |
| E3_da2 | 0.5 | 334 | 0.39 | 1.02 | - | - | - | - | - | - |
| E3_da2 | 1.0 | 283 | 0.44 | 1.18 | - | - | - | - | - | - |
| E3_da2 | 2.0 | 222 | 0.56 | 1.21 | - | - | - | - | - | - |
| E3_da2 | 6.67 | 0 | - | - | - | - | - | - | - | - |
| E3_da3m | 0.08 | 431 | 0.17 | 0.53 | - | - | - | 2380 | 0.16 | 0.64 |
| E3_da3m | 0.5 | 334 | 0.39 | 1.02 | - | - | - | 1931 | 0.36 | 1.49 |
| E3_da3m | 1.0 | 283 | 0.44 | 1.18 | - | - | - | 1612 | 0.52 | 2.25 |
| E3_da3m | 2.0 | 222 | 0.56 | 1.21 | - | - | - | 1248 | 0.65 | 2.60 |
| E3_da3m | 6.67 | 0 | - | - | - | - | - | 88 | 0.58 | 1.26 |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp010_glove8 n | exp010_glove8 median | exp010_glove8 p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - | - | - | - |
| E3_da2 | oracle | 0.08 | 431 | 2.79 | 9.30 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.5 | 334 | 7.05 | 22.23 | - | - | - | - | - | - |
| E3_da2 | oracle | 1.0 | 283 | 7.88 | 30.19 | - | - | - | - | - | - |
| E3_da2 | oracle | 2.0 | 222 | 8.69 | 59.91 | - | - | - | - | - | - |
| E3_da2 | oracle | 6.67 | 0 | - | - | - | - | - | - | - | - |
| E3_da2 | configured | 0.08 | 431 | 2.74 | 9.21 | - | - | - | - | - | - |
| E3_da2 | configured | 0.5 | 334 | 6.99 | 19.98 | - | - | - | - | - | - |
| E3_da2 | configured | 1.0 | 283 | 7.99 | 25.08 | - | - | - | - | - | - |
| E3_da2 | configured | 2.0 | 222 | 11.36 | 34.37 | - | - | - | - | - | - |
| E3_da2 | configured | 6.67 | 0 | - | - | - | - | - | - | - | - |
| E3_da3m | oracle | 0.08 | 431 | 2.79 | 9.30 | - | - | - | 2371 | 2.49 | 10.13 |
| E3_da3m | oracle | 0.5 | 334 | 7.05 | 22.23 | - | - | - | 1931 | 5.47 | 24.24 |
| E3_da3m | oracle | 1.0 | 283 | 7.88 | 30.19 | - | - | - | 1612 | 7.46 | 36.49 |
| E3_da3m | oracle | 2.0 | 222 | 8.69 | 59.91 | - | - | - | 1248 | 9.87 | 46.80 |
| E3_da3m | oracle | 6.67 | 0 | - | - | - | - | - | 88 | 10.15 | 16.47 |
| E3_da3m | configured | 0.08 | 431 | 2.76 | 9.42 | - | - | - | 2380 | 2.48 | 10.02 |
| E3_da3m | configured | 0.5 | 334 | 6.44 | 18.42 | - | - | - | 1931 | 5.47 | 24.29 |
| E3_da3m | configured | 1.0 | 283 | 6.75 | 23.40 | - | - | - | 1612 | 7.81 | 36.32 |
| E3_da3m | configured | 2.0 | 222 | 8.56 | 21.76 | - | - | - | 1248 | 10.37 | 45.44 |
| E3_da3m | configured | 6.67 | 0 | - | - | - | - | - | 88 | 9.69 | 17.96 |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp010_glove8 | exp007_v2_session_scale | exp009_net_scale |
|---|---|---|---|---|
| E1 | track fail | - | - | - |
| E1 | keyframes / segment | 20.5 | 14.2 | 14.2 |
| E1 | runtime s / segment | 91 | 43 | 43 |
| E1 | valid pixels | 100% | 100% | 100% |
| E3_da2 | track fail | 0.00% | - | - |
| E3_da2 | keyframes / segment | 15.0 | - | - |
| E3_da2 | runtime s / segment | 91 | - | - |
| E3_da2 | valid pixels | 84% | - | - |
| E3_da3m | track fail | 0.00% | - | 0.17% |
| E3_da3m | keyframes / segment | 15.0 | - | 12.8 |
| E3_da3m | runtime s / segment | 91 | - | 47 |
| E3_da3m | valid pixels | 84% | - | 86% |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp010_glove8 | exp007_v2_session_scale | exp009_net_scale |
|---|---|---|---|---|
| E3_da2 | scale label | Bsession+Acheck | - | - |
| E3_da2 | segments with a scale | 4/4 | - | - |
| E3_da2 | compared (tile GT) | 4 | - | - |
| E3_da2 | abs err median | 10.4% | - | - |
| E3_da2 | abs err p90 | 11.1% | - | - |
| E3_da2 | bias (median) | -8.8% | - | - |
| E3_da2 | flagged | - | - | - |
| E3_da2 | without flagged: abs err median / p90 | 10.4% / 11.1% | - | - |
| E3_da2 | method Bsession: segments ok, n: abs err median / p90 / bias | 4/4, n 4: 10.4% / 11.1% / -8.8% | - | - |
| E3_da2 | method A: segments ok, n: abs err median / p90 / bias | 0/4, n 0: - / - / - | - | - |
| E3_da3m | scale label | Bnet+Acheck | - | Bnet+Acheck |
| E3_da3m | segments with a scale | 4/4 | - | 30/30 |
| E3_da3m | compared (tile GT) | 4 | - | 28 |
| E3_da3m | abs err median | 0.8% | - | 3.1% |
| E3_da3m | abs err p90 | 14.4% | - | 9.4% |
| E3_da3m | bias (median) | 0.2% | - | -0.1% |
| E3_da3m | flagged | - | - | ep01, ep09, ep19, ep20, ep28, ep29 |
| E3_da3m | without flagged: abs err median / p90 | 0.8% / 14.4% | - | 3.0% / 6.9% |
| E3_da3m | method Bnet: segments ok, n: abs err median / p90 / bias | 4/4, n 4: 0.8% / 14.4% / 0.2% | - | 30/30, n 28: 3.1% / 9.4% / -0.1% |
| E3_da3m | method A: segments ok, n: abs err median / p90 / bias | 0/4, n 0: - / - / - | - | 11/30, n 11: 6.8% / 19.0% / -4.6% |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp010_glove8 n | exp010_glove8 median | exp010_glove8 p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | oracle | anchors | 249 |  |  | - | - | - | - | - | - |
| E3_da2 | oracle | 0.07 s | 244 | 1.4 | 4.0 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.13 s | 239 | 2.1 | 6.1 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.27 s | 229 | 3.1 | 7.7 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.53 s | 210 | 4.1 | 9.5 | - | - | - | - | - | - |
| E3_da2 | oracle | 1.00 s | 183 | 5.0 | 19.6 | - | - | - | - | - | - |
| E3_da2 | oracle | 2.00 s | 147 | 5.7 | 37.6 | - | - | - | - | - | - |
| E3_da2 | oracle | 4.00 s | 76 | 9.4 | 31.0 | - | - | - | - | - | - |
| E3_da2 | configured | anchors | 249 |  |  | - | - | - | - | - | - |
| E3_da2 | configured | 0.07 s | 244 | 1.4 | 3.7 | - | - | - | - | - | - |
| E3_da2 | configured | 0.13 s | 239 | 2.1 | 5.6 | - | - | - | - | - | - |
| E3_da2 | configured | 0.27 s | 229 | 2.9 | 7.2 | - | - | - | - | - | - |
| E3_da2 | configured | 0.53 s | 210 | 4.0 | 8.3 | - | - | - | - | - | - |
| E3_da2 | configured | 1.00 s | 183 | 5.1 | 11.6 | - | - | - | - | - | - |
| E3_da2 | configured | 2.00 s | 147 | 7.0 | 18.8 | - | - | - | - | - | - |
| E3_da2 | configured | 4.00 s | 76 | 11.5 | 18.1 | - | - | - | - | - | - |
| E3_da3m | oracle | anchors | 249 |  |  | - | - | - | 989 |  |  |
| E3_da3m | oracle | 0.07 s | 244 | 1.4 | 4.0 | - | - | - | 976 | 1.2 | 3.6 |
| E3_da3m | oracle | 0.13 s | 239 | 2.1 | 6.1 | - | - | - | 963 | 1.6 | 5.7 |
| E3_da3m | oracle | 0.27 s | 229 | 3.1 | 7.7 | - | - | - | 937 | 2.3 | 7.3 |
| E3_da3m | oracle | 0.53 s | 210 | 4.1 | 9.5 | - | - | - | 890 | 3.1 | 11.2 |
| E3_da3m | oracle | 1.00 s | 183 | 5.0 | 19.6 | - | - | - | 814 | 3.9 | 13.9 |
| E3_da3m | oracle | 2.00 s | 147 | 5.7 | 37.6 | - | - | - | 676 | 5.2 | 14.8 |
| E3_da3m | oracle | 4.00 s | 76 | 9.4 | 31.0 | - | - | - | 398 | 5.9 | 15.8 |
| E3_da3m | oracle | 6.67 s | - | - | - | - | - | - | 55 | 5.6 | 9.7 |
| E3_da3m | configured | anchors | 249 |  |  | - | - | - | 989 |  |  |
| E3_da3m | configured | 0.07 s | 244 | 1.3 | 3.7 | - | - | - | 976 | 1.2 | 3.5 |
| E3_da3m | configured | 0.13 s | 239 | 2.1 | 6.0 | - | - | - | 963 | 1.6 | 5.7 |
| E3_da3m | configured | 0.27 s | 229 | 2.8 | 7.1 | - | - | - | 937 | 2.3 | 7.4 |
| E3_da3m | configured | 0.53 s | 210 | 3.7 | 7.5 | - | - | - | 890 | 3.2 | 10.9 |
| E3_da3m | configured | 1.00 s | 183 | 4.6 | 10.2 | - | - | - | 814 | 4.2 | 14.2 |
| E3_da3m | configured | 2.00 s | 147 | 4.6 | 11.4 | - | - | - | 676 | 5.4 | 16.1 |
| E3_da3m | configured | 4.00 s | 76 | 6.0 | 16.0 | - | - | - | 398 | 6.1 | 18.8 |
| E3_da3m | configured | 6.67 s | - | - | - | - | - | - | 55 | 5.4 | 10.4 |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp010_glove8 n | exp010_glove8 median | exp010_glove8 p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 | exp009_net_scale n | exp009_net_scale median | exp009_net_scale p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | every scale | anchors | 249 |  |  | - | - | - | - | - | - |
| E3_da2 | every scale | 0.07 s | 244 | 0.15 | 0.35 | - | - | - | - | - | - |
| E3_da2 | every scale | 0.13 s | 239 | 0.24 | 0.51 | - | - | - | - | - | - |
| E3_da2 | every scale | 0.27 s | 229 | 0.32 | 0.70 | - | - | - | - | - | - |
| E3_da2 | every scale | 0.53 s | 210 | 0.39 | 0.81 | - | - | - | - | - | - |
| E3_da2 | every scale | 1.00 s | 183 | 0.44 | 1.07 | - | - | - | - | - | - |
| E3_da2 | every scale | 2.00 s | 147 | 0.57 | 1.13 | - | - | - | - | - | - |
| E3_da2 | every scale | 4.00 s | 76 | 0.70 | 1.32 | - | - | - | - | - | - |
| E3_da3m | every scale | anchors | 249 |  |  | - | - | - | 989 |  |  |
| E3_da3m | every scale | 0.07 s | 244 | 0.15 | 0.35 | - | - | - | 976 | 0.14 | 0.44 |
| E3_da3m | every scale | 0.13 s | 239 | 0.24 | 0.51 | - | - | - | 963 | 0.20 | 0.61 |
| E3_da3m | every scale | 0.27 s | 229 | 0.32 | 0.70 | - | - | - | 937 | 0.27 | 0.83 |
| E3_da3m | every scale | 0.53 s | 210 | 0.39 | 0.81 | - | - | - | 890 | 0.36 | 1.18 |
| E3_da3m | every scale | 1.00 s | 183 | 0.44 | 1.07 | - | - | - | 814 | 0.50 | 1.59 |
| E3_da3m | every scale | 2.00 s | 147 | 0.57 | 1.13 | - | - | - | 676 | 0.65 | 1.99 |
| E3_da3m | every scale | 4.00 s | 76 | 0.70 | 1.32 | - | - | - | 398 | 0.56 | 2.41 |
| E3_da3m | every scale | 6.67 s | - | - | - | - | - | - | 55 | 0.57 | 1.16 |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp010_glove8 | exp007_v2_session_scale | exp009_net_scale |
|---|---|---|---|---|---|---|
| E3_da2 | every scale | anchors | 15 (1.00 s) | 246 | - | - |
| E3_da2 | every scale | anchors | 30 (2.00 s) | 246 | - | - |
| E3_da2 | every scale | anchors | 50 (3.33 s) | 246 | - | - |
| E3_da2 | every scale | anchors | 100 (6.67 s) | 246 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 30 (2.00 s) | 26.5 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 50 (3.33 s) | 35.5 | - | - |
| E3_da2 | every scale | counted steps per anchor, median | 100 (6.67 s) | 41.5 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 15 (1.00 s) | 5.3 / 4.1 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 30 (2.00 s) | 7.8 / 5.2 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 50 (3.33 s) | 9.7 / 5.2 | - | - |
| E3_da2 | oracle | pos mm, mean / median | 100 (6.67 s) | 9.8 / 5.3 | - | - |
| E3_da2 | configured | pos mm, mean / median | 15 (1.00 s) | 4.7 / 4.0 | - | - |
| E3_da2 | configured | pos mm, mean / median | 30 (2.00 s) | 6.1 / 5.0 | - | - |
| E3_da2 | configured | pos mm, mean / median | 50 (3.33 s) | 7.2 / 5.8 | - | - |
| E3_da2 | configured | pos mm, mean / median | 100 (6.67 s) | 7.6 / 5.9 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.46 / 0.39 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.52 / 0.46 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.57 / 0.53 | - | - |
| E3_da2 | every scale | rot deg, mean / median | 100 (6.67 s) | 0.58 / 0.55 | - | - |
| E3_da3m | every scale | anchors | 15 (1.00 s) | 246 | - | 978 |
| E3_da3m | every scale | anchors | 30 (2.00 s) | 246 | - | 979 |
| E3_da3m | every scale | anchors | 50 (3.33 s) | 246 | - | 979 |
| E3_da3m | every scale | anchors | 100 (6.67 s) | 246 | - | 979 |
| E3_da3m | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | 15 |
| E3_da3m | every scale | counted steps per anchor, median | 30 (2.00 s) | 26.5 | - | 30 |
| E3_da3m | every scale | counted steps per anchor, median | 50 (3.33 s) | 35.5 | - | 46 |
| E3_da3m | every scale | counted steps per anchor, median | 100 (6.67 s) | 41.5 | - | 49 |
| E3_da3m | oracle | pos mm, mean / median | 15 (1.00 s) | 5.3 / 4.1 | - | 4.7 / 3.2 |
| E3_da3m | oracle | pos mm, mean / median | 30 (2.00 s) | 7.8 / 5.2 | - | 6.4 / 4.2 |
| E3_da3m | oracle | pos mm, mean / median | 50 (3.33 s) | 9.7 / 5.2 | - | 7.7 / 4.9 |
| E3_da3m | oracle | pos mm, mean / median | 100 (6.67 s) | 9.8 / 5.3 | - | 9.1 / 5.5 |
| E3_da3m | configured | pos mm, mean / median | 15 (1.00 s) | 4.4 / 3.6 | - | 4.8 / 3.2 |
| E3_da3m | configured | pos mm, mean / median | 30 (2.00 s) | 5.2 / 4.2 | - | 6.6 / 4.3 |
| E3_da3m | configured | pos mm, mean / median | 50 (3.33 s) | 5.5 / 4.3 | - | 8.0 / 5.3 |
| E3_da3m | configured | pos mm, mean / median | 100 (6.67 s) | 5.9 / 5.1 | - | 9.4 / 5.8 |
| E3_da3m | every scale | rot deg, mean / median | 15 (1.00 s) | 0.46 / 0.39 | - | 0.57 / 0.39 |
| E3_da3m | every scale | rot deg, mean / median | 30 (2.00 s) | 0.52 / 0.46 | - | 0.78 / 0.51 |
| E3_da3m | every scale | rot deg, mean / median | 50 (3.33 s) | 0.57 / 0.53 | - | 0.95 / 0.58 |
| E3_da3m | every scale | rot deg, mean / median | 100 (6.67 s) | 0.58 / 0.55 | - | 1.11 / 0.59 |

### Ground-truth noise floor

| pairs | dt [s] | exp010_glove8 n | exp010_glove8 rot deg med / p95 | exp010_glove8 trans mm med / p95 | exp007_v2_session_scale n | exp007_v2_session_scale rot deg med / p95 | exp007_v2_session_scale trans mm med / p95 | exp009_net_scale n | exp009_net_scale rot deg med / p95 | exp009_net_scale trans mm med / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 21 | 0.10 / 0.18 | 1.6 / 4.1 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | - | - | - | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 2.0 | - | - | - | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 27 | 0.44 / 1.12 | 6.7 / 20.0 | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

