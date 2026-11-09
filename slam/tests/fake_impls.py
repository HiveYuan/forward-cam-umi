"""Cheap fake producer implementations for the framework tests (slam.tests.test_pipeline).

Each runs in env 'venv' on the CPU in well under a second and writes tiny files that follow
the cache output contract (slam.pipeline.view docstring). register() adds them to the
registry under their own impl names; the worker imports the functions by name, so the
registration only matters in the orchestrator process. The SLAM step goes through the real
generic step (slam.pipeline.impl_slam.run_slam: input view, mask OR-ing, save_output) with
FakeBackend registered as backend 'fake_slam'.

FAKE_FAIL=<node id>:<segment> in the environment makes that node fail on that segment
(after publishing the segments before it), to test resuming.
"""
import json
import os
from pathlib import Path

import numpy as np

from slam.backends import base as B
from slam.pipeline import registry as R

B.BACKENDS.setdefault("fake_slam", "slam.tests.fake_impls:FakeBackend")

_M = "slam.tests.fake_impls"
IMPLS = (
    R.Impl("preprocess", "fake_frames", "venv", f"{_M}:run_preprocess",
           {"n_frames": 7, "width": 32, "height": 24, "f_px": 30.0},
           data_inputs=("video", "video_ts", "episodes", "intrinsics", "gt_cam_world"),
           exec_params={"jobs": 1}, doc="test: N synthetic frames per episode"),
    R.Impl("tiles", "fake_tiles", "venv", f"{_M}:run_tiles", {"n_det": 2},
           data_inputs=("tile_layout", "tags"), doc="test: fake tile detections"),
    R.Impl("masks", "fake_box", "venv", f"{_M}:run_masks", {"box": [0.25, 0.25, 0.5, 0.5]},
           doc="test: a constant box mask (x, y, w, h as image fractions)"),
    R.Impl("masks", "fake_box_gpu", "venv", f"{_M}:run_masks", {"box": [0.25, 0.25, 0.5, 0.5]},
           gpu_gb=1e6, doc="test: fake_box that needs more GPU memory than any machine has"),
    R.Impl("slam", "fake_slam", "venv", f"{_M}:run_slam",
           {"step_m": 0.01, "lose_every": 3, "dilate_px": 0, "seed": 0},
           per_segment_process=True, doc="test: straight-line trajectory, every n-th frame lost"),
    R.Impl("depth", "fake_depth", "venv", f"{_M}:run_depth", {"model": "fake-depth", "value_m": 1.5},
           doc="test: constant depth on the run's keyframes"),
)


def register():
    """Register the fake implementations (idempotent)."""
    for impl in IMPLS:
        have = R.IMPLS.get((impl.step, impl.name))
        if have is None:
            R.register(impl)
        elif have != impl:
            raise KeyError(f"{impl.step}/{impl.name} registered with different metadata")


def _maybe_fail(job, seg):
    if os.environ.get("FAKE_FAIL") == f"{job.node['id']}:{seg}":
        raise RuntimeError(f"FAKE_FAIL: {job.node['id']} on {seg}")


def _frames(seg_dir):
    with open(Path(seg_dir) / "frames.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------- producers
def run_preprocess(job):
    import cv2
    from slam import config as C
    p = job.params
    with open(Path(job.data["raw_dir"]) / f"{job.session}_glove_episodes.json") as f:
        eps = {e["episode_index"]: e for e in json.load(f)["episodes"]}
    W, H, n = p["width"], p["height"], p["n_frames"]
    K = [[p["f_px"], 0.0, (W - 1) / 2], [0.0, p["f_px"], (H - 1) / 2], [0.0, 0.0, 1.0]]
    done = []
    for seg in job.todo():
        _maybe_fail(job, seg)
        e = eps[int(seg[2:])]
        tmp = job.tmp(seg)
        (tmp / "images").mkdir()
        wall = np.linspace(e["t_start"], e["t_end"], n)
        k0 = 100 * e["episode_index"]
        frames = []
        for i in range(n):
            img = np.full((H, W, 3), (37 * i) % 256, np.uint8)
            img[:, : (i + 1) * W // n] = 255
            if not cv2.imwrite(str(tmp / "images" / f"{i:06d}.jpg"), img):
                raise RuntimeError("imwrite failed")
            frames.append({"i": i, "k": k0 + i, "wall": float(wall[i]), "in_episode": True})
        with open(tmp / "frames.json", "w") as f:
            json.dump({"session": job.session, "stem": job.data["head_stem"], "episode": e,
                       "size": [W, H], "K": K, "frames": frames}, f, indent=1)
        (tmp / "calib.txt").write_text(f"{K[0][0]:.6f} {K[1][1]:.6f} {K[0][2]:.6f} {K[1][2]:.6f}\n")
        T = np.repeat(np.eye(4)[None], n, 0)
        T[:, 0, 3] = 0.01 * np.arange(n)
        np.savez(tmp / "gt.npz", cam_k=np.arange(k0, k0 + n), T_cam_world=T,
                 cam_tiles=np.full(n, 3), cam_rms=np.full(n, 0.5))
        job.publish(seg, tmp)
        done.append(seg)
    return {"segments": done, "exec": job.exec, "config_work": str(C.WORK), "config_raw": str(C.RAW),
            "config_det_cache": str(C.DET_CACHE), "session": C.SESSIONS[job.session]}


def run_tiles(job):
    for seg in job.todo():
        _maybe_fail(job, seg)
        fr = _frames(job.input_view(seg))["frames"]
        n = job.params["n_det"]
        k = np.repeat([f["k"] for f in fr], n)
        tmp = job.tmp(seg)
        np.savez(tmp / "tiles.npz", det_k=k, det_id=np.tile(np.arange(n), len(fr)),
                 det_corners=np.zeros((len(k), 4, 2)))
        job.publish(seg, tmp)
    return {"n_det": job.params["n_det"]}


def box_mask(n, W, H, box):
    x, y, w, h = box
    m = np.zeros((n, H, W), bool)
    m[:, int(y * H):int(y * H) + int(h * H), int(x * W):int(x * W) + int(w * W)] = True
    return m


def run_masks(job):
    for seg in job.todo():
        _maybe_fail(job, seg)
        fj = _frames(job.input_view(seg))
        W, H = fj["size"]
        m = box_mask(len(fj["frames"]), W, H, job.params["box"])
        tmp = job.tmp(seg)
        np.savez(tmp / "masked.npz", masked=np.packbits(m, axis=-1),
                 meta=json.dumps({"name": job.node["name"], "box": job.params["box"]}))
        job.publish(seg, tmp)
    return {"name": job.node["name"]}


def run_slam(job):
    from slam.pipeline import impl_slam
    for seg in job.todo():
        _maybe_fail(job, seg)
    return impl_slam.run_slam(job)


class FakeBackend(B.SlamBackend):
    name = "fake_slam"

    def run(self, inp, params):
        import cv2
        n = len(inp)
        W, H = inp.size
        for p in inp.images:
            img = cv2.imread(str(p))
            if img is None or img.shape[:2] != (H, W):
                raise RuntimeError(f"bad input image {p}")
        T = np.repeat(np.eye(4)[None], n, 0)
        T[:, 0, 3] = params["step_m"] * np.arange(n)
        tracked = np.ones(n, bool)
        if params["lose_every"]:
            tracked[params["lose_every"] - 1::params["lose_every"]] = False
        kf = np.array([0, n // 2, n - 1])
        pose = np.zeros((len(kf), 7))
        pose[:, 0] = -T[kf, 0, 3]
        pose[:, 6] = 1.0
        masked_frac = None if inp.masked is None else float(inp.masked.mean())
        return B.SlamOutput(T, tracked, metric=False, kf_t=kf,
                            kf_disp=np.full((len(kf), H // 8, W // 8), 0.5, np.float32),
                            kf_pose_cw=pose, extra={"score": np.arange(n, dtype=float)},
                            meta={"n_keyframes": len(kf), "runtime_s": 0.0, "masked_frac": masked_frac,
                                  "valid_frac": None if inp.masked is None else 1.0 - masked_frac})


def run_depth(job):
    e = job.input_of("slam")
    for seg in job.todo():
        _maybe_fail(job, seg)
        view = job.input_view(seg)
        W, H = _frames(view)["size"]
        traj = B.load_output(view / "slam" / f"{e['name']}.npz")
        kf_t = traj["kf_t"]
        tmp = job.tmp(seg)
        np.savez(tmp / "depth.npz", kf_t=kf_t,
                 depth=np.full((len(kf_t), H, W), job.params["value_m"], np.float16),
                 model=np.array(job.params["model"]))
        job.publish(seg, tmp)
    return {"run": e["name"]}
