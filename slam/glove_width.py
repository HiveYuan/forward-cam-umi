#!/usr/bin/env python3
"""Gripper-width labels for a session, taken from Yosub's built glove dataset.

The jaw-width channel is built by scripts/build_dataset.py from the wrist camera with
estimators calibrated against actuator measurements (the glove --log), which is not in
the raw data. Yosub's built glove dataset (pilot_glove_HHs3) already carries it:
action[6] = gripper.pos (commanded-gripper units, calib/width_to_cmd_glove_v2.json).
It has no wall clock or source ids, so its episodes are matched to this session's:

  * the dataset was built with --slow S (default 2.5): a source episode of the marked
    span [t_start, t_end] has len(arange(t_start, t_end, 1 / (15 S))) steps, step k at
    wall time t_start + k / (15 S);
  * consecutive episodes keep their order, so the session is a block at a fixed offset
    in the dataset; val_episodes.json names one (stem, episode) -> dataset index anchor;
  * only exact length matches are kept (trimmed/split episodes have an unknown start);
  * each kept match is verified on images: the dataset video frame vs the raw head frame
    at the same wall time, resized the dataset's way (640x360, INTER_AREA), must be much
    closer than the neighbouring dataset episodes' frames.

Output <work>/<session>/gt/gripper.npz: per kept episode e: g<e>_t (wall), g<e>_v (gripper),
plus meta (source dataset, offset, per-episode source index and image-check numbers).

  /home/student/miniconda3/envs/sam2/bin/python -m slam.glove_width --session yam_glove7
  ... --write-log   # also/only: gt/glove_log_from_dataset.json, the verified widths as
                    # build_dataset --log "e8_meas" events (gripper calibration source)
"""
import argparse
import glob
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from slam import config as C
from slam.preprocess import packet_pts

DS = Path.home() / ".cache/huggingface/lerobot/pilot_glove_HHs3"


def video_frame(path, t, size=(640, 360)):
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.4f}", "-i", str(path),
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(out, np.uint8).reshape(size[1], size[0], 3) if len(out) == size[0] * size[1] * 3 else None


def raw_frame(video, pts, k, W=3840, H=2160):
    t = pts[k]
    out = subprocess.run(["ffmpeg", "-v", "error", "-copyts", "-ss", f"{max(t - 1, 0):.3f}", "-i", str(video),
                          "-vf", f"select='between(t,{t - 0.01:.4f},{t + 0.01:.4f})'", "-fps_mode", "passthrough",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    img = np.frombuffer(out, np.uint8).reshape(H, W, 3)
    return cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA)


def write_log(session):
    """gt/gripper.npz -> a build_dataset --log: one e8_meas event per width sample, in
    gripper command units (the dataset's action[6]; no "units": "mm", so no gap map)."""
    z = np.load(C.gt_dir(session) / "gripper.npz")
    ev = []
    for k in sorted(x for x in z.files if x.endswith("_t")):
        ev += [{"event": "e8_meas", "t_wall": float(t), "gripper_pos": float(v)}
               for t, v in zip(z[k], z[k[:-2] + "_v"])]
    ev.sort(key=lambda e: e["t_wall"])
    dst = C.gt_dir(session) / "glove_log_from_dataset.json"
    json.dump({"source": "slam.glove_width (verified episode match to the built glove dataset)",
               "units": "command", "events": ev}, open(dst, "w"))
    print(f"wrote {dst}: {len(ev)} e8_meas events")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--dataset", default=str(DS))
    ap.add_argument("--slow", type=float, default=2.5)
    ap.add_argument("--write-log", action="store_true")
    a = ap.parse_args()
    if a.write_log and (C.gt_dir(a.session) / "gripper.npz").exists():
        return write_log(a.session)
    s = C.session(a.session)
    stem = s["head_stem"]
    ds = Path(a.dataset)
    meta_eps = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(ds / "meta/episodes/chunk-000/*.parquet")))])
    meta_eps = meta_eps.sort_values("episode_index").reset_index(drop=True)
    data = pd.concat([pd.read_parquet(f, columns=["action", "episode_index", "frame_index"])
                      for f in sorted(glob.glob(str(ds / "data/chunk-000/*.parquet")))])
    L = meta_eps["length"].to_numpy()
    eps = json.load(open(C.RAW / f"{a.session}_glove_episodes.json"))["episodes"]
    step = 1.0 / (15.0 * a.slow)
    n = np.array([len(np.arange(e["t_start"], e["t_end"], step)) for e in eps])

    anchors = [(st, int(ep), i) for i, (st, ep, sfx) in zip(
        json.load(open(ds / "meta/val_episodes.json"))["val_episodes"],
        json.load(open(ds / "meta/val_episodes.json"))["skeleton_episodes"]) if st == stem and not sfx]
    offs = {i - ep for _, ep, i in anchors}
    if len(offs) != 1:
        raise SystemExit(f"need exactly one anchor offset for {stem}, got {offs}")
    off = offs.pop()
    exact = [j for j in range(len(eps)) if 0 <= j + off < len(L) and L[j + off] == n[j]]
    print(f"offset {off} (anchors {anchors}); exact length matches {len(exact)}/{len(eps)}; "
          f"not used: {[j for j in range(len(eps)) if j not in exact]}")

    ts = np.array([x["wall"] for x in json.load(open(C.RAW / f"{stem}_ts.json"))])
    video = C.RAW / f"{stem}.mkv"
    pts = packet_pts(video)
    vkey = "videos/observation.images.b0587b"
    out, info = {}, {}
    for j in exact:
        di = j + off
        row = meta_eps.iloc[di]
        vpath = ds / vkey.replace("videos/", "videos/") / f"chunk-{int(row[vkey + '/chunk_index']):03d}" / \
            f"file-{int(row[vkey + '/file_index']):03d}.mp4"
        checks = []
        for k in (5, int(n[j]) // 2, int(n[j]) - 5):
            t_wall = eps[j]["t_start"] + k * step
            kr = int(np.argmin(np.abs(ts - t_wall)))
            R = raw_frame(video, pts, kr).astype(float)
            own = video_frame(vpath, row[vkey + "/from_timestamp"] + k / 15.0)
            d_own = np.abs(R - own).mean()
            d_other = []
            for dj in (-1, 1):
                if 0 <= di + dj < len(meta_eps):
                    r2 = meta_eps.iloc[di + dj]
                    p2 = ds / "videos/observation.images.b0587b" / f"chunk-{int(r2[vkey + '/chunk_index']):03d}" / \
                        f"file-{int(r2[vkey + '/file_index']):03d}.mp4"
                    k2 = min(k, int(r2["length"]) - 1)
                    o = video_frame(p2, r2[vkey + "/from_timestamp"] + k2 / 15.0)
                    if o is not None:
                        d_other.append(np.abs(R - o).mean())
            checks.append((float(d_own), float(min(d_other))))
        ok = all(d < 0.5 * o for d, o in checks)
        g = np.stack(data[data["episode_index"] == di].sort_values("frame_index")["action"].to_numpy())[:, 6]
        info[j] = {"dataset_episode": di, "image_check": checks, "verified": ok}
        print(f"ep{j:02d} <- {ds.name} ep{di}: image diff own/other " +
              ", ".join(f"{d:.1f}/{o:.1f}" for d, o in checks) + f" -> {'OK' if ok else 'REJECTED'}", flush=True)
        if ok:
            out[f"g{j}_t"] = eps[j]["t_start"] + np.arange(len(g)) * step
            out[f"g{j}_v"] = g.astype(float)
    dst = C.gt_dir(a.session)
    np.savez(dst / "gripper.npz", meta=json.dumps({"dataset": str(ds), "slow": a.slow, "offset": off,
                                                   "episodes": info}), **out)
    print(f"wrote {dst / 'gripper.npz'}: {sum(v['verified'] for v in info.values())} episodes")


if __name__ == "__main__":
    main()
