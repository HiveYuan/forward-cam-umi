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
| masks (named) | `sam2_points`, `tile_geometry` (SAM3 in exp002) | sam2 / venv | `masked.npz` |
| slam (named runs) | `droid` (backend interface `slam/backends/base.py`, AMB3R next) | droid | `traj.npz` |
| depth | `hf_depth` (DA2 metric, Depth Pro) | sam2 | keyframe depth for scale B |
| scale | methods of `slam/scale.py`: `none`, `native`, `A`, `B`; primary + checks | venv | per-segment s, flags |
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

**Reproducibility tolerance.** DROID-SLAM's CUDA kernels are not bitwise deterministic. With
`--repro slam.E3` the same configuration is recomputed under a cache tag and compared with the
first run (`results/repro.md`). Measured tolerance (exp001, yam_glove7 E3, 30 segments):
see "Reproducibility" below (filled in from exp001).

## Experiments

| exp | what |
|---|---|
| exp000_legacy | archive of the pre-framework results (SAM2 + DROID E1/E2/E3, scale modes), tag `legacy-sam2` |
| exp001_sam2_baseline | exp000's E3 configuration re-run through the framework; reproducibility tolerance |
