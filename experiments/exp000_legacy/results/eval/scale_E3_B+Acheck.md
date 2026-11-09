# Scale B+Acheck on yam_glove7, run E3

B is the scale on every segment; A (static ball) is only a cross-check: |s_A/s_B - 1| > 10% flags a segment (recorded only; s and the segment are kept).

## Scale error vs the tile oracle (s/s_oracle - 1)

| set | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) |
|---|---|---|---|---|---|
| all | 30/30 | 28 | 5.8% | 21.4% | -5.3% |
| without flagged | 27/30 | 25 | 5.2% | 20.4% | -4.8% |

## Cross-check A vs B

Segments where both A and B give a scale: 9 (ep01, ep09, ep10, ep12, ep15, ep19, ep24, ep26, ep27). Flagged: 3 (ep01, ep12, ep15).

| segment | A/B - 1 | A err vs oracle | B err vs oracle | flagged | which is wrong |
|---|---|---|---|---|---|
| ep01 | -14.7% | -9.7% | +5.9% | yes | A |
| ep09 | -0.8% | -16.5% | -15.9% |  | - |
| ep10 | -0.3% | -5.1% | -4.8% |  | - |
| ep12 | +19.5% | -5.6% | -21.0% | yes | B |
| ep15 | +19.6% | -4.7% | -20.4% | yes | B |
| ep19 | +5.1% | +7.2% | +2.0% |  | - |
| ep24 | +2.0% | -2.6% | -4.5% |  | - |
| ep26 | +4.2% | -4.5% | -8.3% |  | - |
| ep27 | -1.4% | -2.4% | -0.9% |  | - |

## Label error: tool_t->tool_t+dt position [mm], median / p90, vs tile labels

| labels | anchors | 0.07 s | 0.13 s | 0.27 s | 0.53 s | 1.00 s | 2.00 s | 4.00 s | 6.67 s |
|---|---|---|---|---|---|---|---|---|---|
| E3, scale B+Acheck | 989 | 1.2 / 3.8 | 1.7 / 6.3 | 2.5 / 9.1 | 3.7 / 13.7 | 5.9 / 19.5 | 7.9 / 27.4 | 7.6 / 33.2 | 6.2 / 15.3 |
| E3, tile (oracle) scale | 989 | 1.2 / 3.9 | 1.6 / 6.0 | 2.3 / 7.7 | 3.1 / 11.3 | 4.0 / 14.1 | 5.2 / 15.0 | 5.9 / 14.3 | 5.6 / 7.9 |
| E3, scale B+Acheck, without flagged | 792 | 1.2 / 4.3 | 1.7 / 6.4 | 2.5 / 9.2 | 3.6 / 13.6 | 5.8 / 18.8 | 7.7 / 26.4 | 7.1 / 30.2 | 6.2 / 15.7 |
| E3, tile scale, without flagged | 792 | 1.2 / 4.4 | 1.6 / 6.5 | 2.3 / 8.5 | 3.2 / 12.1 | 4.6 / 15.2 | 6.0 / 19.0 | 6.2 / 17.6 | 5.8 / 8.0 |

Label anchors exist only where the tile labels (>= 2 tiles, 70% coverage) also exist.
