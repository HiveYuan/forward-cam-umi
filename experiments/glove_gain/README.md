# Why glove data helps less with relative actions (2026-11-12 / 13)

**The question.** Yosub's joint-space ACT gains 36% robot val from the 194 glove demonstrations at the
48-teleop budget (0.4645 -> 0.2946). Our relative-action ACT gains 6.6% (exp018 -> exp019).

**The answer so far.** The gap is real in physical units, not an artefact of the loss. With joint actions,
glove data cuts the predicted chunk's tool-position error by 26%. With relative actions it cuts it by 4%,
while 124 more teleop episodes cut it by 18%. Relative actions can learn from more data, but not from
this glove data.

## Anchor of the relative actions (exp037 / exp038, test (a))

Using the previous step's target pose (`prev_action`) instead of the current pose as the anchor:

| arm | robot val, current pose | robot val, prev_action |
|---|---|---|
| T48 | 0.490 | 0.480 |
| G-tile48 | 0.458 | 0.455 |

The glove gain is -5.0% with prev_action vs -6.6% with the current pose, a difference under 2% (one
seed). It does not explain the gap. The anchor stays the current pose: anchoring on the policy's own
previous command lets errors accumulate.

## Loss breakdown (robot val, VAE latent 0)

Normalised L1 by action group ([`loss_decomposition.py`](loss_decomposition.py),
[`loss_decomposition.json`](loss_decomposition.json)):

| arm | all | translation (3) | rot6d (6) | gripper (1) |
|---|---|---|---|---|
| T48 (exp018) | 0.554 | 0.409 | 0.657 | 0.371 |
| G-tile48 (exp019) | 0.519 | 0.397 | 0.604 | 0.377 |
| share of the loss | | 22% | 70% | 7% |

- **Rotation dominates.** rot6d carries 70% of the loss, mostly at steps 50-99 (0.94).
- **Glove data helps the near term.** It lowers steps 0-14 by 9-15% but barely changes steps 50-99.
- **The gripper gets worse.**
  - The glove opens to 0.54-0.70 (command units), while teleop opens to 0.88-1.0.
  - The glove gripper also changes value on 75% of steps; the teleop gripper holds still on 71%.
  - Near-term gripper error rises 35-50% with glove data.
  - It is 7% of the loss, so it is not the main cause.

## B: more teleop in relative space (exp047)

| arm | robot val | change | pos mm j0 / j14 / j49 / j99 / chunk mean | rot mean |
|---|---|---|---|---|
| relative T48 (exp018) | 0.4904 | | 8.6 / 33.6 / 70.5 / 143.1 / 78.7 | 18.2° |
| relative T172 (exp047) | 0.4166 | -15.0% | 8.1 / 28.2 / 56.2 / 100.1 / 64.4 | 15.2° |
| relative G-tile48 (exp019) | 0.4582 | -6.6% | 9.0 / 29.3 / 63.8 / 135.5 / 75.3 | 17.1° |

In joint space, 48 -> 172 teleop gives -31.5% (Yosub: 0.4645 -> 0.3179).

## C: Yosub's joint-space arms retrained, errors in the same physical units (exp048 / exp049)

Robot val:

| arm | ours | Yosub's |
|---|---|---|
| joint T48 (exp048) | 0.4578 | 0.4645 |
| joint G48 (exp049) | 0.2908 | 0.2946 |

Both reproduce his values within 1.5%.

`slam.joint_physical` maps the predicted and label joint chunks through the YAM FK (i2rt grasp_site).
The resulting tool-position and rotation errors equal the relative runs' errors, because a common anchor
changes neither.

Robot val, best checkpoint, chunk with VAE latent 0, median per step:

| arm | pos mm j0 | j14 | j49 | j99 | chunk mean | rot mean | gripper |
|---|---|---|---|---|---|---|---|
| joint T48 | 38.7 | 51.7 | 72.2 | 130.3 | 87.8 | 19.0° | 0.122 |
| joint G48 | 25.1 | 36.5 | 50.0 | 105.5 | 65.2 (-26%) | 16.2° | 0.109 |
| relative T48 | 8.6 | 33.6 | 70.5 | 143.1 | 78.7 | 18.2° | 0.123 |
| relative T172 | 8.1 | 28.2 | 56.2 | 100.1 | 64.4 (-18%) | 15.2° | 0.094 |
| relative G-tile48 | 9.0 | 29.3 | 63.8 | 135.5 | 75.3 (-4%) | 17.1° | 0.125 |
| relative G-slam48 (exp046) | 10.1 | 31.2 | 65.0 | 135.7 | 75.7 (-4%) | 17.2° | 0.139 |

## Reading

1. **With teleop only, both action spaces are about equally accurate.** Relative actions are far better
   at the first steps (9 vs 39 mm: the joint-space absolute target is offset). Joint actions are
   slightly better at step 99.
2. **Glove data helps the joint-space policy at every horizon** (-19% to -35%) and the relative policy
   hardly at all, least at the far horizon.
3. **Suspects.** The joint-space policy has two things ours lacks:
   - **its state:** the joint angles (proprioception); ours is the gripper only;
   - **absolute targets:** the tile-registered glove data gives absolute targets in the robot frame
     (e.g. where the bin is), the same as teleop.

   Relative actions have to infer the remaining motion from the image, where glove and teleop look
   different.

## State tests D1 / D2 (2026-11-13 / 14)

D1 gives the relative policy the current tool pose as state; the D2 variants do so without tiles.

| test | state (10-D unless noted) | runs | where the pose comes from |
|---|---|---|---|
| D1 | tool pose in the robot base + gripper | exp050 (T48), exp051 (G-tile48) | FK; glove: the tile chain (tiles in training labels only; at deployment FK) |
| D2a | pose relative to the episode start + gripper | exp052, exp053 (G-slam48, SLAM v3) | FK / SLAM, no tiles |
| D2c | tool pose in the head camera + gripper | exp054, exp055 | teleop: the SO-101 positioner's joints (slam.cam_state); glove: the ball; no tiles |
| D2d | D2a + D2c + gripper, 19-D | exp056, exp057 | both |

Two caveats:
- **Episode starts:** teleop episodes start at the robot's home pose (spread 1 cm), glove episodes 14 cm away on average
  (spread 10 cm). So the start-relative pose means different things in the two halves.
- **Missing positioner log:** yam_head13 has none, so D2c / D2d use 38 of the 48 teleop episodes and 4 of the 6
  robot-val episodes (15, 52, 73, 84).

### Six val episodes

D1, the first test:

| arm | robot val | pos mm j14 / j49 / j99 / chunk mean | rot |
|---|---|---|---|
| relative T48 + pose (exp050) | 0.4873 | 33.3 / 71.6 / 163.5 / 81.7 | 18.2° |
| relative G-tile48 + pose (exp051) | 0.4039 | 31.3 / 55.3 / 106.8 / 63.2 | 14.5° |
| joint G48, Yosub's arm (exp049) | 0.2908 | 36.5 / 50.0 / 105.5 / 65.2 | 16.2° |

The glove gain is -23% in chunk mean position and -35% at step 99, where it was -4% with the gripper state.

### The four val episodes every arm can use

Best checkpoints re-evaluated on episodes 15, 52, 73, 84. These episodes are easier: all numbers are lower than on six.

| arm | glove labels | robot val | pos mm j14 / j49 / j99 / chunk mean | rot | gripper |
|---|---|---|---|---|---|
| Yosub's G48, joint space (exp049; paper 0.295 on 6) | tiles | 0.206 | 33.6 / 43.4 / 77.5 / 52.5 | 13.2° | 0.083 |
| joint T48 (exp048) | – | 0.275 | 43.0 / 50.2 / 87.4 / 63.8 | 15.5° | 0.095 |
| relative T48, gripper (exp018) | – | 0.412 | 32.5 / 74.2 / 121.1 / 72.3 | 15.7° | 0.112 |
| relative G-slam48, gripper (exp046) | SLAM | 0.365 | 31.0 / 60.3 / 111.9 / 68.6 | 14.4° | 0.133 |
| D1 G-tile48 (exp051) | tiles | 0.326 | 30.9 / 55.5 / 96.3 / 58.5 | 12.1° | 0.102 |
| D2a G-slam48 (exp053) | SLAM | 0.342 | 36.2 / 61.5 / 88.6 / 63.2 | 13.0° | 0.096 |
| D2c G-slam48 (exp055) | SLAM | 0.323 | 31.9 / 65.6 / 116.0 / 67.1 | 11.8° | 0.103 |
| D2d G-slam48 (exp057) | SLAM | 0.328 | 33.1 / 48.5 / 93.9 / 57.2 | 13.6° | 0.097 |

The glove gain (T48 -> G48 of the same state) on these episodes:

| state | val | chunk mean position | step 99 | rotation |
|---|---|---|---|---|
| gripper | -11% | -5% | -8% | -8% |
| D1 | -16% | -20% | -21% | -18% |
| D2a | -17% | -20% | -26% | -15% |
| D2c | -16% | -5% | -8% | -18% |
| D2d | -17% | -21% | -30% | -10% |
| joint space | -25% | -18% | -11% | -15% |

### Reading

- **D2a** recovers D1's position gain without tiles, and has the best step-99 error of the relative arms. Its T48
  baseline is worse, though.
- **D2c** gives the best rotation of all arms but no position gain. The positioner keeps the gripper at the same place
  in the image, so the camera-frame pose mostly carries the tool's orientation relative to the view.
- **D2d** (both states) is the best relative arm: 57.2 mm, level with D1 (58.5 mm, tiles; one seed each, so the
  difference is within the spread between runs) and 52.5 mm for Yosub's joint-space G48. It has the best step-49 error
  of the relative arms (48.5 mm against 43.4 mm for Yosub's) and the largest glove gain (-21% chunk mean, -30% at
  step 99). Its rotation (13.6°) is worse than D2c's, and its step 99 slightly worse than D2a's.
- **Best tile-free arm:** D2d (exp057). It needs the positioner's camera pose at deployment; D2a (exp053) does not.

## Deployment (slam.deploy_rel, eval_grid)

**At each tick:**
1. The state is built exactly as in training (StateBuilder).
2. The chunk's relative actions become targets in the robot base: FK at prediction time . rel_j.
3. Every chunk that predicted the tick is ensembled in the base frame with ACT's weights. LeRobot's own ensembler is
   not used, since it would average relative vectors from different anchors.
4. grasp_site IK, warm-started at the measured joints, gives the joint command.

eval_grid runs relative arms through RelativeRunner. The ARMS entries are rel_Gslam48 (exp046), rel_Gtile48_pose
(exp051) and rel_Gslam48_start (exp053).

**Offline replay** of exp053 on val episode 15:
- The states equal the training states exactly.
- IK converges on all 223 ticks, at 1 ms each.
- The newest chunk's target is 7.9 mm (median) from the teleoperator's recorded command, the policy's own accuracy.
- Ensembling the full chunk in open loop lags: 56 mm, or 18 mm over 15 steps. The setting has to be chosen on the robot.

**Not wired yet:** the camera-frame states (D2c / D2d) need the positioner's live camera pose at deployment.

## Proposed next tests (2026-11-13; D1 and D2 run since, above)

- **D1:** relative actions plus the current tool pose as state (robot frame, from the tile chain), for
  T48 and G-tile48. Does the glove gain come back?
- **D2:** the same with a tile-free state, for example the pose relative to the episode start or the
  gravity direction. How much survives without tiles? This bounds the SLAM pipeline.
