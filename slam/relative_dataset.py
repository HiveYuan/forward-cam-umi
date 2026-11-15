#!/usr/bin/env python3
"""Training-time relative actions on the exp016 datasets (P3, design 2026-11-11).

RelChunkDataset wraps a LeRobotDataset of slam.rel_dataset (pilot_mix_gHs3_rel_tile / _rel_slam) and
returns, for an anchor step t:
  action          (H, 10)  rel_j = anchor_t^-1 . pose_{t+j}, j = 0..H-1 (LeRobot's chunk convention):
                           translation (3) + 6D rotation (6, slam.relative.rot6d) + absolute gripper (1)
  action_is_pad   (H,)     past the episode end, or step t+j flagged by one of `masks`
  observation.state (1,)   gripper (stored as a scalar column); with state="pose_gripper" (10,) = the current
                           tool pose in the robot base (xyz + 6D rotation of the anchor pose: teleop FK of the
                           measured joints, glove the tile-chain pose) + gripper (test D1, 2026-11-13). Only for a
                           dataset whose poses are in the robot base (variant "tile"); its stats file must carry
                           the same state.
                           state="startpose_gripper" (10,) = the current tool pose relative to the episode's start
                           pose (T_start^-1 . T_t: xyz + 6D rotation) + gripper; tile-free (test D2a, 2026-11-14).
                           T_start = the anchor pose at the episode's first step with a valid pose (slam_valid where
                           the column exists); at deployment, FK(now) relative to FK at the rollout's start.
anchor="prev_action" (test (a), 2026-11-12) uses the previous step's target pose as anchor_t instead of the
anchor_pose column (see anchor_poses); its stats file must be computed with the same anchor.
plus the images and LeRobot's bookkeeping keys. anchor_t is the dataset's anchor_pose (teleop: FK of
the measured joints; glove: the pose itself), so rel_0 is the identity for glove steps and the
commanded lead (~2 frames) for teleop, as in Yosub's joint-space data.

Anchors flagged by a mask are not sampled: the wrapper exposes only valid anchors as a contiguous
index space, with per-episode boundaries in meta.episodes, which is all lerobot_train's
EpisodeAwareSampler reads. Both glove datasets carry identical flags, so G-tile and G-slam train on
the same anchors and masked steps.

meta.features reports action (10,) and observation.state (1,); meta.stats is the relative-action
statistics file given (one file for every arm, so that losses are comparable).

  python -m slam.relative_dataset stats  --root <lerobot root> --repo pilot_mix_gHs3_rel_tile \
      --episodes calib/train_eps_pilot_head_Hgt.txt --out <stats.json>      # numpy only, no video
  python -m slam.relative_dataset check  --root ... --repo ... --episodes ... --stats <stats.json>
"""
import argparse
import json
from pathlib import Path

import numpy as np

from slam import geometry as G
from slam import relative as Rl

H_DEFAULT = 100
MASK_KEYS = ("slam_valid", "ik_unreached")
STAT_Q = (1, 10, 50, 90, 99)


def _bad(name, v):
    """1 where a flag column marks the step unusable."""
    v = np.asarray(v, float)
    if name == "slam_valid":
        return v < 0.5
    if name == "ik_unreached":
        return v > 0.5
    raise ValueError(f"unknown mask {name!r}")


def pose_T(p):
    """(..., 6) x y z + rotation vector -> (..., 4, 4)."""
    p = np.asarray(p, float)
    sh = p.shape[:-1]
    T = G.rt_to_T(p.reshape(-1, 6)[:, 3:6], p.reshape(-1, 6)[:, :3])
    return T.reshape(*sh, 4, 4)


def rel10(anchor6, act7):
    """anchor (6,) and actions (H, 7) -> (H, 10) relative actions."""
    A = pose_T(anchor6)
    T = pose_T(act7[:, :6])
    rel = G.inv(A[None]) @ T
    return Rl.to_action10(rel, act7[:, 6])


def read_columns(root):
    import pandas as pd
    files = sorted((Path(root) / "data").glob("chunk-*/file-*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files]).sort_values("index").reset_index(drop=True)


def load_episode_list(path):
    txt = Path(path).read_text().strip()
    return [int(x) for x in json.loads(txt)] if txt.startswith("[") else [int(x) for x in txt.split()]


def valid_anchors(df, masks, anchor="anchor_pose"):
    """Anchors t that may be sampled: no mask flags step t (and, for anchor "prev_action", step t-1)."""
    ok = np.ones(len(df), bool)
    for m in masks:
        ok &= ~_bad(m, df[m].values)
    if anchor == "prev_action":
        prev = _prev_index(df["episode_index"].values)
        ok = ok & ok[prev]
    return ok


ANCHORS = ("anchor_pose", "prev_action")
STATES = ("gripper", "pose_gripper", "startpose_gripper")
_POSE10 = ["x", "y", "z", "r00", "r10", "r20", "r01", "r11", "r21", "gripper.pos"]
STATE_NAMES = {"gripper": ["gripper.pos"], "pose_gripper": _POSE10, "startpose_gripper": _POSE10}


def start_poses(df):
    """{episode: (6,) anchor pose at its first step with a valid pose (slam_valid where present)}."""
    A = np.stack(df["anchor_pose"].values).astype(float)
    ep = df["episode_index"].values
    ok = ~_bad("slam_valid", df["slam_valid"].values) if "slam_valid" in df else np.ones(len(df), bool)
    out = {}
    for e in np.unique(ep):
        r = np.where((ep == e) & ok)[0]
        if len(r):
            out[int(e)] = A[r[0]]
    return out


def startpose_state(start6, anchor6, grip):
    """(6,) start pose, (N, 6) current poses, (N,) gripper -> (N, 10): T_start^-1 . T_t (xyz + 6D rotation) + gripper."""
    rel = G.inv(pose_T(np.asarray(start6, float))[None]) @ pose_T(np.asarray(anchor6, float).reshape(-1, 6))
    return Rl.to_action10(rel, np.asarray(grip, float).reshape(-1))


def pose_state(anchor6, grip):
    """(N, 6) anchor poses + (N,) gripper -> (N, 10) state: xyz + 6D rotation (as the actions) + gripper."""
    anchor6 = np.asarray(anchor6, float).reshape(-1, 6)
    return Rl.to_action10(pose_T(anchor6), np.asarray(grip, float).reshape(-1))


def check_state_dataset(root, state):
    """A pose state needs absolute poses in the robot base: the tile variant of slam.rel_dataset."""
    if state not in STATES:
        raise ValueError(f"state must be one of {STATES}, got {state!r}")
    if state == "pose_gripper":
        meta = json.load(open(Path(root) / "meta" / "relative_labels.json"))
        if meta.get("variant") != "tile":
            raise ValueError(f"state 'pose_gripper' needs robot-base poses (variant 'tile'); {root} is "
                             f"variant {meta.get('variant')!r}")


def _prev_index(ep):
    """Index of step t-1 in the same episode, or t itself at an episode's first step."""
    i = np.arange(len(ep))
    prev = i - 1
    prev[0] = 0
    first = np.r_[True, ep[1:] != ep[:-1]]
    prev[first] = i[first]
    return prev


def anchor_poses(df, anchor="anchor_pose"):
    """(N, 6) anchor pose per step. "anchor_pose": the dataset's column (teleop: FK of the measured joints,
    glove: the pose itself). "prev_action": the previous step's target pose (teleop: the command sent at t-1,
    glove: the pose at t-1; at an episode's first step the step's own target), so rel_0 is one step of motion
    in both halves and at deployment the anchor is the last command sent (decision 2026-11-12, test (a))."""
    if anchor == "anchor_pose":
        return np.stack(df["anchor_pose"].values).astype(float)
    if anchor == "prev_action":
        act = np.stack(df["action"].values).astype(float)[:, :6]
        return act[_prev_index(df["episode_index"].values)]
    raise ValueError(f"anchor must be one of {ANCHORS}, got {anchor!r}")


# ------------------------------------------------------------------------- stats (no video)
def compute_stats(root, episodes, masks=MASK_KEYS, horizon=H_DEFAULT, anchor="anchor_pose", state="gripper"):
    """Relative-action statistics over every valid (anchor, j) pair of the episodes; state statistics over the
    episodes' steps (gripper) or their valid anchors (pose_gripper)."""
    check_state_dataset(root, state)
    df = read_columns(root)
    act = np.stack(df["action"].values).astype(float)
    anc = anchor_poses(df, anchor)
    cur = np.stack(df["anchor_pose"].values).astype(float)
    starts = start_poses(df) if state == "startpose_gripper" else {}
    ep = df["episode_index"].values
    bad = ~valid_anchors(df, masks)
    bad_anchor = ~valid_anchors(df, masks, anchor)
    rows, states = [], []
    for e in episodes:
        r = np.where(ep == e)[0]
        A, P, b = anc[r], act[r], bad[r]
        TA, TP = pose_T(A), pose_T(P[:, :6])
        grip = np.stack(df["observation.state"].values[r]).astype(float).reshape(-1)
        if state == "gripper":
            states.append(grip[:, None])
        elif state == "pose_gripper":
            ok = ~bad_anchor[r]                       # the current pose (anchor_pose column), whatever the anchor
            states.append(pose_state(cur[r][ok], grip[ok]))
        else:
            ok = ~bad_anchor[r]
            if int(e) in starts and ok.any():
                states.append(startpose_state(starts[int(e)], cur[r][ok], grip[ok]))
        for t in np.where(~bad_anchor[r])[0]:
            j = np.arange(t, min(t + horizon, len(r)))
            j = j[~b[j]]
            rel = G.inv(TA[t][None]) @ TP[j]
            rows.append(Rl.to_action10(rel, P[j, 6]))
    X = np.concatenate(rows)
    S = np.concatenate(states)

    def st(x):
        out = {"min": x.min(0), "max": x.max(0), "mean": x.mean(0), "std": x.std(0), "count": np.array([len(x)])}
        out.update({f"q{q:02d}": np.percentile(x, q, axis=0) for q in STAT_Q})
        return {k: np.asarray(v).tolist() for k, v in out.items()}
    return {"action": st(X), "observation.state": st(S),
            "_source": {"root": str(root), "episodes": [int(e) for e in episodes], "masks": list(masks),
                        "horizon": horizon, "anchor": anchor, "state": state, "pairs": int(len(X))}}


# ------------------------------------------------------------------------- wrapper
class _Meta:
    """LeRobotDatasetMetadata proxy: relative features / stats, episode boundaries in anchor space."""

    def __init__(self, base, stats, from_idx, to_idx, state="gripper"):
        self._base = base
        self.features = dict(base.features)
        self.features["action"] = {"dtype": "float32", "shape": (10,),
                                   "names": ["dx", "dy", "dz", "r00", "r10", "r20", "r01", "r11", "r21", "gripper.pos"]}
        self.features["observation.state"] = {"dtype": "float32", "shape": (len(STATE_NAMES[state]),),
                                              "names": STATE_NAMES[state]}
        for k in ("anchor_pose", *MASK_KEYS):
            self.features.pop(k, None)
        st = {k: dict(v) for k, v in base.stats.items() if k in self.features}
        for k in ("action", "observation.state"):
            st[k] = {s: np.asarray(v, dtype=np.float32) for s, v in stats[k].items()}
        self.stats = st
        self.episodes = {"dataset_from_index": list(from_idx), "dataset_to_index": list(to_idx)}

    def __getattr__(self, name):
        return getattr(self._base, name)


class RelChunkDataset:
    def __init__(self, repo, root, episodes, stats, horizon=H_DEFAULT, masks=MASK_KEYS, anchor="anchor_pose",
                 state="gripper", **lerobot_kw):
        import torch  # noqa: F401
        from lerobot.datasets.lerobot_dataset import LeRobotDataset, LeRobotDatasetMetadata
        if anchor not in ANCHORS:
            raise ValueError(f"anchor must be one of {ANCHORS}, got {anchor!r}")
        if stats.get("_source", {}).get("anchor", "anchor_pose") != anchor:
            raise ValueError(f"stats were computed for anchor {stats.get('_source', {}).get('anchor', 'anchor_pose')!r}, "
                             f"the dataset uses {anchor!r}")
        check_state_dataset(root, state)
        if stats.get("_source", {}).get("state", "gripper") != state:
            raise ValueError(f"stats were computed for state {stats.get('_source', {}).get('state', 'gripper')!r}, "
                             f"the dataset uses {state!r}")
        base = LeRobotDatasetMetadata(repo, root=root)
        self.H, self.masks, self.anchor, self.state = horizon, tuple(masks), anchor, state
        fps = base.fps
        dts = {k: [j / fps for j in range(horizon)] for k in ("action", *self.masks)}
        if anchor == "prev_action":                       # step t-1 first (clamped to t at an episode's start)
            dts["action"] = [-1 / fps] + dts["action"]
        self.ds = LeRobotDataset(repo, root=root, episodes=list(episodes), delta_timestamps=dts, **lerobot_kw)
        df = read_columns(root)
        df = df[df["episode_index"].isin(list(episodes))].reset_index(drop=True)
        ok = valid_anchors(df, self.masks, anchor)
        # LeRobotDataset orders frames by the selected episodes' order in the files (= sorted episode index)
        if not np.array_equal(df["episode_index"].values, np.sort(df["episode_index"].values)):
            raise RuntimeError("source frames are not sorted by episode")
        self.starts = start_poses(df) if state == "startpose_gripper" else {}
        if state == "startpose_gripper":                  # an anchor needs its episode's start pose
            ok &= np.isin(df["episode_index"].values, list(self.starts))
        self.idx = np.where(ok)[0]
        ep_of = df["episode_index"].values[self.idx]
        from_idx, to_idx, off = [], [], 0
        for e in sorted(set(int(x) for x in episodes)):
            n = int((ep_of == e).sum())
            if n:
                from_idx.append(off)
                to_idx.append(off + n)
                off += n
        self.meta = _Meta(base, stats, from_idx, to_idx, state)
        self.episodes = None
        self.repo_id, self.root, self.streaming = repo, Path(root), False
        self.num_frames, self.num_episodes = len(self.idx), len(from_idx)
        self.dropped_anchors = int((~ok).sum())

    def __len__(self):
        return self.num_frames

    def __getitem__(self, i):
        import torch
        item = self.ds[int(self.idx[i])]
        act = item["action"].double().numpy()                         # (H, 7), or (H + 1, 7) with step t-1 first
        pad = item["action_is_pad"].numpy().copy()
        if self.anchor == "prev_action":
            anchor, act, pad = act[0, :6], act[1:], pad[1:]
        else:
            anchor = item["anchor_pose"].double().numpy().reshape(6)
        grip = item["observation.state"].double().numpy().reshape(1)
        for m in self.masks:
            pad |= _bad(m, item[m].numpy().reshape(-1))
        item["action"] = torch.as_tensor(rel10(anchor, act), dtype=torch.float32)
        item["action_is_pad"] = torch.as_tensor(pad)
        if self.state == "gripper":
            item["observation.state"] = item["observation.state"].reshape(1).float()
        elif self.state == "pose_gripper":                # the current tool pose: the anchor pose at step t
            pose = item["anchor_pose"].double().numpy().reshape(6)
            item["observation.state"] = torch.as_tensor(pose_state(pose, grip)[0], dtype=torch.float32)
        else:                                             # relative to the episode's start pose
            pose = item["anchor_pose"].double().numpy().reshape(6)
            start = self.starts[int(item["episode_index"])]
            item["observation.state"] = torch.as_tensor(startpose_state(start, pose, grip)[0], dtype=torch.float32)
        for k in ("anchor_pose", *self.masks):
            item.pop(k, None)
            item.pop(f"{k}_is_pad", None)
        return item


# ------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stats", "check"])
    ap.add_argument("--root", required=True, help="dataset directory (<lerobot root>/<repo>)")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--episodes", required=True, help="episode list file (JSON list or whitespace)")
    ap.add_argument("--masks", default=",".join(MASK_KEYS))
    ap.add_argument("--horizon", type=int, default=H_DEFAULT)
    ap.add_argument("--anchor", default="anchor_pose", choices=ANCHORS)
    ap.add_argument("--state", default="gripper", choices=STATES)
    ap.add_argument("--stats", help="check: stats file")
    ap.add_argument("--out", help="stats: output file")
    a = ap.parse_args()
    eps = load_episode_list(a.episodes)
    masks = tuple(m for m in a.masks.split(",") if m)
    if a.cmd == "stats":
        s = compute_stats(a.root, eps, masks, a.horizon, a.anchor, a.state)
        json.dump(s, open(a.out, "w"), indent=1)
        print(f"{a.out}: {s['_source']['pairs']} (anchor, j) pairs; action mean {np.round(s['action']['mean'], 4)}, "
              f"std {np.round(s['action']['std'], 4)}")
        return
    # check: the wrapper's items against a direct numpy computation from the parquet columns
    stats = json.load(open(a.stats))
    rd = RelChunkDataset(a.repo, a.root, eps, stats, a.horizon, masks, a.anchor, a.state)
    df = read_columns(a.root)
    df = df[df["episode_index"].isin(eps)].reset_index(drop=True)
    act = np.stack(df["action"].values).astype(float)
    anc = anchor_poses(df, a.anchor)
    bad = ~valid_anchors(df, masks)
    ep = df["episode_index"].values
    worst, n = 0.0, 0
    rng = np.random.default_rng(0)
    for i in rng.choice(len(rd), size=min(40, len(rd)), replace=False):
        t = int(rd.idx[i])
        r = np.where(ep == ep[t])[0]
        j = np.arange(t, t + a.horizon)
        past = j > r[-1]
        jj = np.minimum(j, r[-1])
        ref = rel10(anc[t], act[jj])
        ref_pad = past | bad[jj]
        item = rd[int(i)]
        if not np.array_equal(item["action_is_pad"].numpy(), ref_pad):
            raise SystemExit(f"pad mismatch at frame {t}")
        got = item["action"].numpy()
        worst = max(worst, float(np.abs(got[~ref_pad] - ref[~ref_pad]).max()) if (~ref_pad).any() else 0.0)
        assert tuple(item["observation.state"].shape) == (len(STATE_NAMES[a.state]),)
        if a.state != "gripper":                          # the state from the anchor_pose column, directly
            cur_t, g_t = np.stack(df["anchor_pose"].values)[t], np.stack(df["observation.state"].values)[t]
            ref_state = (pose_state(cur_t, g_t)[0] if a.state == "pose_gripper" else
                         startpose_state(start_poses(df)[int(ep[t])], cur_t, g_t)[0])
            worst = max(worst, float(np.abs(item["observation.state"].numpy() - ref_state).max()))
        n += 1
    print(f"{n} items; {rd.num_frames} anchors in {rd.num_episodes} episodes ({rd.dropped_anchors} masked anchors "
          f"dropped); action {tuple(item['action'].shape)}; max |wrapper - direct| {worst:.2e}")
    print("CHECK", "OK" if worst < 1e-4 else "FAILED")


if __name__ == "__main__":
    main()
