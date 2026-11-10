# Scale Bnet+Acheck on yam_glove8, run E3_da3m

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.6554 | 0.6511 | -0.7 | - | - | - |  |
| ep01 | 1.4676 | 1.4811 | +0.9 | - | - | - |  |
| ep02 | 0.6741 | 0.8099 | +20.1 | - | - | - |  |
| ep03 | 0.8316 | 0.8274 | -0.5 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 4/4 | 4 | 0.8 | 14.4 | +0.2 |
| Bnet+Acheck, without flagged |  | 4 | 0.8 | 14.4 | +0.2 |
| method Bnet alone | 4/4 | 4 | 0.8 | 14.4 | +0.2 |
| method A alone | 0/4 | 0 | - | - | - |

Flagged: 0. Primary and every check succeeded on 0.
