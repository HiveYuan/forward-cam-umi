# calib/ — the files the paper's chain used

Measured configs and fitted calibrations for the units we built. A new unit
gets its own files (copy, re-measure, rename); nothing here is nominal.
Detection caches (`*_detections.*`), per-frame camera-pose solves
(`*_cam_world.json`) and `tmp_*` are regenerable and stay out of git.

## Cameras

| file | what |
|---|---|
| `B0587_intrinsics.json` | fixed forward B0587 4K (ablation camera) |
| `B0587b_intrinsics.json`, `B0587b_f3_intrinsics.json` | the head camera (second B0587); `_f3` is the focus setting used for every head session since 2026-10-09 |
| `fisheye_glove_yosub_intrinsics.json`, `fisheye_intrinsics.json` | the glove's wrist fisheye (ablation) and the robot's |
| `*.example.json` | format examples for `cameras.json` and the robot bundles |

## Glove units (physical glove <-> file names)

Each glove is its own print: its calipers, bundles and tool frame belong to it alone. Unit names follow
who held the glove when the files were first written (2026-10-05). The yosub_spring glove (2026-11-02) is a
third unit, not listed here.

| unit | physical glove | timeline | files |
|---|---|---|---|
| `yuan` | the first glove, built by Yosub | Yosub's only glove until 2026-10-01 (calipered 2026-09-28); with Yuan since 2026-10-01 | in the repo: `marker_map_glove_yuan.json` (the 09-28 calipers, authoritative) and `tags36h11_yuan.json`. Missing: ball / gripper-back bundles, tool frame (`handeye_glove_yuan`), width-holds calibration |
| `yosub` | the second glove: Yuan's parts, assembled by Yosub after 2026-10-01 | calipered 2026-10-05; recorded glove_cal_yosub and yam_glove1-4 (10-06/07), yam_glove5 (10-08) and yam_glove6-8 (10-15), i.e. pilot_glove_HHs3 and the paper | everything `*_glove_yosub*` / `glove_yosub_*`, plus `head_width_glove_yosub.json` |

Pitfall (Yuan's macOS work, 2026-10-13): that glove was the first glove, unit `yuan`. It was recorded and
re-measured under the name `yosub` (`marker_map_glove_yosub.local.json`, the `glove_yosub_width_verify_*` and
`glove_yosub_task_smoke_*` recordings) because "the glove is Yosub's" was read as unit yosub. Those files belong
to unit `yuan`. Their re-measured sizes (ball 14.6 mm, ...) are not used; Yosub's 09-28 calipers stand (decision
2026-11-12).

## Marker geometry

| file | what |
|---|---|
| `marker_map_glove_{yosub,yuan}.json`, `tags36h11_{yosub,yuan}.json` | calipered marker sizes per glove unit and per tile print |
| `dodeca_bundle_ideal.json` | the robot ball's face layout (dodecahedron prior) |
| `glove_yosub_dodeca_bundle.json`, `glove_yosub_gripper_bundle.json` | the glove ball's faces and the gripper-back markers in its body frame |
| `gripper_bundle.json`, `gripper_bundle_yam_head14_b0587b.json` | the robot's gripper-back markers; the second solved from the head14 session with the head camera |
| `marker_map_v3.json` | robot-rig marker sizes |

## Frames

| file | what |
|---|---|
| `handeye.json`, `handeye_twin.json`, `handeye_yam_he7.json` | forward-camera hand-eyes (T_cam<-base, T_flange<-body) from `handeye.py` |
| `handeye_glove_yosub.json` | the glove ball's virtual-flange transform (`glove_tool_frame.py`) |
| `eef_target.json`, `eef_target_glove_yosub.json` | the tool point in the ball's body frame (robot, glove) |
| `workspace_tiles_pilot{,_v2,_v3}.json` | tile layouts; v3 (2026-10-16, refit from head14 single-tile poses) is the paper's |
| `base_world_20261015.json`, `base_world_v3_20261016.json` | robot base <-> tile world from the head camera (`base_world_fit.py`); v3 is the paper's (6.5 mm / 1.55° median over 5065 frames) |
| `forward_cam_world_*.json` | fixed camera -> tile world per rig state (ablations and glove pose fallback) |
| `head_pose_median.json`, `head_pose_episode_median.json` | the collector's median head pose in the tile frame: where the positioner parks |

## Viewpoint model and positioner

| file | what |
|---|---|
| `head_residual_glove5.npz` | (glove pose, head pose) pairs from the glove5 sessions, neutral head frame (`head_residual_data.py`) |
| `head_residual_model.json` | the ridge viewpoint model (`head_residual_fit.py --save`); held-out 46 mm / 5.4° median |
| `so101/so101_{new,old}_calib.urdf` | SO-101 URDFs used by the kinematic fit |
| `so101_cam_poses_20261014_103556.json` | the 60 (joints, tile-solved camera pose) pairs behind the fit |
| `so101_cam_kin.json` | the fitted positioner kinematics (7 mm / 0.7° residual) |
| `so101_cam_rest.json`, `so101_cam_park_seed.json` | rest pose and IK seed for parking |
| `forward_ref_20261012.png` | reference frame for putting the fixed camera back (`camera_realign.py`) |

## Jaw width and IK

| file | what |
|---|---|
| `gap_to_actuator.json` | caliper mm -> YAM gripper actuator units (robot bench, `gap_bench.py`) |
| `width_to_cmd*.json` | label width -> gripper command maps used by `build_dataset.py --grip-map`; `_glove_v2` is the paper's |
| `head_width_glove_<unit>.json` | the unit's head-camera jaw-width estimators (`slam.head_width fit`): tails/bases -> width, from the unit's caliper width holds (`--source holds`) or, for yosub, pilot_glove_HHs3's head-camera width (`--source hhs3`); `_holdout` = even/odd episode check |
| `ik_seed_yam.json`, `robot_joint_prior.json` | IK start posture and the teleop posture prior (`free_base.py`) |

## Episode lists

`train_eps_pilot_<arm>.txt` are the training-episode lists behind the paper's
arms (`head_Hgt`, `mix_gHs3`, `head_Hgt48`/`head_Hgt_48`, `mix_gHs3_48`,
`mix_FA`, `head_HH2`, `mix_FB`, `mix_gHA`) and the intermediate rounds;
`head_round_orders.json` is the per-scene arm order of the rollout grid.
