#!/usr/bin/env python3
"""Hand-off manifest for recorded sessions: lists exactly which files to send,
their sizes, and prints an rsync line. Nothing is copied or compressed — 4K
MJPEG sessions are 7-14 GB each, so they travel by rsync (or a drive), not
as a tarball.

What a session needs on the receiving side (the builds run there):
  data/raw/<dataset>_{b0587,b0587b,fish}.mkv + _ts.json + _meta.json
  data/raw/<dataset>_glove_episodes.json           (episode boundaries)
  data/raw/<dataset>_glove_log.json                (width holds, if any)
  calib/<dataset>_*_detections.npz                 (optional; saves an hour)
and, once per unit / rig:
  calib/marker_map_glove_<unit>.json, tags36h11_<unit>.json
  calib/glove_<unit>_dodeca_bundle.json, glove_<unit>_gripper_bundle.json
  calib/<camera>_intrinsics.json for every camera (+ _charuco_views.npz)
  calib/cameras.json
  calib/workspace_tiles_*.json, calib/<stem>_cam_world.json

Usage: python scripts/pack_session.py <dataset> [<dataset> ...] --unit <unit> [--dest user@host:/path]
"""
import argparse
import glob
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()   # the tree the script was invoked from, not the symlink target

ap = argparse.ArgumentParser()
ap.add_argument("datasets", nargs="+")
ap.add_argument("--unit", required=True)
ap.add_argument("--dest", default="<user@host:/path/to/forward-cam-umi>",
                help="rsync destination (the receiving repo root)")
ap.add_argument("--out", default=None, help="write the manifest here (default data/raw/handoff_<unit>.txt)")
a = ap.parse_args()

files = []
for ds in a.datasets:
    files += sorted(glob.glob(str(ROOT / f"data/raw/{ds}_*")))
    files += sorted(glob.glob(str(ROOT / f"calib/{ds}_*_detections.*")))
    files += sorted(glob.glob(str(ROOT / f"calib/{ds}_*_cam_world.json")))
files += [str(ROOT / f) for f in (f"calib/marker_map_glove_{a.unit}.json", f"calib/tags36h11_{a.unit}.json",
                                  f"calib/glove_{a.unit}_dodeca_bundle.json", f"calib/glove_{a.unit}_gripper_bundle.json",
                                  "calib/cameras.json")]
files += sorted(glob.glob(str(ROOT / "calib/*_intrinsics.json"))) + sorted(glob.glob(str(ROOT / "calib/*_charuco_views.npz")))
files += sorted(glob.glob(str(ROOT / "calib/workspace_tiles_*.json")))
files = sorted(set(files))

total = 0
missing = []
lines = []
for f in files:
    rel = os.path.relpath(f, ROOT)
    if os.path.exists(f):
        s = os.path.getsize(f); total += s
        lines.append(f"{s / 1e9:8.2f} GB  {rel}")
    else:
        missing.append(rel)
print("\n".join(lines))
print(f"\n{len(lines)} files, {total / 1e9:.1f} GB")
if missing:
    print("MISSING (expected for a complete hand-off):\n  " + "\n  ".join(missing))

out = Path(a.out) if a.out else ROOT / f"data/raw/handoff_{a.unit}.txt"
out.write_text("\n".join(os.path.relpath(f, ROOT) for f in files if os.path.exists(f)) + "\n")
print(f"\nmanifest -> {out}")
print("send with (run from the repo root; keeps the data/raw and calib layout):")
print(f"  rsync -avP --files-from={os.path.relpath(out, ROOT)} . {a.dest}/")
