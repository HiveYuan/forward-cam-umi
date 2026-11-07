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

# Sessions we run. Only single-take sessions for now; multi-take ones (glove5,
# glove6) need their episodes split by take before they can be added.
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


def session(name):
    if name not in SESSIONS:
        raise KeyError(f"unknown session {name!r}; known: {sorted(SESSIONS)}")
    return SESSIONS[name]


def gt_dir(name):
    return WORK / name / "gt"


def segments_dir(name):
    return WORK / name / "segments"
