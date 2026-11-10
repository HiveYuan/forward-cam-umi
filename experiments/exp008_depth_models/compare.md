# exp008: depth networks compared (post-hoc, `compare.py`)

## Scale error vs the tile oracle, 22 episodes with >= 3 tile-visible keyframes

| network | Bsession \|err\| med / p90 | bias | spread (sd log) | >10% / >20% | B \|err\| med / p90 | B spread | Bnet (no ball) \|err\| med / p90 | Bnet bias | Bnet spread | k_session |
|---|---|---|---|---|---|---|---|---|---|---|
| DA2 metric indoor (no K) | 6.9 / 11.4 | -5.5 | 6.6 | 4 / 0 | 5.7 / 20.0 | 10.0 | 66.9 / 77.3 | +66.9 | 6.6 | 0.566 |
| UniDepth V2 + K | 9.4 / 12.6 | -9.4 | 5.6 | 6 / 0 | 9.1 / 19.1 | 8.2 | 6.5 / 16.1 | +6.5 | 5.6 | 0.851 |
| UniDepth V2, own camera | 8.8 / 11.9 | -8.6 | 6.1 | 5 / 0 | 8.3 / 19.9 | 8.5 | 4.6 / 16.3 | +4.6 | 6.1 | 0.873 |
| Metric3D v2 + K | 6.7 / 11.4 | -6.2 | 5.3 | 4 / 0 | 9.1 / 19.6 | 10.4 | 9.0 / 13.9 | +9.0 | 5.3 | 0.861 |
| DA3 metric + K | 17.6 / 21.0 | -17.6 | 4.9 | 20 / 7 | 15.8 / 26.4 | 10.7 | 3.1 / 6.9 | +0.8 | 4.9 | 0.817 |
| MoGe-2 (fov from K) | 18.8 / 24.4 | -18.8 | 6.2 | 21 / 8 | 17.8 / 29.8 | 12.1 | 4.2 / 10.2 | +3.2 | 6.2 | 0.787 |
| Depth Pro + K | 14.6 / 23.1 | -14.6 | 7.5 | 17 / 7 | 14.3 / 28.2 | 11.9 | 10.2 / 19.5 | +10.2 | 7.5 | 0.775 |
| Depth Pro, own FOV | 15.8 / 22.9 | -15.8 | 9.0 | 18 / 5 | 16.7 / 31.9 | 14.5 | 16.8 / 26.1 | +16.8 | 9.0 | 0.722 |

## Scale error vs the tile oracle, all 28 episodes with tile GT

| network | Bsession \|err\| med / p90 | bias | spread (sd log) | >10% / >20% | B \|err\| med / p90 | B spread | Bnet (no ball) \|err\| med / p90 | Bnet bias | Bnet spread | k_session |
|---|---|---|---|---|---|---|---|---|---|---|
| DA2 metric indoor (no K) | 7.8 / 17.4 | -7.3 | 9.3 | 8 / 1 | 6.6 / 21.7 | 12.1 | 63.7 / 76.9 | +63.7 | 9.3 | 0.566 |
| UniDepth V2 + K | 9.4 / 13.8 | -9.4 | 7.5 | 9 / 1 | 9.1 / 21.3 | 10.8 | 6.7 / 17.0 | +6.5 | 7.5 | 0.851 |
| UniDepth V2, own camera | 8.8 / 13.3 | -8.6 | 7.9 | 8 / 1 | 8.3 / 21.5 | 11.1 | 5.9 / 17.7 | +4.6 | 7.9 | 0.873 |
| Metric3D v2 + K | 6.2 / 11.7 | -5.7 | 7.6 | 5 / 1 | 8.2 / 21.1 | 12.4 | 10.0 / 14.1 | +9.5 | 7.6 | 0.861 |
| DA3 metric + K | 18.4 / 23.3 | -18.4 | 7.1 | 26 / 11 | 15.8 / 32.8 | 12.3 | 3.1 / 9.4 | -0.1 | 7.1 | 0.817 |
| MoGe-2 (fov from K) | 19.7 / 25.6 | -19.7 | 9.1 | 27 / 13 | 17.8 / 31.4 | 12.7 | 4.2 / 11.0 | +2.0 | 9.1 | 0.787 |
| Depth Pro + K | 15.8 / 23.9 | -15.8 | 9.9 | 22 / 10 | 15.4 / 30.0 | 12.5 | 10.2 / 20.0 | +8.7 | 9.9 | 0.775 |
| Depth Pro, own FOV | 16.4 / 23.6 | -16.4 | 10.6 | 23 / 7 | 17.4 / 30.3 | 13.7 | 16.7 / 26.5 | +15.8 | 10.6 | 0.722 |

## Labels with Bsession (position error, mm; 989 anchors in exp007)

| network | 1 s median / p90 | 2 s median / p90 | chunk H=30 mean | chunk H=100 mean |
|---|---|---|---|---|
| DA2 metric indoor (no K) | 4.5 / 15.0 | 6.2 / 18.1 | 7.0 | 10.1 |
| UniDepth V2 + K | 4.9 / 18.6 | 6.7 / 27.0 | 7.5 | 10.8 |
| UniDepth V2, own camera | 4.7 / 16.9 | 6.5 / 24.3 | 7.2 | 10.4 |
| Metric3D v2 + K | 4.6 / 15.8 | 6.1 / 20.2 | 7.0 | 9.9 |
| DA3 metric + K | 6.6 / 25.9 | 9.1 / 42.5 | 9.6 | 14.0 |
| MoGe-2 (fov from K) | 6.4 / 26.6 | 8.8 / 41.6 | 9.6 | 13.8 |
| Depth Pro + K | 5.7 / 22.9 | 7.9 / 34.2 | 8.7 | 12.6 |
| Depth Pro, own FOV | 6.1 / 24.5 | 8.4 / 41.7 | 9.2 | 13.7 |
| oracle scale | 3.9 / 13.9 | | | 9.1 |

## Without SLAM: true / network depth on tile cells

| network | pooled median (1 = metric) | spread over episodes (sd log; 22) | depth slope (log-log, median) | shape \|err\| median | 0.35-0.55 / 0.55-0.7 / 0.7-0.9 / 0.9-1.2 / 1.2-1.6 m |
|---|---|---|---|---|---|
| DA2 metric indoor (no K) | 0.586 | 10.3 (10.4) | +0.351 | 1.3 | 0.439 / 0.506 / 0.574 / 0.636 / 0.696 |
| UniDepth V2 + K | 0.925 | 3.6 (3.2) | +0.070 | 0.5 | 0.849 / 0.906 / 0.920 / 0.946 / 0.967 |
| UniDepth V2, own camera | 0.944 | 3.8 (3.6) | +0.090 | 0.5 | 0.880 / 0.919 / 0.943 / 0.956 / 0.985 |
| Metric3D v2 + K | 0.918 | 6.0 (5.7) | +0.263 | 0.9 | 0.761 / 0.855 / 0.899 / 0.970 / 1.026 |
| DA3 metric + K | 0.957 | 8.3 (7.5) | +0.283 | 0.9 | 0.965 / 0.923 / 0.928 / 1.021 / 1.086 |
| MoGe-2 (fov from K) | 0.919 | 8.1 (8.4) | +0.284 | 0.4 | 0.741 / 0.853 / 0.906 / 0.954 / 1.052 |
| Depth Pro + K | 0.905 | 9.6 (8.3) | +0.010 | 0.9 | 0.870 / 0.916 / 0.902 / 0.908 / 0.812 |
| Depth Pro, own FOV | 0.863 | 9.2 (8.0) | +0.080 | 0.9 | 0.754 / 0.833 / 0.861 / 0.886 / 0.842 |

## Own focal estimates (networks run without K)

K's fx = 598.3 px.

| network | keyframes | median | p10 - p90 | sd log |
|---|---|---|---|---|
| UniDepth V2 + K | 384 | 576.3 | 548.4 - 639.4 | 6.9 |
| UniDepth V2, own camera | 384 | 576.3 | 548.4 - 639.4 | 6.9 |
| Depth Pro + K | 384 | 646.5 | 561.6 - 748.9 | 11.6 |
| Depth Pro, own FOV | 384 | 646.5 | 561.6 - 748.9 | 11.6 |

## Ball correction vs what each episode needed (sd of log over episodes)

| network | own k (ball), 22 | k_need, 22 | k_need median, 22 |
|---|---|---|---|
| DA2 metric indoor (no K) | 10.1 | 6.6 | 0.599 |
| UniDepth V2 + K | 5.8 | 5.6 | 0.939 |
| UniDepth V2, own camera | 6.2 | 6.1 | 0.956 |
| Metric3D v2 + K | 7.8 | 5.3 | 0.918 |
| DA3 metric + K | 8.6 | 4.9 | 0.992 |
| MoGe-2 (fov from K) | 9.3 | 6.2 | 0.969 |
| Depth Pro + K | 11.4 | 7.5 | 0.907 |
| Depth Pro, own FOV | 10.9 | 9.0 | 0.856 |
