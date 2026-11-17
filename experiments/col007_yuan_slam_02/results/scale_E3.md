# Scale Bnet+Acheck on yuan_slam_02, run E3

s = Bnet on every segment where it succeeds; checks A only compare: |s_check/s - 1| > 10% flags the segment (recorded; s and the segment are kept).

| segment | oracle s | s | err % | A s | A/s - 1 % | A err % | flagged |
|---|---|---|---|---|---|---|---|
| ep00 | 0.4774 | 0.3775 | -20.9 | - | - | - |  |
| ep01 | 0.7956 | 0.7450 | -6.4 | - | - | - |  |
| ep03 | 0.7872 | 0.7232 | -8.1 | - | - | - |  |
| ep04 | 0.2500 | 0.2569 | +2.7 | 0.2490 | -3.0 | -0.4 |  |
| ep05 | 0.5710 | 0.5903 | +3.4 | - | - | - |  |
| ep07 | 0.6874 | 0.6968 | +1.4 | 0.8664 | +24.3 | +26.0 | A |
| ep08 | 0.3909 | 0.5468 | +39.9 | 0.6022 | +10.1 | +54.1 | A |
| ep09 | 0.8485 | 0.6808 | -19.8 | 0.9155 | +34.5 | +7.9 | A |
| ep11 | 0.0653 | 0.8528 | +1205.9 | 0.8478 | -0.6 | +1198.3 |  |
| ep12 | 0.6291 | 0.3502 | -44.3 | - | - | - |  |

Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:

| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |
|---|---|---|---|---|---|
| Bnet+Acheck, all | 10/10 | 10 | 14.0 | 160.5 | -2.5 |
| Bnet+Acheck, without flagged |  | 7 | 8.1 | 509.0 | -6.4 |
| method Bnet alone | 10/10 | 10 | 14.0 | 160.5 | -2.5 |
| method A alone | 5/10 | 5 | 26.0 | 740.6 | +26.0 |

Flagged: 3 (ep07, ep08, ep09). Primary and every check succeeded on 5 (ep04, ep07, ep08, ep09, ep11).
