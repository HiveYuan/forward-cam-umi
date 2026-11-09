"""Analysis step mask_compare (slam.pipeline.impl_mask_compare) on synthetic segments in a
temporary view (python -m slam.tests.test_mask_compare):

  - per-frame IoU / recall / precision / extra / missed area on hand-built masks with known
    values, including the empty-mask conventions (0 / 0 = 1);
  - cells_iou: the DROID-invalid cell rule equals slam.scale._valid_cells (negated), and the
    dilation by dilate_px changes the cell agreement as computed by hand;
  - worst frames, pooled summary, worst segments, segments below IoU 0.8;
  - overlay selection: half evenly spaced, half lowest IoU, no duplicates;
  - the whole step through a worker Job: output files and keys of the contract, overlays
    next to the results directory (stale ones removed), candidates with and without parts.
"""
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from slam import config as C
from slam.pipeline import impl_mask_compare as M
from slam.pipeline.worker import Job

SESSION = "synth"
W, H = 64, 48
N = W * H


# ---------------------------------------------------------------------- helpers
@contextmanager
def _view():
    """Temporary view root as slam.config.WORK -> (segments dir, variant dir)."""
    old_work, old_sess = C.WORK, dict(C.SESSIONS)
    with tempfile.TemporaryDirectory() as tmp:
        variant = Path(tmp) / "runs" / "expT" / "main"
        C.WORK = variant / "view"
        C.SESSIONS[SESSION] = {"head_stem": "x", "intrinsics": "x", "glove": "yosub", "tile_layout": "x"}
        try:
            yield C.segments_dir(SESSION), variant
        finally:
            C.WORK = old_work
            C.SESSIONS.clear()
            C.SESSIONS.update(old_sess)


def _box(r0, r1, c0, c1, w=W, h=H):
    m = np.zeros((h, w), bool)
    m[r0:r1, c0:c1] = True
    return m


def _save_mask(path, masked, parts=None, names=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    kw = {"masked": np.packbits(np.asarray(masked, bool), axis=-1), "meta": json.dumps({})}
    if parts is not None:
        parts = np.asarray(parts, bool)
        kw.update(parts=np.packbits(parts, axis=-1), part_names=np.array(names),
                  obj_frac=parts.mean((2, 3)))
    np.savez_compressed(path, **kw)


def _write_seg(seg_dir, ref, cand, parts=None, names=None, w=W, h=H, images=False, ref_name="ref",
               cand_name="cand"):
    """A segment in the legacy layout: frames.json, masks/<ref_name>.npz (no parts),
    masks/<cand_name>.npz (with parts if given; masked = their union), optional images."""
    ref, T = np.asarray(ref, bool), len(ref)
    seg_dir.mkdir(parents=True, exist_ok=True)
    json.dump({"size": [w, h], "frames": [{"i": i} for i in range(T)]}, open(seg_dir / "frames.json", "w"))
    _save_mask(seg_dir / "masks" / f"{ref_name}.npz", ref)
    if parts is not None:
        parts = np.asarray(parts, bool)
        cand = parts.any(1)
    _save_mask(seg_dir / "masks" / f"{cand_name}.npz", cand, parts, names)
    if images:
        import cv2
        (seg_dir / "images").mkdir(exist_ok=True)
        rng = np.random.default_rng(0)
        for i in range(T):
            cv2.imwrite(str(seg_dir / "images" / f"{i:06d}.jpg"), rng.integers(0, 255, (h, w, 3), np.uint8))


def _known_frames():
    """(ref, cand, expected per-frame values) of six hand-built frames (H x W = 48 x 64)."""
    a = _box(10, 20, 10, 20)                      # 100 px
    rows = [
        # ref, cand, iou, recall, precision, extra px, missed px
        (a, _box(10, 20, 15, 25), 50 / 150, 0.5, 0.5, 50, 50),     # half overlap
        (np.zeros_like(a), np.zeros_like(a), 1.0, 1.0, 1.0, 0, 0),  # both empty
        (a, np.zeros_like(a), 0.0, 0.0, 1.0, 0, 100),              # candidate empty
        (np.zeros_like(a), a, 0.0, 1.0, 0.0, 100, 0),              # reference empty
        (a, a, 1.0, 1.0, 1.0, 0, 0),                               # identical
        (a, _box(10, 20, 10, 30), 0.5, 1.0, 0.5, 100, 0),          # candidate superset
    ]
    ref = np.stack([r[0] for r in rows])
    cand = np.stack([r[1] for r in rows])
    exp = {"iou": [r[2] for r in rows], "recall": [r[3] for r in rows], "precision": [r[4] for r in rows],
           "extra_area": [r[5] / N for r in rows], "missed_area": [r[6] / N for r in rows]}
    return ref, cand, exp


def _close(a, b, tol=1e-12):
    assert np.allclose(np.asarray(a, float), np.asarray(b, float), atol=tol, rtol=0), (a, b)


# ---------------------------------------------------------------------- tests
def test_stat_and_ratio():
    s = M.stat([1.0, 2.0, 3.0, 4.0, float("nan")])
    assert set(s) == {"n", "median", "p10", "p90", "mean"} and s["n"] == 4
    _close([s["median"], s["mean"], s["p10"], s["p90"]], [2.5, 2.5, 1.3, 3.7])
    assert M.stat([]) == {"n": 0, "median": None, "p10": None, "p90": None, "mean": None}
    _close(M.ratio([0, 1, 0], [0, 2, 5]), [1.0, 0.5, 0.0])


def test_known_per_frame_values():
    ref, cand, exp = _known_frames()
    with _view() as (segs, _):
        _write_seg(segs / "ep00", ref, cand)
        f = M.compare_segment(segs / "ep00", "ref", "cand", 0)
    for k, v in exp.items():
        _close(f[k], v)
    _close(f["area_ref"], ref.sum((1, 2)) / N)
    _close(f["area_cand"], cand.sum((1, 2)) / N)
    assert f["part_names"] == [] and f["part_area"].shape == (6, 0)
    # cells without dilation: frame 0 boxes cover cols 10..19 / 15..24 -> cells 1..2 / 1..3 (rows 1..2)
    _close(f["cells_iou"], [4 / 6, 1.0, 0.0, 0.0, 1.0, 4 / 6])
    # the JSON block of the segment
    b = M.segment_summary(f)
    assert list(b) == ["frames", "iou", "recall", "precision", "area_ref", "area_cand", "extra_area",
                       "missed_area", "cells_iou", "part_area", "worst_frames"]
    assert b["frames"] == 6 and b["part_area"] == {}
    for k in ("iou", "recall", "precision", "extra_area", "missed_area"):
        assert b[k]["n"] == 6
        _close(b[k]["median"], np.median(exp[k]))
        _close(b[k]["mean"], np.mean(exp[k]))
    _close(b["area_ref"], ref.sum() / (6 * N))
    # 5 lowest IoU, ascending, ties in frame order: frames 2, 3 (0.0), 0 (1/3), 5 (0.5), then 1 (1.0)
    assert [w[0] for w in b["worst_frames"]] == [2, 3, 0, 5, 1]
    _close([w[1] for w in b["worst_frames"]], [0.0, 0.0, 1 / 3, 0.5, 1.0])


def test_cells_rule_equals_legacy():
    """invalid_cells == ~slam.scale._valid_cells on random blobs, for several dilations."""
    import cv2
    from slam import scale as SC
    rng = np.random.default_rng(1)
    w, h, T = 96, 64, 5
    m = np.zeros((T, h, w), bool)
    for i in range(T):
        for _ in range(3):
            cv2.circle(m[i].view(np.uint8), (int(rng.integers(0, w)), int(rng.integers(0, h))),
                       int(rng.integers(1, 12)), 1, -1)
    m[0] = False                                    # an empty frame
    m[1, 0, 0] = m[1, h - 1, w - 1] = True           # single pixels at the corners
    with _view() as (segs, _):
        seg = segs / "ep00"
        _save_mask(seg / "masks" / "x.npz", m)
        for d in (0, 1, 3, 8):
            legacy = SC._valid_cells(seg, ["x"], T, (w, h), d)
            assert np.array_equal(M.invalid_cells(m, d), ~legacy), d


def test_cells_iou_dilation():
    """Two single pixels 8 px apart: pixel IoU 0; cells IoU 0 undilated, 6/12 dilated by 8."""
    ref = np.zeros((1, H, W), bool)
    cand = np.zeros((1, H, W), bool)
    ref[0, 20, 20] = True                    # cell (2, 2); dilated rows/cols 12..28 -> cells 1..3 x 1..3
    cand[0, 20, 28] = True                   # cell (2, 3); dilated cols 20..36 -> cells 1..3 x 2..4
    with _view() as (segs, _):
        _write_seg(segs / "ep00", ref, cand)
        f0 = M.compare_segment(segs / "ep00", "ref", "cand", 0)
        f8 = M.compare_segment(segs / "ep00", "ref", "cand", 8)
        f3 = M.compare_segment(segs / "ep00", "ref", "cand", 3)
    _close(f0["iou"], [0.0])
    _close(f8["iou"], [0.0])
    _close(f0["cells_iou"], [0.0])
    _close(f8["cells_iou"], [6 / 12])
    # dilated by 3: ref cols 17..23 -> cells 2; cand cols 25..31 -> cell 3; rows 17..23 -> cell 2
    _close(f3["cells_iou"], [0.0])


def test_parts_area():
    T = 4
    hand = np.stack([_box(0, 8, 0, 8)] * T)            # 64 px
    glove = np.stack([_box(0, 8, 4, 20)] * T)          # 128 px, overlaps hand by 32
    glove[1] = False
    ref = np.stack([_box(0, 8, 0, 20)] * T)
    with _view() as (segs, _):
        _write_seg(segs / "ep00", ref, None, parts=np.stack([hand, glove], 1), names=["hand", "glove"])
        f = M.compare_segment(segs / "ep00", "ref", "cand", 8)
    assert f["part_names"] == ["hand", "glove"]
    _close(f["part_area"][:, 0], [64 / N] * T)
    _close(f["part_area"][:, 1], [128 / N, 0, 128 / N, 128 / N])
    _close(f["area_cand"], [160 / N, 64 / N, 160 / N, 160 / N])      # the union
    b = M.segment_summary(f)
    _close([b["part_area"]["hand"], b["part_area"]["glove"]], [64 / N, 96 / N])


def test_pooled_summary():
    """Two segments: pooled stats over all frames, worst segments, segments below 0.8."""
    a = _box(10, 20, 10, 20)
    good = (np.stack([a] * 4), np.stack([a] * 4))                       # IoU 1 x4
    half = _box(10, 20, 15, 25)
    bad = (np.stack([a] * 3), np.stack([half, half, a]))              # IoU 1/3, 1/3, 1
    with _view() as (segs, _):
        _write_seg(segs / "ep00", *good)
        _write_seg(segs / "ep01", *bad, parts=np.stack([half, half, a])[:, None], names=["hand"])
        per = {s: M.compare_segment(segs / s, "ref", "cand", 8) for s in ("ep00", "ep01")}
    sm = M.pooled_summary(per, ["ep00", "ep01"])
    assert list(sm) == ["frames", "iou", "recall", "precision", "extra_area", "missed_area", "cells_iou",
                        "area_ref", "area_cand", "part_area", "segments_iou_median_below_0.8", "worst_segments"]
    assert sm["frames"] == 7 and sm["iou"]["n"] == 7
    iou = [1, 1, 1, 1, 1 / 3, 1 / 3, 1]
    _close([sm["iou"]["median"], sm["iou"]["mean"], sm["iou"]["p10"]],
           [np.median(iou), np.mean(iou), np.percentile(iou, 10)])
    assert sm["segments_iou_median_below_0.8"] == ["ep01"]
    assert [s for s, _ in sm["worst_segments"]] == ["ep01", "ep00"]
    _close([m for _, m in sm["worst_segments"]], [1 / 3, 1.0])
    # part area: frame-weighted over the segments that have the part (ep01 only)
    assert list(sm["part_area"]) == ["hand"]
    _close(sm["part_area"]["hand"], 100 / N)
    _close(sm["area_ref"], 100 / N)


def test_select_overlays():
    iou = np.array([0.9, 0.2, 0.95, 0.1, 0.8, 0.85, 0.3, 0.99, 0.97, 0.96])   # T = 10
    sel = M.select_overlays(iou, 4)
    # even: bin centres of 2 bins -> rows 2 (T/4 = 2.5) and 7; worst: 3 (0.1), 1 (0.2)
    assert sel == [(2, "even"), (7, "even"), (3, "worst"), (1, "worst")], sel
    # a worst frame that is already an even one is skipped (no duplicates): lowest at row 7
    iou2 = iou.copy()
    iou2[7] = 0.0
    sel = M.select_overlays(iou2, 4)
    assert sel == [(2, "even"), (7, "even"), (3, "worst"), (1, "worst")], sel
    iou3 = iou.copy()
    iou3[2] = 0.05                                    # lowest is even row 2 -> next worst rows 3, 1
    assert M.select_overlays(iou3, 4) == [(2, "even"), (7, "even"), (3, "worst"), (1, "worst")]
    # odd n: n // 2 even, the rest worst
    assert M.select_overlays(iou, 3) == [(5, "even"), (3, "worst"), (1, "worst")]
    assert M.select_overlays(iou, 1) == [(3, "worst")]
    assert M.select_overlays(iou, 0) == []
    # more requested than frames: every frame once
    sel = M.select_overlays(iou[:3], 8)
    assert sorted(k for k, _ in sel) == [0, 1, 2] and len(sel) == 3


def _job(variant, segments, params):
    spec = {"params": params, "node": {"id": "mask_compare", "step": "mask_compare", "name": "mask_compare",
                                       "impl": "default", "key": None},
            "data": {"session": SESSION}, "segments": list(segments), "out_dir": str(variant / "results"),
            "scratch": str(variant / "scratch"), "analysis": {}, "exec": {"jobs": 2}}
    return Job(spec)


def test_run_end_to_end():
    import cv2
    ref, cand, exp = _known_frames()
    T = len(ref)
    hand = np.zeros((T, H, W), bool)
    hand[:, 30:40, 30:40] = True
    parts = np.stack([cand, hand], 1)                 # sam3-like: parts, masked = union
    with _view() as (segs, variant):
        for s in ("ep00", "ep01"):
            _write_seg(segs / s, ref, None, parts=parts, names=["arm", "hand"], images=True,
                       ref_name="sam2", cand_name="sam3")
            _save_mask(segs / s / "masks" / "plain.npz", cand)          # no parts
        stale = variant / "overlays" / "sam3_vs_sam2" / "old.jpg"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"x")
        (variant / "results").mkdir(parents=True)
        params = {"reference": "sam2", "candidates": ["sam3", "plain"], "dilate_px": 8, "overlays_per_segment": 4}
        out = M.run_mask_compare(_job(variant, ["ep00", "ep01"], params))
        res = variant / "results"
        assert set(out) == {"sam3", "plain"} and out["sam3"]["frames"] == 2 * T
        assert sorted(p.name for p in res.iterdir()) == ["masks_plain_vs_sam2.json", "masks_plain_vs_sam2.md",
                                                       "masks_sam3_vs_sam2.json", "masks_sam3_vs_sam2.md"]
        r = json.loads((res / "masks_sam3_vs_sam2.json").read_text())
        assert list(r) == ["reference", "candidate", "dilate_px", "parts", "segments", "summary"]
        assert (r["reference"], r["candidate"], r["dilate_px"], r["parts"]) == ("sam2", "sam3", 8, ["arm", "hand"])
        assert list(r["segments"]) == ["ep00", "ep01"]
        b = r["segments"]["ep00"]
        _close(b["part_area"]["hand"], 100 / N)
        # the hand part adds 100 candidate-only px to every frame
        ex = np.array(exp["extra_area"]) + 100 / N
        _close(b["extra_area"]["median"], np.median(ex))
        _close(b["missed_area"]["median"], np.median(exp["missed_area"]))
        assert b["iou"]["n"] == T and r["summary"]["frames"] == 2 * T
        p = json.loads((res / "masks_plain_vs_sam2.json").read_text())
        assert p["parts"] == [] and p["segments"]["ep00"]["part_area"] == {} and p["summary"]["part_area"] == {}
        _close(p["segments"]["ep01"]["iou"]["median"], np.median(exp["iou"]))
        md = (res / "masks_sam3_vs_sam2.md").read_text()
        assert "| ep00 |" in md and "| ep01 |" in md and "| **all** |" in md and "## Summary" in md
        # overlays next to results/, stale files gone, index consistent with the files
        for cand_name in ("sam3", "plain"):
            od = variant / "overlays" / f"{cand_name}_vs_sam2"
            idx = json.loads((od / "index.json").read_text())
            assert len(idx) == 8 and not (od / "old.jpg").exists()
            assert sorted(p.name for p in od.glob("*.jpg")) == sorted(e["file"] for e in idx)
            for e in idx:
                assert set(e) == {"file", "segment", "i", "iou", "kind"} and e["kind"] in ("even", "worst")
                assert e["file"] == f"{e['segment']}_{e['i']:06d}.jpg"
            for s in ("ep00", "ep01"):
                rows = [(e["i"], e["kind"]) for e in idx if e["segment"] == s]
                assert len({i for i, _ in rows}) == 4                         # no duplicates
                assert [k for _, k in rows] == ["even", "even", "worst", "worst"]
                # even rows of T = 6 frames in 2 bins: 1 and 4; worst: lowest IoU not already taken
                assert [i for i, _ in rows[:2]] == [1, 4]
        idx = json.loads((variant / "overlays" / "sam3_vs_sam2" / "index.json").read_text())
        img = cv2.imread(str(variant / "overlays" / "sam3_vs_sam2" / idx[0]["file"]))
        assert img.shape == (720 + 34 + 30, 960, 3), img.shape  # 64x48 frames resized to 960 wide, + title and legend bands
        # params are checked
        for bad in ({**params, "candidates": ["sam2"]}, {**params, "dilate_px": -1},
                    {**params, "overlays_per_segment": 1.5}, {**params, "candidates": []}):
            try:
                M.run_mask_compare(_job(variant, ["ep00"], bad))
                raise AssertionError(f"accepted {bad}")
            except ValueError:
                pass


def test_shape_mismatch_raises():
    ref, cand, _ = _known_frames()
    with _view() as (segs, _):
        _write_seg(segs / "ep00", ref, cand)
        _save_mask(segs / "ep00" / "masks" / "short.npz", cand[:3])
        try:
            M.compare_segment(segs / "ep00", "ref", "short", 8)
            raise AssertionError("a mask with fewer frames than frames.json was accepted")
        except ValueError:
            pass


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
