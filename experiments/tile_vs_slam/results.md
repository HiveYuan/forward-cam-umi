Robot val, episodes [15, 52, 73, 84, 96, 109], best checkpoint by robot val. Position in mm (median per step j; chunk mean over all 100 steps), rotation and gripper chunk means. Val losses compare across all relative arms (the three stats files have identical action statistics; they differ only in the state's); exp049's is in joint space. D1 (exp051) needs tiles for its state too (the tool pose in the robot base), like Yosub's joint state.

| state | arm | glove labels | step | val | pos j14 / j49 / j99 / chunk mean (mm) | rot | gripper |
|---|---|---|---|---|---|---|---|
| joint | Yosub's G48, joint space (exp049; paper 0.295) | tiles | 44000 | 0.291 | 36.5 / 50.0 / 105.5 / 65.2 | 16.2° | 0.109 |
| gripper | T48 (exp018) | – | 30000 | 0.491 | 33.6 / 70.5 / 143.1 / 78.7 | 18.2° | 0.123 |
| gripper | G-tile48 (exp019) | tiles | 36000 | 0.458 | 29.3 / 63.8 / 135.5 / 75.3 | 17.1° | 0.125 |
| gripper | G-slam48 (exp046) | SLAM | 46000 | 0.461 | 31.2 / 65.0 / 135.7 / 75.7 | 17.1° | 0.139 |
| start | T48 (exp052) | – | 46000 | 0.503 | 40.9 / 75.7 / 147.4 / 87.1 | 18.5° | 0.116 |
| start | G-tile48 (exp059) | tiles | 48000 | 0.446 | 36.7 / 68.4 / 134.5 / 73.1 | 16.4° | 0.130 |
| start | G-slam48 (exp053) | SLAM | 48000 | 0.447 | 34.1 / 65.2 / 120.8 / 71.1 | 16.7° | 0.122 |
| pose in base (D1) | G-tile48 (exp051) | tiles | 48000 | 0.404 | 31.3 / 55.3 / 106.8 / 63.2 | 14.5° | 0.111 |

SLAM minus tiles (same state; negative = SLAM better):

| state | val | pos j14 | pos j49 | pos j99 | pos chunk mean | rot | gripper |
|---|---|---|---|---|---|---|---|
| gripper | +0.003 (+1%) | +2.0 (+7%) | +1.1 (+2%) | +0.2 (+0%) | +0.3 (+0%) | +0.0 (+0%) | +0.014 (+11%) |
| start | +0.001 (+0%) | -2.6 (-7%) | -3.2 (-5%) | -13.7 (-10%) | -1.9 (-3%) | +0.3 (+2%) | -0.008 (-6%) |

Glove gain (G48 vs T48 of the same state, chunk mean position):

| state | tiles | SLAM |
|---|---|---|
| gripper | -4% | -4% |
| start | -16% | -18% |
