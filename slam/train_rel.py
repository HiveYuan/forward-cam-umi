#!/usr/bin/env python3
"""ACT training for P3 through Yosub's lerobot (lerobot_alohamini 0cae109f = lerobot 0.5.2), unmodified.

An experiment config (YAML) names Yosub's train_config.json for the arm being mirrored
(calib/yosub_train_configs/<arm>/, from his archive 2026-11-11) and what changes:

  experiment: exp018_T48_rel
  base_train_config: calib/yosub_train_configs/mix_gHs3_48/train_config.json
  dataset: {repo: pilot_mix_gHs3_rel_tile, root: <dir>, episodes: calib/train_eps_pilot_head_Hgt_48.txt}
  relative: {masks: [], stats: calib/rel_action_stats_teleop172.json}    # omit for Yosub's joint actions
  (relative.anchor: anchor_pose (default) or prev_action, see slam.relative_dataset.anchor_poses)
  overrides: {steps: 50000}                                               # dotted keys allowed
  output_dir: /home/student/yuanliu-hawaii/work/train/exp018_T48_rel

Everything else (ACT architecture, chunk 100, VAE, lr, batch 8, seed, image augmentation, save every
2000 steps) is Yosub's file. With `relative`, lerobot_train.make_dataset is replaced by one that returns
slam.relative_dataset.RelChunkDataset (10-D relative actions, masks folded into action_is_pad, masked
anchors not sampled) with the same image transforms, uint8 frames, tolerance and ImageNet image stats
as lerobot's own make_dataset; the policy's input/output features are cleared so make_policy derives
them from the dataset (observation.state (1,) = gripper, action (10,)).

  R=/home/student/miniconda3/envs/lerobot52/bin/python
  PYTHONPATH=. $R -m slam.train_rel experiments/<exp>/config.yaml
  PYTHONPATH=. $R -m slam.train_rel <config> --steps 20 --output-dir <scratch> --device cpu   # smoke test
"""
import argparse
import copy
import datetime
import json
import sys
from pathlib import Path

import yaml

from slam import config as C
from slam.relative_dataset import MASK_KEYS, RelChunkDataset, load_episode_list


def _set(d, dotted, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d[k]
    if keys[-1] not in d:
        raise KeyError(f"override {dotted!r}: no such key in the base train config")
    d[keys[-1]] = value


def build_train_config(cfg, output_dir=None, steps=None, device=None):
    tc = copy.deepcopy(json.load(open(C.REPO / cfg["base_train_config"])))
    d = cfg["dataset"]
    tc["dataset"]["repo_id"] = d["repo"]
    tc["dataset"]["root"] = str(d["root"])
    if d.get("episodes"):
        tc["dataset"]["episodes"] = load_episode_list(C.REPO / d["episodes"])
    for k, v in (cfg.get("overrides") or {}).items():
        _set(tc, k, v)
    tc["output_dir"] = str(output_dir or cfg["output_dir"])
    tc["job_name"] = cfg["experiment"]
    tc["policy"]["repo_id"] = f"local/{cfg['experiment']}"
    tc["policy"]["push_to_hub"] = False
    tc["wandb"]["enable"] = False
    if steps is not None:
        tc["steps"] = int(steps)
        tc["save_freq"] = min(tc["save_freq"], int(steps))
        tc["log_freq"] = min(tc["log_freq"], max(int(steps) // 4, 1))
    if device:
        tc["policy"]["device"] = device
    if cfg.get("relative"):
        tc["policy"]["input_features"] = {}
        tc["policy"]["output_features"] = {}
    return tc


def relative_make_dataset(rel, chunk):
    stats = json.load(open(C.REPO / rel["stats"]))
    masks = tuple(rel.get("masks", MASK_KEYS))
    anchor = rel.get("anchor", "anchor_pose")

    def make_dataset(tcfg):
        import torch
        from lerobot.transforms import ImageTransforms
        from lerobot.utils.constants import IMAGENET_STATS
        it = ImageTransforms(tcfg.dataset.image_transforms) if tcfg.dataset.image_transforms.enable else None
        ds = RelChunkDataset(tcfg.dataset.repo_id, tcfg.dataset.root, tcfg.dataset.episodes, stats,
                             horizon=chunk, masks=masks, anchor=anchor, image_transforms=it,
                             video_backend=tcfg.dataset.video_backend, return_uint8=True,
                             tolerance_s=tcfg.tolerance_s)
        if tcfg.dataset.use_imagenet_stats:
            for key in ds.meta.camera_keys:
                for stats_type, s in IMAGENET_STATS.items():
                    ds.meta.stats[key][stats_type] = torch.tensor(s, dtype=torch.float32)
        print(f"[train_rel] RelChunkDataset {tcfg.dataset.repo_id}: {ds.num_frames} anchors in "
              f"{ds.num_episodes} episodes, {ds.dropped_anchors} masked anchors dropped, masks {list(masks)}, anchor {anchor}",
              flush=True)
        return ds
    return make_dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--steps", type=int, help="override steps (smoke tests)")
    ap.add_argument("--output-dir", help="override output_dir (smoke tests)")
    ap.add_argument("--device", help="override policy.device (smoke tests)")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    tc = build_train_config(cfg, a.output_dir, a.steps, a.device)
    out = Path(tc["output_dir"])
    if out.exists():
        raise SystemExit(f"{out} exists (lerobot refuses to overwrite a run)")
    out.parent.mkdir(parents=True, exist_ok=True)
    tc_path = out.parent / f"{out.name}.train_config.json"
    json.dump(tc, open(tc_path, "w"), indent=2)
    print(f"[train_rel] {cfg['experiment']}: train config {tc_path}", flush=True)
    import lerobot.scripts.lerobot_train as LT
    if cfg.get("relative"):
        LT.make_dataset = relative_make_dataset(cfg["relative"], tc["policy"]["chunk_size"])
    record = None if (a.steps or a.output_dir or a.device) else provenance(a.config, tc)
    sys.argv = ["lerobot-train", f"--config_path={tc_path}"]
    LT.train()
    if record is not None:                     # experiments/<exp>/run.json, one entry per invocation
        record["end"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        rp = Path(a.config).parent / "run.json"
        runs = json.load(open(rp)) if rp.exists() else {"invocations": []}
        runs["invocations"].append(record)
        json.dump(runs, open(rp, "w"), indent=1)


def provenance(config_path, tc):
    import importlib.metadata as md
    import subprocess
    import torch
    git = lambda *x: subprocess.run(["git", "-C", str(C.REPO), *x], capture_output=True, text=True).stdout.strip()
    lr = Path(__import__("lerobot").__file__).resolve().parents[2]
    return {"git_commit": git("rev-parse", "HEAD"), "git_clean": git("status", "--porcelain") == "",
            "lerobot_checkout": subprocess.run(["git", "-C", str(lr), "rev-parse", "HEAD"], capture_output=True,
                                               text=True).stdout.strip(),
            "packages": {p: md.version(p) for p in ("lerobot", "torch", "torchvision", "torchcodec", "numpy")},
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "config": str(config_path), "output_dir": tc["output_dir"], "steps": tc["steps"], "seed": tc["seed"],
            "start": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}


if __name__ == "__main__":
    main()
