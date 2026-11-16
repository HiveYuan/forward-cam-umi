"""sam3_v2_head's width redirect and registry entry (python -m slam.tests.test_masks_sam3v2_head; CPU, no SAM3)."""
import tempfile
from pathlib import Path

import numpy as np

from slam import masks_sam3v2 as S
from slam.pipeline import registry as R
from slam.pipeline.impl_masks_sam3v2_head import head_width_source


def test_redirect():
    with tempfile.TemporaryDirectory() as d:
        gt = Path(d)
        np.savez(gt / "gripper_head.npz", g3_t=np.array([1.0, 2.0]), g3_v=np.array([0.3, 0.6]))
        np.savez(gt / "gripper_wrist.npz", g3_t=np.array([1.0, 2.0]), g3_v=np.array([0.9, 0.9]))
        orig = S.load_gripper_wrist
        with head_width_source(gt):
            g = S.load_gripper_wrist(gt / "gripper_wrist.npz")         # what sam3_v2 asks for
            assert np.allclose(g[3][1], [0.3, 0.6])                     # ... is the head width
            try:
                S.load_gripper_wrist(gt / "other.npz")
                raise AssertionError("an unexpected path must raise")
            except RuntimeError:
                pass
        assert S.load_gripper_wrist is orig
        assert np.allclose(S.load_gripper_wrist(gt / "gripper_wrist.npz")[3][1], [0.9, 0.9])
        (gt / "gripper_head.npz").unlink()
        try:
            with head_width_source(gt):
                pass
            raise AssertionError("a missing head width must raise")
        except FileNotFoundError:
            pass
        assert S.load_gripper_wrist is orig


def test_registry():
    a, b = R.get("masks", "sam3_v2"), R.get("masks", "sam3_v2_head")
    assert a.params == b.params and a.env == b.env and a.binaries == b.binaries
    assert set(a.code_files) < set(b.code_files) and "gt_gripper_head" in b.data_inputs
    assert "gt_gripper_wrist" not in b.data_inputs
    assert R.get("labels", "default").params["gripper"] == "head"


if __name__ == "__main__":
    for f in (test_redirect, test_registry):
        f()
        print("ok", f.__name__)
