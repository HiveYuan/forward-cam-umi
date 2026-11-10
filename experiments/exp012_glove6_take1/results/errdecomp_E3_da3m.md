# Error decomposition on yam_glove6_take1, run E3_da3m

Tool label error on the 15 fps training timeline vs the tile labels (as in the tool label tables), with the head motion cam_t->cam_t+dt of run E3_da3m rebuilt from one rotation source and one scale: rotation from SLAM or from the tile head poses, translation = s x SLAM's (unscaled) translation with s = the configured scale (Bnet+Acheck) or the per-segment tile oracle (`errdecomp_E3_da3m.json`). (1) SLAM rot + Bnet+Acheck s: the pipeline; (2) SLAM rot + oracle s: perfect scale ~ stereo; (3) tile rot + Bnet+Acheck s: perfect rotation ~ IMU; (4) tile rot + oracle s: both. What is left in the last one is SLAM's translation direction and its scale drift within a segment.

dt 1.00 s position median: (1) SLAM rot + Bnet+Acheck s 5.1, (2) SLAM rot + oracle s 3.1, (3) tile rot + Bnet+Acheck s 6.9, (4) tile rot + oracle s 5.1 mm; chunk H=30 position mean: (1) SLAM rot + Bnet+Acheck s 6.2, (2) SLAM rot + oracle s 4.3, (3) tile rot + Bnet+Acheck s 8.1, (4) tile rot + oracle s 6.5 mm.

## Error decomposition, E3_da3m: tool_t->tool_t+dt position error [mm], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 1643 | 1.2 / 3.5 | 1.7 / 5.2 | 2.5 / 7.3 | 3.7 / 9.7 | 5.1 / 13.7 | 7.5 / 18.3 | 9.3 / 22.8 | 9.7 / 15.2 |
| (2) SLAM rot + oracle s | 1643 | 1.1 / 3.3 | 1.5 / 4.9 | 2.1 / 6.6 | 2.7 / 8.0 | 3.1 / 9.1 | 3.5 / 9.2 | 4.3 / 9.7 | 4.4 / 8.3 |
| (3) tile rot + Bnet+Acheck s | 1643 | 2.0 / 5.6 | 2.8 / 7.8 | 3.8 / 10.5 | 5.3 / 13.2 | 6.9 / 17.9 | 9.2 / 19.7 | 12.1 / 24.7 | 12.5 / 24.5 |
| (4) tile rot + oracle s | 1643 | 2.0 / 5.5 | 2.6 / 7.6 | 3.6 / 10.2 | 4.6 / 12.3 | 5.1 / 14.0 | 5.8 / 14.0 | 7.7 / 16.3 | 8.5 / 16.6 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Error decomposition, E3_da3m: tool_t->tool_t+dt rotation error [deg], median / p90

| combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| (2) SLAM rot + oracle s | 1643 | 0.13 / 0.35 | 0.17 / 0.51 | 0.23 / 0.66 | 0.29 / 0.79 | 0.32 / 0.91 | 0.37 / 0.98 | 0.51 / 1.10 | 0.50 / 1.13 |
| (3) tile rot + Bnet+Acheck s | 1643 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| (4) tile rot + oracle s | 1643 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

n [anchors counting the step]: 0.07 s: 1613, 0.13 s: 1583, 0.27 s: 1527, 0.53 s: 1416, 1.00 s: 1243, 2.00 s: 982, 4.00 s: 587, 6.67 s: 78

## Error decomposition, E3_da3m: chunk-length label error over steps 1..H, mean / median over anchors

| combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| (1) SLAM rot + Bnet+Acheck s | anchors | 1619 | 1624 | 1624 | 1624 |
| (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 4.7 / 3.8 | 6.2 / 5.2 | 7.2 / 6.1 | 7.6 / 6.4 |
| (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| (2) SLAM rot + oracle s | anchors | 1619 | 1624 | 1624 | 1624 |
| (2) SLAM rot + oracle s | position [mm], mean / median | 3.7 / 2.9 | 4.3 / 3.5 | 4.6 / 3.8 | 4.9 / 4.0 |
| (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.43 / 0.31 | 0.48 / 0.37 | 0.52 / 0.40 | 0.55 / 0.45 |
| (3) tile rot + Bnet+Acheck s | anchors | 1619 | 1624 | 1624 | 1624 |
| (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 6.5 / 5.4 | 8.1 / 6.9 | 9.2 / 8.2 | 9.7 / 8.6 |
| (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 |
| (4) tile rot + oracle s | anchors | 1619 | 1624 | 1624 | 1624 |
| (4) tile rot + oracle s | position [mm], mean / median | 5.7 / 4.7 | 6.5 / 5.5 | 7.1 / 6.0 | 7.5 / 6.5 |
| (4) tile rot + oracle s | rotation [deg], mean / median | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 | 0.10 / 0.00 |

## Error decomposition, E3_da3m: by head rotation speed [deg/s]

Speed = tile head rotation between the anchor and 0.5 s later, divided by 0.5 s; anchors per bin (configured scale: 0-10 1222, 10-30 240, 30+ 0, unknown 181; oracle scale: 0-10 1222, 10-30 240, 30+ 0, unknown 181; unknown = no tile pose within 0.12 s of an end, in no bin).

position [mm], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 1222 | 1.1 / 3.0 | 1.5 / 4.2 | 2.2 / 6.0 | 3.4 / 8.4 | 4.6 / 11.3 | 7.2 / 17.9 | 8.7 / 22.9 | 9.7 / 15.2 |
| 0-10 | (2) SLAM rot + oracle s | 1222 | 1.0 / 2.8 | 1.4 / 4.0 | 1.8 / 5.4 | 2.5 / 6.9 | 2.8 / 7.4 | 3.3 / 8.0 | 4.0 / 9.1 | 4.4 / 8.3 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 1222 | 2.0 / 4.9 | 2.5 / 6.8 | 3.5 / 8.9 | 4.8 / 12.2 | 6.2 / 14.6 | 8.7 / 19.1 | 11.7 / 24.8 | 12.5 / 24.5 |
| 0-10 | (4) tile rot + oracle s | 1222 | 1.8 / 4.8 | 2.4 / 6.7 | 3.2 / 8.7 | 4.2 / 11.4 | 4.6 / 12.0 | 5.5 / 12.5 | 7.6 / 15.0 | 8.5 / 16.6 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 240 | 1.6 / 4.5 | 2.8 / 7.5 | 4.4 / 11.5 | 7.3 / 17.4 | 10.6 / 21.6 | 11.7 / 31.2 | 10.4 / 15.7 | - |
| 10-30 | (2) SLAM rot + oracle s | 240 | 1.3 / 4.4 | 2.3 / 7.6 | 3.2 / 11.5 | 4.5 / 13.3 | 6.5 / 15.9 | 6.1 / 15.2 | 7.8 / 9.9 | - |
| 10-30 | (3) tile rot + Bnet+Acheck s | 240 | 2.5 / 6.5 | 4.4 / 9.9 | 6.5 / 14.3 | 9.1 / 20.2 | 12.2 / 25.6 | 13.5 / 35.1 | 15.7 / 21.0 | - |
| 10-30 | (4) tile rot + oracle s | 240 | 2.3 / 6.4 | 4.1 / 9.9 | 6.0 / 13.7 | 7.6 / 15.8 | 10.1 / 19.3 | 9.5 / 23.4 | 14.2 / 18.5 | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

rotation [deg], median / p90:

| speed | combination | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | 1222 | 0.12 / 0.31 | 0.16 / 0.43 | 0.21 / 0.56 | 0.27 / 0.74 | 0.29 / 0.79 | 0.35 / 0.83 | 0.48 / 1.07 | 0.50 / 1.13 |
| 0-10 | (2) SLAM rot + oracle s | 1222 | 0.12 / 0.31 | 0.16 / 0.43 | 0.21 / 0.56 | 0.27 / 0.74 | 0.29 / 0.79 | 0.35 / 0.83 | 0.48 / 1.07 | 0.50 / 1.13 |
| 0-10 | (3) tile rot + Bnet+Acheck s | 1222 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 0-10 | (4) tile rot + oracle s | 1222 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | 240 | 0.14 / 0.41 | 0.25 / 0.61 | 0.37 / 0.87 | 0.44 / 1.09 | 0.55 / 1.17 | 0.59 / 1.73 | 0.91 / 1.13 | - |
| 10-30 | (2) SLAM rot + oracle s | 240 | 0.14 / 0.41 | 0.25 / 0.61 | 0.37 / 0.87 | 0.44 / 1.09 | 0.55 / 1.17 | 0.59 / 1.73 | 0.91 / 1.13 | - |
| 10-30 | (3) tile rot + Bnet+Acheck s | 240 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - |
| 10-30 | (4) tile rot + oracle s | 240 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | - |
| 30+ | (1) SLAM rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (2) SLAM rot + oracle s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (3) tile rot + Bnet+Acheck s | 0 | - | - | - | - | - | - | - | - |
| 30+ | (4) tile rot + oracle s | 0 | - | - | - | - | - | - | - | - |

chunk-length label error, mean / median over anchors:

| speed | combination | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| 0-10 | (1) SLAM rot + Bnet+Acheck s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 4.0 / 3.4 | 5.6 / 4.7 | 6.7 / 5.6 | 7.3 / 6.1 |
| 0-10 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.35 / 0.28 | 0.41 / 0.34 | 0.45 / 0.38 | 0.49 / 0.43 |
| 0-10 | (2) SLAM rot + oracle s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (2) SLAM rot + oracle s | position [mm], mean / median | 3.1 / 2.5 | 3.6 / 3.1 | 4.0 / 3.5 | 4.3 / 3.8 |
| 0-10 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.35 / 0.28 | 0.41 / 0.34 | 0.45 / 0.38 | 0.49 / 0.43 |
| 0-10 | (3) tile rot + Bnet+Acheck s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 5.8 / 4.8 | 7.4 / 6.4 | 8.7 / 7.7 | 9.4 / 8.3 |
| 0-10 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.03 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 0-10 | (4) tile rot + oracle s | anchors | 1222 | 1222 | 1222 | 1222 |
| 0-10 | (4) tile rot + oracle s | position [mm], mean / median | 5.2 / 4.2 | 5.9 / 5.0 | 6.5 / 5.6 | 7.0 / 6.2 |
| 0-10 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.03 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 | 0.05 / 0.00 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | position [mm], mean / median | 7.6 / 6.8 | 9.1 / 8.1 | 9.4 / 8.4 | 9.4 / 8.4 |
| 10-30 | (1) SLAM rot + Bnet+Acheck s | rotation [deg], mean / median | 0.57 / 0.45 | 0.64 / 0.53 | 0.67 / 0.54 | 0.67 / 0.54 |
| 10-30 | (2) SLAM rot + oracle s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (2) SLAM rot + oracle s | position [mm], mean / median | 5.7 / 4.8 | 6.5 / 5.6 | 6.8 / 5.8 | 6.8 / 5.8 |
| 10-30 | (2) SLAM rot + oracle s | rotation [deg], mean / median | 0.57 / 0.45 | 0.64 / 0.53 | 0.67 / 0.54 | 0.67 / 0.54 |
| 10-30 | (3) tile rot + Bnet+Acheck s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (3) tile rot + Bnet+Acheck s | position [mm], mean / median | 9.7 / 8.9 | 11.4 / 10.2 | 11.9 / 10.4 | 11.9 / 10.6 |
| 10-30 | (3) tile rot + Bnet+Acheck s | rotation [deg], mean / median | 0.10 / 0.00 | 0.11 / 0.00 | 0.12 / 0.00 | 0.11 / 0.00 |
| 10-30 | (4) tile rot + oracle s | anchors | 240 | 240 | 240 | 240 |
| 10-30 | (4) tile rot + oracle s | position [mm], mean / median | 8.1 / 7.1 | 9.3 / 8.5 | 9.7 / 8.7 | 9.8 / 8.7 |
| 10-30 | (4) tile rot + oracle s | rotation [deg], mean / median | 0.10 / 0.00 | 0.11 / 0.00 | 0.12 / 0.00 | 0.11 / 0.00 |
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

## Error decomposition, E3_da3m: rotation and translation parts of the SLAM head-motion error at the tool

In cam_t the tool after the head motion is at R b + t (b = cam_t+dt->tool_t+dt), so the SLAM label position error is about the length of dR b + dt: rotation part dR b = (R_slam - R_tile) b, translation part dt = s t_slam - t_tile (lengths in the table). The tile-rotation combinations keep only dt; a cosine near -1 means the two parts cancel at the tool's depth, so replacing the rotation alone makes the labels worse.

| quantity | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|
| rotation part dR b [mm], median / p90 (scale-free) | 1.1 / 2.8 | 1.5 / 4.2 | 2.0 / 5.6 | 2.5 / 6.6 | 2.7 / 7.5 | 3.3 / 7.5 | 4.3 / 9.3 | 4.7 / 10.7 |
| translation part dt [mm], Bnet+Acheck s, median / p90 | 2.0 / 5.2 | 2.8 / 7.5 | 3.8 / 10.2 | 5.3 / 13.0 | 6.8 / 17.3 | 9.1 / 19.4 | 12.0 / 24.2 | 12.5 / 24.5 |
| translation part dt [mm], oracle s, median / p90 | 2.0 / 5.1 | 2.6 / 7.4 | 3.5 / 9.8 | 4.5 / 12.1 | 5.1 / 13.7 | 5.7 / 13.4 | 7.7 / 16.1 | 8.5 / 16.6 |
| cos(dR b, dt), Bnet+Acheck s, median | -0.91 | -0.89 | -0.86 | -0.81 | -0.71 | -0.63 | -0.67 | -0.84 |
| cos(dR b, dt), oracle s, median | -0.93 | -0.92 | -0.91 | -0.90 | -0.89 | -0.88 | -0.91 | -0.96 |

Checks: (1) SLAM rot + Bnet+Acheck s vs `labels_E3_da3m@Bnet+Acheck.json`: identical (anchors, every step and chunk number); (2) SLAM rot + oracle s vs `labels_E3_da3m.json`: identical (anchors, every step and chunk number); cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (configured scale, 72521 pairs): max |position difference| 6.7e-13 mm, max |R difference| 2.2e-15; cam_t->tool_t decomposition with the SLAM rotation vs the label chunk (oracle scale, 72521 pairs): max |position difference| 5.6e-13 mm, max |R difference| 2.2e-15.

## Segments

| segment | configured s | oracle s | flagged | kept: tiles / configured / oracle | anchors configured / oracle |
|---|---|---|---|---|---|
| ep01 | 0.7384 | 0.6027 |  | y/y/y | 107 / 107 |
| ep02 | 0.5875 | 0.6106 |  | n/y/y | 0 / 0 |
| ep03 | 0.6403 | 0.5903 |  | y/y/y | 104 / 104 |
| ep04 | 0.8035 | 0.7955 |  | y/y/y | 112 / 112 |
| ep05 | 0.5786 | 0.5539 |  | y/y/y | 76 / 76 |
| ep06 | 0.9110 | 0.8710 | yes | y/y/y | 77 / 77 |
| ep07 | 0.5201 | 0.4935 |  | y/y/y | 68 / 68 |
| ep08 | 0.6811 | 0.6765 |  | n/y/y | 0 / 0 |
| ep09 | 0.6966 | 0.6154 |  | y/y/y | 93 / 93 |
| ep10 | 0.8478 | 0.7536 |  | n/y/y | 0 / 0 |
| ep11 | 0.7760 | 0.7193 |  | y/y/y | 76 / 76 |
| ep12 | 0.9294 | 0.8195 |  | y/y/y | 89 / 89 |
| ep13 | 0.8414 | 0.7955 |  | n/y/y | 0 / 0 |
| ep14 | 0.7032 | 0.6767 | yes | y/y/y | 69 / 69 |
| ep15 | 0.2037 | 0.1797 |  | y/y/y | 60 / 60 |
| ep16 | 1.5665 | 1.6110 |  | y/y/y | 89 / 89 |
| ep17 | 0.6860 | 0.6244 |  | y/y/y | 81 / 81 |
| ep18 | 0.1154 | 0.1207 |  | n/y/y | 0 / 0 |
| ep19 | 1.2031 | 1.2640 | yes | y/y/y | 62 / 62 |
| ep20 | 0.2837 | 0.2615 |  | n/y/y | 0 / 0 |
| ep21 | 0.3892 | 0.3581 |  | y/y/y | 78 / 78 |
| ep22 | 0.5220 | 0.5340 |  | y/y/y | 77 / 77 |
| ep23 | 0.9338 | 0.9374 | yes | y/y/y | 111 / 111 |
| ep24 | 0.8526 | 0.8512 |  | n/y/y | 0 / 0 |
| ep25 | 0.6512 | 0.5986 |  | y/y/y | 99 / 99 |
| ep26 | 4.0639 | 4.3276 |  | n/y/y | 0 / 0 |
| ep27 | 0.9605 | 0.9231 |  | y/y/y | 115 / 115 |
| ep28 | 1.2011 | 1.1035 |  | n/y/y | 0 / 0 |
| ep29 | 0.8369 | 0.8250 |  | n/y/y | 0 / 0 |
