"""Synthetic checks of the scale methods' core math (python -m slam.tests.test_scale)."""
import numpy as np

from slam import geometry as G
from slam import scale as SC


def test_static_point_recovers_scale():
    rng = np.random.default_rng(0)
    s_true, p = 0.63, np.array([0.1, -0.2, 0.5])
    T = G.rt_to_T(rng.normal(scale=0.2, size=(25, 3)), rng.normal(scale=0.05, size=(25, 3)))
    c = T[:, :3, 3]                                        # unscaled SLAM centres
    R = T[:, :3, :3]
    b = (np.swapaxes(R, 1, 2) @ (p - s_true * c)[..., None])[..., 0]    # ball in the camera (metric)
    s, p_hat, res = SC.fit_static_point((R @ b[..., None])[..., 0], c)
    assert abs(s - s_true) < 1e-9 and np.allclose(p_hat, p) and res.max() < 1e-9


def test_static_point_noise_and_moving_point():
    rng = np.random.default_rng(1)
    T = G.rt_to_T(rng.normal(scale=0.2, size=(25, 3)), rng.normal(scale=0.05, size=(25, 3)))
    R, c = T[:, :3, :3], T[:, :3, 3]
    p = np.array([0.1, -0.2, 0.5])
    b = (np.swapaxes(R, 1, 2) @ (p - 0.63 * c)[..., None])[..., 0] + rng.normal(scale=1e-3, size=(25, 3))
    s, _, res = SC.fit_static_point((R @ b[..., None])[..., 0], c)
    assert abs(s / 0.63 - 1) < 0.05 and np.sqrt((res ** 2).mean()) < 3e-3
    moving = p + np.linspace(0, 0.05, 25)[:, None] * np.array([1.0, 0, 0])     # 5 cm drift
    b2 = (np.swapaxes(R, 1, 2) @ (moving - 0.63 * c)[..., None])[..., 0]
    _, _, res2 = SC.fit_static_point((R @ b2[..., None])[..., 0], c)
    assert np.sqrt((res2 ** 2).mean()) > 5e-3                                # rejected by the residual gate


def test_depth_ratio_scale():
    rng = np.random.default_rng(2)
    z_metric = rng.uniform(0.5, 2.0, size=(67, 120))
    s_true, bias = 0.7, 1.8                                  # network over-estimates depth by 1.8x
    z_slam = z_metric / s_true
    d_net = bias * z_metric
    valid = rng.uniform(size=z_metric.shape) > 0.3
    assert abs(SC.depth_ratio_scale(1 / bias, d_net, z_slam, valid) - s_true) < 1e-9


def test_registry_and_specs():
    assert {"none", "tiles", "A", "B"} <= set(SC.METHODS)



# ---------------------------------------------------------------- interface: specs, chains, cache
def _stub_segment(tmp):
    from pathlib import Path
    seg = Path(tmp) / "ep00"
    (seg / "slam").mkdir(parents=True)
    (seg / "slam" / "R.npz").write_bytes(b"x")
    (seg / "gt.npz").write_bytes(b"x")
    return seg


def _with_stubs(fn):
    import tempfile
    calls = []
    saved = dict(SC.METHODS)

    def stub(name, ok, s):
        def f(seg, run, model="default", knob=1, **_):
            calls.append((name, model, knob))
            return {"s": s if ok else float("nan"), "ok": ok}
        return f
    SC.METHODS.update({"A": stub("A", False, 0.5), "B": stub("B", True, 0.7), "none": stub("none", True, 1.0)})
    try:
        with tempfile.TemporaryDirectory() as tmp:
            fn(_stub_segment(tmp), calls)
    finally:
        SC.METHODS.clear()
        SC.METHODS.update(saved)


def test_chain_fallback_and_failures_not_cached():
    def body(seg, calls):
        r = SC.estimate(seg, "R", "A,B")
        assert r["ok"] and r["s"] == 0.7 and r["method"] == "B" and [c[0] for c in calls] == ["A", "B"]
        assert not (seg / "scale" / "R_A.json").exists() and (seg / "scale" / "R_B.json").exists()
        calls.clear()
        SC.estimate(seg, "R", "A,B")                      # A recomputed (failure not cached), B cached
        assert [c[0] for c in calls] == ["A"]
        assert np.isnan(SC.get_scale(seg, "R", "A"))
    _with_stubs(body)


def test_options_params_and_invalidation():
    import os
    import time

    def body(seg, calls):
        SC.estimate(seg, "R", "B:depth-pro")
        assert calls[-1] == ("B", "depth-pro", 1) and (seg / "scale" / "R_B-depth-pro.json").exists()
        SC.estimate(seg, "R", "B", knob=3)                # non-default parameters: own cache file
        assert calls[-1] == ("B", "default", 3)
        n = len(calls)
        SC.estimate(seg, "R", "B")                        # default cache untouched by the knob=3 run
        assert len(calls) == n + 1 and calls[-1] == ("B", "default", 1)
        SC.estimate(seg, "R", "B")
        assert len(calls) == n + 1                        # now cached
        time.sleep(0.01)
        os.utime(seg / "slam" / "R.npz")                  # upstream changed -> recompute
        SC.estimate(seg, "R", "B")
        assert len(calls) == n + 2
        for bad in ("A:depth-pro", "B:nope", "Z"):
            try:
                SC.estimate(seg, "R", bad)
                raise AssertionError(f"{bad} accepted")
            except (ValueError, KeyError):
                pass
    _with_stubs(body)


def test_b_primary_with_a_check():
    """B+Acheck: s is always B's; A only sets ab_diff/flagged, never s or ok."""
    import tempfile
    saved = dict(SC.METHODS)
    try:
        for sa, a_ok, expect_flag in ((0.80, True, True), (0.72, True, False), (0.5, False, False)):
            SC.METHODS.update({"A": lambda seg, run, sa=sa, a_ok=a_ok, **_: {"s": sa if a_ok else float("nan"), "ok": a_ok},
                               "B": lambda seg, run, **_: {"s": 0.70, "ok": True}})
            with tempfile.TemporaryDirectory() as tmp:
                seg = _stub_segment(tmp)
                (seg / "depth").mkdir()
                r = SC.estimate(seg, "R", "B+Acheck")
                assert r["ok"] and r["s"] == 0.70 and r["flagged"] == expect_flag
                assert (r["ab_diff"] is None) == (not a_ok)
    finally:
        SC.METHODS.clear()
        SC.METHODS.update(saved)


# ---------------------------------------------------------------- cross_check, native, framework kwargs
def _same(a, b):
    return (np.isnan(a) and np.isnan(b)) or a == b


def test_cross_check_flags_never_change_s():
    ok = lambda s: {"s": s, "ok": True}                                   # noqa: E731
    bad = {"s": float("nan"), "ok": False, "error": "x"}
    cases = [  # primary, checks, threshold, expected flagged_by, expected diffs
        (ok(0.70), {"A": ok(0.80)}, 0.10, ["A"], {"A": 0.80 / 0.70 - 1}),
        (ok(0.70), {"A": ok(0.72)}, 0.10, [], {"A": 0.72 / 0.70 - 1}),
        (ok(0.70), {"A": ok(0.60)}, 0.10, ["A"], {"A": 0.60 / 0.70 - 1}),    # negative diff
        (bad, {"A": ok(0.80)}, 0.10, [], {"A": None}),                       # failing primary
        (ok(0.70), {"A": bad}, 0.10, [], {"A": None}),                       # failing check
        (ok(0.70), {"A": ok(0.90), "C": ok(0.71)}, 0.10, ["A"], {"A": 0.90 / 0.70 - 1, "C": 0.71 / 0.70 - 1}),
        (ok(0.70), {"A": ok(0.50), "C": ok(0.95)}, 0.10, ["A", "C"], {"A": 0.50 / 0.70 - 1, "C": 0.95 / 0.70 - 1}),
        (ok(0.70), {"A": ok(0.90)}, None, [], {"A": 0.90 / 0.70 - 1}),       # no threshold: record only
        (ok(0.70), {}, 0.10, [], {}),                                        # no checks
    ]
    for primary, checks, thr, flagged_by, diffs in cases:
        r = SC.cross_check(primary, checks, thr)
        assert _same(r["s"], primary["s"]) and r["ok"] == primary["ok"], (primary, checks, r)
        assert r["flagged_by"] == flagged_by and r["flagged"] == bool(flagged_by), (checks, r)
        assert set(r["checks"]) == set(checks)
        for name, d in diffs.items():
            c = r["checks"][name]
            assert c["ok"] == checks[name]["ok"] and _same(c["s"], checks[name]["s"])
            assert (c["diff"] is None) if d is None else abs(c["diff"] - d) < 1e-15, (name, c, d)


def test_b_with_a_check_keys_and_values():
    """B+Acheck keeps its legacy output keys; its values follow cross_check."""
    import tempfile
    saved = dict(SC.METHODS)
    try:
        SC.METHODS.update({"A": lambda seg, run, **_: {"s": 0.80, "ok": True},
                           "B": lambda seg, run, **_: {"s": 0.70, "ok": True}})
        with tempfile.TemporaryDirectory() as tmp:
            seg = _stub_segment(tmp)
            r = SC.estimate(seg, "R", "B+Acheck", cache=False)
        assert set(r) == {"s", "ok", "s_B", "B_ok", "s_A", "A_ok", "threshold", "ab_diff", "flagged", "model", "method", "provenance"}
        assert r["s"] == r["s_B"] == 0.70 and r["s_A"] == 0.80 and r["ab_diff"] == 0.80 / 0.70 - 1 and r["flagged"]
    finally:
        SC.METHODS.clear()
        SC.METHODS.update(saved)


def test_native():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        for name, extra, expect in (("M", {"metric": np.array(True)}, True),
                                    ("U", {"metric": np.array(False)}, False),
                                    ("L", {}, False)):                 # legacy traj.npz: no 'metric' key
            seg = Path(tmp) / name
            (seg / "slam").mkdir(parents=True)
            np.savez(seg / "slam" / "R.npz", k=np.arange(3), T_slam_cam=np.tile(np.eye(4), (3, 1, 1)), **extra)
            (seg / "gt.npz").write_bytes(b"x")
            r = SC.estimate(seg, "R", "native")
            assert r["ok"] == expect and r["method"] == "native"
            assert r["s"] == 1.0 if expect else (np.isnan(r["s"]) and "error" in r)
            assert (seg / "scale" / "R_native.json").exists() == expect      # failures are not cached


def test_registry_composites_and_framework_kwargs():
    from slam.pipeline import spec as SP
    assert "native" in SC.METHODS and SC.COMPOSITE_METHODS == ("B+Acheck",)
    d = SP.scale_method_defaults()
    assert "B+Acheck" not in d and d["native"] == {} and d["none"] == {}
    assert d["B"]["depth"] == "" and not {"model", "mask_names", "mask_dilate_px"} & set(d["B"])
    import inspect
    p = inspect.signature(SC.scale_depth_ball).parameters
    assert p["mask_names"].default is None and p["mask_dilate_px"].default == 8


def test_provenance_of_mask_kwargs():
    """mask_names/mask_dilate_px at their defaults leave the provenance as before they existed
    (old caches stay valid); other values are recorded (and invalidate)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        seg = _stub_segment(tmp)
        p0 = SC._provenance(seg, "R", "B", {})["params"]
        assert "mask_names" not in p0 and "mask_dilate_px" not in p0 and p0["min_cells"] == 200
        assert SC._provenance(seg, "R", "B", {"mask_names": None, "mask_dilate_px": 8})["params"] == p0
        p1 = SC._provenance(seg, "R", "B", {"mask_names": ["motion"], "mask_dilate_px": 4})["params"]
        assert p1["mask_names"] == ["motion"] and p1["mask_dilate_px"] == 4


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
