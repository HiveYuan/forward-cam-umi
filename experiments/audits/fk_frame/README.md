# P1: robot FK and the glove tool frame

**Question.** The relative-pose datasets need teleop tool poses from the robot's joints (FK) in
the same tool frame as the glove labels. Is our glove tool frame the robot's FK frame, and which
FK / hand-eye / base calibration did Yosub's glove dataset use?

**FK.** `slam/robot_fk.py` (`YamFK`) wraps i2rt's own
`Kinematics(combine_arm_and_gripper_xml(YAM, NO_GRIPPER), "grasp_site").fk`, the same model
build_dataset and evaluate_yam use. i2rt is imported from `third_party/i2rt` at 0b475453 (v1.4.1).
The YAM model, `no_gripper.xml` and the yam block of `no_gripper.yml` are unchanged since v1.3.6
(2026-09-17); before that, only rounding changed. So the FK does not depend on which October
version Yosub ran.

**Test** (`check.py`). `pilot_glove_HHs3`'s joint actions are build_dataset's IK of the tile-chain
glove pose:

    F = inv(T_world_base) · T_world_body · inv(T_flange_body)    for grasp_site

So `FK(q_HHs3)` should reproduce our own tile-chain tool pose,
`T_base_world · T_world_cam · T_cam_body · inv(T_flange_body)`, at the HHs3 step times
`t_start + j / 37.5 s` (`--slow 2.5`). For every HHs3 segment of glove8, glove7 and glove6 take 1,
the source episode (expected ± 3) and start offset are searched. Steps whose IK solution has a
joint at the model's range limit are kept apart (see below).

## Result

52 HHs3 segments matched: glove8 4/4, glove7 21/30, glove6 take 1 27/30. All match at offset 0
except one split: glove6 ep13 is HHs3 46 and 47, the latter starting 6.08 s in. HHs3 64 and 65 are
glove6 take 2.

| hand-eye (T_flange_body) | absolute pos mm | absolute rot ° | relative 0.4 s pos mm | relative 1 s pos mm | relative 1 s rot ° |
|---|---|---|---|---|---|
| **handeye_glove_yosub** (ours) | **0.38 / 1.79** | **0.04 / 0.15** | **0.62 / 3.08** | **0.59 / 3.00** | **0.06 / 0.23** |
| handeye_glove_yosub_spring | 36.3 / 36.8 | 33.5 / 33.6 | 19.2 / 52.8 | 50.2 / 112.4 | 7.1 / 22.9 |
| handeye (robot ball) | 261 / 262 | 164 / 164 | 100 / 234 | 257 / 500 | 14.4 / 68.5 |

Median / p90 over 7,913 steps (the tool moves 120 mm in 1 s at the median).

- **Frame confirmed.** Our FK, `grasp_site`, `handeye_glove_yosub.json` and
  `base_world_v3_20261016.json` are exactly what HHs3 was built with. The residual is the IK
  tolerance (1 mm / 0.57°). For teleop the tool pose is `FK(q)[grasp_site]` with no extra offset,
  because our labels already include `inv(T_flange_body)`.
- **HHs3 joint labels are not the glove pose at joint limits.** 5,180 of 50,014 HHs3 steps (10.4%)
  have an IK joint at the model's range limit: joint 3 at π (2,152 steps), joint 4 at −1.693
  (2,049), joint 6 at ±2.094 (1,371). There, FK is off the glove pose by 67 / 221 mm and
  0.8 / 1.7° (median / p90, 706 matched steps), so the target was out of the robot's reach.
- **Our strict tile chain covers only 54% of HHs3's steps.** It needs ≥ 2 tiles and bridges gaps
  of up to 0.5 s; Yosub's chain also chains single-tile frames. The 9 unmatched glove7 and
  3 unmatched glove6 segments are segments where our chain has no or too few poses (e.g. glove7
  ep06 = HHs3 10: 183 vs 182 steps, 0 tile poses of ours). They are not wrong mappings.
- **Teleop.** FK(action) vs FK(state) is closest at a lag of 1–2 steps (9.6 mm): the action is the
  commanded follower target and leads the encoders by about 0.1 s. Teleop and glove tool
  positions cover the same workspace in the base frame (`results.md`).

These answer two of the questions to Yosub ourselves: the hand-eye file (`handeye_glove_yosub`)
and whether the i2rt version matters for FK (it does not).

```
R=/home/student/miniconda3/envs/lerobot/bin/python      # + mujoco, mink, python-can, tyro, crcmod-plus (2026-11-10)
PYTHONPATH=. $R experiments/audits/fk_frame/check.py      # -> results.json, results.md (~2 min, CPU)
$R -m slam.tests.test_robot_fk
```
