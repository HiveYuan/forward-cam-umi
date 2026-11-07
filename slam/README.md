# Tile-free head-cam UMI: SLAM pipeline

Replaces the workspace AprilTag tiles with monocular SLAM on the head camera.
Design: Google Doc "Tile-Free Head-Cam UMI with SLAM".

Code is here; raw recordings and detection caches are read from the main
head-cam-umi checkout (`HEADCAM_DATA_REPO`); outputs go to `SLAM_WORK`
(see `config.py`).

| Step | Command | Output |
|---|---|---|
| Ball poses (cam→body per frame) | `python -m slam.ball_poses --session yam_glove7` | `<work>/<session>/gt/ball_poses.npz` |
| Tile head poses (ground truth) | `scripts/head_pose_fast.py` (existing), copied to `gt/` | `<work>/<session>/gt/<stem>_cam_world.json` |
| Per-episode segments | `python -m slam.preprocess --session yam_glove7 --jobs 8` | `<work>/<session>/segments/epNN/` |

Run modules from the repository root with `/home/student/yuanliu-hawaii/.venv-headcam/bin/python`.
