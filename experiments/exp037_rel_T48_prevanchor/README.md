# exp037_rel_T48_prevanchor

**What.** exp018_rel_T48 (T48) retrained with `relative.anchor: prev_action`: each chunk is relative to the previous step's target pose (teleop: the command sent at t-1; glove: the pose at t-1) instead of the measured pose at t, with its own normalization (`calib/rel_action_stats_teleop172_prevanchor.json`, same 172 teleop episodes).

**Why.** With relative actions the glove data helped far less than in Yosub's joint-space arms (-6.6% vs -36%). One difference between the two halves: anchored at the measured pose, a teleop chunk starts with the command's lead (rel_0 median 10.8 mm / 3.2°), a glove chunk at zero. With the previous target as anchor, rel_0 is one step of motion in both (3.3 vs 3.1 mm). At deployment the anchor is the last command sent. Compared with exp018 / exp019.
