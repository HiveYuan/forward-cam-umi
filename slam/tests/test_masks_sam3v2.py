"""Pure parts of the SAM3 v2 masks (python -m slam.tests.test_masks_sam3v2): no GPU, no model.

  - frame_widths / held_gate: gripper width at the frame times, NaN in gaps, closed-gripper gate;
  - project / prompt_schedule: body-frame points to pixels, prompt cadence, negative points,
    the held object only on gated frames;
  - attach_filter: seeds (tracked wearer, border-touching seed prompts), transitive growth,
    'cable' never a seed, border seeds off with border_px -1;
  - leak_flags: an instance far larger than its masklet's lower-quartile area is flagged;
  - combine: part layout, held mask only on gated frames, dropped text area, leaked instances
    dropped before the attachment test (they cannot bridge to others);
  - impl_masks_sam3v2.check_params on the registry defaults and on bad values; the exp006 config
    builds and its motion masks use exactly the registry defaults.
"""
import copy
from pathlib import Path

import numpy as np
import yaml

from slam import masks_sam3v2 as S
from slam.pipeline import impl_masks_sam3v2 as I
from slam.pipeline import registry as R
from slam.pipeline import spec as SP

W, H = 64, 48
K = np.array([[50.0, 0, 32], [0, 50.0, 24], [0, 0, 1]])


def _raises(exc, fn, *a, match=None, **kw):
    try:
        fn(*a, **kw)
    except exc as e:
        assert match is None or match in str(e), f"{match!r} not in {str(e)!r}"
        return
    raise AssertionError(f"{fn.__name__} did not raise {exc.__name__}")


def _box(r0, r1, c0, c1):
    m = np.zeros((H, W), bool)
    m[r0:r1, c0:c1] = True
    return m


def _pose(z=0.5):
    T = np.eye(4)
    T[2, 3] = z
    return T


# ---------------------------------------------------------------------------- held gating
def test_frame_widths():
    t = np.array([10.0, 10.1, 10.2, 10.6, 10.7])
    v = np.array([0.2, 0.4, 0.6, 0.6, 0.2])
    wall = [9.0, 9.95, 10.05, 10.15, 10.4, 10.65, 10.75, 10.9]
    w = S.frame_widths(wall, t, v, tol_s=0.12)
    assert np.isnan(w[0])                         # before the series
    assert abs(w[1] - 0.2) < 1e-12                # within tol before the first sample: clamped
    assert abs(w[2] - 0.3) < 1e-12 and abs(w[3] - 0.5) < 1e-12
    assert np.isnan(w[4])                         # 0.2 s from the nearest sample: gap
    assert abs(w[5] - 0.4) < 1e-12 and abs(w[6] - 0.2) < 1e-12
    assert np.isnan(w[7])
    # unsorted series, one sample, empty series
    o = np.array([3, 0, 4, 1, 2])
    assert np.allclose(S.frame_widths(wall, t[o], v[o], 0.12), w, equal_nan=True)
    assert np.allclose(S.frame_widths([10.0, 10.05, 10.5], [10.0], [0.3], 0.1), [0.3, 0.3, np.nan], equal_nan=True)
    assert np.isnan(S.frame_widths([1.0], [], [], 0.1)).all()


def test_held_gate():
    w = np.array([np.nan, 0.2, 0.45, 0.4500001, 0.7])
    assert S.held_gate(w, 0.45).tolist() == [False, True, True, False, False]
    assert not S.held_gate(w, None).any()
    # after_open: the closed phase at the start (rest) is not held; closed after an open frame is
    w = np.array([0.2, 0.2, np.nan, 0.6, 0.65, 0.22, 0.22, 0.5, 0.21])
    assert S.held_gate(w, 0.45).tolist() == [True, True, False, False, False, True, True, False, True]
    assert S.held_gate(w, 0.45, after_open=True).tolist() == [False] * 5 + [True, True, False, True]
    assert not S.held_gate([0.2, 0.3], 0.45, after_open=True).any()


# ---------------------------------------------------------------------------- prompts
def test_body_points_and_project():
    T_bf = np.eye(4)
    T_bf[:3, 3] = [0.1, 0.2, 0.3]
    b = S.body_points(["ball", "flange", [0.01, 0.0, 0.0]], T_bf)
    assert np.allclose(b[0], 0) and np.allclose(b[1], [0.1, 0.2, 0.3]) and np.allclose(b[2], [0.01, 0, 0])
    _raises(ValueError, S.body_points, ["wrist"], T_bf, match="unknown named point")
    pts = [np.zeros(3), np.array([0.1, 0.0, 0.0]), np.array([0.0, 0.0, -0.46]), np.array([0.3, 0.0, 0.0])]
    uv = S.project(_pose(0.5), K, pts, (W, H))
    # centre; 0.1 m right -> +10 px; behind z_min dropped; 0.3 m right -> x = 62 > W - 5 dropped
    assert uv == [[32.0, 24.0], [42.0, 24.0]]
    assert len(S.project(_pose(0.5), K, pts, (W, H), margin=-1e9)) == 3


def test_prompt_schedule():
    frames = [{"i": i, "k": 100 + i} for i in range(25)]
    poses = {100 + i: _pose(0.5) for i in range(25) if i != 10}      # no ball pose on frame 10
    gate = np.zeros(25, bool)
    gate[18:] = True
    out_pt = [np.array([1.0, 0.0, 0.0])]                             # projects outside the image
    objs = [(1, [np.zeros(3)], [np.array([0.05, 0.0, 0.0])], None),
            (2, out_pt, [], None),
            (3, [np.array([0.0, 0.05, 0.0])], [], gate)]
    s = S.prompt_schedule(frames, poses, K, (W, H), 5, objs)
    assert sorted(s) == [0, 5, 15, 20]
    assert s[0] == {1: ([[32.0, 24.0], [37.0, 24.0]], [1, 0])}
    assert 3 not in s[15] and s[20][3] == ([[32.0, 29.0]], [1])
    assert all(2 not in d for d in s.values())
    assert S.prompt_schedule(frames, {}, K, (W, H), 5, objs) == {}


# ---------------------------------------------------------------------------- instance filter
def test_attach_filter_seeds_and_growth():
    rig = _box(10, 20, 20, 30)
    masks = np.stack([
        _box(20, 30, 25, 28),     # 0 hand touching the rig (not the border) -> kept by attachment
        _box(30, 48, 25, 28),     # 1 arm: touches the bottom border -> seed
        _box(0, 48, 0, 4),        # 2 cable along the left border, attached to nothing -> dropped
        _box(5, 8, 40, 44),       # 3 hand floating in the middle -> dropped
        _box(44, 48, 28, 40),     # 4 cable attached to the arm (seed) -> kept transitively
        _box(40, 44, 36, 44),     # 5 cable attached only to cable 4 -> kept (chain)
    ])
    labels = ["hand", "arm", "cable", "hand", "cable", "cable"]
    keep = S.attach_filter(masks, labels, rig, ("hand", "arm"), attach_px=1, border_px=0)
    assert keep.tolist() == [True, True, False, False, True, True]
    # without border seeds the arm is still kept: it touches the hand, which touches the rig
    keep = S.attach_filter(masks, labels, rig, ("hand", "arm"), attach_px=1, border_px=-1)
    assert keep.tolist() == [True, True, False, False, True, True]
    # no rig: only border seeds and what grows from them
    keep = S.attach_filter(masks, labels, None, ("hand", "arm"), attach_px=1, border_px=0)
    assert keep.tolist() == [True, True, False, False, True, True]
    keep = S.attach_filter(masks, labels, np.zeros((H, W), bool), ("hand", "arm"), attach_px=1, border_px=-1)
    assert not keep.any()
    # 3 empty rows between the rig (rows 10-19) and the instance (from row 23): the dilated
    # instance reaches the rig with attach_px 4, not with 3
    m = np.stack([_box(23, 30, 20, 30)])
    assert S.attach_filter(m, ["hand"], rig, (), attach_px=4, border_px=-1).tolist() == [True]
    assert S.attach_filter(m, ["hand"], rig, (), attach_px=3, border_px=-1).tolist() == [False]
    # 'cable' touching the border is not a seed even when listed nowhere else
    assert S.attach_filter(np.stack([_box(0, 48, 0, 4)]), ["cable"], None, ("hand", "arm"), 1, 0).tolist() == [False]
    assert len(S.attach_filter(np.zeros((0, H, W), bool), [], rig, ("hand",), 1, 0)) == 0


def test_leak_flags():
    # masklet 1: 10 frames of ~100 px, one frame balloons to 500 px; masklet 2 grows steadily 100 -> 280
    obj = np.array([1] * 11 + [2] * 10)
    area = np.array([100, 90, 110, 100, 95, 105, 100, 98, 102, 100, 500] + list(range(100, 300, 20)))
    f = S.leak_flags(obj, area, 3.0)
    assert f.tolist() == [False] * 10 + [True] + [False] * 10
    q = np.quantile(area[obj == 1], S.LEAK_QUANTILE)
    assert S.leak_flags([1, 1, 1, 1], [100, 100, 100, 3 * 100], 3.0).tolist() == [False] * 4   # not strictly above
    assert S.leak_flags(obj, area, 0.99 * 500.0 / q)[10] and not S.leak_flags(obj, area, 1.01 * 500.0 / q)[10]
    assert not S.leak_flags(obj, area, 0.0).any()
    # growth by more than the ratio relative to the masklet's lower quartile is flagged too
    assert S.leak_flags([7] * 4, [10, 10, 10, 31], 3.0).tolist() == [False, False, False, True]


def test_combine():
    T = 4
    trk = np.zeros((T, 3, H, W), bool)
    trk[:, 0] = _box(10, 20, 20, 30)          # rig
    trk[:, 2] = _box(0, 5, 0, 5)              # held object (raw tracker output on every frame)
    held_ok = np.array([False, True, False, False])
    inst = {"frame": np.array([0, 0, 2, 3]), "prompt": np.array([0, 1, 1, 0]),
            "masks": np.stack([_box(20, 30, 25, 28), _box(30, 40, 50, 60), _box(20, 48, 25, 28), _box(5, 8, 40, 44)])}
    parts, keep, dropped = S.combine(inst, ["hand", "cable"], trk, held_ok, ("hand",), attach_px=1, border_px=0)
    assert parts.shape == (T, 5, H, W)
    assert keep.tolist() == [True, False, True, False]
    assert (parts[:, 0] == trk[:, 0]).all() and not parts[:, 1].any()
    assert parts[1, 2].sum() == 25 and not parts[[0, 2, 3], 2].any()        # held only where gated
    assert (parts[0, 3] == inst["masks"][0]).all() and not parts[1:, 3].any()
    assert (parts[2, 4] == inst["masks"][2]).all() and not parts[[0, 1, 3], 4].any()   # cable attached to the rig
    assert (dropped[0] == inst["masks"][1]).all() and (dropped[3] == inst["masks"][3]).all()
    assert not dropped[[1, 2]].any()
    _raises(ValueError, S.combine, inst, ["hand", "cable"], trk[:, :2], held_ok, (), 1, 0, match="tracker masks")
    # leak filter: masklet 5 is small on frames 0-2 and balloons on frame 3, where it would
    # attach the floating hand (instance 4) to the rig
    inst2 = {"frame": np.array([0, 1, 2, 3, 3]), "prompt": np.array([1, 1, 1, 1, 0]), "obj": np.array([5, 5, 5, 5, 6]),
             "masks": np.stack([_box(20, 22, 25, 27), _box(20, 22, 25, 27), _box(20, 22, 25, 27),
                                _box(20, 48, 25, 50), _box(40, 44, 50, 54)])}
    _, keep, dropped = S.combine(inst2, ["hand", "cable"], trk, held_ok, (), 1, -1)
    assert keep.tolist() == [True, True, True, True, True]
    parts, keep, dropped = S.combine(inst2, ["hand", "cable"], trk, held_ok, (), 1, -1, leak_ratio=3.0)
    assert keep.tolist() == [True, True, True, False, False]
    assert (dropped[3] == (inst2["masks"][3] | inst2["masks"][4])).all() and not parts[3, 3:].any()
    # split_components: one instance = a piece attached to the rig + a separate piece far away
    two = _box(20, 30, 25, 28) | _box(40, 44, 50, 60)
    inst3 = {"frame": np.array([0]), "prompt": np.array([1]), "obj": np.array([1]), "masks": two[None]}
    parts, keep, dropped = S.combine(inst3, ["hand", "cable"], trk, held_ok, (), 1, -1)
    assert keep.tolist() == [True] and (parts[0, 4] == two).all() and not dropped.any()
    parts, keep, dropped = S.combine(inst3, ["hand", "cable"], trk, held_ok, (), 1, -1, split_components=True)
    assert keep.tolist() == [True] and (parts[0, 4] == _box(20, 30, 25, 28)).all()
    assert (dropped[0] == _box(40, 44, 50, 60)).all()
    assert len(S.components(two)) == 2 and len(S.components(np.zeros((H, W), bool))) == 0


# ---------------------------------------------------------------------------- impl params / config
def test_check_params():
    p = copy.deepcopy(R.get("masks", "sam3_v2").params)
    text, seeds, pts = I.check_params(p)
    assert text == ["hand", "arm", "cable"] and seeds == ["hand", "arm"] and pts["rig_points"][0] == "ball"

    def bad(key, value, match):
        q = copy.deepcopy(p)
        q[key] = value
        _raises(ValueError, I.check_params, q, match=match)
    bad("seed_prompts", ["leg"], "subset")
    bad("text_prompts", ["hand", "hand"], "distinct")
    bad("text_prompts", ["hand", "arm", "held"], "tracker part names")
    bad("rig_points", [], "at least one")
    bad("rig_points", ["wrist"], "rig_points")
    bad("held_points", [[0.1, 0.2]], "held_points")
    bad("prompt_every", 0, "prompt_every")
    bad("attach_px", -1, "attach_px")
    bad("border_px", -2, "border_px")
    bad("leak_ratio", -1.0, "leak_ratio")
    bad("leak_ratio", True, "leak_ratio")
    bad("split_components", 1, "split_components")
    bad("held_after_open", "yes", "held_after_open")
    bad("held_width_max", 0.0, "held_width_max")
    bad("width_tol_s", 0, "width_tol_s")
    q = copy.deepcopy(p)
    q["held_points"], q["held_width_max"] = [], 0.0      # no held object: the threshold is unused
    I.check_params(q)
    q["text_prompts"], q["seed_prompts"] = [], []
    I.check_params(q)


def test_exp006_config_uses_registry_defaults():
    cfg_path = Path(SP.REPO) / "experiments/exp006_sam3_v2/config.yaml"
    if not cfg_path.exists():
        return
    order, an = SP.build(yaml.safe_load(open(cfg_path)))
    by = {n.id: n for n in order}
    m = by["masks.motion"]
    assert m.impl is R.get("masks", "sam3_v2")
    assert m.params == SP.normalize_params(m.impl.params, m.impl.params)
    assert by["masks.sam2"].impl is R.get("masks", "sam2_points")
    assert sorted(i for i in by if i.startswith("slam.")) == ["slam.E1", "slam.E3"]
    assert by["slam.E3"].deps["masks"] == ["masks.motion", "masks.tiles"]


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
