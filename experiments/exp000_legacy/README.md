# exp000_legacy: SAM2 masks + masked DROID-SLAM, yam_glove7 (2026-11-06 to 11-08)

Archive of everything run before the code was restructured into modules + experiments.
It is the reference that later experiments (SAM3 masks, AMB3R) are compared against.

- Code: tag **`legacy-sam2`** = commit `ec10ce2` (branch `slam-pipeline`, pushed to `fork`).
  Every step below can be re-run from that tag with the commands in `slam/README.md`.
- The runs predate `run.json`: no environment snapshot or clean-tree check was recorded.
  The outputs were written over several commits (table at the end); the tag contains the
  final version of every step.
- Large outputs (frames, masks, trajectories, depth, labels) were in
  `work/yam_glove7/` and are not kept in git. `results/` holds the small metric files,
  `logs/` the console logs of the batch runs.

## Data

- Session `yam_glove7` (one take, 30 episodes, 13 min). Head camera stem `yam_glove7_b0587b`
  (B0587, rolling shutter), intrinsics `calib/B0587b_f3_intrinsics.json`, glove unit `yosub`,
  tile layout `calib/workspace_tiles_pilot_v3.json`.
- Segments (`slam.preprocess`): one per episode, from 5 s before its start to its end, every
  frame. Undistorted (alpha = 0, principal point centred), area-resized to 960 px wide,
  cropped to 960×536, JPEG q95. 30 segments, 8972 frames.
- Ground truth: tile head poses (`scripts/head_pose_fast.py --stride 1`); a frame is GT when
  ≥ 2 tiles are seen and the reprojection rms ≤ 5 px (2503 of 5031 in-episode frames).
  Ball poses (`slam.ball_poses`) give cam→body per frame; tool = virtual flange
  (`calib/handeye_glove_yosub.json`).
- GT noise floor (`slam.tiles noise`): 0.13° (same tiles at both ends), 0.39° (tile set changes).

## Groups

| group | SLAM masks | purpose |
|---|---|---|
| static | – (head motion = identity) | lower bound |
| E1 | none | sanity check |
| E2 | motion | tiles still visible |
| E3 | motion + tiles | **main test**, closest to in-the-wild |

All three use the same DROID parameters; they differ only in masks.

## Motion masks: SAM2 (`slam.masks`)

- transformers `Sam2VideoModel`, `facebook/sam2.1-hiera-large` (HF revision `665f8e2`), bf16,
  conda env `sam2` (torch 2.7.1+cu126, transformers 5.20.2).
- Two tracked objects, prompted with **points** (not text), given in the glove body frame and
  projected with the per-frame ball pose every 30 frames:
  `glove` = ball centre + flange point (glove, ball, gripper, held object);
  `hand` = back of the hand, body-frame point `[-0.141, -0.0026, 0.1014]` m (hand, forearm, cable).
  So the prompts depend on the ball pose being detected.
- Propagated forward and backward from the first prompt frame; the union is the mask.
  Mean masked area 7.2% (4.5–10.3% per segment).
- In DROID: dilated 8 px at full resolution; a 1/8-resolution cell is invalid if any of its
  pixels is masked.

## Tile masks (E3 only, `slam.tiles masks`)

Each tile's printed square (75 mm) + 10 mm margin projected with the frame's tile pose; else the
nearest tile pose within 0.5 s with the margin growing 100 mm/s; else the E1 trajectory aligned
to the tile poses by a similarity transform (25 mm margin); plus the detected tag quads.

## DROID-SLAM (`slam.run_droid`, `slam.droid_masked`)

- `third_party/DROID-SLAM` at `2dfd39f` with local build patches (lietorch for sm_86;
  `droid_slam/modules/corr.py` splits the correlation lookup for the int32 limit, output
  identical). Weights `droid.pth` (sha256 `46476ef64cde45a9…`). Conda env `droid`
  (torch 2.5.1+cu124). `torch.manual_seed(0)`; the CUDA kernels are not bitwise deterministic.
- Masks enter BA weights (weight × valid(source cell) × valid(matched cell in the other frame))
  and keyframe selection (mean flow over cells valid in both frames). Images are unchanged.
- Parameters (DROID demo defaults): native 960×536, every frame, buffer = frames + 32,
  beta 0.3, filter_thresh 2.4, warmup 8, keyframe_thresh 4.0, frontend_thresh 16,
  frontend_window 25, frontend_radius 2, frontend_nms 1, backend_thresh 22, backend_radius 2,
  backend_nms 3; global BA at the end (backend 7 then 12 iterations), then trajectory filler.
- Keyframe sweep (`results/eval/keyframe_sweep.md`): denser keyframes help E1 but not E2,
  so the defaults were kept.
- Per segment: ~13 keyframes, ~45 s, peak GPU 14–17 GB.

## Scale (`slam.scale`, `slam.depth`)

| spec | method |
|---|---|
| `none` | s = 1 |
| `tiles` | oracle: Umeyama fit of the SLAM camera centres to the tile head poses (evaluation only) |
| `A` | static ball, point-only: 1 s windows every 0.25 s, accepted if residual ≤ 5 mm and head baseline ≥ 20 mm; weighted median |
| `B` | DA2 metric depth (`depth-anything/Depth-Anything-V2-Metric-Indoor-Large-hf`, rev `d2fc6a9`) on DROID keyframes, corrected by one factor from the ball face-centre depths, vs DROID keyframe depth on mask-valid cells |
| `B:depth-pro` | same with `apple/DepthPro-hf` (rev `de816c8`) |
| `A,B` | A where it succeeds, else B |
| `B+Acheck` | **decision 2026-11-08**: s = B; where A also succeeds, \|s_A/s_B − 1\| > 10% flags the segment (recorded only) |

## Labels and evaluation

- `slam.labels`: tool pose per frame in the SLAM frame, resampled to 15 fps over each episode
  (build_dataset rules: 0.12 s gap tolerance, 70% coverage); gripper width from the wrist camera
  (`slam.wrist_width`). `check`: relative chunk tool_t→tool_t+j vs the tile labels, j = 1..100.
- `slam.evaluate`: pairs (t, t+Δt) with GT at both ends, Δt = 0.08 … 6.67 s; rotation error
  (scale-free), translation and label error with the chosen scale; tracking failure =
  Δt = 0.08 s pairs with rotation error > 2°.

## Key results (E3, all 30 segments)

| | 0.08 s | 0.5 s | 1 s | 2 s | 6.67 s |
|---|---|---|---|---|---|
| head rotation err, median / p95 [deg] | 0.16 / 0.66 | 0.35 / 1.58 | 0.53 / 2.32 | 0.59 / 2.81 | 0.62 / 0.92 |
| (E2) | 0.15 / 0.61 | 0.31 / 1.49 | 0.45 / 2.47 | 0.52 / 3.63 | 0.51 / 0.87 |
| (E1) | 0.24 / 1.26 | 0.60 / 4.46 | 0.85 / 7.88 | 1.11 / 14.80 | 0.98 / 8.62 |

Tracking failures: E1 1.93%, E2 0.04%, E3 0.34%.

Scale vs the tile oracle, `B+Acheck` (28 segments with GT): E3 |err| median 5.8%, p90 21.4%,
bias −5.3%; 3 flagged (ep01: A wrong; ep12, ep15: B wrong); ep09 not flagged (A and B both
≈ −16%). E2: 10.3% / 20.6%; E1: 15.1% / 30.7%.

Label tool_t→tool_t+Δt position error, E3, median / p90 [mm] (15 fps timeline, 989 anchors):

| scale | 0.07 s | 0.53 s | 1.00 s | 2.00 s | 6.67 s |
|---|---|---|---|---|---|
| tiles (oracle) | 1.2 / 3.9 | 3.1 / 11.3 | 4.0 / 14.1 | 5.2 / 15.0 | 5.6 / 7.9 |
| B+Acheck | 1.2 / 3.8 | 3.7 / 13.7 | 5.9 / 19.5 | 7.9 / 27.4 | 6.2 / 15.3 |

## Files

- `results/eval/`: `report.md` (oracle scale, E1–E3), `summary.{md,json}`, `gt_noise.json`,
  `keyframe_sweep.md`, `scale_E3.{md,json}` (A / B / B:depth-pro / A,B vs oracle),
  `scale_E{1,2,3}_B+Acheck.{md,json}`, `labels_<run>[@<scale>].json`.
- `results/B+Acheck_eval/`, `results/eval_scale_A+B/`, `results/eval_scale_B/`:
  `slam.evaluate` + `slam.report` with that scale.
- Not kept: `pairs.csv` (5.8 MB per evaluation, regenerable).
- `logs/`: preprocess, SAM2 masks, E1, E2/E3, keyframe sweep, depth, wrist-tip detection.

## When each output was written

| output | written | commit at that time |
|---|---|---|
| segments, gt.npz | 11-06 21:42–21:44 | committed right after as `2d7e152` (21:52) |
| E1, tile detections, tile masks, SAM2 masks | 11-06 21:58–22:44 | code committed as `9066d38` (22:29) |
| keyframe sweep, E2, E3 | 11-06 23:11 – 11-07 00:17 | `1176633` / `8c6fbac` (22:50 / 23:26) |
| tile labels, gripper widths | 11-07 04:10 | `3e5f88b` |
| depth, scale A/B, A,B evaluations | 11-07 08:08–08:58 | `1431a89` |
| B+Acheck scale, labels, evaluation | 11-08 13:14 | `ec10ce2` |
