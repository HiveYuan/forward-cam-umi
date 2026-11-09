"""Analysis steps (slam.pipeline.impl_analysis) and the stable modules they call, on synthetic
data in a temporary SLAM_WORK (python -m slam.tests.test_analysis):

  - the framework's scale selection: s is always the primary's, checks only flag, and the
    labels and evaluate steps use exactly that s (slam.scale.METHODS stubbed);
  - primary 'native' on a metric and on an up-to-scale trajectory;
  - untracked frames (NaN rows of T_slam_cam, slam.backends.base) through slam.evaluate,
    slam.scale (tiles, A, B) and slam.labels: nothing raises, untracked dt = 0.08 s pairs
    count as tracking failures, untracked keyframes do not enter method B;
  - slam.backends.base.check_output on the optional outputs and meta masks_used.
"""
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from slam import config as C
from slam import geometry as G
from slam.backends import base as B

SESSION = "synth"


# ---------------------------------------------------------------------- helpers
@contextmanager
def _work():
    """Temporary SLAM_WORK with a synthetic session (glove 'yosub' calibration from calib/)."""
    old_work, old_sess = C.WORK, dict(C.SESSIONS)
    with tempfile.TemporaryDirectory() as tmp:
        C.WORK = Path(tmp)
        C.SESSIONS[SESSION] = {"head_stem": "x", "intrinsics": "x", "glove": "yosub", "tile_layout": "x"}
        try:
            yield C.segments_dir(SESSION)
        finally:
            C.WORK = old_work
            C.SESSIONS.clear()
            C.SESSIONS.update(old_sess)


@contextmanager
def _patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


@contextmanager
def _methods(stubs):
    """slam.scale.METHODS with some methods replaced (restored afterwards)."""
    from slam import scale as SC
    saved = dict(SC.METHODS)
    SC.METHODS.update(stubs)
    try:
        yield
    finally:
        SC.METHODS.clear()
        SC.METHODS.update(saved)


def _save_traj(path, T, tracked, metric=False, kf_t=None, kf_disp=None, kf_pose_cw=None, size=(64, 48),
               mask_names=(), meta=None):
    """traj.npz through slam.backends.base.save_output (untracked rows become NaN)."""
    n = len(T)
    inp = B.SlamInput(images=[f"{i:06d}.jpg" for i in range(n)], k=np.arange(n), t=np.arange(n) / 30.0,
                      K=np.eye(3), size=size, mask_names=list(mask_names))
    out = B.SlamOutput(T_slam_cam=T, tracked=np.asarray(tracked, bool), metric=metric, kf_t=kf_t, kf_disp=kf_disp,
                       kf_pose_cw=kf_pose_cw, meta=dict(meta or {"n_keyframes": 0}))
    path.parent.mkdir(parents=True, exist_ok=True)
    return B.save_output(path, out, inp, "fake", {})


def _stub_segments(root, names, runs=(("R", False),)):
    """Segments with a real (tiny) traj.npz per run (metric flag as given) and a gt.npz stand-in."""
    for name in names:
        seg = root / name
        for run, metric in runs:
            _save_traj(seg / "slam" / f"{run}.npz", np.tile(np.eye(4), (5, 1, 1)), np.ones(5, bool), metric=metric)
        (seg / "gt.npz").write_bytes(b"x")
    return [root / n for n in names]


def _job(out_dir, segments, analysis, params=None, inputs=None):
    return SimpleNamespace(session=SESSION, segments=list(segments), out_dir=Path(out_dir), analysis=analysis,
                           params=params or {}, inputs=inputs or {}, log=lambda msg: None)


# per segment: B (primary), A (check), tiles (oracle); None = the method fails there
S_B = {"ep00": 0.70, "ep01": 0.50, "ep02": 0.40, "ep03": None}
S_A = {"ep00": 0.72, "ep01": 0.60, "ep02": None, "ep03": 0.90}
S_T = {"ep00": 0.75, "ep01": 0.55, "ep02": None, "ep03": 0.80}
SEGS = sorted(S_B)
THR = 0.10


def _stub(table, calls, name):
    """A scale method with the per-segment results `table`; B's signature takes the mask
    keywords (like slam.scale.scale_depth_ball), the others do not (and must not get them)."""
    def result(seg, run, masks, dilate, model, knob):
        calls.append((name, seg.name, run, None if masks is None else tuple(masks), dilate, model, knob))
        s = table.get(seg.name)
        return {"s": float("nan") if s is None else s, "ok": s is not None}

    if name == "B":
        def f(seg, run, mask_names=None, mask_dilate_px=8, model="m0", knob=1, **_):
            return result(seg, run, mask_names, mask_dilate_px, model, knob)
    else:
        def f(seg, run, model="m0", knob=1, **kw):
            return result(seg, run, kw.get("mask_names"), kw.get("mask_dilate_px"), model, knob)
    return f


def _scale_analysis(run="R", masks=("motion",), dilate=4):
    return {"slam_runs": {run: {"masks": list(masks), "dilate_px": dilate}},
            "scale": {run: {"primary": "B", "checks": ["A"], "flag_threshold": THR,
                            "methods": {"A": {"knob": 2}, "B": {"knob": 3, "depth": "da2",
                                                                "_depth_node": f"depth.da2@{run}"}}}}}


DEPTH_INPUTS = {"depth.da2@R": {"step": "depth", "name": "da2", "params": {"model": "da2-metric-indoor-large"}}}


# ---------------------------------------------------------------------- scale selection (framework)
def test_scale_run_primary_s_and_flags():
    """scale_run: s = B's on every segment where B succeeds (flagged ones included); flagged iff
    |s_A/s_B - 1| > threshold; the stored file round-trips through _scale_rows."""
    from slam.pipeline import impl_analysis as IA
    calls = []
    with _work() as root, _methods({"A": _stub(S_A, calls, "A"), "B": _stub(S_B, calls, "B"),
                                    "tiles": _stub(S_T, calls, "tiles")}):
        _stub_segments(root, SEGS)
        out = C.WORK / "results"
        out.mkdir()
        job = _job(out, SEGS, _scale_analysis(), inputs=DEPTH_INPUTS)
        res = IA.scale_run(job, "R", job.analysis["scale"]["R"])
        assert res["label"] == "B+Acheck" and res["primary"] == "B" and res["checks"] == ["A"]
        expect_flagged = []
        for r in res["rows"]:
            seg, sb, sa, so = r["segment"], S_B[r["segment"]], S_A[r["segment"]], S_T[r["segment"]]
            assert r["ok"] == (sb is not None) and r["primary"]["ok"] == r["ok"]
            assert r["s"] == sb                                   # exactly B's (None where B failed)
            flag = sb is not None and sa is not None and abs(sa / sb - 1) > THR
            assert r["flagged"] == flag and r["flagged_by"] == (["A"] if flag else []), r
            if flag:
                expect_flagged.append(seg)
            c = r["checks"]["A"]
            assert c["ok"] == (sa is not None) and c["s"] == sa
            assert (c["diff"] is None) == (sa is None or sb is None)
            if c["diff"] is not None:
                assert abs(c["diff"] - (sa / sb - 1)) < 1e-15
            assert r["oracle_s"] == so
            assert (r["err"] is None) == (sb is None or so is None)
            if r["err"] is not None:
                assert abs(r["err"] - (sb / so - 1)) < 1e-15
        assert expect_flagged == ["ep01"]                         # +20%; ep00 +2.9%, ep02/ep03 one side failed
        sm = res["summary"]
        assert sm["flagged"] == expect_flagged and sm["segments"] == 4 and sm["segments_ok"] == 3
        assert sm["both"] == ["ep00", "ep01"] and sm["n_compared"] == 2 and sm["without_flagged"]["n_compared"] == 1
        assert sm["methods"]["A"]["segments_ok"] == 3 and sm["methods"]["B"]["segments_ok"] == 3
        # framework keyword arguments: configured params, depth model from the depth node, run masks
        b_calls = {c for c in calls if c[0] == "B"}
        assert b_calls == {("B", s, "R", ("motion",), 4, "da2-metric-indoor-large", 3) for s in SEGS}, b_calls
        a_calls = {c for c in calls if c[0] == "A"}
        assert a_calls == {("A", s, "R", None, None, "m0", 2) for s in SEGS}, a_calls
        # the stored file -> the {segment: s} map and the flagged list the labels/evaluate steps use
        IA.run_scale(job)
        smap, flagged, label = IA._scale_rows(job, "R")
        assert smap == {r["segment"]: (r["s"] if r["ok"] else None) for r in res["rows"]}
        assert smap == S_B and flagged == expect_flagged and label == "B+Acheck"
        assert (out / "scale_R.md").exists()


def test_check_failure_never_changes_s():
    """Whatever the check returns (fails everywhere, agrees, disagrees wildly), s and ok are the
    primary's; only the flags change."""
    from slam.pipeline import impl_analysis as IA
    variants = {"fails": {s: None for s in SEGS}, "agrees": dict(S_B),
                "wild": {"ep00": 7.0, "ep01": 0.05, "ep02": 0.41, "ep03": 2.0}}
    rows = {}
    with _work() as root:
        segs = _stub_segments(root, SEGS)
        for name, sa in variants.items():
            for seg in segs:                                       # successes are cached: start clean
                shutil.rmtree(seg / "scale", ignore_errors=True)
            with _methods({"A": _stub(sa, [], "A"), "B": _stub(S_B, [], "B"), "tiles": _stub(S_T, [], "tiles")}):
                job = _job(C.WORK, SEGS, _scale_analysis(), inputs=DEPTH_INPUTS)
                rows[name] = IA.scale_run(job, "R", job.analysis["scale"]["R"])["rows"]
    for name, rr in rows.items():
        assert [(r["segment"], r["s"], r["ok"], r["err"]) for r in rr] == \
               [(r["segment"], r["s"], r["ok"], r["err"]) for r in rows["fails"]], name
        assert [r["s"] for r in rr] == [S_B[s] for s in SEGS]
    assert not any(r["flagged"] for r in rows["fails"] + rows["agrees"])
    assert [r["segment"] for r in rows["wild"] if r["flagged"]] == ["ep00", "ep01"]   # ep02 +2.5%, ep03 no B


def test_evaluate_and_labels_use_primary_s():
    """run_evaluate gives evaluate_session a scale_fn returning B's s (NaN where B failed), and
    run_labels builds the scaled labels with B's s; analysis.json records fail_deg and dts."""
    from slam import evaluate as EV
    from slam import labels as L
    from slam.pipeline import impl_analysis as IA
    ev_calls, lab_calls = [], []

    def fake_evaluate_session(session, runs, out, scale_fn=None, dts=EV.DTS, fail_deg=EV.FAIL_DEG, scale_name="tiles"):
        ev_calls.append({"runs": list(runs), "out": Path(out).name, "scale_fn": scale_fn, "dts": list(dts),
                         "fail_deg": fail_deg, "scale_name": scale_name})
        return {"runs": {r: {"track_fail_frac": 0.0, "scale_ok_segments": [0, 0]} for r in runs}}

    def fake_build_segment(seg, ref, scale_mode, T_bt, grip=None, scale=None):
        lab_calls.append((seg.name, ref, scale_mode, scale))
        return {"keep": True}

    with _work() as root, _methods({"A": _stub(S_A, [], "A"), "B": _stub(S_B, [], "B"),
                                    "tiles": _stub(S_T, [], "tiles")}):
        segs = _stub_segments(root, SEGS, runs=(("R", False), ("E", False)))
        out = C.WORK / "results"
        out.mkdir()
        an = _scale_analysis()
        an["slam_runs"]["E"] = {"masks": [], "dilate_px": 8}        # a run without a scale block
        an["labels"] = {"runs": ["R"]}
        an["evaluate"] = {"runs": ["R", "E"]}
        lab_params = {"fps": L.FPS, "label_tol_s": L.LABEL_TOL, "min_coverage": L.MIN_COVERAGE,
                      "bridge_s": L.BRIDGE, "min_episode_s": L.MIN_EPISODE, "gripper": "wrist",
                      "horizon": 100, "chunk_H": [15, 30], "label_steps": [1, 15]}
        job = _job(out, SEGS, an, params=lab_params, inputs=DEPTH_INPUTS)
        IA.run_scale(job)
        with _patched(L, "build_segment", fake_build_segment):
            IA.run_labels(job)
        scaled = {(s, sc) for s, ref, mode, sc in lab_calls if ref == "R" and mode == "B+Acheck"}
        assert scaled == {(s, (S_B[s], "B+Acheck")) for s in SEGS}, scaled
        assert {(s, ref, mode, sc) for s, ref, mode, sc in lab_calls if mode == "tiles"} == \
               {(s, ref, "tiles", None) for s in SEGS for ref in ("tiles", "R")}
        assert (out / "labels_R@B+Acheck.json").exists() and (out / "labels_R.json").exists()

        job.params = {"dts": [0.08, 1.0], "fail_deg": 3.5, "gt_noise": False}
        with _patched(EV, "evaluate_session", fake_evaluate_session):
            IA.run_evaluate(job)
        assert [(c["runs"], c["out"], c["scale_fn"] is None) for c in ev_calls] == \
               [(["R", "E"], "eval_oracle", True), (["R"], "eval_B+Acheck", False)]
        assert all(c["fail_deg"] == 3.5 and c["dts"] == [0.08, 1.0] for c in ev_calls)
        fn = ev_calls[1]["scale_fn"]
        assert ev_calls[1]["scale_name"] == "B+Acheck"
        for seg in segs:
            s = fn(seg, "R", 0.123)                                  # the oracle value is ignored
            assert (np.isnan(s) if S_B[seg.name] is None else s == S_B[seg.name]), (seg.name, s)
        idx = json.load(open(out / "analysis.json"))
        assert idx["evaluate"] == {"fail_deg": 3.5, "dts": [0.08, 1.0]}
        assert idx["runs"]["R"]["scale_label"] == "B+Acheck" and idx["runs"]["E"]["scale_label"] is None
        assert idx["runs"]["R"]["eval"] == {"oracle": "eval_oracle", "scaled": "eval_B+Acheck"}
        assert idx["runs"]["R"]["slam"]["tracked_frac"] == 1.0


def test_native_primary_metric_and_not():
    """primary 'native' (real slam.scale.scale_native): s = 1 on a metric trajectory, no scale on
    an up-to-scale one; evaluate's scale_fn follows."""
    from slam import evaluate as EV
    from slam.pipeline import impl_analysis as IA
    ev_calls = []

    def fake_evaluate_session(session, runs, out, scale_fn=None, dts=EV.DTS, fail_deg=EV.FAIL_DEG, scale_name="tiles"):
        ev_calls.append((list(runs), Path(out).name, scale_fn, scale_name))
        return {"runs": {r: {"track_fail_frac": 0.0, "scale_ok_segments": [0, 0]} for r in runs}}

    block = {"primary": "native", "checks": [], "flag_threshold": None, "methods": {}}
    with _work() as root, _methods({"tiles": _stub(S_T, [], "tiles")}):
        segs = _stub_segments(root, SEGS, runs=(("M", True), ("U", False)))
        out = C.WORK / "results"
        out.mkdir()
        an = {"slam_runs": {r: {"masks": [], "dilate_px": 8} for r in ("M", "U")},
              "scale": {"M": block, "U": block}, "evaluate": {"runs": ["M", "U"]}}
        job = _job(out, SEGS, an, params={"dts": [1.0], "fail_deg": 2.0, "gt_noise": False})
        m = IA.scale_run(job, "M", block)
        u = IA.scale_run(job, "U", block)
        assert m["label"] == u["label"] == "native"
        assert all(r["s"] == 1.0 and r["ok"] and not r["flagged"] for r in m["rows"])
        assert [r["err"] for r in m["rows"]] == [None if S_T[s] is None else 1.0 / S_T[s] - 1 for s in SEGS]
        assert all(r["s"] is None and not r["ok"] and r["err"] is None for r in u["rows"])
        assert all("not metric" in r["primary"]["error"] for r in u["rows"])
        assert m["summary"]["segments_ok"] == 4 and u["summary"]["segments_ok"] == 0 and u["summary"]["n_compared"] == 0
        IA.run_scale(job)
        with _patched(EV, "evaluate_session", fake_evaluate_session):
            IA.run_evaluate(job)
        assert [(c[0], c[1], c[3]) for c in ev_calls] == [(["M", "U"], "eval_oracle", "tiles"),
                                                          (["M", "U"], "eval_native", "native")]
        fn = ev_calls[1][2]
        for seg in segs:
            assert fn(seg, "M", 0.5) == 1.0 and np.isnan(fn(seg, "U", 0.5))


# ---------------------------------------------------------------------- untracked frames
N, FPS, S_TRUE = 90, 30.0, 0.6
UNTRACKED = list(range(40, 50)) + [70]           # 0.33 s block (label gaps) + one isolated frame
KF_T = np.array([20, 45, 47])                    # keyframes 45, 47 are untracked
W, H, F = 64, 48, 100.0


def _rvec(R):
    q = G.R_to_quat(R)
    ang = 2 * np.arctan2(np.linalg.norm(q[:, :3], axis=1), q[:, 3])
    return q[:, :3] / np.maximum(np.linalg.norm(q[:, :3], axis=1, keepdims=True), 1e-12) * ang[:, None]


def _untracked_segment(seg):
    """Head moving in front of a static ball (method A sees a static point), tile poses on every
    frame, SLAM = world -> SLAM similarity of the tile poses at scale 1/S_TRUE with UNTRACKED
    frames lost; DROID-like keyframes and a constant metric-depth cache for method B (disk
    correction). Returns the ball-correction factor k method B computes."""
    t = np.arange(N) / FPS
    wall = 100.0 + t
    T_wc = G.rt_to_T(np.stack([0.05 * np.sin(2 * np.pi * t / 3), 0.08 * np.sin(2 * np.pi * t / 2.5 + 0.3), 0.02 * t], 1),
                     np.stack([0.10 * np.sin(2 * np.pi * t / 3), 0.05 * np.cos(2 * np.pi * t / 3), 0.03 * t], 1))
    T_wb = G.rt_to_T(np.array([0.1, -0.2, 0.3]), np.array([0.0, 0.02, 0.5]))[0]      # static ball
    T_cb = G.inv(T_wc) @ T_wb
    seg.mkdir(parents=True)
    K = [[F, 0, W / 2], [0, F, H / 2], [0, 0, 1]]
    json.dump({"frames": [{"i": i, "k": i, "wall": float(wall[i]), "in_episode": True} for i in range(N)],
               "size": [W, H], "K": K, "session": SESSION,
               "episode": {"episode_index": 0, "t_start": float(wall[0]), "t_end": float(wall[-1])}},
              open(seg / "frames.json", "w"))
    rv = _rvec(T_cb[:, :3, :3])
    assert np.allclose(G.rt_to_T(rv, T_cb[:, :3, 3]), T_cb, atol=1e-12)
    np.savez(seg / "gt.npz", cam_k=np.arange(N), T_cam_world=G.inv(T_wc), cam_tiles=np.full(N, 2), cam_rms=np.ones(N),
             full_k=np.arange(N), full_rvec=rv, full_tvec=T_cb[:, :3, 3])
    G0 = G.rt_to_T(np.array([0.2, 0.1, -0.3]), np.array([0.3, -0.1, 0.2]))[0]       # world -> SLAM frame
    T_sc = G0[None] @ T_wc
    T_sc[:, :3, 3] /= S_TRUE
    tracked = np.ones(N, bool)
    tracked[UNTRACKED] = False
    T_sc[~tracked] = 0.0                                                             # garbage: save_output NaNs it
    from slam.scale import BALL_R
    k = float(np.median([T_cb[i, 2, 3] - BALL_R for i in KF_T]))                    # B, disk: network depth 1 m
    ok_kf = tracked[KF_T]
    disp = np.where(ok_kf, S_TRUE / k, 10 * S_TRUE / k)[:, None, None] * np.ones((len(KF_T), H // 8, W // 8))
    pose = np.zeros((len(KF_T), 7))
    pose[:, 6] = 1.0
    pose[~ok_kf] = np.nan
    meta = _save_traj(seg / "slam" / "R.npz", T_sc, tracked, kf_t=KF_T, kf_disp=disp, kf_pose_cw=pose,
                      size=(W, H), meta={"n_keyframes": len(KF_T), "runtime_s": 1.0})
    assert meta["n_tracked"] == N - len(UNTRACKED) and meta["masks_used"] == []
    (seg / "depth").mkdir()
    np.savez(seg / "depth" / "R_da2-metric-indoor-large.npz", kf_t=KF_T, depth=np.ones((len(KF_T), H, W), np.float16),
             model=np.array("depth-anything/x"))
    return k


def test_untracked_frames_end_to_end():
    from slam import evaluate as EV
    from slam import labels as L
    from slam import scale as SC
    from slam.pipeline import impl_analysis as IA
    with _work() as root:
        seg = root / "ep00"
        _untracked_segment(seg)
        z = B.load_output(seg / "slam" / "R.npz")
        assert np.isnan(z["T_slam_cam"][UNTRACKED]).all() and int(z["tracked"].sum()) == N - len(UNTRACKED)
        S = EV.load_segment(seg)
        T_sc = z["T_slam_cam"]
        # oracle scale: strict & tracked frames only
        s, res = EV.segment_scale(S, T_sc)
        assert abs(s - S_TRUE) < 1e-9 and res < 1e-9
        ok = z["tracked"]
        s2, _ = EV.segment_scale({**S, "strict": S["strict"] & ok}, np.where(ok[:, None, None], T_sc, 0.0))
        assert s2 == s                          # = the fit on the tracked frames only (bit-identical)
        r = SC.estimate(seg, "R", "tiles")
        assert r["ok"] and abs(r["s"] - S_TRUE) < 1e-9
        # A: windows use only tracked frames with a ball pose
        a = SC.estimate(seg, "R", "A")
        assert a["ok"] and abs(a["s"] - S_TRUE) < 1e-6 and a["accepted"] > 0, a
        assert all(w["n"] <= 30 for w in a["accepted_windows"]) and min(w["n"] for w in a["accepted_windows"]) < 30
        # B: the untracked keyframes (NaN pose, 10x inverse depth) are left out
        b = SC.estimate(seg, "R", "B", correction="disk", min_cells=10)
        assert b["ok"] and abs(b["s"] / S_TRUE - 1) < 1e-9 and len(b["s_per_keyframe"]) == 1, b
        # labels: SLAM labels have gaps where the run lost tracking; nothing raises
        T_bt = EV.load_tool_offset(SESSION)
        L.build_segment(seg, "tiles", "tiles", T_bt)
        m1 = L.build_segment(seg, "R", "tiles", T_bt)
        m2 = L.build_segment(seg, "R", "X", T_bt, scale=(S_TRUE, "X"))
        assert m1["keep"] and m2["keep"] and abs(m1["scale"] - S_TRUE) < 1e-9
        lab, tl = np.load(seg / "labels" / "R.npz"), np.load(seg / "labels" / "tiles.npz")
        ts = S["wall"][ok]
        far = np.abs(lab["t"][:, None] - ts[None]).min(1) > L.LABEL_TOL
        assert far.any() and np.array_equal(lab["gap"], far) and not tl["gap"].any()
        assert np.array_equal(np.load(seg / "labels" / "R@X.npz")["gap"], far)
        chk = L.check_labels(SESSION, "R")
        assert chk["anchors"] == int((~far).sum()) and chk["by_step"][1]["pos_mm_median"] < 1e-6
        # evaluate: untracked pairs are skipped by the statistics and count as tracking failures
        out = C.WORK / "eval"
        summ = EV.evaluate_session(SESSION, ["R"], out, dts=[0.08, 0.5])
        P = EV.pairs_for(S, 0.08)
        lost = np.isin(P, UNTRACKED).any(1)
        assert 0 < lost.sum() < len(P)
        R8 = summ["runs"]["R"]["by_dt"]["0.08"]
        assert R8["rot_err_deg"]["n"] == int((~lost).sum()) and R8["rot_err_deg"]["p95"] < 1e-4   # arccos precision
        assert summ["runs"]["R"]["track_fail_frac"] == lost.mean()
        saved = json.load(open(out / "summary.json"))
        assert saved["runs"]["R"]["track_fail_frac"] == lost.mean()
        assert abs(saved["segments"]["ep00"]["R"]["scale"] - S_TRUE) < 1e-9
        assert "rotation error > 2 deg" in (out / "summary.md").read_text()
        summ = EV.evaluate_session(SESSION, ["R"], C.WORK / "eval_s", scale_fn=lambda sg, rn, so: so * 1.1,
                                   dts=[0.08], fail_deg=5.0, scale_name="x")
        assert summ["runs"]["R"]["track_fail_frac"] == lost.mean()       # untracked fail at any threshold
        assert "rotation error > 5 deg" in (C.WORK / "eval_s" / "summary.md").read_text()
        facts = IA.slam_facts(SESSION, "R", ["ep00"])
        assert facts["tracked_frac"] == (N - len(UNTRACKED)) / N and facts["keyframes_per_segment"] == 3


# ---------------------------------------------------------------------- backend output validation
def test_backend_output_validation():
    n, size = 6, (24, 16)                                  # 1/8 grid: (2, 3)
    T = np.tile(np.eye(4), (n, 1, 1))
    tr = np.ones(n, bool)
    good = dict(kf_t=np.array([0, 3, 5]), kf_disp=np.ones((3, 2, 3), np.float32), kf_pose_cw=np.zeros((3, 7)))
    B.check_output(B.SlamOutput(T, tr, False, **good), n, size, ["a"])
    nan_disp = dict(good, kf_disp=np.full((3, 2, 3), np.nan))
    B.check_output(B.SlamOutput(T, tr, False, **nan_disp), n, size)                 # NaN = no depth: allowed
    B.check_output(B.SlamOutput(T, tr, False, kf_t=np.zeros(0, int), kf_disp=np.zeros((0, 2, 3))), n, size)
    B.check_output(B.SlamOutput(T, tr, False, meta={"masks_used": []}), n, size, ["a", "b"])
    bad = [dict(good, kf_t=np.array([0.0, 3.0, 5.0])),                               # not integers
           dict(good, kf_t=np.array([[0, 3, 5]])),                                   # not 1-D
           dict(good, kf_t=np.array([0, 3, 6])),                                     # out of [0, N)
           dict(good, kf_t=np.array([-1, 3, 5])),
           dict(good, kf_disp=np.ones((2, 2, 3))),                                   # M != len(kf_t)
           dict(good, kf_disp=np.ones((3, 3, 2))),                                   # wrong grid
           dict(good, kf_disp=np.ones((3, 2, 3), int)),                              # not float
           dict(good, kf_disp=np.concatenate([np.full((1, 2, 3), np.inf), np.ones((2, 2, 3))])),   # inf
           dict(good, kf_pose_cw=np.zeros((3, 6))),
           dict(good, kf_pose_cw=np.zeros((2, 7))),
           dict(kf_pose_cw=np.zeros((3, 7))),                                        # without kf_t
           dict(good, meta={"masks_used": ["c"]}),                                   # not a configured mask
           dict(good, meta={"masks_used": "a"})]
    for kw in bad:
        try:
            B.check_output(B.SlamOutput(T, tr, False, **kw), n, size, ["a", "b"])
        except ValueError:
            continue
        raise AssertionError(f"accepted {sorted(kw)}: {kw}")
    # save_output: masks_used defaults to the configured masks; a backend may report fewer
    with tempfile.TemporaryDirectory() as tmp:
        inp = B.SlamInput(images=[str(i) for i in range(n)], k=np.arange(n), t=np.arange(n) / 30.0, K=np.eye(3),
                          size=size, mask_names=["a", "b"])
        meta = B.save_output(Path(tmp) / "t.npz", B.SlamOutput(T, tr, False, **good), inp, "fake", {})
        assert meta["masks"] == ["a", "b"] and meta["masks_used"] == ["a", "b"]
        meta = B.save_output(Path(tmp) / "u.npz", B.SlamOutput(T, tr, False, meta={"masks_used": []}), inp, "fake", {})
        assert meta["masks"] == ["a", "b"] and meta["masks_used"] == []
        assert B.load_output(Path(tmp) / "u.npz")["meta"]["masks_used"] == []
        try:
            B.save_output(Path(tmp) / "v.npz", B.SlamOutput(T, tr, False, **dict(good, kf_disp=np.ones((3, 1, 1)))),
                          inp, "fake", {})
            raise AssertionError("save_output did not check the kf_disp grid against inp.size")
        except ValueError:
            pass


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
