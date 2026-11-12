#!/usr/bin/env python3
"""Gripper width from the head camera alone: the paper's tail estimators, calibrated against Yosub's built glove set.

The paper reads the jaw width in the head camera. Each jaw carries a wedge (the tail) with tags; their distance
to the fixed gripper-back tags, along the jaw axis, gives the width through a per-unit linear map. That map is
fitted on caliper width holds (<dataset>_glove_log.json), which are not archived for unit yosub.
pilot_glove_HHs3's gripper channel is that head-camera width: its interpolation kinks sit at the head camera's
frame times, not the wrist camera's (checked 2026-11-12 on 179 episodes). HHs3 therefore stands in for the holds
as the calibration target.

No wrist-camera data enters the width (decision 2026-11-12: the wrist camera is a cross-check only). `fit`
reports the wrist width's error on the same frames, labelled as such.

Method = scripts/build_dataset.py pipeline B:
  * labels_lib.body_frames on the head detections, with the unit's tails + bases. Marker sizes come from
    calib/marker_map_glove_<unit>.json; the ball and gripper-back bundles are the same as for the ball pose.
  * then labels_lib.fit_estimators / predict_aperture (median over the visible tail-base pairs and single tails).

Fitting is per glove unit, over the pose-verified HHs3 episodes (manifest method verified / remapped) of every
session, in width units:
  * HHs3 command -> width by inverting calib/width_to_cmd_glove_v2.json;
  * samples on the map's flat ends (closed floor 0.20, open ceiling 0.998) are censored, since they have no
    unique width;
  * prediction -> command by the same map.
`fit --holdout` fits on even HHs3 episodes and scores the odd ones; `fit` alone fits on all (the calibration).

  S=/home/student/miniconda3/envs/sam2/bin/python
  $S -m slam.head_width markers --session S    # gt/head_markers.npz: body-frame tail/base positions per head frame
  $S -m slam.head_width fit [--holdout]        # calib/head_width_glove_<unit>.json, report printed and stored
  $S -m slam.head_width predict --session S    # gt/gripper_head.npz in gt/gripper_wrist.npz's layout

Detection caches and raw timestamps are read from the main checkout's data, or from <work>/takes for the
per-take sessions (glove5 / glove6 takes, glove8), whichever holds the session's head stem.
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
SLOW_DT = 1.0 / 37.5                    # HHs3 step: 15 fps declared, --slow 2.5 (as slam.hhs3_manifest)
CALIB_METHODS = ("verified", "remapped")
GATE = 0.45                             # the masks' held_width_max: report how often the gate agrees
EPISODE_PAD_S = 0.5                     # predict: each marked episode +- this (gt/gripper_wrist.npz's window)


# ------------------------------------------------------------------------------------------------ helpers
def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def detection_repo(session):
    """The data repo holding the session's head detections and timestamps (main checkout or <work>/takes)."""
    stem = C.session(session)["head_stem"]
    for repo in (C.DATA_REPO, C.WORK / "takes"):
        if (repo / "calib" / f"{stem}_dodeca_detections.npz").exists() and (repo / "data/raw" / f"{stem}_ts.json").exists():
            return repo
    raise FileNotFoundError(f"no head detections / timestamps for {stem} in {C.DATA_REPO} or {C.WORK / 'takes'}")


def unit_markers(unit):
    mm = json.load(open(C.CALIB / f"marker_map_glove_{unit}.json"))
    return ({int(k): float(v) for k, v in mm["tails"].items()},
            {int(k): float(v) for k, v in mm["bases"].items()})


class WidthMap:
    """calib/width_to_cmd_glove_v2.json: glove width (actuator units) -> gripper command, and its inverse on the
    strictly increasing part (commands on the flat ends are censored: no unique width)."""

    def __init__(self, path=GRIP_MAP):
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


def load_markers(session):
    z = np.load(C.gt_dir(session) / "head_markers.npz")
    return z["t"], z["ids"], z["pos"], json.loads(str(z["meta"]))


def rows_from(t, ids, pos):
    """labels_lib rows ({t_wall, pb}) from the stored marker positions (NaN = not localised in that frame)."""
    ok = np.isfinite(pos[..., 0])
    return [{"t_wall": float(t[n]), "pb": {int(ids[j]): pos[n, j] for j in np.where(ok[n])[0]}} for n in range(len(t))]


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


# ------------------------------------------------------------------------------------------------ markers
def cmd_markers(a):
    s = C.session(a.session)
    repo = detection_repo(a.session)
    stem = s["head_stem"]
    K, dist = L.load_intrinsics(C.CALIB / s["intrinsics"])
    T_body, dobj = L.load_bundle(C.CALIB / f"glove_{s['glove']}_dodeca_bundle.json")
    extra = L.load_gripper_bundle(str(C.CALIB / f"glove_{s['glove']}_gripper_bundle.json"))
    tails, bases = unit_markers(s["glove"])
    ts = json.load(open(repo / "data/raw" / f"{stem}_ts.json"))
    det = np.load(repo / "calib" / f"{stem}_dodeca_detections.npz")
    rows = L.body_frames(det, ts, K, dist, T_body, dobj, {**tails, **bases}, extra=extra)
    ids = np.array(sorted({**tails, **bases}))
    pos = np.full((len(rows), len(ids), 3), np.nan)
    for n, r in enumerate(rows):
        for j, i in enumerate(ids):
            if int(i) in r["pb"]:
                pos[n, j] = r["pb"][int(i)]
    seen = np.isfinite(pos[..., 0])
    is_tail = np.isin(ids, list(tails))
    pair = (seen[:, is_tail].any(1) & seen[:, ~is_tail].any(1))
    meta = {"session": a.session, "head_stem": stem, "data_repo": str(repo), "glove": s["glove"],
            "intrinsics": s["intrinsics"], "frames": len(ts), "frames_with_pose": len(rows),
            "frames_with_tail_and_base": int(pair.sum()), "tails": sorted(tails), "bases": sorted(bases),
            "method": "labels_lib.body_frames (build_dataset pipeline B), positions in mm in the ball body frame"}
    dst = C.gt_dir(a.session)
    dst.mkdir(parents=True, exist_ok=True)
    np.savez(dst / "head_markers.npz", k=np.array([r["k"] for r in rows]), t=np.array([r["t_wall"] for r in rows]),
             ids=ids, pos=pos, meta=json.dumps(meta))
    print(f"{a.session}: ball pose in {len(rows)}/{len(ts)} head frames, a tail and a base localised in "
          f"{pair.sum()} ({100 * pair.mean():.1f}% of posed frames) -> {dst / 'head_markers.npz'}")


# ------------------------------------------------------------------------------------------------ fit
def hhs3_episodes(sessions):
    """Pose-verified HHs3 episodes of these sessions: [{session, take_episode, hhs3, t, cmd}]."""
    import pandas as pd
    man = [e for e in json.load(open(MANIFEST))["episodes"]
           if e["session"] in sessions and e["method"] in CALIB_METHODS and e["t0"] is not None]
    df = pd.concat([pd.read_parquet(f, columns=["episode_index", "action"])
                    for f in sorted(glob.glob(str(HHS3_ROOT / "data/**/*.parquet"), recursive=True))])
    grip = {int(h): np.stack(g["action"].values)[:, 6].astype(float) for h, g in df.groupby("episode_index")}
    out = []
    for e in man:
        g = grip[e["hhs3"]]
        out.append({"session": e["session"], "take_episode": e["take_episode"], "hhs3": e["hhs3"],
                    "t": e["t0"] + np.arange(len(g)) * SLOW_DT, "cmd": g})
    return out


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


def score(pred, ref, ok=None):
    """|pred - ref| stats in command units over finite predictions (ok: extra frame mask)."""
    pred, ref = np.asarray(pred, float), np.asarray(ref, float)
    ok = np.ones(len(pred), bool) if ok is None else np.asarray(ok, bool)
    m = np.isfinite(pred) & ok
    if not m.any():
        return {"frames": 0, "coverage": 0.0}
    e = np.abs(pred[m] - ref[m])
    return {"frames": int(m.sum()), "coverage": float(m.sum() / ok.sum()), "median": float(np.median(e)),
            "p90": float(np.percentile(e, 90)), "p95": float(np.percentile(e, 95)), "mean": float(e.mean()),
            "gate_agreement": float(np.mean((pred[m] <= GATE) == (ref[m] <= GATE)))}


def cmd_fit(a):
    sessions = a.sessions or sorted(C.SESSIONS)
    units = {C.session(s)["glove"] for s in sessions}
    if len(units) != 1:
        raise SystemExit(f"one glove unit per fit, got {units}")
    unit = units.pop()
    tails, bases = unit_markers(unit)
    wm = WidthMap()
    eps = hhs3_episodes(sessions)
    ref = reference_rows(sessions, eps)
    hh = np.array([x[3] for x in ref])
    cmd_ref = np.array([x[2] for x in ref])
    fit_sel = (hh % 2 == 0) if a.holdout else np.ones(len(ref), bool)
    fit_sel &= ~wm.censored(cmd_ref)
    fit_rows = [ref[i][1] for i in np.where(fit_sel)[0]]
    mt = np.array([r["t_wall"] for r in fit_rows])
    mv = wm.to_width(cmd_ref[fit_sel])
    print(f"unit {unit}: {len(eps)} HHs3 episodes in {len(sessions)} sessions, {len(ref)} head frames in their spans; "
          f"fit on {len(fit_rows)} ({'even episodes, ' if a.holdout else ''}censored map ends excluded)")
    ests = L.fit_estimators(fit_rows, mt, mv, tails=tails, bases=bases, singles=list(tails), meas_tol=1e-6,
                            verbose=a.verbose)
    if not ests:
        raise SystemExit("no estimator passed labels_lib's gates")
    print(f"{len(ests)} estimators: " + ", ".join(f"{k} ({e['rms_mm']:.1f} mm, n {e['n']})" for k, e in sorted(ests.items())))

    test = (hh % 2 == 1) if a.holdout else np.ones(len(ref), bool)
    w, n_used = predict_widths([x[1] for x in ref], ests)
    pred = wm.to_cmd(w)
    report = {"scored_on": "odd HHs3 episodes (held out)" if a.holdout else "all fitted episodes (in-sample)",
              "head": score(pred, cmd_ref, test), "per_session": {}}
    sess = np.array([x[0] for x in ref])
    for s in sessions:
        report["per_session"][s] = score(pred, cmd_ref, test & (sess == s))
    # cross-check only (not used by the width): the wrist camera's width on the same frames
    wr = np.full(len(ref), np.nan)
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

    out = {"unit": unit, "created": datetime.date.today().isoformat(), "code": "slam/head_width.py",
           "method": "build_dataset pipeline B tail/base estimators (labels_lib.fit_estimators) in width units, "
                     "calibrated against pilot_glove_HHs3's head-camera gripper channel",
           "fit": "even HHs3 episodes" if a.holdout else "all pose-verified HHs3 episodes",
           "sources": {"dataset": str(HHS3_ROOT), "manifest": str(MANIFEST.relative_to(C.REPO)),
                       "manifest_sha256": sha256(MANIFEST), "manifest_methods": list(CALIB_METHODS),
                       "sessions": sessions, "episodes": len(eps), "head_frames_fit": len(fit_rows),
                       "marker_map": f"calib/marker_map_glove_{unit}.json",
                       "grip_map": str(GRIP_MAP.relative_to(C.REPO)), "grip_map_sha256": sha256(GRIP_MAP),
                       "censored_cmd": [wm.y_lo, wm.y_hi],
                       "head_markers": {s: load_markers(s)[3] for s in sessions}},
           "estimators": estimators_to_json(ests), "report": report}
    dst = Path(a.out) if a.out else (C.CALIB / f"head_width_glove_{unit}{'_holdout' if a.holdout else ''}.json")
    json.dump(out, open(dst, "w"), indent=1)
    print("wrote", dst)


# ------------------------------------------------------------------------------------------------ predict
def cmd_predict(a):
    s = C.session(a.session)
    calib = Path(a.calib) if a.calib else C.CALIB / f"head_width_glove_{s['glove']}.json"
    cj = json.load(open(calib))
    if cj["unit"] != s["glove"]:
        raise SystemExit(f"{calib} is for unit {cj['unit']}, session {a.session} uses {s['glove']}")
    ests = estimators_from_json(cj["estimators"])
    wm = WidthMap()
    t, ids, pos, mmeta = load_markers(a.session)
    w, n_used = predict_widths(rows_from(t, ids, pos), ests)
    ok = np.isfinite(w)
    t, cmd, n_used = t[ok], wm.to_cmd(w[ok]), n_used[ok]
    marks = json.load(open(Path(mmeta["data_repo"]) / "data/raw" / f"{a.session}_glove_episodes.json"))["episodes"]
    out, cov = {}, {}
    for e in marks:
        m = (t >= e["t_start"] - EPISODE_PAD_S) & (t <= e["t_end"] + EPISODE_PAD_S)
        if m.sum() < 2:
            continue
        out[f"g{e['episode_index']}_t"], out[f"g{e['episode_index']}_v"] = t[m], cmd[m]
    meta = {"method": "head camera tails/bases -> labels_lib estimators -> width_to_cmd_glove_v2 (slam.head_width)",
            "calib": str(calib.relative_to(C.REPO)) if calib.is_relative_to(C.REPO) else str(calib),
            "calib_sha256": sha256(calib), "head_markers": mmeta, "frames_with_width": int(ok.sum()),
            "frames_with_pose": int(len(ok)), "episode_pad_s": EPISODE_PAD_S, "unsmoothed": True}
    dst = C.gt_dir(a.session) / "gripper_head.npz"
    np.savez(dst, meta=json.dumps(meta), **out)
    print(f"{a.session}: width in {ok.sum()}/{len(ok)} posed head frames ({100 * ok.mean():.1f}%), "
          f"{len(out) // 2} episodes -> {dst}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("markers")
    p.add_argument("--session", required=True)
    p = sub.add_parser("fit")
    p.add_argument("--sessions", nargs="*", help="default: every session in slam.config")
    p.add_argument("--holdout", action="store_true", help="fit on even HHs3 episodes, score the odd ones")
    p.add_argument("--out")
    p.add_argument("--verbose", action="store_true")
    p = sub.add_parser("predict")
    p.add_argument("--session", required=True)
    p.add_argument("--calib", help="default: calib/head_width_glove_<unit>.json")
    a = ap.parse_args()
    {"markers": cmd_markers, "fit": cmd_fit, "predict": cmd_predict}[a.cmd](a)


if __name__ == "__main__":
    main()
