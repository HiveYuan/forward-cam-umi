"""slam.deploy_rel without a robot or a policy (python -m slam.tests.test_deploy_rel; numpy only)."""
import numpy as np

from slam import geometry as G
from slam import relative as Rl
from slam import relative_dataset as RD
from slam.deploy_rel import RelativeChunkPlanner, StateBuilder, T_to_pose6


def rand_T(rng):
    rv, t = rng.normal(0, 0.8, 3), rng.normal(0, 0.3, 3)
    return G.rt_to_T(rv[None], t[None])[0]


def test_pose6_roundtrip():
    rng = np.random.default_rng(0)
    for _ in range(50):
        T = rand_T(rng)
        assert np.allclose(RD.pose_T(T_to_pose6(T)), T, atol=1e-9)


def test_planner_reproduces_targets():
    """A chunk that encodes a known absolute trajectory: the planner returns it exactly, from any anchor."""
    rng = np.random.default_rng(1)
    traj = [rand_T(rng) for _ in range(8)]
    pl = RelativeChunkPlanner(coeff=0.01, horizon=5)
    for t in range(3):                                   # three anchors predicting the same absolute targets
        A = rand_T(rng)
        rel = G.inv(A[None]) @ np.stack(traj[t:t + 5])
        pl.add(t, A, Rl.to_action10(rel, np.full(5, 0.3 + t)))
    T, g, k = pl.current(2)                              # ticks 0..2 all predicted tick 2
    assert k == 3 and np.allclose(T, traj[2], atol=1e-9)
    w = np.exp(-0.01 * np.arange(3))
    assert abs(g - float(np.sum(w * np.array([0.3, 1.3, 2.3])) / w.sum())) < 1e-12


def test_state_builder_matches_training():
    rng = np.random.default_rng(2)
    T0, T1, Tc = rand_T(rng), rand_T(rng), rand_T(rng)
    g = 0.4
    for kind, ref in (("gripper", np.array([g])),
                      ("pose_gripper", RD.pose_state(T_to_pose6(T1), [g])[0]),
                      ("startpose_gripper", RD.startpose_state(T_to_pose6(T0), T_to_pose6(T1), [g])[0]),
                      ("campose_gripper", RD.pose_state(T_to_pose6(Tc), [g])[0]),
                      ("startcam_gripper", RD.startcam_state(T_to_pose6(T0), T_to_pose6(T1), T_to_pose6(Tc), [g])[0])):
        sb = StateBuilder(kind)
        sb.reset(T0)
        assert np.allclose(sb(T1, g, Tc), ref, atol=1e-6), kind
        assert len(sb(T1, g, Tc)) == len(RD.STATE_NAMES[kind])


if __name__ == "__main__":
    for f in (test_pose6_roundtrip, test_planner_reproduces_targets, test_state_builder_matches_training):
        f()
        print("ok", f.__name__)
