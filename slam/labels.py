#!/usr/bin/env python3
"""Per-episode tool poses on the training timeline, and their end-to-end check.

build  For each segment, the tool (virtual flange, build_dataset's IK target frame) is
       expressed in a reference frame at every frame with a ball pose ('full' variant):
         --ref <run>   ref = the segment's SLAM frame:  slam->tool = s.(slam->cam) . (cam->body) . (body->tool)
         --ref tiles   ref = the tile world:            world->tool, tile head poses with
                       build_dataset's --cam-world gates (>= 2 tiles, rms <= 5 px, bridge <= 0.5 s)
       then resampled like build_dataset (glove mode, --episode-marks): 15 fps over the
       marked episode [t_start, t_end] (the take's label series spans every episode, so
       build_dataset's clip to it is a no-op; skipped if < 1 s), componentwise
       quaternion interpolation, a step is a gap when no sample lies within 0.12 s, and
       episodes below 70% coverage are dropped. SLAM frames count as gaps only where
       the run has no pose (DROID returns every frame).
       Scale (out of scope for now): --scale tiles = per-segment Umeyama fit to the tile
       head poses (oracle, for evaluation); --scale none = raw SLAM units.
       Gripper: the wrist-camera width labels from <work>/<session>/gt/gripper.npz
       (slam.glove_width: Yosub's built glove dataset, episodes matched and verified),
       linearly interpolated; a step is a gripper gap when no width sample lies within
       0.12 s, and coverage uses pose AND gripper gaps (build_dataset: min of both).
       -> <segment>/labels/<ref>.npz: t, T_ref_tool (N,4,4), gap, coverage, keep, meta

check  End-to-end label error on the training timeline: the relative chunk
       tool_t->tool_t+j from a SLAM label file vs from the tile label file, for every
       anchor t where both are gap-free, j = 1..100 (6.7 s at 15 fps).
       -> <work>/<session>/eval/labels_<ref>.json

  python -m slam.labels build --session yam_glove7 --ref tiles
  python -m slam.labels build --session yam_glove7 --ref E3
  python -m slam.labels check --session yam_glove7 --ref E3
"""
import argparse
import json

import numpy as np

from slam import config as C
from slam import geometry as G
from slam import relative as Rl
from slam.evaluate import load_segment, load_tool_offset, segment_scale

FPS, LABEL_TOL, MIN_COVERAGE, BRIDGE, MIN_EPISODE = 15.0, 0.12, 0.7, 0.5, 1.0


def interp_poses(tq, ts, T):
    """build_dataset.interp_pose on 4x4s: linear translation, sign-aligned componentwise
    quaternion blend, normalised."""
    q = G.R_to_quat(T[:, :3, :3])
    for i in range(1, len(q)):
        if q[i] @ q[i - 1] < 0:
            q[i] = -q[i]
    qi = np.stack([np.interp(tq, ts, q[:, c]) for c in range(4)], 1)
    qi /= np.linalg.norm(qi, axis=1, keepdims=True)
    out = np.tile(np.eye(4), (len(tq), 1, 1))
    out[:, :3, :3] = G.quat_to_R(qi)
    out[:, :3, 3] = np.stack([np.interp(tq, ts, T[:, :3, 3][:, c]) for c in range(3)], 1)
    return out


def tile_world_cam(S):
    """world->cam per frame with build_dataset's --cam-world gates and bridging (NaN = dropped)."""
    good = np.isfinite(S["T_wc"][:, 0, 0]) & S["strict"]
    gi = np.where(good)[0]
    T_wc = np.full_like(S["T_wc"], np.nan)
    if len(gi) == 0:
        return T_wc
    T_wc[gi] = S["T_wc"][gi]
    for i in np.where(~good)[0]:
        j = np.searchsorted(gi, i)
        if 0 < j < len(gi) and S["wall"][gi[j]] - S["wall"][gi[j - 1]] <= BRIDGE:
            T_wc[i] = interp_poses(S["wall"][i:i + 1], S["wall"][gi[[j - 1, j]]], S["T_wc"][gi[[j - 1, j]]])[0]
    return T_wc


def load_gripper(session):
    p = C.gt_dir(session) / "gripper.npz"
    if not p.exists():
        return {}
    z = np.load(p)
    return {int(k[1:-2]): (z[k], z[k[:-2] + "_v"]) for k in z.files if k.endswith("_t")}


def build_segment(seg, ref, scale_mode, T_bt, grip=None):
    S = load_segment(seg)
    ep = json.load(open(seg / "frames.json"))["episode"]
    meta = {"ref": ref, "scale_mode": scale_mode, "episode": ep["episode_index"]}
    if ref == "tiles":
        T_ref_cam = tile_world_cam(S)
    else:
        z = np.load(seg / "slam" / f"{ref}.npz")
        T_ref_cam = z["T_slam_cam"].astype(float).copy()
        s = 1.0
        if scale_mode == "tiles":
            s, res = segment_scale(S, T_ref_cam)
            meta["align_res_mm"] = 1000 * res
        meta["scale"] = s
        if not np.isfinite(s):
            T_ref_cam[:] = np.nan
        else:
            T_ref_cam[:, :3, 3] *= s
    have = np.isfinite(S["T_cb"][:, 0, 0]) & np.isfinite(T_ref_cam[:, 0, 0])
    ts = S["wall"][have]
    T_samples = T_ref_cam[have] @ S["T_cb"][have] @ T_bt
    out = {"t": np.zeros(0), "T_ref_tool": np.zeros((0, 4, 4)), "gap": np.zeros(0, bool),
           "gripper": np.zeros(0), "gripper_gap": np.zeros(0, bool), "coverage": 0.0, "keep": False}
    gser = (grip or {}).get(ep["episode_index"])
    if len(ts) >= 2:
        t0, t1 = ep["t_start"], ep["t_end"]
        if t1 - t0 >= MIN_EPISODE:
            tq = np.arange(t0, t1, 1.0 / FPS)
            near = np.abs(tq[:, None] - ts[None]).min(1)
            gap = near > LABEL_TOL
            if gser is not None:
                gw = np.interp(tq, gser[0], gser[1])
                ggap = np.abs(tq[:, None] - gser[0][None]).min(1) > LABEL_TOL
            else:
                gw, ggap = np.full(len(tq), np.nan), np.ones(len(tq), bool)
            cov = min(1.0 - gap.mean(), 1.0 - ggap.mean()) if grip else 1.0 - gap.mean()
            out = {"t": tq, "T_ref_tool": interp_poses(tq, ts, T_samples), "gap": gap,
                   "gripper": gw, "gripper_gap": ggap, "coverage": float(cov),
                   "keep": bool(cov >= MIN_COVERAGE)}
        else:
            meta["skipped"] = f"episode only {t1 - t0:.2f} s long"
    meta.update({"coverage": out["coverage"], "keep": out["keep"], "n_steps": len(out["t"]),
                 "gripper": "gt/gripper.npz" if gser is not None else
                 ("no width labels for this episode" if grip else "no gt/gripper.npz: pose-only coverage")})
    (seg / "labels").mkdir(exist_ok=True)
    np.savez(seg / "labels" / f"{ref}.npz", t=out["t"], T_ref_tool=out["T_ref_tool"], gap=out["gap"],
             gripper=out["gripper"], gripper_gap=out["gripper_gap"], coverage=out["coverage"],
             keep=out["keep"], meta=json.dumps(meta))
    return meta


class RefPoses:
    """Per-step tool poses from `build` outputs, for scripts/build_dataset.py --ref-poses.

    lookup(episode_index, t) -> (tvec (3,), rvec (3,), is_gap) for the step whose time is
    t on the episode's 15 fps grid, or None if the episode has no kept label file."""

    def __init__(self, segments_dir, run):
        from pathlib import Path
        self.dir, self.run, self.cache = Path(segments_dir), run, {}

    def episode(self, ep):
        if ep not in self.cache:
            p = self.dir / f"ep{ep:02d}" / "labels" / f"{self.run}.npz"
            z = np.load(p) if p.exists() else None
            self.cache[ep] = z if z is not None and bool(z["keep"]) and len(z["t"]) else None
        return self.cache[ep]

    def lookup(self, ep, t):
        z = self.episode(ep)
        if z is None:
            return None
        i = int(round((t - z["t"][0]) * FPS))
        if not 0 <= i < len(z["t"]) or abs(z["t"][i] - t) > 0.5 / FPS:
            return np.full(3, np.nan), np.full(3, np.nan), True
        T = z["T_ref_tool"][i]
        q = G.R_to_quat(T[:3, :3])[0]
        ang = 2 * np.arctan2(np.linalg.norm(q[:3]), q[3])
        rv = q[:3] / max(np.linalg.norm(q[:3]), 1e-12) * ang
        return T[:3, 3].copy(), rv, bool(z["gap"][i])


def cmd_build(a):
    T_bt = load_tool_offset(a.session)
    grip = load_gripper(a.session)
    print(f"gripper widths for {len(grip)} episodes" if grip else "no gripper widths: pose-only coverage")
    kept = 0
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        m = build_segment(seg, a.ref, a.scale, T_bt, grip)
        kept += m["keep"]
        extra = f", scale {m['scale']:.3f}" if "scale" in m else ""
        print(f"{seg.name}: {m['n_steps']} steps, coverage {100 * m['coverage']:.0f}%, "
              f"{'kept' if m['keep'] else 'DROPPED'}{extra}{', ' + m['skipped'] if 'skipped' in m else ''}")
    print(f"{a.ref}: {kept} episodes kept")


def cmd_check(a):
    H = a.horizon
    errs = {j: [] for j in range(1, H + 1)}
    n_anchor = 0
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        p, g = seg / "labels" / f"{a.ref}.npz", seg / "labels" / "tiles.npz"
        if not (p.exists() and g.exists()):
            continue
        A, B = np.load(p), np.load(g)
        if not (A["keep"] and B["keep"]) or len(A["t"]) == 0:
            continue
        # common timeline: both start at max(t_start, first sample) on a 1/15 s grid
        ta, tb = A["t"], B["t"]
        ia = {round(x * FPS): i for i, x in enumerate(ta)}
        common = [(ia[round(x * FPS)], j) for j, x in enumerate(tb) if round(x * FPS) in ia]
        if len(common) < 2:
            continue
        ca, cb = map(np.array, zip(*common))
        TA, TB = A["T_ref_tool"][ca], B["T_ref_tool"][cb]
        ok = ~A["gap"][ca] & ~B["gap"][cb]
        for t in np.where(ok)[0]:
            ra, pad = Rl.relative_chunk(TA, t, H)
            rb, _ = Rl.relative_chunk(TB, t, H)
            n_anchor += 1
            for j in range(1, H + 1):
                if pad[j - 1] or not ok[min(t + j, len(ok) - 1)]:
                    continue
                d = G.inv(rb[j - 1][None])[0] @ ra[j - 1]
                errs[j].append((1000 * np.linalg.norm(ra[j - 1][:3, 3] - rb[j - 1][:3, 3]),
                                G.rot_angle_deg(d[:3, :3][None])[0]))
    res = {"ref": a.ref, "anchors": n_anchor, "by_step": {}}
    for j in (1, 2, 4, 8, 15, 30, 60, 100):
        if j > H or not errs[j]:
            continue
        e = np.array(errs[j])
        res["by_step"][j] = {"dt_s": j / FPS, "n": len(e), "pos_mm_median": float(np.median(e[:, 0])),
                             "pos_mm_p90": float(np.percentile(e[:, 0], 90)),
                             "rot_deg_median": float(np.median(e[:, 1])),
                             "rot_deg_p90": float(np.percentile(e[:, 1], 90))}
    dst = C.WORK / a.session / "eval"
    dst.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(dst / f"labels_{a.ref}.json", "w"), indent=1)
    print(f"{a.ref} vs tiles, {n_anchor} anchors")
    print("dt[s]   n     pos mm (med/p90)   rot deg (med/p90)")
    for j, r in res["by_step"].items():
        print(f"{r['dt_s']:5.2f} {r['n']:6d}   {r['pos_mm_median']:6.1f} / {r['pos_mm_p90']:6.1f}"
              f"     {r['rot_deg_median']:5.2f} / {r['rot_deg_p90']:5.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "check"])
    ap.add_argument("--session", required=True)
    ap.add_argument("--ref", required=True, help="'tiles' or a SLAM run name (E1, E2, E3)")
    ap.add_argument("--scale", default="tiles", choices=["tiles", "none"])
    ap.add_argument("--horizon", type=int, default=100)
    a = ap.parse_args()
    {"build": cmd_build, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
