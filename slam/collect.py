"""Server side of the glove collection (docs/SLAM_COLLECTION.md): from the sessions rsynced into
COLLECT_REPO (<repo>/data/raw, <repo>/calib) to the inputs of an experiment config.

  python -m slam.collect status
  python -m slam.collect check  <dataset>            arrival: files, transport, metadata, field QC
  python -m slam.collect import-calib <dataset>      the session's intrinsics -> calib/collected/ (never overwritten)
  python -m slam.collect layout <layout_dataset> --unit yuan --intr <file>
                                                     tile layout from the static take -> calib/workspace_tiles_<dataset>.json
  python -m slam.collect holds  <holds_dataset> --unit yuan --intr <file> [--verify-gap MM]
                                                     head-camera width fit -> calib/head_width_glove_<unit>.json
  python -m slam.collect prep   <dataset>            detection, tile GT, ball poses, head width, wrist cross-check
  python -m slam.collect config <dataset> --exp expNNN_name     experiment config with the current defaults
  python -m slam.collect handeye-provisional --unit yuan --from yosub     (opt-in stand-in until the unit is solved)

One-time order per glove unit and tile placement: import the unit's bundles (calib/glove_<unit>_{dodeca,gripper}
_bundle.json), `layout`, `holds`; then per session `check`, `prep`, `config`, `python -m slam.run <config>`.
The wrist camera never feeds the algorithm: `prep` only compares its width with the head camera's.
Interpreters: V (numpy/cv2) and S (slam.head_width: cv2 + pandas), as in slam/README.md. Logs: <work>/<dataset>/logs/.
"""
import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from slam import config as C

V = os.environ.get("V", "/home/student/yuanliu-hawaii/.venv-headcam/bin/python")
S = os.environ.get("S", "/home/student/miniconda3/envs/sam2/bin/python")
CAMS = ("b0587b", "fish")                    # head (algorithm), wrist (cross-check only)
TEMPLATE = C.REPO / "experiments/exp034_adaptive_glove8/config.yaml"   # the current defaults (experiments/README.md)
COLLECTED = C.CALIB / C.COLLECTED_CALIB


def raw_dir():
    return C.COLLECT_REPO / "data/raw"


def load(p):
    return json.load(open(p))


def session_meta(ds):
    p = raw_dir() / f"{ds}_session.json"
    if not p.exists():
        raise SystemExit(f"no {p}: the session was sent without its metadata (scripts/session_meta.py)")
    return load(p)


def scripts_import(name):
    sys.path.insert(0, str(C.REPO / "scripts"))
    return __import__(name)


def run(cmd, log, cwd=C.REPO):
    """Run a step with HEADCAM_DATA_REPO=COLLECT_REPO; output to `log`; stop on failure."""
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HEADCAM_DATA_REPO=str(C.COLLECT_REPO), COLLECT_REPO=str(C.COLLECT_REPO),
               PYTHONPATH=os.pathsep.join(filter(None, [str(C.REPO), os.environ.get("PYTHONPATH")])))
    cmd = [str(c) for c in cmd]
    t0 = time.time()
    print(f"+ {' '.join(cmd)}\n  (log {log})", flush=True)
    with open(log, "a") as f:
        f.write(f"\n# {time.strftime('%F %T')} {' '.join(cmd)}\n")
        f.flush()
        r = subprocess.run(cmd, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT)
    tail = open(log).read().splitlines()[-6:]
    print("  " + "\n  ".join(tail) + f"\n  [{time.time() - t0:.0f}s, rc {r.returncode}]", flush=True)
    if r.returncode:
        raise SystemExit(f"step failed: {cmd[1:3]} (see {log})")


def logs(ds):
    return C.WORK / ds / "logs"


# ---------------------------------------------------------------- calibration files

def import_file(name):
    """COLLECT_REPO/calib/<name> -> calib/collected/<name>; identical re-imports are fine, a different file
    under the same name is refused (a recalibration must get a new --name on the Mac)."""
    name = Path(name).name
    src, dst = C.COLLECT_REPO / "calib" / name, COLLECTED / name
    if dst.exists():
        if src.exists() and not filecmp.cmp(src, dst, shallow=False):
            raise SystemExit(f"calib/{C.COLLECTED_CALIB}/{name} exists with different content; a recalibrated "
                             f"camera needs a new --name in calibrate_uvc.py")
        return f"{C.COLLECTED_CALIB}/{name}"
    if not src.exists():
        raise SystemExit(f"missing {src} (pack_session.py ships calib/*_intrinsics.json)")
    COLLECTED.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    views = src.with_name(src.name.replace("_intrinsics.json", "_charuco_views.npz"))
    if views != src and views.exists() and not (COLLECTED / views.name).exists():
        shutil.copy2(views, COLLECTED / views.name)
    print(f"imported calib/{C.COLLECTED_CALIB}/{name}  (git add it: calibration is tracked)")
    return f"{C.COLLECTED_CALIB}/{name}"


def cmd_import_calib(a):
    meta = session_meta(a.dataset)
    for role in CAMS:
        p = ((meta.get("cameras") or {}).get(role) or {}).get("intrinsics")
        if p:
            import_file(p)
        elif role == "b0587b":
            raise SystemExit("session metadata names no head-camera intrinsics")


def unit_files(unit):
    return {"marker map": C.CALIB / f"marker_map_glove_{unit}.json", "tags": C.CALIB / f"tags36h11_{unit}.json",
            "ball bundle": C.CALIB / f"glove_{unit}_dodeca_bundle.json",
            "back-marker bundle": C.CALIB / f"glove_{unit}_gripper_bundle.json",
            "hand-eye (tool frame)": C.CALIB / f"handeye_glove_{unit}.json",
            "head-camera width": C.CALIB / f"head_width_glove_{unit}.json"}


def provisional(unit):
    p = C.CALIB / f"handeye_glove_{unit}.json"
    return p.exists() and bool(load(p).get("provisional"))


# ---------------------------------------------------------------- detection

def detect(stem, log, wrist=False, force=False):
    tag = "tips16h5" if wrist else "dodeca"
    cache = C.COLLECT_REPO / "calib" / f"{stem}_{tag}_detections.npz"
    mkv = raw_dir() / f"{stem}.mkv"
    if cache.exists() and cache.stat().st_mtime > mkv.stat().st_mtime and not force:
        print(f"= {cache.name} cached")
        return
    (C.COLLECT_REPO / "calib").mkdir(exist_ok=True)
    flags = ["--keep-27"] + ([] if wrist else ["--no-16h5"])
    run([V, C.REPO / "scripts/detect_parallel.py", f"data/raw/{stem}.mkv", *flags,
         "--workers", str(min(16, os.cpu_count() or 8))], log, cwd=C.COLLECT_REPO)


# ---------------------------------------------------------------- check / status

def cmd_check(a):
    ds, raw = a.dataset, raw_dir()
    problems, notes = [], []
    meta = load(raw / f"{ds}_session.json") if (raw / f"{ds}_session.json").exists() else None
    if meta is None:
        problems.append(f"no {ds}_session.json")
    for role in CAMS:
        for ext in (".mkv", "_ts.json", "_meta.json"):
            if not (raw / f"{ds}_{role}{ext}").exists():
                problems.append(f"missing {ds}_{role}{ext}")
    if not (raw / f"{ds}_glove_episodes.json").exists():
        problems.append(f"missing {ds}_glove_episodes.json")
    if list(raw.glob(f"{ds}_*.take1*")):
        problems.append("a .take1 exists: the dataset name was resumed (one take per dataset name)")
    try:
        check_stream = scripts_import("recording_check").check_stream
        for role in CAMS:
            if (raw / f"{ds}_{role}_ts.json").exists():
                r = check_stream(raw, f"{ds}_{role}")
                problems += [f"{ds}_{role}: {p}" for p in r["problems"]]
                notes.append(f"{role}: {r['timing']['frames']} frames, {r['timing']['measured_fps']:.2f} fps")
    except Exception as exc:
        problems.append(f"transport check failed: {type(exc).__name__}: {exc}")
    if meta is not None:
        problems += [f"metadata: {p}" for p in scripts_import("session_meta").problems(meta, raw)]
        if (meta.get("tiles") or {}).get("moved"):
            notes.append("tiles moved since the layout take: the layout must be re-solved")
    qc_p = raw / f"{ds}_field_qc.json"
    if qc_p.exists():
        qc = load(qc_p)
        v = [r["verdict"] for r in qc["episodes"]]
        notes.append(f"field QC: {v.count('OK')} OK, {v.count('WARN')} WARN, {v.count('FAIL')} FAIL "
                     f"{qc['fail_episodes'] or ''}")
    else:
        problems.append(f"no {ds}_field_qc.json (run scripts/field_qc.py on the Mac)")
    if meta is not None and meta.get("unit"):
        for what, p in unit_files(meta["unit"]).items():
            if not p.exists():
                notes.append(f"unit {meta['unit']}: no {what} ({p.name})")
        if provisional(meta["unit"]):
            notes.append(f"unit {meta['unit']}: hand-eye is PROVISIONAL (copied from another unit)")
    for n in notes:
        print(f"  {n}")
    for p in problems:
        print(f"PROBLEM: {p}")
    print("OK: arrived complete" if not problems else f"{len(problems)} problem(s)")
    return int(bool(problems))


def cmd_status(a):
    raw = raw_dir()
    if not raw.is_dir():
        print(f"{raw} does not exist yet")
        return 0
    dss = sorted({p.name[:-len("_b0587b_ts.json")] for p in raw.glob("*_b0587b_ts.json")})
    print(f"COLLECT_REPO {C.COLLECT_REPO}: {len(dss)} head streams")
    print(f"{'dataset':<24} {'meta':>4} {'qc(ok/w/f)':>11} {'det h/w':>7} {'gt':>3} {'ball':>4} {'w_head':>6} {'w_wrist':>7}")
    for ds in dss:
        gt = C.WORK / ds / "gt"
        qc_p = raw / f"{ds}_field_qc.json"
        qc = "-"
        if qc_p.exists():
            v = [r["verdict"] for r in load(qc_p)["episodes"]]
            qc = f"{v.count('OK')}/{v.count('WARN')}/{v.count('FAIL')}"
        yn = lambda p: "y" if p.exists() else "-"
        det = yn(C.COLLECT_REPO / f"calib/{ds}_b0587b_dodeca_detections.npz") + "/" + \
            yn(C.COLLECT_REPO / f"calib/{ds}_fish_tips16h5_detections.npz")
        print(f"{ds:<24} {yn(raw / f'{ds}_session.json'):>4} {qc:>11} {det:>7} "
              f"{yn(gt / f'{ds}_b0587b_cam_world.json'):>3} {yn(gt / 'ball_poses.npz'):>4} "
              f"{yn(gt / 'gripper_head.npz'):>6} {yn(gt / 'gripper_wrist.npz'):>7}")
    return 0


# ---------------------------------------------------------------- one-time: layout, holds

def cmd_layout(a):
    ds = a.dataset
    intr = import_file(a.intr)
    out = C.CALIB / f"workspace_tiles_{ds}.json"
    if out.exists() and not a.force:
        raise SystemExit(f"{out} exists (--force to re-solve; sessions recorded on it keep pointing at it)")
    run([V, C.REPO / "scripts/tiles_pose.py", "layout", f"{ds}_b0587b", "--intr", C.CALIB / intr,
         "--tags", C.CALIB / f"tags36h11_{a.unit}.json", "--name", ds, "--stride", str(a.stride),
         "--raw-dir", raw_dir()], logs(ds) / "layout.log")
    print(f"layout: {out}  (git add it; sessions find it through tiles.layout_take = {ds})")


def split_holds(events, verify_gap=None):
    """Width-hold events -> (training events, verification events). The verification hold is the one at
    `verify_gap` mm, default the last hold of the take (the runbook records it last, at a new width)."""
    group_holds = scripts_import("field_qc").group_holds
    holds = group_holds(events)
    if len(holds) < 3:
        raise SystemExit(f"only {len(holds)} holds; the fit needs several widths plus one to verify")
    vg = holds[-1]["gap_mm"] if verify_gap is None else verify_gap
    vh = [h for h in holds if abs(h["gap_mm"] - vg) < 1e-6]
    if not vh:
        raise SystemExit(f"no hold at {vg} mm; holds: {[h['gap_mm'] for h in holds]}")
    if verify_gap is None and len(vh) > 1:
        raise SystemExit(f"the last hold's width {vg} mm was also used for training; pass --verify-gap")
    in_v = lambda e: any(h["t0"] <= e["t_wall"] <= h["t1"] for h in vh)
    meas = [e for e in events if e.get("event") == "e8_meas"]
    return [e for e in meas if not in_v(e)], [e for e in meas if in_v(e)]


def cmd_holds(a):
    ds, unit = a.dataset, a.unit
    for what in ("marker map", "ball bundle", "back-marker bundle"):
        p = unit_files(unit)[what]
        if not p.exists():
            raise SystemExit(f"missing {p}: the {what} of unit {unit} comes first (original bundles, or "
                             f"README section 6 from a calibration take)")
    intr = import_file(a.intr)
    log = raw_dir() / f"{ds}_glove_log.json"
    j = load(log)
    train, verify = split_holds(j["events"], a.verify_gap)
    w = C.WORK / ds
    w.mkdir(parents=True, exist_ok=True)
    tl, vl = w / "holds_train_log.json", w / "holds_verify_log.json"
    for p, ev in ((tl, train), (vl, verify)):
        p.write_text(json.dumps({**{k: v for k, v in j.items() if k != "events"}, "events": ev,
                                 "split_from": str(log)}, indent=1))
    print(f"holds: {len(train)} training events, {len(verify)} verification events "
          f"({sorted({e['gap_mm'] for e in verify})} mm)")
    detect(f"{ds}_b0587b", logs(ds) / "detect_head.log")
    if (raw_dir() / f"{ds}_fish.mkv").exists():
        detect(f"{ds}_fish", logs(ds) / "detect_wrist.log", wrist=True)
    run([S, "-m", "slam.head_width", "fit", "--source", "holds", "--unit", unit, "--log", tl,
         "--stem", f"{ds}_b0587b", "--intrinsics", intr, "--data-repo", C.COLLECT_REPO,
         "--verify-log", vl, "--verify-stem", f"{ds}_b0587b"], logs(ds) / "holds_fit.log")
    print(f"head-camera width: {unit_files(unit)['head-camera width']}  (git add it)")


def cmd_handeye_provisional(a):
    dst, src = C.CALIB / f"handeye_glove_{a.unit}.json", C.CALIB / f"handeye_glove_{a.src}.json"
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    j = load(src)
    j.update(provisional=True, provisional_from=src.name,
             note=f"PROVISIONAL: a copy of {src.name} (unit {a.src}) so unit {a.unit} can run end to end before "
                  f"its own glove_tool_frame.py solve. Replace with the real solve; labels built with this carry "
                  f"the other unit's ball-to-tool offset. Original note: {j.get('note', '')}")
    dst.write_text(json.dumps(j, indent=1))
    print(f"wrote {dst} (PROVISIONAL; do not commit it as a calibration)")


# ---------------------------------------------------------------- per session

def width_crosscheck(ds):
    """Head-camera width (the label) vs wrist-camera width (cross-check only), per episode."""
    gt = C.gt_dir(ds)
    zh, zw = np.load(gt / "gripper_head.npz"), np.load(gt / "gripper_wrist.npz")
    eps = sorted(int(k[1:-2]) for k in zh.files if k.endswith("_t") and f"g{k[1:-2]}_t" in zw.files)
    rows, allh, allw = [], [], []
    for e in eps:
        th, vh, tw, vw = zh[f"g{e}_t"], zh[f"g{e}_v"], zw[f"g{e}_t"], zw[f"g{e}_v"]
        m = (th >= tw.min()) & (th <= tw.max())
        if m.sum() < 5:
            continue
        wi = np.interp(th[m], tw, vw)
        d = vh[m] - wi
        rows.append({"episode": e, "n": int(m.sum()), "median_abs": float(np.median(np.abs(d))),
                     "p90_abs": float(np.percentile(np.abs(d), 90)), "bias": float(np.median(d))})
        allh.append(vh[m])
        allw.append(wi)
    out = {"episodes": rows}
    if rows:
        h, w = np.concatenate(allh), np.concatenate(allw)
        d = np.abs(h - w)
        out.update(median_abs=float(np.median(d)), p90_abs=float(np.percentile(d, 90)),
                   corr=float(np.corrcoef(h, w)[0, 1]), units="gripper command")
        print(f"width head vs wrist: median |diff| {out['median_abs']:.3f}, p90 {out['p90_abs']:.3f}, "
              f"corr {out['corr']:.3f} over {len(rows)} episodes (command units)")
    (gt / "width_crosscheck.json").write_text(json.dumps(out, indent=1))
    return out


def cmd_prep(a):
    ds = a.dataset
    if ds not in C.SESSIONS:
        raise SystemExit(f"{ds} is not registered: no valid {ds}_session.json in {raw_dir()}")
    s, meta = C.session(ds), session_meta(ds)
    unit = s["glove"]
    cmd_import_calib(a)
    lay = C.CALIB / s["tile_layout"]
    need = [lay, unit_files(unit)["ball bundle"], unit_files(unit)["back-marker bundle"]]
    missing = [str(p) for p in need if not p.exists()]
    if missing:
        raise SystemExit("missing: " + ", ".join(missing) + " (layout: slam.collect layout; bundles: per unit)")
    if (meta.get("tiles") or {}).get("moved"):
        print("WARN: tiles moved since the layout take; the tile GT of this session is suspect")
    gt = C.gt_dir(ds)
    gt.mkdir(parents=True, exist_ok=True)
    stem, lg = s["head_stem"], logs(ds)
    detect(stem, lg / "detect_head.log", force=a.force)
    has_wrist = (raw_dir() / f"{ds}_fish.mkv").exists()
    if has_wrist:
        detect(f"{ds}_fish", lg / "detect_wrist.log", wrist=True, force=a.force)
    cw = gt / f"{stem}_cam_world.json"
    if not cw.exists() or a.force:
        run([V, C.REPO / "scripts/head_pose_fast.py", stem, "--stride", "1", "--layout", lay,
             "--intr", C.CALIB / s["intrinsics"], "--tags", C.CALIB / f"tags36h11_{unit}.json",
             "--raw-dir", raw_dir(), "--out", cw], lg / "head_pose.log")
    run([V, "-m", "slam.ball_poses", "--session", ds], lg / "ball_poses.log")
    hw = unit_files(unit)["head-camera width"]
    if hw.exists():
        run([S, "-m", "slam.head_width", "markers", "--session", ds, "--data-repo", C.COLLECT_REPO],
            lg / "head_width.log")
        run([S, "-m", "slam.head_width", "predict", "--session", ds], lg / "head_width.log")
    else:
        print(f"WARN: no {hw.name} yet (slam.collect holds): no head-camera width for {ds}")
    if has_wrist and s.get("wrist_intrinsics"):
        # d0 (closed, empty jaws) comes from the session's own start-of-session hold; --wrist-d0-mm when it is missing
        d0 = ["--d0-mm", str(a.wrist_d0_mm)] if a.wrist_d0_mm else []
        run([V, "-m", "slam.wrist_width", "--session", ds, *d0], lg / "wrist_width.log")
        if hw.exists():
            width_crosscheck(ds)
    elif has_wrist:
        print("WARN: no wrist intrinsics in the session metadata: wrist cross-check skipped")
    if provisional(unit):
        print(f"WARN: unit {unit}'s hand-eye is PROVISIONAL")
    print(f"prep done: {gt}")


def episodes_for(ds):
    eps = [e["episode_index"] for e in load(raw_dir() / f"{ds}_glove_episodes.json")["episodes"]]
    drop = set(C.session(ds).get("exclude_episodes", []))
    qc_p = raw_dir() / f"{ds}_field_qc.json"
    if qc_p.exists():
        drop |= set(load(qc_p)["fail_episodes"])
    keep = [e for e in eps if e not in drop]
    if not keep:
        raise SystemExit(f"{ds}: no episodes left after exclusions and field-QC FAILs")
    return keep, sorted(drop & set(eps))


def cmd_config(a):
    import yaml
    ds = a.dataset
    if ds not in C.SESSIONS:
        raise SystemExit(f"{ds} is not registered: no valid {ds}_session.json in {raw_dir()}")
    s = C.session(ds)
    out = C.REPO / "experiments" / a.exp / "config.yaml"
    if out.exists() and not a.force:
        raise SystemExit(f"{out} exists")
    cfg = yaml.safe_load(open(TEMPLATE))
    keep, dropped = episodes_for(ds)
    cfg["experiment"] = a.exp
    cfg["data"] = {"session": ds, "episodes": keep, "head_stem": s["head_stem"], "intrinsics": s["intrinsics"],
                   "glove": s["glove"], "tile_layout": s["tile_layout"], "raw_dir": str(raw_dir()),
                   "det_cache_dir": str(C.COLLECT_REPO / "calib"), "gt_dir": str(C.gt_dir(ds))}
    cfg["masks"]["motion"]["impl"] = a.masks
    cfg["labels"]["params"]["gripper"] = a.gripper
    from slam.pipeline import registry as R
    warn = []
    if ("masks", a.masks) not in R.IMPLS:
        warn.append(f"masks impl {a.masks} is not registered in this checkout yet")
    import inspect
    from slam import labels as Lb
    if f'"{a.gripper}"' not in inspect.getsource(Lb.load_gripper) and a.gripper != "wrist":
        warn.append(f"slam.labels.load_gripper has no source '{a.gripper}' in this checkout yet")
    out.parent.mkdir(parents=True, exist_ok=True)
    head = (f"# {a.exp}: collected session {ds} (unit {s['glove']}), current defaults from {TEMPLATE.relative_to(C.REPO)}"
            f"\n# with motion masks {a.masks} and the head-camera gripper width. Episodes: {len(keep)} kept, "
            f"excluded {dropped} (session exclusions + field-QC FAILs).\n# Written by python -m slam.collect config; "
            f"run with HEADCAM_DATA_REPO={C.COLLECT_REPO}:\n#   python -m slam.run experiments/{a.exp}/config.yaml\n")
    out.write_text(head + yaml.safe_dump(cfg, sort_keys=False, width=120))
    print(f"wrote {out}")
    for w in warn:
        print(f"WARN: {w}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    for name in ("check", "import-calib"):
        sub.add_parser(name).add_argument("dataset")
    p = sub.add_parser("layout")
    p.add_argument("dataset"); p.add_argument("--unit", required=True); p.add_argument("--intr", required=True)
    p.add_argument("--stride", type=int, default=10); p.add_argument("--force", action="store_true")
    p = sub.add_parser("holds")
    p.add_argument("dataset"); p.add_argument("--unit", required=True); p.add_argument("--intr", required=True)
    p.add_argument("--verify-gap", type=float, help="the verification hold's width in mm (default: the last hold)")
    p = sub.add_parser("prep")
    p.add_argument("dataset"); p.add_argument("--force", action="store_true", help="redo detection and tile GT")
    p.add_argument("--wrist-d0-mm", type=float, help="wrist cross-check: closed-jaw tip separation when the session "
                                                      "lacks the closed hold")
    p = sub.add_parser("config")
    p.add_argument("dataset"); p.add_argument("--exp", required=True)
    p.add_argument("--masks", default="sam3_v2_head", help="motion-mask impl (sam3_v2_head: held gate from the head width)")
    p.add_argument("--gripper", default="head", help="labels' gripper source")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("handeye-provisional")
    p.add_argument("--unit", required=True); p.add_argument("--from", dest="src", required=True)
    a = ap.parse_args()
    fn = {"status": cmd_status, "check": cmd_check, "import-calib": cmd_import_calib, "layout": cmd_layout,
          "holds": cmd_holds, "prep": cmd_prep, "config": cmd_config,
          "handeye-provisional": cmd_handeye_provisional}[a.cmd]
    return fn(a) or 0


if __name__ == "__main__":
    raise SystemExit(main())
