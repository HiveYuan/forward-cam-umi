"""Group-share sampling of slam.train_rel (python -m slam.tests.test_sampling, lerobot52 env for the sampler test)."""
import numpy as np

from slam import train_rel as T

GROUPS = {"teleop": (0, 178), "glove": (178, 378), "collected": (378, 10 ** 6)}


def test_group_weights_shares():
    ids = [0, 5, 200, 300, 400, 401]
    lengths = [100, 100, 300, 300, 150, 150]               # teleop 200, glove 600, collected 300 anchors
    w, s = T.group_weights(ids, lengths, GROUPS, {"teleop": 0.18})
    share = {g: sum(w[k] * lengths[k] for k, e in enumerate(ids) if GROUPS[g][0] <= e < GROUPS[g][1]) for g in GROUPS}
    assert abs(share["teleop"] - 0.18) < 1e-12 and abs(sum(share.values()) - 1) < 1e-12
    assert abs(share["glove"] / share["collected"] - 2.0) < 1e-12        # the rest in proportion to anchors
    assert s["teleop"]["frame_share"] == round(200 / 1100, 4) and s["teleop"]["share"] == 0.18
    for bad in ({"nope": 0.1}, {"teleop": 1.2}, {"teleop": 0.0}):
        try:
            T.group_weights(ids, lengths, GROUPS, bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    try:
        T.group_weights([0, 2000000], [10, 10], {"a": (0, 10)}, {"a": 0.5})
        raise AssertionError("uncovered episode")
    except ValueError:
        pass


def test_sampler_draws_the_shares():
    try:
        import lerobot  # noqa: F401
    except ImportError:
        print("skip: lerobot not installed in this env")
        return

    class DS:
        episode_ids = [0, 5, 200, 300, 400, 401]
    lengths = np.array([100, 100, 300, 300, 150, 150])
    to = np.cumsum(lengths)
    Cls = T.weighted_sampler_class({"ds": DS()}, GROUPS, {"teleop": 0.18})
    sp = Cls(list(to - lengths), list(to), shuffle=True, seed=1000)
    a = np.array(list(sp))
    b = np.array(list(sp))                                    # the next epoch: another draw
    assert len(a) == lengths.sum() and not np.array_equal(a, b)
    sp2 = Cls(list(to - lengths), list(to), shuffle=True, seed=1000)
    assert np.array_equal(np.array(list(sp2)), a)             # a pure function of (seed, epoch)
    big = np.concatenate([np.array(list(sp)) for _ in range(40)])
    assert abs((big < 200).mean() - 0.18) < 0.01               # teleop anchors are positions 0-199
    assert abs(((big >= 200) & (big < 800)).mean() - 0.82 * 600 / 900) < 0.01


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
