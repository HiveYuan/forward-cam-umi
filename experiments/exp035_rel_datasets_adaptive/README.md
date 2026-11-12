# exp035_rel_datasets_adaptive

**What.** exp016's two relative-pose datasets rebuilt with the SLAM runs of the adaptive start (`droid_adaptive`, exp029-exp034): `pilot_mix_gHs3_rel_tile_v2` (glove labels from tiles, unchanged except for the `slam_valid` flag) and `pilot_mix_gHs3_rel_slam_v2`. Everything else as exp016.

**Why.** exp016's SLAM labels came from the 5 s start, with DROID failures where the collector turned the head before the episode (2026-11-11/12). The rebuilt SLAM dataset trains G-slam48 again (exp036). The flags `slam_valid` and `ik_unreached` stay identical in both datasets.
