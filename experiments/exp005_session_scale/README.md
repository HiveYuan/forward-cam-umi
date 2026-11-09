# exp005_session_scale

**What.** exp003 unchanged (SAM3 masks; DROID E1/E2/E3; DA2 depth; every producer is an exp003
cache entry), with a new scale method for E2 and E3: **`Bsession`** = method B with the ball
correction k pooled over the whole session instead of each segment's own k. A stays a cross-check
(|A/s − 1| > 10% flags). Labels and evaluation as in exp003; the report compares with exp003.

```
HF_TOKEN_PATH=~/.config/yuanliu/hf_token $V -m slam.run experiments/exp005_session_scale/config.yaml
PYTHONPATH=. $V experiments/exp005_session_scale/diagnosis.py \
    --view <work>/runs/exp005_session_scale/main/view --run E3 --masks motion,tiles --out diag_E3.json
```

**Why.** B's long tail on exp003 E3: |err| p90 20.1%, with ep20 −35.7%, ep29 −29.2%, ep21 −22.1%,
ep12 −19.2%, ep15 −13.6%. B is s = k · median(D_net / z_slam) over the background, with k =
median(z_true / D_net) at the ball's face centres. The first question was whether the tail comes from
(a) the segment's k (pooling k would help) or (b) the ratio D_net / z_slam (pooling would not).

## Step 1: diagnosis (before any code change)

Method: `diagnosis.py` on the analysis view of the cached exp003 E3/E2 outputs (same files as exp003;
B reproduces exp003's s bit for bit). B is exactly s = k · R on every segment (R = median of
D_net / z_slam over the background cells; the cell selection does not move with k here,
max |s_B − k·R| / s_B = 2e-16). With the tile oracle s_o, a segment *needed* k_need = s_o / R, and
with the session's k_s (median of the per-segment k):

1 + err_B = k / k_need = (k / k_s) · (k_s / k_need)

- **(a)** k / k_s: the segment's own k is off the session's typical k. Pooling removes it.
- **(b)** k_need / k_s: the segment needs a different correction than the session's typical one.
  Pooling cannot remove it (err with k_s = k_s / k_need − 1).

| E3 (E2) | value |
|---|---|
| k_s = median of the 30 per-segment k (all 30 segments see the ball; 320 samples) | 0.562 (0.566) |
| per-segment k, p10 / p25 / p75 / p90 | 0.486 / 0.522 / 0.588 / 0.629 (0.468 / 0.519 / 0.587 / 0.605) |
| spread (a): sd of log(k / k_s) | 0.105 (0.112) |
| spread (b): sd of log(k_need / k_s) | 0.091 (0.080) |
| var log(1+err_B) = var (a) + var (b) − 2 cov | 0.0152 = 0.0110 + 0.0083 − 0.0041 (0.0135 = 0.0125 + 0.0064 − 0.0054) |
| corr(log k, log k_need) | 0.21 (0.30) |
| best ball-based k (log k_need regressed on log k: slope 0.19) leaves var | 0.0079 vs 0.0083 with k_s alone (0.0058 vs 0.0064) |
| median k_need, and k_s against it | 0.597, k_s −5.9% (0.620, −8.8%) |

**Answer: neither dominates.** (a) is the larger term (about 57% of var (a) + var (b) on E3, 66% on
E2), and (b) is of the same order. Pooling k removes (a) completely. Everything left after pooling
is (b). The own k carries almost no information about what the segment needs (corr 0.21), so no
mix of own and session k does noticeably better than k_s.

**What (b) is.** The tiles give ground truth for part of the background. In each keyframe with a
tile pose, the table plane gives the true depth on the tile cells (1/8 cells fully inside the tile
mask and outside the motion mask, 0.7–0.9 m away):

- **The depth network.** k_tile = median(true depth / D_net) on the tile cells is the network's
  true correction at the table. Over the 20 segments with ≥ 5 tile keyframes (E3), it tracks
  k_need: corr 0.63, median |k_need/k_tile − 1| = 4.1%. It barely tracks the ball's k: corr 0.10,
  median |k/k_tile − 1| = 8.0%. E2 gives the same picture (0.71, 3.6% vs 0.38, 7.4%). sd log k_tile
  is 0.10: DA2's metric scale on the background changes from segment to segment by about 10%, and
  the ball (0.3–0.6 m) does not see this change.
- **DROID's depth is mostly consistent with its trajectory.** In E2 the tiles are not masked, so
  DROID optimises depth on them. There, DROID's keyframe depth on the tiles matches its own
  trajectory scale (the tile oracle) to a median of 2.7%, p90 10.1% (26 segments). In E3 the tile
  cells are masked, so DROID's depth there is unconstrained and cannot be compared. The outlier is
  ep29 (−16% in E2; see below).
- **Few valid cells?** No: corr(background cells, err_Bsession) = 0.02. A ball seen unusually close
  (ep20: 0.33 m vs a typical 0.45–0.55 m) lowers its k. That is part of (a).

So (b) is mostly the depth network's per-segment scale variation on the background. On a few
segments (ep29, partly ep20) it is the trajectory's scale itself: the tile oracle fitted per third of
the segment is not one number.

**Long-tail segments (E3):**

| segment | own k (samples) | k/k_s − 1 | k_need/k_s − 1 | k_tile (tile kf) | err B | err with k_s | source |
|---|---|---|---|---|---|---|---|
| ep20 | 0.436 (14) | −22.4% | +20.7% | 0.569 (1) | −35.7% | −17.2% | half (a): ball seen at 0.33 m gives a low k; half (b): the oracle per third is 0.92 / 0.79 / 0.96, so DROID's scale moves within the segment |
| ep29 | 0.552 (22) | −1.8% | +38.7% | 0.501 (1) | −29.2% | −27.9% | (b), SLAM / oracle side. k is normal and the network on the table is normal. Tile GT exists on only 41 frames (6 in the first third); the oracle over the middle third alone is 0.915 vs 1.224 over all 41. E2's DROID depth on the tiles is −16% off its trajectory, the worst segment |
| ep12 | 0.471 (9) | −16.2% | +3.7% | 0.575 (13) | −19.2% | −3.6% | (a): the network on the table and k_need are normal; the ball's k is low |
| ep15 | 0.515 (6) | −8.3% | +6.2% | 0.579 (9) | −13.6% | −5.8% | mostly (a), few ball samples |
| ep21 | 0.488 (13) | −13.1% | +11.5% | 0.630 (12) | −22.1% | −10.3% | both: k low (a); the network needs a higher k on this segment's background (k_tile 0.630 ≈ k_need 0.627) (b) |
| ep05 | 0.578 (8) | +2.8% | +25.3% | 0.744 (6) | −17.9% | −20.2% | (b), network: k_tile 0.744 ≈ k_need 0.704 |
| ep06 | 0.533 (4) | −5.2% | +11.7% | 0.588 (7) | −15.1% | −10.5% | mostly (b) |
| ep11 | 0.491 (12) | −12.6% | +4.0% | 0.558 (12) | −16.0% | −3.8% | (a) |
| ep19 | 0.696 (15) | +23.9% | +22.2% | 0.584 (1) | +1.4% | −18.1% | (a) and (b) cancel in B. Pooling breaks that, and A flags it |

All segments (E3; the k_tile count is the number of keyframes with tile cells):

| segment | own k (samples) | k/k_s − 1 % | k_need/k_s − 1 % | k_tile (tile kf) | err B % | err Bsession % |
|---|---|---|---|---|---|---|
| ep00 | 0.585 (10) | +4.2 | +0.1 | 0.633 (10) | +4.0 | −0.1 |
| ep01 | 0.683 (10) | +21.6 | +14.4 | 0.699 (6) | +6.3 | −12.6 |
| ep02 | 0.545 (8) | −2.9 | +2.7 | 0.561 (7) | −5.4 | −2.6 |
| ep03 | 0.588 (5) | +4.6 | +16.6 | 0.574 (6) | −10.3 | −14.3 |
| ep04 | 0.645 (9) | +14.8 | +21.3 | - | −5.4 | −17.6 |
| ep05 | 0.578 (8) | +2.8 | +25.3 | 0.744 (6) | −17.9 | −20.2 |
| ep06 | 0.533 (4) | −5.2 | +11.7 | 0.588 (7) | −15.1 | −10.5 |
| ep07 | 0.587 (6) | +4.4 | - | - | - | - |
| ep08 | 0.596 (5) | +6.1 | +11.9 | 0.640 (4) | −5.1 | −10.6 |
| ep09 | 0.530 (9) | −5.6 | −5.9 | 0.568 (2) | +0.2 | +6.2 |
| ep10 | 0.533 (14) | −5.1 | −3.2 | 0.564 (14) | −1.9 | +3.3 |
| ep11 | 0.491 (12) | −12.6 | +4.0 | 0.558 (12) | −16.0 | −3.8 |
| ep12 | 0.471 (9) | −16.2 | +3.7 | 0.575 (13) | −19.2 | −3.6 |
| ep13 | 0.572 (7) | +1.9 | −0.7 | 0.543 (12) | +2.5 | +0.7 |
| ep14 | 0.589 (21) | +4.8 | +6.3 | 0.548 (11) | −1.5 | −5.9 |
| ep15 | 0.515 (6) | −8.3 | +6.2 | 0.579 (9) | −13.6 | −5.8 |
| ep16 | 0.429 (6) | −23.7 | - | - | - | - |
| ep17 | 0.557 (9) | −0.8 | +9.9 | 0.608 (10) | −9.7 | −9.0 |
| ep18 | 0.566 (7) | +0.8 | +5.9 | 0.610 (8) | −4.8 | −5.6 |
| ep19 | 0.696 (15) | +23.9 | +22.2 | 0.584 (1) | +1.4 | −18.1 |
| ep20 | 0.436 (14) | −22.4 | +20.7 | 0.569 (1) | −35.7 | −17.2 |
| ep21 | 0.488 (13) | −13.1 | +11.5 | 0.630 (12) | −22.1 | −10.3 |
| ep22 | 0.500 (12) | −10.9 | −6.8 | 0.599 (3) | −4.4 | +7.3 |
| ep23 | 0.519 (16) | −7.7 | +6.8 | 0.636 (12) | −13.6 | −6.4 |
| ep24 | 0.603 (18) | +7.4 | +12.0 | 0.641 (9) | −4.1 | −10.7 |
| ep25 | 0.627 (13) | +11.7 | +6.3 | 0.471 (5) | +5.0 | −5.9 |
| ep26 | 0.614 (7) | +9.3 | −2.3 | 0.499 (3) | +11.9 | +2.4 |
| ep27 | 0.557 (15) | −0.9 | +2.7 | 0.577 (15) | −3.6 | −2.7 |
| ep28 | 0.567 (10) | +1.0 | −0.8 | 0.507 (8) | +1.7 | +0.8 |
| ep29 | 0.552 (22) | −1.8 | +38.7 | 0.501 (1) | −29.2 | −27.9 |

ep07 and ep16 have no tile GT. Pooling helps (|err| down by > 2 points) on 10 segments, hurts on 10
and changes little on 8 (E2: 12 / 9 / 7). Where the own k happened to follow the segment's need
(ep01, ep04, ep19, ep24), pooling loses that.

## Step 2: method `Bsession` (`slam/scale.py`, `slam/pipeline/impl_analysis.py`)

- `scale_depth_ball` (B) is factored into `_depth_inputs`, `ball_depth_pairs` (ball samples) and
  `background_ratios` (background ratio). The new code reproduces B bit for bit: all result fields
  for E2 and E3 on 30/30 segments, and a frozen copy of the old code in the unit tests.
- `session_k(samples, pool)`: **pool = "segments"** (used here) takes the median over segments of
  each segment's k; "samples" takes the median of all pooled ball samples. Segments is the right
  choice because the ball samples of one segment are not independent: same ball depth, neighbouring
  keyframes, same images. A segment's error is shared by all of its samples, so the independent
  units are segments. Pooling by samples would weight segments by how long the ball faces the camera
  (ep29: 22 samples, ep06: 4). In practice both give the same answer (E3 0.5618 vs 0.5606; |err|
  p90 17.7% vs 17.9%).
- `scale_depth_ball_session(seg, run, k_session, ...)` (method `Bsession`) computes
  s = median(k_session D_net / z_slam) over the same background cells as B. It does not need the
  segment's own ball, so a segment where the ball never shows in a keyframe still gets a scale. It
  records the segment's own `k_ball` and `s_own_k`, the scale with the own k (= B).
- Framework: `k_session` is a framework keyword (`spec.SCALE_FRAMEWORK_KW`). `scale_run` pools
  every segment's ball samples first, whenever the primary or a check is a session method
  (`slam.scale.SESSION_METHODS`), then estimates each segment. `scale_<run>.json` gets
  `"session": {"Bsession": {k_session, pool, n_segments, n_samples, k_segment_p10..p90,
  per_segment: {segment: {k, n}}}}`, and `scale_<run>.md` gets a per-segment table: own k, s with
  own k, s with k_session.

## Result (verification run of this config, all producers from the cache, 0.9 min CPU)

The numbers come from a run of an identical copy of this config outside the repository. Producers:
9/9 cache hits on exp003's keys. eval_oracle and gt_noise are byte-identical to exp003. The labels
files differ from exp003 only in `without_flagged`, because a different set of segments is flagged.
Bsession's s equals the diagnosis on 30/30 segments, and its `s_own_k` equals exp003's B s on 30/30.

Scale error vs the tile oracle (28 segments with tile GT):

| | B (exp003) | Bsession (exp005) |
|---|---|---|
| E3 \|err\| median / p90 | 5.4% / 20.1% | 6.3% / **17.7%** |
| E3 bias (median) | −5.0% | −5.9% |
| E3 rms / max \|err\| | 13.0% / 35.7% | **10.9% / 27.9%** |
| E3 segments > 10% / > 20% | 11 / 3 | 11 / 2 |
| E3 flagged by A | ep01, ep11, ep12, ep20, ep25, ep26 | ep19, ep24 |
| E2 \|err\| median / p90 | 8.1% / 23.1% | 8.8% / **17.5%** |
| E2 bias / rms / max | −6.9% / 13.9% / 35.0% | −8.8% / **11.0% / 24.7%** |
| E2 segments > 10% / > 20% | 13 / 4 | 13 / 2 |

Tool labels tool_t → tool_t+dt, position error vs tile labels (989 anchors, mm):

| | oracle scale | B (exp003) | Bsession (exp005) |
|---|---|---|---|
| E3 1 s median / p90 | 4.3 / 14.6 | 5.7 / 18.4 | **4.8 / 15.6** |
| E3 2 s median / p90 | 5.5 / 14.7 | 7.6 / 27.9 | **6.4 / 18.3** |
| E3 chunk mean H = 15 / 30 / 50 / 100 | 4.8 / 6.6 / 7.8 / 8.9 | 5.5 / 7.9 / 9.5 / 10.9 | **5.0 / 7.1 / 8.5 / 9.6** |
| E2 1 s median / p90 | 3.6 / 13.6 | 5.5 / 18.0 | **4.0 / 15.0** |
| E2 chunk mean H = 15 / 30 / 50 / 100 | 4.8 / 6.8 / 8.5 / 10.2 | 5.6 / 8.3 / 10.5 / 12.5 | **5.0 / 7.2 / 9.0 / 10.5** |

Head translation (E3, Bsession): 1 s 8.72 / 34.56 mm (median / p95), against oracle 8.19 / 34.71
and B 9.06 / 36.2. Rotation is unchanged (scale-free).

**Reading.** The session k trades a slightly worse median scale error (+0.9 points, from the larger
bias) for a shorter tail (p90 −2.4 / −5.6 points, max −8 / −10). The labels improve clearly:
1 s median 5.7 → 4.8 mm, 2 s p90 27.9 → 18.3 mm, chunk H = 100 mean 10.9 → 9.6 mm (oracle 8.9).
The label errors are dominated by the tail segments, which are exactly the ones pooling fixes (ep12,
ep20, ep21). The remaining error is (b), which no ball-based k can remove:

- **Bias:** k_s is 5.9% (E2 8.8%) below the median needed k. This is DA2's depth compression, known
  from exp000: the ball is near, the background far. A one-off calibration of this ratio would leave
  Bsession at |err| median 5.6%, p90 13.3% (E2 6.8% / 11.7%). That number is an in-sample upper
  bound (it removes the bias measured with the oracle on the same data), not a method. B with the
  same correction would be 7.5% / 17.8%.
- **Per-segment spread (sd ≈ 9%):** the depth network's background scale varies from segment to
  segment, and on ep29 and ep20 DROID's scale varies within the segment. Fixing this needs scale
  information that is shared across segments, i.e. one map for the take, or a better depth prior.

## Whole-take DROID (shared map): estimate only, not run

With one DROID map for the take, all segments share one scale. The per-segment network spread then
averages over about 670 keyframes instead of about 13, leaving the session bias (calibratable) plus
DROID's scale drift over 10 min (unknown; this is the risk). The estimates below come from the DROID
code in third_party/DROID-SLAM and exp003's E3 run metadata (30 segments, 8,972 frames, 389
keyframes = 0.043 per frame, 0.160 s per frame including global BA and trajectory filler, peak
14.1–17.1 GB allocated / 16.0–18.8 GB reserved with a buffer of 275–380 slots).

| | per segment today | ep00 preroll → ep29 end | whole take |
|---|---|---|---|
| frames (26.3 fps effective) | ~300 | 15,484 (589 s) | 20,629 (785 s) |
| keyframes (0.043 / frame) | ~13 | ~670 | ~900 |
| video buffer at 960×536 (9.8 MB per slot: image 1.5, fmap/net/inp 3 × 2.06 fp16, disps_up 2.06) | 3–3.7 GB (buffer = frames + 32) | 9.8 GB with buffer = 1,000 (frames + 32 would be 152 GB) | 13 GB with buffer = 1,300 |
| frontend (≤ 48 edges × 172 MB fp16 correlation pyramid + activations, fixed) | ~12 GB | ~12 GB | ~12 GB |
| frontend-phase peak | 14–17 GB | **~22 GB** | **~25 GB** |
| global BA at the end (alt corr, up to 16 × keyframes edges × ~2.3 MB each: GRU state 128×67×120 fp16 + target/weight/motion) | < 1 GB | **~25 GB + 10 GB buffer** | ~33 GB + 13 GB |
| runtime | 48 s | ~41 min + global BA ~5–15 min | ~55 min + ~5–15 min |

On the shared RTX 3090 (24 GB, about 4 GB used by others) **a whole-take run at 960×536 does not
fit as configured.** The frontend phase is at the limit. The final global BA (10,700 proximity edges
in a scene revisited for 10 minutes; DROID caps the count at 16 × keyframes) needs roughly 35 GB.
Ways to make it fit, for the user to decide:

1. **Half resolution (480×268):** about 2.5 MB per slot (2.5 GB), 0.5 GB of frontend correlation,
   about 0.6 MB per BA edge (6.4 GB). Peak about 10–12 GB, runtime about 15–25 min. Rotation accuracy
   at half resolution must be re-validated (DROID's demos run at about 512×384).
2. **Full resolution with a code change:** cap the final global BA (for example 4 × keyframes edges,
   about 6 GB) and keep a 1,000-slot buffer. Peak about 22 GB, still too much next to other users.
   It would also need part of the buffer held off the GPU.
3. **Overlapping chunks (2–3 min, about 10 s overlap):** each chunk is like today's segments (130–220
   keyframes, about 15–17 GB). Scales are chained by Sim(3) alignment on the overlaps. This fits
   today, but scale drift adds up at each of 4–5 joints.

Every option also needs the producers for the frames between episodes (about 6,500 more frames:
undistort, SAM3 masks, tile masks, DA2 depth on the new keyframes) and a "take" segment in place of
per-episode segments. Runtimes are rough: the global BA was never run at this size. Before deciding,
measure one 2–3 min chunk (option 3 or 1).

## Open points

- `pool` and `correction` of Bsession are validated when the method runs, not when the config loads.
  `slam.pipeline.spec.SCALE_CHOICES` covers only B. Suggested core change:
  `SCALE_CHOICES["Bsession"] = {"correction": ("faces", "disk"), "pool": ("segments", "samples")}`.
- The legacy CLI (`slam.scale estimate --method Bsession`) does not compute k_session and reports a
  failure. Only the framework pools.
