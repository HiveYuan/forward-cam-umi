# exp002_sam3_masks: report (variant main)

30 segments. No SLAM runs (no head-motion evaluation); mask comparison only: sam3 vs sam2.

## Mask comparison: sam3 vs sam2 (reference)

8972 frames of 30 segments. Per frame, then pooled over every frame of every segment. IoU = intersection / union (1 when both masks are empty); recall = share of the reference pixels the candidate covers; precision = share of the candidate pixels inside the reference; extra / missed area = candidate-only / reference-only pixels as a share of the frame; DROID-cell IoU = IoU of the 1/8-resolution cells DROID ignores, each mask dilated by 8 px at full resolution first (a cell is ignored when any of its pixels is masked: slam.droid_masked.valid_grid). An empty denominator counts 1 (two empty masks: IoU 1; empty reference: recall 1; empty candidate: precision 1), so n = frames. Per segment: `masks_sam3_vs_sam2.md`.

| quantity | n | median | p10 | p90 | mean |
|---|---|---|---|---|---|
| IoU | 8972 | 0.932 | 0.715 | 0.966 | 0.880 |
| recall (share of the reference covered by the candidate) | 8972 | 0.969 | 0.936 | 0.983 | 0.953 |
| precision (share of the candidate inside the reference) | 8972 | 0.970 | 0.793 | 0.990 | 0.920 |
| extra area: candidate only [% of frame] | 8972 | 0.21% | 0.06% | 1.53% | 0.72% |
| missed area: reference only [% of frame] | 8972 | 0.21% | 0.11% | 0.43% | 0.33% |
| DROID-cell IoU (masks dilated by 8 px) | 8972 | 0.968 | 0.688 | 0.993 | 0.899 |

Mean masked area [% of frame]: sam2 (reference) 7.20%, sam3 (candidate) 7.59%.

| sam3 part | mean area [% of frame] |
|---|---|
| hand | 3.06% |
| arm | 4.05% |
| cable | 0.98% |
| glove | 2.87% |

Parts may overlap; their union is the candidate mask.

Segments with IoU median < 0.8: ep04, ep08, ep18 (3 of 30).

Worst segments (IoU median): ep18 0.773, ep04 0.775, ep08 0.796, ep00 0.819, ep03 0.824.

Overlay images (not copied into results/): `main/overlays/sam3_vs_sam2/` in the experiment's work run directory `<work>/runs/exp002_sam3_masks/` (<work> = `/home/student/yuanliu-hawaii/work`), 120 images: 60 evenly spaced, 60 lowest-IoU; candidate parts filled in distinct colours, reference outlined in white; `index.json` lists file, segment, frame i, IoU and kind.

