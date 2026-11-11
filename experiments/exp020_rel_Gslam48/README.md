# exp020_rel_Gslam48

**What.** ACT with relative actions (P3): 48 teleop + 194 glove episodes (the paper's mix_gHs3_48 list), glove labels from SLAM (sam3_v2, DROID E3, DA3 + K Bnet).
Datasets from exp016; training through Yosub's lerobot with his hyperparameters (`slam.train_rel`):
10-D actions rel_j = anchor_t^-1 · pose_{t+j}, j = 0..99 (translation, 6D rotation, absolute gripper),
state = gripper, one normalization for every arm (`calib/rel_action_stats_teleop172.json`: the 172 teleop
training episodes). The glove arms mask `slam_valid` and `ik_unreached` steps (and skip masked anchors);
both glove datasets carry identical flags, so G-tile and G-slam train on the same anchors.

**Why.** T48 vs G-tile48 vs G-slam48: does glove data still help with relative actions, and what does
replacing the tiles by SLAM cost? Same robot-val episodes, labels and normalization for all three, so
their robot-val losses compare directly (not with the paper's joint-space losses).

```
R=/home/student/miniconda3/envs/lerobot52/bin/python
PYTHONPATH=. $R -m slam.train_rel experiments/exp020_rel_Gslam48/config.yaml
PYTHONPATH=. $R -m slam.val_rel experiments/exp020_rel_Gslam48/config.yaml        # -> results/val.{json,md}
```
