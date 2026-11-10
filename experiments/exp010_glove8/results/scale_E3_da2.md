# Scale Bsession+Acheck on yam_glove8, run E3_da2

s = Bsession on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.6554 | 0.5825 | -11.1 | - | - | - |  |
| ep01 | 1.4676 | 1.3260 | -9.6 | - | - | - |  |
| ep02 | 0.6741 | 0.7492 | +11.1 | - | - | - |  |
| ep03 | 0.8316 | 0.7660 | -7.9 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bsession+Acheck, all | 4/4 | 4 | 10.4 | 11.1 | -8.8 |
| Bsession+Acheck, without flagged |  | 4 | 10.4 | 11.1 | -8.8 |
| method Bsession alone | 4/4 | 4 | 10.4 | 11.1 | -8.8 |
| method A alone | 0/4 | 0 | - | - | - |

Flagged: 0. Primary and every check succeeded on 0.

## Session ball correction (Bsession)

k_session = 0.5721 (pool segments: 4 segments with ball samples, 45 samples); per-segment k p10 / p25 / p75 / p90 = 0.391 / 0.504 / 0.578 / 0.579.

Per segment: own k (ball samples), s with the own k (= B) and with k_session (= Bsession), errors vs the tile oracle:

| segment | own k | ball samples | k/k_session - 1 % | s own k | err own k % | s | err % |
|---|---|---|---|---|---|---|---|
| ep00 | 0.315 | 16 | -44.9 | 0.3212 | -51.0 | 0.5825 | -11.1 |
| ep01 | 0.577 | 7 | +0.9 | 1.3384 | -8.8 | 1.3260 | -9.6 |
| ep02 | 0.567 | 10 | -0.9 | 0.7422 | +10.1 | 0.7492 | +11.1 |
| ep03 | 0.579 | 12 | +1.3 | 0.7757 | -6.7 | 0.7660 | -7.9 |
