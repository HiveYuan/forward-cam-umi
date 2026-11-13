"""Error decomposition step (venv, CPU): which part of the SLAM head motion limits the tool labels.
Called as run_error_decomp(job) by the worker after evaluate, on the analysis view
(slam.config.WORK = <work>/runs/<exp>/<variant>/view; job.out_dir holds scale_<run>.json etc.).

For every label pair (t, t+j) on the 15 fps training timeline the head motion cam_t->cam_t+j is
rebuilt from one rotation source and one scale, the rest kept:

  rotation      SLAM:  rotation of rel_slam = (slam->cam_t)^-1 (slam->cam_t+j)
                tile:  rotation of rel_tile = (world->cam_t)^-1 (world->cam_t+j), tile head poses
  translation   s * (translation of rel_slam), always SLAM's (unscaled) translation, with
                s = the run's configured scale (scale_<run>.json rows, "s") or the tile oracle
                ("oracle_s", per-segment Umeyama fit of the camera centres)

  combination           rotation  scale        stands for
  R_slam+s_configured   SLAM      configured   the real pipeline (= labels_<run>@<label>.json)
  R_slam+s_oracle       SLAM      oracle       perfect global scale (~ stereo) (= labels_<run>.json)
  R_tile+s_configured   tile      configured   perfect rotation (~ IMU)
  R_tile+s_oracle       tile      oracle       both

tool label = (cam_t->tool_t)^-1 [R | s t] (cam_t+j->tool_t+j) (ball poses, tool offset), compared
with the tile label (GT, rel_tile) exactly like slam.labels.check_labels: the label series are
slam.labels.build_segment outputs (episode grid, interp_poses, tile_world_cam gates and bridging,
0.12 s gap tolerance, 70% coverage incl. gripper gaps), written into a scratch copy of each segment;
anchors and counted steps are those of slam.labels.anchor_errors (both label series gap-free at t
and t+j, tile GT at both ends). cam_t->tool_t on the grid is B(t) = C(t)^-1 X(t), with X the SLAM
label (tool) series and C the SLAM camera interpolated over the same samples, so with the SLAM
rotation the label is X(t)^-1 X(t+j): combinations 1 and 2 are computed exactly as slam.labels does
(bit-identical to labels_<run>@<label>.json / labels_<run>.json), combinations 3 and 4 replace the
rotation block of C(t)^-1 C(t+j) by the tile camera's (world->cam over the tile label's samples).
"checks" records both: the decomposition with the SLAM rotation vs the exact labels path (float
noise), and the step / chunk numbers vs the labels step's files in job.out_dir.

Coupling (why the tile rotation alone can make the labels worse): in cam_t the tool after the head
motion is at R b + t, so the label position error of the SLAM motion is about |dR b + dt|, with
dR b = (R_slam - R_tile) b from the rotation error and dt = s t_slam - t_tile from the translation
error. The tile-rotation combinations keep only dt. When SLAM's rotation and translation errors
compensate each other at the tool's depth (cosine of dR b and dt near -1), |dt| is larger than
|dR b + dt|.

Per combination: by_step (slam.labels.step_stats), chunk (slam.labels.chunk_stats: per anchor the
mean over its counted steps j <= H, then mean / median / p90 over anchors; pooled), and the same
per head rotation speed bin (speed = tile rotation angle between the anchor time and speed_window_s
later, divided by speed_window_s; both ends need a tile pose within 0.12 s, else the anchor is in no
bin: "unknown").

Writes errdecomp_<run>.json and errdecomp_<run>.md into job.out_dir:
  {"run", "scale_label", "gripper", "params",
   "combos": {name: {"rotation", "scale", "anchors", "by_step": {j: {dt_s, n, pos_mm_median, pos_mm_p90,
                     rot_deg_median, rot_deg_p90}}, "chunk": {H: {slam.labels.CHUNK_KEYS}},
                     "by_speed": {bin: {"anchors", "by_step", "chunk"}}}},
   "anchors": {"configured": n, "oracle": n},
   "coupling": {"configured"|"oracle": {"by_step": {j: {n, rot_part_mm_median, rot_part_mm_p90,
                trans_part_mm_median, trans_part_mm_p90, cos_median}}}}   (segment_anchors),
   "speed": {"window_s", "bins_deg_s", "anchors": {"configured"|"oracle": {bin: n, "unknown": n}}},
   "segments": {seg: {"s", "oracle_s", "flagged", "kept": {"tiles", "configured", "oracle"},
                      "anchors": {"configured", "oracle"}}},
   "checks": {"decomposition": {"configured"|"oracle": {"pairs", "max_pos_mm", "max_rot_frobenius"}},
              "labels_files": {combo: {"file", "identical", "anchors", "by_step_identical",
                                       "chunk_identical", "max_abs_diff", "compared"} | null}}}
"""
import json
import os
import shutil
from pathlib import Path

import numpy as np

from slam import config as C

COMBOS = (("R_slam+s_configured", "slam", "configured"),
          ("R_slam+s_oracle", "slam", "oracle"),
          ("R_tile+s_configured", "tile", "configured"),
          ("R_tile+s_oracle", "tile", "oracle"))
SCALES = ("configured", "oracle")
SEG_FILES = ("frames.json", "gt.npz", "tiles.npz")       # slam.evaluate.load_segment inputs (tiles optional)
UNKNOWN = "unknown"


# ---------------------------------------------------------------------- helpers
def _clean(o):
    from slam.pipeline.impl_analysis import _clean as clean
    return clean(o)


def speed_bins(edges):
    """Bin edges [0, 10, 30] -> [("0-10", 0, 10), ("10-30", 10, 30), ("30+", 30, inf)]."""
    e = [float(x) for x in edges]
    if not e or any(b <= a for a, b in zip(e, e[1:])):
        raise ValueError(f"error_decomp.speed_bins_deg_s: increasing bin edges, got {edges}")
    out = []
    for i, lo in enumerate(e):
        hi = e[i + 1] if i + 1 < len(e) else float("inf")
        out.append((f"{lo:g}-{hi:g}" if np.isfinite(hi) else f"{lo:g}+", lo, hi))
    return out


def bin_of(speed, bins):
    """Name of the bin holding speed [deg/s] (None: unknown or below the first edge)."""
    if speed is None or not np.isfinite(speed):
        return None
    return next((name for name, lo, hi in bins if lo <= speed < hi), None)


def _link(src, dst):
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    os.symlink(Path(src).resolve(), dst)


def scratch_segment(src, dst, run):
    """dst = a fresh segment directory holding slam.labels.build_segment's inputs of `src`
    (symlinks: frames.json, gt.npz, tiles.npz, slam/<run>.npz); build_segment writes labels/ there."""
    src, dst = Path(src), Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "slam").mkdir(parents=True)
    for f in SEG_FILES:
        if (src / f).exists():
            _link(src / f, dst / f)
    if (src / "slam" / f"{run}.npz").exists():
        _link(src / "slam" / f"{run}.npz", dst / "slam" / f"{run}.npz")
    return dst


def build_label(sd, ref, scale_mode, T_bt, grip, scale=None):
    """slam.labels.build_segment into the scratch segment sd -> the label file as a dict."""
    from slam import labels as L
    meta = L.build_segment(sd, ref, scale_mode, T_bt, grip, scale=scale)
    z = np.load(sd / "labels" / f"{L.label_name(ref, scale_mode)}.npz")
    return {"t": z["t"], "T": z["T_ref_tool"], "gap": z["gap"], "keep": bool(z["keep"]), "meta": meta}


def scaled_slam_cam(T_slam_cam, s):
    """slam->cam with the translation scaled by s, as slam.labels.build_segment does (NaN: no scale)."""
    T = np.asarray(T_slam_cam).astype(float).copy()
    s = float("nan") if s is None else float(s)
    if not np.isfinite(s):
        T[:] = np.nan
    else:
        T[:, :3, 3] *= s
    return T


def cam_series(S, T_ref_cam, tq):
    """ref->cam on the label grid tq, interpolated (slam.labels.interp_poses) over the samples
    build_segment uses for the tool: frames with a ball pose and a reference pose."""
    from slam import labels as L
    have = np.isfinite(S["T_cb"][:, 0, 0]) & np.isfinite(T_ref_cam[:, 0, 0])
    if len(tq) == 0 or have.sum() < 2:
        return np.full((len(tq), 4, 4), np.nan)
    return L.interp_poses(np.asarray(tq), S["wall"][have], T_ref_cam[have])


def step_errors(ra, rb, pad, ok, t, H):
    """[(j, pos_mm, rot_deg)] of relative chunks ra vs rb: slam.labels.anchor_errors' inner loop
    (same operations, so the numbers are bit-identical for the same chunks)."""
    from slam import geometry as G
    e = []
    for j in range(1, H + 1):
        if pad[j - 1] or not ok[min(t + j, len(ok) - 1)]:
            continue
        d = G.inv(rb[j - 1][None])[0] @ ra[j - 1]
        e.append((j, 1000 * np.linalg.norm(ra[j - 1][:3, 3] - rb[j - 1][:3, 3]),
                  G.rot_angle_deg(d[:3, :3][None])[0]))
    return e


def segment_anchors(lab, tile, cam, cam_tile, H):
    """Anchors of one segment for one scale, mirroring slam.labels.anchor_errors.
    lab: SLAM label dict (t, T, gap, keep) built with the scale; tile: tile label dict; cam: SLAM
    camera (scaled like lab) on lab's grid; cam_tile: tile camera on tile's grid.
    -> ([(t index, anchor time, errors with the SLAM rotation, errors with the tile rotation,
          coupling [(j, |dR b| mm, |dt| mm, cos(dR b, dt))])],
        {"pairs", "max_pos_mm", "max_rot_frobenius"}: decomposition with the SLAM rotation vs the
        exact label chunk, over the counted steps).
    Coupling, in cam_t at the counted steps: the tool position after the head motion is R b + t
    (b = cam_t+j->tool_t+j); dR b = (R_slam - R_tile) b is the part of the label position error
    from the SLAM rotation, dt = t_slam (scaled) - t_tile the part from its translation."""
    from slam import geometry as G
    from slam import labels as L
    from slam import relative as Rl
    chk = {"pairs": 0, "max_pos_mm": 0.0, "max_rot_frobenius": 0.0}
    if not (lab["keep"] and tile["keep"]) or len(lab["t"]) == 0:
        return [], chk
    ta, tb = lab["t"], tile["t"]
    ia = {round(x * L.FPS): i for i, x in enumerate(ta)}
    common = [(ia[round(x * L.FPS)], j) for j, x in enumerate(tb) if round(x * L.FPS) in ia]
    if len(common) < 2:
        return [], chk
    ca, cb = map(np.array, zip(*common))
    TA, TB, CA, CW = lab["T"][ca], tile["T"][cb], cam[ca], cam_tile[cb]
    ok = ~lab["gap"][ca] & ~tile["gap"][cb]
    BA = G.inv(CA) @ TA                                   # cam_t -> tool_t on the grid (SLAM side)
    N = len(TA)
    out = []
    for t in np.where(ok)[0]:
        ra, pad = Rl.relative_chunk(TA, t, H)             # SLAM rotation: the slam.labels chunk
        rb, _ = Rl.relative_chunk(TB, t, H)
        idx = np.minimum(np.arange(t + 1, t + 1 + H), N - 1)
        rel = G.inv(CA[t][None]) @ CA[idx]                # SLAM head motion, scaled
        rel_t = rel.copy()
        rel_w = G.inv(CW[t][None]) @ CW[idx]              # tile head motion
        rel_t[:, :3, :3] = rel_w[:, :3, :3]               # tile head rotation
        Binv = G.inv(BA[t][None])
        rt = Binv @ rel_t @ BA[idx]
        e_slam = step_errors(ra, rb, pad, ok, t, H)
        e_tile = step_errors(rt, rb, pad, ok, t, H)
        coup = []
        if e_slam:
            k = np.array([j - 1 for j, _, _ in e_slam])
            dRb = ((rel[k, :3, :3] - rel_w[k, :3, :3]) @ BA[idx[k], :3, 3][..., None])[..., 0]
            dt = rel[k, :3, 3] - rel_w[k, :3, 3]
            nr, nt = np.linalg.norm(dRb, axis=1), np.linalg.norm(dt, axis=1)
            cos = np.where((nr > 1e-12) & (nt > 1e-12), (dRb * dt).sum(1) / np.maximum(nr * nt, 1e-300), np.nan)
            coup = list(zip((k + 1).tolist(), (1000 * nr).tolist(), (1000 * nt).tolist(), cos.tolist()))
            rd = Binv @ rel[k] @ BA[idx[k]]
            chk["pairs"] += len(k)
            chk["max_pos_mm"] = max(chk["max_pos_mm"],
                                    float(1000 * np.abs(rd[:, :3, 3] - ra[k, :3, 3]).max()))
            chk["max_rot_frobenius"] = max(chk["max_rot_frobenius"],
                                           float(np.linalg.norm(rd[:, :3, :3] - ra[k, :3, :3], axis=(1, 2)).max()))
        out.append((int(t), float(tb[cb[t]]), e_slam, e_tile, coup))
    return out, chk


def head_speeds(S, times, window):
    """Tile head rotation speed [deg/s] at each time: rotation angle between t and t + window of
    the tile head poses (slam.labels.tile_world_cam: gated, bridged; interp_poses), / window.
    NaN where either end has no tile pose within slam.labels.LABEL_TOL."""
    from slam import geometry as G
    from slam import labels as L
    times = np.asarray(times, float)
    out = np.full(len(times), np.nan)
    T_wc = L.tile_world_cam(S)
    good = np.isfinite(T_wc[:, 0, 0])
    if len(times) == 0 or good.sum() < 2:
        return out
    ts = S["wall"][good]
    tt = np.concatenate([times, times + window])
    near = np.abs(tt[:, None] - ts[None]).min(1) <= L.LABEL_TOL
    R = L.interp_poses(tt, ts, T_wc[good])[:, :3, :3]
    n = len(times)
    ang = G.rot_angle_deg(np.swapaxes(R[:n], 1, 2) @ R[n:])
    v = near[:n] & near[n:]
    out[v] = ang[v] / window
    return out


def coupling_stats(coups, steps):
    """Per step j: n, median / p90 of |dR b| and |dt| [mm], median cosine (segment_anchors)."""
    out = {}
    for j in steps:
        x = np.array([c[1:] for cc in coups for c in cc if c[0] == j], float).reshape(-1, 3)
        if not len(x):
            continue
        cos = x[np.isfinite(x[:, 2]), 2]
        out[j] = {"n": len(x), "rot_part_mm_median": float(np.median(x[:, 0])),
                  "rot_part_mm_p90": float(np.percentile(x[:, 0], 90)),
                  "trans_part_mm_median": float(np.median(x[:, 1])),
                  "trans_part_mm_p90": float(np.percentile(x[:, 1], 90)),
                  "cos_median": float(np.median(cos)) if len(cos) else None}
    return out


def stats_block(anchors, steps, horizon, chunk_H):
    """{"anchors", "by_step", "chunk"} of anchor_errors-shaped [(segment, t, [(j, pos, rot)])]
    (computed with a horizon >= max(horizon, chunk_H)): slam.labels.step_stats over j <= horizon,
    slam.labels.chunk_stats."""
    from slam import labels as L
    upto = [(s, t, [x for x in e if x[0] <= horizon]) for s, t, e in anchors]
    return {"anchors": len(anchors),
            "by_step": L.step_stats(upto, "", horizon, (), tuple(steps))["by_step"],
            "chunk": L.chunk_stats(anchors, list(chunk_H))}


# ---------------------------------------------------------------------- one run
def decompose(session, segments, run, scale_res, params, scratch, gripper="head", log=print):
    """Error decomposition of `run` on the segments of C.segments_dir(session).
    scale_res: scale_<run>.json (analysis contract; rows s / oracle_s / flagged, label).
    Label files are written under scratch/segments/ (removed at the end)."""
    from slam import labels as L
    from slam.evaluate import load_segment, load_tool_offset
    steps, horizon, chunk_H = list(params["label_steps"]), int(params["horizon"]), list(params["chunk_H"])
    window = float(params["speed_window_s"])
    if window <= 0:
        raise ValueError(f"error_decomp.speed_window_s must be > 0, got {window}")
    bins = speed_bins(params["speed_bins_deg_s"])
    H = max([horizon] + chunk_H)
    label = scale_res["label"]
    rows = {r["segment"]: r for r in scale_res["rows"]}
    T_bt = load_tool_offset(session)
    grip = L.load_gripper(session, gripper)
    root = Path(scratch) / "segments"
    per = {k: [] for k in SCALES}            # (segment, t, e_slam, e_tile, speed, coupling)
    checks = {k: {"pairs": 0, "max_pos_mm": 0.0, "max_rot_frobenius": 0.0} for k in SCALES}
    seg_info = {}
    try:
        for name in segments:
            src = C.segments_dir(session) / name
            r = rows.get(name) or {}
            s_cfg = r.get("s") if r.get("ok", r.get("s") is not None) else None
            scales = {"configured": (s_cfg, label), "oracle": (r.get("oracle_s"), "tiles")}
            info = {"s": s_cfg, "oracle_s": r.get("oracle_s"), "flagged": bool(r.get("flagged")),
                    "kept": {"tiles": False, "configured": False, "oracle": False},
                    "anchors": {k: 0 for k in SCALES}}
            seg_info[name] = info
            if not (src / "slam" / f"{run}.npz").exists():
                log(f"{name}: no slam/{run}.npz, skipped")
                continue
            sd = scratch_segment(src, root / name, run)
            S = load_segment(sd)
            T_sc = np.load(sd / "slam" / f"{run}.npz")["T_slam_cam"]
            tile = build_label(sd, "tiles", "tiles", T_bt, grip)
            info["kept"]["tiles"] = tile["keep"]
            cam_tile = cam_series(S, L.tile_world_cam(S), tile["t"])
            found = {}
            for kind, (s, mode) in scales.items():
                lab = build_label(sd, run, mode, T_bt, grip, scale=(s, mode))
                info["kept"][kind] = lab["keep"]
                cam = cam_series(S, scaled_slam_cam(T_sc, s), lab["t"])
                found[kind], c = segment_anchors(lab, tile, cam, cam_tile, H)
                info["anchors"][kind] = len(found[kind])
                ck = checks[kind]
                ck["pairs"] += c["pairs"]
                ck["max_pos_mm"] = max(ck["max_pos_mm"], c["max_pos_mm"])
                ck["max_rot_frobenius"] = max(ck["max_rot_frobenius"], c["max_rot_frobenius"])
            times = sorted({a[1] for k in SCALES for a in found[k]})
            sp = dict(zip(times, head_speeds(S, times, window)))
            for kind in SCALES:
                per[kind] += [(name, t, es, et, sp[tm], cp) for t, tm, es, et, cp in found[kind]]
    finally:
        shutil.rmtree(root, ignore_errors=True)
    combos = {}
    for cname, rot, kind in COMBOS:
        A = [(sg, t, es if rot == "slam" else et) for sg, t, es, et, _, _ in per[kind]]
        b = {"rotation": rot, "scale": kind, **stats_block(A, steps, horizon, chunk_H), "by_speed": {}}
        sbin = [bin_of(a[4], bins) for a in per[kind]]
        for bname, _, _ in bins:
            b["by_speed"][bname] = stats_block([a for a, x in zip(A, sbin) if x == bname], steps, horizon, chunk_H)
        combos[cname] = b
    spd = {}
    for kind in SCALES:
        sbin = [bin_of(a[4], bins) for a in per[kind]]
        spd[kind] = {bname: sum(x == bname for x in sbin) for bname, _, _ in bins}
        spd[kind][UNKNOWN] = sum(x is None for x in sbin)
    return _clean({"run": run, "scale_label": label, "gripper": gripper, "params": dict(params),
                   "combos": combos, "anchors": {k: len(per[k]) for k in SCALES},
                   "speed": {"window_s": window, "bins_deg_s": [float(x) for x in params["speed_bins_deg_s"]],
                             "anchors": spd},
                   "coupling": {k: {"by_step": coupling_stats([a[5] for a in per[k]], [j for j in steps if j <= horizon])}
                                for k in SCALES},
                   "segments": seg_info, "checks": {"decomposition": checks}})


def _numbers(a, b, path=""):
    """[(path, x, y)] of the numeric leaves of two equally shaped JSON objects (a's keys)."""
    out = []
    if isinstance(a, dict):
        for k, v in a.items():
            out += _numbers(v, (b or {}).get(k) if isinstance(b, dict) else None, f"{path}/{k}")
    elif isinstance(a, (int, float)) and not isinstance(a, bool) or a is None:
        out.append((path, a, b))
    return out


def compare_with_labels(combo, lab, name):
    """A combination vs a labels_*.json of the labels step: anchors, by_step and chunk on their
    common steps / H, exact equality (the same computation) and the largest absolute difference."""
    by_c, by_l = combo["by_step"], lab.get("by_step") or {}
    ch_c, ch_l = combo["chunk"], lab.get("chunk") or {}
    js = [j for j in by_c if j in by_l]
    hs = [h for h in ch_c if h in ch_l]
    pairs = _numbers({j: by_c[j] for j in js}, {j: by_l[j] for j in js})
    pairs_c = _numbers({h: ch_c[h] for h in hs}, {h: ch_l[h] for h in hs})
    same = (lambda pp: all(x == y for _, x, y in pp))
    diffs = [abs(x - y) for _, x, y in pairs + pairs_c if x is not None and y is not None]
    out = {"file": name, "anchors": [combo["anchors"], lab.get("anchors")],
           "by_step_identical": same(pairs) and len(js) == len(by_c),
           "chunk_identical": same(pairs_c) and len(hs) == len(ch_c),
           "max_abs_diff": max(diffs) if diffs else None, "compared": {"steps": js, "chunk_H": hs}}
    out["identical"] = (out["by_step_identical"] and out["chunk_identical"]
                        and combo["anchors"] == lab.get("anchors"))
    return out


def labels_checks(res, out_dir):
    """checks.labels_files: R_slam+s_configured vs labels_<run>@<label>.json, R_slam+s_oracle vs
    labels_<run>.json (when the labels step wrote them into out_dir), else null."""
    run, label = res["run"], res["scale_label"]
    out = {}
    for cname, f in (("R_slam+s_configured", f"labels_{run}@{label}.json"), ("R_slam+s_oracle", f"labels_{run}.json")):
        p = Path(out_dir) / f
        out[cname] = compare_with_labels(res["combos"][cname], json.load(open(p)), f) if p.exists() else None
    return out


# ---------------------------------------------------------------------- markdown
def errdecomp_md(res, session):
    from slam.pipeline import impl_report as R
    L = [f"# Error decomposition on {session}, run {res['run']}", ""]
    L += R.error_decomp_tables(res["run"], res, level="##")
    L += ["## Segments", "",
          "| segment | configured s | oracle s | flagged | kept: tiles / configured / oracle | anchors configured / oracle |",
          "|---|---|---|---|---|---|"]
    num = (lambda v: "-" if v is None else f"{v:.4f}")
    for name, x in res["segments"].items():
        k = x["kept"]
        L.append(f"| {name} | {num(x['s'])} | {num(x['oracle_s'])} | {'yes' if x['flagged'] else ''} | "
                 f"{'/'.join('y' if k[q] else 'n' for q in ('tiles', 'configured', 'oracle'))} | "
                 f"{x['anchors']['configured']} / {x['anchors']['oracle']} |")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------- step
def run_error_decomp(job):
    an = job.analysis or {}
    runs = list((an.get("error_decomp") or {}).get("runs", []))
    gripper = ((an.get("labels") or {}).get("params") or {}).get("gripper", "head")
    out = {}
    for run in runs:
        p = job.out_dir / f"scale_{run}.json"
        if not p.exists():
            raise FileNotFoundError(f"error_decomp {run}: {p.name} missing (the run needs a scale block)")
        res = decompose(job.session, job.segments, run, json.load(open(p)), job.params,
                        job.scratch / run, gripper, job.log)
        res["checks"]["labels_files"] = _clean(labels_checks(res, job.out_dir))
        with open(job.out_dir / f"errdecomp_{run}.json", "w") as f:
            json.dump(res, f, indent=1, allow_nan=False)
        (job.out_dir / f"errdecomp_{run}.md").write_text(errdecomp_md(res, job.session))
        b1 = {c: (res["combos"][c]["by_step"].get("15") or {}).get("pos_mm_median") for c, _, _ in COMBOS}
        lc = {c: (v or {}).get("identical") for c, v in res["checks"]["labels_files"].items()}
        job.log(f"{run} {res['scale_label']}: anchors {res['anchors']}, 1 s position median {b1}; "
                f"identical to the labels files: {lc}; decomposition check {res['checks']['decomposition']}")
        out[run] = {"anchors": res["anchors"], "pos_mm_median_1s": b1, "labels_identical": lc}
    return out
