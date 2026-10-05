# Tracking software: calibrate, record, solve

The Python side of the forward-camera rig. Everything runs from the
**repository root** (`python scripts/...`) and reads/writes `calib/` and
`data/raw/` relative to it — keep that layout.

Status: the robot-side path (same code, robot-mounted markers) is validated
against robot forward kinematics — 7.7 mm / 1.7° median, see
[yam-umi/pos-tracking/dynamic-accuracy.md](https://github.com/YosubShin/yam-umi/blob/main/pos-tracking/dynamic-accuracy.md).
The glove-session path (steps 4–6) is implemented but has not yet been
exercised on a real glove session; expect to report rough edges.

## 0. Install

```
pip install -r scripts/requirements.txt      # opencv-contrib, numpy, scipy
sudo apt install ffmpeg v4l-utils            # ffmpeg/ffprobe + v4l2-ctl
```
Linux with the cameras on USB (UVC). Tested with Python 3.12.

## 1. Measurements — one caliper reading per printed group

Printers rescale by a few percent and the error does not announce itself:
a 3% size error is a 3% range error in every pose. **Caliper one black square
per group** and declare it in the config. Nominal is not enough.

| what | file | fields |
|---|---|---|
| glove markers (sheet `markers/glove_markers_v4.pdf`) | `calib/marker_map_glove_<unit>.json` | `tails`, `bases`, `tips` sizes in mm; `ball_edge_mm` |
| workspace tags (`markers/apriltag_36h11_60mm_marker_75mm_tile_final.pdf`) | `calib/tags36h11_<unit>.json` | `edge_mm`; **use tags 1–5 only** |
| ChArUco board (`markers/charuco_letter_8.5x11.pdf`) | flags to `calibrate_uvc.py` | `--square-mm`, `--marker-mm` |

Two built units are recorded, both from the same sheet and both complete:
`calib/marker_map_glove_{yuan,yosub}.json` with `calib/tags36h11_{yuan,yosub}.json`.
They differ by ~1% in every group — the normal print-to-print variance — which
is why a new unit always gets its **own** file and its own bundle solves
(step 6): copy one of them, replace every size with your calipers, rename.

Two ID traps, already handled if you follow the commands below:
`4x4-27` is a real ball face but aliases to AprilTag `16h5-1` (a robot tip
marker) — detect glove footage with `--keep-27`; workspace tag `36h11-0`
aliases to `4x4-37` (a glove tail) — never place tag 0.

## 2. Cameras: pin by USB port, then lock focus and exposure

Copy `calib/cameras.example.json` to `calib/cameras.json` and edit it for
your machine. Each entry is `[suffix, by_path, name_fragment_or_null,
"WxH", "fps"]`; find by-path links with `ls -l /dev/v4l/by-path/`. Suffixes
the pipeline understands: `b0587` (fixed forward 4K), `b0587b` (second
B0587 — fixed twin or head-worn), `fish` (wrist fisheye). The two B0587s
share a serial, so `b0587b` has no name fallback; if its port changes the
recorder resolves it as "the B0587 that is not the forward one".

Focus is mechanical on the B0587 and intrinsics are focus-dependent:
lock the barrel with the live sharpness meter, mark it, and only then
calibrate.
```
python scripts/focus_tune.py /dev/v4l/by-path/<forward>
```
The exposure/gain ritual (`scripts/uvc_ritual.py`) is applied automatically
by the recorder and the calibrator: manual exposure, `exposure_time_absolute=2`
(0.2 ms), gain 0. Verify behaviourally — a hand waved in front of the lens
must be frozen, not smeared; readback alone lies on these modules.

## 3. Intrinsics (once per camera, or after any barrel movement)

Wave the ChArUco board through the view — near/far, corners, tilted — until
it has collected enough frames; it calibrates, validates on a holdout and
writes `calib/<name>_intrinsics.json`, naming the camera from its device
name (B0587 → `B0587_intrinsics.json`; pass `--name B0587b` for the second
unit). Existing files are backed up, never overwritten.
```
python scripts/calibrate_uvc.py /dev/v4l/by-path/<forward> --square-mm 25.0 --marker-mm <caliper>
python scripts/calibrate_uvc.py /dev/v4l/by-path/<second>  --name B0587b --square-mm 25.0 --marker-mm <caliper>
python scripts/calibrate_uvc.py /dev/v4l/by-path/<fish>    --model rational --square-mm 25.0 --marker-mm <caliper>
```
Expect ~0.7 px RMS at 4K on the holdout; the 1080p fisheye lands near 2.7 px
with `--model rational` (required for it). **Calibrate the glove's wrist camera
under its own `--name`** (e.g. `--name fisheye_glove_<unit>`): the wrist-observation
arm reads gripper width from the 16h5 tip markers that camera sees, which is
metric PnP, and the auto-derived name `fisheye` would overwrite another unit's
file. Only a wrist stream used purely as observations can skip calibration.

## 4. Record a glove session

No robot, no host. Cameras roll continuously; you mark episode boundaries.
Hold the glove in the workspace when it starts — the pre-flight decodes a
live frame from every camera and aborts on zero markers (lens smudge,
exposure not latched, wrong device).
```
python scripts/record_session.py --glove --dataset glove_yuan_01 --num_episodes 30 --task "<task>"
```
At the first prompt do the **width holds**: type `m <gap_mm>` with the jaws
at a caliper-measured opening (closed, mid, open), keep them still and in
the forward camera's view until ENTER. Then `ENTER` starts an episode,
`ENTER` ends it, `d` discards the one you just did, `q` finishes. Outputs in
`data/raw/`: `<dataset>_<cam>.mkv` + `_ts.json` per camera,
`<dataset>_glove_episodes.json` (boundaries), `<dataset>_glove_log.json`
(width holds). Caliper values are logged as raw mm unless
`calib/gap_to_actuator.json` exists (that file comes from a robot bench
measurement and maps mm to the robot's gripper units — we supply it).

Also record one **calibration take** per unit (`--num_episodes 1`): a single
long episode slowly rotating the ball through every orientation at working
distance, with the gripper-back markers visible part of the time. Step 6
solves the ball's geometry from it.

## 5. Detection

```
python scripts/detect_parallel.py data/raw/<dataset>_b0587.mkv --keep-27     # and _b0587b, _fish
```
Writes `calib/<stem>_dodeca_detections.npz` (ArUco 4x4) and
`calib/<stem>_tips16h5_detections.npz`. Uses all cores; `--workers N` to
limit.

## 6. Solve the unit's geometry (once per physical glove)

Face-to-ID layout on the ball is not prescribed; it is recovered from the
calibration take. Three passes, outputs are specific to the physical unit:
```
python scripts/bundle_dodeca.py --npz=calib/glove_cal_b0587_dodeca_detections.npz \
    --intr=calib/B0587_intrinsics.json --marker-mm=<ball caliper> --ball-ids=25-35 --out=calib/tmp_bundle_<unit>.json
python scripts/bundle_dodeca_ideal.py --npz=calib/glove_cal_b0587_dodeca_detections.npz \
    --intr=calib/B0587_intrinsics.json --init=calib/tmp_bundle_<unit>.json --marker-mm=<ball caliper> \
    --out=calib/glove_<unit>_dodeca_bundle.json
python scripts/calibrate_gripper_bundle.py glove_cal_b0587 --bundle=calib/glove_<unit>_dodeca_bundle.json \
    --marker-map=calib/marker_map_glove_<unit>.json --out=calib/glove_<unit>_gripper_bundle.json
```
The robot's solves are included as format examples
(`calib/*_robot.example.json`, 0.71 px RMS on 465 frames).

## What to send back for dataset building

`data/raw/<dataset>_*` (all cameras, mkv + ts.json), the two
`_glove_*.json` sidecars, `calib/<name>_intrinsics.json` for each camera,
`calib/marker_map_glove_<unit>.json`, `calib/tags36h11_<unit>.json`, and the
calibration take. Dataset construction (labels → joint actions via IK) needs
the robot's hand-eye and kinematics, so it runs on the robot side.

## Command index

Every command prints its full documentation with `--help`. Run from the
repository root.

| command | does | step |
|---|---|---|
| `focus_tune.py <dev>` | live sharpness meter to lock a barrel-focused lens | 2 |
| `calibrate_uvc.py <dev> [--name] [--model rational] --square-mm --marker-mm` | live ChArUco intrinsics → `calib/<name>_intrinsics.json` | 3 |
| `record_session.py --glove --dataset D --num_episodes N` | multi-camera session: pre-flight, ritual, episode marks, width holds | 4 |
| `uvc_record.py <name> [dev] [WxH] [fps]` | one camera's raw MJPEG + wall clocks (launched by record_session) | 4 |
| `detect_parallel.py <video.mkv> [--keep-27] [--workers N]` | ArUco 4x4 + AprilTag 16h5 detection caches | 5 |
| `bundle_dodeca.py --npz= --intr= --marker-mm= --ball-ids=` | pass 2: free bundle of the ball's faces | 6 |
| `bundle_dodeca_ideal.py --npz= --init= --intr= --marker-mm= --out=` | pass 3: dodecahedron-prior refinement → the bundle the pipeline uses | 6 |
| `calibrate_gripper_bundle.py <stem> --bundle= --marker-map= --out=` | gripper-back markers in the ball's body frame | 6 |

Libraries (not commands): `labels_lib.py` — the label stack (fused ball
pose, body-frame aperture estimators); `uvc_ritual.py` — per-camera
exposure/gain/focus controls, selected by device name.

## Where to edit

This directory is the single source of truth for these scripts and for the
measured unit configs in `calib/`. The private experiment tree (`pilot`)
links to them with relative symlinks rather than keeping copies, so a change
committed here is immediately what the robot-side pipeline runs. Robot-only
tooling (hand-eye, gap bench, dataset construction, training) is not here.
