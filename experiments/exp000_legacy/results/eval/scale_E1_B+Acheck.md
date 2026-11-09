# Scale B+Acheck on yam_glove7, run E1

B is the scale on every segment; A (static ball) is only a cross-check: |s_A/s_B - 1| > 10% flags a segment (recorded only; s and the segment are kept).

## Scale error vs the tile oracle (s/s_oracle - 1)

| set | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) |
|---|---|---|---|---|---|
| all | 30/30 | 28 | 15.1% | 30.7% | -3.9% |
| without flagged | 25/30 | 23 | 15.0% | 32.2% | -5.0% |

## Cross-check A vs B

Segments where both A and B give a scale: 10 (ep01, ep10, ep12, ep15, ep19, ep24, ep26, ep27, ep28, ep29). Flagged: 5 (ep01, ep12, ep15, ep24, ep29).

| segment | A/B - 1 | A err vs oracle | B err vs oracle | flagged | which is wrong |
|---|---|---|---|---|---|
| ep01 | -23.3% | -20.7% | +3.4% | yes | A |
| ep10 | -8.8% | -10.1% | -1.4% |  | - |
| ep12 | +18.9% | -3.2% | -18.6% | yes | B |
| ep15 | -26.3% | -4.7% | +29.3% | yes | B |
| ep19 | -0.9% | +22.1% | +23.2% |  | - |
| ep24 | +18.1% | +20.0% | +1.6% | yes | A |
| ep26 | +5.8% | -0.1% | -5.6% |  | - |
| ep27 | +7.2% | +43.5% | +33.8% |  | - |
| ep28 | +8.7% | +6.3% | -2.2% |  | - |
| ep29 | -14.0% | -27.1% | -15.2% | yes | A |

## Label error: tool_t->tool_t+dt position [mm], median / p90, vs tile labels

| labels | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| E1, scale B+Acheck | 989 | 1.6 / 5.9 | 2.4 / 9.4 | 3.8 / 15.1 | 5.5 / 23.7 | 7.9 / 42.3 | 10.3 / 70.6 | 14.1 / 97.6 | 12.5 / 89.0 |
| E1, tile (oracle) scale | 989 | 1.6 / 5.4 | 2.4 / 9.0 | 3.6 / 15.0 | 5.0 / 23.6 | 7.0 / 40.2 | 8.2 / 70.4 | 8.7 / 81.9 | 10.0 / 88.4 |
| E1, scale B+Acheck, without flagged | 711 | 1.6 / 5.8 | 2.4 / 9.3 | 3.7 / 15.6 | 5.5 / 26.9 | 8.1 / 48.1 | 10.6 / 75.8 | 11.8 / 123.7 | 5.7 / 91.7 |
| E1, tile scale, without flagged | 711 | 1.6 / 5.1 | 2.4 / 8.9 | 3.7 / 15.3 | 5.5 / 27.3 | 8.1 / 48.1 | 9.6 / 73.6 | 12.3 / 88.7 | 5.8 / 91.0 |

Label anchors exist only where the tile labels (>= 2 tiles, 70% coverage) also exist.
