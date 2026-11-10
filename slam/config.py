"""Paths and per-session settings for the SLAM pipeline.

Code lives in this checkout. The raw recordings and the marker-detection caches
are git-ignored, so they are read from the main head-cam-umi checkout
(HEADCAM_DATA_REPO). Everything the pipeline writes goes under SLAM_WORK:

  <SLAM_WORK>/<session>/gt/                 tile head poses, ball poses
  <SLAM_WORK>/<session>/segments/epNN/      per-episode SLAM inputs
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CALIB = REPO / "calib"                     # tracked calibration (intrinsics, bundles, layouts)
DATA_REPO = Path(os.environ.get("HEADCAM_DATA_REPO", "/home/student/yuanliu-hawaii/head-cam-umi"))
RAW = DATA_REPO / "data/raw"               # git-ignored: videos, *_ts.json, episode marks
DET_CACHE = DATA_REPO / "calib"            # git-ignored: <stem>_dodeca_detections.npz etc.
WORK = Path(os.environ.get("SLAM_WORK", "/home/student/yuanliu-hawaii/work"))

# Sessions we run. Multi-take sessions (glove5, glove6) run one take at a time as their own session
# (<session>_take1 = the .take1 files, _take2 = the plain files): their raw files are symlinked under
# derived names into <work>/takes/data/raw with a per-take episode file renumbered from 0
# (source_episode_index keeps the original), so run the CLI steps of these sessions with
# HEADCAM_DATA_REPO=<work>/takes (detection caches then go to <work>/takes/calib).
SESSIONS = {
    "yam_glove7": {
        "head_stem": "yam_glove7_b0587b",
        "intrinsics": "B0587b_f3_intrinsics.json",
        "glove": "yosub",
        "tile_layout": "workspace_tiles_pilot_v3.json",
        # SAM2 motion-mask prompts: object -> points in the glove's body frame
        # ("ball" = body origin, "flange" = virtual flange, or [x, y, z] in metres).
        # The hand point is the back of the hand (yosub glove), set from one frame.
        "sam2_prompts": {"glove": ["ball", "flange"], "hand": [[-0.141, -0.0026, 0.1014]]},
    },
}
for _s in ("yam_glove8", "yam_glove6_take1", "yam_glove6_take2", "yam_glove5_take1", "yam_glove5_take2"):
    # same collector, glove unit, head camera (f3 intrinsics, glove5 included) and tile layout as glove7
    SESSIONS[_s] = {**SESSIONS["yam_glove7"], "head_stem": f"{_s}_b0587b"}


def session(name):
    if name not in SESSIONS:
        raise KeyError(f"unknown session {name!r}; known: {sorted(SESSIONS)}")
    return SESSIONS[name]


def gt_dir(name):
    return WORK / name / "gt"


def segments_dir(name):
    return WORK / name / "segments"
