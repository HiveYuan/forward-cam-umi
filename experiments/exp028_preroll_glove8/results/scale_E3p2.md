# Scale Bnet+Acheck on yam_glove8, run E3p2

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.7398 | 0.7038 | -4.9 | - | - | - |  |
| ep01 | 1.5358 | 1.4221 | -7.4 | - | - | - |  |
| ep02 | 0.6939 | 0.7586 | +9.3 | - | - | - |  |
| ep03 | 0.8507 | 0.8581 | +0.9 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 4/4 | 4 | 6.1 | 8.8 | -2.0 |
| Bnet+Acheck, without flagged |  | 4 | 6.1 | 8.8 | -2.0 |
| method Bnet alone | 4/4 | 4 | 6.1 | 8.8 | -2.0 |
| method A alone | 0/4 | 0 | - | - | - |

Flagged: 0. Primary and every check succeeded on 0.
