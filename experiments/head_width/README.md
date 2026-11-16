# Gripper width from the head camera (2026-11-12 / 13)

The paper reads the jaw width in the head camera (tails against the gripper-back tags). Our pipeline
used the wrist camera's width in two places:
- the SAM3 masks' held-object gate (`sam3_v2`), which is part of the algorithm;
- the labels' gripper column, which is not used for training or metrics.

Since 2026-11-12 the algorithm reads no wrist-camera data; the wrist camera is a cross-check only.

## Where HHs3's width comes from

Yosub's `docs/RAW_DATA.md` (step 5) says the width comes from the wrist tips, and the paper says it
comes from the tails. Which one did pilot_glove_HHs3 use?

`build_dataset` linearly interpolates the gripper series between the source camera's frames, so its
kinks sit at that camera's frame times.

Over 179 verified HHs3 episodes, 5,462 kinks were located ([`hhs3_width_source.py`](hhs3_width_source.py)).
Distance to the nearest frame:

| camera | median | within 1 ms |
|---|---|---|
| head (b0587b) | 2.9 ms | 29% |
| wrist (fish) | 8.3 ms | 6% (chance) |
| fixed (b0587) | 8.0 ms | 6% (chance) |

So HHs3's gripper is head-camera derived, as the paper says.

## Head-camera width: `slam.head_width`

- **Estimators:** the tail/base estimators of build_dataset's pipeline B on the head detections, one
  calibration per glove unit (`calib/head_width_glove_<unit>.json`).
- **Calibration source:**
  - `holds`: the unit's caliper width holds, the paper's recipe;
  - `hhs3`: for unit yosub, whose holds log is not archived; fitted to HHs3's head-camera width.
- **Holdout** (fit on even HHs3 episodes, score the odd ones; command units, 0.2 = closed, 1.0 = open):

| width | median abs error | p95 | gate (<= 0.45) agreement |
|---|---|---|---|
| head (used) | 0.020 | 0.122 | 96.5% |
| wrist (cross-check only, same 15,333 frames) | 0.023 | 0.138 | 96.6% |

There is no time lag, and a median filter does not help.

## Effect on the pipeline

The masks implementation `sam3_v2_head` is sam3_v2 with the gate on the head width. On the segment
frames (preroll included), the gate changes on 2.5% of frames ([`gate_change.py`](gate_change.py)). The
largest change is glove5 take 2 ep31 (36%), where the head widths (ours and HHs3's) read 0.26-0.5 while
the wrist reads a steady 0.30.

### Adaptive SLAM

Wrist gate (exp029-exp034) -> head gate (exp039-exp044). Label errors are 15 steps (1 s) ahead and use
the Bnet + A-check scale.

| take | rotation 1 s, median (deg) | scale abs error median / p90 | label 1 s median / p90 (mm) | 100-step chunk median / p90 / mean (mm) |
|---|---|---|---|---|
| glove5 take 1 | 0.308 -> 0.309 | 8.7 / 15.3% -> 8.7 / 15.8% | 4.21 / 15.1 -> 4.20 / 15.3 | 5.1 / 18.6 / 8.6 -> 5.1 / 18.5 / 8.7 |
| glove5 take 2 | 0.369 -> 0.366 | 6.1 / 24.7% -> 5.9 / 24.9% | 4.29 / 15.0 -> 4.30 / 17.5 | 5.6 / 14.1 / 8.3 -> 5.5 / 20.6 / 10.4 |
| glove6 take 1 | 0.338 -> 0.344 | 4.8 / 10.4% -> 4.1 / 10.5% | 4.61 / 12.7 -> 4.52 / 12.5 | 6.1 / 12.2 / 7.0 -> 6.0 / 12.2 / 7.0 |
| glove6 take 2 | 0.494 -> 0.489 | 2.7 / 12.2% -> 2.9 / 12.7% | 5.47 / 14.1 -> 5.50 / 14.1 | 6.4 / 10.6 / 6.8 -> 6.4 / 10.6 / 6.8 |
| glove7 | 0.528 -> 0.524 | 3.2 / 9.4% -> 3.1 / 9.3% | 4.35 / 14.6 -> 4.26 / 14.6 | 5.8 / 23.0 / 9.8 -> 5.8 / 23.0 / 9.7 |
| glove8 | 0.440 -> 0.438 | 0.8 / 14.4% -> 0.5 / 11.1% | 4.61 / 10.2 -> 4.60 / 10.7 | 5.1 / 10.2 / 5.9 -> 5.2 / 10.5 / 6.0 |

Unchanged except glove5 take 2, where a few segments got worse (chunk p90 14 -> 21 mm); not yet
inspected.

### Relative-action datasets

exp016 / exp035 / exp045 have the same structure. Errors are SLAM labels vs tile labels, median / p90 in
mm; steps are at 37.5 Hz.

| | 15 steps (0.4 s) | 38 steps (1 s) | 99 steps (2.6 s) |
|---|---|---|---|
| exp016 (5 s start, wrist gate) | 2.77 / 9.9 | 4.81 / 16.2 | 7.39 / 23.9 |
| exp035 (adaptive start, wrist gate) | 2.71 / 9.4 | 4.66 / 14.7 | 6.86 / 20.8 |
| exp045 (adaptive start, head gate) | 2.70 / 9.4 | 4.60 / 14.8 | 6.77 / 20.6 |

Glove slam_valid is 97.2% in all three. The slam_valid and ik_unreached flags are identical: 0 of
88,629 steps differ between exp035 and exp045.

### G-slam48 training

Robot val, best checkpoint:

| run | dataset | robot val |
|---|---|---|
| exp036 | exp035 | 0.4524 |
| exp046 | exp045 | 0.4614 |

The two datasets are nearly identical, so the 2% difference is about the seed-to-seed spread of one
training run.

## Glove units

The first glove (unit `yuan`) has been with Yuan since 2026-10-01. The second (unit `yosub`) recorded
glove5-8, i.e. HHs3; all of this work uses yosub's files. See [`calib/README.md`](../../calib/README.md),
"Glove units".
