"""droid_preroll's subset / expand (python -m slam.tests.test_slam_preroll; CPU, no DROID)."""
import tempfile
from pathlib import Path

import numpy as np

from slam.backends import base as B
from slam.pipeline.impl_slam_preroll import expand, subset


def fake_input(n=20, H=16, W=24):
    return B.SlamInput(images=[f"img{i}.jpg" for i in range(n)], k=np.arange(100, 100 + n), t=np.arange(n) * 0.04,
                       K=np.eye(3), size=(W, H), masked=np.zeros((n, H, W), bool), mask_names=["motion"])


def test_subset_expand_roundtrip():
    inp = fake_input()
    i0 = 7
    sub = subset(inp, i0)
    assert len(sub) == 13 and sub.k[0] == 107 and sub.masked.shape[0] == 13 and sub.images[0] == "img7.jpg"
    m = len(sub)
    T = np.tile(np.eye(4), (m, 1, 1))
    T[:, 0, 3] = np.arange(m)
    out = B.SlamOutput(T_slam_cam=T, tracked=np.ones(m, bool), metric=False, kf_t=np.array([0, 3, 9]),
                       kf_disp=np.ones((3, 2, 3), np.float32), kf_pose_cw=np.zeros((3, 7)),
                       extra={"pose7": np.zeros((m, 7))}, meta={})
    full = expand(out, len(inp), i0)
    assert full.T_slam_cam.shape == (20, 4, 4) and np.isnan(full.T_slam_cam[:i0]).all()
    assert np.array_equal(full.T_slam_cam[i0:], T)
    assert not full.tracked[:i0].any() and full.tracked[i0:].all()
    assert np.array_equal(full.kf_t, [7, 10, 16])
    assert full.extra["pose7"].shape == (20, 7) and np.isnan(full.extra["pose7"][:i0]).all()
    with tempfile.TemporaryDirectory() as d:          # the standard writer accepts it
        meta = B.save_output(Path(d) / "traj.npz", full, inp, "droid_preroll", {})
        z = B.load_output(Path(d) / "traj.npz")
    assert meta["n_frames"] == 20 and meta["n_tracked"] == 13
    assert np.array_equal(z["k"], inp.k) and np.array_equal(z["kf_t"], [7, 10, 16])


if __name__ == "__main__":
    test_subset_expand_roundtrip()
    print("ok test_subset_expand_roundtrip")
