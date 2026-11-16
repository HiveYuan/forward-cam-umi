# Scale Bnet+Acheck on yuan_pilot_01b, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 1.0128 | 0.8940 | -11.7 | 1.3063 | +46.1 | +29.0 | A |
| ep01 | 1.0297 | 0.9713 | -5.7 | - | - | - |  |
| ep02 | 0.2997 | 0.3350 | +11.8 | 0.3445 | +2.8 | +14.9 |  |
| ep03 | 0.9565 | 0.7904 | -17.4 | 0.9128 | +15.5 | -4.6 | A |
| ep04 | 0.7913 | 0.7444 | -5.9 | 0.7977 | +7.2 | +0.8 |  |
| ep05 | 1.0072 | 0.9299 | -7.7 | 1.0892 | +17.1 | +8.1 | A |
| ep06 | 1.1574 | 1.0528 | -9.0 | 1.1091 | +5.4 | -4.2 |  |
| ep07 | 0.0561 | 0.0489 | -13.0 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 8/8 | 8 | 10.4 | 14.3 | -8.4 |
| Bnet+Acheck, without flagged |  | 5 | 9.0 | 12.5 | -5.9 |
| method Bnet alone | 8/8 | 8 | 10.4 | 14.3 | -8.4 |
| method A alone | 6/8 | 6 | 6.4 | 22.0 | +4.5 |

Flagged: 3 (ep00, ep03, ep05). Primary and every check succeeded on 6 (ep00, ep02, ep03, ep04, ep05, ep06).
