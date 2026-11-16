"""undistort_crop_resample's frame choice and in-place resampling (python -m slam.tests.test_preprocess_resample)."""
import json
import tempfile
from pathlib import Path

import numpy as np

from slam.pipeline.impl_preprocess_resample import grid_keep, resample_segment


def test_grid_keep_rates():
    w60 = 1000 + np.arange(600) / 59.7                         # 10 s at 59.7 fps
    k = grid_keep(w60, 26.27)
    fps = (len(k) - 1) / (w60[k[-1]] - w60[k[0]])
    assert abs(fps - 26.27) < 0.3, fps
    assert set(np.diff(k)) <= {2, 3}
    w26 = 1000 + np.arange(260) / 26.27                        # already at the target: untouched
    assert np.array_equal(grid_keep(w26, 26.27), np.arange(260))
    w_gap = np.delete(w60, range(100, 112))                    # a 0.2 s hole: still no duplicates
    kg = grid_keep(w_gap, 26.27)
    assert len(kg) == len(set(kg.tolist()))


def test_resample_segment_in_place():
    with tempfile.TemporaryDirectory() as d:
        seg = Path(d) / "ep00"
        (seg / "images").mkdir(parents=True)
        walls = 1000 + np.arange(120) / 60.0
        frames = []
        for i, w in enumerate(walls):
            (seg / "images" / f"{i:06d}.jpg").write_text(str(i))
            frames.append({"i": i, "k": 500 + i, "wall": float(w), "in_episode": bool(i >= 60)})
        json.dump({"frames": frames, "episode": {"episode_index": 0}}, open(seg / "frames.json", "w"))
        resample_segment(seg, 26.27)
        fj = json.load(open(seg / "frames.json"))
        out = fj["frames"]
        imgs = sorted(p.name for p in (seg / "images").glob("*.jpg"))
        assert imgs == [f"{i:06d}.jpg" for i in range(len(out))]
        for f in out:                                           # image i holds the original frame k
            assert int((seg / "images" / f"{f['i']:06d}.jpg").read_text()) == f["k"] - 500
        assert fj["resample"]["of"] == 120 and fj["resample"]["kept"] == len(out) < 60
        assert "already" in resample_segment(seg, 26.27)        # idempotent


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
