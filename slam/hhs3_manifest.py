#!/usr/bin/env python3
"""Source manifest of pilot_glove_HHs3: for every HHs3 episode, the take, episode and wall-clock start.

Yosub's reconstruction, calib/pilot_glove_HHs3_sources.csv (2026-11-10), matched the 200 HHs3 episode
lengths in build order to the marked episodes: 174 whole marks ("exact", range = the mark's t_start..t_end
clipped to label coverage), 12 "trimmed" and 7 marks "split" in two (s0, s1) by blind gaps, for which
the builder did not log where the range starts. HHs3 step j of an episode is the recording at
t0 + j / (15 * 2.5) s (build_dataset --slow 2.5).

This module finds t0 for every HHs3 episode and verifies it: HHs3's joint actions are build_dataset's IK
of the tile-chain glove pose (experiments/audits/fk_frame), so FK(q_j) must match our own tile-chain
tool pose in the base,
    T_base_world . T_world_cam(t) . T_cam_body(t) . inv(T_flange_body),
at t = t0 + j / 37.5. Our side uses every head frame with a tile solve (single-tile frames included,
reprojection rms <= RMS_MAX px) and a ball pose (the "full" variant, build_dataset's glove setting),
interpolated between frames at most BRACKET_S apart. Steps that ik_flag marks (a joint at its range
limit, or joint 3 on the stretched-arm plateau: the IK did not reach the glove pose) are left out. t0 is searched around the mark (exact: +-0.3 s; trimmed and
split: anywhere the episode fits in its mark), by the median position error.

An episode that fails against the CSV's mark is searched on the neighbouring marks of the take (the
CSV's length walk is ambiguous where marks were trimmed: glove6 main 40-43 are 40 and 41 trimmed, 42
and 43 whole, not "40 split, 41 and 42 trimmed, 43 dropped"); a mark that verifies replaces it.

Output calib/hhs3_manifest.json: per HHs3 episode {hhs3, session (our take session), take_episode,
source_episode, csv_source_episode, status (the CSV's), steps, ik_flag, t0, t0_minus_mark, compared,
median_mm, p90_mm, method, verified, t0_reliable}. method: verified (median < OK_MM on >= MIN_COMPARED
steps), remapped (verified on another mark), mark_start (an "exact" episode too IK-limited to verify:
t0 = the mark's start, as every verified exact episode has), unknown (t0 None). t0_reliable is false
only for unknown; the dataset builder gives those episodes no SLAM labels.

  R=/home/student/miniconda3/envs/lerobot/bin/python
  PYTHONPATH=. $R -m slam.hhs3_manifest            # all sessions whose ground truth exists
"""
import argparse
import csv
import glob
import json
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G

SLOW_DT = 1.0 / 37.5
RMS_MAX, MIN_TILES, BRACKET_S, LIMIT_TOL = 5.0, 1, 0.1, 0.005
J3_STRAIGHT, J3_TOL = 2.9014, 0.001     # HHs3's IK plateau of joint 3 at the stretched arm (targets out of reach)
OK_MM, MIN_COMPARED, SEARCH = 3.0, 20, 3
LR = Path.home() / ".cache/huggingface/lerobot"
SOURCES = C.CALIB / "pilot_glove_HHs3_sources.csv"
OUT = C.CALIB / "hhs3_manifest.json"
TAKES = Path("/home/student/yuanliu-hawaii/work/takes/data/raw")
STEM_TO_SESSION = {
    "yam_glove8_b0587b": "yam_glove8",
    "yam_glove7_b0587b": "yam_glove7",
    "yam_glove6_b0587b.take1": "yam_glove6_take1",
    "yam_glove6_b0587b": "yam_glove6_take2",
    "yam_glove5_b0587b.take1": "yam_glove5_take1",
    "yam_glove5_b0587b": "yam_glove5_take2",
}


def aligned_quats(R):
    """Quaternions of a pose sequence, sign-aligned to their predecessor (as labels.interp_poses does),
    computed once so that interpolation is vectorised."""
    q = G.R_to_quat(R)
    if len(q) > 1:
        flip = np.cumprod(np.where(np.einsum("ij,ij->i", q[1:], q[:-1]) < 0, -1.0, 1.0))
        q[1:] *= flip[:, None]
    return q


def interp_aligned(tq, ts, q, p):
    """labels.interp_poses with precomputed aligned quaternions q and translations p."""
    qi = np.stack([np.interp(tq, ts, q[:, c]) for c in range(4)], 1)
    qi /= np.linalg.norm(qi, axis=1, keepdims=True)
    out = np.tile(np.eye(4), (len(tq), 1, 1))
    out[:, :3, :3] = G.quat_to_R(qi)
    out[:, :3, 3] = np.stack([np.interp(tq, ts, p[:, c]) for c in range(3)], 1)
    return out


def raw_dir(session):
    return TAKES if (TAKES / f"{session}_b0587b_ts.json").exists() else C.RAW


def take_episodes(session):
    """source episode index -> (take episode index, mark)."""
    eps = json.load(open(raw_dir(session) / f"{session}_glove_episodes.json"))
    eps = eps.get("episodes", eps) if isinstance(eps, dict) else eps
    return {int(e.get("source_episode_index", i)): (i, e) for i, e in enumerate(eps)}


class TakePoses:
    """Our tile-chain tool pose in the robot base, per head frame of one take."""

    def __init__(self, session, T_base_world, T_body_tool):
        gt = C.WORK / session / "gt"
        wall = np.array([x["wall"] for x in json.load(open(raw_dir(session) / f"{session}_b0587b_ts.json"))])
        cam = {d["k"]: d for d in json.load(open(gt / f"{session}_b0587b_cam_world.json"))["per_frame"]
               if d["rms"] <= RMS_MAX and d["tiles"] >= MIN_TILES}
        z = np.load(gt / "ball_poses.npz")
        ball = {int(k): T for k, T in zip(z["full_k"], G.rt_to_T(z["full_rvec"], z["full_tvec"]))}
        ks = np.array(sorted(set(cam) & set(ball)))
        T_cw = np.array([cam[k]["T_cam_world"] for k in ks], float).reshape(-1, 4, 4)
        T_cb = np.array([ball[k] for k in ks])
        self.t = wall[ks]
        T = T_base_world[None] @ G.inv(T_cw) @ T_cb @ T_body_tool[None]
        self.p = T[:, :3, 3]
        self.q = aligned_quats(T[:, :3, :3])

    def at(self, tq):
        out = np.full((len(tq), 4, 4), np.nan)
        if len(self.t) < 2:
            return out
        i = np.clip(np.searchsorted(self.t, tq), 1, len(self.t) - 1)
        ok = (tq >= self.t[0]) & (tq <= self.t[-1]) & (self.t[i] - self.t[i - 1] <= BRACKET_S)
        if ok.any():
            out[ok] = interp_aligned(tq[ok], self.t, self.q, self.p)
        return out


def load_hhs3():
    import pandas as pd
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(LR / "pilot_glove_HHs3/data/**/*.parquet"),
                                                                  recursive=True))])
    return np.stack(df["action"].values).astype(float), df["episode_index"].values


def ik_flag(Q, fk, tol=LIMIT_TOL):
    """Heuristic 'IK did not reach its target' from the joints alone: a joint within tol of the model's
    range limit, or joint 3 on HHs3's stretched-arm plateau (2.9014 rad, 7.4% of HHs3's steps; the
    shoulder-to-wrist distance there is within 0.3 mm of its maximum, i.e. the target was too far)."""
    lo, hi = fk.model.jnt_range[:6, 0], fk.model.jnt_range[:6, 1]
    return ((Q <= lo + tol) | (Q >= hi - tol)).any(1) | (np.abs(Q[:, 2] - J3_STRAIGHT) < J3_TOL)


def match(P, F, free, t_lo, t_hi):
    """Best start t0 in [t_lo, t_hi] by the median position error of FK vs our pose (free steps)."""
    j = np.arange(len(F)) * SLOW_DT

    def cost(t0):
        O = P.at(t0 + j)
        v = np.isfinite(O[:, 0, 0]) & free
        if v.sum() < MIN_COMPARED:
            return np.inf, int(v.sum()), None
        e = 1000 * np.linalg.norm(F[v, :3, 3] - O[v, :3, 3], axis=1)
        return float(np.median(e)), int(v.sum()), e

    grid = np.arange(t_lo, t_hi + 1e-9, 0.02)
    best = min(grid, key=lambda t: cost(t)[0]) if len(grid) else t_lo
    fine = np.arange(best - 0.03, best + 0.03 + 1e-9, 0.001)
    t0 = min(fine, key=lambda t: cost(t)[0])
    m, n, e = cost(t0)
    return float(t0), m, n, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    from slam.robot_fk import YamFK
    fk = YamFK()
    T_base_world = np.array(json.load(open(C.CALIB / "base_world_v3_20261016.json"))["T_base_world"], float)
    T_body_tool = G.inv(np.array(json.load(open(C.CALIB / "handeye_glove_yosub.json"))["T_flange_body"],
                                 float)[None])[0]
    A, E = load_hhs3()
    rows = [r for r in csv.DictReader(open(SOURCES)) if r["hhs3_episode"] != ""]
    rows.sort(key=lambda r: float(r["hhs3_episode"]))
    assert [int(float(r["hhs3_episode"])) for r in rows] == list(range(200))
    takes, out, missing = {}, [], set()
    for r in rows:
        h, session = int(float(r["hhs3_episode"])), STEM_TO_SESSION[r["stem"]]
        src = int(r["mark_episode"])
        if session not in takes:
            gt = C.WORK / session / "gt"
            have = (gt / "ball_poses.npz").exists() and (gt / f"{session}_b0587b_cam_world.json").exists()
            takes[session] = (TakePoses(session, T_base_world, T_body_tool) if have else None,
                              take_episodes(session))
        P, eps = takes[session]
        te, mark = eps[src]
        assert abs(mark["t_start"] - float(r["t_start"])) < 1e-6, (h, mark["t_start"], r["t_start"])
        q = A[E == h, :6]
        assert len(q) == int(r["len"]), (h, len(q), r["len"])
        row = {"hhs3": h, "session": session, "csv_source_episode": src, "status": r["status"],
               "steps": len(q), "ik_flag": int(ik_flag(q, fk).sum())}
        if P is None:
            missing.add(session)
            row.update(take_episode=te, source_episode=src, mark_t_start=mark["t_start"],
                       mark_t_end=mark["t_end"], t0=mark["t_start"] if r["status"] == "exact" else None,
                       method="mark_start" if r["status"] == "exact" else "unknown", t0_reliable=False,
                       verified=False)
            out.append(row)
            continue
        F, free = fk(q), ~ik_flag(q, fk)
        span = len(q) * SLOW_DT

        def window(m, status):
            if status == "exact":
                return m["t_start"] - 0.3, m["t_start"] + 0.3
            return m["t_start"] - 0.3, m["t_end"] - span + 0.3

        lo, hi = window(mark, r["status"])
        t0, med, n, e = match(P, F, free, lo, hi)
        ok = bool(np.isfinite(med) and med < OK_MM and n >= MIN_COMPARED)
        method = "verified" if ok else None
        if not ok and free.sum() >= MIN_COMPARED:
            # the CSV's length walk can pick the wrong mark; try the neighbouring marks of the take
            by_te = {i: (sv, mv) for sv, (i, mv) in eps.items()}
            cands = []
            for te2 in range(te - SEARCH, te + SEARCH + 1):
                if te2 == te or te2 not in by_te:
                    continue
                src2, m2 = by_te[te2]
                if m2["t_end"] - m2["t_start"] < span - 0.3:
                    continue
                c = match(P, F, free, *window(m2, "trimmed"))
                if np.isfinite(c[1]) and c[1] < OK_MM and c[2] >= MIN_COMPARED:
                    cands.append((c[1], te2, src2, m2, c))
            if cands:
                _, te, src, mark, (t0, med, n, e) = min(cands, key=lambda x: x[0])
                ok, method = True, "remapped"
        if not ok:
            if r["status"] == "exact":
                method, t0 = "mark_start", mark["t_start"]
            else:
                method, t0 = "unknown", None
        row.update(take_episode=te, source_episode=src, mark_t_start=mark["t_start"], mark_t_end=mark["t_end"],
                   t0=t0, t0_minus_mark=None if t0 is None else round(t0 - mark["t_start"], 4),
                   compared=n, median_mm=None if e is None else round(med, 3),
                   p90_mm=None if e is None else round(float(np.percentile(e, 90)), 3),
                   method=method, verified=ok, t0_reliable=method in ("verified", "remapped", "mark_start"))
        out.append(row)
        print(f"HHs3 {h:3d} {session} ep{te:02d} ({r['status']}, {method}): "
              f"t0-mark {row['t0_minus_mark']}, {n} steps, median {med:.2f} mm")
    # one HHs3 episode per stretch of a source episode: overlapping [t0, t0 + span] on the same mark is an error
    seen = {}
    for r in out:
        if r.get("t0") is None:
            continue
        key = (r["session"], r["take_episode"])
        span = (r["t0"], r["t0"] + r["steps"] * SLOW_DT)
        for other, osp in seen.get(key, []):
            if span[0] < osp[1] - 1e-3 and osp[0] < span[1] - 1e-3:
                raise SystemExit(f"HHs3 {r['hhs3']} overlaps HHs3 {other} on {key}")
        seen.setdefault(key, []).append((r["hhs3"], span))
    import collections
    summary = {"episodes": len(out), "methods": dict(collections.Counter(r["method"] for r in out)),
               "remapped": [(r["hhs3"], r["session"], r["csv_source_episode"], r["source_episode"], r["median_mm"])
                            for r in out if r["method"] == "remapped"],
               "unverified": [(r["hhs3"], r["session"], r["status"], r["method"], r.get("compared"),
                               r.get("median_mm"), r["ik_flag"], r["steps"]) for r in out if not r["verified"]],
               "sessions_without_ground_truth": sorted(missing),
               "params": {"rms_max_px": RMS_MAX, "bracket_s": BRACKET_S, "ok_mm": OK_MM,
                          "min_compared": MIN_COMPARED, "min_tiles": MIN_TILES, "limit_tol_rad": LIMIT_TOL,
                          "j3_straight": J3_STRAIGHT, "slow_dt": SLOW_DT},
               "source": "calib/pilot_glove_HHs3_sources.csv (Yosub, 2026-11-10)"}
    json.dump({"summary": summary, "episodes": out}, open(a.out, "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
