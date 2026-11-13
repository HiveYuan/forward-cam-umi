#!/usr/bin/env python3
"""Physical chunk errors of a joint-space policy (Yosub's arms), comparable with slam.val_rel's relative-run errors.

slam.val_rel saves a joint-space run's predicted chunks (VAE latent 0) and labels to
<run_dir>/val_chunks/<best|last>_<set>.npz {pred, tgt (N, H, 7: joint1-6 rad + gripper), pad (N, H)}. Here both
go through the YAM FK (slam.robot_fk, i2rt grasp_site, the tool frame of every label):
  * tool position error |p_pred - p_tgt| in mm and rotation error angle(R_pred^T R_tgt) in deg;
  * gripper |pred - tgt| in command units;
  * at j = 0, 14, 49, 99 (median) and over the chunk (mean, median), on non-padded steps.
These equal val_rel's relative-run errors: the relative label is anchor^-1 . FK(target), and a common anchor
changes neither the position distance nor the relative rotation.

  L=/home/student/miniconda3/envs/lerobot/bin/python      # i2rt + mink
  PYTHONPATH=. $L -m slam.joint_physical experiments/<exp>/config.yaml   # -> results/physical_fk.{json,md}
"""
import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from slam.robot_fk import YamFK

JS = (0, 14, 49, 99)


def chunk_errors(pred, tgt, pad, fk):
    n, h = pred.shape[:2]
    Tp = fk(pred[..., :6].reshape(-1, 6)).reshape(n, h, 4, 4)
    Tt = fk(tgt[..., :6].reshape(-1, 6)).reshape(n, h, 4, 4)
    pos = 1000 * np.linalg.norm(Tp[..., :3, 3] - Tt[..., :3, 3], axis=-1)
    cos = (np.trace(np.swapaxes(Tp[..., :3, :3], -1, -2) @ Tt[..., :3, :3], axis1=-2, axis2=-1) - 1) / 2
    rot = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    grip = np.abs(pred[..., 6] - tgt[..., 6])
    V = ~pad.astype(bool)
    out = {}
    for k, E in (("pos_mm", pos), ("rot_deg", rot), ("grip", grip)):
        out[k] = {**{f"j{j}": float(np.median(E[:, j][V[:, j]])) for j in JS if j < h and V[:, j].any()},
                  "chunk_mean": float(np.mean(E[V])), "chunk_median": float(np.median(E[V]))}
    out["samples"] = int(n)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--run-dir", help="default: the config's output_dir")
    ap.add_argument("--out", help="default: experiments/<exp>/results")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    run = Path(a.run_dir or cfg["output_dir"])
    out = Path(a.out or (Path(a.config).parent / "results"))
    val = json.load(open(out / "val.json"))
    fk = YamFK()
    res = {"experiment": cfg["experiment"], "method": "slam.joint_physical: FK (i2rt grasp_site) of predicted vs label "
           "joint chunks, VAE latent 0", "physical": {}}
    for key, d in sorted(val["val_chunks"].items()):
        label, vset = key.split("_", 1)
        z = np.load(run / d["file"])
        res["physical"].setdefault(label, {"step": d["step"]})[vset] = chunk_errors(z["pred"], z["tgt"], z["pad"], fk)
        e = res["physical"][label][vset]
        print(f"{key} (step {d['step']}): pos mm mean {e['pos_mm']['chunk_mean']:.1f}, rot deg mean "
              f"{e['rot_deg']['chunk_mean']:.2f}, gripper mean {e['grip']['chunk_mean']:.3f}", flush=True)
    json.dump(res, open(out / "physical_fk.json", "w"), indent=1)
    L = [f"# {cfg['experiment']}: physical chunk errors (FK of the joint chunks, VAE latent 0)", "",
         "Median over non-padded steps at j; chunk mean over all steps (comparable with val.md of the relative runs).", "",
         "| checkpoint | set | pos mm j0 / j14 / j49 / j99 / chunk mean | rot deg j0 / j14 / j49 / j99 / mean | gripper chunk mean |",
         "|---|---|---|---|---|"]
    for label, p in res["physical"].items():
        for vset in (k for k in p if k != "step"):
            e = p[vset]
            f = lambda d, fmt: " / ".join(fmt.format(d.get(f"j{j}", float("nan"))) for j in JS) + " / " + fmt.format(d["chunk_mean"])
            L.append(f"| {label} ({p['step']}) | {vset} | {f(e['pos_mm'], '{:.1f}')} | {f(e['rot_deg'], '{:.2f}')} | "
                     f"{e['grip']['chunk_mean']:.3f} |")
    (out / "physical_fk.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
