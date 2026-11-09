# exp004_error_decomposition: report (variant main)

30 segments. Runs: E1, E2, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | 0.24 / 1.26 | 0.60 / 4.46 | 0.85 / 7.88 | 1.11 / 14.80 | 0.98 / 8.62 |
| E2 | 0.15 / 0.60 | 0.32 / 1.51 | 0.47 / 2.36 | 0.55 / 3.64 | 0.52 / 0.89 |
| E3 | 0.16 / 0.63 | 0.36 / 1.52 | 0.52 / 2.17 | 0.64 / 2.67 | 0.73 / 1.21 |

n [frame pairs]: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E1 | oracle (tiles) | 3.63 / 17.91 | 9.92 / 65.90 | 13.93 / 117.98 | 17.19 / 209.69 | 12.66 / 158.28 |
| E2 | oracle (tiles) | 2.31 / 9.93 | 5.10 / 25.16 | 7.24 / 34.40 | 8.51 / 49.15 | 8.60 / 14.08 |
| E2 | B+Acheck | 2.32 / 9.44 | 5.68 / 24.69 | 8.75 / 35.37 | 11.06 / 48.22 | 11.21 / 18.50 |
| E3 | oracle (tiles) | 2.47 / 9.73 | 5.52 / 25.17 | 8.19 / 34.71 | 9.98 / 43.87 | 10.88 / 17.42 |
| E3 | B+Acheck | 2.51 / 9.39 | 5.89 / 25.36 | 9.06 / 36.20 | 12.17 / 45.14 | 10.85 / 17.89 |

n [frame pairs]:

- E1 oracle (tiles), E2 oracle (tiles), E3 oracle (tiles): 0.08 s: 2371, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E2 B+Acheck, E3 B+Acheck: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | 1.93% | 14.2 | 43 | 100% |
| E2 | 0.00% | 12.7 | 45 | 89% |
| E3 | 0.21% | 13.0 | 48 | 85% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E2 | B+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 8.1% | 23.1% | -6.9% | ep01, ep11, ep12, ep15, ep20, ep29 |
| E2 | B+Acheck, without flagged | 24/30 | 22 | 4.9% | 19.6% | -4.9% |  |
| E2 | B+Acheck, method B (primary) | 30/30 | 28 | 8.1% | 23.1% | -6.9% |  |
| E2 | B+Acheck, method A (check) | 12/30 | 12 | 4.3% | 16.7% | -4.3% |  |
| E3 | B+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 5.4% | 20.1% | -5.0% | ep01, ep11, ep12, ep20, ep25, ep26 |
| E3 | B+Acheck, without flagged | 24/30 | 22 | 5.0% | 17.6% | -5.0% |  |
| E3 | B+Acheck, method B (primary) | 30/30 | 28 | 5.4% | 20.1% | -5.0% |  |
| E3 | B+Acheck, method A (check) | 14/30 | 14 | 4.4% | 16.5% | -1.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E2 | oracle (tiles) | 989 | 1.1 / 3.4 | 1.5 / 5.5 | 2.1 / 7.5 | 2.7 / 11.0 | 3.6 / 13.6 | 4.6 / 14.1 | 5.4 / 12.9 | 4.9 / 7.5 |
| E2 | B+Acheck | 989 | 1.1 / 3.4 | 1.6 / 5.6 | 2.4 / 8.5 | 3.6 / 13.5 | 5.5 / 18.0 | 7.6 / 26.2 | 7.2 / 32.2 | 6.5 / 14.4 |
| E3 | oracle (tiles) | 989 | 1.2 / 3.6 | 1.7 / 5.7 | 2.3 / 7.8 | 3.2 / 11.3 | 4.3 / 14.6 | 5.5 / 14.7 | 5.9 / 17.0 | 5.8 / 8.7 |
| E3 | B+Acheck | 989 | 1.2 / 3.6 | 1.8 / 5.8 | 2.5 / 9.0 | 3.7 / 13.9 | 5.7 / 18.4 | 7.6 / 27.9 | 7.4 / 30.1 | 5.6 / 12.5 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E2 | every scale | 989 | 0.13 / 0.40 | 0.19 / 0.62 | 0.25 / 0.85 | 0.33 / 1.27 | 0.46 / 1.72 | 0.53 / 1.91 | 0.53 / 1.56 | 0.53 / 0.82 |
| E3 | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.60 | 0.27 / 0.86 | 0.36 / 1.23 | 0.52 / 1.62 | 0.62 / 2.06 | 0.57 / 1.91 | 0.71 / 1.12 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E2 | anchors | 978 | 979 | 979 | 979 |
| E2 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E2 | position [mm], oracle (tiles), mean / median | 4.8 / 2.9 | 6.8 / 4.0 | 8.5 / 4.5 | 10.2 / 4.8 |
| E2 | position [mm], B+Acheck, mean / median | 5.6 / 3.7 | 8.3 / 5.4 | 10.5 / 6.1 | 12.5 / 7.2 |
| E2 | rotation [deg], every scale, mean / median | 0.56 / 0.36 | 0.78 / 0.47 | 0.94 / 0.51 | 1.10 / 0.54 |
| E3 | anchors | 978 | 979 | 979 | 979 |
| E3 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3 | position [mm], oracle (tiles), mean / median | 4.8 / 3.3 | 6.6 / 4.4 | 7.8 / 5.2 | 8.9 / 5.4 |
| E3 | position [mm], B+Acheck, mean / median | 5.5 / 3.8 | 7.9 / 5.4 | 9.5 / 6.2 | 10.9 / 7.0 |
| E3 | rotation [deg], every scale, mean / median | 0.56 / 0.40 | 0.77 / 0.52 | 0.91 / 0.59 | 1.03 / 0.60 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E2, H=100: 49 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 40 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles, dt 0.5 s | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles, dt 2.0 s | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes between the ends | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

## Error decomposition, run E3: SLAM or tile head rotation x configured or oracle scale

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3 rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (B+Acheck) or the per-segment tile oracle (`errdecomp_E3.json`). (1) SLAM rot + B+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + B+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + B+Acheck s 5.7, (2) SLAM rot + oracle s 4.3, (3) tile rot + B+Acheck s 8.8, (4) tile rot + oracle s 7.7 mm; chunk H=30 position mean: (1) SLAM rot + B+Acheck s 7.9, (2) SLAM rot + oracle s 6.6, (3) tile rot + B+Acheck s 13.1, (4) tile rot + oracle s 11.9 mm.

### Error decomposition, E3: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + B+Acheck s | 989 | 1.2 / 3.6 | 1.8 / 5.8 | 2.5 / 9.0 | 3.7 / 13.9 | 5.7 / 18.4 | 7.6 / 27.9 | 7.4 / 30.1 | 5.6 / 12.5 |
| (2) SLAM rot + oracle s | 989 | 1.2 / 3.6 | 1.7 / 5.7 | 2.3 / 7.8 | 3.2 / 11.3 | 4.3 / 14.6 | 5.5 / 14.7 | 5.9 / 17.0 | 5.8 / 8.7 |
| (3) tile rot + B+Acheck s | 989 | 2.2 / 6.2 | 3.1 / 9.1 | 4.3 / 12.8 | 6.0 / 20.1 | 8.8 / 30.5 | 12.0 / 37.0 | 10.5 / 32.7 | 10.5 / 16.3 |
| (4) tile rot + oracle s | 989 | 2.2 / 6.3 | 3.0 / 9.1 | 4.1 / 12.9 | 5.5 / 17.8 | 7.7 / 25.4 | 9.8 / 30.7 | 9.0 / 27.6 | 10.9 / 15.7 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

### Error decomposition, E3: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + B+Acheck s | 989 | 0.14 / 0.44 | 0.20 / 0.60 | 0.27 / 0.86 | 0.36 / 1.23 | 0.52 / 1.62 | 0.62 / 2.06 | 0.57 / 1.91 | 0.71 / 1.12 |
| (2) SLAM rot + oracle s | 989 | 0.14 / 0.44 | 0.20 / 0.60 | 0.27 / 0.86 | 0.36 / 1.23 | 0.52 / 1.62 | 0.62 / 2.06 | 0.57 / 1.91 | 0.71 / 1.12 |
| (3) tile rot + B+Acheck s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

### Error decomposition, E3: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + B+Acheck s | anchors | 978 | 979 | 979 | 979 |
| (1) SLAM rot + B+Acheck s | position [mm], mean / median | 5.5 / 3.8 | 7.9 / 5.4 | 9.5 / 6.2 | 10.9 / 7.0 |
| (1) SLAM rot + B+Acheck s | rotation [deg], mean / median | 0.56 / 0.40 | 0.77 / 0.52 | 0.91 / 0.59 | 1.03 / 0.60 |
| (2) SLAM rot + oracle s | anchors | 978 | 979 | 979 | 979 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 4.8 / 3.3 | 6.6 / 4.4 | 7.8 / 5.2 | 8.9 / 5.4 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.56 / 0.40 | 0.77 / 0.52 | 0.91 / 0.59 | 1.03 / 0.60 |
| (3) tile rot + B+Acheck s | anchors | 978 | 979 | 979 | 979 |
| (3) tile rot + B+Acheck s | position [mm], mean / median | 9.2 / 6.3 | 13.1 / 8.8 | 15.8 / 10.5 | 18.0 / 11.7 |
| (3) tile rot + B+Acheck s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.01 / 0.00 |
| (4) tile rot + oracle s | anchors | 978 | 979 | 979 | 979 |
| (4) tile rot + oracle s | position [mm], mean / median | 8.6 / 6.0 | 11.9 / 8.2 | 14.3 / 9.3 | 16.3 / 9.5 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.01 / 0.00 |

### Error decomposition, E3: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 756, 10-30 155, 30+ 0, unknown 78; oracle scale: 0-10 756, 10-30 155, 30+ 0, unknown 78; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + B+Acheck s | 756 | 1.0 / 2.9 | 1.4 / 4.3 | 2.1 / 5.9 | 3.2 / 8.1 | 5.2 / 12.5 | 7.2 / 20.1 | 7.5 / 30.5 | 5.6 / 12.5 |
| 0-10 | (2) SLAM rot + oracle s | 756 | 1.0 / 3.0 | 1.4 / 4.2 | 1.9 / 5.8 | 2.5 / 7.8 | 3.5 / 11.5 | 5.1 / 13.9 | 6.0 / 18.3 | 5.7 / 8.7 |
| 0-10 | (3) tile rot + B+Acheck s | 756 | 1.9 / 5.2 | 2.5 / 7.6 | 3.5 / 10.8 | 5.0 / 15.4 | 7.6 / 22.8 | 11.4 / 33.5 | 10.8 / 33.3 | 10.5 / 16.4 |
| 0-10 | (4) tile rot + oracle s | 756 | 1.9 / 5.4 | 2.5 / 7.7 | 3.3 / 10.8 | 4.5 / 15.3 | 6.5 / 21.6 | 9.2 / 28.1 | 9.2 / 27.9 | 11.0 / 15.8 |
| 10-30 | (1) SLAM rot + B+Acheck s | 155 | 2.5 / 6.5 | 4.4 / 9.4 | 7.9 / 13.4 | 11.8 / 20.6 | 17.8 / 41.2 | 16.7 / 94.7 | - | - |
| 10-30 | (2) SLAM rot + oracle s | 155 | 2.3 / 6.7 | 3.6 / 9.7 | 6.1 / 13.7 | 8.9 / 19.4 | 11.6 / 33.8 | 12.7 / 96.4 | - | - |
| 10-30 | (3) tile rot + B+Acheck s | 155 | 3.6 / 8.5 | 6.4 / 14.4 | 10.9 / 22.3 | 16.5 / 38.5 | 25.7 / 80.8 | 30.0 / 186.0 | - | - |
| 10-30 | (4) tile rot + oracle s | 155 | 3.6 / 9.1 | 5.7 / 14.4 | 9.7 / 22.2 | 13.0 / 39.5 | 17.7 / 81.8 | 20.3 / 188.0 | - | - |
| 30+ | (1) SLAM rot + B+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + B+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + B+Acheck s | 756 | 0.13 / 0.37 | 0.17 / 0.52 | 0.23 / 0.69 | 0.31 / 0.97 | 0.42 / 1.36 | 0.56 / 1.93 | 0.58 / 1.92 | 0.71 / 1.13 |
| 0-10 | (2) SLAM rot + oracle s | 756 | 0.13 / 0.37 | 0.17 / 0.52 | 0.23 / 0.69 | 0.31 / 0.97 | 0.42 / 1.36 | 0.56 / 1.93 | 0.58 / 1.92 | 0.71 / 1.13 |
| 0-10 | (3) tile rot + B+Acheck s | 756 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 756 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + B+Acheck s | 155 | 0.22 / 0.58 | 0.35 / 1.08 | 0.55 / 1.58 | 0.84 / 2.65 | 1.13 / 5.41 | 1.38 / 11.41 | - | - |
| 10-30 | (2) SLAM rot + oracle s | 155 | 0.22 / 0.58 | 0.35 / 1.08 | 0.55 / 1.58 | 0.84 / 2.65 | 1.13 / 5.41 | 1.38 / 11.41 | - | - |
| 10-30 | (3) tile rot + B+Acheck s | 155 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - | - |
| 10-30 | (4) tile rot + oracle s | 155 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - | - |
| 30+ | (1) SLAM rot + B+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + B+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + B+Acheck s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (1) SLAM rot + B+Acheck s | position [mm], mean / median | 4.3 / 3.3 | 6.3 / 4.9 | 8.3 / 5.9 | 10.0 / 6.5 |
| 0-10 | (1) SLAM rot + B+Acheck s | rotation [deg], mean / median | 0.46 / 0.33 | 0.65 / 0.46 | 0.81 / 0.55 | 0.97 / 0.59 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 3.9 / 2.7 | 5.4 / 3.9 | 6.8 / 4.7 | 8.2 / 5.0 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.46 / 0.33 | 0.65 / 0.46 | 0.81 / 0.55 | 0.97 / 0.59 |
| 0-10 | (3) tile rot + B+Acheck s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (3) tile rot + B+Acheck s | position [mm], mean / median | 7.5 / 5.3 | 11.0 / 8.0 | 14.1 / 9.9 | 17.0 / 11.4 |
| 0-10 | (3) tile rot + B+Acheck s | rotation [deg], mean / median | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 756 | 756 | 756 | 756 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 7.1 / 4.9 | 10.0 / 7.1 | 12.7 / 8.7 | 15.2 / 9.2 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 | 0.01 / 0.00 |
| 10-30 | (1) SLAM rot + B+Acheck s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (1) SLAM rot + B+Acheck s | position [mm], mean / median | 12.2 / 10.5 | 17.3 / 11.5 | 18.2 / 12.0 | 18.2 / 12.0 |
| 10-30 | (1) SLAM rot + B+Acheck s | rotation [deg], mean / median | 1.08 / 0.76 | 1.52 / 0.89 | 1.62 / 0.90 | 1.62 / 0.90 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 10.1 / 7.8 | 14.0 / 9.6 | 14.8 / 9.6 | 14.8 / 9.6 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 1.08 / 0.76 | 1.52 / 0.89 | 1.62 / 0.90 | 1.62 / 0.90 |
| 10-30 | (3) tile rot + B+Acheck s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (3) tile rot + B+Acheck s | position [mm], mean / median | 18.9 / 15.5 | 26.7 / 18.0 | 28.3 / 17.9 | 28.3 / 17.9 |
| 10-30 | (3) tile rot + B+Acheck s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 155 | 155 | 155 | 155 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 17.1 / 11.8 | 24.3 / 13.4 | 25.9 / 13.8 | 25.9 / 13.8 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 | 0.02 / 0.00 |
| 30+ | (1) SLAM rot + B+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (1) SLAM rot + B+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (1) SLAM rot + B+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (2) SLAM rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (3) tile rot + B+Acheck s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (3) tile rot + B+Acheck s | position [mm], mean / median | - | - | - | - |
| 30+ | (3) tile rot + B+Acheck s | rotation [deg], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | anchors | 0 | 0 | 0 | 0 |
| 30+ | (4) tile rot + oracle s | position [mm], mean / median | - | - | - | - |
| 30+ | (4) tile rot + oracle s | rotation [deg], mean / median | - | - | - | - |

### Error decomposition, E3: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.3 / 4.1 | 1.8 / 5.7 | 2.6 / 8.2 | 3.3 / 11.9 | 4.6 / 16.4 | 5.7 / 21.9 | 5.0 / 19.9 | 6.6 / 9.5 |
| translation part dt [mm], B+Acheck s, median / p90 | 2.2 / 6.2 | 3.1 / 9.1 | 4.3 / 12.8 | 6.0 / 20.1 | 8.8 / 30.5 | 12.0 / 37.0 | 10.5 / 32.7 | 10.5 / 16.3 |
| translation part dt [mm], oracle s, median / p90 | 2.2 / 6.3 | 3.0 / 9.1 | 4.1 / 12.9 | 5.5 / 17.8 | 7.7 / 25.4 | 9.8 / 30.7 | 9.0 / 27.6 | 10.9 / 15.7 |
| cos(dR b, dt), B+Acheck s, median | -0.90 | -0.90 | -0.89 | -0.90 | -0.92 | -0.89 | -0.83 | -0.86 |
| cos(dR b, dt), oracle s, median | -0.90 | -0.91 | -0.90 | -0.91 | -0.92 | -0.90 | -0.89 | -0.85 |

Checks: (1) SLAM rot + B+Acheck s vs `labels_E3@B+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 48735 pairs): max |position difference| 4.4e-13 mm, max |R difference| 7.8e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 48735 pairs): max |position difference| 4.4e-13 mm, max |R difference| 7.8e-16.

## Comparison with other experiments

- exp003_droid_sam3: `exp003_droid_sam3/results/metrics.json`

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp004_error_decomposition n | exp004_error_decomposition median | exp004_error_decomposition p95 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p95 |
|---|---|---|---|---|---|---|---|
| static | 0.08 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | 2380 | 0.24 | 1.26 | 2380 | 0.24 | 1.26 |
| E1 | 0.5 | 1931 | 0.60 | 4.46 | 1931 | 0.60 | 4.46 |
| E1 | 1.0 | 1612 | 0.85 | 7.88 | 1612 | 0.85 | 7.88 |
| E1 | 2.0 | 1248 | 1.11 | 14.80 | 1248 | 1.11 | 14.80 |
| E1 | 6.67 | 88 | 0.98 | 8.62 | 88 | 0.98 | 8.62 |
| E2 | 0.08 | 2380 | 0.15 | 0.60 | 2380 | 0.15 | 0.60 |
| E2 | 0.5 | 1931 | 0.32 | 1.51 | 1931 | 0.32 | 1.51 |
| E2 | 1.0 | 1612 | 0.47 | 2.36 | 1612 | 0.47 | 2.36 |
| E2 | 2.0 | 1248 | 0.55 | 3.64 | 1248 | 0.55 | 3.64 |
| E2 | 6.67 | 88 | 0.52 | 0.89 | 88 | 0.52 | 0.89 |
| E3 | 0.08 | 2380 | 0.16 | 0.63 | 2380 | 0.16 | 0.63 |
| E3 | 0.5 | 1931 | 0.36 | 1.52 | 1931 | 0.36 | 1.52 |
| E3 | 1.0 | 1612 | 0.52 | 2.17 | 1612 | 0.52 | 2.17 |
| E3 | 2.0 | 1248 | 0.64 | 2.67 | 1248 | 0.64 | 2.67 |
| E3 | 6.67 | 88 | 0.73 | 1.21 | 88 | 0.73 | 1.21 |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp004_error_decomposition n | exp004_error_decomposition median | exp004_error_decomposition p95 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p95 |
|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | 2371 | 3.63 | 17.91 | 2371 | 3.63 | 17.91 |
| E1 | oracle | 0.5 | 1931 | 9.92 | 65.90 | 1931 | 9.92 | 65.90 |
| E1 | oracle | 1.0 | 1612 | 13.93 | 117.98 | 1612 | 13.93 | 117.98 |
| E1 | oracle | 2.0 | 1248 | 17.19 | 209.69 | 1248 | 17.19 | 209.69 |
| E1 | oracle | 6.67 | 88 | 12.66 | 158.28 | 88 | 12.66 | 158.28 |
| E2 | oracle | 0.08 | 2371 | 2.31 | 9.93 | 2371 | 2.31 | 9.93 |
| E2 | oracle | 0.5 | 1931 | 5.10 | 25.16 | 1931 | 5.10 | 25.16 |
| E2 | oracle | 1.0 | 1612 | 7.24 | 34.40 | 1612 | 7.24 | 34.40 |
| E2 | oracle | 2.0 | 1248 | 8.51 | 49.15 | 1248 | 8.51 | 49.15 |
| E2 | oracle | 6.67 | 88 | 8.60 | 14.08 | 88 | 8.60 | 14.08 |
| E2 | configured | 0.08 | 2380 | 2.32 | 9.44 | 2380 | 2.32 | 9.44 |
| E2 | configured | 0.5 | 1931 | 5.68 | 24.69 | 1931 | 5.68 | 24.69 |
| E2 | configured | 1.0 | 1612 | 8.75 | 35.37 | 1612 | 8.75 | 35.37 |
| E2 | configured | 2.0 | 1248 | 11.06 | 48.22 | 1248 | 11.06 | 48.22 |
| E2 | configured | 6.67 | 88 | 11.21 | 18.50 | 88 | 11.21 | 18.50 |
| E3 | oracle | 0.08 | 2371 | 2.47 | 9.73 | 2371 | 2.47 | 9.73 |
| E3 | oracle | 0.5 | 1931 | 5.52 | 25.17 | 1931 | 5.52 | 25.17 |
| E3 | oracle | 1.0 | 1612 | 8.19 | 34.71 | 1612 | 8.19 | 34.71 |
| E3 | oracle | 2.0 | 1248 | 9.98 | 43.87 | 1248 | 9.98 | 43.87 |
| E3 | oracle | 6.67 | 88 | 10.88 | 17.42 | 88 | 10.88 | 17.42 |
| E3 | configured | 0.08 | 2380 | 2.51 | 9.39 | 2380 | 2.51 | 9.39 |
| E3 | configured | 0.5 | 1931 | 5.89 | 25.36 | 1931 | 5.89 | 25.36 |
| E3 | configured | 1.0 | 1612 | 9.06 | 36.20 | 1612 | 9.06 | 36.20 |
| E3 | configured | 2.0 | 1248 | 12.17 | 45.14 | 1248 | 12.17 | 45.14 |
| E3 | configured | 6.67 | 88 | 10.85 | 17.89 | 88 | 10.85 | 17.89 |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp004_error_decomposition | exp003_droid_sam3 |
|---|---|---|---|
| E1 | track fail | 1.93% | 1.93% |
| E1 | keyframes / segment | 14.2 | 14.2 |
| E1 | runtime s / segment | 43 | 43 |
| E1 | valid pixels | 100% | 100% |
| E2 | track fail | 0.00% | 0.00% |
| E2 | keyframes / segment | 12.7 | 12.7 |
| E2 | runtime s / segment | 45 | 45 |
| E2 | valid pixels | 89% | 89% |
| E3 | track fail | 0.21% | 0.21% |
| E3 | keyframes / segment | 13.0 | 13.0 |
| E3 | runtime s / segment | 48 | 48 |
| E3 | valid pixels | 85% | 85% |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp004_error_decomposition | exp003_droid_sam3 |
|---|---|---|---|
| E2 | scale label | B+Acheck | B+Acheck |
| E2 | segments with a scale | 30/30 | 30/30 |
| E2 | compared (tile GT) | 28 | 28 |
| E2 | abs err median | 8.1% | 8.1% |
| E2 | abs err p90 | 23.1% | 23.1% |
| E2 | bias (median) | -6.9% | -6.9% |
| E2 | flagged | ep01, ep11, ep12, ep15, ep20, ep29 | ep01, ep11, ep12, ep15, ep20, ep29 |
| E2 | without flagged: abs err median / p90 | 4.9% / 19.6% | 4.9% / 19.6% |
| E2 | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 8.1% / 23.1% / -6.9% | 30/30, n 28: 8.1% / 23.1% / -6.9% |
| E2 | method A: segments ok, n: abs err median / p90 / bias | 12/30, n 12: 4.3% / 16.7% / -4.3% | 12/30, n 12: 4.3% / 16.7% / -4.3% |
| E3 | scale label | B+Acheck | B+Acheck |
| E3 | segments with a scale | 30/30 | 30/30 |
| E3 | compared (tile GT) | 28 | 28 |
| E3 | abs err median | 5.4% | 5.4% |
| E3 | abs err p90 | 20.1% | 20.1% |
| E3 | bias (median) | -5.0% | -5.0% |
| E3 | flagged | ep01, ep11, ep12, ep20, ep25, ep26 | ep01, ep11, ep12, ep20, ep25, ep26 |
| E3 | without flagged: abs err median / p90 | 5.0% / 17.6% | 5.0% / 17.6% |
| E3 | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 5.4% / 20.1% / -5.0% | 30/30, n 28: 5.4% / 20.1% / -5.0% |
| E3 | method A: segments ok, n: abs err median / p90 / bias | 14/30, n 14: 4.4% / 16.5% / -1.6% | 14/30, n 14: 4.4% / 16.5% / -1.6% |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp004_error_decomposition n | exp004_error_decomposition median | exp004_error_decomposition p90 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p90 |
|---|---|---|---|---|---|---|---|---|
| E2 | oracle | anchors | 989 |  |  | 989 |  |  |
| E2 | oracle | 0.07 s | 976 | 1.1 | 3.4 | 976 | 1.1 | 3.4 |
| E2 | oracle | 0.13 s | 963 | 1.5 | 5.5 | 963 | 1.5 | 5.5 |
| E2 | oracle | 0.27 s | 937 | 2.1 | 7.5 | 937 | 2.1 | 7.5 |
| E2 | oracle | 0.53 s | 890 | 2.7 | 11.0 | 890 | 2.7 | 11.0 |
| E2 | oracle | 1.00 s | 814 | 3.6 | 13.6 | 814 | 3.6 | 13.6 |
| E2 | oracle | 2.00 s | 676 | 4.6 | 14.1 | 676 | 4.6 | 14.1 |
| E2 | oracle | 4.00 s | 398 | 5.4 | 12.9 | 398 | 5.4 | 12.9 |
| E2 | oracle | 6.67 s | 55 | 4.9 | 7.5 | 55 | 4.9 | 7.5 |
| E2 | configured | anchors | 989 |  |  | 989 |  |  |
| E2 | configured | 0.07 s | 976 | 1.1 | 3.4 | 976 | 1.1 | 3.4 |
| E2 | configured | 0.13 s | 963 | 1.6 | 5.6 | 963 | 1.6 | 5.6 |
| E2 | configured | 0.27 s | 937 | 2.4 | 8.5 | 937 | 2.4 | 8.5 |
| E2 | configured | 0.53 s | 890 | 3.6 | 13.5 | 890 | 3.6 | 13.5 |
| E2 | configured | 1.00 s | 814 | 5.5 | 18.0 | 814 | 5.5 | 18.0 |
| E2 | configured | 2.00 s | 676 | 7.6 | 26.2 | 676 | 7.6 | 26.2 |
| E2 | configured | 4.00 s | 398 | 7.2 | 32.2 | 398 | 7.2 | 32.2 |
| E2 | configured | 6.67 s | 55 | 6.5 | 14.4 | 55 | 6.5 | 14.4 |
| E3 | oracle | anchors | 989 |  |  | 989 |  |  |
| E3 | oracle | 0.07 s | 976 | 1.2 | 3.6 | 976 | 1.2 | 3.6 |
| E3 | oracle | 0.13 s | 963 | 1.7 | 5.7 | 963 | 1.7 | 5.7 |
| E3 | oracle | 0.27 s | 937 | 2.3 | 7.8 | 937 | 2.3 | 7.8 |
| E3 | oracle | 0.53 s | 890 | 3.2 | 11.3 | 890 | 3.2 | 11.3 |
| E3 | oracle | 1.00 s | 814 | 4.3 | 14.6 | 814 | 4.3 | 14.6 |
| E3 | oracle | 2.00 s | 676 | 5.5 | 14.7 | 676 | 5.5 | 14.7 |
| E3 | oracle | 4.00 s | 398 | 5.9 | 17.0 | 398 | 5.9 | 17.0 |
| E3 | oracle | 6.67 s | 55 | 5.8 | 8.7 | 55 | 5.8 | 8.7 |
| E3 | configured | anchors | 989 |  |  | 989 |  |  |
| E3 | configured | 0.07 s | 976 | 1.2 | 3.6 | 976 | 1.2 | 3.6 |
| E3 | configured | 0.13 s | 963 | 1.8 | 5.8 | 963 | 1.8 | 5.8 |
| E3 | configured | 0.27 s | 937 | 2.5 | 9.0 | 937 | 2.5 | 9.0 |
| E3 | configured | 0.53 s | 890 | 3.7 | 13.9 | 890 | 3.7 | 13.9 |
| E3 | configured | 1.00 s | 814 | 5.7 | 18.4 | 814 | 5.7 | 18.4 |
| E3 | configured | 2.00 s | 676 | 7.6 | 27.9 | 676 | 7.6 | 27.9 |
| E3 | configured | 4.00 s | 398 | 7.4 | 30.1 | 398 | 7.4 | 30.1 |
| E3 | configured | 6.67 s | 55 | 5.6 | 12.5 | 55 | 5.6 | 12.5 |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp004_error_decomposition n | exp004_error_decomposition median | exp004_error_decomposition p90 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p90 |
|---|---|---|---|---|---|---|---|---|
| E2 | every scale | anchors | 989 |  |  | 989 |  |  |
| E2 | every scale | 0.07 s | 976 | 0.13 | 0.40 | 976 | 0.13 | 0.40 |
| E2 | every scale | 0.13 s | 963 | 0.19 | 0.62 | 963 | 0.19 | 0.62 |
| E2 | every scale | 0.27 s | 937 | 0.25 | 0.85 | 937 | 0.25 | 0.85 |
| E2 | every scale | 0.53 s | 890 | 0.33 | 1.27 | 890 | 0.33 | 1.27 |
| E2 | every scale | 1.00 s | 814 | 0.46 | 1.72 | 814 | 0.46 | 1.72 |
| E2 | every scale | 2.00 s | 676 | 0.53 | 1.91 | 676 | 0.53 | 1.91 |
| E2 | every scale | 4.00 s | 398 | 0.53 | 1.56 | 398 | 0.53 | 1.56 |
| E2 | every scale | 6.67 s | 55 | 0.53 | 0.82 | 55 | 0.53 | 0.82 |
| E3 | every scale | anchors | 989 |  |  | 989 |  |  |
| E3 | every scale | 0.07 s | 976 | 0.14 | 0.44 | 976 | 0.14 | 0.44 |
| E3 | every scale | 0.13 s | 963 | 0.20 | 0.60 | 963 | 0.20 | 0.60 |
| E3 | every scale | 0.27 s | 937 | 0.27 | 0.86 | 937 | 0.27 | 0.86 |
| E3 | every scale | 0.53 s | 890 | 0.36 | 1.23 | 890 | 0.36 | 1.23 |
| E3 | every scale | 1.00 s | 814 | 0.52 | 1.62 | 814 | 0.52 | 1.62 |
| E3 | every scale | 2.00 s | 676 | 0.62 | 2.06 | 676 | 0.62 | 2.06 |
| E3 | every scale | 4.00 s | 398 | 0.57 | 1.91 | 398 | 0.57 | 1.91 |
| E3 | every scale | 6.67 s | 55 | 0.71 | 1.12 | 55 | 0.71 | 1.12 |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp004_error_decomposition | exp003_droid_sam3 |
|---|---|---|---|---|---|
| E2 | every scale | anchors | 15 (1.00 s) | 978 | 978 |
| E2 | every scale | anchors | 30 (2.00 s) | 979 | 979 |
| E2 | every scale | anchors | 50 (3.33 s) | 979 | 979 |
| E2 | every scale | anchors | 100 (6.67 s) | 979 | 979 |
| E2 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | 15 |
| E2 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | 30 |
| E2 | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | 46 |
| E2 | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | 49 |
| E2 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.8 / 2.9 | 4.8 / 2.9 |
| E2 | oracle | pos mm, mean / median | 30 (2.00 s) | 6.8 / 4.0 | 6.8 / 4.0 |
| E2 | oracle | pos mm, mean / median | 50 (3.33 s) | 8.5 / 4.5 | 8.5 / 4.5 |
| E2 | oracle | pos mm, mean / median | 100 (6.67 s) | 10.2 / 4.8 | 10.2 / 4.8 |
| E2 | configured | pos mm, mean / median | 15 (1.00 s) | 5.6 / 3.7 | 5.6 / 3.7 |
| E2 | configured | pos mm, mean / median | 30 (2.00 s) | 8.3 / 5.4 | 8.3 / 5.4 |
| E2 | configured | pos mm, mean / median | 50 (3.33 s) | 10.5 / 6.1 | 10.5 / 6.1 |
| E2 | configured | pos mm, mean / median | 100 (6.67 s) | 12.5 / 7.2 | 12.5 / 7.2 |
| E2 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.56 / 0.36 | 0.56 / 0.36 |
| E2 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.47 | 0.78 / 0.47 |
| E2 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.94 / 0.51 | 0.94 / 0.51 |
| E2 | every scale | rot deg, mean / median | 100 (6.67 s) | 1.10 / 0.54 | 1.10 / 0.54 |
| E3 | every scale | anchors | 15 (1.00 s) | 978 | 978 |
| E3 | every scale | anchors | 30 (2.00 s) | 979 | 979 |
| E3 | every scale | anchors | 50 (3.33 s) | 979 | 979 |
| E3 | every scale | anchors | 100 (6.67 s) | 979 | 979 |
| E3 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | 15 |
| E3 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | 30 |
| E3 | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | 46 |
| E3 | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | 49 |
| E3 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.8 / 3.3 | 4.8 / 3.3 |
| E3 | oracle | pos mm, mean / median | 30 (2.00 s) | 6.6 / 4.4 | 6.6 / 4.4 |
| E3 | oracle | pos mm, mean / median | 50 (3.33 s) | 7.8 / 5.2 | 7.8 / 5.2 |
| E3 | oracle | pos mm, mean / median | 100 (6.67 s) | 8.9 / 5.4 | 8.9 / 5.4 |
| E3 | configured | pos mm, mean / median | 15 (1.00 s) | 5.5 / 3.8 | 5.5 / 3.8 |
| E3 | configured | pos mm, mean / median | 30 (2.00 s) | 7.9 / 5.4 | 7.9 / 5.4 |
| E3 | configured | pos mm, mean / median | 50 (3.33 s) | 9.5 / 6.2 | 9.5 / 6.2 |
| E3 | configured | pos mm, mean / median | 100 (6.67 s) | 10.9 / 7.0 | 10.9 / 7.0 |
| E3 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.56 / 0.40 | 0.56 / 0.40 |
| E3 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.77 / 0.52 | 0.77 / 0.52 |
| E3 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.91 / 0.59 | 0.91 / 0.59 |
| E3 | every scale | rot deg, mean / median | 100 (6.67 s) | 1.03 / 0.60 | 1.03 / 0.60 |

### Ground-truth noise floor

| pairs | dt [s] | exp004_error_decomposition n | exp004_error_decomposition rot deg med / p95 | exp004_error_decomposition trans mm med / p95 | exp003_droid_sam3 n | exp003_droid_sam3 rot deg med / p95 | exp003_droid_sam3 trans mm med / p95 |
|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 2.0 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

