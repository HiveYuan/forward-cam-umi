# Error decomposition on yam_glove8, run E3_da2

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3_da2 rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bsession+Acheck) or the per-segment tile oracle (`errdecomp_E3_da2.json`). (1) SLAM rot + Bsession+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bsession+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bsession+Acheck s 5.1, (2) SLAM rot + oracle s 5.0, (3) tile rot + Bsession+Acheck s 8.0, (4) tile rot + oracle s 8.2 mm; chunk H=30 position mean: (1) SLAM rot + Bsession+Acheck s 6.1, (2) SLAM rot + oracle s 7.8, (3) tile rot + Bsession+Acheck s 9.4, (4) tile rot + oracle s 10.8 mm.

## Error decomposition, E3_da2: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 249 | 1.4 / 3.7 | 2.1 / 5.6 | 2.9 / 7.2 | 4.0 / 8.3 | 5.1 / 11.6 | 7.0 / 18.8 | 11.5 / 18.1 |
| (2) SLAM rot + oracle s | 249 | 1.4 / 4.0 | 2.1 / 6.1 | 3.1 / 7.7 | 4.1 / 9.5 | 5.0 / 19.6 | 5.7 / 37.6 | 9.4 / 31.0 |
| (3) tile rot + Bsession+Acheck s | 249 | 2.4 / 5.8 | 3.8 / 8.9 | 5.2 / 12.4 | 6.9 / 14.8 | 8.0 / 20.1 | 11.0 / 26.5 | 15.7 / 25.1 |
| (4) tile rot + oracle s | 249 | 2.4 / 5.6 | 3.8 / 9.1 | 5.4 / 12.9 | 7.1 / 16.1 | 8.2 / 25.2 | 8.8 / 41.8 | 12.9 / 35.9 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

## Error decomposition, E3_da2: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bsession+Acheck s | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| (2) SLAM rot + oracle s | 249 | 0.15 / 0.35 | 0.24 / 0.51 | 0.32 / 0.70 | 0.39 / 0.81 | 0.44 / 1.07 | 0.57 / 1.13 | 0.70 / 1.32 |
| (3) tile rot + Bsession+Acheck s | 249 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 249 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 244, 0.13 s: 239, 0.27 s: 229, 0.53 s: 210, 1.00 s: 183, 2.00 s: 147, 4.00 s: 76

## Error decomposition, E3_da2: chunk-length label error over steps 1..H, mean / median over anchors

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

## Error decomposition, E3_da2: by head rotation speed [deg/s]

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

## Error decomposition, E3_da2: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s |
|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.4 / 3.0 | 2.1 / 4.5 | 2.7 / 6.0 | 3.3 / 7.0 | 4.1 / 9.3 | 4.5 / 11.0 | 6.2 / 10.6 |
| translation part dt [mm], Bsession+Acheck s, median / p90 | 2.4 / 5.8 | 3.8 / 8.7 | 5.2 / 12.3 | 6.9 / 14.8 | 8.0 / 20.7 | 11.0 / 26.6 | 15.7 / 25.0 |
| translation part dt [mm], oracle s, median / p90 | 2.4 / 5.6 | 3.8 / 9.1 | 5.4 / 12.9 | 7.0 / 16.3 | 8.2 / 25.2 | 8.8 / 42.8 | 12.9 / 35.0 |
| cos(dR b, dt), Bsession+Acheck s, median | -0.92 | -0.93 | -0.93 | -0.91 | -0.92 | -0.90 | -0.76 |
| cos(dR b, dt), oracle s, median | -0.92 | -0.93 | -0.93 | -0.91 | -0.86 | -0.85 | -0.79 |

Checks: (1) SLAM rot + Bsession+Acheck s vs `labels_E3_da2@Bsession+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3_da2.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 10222 pairs): max |position difference| 3.3e-13 mm, max |R difference| 6.5e-16; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 10222 pairs): max |position difference| 3.3e-13 mm, max |R difference| 6.5e-16.

## Segments

| segment | configured s | oracle s | flagged | kept: tiles / configured / oracle | anchors configured / oracle |
|---|---|---|---|---|---|
| ep00 | 0.5825 | 0.6554 |  | y/y/y | 86 / 86 |
| ep01 | 1.3260 | 1.4676 |  | y/y/y | 84 / 84 |
| ep02 | 0.7492 | 0.6741 |  | y/y/y | 79 / 79 |
| ep03 | 0.7660 | 0.8316 |  | n/y/y | 0 / 0 |
