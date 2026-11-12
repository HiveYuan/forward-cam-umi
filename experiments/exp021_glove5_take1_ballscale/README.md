# exp021_glove5_take1_ballscale

**What.** Ad hoc (2026-11-11): on glove5 take 1 (exp014), every combination of depth network and ball correction, against the
tile-fitted scale: DA3 metric + K and DA2 metric indoor, each with no ball (`Bnet`), the ball per segment
(`B`) and the ball pooled over the session (`Bsession`), plus A. Two aliases of the same DROID E3 run
(cached): `E3_da3m` (primary Bnet = the default; checks A, B, Bsession) and `E3_da2` (primary Bsession
= the previous default; checks A, B, Bnet). The scale summary reports each check's error.

**Why.** glove5 (recorded 2026-10-08) has DA3 Bnet's largest bias (+5.6 / +8.3%) and most of the long
tail. The camera intrinsics were ruled out (tile re-solve: f3 fits better than the older
`B0587b_intrinsics.json`); this checks whether a ball correction removes the bias.
