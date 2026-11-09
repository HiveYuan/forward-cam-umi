# Scale B+Acheck on yam_glove7, run E2

B is the scale on every segment; A (static ball) is only a cross-check: |s_A/s_B - 1| > 10% flags a segment (recorded only; s and the segment are kept).

## Scale error vs the tile oracle (s/s_oracle - 1)

| set | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) |
|---|---|---|---|---|---|
| all | 30/30 | 28 | 10.3% | 20.6% | -10.3% |
| without flagged | 23/30 | 21 | 6.0% | 18.0% | -6.0% |

## Cross-check A vs B

Segments where both A and B give a scale: 12 (ep01, ep09, ep10, ep11, ep12, ep15, ep19, ep20, ep24, ep26, ep28, ep29). Flagged: 7 (ep01, ep11, ep12, ep15, ep20, ep28, ep29).

| segment | A/B - 1 | A err vs oracle | B err vs oracle | flagged | which is wrong |
|---|---|---|---|---|---|
| ep01 | -16.0% | -9.8% | +7.4% | yes | A |
| ep09 | +2.0% | -16.2% | -17.8% |  | - |
| ep10 | +0.9% | -5.1% | -5.9% |  | - |
| ep11 | +14.9% | -3.7% | -16.2% | yes | B |
| ep12 | +22.8% | -0.2% | -18.7% | yes | B |
| ep15 | +10.5% | -5.3% | -14.3% | yes | B |
| ep19 | +4.7% | +7.1% | +2.3% |  | - |
| ep20 | +47.9% | -3.4% | -34.7% | yes | B |
| ep24 | +3.2% | -2.7% | -5.7% |  | - |
| ep26 | +2.7% | -5.5% | -8.0% |  | - |
| ep28 | +18.0% | +3.4% | -12.3% | yes | B |
| ep29 | -10.9% | -32.0% | -23.7% | yes | A |

## Label error: tool_t->tool_t+dt position [mm], median / p90, vs tile labels

| labels | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| E2, scale B+Acheck | 989 | 1.2 / 3.5 | 1.7 / 5.6 | 2.4 / 8.5 | 3.5 / 13.4 | 5.3 / 18.6 | 7.3 / 25.7 | 7.0 / 34.8 | 5.5 / 16.8 |
| E2, tile (oracle) scale | 989 | 1.1 / 3.6 | 1.6 / 5.5 | 2.1 / 7.3 | 2.7 / 11.1 | 3.6 / 13.2 | 4.7 / 13.3 | 5.5 / 12.8 | 4.7 / 7.1 |
| E2, scale B+Acheck, without flagged | 711 | 1.2 / 3.8 | 1.7 / 5.7 | 2.4 / 8.0 | 3.5 / 12.8 | 5.3 / 17.5 | 7.5 / 22.6 | 6.9 / 41.4 | 6.0 / 17.1 |
| E2, tile scale, without flagged | 711 | 1.2 / 4.0 | 1.6 / 5.9 | 2.2 / 7.9 | 3.0 / 12.2 | 4.1 / 14.0 | 5.1 / 15.3 | 5.6 / 41.4 | 5.0 / 7.1 |

Label anchors exist only where the tile labels (>= 2 tiles, 70% coverage) also exist.
