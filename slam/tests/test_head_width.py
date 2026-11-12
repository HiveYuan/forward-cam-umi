"""slam.head_width without data (python -m slam.tests.test_head_width; CPU)."""
import numpy as np

from slam import head_width as H


def test_width_map_inverse():
    wm = H.WidthMap()
    x = np.linspace(wm.xi[0], wm.xi[-1], 200)
    c = wm.to_cmd(x)
    inner = (c > wm.y_lo + 2e-3) & (c < wm.y_hi - 2e-3)          # clear of the censoring band (1e-3 in command)
    assert inner.sum() > 100 and np.allclose(wm.to_width(c[inner]), x[inner])
    assert np.isnan(wm.to_width(c[c >= wm.y_hi - 5e-4])).all()   # the near-flat top (0.998..0.9985) is censored
    cmd = np.array([wm.y_lo, wm.y_lo + 0.0005, wm.y_hi, 1.0, 0.5])
    w = wm.to_width(cmd)
    assert np.isnan(w[:4]).all() and np.isfinite(w[4])       # flat ends censored, interior invertible


def test_fit_predict_synthetic():
    """A tail moving along a fixed body-frame axis with the width, a fixed base: the estimators recover the width."""
    rng = np.random.default_rng(0)
    n = 2000
    w = rng.uniform(0.1, 0.9, n)
    axis = np.array([0.6, 0.0, 0.8])
    base = np.array([-80.0, -30.0, 60.0])
    tail = base + np.array([5.0, 10.0, 0.0]) + 45.0 * w[:, None] * axis + rng.normal(0, 0.3, (n, 3))
    ids = np.array([36, 40])
    pos = np.stack([tail, np.tile(base, (n, 1)) + rng.normal(0, 0.3, (n, 3))], 1)
    pos[::7, 0] = np.nan                                     # tail not localised in some frames
    t = 1000.0 + np.arange(n) * 0.04
    rows = H.rows_from(t, ids, pos)
    assert 36 not in rows[0]["pb"] and 40 in rows[0]["pb"] and 36 in rows[1]["pb"]
    ests = H.L.fit_estimators(rows, t, w, tails={36: 12.18}, bases={40: 12.18}, singles=[], meas_tol=1e-6,
                              verbose=False)
    assert list(ests) == ["pair:36-40"]
    pred, used = H.predict_widths(rows, ests)
    assert np.isnan(pred[::7]).all() and (used[1::7] == 1).all()
    ok = np.isfinite(pred)
    assert np.median(np.abs(pred[ok] - w[ok])) < 0.01


def test_score_coverage():
    pred = np.array([0.3, np.nan, 0.5, 0.2, np.nan, 0.9])
    ref = np.array([0.3, 0.4, 0.4, 0.2, 0.5, 0.5])
    s = H.score(pred, ref, np.array([1, 1, 1, 0, 0, 0], bool))
    assert s["frames"] == 2 and abs(s["coverage"] - 2 / 3) < 1e-12
    assert abs(s["gate_agreement"] - 0.5) < 1e-12           # 0.5 vs 0.4 straddles the 0.45 gate


def test_holds_log_and_sparse_fit():
    """A width-holds log in raw mm (record_session --width_holds): converted by gap_to_actuator, and only frames
    within 0.3 s of a hold enter the fit (frames in transit between holds would get interpolated ramp values)."""
    import json
    import tempfile
    rng = np.random.default_rng(1)
    holds_mm = [0.0, 20.0, 40.0, 60.0, 80.0]
    ev = [{"event": "e8_meas", "t_wall": 6.0 * i + k * 0.04, "gripper_pos": mm}   # hold i: [6i, 6i + 4) s
          for i, mm in enumerate(holds_mm) for k in range(100)]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"units": "mm", "events": ev}, f)
    mt, mv, units = H.load_holds(f.name)
    assert units == "mm" and np.allclose(H.to_mm(mv), np.array([e["gripper_pos"] for e in ev]))
    t_rows = np.arange(0.0, 30.0, 0.04)                       # camera frames, holds and the transit between them
    w_true = np.interp(t_rows, mt, mv)
    j = np.clip(np.searchsorted(mt, t_rows), 1, len(mt) - 1)
    far = np.minimum(np.abs(t_rows - mt[j - 1]), np.abs(mt[j] - t_rows)) > H.HOLD_TOL_S
    w_true[far] = 2.0                                         # transit far from a hold: a width the fit must not see
    axis = np.array([0.0, 0.6, 0.8])
    tail = 50.0 * w_true[:, None] * axis + rng.normal(0, 0.2, (len(t_rows), 3))
    pos = np.stack([tail, rng.normal(0, 0.2, (len(t_rows), 3))], 1)
    rows = H.rows_from(t_rows, np.array([36, 40]), pos)
    ests = H.L.fit_estimators(rows, mt, mv, tails={36: 12.0}, bases={40: 12.0}, singles=[], meas_tol=H.HOLD_TOL_S,
                              verbose=False)
    assert "pair:36-40" in ests and far.any()
    s = H.score_holds(rows, ests, mt, mv)
    assert s["median"] < 0.5 and set(s["per_hold_mm"]) == {f"{x:.1f}" for x in holds_mm}


if __name__ == "__main__":
    for f in (test_width_map_inverse, test_fit_predict_synthetic, test_score_coverage, test_holds_log_and_sparse_fit):
        f()
        print("ok", f.__name__)
