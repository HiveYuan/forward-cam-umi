# Scale Bnet+Acheck on yam_glove6_take2, run E3p2

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.7027 | 0.7971 | +13.4 | - | - | - |  |
| ep01 | 1.0661 | 1.1052 | +3.7 | - | - | - |  |
| ep02 | 1.8040 | 1.7508 | -3.0 | - | - | - |  |
| ep03 | 0.8934 | 0.8843 | -1.0 | - | - | - |  |
| ep04 | 0.6972 | 0.7372 | +5.7 | - | - | - |  |
| ep05 | 0.9336 | 0.9615 | +3.0 | - | - | - |  |
| ep06 | 0.9620 | 0.9121 | -5.2 | - | - | - |  |
| ep07 | 0.7315 | 0.6459 | -11.7 | - | - | - |  |
| ep08 | 0.7856 | 0.8319 | +5.9 | - | - | - |  |
| ep09 | 1.1804 | 1.2220 | +3.5 | - | - | - |  |
| ep10 | 0.6652 | 0.6317 | -5.0 | - | - | - |  |
| ep11 | 1.1501 | 1.0637 | -7.5 | - | - | - |  |
| ep12 | 0.4767 | 0.5373 | +12.7 | 0.3537 | -34.2 | -25.8 | A |
| ep13 | 1.9261 | 1.8673 | -3.1 | - | - | - |  |
| ep14 | 0.4502 | 0.4638 | +3.0 | - | - | - |  |
| ep15 | 1.4292 | 1.3846 | -3.1 | - | - | - |  |
| ep16 | 2.3742 | 2.4292 | +2.3 | - | - | - |  |
| ep17 | 1.6217 | 0.6854 | -57.7 | - | - | - |  |
| ep18 | 0.9667 | 1.0040 | +3.9 | 0.5376 | -46.4 | -44.4 | A |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 19/19 | 19 | 3.9 | 12.8 | +2.3 |
| Bnet+Acheck, without flagged |  | 17 | 3.7 | 12.4 | -1.0 |
| method Bnet alone | 19/19 | 19 | 3.9 | 12.8 | +2.3 |
| method A alone | 2/19 | 2 | 35.1 | 42.5 | -35.1 |

Flagged: 2 (ep12, ep18). Primary and every check succeeded on 2 (ep12, ep18).
