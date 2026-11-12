# Tile-free head-cam UMI: SLAM pipeline

Replaces the workspace AprilTag tiles with monocular SLAM on the head camera.
Design: Google Doc "Tile-Free Head-Cam UMI with SLAM". Metric scale comes from
interchangeable methods in `scale.py` (see "Scale" below); `tiles` is the oracle.

**Experiments (since 2026-11-08):** run everything through the experiment framework,
`python -m slam.run experiments/<exp>/config.yaml` (see `experiments/README.md` and
`slam/pipeline/`). It calls the modules below; their CLIs still work for ad-hoc use.
SLAM backends implement `slam/backends/base.py` (DROID now, AMB3R next). Decisions 2026-11-09: the motion masks are frozen at
`sam3_v2` (exp006's parameters). Decision 2026-11-10: the scale primary is `Bnet` (the metric depth of
DA3METRIC-LARGE with the camera K, no ball; `depth_models.py`) with the A check, replacing `Bsession`
(experiments/cross_session); see `experiments/README.md`, "Current defaults". New in the modules:
scale method `native` and the generic `cross_check` (`scale.py`), chunk-length label
metrics (`labels.py`), `evaluate_session` (`evaluate.py`), `tiles.noise_floor` /
`segment_tile_masks`. `run_droid.py` now writes the backend's `traj.npz` format: it adds
`tracked` and `metric`, and `pose7` is renamed `x_pose7`.

Code is here; raw recordings and detection caches are read from the main
head-cam-umi checkout (`HEADCAM_DATA_REPO`); outputs go to `SLAM_WORK`
(see `config.py`). Run modules from the repository root.

Environments: `V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python` (numpy, cv2),
`D=/home/student/miniconda3/envs/droid/bin/python` (DROID-SLAM),
`S=/home/student/miniconda3/envs/sam2/bin/python` (SAM2 via transformers, pandas),
`R=/home/student/miniconda3/envs/lerobot/bin/python` (lerobot 0.4.4).

| # | Step | Command | Output (`<work>/<session>/...`) |
|---|---|---|---|
| 0 | Tile head poses (GT) | `scripts/head_pose_fast.py <stem> --stride 1 --layout calib/workspace_tiles_pilot_v3.json` | `gt/<stem>_cam_world.json` |
| 1 | Ball poses cam→body | `$V -m slam.ball_poses --session S` | `gt/ball_poses.npz` |
| 2 | Per-episode segments (undistort, crop, 960×536, 5 s preroll) | `$V -m slam.preprocess --session S --jobs 8` | `segments/epNN/{images,calib.txt,frames.json,gt.npz}` |
| 3 | Tile detections, GT noise floor | `$V -m slam.tiles detect --session S`; `... noise ...` | `epNN/tiles.npz`, `eval/gt_noise.json` |
| 4 | Motion masks (SAM2: glove+held object, hand+forearm) | `$S -m slam.masks --session S` | `epNN/masks/motion.npz`, `qa_motion.jpg` |
| 5 | E1 (no masks) | `$D -m slam.run_batch --session S --run E1` | `epNN/slam/E1.npz` |
| 6 | E3 tile masks (needs E1 for occluded tiles) | `$V -m slam.tiles masks --session S` | `epNN/masks/tiles.npz` |
| 7 | E2, E3 | `$D -m slam.run_batch --session S --run E2 --masks motion`; `--run E3 --masks motion,tiles` | `epNN/slam/E{2,3}.npz` |
| 8 | Head-motion evaluation | `$V -m slam.evaluate --session S --runs E1,E2,E3` | `eval/{pairs.csv,summary.json,summary.md}` |
| 9a | Gripper width from the session's own wrist camera, calibrated from repo files only: fingertip-tag separation − closed-jaw separation (from the session) → `gap_to_actuator.json` → `width_to_cmd_glove_v2.json` (needs step 11a first) | `$V -m slam.wrist_width --session S --write-log` | `gt/gripper_wrist.npz`, `gt/glove_log_from_wrist.json` |
| 9a′ | Optional reference: widths of Yosub's built glove set, episodes matched by order/length and verified on images | `$S -m slam.glove_width --session S` | `gt/gripper.npz` |
| 9b | Labels on the 15 fps grid (pose + gripper; `--gripper wrist` default, or `dataset`), end-to-end check | `$V -m slam.labels build --session S --ref tiles`; `--ref E3`; `check --ref E3` | `epNN/labels/*.npz`, `eval/labels_E3.json` |
| 10 | Report | `$V -m slam.report --session S` | `eval/report.md` |
| 11 | LeRobot dataset (action = 7-D tool pose in the SLAM frame + gripper, state = gripper, label_valid) and its check | `$R -m slam.export_lerobot --session S --run E3 --repo R`; `--verify` | `<work>/lerobot/R` |
| 12 | Training-time relative 10-D chunks (LeRobot delta_timestamps) | `slam.relative_dataset.RelativeChunkDataset`; self-check `$R -m slam.relative_dataset ...` | |

| 11a | Wrist-camera tip detections (16h5) | `cd <main checkout> && $V scripts/detect_parallel.py data/raw/S_fish.mkv --workers 20` | `<main>/calib/S_fish_tips16h5_detections.npz` |
| 11b | Same through Yosub's pipeline, gripper from the WRIST camera: `build_dataset.py --grip-from-wrist` fits its tip estimators against the step-9a widths (in place of the unit's caliper width-holds log, which is not archived) | `$R scripts/build_dataset.py --pipeline B --forward <stem> --wrist S_fish --grip-from-wrist --wrist-intrinsics calib/fisheye_glove_yosub_intrinsics.json --log <work>/S/gt/glove_log_from_wrist.json --episode-marks <raw>/S_glove_episodes.json --raw-dir <raw> --det-dir <main>/calib --intrinsics calib/B0587b_f3_intrinsics.json --bundle calib/glove_yosub_dodeca_bundle.json --gripper-bundle calib/glove_yosub_gripper_bundle.json --marker-map calib/marker_map_glove_yosub.json --ref-poses <work>/S/segments --ref-run E3 --state-gripper-only --out R --out-root <dir>` | dataset |
| 13 | Dataset check (either writer) | `$R -m slam.verify_dataset --session S --run E3 --root <dir> --repo R` | |

yam_glove7: the step-9a wrist width, fitted to nothing from Yosub's data, agrees with the
widths of his built glove set on all 26 overlapping episodes (median |err| 0.013, p95 0.105,
corr 0.972, command units, range 0.20-0.78); the closed-jaw offset (16.9 mm) matches the one
implied by his block-grasp anchor (16.4 mm). Both E3 datasets (28 episodes, 2709 frames) pass
`slam.verify_dataset`. With the unit's width-holds log as `--log`, step 11b is exactly
Yosub's glove recipe with the SLAM head chain.

Key modules: `droid_masked.py` (mask-aware DROID: BA weights × valid(source) ×
valid(matched target), masked keyframe selection), `relative.py` (relative
10-D actions: 3 translation + 6D rotation + absolute gripper; deployment and
temporal ensembling helpers), `geometry.py`.
`robot_fk.py` (YAM FK of i2rt's `grasp_site` = the glove labels' tool frame, i2rt's own `Kinematics`
imported from `third_party/i2rt` at Yosub's v1.3.3 (47fee5e, mujoco 3.13.0, mink 1.3.0; lerobot env);
validated against HHs3's IK in `experiments/audits/fk_frame`).
`hhs3_manifest.py` (source take / episode / start of every pilot_glove_HHs3 episode, Yosub's CSV checked
and corrected by FK matching; `ik_flag`) and `rel_dataset.py` (the relative-pose datasets of exp016:
`pilot_mix_gHs3_rel_tile` / `_rel_slam`, flags `slam_valid`, `ik_unreached`).

DROID parameters: demo defaults at native 960×536, every frame, global BA at the
end. A keyframe-threshold sweep (filter/keyframe 2.4/4.0 vs 1.2/2.0 vs 0.6/1.0)
helped E1 (no masks) but not E2: with motion masks the 1 s rotation error was
0.35° vs 0.33° median at twice the runtime, so the defaults are kept.

Tests: `$V -m slam.tests.test_<name>` for pipeline (framework core), scale, analysis,
labels, labels_chunk, report, relative; dataset checks:
`slam.export_lerobot --verify`, `slam.relative_dataset` self-check.

## Scale (`scale.py`, `depth.py`)

One interface, `scale.estimate(segment, run, spec)` / `get_scale(...)`, selected by a
spec string wherever a scale is used (`slam.labels --scale`, `slam.evaluate --scale`,
`slam.report --scale`):

| spec | method | needs |
|---|---|---|
| `none` | s = 1 | – |
| `tiles` | oracle: Umeyama fit to the tile head poses | tile GT (evaluation only) |
| `A` | static ball: windows where the ball centre is static in the world, p_i = R_i b_i + s c_i solved linearly; residual ≤ 5 mm, head baseline ≥ 20 mm; weighted median | ball poses, SLAM |
| `B` / `B:<model>` | metric depth (`depth.py`: `da2-metric-indoor-large` default, `depth-pro`) corrected by the ball (face-centre depths vs network depth), against DROID keyframe depth on mask-valid cells | `$S -m slam.depth --session S --run R [--model M]` |
| `A,B` | fallback chain: A where it succeeds, else B | both |
| `B+Acheck` | main method 2026-11-08 to 2026-11-09: s = B on every segment; A computed where possible and only compared, \|s_A/s_B − 1\| > 10% flags the segment (recorded, nothing changed or dropped) | both |
| `Bsession` (framework only) | **main method (decision 2026-11-09)**, with the A check: B with one ball correction k pooled over the session (median of the per-segment k) instead of each segment's own k (exp005) | both, all segments of the session |

Options of B (keyword arguments of `scale_depth_ball`): `correction=faces|disk`,
`fit=scale|affine`, `depth_window`. Results are cached per segment in
`epNN/scale/<run>_<spec>.json` (use `--overwrite` after changing parameters or upstream
files). Labels built with a non-oracle scale are named `<run>@<spec>` (e.g. `E3@A,B`) and
work with `export_lerobot --run`, `build_dataset --ref-run`.

```
$V -m slam.scale estimate --session S --run E3 --method A
$V -m slam.scale eval --session S --run E3 --methods "A;B;B:depth-pro;A,B"     # vs the oracle
$V -m slam.labels build --session S --ref E3 --scale A,B
$V -m slam.evaluate --session S --runs E3 --scale A,B                            # eval_scale_A+B/
$V -m slam.scale crosscheck --session S --run E3 --method B+Acheck   # eval/scale_E3_B+Acheck.md
```

yam_glove7 E3 with `B+Acheck`: scale |err| median 5.8%, p90 21.4%, bias −5.3% (30/30
segments, 28 with tile GT); A and B both on 9 segments, 3 flagged: ep01 (A wrong, −9.7%),
ep12 and ep15 (B wrong, ≈ −20%). ep09 is not flagged although both are ≈ −16% (shared error).
Labels: tool_t→tool_t+1 s 5.9 / 19.5 mm (median / p90) vs 4.0 / 14.1 mm with the oracle.

yam_glove7, E3 (scale error vs the tile oracle, 28 segments with GT):
A 9/30 segments, |err| median 5.1%, p90 11.1%; B (DA2) 30/30, 5.8% / 21.4%;
B:depth-pro 16.7% / 30.8%; A,B 30/30, 5.4% / 19.0%. Labels with A,B: tool_t→tool_t+1s
position error 5.0 mm median (oracle scale 4.0 mm). The DA2 metric depth compresses the
range in this white scene (true/network depth 0.49 at 0.3–0.6 m, 0.69 at 0.9–1.2 m), so a
single correction factor taken at the ball biases B low by ~5%; an affine fit to the ball
extrapolates worse (12.6%), so the default is a single factor.

