"""Error decomposition step (slam.pipeline.impl_error_decomp) on synthetic segments
(python -m slam.tests.test_error_decomp).

A synthetic session: tile head poses (world->cam), ball poses (cam->ball) and a SLAM trajectory
built from the tile poses (a similarity transform of them, optionally with rotation errors), at
30 fps, labelled on the 15 fps grid by the unchanged slam.labels code.
"""
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G
from slam import labels as L
from slam.pipeline import impl_error_decomp as ED
from slam.pipeline.worker import Job

PARAMS = {"label_steps": [1, 2, 4, 8, 15, 30, 60], "horizon": 60, "chunk_H": [15, 30, 50, 75],
          "speed_bins_deg_s": [0.0, 10.0, 30.0], "speed_window_s": 0.5}
FPS_CAM = 30.0
S_TRUE = 0.6                                   # SLAM units -> metres
G0 = G.rt_to_T(np.array([0.3, -0.2, 0.5]), np.array([0.4, -0.1, 0.2]))[0]     # world -> SLAM frame


@contextmanager
def _work():
    """Temporary SLAM_WORK with a synthetic session (glove 'yosub' tool offset from calib/)."""
    old_work, old_sess = C.WORK, dict(C.SESSIONS)
    with tempfile.TemporaryDirectory() as tmp:
        C.WORK = Path(tmp)
        C.SESSIONS["synth"] = {"head_stem": "x", "intrinsics": "x", "glove": "yosub", "tile_layout": "x"}
        try:
            yield Path(tmp)
        finally:
            C.WORK = old_work
            C.SESSIONS.clear()
            C.SESSIONS.update(old_sess)


def head_poses(tau, rot=True, trans=True, omega_deg=None):
    """world->cam poses at times tau [s]: smooth rotation and translation; omega_deg: constant
    rotation rate about the camera y axis instead."""
    if omega_deg is not None:                  # world->cam = R_x(0.1) R_y(omega tau)
        T = np.tile(np.eye(4), (len(tau), 1, 1))
        T[:, :3, :3] = G.rodrigues([0.1, 0, 0])[0][None] @ G.rodrigues(
            np.stack([0 * tau, np.radians(omega_deg) * tau, 0 * tau], 1))
    else:
        rv = np.stack([0.2 * np.sin(0.7 * tau), 0.4 * np.sin(0.5 * tau) + 0.1 * tau, 0.1 * np.cos(0.9 * tau)], 1)
        T = G.rt_to_T(rv if rot else 0 * rv, np.zeros((len(tau), 3)))
    if trans:
        T[:, :3, 3] = np.stack([0.1 * np.sin(0.6 * tau), 0.05 * tau, 0.03 * np.cos(1.1 * tau)], 1)
    else:
        T[:, :3, 3] = [0.2, 0.1, 0.4]
    return T


def slam_from_tiles(T_wc, s_true=S_TRUE, rot_err_deg=0.0, tau=None):
    """SLAM trajectory = similarity transform of the tile head poses (G0, 1 / s_true); with
    rot_err_deg: a camera-frame rotation error of that amplitude (about z, varying in time)."""
    T = G0[None] @ T_wc
    if rot_err_deg:
        E = G.rodrigues(np.stack([0 * tau, 0.3 * np.sin(1.3 * tau), np.sin(2.0 * tau)], 1) * np.radians(rot_err_deg))
        T[:, :3, :3] = T[:, :3, :3] @ E
    T[:, :3, 3] /= s_true
    return T


def make_segment(seg, T_wc, T_sc, wall, t_start, t_end, ball_drop=()):
    """Segment files as slam.preprocess / slam.run_droid write them (frames.json, gt.npz,
    slam/E3.npz); ball poses (cam->ball) missing at the frame indices in ball_drop."""
    seg.mkdir(parents=True)
    n = len(wall)
    k = np.arange(n) + 1000
    json.dump({"episode": {"episode_index": int(seg.name[2:]), "t_start": float(t_start), "t_end": float(t_end)},
               "frames": [{"i": i, "k": int(k[i]), "wall": float(wall[i]), "in_episode": bool(t_start <= wall[i] <= t_end)}
                          for i in range(n)]}, open(seg / "frames.json", "w"))
    tau = wall - wall[0]
    keep = np.array([i for i in range(n) if i not in set(ball_drop)], int)
    rv = np.stack([0.1 + 0.05 * np.sin(tau), 0.2 + 0.1 * np.sin(0.8 * tau), 0.05 * tau], 1)
    tv = np.stack([0.05 + 0.03 * np.sin(0.9 * tau), 0.02 * np.cos(tau), 0.45 + 0.05 * np.sin(0.4 * tau)], 1)
    np.savez(seg / "gt.npz", cam_k=k, T_cam_world=G.inv(T_wc), cam_tiles=np.full(n, 3), cam_rms=np.ones(n),
             full_k=k[keep], full_rvec=rv[keep], full_tvec=tv[keep])
    (seg / "slam").mkdir()
    np.savez(seg / "slam" / "E3.npz", k=k, T_slam_cam=T_sc, meta=json.dumps({"n_keyframes": 5}))
    return seg


def timeline(t0=1000.01, dur=7.0, ep=(0.5, 6.2)):
    """Frame times and episode bounds. t0 is not a multiple of 1/30 s: slam.labels.anchor_errors
    keys the common timeline by round(t * 15), and a grid time with t * 15 exactly at .5 (e.g.
    1000.5 s) collides with its neighbour under round-half-to-even."""
    wall = t0 + np.arange(int(dur * FPS_CAM)) / FPS_CAM
    return wall, t0 + ep[0], t0 + ep[1]


def scale_res(rows, label="B+Acheck"):
    """scale_<run>.json (analysis contract) with the fields the step reads."""
    return {"run": "E3", "label": label, "primary": "B", "checks": ["A"],
            "rows": [{"segment": s, "s": c, "ok": c is not None, "oracle_s": o, "flagged": False} for s, c, o in rows]}


def decompose(segs, rows, params=PARAMS):
    return ED.decompose("synth", segs, "E3", scale_res(rows), params, C.WORK / "scratch")


def worst(res, combo, key):
    """Largest median / p90 of a combination over its steps (key 'pos_mm' or 'rot_deg')."""
    by = res["combos"][combo]["by_step"]
    return max(max(b[f"{key}_median"], b[f"{key}_p90"]) for b in by.values())


# ---------------------------------------------------------------------- tests
def test_speed_bins():
    b = ED.speed_bins([0, 10, 30])
    assert [x[0] for x in b] == ["0-10", "10-30", "30+"] and b[2][2] == float("inf")
    assert ED.bin_of(9.99, b) == "0-10" and ED.bin_of(10.0, b) == "10-30" and ED.bin_of(300, b) == "30+"
    assert ED.bin_of(float("nan"), b) is None and ED.bin_of(None, b) is None and ED.bin_of(-1, b) is None
    for bad in ([], [10, 10], [30, 10]):
        try:
            ED.speed_bins(bad)
            raise AssertionError(bad)
        except ValueError:
            pass


def test_perfect_slam_all_zero():
    """SLAM = similarity transform of the tile poses and the configured scale = the oracle: every
    combination reproduces the tile labels."""
    with _work() as w:
        wall, ts, te = timeline()
        T_wc = head_poses(wall - wall[0])
        make_segment(w / "synth" / "segments" / "ep00", T_wc, slam_from_tiles(T_wc), wall, ts, te)
        res = decompose(["ep00"], [("ep00", S_TRUE, S_TRUE)])
        assert not (w / "synth" / "segments" / "ep00" / "labels").exists()      # nothing written into the view
        assert not (w / "scratch" / "segments").exists()                        # scratch label files removed
    assert list(res["combos"]) == [c for c, _, _ in ED.COMBOS]
    n = res["anchors"]["configured"]
    assert n == res["anchors"]["oracle"] > 60 and res["segments"]["ep00"]["anchors"] == {"configured": n, "oracle": n}
    for c, x in res["combos"].items():
        assert x["anchors"] == n and set(x["by_step"]) == {str(j) for j in PARAMS["label_steps"]}
        assert worst(res, c, "pos_mm") < 1e-6, (c, worst(res, c, "pos_mm"))
        assert worst(res, c, "rot_deg") < 1e-4, (c, worst(res, c, "rot_deg"))   # arccos floor ~1e-6 deg
        assert set(x["chunk"]) == {str(h) for h in PARAMS["chunk_H"]}
        assert x["chunk"]["75"]["pos_mm_mean"] < 1e-6
    for kind in ED.SCALES:
        d = res["checks"]["decomposition"][kind]
        assert d["pairs"] > 1000 and d["max_pos_mm"] < 1e-9 and d["max_rot_frobenius"] < 1e-12
        cp = res["coupling"][kind]["by_step"]["15"]
        assert cp["rot_part_mm_median"] < 1e-6 and cp["trans_part_mm_median"] < 1e-6


def test_scale_error_removed_by_oracle_scale():
    """Configured scale 25% too large: the oracle-scale combinations are exact, the configured ones
    have a position error of 0.25 x the head translation (no rotation error), whatever the rotation
    source."""
    with _work() as w:
        wall, ts, te = timeline()
        T_wc = head_poses(wall - wall[0])
        make_segment(w / "synth" / "segments" / "ep00", T_wc, slam_from_tiles(T_wc), wall, ts, te)
        res = decompose(["ep00"], [("ep00", 1.25 * S_TRUE, S_TRUE)])
        tile = L.build_segment(w / "synth" / "segments" / "ep00", "tiles", "tiles", np.eye(4))
    assert tile["keep"]
    for c in ("R_slam+s_oracle", "R_tile+s_oracle"):
        assert worst(res, c, "pos_mm") < 1e-6 and worst(res, c, "rot_deg") < 1e-4
    a, b = res["combos"]["R_slam+s_configured"]["by_step"], res["combos"]["R_tile+s_configured"]["by_step"]
    # expected: 0.25 |P(t+j) - P(t)| with P the head positions linearly interpolated on the 15 fps grid
    tq = np.arange(ts, te, 1 / L.FPS)
    P = np.stack([np.interp(tq, wall, T_wc[:, c, 3]) for c in range(3)], 1)
    for j, x in a.items():
        j = int(j)
        e = 1000 * 0.25 * np.linalg.norm(P[j:] - P[:-j], axis=1)
        assert x["n"] == len(e) and abs(x["pos_mm_median"] - np.median(e)) < 1e-6, (j, x, np.median(e))
        assert abs(x["pos_mm_p90"] - np.percentile(e, 90)) < 1e-6 and x["rot_deg_p90"] < 1e-4
        assert abs(b[str(j)]["pos_mm_median"] - x["pos_mm_median"]) < 1e-6 and b[str(j)]["rot_deg_p90"] < 1e-4
    assert a["30"]["pos_mm_median"] > 10
    cp = res["coupling"]
    assert cp["oracle"]["by_step"]["15"]["trans_part_mm_median"] < 1e-6
    assert abs(cp["configured"]["by_step"]["15"]["trans_part_mm_median"] - a["15"]["pos_mm_median"]) < 1e-6


def test_rotation_error_removed_by_tile_rotation():
    """A camera that only rotates (no head translation), SLAM with a rotation error: the tile
    rotation removes the whole label error, the oracle scale nothing."""
    with _work() as w:
        wall, ts, te = timeline()
        tau = wall - wall[0]
        T_wc = head_poses(tau, trans=False)
        make_segment(w / "synth" / "segments" / "ep00", T_wc, slam_from_tiles(T_wc, rot_err_deg=1.0, tau=tau),
                     wall, ts, te)
        res = decompose(["ep00"], [("ep00", 1.25 * S_TRUE, S_TRUE)])
    for c in ("R_tile+s_configured", "R_tile+s_oracle"):
        assert worst(res, c, "pos_mm") < 1e-6 and worst(res, c, "rot_deg") < 1e-4, c
    a, b = res["combos"]["R_slam+s_configured"], res["combos"]["R_slam+s_oracle"]
    assert a["by_step"]["15"]["rot_deg_median"] > 0.2 and a["by_step"]["15"]["pos_mm_median"] > 1.0
    for j, x in a["by_step"].items():                     # no head translation: the scale does not matter
        assert all(abs(x[k] - b["by_step"][j][k]) < 1e-9 for k in x), j
    assert all(abs(x["pos_mm_mean"] - b["chunk"][h]["pos_mm_mean"]) < 1e-9 for h, x in a["chunk"].items())
    cp = res["coupling"]["oracle"]["by_step"]["15"]
    assert cp["trans_part_mm_median"] < 1e-6 and cp["rot_part_mm_median"] > 1.0


def test_rotation_error_with_translation():
    """With head translation too, the tile rotation still removes every label rotation error; the
    position error that remains comes from SLAM's translation expressed in its rotated cam_t."""
    with _work() as w:
        wall, ts, te = timeline()
        tau = wall - wall[0]
        T_wc = head_poses(tau)
        make_segment(w / "synth" / "segments" / "ep00", T_wc, slam_from_tiles(T_wc, rot_err_deg=1.0, tau=tau),
                     wall, ts, te)
        res = decompose(["ep00"], [("ep00", S_TRUE, S_TRUE)])
    for c in ("R_tile+s_configured", "R_tile+s_oracle"):
        assert worst(res, c, "rot_deg") < 1e-4, c
    assert res["combos"]["R_slam+s_oracle"]["by_step"]["15"]["rot_deg_median"] > 0.2
    assert res["combos"]["R_tile+s_oracle"]["by_step"]["15"]["pos_mm_median"] > 1e-3


def test_speed_bins_and_unknown():
    """Constant 20 deg/s head rotation: every anchor whose t + 0.5 s has a tile pose is in 10-30;
    the frames stop at the episode end, so the last anchors are unknown."""
    with _work() as w:
        wall, ts, te = timeline(dur=6.0, ep=(0.5, 5.99))
        T_wc = head_poses(wall - wall[0], omega_deg=20.0)
        make_segment(w / "synth" / "segments" / "ep00", T_wc, slam_from_tiles(T_wc), wall, ts, te)
        res = decompose(["ep00"], [("ep00", S_TRUE, S_TRUE)])
    tq = np.arange(ts, te, 1 / L.FPS)
    unknown = int((tq + 0.5 > wall[-1] + L.LABEL_TOL).sum())
    n = res["anchors"]["oracle"]
    assert n == len(tq) and unknown > 0
    assert res["speed"]["anchors"]["oracle"] == {"0-10": 0, "10-30": n - unknown, "30+": 0, "unknown": unknown}
    by = res["combos"]["R_slam+s_oracle"]["by_speed"]
    assert by["10-30"]["anchors"] == n - unknown and by["0-10"]["anchors"] == 0 and by["0-10"]["by_step"] == {}
    assert by["0-10"]["chunk"]["15"]["anchors"] == 0 and by["0-10"]["chunk"]["15"]["pos_mm_mean"] is None
    assert res["speed"]["window_s"] == 0.5 and res["speed"]["bins_deg_s"] == [0.0, 10.0, 30.0]


def _labels_like_the_labels_step(segs, rows, out):
    """labels_E3.json and labels_E3@B+Acheck.json as slam.pipeline.impl_analysis.run_labels writes
    them (label files in the segments, oracle scale from slam.scale.estimate)."""
    from slam.evaluate import load_tool_offset
    from slam.pipeline.impl_analysis import _clean, label_result
    T_bt = load_tool_offset("synth")
    ev = {"horizon": PARAMS["horizon"], "chunk_H": PARAMS["chunk_H"], "label_steps": PARAMS["label_steps"]}
    root = C.segments_dir("synth")
    for s in segs:
        L.build_segment(root / s, "tiles", "tiles", T_bt, {})
    kept_o = {s: bool(L.build_segment(root / s, "E3", "tiles", T_bt, {})["keep"]) for s in segs}
    smap = {r[0]: r[1] for r in rows}
    kept_c = {s: bool(L.build_segment(root / s, "E3", "B+Acheck", T_bt, {}, scale=(smap[s], "B+Acheck"))["keep"])
              for s in segs}
    for name, kept in (("E3", kept_o), ("E3@B+Acheck", kept_c)):
        json.dump(_clean(label_result("synth", name, ev, (), kept)), open(out / f"labels_{name}.json", "w"), indent=1)


def test_step_reproduces_labels_files():
    """run_error_decomp on two segments with ball-pose gaps, one without a configured scale: the
    SLAM-rotation combinations are bit-identical to the labels step's files; outputs are strict JSON."""
    from slam import scale as SC
    with _work() as w:
        root = w / "synth" / "segments"
        for i, (drop, err) in enumerate(((range(40, 52), 0.7), (list(range(100, 106)) + list(range(150, 175)), 1.5))):
            wall, ts, te = timeline(t0=1000.01 + 100 * i)
            tau = wall - wall[0]
            T_wc = head_poses(tau)
            make_segment(root / f"ep0{i}", T_wc, slam_from_tiles(T_wc, rot_err_deg=err, tau=tau), wall, ts, te,
                         ball_drop=drop)
        oracle = {s: float(SC.estimate(root / s, "E3", "tiles")["s"]) for s in ("ep00", "ep01")}
        rows = [("ep00", 0.9 * oracle["ep00"], oracle["ep00"]), ("ep01", None, oracle["ep01"])]
        out = w / "results"
        out.mkdir()
        json.dump(scale_res(rows), open(out / "scale_E3.json", "w"))
        _labels_like_the_labels_step(["ep00", "ep01"], rows, out)
        spec = {"params": PARAMS, "node": {"id": "error_decomp", "step": "error_decomp", "name": "error_decomp",
                                           "impl": "default", "key": None},
                "data": {"session": "synth"}, "segments": ["ep00", "ep01"], "out_dir": str(out),
                "scratch": str(w / "scratch" / "error_decomp"),
                "analysis": {"error_decomp": {"runs": ["E3"], "params": PARAMS},
                             "labels": {"runs": ["E3"], "params": {"gripper": "wrist"}}}}
        r = ED.run_error_decomp(Job(spec))
        res = json.loads((out / "errdecomp_E3.json").read_text(),
                         parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
        md = (out / "errdecomp_E3.md").read_text()
        lab_c = json.load(open(out / "labels_E3@B+Acheck.json"))
    assert r["E3"]["labels_identical"] == {"R_slam+s_configured": True, "R_slam+s_oracle": True}
    chk = res["checks"]["labels_files"]
    assert chk["R_slam+s_configured"]["file"] == "labels_E3@B+Acheck.json" and chk["R_slam+s_configured"]["identical"]
    assert chk["R_slam+s_oracle"]["max_abs_diff"] == 0.0 and chk["R_slam+s_oracle"]["anchors"][0] > 0
    seg = res["segments"]
    assert seg["ep01"]["s"] is None and seg["ep01"]["anchors"]["configured"] == 0 and seg["ep01"]["anchors"]["oracle"] > 0
    assert res["anchors"]["configured"] == seg["ep00"]["anchors"]["configured"] == lab_c["anchors"]
    assert res["anchors"]["oracle"] == seg["ep00"]["anchors"]["oracle"] + seg["ep01"]["anchors"]["oracle"]
    assert res["gripper"] == "wrist" and res["params"] == PARAMS and res["scale_label"] == "B+Acheck"
    # the rotation error is removed by the tile rotation (rotation of the labels), not by the scale;
    # across the dropped ball poses the label grid interpolates products over up to 0.8 s, so
    # C(t)^-1 X(t) differs from the tile side by ~1e-4 deg there (exactly 0 on frame times)
    c = res["combos"]
    assert max(b["rot_deg_p90"] for b in c["R_tile+s_oracle"]["by_step"].values()) < 1e-3
    assert c["R_slam+s_oracle"]["by_step"]["15"]["rot_deg_median"] > 0.2
    # the counted steps of a combination never exceed what its anchors allow (gaps: fewer than anchors)
    assert all(b["n"] <= c["R_tile+s_oracle"]["anchors"] for b in c["R_tile+s_oracle"]["by_step"].values())
    assert c["R_tile+s_oracle"]["by_step"]["60"]["n"] < c["R_tile+s_oracle"]["by_step"]["1"]["n"]
    for title in ("position error [mm], median / p90", "rotation error [deg], median / p90", "chunk-length",
                  "by head rotation speed", "rotation and translation parts", "## Segments"):
        assert title in md, title
    assert "vs `labels_E3@B+Acheck.json`: identical" in md and "vs `labels_E3.json`: identical" in md


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
