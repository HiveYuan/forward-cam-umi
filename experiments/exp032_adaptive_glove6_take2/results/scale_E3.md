# Scale Bnet+Acheck on yam_glove6_take2, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.6706 | 0.7204 | +7.4 | - | - | - |  |
| ep01 | 0.5586 | 0.5732 | +2.6 | - | - | - |  |
| ep02 | 0.7737 | 0.7947 | +2.7 | - | - | - |  |
| ep03 | 0.6040 | 0.6391 | +5.8 | - | - | - |  |
| ep04 | 0.2538 | 0.2640 | +4.0 | - | - | - |  |
| ep05 | 0.1383 | 0.1409 | +1.9 | - | - | - |  |
| ep06 | 0.6219 | 0.6207 | -0.2 | - | - | - |  |
| ep07 | 0.6707 | 0.6683 | -0.4 | - | - | - |  |
| ep08 | 0.1554 | 0.1534 | -1.2 | - | - | - |  |
| ep09 | 0.7208 | 0.8076 | +12.0 | - | - | - |  |
| ep10 | 0.7070 | 0.7063 | -0.1 | - | - | - |  |
| ep11 | 0.6916 | 0.6832 | -1.2 | - | - | - |  |
| ep12 | 0.6028 | 0.6974 | +15.7 | 0.4617 | -33.8 | -23.4 | A |
| ep13 | 0.9194 | 0.9566 | +4.0 | - | - | - |  |
| ep14 | 1.1623 | 1.2064 | +3.8 | - | - | - |  |
| ep15 | 0.2121 | 0.2072 | -2.3 | - | - | - |  |
| ep16 | 0.6368 | 0.6511 | +2.2 | - | - | - |  |
| ep17 | 0.7094 | 0.7987 | +12.6 | - | - | - |  |
| ep18 | 0.7398 | 0.7768 | +5.0 | 0.3917 | -49.6 | -47.1 | A |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 19/19 | 19 | 2.7 | 12.2 | +2.7 |
| Bnet+Acheck, without flagged |  | 17 | 2.6 | 9.3 | +2.6 |
| method Bnet alone | 19/19 | 19 | 2.7 | 12.2 | +2.7 |
| method A alone | 2/19 | 2 | 35.2 | 44.7 | -35.2 |

Flagged: 2 (ep12, ep18). Primary and every check succeeded on 2 (ep12, ep18).
