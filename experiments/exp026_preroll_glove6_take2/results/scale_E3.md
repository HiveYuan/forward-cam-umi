# Scale Bnet+Acheck on yam_glove6_take2, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.6706 | 0.7204 | +7.4 | - | - | - |  |
| ep01 | 0.5586 | 0.5732 | +2.6 | - | - | - |  |
| ep02 | 0.5748 | 0.5944 | +3.4 | - | - | - |  |
| ep03 | 0.6040 | 0.6391 | +5.8 | - | - | - |  |
| ep04 | 0.2538 | 0.2640 | +4.0 | - | - | - |  |
| ep05 | 0.1383 | 0.1409 | +1.9 | - | - | - |  |
| ep06 | 0.6219 | 0.6207 | -0.2 | - | - | - |  |
| ep07 | 0.6707 | 0.6683 | -0.4 | - | - | - |  |
| ep08 | 0.1554 | 0.1534 | -1.2 | - | - | - |  |
| ep09 | 1.2689 | 1.1461 | -9.7 | - | - | - |  |
| ep10 | 4.8212 | 4.2264 | -12.3 | - | - | - |  |
| ep11 | 0.6916 | 0.6832 | -1.2 | - | - | - |  |
| ep12 | 0.6028 | 0.6974 | +15.7 | 0.4617 | -33.8 | -23.4 | A |
| ep13 | 0.9194 | 0.9566 | +4.0 | - | - | - |  |
| ep14 | 1.1623 | 1.2064 | +3.8 | - | - | - |  |
| ep15 | 0.2121 | 0.2072 | -2.3 | - | - | - |  |
| ep16 | 0.6368 | 0.6511 | +2.2 | - | - | - |  |
| ep17 | 0.8519 | 1.0041 | +17.9 | - | - | - |  |
| ep18 | 0.7398 | 0.7768 | +5.0 | 0.3917 | -49.6 | -47.1 | A |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 19/19 | 19 | 3.8 | 13.0 | +2.6 |
| Bnet+Acheck, without flagged |  | 17 | 3.4 | 10.7 | +2.2 |
| method Bnet alone | 19/19 | 19 | 3.8 | 13.0 | +2.6 |
| method A alone | 2/19 | 2 | 35.2 | 44.7 | -35.2 |

Flagged: 2 (ep12, ep18). Primary and every check succeeded on 2 (ep12, ep18).
