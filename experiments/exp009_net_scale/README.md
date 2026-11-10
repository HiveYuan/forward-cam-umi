# exp009_net_scale

**What.** The scale taken from the depth network alone: `Bnet` (k = 1, no ball; s = median of
network depth / DROID depth on the background) as the primary, with the usual A cross-check. Run for
the four networks of exp008 with the best Bnet error or spread:
- DA3 metric + K;
- MoGe-2;
- UniDepth V2 + K;
- Metric3D v2 + K.

Also: tool labels and evaluation per network, and exp004's error decomposition for DA3. Analysis
only; the producers are exp008's (cache hits).

**Why.** exp008 (`../exp008_depth_models/compare.md`), on the 22 well-tiled episodes:
- Bnet with DA3 metric + K had scale |err| 3.1% median / 6.9% p90 and bias +0.8%, with no ball. The
  default (DA2 + Bsession) had 6.9% / 11.4%, bias -5.5%.
- The ball over-corrects the new networks (k_session 0.72-0.87 against k_need 0.86-0.99): they
  over-estimate the ball's depth more than the surfaces'. For DA3, MoGe-2, UniDepth and Depth Pro + K,
  Bnet beats Bsession on the median; for Metric3D, Bsession is better.
- exp008 computed labels only with its primary (Bsession). This run gives the label errors that
  Bnet's scale produces.

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp009_net_scale/config.yaml
```

## Results

The run took 1.8 min, all producers cache hits. Run at f2ceaec.

| | scale \|err\| med / p90, bias (28) | scale (22) | labels 1 s med / p90 | 2 s | chunk mean H = 15 / 30 / 50 / 100 |
|---|---|---|---|---|---|
| oracle scale | - | - | 3.9 / 13.9 mm | 5.2 / 14.8 | 4.7 / 6.4 / 7.7 / 9.1 |
| **DA3 metric + K, Bnet** | 3.1 / 9.4%, -0.1% | 3.1 / 6.9% | **4.2 / 14.2** | 5.4 / 16.1 | 4.8 / 6.6 / 8.0 / 9.4 |
| MoGe-2, Bnet | 4.2 / 11.0%, +2.0% | 4.2 / 10.2% | 4.1 / 15.5 | 5.3 / 16.7 | 4.9 / 6.8 / 8.3 / 10.0 |
| UniDepth V2 + K, Bnet | 6.7 / 17.0%, +6.5% | 6.5 / 16.1% | 4.7 / 16.3 | 6.4 / 18.3 | 5.1 / 7.2 / 8.9 / 10.7 |
| Metric3D v2 + K, Bnet | 10.0 / 14.1%, +9.5% | 9.0 / 13.9% | 4.6 / 19.4 | 6.6 / 23.6 | 5.5 / 7.8 / 9.7 / 11.6 |
| exp007 default: DA2, Bsession | 7.8 / 17.4%, -7.3% | 6.9 / 11.4% | 4.5 / 15.0 | 6.2 / 18.1 | 4.9 / 7.0 / 8.6 / 10.1 |

989 label anchors in every row.

**Error decomposition, DA3 + Bnet** (exp004's analysis, label position at 1 s, median):

| head rotation | Bnet scale | oracle scale |
|---|---|---|
| SLAM | 4.2 mm | 3.9 mm |
| tile | 7.6 mm | 7.3 mm |

exp007 had 4.5 and 8.2 mm with Bsession in the same two positions.

**A cross-check.** A flags 6 segments with DA3: ep01, 09, 19, 20, 28 and 29. A itself is biased
about 5% low (exp000, body sway), so with an unbiased primary more segments cross the 10%
threshold. The flags are informational and change nothing.

**Reading.**
- **DA3 metric + K without the ball closes most of the scale gap.** The label error that scale
  adds over the oracle drops from 0.6 to 0.3 mm at 1 s and from 1.0 to 0.3 mm at H = 100.
  What remains is SLAM's motion error and the tile GT's own noise.
- **The p90 tail at 2 s also shrinks**: 16.1 mm against 18.1 mm for exp007 (oracle 14.8).
- **MoGe-2 is close behind**: 4.1 mm at 1 s, but 10.0 mm at H = 100.
- **Caveats.**
  - This is one session, scene and camera. A metric depth network's absolute scale depends on
    the scene; within this session its spread is 4.9%.
  - The near-zero bias may not carry over to other scenes. In the wild there is no tile oracle to
    check it.
  - The ball can no longer be the absolute reference (exp008: the networks misjudge it). It can
    still be a relative check: k moving away from the session's usual value.
