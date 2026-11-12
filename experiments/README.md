# Experiments

Every experiment is one directory `experiments/expNNN_<name>/` and one command:

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/expNNN_<name>/config.yaml            # run (or resume) it
$V -m slam.run experiments/expNNN_<name>/config.yaml --dry-run  # plan: cache keys, what is cached
$V -m slam.run ... --repro slam.E3                              # also recompute slam.E3 once and compare
```

| file | written by | in git |
|---|---|---|
| `config.yaml` | you: data, every step's implementation and **all** parameters, model revisions / weight hashes | yes, committed before running |
| `README.md` | you: what and why | yes |
| `run.json` | `slam.run`: git commit and clean flag, full command, package snapshot of every environment used, weight hashes, data fingerprints, GPU, start/end, seeds, cache keys, per-step timing; one entry per invocation | yes |
| `results/` | `slam.run`: `metrics.json` (canonical numbers), `report.md`, scale/labels/eval md+json, `repro.{md,json}` | yes |

Rules (enforced by `slam.run`):
- The config must be committed and the work tree clean, except this experiment's `results/`
  and `run.json` (`--allow-dirty` only for tests; it is recorded).
- An experiment that already ran is never changed: running it again with a different config,
  or re-running a completed one at another commit or with other cache keys, is refused.
  Change something = new number. Resuming a failed run is allowed; so is re-running a
  completed one unchanged (e.g. to add `--repro`). One invocation per experiment at a time.
- GPU steps take a lock file (`<work>/locks/gpu.lock`) so two runs never share the card, then
  wait for enough free memory (DROID 18 GB, SAM2 12 GB, depth 6 GB).
- A config must list every parameter of every implementation (missing or unknown keys are
  errors), so the config alone says what ran.
- `tiles` scale is the evaluation oracle; it cannot be a run's scale method.

## How it works (`slam/pipeline/`)

Steps and their implementations (`registry.py`; the config picks one per step):

| step | implementations | env | output |
|---|---|---|---|
| preprocess | `undistort_crop` | venv | frames, per-segment GT slices |
| tiles | `apriltag_36h11` | venv | tile detections (evaluation GT) |
| masks (named) | `sam2_points`, `sam3_text_points`, `tile_geometry` | sam2 / sam3 / venv | `masked.npz` |
| slam (named runs) | `droid` (backend interface `slam/backends/base.py`, AMB3R next) | droid | `traj.npz` |
| depth | `hf_depth` (DA2 metric, Depth Pro); `unidepth_v2`, `metric3d_v2`, `da3_metric`, `moge2` (take K); `depth_pro_f` (Depth Pro with K) | sam2 / mdepth / sam2 | keyframe depth for scale B |
| mask_compare | `impl_mask_compare.py`: mask sets vs a reference (IoU, recall, precision, extra / missed area, DROID-cell IoU) | venv | `masks_<cand>_vs_<ref>.{json,md}`; overlays in `<work>/runs/<exp>/<variant>/overlays/` |
| error_decomp | `impl_error_decomp.py`: label error with the head rotation and/or scale replaced by the tile GT | venv | `errdecomp_<run>.{json,md}` |
| scale | methods of `slam/scale.py`: `none`, `native`, `A`, `B`, `Bsession`, `Bnet`; primary + checks | venv | per-segment s, flags |
| labels | `slam/labels.py` | venv | 15 fps tool poses, error vs tiles, chunk metrics |
| evaluate | `slam/evaluate.py`, `slam/tiles.py noise` | venv | head-motion metrics vs tiles |
| report | `impl_report.py` | venv | `results/` |

The orchestrator runs in `.venv-headcam` and starts each step as a subprocess worker in the
step's environment (`envs.py`).

**Cache.** Producer outputs (frames, masks, trajectories, depth) live in
`<work>/cache/<step>/<key>/epNN/`. The key hashes:
- the implementation, its full parameters, and the keys of its inputs;
- the fingerprints of the data files it reads (raw video, calibration, GT);
- its code: the Python files it runs, hashed as syntax trees, so comments and docstrings don't
  count; compiled extensions; the third-party checkouts with their local patches, including
  submodules;
- the package versions and Python version of its environment;
- external tools (ffmpeg).

Two things are left out on purpose: names in the config (`E3`, `motion`) and the weights' file
path (only their sha256). Experiments with the same upstream configuration therefore share the
cache, while any change to code, parameters, data or environment gets a new key. A segment directory appears only when complete
(atomic rename), so an interrupted run resumes where it stopped. Analysis (scale, labels,
evaluation) is small and recomputed per experiment in `<work>/runs/<exp>/<variant>/`.

**Reproducibility tolerance.** `--repro slam.E3` recomputes a node under a cache tag, reruns
everything downstream, and compares with the first run (`results/repro.md`). Measured in
exp001 (yam_glove7, 30 segments, RTX 3090, driver 580, DROID torch 2.5.1+cu124):

- **Tolerance: 0, i.e. bitwise identical.** E3 recomputed: all arrays of `traj.npz` match on
  30/30 segments (poses, keyframe poses, inverse depth, keyframe indices). So do every metric
  downstream (scale, labels, evaluation).
- The trajectories are also bit-identical to the 2026-11-06 legacy runs: E1 and E3 30/30, and
  the SAM2 masks 30/30 segments (8972 frames).
- So, despite the expectation, DROID's CUDA path is deterministic on this setup
  (`torch.manual_seed(0)`, one GPU).
- Not covered: other GPUs, drivers or CUDA/torch builds may differ. Re-measure with `--repro`
  when any of them changes; the package versions are in the cache key anyway.
- exp001's `repro.md` shows a "rotation difference" max of 0.017 deg with all deltas 0. That is
  the numerical floor of the arccos angle formula used then (a trajectory compared with itself
  reads 0.019 deg), not a difference. The report now uses an atan2 formula and states
  bit-identity explicitly (from exp002 on).

## Current defaults (decisions)

New experiments start from these unless they test an alternative to them:

| what | default | since | evidence |
|---|---|---|---|
| motion masks | `sam3_v2_head`: `sam3_v2` (exp006's parameters, frozen; a change needs a new impl name or version and its own comparison) with the held-object gate on the head-camera gripper width (`slam.head_width`) | 2026-11-12 | no wrist-camera data in the algorithm (the wrist camera is a cross-check only); `sam3_v2` (2026-11-09, exp006 audit: moving regions 54/80 vs SAM2 40, static 10/74 vs v1 73, held block 0.98-0.99) gated on the wrist width; the gate differs on 2.5% of segment frames. Runs: exp039-exp044 |
| tile masks (E3) | `tile_geometry`, `slam_fallback: E1` | exp000 (legacy) | exp001 reproduces it bitwise |
| scale | primary `Bnet` (no ball) on depth `da3_metric` (DA3METRIC-LARGE with the camera K, exp008's parameters), check `A` at 10% (informational) | 2026-11-10 | cross_session (glove6 take 1, glove7, glove8; 61 episodes): scale \|err\| 4.0 / 13.2% vs 14.2 / 26.2% for DA2 + `Bsession`, labels at 1 s 4.8 vs 7.2 mm median. Replaces `Bsession` (2026-11-09), whose ball correction depends on how near the ball is held (glove6: -22%) |
| SLAM | `droid_adaptive`: `droid` (demo parameters, native 960x536, per-episode segments with a 5 s preroll), re-run from 1 s before the episode where the first run turns faster than 120°/s before the episode | 2026-11-12 | exp023-exp028 (167 segments): DROID initialized on fast pre-episode head turns (all 6 episodes with a scale error > 50%); a 1 s start only there gives scale \|err\| 5.8 / 15.0% vs 6.6 / 19.0%, 2 vs 6 episodes > 50%, label chunk mean 8.1 vs 17.9 mm, rotation unchanged; a short start everywhere loses accuracy (rotation 0.36° -> 0.44-0.50° at 1 s). Runs: exp029-exp034. Replaces `droid` (exp000) |
| labels gripper | `head`: gt/gripper_head.npz (`slam.head_width`, tail/base estimators calibrated per glove unit: caliper width holds, or for yosub pilot_glove_HHs3's head-camera width) | 2026-11-12 | holdout vs HHs3: median 0.020 / p95 0.122 command units (wrist 0.023 / 0.138, cross-check only) |

## Experiments

| exp | what |
|---|---|
| exp000_legacy | archive of the pre-framework results (SAM2 + DROID E1/E2/E3, scale modes), tag `legacy-sam2` |
| exp001_sam2_baseline | exp000's E3 configuration re-run through the framework; reproducibility tolerance |
| exp002_sam3_masks | SAM3 masks (text: hand/arm/cable + ball-pose points for the rig) vs SAM2; overlay gallery; region audit in `audits/` |
| exp003_droid_sam3 | DROID E1/E2/E3 with the SAM3 masks, vs exp000/exp001 |
| exp004_error_decomposition | exp003's E3 label error split into SLAM vs tile rotation x B vs oracle scale (IMU / stereo question) |
| exp005_session_scale | scale `Bsession`: one ball correction k pooled over the session, vs per-segment B; diagnosis of the long tail |
| exp006_sam3_v2 | SAM3 masks v2 (`sam3_v2`): leak-filtered text instances attached to the wearer, denser rig prompts, held-block point; DROID E3 |
| exp007_v2_session_scale | the current defaults: exp006's masks and DROID E3 with scale Bsession + A check; the baseline for later backends |
| exp008_depth_models | depth networks that take K (UniDepth V2, Metric3D v2, DA3 metric, MoGe-2, Depth Pro with K) vs DA2 for Bsession / B / Bnet (no ball); K ablations |
| exp009_net_scale | scale `Bnet` (the network's own metric depth, no ball) + A check for DA3 metric, MoGe-2, UniDepth + K, Metric3D + K: labels, evaluation, error decomposition (DA3) |
| exp010_glove8 | glove8: default (DA2 + Bsession) vs DA3 metric + K, Bnet |
| exp011_glove6_take1 | glove6 take 1, failed on ep00 (false start without ball / tile pose); superseded by exp012 |
| exp012_glove6_take1 | glove6 take 1 without ep00: default vs DA3 + Bnet |
| exp013_glove6_take2 | glove6 take 2: the defaults (sam3_v2, DROID E3, DA3 + K Bnet) |
| exp014_glove5_take1 | glove5 take 1: the defaults (SAM3 inference state moved to the CPU for memory, bit-identical) |
| exp015_glove5_take2 | glove5 take 2: the defaults |
| exp016_rel_datasets | P2: relative-pose versions of pilot_mix_gHs3, glove labels from tiles (FK of HHs3) vs SLAM; HHs3 source manifest |
| exp017_envcheck_mix_gHs3_48 | P3: Yosub's mix_gHs3_48 retrained 10k steps in our env; matches his val curve within ±2.2% |
| exp018_rel_T48 | P3: ACT, relative actions, 48 teleop episodes |
| exp019_rel_Gtile48 | P3: + 194 glove segments, tile labels |
| exp020_rel_Gslam48 | P3: + 194 glove segments, SLAM labels (5 s start) |
| exp021_glove5_take1_ballscale, exp022_glove5_take2_ballscale | glove5: DA3 + K / DA2 x no ball / ball per segment / ball per session; the ball makes glove5 worse |
| exp023-exp028 (preroll_*) | DROID started 5 / 2 / 1 s before the episode on all six takes (`droid_preroll`) |
| exp029-exp034 (adaptive_*) | the adaptive start (`droid_adaptive`), the default since 2026-11-12, on all six takes |
| exp035_rel_datasets_adaptive | exp016 rebuilt with the adaptive SLAM runs |
| exp036_rel_Gslam48_adaptive | exp020 retrained on exp035's SLAM dataset |
| exp037_rel_T48_prevanchor, exp038_rel_Gtile48_prevanchor | test (a): exp018 / exp019 with the anchor = the previous step's target pose |
| exp039-exp044 (adaptive_head_*) | exp029-exp034 with no wrist-camera data: `sam3_v2_head` masks, head labels gripper |
| exp045_rel_datasets_head | exp035 rebuilt from exp039-exp044 (`pilot_mix_gHs3_rel_{tile,slam}_v3`) |
| cross_session/ | summary over glove6 take 1, glove7 and glove8: DA3 + Bnet 4.0 / 13.2% vs default 14.2 / 26.2% scale error; labels 1 s 4.8 vs 7.2 mm |
