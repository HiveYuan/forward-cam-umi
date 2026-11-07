#!/usr/bin/env python3
"""Run one SLAM configuration over all segments of a session, one subprocess per
segment (clean GPU state each time). Skips segments whose output exists.

  conda run -n droid python -m slam.run_batch --session yam_glove7 --run E2 --masks motion
"""
import argparse
import subprocess
import sys
import time

from slam import config as C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--masks", default="")
    ap.add_argument("--episodes", default="all")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("extra", nargs=argparse.REMAINDER, help="passed to run_droid after --")
    a = ap.parse_args()

    segs = sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]"))
    if a.episodes != "all":
        want = {f"ep{int(x):02d}" for x in a.episodes.split(",")}
        segs = [s for s in segs if s.name in want]
    failed = []
    t0 = time.time()
    for seg in segs:
        out = seg / "slam" / f"{a.run}.npz"
        if out.exists() and not a.overwrite:
            continue
        cmd = [sys.executable, "-m", "slam.run_droid", "--segment", str(seg), "--run", a.run,
               "--masks", a.masks] + [x for x in a.extra if x != "--"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        if r.returncode != 0:
            failed.append(seg.name)
            last = "FAILED: " + (r.stderr.strip().splitlines() or ["?"])[-1]
        print(f"[{time.time() - t0:6.0f}s] {seg.name} {a.run}: {last}", flush=True)
    if failed:
        raise SystemExit(f"failed: {failed}")


if __name__ == "__main__":
    main()
