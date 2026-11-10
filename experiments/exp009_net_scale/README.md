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
- The ball correction made the new networks worse. They over-estimate the ball's depth by 15-25% but
  the table at the same distance far less.
- exp008 computed labels only with its primary (Bsession). This run gives the label errors that
  Bnet's scale produces.

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp009_net_scale/config.yaml
```
