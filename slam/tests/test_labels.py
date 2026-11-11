"""RefPoses lookup against the stored label files (needs <work>/yam_glove7/segments/*/labels/E1.npz).

Since 2026-11-10 the lookup interpolates between the 15 fps label steps (build_dataset --slow samples
the timeline at 15 * slow Hz): on a grid time it returns the stored pose, in between the interpolation
of its two neighbours, and a gap if either neighbour is one.
"""
import numpy as np

from slam import config as C
from slam import geometry as G
from slam.labels import RefPoses, interp_poses


def test_refposes_roundtrip():
    seg = C.segments_dir("yam_glove7")
    rp = RefPoses(seg, "E1")
    n = 0
    for ep in range(30):
        z = rp.episode(ep)
        if z is None:
            continue
        for i in range(1, len(z["t"]) - 1, 7):
            tv, rv, gap = rp.lookup(ep, z["t"][i])                   # on the grid: the stored pose
            assert np.allclose(G.rt_to_T(rv, tv)[0], z["T_ref_tool"][i], atol=1e-9)
            tm = 0.6 * z["t"][i] + 0.4 * z["t"][i + 1]               # between steps i and i+1
            tv, rv, gap = rp.lookup(ep, tm)
            ref = interp_poses(np.array([tm]), z["t"][[i, i + 1]], z["T_ref_tool"][[i, i + 1]])[0]
            assert np.allclose(G.rt_to_T(rv, tv)[0], ref, atol=1e-9)
            assert gap == bool(z["gap"][i] or z["gap"][i + 1])
            n += 1
        assert rp.lookup(ep, z["t"][0] - 1.0)[2]                     # off the episode -> gap
    assert n > 100


if __name__ == "__main__":
    test_refposes_roundtrip()
    print("ok test_refposes_roundtrip")
