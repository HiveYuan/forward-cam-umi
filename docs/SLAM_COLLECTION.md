# Collecting glove sessions for the tile-free SLAM pipeline (macOS)

Recording runs on the Mac; everything after `field_qc` runs on the server.

**What is recorded and why**

| stream | role | used by the algorithm |
|---|---|---|
| head camera `b0587b` | policy observation, SLAM, metric depth, glove ball pose, jaw width (tails + back markers) | yes |
| wrist fisheye `fish` | jaw width from the fingertip tags, as an independent check of the head-camera width | **no**, cross-check only |
| workspace tiles (in the head view) | ground-truth head pose for evaluation | no (masked out of SLAM) |

Glove: unit **`yuan`** (the first glove, with Yuan since 10-01). Its marker sizes are
`calib/marker_map_glove_yuan.json` (Yosub's 09-28 calipers). Never record or label it
under a `yosub` name, and never use the 10-13 `marker_map_glove_yosub.local.json`
(see `calib/README.md`, "Glove units").

Dataset names used below:

| name | what | how often |
|---|---|---|
| `yuan_layout_NN` | tile layout, static camera | after every (re)taping of the tiles |
| `yuan_holds_NN` | caliper width holds | once per glove unit, again after any marker change |
| `yuan_cal_NN` | ball / back-marker geometry | only if the original yuan bundles are not found |
| `yuan_pilot_01` | 5–10 episodes, full pipeline test | once, before the data sessions |
| `yuan_slam_NN` | data sessions, ~15 episodes each | |

## 1. One-time setup

1. **Repository.** On the Mac, check out branch `collect` of the fork
   (`git fetch fork && git checkout collect`). Install as in `scripts/README.md`
   (§0 and "macOS adapter").
2. **Glove markers (look at the glove).** The fingertip tags that face the wrist camera
   must be AprilTag 16h5 ids 2 and 3 (`tips` in the yuan map). The tails' outside faces
   carry 4x4 ids 38/39. If the fingertips carry 4x4 38/39 instead (as noted on 10-13),
   the same ids sit on two parts of the glove: stop and resolve that first.
   The rehearsal's `field_qc` prints which ids the wrist camera actually sees.
3. **Cameras.** `python scripts/cameras_setup.py --require-head` (roles: `b0587b` head,
   `fish` wrist; skip the forward camera). Then `python scripts/focus_tune.py head` and
   `... wrist`. Lock the head focus and put a witness mark on the barrel.
4. **Intrinsics.** If the head camera's focus moved since its last calibration, or there
   is none, calibrate (caliper the ChArUco board first):
   ```
   python scripts/calibrate_uvc.py head  --name B0587b_yuan --square-mm <measured> --marker-mm <measured>
   python scripts/calibrate_uvc.py wrist --name fisheye_glove_yuan --model rational --square-mm <measured> --marker-mm <measured>
   ```
   Any later focus change needs a new head calibration.
5. **Light.** macOS has no exposure control (auto exposure). Use bright, steady light
   (no changing daylight); dim light means long exposures and motion blur on a
   rolling-shutter camera. Keep the light the same for all sessions.
6. **The Mac.** Plugged in, never asleep during a session (run `caffeinate -dimsu` in a
   second terminal), no other camera app open. Free disk: the recorder prints its own
   estimate at start; plan on ~8 GB per recorded minute (head + wrist, macOS re-encode)
   and twice the footage during the final remux (~130 GB free for a 15-episode session).
7. **Tiles.** Use the `yuan` print (`calib/tags36h11_yuan.json`: 36h11 ids 1–5, 60.16 mm;
   never id 0). Tape all four flat and firmly:
   - where your gaze lands while grasping, so that **at least two** are in view during
     every episode, with one right next to the bin;
   - spread over the whole workspace the task covers;
   - **no other tag or marker anywhere in the scene** (posters, spare tiles, robot markers).

   The tiles must not move for the rest of the collection. If one is bumped: note it
   (`session_meta.py --tiles-moved`) and record a new layout take.
8. **Layout take.** Take the head camera off, put it on a stand or the table so that all
   four tiles are in view, and record 20 s without touching it:
   ```
   python scripts/record_session.py --cameras_only --cameras b0587b --dataset yuan_layout_01 --duration 20 --num_episodes 1 --no_preview
   ```
9. **Width holds** (head camera worn, as in a session; ~10 min):
   ```
   POSE_PUB=0 python scripts/record_session.py --glove --width_holds --glove_unit yuan \
       --marker-map calib/marker_map_glove_yuan.json --cameras b0587b,fish --dataset yuan_holds_01 --num_episodes 1
   ```
   At the prompt type the spacer width (`m 0` closed, then about 20, 40, 60, 80 mm, each
   a caliper-measured rigid spacer) and ENTER; ENTER again ends the hold. During each
   15–20 s hold, at working distance, slowly rotate the glove so the head camera sees
   **both** jaws' tails and the back markers from several angles. Then one extra hold at
   a width not used above (for verification), and `q`.
10. **Glove geometry.** If the original (pre-10-13, solved at 15.18 mm) yuan ball and
    back-marker bundles are found on the Mac, send them; otherwise record a calibration
    take: one long episode, slowly turning the ball through every orientation at working
    distance with the back markers visible part of the time (`--dataset yuan_cal_01
    --num_episodes 1`, same command as a session).
11. **Send** layout, holds (and cal) as in §4 and wait for the server's OK: layout
    solved, head-camera width fitted with its hold-out error, bundles in place.

## 2. Pilot

Record `yuan_pilot_01` exactly as a data session (§3) with 5–10 episodes, run `field_qc`,
send it, and wait until the server has run it end to end before the data sessions.

## 3. A data session

```
caffeinate -dimsu &        # or in a second terminal
POSE_PUB=0 python scripts/record_session.py --glove --glove_unit yuan \
    --marker-map calib/marker_map_glove_yuan.json --cameras b0587b,fish \
    --dataset yuan_slam_01 --num_episodes 15 --task "<task>"
```

**Start of the session** (before the first ENTER): hold the glove in the head view, fully
**closed and empty** for 2 s, then fully **open** for 2 s.

**Every episode:**

1. *Before ENTER*: glove open at the start position, in view, ball towards your head.
   Keep your head **steady for at least 5 s** — slow, small movements are fine, no quick
   turns. SLAM starts 5 s before ENTER and a fast turn there can make it fail to
   initialise (glove5 take 1: 8 of 49 episodes turned faster than 120°/s in those 5 s,
   by the tiles).
2. *ENTER* is pressed by a helper or a clicker/foot pedal. If you press it yourself, keep
   the keyboard inside your view within reach and do not turn your head to it.
3. *The task* at a natural pace; let your head follow naturally, no whipping.
4. *ENTER* after the release, once the hand has withdrawn. A failed episode (dropped
   object, bumped bin): type `d` + ENTER at that prompt to discard it.

**End:** `q` + ENTER, then wait for "remux" to finish (never Ctrl-C during it).

**Right after the session, on the Mac:**

```
python scripts/session_meta.py yuan_slam_01 --from <previous session>   # first session: give all fields
python scripts/field_qc.py yuan_slam_01
```

`field_qc` lists each episode as OK / WARN / FAIL (preroll recorded and calm, ball seen
at the start and in ≥ 70 % of frames, ≥ 1 tile in ≥ 70 % of frames, tail + back marker
pair, wrist tips). Re-record the FAIL count **under a new name** (`yuan_slam_01b`); never
resume a dataset name. Anything noteworthy goes into the metadata:
`session_meta.py yuan_slam_01 --note "..." --episode-note 7="..." --exclude 3`.

## 4. Sending

```
python scripts/pack_session.py yuan_slam_01 --unit yuan --marker-map calib/marker_map_glove_yuan.json \
    --dest student@<server>:/home/student/yuanliu-hawaii/incoming/collect
```

It prints the file list and the `rsync` line (raw video, timestamps, episode marks, holds
log, `_session.json`, `_field_qc.json`, intrinsics, layouts). Delete a session from the Mac
only after the server confirms it arrived complete.

## 5. Never

- re-encode, trim, rotate or rename raw files;
- resume an existing dataset name (a second run renames the first take to `.take1`);
- record this glove under `yosub`, or with a marker map other than `marker_map_glove_yuan.json`;
- move the tiles between the layout take and the last session;
- let the Mac sleep or change its clock during a session (episode marks use the wall clock).
