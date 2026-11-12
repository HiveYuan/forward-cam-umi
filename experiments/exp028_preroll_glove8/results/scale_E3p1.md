# Scale Bnet+Acheck on yam_glove8, run E3p1

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.9260 | 0.6003 | -35.2 | - | - | - |  |
| ep01 | 0.0409 | 0.0541 | +32.4 | - | - | - |  |
| ep02 | 0.7432 | 0.7983 | +7.4 | - | - | - |  |
| ep03 | 0.7996 | 0.8559 | +7.0 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 4/4 | 4 | 19.9 | 34.3 | +7.2 |
| Bnet+Acheck, without flagged |  | 4 | 19.9 | 34.3 | +7.2 |
| method Bnet alone | 4/4 | 4 | 19.9 | 34.3 | +7.2 |
| method A alone | 0/4 | 0 | - | - | - |

Flagged: 0. Primary and every check succeeded on 0.
