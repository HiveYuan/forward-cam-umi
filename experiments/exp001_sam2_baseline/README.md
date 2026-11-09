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

**Result (2026-11-08, commit a862b33, 103 min).**
- Every exp000 number is reproduced exactly. SAM2 masks, E1/E3 trajectories and tile masks are
  bit-identical to the legacy files.
- E3 recomputed (`repro1`) is bit-identical too, so the reproducibility tolerance is 0 (see
  experiments/README.md).
- New chunk-length label error (mean over steps 1..H, position mm / rotation deg), E3:

| scale | H=15 | H=30 | H=50 | H=100 |
|---|---|---|---|---|
| oracle (tiles) | 4.9 / 0.59 | 6.8 / 0.81 | 8.2 / 0.97 | 9.5 / 1.12 |
| B+Acheck | 5.7 / 0.59 | 8.3 / 0.81 | 10.2 / 0.97 | 11.9 / 1.12 |
