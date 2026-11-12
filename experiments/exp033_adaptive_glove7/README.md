# exp033_adaptive_glove7

**What.** The adaptive SLAM start, now the default (`droid_adaptive`: DROID from the segment's 5 s preroll; re-run from 1 s before the episode where the first run turns faster than 120°/s before the episode), on glove7, with DA3 metric + K Bnet, the A check, labels and the head-motion evaluation.

**Why.** Decision 2026-11-12 from exp027_preroll_glove7: fast pre-episode head turns make DROID initialize badly; the short start only where a turn is seen fixed those segments without the accuracy loss of a short start everywhere. DROID is deterministic on this GPU, so each segment should equal exp027_preroll_glove7's E3 (no turn) or E3p1 (turn): checked after the run. Its trajectories feed the rebuilt relative-action datasets (exp035).
