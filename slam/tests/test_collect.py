"""slam.collect and the collected-session registry (python -m slam.tests.test_collect; CPU, no data)."""
import json
import os
import tempfile
from pathlib import Path

from slam import collect as K
from slam import config as C


def meta(ds="yuan_slam_01", **kw):
    m = {"schema": "slam_session/1", "dataset": ds, "unit": "yuan",
         "cameras": {"b0587b": {"intrinsics": "calib/B0587b_yuan_intrinsics.json"},
                     "fish": {"intrinsics": "calib/fisheye_glove_yuan_intrinsics.json"}},
         "tiles": {"tags": "calib/tags36h11_yuan.json", "layout_take": "yuan_layout_01"},
         "exclude_episodes": [3]}
    m.update(kw)
    return m


def test_collected_session_entry():
    s = C.collected_session(meta())
    assert s["head_stem"] == "yuan_slam_01_b0587b"
    assert s["intrinsics"] == "collected/B0587b_yuan_intrinsics.json"
    assert s["wrist_intrinsics"] == "collected/fisheye_glove_yuan_intrinsics.json"
    assert s["tile_layout"] == "workspace_tiles_yuan_layout_01.json"     # from the layout take
    assert s["glove"] == "yuan" and s["exclude_episodes"] == [3]
    assert s["sam2_prompts"] == C.UNIT_PROMPTS["yosub"]                  # same sheet and ids: yosub's points
    s2 = C.collected_session(meta(tiles={"tags": "x", "layout_take": "a", "layout": "calib/workspace_tiles_b.json"}))
    assert s2["tile_layout"] == "workspace_tiles_b.json"                 # an explicit layout wins
    s3 = C.collected_session(meta(cameras={"b0587b": {"intrinsics": "calib/h.json"}}))
    assert s3["wrist_intrinsics"] is None


def test_split_holds_takes_the_last_hold_for_verification():
    ev = [{"event": "e8_meas", "t_wall": t, "gap_mm": g, "gripper_pos": g}
          for t, g in [(0, 0.0), (0.5, 0.0), (5, 20.0), (5.5, 20.0), (10, 40.0), (15, 57.9), (15.5, 57.9)]]
    train, verify = K.split_holds(ev)
    assert {e["gap_mm"] for e in verify} == {57.9} and len(verify) == 2
    assert {e["gap_mm"] for e in train} == {0.0, 20.0, 40.0}
    train, verify = K.split_holds(ev, verify_gap=20.0)
    assert {e["gap_mm"] for e in verify} == {20.0}
    try:                                              # last width also used for training: ambiguous
        K.split_holds(ev + [{"event": "e8_meas", "t_wall": 30, "gap_mm": 0.0, "gripper_pos": 0.0}])
        raise AssertionError("expected SystemExit")
    except SystemExit:
        pass


def test_import_never_overwrites_a_calibration():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        old = (C.COLLECT_REPO, K.COLLECTED)
        C.COLLECT_REPO, K.COLLECTED = d / "repo", d / "calib_collected"
        try:
            (d / "repo/calib").mkdir(parents=True)
            src = d / "repo/calib/B0587b_yuan_intrinsics.json"
            src.write_text(json.dumps({"camera_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "dist_coeffs": [0]}))
            assert K.import_file("calib/B0587b_yuan_intrinsics.json") == "collected/B0587b_yuan_intrinsics.json"
            assert (K.COLLECTED / src.name).exists()
            K.import_file(src.name)                    # identical: fine
            src.write_text(json.dumps({"camera_matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 1]], "dist_coeffs": [0]}))
            try:
                K.import_file(src.name)
                raise AssertionError("expected SystemExit")
            except SystemExit as e:
                assert "different content" in str(e)
        finally:
            C.COLLECT_REPO, K.COLLECTED = old


def test_registry_reads_session_files():
    with tempfile.TemporaryDirectory() as d:
        raw = Path(d) / "data/raw"
        raw.mkdir(parents=True)
        (raw / "yuan_t9_session.json").write_text(json.dumps(meta("yuan_t9")))
        (raw / "broken_session.json").write_text("{")
        old_repo, old_sessions = C.COLLECT_REPO, dict(C.SESSIONS)
        C.COLLECT_REPO = Path(d)
        try:
            C._register_collected()
            assert C.session("yuan_t9")["glove"] == "yuan"
            assert "broken" not in C.SESSIONS
            assert C.SESSIONS["yam_glove7"] == old_sessions["yam_glove7"]   # the paper sessions are untouched
        finally:
            C.COLLECT_REPO = old_repo
            C.SESSIONS.clear()
            C.SESSIONS.update(old_sessions)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
