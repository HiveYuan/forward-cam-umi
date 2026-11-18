# Scale Bpar+Acheck on yuan_slam_01, run E3

s = Bpar on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep02 | 0.4193 | 1.8219 | +334.5 | - | - | - |  |
| ep03 | 0.8545 | 0.7448 | -12.8 | 0.8843 | +18.7 | +3.5 | A |
| ep05 | 0.8389 | 0.8781 | +4.7 | 0.8432 | -4.0 | +0.5 |  |
| ep06 | 0.7103 | 0.7104 | +0.0 | - | - | - |  |
| ep07 | 0.6487 | 0.7466 | +15.1 | 0.8279 | +10.9 | +27.6 | A |
| ep08 | 1.3930 | 1.3089 | -6.0 | - | - | - |  |
| ep10 | 0.1158 | 0.0903 | -22.0 | - | - | - |  |
| ep14 | 0.5300 | 0.5577 | +5.2 | 0.5607 | +0.5 | +5.8 |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bpar+Acheck, all | 8/8 | 8 | 9.4 | 115.8 | +2.3 |
| Bpar+Acheck, without flagged |  | 6 | 5.6 | 178.3 | +2.3 |
| method Bpar alone | 8/8 | 8 | 9.4 | 115.8 | +2.3 |
| method A alone | 4/8 | 4 | 4.6 | 21.1 | +4.6 |

Flagged: 2 (ep03, ep07). Primary and every check succeeded on 4 (ep03, ep05, ep07, ep14).
