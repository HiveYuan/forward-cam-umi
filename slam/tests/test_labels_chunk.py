"""Chunk-length label metric and evaluate_session overrides on synthetic data
(python -m slam.tests.test_labels_chunk)."""
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G
from slam import labels as L


@contextmanager
def _work():
    """Temporary SLAM_WORK with a synthetic session (glove 'yosub' calibration from calib/)."""
    old_work, old_sess = C.WORK, dict(C.SESSIONS)
    with tempfile.TemporaryDirectory() as tmp:
        C.WORK = Path(tmp)
        C.SESSIONS["synth"] = {"head_stem": "x", "intrinsics": "x", "glove": "yosub", "tile_layout": "x"}
        try:
            yield Path(tmp) / "synth" / "segments"
        finally:
            C.WORK = old_work
            C.SESSIONS.clear()
            C.SESSIONS.update(old_sess)


def _rx(deg):
    return G.rt_to_T(np.array([np.radians(deg), 0, 0]), np.zeros(3))[0]


# ---------------------------------------------------------------- chunk metric
def test_chunk_stats_by_hand():
    anchors = [("ep00", 0, [(1, 1.0, 0.1), (2, 3.0, 0.3)]),
               ("ep00", 1, [(2, 5.0, 0.5)]),
               ("ep00", 2, [])]
    r = L.chunk_stats(anchors, [1, 2])
    assert set(r) == {"1", "2"} and set(r["1"]) == set(L.CHUNK_KEYS)
    assert r["1"]["anchors"] == 1 and r["1"]["pos_mm_mean"] == 1.0 and r["1"]["pooled_pos_mm_mean"] == 1.0
    h = r["2"]                                       # anchor means 2.0 and 5.0; pooled (1 + 3 + 5) / 3
    assert h["anchors"] == 2 and abs(h["pos_mm_mean"] - 3.5) < 1e-12 and abs(h["pos_mm_median"] - 3.5) < 1e-12
    assert abs(h["pos_mm_p90"] - (2.0 + 0.9 * 3.0)) < 1e-12 and abs(h["pooled_pos_mm_mean"] - 3.0) < 1e-12
    assert abs(h["rot_deg_mean"] - 0.35) < 1e-12 and abs(h["pooled_rot_deg_mean"] - 0.3) < 1e-12
    e = L.chunk_stats([("ep00", 0, [])], [5])["5"]
    assert e["anchors"] == 0 and e["pos_mm_mean"] is None


def test_chunk_metric_known_errors():
    """Tile labels move along x at v per step; the test labels over-scale the translation by
    (1 + e) and rotate about x by w per step, so the chunk error at step j is exactly
    e v j (position) and w j (rotation), on the steps check_labels counts."""
    N, v, e, w, gap_at = 40, 0.002, 0.05, 0.1, 25
    t = 3.0 + np.arange(N) / L.FPS
    base = G.rt_to_T(np.array([0.3, -0.2, 0.1]), np.array([0.5, 0.1, 0.9]))[0]   # arbitrary ref frame
    TB, TA = np.zeros((N, 4, 4)), np.zeros((N, 4, 4))
    for k in range(N):
        TB[k] = base @ G.rt_to_T(np.zeros(3), np.array([v * k, 0, 0]))[0]
        TA[k] = base @ G.rt_to_T(np.zeros(3), np.array([(1 + e) * v * k, 0, 0]))[0] @ _rx(w * k)
    gap = np.zeros(N, bool)
    gap[gap_at] = True
    with _work() as segs:
        d = segs / "ep00" / "labels"
        d.mkdir(parents=True)
        np.savez(d / "tiles.npz", t=t, T_ref_tool=TB, gap=np.zeros(N, bool), keep=True)
        np.savez(d / "X.npz", t=t, T_ref_tool=TA, gap=gap, keep=True)
        Hs = [5, 10, 100]
        anchors = list(L.anchor_errors("synth", "X", 100))
        chk = L.check_labels("synth", "X", 100)
        assert L.step_stats(anchors, "X", 100) == chk
        ch = L.chunk_labels("synth", "X", Hs)
        assert ch == L.chunk_stats(anchors, Hs)
    ok = ~gap
    assert chk["anchors"] == ok.sum() == len(anchors)
    for j, r in chk["by_step"].items():               # every anchor has the same error at step j
        n = sum(1 for a in range(N) if ok[a] and a + j < N and ok[a + j])
        assert r["n"] == n and abs(r["pos_mm_median"] - 1000 * e * v * j) < 1e-9
        assert abs(r["rot_deg_p90"] - w * j) < 1e-9
    for H in Hs:
        per, pooled = [], []
        for a in range(N):
            js = [j for j in range(1, H + 1) if ok[a] and a + j < N and ok[a + j]]
            if js:
                per.append([np.mean([1000 * e * v * j for j in js]), np.mean([w * j for j in js])])
                pooled += [(1000 * e * v * j, w * j) for j in js]
        per, pooled = np.array(per), np.array(pooled)
        r = ch[str(H)]
        assert r["anchors"] == len(per)
        for key, x in (("pos_mm_mean", per[:, 0].mean()), ("pos_mm_median", np.median(per[:, 0])),
                       ("pos_mm_p90", np.percentile(per[:, 0], 90)), ("rot_deg_mean", per[:, 1].mean()),
                       ("rot_deg_median", np.median(per[:, 1])), ("rot_deg_p90", np.percentile(per[:, 1], 90)),
                       ("pooled_pos_mm_mean", pooled[:, 0].mean()), ("pooled_rot_deg_mean", pooled[:, 1].mean())):
            assert abs(r[key] - x) < 1e-9, (H, key, r[key], x)
    # the last anchor (no step left) counts for check_labels but not for the chunk metric
    assert ch["100"]["anchors"] == chk["anchors"] - 1


# ---------------------------------------------------------------- evaluate_session overrides
def _synthetic_segment(seg, s_true=0.6, fps=30.0, n=60):
    seg.mkdir(parents=True)
    k = np.arange(n)
    T_wc = np.stack([G.rt_to_T(np.array([0, np.radians(0.5 * i), 0]), np.array([0.005 * i, 0.001 * i, 0]))[0]
                     for i in k])
    json.dump({"frames": [{"k": int(i), "wall": float(i / fps), "in_episode": True} for i in k]},
              open(seg / "frames.json", "w"))
    np.savez(seg / "gt.npz", cam_k=k, T_cam_world=G.inv(T_wc), cam_tiles=np.full(n, 2), cam_rms=np.ones(n),
             full_k=k, full_rvec=np.tile([0.1, 0.2, 0.0], (n, 1)), full_tvec=np.tile([0.05, 0.0, 0.4], (n, 1)))
    G0 = G.rt_to_T(np.array([0.2, 0.1, -0.3]), np.array([0.3, -0.1, 0.2]))[0]   # world -> SLAM frame
    T_sc = G0[None] @ T_wc
    T_sc[:, :3, 3] /= s_true                                                       # up to scale
    (seg / "slam").mkdir()
    np.savez(seg / "slam" / "R.npz", k=k, T_slam_cam=T_sc, meta=json.dumps({"n_keyframes": 5}))


def test_evaluate_session_overrides():
    from slam import evaluate as EV
    dts0, fail0 = list(EV.DTS), EV.FAIL_DEG
    with _work() as segs:
        _synthetic_segment(segs / "ep00")
        out = C.WORK / "out"
        S = EV.evaluate_session("synth", ["R"], out / "a", dts=[0.1, 0.5])
        saved = json.load(open(out / "a" / "summary.json"))
        assert saved["dts"] == [0.1, 0.5] and set(saved["runs"]["R"]["by_dt"]) == {"0.1", "0.5"}
        assert saved["runs"]["R"]["track_fail_frac"] is None                      # no 0.08 s pairs
        b = saved["runs"]["R"]["by_dt"]["0.5"]
        assert b["rot_err_deg"]["n"] == 45 and b["rot_err_deg"]["median"] < 1e-5
        assert b["trans_err_mm"]["median"] < 1e-6 and b["label_pos_err_mm"]["median"] < 1e-6   # oracle scale
        assert abs(saved["segments"]["ep00"]["R"]["scale"] - 0.6) < 1e-9
        assert "scale_vs_oracle" not in saved["segments"]["ep00"] and S["scale"] == "tiles"
        assert (out / "a" / "summary.md").read_text().count("| R |") >= 5
        # fail_deg override (dt 0.08 s pairs exist at 30 fps): every pair 'fails' below 0 deg
        S = EV.evaluate_session("synth", ["R"], out / "b", dts=[0.08], fail_deg=-1.0)
        assert S["runs"]["R"]["track_fail_frac"] == 1.0
        S = EV.evaluate_session("synth", ["R"], out / "c", dts=[0.08])
        assert S["runs"]["R"]["track_fail_frac"] == 0.0
        # scale override: s = 2 x oracle doubles the head translation
        S = EV.evaluate_session("synth", ["R"], out / "d", scale_fn=lambda seg, run, so: 2 * so,
                                dts=[0.5], scale_name="twice")
        seg = S["segments"]["ep00"]
        assert abs(seg["scale_vs_oracle"]["R"] - 1.0) < 1e-12 and abs(seg["R"]["scale"] - 1.2) < 1e-9
        b = S["runs"]["R"]["by_dt"]["0.5"]
        assert abs(b["trans_err_mm"]["median"] - b["gt_trans_mm"]["median"]) < 1e-6
        assert S["scale"] == "twice" and "scale twice" in (out / "d" / "summary.md").read_text()
    assert EV.DTS == dts0 and EV.FAIL_DEG == fail0                               # module defaults untouched


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
