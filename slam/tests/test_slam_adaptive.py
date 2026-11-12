"""droid_adaptive's decision (python -m slam.tests.test_slam_adaptive; CPU, fake backend, no DROID)."""
import numpy as np

from slam.backends import base as B
from slam.pipeline.impl_slam_adaptive import preroll_peak, run_adaptive


def rotz(deg):
    a = np.radians(deg)
    T = np.eye(4)
    T[:2, :2] = [[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]
    return T


class FakeBackend:
    """Yaw angle per frame from a function of time; records the inputs it was given."""

    def __init__(self, yaw_of_t):
        self.yaw_of_t, self.calls = yaw_of_t, []

    def run(self, inp, params):
        self.calls.append((len(inp), float(inp.t[0])))
        T = np.stack([rotz(self.yaw_of_t(t)) for t in inp.t])
        return B.SlamOutput(T_slam_cam=T, tracked=np.ones(len(inp), bool), metric=False,
                            kf_t=np.array([0, len(inp) - 1]), kf_disp=np.ones((2, 2, 3), np.float32),
                            meta={"runtime_s": 1.0})


def fake_input(n=250, dt=0.04):            # 10 s at 25 fps; the episode starts at 5 s
    return B.SlamInput(images=[f"{i}.jpg" for i in range(n)], k=np.arange(n), t=np.arange(n) * dt,
                       K=np.eye(3), size=(24, 16), masked=None, mask_names=[])


def test_peak():
    t = np.arange(10) * 0.1
    yaw = np.cumsum([0, 5, 5, 20, 5, 5, 50, 5, 5, 5])              # 200 deg/s into frame 3, 500 deg/s into frame 6
    T = np.stack([rotz(y) for y in yaw])
    p, tp = preroll_peak(T, t, t_start=0.55)                       # only pairs ending before 0.55 s count
    assert abs(p - 200) < 1e-6 and abs(tp - (0.3 - 0.55)) < 1e-9
    assert preroll_peak(T, t, t_start=0.0) == (0.0, None)          # no pair before the start


def test_turn_gives_short_start():
    inp = fake_input()
    be = FakeBackend(lambda t: 180.0 * min(max(t - 2.0, 0.0), 0.5) / 0.5)   # 180 deg in 0.5 s at t = 2 s (360 deg/s)
    out, info = run_adaptive(be, inp, t_start=5.0, params={}, turn_deg_s=120.0, short_preroll_s=1.0)
    assert info["short_start"] and abs(info["preroll_peak_deg_s"] - 360) < 1e-6
    assert len(be.calls) == 2 and be.calls[1] == (150, 4.0)          # second run from t = 4 s (frame 100)
    assert info["first_frame"] == 100 and not out.tracked[:100].any() and out.tracked[100:].all()
    assert out.kf_t[0] == 100 and out.T_slam_cam.shape == (250, 4, 4)


def test_calm_keeps_first_run():
    inp = fake_input()
    be = FakeBackend(lambda t: 30.0 * t)                            # 30 deg/s everywhere
    out, info = run_adaptive(be, inp, t_start=5.0, params={}, turn_deg_s=120.0, short_preroll_s=1.0)
    assert not info["short_start"] and len(be.calls) == 1 and out.tracked.all() and info["first_frame"] == 0


if __name__ == "__main__":
    test_peak()
    test_turn_gives_short_start()
    test_calm_keeps_first_run()
    print("ok test_slam_adaptive")
