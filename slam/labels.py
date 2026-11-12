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
       Scale: --scale <spec> from slam.scale (none | tiles = oracle | A = static ball |
       B[:model] = metric depth + ball | fallback chains like "A,B").
       Gripper: --gripper head (default since 2026-11-12) = <work>/<session>/gt/gripper_head.npz,
       the head camera's width (slam.head_width: the paper's tail/base estimators); --gripper
       wrist = gt/gripper_wrist.npz (slam.wrist_width; cross-check only, no wrist-camera data in
       the algorithm); --gripper dataset = gt/gripper.npz (widths of Yosub's built glove
       dataset, slam.glove_width). Linearly interpolated; a step is a gripper gap when no width sample lies within
       0.12 s, and coverage uses pose AND gripper gaps (build_dataset: min of both).
       -> <segment>/labels/<name>.npz: t, T_ref_tool (N,4,4), gap, coverage, keep, meta
          <name> = <ref> with the oracle (tiles) scale, else <ref>@<scale spec>, e.g. E3@A

check  End-to-end label error on the training timeline: the relative chunk
       tool_t->tool_t+j from a SLAM label file vs from the tile label file, for every
       anchor t where both are gap-free, j = 1..100 (6.7 s at 15 fps).
       -> <work>/<session>/eval/labels_<ref>.json
       chunk_labels(): the same errors averaged over each anchor's chunk j = 1..H (used by
       the experiment framework, slam.pipeline.impl_analysis).

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
from slam.evaluate import load_segment, load_tool_offset

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


GRIPPER_FILES = {"head": "gripper_head.npz", "wrist": "gripper_wrist.npz", "dataset": "gripper.npz"}


def load_gripper(session, source="head"):
    """{episode: (wall times, command)} from the source's gt file; {} if it does not exist."""
    if source not in GRIPPER_FILES:
        raise ValueError(f"gripper source {source!r}: one of {sorted(GRIPPER_FILES)}")
    p = C.gt_dir(session) / GRIPPER_FILES[source]
    if not p.exists():
        return {}
    z = np.load(p)
    return {int(k[1:-2]): (z[k], z[k[:-2] + "_v"]) for k in z.files if k.endswith("_t")}


def label_name(ref, scale_mode):
    return ref if ref == "tiles" or scale_mode == "tiles" else f"{ref}@{scale_mode}"


def build_segment(seg, ref, scale_mode, T_bt, grip=None, scale=None):
    """scale: None = slam.scale.estimate(seg, ref, scale_mode); or (s, method label) computed
    elsewhere (s None/NaN = no scale for this segment). The file is named after scale_mode."""
    S = load_segment(seg)
    ep = json.load(open(seg / "frames.json"))["episode"]
    meta = {"ref": ref, "scale_mode": scale_mode, "episode": ep["episode_index"]}
    if ref == "tiles":
        T_ref_cam = tile_world_cam(S)
    else:
        z = np.load(seg / "slam" / f"{ref}.npz")
        T_ref_cam = z["T_slam_cam"].astype(float).copy()
        if scale is None:
            from slam.scale import estimate
            r = estimate(seg, ref, scale_mode)
            s = float(r["s"]) if r.get("ok") else float("nan")
            meta["scale_method_used"] = r.get("method")
        else:
            s = float("nan") if scale[0] is None else float(scale[0])
            meta["scale_method_used"] = scale[1]
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
                 "gripper": "gt width file (labels gripper source)" if gser is not None else
                 ("no width labels for this episode" if grip else "no gripper widths: pose-only coverage")})
    (seg / "labels").mkdir(exist_ok=True)
    np.savez(seg / "labels" / f"{label_name(ref, scale_mode)}.npz", t=out["t"], T_ref_tool=out["T_ref_tool"], gap=out["gap"],
             gripper=out["gripper"], gripper_gap=out["gripper_gap"], coverage=out["coverage"],
             keep=out["keep"], meta=json.dumps(meta))
    return meta


class RefPoses:
    """Per-step tool poses from `build` outputs, for scripts/build_dataset.py --ref-poses.

    lookup(episode_index, t) -> (tvec (3,), rvec (3,), is_gap): the pose at time t, interpolated
    between the two 15 fps label steps around it (is_gap if either is a gap), or None if the
    episode has no kept label file. Interpolation matters with build_dataset --slow S: the
    timeline is then sampled at 15 * S Hz, and rounding to the 15 fps grid repeated each label
    S times (a stair-step); until 2026-11-10 the nearest step was returned."""

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
        tt = z["t"]
        if not tt[0] - 1e-6 <= t <= tt[-1] + 1e-6:
            return np.full(3, np.nan), np.full(3, np.nan), True
        i = int(np.clip(np.searchsorted(tt, t), 1, len(tt) - 1)) if len(tt) > 1 else 0
        j = max(i - 1, 0)
        T = interp_poses(np.array([t]), tt[[j, i]], z["T_ref_tool"][[j, i]])[0] if i != j else z["T_ref_tool"][i]
        q = G.R_to_quat(T[:3, :3][None])[0]
        if q[3] < 0:
            q = -q
        ang = 2 * np.arctan2(np.linalg.norm(q[:3]), q[3])
        rv = q[:3] / max(np.linalg.norm(q[:3]), 1e-12) * ang
        return T[:3, 3].copy(), rv, bool(z["gap"][i] or z["gap"][j])


def cmd_build(a):
    T_bt = load_tool_offset(a.session)
    grip = load_gripper(a.session, a.gripper)
    print(f"gripper widths for {len(grip)} episodes" if grip else "no gripper widths: pose-only coverage")
    kept = 0
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        m = build_segment(seg, a.ref, a.scale, T_bt, grip)
        kept += m["keep"]
        extra = f", scale {m['scale']:.3f}" if "scale" in m else ""
        print(f"{seg.name}: {m['n_steps']} steps, coverage {100 * m['coverage']:.0f}%, "
              f"{'kept' if m['keep'] else 'DROPPED'}{extra}{', ' + m['skipped'] if 'skipped' in m else ''}")
    print(f"{label_name(a.ref, a.scale)}: {kept} episodes kept")


STEPS = (1, 2, 4, 8, 15, 30, 60, 100)


def anchor_errors(session, name, horizon=100, exclude=()):
    """The anchors of check_labels: yields (segment, anchor index, [(j, pos_mm, rot_deg), ...])
    for every anchor t where label file <name> and the tile labels are both gap-free, with the
    error of the relative chunk tool_t->tool_t+j (vs the tile labels) at every step j = 1..horizon
    that check_labels counts (not padded past the end, gap-free at t+j)."""
    H = horizon
    for seg in sorted(C.segments_dir(session).glob("ep[0-9][0-9]")):
        if seg.name in exclude:
            continue
        p, g = seg / "labels" / f"{name}.npz", seg / "labels" / "tiles.npz"
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
            e = []
            for j in range(1, H + 1):
                if pad[j - 1] or not ok[min(t + j, len(ok) - 1)]:
                    continue
                d = G.inv(rb[j - 1][None])[0] @ ra[j - 1]
                e.append((j, 1000 * np.linalg.norm(ra[j - 1][:3, 3] - rb[j - 1][:3, 3]),
                          G.rot_angle_deg(d[:3, :3][None])[0]))
            yield seg.name, int(t), e


def step_stats(anchors, name, horizon=100, exclude=(), steps=STEPS):
    """check_labels' summary of anchor_errors() output: per step j in `steps`, error statistics
    over the anchors that count step j."""
    H = horizon
    errs = {j: [] for j in range(1, H + 1)}
    n_anchor = 0
    for _, _, e in anchors:
        n_anchor += 1
        for j, pos, rot in e:
            errs[j].append((pos, rot))
    res = {"ref": name, "anchors": n_anchor, "excluded": sorted(exclude), "by_step": {}}
    for j in steps:
        if j > H or not errs[j]:
            continue
        e = np.array(errs[j])
        res["by_step"][j] = {"dt_s": j / FPS, "n": len(e), "pos_mm_median": float(np.median(e[:, 0])),
                             "pos_mm_p90": float(np.percentile(e[:, 0], 90)),
                             "rot_deg_median": float(np.median(e[:, 1])),
                             "rot_deg_p90": float(np.percentile(e[:, 1], 90))}
    return res


def check_labels(session, name, horizon=100, exclude=(), steps=STEPS):
    """Relative-chunk error of label file <name> vs the tile labels, per step j (dt = j/15 s),
    over anchors where both are gap-free; segments in `exclude` (e.g. "ep12") are skipped."""
    return step_stats(anchor_errors(session, name, horizon, exclude), name, horizon, exclude, steps)


CHUNK_KEYS = ("anchors", "pos_mm_mean", "pos_mm_median", "pos_mm_p90", "rot_deg_mean", "rot_deg_median",
              "rot_deg_p90", "pooled_pos_mm_mean", "pooled_rot_deg_mean")


def chunk_stats(anchors, chunk_H):
    """Chunk-length label error from anchor_errors() output (computed with horizon >= max(chunk_H)):
    for each H, per anchor the mean error over its counted steps j = 1..H (anchors with no
    counted step are left out), then mean / median / p90 over anchors; pooled = mean over all
    (anchor, j) pairs. -> {str(H): {CHUNK_KEYS}}."""
    anchors = [e for _, _, e in anchors]
    out = {}
    for H in chunk_H:
        per, pooled = [], []
        for e in anchors:
            a = np.array([(pos, rot) for j, pos, rot in e if j <= H]).reshape(-1, 2)
            if len(a):
                per.append(a.mean(0))
                pooled.append(a)
        r = dict.fromkeys(CHUNK_KEYS)
        r["anchors"] = len(per)
        if per:
            per, pooled = np.array(per), np.concatenate(pooled)
            for c, q in ((0, "pos_mm"), (1, "rot_deg")):
                r.update({f"{q}_mean": float(per[:, c].mean()), f"{q}_median": float(np.median(per[:, c])),
                          f"{q}_p90": float(np.percentile(per[:, c], 90)),
                          f"pooled_{q}_mean": float(pooled[:, c].mean())})
        out[str(H)] = r
    return out


def chunk_labels(session, name, chunk_H, exclude=()):
    """chunk_stats() of label file <name> vs the tile labels."""
    return chunk_stats(anchor_errors(session, name, max(chunk_H), exclude), chunk_H)


def cmd_check(a):
    name = label_name(a.ref, a.scale)
    res = check_labels(a.session, name, a.horizon)
    dst = C.WORK / a.session / "eval"
    dst.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(dst / f"labels_{name}.json", "w"), indent=1)
    print(f"{name} vs tiles, {res['anchors']} anchors")
    print("dt[s]   n     pos mm (med/p90)   rot deg (med/p90)")
    for j, r in res["by_step"].items():
        print(f"{r['dt_s']:5.2f} {r['n']:6d}   {r['pos_mm_median']:6.1f} / {r['pos_mm_p90']:6.1f}"
              f"     {r['rot_deg_median']:5.2f} / {r['rot_deg_p90']:5.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "check"])
    ap.add_argument("--session", required=True)
    ap.add_argument("--ref", required=True, help="'tiles' or a SLAM run name (E1, E2, E3)")
    ap.add_argument("--scale", default="tiles", help="slam.scale spec: none|tiles|A|B[:model]|A,B ...")
    ap.add_argument("--horizon", type=int, default=100)
    ap.add_argument("--gripper", default="head", choices=sorted(GRIPPER_FILES))
    a = ap.parse_args()
    {"build": cmd_build, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
