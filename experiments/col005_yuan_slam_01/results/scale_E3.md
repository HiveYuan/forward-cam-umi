# Scale Bnet+Acheck on yuan_slam_01, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep02 | 0.4193 | 0.4579 | +9.2 | - | - | - |  |
| ep03 | 0.8545 | 0.6517 | -23.7 | 0.8843 | +35.7 | +3.5 | A |
| ep05 | 0.8389 | 0.8083 | -3.6 | 0.8432 | +4.3 | +0.5 |  |
| ep06 | 0.7103 | 0.6885 | -3.1 | - | - | - |  |
| ep07 | 0.6487 | 0.6609 | +1.9 | 0.8279 | +25.3 | +27.6 | A |
| ep08 | 1.3930 | 0.6289 | -54.9 | - | - | - |  |
| ep10 | 0.1158 | 0.0834 | -27.9 | - | - | - |  |
| ep14 | 0.5300 | 0.5354 | +1.0 | 0.5607 | +4.7 | +5.8 |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 8/8 | 8 | 6.4 | 36.0 | -3.4 |
| Bnet+Acheck, without flagged |  | 6 | 6.4 | 41.4 | -3.4 |
| method Bnet alone | 8/8 | 8 | 6.4 | 36.0 | -3.4 |
| method A alone | 4/8 | 4 | 4.6 | 21.1 | +4.6 |

Flagged: 2 (ep03, ep07). Primary and every check succeeded on 4 (ep03, ep05, ep07, ep14).
