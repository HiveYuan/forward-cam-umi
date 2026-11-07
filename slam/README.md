# Tile-free head-cam UMI: SLAM pipeline

Replaces the workspace AprilTag tiles with monocular SLAM on the head camera.
Design: Google Doc "Tile-Free Head-Cam UMI with SLAM". Scale recovery is not
implemented yet (translation metrics and labels use a tile-fitted scale, marked
as an oracle).

Code is here; raw recordings and detection caches are read from the main
head-cam-umi checkout (`HEADCAM_DATA_REPO`); outputs go to `SLAM_WORK`
(see `config.py`). Run modules from the repository root.

Environments: `V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python` (numpy, cv2),
`D=/home/student/miniconda3/envs/droid/bin/python` (DROID-SLAM),
`S=/home/student/miniconda3/envs/sam2/bin/python` (SAM2 via transformers).

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
| 9 | Labels on the 15 fps grid, end-to-end check | `$V -m slam.labels build --session S --ref tiles`; `--ref E3`; `check --ref E3` | `epNN/labels/*.npz`, `eval/labels_E3.json` |
| 10 | Report | `$V -m slam.report --session S` | `eval/report.md` |
| 11 | LeRobot dataset | `scripts/build_dataset.py ... --ref-poses <work>/<session>/segments --ref-run E3 --state-gripper-only` (needs the gripper calibration log and lerobot) | dataset |

Key modules: `droid_masked.py` (mask-aware DROID: BA weights × valid(source) ×
valid(matched target), masked keyframe selection), `relative.py` (relative
10-D actions: 3 translation + 6D rotation + absolute gripper; deployment and
temporal ensembling helpers), `geometry.py`.

DROID parameters: demo defaults at native 960×536, every frame, global BA at the
end. A keyframe-threshold sweep (filter/keyframe 2.4/4.0 vs 1.2/2.0 vs 0.6/1.0)
helped E1 (no masks) but not E2: with motion masks the 1 s rotation error was
0.35° vs 0.33° median at twice the runtime, so the defaults are kept.

Tests: `$V -m slam.tests.test_relative`, `$V -m slam.tests.test_labels`.
