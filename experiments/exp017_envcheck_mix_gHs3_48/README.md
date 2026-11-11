# exp017_envcheck_mix_gHs3_48

**What.** Yosub's arm `mix_gHs3_48` (joint actions, his `pilot_mix_gHs3`, his train config: ACT, chunk 100,
VAE, batch 8, lr 1e-5, seed 1000) retrained in our P3 environment (`lerobot52`: his `lerobot_alohamini`
at 0cae109f = lerobot 0.5.2, torch 2.11) for 10k of its 50k steps.

**Why.** Before training the relative-action arms, check that our environment trains like his: the
robot-val loss (`slam.val_rel`, = his `scripts/compute_val_loss.py`) at 2k-10k steps against his curve
in `docs/results/head_val_curves.csv` (1.388, 0.718, 0.490, 0.459, 0.380). GPU training is not bitwise
deterministic, so a match within a few percent is the expectation.
