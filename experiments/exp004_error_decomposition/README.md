# exp004_error_decomposition

**What.** exp003 unchanged (SAM3 masks, DROID E1/E2/E3, scale B+Acheck; every producer comes from
exp003's cache), plus the `error_decomp` analysis step (`slam/pipeline/impl_error_decomp.py`) on E3.
It splits the tool label error into what the SLAM head rotation causes and what the scale causes.
For every label pair (t, t+dt) on the 15 fps training timeline, the head motion cam_t->cam_t+dt is
rebuilt from one rotation source and one scale. The translation is always SLAM's:

| combination | rotation of cam_t->cam_t+dt | translation | stands for |
|---|---|---|---|
| (1) R_slam+s_configured | SLAM | s_B+Acheck x t_slam | the real pipeline, = `labels_E3@B+Acheck` |
| (2) R_slam+s_oracle | SLAM | s_oracle x t_slam | perfect global scale (~ stereo), = `labels_E3` |
| (3) R_tile+s_configured | tile head poses | s_B+Acheck x t_slam | perfect rotation (~ IMU) |
| (4) R_tile+s_oracle | tile head poses | s_oracle x t_slam | both; what is left is SLAM's translation |

Tool label = (cam_t->tool_t)^-1 [R | s t_slam] (cam_t+dt->tool_t+dt), using the ball poses and the
tool offset. It is compared with the tile label exactly as `slam.labels` does: the same label files
(`slam.labels.build_segment`), the same anchors and counted steps (`anchor_errors`), and the same
statistics (`step_stats`, `chunk_stats`). Only pairs with tile GT at both ends count.

Reported for each combination:
- tool position and rotation error vs dt (0.07 to 6.67 s);
- mean label error per chunk length H = 15 / 30 / 50 / 100;
- both of the above per head rotation speed bin (0-10 / 10-30 / 30+ deg/s). Speed is the tile head
  rotation over the 0.5 s after the anchor.

The step also records two things:
- a coupling table: the parts of the SLAM head-motion error at the tool from the rotation
  (dR b) and from the translation (dt), and the cosine between them;
- checks: combinations 1 and 2 against this run's labels files, and the decomposition against
  the label chunks.

**Why.** This supports the hardware decision on adding an IMU and/or stereo to the head camera.
Stereo would fix the metric scale, which is about combination (2). An IMU would fix the
rotation, which is about combination (3).

```
$V -m slam.run experiments/exp004_error_decomposition/config.yaml     # CPU only: producers are cache hits
```

**How to read it.**
- (1) vs (2) is what a perfect per-segment scale gains. Stereo also fixes the scale drift within a
  segment, which the per-segment oracle does not, so (2) understates a perfect stereo. Stereo
  depth noise is not modelled.
- (1) vs (3) is what perfect rotation gains *when SLAM's own translation is kept*. The tool
  rotation label depends only on the head rotation and the ball poses. In (3) and (4) it is
  therefore the tile label's own rotation, so their rotation error is about 0 by construction. The
  0.01-0.02 deg means come from interpolating between frames.
- In cam_t the tool after the head motion sits at R b + t. The SLAM label position error is
  therefore about |dR b + dt|, and (3) and (4) keep only dt. If SLAM's rotation and translation
  errors cancel at the tool's depth (cosine near -1), (3) is *worse* than (1).
- The rotation error of the tile GT itself (about 0.4 deg per tile set, `gt_noise.json`) is in the
  reference of every combination.

**Result (scratch run of this config, 2026-11-08; everything below the producers recomputed in 1 min).**
Combinations (1) and (2) reproduce exp003's `labels_E3@B+Acheck.json` and `labels_E3.json`
bit-identically: 989 anchors, every by-step and chunk number equal, max |difference| 0. The
decomposition with the SLAM rotation matches the label chunks to 4e-13 mm (48 735 pairs).

| E3, 989 anchors | (1) SLAM rot + B+Acheck | (2) SLAM rot + oracle s | (3) tile rot + B+Acheck | (4) tile rot + oracle s |
|---|---|---|---|---|
| position at 1 s, median / p90 [mm] | 5.7 / 18.4 | 4.3 / 14.6 | 8.8 / 30.5 | 7.7 / 25.4 |
| rotation at 1 s, median / p90 [deg] | 0.52 / 1.62 | 0.52 / 1.62 | 0.00 / 0.00 | 0.00 / 0.00 |
| position at 2 s, median / p90 [mm] | 7.6 / 27.9 | 5.5 / 14.7 | 12.0 / 37.0 | 9.8 / 30.7 |
| chunk mean position, H = 15 / 30 / 50 / 100 [mm] | 5.5 / 7.9 / 9.5 / 10.9 | 4.8 / 6.6 / 7.8 / 8.9 | 9.2 / 13.1 / 15.8 / 18.0 | 8.6 / 11.9 / 14.3 / 16.3 |
| chunk mean rotation, H = 15 / 100 [deg] | 0.56 / 1.03 | 0.56 / 1.03 | 0.02 / 0.01 | 0.02 / 0.01 |
| position at 1 s, head speed 0-10 deg/s (756 anchors) [mm] | 5.2 | 3.5 | 7.6 | 6.5 |
| position at 1 s, head speed 10-30 deg/s (155 anchors) [mm] | 17.8 | 11.6 | 25.7 | 17.7 |

- **Scale (stereo).** A perfect per-segment scale cuts the 1 s position error by a quarter:
  - 1 s median 5.7 -> 4.3 mm, p90 18.4 -> 14.6 mm;
  - chunk mean -12% / -16% / -18% / -18% at H = 15 / 30 / 50 / 100;
  - 2 s p90 27.9 -> 14.7 mm (the largest B errors dominate the tail: -36% / -29% / -22% / -19% on
    ep20 / ep29 / ep21 / ep12, `scale_E3.json`);
  - the gain is largest with fast head rotation (10-30 deg/s at 1 s: 17.8 -> 11.6 mm).
- **Rotation (IMU).** Perfect rotation with SLAM's translation kept removes the label rotation
  error (0.52 -> 0.00 deg at 1 s) but makes the position *worse* (5.7 -> 8.8 mm at 1 s, chunk
  H = 30: 7.9 -> 13.1 mm). The coupling table shows why:
  - at 1 s the tool displacement from DROID's rotation error is 4.6 mm (median) and from its
    translation error 7.7 mm (oracle scale);
  - the two point in nearly opposite directions (cosine median -0.92 at 1 s, -0.85 to -0.92
    over every dt), so together they leave 4.3 mm;
  - DROID's motion is image-consistent, so its rotation and translation errors compensate for
    points at the scene depth, which is where the tool is.

  An IMU that only replaces the rotation (loosely coupled) would trade about 0.5 deg of rotation
  error for about +3 mm of position error. It helps the position only when the translation is
  re-estimated with it (tightly coupled VIO). This experiment cannot measure that: it needs a
  VIO run, e.g. with a gyro simulated from the tile rotation plus noise.
- **What is left: (4).** 7.7 mm at 1 s and 9.8 mm at 2 s. This is SLAM's translation direction
  and its scale drift within a segment. It matches the head translation error of exp003's
  evaluation (E3, oracle scale: 8.2 mm at 1 s).
- **Head speed.** 756 anchors are at 0-10 deg/s and 155 at 10-30 deg/s. None are at 30+ deg/s.
  The tile GT has almost no such motion (2 of 1931 strict frame pairs at 0.5 s in the evaluation),
  so this session cannot show how the combinations behave under fast head rotation. 78 anchors have no speed because there is no tile pose
  within 0.12 s of the window's end: in 61 the window runs past the segment's last frame (the
  episode end), in 17 it ends in a tile gap. The 10-30 deg/s anchors all sit in the second
  half of their episodes (6-43 steps left), so that bin has no 4 s or 6.67 s steps, and its
  H = 100 chunk equals H = 50 (no anchor there has more than 43 steps left).
