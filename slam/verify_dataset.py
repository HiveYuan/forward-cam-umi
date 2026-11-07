#!/usr/bin/env python3
"""Check a LeRobot dataset with 7-D pose actions (scripts/build_dataset.py --ref-poses, or
slam.export_lerobot) against the SLAM label files and the gripper widths.

Episodes are matched in order: both writers emit the session's kept episodes (label
file kept, width labels present) in marked order. Checks: step counts, action pose ==
labels ref->tool (float32), relative chunks, state == gripper only, the dataset's gripper
vs gt/gripper.npz, and the first image vs the raw head frame.

  /home/student/miniconda3/envs/lerobot/bin/python -m slam.verify_dataset --session yam_glove7 \
      --run E3 --root <work>/lerobot/yam_glove7_bd_slamE3 --repo yam_glove7_bd_slamE3
"""
import argparse
import json

import numpy as np

from slam import config as C
from slam import geometry as G
from slam import relative as Rl
from slam.export_lerobot import IMKEY, decode_frames, episodes
from slam.preprocess import packet_pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--run", default="E3")
    ap.add_argument("--root", required=True)
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    ds = LeRobotDataset(a.repo, root=a.root)
    labels = list(episodes(a.session, a.run))
    s = C.session(a.session)
    ts = np.array([x["wall"] for x in json.load(open(C.RAW / f"{s['head_stem']}_ts.json"))])
    video = C.RAW / f"{s['head_stem']}.mkv"
    pts = packet_pts(video)
    if ds.meta.total_episodes != len(labels):
        raise SystemExit(f"{ds.meta.total_episodes} dataset episodes vs {len(labels)} kept label files")
    print(f"state names {ds.meta.features['observation.state']['names']}, action names "
          f"{ds.meta.features['action']['names']}")
    wp = wr = wi = 0.0
    gerr = []
    for d, (ep, z) in enumerate(labels):
        f0, f1 = ds.meta.episodes[d]["dataset_from_index"], ds.meta.episodes[d]["dataset_to_index"]
        if f1 - f0 != len(z["t"]):
            raise SystemExit(f"dataset ep{d} has {f1 - f0} frames, label ep{ep} {len(z['t'])}")
        rows = [ds.hf_dataset[i] for i in range(f0, f1)]
        act = np.stack([r["action"].numpy() for r in rows]).astype(float)
        st = np.stack([r["observation.state"].numpy() for r in rows]).astype(float).reshape(len(rows), -1)
        T = G.rt_to_T(act[:, 3:6], act[:, :3])
        wp = max(wp, float(np.abs(T - z["T_ref_tool"]).max()))
        t = len(z["t"]) // 3
        A, _ = Rl.chunk_actions(T, act[:, 6], t, 100)
        B, _ = Rl.chunk_actions(z["T_ref_tool"], act[:, 6], t, 100)
        wr = max(wr, float(np.abs(A - B).max()))
        if st.shape[1] != 1 or not np.allclose(st[:, 0], act[:, 6]):
            raise SystemExit(f"ep{ep}: state is not the gripper channel")
        gerr.append(act[:, 6] - z["gripper"])
        item = ds[f0]
        img = (item[IMKEY].permute(1, 2, 0).numpy() * 255).astype(float)
        k = int(np.argmin(np.abs(ts - z["t"][0])))
        wi = max(wi, float(np.abs(img - decode_frames(video, pts, [k])[k].astype(float)).mean()))
    g = np.concatenate(gerr)
    print(f"{len(labels)} episodes, {ds.num_frames} frames")
    print(f"max |action pose - label| {wp:.2e}; max |relative chunk - label chunk| {wr:.2e}; "
          f"worst first-image diff {wi:.2f}/255")
    print(f"gripper vs width labels: median |err| {np.median(np.abs(g)):.3f}, p95 {np.percentile(np.abs(g), 95):.3f} "
          f"(command units; label range {min(np.nanmin(z['gripper']) for _, z in labels):.2f}-"
          f"{max(np.nanmax(z['gripper']) for _, z in labels):.2f})")
    ok = wp < 1e-4 and wr < 1e-4 and wi < 6.0
    print("VERIFY", "OK" if ok else "FAILED")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
