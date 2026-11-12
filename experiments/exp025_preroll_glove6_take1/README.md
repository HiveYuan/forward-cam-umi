# exp025_preroll_glove6_take1

**What.** DROID E3 on glove6 take 1 (exp012_glove6_take1) with the backend started 5 s (the default so far, cached), 2 s and 1 s
before the episode start (`droid_preroll`, `preroll_s`). Frames, masks and tile masks are unchanged; frames
before the cut get no pose. Each run gets DA3 metric + K Bnet with the A check, labels and the head-motion
evaluation, so the three are compared on the same episodes.

**Why.** The same test as exp023/exp024 on the other sessions (they have fewer fast pre-episode turns). glove5 has the largest DA3 scale errors (2026-11-11). Every episode with a scale error above 50%
had a fast head turn (> 120°/s) in the 5 s before the episode (looking away and back, likely to the
terminal where episodes are marked), and DROID initialized on it: its trajectory got spurious
translations (e.g. glove5 take 2 ep13: 21 SLAM units of path, the tile-fitted scale 0.024). Before the
episode the head is mostly still (57% of segments have no keyframe in its last second), so starting the
backend 1-2 s before the episode should initialize it on the task's own motion. To check: scale error,
label error (incl. the episode's first second) and failures vs the 5 s runs.

The sam3_v2 motion masks are recomputed here (same parameters; masks_sam3v2.py changed in 0160981 with
bit-identical outputs, so the cached ones carry another key), hence the 5 s run as well (user decision 2026-11-11).
