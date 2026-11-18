# Tile vs SLAM glove labels in the same action space (2026-11-17)

**Question (Yosub, sync meeting 2026-11-17).** Our SLAM arms (relative actions) and his G48 (joint space, tile labels)
differ in two ways at once: the action space and where the glove poses come from. Which one costs what?

**Setup (his option 1: relative space for both).** Pairs of arms that differ only in the glove-pose source:
- **tiles:** FK of Yosub's HHs3 joints;
- **SLAM:** the tile-free pipeline (exp039-exp044).

Everything else is identical: the 48 teleop + 194 glove episodes, Yosub's hyperparameters, seed 1000, the loss masks and
the images.
- `pilot_mix_gHs3_rel_tile_v3` and `_rel_slam_v3` were checked column by column: only the glove poses differ.
- `_rel_tile` (exp019's) equals `_rel_tile_v3` in every column.

| state | tiles | SLAM |
|---|---|---|
| gripper only | exp019 | exp046 |
| pose relative to the episode start + gripper (D2a) | **exp059 (new)** | exp053 |

[compare.py](compare.py) builds the table from each run's `results/val.json`, on the 6 robot-val episodes and
the best checkpoint by robot val. `--recheck` re-evaluated the four best checkpoints with today's code:
- the physical errors are identical to the stored ones;
- val loss differs by at most 0.0003, because the loss runs in train mode ([recheck.json](recheck.json)).

## Results ([results.md](results.md))

| state | arm | glove labels | val | pos mm j14 / j49 / j99 / chunk mean | rot | gripper |
|---|---|---|---|---|---|---|
| joint | Yosub's G48, joint space (exp049; paper 0.295) | tiles | 0.291 | 36.5 / 50.0 / 105.5 / 65.2 | 16.2° | 0.109 |
| gripper | T48 (exp018) | – | 0.491 | 33.6 / 70.5 / 143.1 / 78.7 | 18.2° | 0.123 |
| gripper | G-tile48 (exp019) | tiles | 0.458 | 29.3 / 63.8 / 135.5 / 75.3 | 17.1° | 0.125 |
| gripper | G-slam48 (exp046) | SLAM | 0.461 | 31.2 / 65.0 / 135.7 / 75.7 | 17.1° | 0.139 |
| start | T48 (exp052) | – | 0.503 | 40.9 / 75.7 / 147.4 / 87.1 | 18.5° | 0.116 |
| start | G-tile48 (exp059) | tiles | 0.446 | 36.7 / 68.4 / 134.5 / 73.1 | 16.4° | 0.130 |
| start | G-slam48 (exp053, D2a) | SLAM | 0.447 | 34.1 / 65.2 / 120.8 / 71.1 | 16.7° | 0.122 |
| pose in base (D1) | G-tile48 (exp051) | tiles | 0.404 | 31.3 / 55.3 / 106.8 / 63.2 | 14.5° | 0.111 |

- **Val losses.** All relative arms have identical action statistics (the stats files differ only in the state's), so
  their val losses compare directly. exp049's loss is in joint space; only its physical errors compare.
- **SLAM minus tiles:**
  - gripper state: val +0.003, chunk mean +0.3 mm;
  - start state: val +0.001, chunk mean -1.9 mm, step 99 -13.7 mm.

## Reading

- **SLAM labels cost nothing measurable** against tile labels in either state. The differences are within the
  checkpoint-to-checkpoint spread: exp059's step 50000 gives 72.6 mm and 127.5 mm at step 99, vs 73.1 / 134.5 at the
  best step. One seed each.
- **The gap to Yosub's G48 comes from the state, not from SLAM.**
  - With tile labels, the absolute pose state (D1, exp051) beats the start-relative state (exp059): 63.2 vs 73.1 mm,
    val 0.404 vs 0.446.
  - Like Yosub's joint angles, D1's state is the tool pose in the robot base, which only tiles give for the glove half.
- **The glove gain depends on the state, not on the label source:** -4% (tiles and SLAM) with the gripper state, -16%
  (tiles) and -18% (SLAM) with the start-relative state, in chunk mean position against the T48 of the same state.
