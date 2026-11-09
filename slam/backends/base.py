"""SLAM backend interface: DROID-SLAM now, AMB3R-VO (or any other) later.

A backend turns one segment's frames into one camera pose per frame. It gets:
  SlamInput.images      paths of the undistorted pinhole frames, in time order (all W x H)
  SlamInput.k, t        original frame index and wall time [s] of each image
  SlamInput.K, size     3x3 intrinsics of the images, (W, H)
  SlamInput.masked      (N, H, W) bool, True = pixel moves on its own (hand, glove, ...) or is
                        excluded for evaluation (tiles); None = no masks. The backend decides
                        how to use it (DROID: zero BA weight + keyframe selection; a
                        feed-forward model may ignore it, which it must state in meta
                        masks_used, see below)
and returns SlamOutput:
  T_slam_cam            (N, 4, 4) camera -> SLAM-frame pose of every input frame (NaN = none)
  tracked               (N,) bool, False where the backend lost tracking / has no pose
  metric                True if translations are in metres (the 'native' scale method then
                        applies), False if up to scale (monocular DROID)
  kf_t, kf_disp         optional depth for scale method B: image indices (M,) (1-D integers in
                        [0, N)) and inverse depth (M, H//8, W//8) float, finite or NaN (= no
                        depth), in the SLAM's units on the 1/8 grid of the input (DROID's native
                        output; other backends resample to this grid)
  kf_pose_cw            optional (M, 7) keyframe world->cam poses [t q] (DROID convention);
                        needs kf_t
  extra                 backend-specific arrays, saved as-is (prefixed 'x_')
  meta                  json-able facts: runtime, peak GPU, keyframes, ... and
                        masks_used: the names (of SlamInput.mask_names) of the masks the backend
                        actually applied; default (key absent) = all configured masks. A
                        feed-forward backend that ignores the masks MUST set masks_used = [].
                        The saved meta has both 'masks' (configured) and 'masks_used'.

save_output() writes the traj.npz every downstream step reads; its keys are a superset of
the legacy slam.run_droid output (k, i, T_slam_cam, meta, kf_*), so slam.evaluate,
slam.scale, slam.labels and slam.tiles read it unchanged.
"""
import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

BACKENDS = {"droid": "slam.backends.droid:DroidBackend"}


@dataclass
class SlamInput:
    images: list
    k: np.ndarray
    t: np.ndarray
    K: np.ndarray
    size: tuple
    masked: np.ndarray = None
    mask_names: list = field(default_factory=list)

    def __len__(self):
        return len(self.images)


@dataclass
class SlamOutput:
    T_slam_cam: np.ndarray
    tracked: np.ndarray
    metric: bool
    kf_t: np.ndarray = None
    kf_disp: np.ndarray = None
    kf_pose_cw: np.ndarray = None
    extra: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


class SlamBackend:
    """Subclass and register in BACKENDS. run() must return one pose per input frame."""
    name = "base"

    def run(self, inp: SlamInput, params: dict) -> SlamOutput:
        raise NotImplementedError


def get(name):
    if name not in BACKENDS:
        raise KeyError(f"unknown SLAM backend {name!r}; known {sorted(BACKENDS)}")
    mod, cls = BACKENDS[name].split(":")
    return getattr(importlib.import_module(mod), cls)()


def unpack_masks(path, n, size):
    """masked.npz (packbits along the last axis) -> (n, H, W) bool."""
    W, H = size
    m = np.unpackbits(np.load(path)["masked"], axis=-1, count=W).astype(bool)
    if m.shape != (n, H, W):
        raise ValueError(f"{path}: mask shape {m.shape} != {(n, H, W)}")
    return m


def load_input(seg_dir, mask_names=()):
    """SlamInput from a segment directory in the legacy layout (images/, frames.json,
    masks/<name>.npz); several masks are OR-ed."""
    seg_dir = Path(seg_dir)
    fj = json.load(open(seg_dir / "frames.json"))
    fr = fj["frames"]
    size = tuple(fj["size"])
    masked = None
    for name in mask_names:
        m = unpack_masks(seg_dir / "masks" / f"{name}.npz", len(fr), size)
        masked = m if masked is None else (masked | m)
    return SlamInput(images=[seg_dir / "images" / f"{f['i']:06d}.jpg" for f in fr],
                     k=np.array([f["k"] for f in fr], int), t=np.array([f["wall"] for f in fr], float),
                     K=np.array(fj["K"], float), size=size, masked=masked, mask_names=list(mask_names))


def check_output(out, n, size=None, mask_names=None):
    """Validate a backend's SlamOutput for n input frames of size (W, H) (None: the 1/8 grid of
    kf_disp is not checked) and configured masks mask_names (None: masks_used not checked)."""
    if out.T_slam_cam.shape != (n, 4, 4):
        raise ValueError(f"T_slam_cam has shape {out.T_slam_cam.shape}, expected {(n, 4, 4)}")
    if out.tracked.shape != (n,) or out.tracked.dtype != bool:
        raise ValueError("tracked must be a (N,) bool array")
    ok = np.isfinite(out.T_slam_cam).all((1, 2))
    if np.any(out.tracked & ~ok):
        raise ValueError("tracked frames must have finite poses")
    if (out.kf_t is None) != (out.kf_disp is None):
        raise ValueError("kf_t and kf_disp come together")
    if out.kf_t is not None:
        kf_t = np.asarray(out.kf_t)
        if kf_t.ndim != 1 or not np.issubdtype(kf_t.dtype, np.integer):
            raise ValueError(f"kf_t must be a 1-D integer array, got shape {kf_t.shape} dtype {kf_t.dtype}")
        if len(kf_t) and (kf_t.min() < 0 or kf_t.max() >= n):
            raise ValueError(f"kf_t must be image indices in [0, {n}), got [{kf_t.min()}, {kf_t.max()}]")
        disp = np.asarray(out.kf_disp)
        grid = None if size is None else (int(size[1]) // 8, int(size[0]) // 8)
        if disp.ndim != 3 or len(disp) != len(kf_t) or (grid is not None and disp.shape[1:] != grid):
            want = f"({len(kf_t)}, {grid[0]}, {grid[1]})" if grid else f"({len(kf_t)}, H/8, W/8)"
            raise ValueError(f"kf_disp has shape {disp.shape}, expected {want}")
        if not np.issubdtype(disp.dtype, np.floating):
            raise ValueError(f"kf_disp must be a float array, got {disp.dtype}")
        if np.isinf(disp).any():
            raise ValueError("kf_disp must be finite or NaN (no depth), not inf")
    if out.kf_pose_cw is not None:
        if out.kf_t is None:
            raise ValueError("kf_pose_cw needs kf_t")
        pose = np.asarray(out.kf_pose_cw)
        if pose.shape != (len(out.kf_t), 7) or not np.issubdtype(pose.dtype, np.number):
            raise ValueError(f"kf_pose_cw has shape {pose.shape} dtype {pose.dtype}, expected ({len(out.kf_t)}, 7) numbers")
    used = (out.meta or {}).get("masks_used")
    if used is not None:
        if not isinstance(used, (list, tuple)) or not all(isinstance(m, str) for m in used):
            raise ValueError(f"meta masks_used must be a list of mask names, got {used!r}")
        if mask_names is not None and set(used) - set(mask_names):
            raise ValueError(f"meta masks_used {list(used)} not among the configured masks {list(mask_names)}")


def save_output(path, out, inp, backend, params):
    """Standard traj.npz (see module docstring)."""
    check_output(out, len(inp), inp.size, inp.mask_names)
    T = out.T_slam_cam.astype(np.float64).copy()
    T[~out.tracked] = np.nan
    meta = dict(out.meta)
    used = meta.get("masks_used")
    meta["masks_used"] = list(inp.mask_names) if used is None else list(used)
    meta.update({"backend": backend, "masks": list(inp.mask_names), "metric": bool(out.metric),
                 "n_frames": len(inp), "n_tracked": int(out.tracked.sum()),
                 "params": params})
    arrays = {"k": np.asarray(inp.k), "i": np.arange(len(inp)), "T_slam_cam": T,
              "tracked": out.tracked, "metric": np.array(bool(out.metric))}
    for key in ("kf_t", "kf_disp", "kf_pose_cw"):
        v = getattr(out, key)
        if v is not None:
            arrays[key] = np.asarray(v)
    for k, v in out.extra.items():
        arrays[f"x_{k}"] = np.asarray(v)
    np.savez(path, meta=json.dumps(meta, default=str), **arrays)
    return meta


def load_output(path):
    z = np.load(path)
    out = {k: z[k] for k in z.files if k != "meta"}
    out["meta"] = json.loads(str(z["meta"]))
    out.setdefault("tracked", np.isfinite(out["T_slam_cam"]).all((1, 2)))
    out["metric"] = bool(out.get("metric", np.array(False)))
    return out
