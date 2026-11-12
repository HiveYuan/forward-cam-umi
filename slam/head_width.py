#!/usr/bin/env python3
"""Gripper width from the head camera alone: the paper's tail estimators, one calibration per glove unit.

The paper reads the jaw width in the head camera. Each jaw carries a wedge (the tail) with tags; their distance
to the fixed gripper-back tags, along the jaw axis, gives the width through a per-unit linear map. No
wrist-camera data enters the width (decision 2026-11-12: the wrist camera is a cross-check only; the hhs3 fit
reports the wrist width's error on the same frames, labelled as such).

Method = scripts/build_dataset.py pipeline B:
  * labels_lib.body_frames on a camera's 4x4 detections, with the unit's tails + bases. Marker sizes come from
    calib/marker_map_glove_<unit>.json; the ball and back-marker bundles are calib/glove_<unit>_dodeca_bundle.json
    and calib/glove_<unit>_gripper_bundle.json.
  * then labels_lib.fit_estimators / predict_aperture (median over the visible tail-base pairs and single tails),
    in width units (actuator units of the robot gripper);
  * the prediction maps to the gripper command by the calibration's grip map (default
    calib/width_to_cmd_glove_v2.json, the paper's).
The glove unit always comes from the session's `glove` field in slam.config; nothing here is tied to one unit.

Calibration sources (`fit --source`), both writing calib/head_width_glove_<unit>.json in one format:
  holds  the paper's recipe: the unit's caliper width holds. The log is <dataset>_glove_log.json (record_session
         --width_holds, e8_meas events; raw mm are converted by calib/gap_to_actuator.json as build_dataset does).
         Its frames come from that recording's camera stem; tail/base geometry is in the body frame, so any camera
         that saw the holds works. Only frames within 0.3 s of a hold enter the fit (build_dataset's meas_tol).
         With --verify-log / --verify-stem, a second hold recording is scored (mm).
  hhs3   for unit yosub, whose holds log is not archived. pilot_glove_HHs3's gripper channel is the head-camera
         width: its interpolation kinks sit at the head camera's frame times, not the wrist camera's (checked
         2026-11-12 on 179 episodes). So it stands in as the target: the pose-verified HHs3 episodes (manifest
         method verified / remapped) of the HHs3 sessions. HHs3 command -> width by inverting the grip map;
         samples on its flat ends (closed floor 0.20, open ceiling 0.998) are censored, since they have no unique
         width. --holdout fits on even HHs3 episodes and scores the odd ones.

  S=/home/student/miniconda3/envs/sam2/bin/python
  $S -m slam.head_width markers --session S                    # gt/head_markers.npz (per session, CPU, seconds)
  $S -m slam.head_width fit --source hhs3 [--holdout]          # unit yosub
  $S -m slam.head_width fit --source holds --unit U --log <dataset>_glove_log.json --stem <dataset>_<cam>
        --intrinsics <calib file> [--data-repo DIR] [--verify-log L --verify-stem S]
  $S -m slam.head_width predict --session S                    # gt/gripper_head.npz (gt/gripper_wrist.npz's layout)

Python API: marker_rows(), fit_hhs3(), fit_holds(), write_calib(), predict_session(), load_gripper_head().
Consumers read the width through gt/gripper_head.npz: {g<e>_t wall clock, g<e>_v command} for each marked
episode +- 0.5 s, plus meta.

Detection caches and raw timestamps are read from <data repo>/calib and <data repo>/data/raw. The data repo is
the main checkout's, or <work>/takes for the per-take sessions (glove5 / glove6 takes, glove8): whichever holds
the stem, unless --data-repo is given.
"""
import argparse
import datetime
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from slam import config as C

sys.path.insert(0, str(C.REPO / "scripts"))
import labels_lib as L  # noqa: E402

HHS3_ROOT = Path.home() / ".cache/huggingface/lerobot/pilot_glove_HHs3"
MANIFEST = C.CALIB / "hhs3_manifest.json"
GRIP_MAP = C.CALIB / "width_to_cmd_glove_v2.json"
GAP_TO_ACT = C.CALIB / "gap_to_actuator.json"
SLOW_DT = 1.0 / 37.5                    # HHs3 step: 15 fps declared, --slow 2.5 (as slam.hhs3_manifest)
HHS3_METHODS = ("verified", "remapped")
HOLD_TOL_S = 0.3                        # build_dataset's meas_tol for sparse caliper holds
GATE = 0.45                             # the masks' held_width_max: report how often the gate agrees
EPISODE_PAD_S = 0.5                     # predict: each marked episode +- this (gt/gripper_wrist.npz's window)


# ------------------------------------------------------------------------------------------------ helpers
def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    p = Path(path).resolve()
    return str(p.relative_to(C.REPO)) if p.is_relative_to(C.REPO) else str(p)


def calib_path(unit):
    return C.CALIB / f"head_width_glove_{unit}.json"


def data_repo_for(stem, data_repo=None):
    """The data repo holding <stem>'s 4x4 detections and timestamps (given, main checkout, or <work>/takes)."""
    cands = [Path(data_repo)] if data_repo else [C.DATA_REPO, C.WORK / "takes"]
    for repo in cands:
        if (repo / "calib" / f"{stem}_dodeca_detections.npz").exists() and (repo / "data/raw" / f"{stem}_ts.json").exists():
            return repo
    raise FileNotFoundError(f"no detections / timestamps for {stem} in {[str(c) for c in cands]}")


def unit_markers(unit):
    mm = json.load(open(C.CALIB / f"marker_map_glove_{unit}.json"))
    return ({int(k): float(v) for k, v in mm["tails"].items()},
            {int(k): float(v) for k, v in mm["bases"].items()})


class WidthMap:
    """Grip map (default calib/width_to_cmd_glove_v2.json): glove width (actuator units) -> gripper command, and its
    inverse on the strictly increasing part (commands on the flat ends are censored: no unique width)."""

    def __init__(self, path=GRIP_MAP):
        self.path = Path(path)
        m = json.load(open(path))
        self.x, self.y = np.asarray(m["x_width"], float), np.asarray(m["y_cmd"], float)
        top = int(np.argmax(self.y))                        # first point of the open ceiling
        self.y_lo, self.y_hi = float(self.y[0]), float(self.y[top])
        self.xi, self.yi = self.x[:top + 1], self.y[:top + 1]
        if not np.all(np.diff(self.yi) > 0):
            raise ValueError(f"{path}: command not strictly increasing below its ceiling")

    def to_cmd(self, w):
        return np.interp(w, self.x, self.y)

    def censored(self, cmd, eps=1e-3):
        cmd = np.asarray(cmd, float)
        return (cmd <= self.y_lo + eps) | (cmd >= self.y_hi - eps)

    def to_width(self, cmd):
        """Width for commands inside the invertible range; NaN on the censored ends."""
        cmd = np.asarray(cmd, float)
        w = np.interp(cmd, self.yi, self.xi)
        return np.where(self.censored(cmd), np.nan, w)


def marker_rows(stem, intrinsics, unit, data_repo=None):
    """labels_lib rows ({k, t_wall, pb: {marker id: body-frame position mm}}) for every frame of <stem> with a ball
    pose, and (number of frames, data repo used)."""
    repo = data_repo_for(stem, data_repo)
    K, dist = L.load_intrinsics(C.CALIB / intrinsics)
    T_body, dobj = L.load_bundle(C.CALIB / f"glove_{unit}_dodeca_bundle.json")
    extra = L.load_gripper_bundle(str(C.CALIB / f"glove_{unit}_gripper_bundle.json"))
    tails, bases = unit_markers(unit)
    ts = json.load(open(repo / "data/raw" / f"{stem}_ts.json"))
    det = np.load(repo / "calib" / f"{stem}_dodeca_detections.npz")
    return L.body_frames(det, ts, K, dist, T_body, dobj, {**tails, **bases}, extra=extra), len(ts), repo


def rows_to_arrays(rows, ids):
    pos = np.full((len(rows), len(ids), 3), np.nan)
    for n, r in enumerate(rows):
        for j, i in enumerate(ids):
            if int(i) in r["pb"]:
                pos[n, j] = r["pb"][int(i)]
    return np.array([r["t_wall"] for r in rows], float), pos


def rows_from(t, ids, pos):
    """labels_lib rows ({t_wall, pb}) from stored marker positions (NaN = not localised in that frame)."""
    ok = np.isfinite(pos[..., 0])
    return [{"t_wall": float(t[n]), "pb": {int(ids[j]): pos[n, j] for j in np.where(ok[n])[0]}} for n in range(len(t))]


def load_markers(session):
    z = np.load(C.gt_dir(session) / "head_markers.npz")
    return z["t"], z["ids"], z["pos"], json.loads(str(z["meta"]))


def estimators_from_json(d):
    return {k: {**e, "ctr": np.asarray(e["ctr"], float), "axis": np.asarray(e["axis"], float)} for k, e in d.items()}


def estimators_to_json(ests):
    return {k: {kk: (vv.tolist() if isinstance(vv, np.ndarray) else vv) for kk, vv in e.items()} for k, e in ests.items()}


def predict_widths(rows, ests):
    """(width in actuator units or NaN, number of estimators used) per row."""
    w, n = np.full(len(rows), np.nan), np.zeros(len(rows), int)
    for i, r in enumerate(rows):
        g, k = L.predict_aperture(r["pb"], ests)
        if g is not None:
            w[i], n[i] = g, k
    return w, n


def score(pred, ref, ok=None, gate=GATE):
    """|pred - ref| stats over finite predictions within ok (coverage = finite share of ok)."""
    pred, ref = np.asarray(pred, float), np.asarray(ref, float)
    ok = np.ones(len(pred), bool) if ok is None else np.asarray(ok, bool)
    m = np.isfinite(pred) & ok
    if not m.any():
        return {"frames": 0, "coverage": 0.0}
    e = np.abs(pred[m] - ref[m])
    out = {"frames": int(m.sum()), "coverage": float(m.sum() / ok.sum()), "median": float(np.median(e)),
           "p90": float(np.percentile(e, 90)), "p95": float(np.percentile(e, 95)), "mean": float(e.mean())}
    if gate is not None:
        out["gate_agreement"] = float(np.mean((pred[m] <= gate) == (ref[m] <= gate)))
    return out


# ------------------------------------------------------------------------------------------------ markers
def cmd_markers(a):
    s = C.session(a.session)
    tails, bases = unit_markers(s["glove"])
    rows, n_frames, repo = marker_rows(s["head_stem"], s["intrinsics"], s["glove"], a.data_repo)
    ids = np.array(sorted({**tails, **bases}))
    t, pos = rows_to_arrays(rows, ids)
    seen = np.isfinite(pos[..., 0])
    is_tail = np.isin(ids, list(tails))
    pair = seen[:, is_tail].any(1) & seen[:, ~is_tail].any(1)
    meta = {"session": a.session, "head_stem": s["head_stem"], "data_repo": str(repo), "glove": s["glove"],
            "intrinsics": s["intrinsics"], "frames": n_frames, "frames_with_pose": len(rows),
            "frames_with_tail_and_base": int(pair.sum()), "tails": sorted(tails), "bases": sorted(bases),
            "method": "labels_lib.body_frames (build_dataset pipeline B), positions in mm in the ball body frame"}
    dst = C.gt_dir(a.session)
    dst.mkdir(parents=True, exist_ok=True)
    np.savez(dst / "head_markers.npz", k=np.array([r["k"] for r in rows]), t=t, ids=ids, pos=pos, meta=json.dumps(meta))
    print(f"{a.session}: ball pose in {len(rows)}/{n_frames} head frames, a tail and a base localised in "
          f"{pair.sum()} ({100 * pair.mean():.1f}% of posed frames) -> {dst / 'head_markers.npz'}")


# ------------------------------------------------------------------------------------------------ fit: hhs3
def hhs3_sessions():
    return sorted({e["session"] for e in json.load(open(MANIFEST))["episodes"]} & set(C.SESSIONS))


def hhs3_episodes(sessions):
    """Pose-verified HHs3 episodes of these sessions: [{session, take_episode, hhs3, t, cmd}]."""
    import pandas as pd
    man = [e for e in json.load(open(MANIFEST))["episodes"]
           if e["session"] in sessions and e["method"] in HHS3_METHODS and e["t0"] is not None]
    df = pd.concat([pd.read_parquet(f, columns=["episode_index", "action"])
                    for f in sorted(glob.glob(str(HHS3_ROOT / "data/**/*.parquet"), recursive=True))])
    grip = {int(h): np.stack(g["action"].values)[:, 6].astype(float) for h, g in df.groupby("episode_index")}
    return [{"session": e["session"], "take_episode": e["take_episode"], "hhs3": e["hhs3"],
             "t": e["t0"] + np.arange(len(grip[e["hhs3"]])) * SLOW_DT, "cmd": grip[e["hhs3"]]} for e in man]


def reference_rows(sessions, episodes):
    """Head frames inside each HHs3 episode span with the HHs3 command at their time:
    [(session, row, cmd_ref, hhs3 index)], time-ordered."""
    out = []
    for s in sessions:
        t, ids, pos, _ = load_markers(s)
        rows = rows_from(t, ids, pos)
        for e in (e for e in episodes if e["session"] == s):
            i = np.where((t >= e["t"][0]) & (t <= e["t"][-1]))[0]
            ref = np.interp(t[i], e["t"], e["cmd"])
            out += [(s, rows[n], float(c), e["hhs3"]) for n, c in zip(i, ref)]
    out.sort(key=lambda x: x[1]["t_wall"])
    return out


def wrist_series(session):
    """Cross-check only: gt/gripper_wrist.npz (slam.wrist_width) as one time-sorted series."""
    p = C.gt_dir(session) / "gripper_wrist.npz"
    if not p.exists():
        return None
    z = np.load(p)
    t = np.concatenate([z[k] for k in z.files if k.endswith("_t")])
    v = np.concatenate([z[k[:-2] + "_v"] for k in z.files if k.endswith("_t")])
    o = np.argsort(t)
    return t[o], v[o]


def fit_hhs3(sessions=None, holdout=False, grip_map=GRIP_MAP, verbose=False):
    """Estimators fitted to HHs3's head-camera widths -> calibration dict (see write_calib)."""
    sessions = sessions or hhs3_sessions()
    units = {C.session(s)["glove"] for s in sessions}
    if len(units) != 1:
        raise SystemExit(f"one glove unit per fit, got {units}")
    unit = units.pop()
    tails, bases = unit_markers(unit)
    wm = WidthMap(grip_map)
    eps = hhs3_episodes(sessions)
    ref = reference_rows(sessions, eps)
    hh = np.array([x[3] for x in ref])
    cmd_ref = np.array([x[2] for x in ref])
    fit_sel = ((hh % 2 == 0) if holdout else np.ones(len(ref), bool)) & ~wm.censored(cmd_ref)
    fit_rows = [ref[i][1] for i in np.where(fit_sel)[0]]
    mt = np.array([r["t_wall"] for r in fit_rows])
    mv = wm.to_width(cmd_ref[fit_sel])
    print(f"hhs3, unit {unit}: {len(eps)} HHs3 episodes in {len(sessions)} sessions, {len(ref)} head frames in their "
          f"spans; fit on {len(fit_rows)} ({'even episodes, ' if holdout else ''}censored map ends excluded)")
    ests = L.fit_estimators(fit_rows, mt, mv, tails=tails, bases=bases, singles=list(tails), meas_tol=1e-6,
                            verbose=verbose)
    if not ests:
        raise SystemExit("no estimator passed labels_lib's gates")

    test = (hh % 2 == 1) if holdout else np.ones(len(ref), bool)
    w, _ = predict_widths([x[1] for x in ref], ests)
    pred = wm.to_cmd(w)
    sess = np.array([x[0] for x in ref])
    report = {"units": "gripper command", "scored_on": "odd HHs3 episodes (held out)" if holdout else
              "all fitted episodes (in-sample)", "head": score(pred, cmd_ref, test),
              "per_session": {s: score(pred, cmd_ref, test & (sess == s)) for s in sessions}}
    wr = np.full(len(ref), np.nan)                       # cross-check only: the wrist width, not used
    for s in sessions:
        ws = wrist_series(s)
        if ws is None:
            continue
        i = np.where(sess == s)[0]
        tt = np.array([ref[j][1]["t_wall"] for j in i])
        k = np.clip(np.searchsorted(ws[0], tt), 1, len(ws[0]) - 1)
        near = np.minimum(np.abs(tt - ws[0][k - 1]), np.abs(ws[0][k] - tt)) <= 0.12
        wr[i] = np.where(near, np.interp(tt, ws[0], ws[1]), np.nan)
    both = test & np.isfinite(pred) & np.isfinite(wr)
    report["crosscheck_wrist_not_used"] = {"wrist": score(wr, cmd_ref, test),
                                           "on_common_frames": {"head": score(pred, cmd_ref, both),
                                                                "wrist": score(wr, cmd_ref, both)}}
    h = report["head"]
    print(f"head width vs HHs3, {report['scored_on']}: coverage {100 * h['coverage']:.1f}%, |err| median {h['median']:.4f}"
          f" / p90 {h['p90']:.4f} / p95 {h['p95']:.4f} (command units), gate <= {GATE} agrees on "
          f"{100 * h['gate_agreement']:.2f}%")
    for s, r in report["per_session"].items():
        if r["frames"]:
            print(f"  {s:18s} {r['frames']:6d} frames, coverage {100 * r['coverage']:.1f}%, median {r['median']:.4f}, "
                  f"p95 {r['p95']:.4f}, gate {100 * r['gate_agreement']:.2f}%")
    c = report["crosscheck_wrist_not_used"]["on_common_frames"]
    if c["wrist"]["frames"]:
        print(f"cross-check (wrist camera, not used): on {c['wrist']['frames']} common frames median |err| head "
              f"{c['head']['median']:.4f} / wrist {c['wrist']['median']:.4f}, p95 {c['head']['p95']:.4f} / "
              f"{c['wrist']['p95']:.4f}, gate {100 * c['head']['gate_agreement']:.2f}% / {100 * c['wrist']['gate_agreement']:.2f}%")
    sources = {"dataset": str(HHS3_ROOT), "manifest": rel(MANIFEST), "manifest_sha256": sha256(MANIFEST),
               "manifest_methods": list(HHS3_METHODS), "sessions": sessions, "episodes": len(eps),
               "fit_on": "even HHs3 episodes" if holdout else "all pose-verified HHs3 episodes",
               "head_frames_fit": len(fit_rows), "censored_cmd": [wm.y_lo, wm.y_hi],
               "head_markers": {s: load_markers(s)[3] for s in sessions}}
    return {"unit": unit, "source": "hhs3", "estimators": ests, "grip_map": wm.path, "sources": sources, "report": report}


# ------------------------------------------------------------------------------------------------ fit: holds
def load_holds(log_path):
    """(t, width in actuator units) of a width-holds log's e8_meas events; raw mm -> actuator by
    calib/gap_to_actuator.json, as build_dataset does."""
    log = json.load(open(log_path))
    meas = sorted((e["t_wall"], e["gripper_pos"]) for e in log["events"] if e["event"] == "e8_meas")
    if not meas:
        raise SystemExit(f"{log_path}: no e8_meas events (record_session --width_holds)")
    mt, mv = (np.array(x, float) for x in zip(*meas))
    units = log.get("units", "actuator")
    if units == "mm":
        g2a = json.load(open(GAP_TO_ACT))
        mv = g2a["a"] * mv + g2a["b"]
    elif units != "actuator":
        raise SystemExit(f"{log_path}: units {units!r}; a holds log is in mm or actuator units")
    return mt, mv, units


def to_mm(w):
    g2a = json.load(open(GAP_TO_ACT))
    return (np.asarray(w, float) - g2a["b"]) / g2a["a"]


def score_holds(rows, ests, mt, mv):
    """Prediction vs the holds on frames within HOLD_TOL_S of a hold, in mm (gap_to_actuator inverted)."""
    t = np.array([r["t_wall"] for r in rows])
    j = np.clip(np.searchsorted(mt, t), 1, len(mt) - 1)
    near = np.minimum(np.abs(t - mt[j - 1]), np.abs(mt[j] - t)) <= HOLD_TOL_S
    ref = np.interp(t, mt, mv)
    w, _ = predict_widths(rows, ests)
    out = score(to_mm(w), to_mm(ref), near, gate=None)
    out["units"] = "mm"
    out["per_hold_mm"] = {f"{x:.1f}": score(to_mm(w), to_mm(ref), near & np.isclose(to_mm(ref), x, atol=0.05),
                                            gate=None) for x in np.unique(np.round(to_mm(mv), 1))}
    return out


def fit_holds(unit, log, stem, intrinsics, data_repo=None, verify_log=None, verify_stem=None, verify_intrinsics=None,
              grip_map=GRIP_MAP, verbose=False):
    """Estimators fitted to a unit's caliper width holds (the paper's recipe) -> calibration dict."""
    tails, bases = unit_markers(unit)
    mt, mv, units = load_holds(log)
    rows, n_frames, repo = marker_rows(stem, intrinsics, unit, data_repo)
    print(f"holds, unit {unit}: {len(mt)} hold samples ({units}), {stem}: ball pose in {len(rows)}/{n_frames} frames")
    ests = L.fit_estimators(rows, mt, mv, tails=tails, bases=bases, singles=list(tails), meas_tol=HOLD_TOL_S,
                            verbose=verbose)
    if not ests:
        raise SystemExit("no estimator passed labels_lib's gates (holds must span >= 0.4 of the stroke, both jaws seen)")
    report = {"fit": score_holds(rows, ests, mt, mv), "estimator_holdout": {k: {"rms_mm": e["rms_mm"], "n": e["n"]}
                                                                           for k, e in ests.items()}}
    f = report["fit"]
    print(f"fit recording (in-sample): coverage {100 * f['coverage']:.1f}%, |err| median {f['median']:.2f} mm, "
          f"p95 {f['p95']:.2f} mm")
    sources = {"log": str(Path(log).resolve()), "log_sha256": sha256(log), "log_units": units, "stem": stem,
               "intrinsics": intrinsics, "data_repo": str(repo), "gap_to_actuator": rel(GAP_TO_ACT),
               "marker_map": f"calib/marker_map_glove_{unit}.json", "hold_tol_s": HOLD_TOL_S}
    if verify_log:
        vt, vv, _ = load_holds(verify_log)
        vrows, _, vrepo = marker_rows(verify_stem, verify_intrinsics or intrinsics, unit, data_repo)
        report["verify"] = score_holds(vrows, ests, vt, vv)
        v = report["verify"]
        print(f"verify recording {verify_stem}: coverage {100 * v['coverage']:.1f}%, |err| median {v['median']:.2f} mm, "
              f"p95 {v['p95']:.2f} mm")
        sources["verify"] = {"log": str(Path(verify_log).resolve()), "log_sha256": sha256(verify_log),
                             "stem": verify_stem, "data_repo": str(vrepo)}
    return {"unit": unit, "source": "holds", "estimators": ests, "grip_map": Path(grip_map), "sources": sources,
            "report": report}


# ------------------------------------------------------------------------------------------------ write / predict
def write_calib(cal, dst=None):
    """calib/head_width_glove_<unit>.json: {unit, source, method, created, code, grip_map, grip_map_sha256,
    marker_map, sources, estimators, report}."""
    dst = Path(dst) if dst else calib_path(cal["unit"])
    out = {"unit": cal["unit"], "source": cal["source"], "created": datetime.date.today().isoformat(),
           "code": "slam/head_width.py",
           "method": "build_dataset pipeline B tail/base estimators (labels_lib.fit_estimators) on the head camera, "
                     "in width units (actuator), mapped to the gripper command by grip_map",
           "grip_map": rel(cal["grip_map"]), "grip_map_sha256": sha256(cal["grip_map"]),
           "marker_map": f"calib/marker_map_glove_{cal['unit']}.json", "sources": cal["sources"],
           "estimators": estimators_to_json(cal["estimators"]), "report": cal["report"]}
    json.dump(out, open(dst, "w"), indent=1)
    print("wrote", dst)
    return dst


def predict_session(session, calib=None):
    """gt/head_markers.npz + the unit's calibration -> gt/gripper_head.npz; returns its path."""
    s = C.session(session)
    calib = Path(calib) if calib else calib_path(s["glove"])
    cj = json.load(open(calib))
    if cj["unit"] != s["glove"]:
        raise SystemExit(f"{calib} is for unit {cj['unit']}, session {session} uses {s['glove']}")
    ests = estimators_from_json(cj["estimators"])
    wm = WidthMap(C.REPO / cj["grip_map"])
    t, ids, pos, mmeta = load_markers(session)
    if mmeta["glove"] != s["glove"]:
        raise SystemExit(f"gt/head_markers.npz of {session} was made for unit {mmeta['glove']}; rerun markers")
    w, _ = predict_widths(rows_from(t, ids, pos), ests)
    ok = np.isfinite(w)
    t, cmd = t[ok], wm.to_cmd(w[ok])
    marks = json.load(open(Path(mmeta["data_repo"]) / "data/raw" / f"{session}_glove_episodes.json"))["episodes"]
    out = {}
    for e in marks:
        m = (t >= e["t_start"] - EPISODE_PAD_S) & (t <= e["t_end"] + EPISODE_PAD_S)
        if m.sum() >= 2:
            out[f"g{e['episode_index']}_t"], out[f"g{e['episode_index']}_v"] = t[m], cmd[m]
    meta = {"method": "head camera tails/bases -> labels_lib estimators -> grip map (slam.head_width)",
            "unit": s["glove"], "calib": rel(calib), "calib_sha256": sha256(calib), "calib_source": cj["source"],
            "head_markers": mmeta, "frames_with_width": int(ok.sum()), "frames_with_pose": int(len(ok)),
            "episode_pad_s": EPISODE_PAD_S, "unsmoothed": True}
    dst = C.gt_dir(session) / "gripper_head.npz"
    np.savez(dst, meta=json.dumps(meta), **out)
    print(f"{session}: width in {ok.sum()}/{len(ok)} posed head frames ({100 * ok.mean():.1f}%), "
          f"{len(out) // 2} episodes -> {dst}")
    return dst


def load_gripper_head(session):
    """{episode index: (wall times, command)} from gt/gripper_head.npz ({} if absent)."""
    p = C.gt_dir(session) / "gripper_head.npz"
    if not p.exists():
        return {}
    z = np.load(p)
    return {int(k[1:-2]): (z[k], z[k[:-2] + "_v"]) for k in z.files if k.endswith("_t")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("markers", help="gt/head_markers.npz for a session")
    p.add_argument("--session", required=True)
    p.add_argument("--data-repo", help="default: the main checkout's data or <work>/takes, whichever has the stem")
    p = sub.add_parser("fit", help="calib/head_width_glove_<unit>.json")
    p.add_argument("--source", choices=("holds", "hhs3"), required=True)
    p.add_argument("--grip-map", default=str(GRIP_MAP))
    p.add_argument("--out", help="default: calib/head_width_glove_<unit>.json (hhs3 --holdout: ..._holdout.json)")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--sessions", nargs="*", help="hhs3: default every slam.config session in the HHs3 manifest")
    p.add_argument("--holdout", action="store_true", help="hhs3: fit on even HHs3 episodes, score the odd ones")
    p.add_argument("--unit", help="holds: glove unit (calib/marker_map_glove_<unit>.json, glove_<unit>_*_bundle.json)")
    p.add_argument("--log", help="holds: <dataset>_glove_log.json with the caliper holds")
    p.add_argument("--stem", help="holds: camera stem of that recording (<stem>_dodeca_detections.npz, <stem>_ts.json)")
    p.add_argument("--intrinsics", help="holds: that camera's intrinsics file in calib/")
    p.add_argument("--data-repo")
    p.add_argument("--verify-log")
    p.add_argument("--verify-stem")
    p.add_argument("--verify-intrinsics", help="default: --intrinsics")
    p = sub.add_parser("predict", help="gt/gripper_head.npz for a session")
    p.add_argument("--session", required=True)
    p.add_argument("--calib", help="default: calib/head_width_glove_<unit>.json")
    a = ap.parse_args()
    if a.cmd == "markers":
        cmd_markers(a)
    elif a.cmd == "predict":
        predict_session(a.session, a.calib)
    elif a.source == "hhs3":
        cal = fit_hhs3(a.sessions, a.holdout, a.grip_map, a.verbose)
        write_calib(cal, a.out or (calib_path(cal["unit"]).with_name(f"head_width_glove_{cal['unit']}_holdout.json")
                                   if a.holdout else None))
    else:
        missing = [f"--{k}" for k in ("unit", "log", "stem", "intrinsics") if not getattr(a, k)]
        if missing or bool(a.verify_log) != bool(a.verify_stem):
            ap.error(f"--source holds needs {missing or ['--verify-log with --verify-stem']}")
        write_calib(fit_holds(a.unit, a.log, a.stem, a.intrinsics, a.data_repo, a.verify_log, a.verify_stem,
                              a.verify_intrinsics, a.grip_map, a.verbose), a.out)


if __name__ == "__main__":
    main()
