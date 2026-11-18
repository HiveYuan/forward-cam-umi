# Scale Bpar+Acheck on yuan_slam_02, run E3

s = Bpar on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.4774 | 0.3926 | -17.8 | - | - | - |  |
| ep01 | 0.7956 | 0.7813 | -1.8 | - | - | - |  |
| ep03 | 0.7872 | 0.7660 | -2.7 | - | - | - |  |
| ep04 | 0.2500 | 0.2680 | +7.2 | 0.2490 | -7.1 | -0.4 |  |
| ep05 | 0.5710 | 0.6215 | +8.9 | - | - | - |  |
| ep07 | 0.6874 | 0.7111 | +3.4 | 0.8664 | +21.8 | +26.0 | A |
| ep08 | 0.3909 | 0.5474 | +40.1 | 0.6022 | +10.0 | +54.1 |  |
| ep09 | 0.8485 | 0.7790 | -8.2 | 0.9155 | +17.5 | +7.9 | A |
| ep11 | 0.0653 | 0.8593 | +1215.9 | 0.8478 | -1.3 | +1198.3 |  |
| ep12 | 0.6291 | 0.4050 | -35.6 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bpar+Acheck, all | 10/10 | 10 | 8.5 | 157.6 | +0.8 |
| Bpar+Acheck, without flagged |  | 8 | 13.3 | 392.8 | +2.7 |
| method Bpar alone | 10/10 | 10 | 8.5 | 157.6 | +0.8 |
| method A alone | 5/10 | 5 | 26.0 | 740.6 | +26.0 |

Flagged: 2 (ep07, ep09). Primary and every check succeeded on 5 (ep04, ep07, ep08, ep09, ep11).
