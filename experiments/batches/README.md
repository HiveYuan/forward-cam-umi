# Batches: collected sessions -> trained policy (`python -m slam.ingest`)

A batch file says which collected sessions to process and what to train on them. It is data, not
code: a new collection needs only a new batch file. `slam/ingest.py` documents the stages; its
`DEFAULTS` hold every default value.

```
python -m slam.ingest start  experiments/batches/<batch>.yaml   # detached; log work/ingest/<batch>/ingest.log
python -m slam.ingest status experiments/batches/<batch>.yaml
python -m slam.ingest run    experiments/batches/<batch>.yaml   # the same in the foreground
```

Every stage is skipped when its outputs exist, so `start` again after a stop or a fix continues
where the batch was. Configs, results and the report are committed locally; nothing is pushed.

## The file

```yaml
batch: yuan_slam_b1                        # name: work/ingest/<batch>/, experiments/batches/<batch>/
description: ...
bucket: gs://yuan-headcam-umi-collect/yuan # <bucket>/data/raw, <bucket>/calib (pulled, never written)
sessions: [yuan_slam_01, ...]              # or {glob: "yuan_slam_*"}: every matching session in the bucket
overrides:                                 # review decisions, per session
  yuan_slam_06: {include: [2, 14, 17]}     #   episodes added back (field-QC false FAILs) / exclude: removed
wrist: crosscheck_transient                # crosscheck_transient | keep | none
raw_policy: keep                           # keep | delete_after_export (a <video>.fingerprint keeps reruns possible)
min_free_gb: 40
gates: {label_err_1s_mm_max: 8.0, slam_valid_min: 0.9, grip_coverage_min: 0.7, max_rejected_fraction: 0.3}
accept_held: []                            # sessions held by a gate that a person reviewed and accepts
slam: {run: E3, masks: sam3_v2_head, gripper: head, target_fps: 26.27}
dataset:
  base: {repo: pilot_mix_gHs3_rel_slam_v3, root: <work>/lerobot/pilot_mix_gHs3_rel_slam_v3, glove_first_episode: 178}
  out: pilot_mix_gHs3_yuan_rel_slam_v1     # the training dataset written: base + the batch's shards
  fps: 15.0, slow: 2.5                     # the HHs3 timeline: step j = t_start + j / 37.5 s
  bridge_s: 0.3                            # slam_valid: bracketing SLAM poses at most this far apart
  gripper_median_s: 0.3                    # head-width median filter
  grip_label_tol_s: 0.12                   # gripper coverage = steps with a head-width sample this close
  val_fraction: 0.1                        # per session, held out of training: "collected val"
train:                                     # arms: the template's config with the new dataset and episodes
  - {exp: exp058_..., template: exp053_rel_Gslam48_startstate}
compare: [exp052_rel_T48_startstate]       # earlier arms shown in the report (relative ones are also
reference: exp049_joint_G48                #   evaluated on the collected val); Yosub's paper arm
```

## What a batch does with the data

- **Episodes.** Each session's experiment config keeps the episodes that passed field QC and the
  session's exclusions, plus `overrides`. A session whose config equals an existing experiment's
  reuses it (and its SLAM results).
- **Gates.** An episode is dropped when it has no SLAM pose, its scale failed, or its head-width
  gripper covers under 70% of its steps (build_dataset's `min_coverage`). A session is held when its
  median label error at 1 s (vs the tile GT, sessions with tiles only) is over 8 mm, its SLAM-valid
  share under 90%, or it lost more than 30% of its episodes. Held sessions wait for `accept_held`.
- **Shards and mix.** Each session becomes a LeRobot shard with the base dataset's features; the mix
  is the base (unchanged, same episode indices) + the shards. `val_fraction` of each session's
  episodes, evenly spread, form `meta/val_episodes_collected.json` and are left out of training.
- **Training.** Each arm copies its template's config (stats, masks, state, Yosub's settings) and adds
  the collected training episodes to the template's episode list. `slam.val_rel` reports robot val,
  glove val and collected val; the template and the `compare` arms are evaluated on the collected val
  too, so the report shows what the new data changed.
