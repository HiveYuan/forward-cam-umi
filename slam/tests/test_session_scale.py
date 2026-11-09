"""Session-level ball correction (scale method Bsession, exp005) on synthetic data
(python -m slam.tests.test_session_scale):

  - session_k: pooling of per-segment ball samples (median of the per-segment k, or of all
    samples), segments without samples, invalid pool;
  - method B unchanged by the refactor (ball samples / background ratio factored out): its full
    result equals a frozen copy of the pre-refactor code on synthetic segments, for both ball
    corrections, both fits, a depth window and explicit masks;
  - Bsession: s = median(k_session D_net / z_slam) recovers the true scale when k_session is the
    network's true correction, whatever the segment's own ball says, and works on a segment
    whose ball is never seen; s_own_k is B's s; failures are explicit;
  - the framework (impl_analysis.scale_run): k_session pooled over every segment first, passed to
    every segment, recorded under "session" (only for session methods); a check never changes s;
  - config: Bsession's config-facing parameters, exp005's config validates.
"""
import json
import tempfile
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G
from slam import scale as SC
from slam.tests import test_analysis as TA

N, W, H, F = 40, 192, 128, 150.0
KF_T = np.arange(2, N, 4)        # 10 keyframes
BIAS = 2.0                 # network over-estimates the background depth 2x (exact in float16)
BALL_PX = 12               # ball disk radius in the depth image / masks [px]


# ---------------------------------------------------------------------- synthetic segment
def _b_segment(seg, s_true=0.6, ball_bias=2.0, ball=True, seed=0):
    """Head moving in front of a static ball (0.45 m) and a background at 0.8-1.6 m (block-
    constant on DROID's 1/8 grid). Network depth = BIAS x true depth on the background and
    ball_bias x the ball centre's depth on the ball's disk; SLAM = world at scale 1/s_true with
    inverse depth s_true / z on the grid; the ball's disk is masked (masks/motion.npz); tile GT on
    every frame, ball poses on every frame (none with ball=False)."""
    rng = np.random.default_rng(seed)
    t = np.arange(N) / 30.0
    T_wc = G.rt_to_T(np.stack([0.03 * np.sin(2 * np.pi * t / 1.3), 0.04 * np.sin(2 * np.pi * t / 1.1 + 0.3),
                               0.01 * t], 1),
                     np.stack([0.06 * np.sin(2 * np.pi * t / 1.3), 0.03 * np.cos(2 * np.pi * t / 1.3), 0.02 * t], 1))
    T_wb = G.rt_to_T(np.array([0.3, -0.2, 0.1]), np.array([0.0, 0.0, 0.45]))[0]
    T_cb = G.inv(T_wc) @ T_wb
    seg.mkdir(parents=True)
    K = np.array([[F, 0, W / 2], [0, F, H / 2], [0, 0, 1]])
    json.dump({"frames": [{"i": i, "k": i, "wall": 100.0 + float(t[i]), "in_episode": True} for i in range(N)],
               "size": [W, H], "K": K.tolist(), "session": TA.SESSION,
               "episode": {"episode_index": 0, "t_start": 100.0, "t_end": 100.0 + float(t[-1])}},
              open(seg / "frames.json", "w"))
    rv = TA._rvec(T_cb[:, :3, :3])
    fk = np.arange(N) if ball else np.zeros(0, int)
    np.savez(seg / "gt.npz", cam_k=np.arange(N), T_cam_world=G.inv(T_wc), cam_tiles=np.full(N, 2),
             cam_rms=np.ones(N), full_k=fk, full_rvec=rv[fk], full_tvec=T_cb[fk, :3, 3])
    # background: metric depth per 1/8 cell, multiples of 1/256 m (exact in float16, also x BIAS)
    z_bg = np.round(rng.uniform(0.8, 1.6, size=(len(KF_T), H // 8, W // 8)) * 256) / 256
    uv = (K @ T_cb[:, :3, 3].T).T
    uv = uv[:, :2] / uv[:, 2:]
    yy, xx = np.mgrid[0:H, 0:W]
    disk = ((xx[None] - uv[:, 0, None, None]) ** 2 + (yy[None] - uv[:, 1, None, None]) ** 2) <= BALL_PX ** 2
    depth = np.repeat(np.repeat(BIAS * z_bg, 8, axis=1), 8, axis=2)
    for j, i in enumerate(KF_T):
        depth[j][disk[i]] = ball_bias * T_cb[i, 2, 3]
    (seg / "depth").mkdir()
    np.savez(seg / "depth" / "R_da2-metric-indoor-large.npz", kf_t=KF_T, depth=depth.astype(np.float16),
             model=np.array("depth-anything/x"))
    (seg / "masks").mkdir()
    np.savez(seg / "masks" / "motion.npz", masked=np.packbits(disk, axis=-1))
    G0 = G.rt_to_T(np.array([0.2, 0.1, -0.3]), np.array([0.3, -0.1, 0.2]))[0]          # world -> SLAM
    T_sc = G0[None] @ T_wc
    T_sc[:, :3, 3] /= s_true
    pose = np.zeros((len(KF_T), 7))
    pose[:, 6] = 1.0
    TA._save_traj(seg / "slam" / "R.npz", T_sc, np.ones(N, bool), kf_t=KF_T, kf_disp=s_true / z_bg,
                  kf_pose_cw=pose, size=(W, H), mask_names=["motion"], meta={"n_keyframes": len(KF_T)})
    return seg


def _same(a, b):
    """Equal results (dicts/lists/floats; NaN == NaN), bit for bit."""
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return isinstance(b, (list, tuple)) and len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
        return True
    return type(a) is type(b) and a == b


# ---------------------------------------------------------------------- frozen pre-refactor B
def _legacy_scale_depth_ball(seg, run, model="da2-metric-indoor-large", correction="faces", min_facing=0.7,
                             fit="scale", min_affine_range=0.15, depth_window=None, z_max=4.0, min_cells=200,
                             mask_names=None, mask_dilate_px=8, **_):
    """slam.scale.scale_depth_ball as of commit 131f614 (before exp005 factored it), verbatim."""
    dp = seg / "depth" / f"{run}_{model}.npz"
    if not dp.exists():
        return {"s": float("nan"), "ok": False, "error": f"missing {dp} (run slam.depth)"}
    D = np.load(dp)
    S = SC._segment(seg)
    z, meta = SC._run(seg, run)
    fj = json.load(open(seg / "frames.json"))
    K = np.array(fj["K"])
    W, H = fj["size"]
    kf_t, disp = z["kf_t"], z["kf_disp"].astype(float)
    if not np.array_equal(D["kf_t"], kf_t):
        return {"s": float("nan"), "ok": False, "error": "depth cache is for other keyframes"}
    T_sc = z["T_slam_cam"]
    kf_ok = np.isfinite(T_sc[kf_t]).all((1, 2))
    if "kf_pose_cw" in z.files:
        kf_ok &= np.isfinite(z["kf_pose_cw"]).all(1)
    names = meta.get("masks", []) if mask_names is None else list(mask_names)
    valid = SC._valid_cells(seg, names, len(fj["frames"]), (W, H), mask_dilate_px)
    pairs = []
    faces = SC.ball_faces(fj["session"]) if correction == "faces" else None
    for j, i in enumerate(kf_t):
        if not np.isfinite(S["T_cb"][i, 0, 0]):
            continue
        dn = D["depth"][j].astype(float)
        Tcb = S["T_cb"][i]
        if faces is not None:
            Pc = (Tcb[:3, :3] @ faces[0].T).T + Tcb[:3, 3]
            nc = (Tcb[:3, :3] @ faces[1].T).T
            facing = (nc * -Pc / np.linalg.norm(Pc, axis=1, keepdims=True)).sum(1) >= min_facing
            for P in Pc[facing]:
                u, v, w_ = K @ P
                u, v = int(round(u / w_)), int(round(v / w_))
                if 2 <= u < W - 2 and 2 <= v < H - 2:
                    pairs.append((np.median(dn[v - 1:v + 2, u - 1:u + 2]), P[2], int(i)))
        else:
            b = Tcb[:3, 3]
            u, v, w_ = K @ b
            u, v = u / w_, v / w_
            r = 0.6 * K[0, 0] * SC.BALL_R / b[2]
            if 0 <= u < W and 0 <= v < H and r >= 2:
                yy, xx = np.mgrid[0:H, 0:W]
                disk = (xx - u) ** 2 + (yy - v) ** 2 <= r ** 2
                pairs.append((np.median(dn[disk]), b[2] - SC.BALL_R, int(i)))
    if not pairs:
        return {"s": float("nan"), "ok": False, "error": "ball never visible in a keyframe"}
    pr = np.array([(d, zt) for d, zt, _ in pairs])
    k = float(np.median(pr[:, 1] / pr[:, 0]))
    alpha, beta, fit_used = k, 0.0, "scale"
    if fit == "affine" and len(pr) >= 10 and np.ptp(pr[:, 1]) >= min_affine_range:
        ii, jj = np.triu_indices(len(pr), 1)
        dd = pr[jj, 0] - pr[ii, 0]
        ok = np.abs(dd) > 1e-3
        alpha = float(np.median((pr[jj, 1] - pr[ii, 1])[ok] / dd[ok]))
        beta = float(np.median(pr[:, 1] - alpha * pr[:, 0]))
        fit_used = "affine"
    z_ball = {int(i): float(S["T_cb"][i, 2, 3]) for i in kf_t if np.isfinite(S["T_cb"][i, 0, 0])}
    zb_med = float(np.median(list(z_ball.values()))) if z_ball else np.nan
    ratios, per_kf = [], []
    for j, i in enumerate(kf_t):
        if not kf_ok[j]:
            continue
        d8 = D["depth"][j].astype(float).reshape(H // 8, 8, W // 8, 8).mean((1, 3))
        zc = alpha * d8 + beta
        zs = 1.0 / np.clip(disp[j], 1e-6, None)
        m = valid[i] & np.isfinite(zc) & (zc > 0.1) & (zc < z_max) & (disp[j] > 1e-3) & np.isfinite(disp[j])
        if depth_window:
            m &= np.abs(zc / z_ball.get(int(i), zb_med) - 1) <= depth_window
        m[:1], m[-1:], m[:, :1], m[:, -1:] = False, False, False, False
        if m.sum() < min_cells:
            continue
        per_kf.append(SC.depth_ratio_scale(1.0, zc, zs, m))
        ratios.append(zc[m] / zs[m])
    if not per_kf:
        return {"s": float("nan"), "ok": False, "error": "no keyframe with enough valid background"}
    s = float(np.median(np.concatenate(ratios)))
    return {"s": s, "ok": True, "k_ball": k, "ball_samples": len(pr), "ball_depth_range_m": float(np.ptp(pr[:, 1])),
            "fit": fit_used, "alpha": alpha, "beta": beta, "s_per_keyframe": per_kf, "model": model,
            "correction": correction, "depth_window": depth_window}


# ---------------------------------------------------------------------- session_k (pure)
def test_session_k_pooling():
    rng = np.random.default_rng(3)
    samples = {}
    for name, k, n in (("ep00", 0.50, 5), ("ep01", 0.55, 40), ("ep02", 0.62, 9), ("ep03", None, 0)):
        d = rng.uniform(0.6, 1.2, size=n)
        samples[name] = np.stack([d, k * d * rng.uniform(0.9, 1.1, size=n)], 1) if n else np.zeros((0, 2))
    seg_k = {s: float(np.median(p[:, 1] / p[:, 0])) for s, p in samples.items() if len(p)}
    r = SC.session_k(samples)                                    # default: median of per-segment k
    assert r["pool"] == "segments" and r["k_session"] == float(np.median(list(seg_k.values())))
    assert r["n_segments"] == 3 and r["n_samples"] == 54
    assert all(r["per_segment"][s] == {"k": seg_k[s], "n": len(samples[s])} for s in seg_k)
    assert np.isnan(r["per_segment"]["ep03"]["k"]) and r["per_segment"]["ep03"]["n"] == 0
    assert r["k_segment_p10"] < r["k_segment_p25"] < r["k_segment_p75"] < r["k_segment_p90"]
    rs = SC.session_k(samples, "samples")                        # all samples pooled: ep01 dominates
    allr = np.concatenate([p[:, 1] / p[:, 0] for p in samples.values() if len(p)])
    assert rs["k_session"] == float(np.median(allr)) and abs(rs["k_session"] - 0.55) < 0.02
    assert SC.session_k({"a": [[1.0, 0.5]], "b": [[2.0, 1.2]], "c": [[1.0, 0.7]]})["k_session"] == 0.6
    empty = SC.session_k({"ep00": np.zeros((0, 2))})
    assert np.isnan(empty["k_session"]) and empty["n_segments"] == 0 and np.isnan(empty["k_segment_p10"])
    for bad in ("mean", "segment"):
        try:
            SC.session_k(samples, bad)
            raise AssertionError(f"pool {bad!r} accepted")
        except ValueError:
            pass


# ---------------------------------------------------------------------- B unchanged
def test_b_bit_identical_to_pre_refactor():
    variants = [{}, {"correction": "disk"}, {"fit": "affine", "min_affine_range": 0.0},
                {"depth_window": 1.2, "min_cells": 20}, {"mask_names": ["motion"], "mask_dilate_px": 4},
                {"min_cells": 100000}, {"min_facing": 0.95}]
    with TA._work() as root:
        segs = [_b_segment(root / "ep00", 0.6, 1.7, seed=1), _b_segment(root / "ep01", 0.45, 2.3, seed=2),
                _b_segment(root / "ep02", 0.7, 2.0, ball=False, seed=3)]
        n_ok = 0
        for seg in segs:
            for kw in variants:
                new, old = SC.scale_depth_ball(seg, "R", **kw), _legacy_scale_depth_ball(seg, "R", **kw)
                assert _same(new, old), (seg.name, kw, new, old)
                n_ok += new["ok"]
        assert n_ok == 2 * (len(variants) - 1)                   # ep02: no ball; min_cells 100000: no cells
        assert SC.scale_depth_ball(segs[2], "R")["error"] == "ball never visible in a keyframe"
        # through the cached interface too
        r = SC.estimate(segs[0], "R", "B", cache=False)
        assert r["method"] == "B" and _same({k: v for k, v in r.items() if k not in ("method", "provenance")},
                                            _legacy_scale_depth_ball(segs[0], "R"))


# ---------------------------------------------------------------------- Bsession
def test_bsession_recovers_scale_with_true_k():
    """k_session = the network's true background correction (1/BIAS) gives the true scale on
    every segment, whatever its own ball says (ball_bias != BIAS) and with no ball at all."""
    with TA._work() as root:
        cases = [("ep00", 0.6, 1.6, True), ("ep01", 0.45, 2.6, True), ("ep02", 0.7, 2.0, False)]
        for name, s_true, bb, ball in cases:
            seg = _b_segment(root / name, s_true, bb, ball=ball, seed=len(name) + int(name[-1]))
            r = SC.estimate(seg, "R", "Bsession", k_session=1 / BIAS, min_cells=50)
            assert r["ok"] and r["method"] == "Bsession" and abs(r["s"] / s_true - 1) < 1e-12, (name, r)
            assert r["k_session"] == 1 / BIAS and r["pool"] == "segments"
            assert len(r["s_per_keyframe"]) == len(KF_T)
            b = SC.scale_depth_ball(seg, "R", min_cells=50)
            if ball:
                # own k from the ball (~1/ball_bias, the face centres ~4% nearer than the centre):
                # s_own_k is B's s = BIAS k_own s_true, off by ~BIAS/ball_bias
                assert r["k_ball"] == b["k_ball"] and r["ball_samples"] == b["ball_samples"] > 0
                assert 0.9 < r["k_ball"] * bb < 1.0
                assert r["s_own_k"] == b["s"] and abs(r["s_own_k"] / (BIAS * r["k_ball"] * s_true) - 1) < 1e-12
            else:
                assert not b["ok"] and np.isnan(r["k_ball"]) and r["ball_samples"] == 0 and np.isnan(r["s_own_k"])
            # s is linear in k_session (no depth window; corrected depths stay inside (0.1, z_max))
            r2 = SC.scale_depth_ball_session(seg, "R", k_session=0.8 / BIAS, min_cells=50)
            assert abs(r2["s"] / (0.8 * s_true) - 1) < 1e-12


def test_bsession_failures():
    with TA._work() as root:
        seg = _b_segment(root / "ep00")
        for ks in (None, float("nan"), 0.0, -0.5):
            r = SC.scale_depth_ball_session(seg, "R", k_session=ks)
            assert not r["ok"] and np.isnan(r["s"]) and "k_session" in r["error"], ks
        r = SC.estimate(seg, "R", "Bsession")                  # legacy interface without the framework
        assert not r["ok"] and not (seg / "scale").exists()     # failures are not cached
        r = SC.scale_depth_ball_session(seg, "R", k_session=0.5, min_cells=100000)
        assert not r["ok"] and r["error"] == "no keyframe with enough valid background"
        r = SC.scale_depth_ball_session(seg, "R", k_session=0.5, model="depth-pro")
        assert not r["ok"] and "missing" in r["error"]
        for kw in ({"pool": "mean"}, {"correction": "face"}):
            try:
                SC.scale_depth_ball_session(seg, "R", k_session=0.5, **kw)
                raise AssertionError(f"accepted {kw}")
            except ValueError:
                pass
        # ball_samples: the same samples B takes its k from; none without ball poses
        bs = SC.ball_samples(seg, "R")
        assert bs["ok"] and bs["n"] == len(bs["pairs"]) == len(bs["frames"]) > 0
        assert bs["k"] == SC.scale_depth_ball(seg, "R")["k_ball"] and set(bs["frames"]) <= set(KF_T.tolist())
        nob = SC.ball_samples(_b_segment(root / "ep01", ball=False), "R")
        assert not nob["ok"] and nob["n"] == 0 and nob["pairs"].shape == (0, 2) and np.isnan(nob["k"])


def test_bsession_cache_keyed_by_k_session():
    with TA._work() as root:
        seg = _b_segment(root / "ep00")
        r1 = SC.estimate(seg, "R", "Bsession", k_session=0.5, min_cells=50)
        r2 = SC.estimate(seg, "R", "Bsession", k_session=0.4, min_cells=50)
        assert abs(r2["s"] / r1["s"] - 0.8) < 1e-12 and len(list((seg / "scale").glob("R_Bsession_*.json"))) == 2
        assert SC.estimate(seg, "R", "Bsession", k_session=0.5, min_cells=50)["s"] == r1["s"]
        assert r1["provenance"]["params"]["k_session"] == 0.5
        assert any(f.name == "R_da2-metric-indoor-large.npz" for f in [seg / "depth" / n for n in
                                                                       r1["provenance"]["upstream"]])


# ---------------------------------------------------------------------- framework
S_TRUE = {"ep00": 0.6, "ep01": 0.45, "ep02": 0.7, "ep03": 0.5}
BALL_BIAS = {"ep00": 1.6, "ep01": 2.6, "ep02": 2.1, "ep03": None}          # ep03: ball never seen
BS_PARAMS = {"depth": "da2", "correction": "faces", "min_facing": 0.7, "pool": "segments", "depth_window": None,
             "z_max": 4.0, "min_cells": 50, "_depth_node": "depth.da2@R"}


def _bs_analysis(primary="Bsession", checks=("A",)):
    methods = {"Bsession": dict(BS_PARAMS), "A": {"knob": 2},
               "B": {"depth": "da2", "correction": "faces", "min_facing": 0.7, "fit": "scale",
                     "min_affine_range": 0.15, "depth_window": None, "z_max": 4.0, "min_cells": 50,
                     "_depth_node": "depth.da2@R"}}
    used = [primary] + list(checks)
    return {"slam_runs": {"R": {"masks": ["motion"], "dilate_px": 8}},
            "scale": {"R": {"primary": primary, "checks": list(checks), "flag_threshold": 0.10 if checks else None,
                            "methods": {m: methods[m] for m in used}}}}


def _bs_segments(root):
    for i, (name, s) in enumerate(S_TRUE.items()):
        bb = BALL_BIAS[name]
        _b_segment(root / name, s, 2.0 if bb is None else bb, ball=bb is not None, seed=10 + i)


def test_scale_run_session_k():
    from slam.pipeline import impl_analysis as IA
    segs = sorted(S_TRUE)
    with TA._work() as root, TA._methods({"A": TA._stub({s: 0.5 for s in segs}, [], "A")}):
        _bs_segments(root)
        own = {s: SC.ball_samples(root / s, "R")["k"] for s in segs}
        assert np.isnan(own["ep03"]) and all(np.isfinite(own[s]) for s in segs[:3])
        k_sess = float(np.median([own[s] for s in segs[:3]]))
        out = C.WORK / "results"
        out.mkdir()
        job = TA._job(out, segs, _bs_analysis(), inputs=TA.DEPTH_INPUTS)
        res = IA.scale_run(job, "R", job.analysis["scale"]["R"])
        assert res["label"] == "Bsession+Acheck" and set(res["session"]) == {"Bsession"}
        sk = res["session"]["Bsession"]
        assert sk["k_session"] == k_sess and sk["pool"] == "segments" and sk["n_segments"] == 3
        assert {s: v["k"] for s, v in sk["per_segment"].items()} == {s: (None if s == "ep03" else own[s]) for s in segs}
        for r in res["rows"]:
            s, p = r["segment"], r["primary"]
            # every segment (ep03 without a ball too) gets k_session: s = 2 k_session s_true exactly
            assert r["ok"] and p["k_session"] == k_sess and abs(r["s"] / (BIAS * k_sess * S_TRUE[s]) - 1) < 1e-12, r
            assert abs(r["err"] - (r["s"] / r["oracle_s"] - 1)) < 1e-15 and abs(r["oracle_s"] / S_TRUE[s] - 1) < 1e-9
            assert (p["k_ball"] is None) == (s == "ep03") and (p["k_ball"] is None or p["k_ball"] == own[s])
        # B on the same segments: s_own_k is B's s; B fails where the ball is never seen
        bres = IA.scale_run(job, "R", _bs_analysis("B", [])["scale"]["R"])
        assert "session" not in bres                              # non-session runs: unchanged keys
        for rb, rs in zip(bres["rows"], res["rows"]):
            assert rb["s"] == rs["primary"]["s_own_k"]
        assert [r["ok"] for r in bres["rows"]] == [True, True, True, False]
        # the stored files
        IA.run_scale(job)
        sj = json.load(open(out / "scale_R.json"))
        assert sj["session"]["Bsession"]["k_session"] == k_sess and sj["summary"]["segments_ok"] == 4
        md = (out / "scale_R.md").read_text()
        assert "## Session ball correction (Bsession)" in md and f"k_session = {k_sess:.4f}" in md
        assert md.count("| ep0") == 2 * len(segs)                # main table + per-segment session table


def _clear_scale_caches(root, segs):
    import shutil
    for s in segs:
        shutil.rmtree(root / s / "scale", ignore_errors=True)


def test_session_check_never_changes_s():
    """Bsession primary: whatever check A returns, s, ok and err are Bsession's; Bsession as a
    check gets k_session too and only flags."""
    from slam.pipeline import impl_analysis as IA
    segs = sorted(S_TRUE)
    variants = {"fails": {s: None for s in segs}, "agrees": None, "wild": {"ep00": 9.0, "ep01": 0.01, "ep02": None,
                                                                          "ep03": 3.0}}
    rows = {}
    with TA._work() as root:
        _bs_segments(root)
        for name, sa in variants.items():
            _clear_scale_caches(root, segs)                      # successes are cached: start clean
            table = sa if sa is not None else {s: 0.5 for s in segs}
            with TA._methods({"A": TA._stub(table, [], "A")}):
                job = TA._job(C.WORK, segs, _bs_analysis(), inputs=TA.DEPTH_INPUTS)
                rows[name] = IA.scale_run(job, "R", job.analysis["scale"]["R"])["rows"]
        _clear_scale_caches(root, segs)
        with TA._methods({"A": TA._stub({s: 0.5 for s in segs}, [], "A")}):
            job = TA._job(C.WORK, segs, _bs_analysis("A", ["Bsession"]), inputs=TA.DEPTH_INPUTS)
            as_check = IA.scale_run(job, "R", job.analysis["scale"]["R"])
    ref = [(r["segment"], r["s"], r["ok"], r["err"]) for r in rows["fails"]]
    for name, rr in rows.items():
        assert [(r["segment"], r["s"], r["ok"], r["err"]) for r in rr] == ref, name
    assert not any(r["flagged"] for r in rows["fails"])
    assert [r["segment"] for r in rows["wild"] if r["flagged"]] == ["ep00", "ep01", "ep03"]
    assert set(as_check["session"]) == {"Bsession"} and all(r["s"] == 0.5 for r in as_check["rows"])
    for r, ro in zip(as_check["rows"], rows["fails"]):
        assert r["checks"]["Bsession"]["s"] == ro["s"] and abs(r["checks"]["Bsession"]["diff"] - (ro["s"] / 0.5 - 1)) < 1e-15


# ---------------------------------------------------------------------- config
def test_config_parameters():
    from slam.pipeline import spec as SP
    assert "k_session" in SP.SCALE_FRAMEWORK_KW and SC.SESSION_METHODS == {"Bsession": "k_session"}
    assert "Bsession" in SC.TAKES_MODEL and "Bsession" not in SC.COMPOSITE_METHODS
    d = SP.scale_method_defaults()["Bsession"]
    assert d == {"depth": "", "correction": "faces", "min_facing": 0.7, "pool": "segments", "depth_window": None,
                 "z_max": 4.0, "min_cells": 200}
    p = Path(__file__).resolve().parents[2] / "experiments" / "exp005_session_scale" / "config.yaml"
    if p.exists():
        import yaml
        cfg = yaml.safe_load(open(p))
        _, an = SP.build(cfg)
        for run in ("E3", "E2"):
            blk = an["scale"][run]
            assert blk["primary"] == "Bsession" and blk["checks"] == ["A"]
            assert blk["methods"]["Bsession"]["_depth_node"] == f"depth.da2@{run}"
            assert {k: v for k, v in blk["methods"]["Bsession"].items() if k != "_depth_node"} == {**d, "depth": "da2"}


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
