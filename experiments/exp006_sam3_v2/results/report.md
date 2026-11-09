# exp006_sam3_v2: report (variant main)

30 segments. Runs: E1, E3 (static = head motion identity, no SLAM). Ground truth: tile head poses; "oracle (tiles)" = per-segment scale fitted to the tile poses (evaluation only).

## Head rotation error cam_t->cam_t+dt [deg], median / p95

| run | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|
| static | 0.39 / 1.63 | 2.11 / 8.93 | 3.74 / 15.07 | 5.93 / 23.51 | 7.76 / 13.01 |
| E1 | 0.24 / 1.26 | 0.60 / 4.46 | 0.85 / 7.88 | 1.11 / 14.80 | 0.98 / 8.62 |
| E3 | 0.16 / 0.64 | 0.36 / 1.49 | 0.52 / 2.25 | 0.65 / 2.60 | 0.58 / 1.26 |

n [frame pairs]: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Head translation error [mm], median / p95

| run | scale | 0.08 s | 0.5 s | 1.0 s | 2.0 s | 6.67 s |
|---|---|---|---|---|---|---|
| E1 | oracle (tiles) | 3.63 / 17.91 | 9.92 / 65.90 | 13.93 / 117.98 | 17.19 / 209.69 | 12.66 / 158.28 |
| E3 | oracle (tiles) | 2.49 / 10.13 | 5.47 / 24.24 | 7.46 / 36.49 | 9.87 / 46.80 | 10.15 / 16.47 |
| E3 | B+Acheck | 2.45 / 9.83 | 5.80 / 25.13 | 8.90 / 40.37 | 12.05 / 53.74 | 9.90 / 17.67 |

n [frame pairs]:

- E1 oracle (tiles), E3 oracle (tiles): 0.08 s: 2371, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88
- E3 B+Acheck: 0.08 s: 2380, 0.5 s: 1931, 1.0 s: 1612, 2.0 s: 1248, 6.67 s: 88

## Tracking, keyframes, runtime

| run | track fail (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |
|---|---|---|---|---|
| E1 | 1.93% | 14.2 | 43 | 100% |
| E3 | 0.17% | 12.8 | 47 | 86% |

## Scale error vs the tile oracle (s / s_oracle - 1)

| run | scale | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) | flagged |
|---|---|---|---|---|---|---|---|
| E3 | B+Acheck (flag \|check/primary - 1\| > 10%) | 30/30 | 28 | 6.6% | 21.7% | -5.2% | ep01, ep12, ep15, ep20 |
| E3 | B+Acheck, without flagged | 26/30 | 24 | 5.2% | 16.6% | -4.7% |  |
| E3 | B+Acheck, method B (primary) | 30/30 | 28 | 6.6% | 21.7% | -5.2% |  |
| E3 | B+Acheck, method A (check) | 11/30 | 11 | 6.8% | 19.0% | -4.6% |  |

s is always the primary's; checks only flag segments (nothing is changed or dropped).

## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position error [mm], median / p90

The "Tool labels" tables are the slam.labels check on the 15 fps training timeline: the relative chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage rules).

| run | scale | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle (tiles) | 989 | 1.2 / 3.6 | 1.6 / 5.7 | 2.3 / 7.3 | 3.1 / 11.2 | 3.9 / 13.9 | 5.2 / 14.8 | 5.9 / 15.8 | 5.6 / 9.7 |
| E3 | B+Acheck | 989 | 1.2 / 3.6 | 1.7 / 6.0 | 2.5 / 8.7 | 3.8 / 13.3 | 5.7 / 18.7 | 7.7 / 26.4 | 7.3 / 36.7 | 6.1 / 13.4 |

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
| E3 | position [mm], B+Acheck, mean / median | 5.5 / 3.8 | 8.0 / 5.4 | 9.9 / 6.4 | 11.7 / 7.1 |
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

## Mask comparison: motion vs sam2 (reference)

8972 frames of 30 segments. Per frame, then pooled over every frame of every segment. IoU = intersection / union (1 when both masks are empty); recall = share of the reference pixels the candidate covers; precision = share of the candidate pixels inside the reference; extra / missed area = candidate-only / reference-only pixels as a share of the frame; DROID-cell IoU = IoU of the 1/8-resolution cells DROID ignores, each mask dilated by 8 px at full resolution first (a cell is ignored when any of its pixels is masked: slam.droid_masked.valid_grid). An empty denominator counts 1 (two empty masks: IoU 1; empty reference: recall 1; empty candidate: precision 1), so n = frames. Per segment: `masks_motion_vs_sam2.md`.

| quantity | n | median | p10 | p90 | mean |
|---|---|---|---|---|---|
| IoU | 8972 | 0.942 | 0.875 | 0.965 | 0.918 |
| recall (share of the reference covered by the candidate) | 8972 | 0.969 | 0.933 | 0.984 | 0.956 |
| precision (share of the candidate inside the reference) | 8972 | 0.979 | 0.923 | 0.990 | 0.959 |
| extra area: candidate only [% of frame] | 8972 | 0.14% | 0.05% | 0.67% | 0.33% |
| missed area: reference only [% of frame] | 8972 | 0.21% | 0.10% | 0.44% | 0.35% |
| DROID-cell IoU (masks dilated by 8 px) | 8972 | 0.979 | 0.888 | 0.994 | 0.952 |

Mean masked area [% of frame]: sam2 (reference) 7.20%, motion (candidate) 7.19%.

| motion part | mean area [% of frame] |
|---|---|
| rig | 2.72% |
| hand_track | 3.39% |
| held | 0.14% |
| hand | 2.49% |
| arm | 3.47% |
| cable | 0.63% |

Parts may overlap; their union is the candidate mask.

Segments with IoU median < 0.8: none (0 of 30).

Worst segments (IoU median): ep20 0.888, ep12 0.902, ep00 0.905, ep09 0.912, ep21 0.926.

Overlay images (not copied into results/): `main/overlays/motion_vs_sam2/` in the experiment's work run directory `<work>/runs/exp006_sam3_v2/` (<work> = `/home/student/yuanliu-hawaii/work`), 120 images: 60 evenly spaced, 60 lowest-IoU; candidate parts filled in distinct colours, reference outlined in white; `index.json` lists file, segment, frame i, IoU and kind.

## Comparison with other experiments

- exp001_sam2_baseline: `exp001_sam2_baseline/results/metrics.json`
- exp003_droid_sam3: `exp003_droid_sam3/results/metrics.json`
- runs only in exp003_droid_sam3 (not shown): E2

Rows: what this experiment has. "configured" = each experiment's own scale method (labels in the scale table); "-" = not available.

### Head rotation error [deg], n = frame pairs

| run | dt [s] | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p95 | exp001_sam2_baseline n | exp001_sam2_baseline median | exp001_sam2_baseline p95 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| static | 0.08 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 | 2380 | 0.39 | 1.63 |
| static | 0.5 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 | 1931 | 2.11 | 8.93 |
| static | 1.0 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 | 1612 | 3.74 | 15.07 |
| static | 2.0 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 | 1248 | 5.93 | 23.51 |
| static | 6.67 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 | 88 | 7.76 | 13.01 |
| E1 | 0.08 | 2380 | 0.24 | 1.26 | 2380 | 0.24 | 1.26 | 2380 | 0.24 | 1.26 |
| E1 | 0.5 | 1931 | 0.60 | 4.46 | 1931 | 0.60 | 4.46 | 1931 | 0.60 | 4.46 |
| E1 | 1.0 | 1612 | 0.85 | 7.88 | 1612 | 0.85 | 7.88 | 1612 | 0.85 | 7.88 |
| E1 | 2.0 | 1248 | 1.11 | 14.80 | 1248 | 1.11 | 14.80 | 1248 | 1.11 | 14.80 |
| E1 | 6.67 | 88 | 0.98 | 8.62 | 88 | 0.98 | 8.62 | 88 | 0.98 | 8.62 |
| E3 | 0.08 | 2380 | 0.16 | 0.64 | 2380 | 0.16 | 0.66 | 2380 | 0.16 | 0.63 |
| E3 | 0.5 | 1931 | 0.36 | 1.49 | 1931 | 0.35 | 1.58 | 1931 | 0.36 | 1.52 |
| E3 | 1.0 | 1612 | 0.52 | 2.25 | 1612 | 0.53 | 2.32 | 1612 | 0.52 | 2.17 |
| E3 | 2.0 | 1248 | 0.65 | 2.60 | 1248 | 0.59 | 2.81 | 1248 | 0.64 | 2.67 |
| E3 | 6.67 | 88 | 0.58 | 1.26 | 88 | 0.62 | 0.92 | 88 | 0.73 | 1.21 |

### Head translation error [mm], n = frame pairs

| run | scale | dt [s] | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p95 | exp001_sam2_baseline n | exp001_sam2_baseline median | exp001_sam2_baseline p95 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | oracle | 0.08 | 2371 | 3.63 | 17.91 | 2371 | 3.63 | 17.91 | 2371 | 3.63 | 17.91 |
| E1 | oracle | 0.5 | 1931 | 9.92 | 65.90 | 1931 | 9.92 | 65.90 | 1931 | 9.92 | 65.90 |
| E1 | oracle | 1.0 | 1612 | 13.93 | 117.98 | 1612 | 13.93 | 117.98 | 1612 | 13.93 | 117.98 |
| E1 | oracle | 2.0 | 1248 | 17.19 | 209.69 | 1248 | 17.19 | 209.69 | 1248 | 17.19 | 209.69 |
| E1 | oracle | 6.67 | 88 | 12.66 | 158.28 | 88 | 12.66 | 158.28 | 88 | 12.66 | 158.28 |
| E3 | oracle | 0.08 | 2371 | 2.49 | 10.13 | 2371 | 2.45 | 10.33 | 2371 | 2.47 | 9.73 |
| E3 | oracle | 0.5 | 1931 | 5.47 | 24.24 | 1931 | 5.45 | 25.50 | 1931 | 5.52 | 25.17 |
| E3 | oracle | 1.0 | 1612 | 7.46 | 36.49 | 1612 | 7.81 | 37.39 | 1612 | 8.19 | 34.71 |
| E3 | oracle | 2.0 | 1248 | 9.87 | 46.80 | 1248 | 9.39 | 47.49 | 1248 | 9.98 | 43.87 |
| E3 | oracle | 6.67 | 88 | 10.15 | 16.47 | 88 | 10.14 | 14.99 | 88 | 10.88 | 17.42 |
| E3 | configured | 0.08 | 2380 | 2.45 | 9.83 | 2380 | 2.45 | 10.21 | 2380 | 2.51 | 9.39 |
| E3 | configured | 0.5 | 1931 | 5.80 | 25.13 | 1931 | 5.95 | 26.27 | 1931 | 5.89 | 25.36 |
| E3 | configured | 1.0 | 1612 | 8.90 | 40.37 | 1612 | 9.42 | 40.22 | 1612 | 9.06 | 36.20 |
| E3 | configured | 2.0 | 1248 | 12.05 | 53.74 | 1248 | 11.70 | 51.45 | 1248 | 12.17 | 45.14 |
| E3 | configured | 6.67 | 88 | 9.90 | 17.67 | 88 | 10.20 | 18.55 | 88 | 10.85 | 17.89 |

### Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime

| run | quantity | exp006_sam3_v2 | exp001_sam2_baseline | exp003_droid_sam3 |
|---|---|---|---|---|
| E1 | track fail | 1.93% | 1.93% | 1.93% |
| E1 | keyframes / segment | 14.2 | 14.2 | 14.2 |
| E1 | runtime s / segment | 43 | 43 | 43 |
| E1 | valid pixels | 100% | 100% | 100% |
| E3 | track fail | 0.17% | 0.34% | 0.21% |
| E3 | keyframes / segment | 12.8 | 12.8 | 13.0 |
| E3 | runtime s / segment | 47 | 47 | 48 |
| E3 | valid pixels | 86% | 86% | 85% |

### Scale error vs the tile oracle (configured scale)

| run | quantity | exp006_sam3_v2 | exp001_sam2_baseline | exp003_droid_sam3 |
|---|---|---|---|---|
| E3 | scale label | B+Acheck | B+Acheck | B+Acheck |
| E3 | segments with a scale | 30/30 | 30/30 | 30/30 |
| E3 | compared (tile GT) | 28 | 28 | 28 |
| E3 | abs err median | 6.6% | 5.8% | 5.4% |
| E3 | abs err p90 | 21.7% | 21.4% | 20.1% |
| E3 | bias (median) | -5.2% | -5.3% | -5.0% |
| E3 | flagged | ep01, ep12, ep15, ep20 | ep01, ep12, ep15 | ep01, ep11, ep12, ep20, ep25, ep26 |
| E3 | without flagged: abs err median / p90 | 5.2% / 16.6% | 5.2% / 20.4% | 5.0% / 17.6% |
| E3 | method B: segments ok, n: abs err median / p90 / bias | 30/30, n 28: 6.6% / 21.7% / -5.2% | 30/30, n 28: 5.8% / 21.4% / -5.3% | 30/30, n 28: 5.4% / 20.1% / -5.0% |
| E3 | method A: segments ok, n: abs err median / p90 / bias | 11/30, n 11: 6.8% / 19.0% / -4.6% | 9/30, n 9: 5.1% / 11.1% / -4.7% | 14/30, n 14: 4.4% / 16.5% / -1.6% |

### Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step

| run | scale | dt | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p90 | exp001_sam2_baseline n | exp001_sam2_baseline median | exp001_sam2_baseline p90 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3 | oracle | anchors | 989 |  |  | 989 |  |  | 989 |  |  |
| E3 | oracle | 0.07 s | 976 | 1.2 | 3.6 | 976 | 1.2 | 3.9 | 976 | 1.2 | 3.6 |
| E3 | oracle | 0.13 s | 963 | 1.6 | 5.7 | 963 | 1.6 | 6.0 | 963 | 1.7 | 5.7 |
| E3 | oracle | 0.27 s | 937 | 2.3 | 7.3 | 937 | 2.3 | 7.7 | 937 | 2.3 | 7.8 |
| E3 | oracle | 0.53 s | 890 | 3.1 | 11.2 | 890 | 3.1 | 11.3 | 890 | 3.2 | 11.3 |
| E3 | oracle | 1.00 s | 814 | 3.9 | 13.9 | 814 | 4.0 | 14.1 | 814 | 4.3 | 14.6 |
| E3 | oracle | 2.00 s | 676 | 5.2 | 14.8 | 676 | 5.2 | 15.0 | 676 | 5.5 | 14.7 |
| E3 | oracle | 4.00 s | 398 | 5.9 | 15.8 | 398 | 5.9 | 14.3 | 398 | 5.9 | 17.0 |
| E3 | oracle | 6.67 s | 55 | 5.6 | 9.7 | 55 | 5.6 | 7.9 | 55 | 5.8 | 8.7 |
| E3 | configured | anchors | 989 |  |  | 989 |  |  | 989 |  |  |
| E3 | configured | 0.07 s | 976 | 1.2 | 3.6 | 976 | 1.2 | 3.8 | 976 | 1.2 | 3.6 |
| E3 | configured | 0.13 s | 963 | 1.7 | 6.0 | 963 | 1.7 | 6.3 | 963 | 1.8 | 5.8 |
| E3 | configured | 0.27 s | 937 | 2.5 | 8.7 | 937 | 2.5 | 9.1 | 937 | 2.5 | 9.0 |
| E3 | configured | 0.53 s | 890 | 3.8 | 13.3 | 890 | 3.7 | 13.7 | 890 | 3.7 | 13.9 |
| E3 | configured | 1.00 s | 814 | 5.7 | 18.7 | 814 | 5.9 | 19.5 | 814 | 5.7 | 18.4 |
| E3 | configured | 2.00 s | 676 | 7.7 | 26.4 | 676 | 7.9 | 27.4 | 676 | 7.6 | 27.9 |
| E3 | configured | 4.00 s | 398 | 7.3 | 36.7 | 398 | 7.6 | 33.2 | 398 | 7.4 | 30.1 |
| E3 | configured | 6.67 s | 55 | 6.1 | 13.4 | 55 | 6.2 | 15.3 | 55 | 5.6 | 12.5 |

### Tool label rotation error [deg], n = anchors counting the step (rotation is scale-free: same for every scale)

| run | scale | dt | exp006_sam3_v2 n | exp006_sam3_v2 median | exp006_sam3_v2 p90 | exp001_sam2_baseline n | exp001_sam2_baseline median | exp001_sam2_baseline p90 | exp003_droid_sam3 n | exp003_droid_sam3 median | exp003_droid_sam3 p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E3 | every scale | anchors | 989 |  |  | 989 |  |  | 989 |  |  |
| E3 | every scale | 0.07 s | 976 | 0.14 | 0.44 | 976 | 0.14 | 0.44 | 976 | 0.14 | 0.44 |
| E3 | every scale | 0.13 s | 963 | 0.20 | 0.61 | 963 | 0.20 | 0.67 | 963 | 0.20 | 0.60 |
| E3 | every scale | 0.27 s | 937 | 0.27 | 0.83 | 937 | 0.27 | 0.88 | 937 | 0.27 | 0.86 |
| E3 | every scale | 0.53 s | 890 | 0.36 | 1.18 | 890 | 0.36 | 1.25 | 890 | 0.36 | 1.23 |
| E3 | every scale | 1.00 s | 814 | 0.50 | 1.59 | 814 | 0.53 | 1.66 | 814 | 0.52 | 1.62 |
| E3 | every scale | 2.00 s | 676 | 0.65 | 1.99 | 676 | 0.59 | 2.25 | 676 | 0.62 | 2.06 |
| E3 | every scale | 4.00 s | 398 | 0.56 | 2.41 | 398 | 0.50 | 2.00 | 398 | 0.57 | 1.91 |
| E3 | every scale | 6.67 s | 55 | 0.57 | 1.16 | 55 | 0.61 | 0.89 | 55 | 0.71 | 1.12 |

### Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, then mean / median over anchors (rotation is scale-free: same for every scale)

| run | scale | quantity | H [steps of 1/15 s] | exp006_sam3_v2 | exp001_sam2_baseline | exp003_droid_sam3 |
|---|---|---|---|---|---|---|
| E3 | every scale | anchors | 15 (1.00 s) | 978 | 978 | 978 |
| E3 | every scale | anchors | 30 (2.00 s) | 979 | 979 | 979 |
| E3 | every scale | anchors | 50 (3.33 s) | 979 | 979 | 979 |
| E3 | every scale | anchors | 100 (6.67 s) | 979 | 979 | 979 |
| E3 | every scale | counted steps per anchor, median | 15 (1.00 s) | 15 | - | 15 |
| E3 | every scale | counted steps per anchor, median | 30 (2.00 s) | 30 | - | 30 |
| E3 | every scale | counted steps per anchor, median | 50 (3.33 s) | 46 | - | 46 |
| E3 | every scale | counted steps per anchor, median | 100 (6.67 s) | 49 | - | 49 |
| E3 | oracle | pos mm, mean / median | 15 (1.00 s) | 4.7 / 3.2 | 4.9 / 3.2 | 4.8 / 3.3 |
| E3 | oracle | pos mm, mean / median | 30 (2.00 s) | 6.4 / 4.2 | 6.8 / 4.4 | 6.6 / 4.4 |
| E3 | oracle | pos mm, mean / median | 50 (3.33 s) | 7.7 / 4.9 | 8.2 / 5.1 | 7.8 / 5.2 |
| E3 | oracle | pos mm, mean / median | 100 (6.67 s) | 9.1 / 5.5 | 9.5 / 5.4 | 8.9 / 5.4 |
| E3 | configured | pos mm, mean / median | 15 (1.00 s) | 5.5 / 3.8 | 5.7 / 3.8 | 5.5 / 3.8 |
| E3 | configured | pos mm, mean / median | 30 (2.00 s) | 8.0 / 5.4 | 8.3 / 5.7 | 7.9 / 5.4 |
| E3 | configured | pos mm, mean / median | 50 (3.33 s) | 9.9 / 6.4 | 10.2 / 6.6 | 9.5 / 6.2 |
| E3 | configured | pos mm, mean / median | 100 (6.67 s) | 11.7 / 7.1 | 11.9 / 7.3 | 10.9 / 7.0 |
| E3 | every scale | rot deg, mean / median | 15 (1.00 s) | 0.57 / 0.39 | 0.59 / 0.40 | 0.56 / 0.40 |
| E3 | every scale | rot deg, mean / median | 30 (2.00 s) | 0.78 / 0.51 | 0.81 / 0.51 | 0.77 / 0.52 |
| E3 | every scale | rot deg, mean / median | 50 (3.33 s) | 0.95 / 0.58 | 0.97 / 0.56 | 0.91 / 0.59 |
| E3 | every scale | rot deg, mean / median | 100 (6.67 s) | 1.11 / 0.59 | 1.12 / 0.58 | 1.03 / 0.60 |

### Ground-truth noise floor

| pairs | dt [s] | exp006_sam3_v2 n | exp006_sam3_v2 rot deg med / p95 | exp006_sam3_v2 trans mm med / p95 | exp001_sam2_baseline n | exp001_sam2_baseline rot deg med / p95 | exp001_sam2_baseline trans mm med / p95 | exp003_droid_sam3 n | exp003_droid_sam3 rot deg med / p95 | exp003_droid_sam3 trans mm med / p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| same tiles | 0.08 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 | 96 | 0.13 / 0.41 | 1.9 / 5.7 |
| same tiles | 0.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 | 18 | 0.14 / 0.45 | 2.5 / 6.5 |
| same tiles | 2.0 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 | 6 | 0.82 / 1.52 | 14.2 / 24.1 |
| tile set changes | - | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 | 120 | 0.39 / 1.16 | 7.5 / 27.6 |

### Mask comparison (per frame, pooled over every frame of every segment)

Rows: the mask comparisons of every experiment (<candidate>_vs_<reference>); details in each experiment's report.md and masks_*.md.

| comparison | quantity | exp006_sam3_v2 | exp001_sam2_baseline | exp003_droid_sam3 |
|---|---|---|---|---|
| motion_vs_sam2 | reference / candidate | sam2 / motion | - | - |
| motion_vs_sam2 | dilate [px] | 8 | - | - |
| motion_vs_sam2 | segments / frames | 30 / 8972 | - | - |
| motion_vs_sam2 | IoU median / p10 | 0.942 / 0.875 | - | - |
| motion_vs_sam2 | recall median / p10 | 0.969 / 0.933 | - | - |
| motion_vs_sam2 | precision median / p10 | 0.979 / 0.923 | - | - |
| motion_vs_sam2 | extra area (candidate only) median / p90 [% of frame] | 0.14% / 0.67% | - | - |
| motion_vs_sam2 | missed area (reference only) median / p90 [% of frame] | 0.21% / 0.44% | - | - |
| motion_vs_sam2 | DROID-cell IoU median / p10 | 0.979 / 0.888 | - | - |
| motion_vs_sam2 | mean area reference / candidate [% of frame] | 7.20% / 7.19% | - | - |
| motion_vs_sam2 | part area: rig [% of frame] | 2.72% | - | - |
| motion_vs_sam2 | part area: hand_track [% of frame] | 3.39% | - | - |
| motion_vs_sam2 | part area: held [% of frame] | 0.14% | - | - |
| motion_vs_sam2 | part area: hand [% of frame] | 2.49% | - | - |
| motion_vs_sam2 | part area: arm [% of frame] | 3.47% | - | - |
| motion_vs_sam2 | part area: cable [% of frame] | 0.63% | - | - |
| motion_vs_sam2 | segments with IoU median < 0.8 | 0 | - | - |
| motion_vs_sam2 | worst segments (IoU median) | ep20 0.888, ep12 0.902, ep00 0.905, ep09 0.912, ep21 0.926 | - | - |

