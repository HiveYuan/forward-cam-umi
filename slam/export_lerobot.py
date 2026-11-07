#!/usr/bin/env python3
"""Write a LeRobot dataset of SLAM-labelled glove episodes (design doc, "Relative labels").

One LeRobot episode per kept label file <segment>/labels/<run>.npz (slam.labels build):
  action               (7)  ref->tool pose in the episode's SLAM frame: x y z rx ry rz
                            (rotation vector) + gripper (absolute width, command units).
                            Absolute in an arbitrary per-episode frame: training converts
                            each chunk to relative 10-D actions with slam.relative.chunk_actions
                            (translation 3 + 6D rotation + gripper), so the frame cancels.
  observation.state    (1)  gripper only (absolute poses mean nothing across SLAM frames)
  observation.label_valid (1)  1 where neither pose nor gripper is a gap (build_dataset
                            emits gap steps interpolated; this lets training mask them)
  observation.images.b0587b   head frame nearest the step's wall time, raw (distorted)
                            and resized to 640x360 with INTER_AREA: build_dataset's recipe,
                            so the policy sees the same images as before
Timeline: 15 fps from the episode's t_start, the build_dataset grid. Meta sidecar
meta/slam_labels.json records run, scale mode and per-episode source.

  /home/student/miniconda3/envs/lerobot/bin/python -m slam.export_lerobot --session yam_glove7 \
      --run E3 --repo yam_glove7_slamE3 --root <dir>
  ... --verify     # reload the dataset and check it against the label files and raw video
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from slam import config as C
from slam import geometry as G
from slam import relative as Rl
from slam.labels import FPS, RefPoses
from slam.preprocess import packet_pts

IMKEY = "observation.images.b0587b"
OBS = (640, 360)


def decode_frames(video, pts, ks, W=3840, H=2160):
    """Raw frames for sorted original indices ks (one ffmpeg pass over [ks[0], ks[-1]])."""
    k0, k1 = int(ks[0]), int(ks[-1])
    t0, t1 = pts[k0] - 0.01, pts[k1] + 0.01
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-copyts", "-ss", f"{max(t0 - 1, 0):.3f}", "-i", str(video),
                          "-vf", f"select='between(t,{t0:.4f},{t1:.4f})'", "-fps_mode", "passthrough",
                          "-frames:v", str(k1 - k0 + 1), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    want, out, k = set(int(x) for x in ks), {}, k0
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        if k in want:
            img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            out[k] = cv2.cvtColor(cv2.resize(img, OBS, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        k += 1
    p.wait()
    if len(out) != len(want):
        raise RuntimeError(f"decoded {len(out)} of {len(want)} frames")
    return out


def episodes(session, run):
    for seg in sorted(C.segments_dir(session).glob("ep[0-9][0-9]")):
        p = seg / "labels" / f"{run}.npz"
        if p.exists():
            z = np.load(p)
            if bool(z["keep"]) and len(z["t"]) and np.isfinite(z["gripper"]).all():
                yield int(seg.name[2:]), z


def export(a):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    s = C.session(a.session)
    stem = s["head_stem"]
    ts = np.array([x["wall"] for x in json.load(open(C.RAW / f"{stem}_ts.json"))])
    video = C.RAW / f"{stem}.mkv"
    pts = packet_pts(video)
    root = Path(a.root) / a.repo
    if root.exists():
        if not a.overwrite:
            raise SystemExit(f"{root} exists (use --overwrite)")
        shutil.rmtree(root)
    features = {
        "action": {"dtype": "float32", "shape": (7,),
                   "names": ["tool.x", "tool.y", "tool.z", "tool.rx", "tool.ry", "tool.rz", "gripper.pos"]},
        "observation.state": {"dtype": "float32", "shape": (1,), "names": ["gripper.pos"]},
        "observation.label_valid": {"dtype": "float32", "shape": (1,), "names": ["valid"]},
        IMKEY: {"dtype": "video", "shape": (OBS[1], OBS[0], 3), "names": ["height", "width", "channels"]},
    }
    ds = LeRobotDataset.create(repo_id=a.repo, fps=int(FPS), features=features, root=root,
                               robot_type="yam", use_videos=True, image_writer_threads=4)
    rp = RefPoses(C.segments_dir(a.session), a.run)
    side = {"session": a.session, "run": a.run, "frame": "tool (virtual flange) in the episode's SLAM frame",
            "rotation": "rotation vector; convert chunks with slam.relative.chunk_actions",
            "episodes": []}
    for ep, z in episodes(a.session, a.run):
        meta = json.loads(str(z["meta"]))
        ks = [int(np.argmin(np.abs(ts - t))) for t in z["t"]]
        imgs = decode_frames(video, pts, sorted(set(ks)))
        for i, t in enumerate(z["t"]):
            tv, rv, _ = rp.lookup(ep, t)
            g = float(z["gripper"][i])
            valid = float(not (z["gap"][i] or z["gripper_gap"][i]))
            ds.add_frame({"action": np.concatenate([tv, rv, [g]]).astype(np.float32),
                          "observation.state": np.array([g], np.float32),
                          "observation.label_valid": np.array([valid], np.float32),
                          IMKEY: imgs[ks[i]], "task": a.task})
        ds.save_episode()
        side["episodes"].append({"dataset_episode": len(side["episodes"]), "source_episode": ep,
                                 "t_start": float(z["t"][0]), "steps": len(z["t"]),
                                 "scale": meta.get("scale"), "scale_mode": meta.get("scale_mode"),
                                 "coverage": float(z["coverage"])})
        print(f"ep{ep:02d}: {len(z['t'])} steps, coverage {100 * float(z['coverage']):.0f}%", flush=True)
    ds.finalize()
    json.dump(side, open(root / "meta" / "slam_labels.json", "w"), indent=1)
    print(f"wrote {root}: {len(side['episodes'])} episodes")


def verify(a):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    root = Path(a.root) / a.repo
    side = json.load(open(root / "meta" / "slam_labels.json"))
    ds = LeRobotDataset(a.repo, root=root)
    s = C.session(a.session)
    ts = np.array([x["wall"] for x in json.load(open(C.RAW / f"{s['head_stem']}_ts.json"))])
    video = C.RAW / f"{s['head_stem']}.mkv"
    pts = packet_pts(video)
    labels = dict(episodes(a.session, a.run))
    worst_pose = worst_rel = worst_img = 0.0
    for e in side["episodes"]:
        z = labels[e["source_episode"]]
        f0, f1 = ds.meta.episodes[e["dataset_episode"]]["dataset_from_index"], \
            ds.meta.episodes[e["dataset_episode"]]["dataset_to_index"]
        if f1 - f0 != len(z["t"]):
            raise SystemExit(f"episode {e}: {f1 - f0} frames vs {len(z['t'])} label steps")
        act = np.stack([ds.hf_dataset[i]["action"].numpy() for i in range(f0, f1)]).astype(float)
        T = G.rt_to_T(act[:, 3:6], act[:, :3])
        worst_pose = max(worst_pose, float(np.abs(T - z["T_ref_tool"]).max()))
        # a training sample: relative chunk from the dataset vs from the label file
        t = len(z["t"]) // 3
        A, _ = Rl.chunk_actions(T, act[:, 6], t, 100)
        B, _ = Rl.chunk_actions(z["T_ref_tool"], z["gripper"], t, 100)
        worst_rel = max(worst_rel, float(np.abs(A - B).max()))
        # images: decoded dataset frame vs the raw frame at the step's wall time
        for i in (0, len(z["t"]) // 2):
            item = ds[f0 + i]
            img = (item[IMKEY].permute(1, 2, 0).numpy() * 255).astype(float)
            k = int(np.argmin(np.abs(ts - z["t"][i])))
            ref = decode_frames(video, pts, [k])[k].astype(float)
            worst_img = max(worst_img, float(np.abs(img - ref).mean()))
    print(f"{len(side['episodes'])} episodes, {ds.num_frames} frames; max |pose - label| {worst_pose:.2e}; "
          f"max |relative chunk - label chunk| {worst_rel:.2e}; worst mean image diff {worst_img:.2f}/255")
    ok = worst_pose < 1e-4 and worst_rel < 1e-4 and worst_img < 6.0
    print("VERIFY", "OK" if ok else "FAILED")
    if not ok:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--run", default="E3")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--root", default=str(C.WORK / "lerobot"))
    ap.add_argument("--task", default="pick red block into bin")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--verify", action="store_true", help="only verify an existing export")
    a = ap.parse_args()
    verify(a) if a.verify else export(a)


if __name__ == "__main__":
    main()
