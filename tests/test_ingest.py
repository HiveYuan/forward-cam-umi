"""slam.ingest / slam.collect_dataset / slam.pipeline.hashing sidecars: the pure parts (no bucket, GPU or data)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from slam import collect_dataset as CD  # noqa: E402
from slam import ingest as I  # noqa: E402
from slam.pipeline import hashing as H  # noqa: E402

GATES = {"label_err_1s_mm_max": 8.0, "slam_valid_min": 0.9, "grip_coverage_min": 0.7, "max_rejected_fraction": 0.3}


def row(ep, steps=100, valid=100, scale=True, cov=1.0):
    return {"episode": ep, "steps": steps, "slam_valid": valid, "scale_ok": scale, "grip_coverage": cov}


class TestSeries(unittest.TestCase):
    def test_medfilt_matches_naive(self):
        rng = np.random.default_rng(0)
        v = rng.normal(size=50)
        n = 5
        p = np.pad(v, 2, mode="edge")
        naive = np.array([np.median(p[i:i + n]) for i in range(len(v))])
        np.testing.assert_allclose(CD.medfilt(v, n), naive)
        np.testing.assert_allclose(CD.medfilt(v, 1), v)
        np.testing.assert_allclose(CD.medfilt(v, 4), CD.medfilt(v, 5))        # even windows round up to odd

    def test_medfilt_removes_isolated_spike_keeps_edge(self):
        v = np.r_[np.zeros(20), np.ones(20)]
        v[10] = 1.0
        f = CD.medfilt(v, 5)
        self.assertEqual(f[10], 0.0)
        np.testing.assert_array_equal(f[18:22], [0, 0, 1, 1])

    def test_timeline_is_build_dataset_arange(self):
        t = CD.timeline(100.0, 101.0, 15.0, 2.5)
        self.assertEqual(len(t), 38)
        self.assertAlmostEqual(t[1] - t[0], 1 / 37.5)
        self.assertLess(t[-1], 101.0)

    def test_nearest(self):
        ts = np.array([0.0, 1.0, 2.0])
        np.testing.assert_allclose(CD.nearest_dist(ts, np.array([-1.0, 0.4, 0.6, 5.0])), [1.0, 0.4, 0.4, 3.0])
        np.testing.assert_array_equal(CD.nearest_index(ts, np.array([0.4, 0.6, 1.5, 9.0])), [0, 1, 1, 2])
        self.assertTrue(np.isinf(CD.nearest_dist([], np.array([1.0]))).all())

    def test_gripper_series_coverage(self):
        t = np.r_[np.arange(0, 1, 0.02), np.arange(2, 3, 0.02)]          # a 1 s hole
        v = np.ones_like(t) * 0.5
        tq = CD.timeline(0, 3, 15, 2.5)
        g, cov = CD.gripper_series(t, v, tq, 0.3, 0.12)
        self.assertTrue(np.allclose(g, 0.5))
        hole = np.mean((tq > 1 + 0.12) & (tq < 2 - 0.12))
        self.assertAlmostEqual(cov, 1 - hole, delta=0.02)
        g, cov = CD.gripper_series([], [], tq, 0.3, 0.12)
        self.assertEqual(cov, 0.0)


class TestValSplit(unittest.TestCase):
    def test_val_split(self):
        self.assertEqual(CD.val_split(30, 0.1), [5, 15, 25])                 # 3 of 30, spread
        self.assertEqual(CD.val_split(8, 0.1), [4])                          # at least one
        self.assertEqual(CD.val_split(1, 0.1), [])                           # never the only episode
        self.assertEqual(CD.val_split(30, 0.0), [])
        self.assertEqual(len(CD.val_split(42, 0.1)), 4)
        self.assertTrue(all(0 <= i < 42 for i in CD.val_split(42, 0.5)))


class TestGates(unittest.TestCase):
    def test_all_good(self):
        kept, why, v = CD.gate_session([row(0), row(1)], 5.0, GATES)
        self.assertEqual(kept, [0, 1])
        self.assertFalse(v["held"])

    def test_episode_drops(self):
        rows = [row(0), row(1, scale=False), row(2, valid=0), row(3, cov=0.5)] + [row(i) for i in range(4, 12)]
        kept, why, v = CD.gate_session(rows, None, GATES)
        self.assertEqual(kept, [0] + list(range(4, 12)))
        self.assertIn("scale failed", why[1])
        self.assertIn("no SLAM pose", why[2])
        self.assertTrue(why[3][0].startswith("gripper coverage"))
        self.assertFalse(v["held"])                                       # 3/12 = 25% <= 30%

    def test_session_held(self):
        _, _, v = CD.gate_session([row(0), row(1, cov=0.1)], None, GATES)
        self.assertTrue(v["held"])                                        # 50% dropped
        _, _, v = CD.gate_session([row(0, valid=80)], None, GATES)
        self.assertTrue(v["held"])                                        # slam_valid 0.8
        _, _, v = CD.gate_session([row(0)], 9.5, GATES)
        self.assertTrue(v["held"] and "label error" in v["reasons"][0])
        _, _, v = CD.gate_session([row(0)], None, GATES)                  # no tiles: no label gate
        self.assertFalse(v["held"])


class TestBatch(unittest.TestCase):
    def write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
        f.write(text)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_defaults_and_merge(self):
        b = I.load_batch(self.write("batch: t1\nbucket: gs://x/y\nsessions: [a]\ngates: {slam_valid_min: 0.8}\n"))
        self.assertEqual(b["gates"]["slam_valid_min"], 0.8)
        self.assertEqual(b["gates"]["label_err_1s_mm_max"], 8.0)
        self.assertEqual(b["dataset"]["slow"], 2.5)
        self.assertEqual(b["dataset"]["slam_run"], "E3")
        self.assertTrue(b["commit"])

    def test_validation(self):
        for bad in ("batch: t\nsessions: []\n",                             # no bucket
                    "batch: 'a b'\nbucket: gs://x\n",                       # bad name
                    "batch: t\nbucket: gs://x\nwrist: sometimes\n",
                    "batch: t\nbucket: gs://x\nraw_policy: shred\n",
                    "batch: t\nbucket: gs://x\ntypo_key: 1\n",
                    "batch: t\nbucket: gs://x\ntrain: [{exp: e, template: t}]\n"):   # train without dataset.out
            with self.assertRaises(SystemExit, msg=bad):
                I.load_batch(self.write(bad))


def bare_ingest(batch_text, tmp):
    """An Ingest without __init__'s directories: state in tmp, batch from text."""
    import threading
    p = Path(tmp) / "b.yaml"
    p.write_text(batch_text)
    ing = I.Ingest.__new__(I.Ingest)
    ing.b = I.load_batch(str(p))
    ing.state, ing.state_p = {"sessions": {}}, Path(tmp) / "state.json"
    ing.lock, ing.git_lock, ing.stop_reason = threading.Lock(), threading.Lock(), None
    ing.log = lambda msg: None
    return ing


class TestOrchestration(unittest.TestCase):
    def test_lane_survives_systemexit_and_releases_waiters(self):
        import threading
        with tempfile.TemporaryDirectory() as d:
            ing = bare_ingest("batch: t\nbucket: gs://x\n", d)
            done = {s: threading.Event() for s in ("a", "b", "c")}
            seen = []

            def step(ds):
                seen.append(ds)
                if ds == "a":
                    raise SystemExit("bad input")
                if ds == "b":
                    raise ValueError("boom")
            ing.lane("t", ["a", "b", "c"], step, None, done)
            self.assertEqual(seen, ["a", "b", "c"])                 # the lane went on after both failures
            self.assertTrue(all(e.is_set() for e in done.values()))
            self.assertIn("SystemExit", ing.st("a")["failed"])
            self.assertNotIn("failed", ing.st("c"))

    def test_lane_stop_releases_all(self):
        import threading
        with tempfile.TemporaryDirectory() as d:
            ing = bare_ingest("batch: t\nbucket: gs://x\n", d)
            done = {s: threading.Event() for s in ("a", "b")}

            def step(ds):
                raise I.Stop("need a person")
            ing.lane("t", ["a", "b"], step, None, done)
            self.assertTrue(done["b"].is_set())
            self.assertEqual(ing.stop_reason, "need a person")

    def test_train_finished_needs_the_final_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {"base_train_config": "calib/yosub_train_configs/mix_gHs3_48/train_config.json",
                   "overrides": {"steps": 20}, "output_dir": d}
            (Path(d) / "checkpoints" / "last").mkdir(parents=True)          # lerobot writes `last` from step 2000 on
            self.assertFalse(I.Ingest.train_finished(cfg))
            (Path(d) / "checkpoints" / "000020" / "pretrained_model").mkdir(parents=True)
            self.assertTrue(I.Ingest.train_finished(cfg))

    def test_bucket_ls(self):
        from unittest import mock
        R = lambda rc, out="", err="": mock.Mock(returncode=rc, stdout=out, stderr=err)
        ok = R(0, "   1234  2026-11-16T00:00:00Z  gs://b/y/data/raw/s_b0587b.mkv\nTOTAL: 1 objects, 1234 bytes\n")
        with mock.patch.object(I.subprocess, "run", return_value=ok):
            self.assertEqual(I.bucket_ls("gs://b/y/data/raw/s_*"), {"s_b0587b.mkv": 1234})
        none = R(1, err="ERROR: (gcloud.storage.ls) One or more URLs matched no objects.")
        with mock.patch.object(I.subprocess, "run", return_value=none):
            self.assertEqual(I.bucket_ls("gs://b/x"), {})
        bad = R(1, err="ERROR: (gcloud.storage.ls) There was a problem refreshing your current auth tokens")
        with mock.patch.object(I.subprocess, "run", return_value=bad), mock.patch.object(I.time, "sleep"):
            with self.assertRaises(RuntimeError):
                I.bucket_ls("gs://b/x")

    def test_export_reuse_needs_same_params(self):
        with tempfile.TemporaryDirectory() as d:
            ing = bare_ingest("batch: t\nbucket: gs://x\n", d)
            dd = ing.b["dataset"]
            sj = {"experiment": "col1", "shard": d, "gates": ing.b["gates"], "builder_version": CD.BUILDER_VERSION,
                  "params": {k: dd[k] for k in CD.EXPORT_PARAMS}, "base": dd["base"]["repo"]}
            self.assertTrue(ing.export_reusable(sj, "col1"))
            self.assertFalse(ing.export_reusable(sj, "col2"))
            self.assertFalse(ing.export_reusable({**sj, "params": {**sj["params"], "gripper_median_s": 0.5}}, "col1"))
            self.assertFalse(ing.export_reusable({**sj, "gates": {**sj["gates"], "slam_valid_min": 0.8}}, "col1"))
            self.assertFalse(ing.export_reusable({k: v for k, v in sj.items() if k != "params"}, "col1"))

    def test_reference_shorthand(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(bare_ingest("batch: t\nbucket: gs://x\n", d).b["reference"]["paper_val"], 0.2946)
            b = bare_ingest("batch: t\nbucket: gs://x\nreference: exp018_rel_T48\n", d).b
            self.assertEqual(b["reference"], {"exp": "exp018_rel_T48", "paper_val": None})


class TestSidecar(unittest.TestCase):
    def test_fingerprint_survives_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "v.mkv"
            p.write_bytes(os.urandom(4096))
            fp = H.file_fingerprint(p)
            self.assertIsNone(H.file_fingerprint(Path(d) / "missing.mkv"))
            self.assertEqual(H.write_sidecar(p), fp)
            p.unlink()
            self.assertEqual(H.file_fingerprint(p), fp)
            self.assertEqual(H.sidecar_path(p).name, "v.mkv.fingerprint")


@unittest.skipUnless((I.C.COLLECT_REPO / "data/raw/yuan_slam_06_session.json").exists(), "needs the collected sessions")
class TestConfigOverrides(unittest.TestCase):
    def test_include_exclude(self):
        from slam import collect as K
        base, _, _ = K.build_config("yuan_slam_06", "x")
        cfg, head, _ = K.build_config("yuan_slam_06", "x", include=[2, 14, 17], exclude=[0])
        e0, e1 = set(base["data"]["episodes"]), set(cfg["data"]["episodes"])
        self.assertEqual(e1, (e0 | {2, 14, 17}) - {0})
        self.assertIn("added by hand [2, 14, 17]", head)
        self.assertIn("removed by hand [0]", head)
        with self.assertRaises(SystemExit):
            K.build_config("yuan_slam_06", "x", include=[999])


if __name__ == "__main__":
    unittest.main()
