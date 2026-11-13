# Scale Bnet+Acheck on yam_glove6_take2, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.6573 | 0.7070 | +7.6 | - | - | - |  |
| ep01 | 0.5586 | 0.5732 | +2.6 | - | - | - |  |
| ep02 | 0.7737 | 0.7947 | +2.7 | - | - | - |  |
| ep03 | 0.6091 | 0.6697 | +9.9 | - | - | - |  |
| ep04 | 0.5510 | 0.5672 | +2.9 | - | - | - |  |
| ep05 | 0.1383 | 0.1409 | +1.9 | - | - | - |  |
| ep06 | 0.8201 | 0.8185 | -0.2 | - | - | - |  |
| ep07 | 0.6294 | 0.6258 | -0.6 | - | - | - |  |
| ep08 | 0.1314 | 0.1299 | -1.2 | - | - | - |  |
| ep09 | 0.6923 | 0.7732 | +11.7 | - | - | - |  |
| ep10 | 4.8217 | 4.1822 | -13.3 | - | - | - |  |
| ep11 | 0.6568 | 0.6523 | -0.7 | - | - | - |  |
| ep12 | 0.5708 | 0.6609 | +15.8 | 0.4382 | -33.7 | -23.2 | A |
| ep13 | 0.9194 | 0.9566 | +4.0 | - | - | - |  |
| ep14 | 1.1623 | 1.2064 | +3.8 | - | - | - |  |
| ep15 | 0.2385 | 0.2344 | -1.7 | - | - | - |  |
| ep16 | 0.7039 | 0.7191 | +2.2 | - | - | - |  |
| ep17 | 0.7094 | 0.7987 | +12.6 | - | - | - |  |
| ep18 | 0.7398 | 0.7768 | +5.0 | 0.3917 | -49.6 | -47.1 | A |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 19/19 | 19 | 2.9 | 12.7 | +2.7 |
| Bnet+Acheck, without flagged |  | 17 | 2.7 | 12.0 | +2.6 |
| method Bnet alone | 19/19 | 19 | 2.9 | 12.7 | +2.7 |
| method A alone | 2/19 | 2 | 35.1 | 44.7 | -35.1 |

Flagged: 2 (ep12, ep18). Primary and every check succeeded on 2 (ep12, ep18).
