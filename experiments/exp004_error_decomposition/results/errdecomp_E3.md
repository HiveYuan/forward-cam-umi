# Error decomposition on yam_glove7, run E3

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3 rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (B+Acheck) or the per-segment tile oracle (`errdecomp_E3.json`). (1) SLAM rot + B+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + B+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + B+Acheck s 5.7, (2) SLAM rot + oracle s 4.3, (3) tile rot + B+Acheck s 8.8, (4) tile rot + oracle s 7.7 mm; chunk H=30 position mean: (1) SLAM rot + B+Acheck s 7.9, (2) SLAM rot + oracle s 6.6, (3) tile rot + B+Acheck s 13.1, (4) tile rot + oracle s 11.9 mm.

## Error decomposition, E3: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + B+Acheck s | 989 | 1.2 / 3.6 | 1.8 / 5.8 | 2.5 / 9.0 | 3.7 / 13.9 | 5.7 / 18.4 | 7.6 / 27.9 | 7.4 / 30.1 | 5.6 / 12.5 |
| (2) SLAM rot + oracle s | 989 | 1.2 / 3.6 | 1.7 / 5.7 | 2.3 / 7.8 | 3.2 / 11.3 | 4.3 / 14.6 | 5.5 / 14.7 | 5.9 / 17.0 | 5.8 / 8.7 |
| (3) tile rot + B+Acheck s | 989 | 2.2 / 6.2 | 3.1 / 9.1 | 4.3 / 12.8 | 6.0 / 20.1 | 8.8 / 30.5 | 12.0 / 37.0 | 10.5 / 32.7 | 10.5 / 16.3 |
| (4) tile rot + oracle s | 989 | 2.2 / 6.3 | 3.0 / 9.1 | 4.1 / 12.9 | 5.5 / 17.8 | 7.7 / 25.4 | 9.8 / 30.7 | 9.0 / 27.6 | 10.9 / 15.7 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Error decomposition, E3: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + B+Acheck s | 989 | 0.14 / 0.44 | 0.20 / 0.60 | 0.27 / 0.86 | 0.36 / 1.23 | 0.52 / 1.62 | 0.62 / 2.06 | 0.57 / 1.91 | 0.71 / 1.12 |
| (2) SLAM rot + oracle s | 989 | 0.14 / 0.44 | 0.20 / 0.60 | 0.27 / 0.86 | 0.36 / 1.23 | 0.52 / 1.62 | 0.62 / 2.06 | 0.57 / 1.91 | 0.71 / 1.12 |
| (3) tile rot + B+Acheck s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Error decomposition, E3: chunk-length label error over steps 1..H, mean / median over anchors

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

## Error decomposition, E3: by head rotation speed [deg/s]

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

## Error decomposition, E3: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.3 / 4.1 | 1.8 / 5.7 | 2.6 / 8.2 | 3.3 / 11.9 | 4.6 / 16.4 | 5.7 / 21.9 | 5.0 / 19.9 | 6.6 / 9.5 |
| translation part dt [mm], B+Acheck s, median / p90 | 2.2 / 6.2 | 3.1 / 9.1 | 4.3 / 12.8 | 6.0 / 20.1 | 8.8 / 30.5 | 12.0 / 37.0 | 10.5 / 32.7 | 10.5 / 16.3 |
| translation part dt [mm], oracle s, median / p90 | 2.2 / 6.3 | 3.0 / 9.1 | 4.1 / 12.9 | 5.5 / 17.8 | 7.7 / 25.4 | 9.8 / 30.7 | 9.0 / 27.6 | 10.9 / 15.7 |
| cos(dR b, dt), B+Acheck s, median | -0.90 | -0.90 | -0.89 | -0.90 | -0.92 | -0.89 | -0.83 | -0.86 |
| cos(dR b, dt), oracle s, median | -0.90 | -0.91 | -0.90 | -0.91 | -0.92 | -0.90 | -0.89 | -0.85 |

Checks: (1) SLAM rot + B+Acheck s vs `labels_E3@B+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 48735 pairs): max |position difference| 4.4e-13 mm, max |R difference| 7.8e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 48735 pairs): max |position difference| 4.4e-13 mm, max |R difference| 7.8e-16.

## Segments

| segment | configured s | oracle s | flagged | kept: tiles / configured / oracle | anchors configured / oracle |
|---|---|---|---|---|---|
| ep00 | 0.6075 | 0.5840 |  | y/y/y | 98 / 98 |
| ep01 | 0.7676 | 0.7220 | yes | n/y/y | 0 / 0 |
| ep02 | 0.5150 | 0.5446 |  | n/y/y | 0 / 0 |
| ep03 | 0.0408 | 0.0455 |  | n/y/y | 0 / 0 |
| ep04 | 0.7355 | 0.7775 |  | n/y/y | 0 / 0 |
| ep05 | 0.5542 | 0.6752 |  | n/y/y | 0 / 0 |
| ep06 | 0.6193 | 0.7298 |  | n/y/y | 0 / 0 |
| ep07 | 0.6493 | - |  | n/y/n | 0 / 0 |
| ep08 | 0.6094 | 0.6422 |  | n/y/y | 0 / 0 |
| ep09 | 0.2382 | 0.2376 |  | n/y/y | 0 / 0 |
| ep10 | 0.5700 | 0.5811 |  | y/y/y | 110 / 110 |
| ep11 | 0.0762 | 0.0907 | yes | y/y/y | 81 / 81 |
| ep12 | 0.6830 | 0.8453 | yes | y/y/y | 93 / 93 |
| ep13 | 0.8035 | 0.7837 |  | n/y/y | 0 / 0 |
| ep14 | 0.8479 | 0.8604 |  | n/y/y | 0 / 0 |
| ep15 | 0.4024 | 0.4656 |  | y/y/y | 104 / 104 |
| ep16 | 0.1441 | - |  | n/y/n | 0 / 0 |
| ep17 | 0.7132 | 0.7901 |  | y/y/y | 95 / 95 |
| ep18 | 0.4899 | 0.5148 |  | y/y/y | 124 / 124 |
| ep19 | 0.8727 | 0.8608 |  | n/y/y | 0 / 0 |
| ep20 | 0.5911 | 0.9193 | yes | n/y/y | 0 / 0 |
| ep21 | 0.6617 | 0.8494 |  | y/y/y | 102 / 102 |
| ep22 | 0.5919 | 0.6194 |  | n/y/y | 0 / 0 |
| ep23 | 0.6422 | 0.7429 |  | n/y/y | 0 / 0 |
| ep24 | 0.6138 | 0.6399 |  | y/y/y | 81 / 81 |
| ep25 | 1.2389 | 1.1793 | yes | n/y/y | 0 / 0 |
| ep26 | 0.6658 | 0.5952 | yes | n/y/y | 0 / 0 |
| ep27 | 0.8223 | 0.8528 |  | y/y/y | 101 / 101 |
| ep28 | 0.0836 | 0.0822 |  | n/y/y | 0 / 0 |
| ep29 | 0.8673 | 1.2245 |  | n/y/y | 0 / 0 |
