# exp016_rel_datasets

**What.** Relative-pose versions of Yosub's `pilot_mix_gHs3` (P2): two LeRobot datasets that differ
only in where the glove poses come from.

| dataset | teleop (ep 0-177) | glove (ep 178-377) |
|---|---|---|
| `pilot_mix_gHs3_rel_tile` | FK(action) target, FK(state) anchor | FK(HHs3 joints): Yosub's tile-chain labels |
| `pilot_mix_gHs3_rel_slam` | same | s · T_slam_cam · T_cam_body · inv(T_flange_body) at the HHs3 step times |

Images, timeline (glove `--slow 2.5`), gripper, tasks and episode numbering are the source's, so the
paper's train / val lists (`calib/train_eps_pilot_*.txt`, `meta/val_episodes.json`) apply unchanged.
Per step: `action` (7: x y z, rotation vector, gripper), `observation.state` (gripper), `anchor_pose`
(6), and two flags, the same in both datasets:
- `slam_valid`: the glove step has a SLAM pose (pose samples at most 0.3 s apart, segment scale ok,
  manifest start reliable);
- `ik_unreached`: HHs3's IK did not reach the glove pose (decision 2026-11-11, option b): a joint at
  its range limit, or joint 3 on the stretched-arm plateau (2.9014 rad), or FK more than 30 mm from
  the IK target rebuilt with our tile chain.
Training (P3) turns chunks into relative 10-D actions and chooses the loss masks.

**Inputs.** `calib/hhs3_manifest.json` (`slam.hhs3_manifest`): the source take, episode and start of
every HHs3 episode, from Yosub's `calib/pilot_glove_HHs3_sources.csv`, each checked by matching
FK(HHs3 joints) to our tile-chain tool pose (0.4 mm where the IK converged). SLAM runs: the default
(sam3_v2, DROID E3, Bnet on DA3 metric + K) of exp009, exp010, exp012-exp015. FK: i2rt v1.3.3
(Yosub's), `slam/robot_fk.py`.

```
R=/home/student/miniconda3/envs/lerobot/bin/python
PYTHONPATH=. $R -m slam.hhs3_manifest                                   # -> calib/hhs3_manifest.json
PYTHONPATH=. $R -m slam.rel_dataset build experiments/exp016_rel_datasets/config.yaml
```
