"""Regression checks of the YAM FK (lerobot env: python -m slam.tests.test_robot_fk).

The reference values are i2rt's FK at 0b475453 (slam.robot_fk). The frame is validated against
i2rt's IK (pilot_glove_HHs3) in experiments/audits/fk_frame (0.4 mm median); this test only
guards against a changed model, e.g. another i2rt checkout.
"""
import numpy as np

from slam.robot_fk import YamFK

REF = {
    (0, 0, 0, 0, 0, 0): [[0, 0, 1, 0.1106], [0, 1, 0, 0], [-1, 0, 0, 0.1735]],
    (0.3, 0.8, 0.9, -0.4, 0.2, 0.5): [[-0.29969, 0.0403, 0.95319, 0.17203],
                                      [0.39913, 0.91277, 0.0869, 0.04581],
                                      [-0.86653, 0.40649, -0.28963, 0.35486]],
}


def test_reference_poses():
    fk = YamFK()
    for q, T in REF.items():
        assert np.allclose(fk(np.array(q))[:3], np.array(T), atol=5e-5), q


def test_batch_and_rigid():
    fk = YamFK()
    Q = np.random.default_rng(0).uniform(-1, 1, (20, 6)) + np.array([0, 1.5, 1.5, 0, 0, 0])
    T = fk(Q)
    assert T.shape == (20, 4, 4)
    assert np.allclose(T[3], fk(Q[3]))
    R = T[:, :3, :3]
    assert np.allclose(R @ np.swapaxes(R, 1, 2), np.eye(3), atol=1e-9)
    assert np.allclose(np.linalg.det(R), 1)


if __name__ == "__main__":
    test_reference_poses()
    test_batch_and_rigid()
    print("OK")
