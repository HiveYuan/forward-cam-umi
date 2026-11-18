#!/usr/bin/env python3
"""Tile vs SLAM glove labels in the same (relative) action space, for two states (Yosub's request, sync 2026-11-17).

Pairs that differ only in where the glove poses come from (tiles: FK of Yosub's HHs3 joints; SLAM):
  gripper state:       exp019_rel_Gtile48 (pilot_mix_gHs3_rel_tile)     vs exp046_rel_Gslam48_head (_rel_slam_v3)
  start-relative pose: exp059_rel_Gtile48_startstate (_rel_tile_v3)     vs exp053_rel_Gslam48_startstate (_rel_slam_v3)
with the teleop-only baselines exp018 / exp052, Yosub's joint-space G48 (exp049) as the reference, and D1 (exp051:
tiles, state = the tool pose in the robot base, the relative-space arm closest to Yosub's joint state).
Numbers: the 6 robot-val episodes (meta/val_episodes.json), best checkpoint by robot val, from each run's
results/val.json (exp049: results/physical_fk.json).

  python experiments/tile_vs_slam/compare.py                 # -> experiments/tile_vs_slam/results.{json,md}
  PYTHONPATH=. <lerobot52 python> experiments/tile_vs_slam/compare.py --recheck exp019_rel_Gtile48 ...
      re-evaluates the best checkpoints on robot val with the current slam.val_rel and compares with val.json
      (-> experiments/tile_vs_slam/recheck.json)
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EXP = REPO / "experiments"

REF = ("exp049_joint_G48", "Yosub's G48, joint space (exp049; paper 0.295)", "tiles")
ROWS = [  # (state, experiment, label, glove labels)
    ("gripper", "exp018_rel_T48", "T48 (exp018)", "–"),
    ("gripper", "exp019_rel_Gtile48", "G-tile48 (exp019)", "tiles"),
    ("gripper", "exp046_rel_Gslam48_head", "G-slam48 (exp046)", "SLAM"),
    ("start", "exp052_rel_T48_startstate", "T48 (exp052)", "–"),
    ("start", "exp059_rel_Gtile48_startstate", "G-tile48 (exp059)", "tiles"),
    ("start", "exp053_rel_Gslam48_startstate", "G-slam48 (exp053)", "SLAM"),
    ("pose in base (D1)", "exp051_rel_Gtile48_posestate", "G-tile48 (exp051)", "tiles"),
]
PAIRS = [("gripper", "exp019_rel_Gtile48", "exp046_rel_Gslam48_head"),
         ("start", "exp059_rel_Gtile48_startstate", "exp053_rel_Gslam48_startstate")]
METRICS = [("val", None), ("pos j14", ("pos_mm", "j14")), ("pos j49", ("pos_mm", "j49")),
           ("pos j99", ("pos_mm", "j99")), ("pos chunk mean", ("pos_mm", "chunk_mean")),
           ("rot chunk mean", ("rot_deg", "chunk_mean")), ("gripper chunk mean", ("grip", "chunk_mean"))]


def load(e):
    v = json.load(open(EXP / e / "results" / "val.json"))
    step = v["best_step_robot_val"]
    if "physical" in v:
        rob = v["physical"]["best"]["robot"]
        val = rob["loss"]
    else:   # joint-space run: loss in val.json, physical errors by slam.joint_physical
        val = next(c for c in v["checkpoints"] if c["step"] == step)["robot"]["loss"]
        rob = json.load(open(EXP / e / "results" / "physical_fk.json"))["physical"]["best"]["robot"]
    out = {"step": step, "episodes": v["val_episodes"]["robot"], "val": val}
    for name, key in METRICS[1:]:
        out[name] = rob[key[0]][key[1]]
    return out


def fmt(name, x):
    return f"{x:.3f}" if name in ("val", "gripper chunk mean") else (f"{x:.1f}°" if name.startswith("rot") else f"{x:.1f}")


def table():
    res = {e: load(e) for e in [REF[0]] + [r[1] for r in ROWS]}
    eps = {tuple(r["episodes"]) for r in res.values()}
    assert len(eps) == 1, f"arms evaluated on different robot-val episodes: {eps}"
    L = [f"Robot val, episodes {list(eps.pop())}, best checkpoint by robot val. Position in mm (median per step j; chunk mean "
         "over all 100 steps), rotation and gripper chunk means. Val losses compare across all relative arms (the three "
         "stats files have identical action statistics; they differ only in the state's); exp049's is in joint space. "
         "D1 (exp051) needs tiles for its state too (the tool pose in the robot base), like Yosub's joint state.", "",
         "| state | arm | glove labels | step | val | pos j14 / j49 / j99 / chunk mean (mm) | rot | gripper |",
         "|---|---|---|---|---|---|---|---|"]

    def row(state, e, label, src):
        r = res[e]
        pos = " / ".join(fmt(m, r[m]) for m in ("pos j14", "pos j49", "pos j99", "pos chunk mean"))
        L.append(f"| {state} | {label} | {src} | {r['step']} | {r['val']:.3f} | {pos} | {fmt('rot', r['rot chunk mean'])} "
                 f"| {r['gripper chunk mean']:.3f} |")
    row("joint", *REF)
    for r in ROWS:
        row(*r)
    L += ["", "SLAM minus tiles (same state; negative = SLAM better):", "",
          "| state | val | pos j14 | pos j49 | pos j99 | pos chunk mean | rot | gripper |", "|---|---|---|---|---|---|---|---|"]
    diffs = {}
    for state, t, s in PAIRS:
        d = {m: res[s][m] - res[t][m] for m, _ in METRICS}
        diffs[state] = d
        cells = []
        for m, _ in METRICS:
            rel = 100 * d[m] / res[t][m]
            cells.append(f"{d[m]:+.3f} ({rel:+.0f}%)" if m in ("val", "gripper chunk mean") else f"{d[m]:+.1f} ({rel:+.0f}%)")
        L.append(f"| {state} | " + " | ".join(cells) + " |")
    L += ["", "Glove gain (G48 vs T48 of the same state, chunk mean position):", "",
          "| state | tiles | SLAM |", "|---|---|---|"]
    for state, t, s in PAIRS:
        base = next(r[1] for r in ROWS if r[0] == state and r[3] == "–")
        g = lambda e: 100 * (res[e]["pos chunk mean"] / res[base]["pos chunk mean"] - 1)
        L.append(f"| {state} | {g(t):+.0f}% | {g(s):+.0f}% |")
    json.dump({"arms": res, "slam_minus_tile": diffs}, open(OUT / "results.json", "w"), indent=1)
    (OUT / "results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def recheck(exps):
    sys.path.insert(0, str(REPO))
    import yaml
    from slam.val_rel import evaluate, make_loader
    out = json.load(open(OUT / "recheck.json")) if (OUT / "recheck.json").exists() else {}
    for e in exps:
        cfg = yaml.safe_load(open(EXP / e / "config.yaml"))
        v = json.load(open(EXP / e / "results" / "val.json"))
        step = v["best_step_robot_val"]
        ck = Path(cfg["output_dir"]) / "checkpoints" / f"{step:06d}" / "pretrained_model"
        chunk = json.load(open(ck / "config.json"))["chunk_size"]
        stats = json.load(open(REPO / cfg["relative"]["stats"]))
        r = evaluate(ck, make_loader(cfg, v["val_episodes"]["robot"], chunk, stats, 16, 4), True, stats)
        old = v["physical"]["best"]["robot"]
        cmp = {"loss": (old["loss"], r["loss"]), "pos_chunk_mean": (old["pos_mm"]["chunk_mean"], r["pos_mm"]["chunk_mean"]),
               "rot_chunk_mean": (old["rot_deg"]["chunk_mean"], r["rot_deg"]["chunk_mean"])}
        out[e] = {"step": step, "stored_vs_now": cmp}
        print(e, step, {k: f"{a:.4f} -> {b:.4f}" for k, (a, b) in cmp.items()}, flush=True)
    json.dump(out, open(OUT / "recheck.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recheck", nargs="+", metavar="EXP")
    a = ap.parse_args()
    recheck(a.recheck) if a.recheck else table()
