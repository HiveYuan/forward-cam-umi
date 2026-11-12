# Scale Bnet+Acheck on yam_glove6_take2, run E3p1

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.5459 | 0.6095 | +11.7 | - | - | - |  |
| ep01 | 0.6831 | 0.7709 | +12.9 | - | - | - |  |
| ep02 | 0.7737 | 0.7947 | +2.7 | - | - | - |  |
| ep03 | 0.4820 | 0.4997 | +3.7 | - | - | - |  |
| ep04 | 0.8230 | 0.8413 | +2.2 | - | - | - |  |
| ep05 | 0.3402 | 0.4329 | +27.2 | - | - | - |  |
| ep06 | 0.8632 | 0.8554 | -0.9 | - | - | - |  |
| ep07 | 0.9566 | 0.9521 | -0.5 | - | - | - |  |
| ep08 | 1.0185 | 0.9242 | -9.3 | - | - | - |  |
| ep09 | 0.7208 | 0.8076 | +12.0 | - | - | - |  |
| ep10 | 0.7070 | 0.7063 | -0.1 | - | - | - |  |
| ep11 | 0.9279 | 0.7701 | -17.0 | - | - | - |  |
| ep12 | 0.6455 | 0.7143 | +10.7 | 0.4770 | -33.2 | -26.1 | A |
| ep13 | 0.7132 | 0.7916 | +11.0 | - | - | - |  |
| ep14 | 0.9824 | 0.8252 | -16.0 | - | - | - |  |
| ep15 | 0.8219 | 0.7830 | -4.7 | - | - | - |  |
| ep16 | 0.5641 | 0.6243 | +10.7 | - | - | - |  |
| ep17 | 0.7094 | 0.7987 | +12.6 | - | - | - |  |
| ep18 | 0.8616 | 0.9018 | +4.7 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 19/19 | 19 | 10.7 | 16.2 | +3.7 |
| Bnet+Acheck, without flagged |  | 18 | 10.0 | 16.3 | +3.2 |
| method Bnet alone | 19/19 | 19 | 10.7 | 16.2 | +3.7 |
| method A alone | 1/19 | 1 | 26.1 | 26.1 | -26.1 |

Flagged: 1 (ep12). Primary and every check succeeded on 1 (ep12).
