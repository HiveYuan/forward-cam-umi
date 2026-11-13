#!/usr/bin/env python3
"""Session metadata for a glove session: data/raw/<dataset>_session.json.

Written once per session, right after recording, so the server never has to
guess which glove, intrinsics, tile print or layout a session used (the
HHs3 source CSV had to be reverse-engineered for exactly that reason).

  python scripts/session_meta.py <dataset> --from <previous dataset>      # copy, then ask what is missing
  python scripts/session_meta.py <dataset> --unit yuan --task "pick red block into bin" \
      --location "Yuan desk, Holmes 3xx" --collector yuan --head-intr calib/<head>.json \
      --wrist-intr calib/<wrist>.json --layout-take yuan_layout_01 --holds yuan_holds_01 \
      --enter-method helper
  python scripts/session_meta.py <dataset> --note "lights dimmed at ep 12" --episode-note 7="block slipped, kept"
  python scripts/session_meta.py <dataset> --exclude 3,9        # episodes to leave out (besides field_qc FAILs)
  python scripts/session_meta.py <dataset> --check              # exit 1 if a required field is missing

Fields (schema slam_session/1): unit, collector, location, task, objects, lighting,
enter_method (helper | clicker | keyboard-in-view | self), session_start_hold (closed +
open glove shown at the start), cameras.<role>.intrinsics (b0587b = head; fish = wrist,
cross-check only), tiles.{tags, layout_take, layout, moved}, width_calibration.holds_dataset,
exclude_episodes, episode_notes, notes; plus created / platform / git commit.
"""
import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
SCHEMA = "slam_session/1"
ENTER = ("helper", "clicker", "keyboard-in-view", "self")
REQUIRED = ("unit", "collector", "location", "task", "enter_method", "session_start_hold",
            "cameras.b0587b.intrinsics", "tiles.tags", "tiles.layout_take", "width_calibration.holds_dataset")
PER_SESSION = ("dataset", "created", "platform", "git", "notes", "episode_notes", "exclude_episodes")


def get(d, dotted):
    for k in dotted.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def put(d, dotted, v):
    ks = dotted.split(".")
    for k in ks[:-1]:
        d = d.setdefault(k, {})
    d[ks[-1]] = v


def problems(meta, raw):
    out = [f"missing {f}" for f in REQUIRED if get(meta, f) in (None, "")]
    if meta.get("enter_method") not in (None, "") and meta["enter_method"] not in ENTER:
        out.append(f"enter_method must be one of {ENTER}")
    for f in ("cameras.b0587b.intrinsics", "cameras.fish.intrinsics", "tiles.tags", "tiles.layout"):
        p = get(meta, f)
        if p and not (ROOT / p).exists() and not Path(p).exists():
            out.append(f"{f}: {p} not found")
    if unit := meta.get("unit"):
        if not (ROOT / f"calib/marker_map_glove_{unit}.json").exists():
            out.append(f"unit {unit}: calib/marker_map_glove_{unit}.json not found")
    if not (raw / f"{meta['dataset']}_glove_episodes.json").exists() and \
            meta.get("dataset") != get(meta, "width_calibration.holds_dataset") and \
            meta.get("dataset") != get(meta, "tiles.layout_take"):
        out.append(f"no {meta['dataset']}_glove_episodes.json in {raw}")
    return out


def git_commit():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--raw-dir", default=str(ROOT / "data/raw"))
    ap.add_argument("--from", dest="src", help="copy the fields of an earlier session (not its notes/exclusions)")
    for f, h in (("unit", "glove unit"), ("collector", None), ("location", "where (scene)"), ("task", None),
                 ("objects", None), ("lighting", None)):
        ap.add_argument(f"--{f}", help=h)
    ap.add_argument("--enter-method", choices=ENTER)
    ap.add_argument("--no-start-hold", action="store_true", help="the closed/open glove hold was NOT done")
    ap.add_argument("--head-intr")
    ap.add_argument("--wrist-intr")
    ap.add_argument("--tags", help="workspace tags json (default calib/tags36h11_<unit>.json)")
    ap.add_argument("--layout-take", help="dataset name of the static tile-layout take")
    ap.add_argument("--layout", help="calib/workspace_tiles_<name>.json once solved")
    ap.add_argument("--tiles-moved", action="store_true", help="a tile was moved/bumped since the layout take")
    ap.add_argument("--holds", help="dataset name of the width-holds session for this unit")
    ap.add_argument("--note", action="append", default=[])
    ap.add_argument("--episode-note", action="append", default=[], metavar="IDX=TEXT")
    ap.add_argument("--exclude", help="comma list of episode indices to leave out")
    ap.add_argument("--check", action="store_true", help="only validate")
    ap.add_argument("--no-input", action="store_true", help="never prompt")
    a = ap.parse_args()

    raw = Path(a.raw_dir)
    path = raw / f"{a.dataset}_session.json"
    meta = json.load(open(path)) if path.exists() else {"schema": SCHEMA, "dataset": a.dataset}
    if a.check:
        bad = problems(meta, raw) if path.exists() else [f"{path} does not exist"]
        print("\n".join(bad) if bad else f"OK: {path}")
        return int(bool(bad))
    if a.src:
        src = json.load(open(raw / f"{a.src}_session.json"))
        for k, v in src.items():
            if k not in PER_SESSION and k not in meta:
                meta[k] = v
        meta.setdefault("tiles", {}).pop("moved", None)
    sets = {"unit": a.unit, "collector": a.collector, "location": a.location, "task": a.task, "objects": a.objects,
            "lighting": a.lighting, "enter_method": a.enter_method, "cameras.b0587b.intrinsics": a.head_intr,
            "cameras.fish.intrinsics": a.wrist_intr, "tiles.tags": a.tags, "tiles.layout_take": a.layout_take,
            "tiles.layout": a.layout, "width_calibration.holds_dataset": a.holds}
    for k, v in sets.items():
        if v is not None:
            put(meta, k, v)
    if a.no_start_hold:
        meta["session_start_hold"] = False
    meta.setdefault("session_start_hold", True)
    if a.tiles_moved:
        put(meta, "tiles.moved", True)
    if meta.get("unit") and not get(meta, "tiles.tags"):
        put(meta, "tiles.tags", f"calib/tags36h11_{meta['unit']}.json")
    put(meta, "cameras.fish.role", "wrist: cross-check only, never an algorithm input")
    meta["notes"] = meta.get("notes", []) + a.note
    for en in a.episode_note:
        i, _, txt = en.partition("=")
        meta.setdefault("episode_notes", {})[str(int(i))] = txt
    if a.exclude:
        meta["exclude_episodes"] = sorted(set(meta.get("exclude_episodes", [])) |
                                          {int(x) for x in a.exclude.split(",") if x.strip()})
    if sys.stdin.isatty() and not a.no_input:
        for f in REQUIRED:
            if get(meta, f) in (None, ""):
                hint = f" {ENTER}" if f == "enter_method" else ""
                v = input(f"{f}{hint}: ").strip()
                if v:
                    put(meta, f, v)
    meta.update(schema=SCHEMA, dataset=a.dataset, platform=platform.platform(), git=git_commit(),
                created=meta.get("created") or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                updated=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    path.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    bad = problems(meta, raw)
    print(f"wrote {path}")
    for b in bad:
        print(f"  MISSING/INVALID: {b}")
    return int(bool(bad))


if __name__ == "__main__":
    raise SystemExit(main())
