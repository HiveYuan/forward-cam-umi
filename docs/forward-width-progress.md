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

## P95 investigation after the checkpoint

The initial checkpoint was committed and pushed as `4a11c3b` before this review.
Per-frame analysis found two error modes. Some converged joint solves remain in
a poor local pose minimum despite a large image residual. Other frames have
only 0.3–0.4 px image residual but 2–3 mm width error, so a residual threshold
alone cannot certify metric accuracy.

The solver now retries SQPnP initializations at normalized trained-stroke
positions 0, 0.5, and 1 if the warm solve fails or exceeds the 1 px Huber scale.
It selects the lowest Huber cost among converged positive-depth solutions.
The width is still free to leave the training range. At frame 512, this changes
the fused estimate from 61.99 to 58.65 mm for the 57.9 mm hold; frame 711 changes
from 54.37 to 56.21 mm. The frozen motion parameters need no change for recovery.

New model artifacts rank candidate faces by training time-blocked p95. Faces
sharing a fixed tag have correlated pose errors, so only the best available face
per reference votes in the fused median; another face remains a fallback. The
training ranking favors 44 over 48 for reference 46 and 49 over 45 for reference
47. Scores are frozen before the verification replay. Old unranked artifacts
retain flat-median fusion.

| 57.9 mm replay | Checkpoint | Solver recovery | Recovery + reference ranking | Gate |
| --- | ---: | ---: | ---: | ---: |
| P95 absolute error | 2.3602 mm | 2.2016 mm | 2.0836 mm | <=2 mm |
| Signed median error | +0.0824 mm | -0.1613 mm | -0.2039 mm | absolute value <=1 mm |
| Error RMS | 1.3896 mm | 1.3362 mm | 1.2587 mm | diagnostic |
| Coverage | 689/821 (83.9%) | 691/821 (84.2%) | 691/821 (84.2%) | >=70% |

P95 remains 0.0836 mm above the gate. No extra frame rejection, clipping,
temporal smoothing, or changed calibration/capture settings explain the gain.
The 64.6 mm training-hold replay also has p95 2.1949 mm, indicating a remaining
tail-error problem beyond the one verification aperture.

Other diagnostic attempts were not adopted:

- Body-pose rotation priors at 1, 3, and 5 degrees, chosen by training-blocked
  RMS: the selected 1-degree prior yields verification p95 2.2155 mm.
- Taking a median within each reference before fusing references: p95 2.2029 mm.
- First-order image-row motion timing correction, fitted on training data:
  verification p95 worsens from 2.2019 to 2.2356 mm on the same 670 frames with
  neighboring observations. The fitted coefficient is not a camera readout-time
  measurement.

Reference ranking is an engineering candidate, not a new blind qualification.
A cached training-block comparison had p95 2.8414 mm for flat fusion versus
2.8841 mm for the ranked-reference policy, so the validation improvement is not
uniform across datasets. Although model parameters and ranking scores use only
training data, the 57.9 mm recording has now been inspected repeatedly while
developing inference policies. Fresh unseen holds are required for qualification.

Reproduce the latest review:

```bash
.venv/bin/python scripts/forward_width_check.py \
  glove_yuan_width_02 glove_yuan_width_verify_01 --unit yuan \
  --out tmp/forward_width_yuan_v4.local.json
```

Reports include solver policy and implementation hashes in addition to frozen
model and input hashes. All 14 width regressions pass, including wrong planar
pose recovery, a degenerate cold seed, correlated-reference fusion, missing-face
fallback, and historical model compatibility. Existing marker-map regressions
also pass (7 tests), for 21 passing local regressions in total.

Next useful experiments are corner localization/pose-conditioning diagnostics
and testing the straight-travel/constant-marker-orientation assumption at more
intermediate apertures and viewing angles. Three measured apertures provide
limited evidence for that motion model. Changes should preserve coverage and
the 70% / 1 mm / 2 mm gates, then be assessed on fresh unseen holds; this review
does not justify treating the remaining tail error as solved.
