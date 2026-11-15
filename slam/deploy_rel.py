#!/usr/bin/env python3
"""Deploying a relative-action ACT policy (the slam.relative_dataset arms) on the YAM.

Each control tick (fps 15) does the following:
  1. state: from the robot (and, for the camera-frame states, the camera positioner), built exactly as in training by
     StateBuilder; T_now = FK(q) is the anchor.
  2. chunk: the policy predicts H relative actions from the head image + state (eval mode, VAE latent 0),
     unnormalised with the checkpoint's own action statistics.
  3. targets: each relative action becomes an absolute target in the robot base, T_now . rel_j (relative.deploy_targets).
  4. ensembling: every chunk that predicted the current tick is averaged in the base frame (relative.ensemble), with
     ACT's weights w_i = exp(-coeff . i), i = 0 the oldest prediction. The gripper uses the same weights.
  5. IK: i2rt grasp_site, warm-started at the measured joints (evaluate_yam's settings), gives the joint command; the
     caller applies its slew limiter.
LeRobot's own ACT temporal ensembler must stay off: it averages raw action vectors, and relative actions of different
chunks are expressed in different anchors.

RelativeChunkPlanner and StateBuilder are numpy only. RelativeActPolicy needs the training env (torch + lerobot);
ik_solver needs i2rt (mink).

Offline replay without the robot (two envs, two stages):
  T=/home/student/miniconda3/envs/lerobot52/bin/python   L=/home/student/miniconda3/envs/lerobot/bin/python
  PYTHONPATH=. $T -m slam.deploy_rel replay-policy experiments/<exp>/config.yaml --episode 15 --out <dir>
  PYTHONPATH=. $L -m slam.deploy_rel replay-ik <dir>/<exp>_ep15.npz
Stage 1 runs the policy on a recorded robot-val episode: the dataset's images, and the states built by StateBuilder from
the recorded quantities, checked against the training wrapper's states. Stage 2 runs the planner + IK. It compares the
commanded joints with the teleoperator's recorded commands, and reports the IK convergence and time per tick.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from slam import geometry as G
from slam import relative as Rl
from slam import relative_dataset as RD


def T_to_pose6(T):
    """(4, 4) -> (6,) xyz + rotation vector (the datasets' pose layout)."""
    R = np.asarray(T, float)[:3, :3]
    ang = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))
    if ang < 1e-9:
        rv = np.zeros(3)
    else:
        w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
        if np.pi - ang < 1e-6:                                   # near pi: from the symmetric part
            B = (R + np.eye(3)) / 2
            ax = np.sqrt(np.clip(np.diag(B), 0, None))
            i = int(np.argmax(ax))
            ax = B[:, i] / np.sqrt(B[i, i])
            rv = ax * ang
        else:
            rv = w / (2 * np.sin(ang)) * ang
    return np.concatenate([np.asarray(T, float)[:3, 3], rv])


class StateBuilder:
    """The policy state at deployment, as slam.relative_dataset builds it for training.

    kind: one of relative_dataset.STATES. reset(T_start) at the rollout's first tick (the start-relative states).
    __call__(T_base_tool, gripper, T_cam_tool=None) -> (D,) float32."""

    def __init__(self, kind):
        if kind not in RD.STATES:
            raise ValueError(f"state must be one of {RD.STATES}, got {kind!r}")
        self.kind, self.T_start = kind, None

    def reset(self, T_base_tool_start):
        self.T_start = np.asarray(T_base_tool_start, float)

    def __call__(self, T_base_tool, gripper, T_cam_tool=None):
        g = np.array([float(gripper)])
        now6 = T_to_pose6(T_base_tool)
        if self.kind == "gripper":
            s = g
        elif self.kind == "pose_gripper":
            s = RD.pose_state(now6, g)[0]
        elif self.kind == "startpose_gripper":
            s = RD.startpose_state(T_to_pose6(self._start()), now6, g)[0]
        elif self.kind == "campose_gripper":
            s = RD.pose_state(T_to_pose6(self._cam(T_cam_tool)), g)[0]
        else:
            s = RD.startcam_state(T_to_pose6(self._start()), now6, T_to_pose6(self._cam(T_cam_tool)), g)[0]
        return np.asarray(s, np.float32)

    def _start(self):
        if self.T_start is None:
            raise RuntimeError("StateBuilder.reset(T_start) first (start-relative state)")
        return self.T_start

    @staticmethod
    def _cam(T):
        if T is None:
            raise RuntimeError("this state needs the tool pose in the head camera (camera positioner)")
        return T


class RelativeChunkPlanner:
    """Absolute targets from relative chunks, temporally ensembled in the robot base (numpy only)."""

    def __init__(self, coeff=0.01, horizon=None):
        self.coeff, self.horizon = float(coeff), horizon
        self.reset()

    def reset(self):
        self.buf = {}                       # tick -> list of (prediction tick, T target, gripper)

    def add(self, tick, T_base_tool, actions):
        """The chunk predicted at `tick` from the anchor T_base_tool: (H, 10) relative actions."""
        a = np.asarray(actions, float)
        if self.horizon:
            a = a[: self.horizon]
        T, g = Rl.deploy_targets(np.asarray(T_base_tool, float), a)
        for j in range(len(a)):
            self.buf.setdefault(tick + j, []).append((tick, T[j], float(g[j])))

    def current(self, tick):
        """(T target, gripper, number of chunks averaged) for `tick`; drops older ticks."""
        for k in [k for k in self.buf if k < tick]:
            del self.buf[k]
        preds = sorted(self.buf.get(tick, []), key=lambda x: x[0])      # oldest first
        if not preds:
            raise RuntimeError(f"no prediction for tick {tick}")
        w = np.exp(-self.coeff * np.arange(len(preds)))
        T = Rl.ensemble(np.stack([p[1] for p in preds]), w) if len(preds) > 1 else preds[0][1]
        g = float(np.sum(w * np.array([p[2] for p in preds])) / w.sum())
        return T, g, len(preds)


def ik_solver(kin=None):
    """f(T target, q seed) -> (q (6,), converged): i2rt grasp_site IK with evaluate_yam's settings."""
    if kin is None:
        from slam.robot_fk import YamFK
        kin = YamFK().kin

    def solve(T, q_seed):
        ok, q = kin.ik(np.asarray(T, float), "grasp_site", init_q=np.asarray(q_seed, float).copy(),
                       pos_threshold=1e-3, ori_threshold=1e-2, max_iters=60)
        return np.array(q[:6], float), bool(ok)
    return solve


class RelativeActPolicy:
    """An ACT checkpoint of slam.train_rel: obs dict -> (H, 10) unnormalised relative actions (training env)."""

    def __init__(self, ckpt_dir, device="cuda"):
        import torch  # noqa: F401
        from lerobot.policies import make_pre_post_processors
        from lerobot.policies.act.modeling_act import ACTPolicy
        from safetensors.numpy import load_file
        self.device = device
        self.policy = ACTPolicy.from_pretrained(str(ckpt_dir)).to(device).eval()
        self.pre, _ = make_pre_post_processors(self.policy.config, str(ckpt_dir),
                                               preprocessor_overrides={"device_processor": {"device": device}})
        st = load_file(str(next(Path(ckpt_dir).glob("policy_preprocessor_step_*_normalizer_processor.safetensors"))))
        self.mean, self.std = st["action.mean"].astype(float), st["action.std"].astype(float) + 1e-8

    def __call__(self, batch):
        """batch: the preprocessed-ready dict (images (1, 3, H, W) float in [0, 1], observation.state (1, D))."""
        import torch
        with torch.inference_mode():
            b = self.pre({k: (v.to(self.device) if torch.is_tensor(v) else v) for k, v in batch.items()})
            out = self.policy.predict_action_chunk(b)
        return out[0].double().cpu().numpy() * self.std + self.mean


# ---------------------------------------------------------------- offline replay
def replay_policy(cfg_path, episode, out_dir, device="cuda"):
    import torch
    import yaml
    from slam import config as C
    cfg = yaml.safe_load(open(cfg_path))
    rel = cfg["relative"]
    v = json.load(open(Path(cfg_path).parent / "results/val.json"))
    ck = Path(cfg["output_dir"]) / "checkpoints" / f"{v['best_step_robot_val']:06d}" / "pretrained_model"
    stats = json.load(open(C.REPO / rel["stats"]))
    root = cfg["dataset"]["root"]
    kind = rel.get("state", "gripper")
    ds = RD.RelChunkDataset(cfg["dataset"]["repo"], root, [episode], stats, horizon=100, masks=(),
                            anchor=rel.get("anchor", "anchor_pose"), state=kind)
    df = RD.read_columns(root)
    df = df[df["episode_index"] == episode].reset_index(drop=True)
    A = RD.pose_T(np.stack(df["anchor_pose"].values).astype(float))              # FK of the measured joints
    grip = np.stack(df["observation.state"].values).astype(float).reshape(-1)
    cam = RD.cam_poses(root, df)[0] if kind in RD.USES_CAM else None
    sb = StateBuilder(kind)
    sb.reset(A[0])
    pol = RelativeActPolicy(ck, device)
    chunks, states, worst = [], [], 0.0
    for i in range(len(ds)):
        item = ds[i]
        t = int(ds.idx[i])                                   # row within the episode (masks off: every step)
        s = sb(A[t], grip[t], RD.pose_T(cam[t]) if cam is not None else None)
        worst = max(worst, float(np.abs(s - item["observation.state"].numpy()).max()))
        batch = {k: (v[None] if torch.is_tensor(v) else v) for k, v in item.items()
                 if k.startswith("observation.")}
        batch["observation.state"] = torch.as_tensor(s)[None]
        batch["task"] = [""]
        chunks.append(pol(batch))
        states.append(s)
    import glob                                              # the recorded joints come from the source mix
    import pandas as pd
    mix = Path.home() / ".cache/huggingface/lerobot/pilot_mix_gHs3"
    sdf = pd.concat([pd.read_parquet(f, columns=["episode_index", "frame_index", "action", "observation.state"])
                     for f in sorted(glob.glob(str(mix / "data/**/*.parquet"), recursive=True))])
    sdf = sdf[sdf["episode_index"] == episode].sort_values("frame_index")
    q_cmd = np.stack(sdf["action"].values).astype(float)
    q_meas = np.stack(sdf["observation.state"].values).astype(float)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{cfg['experiment']}_ep{episode}.npz"
    np.savez(dst, chunks=np.stack(chunks), T_now=A[ds.idx], states=np.stack(states), q_cmd_rec=q_cmd[ds.idx],
             q_meas_rec=q_meas[ds.idx], meta=json.dumps({"experiment": cfg["experiment"], "episode": episode,
                                                          "state": kind, "checkpoint": str(ck)}))
    print(f"{dst}: {len(chunks)} ticks; StateBuilder vs training state max |diff| {worst:.2e}")


def replay_ik(path, coeff=0.01):
    z = np.load(path)
    from slam.robot_fk import YamFK
    fk = YamFK()
    solve = ik_solver(fk.kin)
    pl = RelativeChunkPlanner(coeff)
    n = len(z["chunks"])
    q_out, ok_all, n_avg, dt = [], [], [], []
    for t in range(n):
        pl.add(t, z["T_now"][t], z["chunks"][t])
        T, g, k = pl.current(t)
        t0 = time.perf_counter()
        q, ok = solve(T, z["q_meas_rec"][t][:6])
        dt.append(time.perf_counter() - t0)
        q_out.append(q)
        ok_all.append(ok)
        n_avg.append(k)
    q_out = np.array(q_out)
    rec = z["q_cmd_rec"][:, :6]
    P_out = fk(q_out)[:, :3, 3]
    P_rec = fk(rec)[:, :3, 3]
    print(f"{Path(path).name}: {n} ticks; IK converged {100 * np.mean(ok_all):.1f}%, {1000 * np.median(dt):.1f} ms median "
          f"({1000 * np.percentile(dt, 95):.1f} p95); chunks averaged per tick median {int(np.median(n_avg))}")
    print(f"  commanded vs teleop's recorded command: tool position {1000 * np.median(np.linalg.norm(P_out - P_rec, axis=1)):.1f} mm "
          f"median ({1000 * np.percentile(np.linalg.norm(P_out - P_rec, axis=1), 90):.1f} p90); joints "
          f"{np.degrees(np.median(np.abs(q_out - rec))):.2f} deg median")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("replay-policy")
    p.add_argument("config")
    p.add_argument("--episode", type=int, default=15)
    p.add_argument("--out", required=True)
    p.add_argument("--device", default="cuda")
    p = sub.add_parser("replay-ik")
    p.add_argument("npz")
    p.add_argument("--coeff", type=float, default=0.01)
    a = ap.parse_args()
    if a.cmd == "replay-policy":
        replay_policy(a.config, a.episode, a.out, a.device)
    else:
        replay_ik(a.npz, a.coeff)


if __name__ == "__main__":
    main()
