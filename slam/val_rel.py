#!/usr/bin/env python3
"""Validation of a P3 training run (slam.train_rel): Yosub's val loss for every checkpoint, plus the
relative-pose errors in physical units for the best and the last checkpoint.

Val sets are the dataset's own: meta/val_episodes.json ("robot val", 6 teleop episodes, encoder
labels: the paper's checkpoint criterion) and, for a mix, meta/val_episodes_glove.json ("glove val").
Loss: as scripts/compute_val_loss.py (policy in train mode under no_grad, the checkpoint's
preprocessor, policy.forward's L1 + kl_weight * KL, batch-weighted mean). For relative runs the val
data is RelChunkDataset with the run's masks, so it matches training; Yosub's joint-action runs use a
plain LeRobotDataset with action deltas 0..chunk-1 (the env-check arm).
Physical errors (relative runs): the policy's chunk with the VAE latent at zero (eval mode,
predict_action_chunk), unnormalised with the run's stats, against the label: tool position (mm),
rotation (deg, 6D -> R by Gram-Schmidt) and gripper (command units) at j = 0, 14, 49, 99 and averaged
over the chunk, on non-padded steps.

  R=/home/student/miniconda3/envs/lerobot52/bin/python
  PYTHONPATH=. $R -m slam.val_rel experiments/<exp>/config.yaml            # -> experiments/<exp>/results/
  PYTHONPATH=. $R -m slam.val_rel <config> --run-dir <dir> --out <dir>     # e.g. a smoke run
"""
import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from slam import config as C
from slam import relative as Rl
from slam.relative_dataset import MASK_KEYS, RelChunkDataset

JS = (0, 14, 49, 99)


def val_episode_sets(root):
    out = {}
    for name, f in (("robot", "val_episodes.json"), ("glove", "val_episodes_glove.json")):
        p = Path(root) / "meta" / f
        if p.exists():
            out[name] = [int(e) for e in json.load(open(p))["val_episodes"]]
    return out


def make_loader(cfg, eps, chunk, stats, batch_size, workers):
    import torch
    d = cfg["dataset"]
    if cfg.get("relative"):
        ds = RelChunkDataset(d["repo"], d["root"], eps, stats, horizon=chunk,
                             masks=tuple(cfg["relative"].get("masks", MASK_KEYS)),
                             anchor=cfg["relative"].get("anchor", "anchor_pose"))
    else:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset, LeRobotDatasetMetadata
        fps = LeRobotDatasetMetadata(d["repo"], root=d["root"]).fps
        ds = LeRobotDataset(d["repo"], root=d["root"], episodes=eps,
                            delta_timestamps={"action": [j / fps for j in range(chunk)]})
    return torch.utils.data.DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=workers)


def evaluate(ckpt, loader, physical, stats, device="cuda"):
    import torch
    from lerobot.policies import make_pre_post_processors
    from lerobot.policies.act.modeling_act import ACTPolicy
    policy = ACTPolicy.from_pretrained(str(ckpt))
    policy.to(device)
    pre, _ = make_pre_post_processors(policy.config, str(ckpt))
    tot, n, l1, kld = 0.0, 0, 0.0, 0.0
    errs = {"pos_mm": [], "rot_deg": [], "grip": [], "valid": []}
    mean = std = None
    if physical:
        mean = np.asarray(stats["action"]["mean"], float)
        std = np.asarray(stats["action"]["std"], float) + 1e-8
    with torch.no_grad():
        for batch in loader:
            raw_action = batch["action"].clone() if physical else None
            raw_pad = batch["action_is_pad"].clone() if physical else None
            b = {k: (v.to(device, non_blocking=True) if torch.is_tensor(v) else v) for k, v in batch.items()}
            b = pre(b)
            policy.train()
            loss, info = policy.forward(b)
            m = next(v for v in batch.values() if torch.is_tensor(v)).shape[0]
            tot += float(loss) * m
            l1 += float(info.get("l1_loss", 0.0)) * m
            kld += float(info.get("kld_loss", 0.0)) * m
            n += m
            if physical:
                pred = policy.predict_action_chunk(b).double().cpu().numpy() * std + mean      # (B, H, 10)
                tgt = raw_action.double().numpy()
                Rp, Rt = Rl.rot6d_to_R(pred[..., 3:9]), Rl.rot6d_to_R(tgt[..., 3:9])
                cos = (np.trace(np.swapaxes(Rp, -1, -2) @ Rt, axis1=-2, axis2=-1) - 1) / 2
                errs["pos_mm"].append(1000 * np.linalg.norm(pred[..., :3] - tgt[..., :3], axis=-1))
                errs["rot_deg"].append(np.degrees(np.arccos(np.clip(cos, -1, 1))))
                errs["grip"].append(np.abs(pred[..., 9] - tgt[..., 9]))
                errs["valid"].append(~raw_pad.numpy())
    out = {"loss": tot / max(n, 1), "l1": l1 / max(n, 1), "kld": kld / max(n, 1), "samples": n}
    if physical and errs["valid"]:
        V = np.concatenate(errs["valid"])
        for k in ("pos_mm", "rot_deg", "grip"):
            E = np.concatenate(errs[k])
            out[k] = {**{f"j{j}": float(np.median(E[:, j][V[:, j]])) for j in JS if V[:, j].any()},
                      "chunk_mean": float(np.mean(E[V])), "chunk_median": float(np.median(E[V]))}
    del policy
    torch.cuda.empty_cache()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--run-dir", help="default: the config's output_dir")
    ap.add_argument("--out", help="default: experiments/<exp>/results")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--max-episodes", type=int, help="smoke tests: first N val episodes per set")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    run = Path(a.run_dir or cfg["output_dir"])
    out = Path(a.out or (Path(a.config).parent / "results"))
    out.mkdir(parents=True, exist_ok=True)
    rel = bool(cfg.get("relative"))
    stats = json.load(open(C.REPO / cfg["relative"]["stats"])) if rel else None
    ckpts = sorted(p for p in (run / "checkpoints").glob("[0-9]*") if (p / "pretrained_model").exists())
    chunk = json.load(open(ckpts[0] / "pretrained_model" / "config.json"))["chunk_size"]
    sets = val_episode_sets(cfg["dataset"]["root"])
    if a.max_episodes:
        sets = {k: v[:a.max_episodes] for k, v in sets.items()}
    loaders = {k: make_loader(cfg, v, chunk, stats, a.batch_size, a.workers) for k, v in sets.items()}
    res = {"experiment": cfg["experiment"], "run_dir": str(run), "val_episodes": sets, "checkpoints": []}
    for c in ckpts:
        row = {"step": int(c.name)}
        for k, L in loaders.items():
            row[k] = evaluate(c / "pretrained_model", L, False, stats, a.device)
        res["checkpoints"].append(row)
        print(f"step {row['step']:6d}: " + ", ".join(f"{k} loss {row[k]['loss']:.4f}" for k in loaders), flush=True)
    best = min(res["checkpoints"], key=lambda r: r["robot"]["loss"])
    res["best_step_robot_val"] = best["step"]
    if rel:
        res["physical"] = {}
        for label, step in (("best", best["step"]), ("last", res["checkpoints"][-1]["step"])):
            c = run / "checkpoints" / f"{step:06d}" / "pretrained_model"
            res["physical"][label] = {"step": step, **{k: evaluate(c, L, True, stats, a.device)
                                                       for k, L in loaders.items()}}
    json.dump(res, open(out / "val.json", "w"), indent=1)
    write_md(res, out / "val.md")
    print(f"best robot val: step {best['step']} loss {best['robot']['loss']:.4f}")


def write_md(res, path):
    sets = [k for k in ("robot", "glove") if k in res["checkpoints"][0]]
    L = [f"# {res['experiment']}: validation", "",
         "| step | " + " | ".join(f"{k} val loss (L1 + 10 KL) | {k} L1" for k in sets) + " |",
         "|---|" + "---|---|" * len(sets)]
    for r in res["checkpoints"]:
        L.append(f"| {r['step']} | " + " | ".join(f"{r[k]['loss']:.4f} | {r[k]['l1']:.4f}" for k in sets) + " |")
    L += ["", f"Best robot val at step {res['best_step_robot_val']}."]
    if "physical" in res:
        L += ["", "Relative-pose errors of the predicted chunk (VAE latent 0), median over non-padded steps:", "",
              "| checkpoint | set | pos mm j0 / j14 / j49 / j99 / chunk mean | rot deg j0 / j14 / j49 / j99 / mean | gripper chunk mean |",
              "|---|---|---|---|---|"]
        for label, p in res["physical"].items():
            for k in sets:
                e = p[k]
                f = lambda d: " / ".join(f"{d.get(f'j{j}', float('nan')):.1f}" for j in JS) + f" / {d['chunk_mean']:.1f}"
                L.append(f"| {label} ({p['step']}) | {k} | {f(e['pos_mm'])} | "
                         + " / ".join(f"{e['rot_deg'].get(f'j{j}', float('nan')):.2f}" for j in JS)
                         + f" / {e['rot_deg']['chunk_mean']:.2f} | {e['grip']['chunk_mean']:.3f} |")
    Path(path).write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
