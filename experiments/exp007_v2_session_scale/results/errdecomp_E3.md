# Error decomposition on yam_glove7, run E3

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3 rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bsession+Acheck) or the per-segment tile oracle (`errdecomp_E3.json`). (1) SLAM rot + Bsession+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bsession+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bsession+Acheck s 4.5, (2) SLAM rot + oracle s 3.9, (3) tile rot + Bsession+Acheck s 8.2, (4) tile rot + oracle s 7.3 mm; chunk H=30 position mean: (1) SLAM rot + Bsession+Acheck s 7.0, (2) SLAM rot + oracle s 6.4, (3) tile rot + Bsession+Acheck s 12.6, (4) tile rot + oracle s 12.1 mm.

## Error decomposition, E3: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 989 | 1.2 / 3.5 | 1.6 / 5.7 | 2.3 / 7.7 | 3.3 / 11.3 | 4.5 / 15.0 | 6.2 / 18.1 | 6.6 / 22.3 | 7.6 / 17.2 |
| (2) SLAM rot + oracle s | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| (3) tile rot + Bsession+Acheck s | 989 | 2.2 / 6.3 | 3.1 / 9.2 | 4.2 / 12.4 | 5.7 / 17.6 | 8.2 / 25.4 | 11.8 / 30.1 | 9.8 / 33.7 | 11.5 / 22.7 |
| (4) tile rot + oracle s | 989 | 2.1 / 6.3 | 3.1 / 9.1 | 4.1 / 12.2 | 5.5 / 17.3 | 7.3 / 25.0 | 9.6 / 29.9 | 9.3 / 33.7 | 10.2 / 14.0 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Error decomposition, E3: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| (2) SLAM rot + oracle s | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| (3) tile rot + Bsession+Acheck s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 989 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Error decomposition, E3: chunk-length label error over steps 1..H, mean / median over anchors

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

## Error decomposition, E3: by head rotation speed [deg/s]

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

## Error decomposition, E3: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.3 / 4.3 | 1.9 / 5.8 | 2.5 / 7.7 | 3.4 / 11.1 | 4.4 / 15.5 | 6.0 / 20.9 | 5.0 / 24.0 | 5.6 / 8.0 |
| translation part dt [mm], Bsession+Acheck s, median / p90 | 2.2 / 6.2 | 3.1 / 9.2 | 4.2 / 12.3 | 5.7 / 17.6 | 8.2 / 25.3 | 11.8 / 30.1 | 9.8 / 33.7 | 11.5 / 22.7 |
| translation part dt [mm], oracle s, median / p90 | 2.1 / 6.2 | 3.1 / 9.1 | 4.1 / 12.3 | 5.5 / 17.3 | 7.3 / 24.9 | 9.6 / 29.9 | 9.3 / 33.7 | 10.2 / 14.0 |
| cos(dR b, dt), Bsession+Acheck s, median | -0.91 | -0.90 | -0.90 | -0.92 | -0.93 | -0.88 | -0.84 | -0.85 |
| cos(dR b, dt), oracle s, median | -0.91 | -0.91 | -0.90 | -0.92 | -0.94 | -0.92 | -0.90 | -0.85 |

Checks: (1) SLAM rot + Bsession+Acheck s vs `labels_E3@Bsession+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 48735 pairs): max |position difference| 4.4e-13 mm, max |R difference| 7.2e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 48735 pairs): max |position difference| 3.9e-13 mm, max |R difference| 7.2e-16.

## Segments

| segment | configured s | oracle s | flagged | kept: tiles / configured / oracle | anchors configured / oracle |
|---|---|---|---|---|---|
| ep00 | 0.6177 | 0.6231 |  | y/y/y | 98 / 98 |
| ep01 | 0.7317 | 0.8276 |  | n/y/y | 0 / 0 |
| ep02 | 0.5851 | 0.5863 |  | n/y/y | 0 / 0 |
| ep03 | 0.2957 | 0.3450 |  | n/y/y | 0 / 0 |
| ep04 | 0.6166 | 0.7427 |  | n/y/y | 0 / 0 |
| ep05 | 0.4619 | 0.5695 |  | n/y/y | 0 / 0 |
| ep06 | 0.5465 | 0.5964 |  | n/y/y | 0 / 0 |
| ep07 | 0.6282 | - |  | n/y/n | 0 / 0 |
| ep08 | 0.6111 | 0.6805 |  | n/y/y | 0 / 0 |
| ep09 | 0.5019 | 0.5375 | yes | n/y/y | 0 / 0 |
| ep10 | 0.4786 | 0.4555 |  | y/y/y | 110 / 110 |
| ep11 | 0.1535 | 0.1555 |  | y/y/y | 81 / 81 |
| ep12 | 0.4204 | 0.4532 |  | y/y/y | 93 / 93 |
| ep13 | 0.7449 | 0.7447 |  | n/y/y | 0 / 0 |
| ep14 | 0.7733 | 0.8047 |  | n/y/y | 0 / 0 |
| ep15 | 0.4761 | 0.4991 |  | y/y/y | 104 / 104 |
| ep16 | 1.2944 | - |  | n/y/n | 0 / 0 |
| ep17 | 0.7138 | 0.7803 |  | y/y/y | 95 / 95 |
| ep18 | 0.6487 | 0.6937 |  | y/y/y | 124 / 124 |
| ep19 | 0.6410 | 0.7867 | yes | n/y/y | 0 / 0 |
| ep20 | 0.8063 | 0.9653 |  | n/y/y | 0 / 0 |
| ep21 | 0.7617 | 0.8335 |  | y/y/y | 102 / 102 |
| ep22 | 0.5959 | 0.5505 |  | n/y/y | 0 / 0 |
| ep23 | 0.6858 | 0.7551 |  | n/y/y | 0 / 0 |
| ep24 | 0.7033 | 0.7746 |  | y/y/y | 81 / 81 |
| ep25 | 0.7188 | 0.7452 |  | n/y/y | 0 / 0 |
| ep26 | 0.7370 | 0.7963 |  | n/y/y | 0 / 0 |
| ep27 | 1.0571 | 1.0530 |  | y/y/y | 101 / 101 |
| ep28 | 0.1456 | 0.1500 |  | n/y/y | 0 / 0 |
| ep29 | 0.8510 | 1.2498 |  | n/y/y | 0 / 0 |
