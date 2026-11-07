"""Relative action labels (design doc, "Relative labels").

The dataset stores ONE pose per step: the tool in a per-episode reference frame,
ref->tool_k (ref = the segment's SLAM frame for glove data, the robot base for teleop).
At training time a chunk anchored at step t is converted to relative poses

    tool_t->tool_{t+j} = (ref->tool_t)^-1 (ref->tool_{t+j}),   j = 1..H

which equals (cam_t->tool_t)^-1 (cam_t->cam_{t+j}) (cam_{t+j}->tool_{t+j}) for SLAM
data, so any drift of the reference frame accumulated before t cancels and only the
error inside the window remains. The chunk length can change without rebuilding.

Action per step (10): relative translation (3) + relative rotation as 6D (first two
columns of R) + absolute gripper width (1).

Deployment: FK gives base->tool_t; the target for step j is base->tool_t . rel_j.
Temporal ensembling first maps every past chunk's prediction for the current step
into the base frame with the FK pose of the step at which it was predicted.
"""
import numpy as np

from slam import geometry as G


def relative_chunk(T_ref_tool, t, horizon):
    """(N, 4, 4) poses, anchor index t -> (horizon, 4, 4) tool_t->tool_{t+j}, j=1..horizon,
    and a (horizon,) bool 'is_pad' for steps past the end (LeRobot's action_is_pad);
    padded steps repeat the last pose."""
    N = len(T_ref_tool)
    j = np.arange(t + 1, t + 1 + horizon)
    pad = j >= N
    j = np.minimum(j, N - 1)
    return G.inv(T_ref_tool[t][None]) @ T_ref_tool[j], pad


def rot6d(R):
    """(..., 3, 3) -> (..., 6): first two columns, [r00 r10 r20 r01 r11 r21]."""
    return np.concatenate([R[..., :, 0], R[..., :, 1]], -1)


def rot6d_to_R(d):
    """(..., 6) -> (..., 3, 3) by Gram-Schmidt (Zhou et al. 2019)."""
    a1, a2 = d[..., :3], d[..., 3:]
    b1 = a1 / np.linalg.norm(a1, axis=-1, keepdims=True)
    a2 = a2 - (b1 * a2).sum(-1, keepdims=True) * b1
    b2 = a2 / np.linalg.norm(a2, axis=-1, keepdims=True)
    b3 = np.cross(b1, b2)
    return np.stack([b1, b2, b3], -1)


def to_action10(rel, gripper):
    """(H, 4, 4) relative poses + (H,) absolute gripper -> (H, 10)."""
    return np.concatenate([rel[:, :3, 3], rot6d(rel[:, :3, :3]), np.asarray(gripper, float)[:, None]], 1)


def from_action10(a):
    """(H, 10) -> ((H, 4, 4) relative poses, (H,) gripper)."""
    T = np.tile(np.eye(4), (len(a), 1, 1))
    T[:, :3, :3] = rot6d_to_R(a[:, 3:9])
    T[:, :3, 3] = a[:, :3]
    return T, a[:, 9]


def chunk_actions(T_ref_tool, gripper, t, horizon):
    """Training-time conversion for one sample: (horizon, 10) actions and is_pad."""
    rel, pad = relative_chunk(T_ref_tool, t, horizon)
    g = np.asarray(gripper, float)[np.minimum(np.arange(t + 1, t + 1 + horizon), len(gripper) - 1)]
    return to_action10(rel, g), pad


def deploy_targets(T_base_tool_t, actions):
    """FK pose at prediction time + (H, 10) predicted actions -> (H, 4, 4) base->tool targets
    and (H,) gripper commands (IK is the robot side's job)."""
    rel, g = from_action10(actions)
    return T_base_tool_t[None] @ rel, g


def ensemble(targets, weights):
    """Temporal ensemble of K predictions for the SAME step, each already in the base
    frame ((K, 4, 4)): weighted mean translation and chordal-mean rotation."""
    w = np.asarray(weights, float)
    w = w / w.sum()
    out = np.eye(4)
    out[:3, 3] = (w[:, None] * targets[:, :3, 3]).sum(0)
    U, _, Vt = np.linalg.svd((w[:, None, None] * targets[:, :3, :3]).sum(0))
    out[:3, :3] = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    return out
