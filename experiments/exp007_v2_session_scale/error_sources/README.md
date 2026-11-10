# Error sources of the session-pooled depth + ball scale (exp007, E3)

Post-hoc analysis of exp007's scale ("Depth + ball, corrected once per session" = `Bsession`) against
the per-episode tile-fitted scale. It is read only: it uses exp007's analysis view, and the run
itself is unchanged. Two independent checks recomputed every number below from the view and
challenged its interpretation (`checks/`). The wording here follows their corrections.

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
D=experiments/exp007_v2_session_scale/error_sources
PYTHONPATH=. $V experiments/exp005_session_scale/diagnosis.py \
    --view /home/student/yuanliu-hawaii/work/runs/exp007_v2_session_scale/main/view \
    --run E3 --masks motion,tiles --out $D/diag_E3_v2.json        # per-episode k, k_need, k_tile, thirds
$V $D/decompose.py $D/diag_E3_v2.json                           # bias / spread split, counterfactuals
PYTHONPATH=. $V $D/checks/recompute_view.py                     # independent recompute from the view
$V $D/checks/stats.py                                           # statistics checks (needs scipy)
PYTHONPATH=. $V $D/checks/physics.py $D/checks/phys.json        # depth ranges, correction vs depth, ep29
```

`diagnosis.py` reproduces exp007's Bsession results exactly:
- |err| median 7.84%, p90 17.44%, bias -7.35%, rms 11.10%, max 31.9%;
- the per-episode s matches `results/scale_E3.json`.

## Setup

- Bsession sets each episode's scale to s = k_s · R:
  - k_s = 0.566 is the median over the 30 episodes of each episode's own ball correction k.
  - R = median(network depth / DROID depth) over the background cells of the episode's keyframes.
- The tile-fitted (oracle) scale is s_o = k_need · R.
- So **1 + err = k_s / k_need**, and every error is a mismatch between the session's correction and
  the one the episode needed.
- Max deviation from that identity is 2e-16 on this data. It is not a general identity: the depth
  gates act on k·D, but no cell falls in the bands where they would differ.

## Results (28 episodes with tile ground truth)

| source | size | share of the mean squared log error |
|---|---|---|
| Bias: the session correction is too small for the background | mean log error -8.0% (median err -7.3%) | about half (45.6%; bootstrap 90% CI 32-64%) |
| Episode-to-episode spread | sd 9.1% (log) | about half (54.4%) |
| Estimate of k_s from 30 episodes | bootstrap sd 2.0%, 90% CI -4.3% / +2.5% | a session-wide offset, already inside the bias |

### Bias

- **Distances.** The ball samples are at a median of 0.48 m (per-episode medians 0.33-0.59 m). The
  background cells that R uses are at about 0.8 m (p10-p90 0.58-1.02 m). The tiles are at 0.85 m.
- **DA2's correction grows with distance.** Ratios of true to network depth on the table (true
  depth from the tile plane): 0.533 at 0.55-0.70 m, 0.569 at 0.7-0.9 m, 0.642 at 0.9-1.2 m and
  0.693 at 1.2-1.6 m. DA2 over-estimates depth by about 1.7-1.9x, less with distance. ("Compresses
  depth" is the wrong picture.)
- **The ball is not on the table's curve.** It sits about 10% above it, so the net mismatch is
  smaller than distance alone predicts. Over the 19 well-tiled episodes:
  - ball k 0.558;
  - table k_tile 0.580 (larger in 15 of 19 episodes, Wilcoxon p = 0.014);
  - needed k_need 0.605.
- **What a one-off calibration of the factor would give.**

  | | median \|err\| | p90 |
  |---|---|---|
  | as is | 7.8% | 17.4% |
  | in-sample | 5.2% | 12.5% |
  | leave-one-out | 5.4% | 13.0% |

  Whether the factor (about 1.087) carries over to other sessions cannot be tested with one
  session.

### Spread

- **The depth network's background scale is a major part of it, but cannot be cleanly separated.**
  On the 19 episodes with at least 5 tile keyframes:
  - log k_tile correlates 0.68 with log k_need (90% CI 0.39-0.84; Spearman 0.66) and explains about
    half of its variance (R² 0.46, slope 0.47);
  - the ball's k correlates only 0.30 with k_tile (CI includes 0).
- **Caveats on that split.**
  - k_tile is measured on tile cells, which R excludes.
  - k_tile also varies with viewing distance (corr 0.56).
  - It drops to r = 0.37 when all 26 episodes with any tile keyframe are used.
  - The corr(t, r) = -0.72 of `decompose.py` follows from the algebra, so its +102% / +55% / -109%
    shares are not an attribution.
- **Reference uncertainty.** The 9 episodes whose DROID keyframes rarely coincide with tile frames
  (median 14% of used keyframes with a strict tile pose, vs 81% in the others) contribute 66% of
  the squared deviations. ep29 alone contributes 39%:
  - its oracle is 1.25 with six 2-tile frames (81-86) and 0.77 without them (bootstrap sd 15%);
  - tiles and SLAM disagree on where those frames are (52-60 mm vs 27-31 mm from the cluster), which
    is within the tile GT's own noise when the tile set changes;
  - with 0.77 as the reference its error would be +10% instead of -32%.
- **Within-episode DROID scale changes** are real in some well-tiled episodes:
  - ep10: 0.347 vs 0.468 on its thirds; ep13: 0.735 vs 0.842;
  - their Bsession errors are nevertheless small (+5.1%, 0.0%);
  - ep20's middle third (0.57 vs 0.94 / 0.97) is fit noise (55 frames, 26 mm of head travel).

### Labels

The scale error raises the 1 s label position error from 3.9 to 4.5 mm (medians, 814 anchors) and the
H=100 chunk mean from 9.1 to 10.1 mm. The chunks are truncated to a median of 49 counted steps.
These are differences of summary statistics, not a per-anchor attribution.

## Files

- `diag_E3_v2.json`: output of exp005's `diagnosis.py` on exp007's view. Per episode it holds the
  own k, k_need, k_tile, R, the oracle and the oracle on thirds.
- `decompose.py`: bias / spread split and counterfactuals. Its t / r variance shares are
  algebraically confounded (see the spread caveats).
- `checks/recompute_view.py`, `checks/stats.py` (+ `view_recompute.json`): independent recompute and
  statistics (leave-one-out, bootstrap, robustness).
- `checks/physics.py`, `checks/kf.py` (+ `phys.json`): depth ranges, correction vs depth, keyframe /
  tile-frame overlap, ep29 and ep20.

## With the reference noise taken out (`refnoise.py`, `refnoise.json`)

**How the reference's own uncertainty is measured.** A moving-block bootstrap (blocks of 13 fit
frames, 2,000 resamples) of the tile-fitted scale gives sd_ref per episode. The rms over the 28
episodes is 4.7%; the largest are ep29 19.7%, ep22 8.8%, ep20 6.1%, ep18 4.4%, ep10 4.1%, ep17 3.6%
and ep23 3.4%.

**Two causes.**
- Weak tile geometry: ep29 (41 frames, 5 cm of head travel), ep22 (70 frames, 5 cm), ep18 (4.6 cm
  of head travel) and ep20 (a noisy middle third).
- DROID's scale changing within the episode: ep10 (thirds 0.35 / 0.51 / 0.47), ep17 and ep23. These
  have plenty of tile frames; one scale just does not describe the trajectory. That is SLAM's error,
  not the reference's.

**Scale error.** Same subsets for both methods; the subsets are chosen from tile data only.

| | all 28 | without weak references (24) | also without within-episode scale changes (21) |
|---|---|---|---|
| Bsession \|err\| median / p90 | 7.8% / 17.4% | 7.3% / 16.2% | 7.2% / 17.0% |
| Bsession bias (median) / spread (sd of log) | -7.3% / 9.1% | -7.3% / 6.6% | -7.2% / 6.5% |
| Bsession rms / max, episodes > 20% | 11.1% / 31.9%, 1 | 9.2% / 18.9%, 0 | 9.4% / 18.9%, 0 |
| B \|err\| median / p90 | 6.6% / 21.7% | 6.6% / 19.3% | 6.4% / 20.4% |
| B spread (sd of log), episodes > 20% | 11.9%, 5 | 9.5%, 3 | 9.8%, 3 |
| Bsession with the bias also removed (leave-one-out): median / p90 | 5.4% / 13.0% | 4.4% / 12.2% | 4.6% / 10.7% |

On all 28, subtracting the mean reference variance from the observed variance gives a method spread
of 7.8% for Bsession (observed 9.1%) and 10.9% for B (observed 11.9%).

**Tool labels.** Position error, median / p90 at 1 s and mean over a 100-step chunk, in mm.

| | all 28 (989 anchors) | 24 (865) | 21 (660) |
|---|---|---|---|
| B | 5.7 / 18.7, 11.7 | 5.7 / 20.7, 12.6 | 5.6 / 27.0, 14.2 |
| Bsession | 4.5 / 15.0, 10.1 | 4.4 / 16.7, 10.7 | 3.9 / 17.8, 11.3 |
| oracle scale | 3.9 / 13.9, 9.1 | 3.8 / 15.3, 9.6 | 3.4 / 16.9, 10.4 |

Removing episodes changes the anchor set, so compare label numbers within a column only.

**Reading.**
- The method's own episode-to-episode spread is about 6.5-7.8% (observed 9.1%).
- The bias of about -7% belongs to the method and does not change.
- No episode is above 20% once the weak references are removed.
- Pooling still clearly beats the per-episode correction on clean episodes: spread 6.6% vs 9.5%.

## Only episodes with at least 3 tile-visible keyframes (`tile_keyframes.json`)

A tile-visible keyframe is a DROID keyframe of E3 with a strict tile pose (at least 2 tiles, rms at
most 5). 22 of the 28 episodes are kept. Dropped: ep04 (0 tile keyframes), ep09 (2), ep19 (1),
ep20 (1), ep26 (2) and ep29 (0); ep07 and ep16 have no tile-fitted scale at all.

Background on the two scales being compared:
- The tile-fitted scale uses every tile-visible frame, not only keyframes. ep09 and ep26 have 205
  and 178 tile frames and stable fits.
- Bsession's background ratio uses keyframes only. With fewer than 3 tile-visible keyframes, the two
  scales are measured at different times of the episode.

| | all 28 | >= 3 tile keyframes (22) |
|---|---|---|
| Bsession \|err\| median / p90 | 7.8% / 17.4% | 6.9% / 11.4% |
| Bsession bias (median) / spread (sd of log) | -7.3% / 9.1% | -5.5% / 6.5% |
| Bsession rms / max; episodes > 10% / > 20% | 11.1% / 31.9%; 8 / 1 | 8.1% / 18.9%; 4 / 0 |
| B \|err\| median / p90 | 6.6% / 21.7% | 5.7% / 20.0% |
| B bias / spread; episodes > 10% / > 20% | -5.2% / 11.9%; 11 / 5 | -4.2% / 9.8%; 8 / 3 |
| Bsession with the bias also removed (leave-one-out): median / p90 | 5.4% / 13.0% | 4.4% / 11.5% |

Tool labels are unchanged. Their anchors come only from 10 episodes with dense tile coverage (ep00,
10, 11, 12, 15, 17, 18, 21, 24, 27), and none of the dropped episodes has any.
