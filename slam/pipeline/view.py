"""Segment views: the legacy per-segment layout, assembled from cached producer outputs
with symlinks, so the stable slam.* code (evaluate, scale, labels, tiles, ...) runs on it
unchanged with config.WORK pointed at the view root.

  <root>/<session>/gt                       -> data.gt_dir
  <root>/<session>/segments/epNN/
      images/ frames.json calib.txt gt.npz  -> cache/preprocess/<key>/epNN/...
      tiles.npz                             -> cache/tiles/<key>/epNN/tiles.npz
      masks/<name>.npz                      -> cache/masks/<key>/epNN/masked.npz
      slam/<run>.npz                        -> cache/slam/<key>/epNN/traj.npz
      depth/<run>_<model>.npz               -> cache/depth/<key>/epNN/depth.npz

Cache output contract (what each producer writes into its epNN/ directory):
  preprocess  images/NNNNNN.jpg, frames.json, calib.txt, gt.npz   (slam.preprocess format)
  tiles       tiles.npz                                          (slam.tiles detect format)
  masks       masked.npz: masked = packbits of (T, H, W) bool along the last axis, True = do
              not use; meta (json); optional qa.jpg
  slam        traj.npz (slam.backends.base.save_output format)
  depth       depth.npz: kf_t, depth (n_kf, H, W) float16 metres, model
"""
import os
import shutil
from pathlib import Path

PRE_FILES = ("images", "frames.json", "calib.txt", "gt.npz")
OUTPUT_FILE = {"tiles": "tiles.npz", "masks": "masked.npz", "slam": "traj.npz", "depth": "depth.npz"}


def _link(src, dst):
    src, dst = Path(src), Path(dst)
    if not src.exists():
        raise FileNotFoundError(f"view source missing: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        if dst.is_symlink() and os.readlink(dst) == str(src):
            return
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    os.symlink(src, dst)


def view_path(entry, seg):
    """Path of an entry's file inside a segment view directory (relative)."""
    step = entry["step"]
    if step == "tiles":
        return Path("tiles.npz")
    if step == "masks":
        return Path("masks") / f"{entry['name']}.npz"
    if step == "slam":
        return Path("slam") / f"{entry['name']}.npz"
    if step == "depth":
        return Path("depth") / f"{entry['run']}_{entry['model']}.npz"
    raise ValueError(step)


def link_segment(seg_dir, seg, entries):
    """Populate one segment view directory. entries: dicts with step, dir (cache entry),
    name, and for depth: run, model."""
    seg_dir = Path(seg_dir)
    seg_dir.mkdir(parents=True, exist_ok=True)
    for e in entries:
        src_seg = Path(e["dir"]) / seg
        if e["step"] == "preprocess":
            for f in PRE_FILES:
                _link(src_seg / f, seg_dir / f)
        else:
            _link(src_seg / OUTPUT_FILE[e["step"]], seg_dir / view_path(e, seg))


def build(root, session, segments, gt_dir, entries, fresh=True):
    """Assemble a view at <root>. fresh=True removes an earlier view first (root must be a
    directory created by this module: it carries a .slam_view marker)."""
    root = Path(root)
    if fresh and root.exists():
        if not (root / ".slam_view").exists():
            raise RuntimeError(f"{root} exists and is not a view; refusing to delete it")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / ".slam_view").write_text("segment view; safe to delete\n")
    _link(Path(gt_dir), root / session / "gt")
    segs_root = root / session / "segments"
    for seg in segments:
        link_segment(segs_root / seg, seg, entries)
    return segs_root
