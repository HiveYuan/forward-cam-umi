#!/usr/bin/env python3
"""Evaluate SLAM head trajectories against the tile ground truth.

For every segment and run, pairs (a, b) are formed with an anchor frame a inside the
episode and b the frame whose wall time is closest to t_a + dt (within half a frame).
Both frames need a strict tile pose (>= 2 tiles, rms <= 5 px) and a SLAM pose.

  head motion   cam_a->cam_b = (world->cam_a ... ) from the tiles vs (slam->cam_a)^-1 (slam->cam_b)
  rotation err  angle(R_gt^T R_slam)                         [deg]  primary, scale-free
  trans err     |t_gt - s t_slam|, s = per-segment Umeyama   [mm]   oracle (tile-fitted) scale
  label err     tool_a->tool_b with the ball poses at both ends (build_dataset "full"
                variant) and the flange (tool) frame, tile head motion vs SLAM head motion
  static        baseline cam_a->cam_b = I (no SLAM at all)
  track fail    dt = 0.08 s pairs whose rotation error exceeds 2 deg
  same_tiles    1 if the same tile set is detected at both ends (tiles.npz). The tile GT
                has a fixed per-tile-set bias (~0.4 deg, slam.tiles noise), so pairs whose
                tile set changes carry that bias; same-tile pairs are the cleaner reference

Outputs (in <work>/<session>/eval/):
  pairs.csv       one row per (run, segment, dt, anchor)
  summary.json    per run x dt: medians / p90 / p95, per head-speed bin, per segment
  summary.md      the same as tables

  python -m slam.evaluate --session yam_glove7 --runs E1,E2,E3
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G

DTS = [0.08, 0.25, 0.5, 1.0, 2.0, 4.0, 6.67]
SPEED_BINS = [0, 10, 30, 60, 1e9]           # deg/s of head rotation, at dt = 0.5 s
FAIL_DEG = 2.0


def load_tool_offset(session):
    """T_body_tool = inverse of the glove hand-eye's T_flange_body (build_dataset's Binv)."""
    s = C.session(session)
    he = json.load(open(C.CALIB / f"handeye_glove_{s['glove']}.json"))
    return G.inv(np.array(he["T_flange_body"], float)[None])[0]


def load_segment(seg):
    fj = json.load(open(seg / "frames.json"))
    fr = fj["frames"]
    k = np.array([f["k"] for f in fr])
    wall = np.array([f["wall"] for f in fr])
    ine = np.array([f["in_episode"] for f in fr])
    gt = np.load(seg / "gt.npz")
    n = len(k)
    idx = {kk: i for i, kk in enumerate(k)}

    T_wc = np.full((n, 4, 4), np.nan)
    strict = np.zeros(n, bool)
    tiles = np.zeros(n, int)
    for kk, T, nt, rms in zip(gt["cam_k"], gt["T_cam_world"], gt["cam_tiles"], gt["cam_rms"]):
        i = idx[int(kk)]
        T_wc[i] = G.inv(T[None])[0]
        tiles[i] = nt
        strict[i] = nt >= 2 and rms <= 5.0
    T_cb = np.full((n, 4, 4), np.nan)
    if len(gt["full_k"]):
        Tb = G.rt_to_T(gt["full_rvec"], gt["full_tvec"])
        for kk, T in zip(gt["full_k"], Tb):
            T_cb[idx[int(kk)]] = T
    tile_set = [frozenset() for _ in range(n)]
    if (seg / "tiles.npz").exists():
        z = np.load(seg / "tiles.npz")
        sets = {}
        for kk, tid in zip(z["det_k"], z["det_id"]):
            sets.setdefault(int(kk), set()).add(int(tid))
        tile_set = [frozenset(sets.get(int(kk), ())) for kk in k]
    return {"name": seg.name, "k": k, "wall": wall, "in_ep": ine, "T_wc": T_wc,
            "strict": strict, "tiles": tiles, "T_cb": T_cb, "tile_set": tile_set}


def load_run(seg, run, n):
    p = seg / "slam" / f"{run}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    if len(z["k"]) != n:
        raise RuntimeError(f"{p}: {len(z['k'])} poses for {n} frames")
    return z["T_slam_cam"].astype(float), json.loads(str(z["meta"]))


def pairs_for(S, dt):
    wall, ok = S["wall"], S["strict"]
    a_idx = np.where(S["in_ep"] & ok)[0]
    b_idx = np.searchsorted(wall, wall[a_idx] + dt)
    out = []
    for a, b in zip(a_idx, b_idx):
        cands = [c for c in (b - 1, b) if a < c < len(wall)]
        if not cands:
            continue
        c = min(cands, key=lambda c: abs(wall[c] - wall[a] - dt))
        if abs(wall[c] - wall[a] - dt) <= 0.021 and ok[c]:
            out.append((a, c))
    return np.array(out, int).reshape(-1, 2)


def segment_scale(S, T_sc):
    m = S["strict"]
    if m.sum() < 10:
        return np.nan, np.nan
    src, dst = T_sc[m, :3, 3], S["T_wc"][m, :3, 3]
    if np.linalg.norm(dst - dst.mean(0), axis=1).max() < 0.01:     # < 1 cm of head travel
        return np.nan, np.nan
    s, R, t = G.umeyama_scale(src, dst)
    res = np.linalg.norm(dst - (s * (R @ src.T).T + t), axis=1)
    return s, float(np.median(res))


def evaluate_pairs(S, T_sc, s, T_bt, P):
    a, b = P[:, 0], P[:, 1]
    rel_gt = G.inv(S["T_wc"][a]) @ S["T_wc"][b]
    out = {"same_tiles": np.array([float(S["tile_set"][i] == S["tile_set"][j]) for i, j in P]),
           "gt_rot_deg": G.rot_angle_deg(rel_gt[:, :3, :3]),
           "gt_trans_mm": 1000 * np.linalg.norm(rel_gt[:, :3, 3], axis=1)}
    if T_sc is not None:
        rel = G.inv(T_sc[a]) @ T_sc[b]
        out["rot_err_deg"] = G.rot_angle_deg(np.swapaxes(rel_gt[:, :3, :3], 1, 2) @ rel[:, :3, :3])
        rel_s = rel.copy()
        rel_s[:, :3, 3] *= s
        out["trans_err_mm"] = 1000 * np.linalg.norm(rel_gt[:, :3, 3] - rel_s[:, :3, 3], axis=1)
    else:                                           # static-head baseline: rel = I
        rel_s = np.tile(np.eye(4), (len(P), 1, 1))
        out["rot_err_deg"] = out["gt_rot_deg"].copy()
        out["trans_err_mm"] = out["gt_trans_mm"].copy()
    # end-to-end label: tool_a -> tool_b
    Ta = S["T_cb"][a] @ T_bt
    Tb = S["T_cb"][b] @ T_bt
    lab_gt = G.inv(Ta) @ rel_gt @ Tb
    lab = G.inv(Ta) @ rel_s @ Tb
    d = G.inv(lab_gt) @ lab
    out["label_pos_err_mm"] = 1000 * np.linalg.norm(lab_gt[:, :3, 3] - lab[:, :3, 3], axis=1)
    out["label_rot_err_deg"] = G.rot_angle_deg(d[:, :3, :3])
    return out


def stats(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "median": float(np.median(x)), "p90": float(np.percentile(x, 90)),
            "p95": float(np.percentile(x, 95)), "mean": float(x.mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--runs", default="E1,E2,E3")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out) if a.out else C.WORK / a.session / "eval"
    out.mkdir(parents=True, exist_ok=True)
    T_bt = load_tool_offset(a.session)
    runs = ["static"] + [r for r in a.runs.split(",") if r]

    rows, seg_info = [], {}
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        S = load_segment(seg)
        seg_info[S["name"]] = {"n_frames": len(S["k"]), "in_ep": int(S["in_ep"].sum()),
                               "in_ep_strict": int((S["in_ep"] & S["strict"]).sum())}
        for run in runs:
            if run == "static":
                T_sc, meta, s, res = None, {}, np.nan, np.nan
            else:
                r = load_run(seg, run, len(S["k"]))
                if r is None:
                    continue
                T_sc, meta = r
                s, res = segment_scale(S, T_sc)
                seg_info[S["name"]][run] = {"scale": s, "align_res_mm": 1000 * res,
                                            "n_keyframes": meta.get("n_keyframes"),
                                            "runtime_s": meta.get("runtime_s"),
                                            "valid_frac": meta.get("valid_frac")}
            for dt in DTS:
                P = pairs_for(S, dt)
                if len(P) == 0:
                    continue
                e = evaluate_pairs(S, T_sc, s, T_bt, P)
                for j, (pa, pb) in enumerate(P):
                    rows.append({"run": run, "segment": S["name"], "dt": dt, "k_a": int(S["k"][pa]),
                                 "k_b": int(S["k"][pb]), **{key: float(v[j]) for key, v in e.items()}})

    keys = list(rows[0].keys())
    with open(out / "pairs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    col = {k: np.array([r[k] for r in rows]) for k in keys if k not in ("run", "segment")}
    run_c = np.array([r["run"] for r in rows])
    seg_c = np.array([r["segment"] for r in rows])
    summary = {"dts": DTS, "runs": {}, "segments": seg_info}
    for run in runs:
        R = {"by_dt": {}, "by_speed_dt0.5": {}, "per_segment_dt1": {}}
        for dt in DTS:
            m = (run_c == run) & np.isclose(col["dt"], dt)
            R["by_dt"][str(dt)] = {k: stats(col[k][m]) for k in
                                   ("rot_err_deg", "trans_err_mm", "label_pos_err_mm", "label_rot_err_deg",
                                    "gt_rot_deg", "gt_trans_mm")}
            ms = m & (col["same_tiles"] > 0.5)
            R["by_dt"][str(dt)]["rot_err_deg_same_tiles"] = stats(col["rot_err_deg"][ms])
            R["by_dt"][str(dt)]["trans_err_mm_same_tiles"] = stats(col["trans_err_mm"][ms])
        m = (run_c == run) & np.isclose(col["dt"], 0.08)
        R["track_fail_frac"] = float((col["rot_err_deg"][m] > FAIL_DEG).mean()) if m.any() else None
        m5 = (run_c == run) & np.isclose(col["dt"], 0.5)
        speed = col["gt_rot_deg"] / 0.5
        for lo, hi in zip(SPEED_BINS[:-1], SPEED_BINS[1:]):
            mb = m5 & (speed >= lo) & (speed < hi)
            R["by_speed_dt0.5"][f"{lo}-{hi if hi < 1e8 else 'inf'}"] = stats(col["rot_err_deg"][mb])
        for sname in seg_info:
            ms = (run_c == run) & np.isclose(col["dt"], 1.0) & (seg_c == sname)
            R["per_segment_dt1"][sname] = stats(col["rot_err_deg"][ms])
        summary["runs"][run] = R
    json.dump(summary, open(out / "summary.json", "w"), indent=1, default=float)
    md = render_md(summary, runs)
    (out / "summary.md").write_text(md)
    print(md)


def fmt(s, key="median"):
    return "-" if not s or s.get("n", 0) == 0 else f"{s[key]:.2f}"


def render_md(S, runs):
    L = []
    for metric, title in (("rot_err_deg", "Head rotation error [deg]"),
                          ("rot_err_deg_same_tiles", "Head rotation error, same tiles seen at both ends [deg]"),
                          ("trans_err_mm", "Head translation error, tile-fitted scale [mm]"),
                          ("label_pos_err_mm", "Label (tool_t->tool_t+dt) position error [mm]"),
                          ("label_rot_err_deg", "Label rotation error [deg]")):
        L += [f"### {title}: median / p95", "",
              "| run | " + " | ".join(f"{d}s" for d in S["dts"]) + " |",
              "|---|" + "---|" * len(S["dts"])]
        for run in runs:
            cells = []
            for d in S["dts"]:
                s = S["runs"][run]["by_dt"][str(d)][metric]
                cells.append(f"{fmt(s)} / {fmt(s, 'p95')}")
            L.append(f"| {run} | " + " | ".join(cells) + " |")
        L.append("")
    n = S["runs"][runs[0]]["by_dt"]
    L += ["Pairs per dt: " + ", ".join(f"{d}s: {n[str(d)]['rot_err_deg'].get('n', 0)}" for d in S["dts"]), ""]
    L += ["### Rotation error at dt = 0.5 s by head rotation speed [deg/s]: median (n)", "",
          "| run | " + " | ".join(S["runs"][runs[0]]["by_speed_dt0.5"]) + " |",
          "|---|" + "---|" * len(S["runs"][runs[0]]["by_speed_dt0.5"])]
    for run in runs:
        b = S["runs"][run]["by_speed_dt0.5"]
        L.append(f"| {run} | " + " | ".join(f"{fmt(v)} ({v.get('n', 0)})" for v in b.values()) + " |")
    L += ["", "### Tracking failures (dt = 0.08 s pairs with rotation error > 2 deg)", ""]
    for run in runs[1:]:
        f = S["runs"][run]["track_fail_frac"]
        L.append(f"- {run}: {100 * f:.2f}%" if f is not None else f"- {run}: -")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
