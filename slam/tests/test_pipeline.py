"""Tests of the experiment framework core (python -m slam.tests.test_pipeline).

Unit tests of hashing, spec, cache, view, worker.Job and runinfo, plus an end-to-end run of
the orchestrator with the cheap fake implementations of slam.tests.fake_impls (env 'venv',
CPU only). Everything is written to temporary directories (set TMPDIR to choose where);
orchestrator.WORK is pointed at a temporary work directory for the end-to-end test.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import yaml

from slam.backends import base as B
from slam.pipeline import cache as CA
from slam.pipeline import hashing as H
from slam.pipeline import orchestrator as O
from slam.pipeline import registry as R
from slam.pipeline import runinfo as RI
from slam.pipeline import spec as SP
from slam.pipeline import view as V
from slam.pipeline import worker as W
from slam.tests import fake_impls as F

EXP001 = SP.REPO / "experiments/exp001_sam2_baseline/config.yaml"


def _raises(exc, fn, *args, match=None, **kw):
    try:
        fn(*args, **kw)
    except exc as e:
        if match is not None:
            assert match in str(e), f"{match!r} not in {str(e)!r}"
        return e
    raise AssertionError(f"{getattr(fn, '__name__', fn)} did not raise {exc.__name__}")


# ====================================================================== hashing
def test_canonical_order_and_types():
    a = {"b": 1, "a": {"y": [1, 2.5, "x"], "x": None}, "c": True}
    b = {"c": True, "a": {"x": None, "y": [1, 2.5, "x"]}, "b": 1}
    assert H.canonical(a) == H.canonical(b)
    assert H.canonical({"p": Path("/a/b"), "t": (1, (2, 3))}) == H.canonical({"t": [1, [2, 3]], "p": "/a/b"})
    assert H.canonical({"x": 5}) != H.canonical({"x": 5.0})          # documented: normalise first
    assert H.canonical([1, 2]) != H.canonical([2, 1])                 # list order is content
    assert H.canonical({"x": True}) != H.canonical({"x": 1})
    assert H.canonical(np.float64(0.1)) == H.canonical(0.1)
    for bad in (float("nan"), float("inf"), -float("inf")):
        _raises(ValueError, H.canonical, {"x": [1.0, {"y": bad}]})
    for bad in (object(), {1, 2}, np.int64(3), np.zeros(2)):
        _raises(TypeError, H.canonical, {"x": bad})


def _key(**over):
    kw = dict(step="slam", impl="droid", version=1,
              params={"a": 1.0, "b": [1, 2], "w": {"p": "x", "s": "y"}},
              data={"video": "sha256:aa", "tags": "sha256:bb"},
              deps={"preprocess": "k1", "masks": ["k2", "k3"]}, tag=None)
    kw.update(over)
    return H.node_key(**kw)


def test_node_key():
    k = _key()
    assert len(k) == H.KEY_LEN and k == _key() and int(k, 16) >= 0
    assert k == _key(params={"w": {"s": "y", "p": "x"}, "b": [1, 2], "a": 1.0},
                     data={"tags": "sha256:bb", "video": "sha256:aa"},
                     deps={"masks": ["k2", "k3"], "preprocess": "k1"})
    assert k == _key(tag="") == _key(version="1")
    changed = [dict(params={"a": 1.5, "b": [1, 2], "w": {"p": "x", "s": "y"}}),
               dict(params={"a": 1.0, "b": [2, 1], "w": {"p": "x", "s": "y"}}),
               dict(version=2), dict(step="depth"), dict(impl="droid2"),
               dict(data={"video": "sha256:ab", "tags": "sha256:bb"}),
               dict(data={"video": "sha256:aa"}),
               dict(deps={"preprocess": "k1", "masks": ["k2"]}),
               dict(deps={"preprocess": "kX", "masks": ["k2", "k3"]}),
               dict(tag="repro1"), dict(tag="repro2")]
    keys = {_key(**c) for c in changed}
    assert k not in keys and len(keys) == len(changed)


def test_quick_file_hash_and_fingerprint():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        data = np.random.default_rng(0).integers(0, 256, 1000, dtype=np.uint8).tobytes()
        a = td / "a.bin"
        a.write_bytes(data)
        b = td / "sub" / "b.bin"
        b.parent.mkdir()
        shutil.copy(a, b)
        os.utime(b, (0, 0))                                   # other name, dir and mtime
        h = H.quick_file_hash(a, chunk=64)
        assert h.startswith("quick:1000:") and H.quick_file_hash(b, chunk=64) == h

        def variant(pos=None, size=None):
            d = bytearray(data)
            if pos is not None:
                d[pos] ^= 1
            b.write_bytes(bytes(d[:size]))
            return H.quick_file_hash(b, chunk=64)
        assert variant(pos=999) != h                          # last byte
        assert variant(pos=1000 - 64) != h                    # first byte of the last chunk
        assert variant(pos=0) != h
        assert variant(size=999) != h                         # truncation
        assert variant(pos=500) == h                          # documented: middle not read
        assert H.quick_file_hash(b, chunk=600) != H.quick_file_hash(a, chunk=600)   # <= 2 chunks: all read
        b.write_bytes(data)
        assert H.quick_file_hash(b, chunk=64) == h

        assert H.file_fingerprint(a) == "sha256:" + hashlib.sha256(data).hexdigest()
        assert H.file_fingerprint(a, quick_above=100).startswith("quick:1000:")
        assert H.file_fingerprint(td / "missing") is None
        _raises(IsADirectoryError, H.file_fingerprint, td)
        assert H.sha256_file(a, chunk=7) == hashlib.sha256(data).hexdigest()


# ====================================================================== spec
def test_normalize_params():
    d = {"a": 1.0, "n": 3, "flag": True, "s": "x", "lst": [0.5, 1.0], "ints": [1, 2],
         "w": {"path": "p", "sha": "h"}, "prompts": {"glove": ["ball"]}, "opt": None, "free": []}
    ok = {"a": 5, "n": 3, "flag": False, "s": "y", "lst": [1, 2.5], "ints": [4], "w": {"sha": "h2", "path": "p2"},
          "prompts": {"hand": [[0, 0, 1]], "other": "anything"}, "opt": "E1", "free": [1, "a"]}
    p = SP.normalize_params(d, ok)
    assert list(p) == list(d)
    assert p["a"] == 5.0 and type(p["a"]) is float
    assert p["lst"] == [1.0, 2.5] and all(type(x) is float for x in p["lst"])
    assert p["w"] == {"path": "p2", "sha": "h2"} and p["opt"] == "E1" and p["free"] == [1, "a"]
    assert p["prompts"] == ok["prompts"] and p["prompts"] is not ok["prompts"]      # free-form, copied
    def canon(**kw):
        return H.canonical(SP.normalize_params(d, {**ok, **kw}))
    assert canon(a=5) == canon(a=5.0) and canon(lst=[1, 2]) == canon(lst=[1.0, 2.0])
    assert H.node_key("s", "i", 1, SP.normalize_params(d, {**ok, "a": 5}), {}, {}) == \
        H.node_key("s", "i", 1, SP.normalize_params(d, {**ok, "a": 5.0}), {}, {})

    given = {k: v for k, v in ok.items() if k not in ("n", "s")}
    e = _raises(SP.ConfigError, SP.normalize_params, d, {**given, "zz": 1, "yy": 2}, "slam.E3.params")
    assert "slam.E3.params" in str(e) and "missing n (default 3), s (default 'x')" in str(e)
    assert "unknown zz, yy" in str(e)
    _raises(SP.ConfigError, SP.normalize_params, d, {**ok, "w": {"path": "p"}}, match="params.w")
    _raises(SP.ConfigError, SP.normalize_params, d, None, match="missing")
    _raises(SP.ConfigError, SP.normalize_params, d, [1], match="mapping")
    assert SP.normalize_params({}, None) == {}
    for k, v in (("flag", 1), ("flag", "true"), ("a", True), ("a", "5"), ("n", True), ("n", 3.0),
                 ("s", 1), ("lst", 0.5), ("lst", [1, True]), ("ints", [1.5]), ("prompts", ["ball"]),
                 ("w", "p"), ("free", {})):
        _raises(SP.ConfigError, SP.normalize_params, d, {**ok, k: v}, match=f"params.{k}")


def _exp001():
    return yaml.safe_load(EXP001.read_text())


def test_build_exp001():
    order, an = SP.build(_exp001())
    ids = [n.id for n in order]
    assert sorted(ids) == sorted(["preprocess", "tiles", "masks.motion", "masks.tiles", "slam.E1",
                                  "slam.E3", "depth.da2@E3"])
    pos = {nid: i for i, nid in enumerate(ids)}
    for n in order:
        assert all(pos[d] < pos[n.id] for d in n.dep_ids()), n.id
    by = {n.id: n for n in order}
    assert by["tiles"].deps == {"preprocess": "preprocess"}
    assert by["masks.motion"].deps == {"preprocess": "preprocess"}
    assert by["masks.tiles"].deps == {"preprocess": "preprocess", "tiles": "tiles", "slam_fallback": "slam.E1"}
    assert by["slam.E1"].deps == {"preprocess": "preprocess", "masks": []}
    assert by["slam.E3"].deps == {"preprocess": "preprocess", "masks": ["masks.motion", "masks.tiles"]}
    assert by["depth.da2@E3"].deps == {"preprocess": "preprocess", "slam": "slam.E3"}
    assert by["depth.da2@E3"].name == "da2" and by["slam.E3"].name == "E3"
    assert by["slam.E3"].impl is R.get("slam", "droid")
    assert by["masks.tiles"].params["slam_fallback"] == "E1"
    assert type(by["slam.E3"].params["keyframe_thresh"]) is float and by["slam.E3"].params["frontend_window"] == 25
    sc = an["scale"]["E3"]
    assert sc["primary"] == "B" and sc["checks"] == ["A"] and sc["flag_threshold"] == 0.1
    assert sc["methods"]["B"]["_depth_node"] == "depth.da2@E3" and sc["methods"]["A"]["min_frames"] == 10
    assert an["labels"]["runs"] == ["E3"] and an["evaluate"]["runs"] == ["E1", "E3"]
    assert an["evaluate"]["params"]["dts"][-1] == 6.67 and an["report"]["params"]["compare"] == ["exp000_legacy"]
    assert set(an["scale"]) == {"E3"}


def _bad(mutate, match, exc=SP.ConfigError):
    cfg = _exp001()
    mutate(cfg)
    return _raises(exc, SP.build, cfg, match=match)


def test_build_errors():
    def setp(path, value):
        def f(c):
            d = c
            for k in path[:-1]:
                d = d[k]
            d[path[-1]] = value
        return f

    def delp(*path):
        def f(c):
            d = c
            for k in path[:-1]:
                d = d[k]
            del d[path[-1]]
        return f
    _bad(setp(("masks", "motion", "impl"), "sam9"), "sam9")
    _bad(setp(("slam", "E3", "impl"), "orb"), "orb")
    _bad(delp("masks", "motion", "impl"), "masks.motion")
    _bad(delp("slam", "E3", "params", "seed"), "missing seed")
    _bad(setp(("slam", "E3", "masks"), ["motion", "nope"]), "slam.E3.masks")
    _bad(setp(("slam", "E3", "masks"), "motion"), "slam.E3.masks")
    _bad(setp(("slam", "E3", "masks"), ["motion", "motion"]), "duplicate")
    _bad(setp(("masks", "tiles", "params", "slam_fallback"), "E3"), "dependency cycle")       # E3 uses masks.tiles
    _bad(setp(("masks", "tiles", "params", "slam_fallback"), "E7"), "slam_fallback")
    _bad(delp("tiles"), "needs the 'tiles' step")
    _bad(setp(("depth", "da2", "runs"), ["E9"]), "depth.da2.runs")
    _bad(setp(("scale", "E3", "primary"), "tiles"), "evaluation oracle")
    _bad(setp(("scale", "E3", "primary"), "Z"), "scale.E3.primary")
    _bad(setp(("scale", "E3", "checks"), ["tiles"]), "scale.E3.checks")
    _bad(setp(("scale", "E3", "checks"), ["B"]), "scale.E3.checks")
    _bad(delp("scale", "E3", "flag_threshold"), "flag_threshold")
    _bad(delp("scale", "E3", "methods", "A"), "scale.E3.methods")                              # missing
    _bad(setp(("scale", "E3", "methods", "tiles"), {}), "scale.E3.methods")                    # extra
    _bad(delp("scale", "E3", "methods", "B", "z_max"), "missing z_max")
    _bad(setp(("scale", "E3", "unknown"), 1), "unknown keys")
    _bad(lambda c: c["scale"].__setitem__("E9", c["scale"].pop("E3")), "no slam run 'E9'")
    _bad(setp(("scale", "E3", "methods", "B", "depth"), "nope"), "no depth node 'nope'")
    _bad(delp("depth"), "no depth node 'da2' for run E3")
    _bad(setp(("depth", "da2", "runs"), ["E1"]), "no depth node 'da2' for run E3")              # per run
    _bad(setp(("labels", "runs"), ["E9"]), "labels.runs")
    _bad(setp(("evaluate", "runs"), ["E1", "E9"]), "evaluate.runs")
    _bad(setp(("evaluate", "params", "gt_noise"), 1), "gt_noise")
    _bad(setp(("maskz",), {}), "unknown top-level keys")
    _bad(delp("experiment"), "experiment")
    _bad(delp("data", "gt_dir"), "data: missing")
    _bad(setp(("data", "extra"), 1), "unknown")
    _bad(setp(("data", "episodes"), "some"), "data.episodes")
    _bad(delp("slam"), "missing 'slam'")
    # a misspelt block key would otherwise be ignored silently (e.g. E3 run without masks)
    _bad(lambda c: c["slam"]["E3"].__setitem__("mask", c["slam"]["E3"].pop("masks")), "slam.E3")
    _bad(setp(("depth", "da2", "run"), ["E3"]), "depth.da2")
    _bad(setp(("masks", "motion", "param"), {}), "masks.motion")
    _bad(setp(("labels", "run"), ["E3"]), "labels")
    # without the scale/analysis blocks the producer graph alone is valid
    c = _exp001()
    for k in ("scale", "labels", "evaluate", "report", "depth"):
        del c[k]
    order, an = SP.build(c)
    assert len(order) == 6 and an == {"scale": {}, "labels": None, "evaluate": None, "report": None}


def _fps(cfg, code_state="abc"):
    """Synthetic fingerprints: every data file, and per implementation its code (the DROID
    impl also carries the third-party checkout state `code_state`)."""
    data = {k: f"sha256:{k}" for k in SP.data_files(cfg["data"])}
    code = {}
    for impl in R.IMPLS.values():
        f = {f"src:{p}": f"ast:{p}" for p in impl.code_files}
        f.update({f"git:{c}": {"commit": code_state, "dirty": False} for c in impl.code_inputs})
        code[SP.impl_id(impl)] = f
    return data, code


def _keys(cfg, tags=None, data=None, code=None):
    order, _ = SP.build(cfg)
    d0, c0 = _fps(cfg)
    SP.compute_keys(order, data or d0, code or c0, tags)
    return {n.id: n.key for n in order}


def _diff(a, b):
    return {k for k in a if a[k] != b[k]}


def test_compute_keys_share_upstream():
    base = _keys(_exp001())
    assert len(set(base.values())) == len(base)
    c = _exp001()
    c["slam"]["E3"]["params"]["keyframe_thresh"] = 3.5
    assert _diff(base, _keys(c)) == {"slam.E3", "depth.da2@E3"}
    c = _exp001()
    c["slam"]["E1"]["params"]["beta"] = 0.2
    assert _diff(base, _keys(c)) == {"slam.E1", "masks.tiles", "slam.E3", "depth.da2@E3"}
    c = _exp001()
    c["masks"]["motion"]["params"]["prompt_every"] = 15
    assert _diff(base, _keys(c)) == {"masks.motion", "slam.E3", "depth.da2@E3"}
    c = _exp001()
    c["preprocess"]["params"]["jpg_quality"] = 90
    assert _diff(base, _keys(c)) == set(base)
    c = _exp001()                                     # spelling, order, exec and analysis: not hashed
    c["slam"]["E3"]["params"]["keyframe_thresh"] = 4
    c["slam"]["E3"]["masks"] = ["tiles", "motion"]
    c["slam"]["E3"]["params"] = dict(reversed(list(c["slam"]["E3"]["params"].items())))
    c["exec"] = {"jobs": 2}
    c["evaluate"]["params"]["fail_deg"] = 3.0
    c["scale"]["E3"]["flag_threshold"] = 0.2
    c["description"] = "other words"
    assert _keys(c) == base
    data, code = _fps(_exp001())
    assert _diff(base, _keys(_exp001(), data={**data, "handeye": "sha256:new"})) == {
        "masks.motion", "slam.E3", "depth.da2@E3"}
    assert _diff(base, _keys(_exp001(), data={**data, "video": "sha256:new"})) == set(base)
    assert _diff(base, _keys(_exp001(), data={**data, "gt_gripper_wrist": "sha256:new"})) == set()
    assert _diff(base, _keys(_exp001(), code=_fps(_exp001(), "def")[1])) == {
        "slam.E1", "masks.tiles", "slam.E3", "depth.da2@E3"}
    assert _diff(base, _keys(_exp001(), tags={"slam.E3": "repro1"})) == {"slam.E3", "depth.da2@E3"}
    assert _diff(base, _keys(_exp001(), tags={"slam.E1": "repro1"})) == {
        "slam.E1", "masks.tiles", "slam.E3", "depth.da2@E3"}
    r1, r2 = _keys(_exp001(), tags={"slam.E3": "repro1"}), _keys(_exp001(), tags={"slam.E3": "repro2"})
    assert r1["slam.E3"] != r2["slam.E3"] and r1["slam.E1"] == r2["slam.E1"]


def test_rename_does_not_change_keys():
    base = _keys(_exp001())
    c = _exp001()
    c["masks"] = {"dyn": c["masks"]["motion"], "tilegeo": c["masks"]["tiles"]}
    c["masks"]["tilegeo"]["params"]["slam_fallback"] = "nomask"
    c["slam"] = {"nomask": c["slam"]["E1"], "main": c["slam"]["E3"]}
    c["slam"]["main"]["masks"] = ["dyn", "tilegeo"]
    c["depth"] = {"depthB": {**c["depth"]["da2"], "runs": ["main"]}}
    c["scale"] = {"main": c["scale"]["E3"]}
    c["scale"]["main"]["methods"]["B"]["depth"] = "depthB"
    c["labels"]["runs"] = ["main"]
    c["evaluate"]["runs"] = ["nomask", "main"]
    k = _keys(c)
    ren = {"preprocess": "preprocess", "tiles": "tiles", "masks.motion": "masks.dyn",
           "masks.tiles": "masks.tilegeo", "slam.E1": "slam.nomask", "slam.E3": "slam.main",
           "depth.da2@E3": "depth.depthB@main"}
    assert set(k) == set(ren.values())
    for old, new in ren.items():
        assert base[old] == k[new], (old, new)
    # the fallback still matters through the key of the run it names
    c = _exp001()
    c["slam"]["E1"]["masks"] = ["motion"]
    assert {"masks.tiles", "slam.E3"} <= _diff(base, _keys(c))
    c = _exp001()
    c["masks"]["tiles"]["params"]["slam_fallback"] = None
    assert _diff(base, _keys(c)) == {"masks.tiles", "slam.E3", "depth.da2@E3"}


def test_descendants():
    order, _ = SP.build(_exp001())
    ids = {n.id for n in order}
    assert SP.descendants(order, "preprocess") == ids
    assert SP.descendants(order, "slam.E1") == {"slam.E1", "masks.tiles", "slam.E3", "depth.da2@E3"}
    assert SP.descendants(order, "masks.motion") == {"masks.motion", "slam.E3", "depth.da2@E3"}
    assert SP.descendants(order, "tiles") == {"tiles", "masks.tiles", "slam.E3", "depth.da2@E3"}
    assert SP.descendants(order, "slam.E3") == {"slam.E3", "depth.da2@E3"}
    assert SP.descendants(order, "depth.da2@E3") == {"depth.da2@E3"}


# ====================================================================== cache
def test_cache_publish_and_manifest():
    with tempfile.TemporaryDirectory() as td:
        d = CA.node_dir(td, "slam", "0123456789abcdef")
        assert d == Path(td) / "cache" / "slam" / "0123456789abcdef"
        assert CA.missing_segments(d, ["ep00", "ep01"]) == ["ep00", "ep01"]       # entry absent
        t = CA.tmp_dir(d, "ep00")
        (t / "traj.npz").write_text("first")
        assert CA.done_segments(d) == set()                                     # tmp is not a segment
        final = CA.commit_segment(d, "ep00", t)
        assert final == d / "ep00" and not t.exists() and (final / "traj.npz").read_text() == "first"
        assert CA.done_segments(d) == {"ep00"} and CA.missing_segments(d, ["ep00", "ep01"]) == ["ep01"]
        t2 = CA.tmp_dir(d, "ep00")                                              # a second publisher
        (t2 / "traj.npz").write_text("second")
        assert CA.commit_segment(d, "ep00", t2) == final
        assert (final / "traj.npz").read_text() == "first" and not t2.exists()
        assert sorted(p.name for p in d.iterdir()) == ["ep00"]
        t3 = CA.tmp_dir(d, "ep01")
        (t3 / "x").write_text("1")
        assert CA.tmp_dir(d, "ep01") == t3 and not (t3 / "x").exists()          # fresh each time
        (d / "ep1").mkdir()
        (d / "ep001").mkdir()
        (d / "ep02.txt").write_text("")
        assert CA.done_segments(d) == {"ep00"}
        CA.clean_tmp(d)
        assert not list(d.glob(".tmp-*"))
        _raises(OSError, CA.commit_segment, d, "ep05", d / ".tmp-missing")

        m = {"step": "slam", "impl": "droid", "version": 1, "params": {"a": 1.0, "b": [1, 2]},
             "data": {"v": "sha256:1"}, "deps": {"preprocess": "k1", "masks": []}, "tag": None, "key": "k",
             "created": {"experiment": "e1"}}
        assert CA.write_manifest(d, m) == m
        assert json.load(open(d / "manifest.json")) == m
        m2 = {**m, "created": {"experiment": "e2"}}                             # not identity
        assert CA.write_manifest(d, m2)["created"] == {"experiment": "e1"}
        assert CA.write_manifest(d, {**m, "params": {"b": [1, 2], "a": 1.0}}) == m
        for k, v in (("params", {"a": 2.0, "b": [1, 2]}), ("version", 2), ("data", {}), ("tag", "repro1"),
                     ("deps", {"preprocess": "k2", "masks": []}), ("impl", "x"), ("step", "depth")):
            _raises(RuntimeError, CA.write_manifest, d, {**m, k: v}, match=f"'{k}'")
        assert json.load(open(d / "manifest.json")) == m
        assert not list(d.glob(".manifest-*"))


def test_cache_lock():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "cache" / "x" / "k"
        with CA.lock(d):
            assert (d / ".lock").exists()
            _raises(TimeoutError, lambda: CA.lock(d, wait_s=0).__enter__())
            code = ("import sys; from slam.pipeline import cache as CA\n"
                    "try:\n    CA.lock(sys.argv[1], wait_s=0).__enter__()\nexcept TimeoutError:\n    sys.exit(3)\n")
            r = subprocess.run([O.E.python("venv"), "-c", code, str(d)], cwd=SP.REPO,
                               env=dict(os.environ, PYTHONPATH=str(SP.REPO)))
            assert r.returncode == 3                                            # another process waits
        with CA.lock(d, wait_s=0):                                              # released
            pass


# ====================================================================== view
def _write_pre_seg(d, n=3, W=16, H=8):
    d.mkdir(parents=True)
    (d / "images").mkdir()
    for i in range(n):
        (d / "images" / f"{i:06d}.jpg").write_bytes(b"jpg")
    (d / "frames.json").write_text(json.dumps({"size": [W, H], "K": np.eye(3).tolist(),
                                               "frames": [{"i": i, "k": 10 + i, "wall": 1.0 + i} for i in range(n)]}))
    (d / "calib.txt").write_text("1 1 0 0\n")
    np.savez(d / "gt.npz", cam_k=np.arange(n))


def _fake_cache(root, segs):
    """Cache entries of every step type: {label: entry}."""
    ents = {"pre": {"step": "preprocess", "name": "preprocess"}, "tiles": {"step": "tiles", "name": "tiles"},
            "m1": {"step": "masks", "name": "motion"}, "m2": {"step": "masks", "name": "tiles"},
            "s1": {"step": "slam", "name": "E1"}, "s3": {"step": "slam", "name": "E3"},
            "dep": {"step": "depth", "name": "da2", "run": "E3", "model": "da2-metric-indoor-large"}}
    for i, (lab, e) in enumerate(ents.items()):
        e["key"] = f"{i:016x}"
        e["dir"] = str(CA.node_dir(root, e["step"], e["key"]))
        for seg in segs:
            sd = Path(e["dir"]) / seg
            if e["step"] == "preprocess":
                _write_pre_seg(sd)
            else:
                sd.mkdir(parents=True)
                (sd / V.OUTPUT_FILE[e["step"]]).write_text(f"{lab} {seg}")
    return ents


def test_view_build_layout():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        segs = ["ep00", "ep02"]
        ents = _fake_cache(td / "work", segs)
        gt = td / "gt"
        gt.mkdir()
        root = td / "view"
        segs_root = V.build(root, "sess", segs, gt, list(ents.values()))
        assert segs_root == root / "sess" / "segments" and (root / ".slam_view").exists()
        assert (root / "sess" / "gt").is_symlink() and os.readlink(root / "sess" / "gt") == str(gt)
        for seg in segs:
            sd = segs_root / seg
            want = {"images": ("pre", "images"), "frames.json": ("pre", "frames.json"),
                    "calib.txt": ("pre", "calib.txt"), "gt.npz": ("pre", "gt.npz"),
                    "tiles.npz": ("tiles", "tiles.npz"), "masks/motion.npz": ("m1", "masked.npz"),
                    "masks/tiles.npz": ("m2", "masked.npz"), "slam/E1.npz": ("s1", "traj.npz"),
                    "slam/E3.npz": ("s3", "traj.npz"),
                    "depth/E3_da2-metric-indoor-large.npz": ("dep", "depth.npz")}
            for rel, (lab, f) in want.items():
                p = sd / rel
                assert p.is_symlink() and os.readlink(p) == str(Path(ents[lab]["dir"]) / seg / f), rel
            files = sorted(str(p.relative_to(sd)) for p in sd.rglob("*") if p.is_symlink())
            assert files == sorted(want), files
            assert (sd / "slam/E3.npz").read_text() == f"s3 {seg}"
            assert len(list((sd / "images").iterdir())) == 3
        # rebuild in place (fresh=False) with another masks entry: the stale link is replaced
        new = dict(ents["m1"], key="f" * 16, dir=str(CA.node_dir(td / "work", "masks", "f" * 16)))
        for seg in segs:
            (Path(new["dir"]) / seg).mkdir(parents=True)
            (Path(new["dir"]) / seg / "masked.npz").write_text("new")
        V.build(root, "sess", segs, gt, [new], fresh=False)
        assert (segs_root / "ep00" / "masks/motion.npz").read_text() == "new"
        assert (segs_root / "ep00" / "slam/E3.npz").exists()                    # kept
        V.build(root, "sess", ["ep00"], gt, [ents["pre"]])                       # fresh: old view removed
        assert not (segs_root / "ep02").exists() and not (segs_root / "ep00" / "slam").exists()
        assert Path(ents["s3"]["dir"], "ep00", "traj.npz").exists()             # the cache is untouched
        _raises(FileNotFoundError, V.build, root, "sess", ["ep01"], gt, [ents["pre"]])
        assert V.view_path(ents["dep"], "ep00") == Path("depth/E3_da2-metric-indoor-large.npz")
        _raises(ValueError, V.view_path, {"step": "labels"}, "ep00")


def test_view_refuses_non_view_dir():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ents = _fake_cache(td / "work", ["ep00"])
        gt = td / "gt"
        gt.mkdir()
        precious = td / "data"
        precious.mkdir()
        (precious / "keep.txt").write_text("legacy")
        _raises(RuntimeError, V.build, precious, "sess", ["ep00"], gt, [ents["pre"]], match="not a view")
        assert (precious / "keep.txt").read_text() == "legacy" and not (precious / ".slam_view").exists()


# ====================================================================== worker.Job
def test_worker_job_api():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ents = _fake_cache(td / "work", ["ep00", "ep01"])
        gt = td / "gt"
        gt.mkdir()
        out = CA.node_dir(td / "work", "slam", "9" * 16)
        inputs = {"preprocess": ents["pre"], "masks.motion": ents["m1"], "masks.tiles": ents["m2"]}
        job = W.Job({"params": {"a": 1}, "node": {"id": "slam.E3", "step": "slam", "name": "E3", "impl": "droid",
                                                  "key": "9" * 16},
                     "data": {"session": "sess", "gt_dir": str(gt)}, "segments": ["ep00", "ep01"],
                     "out_dir": str(out), "inputs": inputs, "scratch": str(td / "scratch")})
        assert job.todo() == ["ep00", "ep01"] and job.exec == {} and job.analysis == {}
        v = job.input_view("ep01")
        assert v == td / "scratch" / "view" / "sess" / "segments" / "ep01"
        assert (v / "frames.json").is_symlink() and (v / "masks" / "tiles.npz").read_text() == "m2 ep01"
        assert os.readlink(job.view_root() / "sess" / "gt") == str(gt)
        (v / "junk").write_text("x")
        assert not (job.input_view("ep01") / "junk").exists()                   # rebuilt
        inp = B.load_input(v, [])
        assert len(inp) == 3 and inp.size == (16, 8) and inp.masked is None
        assert list(inp.k) == [10, 11, 12] and inp.images[0] == v / "images" / "000000.jpg"
        t = job.tmp("ep00")
        (t / "traj.npz").write_text("x")
        job.publish("ep00", t)
        assert job.todo() == ["ep01"]
        assert job.input_of("preprocess") is ents["pre"] and job.input_of("masks", "tiles") is ents["m2"]
        _raises(KeyError, job.input_of, "masks")                                # two candidates
        _raises(KeyError, job.input_of, "slam")


def test_backend_io_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        sd = td / "seg"
        _write_pre_seg(sd, n=5, W=24, H=16)
        (sd / "masks").mkdir()
        m1, m2 = F.box_mask(5, 24, 16, [0.25, 0.25, 0.5, 0.5]), F.box_mask(5, 24, 16, [0.0, 0.0, 0.25, 0.25])
        np.savez(sd / "masks" / "a.npz", masked=np.packbits(m1, axis=-1), meta="{}")
        np.savez(sd / "masks" / "b.npz", masked=np.packbits(m2, axis=-1), meta="{}")
        inp = B.load_input(sd, ["a", "b"])
        assert inp.masked.shape == (5, 16, 24) and np.array_equal(inp.masked, m1 | m2) and inp.mask_names == ["a", "b"]
        _raises(ValueError, B.unpack_masks, sd / "masks" / "a.npz", 4, (24, 16))
        T = np.repeat(np.eye(4)[None], 5, 0)
        T[:, 0, 3] = np.arange(5)
        tracked = np.array([1, 0, 1, 1, 0], bool)
        out = B.SlamOutput(T, tracked, metric=True, kf_t=np.array([0, 2]), kf_disp=np.ones((2, 2, 3)),
                           extra={"conf": np.arange(5.0)}, meta={"runtime_s": 1.5})
        meta = B.save_output(td / "traj.npz", out, inp, "fake", {"p": 1})
        assert meta["masks"] == ["a", "b"] and meta["n_tracked"] == 3 and meta["runtime_s"] == 1.5
        z = B.load_output(td / "traj.npz")
        assert np.isnan(z["T_slam_cam"][[1, 4]]).all() and np.array_equal(z["T_slam_cam"][[0, 2, 3]], T[[0, 2, 3]])
        assert z["metric"] is True and np.array_equal(z["tracked"], tracked) and np.array_equal(z["k"], inp.k)
        assert np.array_equal(z["x_conf"], np.arange(5.0)) and z["meta"]["params"] == {"p": 1}
        assert "kf_pose_cw" not in z
        for bad in (B.SlamOutput(T[:4], tracked[:4], False), B.SlamOutput(T, tracked.astype(int), False),
                    B.SlamOutput(np.full_like(T, np.nan), tracked, False),
                    B.SlamOutput(T, tracked, False, kf_t=np.array([0]))):
            _raises(ValueError, B.save_output, td / "bad.npz", bad, inp, "fake", {})


# ====================================================================== runinfo
def test_git_repo_state_ignore():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        repo.mkdir()

        def git(*a):
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@example.com",
                            "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", *a],
                           check=True, capture_output=True)
        git("init", "-q")
        (repo / "experiments" / "e1").mkdir(parents=True)
        (repo / "experiments" / "e1" / "config.yaml").write_text("a: 1\n")
        (repo / "code.py").write_text("x = 1\n")
        git("add", ".")
        git("commit", "-q", "-m", "init")
        ign = ["experiments/e1/results", "experiments/e1/run.json"]
        s = RI.git_repo_state(repo, ign)
        assert s["clean"] and s["dirty_files"] == [] and len(s["commit"]) == 40 and s["branch"] == "main"
        res = repo / "experiments" / "e1" / "results" / "sub"
        res.mkdir(parents=True)
        (res / "metrics.json").write_text("{}")
        (repo / "experiments" / "e1" / "run.json").write_text("{}")
        assert RI.git_repo_state(repo, ign)["clean"]                           # untracked inside: ignored
        assert RI.git_repo_state(repo, [p + "/" for p in ign[:1]] + ign[1:])["clean"]
        s = RI.git_repo_state(repo)
        assert not s["clean"] and len(s["dirty_files"]) == 2
        other = repo / "experiments" / "e1" / "results_old.txt"                # same prefix, other path
        other.write_text("x")
        s = RI.git_repo_state(repo, ign)
        assert not s["clean"] and s["dirty_files"] == ["?? experiments/e1/results_old.txt"]
        other.unlink()
        (repo / "notes.txt").write_text("x")                                   # untracked outside
        s = RI.git_repo_state(repo, ign)
        assert not s["clean"] and s["dirty_files"] == ["?? notes.txt"]
        (repo / "notes.txt").unlink()
        (repo / "code.py").write_text("x = 2\n")                               # tracked, modified
        s = RI.git_repo_state(repo, ign)
        assert not s["clean"] and s["dirty_files"] == [" M code.py"] and s["describe"].endswith("-dirty")
        (repo / "code.py").write_text("x = 1\n")
        assert RI.git_repo_state(repo, ign)["clean"]
        # hashing.git_state (code_inputs fingerprints): tracked changes only, diff hashed
        g = H.git_state(repo)
        assert g == {"commit": s["commit"], "dirty": False, "diff_sha256": None, "submodules": {}}
        (repo / "untracked.txt").write_text("x")
        assert H.git_state(repo) == g
        (repo / "code.py").write_text("x = 3\n")
        g3 = H.git_state(repo)
        assert g3["dirty"] and g3["diff_sha256"] and g3["commit"] == g["commit"]
        (repo / "code.py").write_text("x = 4\n")
        assert H.git_state(repo)["diff_sha256"] not in (None, g3["diff_sha256"])


def test_envs_python():
    from slam.pipeline import envs as E
    assert Path(E.python("venv")).exists() and E.ENVS["venv"] == E.python("venv")
    _raises(KeyError, E.python, "no_such_env")
    os.environ["SLAM_PY_NO_SUCH_ENV"] = E.python("venv")
    try:
        assert E.python("no_such_env") == E.python("venv")
        os.environ["SLAM_PY_NO_SUCH_ENV"] = "/nonexistent/python"
        _raises(FileNotFoundError, E.python, "no_such_env")
    finally:
        del os.environ["SLAM_PY_NO_SUCH_ENV"]


# ====================================================================== end to end
SESSION, STEM = "fakesess", "fakesess_cam"


def _fake_data(root):
    raw, gt = root / "raw", root / "gt"
    raw.mkdir(parents=True)
    gt.mkdir()
    (root / "det").mkdir()
    eps = [{"episode_index": i, "t_start": 1000.0 + 10 * i, "t_end": 1003.0 + 10 * i, "duration_s": 3.0}
           for i in (0, 1, 3)]
    (raw / f"{SESSION}_glove_episodes.json").write_text(json.dumps({"dataset": SESSION, "episodes": eps}))
    (raw / f"{STEM}.mkv").write_bytes(b"\x1a\x45\xdf\xa3 not a real video " * 64)
    (raw / f"{STEM}_ts.json").write_text(json.dumps([{"wall": 995.0 + 0.04 * i} for i in range(1000)]))
    (gt / f"{STEM}_cam_world.json").write_text(json.dumps({"frames": []}))
    np.savez(gt / "ball_poses.npz", ball_k=np.arange(3))
    np.savez(gt / "gripper_wrist.npz", t=np.arange(3.0))


def _fake_config(root, exp="fake_exp", step_m_b=0.01, mutate=None):
    """Scratch config outside the repository; step_m_b: a parameter of slam run B only."""
    slam_p = {"step_m": 0.01, "lose_every": 3, "dilate_px": 0, "seed": 0}
    cfg = {"experiment": exp,
           "description": "framework end-to-end test with fake implementations",
           "data": {"session": SESSION, "episodes": [0, 3], "head_stem": STEM,
                    "intrinsics": "B0587b_f3_intrinsics.json", "glove": "yosub",
                    "tile_layout": "workspace_tiles_pilot_v3.json", "raw_dir": str(root / "raw"),
                    "det_cache_dir": str(root / "det"), "gt_dir": str(root / "gt")},
           "preprocess": {"impl": "fake_frames", "params": {"n_frames": 7, "width": 32, "height": 24, "f_px": 30}},
           "tiles": {"impl": "fake_tiles", "params": {"n_det": 2}},
           "masks": {"box": {"impl": "fake_box", "params": {"box": [0.25, 0.25, 0.5, 0.5]}},
                     "corner": {"impl": "fake_box", "params": {"box": [0, 0, 0.25, 0.25]}}},
           "slam": {"A": {"impl": "fake_slam", "masks": [], "params": dict(slam_p)},
                    "B": {"impl": "fake_slam", "masks": ["box", "corner"],
                          "params": {**slam_p, "step_m": step_m_b}}},
           "depth": {"d": {"impl": "fake_depth", "runs": ["B"], "params": {"model": "fake-depth", "value_m": 1.5}}},
           "exec": {"jobs": 2}}
    if mutate:
        mutate(cfg)
    d = root / "configs" / exp
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    return d / "config.yaml"


def _cli(cfg, *argv, quiet=False):
    """orchestrator.main on argv; returns (stdout, the scratch run.json invocation). The
    output is printed when it fails (unless quiet: an expected failure)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            O.main([str(cfg), "--gpu-wait-min", "0", *argv])
    except BaseException:
        if not quiet:
            print(buf.getvalue()[-6000:])
        raise
    exp = yaml.safe_load(Path(cfg).read_text())["experiment"]
    return buf.getvalue(), _scratch_inv(exp)


def _scratch_inv(exp):
    rj = O.WORK / "runs" / "_scratch" / exp / "run.json"
    return json.load(open(rj))["invocations"][-1] if rj.exists() else None


def _nodes(inv, start=0, stop=None):
    recs = inv["record"]["nodes"][start:stop]
    return {r["id"]: r["status"] for r in recs}, {r["id"]: r["key"] for r in recs}


def _n_entries(work):
    return {s: len(list((work / "cache" / s).iterdir())) for s in ("preprocess", "tiles", "masks", "slam", "depth")}


ALL = {"preprocess", "tiles", "masks.box", "masks.corner", "slam.A", "slam.B", "depth.d@B"}


def test_orchestrator_end_to_end():
    F.register()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _fake_data(root)
        cfg = _fake_config(root)
        old = O.WORK
        O.WORK = work = root / "work"
        try:
            _e2e(root, cfg, work)
        finally:
            O.WORK = old


def _e2e(root, cfg, work):
    # ---------------------------------------------------------------- dry run: nothing written
    out, inv = _cli(cfg, "--dry-run")
    assert inv is None and not work.exists() and "2 segments" in out and "cached 0/2" in out
    out, _ = _cli(cfg, "--dry-run", "--episodes", "3")
    assert "1 segments" in out
    _raises(SP.ConfigError, _cli, cfg, "--dry-run", "--episodes", "2", match="--episodes", quiet=True)

    # ---------------------------------------------------------------- 1st run: everything computed
    out, inv = _cli(cfg)
    st, k1 = _nodes(inv)
    assert inv["status"] == "complete" and inv["scratch"] is True and inv["segments"] == ["ep00", "ep03"]
    assert set(st) == ALL and set(st.values()) == {"computed"}, st
    assert all(r["segments_computed"] == 2 and r["segments_cached"] == 0 for r in inv["record"]["nodes"])
    assert inv["seeds"] == {"slam.A": 0, "slam.B": 0}
    assert set(O.ANALYSIS_DATA) <= set(inv["data_fingerprints"])
    assert inv["code_fingerprints"] and all(v == {} for v in inv["code_fingerprints"].values())
    run_root = work / "runs" / "_scratch" / "fake_exp"
    by_id = {r["id"]: r for r in inv["record"]["nodes"]}
    pre = by_id["preprocess"]["results"][0]
    assert pre["segments"] == ["ep00", "ep03"] and pre["exec"] == {"jobs": 2}
    assert pre["config_work"] == str(work) and pre["config_raw"] == str(root / "raw")
    assert pre["config_det_cache"] == str(root / "det")
    assert pre["session"] == {"head_stem": STEM, "intrinsics": "B0587b_f3_intrinsics.json", "glove": "yosub",
                              "tile_layout": "workspace_tiles_pilot_v3.json"}
    assert len(by_id["slam.B"]["results"]) == 2                                # one process per segment
    step_of = {"preprocess": "preprocess", "tiles": "tiles", "masks.box": "masks", "masks.corner": "masks",
               "slam.A": "slam", "slam.B": "slam", "depth.d@B": "depth"}
    for nid, key in k1.items():
        d = CA.node_dir(work, step_of[nid], key)
        assert CA.done_segments(d) == {"ep00", "ep03"}, nid
        man = json.load(open(d / "manifest.json"))
        assert man["key"] == key and man["tag"] is None and man["created"]["experiment"] == "fake_exp"
        assert not list(d.glob(".tmp-*"))
    assert len(set(k1.values())) == len(k1)
    man = json.load(open(CA.node_dir(work, "slam", k1["slam.B"]) / "manifest.json"))
    assert man["deps"] == {"preprocess": k1["preprocess"], "masks": sorted([k1["masks.box"], k1["masks.corner"]])}
    assert man["params"]["step_m"] == 0.01 and man["data"] == {}
    assert json.load(open(CA.node_dir(work, "preprocess", k1["preprocess"]) / "manifest.json"))["params"]["f_px"] == 30.0
    # outputs follow the cache contract
    seg = CA.node_dir(work, "preprocess", k1["preprocess"]) / "ep03"
    fj = json.load(open(seg / "frames.json"))
    assert len(fj["frames"]) == 7 and fj["frames"][0]["k"] == 300 and fj["size"] == [32, 24]
    assert len(list((seg / "images").glob("*.jpg"))) == 7 and (seg / "calib.txt").exists()
    zb = B.load_output(CA.node_dir(work, "slam", k1["slam.B"]) / "ep03" / "traj.npz")
    za = B.load_output(CA.node_dir(work, "slam", k1["slam.A"]) / "ep03" / "traj.npz")
    assert zb["T_slam_cam"].shape == (7, 4, 4) and list(zb["tracked"]) == [1, 1, 0, 1, 1, 0, 1]
    assert np.isnan(zb["T_slam_cam"][[2, 5]]).all() and zb["T_slam_cam"][1, 0, 3] == 0.01
    assert zb["meta"]["masks"] == ["box", "corner"] and za["meta"]["masks"] == []
    assert zb["meta"]["masked_frac"] == 0.3125 and za["meta"]["masked_frac"] is None     # OR of both masks
    assert zb["meta"]["backend"] == "fake_slam" and zb["meta"]["params"]["step_m"] == 0.01
    zd = np.load(CA.node_dir(work, "depth", k1["depth.d@B"]) / "ep00" / "depth.npz")
    assert zd["depth"].shape == (3, 24, 32) and zd["depth"].dtype == np.float16 and list(zd["kf_t"]) == [0, 3, 6]
    # analysis view over the cached outputs (no analysis steps configured)
    vseg = run_root / "main" / "view" / SESSION / "segments" / "ep03"
    for rel, nid, f in (("images", "preprocess", "images"), ("gt.npz", "preprocess", "gt.npz"),
                        ("tiles.npz", "tiles", "tiles.npz"), ("masks/box.npz", "masks.box", "masked.npz"),
                        ("masks/corner.npz", "masks.corner", "masked.npz"), ("slam/A.npz", "slam.A", "traj.npz"),
                        ("slam/B.npz", "slam.B", "traj.npz"), ("depth/B_fake-depth.npz", "depth.d@B", "depth.npz")):
        assert os.readlink(vseg / rel) == str(CA.node_dir(work, step_of[nid], k1[nid]) / "ep03" / f), rel
    assert os.readlink(run_root / "main" / "view" / SESSION / "gt") == str(root / "gt")
    assert not (run_root / "main" / "view" / SESSION / "segments" / "ep01").exists()
    assert (run_root / "main" / "results").is_dir() and inv["record"]["variants"]["main"]["steps"] == {}
    assert not (run_root / "scratch").exists() or not list((run_root / "scratch").iterdir())
    assert (run_root / "logs").is_dir() and len(list((run_root / "logs").glob("*.log"))) == 9
    assert inv["repro"] is None

    # ---------------------------------------------------------------- 2nd run: all hits
    out, inv = _cli(cfg)
    st, k2 = _nodes(inv)
    assert inv["status"] == "complete" and k2 == k1 and set(st.values()) == {"hit"}, st
    assert all(r["segments_cached"] == 2 and r["segments_computed"] == 0 for r in inv["record"]["nodes"])
    assert _n_entries(work) == {"preprocess": 1, "tiles": 1, "masks": 2, "slam": 2, "depth": 1}

    # ---------------------------------------------------------------- slam param changed: only slam.B + depth
    cfg_b = _fake_config(root, exp="fake_exp_b", step_m_b=0.02)
    out, inv = _cli(cfg_b)
    st, k3 = _nodes(inv)
    changed = {"slam.B", "depth.d@B"}
    assert {i for i in ALL if k3[i] != k1[i]} == changed, (k1, k3, st)
    assert {i for i, s in st.items() if s == "computed"} == changed and {st[i] for i in ALL - changed} == {"hit"}
    zb2 = B.load_output(CA.node_dir(work, "slam", k3["slam.B"]) / "ep03" / "traj.npz")
    assert zb2["T_slam_cam"][1, 0, 3] == 0.02
    assert CA.done_segments(CA.node_dir(work, "slam", k1["slam.B"])) == {"ep00", "ep03"}    # old entry kept

    # ---------------------------------------------------------------- failure, then resume
    def corner(c):
        c["masks"]["corner"]["params"]["box"] = [0, 0, 0.5, 0.25]          # 16 x 6 px, disjoint from box
    cfg_c = _fake_config(root, exp="fake_exp_c", mutate=corner)
    for fail, node in (("masks.corner:ep03", "masks.corner"), ("slam.B:ep03", "slam.B")):
        os.environ["FAKE_FAIL"] = fail
        try:
            _raises(RuntimeError, _cli, cfg_c, match=f"worker {node}.", quiet=True)
        finally:
            del os.environ["FAKE_FAIL"]
        inv = _scratch_inv("fake_exp_c")
        assert inv["status"] == "failed" and "worker" in inv["error"] and inv["record"]["nodes"][-1]["id"] == node
        key = inv["record"]["nodes"][-1]["key"]
        assert CA.done_segments(CA.node_dir(work, node.split(".")[0], key)) == {"ep00"}   # ep00 kept
    out, inv = _cli(cfg_c)
    st = {r["id"]: (r["status"], r["segments_cached"], r["segments_computed"]) for r in inv["record"]["nodes"]}
    assert st["masks.corner"] == ("hit", 2, 0) and st["slam.B"] == ("computed", 1, 1)
    assert st["depth.d@B"] == ("computed", 0, 2) and st["slam.A"] == ("hit", 2, 0)
    for nid, d in ((r["id"], CA.node_dir(work, step_of[r["id"]], r["key"])) for r in inv["record"]["nodes"]):
        assert not list(d.glob(".tmp-*")), nid
    zc = B.load_output(CA.node_dir(work, "slam", inv["record"]["nodes"][5]["key"]) / "ep03" / "traj.npz")
    assert zc["meta"]["masked_frac"] == (192 + 96) / 768

    # ---------------------------------------------------------------- not enough GPU memory: refused, recorded
    def gpu(c):
        c["masks"]["box"]["impl"] = "fake_box_gpu"
    cfg_g = _fake_config(root, exp="fake_exp_gpu", mutate=gpu)
    _raises(RuntimeError, _cli, cfg_g, match="GPU", quiet=True)
    inv = _scratch_inv("fake_exp_gpu")
    assert inv["status"] == "failed" and "GPU" in inv["error"]

    # ---------------------------------------------------------------- --repro slam.B=2
    n_before = _n_entries(work)
    for bad in ("slam.Z", "slam.B=x", "slam.B=-1"):
        _raises(SP.ConfigError, _cli, cfg, "--repro", bad, match="--repro", quiet=True)       # refused before running
    assert _n_entries(work) == n_before
    out, inv = _cli(cfg, "--repro", "slam.B=2")
    assert inv["status"] == "complete"
    recs = inv["record"]["nodes"]
    assert len(recs) == 3 * len(ALL)
    st, km = _nodes(inv, 0, len(ALL))
    assert km == k1 and set(st.values()) == {"hit"}
    rep = inv["repro"]
    assert rep["node"] == "slam.B" and rep["base_keys"] == {i: k1[i] for i in changed}
    assert [r["variant"] for r in rep["runs"]] == ["repro1", "repro2"]
    seen = {k1["slam.B"], k1["depth.d@B"], k3["slam.B"], k3["depth.d@B"]}
    for i, r in enumerate(rep["runs"]):
        st, kr = _nodes(inv, (i + 1) * len(ALL), (i + 2) * len(ALL))
        assert set(r["keys"]) == changed and r["keys"] == {x: kr[x] for x in changed}
        assert {x for x in ALL if kr[x] != k1[x]} == changed
        assert {x for x, s in st.items() if s == "computed"} == changed
        assert not (set(r["keys"].values()) & seen)
        seen |= set(r["keys"].values())
        tag = r["variant"]
        man = json.load(open(CA.node_dir(work, "slam", kr["slam.B"]) / "manifest.json"))
        assert man["tag"] == tag and man["params"] == json.load(open(
            CA.node_dir(work, "slam", k1["slam.B"]) / "manifest.json"))["params"]
        man = json.load(open(CA.node_dir(work, "depth", kr["depth.d@B"]) / "manifest.json"))
        assert man["tag"] is None and man["deps"]["slam"] == kr["slam.B"]
        vseg = run_root / tag / "view" / SESSION / "segments" / "ep00"
        assert os.readlink(vseg / "slam/B.npz") == str(CA.node_dir(work, "slam", kr["slam.B"]) / "ep00" / "traj.npz")
        assert os.readlink(vseg / "slam/A.npz") == str(CA.node_dir(work, "slam", k1["slam.A"]) / "ep00" / "traj.npz")
        assert (run_root / tag / "results").is_dir()
        zr = B.load_output(CA.node_dir(work, "slam", kr["slam.B"]) / "ep03" / "traj.npz")
        assert np.array_equal(zr["T_slam_cam"], zb["T_slam_cam"], equal_nan=True)       # deterministic fake
    assert set(inv["record"]["variants"]) == {"main", "repro1", "repro2"}
    assert {p.name for p in run_root.iterdir()} >= {"main", "repro1", "repro2", "logs", "jobs", "run.json"}
    assert _n_entries(work) == {**n_before, "slam": n_before["slam"] + 2, "depth": n_before["depth"] + 2}
    out, inv = _cli(cfg, "--repro", "slam.B")                                  # repro1 is cached now
    assert {r["status"] for r in inv["record"]["nodes"]} == {"hit"}

    # ---------------------------------------------------------------- refusals
    _raises(SP.ConfigError, O.main, [str(EXP001), "--episodes", "1", "--dry-run"], match="--episodes")
    bad = root / "configs" / "misnamed"
    bad.mkdir()
    shutil.copy(cfg, bad / "config.yaml")
    _raises(SP.ConfigError, O.main, [str(bad / "config.yaml"), "--dry-run"], match="directory of that name")



# ====================================================================== review fixes
def test_source_hash_ignores_comments_and_docstrings():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m.py"
        p.write_text('"""Module doc."""\nimport numpy as np\n\n\ndef f(x):\n    """Doc."""\n    return x + 1\n')
        h0 = H.source_hash(p)
        p.write_text('"""Other words."""\nimport numpy as np  # comment\n\ndef f(x):\n    """New doc."""\n'
                     '    # why\n    return (x + 1)\n')
        assert H.source_hash(p) == h0                      # comments, docstrings, formatting
        p.write_text('"""Module doc."""\nimport numpy as np\n\n\ndef f(x):\n    """Doc."""\n    return x + 2\n')
        assert H.source_hash(p) != h0                      # a code change
        p.write_text('import numpy as np\n\n\ndef f(x):\n    return x + 1\n')
        assert H.source_hash(p) == h0
    # every producer's declared code files exist and hash
    for impl in R.IMPLS.values():
        for rel in impl.code_files:
            assert H.source_hash(SP.REPO / rel).startswith("ast:"), rel


def test_weights_path_not_in_key():
    base = _keys(_exp001())
    c = _exp001()
    for run in ("E1", "E3"):
        c["slam"][run]["params"]["weights"]["path"] = "/elsewhere/droid.pth"
    assert _keys(c) == base
    c = _exp001()
    c["slam"]["E3"]["params"]["weights"]["sha256"] = "0" * 64
    assert _diff(base, _keys(c)) == {"slam.E3", "depth.da2@E3"}
    data, code = _fps(_exp001())
    code["masks/sam2_points"] = {**code["masks/sam2_points"], "pkg:transformers": "9.9"}
    assert _diff(base, _keys(_exp001(), code=code)) == {"masks.motion", "slam.E3", "depth.da2@E3"}


def test_review_config_checks():
    def setp(path, value):
        def f(c):
            d = c
            for k in path[:-1]:
                d = d[k]
            d[path[-1]] = value
        return f
    _bad(lambda c: c["slam"].__setitem__("tiles", c["slam"].pop("E1")), "reserved")
    _bad(lambda c: c["slam"].__setitem__("E 1", c["slam"].pop("E1")), "names use")
    _bad(lambda c: c["slam"]["E1"].pop("masks"), "missing 'masks'")
    _bad(setp(("scale", "E3", "flag_threshold"), 10), "fraction in (0, 1)")
    _bad(setp(("scale", "E3", "flag_threshold"), True), "fraction in (0, 1)")
    _bad(setp(("scale", "E3", "checks"), ["A", "A"]), "duplicate")
    _bad(lambda c: c["scale"]["E3"].pop("checks"), "missing 'checks'")
    _bad(lambda c: (c["scale"]["E3"].__setitem__("checks", []), c["scale"]["E3"]["methods"].pop("A")),
         "null without checks")
    _bad(setp(("scale", "E3", "methods", "B", "fit"), "afine"), "scale.E3.methods.B.fit")
    _bad(setp(("scale", "E3", "methods", "B", "correction"), "face"), "correction")
    _bad(setp(("masks", "motion", "params", "dtype"), "bf16"), "dtype")
    _bad(setp(("labels", "params", "gripper"), "wirst"), "gripper")
    _bad(setp(("labels", "params", "fps"), 30.0), "fixed in slam.labels")
    _bad(setp(("depth", "da2", "params", "model"), "zoe"), "model")
    _bad(lambda c: c["depth"].__setitem__("da2b", dict(c["depth"]["da2"])), "already has model")
    _bad(setp(("report", "runs"), ["E3"]), "report")
    _bad(lambda c: c["labels"].pop("runs"), "missing 'runs'")
    _bad(setp(("data", "episodes"), []), "data.episodes")
    _bad(setp(("data", "episodes"), [True]), "data.episodes")
    # without checks: flag_threshold null is valid
    c = _exp001()
    c["scale"]["E3"]["checks"] = []
    c["scale"]["E3"]["flag_threshold"] = None
    del c["scale"]["E3"]["methods"]["A"]
    SP.build(c)


def test_check_previous_refuses_completed_elsewhere():
    from types import SimpleNamespace
    with tempfile.TemporaryDirectory() as td:
        exp = Path(td) / "exp_x"
        exp.mkdir()
        me = SimpleNamespace(exp_dir=exp, cfg_sha="c1", git={"commit": "aaa"},
                             run_json_path=lambda: exp / "run.json")
        keys = {"slam.E3": "k1"}
        assert O.Runner.check_previous(me, keys) == []
        (exp / "results").mkdir()
        (exp / "results" / "x.json").write_text("{}")
        _raises(SP.ConfigError, O.Runner.check_previous, me, keys, match="without run.json")

        def write(*invs):
            (exp / "run.json").write_text(json.dumps({"invocations": list(invs)}))
        done = {"config_sha256": "c1", "status": "complete", "git": {"commit": "aaa"}, "keys": keys}
        write(done)
        assert len(O.Runner.check_previous(me, keys)) == 1                  # same commit + keys: allowed
        _raises(SP.ConfigError, O.Runner.check_previous, me, {"slam.E3": "k2"}, match="already completed")
        me.git = {"commit": "bbb"}
        _raises(SP.ConfigError, O.Runner.check_previous, me, keys, match="already completed")
        write({**done, "status": "failed"})
        assert len(O.Runner.check_previous(me, keys)) == 1                  # resume a failed run
        write({**done, "config_sha256": "c0", "status": "failed"})
        _raises(SP.ConfigError, O.Runner.check_previous, me, keys, match="different config")

if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
