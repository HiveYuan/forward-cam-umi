"""RefPoses lookup against the stored label files (needs <work>/yam_glove7/segments/*/labels/E1.npz)."""
import numpy as np

from slam import config as C
from slam import geometry as G
from slam.labels import RefPoses


def test_refposes_roundtrip():
    seg = C.segments_dir("yam_glove7")
    rp = RefPoses(seg, "E1")
    n = 0
    for ep in range(30):
        z = rp.episode(ep)
        if z is None:
            continue
        for i in range(0, len(z["t"]), 7):
            tv, rv, gap = rp.lookup(ep, z["t"][i] + 0.004)       # small timing jitter
            T = G.rt_to_T(rv, tv)[0]
            assert np.allclose(T, z["T_ref_tool"][i], atol=1e-9)
            assert gap == bool(z["gap"][i])
            n += 1
        assert rp.lookup(ep, z["t"][0] - 1.0)[2]                 # off the grid -> gap
    assert n > 100


if __name__ == "__main__":
    test_refposes_roundtrip()
    print("ok test_refposes_roundtrip")
