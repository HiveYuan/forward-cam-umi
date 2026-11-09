# exp001_sam2_baseline: report (variant main)

30 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | 0.24 / 1.26 | 0.60 / 4.46 | 0.85 / 7.88 | 1.11 / 14.80 | 0.98 / 8.62 |
| E3 | 0.16 / 0.66 | 0.35 / 1.58 | 0.53 / 2.32 | 0.59 / 2.81 | 0.62 / 0.92 |

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E1 | oracle (tiles) | 3.63 / 17.91 | 9.92 / 65.90 | 13.93 / 117.98 | 17.19 / 209.69 | 12.66 / 158.28 |
| E3 | oracle (tiles) | 2.45 / 10.33 | 5.45 / 25.50 | 7.81 / 37.39 | 9.39 / 47.49 | 10.14 / 14.99 |
| E3 | B+Acheck | 2.45 / 10.21 | 5.95 / 26.27 | 9.42 / 40.22 | 11.70 / 51.45 | 10.20 / 18.55 |

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | 1.93% | 14.2 | 43 | 100% |
| E3 | 0.34% | 12.8 | 47 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | B+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 5.8% | 21.4% | -5.3% | ep01, ep12, ep15 |
| E3 | B+Acheck, without flagged | 27/30 | 25 | 5.2% | 20.4% | -4.8% |  |
| E3 | B+Acheck, method B (primary) | 30/30 | 28 | 5.8% | 21.4% | -5.3% |  |
| E3 | B+Acheck, method A (check) | 9/30 | 9 | 5.1% | 11.1% | -4.7% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 989 | 1.2 / 3.9 | 1.6 / 6.0 | 2.3 / 7.7 | 3.1 / 11.3 | 4.0 / 14.1 | 5.2 / 15.0 | 5.9 / 14.3 | 5.6 / 7.9 |
| E3 | B+Acheck | 989 | 1.2 / 3.8 | 1.7 / 6.3 | 2.5 / 9.1 | 3.7 / 13.7 | 5.9 / 19.5 | 7.9 / 27.4 | 7.6 / 33.2 | 6.2 / 15.3 |

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation error [deg], median / p90

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 989 | 0.14 / 0.44 | 0.20 / 0.67 | 0.27 / 0.88 | 0.36 / 1.25 | 0.53 / 1.66 | 0.59 / 2.25 | 0.50 / 2.00 | 0.61 / 0.89 |
| E3 | B+Acheck | 989 | 0.14 / 0.44 | 0.20 / 0.67 | 0.27 / 0.88 | 0.36 / 1.25 | 0.53 / 1.66 | 0.59 / 2.25 | 0.50 / 2.00 | 0.61 / 0.89 |

## Chunk-length label error: mean over anchors of the mean error over steps 1..H, position [mm] / rotation [deg]

| run | scale | anchors | H=15 (1.00 s) | H=30 (2.00 s) | H=50 (3.33 s) | H=100 (6.67 s) |
|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 978 | 4.9 / 0.59 | 6.8 / 0.81 | 8.2 / 0.97 | 9.5 / 1.12 |
| E3 | B+Acheck | 978 | 5.7 / 0.59 | 8.3 / 0.81 | 10.2 / 0.97 | 11.9 / 1.12 |

## Ground-truth noise floor (slam.tiles noise, 2-tile solves)

From 40 frames with all 4 tiles, comparing disjoint tile pairs.

| pairs | n | rot deg median / p95 | trans mm median / p95 |
|---|---|---|---|
| same tiles, dt 0.08 s | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles, dt 0.5 s | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles, dt 2.0 s | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes between the ends | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

## Reproducibility

slam.E3 recomputed 1 time(s): see `repro.md` (tolerance table) and `repro.json`.

## Comparison with other experiments

- exp000_legacy: legacy adapter over `exp000_legacy/results/` (eval/, B+Acheck_eval/; no chunk metrics)
- runs only in exp000_legacy (not shown): E2

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg]

| run | dt | exp001_sam2_baseline median | exp001_sam2_baseline p95 | exp000_legacy median | exp000_legacy p95 |
|---|---|---|---|---|---|
| static | 0.08 | 0.39 | 1.63 | 0.39 | 1.63 |
| static | 0.5 | 2.11 | 8.93 | 2.11 | 8.93 |
| static | 1.0 | 3.74 | 15.07 | 3.74 | 15.07 |
| static | 2.0 | 5.93 | 23.51 | 5.93 | 23.51 |
| static | 6.67 | 7.76 | 13.01 | 7.76 | 13.01 |
| E1 | 0.08 | 0.24 | 1.26 | 0.24 | 1.26 |
| E1 | 0.5 | 0.60 | 4.46 | 0.60 | 4.46 |
| E1 | 1.0 | 0.85 | 7.88 | 0.85 | 7.88 |
| E1 | 2.0 | 1.11 | 14.80 | 1.11 | 14.80 |
| E1 | 6.67 | 0.98 | 8.62 | 0.98 | 8.62 |
| E3 | 0.08 | 0.16 | 0.66 | 0.16 | 0.66 |
| E3 | 0.5 | 0.35 | 1.58 | 0.35 | 1.58 |
| E3 | 1.0 | 0.53 | 2.32 | 0.53 | 2.32 |
| E3 | 2.0 | 0.59 | 2.81 | 0.59 | 2.81 |
| E3 | 6.67 | 0.62 | 0.92 | 0.62 | 0.92 |

### Head translation error [mm]

| run | scale | dt | exp001_sam2_baseline median | exp001_sam2_baseline p95 | exp000_legacy median | exp000_legacy p95 |
|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | 3.63 | 17.91 | 3.63 | 17.91 |
| E1 | oracle | 0.5 | 9.92 | 65.90 | 9.92 | 65.90 |
| E1 | oracle | 1.0 | 13.93 | 117.98 | 13.93 | 117.98 |
| E1 | oracle | 2.0 | 17.19 | 209.69 | 17.19 | 209.69 |
| E1 | oracle | 6.67 | 12.66 | 158.28 | 12.66 | 158.28 |
| E3 | oracle | 0.08 | 2.45 | 10.33 | 2.45 | 10.33 |
| E3 | oracle | 0.5 | 5.45 | 25.50 | 5.45 | 25.50 |
| E3 | oracle | 1.0 | 7.81 | 37.39 | 7.81 | 37.39 |
| E3 | oracle | 2.0 | 9.39 | 47.49 | 9.39 | 47.49 |
| E3 | oracle | 6.67 | 10.14 | 14.99 | 10.14 | 14.99 |
| E3 | configured | 0.08 | 2.45 | 10.21 | 2.45 | 10.21 |
| E3 | configured | 0.5 | 5.95 | 26.27 | 5.95 | 26.27 |
| E3 | configured | 1.0 | 9.42 | 40.22 | 9.42 | 40.22 |
| E3 | configured | 2.0 | 11.70 | 51.45 | 11.70 | 51.45 |
| E3 | configured | 6.67 | 10.20 | 18.55 | 10.20 | 18.55 |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp001_sam2_baseline | exp000_legacy |
|---|---|---|---|
| E1 | track fail | 1.93% | 1.93% |
| E1 | keyframes / segment | 14.2 | 14.2 |
| E1 | runtime s / segment | 43 | 44 |
| E1 | valid pixels | 100% | 100% |
| E3 | track fail | 0.34% | 0.34% |
| E3 | keyframes / segment | 12.8 | 12.8 |
| E3 | runtime s / segment | 47 | 47 |
| E3 | valid pixels | 86% | 86% |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp001_sam2_baseline | exp000_legacy |
|---|---|---|---|
| E3 | scale label | B+Acheck | B+Acheck |
| E3 | segments with a scale | 30/30 | 30/30 |
| E3 | compared (tile GT) | 28 | 28 |
| E3 | abs err median | 5.8% | 5.8% |
| E3 | abs err p90 | 21.4% | 21.4% |
| E3 | bias (median) | -5.3% | -5.3% |
| E3 | flagged | ep01, ep12, ep15 | ep01, ep12, ep15 |
| E3 | without flagged: abs err median / p90 | 5.2% / 20.4% | 5.2% / 20.4% |
| E3 | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 5.8% / 21.4% / -5.3% | 30/30, n 28: 5.8% / 21.4% / -5.3% |
| E3 | method A: segments ok, n: abs err median / p90 / bias | 9/30, n 9: 5.1% / 11.1% / -4.7% | 9/30, n 9: 5.1% / 11.1% / -4.7% |

### Tool label position error tool_t->tool_t+dt [mm]

| run | scale | dt | exp001_sam2_baseline median | exp001_sam2_baseline p90 | exp000_legacy median | exp000_legacy p90 |
|---|---|---|---|---|---|---|
| E3 | oracle | anchors | 989 |  | 989 |  |
| E3 | oracle | 0.07 s | 1.2 | 3.9 | 1.2 | 3.9 |
| E3 | oracle | 0.13 s | 1.6 | 6.0 | 1.6 | 6.0 |
| E3 | oracle | 0.27 s | 2.3 | 7.7 | 2.3 | 7.7 |
| E3 | oracle | 0.53 s | 3.1 | 11.3 | 3.1 | 11.3 |
| E3 | oracle | 1.00 s | 4.0 | 14.1 | 4.0 | 14.1 |
| E3 | oracle | 2.00 s | 5.2 | 15.0 | 5.2 | 15.0 |
| E3 | oracle | 4.00 s | 5.9 | 14.3 | 5.9 | 14.3 |
| E3 | oracle | 6.67 s | 5.6 | 7.9 | 5.6 | 7.9 |
| E3 | configured | anchors | 989 |  | 989 |  |
| E3 | configured | 0.07 s | 1.2 | 3.8 | 1.2 | 3.8 |
| E3 | configured | 0.13 s | 1.7 | 6.3 | 1.7 | 6.3 |
| E3 | configured | 0.27 s | 2.5 | 9.1 | 2.5 | 9.1 |
| E3 | configured | 0.53 s | 3.7 | 13.7 | 3.7 | 13.7 |
| E3 | configured | 1.00 s | 5.9 | 19.5 | 5.9 | 19.5 |
| E3 | configured | 2.00 s | 7.9 | 27.4 | 7.9 | 27.4 |
| E3 | configured | 4.00 s | 7.6 | 33.2 | 7.6 | 33.2 |
| E3 | configured | 6.67 s | 6.2 | 15.3 | 6.2 | 15.3 |

### Tool label rotation error [deg]

| run | scale | dt | exp001_sam2_baseline median | exp001_sam2_baseline p90 | exp000_legacy median | exp000_legacy p90 |
|---|---|---|---|---|---|---|
| E3 | oracle | anchors | 989 |  | 989 |  |
| E3 | oracle | 0.07 s | 0.14 | 0.44 | 0.14 | 0.44 |
| E3 | oracle | 0.13 s | 0.20 | 0.67 | 0.20 | 0.67 |
| E3 | oracle | 0.27 s | 0.27 | 0.88 | 0.27 | 0.88 |
| E3 | oracle | 0.53 s | 0.36 | 1.25 | 0.36 | 1.25 |
| E3 | oracle | 1.00 s | 0.53 | 1.66 | 0.53 | 1.66 |
| E3 | oracle | 2.00 s | 0.59 | 2.25 | 0.59 | 2.25 |
| E3 | oracle | 4.00 s | 0.50 | 2.00 | 0.50 | 2.00 |
| E3 | oracle | 6.67 s | 0.61 | 0.89 | 0.61 | 0.89 |
| E3 | configured | anchors | 989 |  | 989 |  |
| E3 | configured | 0.07 s | 0.14 | 0.44 | 0.14 | 0.44 |
| E3 | configured | 0.13 s | 0.20 | 0.67 | 0.20 | 0.67 |
| E3 | configured | 0.27 s | 0.27 | 0.88 | 0.27 | 0.88 |
| E3 | configured | 0.53 s | 0.36 | 1.25 | 0.36 | 1.25 |
| E3 | configured | 1.00 s | 0.53 | 1.66 | 0.53 | 1.66 |
| E3 | configured | 2.00 s | 0.59 | 2.25 | 0.59 | 2.25 |
| E3 | configured | 4.00 s | 0.50 | 2.00 | 0.50 | 2.00 |
| E3 | configured | 6.67 s | 0.61 | 0.89 | 0.61 | 0.89 |

### Chunk-length label error, mean over anchors of the mean over steps 1..H

| run | scale | H | exp001_sam2_baseline pos mm | exp001_sam2_baseline rot deg | exp000_legacy pos mm | exp000_legacy rot deg |
|---|---|---|---|---|---|---|
| E3 | oracle | 15 | 4.9 | 0.59 | - | - |
| E3 | oracle | 30 | 6.8 | 0.81 | - | - |
| E3 | oracle | 50 | 8.2 | 0.97 | - | - |
| E3 | oracle | 100 | 9.5 | 1.12 | - | - |
| E3 | configured | 15 | 5.7 | 0.59 | - | - |
| E3 | configured | 30 | 8.3 | 0.81 | - | - |
| E3 | configured | 50 | 10.2 | 0.97 | - | - |
| E3 | configured | 100 | 11.9 | 1.12 | - | - |

### Ground-truth noise floor

| pairs | dt | exp001_sam2_baseline n | exp001_sam2_baseline rot deg med / p95 | exp001_sam2_baseline trans mm med / p95 | exp000_legacy n | exp000_legacy rot deg med / p95 | exp000_legacy trans mm med / p95 |
|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 2.0 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

