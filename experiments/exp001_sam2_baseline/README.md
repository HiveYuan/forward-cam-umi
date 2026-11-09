# exp001_sam2_baseline

**What.** The legacy E3 configuration (exp000_legacy) run through the experiment framework:
SAM2 point-prompt motion masks, tile masks (E1 trajectory fills frames without a nearby tile
pose), masked DROID-SLAM E3 with the demo parameters, scale B (DA2 metric depth + ball) with
an A (static ball) cross-check, labels on the 15 fps grid, evaluation against the tiles.
E1 (no masks) is also evaluated.

**Why.**
1. Validate the framework: from the same inputs it must reproduce exp000's numbers (up to
   DROID's run-to-run variation).
2. Measure that variation: `--repro slam.E3` recomputes E3 under a cache tag and compares
   (`results/repro.md`); the result is the reproducibility tolerance in experiments/README.md.
3. Same-framework SAM2 reference for the SAM3 experiments (exp002 masks, exp003 DROID + SAM3),
   including the new chunk-length label metric (H = 15/30/50/100), which exp000 lacks.

```
$V -m slam.run experiments/exp001_sam2_baseline/config.yaml --repro slam.E3
```
