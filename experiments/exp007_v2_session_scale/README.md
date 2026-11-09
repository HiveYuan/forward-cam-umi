# exp007_v2_session_scale

**What.** The current defaults (decisions of 2026-11-09, `experiments/README.md`) on yam_glove7:
- the producers are exp006's, unchanged (cache hits): `sam3_v2` motion masks, tile masks, masked
  DROID-SLAM E3 and its DA2 keyframe depth;
- scale primary `Bsession` with the A cross-check, using exp005's parameters;
- labels, evaluation and the exp004 error decomposition on E3;
- the report compares with exp005 (Bsession on the first SAM3 masks) and exp006 (B on the same masks).

It is an analysis-only run. E1 is in the config only because the tile masks depend on it (their
fallback run).

**Why.** exp006 measured the v2 masks with scale B. exp005 measured Bsession only on the first SAM3
masks (exp003). This experiment gives the baseline of the configuration now in use, against which
later SLAM backends (AMB3R) are compared.

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp007_v2_session_scale/config.yaml
```

## Results

The run took 0.6 min. All 7 producers were cache hits on exp006's keys. Numbers are from
`results/report.md`, `scale_E3.md` and `errdecomp_E3.md`. k_session = 0.566 (30 segments, 321 ball samples;
exp005 0.562).

**Scale error vs the tile oracle** (E3, 28 segments with tile GT):

| | exp006: v2 masks, B | **exp007: v2 masks, Bsession** | exp005: v1 masks, Bsession |
|---|---|---|---|
| \|err\| median / p90 | 6.6% / 21.7% | 7.8% / 17.4% | 6.3% / 17.7% |
| bias (median) | -5.2% | -7.3% | -5.9% |
| rms / max \|err\| | 13.3% / 31.9% | 11.1% / 31.9% | 10.9% / 27.9% |
| segments > 10% / > 20% | 11 / 5 | 8 / 1 | 11 / 2 |
| flagged by A | ep01, ep12, ep15, ep20 | ep09, ep19 | ep19, ep24 |

**Tool labels tool_t -> tool_t+dt, position error vs tile labels** (989 anchors, mm):

| | oracle scale | exp006 B | **exp007 Bsession** |
|---|---|---|---|
| 1 s median / p90 | 3.9 / 13.9 | 5.7 / 18.7 | 4.5 / 15.0 |
| 2 s median / p90 | 5.2 / 14.8 | 7.7 / 26.4 | 6.2 / 18.1 |
| chunk mean, H = 15 / 30 / 50 / 100 | 4.7 / 6.4 / 7.7 / 9.1 | 5.5 / 8.0 / 9.9 / 11.7 | 4.9 / 7.0 / 8.6 / 10.1 |

Head translation at 1 s (median / p95): Bsession 8.34 / 35.9 mm, B 8.90 / 40.4, oracle 7.46 / 36.5.
Rotation and tracking are unchanged from exp006 (same SLAM run): 0.52 deg median at 1 s, failure 0.17%.

**Error decomposition** (exp004's analysis, label position at 1 s, median):
- SLAM rotation + Bsession: 4.5 mm.
- SLAM rotation + oracle scale: 3.9 mm.
- Tile rotation + Bsession: 8.2 mm.
- Tile rotation + oracle scale: 7.3 mm.

Chunk H = 30 means: 7.0 / 6.4 / 12.6 / 12.1 mm.

**Reading.**
- **Same trade-off as exp005 on the first SAM3 masks.** Pooling k removes most of the tail: p90 drops
  from 21.7% to 17.4%, rms from 13.3% to 11.1%, and segments above 20% from 5 to 1. The cost is a
  larger bias, -7.3%, from DA2's depth compression between the near ball and the far background,
  which raises the median from 6.6% to 7.8%.
- **The labels improve clearly.** At 1 s the median drops from 5.7 to 4.5 mm (oracle 3.9) and the
  p90 from 18.7 to 15.0 mm. Chunk means improve by 0.6-1.6 mm.
- **What is left of scale in the labels** is the gap to the oracle: 0.6 mm at 1 s (median), 1.0 mm
  at H = 100 (mean).
- **The largest remaining scale error is ep29** (-31.9%). exp005 traced it to the trajectory and
  oracle side: DROID's scale varies within the segment, and tile GT exists on only 41 frames.
- **A perfect scale would not remove most of the error.** With the oracle scale, the label error is
  still 3.9 mm at 1 s and 9.1 mm at H = 100. That remainder is SLAM's motion and the tile GT's own
  noise.

## Error sources (post-hoc analysis)

[`error_sources/README.md`](error_sources/README.md) splits Bsession's scale error, with independent
checks. About half of the squared error is a bias of about -8%: the ball correction is measured at
about 0.5 m but applied to background at about 0.8 m, and DA2's correction grows with distance. A
one-off calibration would give |err| median about 5% and p90 about 13% (leave-one-out). The other
half is episode-to-episode spread, sd about 9%. A large part of it follows DA2's background scale
changing per episode, which the ball does not see, but the share cannot be cleanly separated. Two
thirds of the spread come from 9 episodes whose keyframes rarely see the tiles, and there the
reference itself is uncertain. In ep29 the oracle is 1.25 with six 2-tile frames and 0.77 without
them.
