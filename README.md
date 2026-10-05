# forward-cam-umi

An attempt to remove the wrist camera from
[YAM-UMI](https://github.com/YosubShin/yam-umi) and make the glove entirely
electronics-free.

YAM-UMI reads gripper width from AprilTags on the gripper tips, seen by the wrist
camera, and can optionally track wrist pose with a dodecahedral marker ball seen
by an external forward-facing camera. This project drops the wrist camera, so the
forward camera has to recover **both** wrist pose and gripper width by itself.
That takes extra markers and printed parts, which live here.

This repository depends on YAM-UMI: the gripper, the dodecahedral ball, and its
stalk and arc mount all come from there. Build YAM-UMI first.

> **Status: experimental.** These parts are for trying things out and are not
> documented or characterised the way YAM-UMI is.

## Design updates

### 2026-09-28 — Aperture tail clearance

- Raised the link extending from the gripper side as high as possible to
  minimize collisions with objects.
- Lengthened that link by a few millimeters to address slight interference with
  the gripper plate when the gripper is fully closed.
- Updated the [STEP model](STEP/aperture_tails.step) and both
  [left](STL/aperture_tail_left.stl) and [right](STL/aperture_tail_right.stl) STLs.

## Hardware

### Gripper width from the forward camera

The gripper tips are often occluded from the forward camera's vantage point, so
their markers can't be relied on.

- **`aperture_tail`** attaches to a gripper tip and moves with it as the gripper
  opens and closes, carrying markers where the forward camera can see them. The
  left and right tails are both derived from `STEP/aperture_tails.step`; print
  `STL/aperture_tail_left.stl` and `STL/aperture_tail_right.stl`.
- **`gripper_back_marker_holder`** is the fixed reference the tails are measured
  against. It is mounted on the back of the gripper, and each tail sits right
  beside its holder when the gripper is fully closed and is farthest from it when
  the gripper is fully open. You need two. The `_left` and `_right` STLs are the
  same file, duplicated so a full set prints without renaming anything.

### Ground truth on the robot

To validate position tracking, the same dodecahedral ball is mounted on the YAM
robot arm, so the tracked pose can be compared against the robot's forward
kinematics.

- **`wrist_stalk_adapter_v3`** mounts the ball's stalk on the robot arm.
- **`retainer_radial_tab`** holds the ball on the robot-arm stalk.

## Markers

Print every sheet at **100% / actual size** and check the 100 mm bar with
calipers before cutting anything.

| Sheet | Contents |
|---|---|
| `markers/robot_markers_v4.pdf` | Robot rig. `DICT_4X4_100` IDs 0–24 (ball, tails, base) and AprilTag 16h5 tip IDs 0 and 1 |
| `markers/glove_markers_v4.pdf` | Glove rig. `DICT_4X4_100` IDs 25–49 and AprilTag 16h5 tip IDs 2 and 3. Same file as in YAM-UMI's `pos-tracking/` |
| `markers/apriltag_36h11_60mm_marker_75mm_tile_final.pdf` | AprilTag 36h11 IDs 0–5, 60 mm markers on 75 mm tiles |
| `markers/charuco_letter_8.5x11.pdf` | ChArUco board, US Letter |

The robot and glove sheets share one layout, and the glove IDs are the robot IDs
plus 25. IDs 0–24 always mean the robot and 25–49 always mean the glove, so both
rigs can be in view at the same time.

## License

MIT. See [LICENSE](LICENSE).

## Software

The calibration, recording and tracking code lives in [`scripts/`](scripts/)
with its own [README](scripts/README.md): camera intrinsics (live ChArUco),
glove-session recording with episode marks and caliper width holds, marker
detection, and the solvers that recover a ball's face layout and the
gripper-back marker geometry. Measured marker configs for built units are in
[`calib/`](calib/); every printed group must be caliper-measured and declared
there — see the README's measurement table.
