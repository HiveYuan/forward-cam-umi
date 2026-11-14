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

## Proposed next tests (not run)

- **D1:** relative actions plus the current tool pose as state (robot frame, from the tile chain), for
  T48 and G-tile48. Does the glove gain come back?
- **D2:** the same with a tile-free state, for example the pose relative to the episode start or the
  gravity direction. How much survives without tiles? This bounds the SLAM pipeline.
