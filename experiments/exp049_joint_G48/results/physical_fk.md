# exp049_joint_G48: physical chunk errors (FK of the joint chunks, VAE latent 0)

Median over non-padded steps at j; chunk mean over all steps (comparable with val.md of the relative runs).

| checkpoint | set | pos mm j0 / j14 / j49 / j99 / chunk mean | rot deg j0 / j14 / j49 / j99 / mean | gripper chunk mean |
|---|---|---|---|---|
| best (44000) | glove | 22.5 / 35.3 / 51.0 / 101.3 / 71.2 | 5.03 / 7.35 / 13.11 / 25.30 / 16.19 | 0.082 |
| best (44000) | robot | 25.1 / 36.5 / 50.0 / 105.5 / 65.2 | 7.15 / 10.44 / 13.84 / 17.41 / 16.18 | 0.109 |
| last (50000) | glove | 20.9 / 32.2 / 49.0 / 110.7 / 70.6 | 4.55 / 7.05 / 12.54 / 25.27 / 15.96 | 0.083 |
| last (50000) | robot | 23.5 / 35.4 / 54.2 / 101.2 / 66.9 | 6.75 / 10.92 / 14.87 / 18.42 / 16.21 | 0.102 |
