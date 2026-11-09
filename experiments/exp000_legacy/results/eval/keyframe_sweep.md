# DROID keyframe-threshold sweep (yam_glove7, 2026-11-06)

Rotation error of cam_t->cam_t+dt vs tile GT (>= 2 tiles), median / p90 [deg].
A = demo defaults (filter_thresh 2.4, keyframe_thresh 4.0), B = 1.2 / 2.0, C = 0.6 / 1.0.

No masks (E1), segments ep00, ep10, ep11, ep14, ep21:
| setting | 0.08 s | 0.5 s | 1 s | 2 s | keyframes/seg | runtime/seg |
|---|---|---|---|---|---|---|
| A | 0.27 / 0.99 | 0.99 / 4.57 | 1.85 / 7.87 | 2.89 / 15.45 | ~14 | ~45 s |
| B | 0.22 / 0.80 | 0.92 / 3.73 | 1.73 / 6.21 | 3.25 / 8.83 | ~24 | ~105 s |
| C | 0.22 / 0.77 | 0.93 / 4.34 | 1.81 / 7.36 | 3.42 / 15.18 | ~54 | ~195 s |

Motion masks (E2), segments ep00, ep10, ep14, ep21:
| setting | 0.08 s | 0.5 s | 1 s | 2 s | runtime/seg |
|---|---|---|---|---|---|
| A | 0.15 / 0.39 | 0.26 / 0.71 | 0.35 / 0.87 | 0.43 / 1.03 | ~50 s |
| B | 0.13 / 0.32 | 0.25 / 0.69 | 0.33 / 0.88 | 0.41 / 1.01 | ~110 s |

Decision: keep the defaults (A) for E1-E3; the masks, not keyframe density, are what matter.
