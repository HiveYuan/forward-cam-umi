# forward-cam-umi

Experimental add-ons to [YAM-UMI](https://github.com/YosubShin/yam-umi) that use
an external, forward-facing camera instead of the wrist fisheye for:

- **Position tracking.** The dodecahedral marker ball from YAM-UMI is watched by
  the external camera. This repository adds the parts that mount the same ball on
  the YAM robot arm, so tracking can be checked against ground truth from the
  robot's forward kinematics.
- **Gripper width tracking.** Aperture is read by the external camera from
  markers on printed tails behind the jaws, rather than from tip markers seen by
  the wrist fisheye.

This repository depends on YAM-UMI: the gripper, the dodecahedral ball, and its
stalk and arc mount all come from there. Build YAM-UMI first.

> **Status: experimental.** These parts are for trying things out and are not
> documented or characterised the way YAM-UMI is.

## Hardware

| Part | Files | Notes |
|---|---|---|
| `wrist_stalk_adapter_v3` | STEP, STL | Mounts the ball's stalk on the YAM robot arm |
| `retainer_radial_tab` | STEP, STL | Holds the ball on the robot-arm stalk |
| `gripper_back_marker_holder` | STEP; STL left and right | Holds markers on the back of the gripper |
| `aperture_tail` | STEP (right, v3); STL left and right | Printed tails that carry the aperture markers behind the jaws |

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
