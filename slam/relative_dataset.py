#!/usr/bin/env python3
"""Training-time conversion of a slam.export_lerobot dataset to relative actions.

RelativeChunkDataset wraps a LeRobotDataset loaded with
delta_timestamps = {"action": [0, 1/fps, ..., H/fps]} and returns per sample
  action          (H, 10)  tool_t->tool_t+j, j = 1..H: translation (3) + 6D rotation (6) +
                           absolute gripper (1)   (slam/relative.py)
  action_is_pad   (H,)     steps past the episode end (LeRobot's padding)
plus every other key of the underlying item (images, observation.state, ...).
The anchor pose is the dataset action at t (delta 0), so the per-episode SLAM frame
cancels. A policy trained on it outputs relative chunks; deployment composes them with
the robot's FK pose (relative.deploy_targets).

  /home/student/miniconda3/envs/lerobot/bin/python -m slam.relative_dataset \
      --root <work>/lerobot --repo yam_glove7_slamE3 --session yam_glove7 --run E3   # self-check
"""
import argparse
from pathlib import Path

import numpy as np
import torch

from slam import geometry as G
from slam import relative as Rl


class RelativeChunkDataset(torch.utils.data.Dataset):
    def __init__(self, repo, root, horizon=100, **kw):
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        self.H = horizon
        meta = LeRobotDataset(repo, root=root).meta
        dts = {"action": [k / meta.fps for k in range(horizon + 1)]}
        self.ds = LeRobotDataset(repo, root=root, delta_timestamps=dts, **kw)

    def __len__(self):
        return len(self.ds)

    def __getitem__(self, i):
        item = self.ds[i]
        a = item["action"].double().numpy()                        # (H+1, 7), row 0 = step t
        pad = item["action_is_pad"].numpy()[1:]
        T = G.rt_to_T(a[:, 3:6], a[:, :3])
        rel = G.inv(T[:1]) @ T[1:]
        item["action"] = torch.as_tensor(Rl.to_action10(rel, a[1:, 6]), dtype=torch.float32)
        item["action_is_pad"] = torch.as_tensor(pad)
        return item


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--run", default="E3")
    ap.add_argument("--horizon", type=int, default=100)
    a = ap.parse_args()
    import json
    from slam.export_lerobot import episodes
    rd = RelativeChunkDataset(a.repo, Path(a.root) / a.repo, a.horizon)
    side = json.load(open(Path(a.root) / a.repo / "meta" / "slam_labels.json"))
    labels = dict(episodes(a.session, a.run))
    worst, n = 0.0, 0
    for e in side["episodes"][::3]:
        z = labels[e["source_episode"]]
        f0 = rd.ds.meta.episodes[e["dataset_episode"]]["dataset_from_index"]
        for t in (0, len(z["t"]) // 2, len(z["t"]) - 2):
            item = rd[f0 + t]
            ref, pad = Rl.chunk_actions(z["T_ref_tool"], z["gripper"], t, a.horizon)
            got = item["action"].numpy()
            if not np.array_equal(item["action_is_pad"].numpy(), pad):
                raise SystemExit(f"pad mismatch ep{e['source_episode']} t={t}")
            worst = max(worst, float(np.abs(got[~pad] - ref[~pad]).max()) if (~pad).any() else 0.0)
            n += 1
    print(f"{n} samples, action {tuple(item['action'].shape)}, max |relative action - label| {worst:.2e}")
    print("SELF-CHECK", "OK" if worst < 1e-4 else "FAILED")


if __name__ == "__main__":
    main()
