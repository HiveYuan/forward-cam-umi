#!/usr/bin/env python3
"""The tool pose in the head camera's frame for every step of a relative-action dataset (test D2c, 2026-11-14).

D1 (exp051) showed that the glove data's value comes from knowing where the gripper is. D2c gives the policy that,
tile-free, as the egocentric tool pose: T_cam_tool, the tool in the head camera that sees it.
  glove   from the ball the head camera sees, the labels' own chain without the tiles:
          T_cam_tool = T_cam_body (gt/ball_poses.npz, 'full' = faces + back markers) . inv(T_flange_body).
          It is interpolated at the HHs3 step times (manifest t0 + j / 37.5), valid where the bracketing ball poses
          are <= bridge_s apart.
  teleop  from the camera positioner (SO-101) that held the camera during teleoperation, as at deployment:
          T_cam_tool = inv(T_world_cam(q_so101)) . T_world_base . FK(q_yam). The positioner's measured joints come
          from <session>_so101cam_track.jsonl, through its kinematic fit (calib/so101_cam_kin.json) and
          calib/base_world_v3_20261016.json; these are fixed calibrations, not per-frame tiles. The teleop step times
          come from the skeleton wall clocks (pilot_head_Hgt step j = skeleton frame 2j, verified exactly).
          yam_head13 has no track log, so its 27 episodes have no camera pose.
Output <dataset root>/meta/cam_tool_pose.npz: index (dataset index), pose6 (N, 6: xyz m + rotation vector), valid
(N,), meta. slam.relative_dataset's state "campose_gripper" reads it.

  L=/home/student/miniconda3/envs/lerobot/bin/python      # scipy, cv2, pandas
  PYTHONPATH=. $L -m slam.cam_state build --root <lerobot root>/pilot_mix_gHs3_rel_slam_v3
  PYTHONPATH=. $L -m slam.cam_state check --root ...       # tool-point image positions: teleop vs glove
"""
import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G
from slam.rel_dataset import pose6, poses_at
from slam.relative_dataset import pose_T, read_columns

LEROBOT = Path.home() / ".cache/huggingface/lerobot"
TELEOP_SESSIONS = ("yam_head12", "yam_head13", "yam_head14")        # pilot_head_Hgt episodes 0-84, 85-111, 112-177
TRACK_DIR = C.WORK / "so101_track"                                  # <session>_so101cam_track.jsonl (from the bucket)
GLOVE_FIRST = 178
SLOW_DT = 1.0 / 37.5
BRIDGE_S = 0.3


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------- teleop
def teleop_walls():
    """{pilot teleop episode: wall time per dataset step} (skeleton wall clocks, the build_dataset subsampling)."""
    import pandas as pd
    out, p = {}, 0
    for sess in TELEOP_SESSIONS:
        files = sorted(glob.glob(str(LEROBOT / sess / "data/**/*.parquet"), recursive=True))
        n = pd.concat([pd.read_parquet(f, columns=["episode_index"]) for f in files]).groupby("episode_index").size()
        W = {json.loads(l)["episode_index"]: np.array(json.loads(l)["t_wall"])
             for l in open(LEROBOT / sess / "meta/episode_frames_wallclock.jsonl")}
        for e in sorted(n.index):
            tw = W[int(e)][: min(int(n[e]), len(W[int(e)]))]
            step = max(int(round((len(tw) - 1) / (tw[-1] - tw[0]) / 15.0)), 1)
            out[p] = (sess, tw[::step])
            p += 1
    return out


def so101_model():
    sys.path.insert(0, str(C.REPO / "scripts"))
    import so101_cam_kin as K
    d = json.load(open(C.CALIB / "so101_cam_kin.json"))
    return K.Model(K.load_urdf(), d["signs"]), np.array(d["x"])


def track_cam_poses(session, model, x):
    """(t, T_world_cam) from the positioner's track log, or (None, None) without one."""
    p = TRACK_DIR / f"{session}_so101cam_track.jsonl"
    if not p.exists():
        return None, None
    t, T = [], []
    for line in open(p):
        r = json.loads(line)
        if r.get("header") or r.get("q_meas") is None:
            continue
        t.append(r["t"])
        T.append(model.fk(x, r["q_meas"]))
    o = np.argsort(t)
    return np.array(t)[o], np.array(T)[o]


# ---------------------------------------------------------------- glove
def glove_ball(session):
    """(t, T_cam_body) of the session's head frames with a fused ball pose ('full' variant)."""
    from slam.head_width import data_repo_for
    stem = C.session(session)["head_stem"]
    ts = json.load(open(data_repo_for(stem) / "data/raw" / f"{stem}_ts.json"))
    z = np.load(C.gt_dir(session) / "ball_poses.npz")
    k = z["full_k"]
    t = np.array([ts[int(i)]["wall"] for i in k])
    T = G.rt_to_T(z["full_rvec"], z["full_tvec"])
    o = np.argsort(t)
    return t[o], T[o]


# ---------------------------------------------------------------- build
def build(root):
    df = read_columns(root)
    ep = df["episode_index"].values
    fi = df["frame_index"].values
    N = len(df)
    pose = np.full((N, 6), np.nan, np.float32)
    valid = np.zeros(N, bool)
    src = np.full(N, "", object)
    # teleop
    model, x = so101_model()
    T_world_base = np.array(json.load(open(C.CALIB / "base_world_v3_20261016.json"))["T_world_base"], float)
    walls = teleop_walls()
    A = pose_T(np.stack(df["anchor_pose"].values).astype(float))           # base -> tool (FK of the measured joints)
    tracks = {}
    for p, (sess, tw) in walls.items():
        r = np.where(ep == p)[0]
        if not len(r):
            continue
        if sess not in tracks:
            tracks[sess] = track_cam_poses(sess, model, x)
        tt, TT = tracks[sess]
        src[r] = sess
        if tt is None:
            continue
        tq = tw[fi[r]]
        Twc, ok = poses_at(tt, TT, tq, BRIDGE_S)
        if not ok.any():
            continue
        T_cam_tool = G.inv(Twc) @ T_world_base[None] @ A[r]
        pose[r[ok]] = pose6(T_cam_tool[ok])
        valid[r[ok]] = True
    # glove
    man = {e["hhs3"]: e for e in json.load(open(C.CALIB / "hhs3_manifest.json"))["episodes"]}
    T_fb = np.array(json.load(open(C.CALIB / "handeye_glove_yosub.json"))["T_flange_body"], float)
    balls = {}
    for e in sorted(set(int(v) for v in ep if v >= GLOVE_FIRST)):
        m = man.get(e - GLOVE_FIRST)
        r = np.where(ep == e)[0]
        if m is None or m.get("t0") is None:
            continue
        sess = m["session"]
        if sess not in balls:
            balls[sess] = glove_ball(sess)
        tb, Tb = balls[sess]
        tq = m["t0"] + fi[r] * SLOW_DT
        Tcb, ok = poses_at(tb, Tb, tq, BRIDGE_S)
        if not ok.any():
            continue
        T_cam_tool = Tcb @ G.inv(T_fb[None])
        pose[r[ok]] = pose6(T_cam_tool[ok])
        valid[r[ok]] = True
        src[r] = sess
    meta = {"method": "slam.cam_state: tool pose in the head camera; glove from the ball (no tiles), teleop from the "
                      "SO-101 positioner's measured joints through its kinematic fit and base_world_v3",
            "bridge_s": BRIDGE_S, "track_dir": str(TRACK_DIR),
            "calib": {f: sha256(C.CALIB / f) for f in ("so101_cam_kin.json", "base_world_v3_20261016.json",
                                                       "handeye_glove_yosub.json", "hhs3_manifest.json")},
            "valid": {"teleop": int(valid[ep < GLOVE_FIRST].sum()), "teleop_steps": int((ep < GLOVE_FIRST).sum()),
                      "glove": int(valid[ep >= GLOVE_FIRST].sum()), "glove_steps": int((ep >= GLOVE_FIRST).sum())},
            "teleop_without_track": sorted({str(s) for s, v in zip(src[ep < GLOVE_FIRST], valid[ep < GLOVE_FIRST]) if not v})}
    out = Path(root) / "meta" / "cam_tool_pose.npz"
    np.savez(out, index=df["index"].values, pose6=pose, valid=valid, meta=json.dumps(meta))
    print(f"wrote {out}: valid teleop {meta['valid']['teleop']}/{meta['valid']['teleop_steps']}, "
          f"glove {meta['valid']['glove']}/{meta['valid']['glove_steps']}; teleop without a pose: {meta['teleop_without_track']}")


def check(root):
    """Where the tool point lands in the head image, teleop vs glove (the paper: normalised gripper centroid 0.37 / 0.62
    under the positioner against 0.38 / 0.60 for the collector)."""
    z = np.load(Path(root) / "meta" / "cam_tool_pose.npz")
    df = read_columns(root)
    ep = df["episode_index"].values
    intr = json.load(open(C.CALIB / "B0587b_f3_intrinsics.json"))
    K = np.array(intr["camera_matrix"], float)
    W, H = intr.get("width", 3840), intr.get("height", 2160)
    v = z["valid"]
    p = z["pose6"][:, :3].astype(float)
    for name, sel in (("teleop", (ep < GLOVE_FIRST) & v), ("glove", (ep >= GLOVE_FIRST) & v)):
        q = p[sel]
        uv = (K @ (q / q[:, 2:3]).T).T[:, :2]
        print(f"{name:6s} {sel.sum():6d} steps: tool point distance median {np.median(np.linalg.norm(q, axis=1)):.3f} m, "
              f"image u/W median {np.median(uv[:, 0]) / W:.2f}, v/H {np.median(uv[:, 1]) / H:.2f}, in front {np.mean(q[:, 2] > 0):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "check"])
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    {"build": build, "check": check}[a.cmd](a.root)


if __name__ == "__main__":
    main()
