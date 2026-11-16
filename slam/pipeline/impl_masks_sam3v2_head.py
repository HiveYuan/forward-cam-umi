"""Masks step, implementation sam3_v2_head (env sam3): sam3_v2 with the held-object gate on the HEAD-camera
gripper width.

Decision 2026-11-12: no wrist-camera data in the algorithm. sam3_v2 gates its held-object prompt on the wrist
camera's width (<gt_dir>/gripper_wrist.npz, slam.wrist_width). This implementation runs the same code with the
same parameters on the head camera's width instead (<gt_dir>/gripper_head.npz, slam.head_width; same file
layout). Unlike sam3_v2, it refuses to run without that file: a missing width would silently switch the held
object off.

sam3_v2's module is reused unchanged, so sam3_v2's cache keys and cached masks stay valid. Its one width read,
masks_sam3v2.load_gripper_wrist(<gt_dir>/gripper_wrist.npz), is redirected to gripper_head.npz for the duration
of the call; any other path raises.
"""
from contextlib import contextmanager
from pathlib import Path

WIDTH_FILE = "gripper_head.npz"


@contextmanager
def head_width_source(gt_dir):
    """masks_sam3v2.load_gripper_wrist reads <gt_dir>/gripper_head.npz inside the block (restored after)."""
    from slam import masks_sam3v2 as S
    head = Path(gt_dir) / WIDTH_FILE
    if not head.exists():
        raise FileNotFoundError(f"{head} missing: run python -m slam.head_width predict --session <session>")
    orig = S.load_gripper_wrist

    def load(path):
        if Path(path) != Path(gt_dir) / "gripper_wrist.npz":
            raise RuntimeError(f"sam3_v2_head: unexpected width read {path} (sam3_v2's loader changed?)")
        return orig(head)

    S.load_gripper_wrist = load
    try:
        yield head
    finally:
        S.load_gripper_wrist = orig


def run_sam3_v2_head(job):
    from slam import config as C
    from slam.pipeline import impl_masks_sam3v2 as base
    with head_width_source(C.gt_dir(job.session)) as head:
        job.log(f"held-object gate on the head-camera width: {head}")
        return base.run_sam3_v2(job)
