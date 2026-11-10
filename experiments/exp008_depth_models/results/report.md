# exp008_depth_models: report (variant main)

30 segments. Runs: E1, E3_da2, E3_uniK, E3_uni, E3_m3d, E3_da3m, E3_moge, E3_dproK, E3_dpro (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | - / - | - / - | - / - | - / - | - / - |
| E3_da2 | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_uniK | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_uni | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_m3d | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_da3m | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_moge | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_dproK | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |
| E3_dpro | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |

n [frame pairs]:

- static, E3_da2, E3_uniK, E3_uni, E3_m3d, E3_da3m, E3_moge, E3_dproK, E3_dpro: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E1: 0.08 s: -, 0.5 s: -, 1.0 s: -, 2.0 s: -, 6.67 s: -

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E3_da2 | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_da2 | Bsession+Bcheck+Bnetcheck | 2.46 / 10.02 | 5.68 / 24.35 | 8.34 / 35.86 | 11.82 / 46.05 | 11.61 / 24.13 |
| E3_uniK | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_uniK | Bsession+Bcheck+Bnetcheck | 2.46 / 9.82 | 5.69 / 25.45 | 8.59 / 40.02 | 12.78 / 57.07 | 11.75 / 26.97 |
| E3_uni | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_uni | Bsession+Bcheck+Bnetcheck | 2.46 / 9.80 | 5.65 / 25.06 | 8.46 / 39.98 | 12.50 / 54.44 | 11.58 / 24.02 |
| E3_m3d | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_m3d | Bsession+Bcheck+Bnetcheck | 2.45 / 9.86 | 5.60 / 24.70 | 8.26 / 38.57 | 11.31 / 50.54 | 9.11 / 18.94 |
| E3_da3m | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_da3m | Bsession+Bcheck+Bnetcheck | 2.47 / 9.71 | 6.43 / 28.26 | 9.91 / 48.26 | 14.63 / 76.27 | 14.62 / 49.89 |
| E3_moge | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_moge | Bsession+Bcheck+Bnetcheck | 2.47 / 9.70 | 6.49 / 28.07 | 10.20 / 48.11 | 15.06 / 74.54 | 13.33 / 48.27 |
| E3_dproK | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_dproK | Bsession+Bcheck+Bnetcheck | 2.47 / 9.89 | 6.27 / 27.07 | 9.68 / 43.61 | 13.76 / 63.35 | 13.07 / 35.17 |
| E3_dpro | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3_dpro | Bsession+Bcheck+Bnetcheck | 2.47 / 9.77 | 6.30 / 30.02 | 10.14 / 53.73 | 15.04 / 82.59 | 12.06 / 58.59 |

n [frame pairs]:

- E3_da2 oracle (tiles), E3_uniK oracle (tiles), E3_uni oracle (tiles), E3_m3d oracle (tiles), E3_da3m oracle (tiles), E3_moge oracle (tiles), E3_dproK oracle (tiles), E3_dpro oracle (tiles): 0.08 s: 2371, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E3_da2 Bsession+Bcheck+Bnetcheck, E3_uniK Bsession+Bcheck+Bnetcheck, E3_uni Bsession+Bcheck+Bnetcheck, E3_m3d Bsession+Bcheck+Bnetcheck, E3_da3m Bsession+Bcheck+Bnetcheck, E3_moge Bsession+Bcheck+Bnetcheck, E3_dproK Bsession+Bcheck+Bnetcheck, E3_dpro Bsession+Bcheck+Bnetcheck: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | - | 14.2 | 43 | 100% |
| E3_da2 | 0.17% | 12.8 | 47 | 86% |
| E3_uniK | 0.17% | 12.8 | 47 | 86% |
| E3_uni | 0.17% | 12.8 | 47 | 86% |
| E3_m3d | 0.17% | 12.8 | 47 | 86% |
| E3_da3m | 0.17% | 12.8 | 47 | 86% |
| E3_moge | 0.17% | 12.8 | 47 | 86% |
| E3_dproK | 0.17% | 12.8 | 47 | 86% |
| E3_dpro | 0.17% | 12.8 | 47 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3_da2 | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 7.8% | 17.4% | -7.3% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_da2 | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_da2 | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 7.8% | 17.4% | -7.3% |  |
| E3_da2 | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 6.6% | 21.7% | -5.2% |  |
| E3_da2 | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 63.7% | 76.9% | 63.7% |  |
| E3_uniK | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 9.4% | 13.8% | -9.4% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_uniK | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_uniK | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 9.4% | 13.8% | -9.4% |  |
| E3_uniK | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 9.1% | 21.3% | -9.1% |  |
| E3_uniK | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 6.7% | 17.0% | 6.5% |  |
| E3_uni | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 8.8% | 13.3% | -8.6% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_uni | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_uni | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 8.8% | 13.3% | -8.6% |  |
| E3_uni | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 8.3% | 21.5% | -8.3% |  |
| E3_uni | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 5.9% | 17.7% | 4.6% |  |
| E3_m3d | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 6.2% | 11.7% | -5.7% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_m3d | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_m3d | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 6.2% | 11.7% | -5.7% |  |
| E3_m3d | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 8.2% | 21.1% | -7.4% |  |
| E3_m3d | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 10.0% | 14.1% | 9.5% |  |
| E3_da3m | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 18.4% | 23.3% | -18.4% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_da3m | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_da3m | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 18.4% | 23.3% | -18.4% |  |
| E3_da3m | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 15.8% | 32.8% | -15.8% |  |
| E3_da3m | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 3.1% | 9.4% | -0.1% |  |
| E3_moge | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 19.7% | 25.6% | -19.7% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_moge | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_moge | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 19.7% | 25.6% | -19.7% |  |
| E3_moge | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 17.8% | 31.4% | -17.8% |  |
| E3_moge | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 4.2% | 11.0% | 2.0% |  |
| E3_dproK | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 15.8% | 23.9% | -15.8% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_dproK | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_dproK | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 15.8% | 23.9% | -15.8% |  |
| E3_dproK | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 15.4% | 30.0% | -15.4% |  |
| E3_dproK | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 10.2% | 20.0% | 8.7% |  |
| E3_dpro | Bsession+Bcheck+Bnetcheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 16.4% | 23.6% | -16.4% | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 |
| E3_dpro | Bsession+Bcheck+Bnetcheck, without flagged | 0/30 | 0 | - | - | - |  |
| E3_dpro | Bsession+Bcheck+Bnetcheck, method Bsession (primary) | 30/30 | 28 | 16.4% | 23.6% | -16.4% |  |
| E3_dpro | Bsession+Bcheck+Bnetcheck, method B (check) | 30/30 | 28 | 17.4% | 30.3% | -17.4% |  |
| E3_dpro | Bsession+Bcheck+Bnetcheck, method Bnet (check) | 30/30 | 28 | 16.7% | 26.5% | 15.8% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_da2 | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.5 | 1.6 / 5.7 | 2.3 / 7.7 | 3.3 / 11.3 | 4.5 / 15.0 | 6.2 / 18.1 | 6.6 / 22.3 | 7.6 / 17.2 |
| E3_uniK | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_uniK | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.6 | 1.6 / 5.9 | 2.4 / 8.3 | 3.4 / 13.0 | 4.9 / 18.6 | 6.7 / 27.0 | 6.8 / 27.6 | 7.9 / 25.4 |
| E3_uni | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_uni | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.5 | 1.6 / 5.8 | 2.4 / 8.1 | 3.3 / 12.8 | 4.7 / 16.9 | 6.5 / 24.3 | 6.7 / 24.9 | 7.0 / 22.3 |
| E3_m3d | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_m3d | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.5 | 1.6 / 5.6 | 2.4 / 7.8 | 3.3 / 11.9 | 4.6 / 15.8 | 6.1 / 20.2 | 6.7 / 22.6 | 6.2 / 14.9 |
| E3_da3m | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_da3m | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.7 | 1.8 / 6.3 | 2.7 / 10.0 | 4.2 / 16.3 | 6.6 / 25.9 | 9.1 / 42.5 | 9.0 / 45.6 | 11.8 / 49.6 |
| E3_moge | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_moge | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.7 | 1.8 / 6.3 | 2.6 / 10.0 | 4.1 / 16.0 | 6.4 / 26.6 | 8.8 / 41.6 | 9.4 / 43.9 | 10.4 / 47.9 |
| E3_dproK | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_dproK | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.7 | 1.8 / 6.3 | 2.5 / 9.2 | 3.8 / 14.6 | 5.7 / 22.9 | 7.9 / 34.2 | 8.2 / 37.4 | 10.1 / 34.1 |
| E3_dpro | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3_dpro | Bsession+Bcheck+Bnetcheck | 989 | 1.2 / 3.9 | 1.8 / 6.5 | 2.6 / 9.7 | 3.9 / 14.8 | 6.1 / 24.5 | 8.4 / 41.7 | 8.0 / 53.9 | 8.4 / 58.7 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90 (rotation is scale-free: same for every scale)

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3_da2 | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_uniK | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_uni | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_m3d | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_da3m | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_moge | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_dproK | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |
| E3_dpro | every scale | 989 | 0.14 / 0.44 | 0.20 / 0.61 | 0.27 / 0.83 | 0.36 / 1.18 | 0.50 / 1.59 | 0.65 / 1.99 | 0.56 / 2.41 | 0.57 / 1.16 |

n [anchors counting the step]: 0.07 s: 976, 0.13 s: 963, 0.27 s: 937, 0.53 s: 890, 1.00 s: 814, 2.00 s: 676, 4.00 s: 398, 6.67 s: 55

## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, then mean / median over anchors

| run | quantity | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|
| E3_da2 | anchors | 978 | 979 | 979 | 979 |
| E3_da2 | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_da2 | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_da2 | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 4.9 / 3.3 | 7.0 / 4.6 | 8.6 / 5.9 | 10.1 / 6.6 |
| E3_da2 | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_uniK | anchors | 978 | 979 | 979 | 979 |
| E3_uniK | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_uniK | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_uniK | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 5.2 / 3.4 | 7.5 / 4.9 | 9.3 / 6.1 | 10.8 / 7.5 |
| E3_uniK | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_uni | anchors | 978 | 979 | 979 | 979 |
| E3_uni | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_uni | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_uni | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 5.1 / 3.3 | 7.2 / 4.7 | 8.9 / 6.0 | 10.4 / 7.3 |
| E3_uni | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_m3d | anchors | 978 | 979 | 979 | 979 |
| E3_m3d | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_m3d | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_m3d | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 4.9 / 3.4 | 7.0 / 4.5 | 8.5 / 5.5 | 9.9 / 6.4 |
| E3_m3d | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_da3m | anchors | 978 | 979 | 979 | 979 |
| E3_da3m | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_da3m | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_da3m | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 6.3 / 4.2 | 9.6 / 6.2 | 12.0 / 7.4 | 14.0 / 9.5 |
| E3_da3m | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_moge | anchors | 978 | 979 | 979 | 979 |
| E3_moge | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_moge | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_moge | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 6.3 / 4.1 | 9.6 / 6.1 | 12.0 / 7.3 | 13.8 / 9.1 |
| E3_moge | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_dproK | anchors | 978 | 979 | 979 | 979 |
| E3_dproK | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_dproK | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_dproK | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 5.8 / 3.7 | 8.7 / 5.5 | 10.8 / 6.7 | 12.6 / 8.3 |
| E3_dproK | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |
| E3_dpro | anchors | 978 | 979 | 979 | 979 |
| E3_dpro | counted steps per anchor, median | 15 | 30 | 46 | 49 |
| E3_dpro | position [mm], oracle (tiles), mean / median | 4.7 / 3.2 | 6.4 / 4.2 | 7.7 / 4.9 | 9.1 / 5.5 |
| E3_dpro | position [mm], Bsession+Bcheck+Bnetcheck, mean / median | 6.1 / 4.0 | 9.2 / 6.0 | 11.5 / 7.3 | 13.7 / 8.2 |
| E3_dpro | rotation [deg], every scale, mean / median | 0.57 / 0.39 | 0.78 / 0.51 | 0.95 / 0.58 | 1.11 / 0.59 |

(rotation is scale-free: same for every scale)

Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are truncated chunks: the counted-steps row gives per H the median number of steps j <= H an anchor counts (e.g. E3_da2, H=100: 49 of 100).

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 40 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles, dt 0.5 s | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles, dt 2.0 s | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes between the ends | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

## Comparison with other experiments

- exp007_v2_session_scale: `exp007_v2_session_scale/results/metrics.json`
- runs only in exp007_v2_session_scale (not shown): E3

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 |
|---|---|---|---|---|---|---|---|
| static | 0.08 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | - | - | - | - | - | - |
| E1 | 0.5 | - | - | - | - | - | - |
| E1 | 1.0 | - | - | - | - | - | - |
| E1 | 2.0 | - | - | - | - | - | - |
| E1 | 6.67 | - | - | - | - | - | - |
| E3_da2 | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_da2 | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_da2 | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_da2 | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_da2 | 6.67 | 88 | 0.58 | 1.26 | - | - | - |
| E3_uniK | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_uniK | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_uniK | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_uniK | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_uniK | 6.67 | 88 | 0.58 | 1.26 | - | - | - |
| E3_uni | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_uni | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_uni | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_uni | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_uni | 6.67 | 88 | 0.58 | 1.26 | - | - | - |
| E3_m3d | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_m3d | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_m3d | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_m3d | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_m3d | 6.67 | 88 | 0.58 | 1.26 | - | - | - |
| E3_da3m | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_da3m | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_da3m | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_da3m | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_da3m | 6.67 | 88 | 0.58 | 1.26 | - | - | - |
| E3_moge | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_moge | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_moge | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_moge | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_moge | 6.67 | 88 | 0.58 | 1.26 | - | - | - |
| E3_dproK | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_dproK | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_dproK | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_dproK | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_dproK | 6.67 | 88 | 0.58 | 1.26 | - | - | - |
| E3_dpro | 0.08 | 2380 | 0.16 | 0.64 | - | - | - |
| E3_dpro | 0.5 | 1931 | 0.36 | 1.49 | - | - | - |
| E3_dpro | 1.0 | 1612 | 0.52 | 2.25 | - | - | - |
| E3_dpro | 2.0 | 1248 | 0.65 | 2.60 | - | - | - |
| E3_dpro | 6.67 | 88 | 0.58 | 1.26 | - | - | - |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p95 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p95 |
|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | - | - | - | - | - | - |
| E1 | oracle | 0.5 | - | - | - | - | - | - |
| E1 | oracle | 1.0 | - | - | - | - | - | - |
| E1 | oracle | 2.0 | - | - | - | - | - | - |
| E1 | oracle | 6.67 | - | - | - | - | - | - |
| E3_da2 | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_da2 | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_da2 | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_da2 | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_da2 | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_da2 | configured | 0.08 | 2380 | 2.46 | 10.02 | - | - | - |
| E3_da2 | configured | 0.5 | 1931 | 5.68 | 24.35 | - | - | - |
| E3_da2 | configured | 1.0 | 1612 | 8.34 | 35.86 | - | - | - |
| E3_da2 | configured | 2.0 | 1248 | 11.82 | 46.05 | - | - | - |
| E3_da2 | configured | 6.67 | 88 | 11.61 | 24.13 | - | - | - |
| E3_uniK | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_uniK | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_uniK | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_uniK | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_uniK | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_uniK | configured | 0.08 | 2380 | 2.46 | 9.82 | - | - | - |
| E3_uniK | configured | 0.5 | 1931 | 5.69 | 25.45 | - | - | - |
| E3_uniK | configured | 1.0 | 1612 | 8.59 | 40.02 | - | - | - |
| E3_uniK | configured | 2.0 | 1248 | 12.78 | 57.07 | - | - | - |
| E3_uniK | configured | 6.67 | 88 | 11.75 | 26.97 | - | - | - |
| E3_uni | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_uni | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_uni | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_uni | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_uni | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_uni | configured | 0.08 | 2380 | 2.46 | 9.80 | - | - | - |
| E3_uni | configured | 0.5 | 1931 | 5.65 | 25.06 | - | - | - |
| E3_uni | configured | 1.0 | 1612 | 8.46 | 39.98 | - | - | - |
| E3_uni | configured | 2.0 | 1248 | 12.50 | 54.44 | - | - | - |
| E3_uni | configured | 6.67 | 88 | 11.58 | 24.02 | - | - | - |
| E3_m3d | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_m3d | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_m3d | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_m3d | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_m3d | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_m3d | configured | 0.08 | 2380 | 2.45 | 9.86 | - | - | - |
| E3_m3d | configured | 0.5 | 1931 | 5.60 | 24.70 | - | - | - |
| E3_m3d | configured | 1.0 | 1612 | 8.26 | 38.57 | - | - | - |
| E3_m3d | configured | 2.0 | 1248 | 11.31 | 50.54 | - | - | - |
| E3_m3d | configured | 6.67 | 88 | 9.11 | 18.94 | - | - | - |
| E3_da3m | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_da3m | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_da3m | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_da3m | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_da3m | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_da3m | configured | 0.08 | 2380 | 2.47 | 9.71 | - | - | - |
| E3_da3m | configured | 0.5 | 1931 | 6.43 | 28.26 | - | - | - |
| E3_da3m | configured | 1.0 | 1612 | 9.91 | 48.26 | - | - | - |
| E3_da3m | configured | 2.0 | 1248 | 14.63 | 76.27 | - | - | - |
| E3_da3m | configured | 6.67 | 88 | 14.62 | 49.89 | - | - | - |
| E3_moge | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_moge | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_moge | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_moge | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_moge | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_moge | configured | 0.08 | 2380 | 2.47 | 9.70 | - | - | - |
| E3_moge | configured | 0.5 | 1931 | 6.49 | 28.07 | - | - | - |
| E3_moge | configured | 1.0 | 1612 | 10.20 | 48.11 | - | - | - |
| E3_moge | configured | 2.0 | 1248 | 15.06 | 74.54 | - | - | - |
| E3_moge | configured | 6.67 | 88 | 13.33 | 48.27 | - | - | - |
| E3_dproK | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_dproK | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_dproK | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_dproK | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_dproK | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_dproK | configured | 0.08 | 2380 | 2.47 | 9.89 | - | - | - |
| E3_dproK | configured | 0.5 | 1931 | 6.27 | 27.07 | - | - | - |
| E3_dproK | configured | 1.0 | 1612 | 9.68 | 43.61 | - | - | - |
| E3_dproK | configured | 2.0 | 1248 | 13.76 | 63.35 | - | - | - |
| E3_dproK | configured | 6.67 | 88 | 13.07 | 35.17 | - | - | - |
| E3_dpro | oracle | 0.08 | 2371 | 2.49 | 10.13 | - | - | - |
| E3_dpro | oracle | 0.5 | 1931 | 5.47 | 24.24 | - | - | - |
| E3_dpro | oracle | 1.0 | 1612 | 7.46 | 36.49 | - | - | - |
| E3_dpro | oracle | 2.0 | 1248 | 9.87 | 46.80 | - | - | - |
| E3_dpro | oracle | 6.67 | 88 | 10.15 | 16.47 | - | - | - |
| E3_dpro | configured | 0.08 | 2380 | 2.47 | 9.77 | - | - | - |
| E3_dpro | configured | 0.5 | 1931 | 6.30 | 30.02 | - | - | - |
| E3_dpro | configured | 1.0 | 1612 | 10.14 | 53.73 | - | - | - |
| E3_dpro | configured | 2.0 | 1248 | 15.04 | 82.59 | - | - | - |
| E3_dpro | configured | 6.67 | 88 | 12.06 | 58.59 | - | - | - |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp008_depth_models | exp007_v2_session_scale |
|---|---|---|---|
| E1 | track fail | - | - |
| E1 | keyframes / segment | 14.2 | 14.2 |
| E1 | runtime s / segment | 43 | 43 |
| E1 | valid pixels | 100% | 100% |
| E3_da2 | track fail | 0.17% | - |
| E3_da2 | keyframes / segment | 12.8 | - |
| E3_da2 | runtime s / segment | 47 | - |
| E3_da2 | valid pixels | 86% | - |
| E3_uniK | track fail | 0.17% | - |
| E3_uniK | keyframes / segment | 12.8 | - |
| E3_uniK | runtime s / segment | 47 | - |
| E3_uniK | valid pixels | 86% | - |
| E3_uni | track fail | 0.17% | - |
| E3_uni | keyframes / segment | 12.8 | - |
| E3_uni | runtime s / segment | 47 | - |
| E3_uni | valid pixels | 86% | - |
| E3_m3d | track fail | 0.17% | - |
| E3_m3d | keyframes / segment | 12.8 | - |
| E3_m3d | runtime s / segment | 47 | - |
| E3_m3d | valid pixels | 86% | - |
| E3_da3m | track fail | 0.17% | - |
| E3_da3m | keyframes / segment | 12.8 | - |
| E3_da3m | runtime s / segment | 47 | - |
| E3_da3m | valid pixels | 86% | - |
| E3_moge | track fail | 0.17% | - |
| E3_moge | keyframes / segment | 12.8 | - |
| E3_moge | runtime s / segment | 47 | - |
| E3_moge | valid pixels | 86% | - |
| E3_dproK | track fail | 0.17% | - |
| E3_dproK | keyframes / segment | 12.8 | - |
| E3_dproK | runtime s / segment | 47 | - |
| E3_dproK | valid pixels | 86% | - |
| E3_dpro | track fail | 0.17% | - |
| E3_dpro | keyframes / segment | 12.8 | - |
| E3_dpro | runtime s / segment | 47 | - |
| E3_dpro | valid pixels | 86% | - |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp008_depth_models | exp007_v2_session_scale |
|---|---|---|---|
| E3_da2 | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_da2 | segments with a scale | 30/30 | - |
| E3_da2 | compared (tile GT) | 28 | - |
| E3_da2 | abs err median | 7.8% | - |
| E3_da2 | abs err p90 | 17.4% | - |
| E3_da2 | bias (median) | -7.3% | - |
| E3_da2 | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_da2 | without flagged: abs err median / p90 | - / - | - |
| E3_da2 | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 7.8% / 17.4% / -7.3% | - |
| E3_da2 | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 6.6% / 21.7% / -5.2% | - |
| E3_da2 | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 63.7% / 76.9% / 63.7% | - |
| E3_uniK | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_uniK | segments with a scale | 30/30 | - |
| E3_uniK | compared (tile GT) | 28 | - |
| E3_uniK | abs err median | 9.4% | - |
| E3_uniK | abs err p90 | 13.8% | - |
| E3_uniK | bias (median) | -9.4% | - |
| E3_uniK | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_uniK | without flagged: abs err median / p90 | - / - | - |
| E3_uniK | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 9.4% / 13.8% / -9.4% | - |
| E3_uniK | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 9.1% / 21.3% / -9.1% | - |
| E3_uniK | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 6.7% / 17.0% / 6.5% | - |
| E3_uni | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_uni | segments with a scale | 30/30 | - |
| E3_uni | compared (tile GT) | 28 | - |
| E3_uni | abs err median | 8.8% | - |
| E3_uni | abs err p90 | 13.3% | - |
| E3_uni | bias (median) | -8.6% | - |
| E3_uni | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_uni | without flagged: abs err median / p90 | - / - | - |
| E3_uni | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 8.8% / 13.3% / -8.6% | - |
| E3_uni | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 8.3% / 21.5% / -8.3% | - |
| E3_uni | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 5.9% / 17.7% / 4.6% | - |
| E3_m3d | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_m3d | segments with a scale | 30/30 | - |
| E3_m3d | compared (tile GT) | 28 | - |
| E3_m3d | abs err median | 6.2% | - |
| E3_m3d | abs err p90 | 11.7% | - |
| E3_m3d | bias (median) | -5.7% | - |
| E3_m3d | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_m3d | without flagged: abs err median / p90 | - / - | - |
| E3_m3d | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 6.2% / 11.7% / -5.7% | - |
| E3_m3d | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 8.2% / 21.1% / -7.4% | - |
| E3_m3d | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 10.0% / 14.1% / 9.5% | - |
| E3_da3m | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_da3m | segments with a scale | 30/30 | - |
| E3_da3m | compared (tile GT) | 28 | - |
| E3_da3m | abs err median | 18.4% | - |
| E3_da3m | abs err p90 | 23.3% | - |
| E3_da3m | bias (median) | -18.4% | - |
| E3_da3m | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_da3m | without flagged: abs err median / p90 | - / - | - |
| E3_da3m | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 18.4% / 23.3% / -18.4% | - |
| E3_da3m | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 15.8% / 32.8% / -15.8% | - |
| E3_da3m | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 3.1% / 9.4% / -0.1% | - |
| E3_moge | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_moge | segments with a scale | 30/30 | - |
| E3_moge | compared (tile GT) | 28 | - |
| E3_moge | abs err median | 19.7% | - |
| E3_moge | abs err p90 | 25.6% | - |
| E3_moge | bias (median) | -19.7% | - |
| E3_moge | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_moge | without flagged: abs err median / p90 | - / - | - |
| E3_moge | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 19.7% / 25.6% / -19.7% | - |
| E3_moge | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 17.8% / 31.4% / -17.8% | - |
| E3_moge | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 4.2% / 11.0% / 2.0% | - |
| E3_dproK | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_dproK | segments with a scale | 30/30 | - |
| E3_dproK | compared (tile GT) | 28 | - |
| E3_dproK | abs err median | 15.8% | - |
| E3_dproK | abs err p90 | 23.9% | - |
| E3_dproK | bias (median) | -15.8% | - |
| E3_dproK | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_dproK | without flagged: abs err median / p90 | - / - | - |
| E3_dproK | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 15.8% / 23.9% / -15.8% | - |
| E3_dproK | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 15.4% / 30.0% / -15.4% | - |
| E3_dproK | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 10.2% / 20.0% / 8.7% | - |
| E3_dpro | scale label | Bsession+Bcheck+Bnetcheck | - |
| E3_dpro | segments with a scale | 30/30 | - |
| E3_dpro | compared (tile GT) | 28 | - |
| E3_dpro | abs err median | 16.4% | - |
| E3_dpro | abs err p90 | 23.6% | - |
| E3_dpro | bias (median) | -16.4% | - |
| E3_dpro | flagged | ep00, ep01, ep02, ep03, ep04, ep05, ep06, ep07, ep08, ep09, ep10, ep11, ep12, ep13, ep14, ep15, ep16, ep17, ep18, ep19, ep20, ep21, ep22, ep23, ep24, ep25, ep26, ep27, ep28, ep29 | - |
| E3_dpro | without flagged: abs err median / p90 | - / - | - |
| E3_dpro | method Bsession: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 16.4% / 23.6% / -16.4% | - |
| E3_dpro | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 17.4% / 30.3% / -17.4% | - |
| E3_dpro | method Bnet: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 16.7% / 26.5% / 15.8% | - |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3_da2 | oracle | anchors | 989 |  |  | - | - | - |
| E3_da2 | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_da2 | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_da2 | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_da2 | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_da2 | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_da2 | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_da2 | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_da2 | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_da2 | configured | anchors | 989 |  |  | - | - | - |
| E3_da2 | configured | 0.07 s | 976 | 1.2 | 3.5 | - | - | - |
| E3_da2 | configured | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_da2 | configured | 0.27 s | 937 | 2.3 | 7.7 | - | - | - |
| E3_da2 | configured | 0.53 s | 890 | 3.3 | 11.3 | - | - | - |
| E3_da2 | configured | 1.00 s | 814 | 4.5 | 15.0 | - | - | - |
| E3_da2 | configured | 2.00 s | 676 | 6.2 | 18.1 | - | - | - |
| E3_da2 | configured | 4.00 s | 398 | 6.6 | 22.3 | - | - | - |
| E3_da2 | configured | 6.67 s | 55 | 7.6 | 17.2 | - | - | - |
| E3_uniK | oracle | anchors | 989 |  |  | - | - | - |
| E3_uniK | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_uniK | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_uniK | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_uniK | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_uniK | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_uniK | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_uniK | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_uniK | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_uniK | configured | anchors | 989 |  |  | - | - | - |
| E3_uniK | configured | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_uniK | configured | 0.13 s | 963 | 1.6 | 5.9 | - | - | - |
| E3_uniK | configured | 0.27 s | 937 | 2.4 | 8.3 | - | - | - |
| E3_uniK | configured | 0.53 s | 890 | 3.4 | 13.0 | - | - | - |
| E3_uniK | configured | 1.00 s | 814 | 4.9 | 18.6 | - | - | - |
| E3_uniK | configured | 2.00 s | 676 | 6.7 | 27.0 | - | - | - |
| E3_uniK | configured | 4.00 s | 398 | 6.8 | 27.6 | - | - | - |
| E3_uniK | configured | 6.67 s | 55 | 7.9 | 25.4 | - | - | - |
| E3_uni | oracle | anchors | 989 |  |  | - | - | - |
| E3_uni | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_uni | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_uni | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_uni | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_uni | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_uni | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_uni | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_uni | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_uni | configured | anchors | 989 |  |  | - | - | - |
| E3_uni | configured | 0.07 s | 976 | 1.2 | 3.5 | - | - | - |
| E3_uni | configured | 0.13 s | 963 | 1.6 | 5.8 | - | - | - |
| E3_uni | configured | 0.27 s | 937 | 2.4 | 8.1 | - | - | - |
| E3_uni | configured | 0.53 s | 890 | 3.3 | 12.8 | - | - | - |
| E3_uni | configured | 1.00 s | 814 | 4.7 | 16.9 | - | - | - |
| E3_uni | configured | 2.00 s | 676 | 6.5 | 24.3 | - | - | - |
| E3_uni | configured | 4.00 s | 398 | 6.7 | 24.9 | - | - | - |
| E3_uni | configured | 6.67 s | 55 | 7.0 | 22.3 | - | - | - |
| E3_m3d | oracle | anchors | 989 |  |  | - | - | - |
| E3_m3d | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_m3d | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_m3d | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_m3d | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_m3d | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_m3d | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_m3d | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_m3d | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_m3d | configured | anchors | 989 |  |  | - | - | - |
| E3_m3d | configured | 0.07 s | 976 | 1.2 | 3.5 | - | - | - |
| E3_m3d | configured | 0.13 s | 963 | 1.6 | 5.6 | - | - | - |
| E3_m3d | configured | 0.27 s | 937 | 2.4 | 7.8 | - | - | - |
| E3_m3d | configured | 0.53 s | 890 | 3.3 | 11.9 | - | - | - |
| E3_m3d | configured | 1.00 s | 814 | 4.6 | 15.8 | - | - | - |
| E3_m3d | configured | 2.00 s | 676 | 6.1 | 20.2 | - | - | - |
| E3_m3d | configured | 4.00 s | 398 | 6.7 | 22.6 | - | - | - |
| E3_m3d | configured | 6.67 s | 55 | 6.2 | 14.9 | - | - | - |
| E3_da3m | oracle | anchors | 989 |  |  | - | - | - |
| E3_da3m | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_da3m | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_da3m | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_da3m | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_da3m | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_da3m | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_da3m | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_da3m | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_da3m | configured | anchors | 989 |  |  | - | - | - |
| E3_da3m | configured | 0.07 s | 976 | 1.2 | 3.7 | - | - | - |
| E3_da3m | configured | 0.13 s | 963 | 1.8 | 6.3 | - | - | - |
| E3_da3m | configured | 0.27 s | 937 | 2.7 | 10.0 | - | - | - |
| E3_da3m | configured | 0.53 s | 890 | 4.2 | 16.3 | - | - | - |
| E3_da3m | configured | 1.00 s | 814 | 6.6 | 25.9 | - | - | - |
| E3_da3m | configured | 2.00 s | 676 | 9.1 | 42.5 | - | - | - |
| E3_da3m | configured | 4.00 s | 398 | 9.0 | 45.6 | - | - | - |
| E3_da3m | configured | 6.67 s | 55 | 11.8 | 49.6 | - | - | - |
| E3_moge | oracle | anchors | 989 |  |  | - | - | - |
| E3_moge | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_moge | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_moge | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_moge | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_moge | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_moge | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_moge | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_moge | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_moge | configured | anchors | 989 |  |  | - | - | - |
| E3_moge | configured | 0.07 s | 976 | 1.2 | 3.7 | - | - | - |
| E3_moge | configured | 0.13 s | 963 | 1.8 | 6.3 | - | - | - |
| E3_moge | configured | 0.27 s | 937 | 2.6 | 10.0 | - | - | - |
| E3_moge | configured | 0.53 s | 890 | 4.1 | 16.0 | - | - | - |
| E3_moge | configured | 1.00 s | 814 | 6.4 | 26.6 | - | - | - |
| E3_moge | configured | 2.00 s | 676 | 8.8 | 41.6 | - | - | - |
| E3_moge | configured | 4.00 s | 398 | 9.4 | 43.9 | - | - | - |
| E3_moge | configured | 6.67 s | 55 | 10.4 | 47.9 | - | - | - |
| E3_dproK | oracle | anchors | 989 |  |  | - | - | - |
| E3_dproK | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_dproK | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_dproK | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_dproK | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_dproK | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_dproK | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_dproK | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_dproK | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_dproK | configured | anchors | 989 |  |  | - | - | - |
| E3_dproK | configured | 0.07 s | 976 | 1.2 | 3.7 | - | - | - |
| E3_dproK | configured | 0.13 s | 963 | 1.8 | 6.3 | - | - | - |
| E3_dproK | configured | 0.27 s | 937 | 2.5 | 9.2 | - | - | - |
| E3_dproK | configured | 0.53 s | 890 | 3.8 | 14.6 | - | - | - |
| E3_dproK | configured | 1.00 s | 814 | 5.7 | 22.9 | - | - | - |
| E3_dproK | configured | 2.00 s | 676 | 7.9 | 34.2 | - | - | - |
| E3_dproK | configured | 4.00 s | 398 | 8.2 | 37.4 | - | - | - |
| E3_dproK | configured | 6.67 s | 55 | 10.1 | 34.1 | - | - | - |
| E3_dpro | oracle | anchors | 989 |  |  | - | - | - |
| E3_dpro | oracle | 0.07 s | 976 | 1.2 | 3.6 | - | - | - |
| E3_dpro | oracle | 0.13 s | 963 | 1.6 | 5.7 | - | - | - |
| E3_dpro | oracle | 0.27 s | 937 | 2.3 | 7.3 | - | - | - |
| E3_dpro | oracle | 0.53 s | 890 | 3.1 | 11.2 | - | - | - |
| E3_dpro | oracle | 1.00 s | 814 | 3.9 | 13.9 | - | - | - |
| E3_dpro | oracle | 2.00 s | 676 | 5.2 | 14.8 | - | - | - |
| E3_dpro | oracle | 4.00 s | 398 | 5.9 | 15.8 | - | - | - |
| E3_dpro | oracle | 6.67 s | 55 | 5.6 | 9.7 | - | - | - |
| E3_dpro | configured | anchors | 989 |  |  | - | - | - |
| E3_dpro | configured | 0.07 s | 976 | 1.2 | 3.9 | - | - | - |
| E3_dpro | configured | 0.13 s | 963 | 1.8 | 6.5 | - | - | - |
| E3_dpro | configured | 0.27 s | 937 | 2.6 | 9.7 | - | - | - |
| E3_dpro | configured | 0.53 s | 890 | 3.9 | 14.8 | - | - | - |
| E3_dpro | configured | 1.00 s | 814 | 6.1 | 24.5 | - | - | - |
| E3_dpro | configured | 2.00 s | 676 | 8.4 | 41.7 | - | - | - |
| E3_dpro | configured | 4.00 s | 398 | 8.0 | 53.9 | - | - | - |
| E3_dpro | configured | 6.67 s | 55 | 8.4 | 58.7 | - | - | - |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp008_depth_models n | exp008_depth_models median | exp008_depth_models p90 | exp007_v2_session_scale n | exp007_v2_session_scale median | exp007_v2_session_scale p90 |
|---|---|---|---|---|---|---|---|---|
| E3_da2 | every scale | anchors | 989 |  |  | - | - | - |
| E3_da2 | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_da2 | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_da2 | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_da2 | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_da2 | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_da2 | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_da2 | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_da2 | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |
| E3_uniK | every scale | anchors | 989 |  |  | - | - | - |
| E3_uniK | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_uniK | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_uniK | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_uniK | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_uniK | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_uniK | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_uniK | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_uniK | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |
| E3_uni | every scale | anchors | 989 |  |  | - | - | - |
| E3_uni | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_uni | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_uni | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_uni | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_uni | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_uni | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_uni | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_uni | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |
| E3_m3d | every scale | anchors | 989 |  |  | - | - | - |
| E3_m3d | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_m3d | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_m3d | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_m3d | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_m3d | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_m3d | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_m3d | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_m3d | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |
| E3_da3m | every scale | anchors | 989 |  |  | - | - | - |
| E3_da3m | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_da3m | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_da3m | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_da3m | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_da3m | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_da3m | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_da3m | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_da3m | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |
| E3_moge | every scale | anchors | 989 |  |  | - | - | - |
| E3_moge | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_moge | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_moge | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_moge | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_moge | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_moge | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_moge | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_moge | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |
| E3_dproK | every scale | anchors | 989 |  |  | - | - | - |
| E3_dproK | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_dproK | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_dproK | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_dproK | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_dproK | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_dproK | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_dproK | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_dproK | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |
| E3_dpro | every scale | anchors | 989 |  |  | - | - | - |
| E3_dpro | every scale | 0.07 s | 976 | 0.14 | 0.44 | - | - | - |
| E3_dpro | every scale | 0.13 s | 963 | 0.20 | 0.61 | - | - | - |
| E3_dpro | every scale | 0.27 s | 937 | 0.27 | 0.83 | - | - | - |
| E3_dpro | every scale | 0.53 s | 890 | 0.36 | 1.18 | - | - | - |
| E3_dpro | every scale | 1.00 s | 814 | 0.50 | 1.59 | - | - | - |
| E3_dpro | every scale | 2.00 s | 676 | 0.65 | 1.99 | - | - | - |
| E3_dpro | every scale | 4.00 s | 398 | 0.56 | 2.41 | - | - | - |
| E3_dpro | every scale | 6.67 s | 55 | 0.57 | 1.16 | - | - | - |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp008_depth_models | exp007_v2_session_scale |
|---|---|---|---|---|---|
| E3_da2 | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_da2 | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_da2 | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_da2 | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_da2 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_da2 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_da2 | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_da2 | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_da2 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_da2 | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_da2 | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_da2 | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_da2 | configured | pos mm, mean / median | 15 (1.00 s) | 4.9 / 3.3 | - |
| E3_da2 | configured | pos mm, mean / median | 30 (2.00 s) | 7.0 / 4.6 | - |
| E3_da2 | configured | pos mm, mean / median | 50 (3.33 s) | 8.6 / 5.9 | - |
| E3_da2 | configured | pos mm, mean / median | 100 (6.67 s) | 10.1 / 6.6 | - |
| E3_da2 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_da2 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_da2 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_da2 | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |
| E3_uniK | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_uniK | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_uniK | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_uniK | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_uniK | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_uniK | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_uniK | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_uniK | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_uniK | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_uniK | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_uniK | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_uniK | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_uniK | configured | pos mm, mean / median | 15 (1.00 s) | 5.2 / 3.4 | - |
| E3_uniK | configured | pos mm, mean / median | 30 (2.00 s) | 7.5 / 4.9 | - |
| E3_uniK | configured | pos mm, mean / median | 50 (3.33 s) | 9.3 / 6.1 | - |
| E3_uniK | configured | pos mm, mean / median | 100 (6.67 s) | 10.8 / 7.5 | - |
| E3_uniK | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_uniK | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_uniK | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_uniK | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |
| E3_uni | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_uni | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_uni | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_uni | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_uni | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_uni | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_uni | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_uni | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_uni | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_uni | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_uni | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_uni | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_uni | configured | pos mm, mean / median | 15 (1.00 s) | 5.1 / 3.3 | - |
| E3_uni | configured | pos mm, mean / median | 30 (2.00 s) | 7.2 / 4.7 | - |
| E3_uni | configured | pos mm, mean / median | 50 (3.33 s) | 8.9 / 6.0 | - |
| E3_uni | configured | pos mm, mean / median | 100 (6.67 s) | 10.4 / 7.3 | - |
| E3_uni | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_uni | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_uni | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_uni | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |
| E3_m3d | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_m3d | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_m3d | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_m3d | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_m3d | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_m3d | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_m3d | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_m3d | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_m3d | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_m3d | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_m3d | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_m3d | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_m3d | configured | pos mm, mean / median | 15 (1.00 s) | 4.9 / 3.4 | - |
| E3_m3d | configured | pos mm, mean / median | 30 (2.00 s) | 7.0 / 4.5 | - |
| E3_m3d | configured | pos mm, mean / median | 50 (3.33 s) | 8.5 / 5.5 | - |
| E3_m3d | configured | pos mm, mean / median | 100 (6.67 s) | 9.9 / 6.4 | - |
| E3_m3d | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_m3d | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_m3d | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_m3d | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |
| E3_da3m | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_da3m | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_da3m | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_da3m | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_da3m | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_da3m | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_da3m | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_da3m | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_da3m | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_da3m | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_da3m | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_da3m | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_da3m | configured | pos mm, mean / median | 15 (1.00 s) | 6.3 / 4.2 | - |
| E3_da3m | configured | pos mm, mean / median | 30 (2.00 s) | 9.6 / 6.2 | - |
| E3_da3m | configured | pos mm, mean / median | 50 (3.33 s) | 12.0 / 7.4 | - |
| E3_da3m | configured | pos mm, mean / median | 100 (6.67 s) | 14.0 / 9.5 | - |
| E3_da3m | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_da3m | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_da3m | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_da3m | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |
| E3_moge | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_moge | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_moge | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_moge | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_moge | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_moge | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_moge | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_moge | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_moge | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_moge | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_moge | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_moge | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_moge | configured | pos mm, mean / median | 15 (1.00 s) | 6.3 / 4.1 | - |
| E3_moge | configured | pos mm, mean / median | 30 (2.00 s) | 9.6 / 6.1 | - |
| E3_moge | configured | pos mm, mean / median | 50 (3.33 s) | 12.0 / 7.3 | - |
| E3_moge | configured | pos mm, mean / median | 100 (6.67 s) | 13.8 / 9.1 | - |
| E3_moge | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_moge | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_moge | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_moge | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |
| E3_dproK | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_dproK | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_dproK | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_dproK | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_dproK | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_dproK | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_dproK | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_dproK | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_dproK | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_dproK | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_dproK | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_dproK | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_dproK | configured | pos mm, mean / median | 15 (1.00 s) | 5.8 / 3.7 | - |
| E3_dproK | configured | pos mm, mean / median | 30 (2.00 s) | 8.7 / 5.5 | - |
| E3_dproK | configured | pos mm, mean / median | 50 (3.33 s) | 10.8 / 6.7 | - |
| E3_dproK | configured | pos mm, mean / median | 100 (6.67 s) | 12.6 / 8.3 | - |
| E3_dproK | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_dproK | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_dproK | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_dproK | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |
| E3_dpro | every scale | anchors | 15 (1.00 s) | 978 | - |
| E3_dpro | every scale | anchors | 30 (2.00 s) | 979 | - |
| E3_dpro | every scale | anchors | 50 (3.33 s) | 979 | - |
| E3_dpro | every scale | anchors | 100 (6.67 s) | 979 | - |
| E3_dpro | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - |
| E3_dpro | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - |
| E3_dpro | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - |
| E3_dpro | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - |
| E3_dpro | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | - |
| E3_dpro | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | - |
| E3_dpro | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | - |
| E3_dpro | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | - |
| E3_dpro | configured | pos mm, mean / median | 15 (1.00 s) | 6.1 / 4.0 | - |
| E3_dpro | configured | pos mm, mean / median | 30 (2.00 s) | 9.2 / 6.0 | - |
| E3_dpro | configured | pos mm, mean / median | 50 (3.33 s) | 11.5 / 7.3 | - |
| E3_dpro | configured | pos mm, mean / median | 100 (6.67 s) | 13.7 / 8.2 | - |
| E3_dpro | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | - |
| E3_dpro | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | - |
| E3_dpro | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | - |
| E3_dpro | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | - |

### Ground-truth noise floor

| pairs | dt [s] | exp008_depth_models n | exp008_depth_models rot deg med / p95 | exp008_depth_models trans mm med / p95 | exp007_v2_session_scale n | exp007_v2_session_scale rot deg med / p95 | exp007_v2_session_scale trans mm med / p95 |
|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 2.0 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

