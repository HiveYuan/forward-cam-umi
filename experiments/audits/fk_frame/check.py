#!/usr/bin/env python3
"""P1 check: is our glove tool frame the robot's FK tool frame (grasp_site)?

Yosub's pilot_glove_HHs3 carries joint actions: build_dataset's IK of the tile-chain glove pose
  F = inv(T_world_base) . T_world_body . inv(T_flange_body)   for grasp_site
(base_world_v3_20261016, --slow 2.5: step j = t_start + j / 37.5 s of the recording). So
FK(q_HHs3) should reproduce our own tile-chain tool pose for the same episode, up to the IK
tolerance (1 mm / 0.57 deg), build_dataset's slew clamp and the differences between the two
tile chains (his: single-tile frames chained; ours: >= 2 tiles, bridged <= 0.5 s).

HHs3 segment -> source episode and time offset: for each HHs3 segment of glove8 (0-3), glove7 (4-33) and
glove6 take 1 (from 34), the take episode (expected +- 3) and start offset with the smallest median position
error; a match needs < 5 mm on >= 30 steps (HHs3 trims and splits episodes, and our strict tile chain
leaves gaps). For each matched segment:
  ours(t) = T_base_world . T_world_cam(t) . T_cam_body(t) . inv(T_flange_body_H), per head frame,
            interpolated to the HHs3 step times between valid frames at most 0.1 s apart;
  the time offset of the HHs3 episode is searched (trimmed episodes start later);
  errors: absolute (pose in the base) and relative over k steps (tool_t -> tool_t+k, the quantity
          the relative labels use; independent of base_world), k = 15 (0.4 s) and 37 (~1 s).
  H = each hand-eye file that could have been used: handeye_glove_yosub (ours),
      handeye_glove_yosub_spring, handeye (the robot ball).
Teleop: FK of pilot_head_Hgt actions and states, position / tool-axis ranges next to the
glove's (FK of HHs3) in the same base frame.

  R=/home/student/miniconda3/envs/lerobot/bin/python
  PYTHONPATH=. $R experiments/audits/fk_frame/check.py      # -> results.json, results.md
"""
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from slam import geometry as G
from slam.evaluate import load_segment
from slam.labels import interp_poses, tile_world_cam
from slam.robot_fk import YamFK

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LR = Path.home() / ".cache/huggingface/lerobot"
RUNS = Path("/home/student/yuanliu-hawaii/work/runs")
SLOW_DT = 1.0 / 37.5
HANDEYES = ["handeye_glove_yosub", "handeye_glove_yosub_spring", "handeye"]
# session, view segments dir, HHs3 episodes to match, expected take episode of HHs3 episode h
SESSIONS = [
    ("glove8", RUNS / "exp010_glove8/main/view/yam_glove8/segments", range(0, 4), lambda h: h),
    ("glove7", RUNS / "exp009_net_scale/main/view/yam_glove7/segments", range(4, 34), lambda h: h - 4),
    ("glove6 take 1", RUNS / "exp012_glove6_take1/main/view/yam_glove6_take1/segments", range(34, 66),
     lambda h: h - 33),
]
SEARCH = 3            # candidate take episodes: expected +- SEARCH
MATCH_MM = 5.0        # a match: median position error at the best offset below this
KS = (15, 37)


def load_lerobot(name):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(LR / name / "data/**/*.parquet"), recursive=True))])
    return (np.stack(df["action"].values).astype(float), np.stack(df["observation.state"].values).astype(float),
            df["episode_index"].values)


def rot_deg(R):
    return np.degrees(np.arccos(np.clip((np.trace(R, axis1=-2, axis2=-1) - 1) / 2, -1, 1)))


def ours_at(S, T_bt, T_bw, tq):
    """Our tool pose in the base at times tq (NaN where no valid frame within 50 ms)."""
    T_wc = tile_world_cam(S)
    ok = np.isfinite(T_wc[:, 0, 0]) & np.isfinite(S["T_cb"][:, 0, 0])
    ts = S["wall"][ok]
    out = np.full((len(tq), 4, 4), np.nan)
    if ok.sum() < 2:
        return out
    T = T_bw[None] @ T_wc[ok] @ S["T_cb"][ok] @ T_bt[None]
    i = np.clip(np.searchsorted(ts, tq), 1, len(ts) - 1)
    inside = (tq >= ts[0]) & (tq <= ts[-1]) & (ts[i] - ts[i - 1] <= 0.1)    # both neighbours within 0.1 s
    if inside.any():
        out[inside] = interp_poses(tq[inside], ts, T)
    return out


def errors(F, O, ks=KS, free=None):
    """free: (N,) bool, steps whose IK solution is not at a joint limit (None = all)."""
    v = np.isfinite(O[:, 0, 0]) & (True if free is None else free)
    r = {"n": int(v.sum())}
    if v.sum() < 10:
        return r
    r["abs_mm"] = 1000 * np.linalg.norm(F[v, :3, 3] - O[v, :3, 3], axis=1)
    r["abs_deg"] = rot_deg(np.swapaxes(F[v, :3, :3], 1, 2) @ O[v, :3, :3])
    for k in ks:
        i = np.where(v[:-k] & v[k:])[0]
        if len(i) == 0:
            continue
        rf = G.inv(F[i]) @ F[i + k]
        ro = G.inv(O[i]) @ O[i + k]
        r[f"rel{k}_mm"] = 1000 * np.linalg.norm(rf[:, :3, 3] - ro[:, :3, 3], axis=1)
        r[f"rel{k}_deg"] = rot_deg(np.swapaxes(rf[:, :3, :3], 1, 2) @ ro[:, :3, :3])
        r[f"rel{k}_motion_mm"] = 1000 * np.linalg.norm(ro[:, :3, 3], axis=1)
    return r


def best_offset(S, T_bt, T_bw, t0, F, free):
    """Offset d (s) of the HHs3 episode start against the episode mark, by median position error
    over the steps whose IK is not at a joint limit (free)."""
    j = np.arange(len(F))

    def cost(d):
        O = ours_at(S, T_bt, T_bw, t0 + d + j * SLOW_DT)
        v = np.isfinite(O[:, 0, 0]) & free
        if v.sum() < 30:
            return np.inf
        return float(np.median(np.linalg.norm(F[v, :3, 3] - O[v, :3, 3], axis=1)))

    span = S["wall"][-1] - t0
    coarse = np.arange(-1.0, max(span - 30 * SLOW_DT, 0) + 0.05, 0.1)     # split segments start later
    d0 = min(coarse, key=cost)
    fine = np.arange(d0 - 0.1, d0 + 0.1001, 0.005)
    d = min(fine, key=cost)
    return float(d), cost(d)


def near_limit(Q, fk, tol=0.005):
    lo, hi = fk.model.jnt_range[:6, 0], fk.model.jnt_range[:6, 1]
    return (Q <= lo + tol) | (Q >= hi - tol)


def at_limit(Q, fk, tol=0.005):
    """Steps whose IK solution has a joint at the model's range limit (the target was not reached)."""
    return near_limit(Q, fk, tol).any(1)


def q(x, p):
    return float(np.percentile(x, p)) if len(x) else None


def summarize(rows, key):
    x = np.concatenate([r[key] for r in rows if key in r]) if any(key in r for r in rows) else np.zeros(0)
    return {"n": int(len(x)), "median": q(x, 50), "p90": q(x, 90)}


def main():
    fk = YamFK()
    T_bw = np.array(json.load(open(REPO / "calib/base_world_v3_20261016.json"))["T_base_world"], float)
    T_bts = {h: G.inv(np.array(json.load(open(REPO / f"calib/{h}.json"))["T_flange_body"], float)[None])[0]
             for h in HANDEYES}
    A, _, E = load_lerobot("pilot_glove_HHs3")
    res = {"episodes": [], "pooled": {}}
    per_h = {h: [] for h in HANDEYES}
    lim_rows = []
    lim_all = at_limit(A[:, :6], fk)
    res["hhs3_steps_at_joint_limit"] = {"steps": int(lim_all.sum()), "of": int(len(A)),
                                        "per_joint": [int(x) for x in near_limit(A[:, :6], fk).sum(0)]}
    for sess, segdir, hs, to_e in SESSIONS:
        segs = {}
        for seg in sorted(segdir.glob("ep[0-9][0-9]")):
            ep = json.load(open(seg / "frames.json"))["episode"]
            segs[ep["episode_index"]] = (load_segment(seg), ep)
        for h in hs:
            F = fk(A[E == h, :6])
            free = ~at_limit(A[E == h, :6], fk)
            best = (np.inf, None, None)
            for e in range(to_e(h) - SEARCH, to_e(h) + SEARCH + 1):
                if e in segs:
                    S, ep = segs[e]
                    d, c = best_offset(S, T_bts[HANDEYES[0]], T_bw, ep["t_start"], F, free)
                    if c < best[0]:
                        best = (c, e, d)
            c, e, d = best
            row = {"session": sess, "hhs3": h, "steps": len(F), "episode": e,
                   "offset_s": None if e is None else round(d, 3),
                   "median_pos_mm_at_offset": None if e is None else round(1000 * c, 2)}
            res["episodes"].append(row)
            if e is None or 1000 * c >= MATCH_MM:
                print(f"{sess} HHs3 {h:3d}: no match (best ep {e}, {1000 * c:.1f} mm)")
                continue
            S, ep = segs[e]
            tq = ep["t_start"] + d + np.arange(len(F)) * SLOW_DT
            row["at_limit_steps"] = int((~free).sum())
            lim_rows.append(errors(F, ours_at(S, T_bts[HANDEYES[0]], T_bw, tq), free=~free))
            for hname in HANDEYES:
                r = errors(F, ours_at(S, T_bts[hname], T_bw, tq), free=free)
                per_h[hname].append(r)
                row[hname] = {k: (float(np.median(v)) if isinstance(v, np.ndarray) else v) for k, v in r.items()}
            print(f"{sess} HHs3 {h:3d} = ep{e:02d} {d:+.3f} s: abs {row[HANDEYES[0]].get('abs_mm', float('nan')):.1f} mm, "
                  f"rel(1 s) {row[HANDEYES[0]].get('rel37_mm', float('nan')):.1f} mm, at limit {row['at_limit_steps']}")
    good = [r for r in res["episodes"] if HANDEYES[0] in r]
    res["matched"] = len(good)
    res["unmatched"] = [(r["session"], r["hhs3"], r["episode"], r["median_pos_mm_at_offset"])
                        for r in res["episodes"] if HANDEYES[0] not in r]
    for hname in HANDEYES:
        res["pooled"][hname] = {k: summarize(per_h[hname], k) for k in
                                ["abs_mm", "abs_deg"] + [f"rel{k}_{u}" for k in KS for u in ("mm", "deg", "motion_mm")]}
    res["pooled_at_limit"] = {k: summarize(lim_rows, k) for k in ("abs_mm", "abs_deg")}


    # teleop vs glove in the base frame
    At, St, Et = load_lerobot("pilot_head_Hgt")
    Fa, Fs, Fg = fk(At[:, :6]), fk(St[:, :6]), fk(A[:, :6])
    lag = []
    for L in range(0, 6):
        m = Et[L:] == Et[:len(Et) - L]
        lag.append(float(np.median(1000 * np.linalg.norm(Fa[:len(Fa) - L, :3, 3] - Fs[L:, :3, 3], axis=1)[m])))
    def dist(Fx):
        p, z = Fx[:, :3, 3], Fx[:, :3, 2]
        return {"pos_p5_p50_p95_m": np.percentile(p, [5, 50, 95], axis=0).round(3).tolist(),
                "tool_z_p5_p50_p95": np.percentile(z, [5, 50, 95], axis=0).round(3).tolist()}
    res["teleop"] = {"fk_action_vs_state_mm_by_lag_steps": [round(x, 2) for x in lag],
                     "teleop_action": dist(Fa), "glove_HHs3": dist(Fg)}
    json.dump(res, open(HERE / "results.json", "w"), indent=1, default=float)
    write_md(res)


def write_md(res):
    f = lambda s: "–" if s["median"] is None else f"{s['median']:.2f} / {s['p90']:.2f}"
    L = ["# FK frame check (P1): FK(HHs3 joints) vs our tile-chain tool pose", "",
         f"Matched HHs3 segments: {res['matched']}; unmatched (session, HHs3, best take episode, median mm): "
         f"{res['unmatched']}", "",
         f"HHs3 steps with an IK joint at the model's range limit: {res['hhs3_steps_at_joint_limit']}; "
         f"on matched episodes their FK is off our pose by {f(res['pooled_at_limit']['abs_mm'])} mm, "
         f"{f(res['pooled_at_limit']['abs_deg'])} deg (median / p90). They are left out of the table below.", "",
         "| hand-eye (T_flange_body) | abs pos mm | abs rot deg | rel 0.4 s pos mm | rel 0.4 s rot deg | "
         "rel 1 s pos mm | rel 1 s rot deg | tool motion in 1 s, mm |", "|---|---|---|---|---|---|---|---|"]
    for h, p in res["pooled"].items():
        L.append(f"| {h} | {f(p['abs_mm'])} | {f(p['abs_deg'])} | {f(p['rel15_mm'])} | {f(p['rel15_deg'])} | "
                 f"{f(p['rel37_mm'])} | {f(p['rel37_deg'])} | {f(p['rel37_motion_mm'])} |")
    L += ["", "Values are median / p90 over all matched HHs3 steps.", "", "## Teleop vs glove in the base frame", "",
          f"FK(action) vs FK(state), median mm by lag 0..5 steps: {res['teleop']['fk_action_vs_state_mm_by_lag_steps']}",
          "", "| | position p5 / p50 / p95 (m, x y z) | tool z-axis p5 / p50 / p95 |", "|---|---|---|"]
    for k in ("teleop_action", "glove_HHs3"):
        d = res["teleop"][k]
        L.append(f"| {k} | {d['pos_p5_p50_p95_m']} | {d['tool_z_p5_p50_p95']} |")
    L += ["", "## Per episode (hand-eye handeye_glove_yosub)", "",
          "| session | take ep | HHs3 | steps | offset s | compared steps | at joint limit | abs mm | rel 1 s mm |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in res["episodes"]:
        if HANDEYES[0] not in r:
            continue
        h = r[HANDEYES[0]]
        L.append(f"| {r['session']} | {r['episode']} | {r['hhs3']} | {r['steps']} | {r['offset_s']:+.3f} | {h['n']} | "
                 f"{r['at_limit_steps']} | {h.get('abs_mm', float('nan')):.1f} | {h.get('rel37_mm', float('nan')):.1f} |")
    (HERE / "results.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
