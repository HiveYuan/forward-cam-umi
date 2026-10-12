# Forward width progress — 2026-10-13

The fixed forward camera can recover width from existing Yuan recordings without
changing camera intrinsics, rigid ball/base geometry, marker sizes, or capture
settings. The new offline estimator jointly fits a moving/fixed marker pair's
image corners, instead of subtracting independently estimated tag depths.

Training: `glove_yuan_width_02`, measured holds 0, 32.3, and 64.6 mm.
Verification: `glove_yuan_width_verify_01`, a separate 57.9 mm hold.
Only training data selects and fits estimators. The frozen model is reloaded
before verification. No prediction clipping or temporal smoothing is applied.

| Verification metric | Original estimator | Joint image estimator | Gate |
| --- | ---: | ---: | ---: |
| Signed median error | -1.23 mm | +0.08 mm | absolute value <=1 mm |
| P95 absolute error | 11.23 mm | 2.36 mm | <=2 mm |
| Width coverage | 91.7% | 83.9% (689/821 frames) | >=70% |

Coverage and median error pass. P95 still fails by 0.36 mm; this checkpoint does
not certify forward-width accuracy. Missing detections and rejected solves stay
in the coverage denominator. Moving-width accuracy remains untested.

Selected local pairs: 44–46, 45–47, 48–46, and 49–47. Candidate checks require
three apertures, at least 40 paired observations per aperture, a nearby base
reference, optimizer convergence, and physical-mm time-blocked holdout gates.
Single-marker and cross-jaw estimators are excluded.

Reproduce with the original local recordings and fixed calibration files:

```bash
.venv/bin/python scripts/forward_width_check.py \
  glove_yuan_width_02 glove_yuan_width_verify_01 --unit yuan \
  --out tmp/forward_width_yuan_v2.local.json
```

Exit status 2 denotes an accuracy-gate failure; it still saves the report,
frozen model, and per-frame predictions in `tmp/`. Those device-specific artifacts
and videos are kept locally. The legacy normalized actuator estimator is unchanged.

Regression checks:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_forward_width.py' -v
```

All nine regressions pass, including metric scale, perspective changes, unseen
apertures, missing/ambiguous IDs, repeated hold boundaries, and coverage accounting.

Next: examine the high-error frames and per-pair disagreement, then test any
change using training-only selection with the same independent recording and
unchanged 70% / 1 mm / 2 mm final gates.
