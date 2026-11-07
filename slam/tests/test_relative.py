"""Checks of the relative-label math (python -m pytest slam/tests, or python -m slam.tests.test_relative)."""
import numpy as np

from slam import geometry as G
from slam import relative as Rl


def random_T(rng, n):
    rv = rng.normal(size=(n, 3))
    return G.rt_to_T(rv, rng.normal(size=(n, 3)))


def test_rot6d_roundtrip():
    rng = np.random.default_rng(0)
    R = random_T(rng, 50)[:, :3, :3]
    assert np.allclose(Rl.rot6d_to_R(Rl.rot6d(R)), R, atol=1e-12)


def test_action10_roundtrip():
    rng = np.random.default_rng(1)
    T = random_T(rng, 20)
    g = rng.uniform(0, 1, 20)
    T2, g2 = Rl.from_action10(Rl.to_action10(T, g))
    assert np.allclose(T2, T, atol=1e-12) and np.allclose(g2, g)


def test_reference_frame_drift_cancels():
    """Any rigid change of the reference frame (SLAM origin, drift accumulated before t)
    leaves the relative chunk unchanged."""
    rng = np.random.default_rng(2)
    T = random_T(rng, 40)
    D = random_T(rng, 1)[0]
    a, _ = Rl.relative_chunk(T, 7, 10)
    b, _ = Rl.relative_chunk(D[None] @ T, 7, 10)
    assert np.allclose(a, b, atol=1e-10)


def test_matches_three_term_formula():
    """(slam->tool_t)^-1 (slam->tool_t+j) == (cam_t->tool_t)^-1 (cam_t->cam_t+j) (cam_t+j->tool_t+j)."""
    rng = np.random.default_rng(3)
    T_sc = random_T(rng, 12)                 # slam->cam
    T_ct = random_T(rng, 12)                 # cam->tool (ball pose . body->tool)
    rel, _ = Rl.relative_chunk(T_sc @ T_ct, 0, 11)
    for j in range(1, 12):
        three = G.inv(T_ct[0][None])[0] @ (G.inv(T_sc[0][None])[0] @ T_sc[j]) @ T_ct[j]
        assert np.allclose(rel[j - 1], three, atol=1e-10)


def test_padding_past_episode_end():
    rng = np.random.default_rng(4)
    T = random_T(rng, 10)
    rel, pad = Rl.relative_chunk(T, 7, 5)
    assert pad.tolist() == [False, False, True, True, True]
    assert np.allclose(rel[2], rel[1]) and np.allclose(rel[4], rel[1])


def test_deploy_reproduces_trajectory():
    """Robot at base->tool_t executing the labels of a demo reproduces the demo's motion."""
    rng = np.random.default_rng(5)
    T_ref = random_T(rng, 30)
    g = rng.uniform(0, 1, 30)
    acts, _ = Rl.chunk_actions(T_ref, g, 3, 20)
    T_base_tool_t = random_T(rng, 1)[0]
    tgt, g2 = Rl.deploy_targets(T_base_tool_t, acts)
    M = T_base_tool_t @ G.inv(T_ref[3][None])[0]        # base<-ref that puts tool_t at the robot
    assert np.allclose(tgt, M[None] @ T_ref[4:24], atol=1e-10) and np.allclose(g2, g[4:24])


def test_ensemble():
    rng = np.random.default_rng(6)
    T = random_T(rng, 1)[0]
    assert np.allclose(Rl.ensemble(np.stack([T, T, T]), [1, 2, 3]), T, atol=1e-12)


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
