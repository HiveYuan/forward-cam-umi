# Scale Bnet+Acheck on yuan_pilot_01c, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.9703 | 0.6620 | -31.8 | 1.1043 | +66.8 | +13.8 | A |
| ep01 | 1.2744 | 1.1572 | -9.2 | 1.3795 | +19.2 | +8.3 | A |
| ep02 | 0.7767 | 0.7441 | -4.2 | 1.0439 | +40.3 | +34.4 | A |
| ep03 | 0.8589 | 0.9221 | +7.4 | - | - | - |  |
| ep04 | 0.9088 | 0.8861 | -2.5 | - | - | - |  |
| ep05 | 0.8501 | 0.8335 | -2.0 | 0.7298 | -12.4 | -14.2 | A |
| ep06 | 0.6715 | 0.6203 | -7.6 | - | - | - |  |
| ep07 | 0.7786 | 0.7419 | -4.7 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 8/8 | 8 | 6.0 | 16.0 | -4.5 |
| Bnet+Acheck, without flagged |  | 4 | 6.0 | 7.5 | -3.6 |
| method Bnet alone | 8/8 | 8 | 6.0 | 16.0 | -4.5 |
| method A alone | 4/8 | 4 | 14.0 | 28.3 | +11.0 |

Flagged: 4 (ep00, ep01, ep02, ep05). Primary and every check succeeded on 4 (ep00, ep01, ep02, ep05).
