# Scale Bnet+Acheck on yam_glove8, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.6948 | 0.6908 | -0.6 | - | - | - |  |
| ep01 | 1.8459 | 1.8514 | +0.3 | - | - | - |  |
| ep02 | 0.5615 | 0.6491 | +15.6 | - | - | - |  |
| ep03 | 0.6967 | 0.6939 | -0.4 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 4/4 | 4 | 0.5 | 11.1 | -0.1 |
| Bnet+Acheck, without flagged |  | 4 | 0.5 | 11.1 | -0.1 |
| method Bnet alone | 4/4 | 4 | 0.5 | 11.1 | -0.1 |
| method A alone | 0/4 | 0 | - | - | - |

Flagged: 0. Primary and every check succeeded on 0.
