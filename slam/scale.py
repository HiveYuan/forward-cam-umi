#!/usr/bin/env python3
"""Metric scale of a monocular SLAM segment: interchangeable methods behind one interface.

A method maps (segment, SLAM run) to a scale s with  metric translation = s * SLAM translation
(rotation is scale-free). Methods (registry METHODS, selected by name everywhere a scale is used:
slam.labels --scale, slam.evaluate --scale, slam.report):

  none   s = 1 (raw SLAM units)
  native s = 1 for a metric SLAM run (traj.npz metric=True, e.g. a backend that outputs metres);
         fails on an up-to-scale run (monocular DROID, legacy files without the key)
  tiles  oracle: Umeyama fit of the SLAM camera centres to the tile head poses (evaluation only)
  A      static ball (design doc, option A, point-only): while the hand rests, the ball centre is a
         fixed point of the scene. In the SLAM frame it is p_i = R_i b_i + s c_i (b_i = ball centre
         in the camera from PnP, R_i, c_i = SLAM camera rotation and unscaled centre), so over a
         window   [c_i, -I] [s; p] = -R_i b_i   is linear in (s, p). Sliding windows are solved;
         a window counts when its residual is small (the ball really was static) and the head moved
         enough (the scale is observable). s = weighted median over accepted windows. Uses only
         the ball and SLAM, no tiles, so it runs in the wild. Known bias: on natural footage a
         "static" hand still drifts a little with the head (body sway); motion collinear with the
         head is absorbed into s without raising the residual. glove7: s about 5% low on SLAM and
         ~12-17% low on tile GT poses; gating on rotational/non-collinear head motion does not
         remove it, so A needs the deliberate rest-and-sweep gesture to be accurate.
  B      metric depth + ball (design doc, option B): a monocular metric-depth network
         (slam.depth, cached per keyframe) is corrected per segment by the ball, whose PnP depth is
         metric: k = median over keyframes and ball faces of (face-centre depth from the ball pose)
         / (network depth at the face centre's pixel), using faces that face the camera
         (correction="faces", default; the face centres lie well inside the ball's silhouette, so
         background depth does not bleed in), or the depth of a disk at the projected ball centre
         (correction="disk", biased low because the small ball blends with the background). The corrected depth of
         the static background (cells valid under the run's masks) against DROID's keyframe depth
         gives s = median(k D_net / z_slam). Known bias: the network over-estimates depth at the
         small, near ball relative to the background (depth-dependent error in this white scene),
         so k and s come out ~5% low with DA2 (~17% with Depth Pro).

  Bsession  B with a session-level ball correction (exp005): k_session = median over the session's
         segments of each segment's k (session_k, pool="segments"; or the median over all pooled
         ball samples, pool="samples"), then s = median(k_session D_net / z_slam) per segment as in
         B. The framework computes k_session over every segment of the run first and passes it as
         the keyword k_session (SESSION_METHODS). Removes the per-segment error of k (few ball
         samples, a ball seen at an unusual depth), not the segment-to-segment variation of the
         network's scale on the background (exp005: glove7 E3 |err| p90 20.1 -> 17.7%, median
         5.4 -> 6.3%, bias -5.0 -> -5.9%; labels 1 s 5.7 -> 4.8 mm).

  B+Acheck  decision of 2026-11-08: B is the method, A only cross-checks. s = B's result on
         every segment; where A also succeeds, the relative difference s_A/s_B - 1 is recorded
         and |diff| > threshold (10%) flags the segment. Flags are informational only: they
         neither change s nor drop the segment. The general form (any primary, any checks) is
         cross_check(), used by the experiment framework (slam.pipeline.impl_analysis).

A spec may chain methods for fallback: "A,B" = A if it succeeds, else B. "B:<model>" picks the
depth network (slam.depth MODELS; default da2-metric-indoor-large), e.g. "B:depth-pro".
Each result is cached in <segment>/scale/<run>_<method>.json: {s, ok, method, ...diagnostics}.

  python -m slam.scale estimate --session yam_glove7 --run E3 --method A
  python -m slam.scale eval --session yam_glove7 --run E3 --methods A,B     # vs the tile oracle
"""
import argparse
import hashlib
import inspect
import json

import numpy as np

from slam import config as C
from slam import geometry as G

BALL_R = 0.0215                 # dodeca centre to face centre [m] (glove_yosub_dodeca_bundle)
DEPTH_MODELS = ("da2-metric-indoor-large", "depth-pro")      # slam.depth MODELS keys
CACHE_VERSION = 2


# ------------------------------------------------------------------ helpers
def _segment(seg):
    from slam.evaluate import load_segment
    return load_segment(seg)


def _run(seg, run):
    z = np.load(seg / "slam" / f"{run}.npz")
    return z, json.loads(str(z["meta"]))


# ------------------------------------------------------------------ core math (pure, tested)
def fit_static_point(Rb, c):
    """Window of frames where a point is static: Rb (N, 3) = R_i b_i, c (N, 3) unscaled camera
    centres. Solves [c_i, -I][s; p] = -R_i b_i; returns (s, p, per-frame residual [m])."""
    A = np.zeros((3 * len(c), 4))
    A[:, 0] = c.reshape(-1)
    A[:, 1:] = -np.tile(np.eye(3), (len(c), 1))
    x, *_ = np.linalg.lstsq(A, -Rb.reshape(-1), rcond=None)
    s, p = x[0], x[1:]
    return float(s), p, np.linalg.norm(Rb + s * c - p, axis=1)


def depth_ratio_scale(k, d_net, z_slam, valid):
    """Metric/SLAM scale from corrected network depth k*d_net and SLAM depth z_slam on valid cells."""
    return float(np.median(k * d_net[valid] / z_slam[valid]))


# ------------------------------------------------------------------ methods
def scale_none(seg, run, **_):
    return {"s": 1.0, "ok": True}


def scale_native(seg, run, **_):
    """s = 1 when the run's trajectory is already metric (traj.npz 'metric'; absent = not metric)."""
    z = np.load(seg / "slam" / f"{run}.npz")
    if "metric" in z.files and bool(z["metric"]):
        return {"s": 1.0, "ok": True, "metric": True}
    return {"s": float("nan"), "ok": False, "metric": False,
            "error": f"run {run} is not metric (traj.npz metric is False or missing)"}


def scale_tiles(seg, run, **_):
    from slam.evaluate import segment_scale
    S = _segment(seg)
    z, _ = _run(seg, run)
    s, res = segment_scale(S, z["T_slam_cam"].astype(float))
    return {"s": float(s), "ok": bool(np.isfinite(s)), "align_res_mm": 1000 * float(res)}


def scale_static_ball(seg, run, window_s=1.0, step_s=0.25, res_max_mm=5.0, min_baseline_mm=20.0,
                      min_frames=10, **_):
    """Windows use only frames with a ball pose AND a finite SLAM pose (untracked frames are
    NaN rows); a window with fewer than min_frames such frames is skipped."""
    S = _segment(seg)
    z, _ = _run(seg, run)
    T = z["T_slam_cam"].astype(float)
    have = np.isfinite(S["T_cb"][:, 0, 0]) & np.isfinite(T).all((1, 2))
    idx = np.where(have)[0]
    wall = S["wall"]
    wins = []
    t0 = wall[0]
    while t0 + window_s <= wall[-1] + 1e-9:
        w = idx[(wall[idx] >= t0) & (wall[idx] < t0 + window_s)]
        t0 += step_s
        if len(w) < min_frames:
            continue
        Rb = (T[w, :3, :3] @ S["T_cb"][w, :3, 3][..., None])[..., 0]       # R_i b_i
        c = T[w, :3, 3]
        s, p, res = fit_static_point(Rb, c)
        if not np.isfinite(s) or s <= 0:
            continue
        base = s * np.linalg.norm(c - c.mean(0), axis=1).max()
        wins.append({"t0": float(wall[w[0]]), "s": float(s), "res_mm": 1000 * float(np.sqrt((res ** 2).mean())),
                     "baseline_mm": 1000 * float(base), "n": int(len(w))})
    acc = [w for w in wins if w["res_mm"] <= res_max_mm and w["baseline_mm"] >= min_baseline_mm]
    out = {"windows": len(wins), "accepted": len(acc),
           "static_s": float(sum(step_s for _ in acc)), "params": {"window_s": window_s, "res_max_mm": res_max_mm,
                                                                   "min_baseline_mm": min_baseline_mm}}
    if not acc:
        return {"s": float("nan"), "ok": False, **out}
    s = np.array([w["s"] for w in acc])
    wt = np.array([w["baseline_mm"] / max(w["res_mm"], 0.3) for w in acc])
    o = np.argsort(s)
    cw = np.cumsum(wt[o]) / wt.sum()
    s_med = float(s[o][np.searchsorted(cw, 0.5)])
    return {"s": s_med, "ok": True, "s_spread": [float(np.percentile(s, 25)), float(np.percentile(s, 75))],
            "accepted_windows": acc, **out}


def _valid_cells(seg, names, n_frames, size, dilate_px=8):
    """Same rule as slam.droid_masked.valid_grid, numpy: (T, H/8, W/8) bool."""
    import cv2
    W, H = size
    valid = np.ones((n_frames, H // 8, W // 8), bool)
    if not names:
        return valid
    masked = np.zeros((n_frames, H, W), bool)
    for nme in names:
        masked |= np.unpackbits(np.load(seg / "masks" / f"{nme}.npz")["masked"], axis=-1, count=W).astype(bool)
    k = np.ones((2 * dilate_px + 1, 2 * dilate_px + 1), np.uint8)
    for i in range(n_frames):
        m = cv2.dilate(masked[i].astype(np.uint8), k)
        valid[i] = m.reshape(H // 8, 8, W // 8, 8).max((1, 3)) == 0
    return valid


def ball_faces(session):
    """Face centres and outward normals of the ball in its body frame."""
    import sys
    sys.path.insert(0, str(C.REPO / "scripts"))
    import labels_lib as L
    T_body, _ = L.load_bundle(C.CALIB / f"glove_{C.session(session)['glove']}_dodeca_bundle.json")
    P = np.array([T[:3, 3] for T in T_body.values()])
    return P, P / np.linalg.norm(P, axis=1, keepdims=True)


def _depth_inputs(seg, run, model):
    """Inputs of the metric-depth methods for one segment: (ctx, None), or (None, failed result).
    ctx: depth (n_kf, H, W) network depth, S (slam.evaluate segment: ball poses T_cb), z / meta
    (SLAM run), fj (frames.json), K, size (W, H), kf_t, disp (inverse depth on the 1/8 grid)."""
    dp = seg / "depth" / f"{run}_{model}.npz"
    if not dp.exists():
        return None, {"s": float("nan"), "ok": False, "error": f"missing {dp} (run slam.depth)"}
    D = np.load(dp)
    S = _segment(seg)
    z, meta = _run(seg, run)
    fj = json.load(open(seg / "frames.json"))
    kf_t, disp = z["kf_t"], z["kf_disp"].astype(float)
    if not np.array_equal(D["kf_t"], kf_t):
        return None, {"s": float("nan"), "ok": False, "error": "depth cache is for other keyframes"}
    return {"depth": D["depth"], "S": S, "z": z, "meta": meta, "fj": fj, "K": np.array(fj["K"]),
            "size": tuple(fj["size"]), "kf_t": kf_t, "disp": disp}, None


def ball_depth_pairs(ctx, correction="faces", min_facing=0.7):
    """Ball samples of method B on the keyframes: [(network depth, metric depth, frame index)].
    correction="faces": the face centres facing the camera (cos >= min_facing), network depth =
    median of the 3x3 pixels at the projected centre; "disk": a disk at the projected ball centre
    vs the depth of the ball's front (centre depth - BALL_R)."""
    S, K, kf_t, depth = ctx["S"], ctx["K"], ctx["kf_t"], ctx["depth"]
    W, H = ctx["size"]
    pairs = []                                                  # (network depth, metric depth)
    faces = ball_faces(ctx["fj"]["session"]) if correction == "faces" else None
    for j, i in enumerate(kf_t):
        if not np.isfinite(S["T_cb"][i, 0, 0]):
            continue
        dn = depth[j].astype(float)                            # network depth, (H, W) metres
        Tcb = S["T_cb"][i]
        if faces is not None:
            Pc = (Tcb[:3, :3] @ faces[0].T).T + Tcb[:3, 3]     # face centres in the camera
            nc = (Tcb[:3, :3] @ faces[1].T).T
            facing = (nc * -Pc / np.linalg.norm(Pc, axis=1, keepdims=True)).sum(1) >= min_facing
            for P in Pc[facing]:
                u, v, w_ = K @ P
                u, v = int(round(u / w_)), int(round(v / w_))
                if 2 <= u < W - 2 and 2 <= v < H - 2:
                    pairs.append((np.median(dn[v - 1:v + 2, u - 1:u + 2]), P[2], int(i)))
        else:
            b = Tcb[:3, 3]
            u, v, w_ = K @ b
            u, v = u / w_, v / w_
            r = 0.6 * K[0, 0] * BALL_R / b[2]
            if 0 <= u < W and 0 <= v < H and r >= 2:
                yy, xx = np.mgrid[0:H, 0:W]
                disk = (xx - u) ** 2 + (yy - v) ** 2 <= r ** 2
                pairs.append((np.median(dn[disk]), b[2] - BALL_R, int(i)))
    return pairs


def background_ratios(ctx, valid, alpha, beta=0.0, z_max=4.0, min_cells=200, depth_window=None):
    """Corrected network depth alpha * d + beta over DROID's keyframe depth on the background:
    cells valid under the masks (valid: (T, H/8, W/8)), finite, 0.1 < corrected depth < z_max,
    inverse depth > 1e-3, not on the grid border, optionally within depth_window of the ball's
    depth. Keyframes without a finite SLAM pose (their frame's T_slam_cam row, or kf_pose_cw
    where saved) and keyframes with fewer than min_cells such cells are left out.
    Returns (ratios: one array per used keyframe, per-keyframe medians)."""
    S, z, kf_t, disp, depth = ctx["S"], ctx["z"], ctx["kf_t"], ctx["disp"], ctx["depth"]
    W, H = ctx["size"]
    T_sc = z["T_slam_cam"]
    kf_ok = np.isfinite(T_sc[kf_t]).all((1, 2))                # keyframes with a SLAM pose
    if "kf_pose_cw" in z.files:
        kf_ok &= np.isfinite(z["kf_pose_cw"]).all(1)
    z_ball = {int(i): float(S["T_cb"][i, 2, 3]) for i in kf_t if np.isfinite(S["T_cb"][i, 0, 0])}
    zb_med = float(np.median(list(z_ball.values()))) if z_ball else np.nan
    ratios, per_kf = [], []
    for j, i in enumerate(kf_t):
        if not kf_ok[j]:
            continue
        d8 = depth[j].astype(float).reshape(H // 8, 8, W // 8, 8).mean((1, 3))   # DROID's 1/8 grid
        zc = alpha * d8 + beta                                  # corrected (metric) network depth
        zs = 1.0 / np.clip(disp[j], 1e-6, None)
        m = valid[i] & np.isfinite(zc) & (zc > 0.1) & (zc < z_max) & (disp[j] > 1e-3) & np.isfinite(disp[j])
        if depth_window:                                       # compare only near the ball's depth
            m &= np.abs(zc / z_ball.get(int(i), zb_med) - 1) <= depth_window
        m[:1], m[-1:], m[:, :1], m[:, -1:] = False, False, False, False
        if m.sum() < min_cells:
            continue
        per_kf.append(depth_ratio_scale(1.0, zc, zs, m))
        ratios.append(zc[m] / zs[m])
    return ratios, per_kf


def _run_valid_cells(seg, ctx, mask_names, mask_dilate_px):
    names = ctx["meta"].get("masks", []) if mask_names is None else list(mask_names)
    return _valid_cells(seg, names, len(ctx["fj"]["frames"]), ctx["size"], mask_dilate_px)


def scale_depth_ball(seg, run, model="da2-metric-indoor-large", correction="faces", min_facing=0.7,
                     fit="scale", min_affine_range=0.15, depth_window=None, z_max=4.0, min_cells=200,
                     mask_names=None, mask_dilate_px=8, **_):
    """fit: "scale" = corrected depth k d (one factor from the ball), "affine" = a d + b fitted
    (Theil-Sen) to the ball samples across keyframes, falling back to "scale" if the ball's depth
    range is below min_affine_range [m]. Background cells: valid under the masks mask_names
    (None = the masks recorded in the run's meta) dilated by mask_dilate_px. Keyframes without a
    finite SLAM pose (their frame's T_slam_cam row, or kf_pose_cw where saved) are left out of
    the background ratio; non-finite inverse depth cells never count."""
    ctx, err = _depth_inputs(seg, run, model)
    if err is not None:
        return err
    valid = _run_valid_cells(seg, ctx, mask_names, mask_dilate_px)
    pairs = ball_depth_pairs(ctx, correction, min_facing)
    if not pairs:
        return {"s": float("nan"), "ok": False, "error": "ball never visible in a keyframe"}
    pr = np.array([(d, zt) for d, zt, _ in pairs])
    k = float(np.median(pr[:, 1] / pr[:, 0]))
    alpha, beta, fit_used = k, 0.0, "scale"
    if fit == "affine" and len(pr) >= 10 and np.ptp(pr[:, 1]) >= min_affine_range:
        ii, jj = np.triu_indices(len(pr), 1)                   # Theil-Sen
        dd = pr[jj, 0] - pr[ii, 0]
        ok = np.abs(dd) > 1e-3
        alpha = float(np.median((pr[jj, 1] - pr[ii, 1])[ok] / dd[ok]))
        beta = float(np.median(pr[:, 1] - alpha * pr[:, 0]))
        fit_used = "affine"
    ratios, per_kf = background_ratios(ctx, valid, alpha, beta, z_max, min_cells, depth_window)
    if not per_kf:
        return {"s": float("nan"), "ok": False, "error": "no keyframe with enough valid background"}
    s = float(np.median(np.concatenate(ratios)))
    return {"s": s, "ok": True, "k_ball": k, "ball_samples": len(pr), "ball_depth_range_m": float(np.ptp(pr[:, 1])),
            "fit": fit_used, "alpha": alpha, "beta": beta, "s_per_keyframe": per_kf, "model": model,
            "correction": correction, "depth_window": depth_window}


# ------------------------------------------------------------------ session-level ball correction
SESSION_POOLS = ("segments", "samples")


def ball_samples(seg, run, model="da2-metric-indoor-large", correction="faces", min_facing=0.7):
    """Method B's ball samples of one segment (for pooling over a session): {ok, pairs (n, 2)
    [network depth, metric depth], frames (n,), k (median metric / network, NaN if none), n,
    error}. The same samples scale_depth_ball takes its k_ball from."""
    ctx, err = _depth_inputs(seg, run, model)
    if err is not None:
        return {"ok": False, "pairs": np.zeros((0, 2)), "frames": np.zeros(0, int), "k": float("nan"), "n": 0,
                "error": err["error"]}
    pairs = ball_depth_pairs(ctx, correction, min_facing)
    pr = np.array([(d, zt) for d, zt, _ in pairs]).reshape(-1, 2)
    k = float(np.median(pr[:, 1] / pr[:, 0])) if len(pr) else float("nan")
    return {"ok": bool(len(pr)), "pairs": pr, "frames": np.array([i for *_, i in pairs], int), "k": k,
            "n": int(len(pr)), "error": None if len(pr) else "ball never visible in a keyframe"}


def session_k(samples, pool="segments"):
    """Session-level ball correction from per-segment ball samples {segment: (n, 2) array of
    [network depth, metric depth]} (segments without samples: empty array).
      pool="segments": k_session = median over segments with samples of the segment's
                       k = median(metric / network) (each segment counts once, as many
                       keyframes and visible faces as it has)
      pool="samples":  k_session = median of metric / network over all samples pooled
    Returns {k_session, pool, n_segments, n_samples, k_segment_p10/p25/p75/p90 (spread of the
    per-segment k), per_segment: {segment: {k, n}}}; k_session NaN when no segment has samples."""
    if pool not in SESSION_POOLS:
        raise ValueError(f"pool: one of {SESSION_POOLS}, got {pool!r}")
    per, ks, allr = {}, [], []
    for name, pr in samples.items():
        pr = np.asarray(pr, float).reshape(-1, 2)
        r = pr[:, 1] / pr[:, 0]
        k = float(np.median(r)) if len(r) else float("nan")
        per[name] = {"k": k, "n": int(len(r))}
        if len(r):
            ks.append(k)
            allr.append(r)
    if not ks:
        k_sess = float("nan")
    elif pool == "segments":
        k_sess = float(np.median(ks))
    else:
        k_sess = float(np.median(np.concatenate(allr)))
    pct = {f"k_segment_p{q}": float(np.percentile(ks, q)) if ks else float("nan") for q in (10, 25, 75, 90)}
    return {"k_session": k_sess, "pool": pool, "n_segments": len(ks), "n_samples": int(sum(len(r) for r in allr)),
            **pct, "per_segment": per}


def session_k_of_run(segs, run, model="da2-metric-indoor-large", correction="faces", min_facing=0.7,
                     pool="segments"):
    """session_k over the ball samples of every segment directory in segs (one SLAM run)."""
    return session_k({seg.name: ball_samples(seg, run, model, correction, min_facing)["pairs"] for seg in segs},
                     pool)


def scale_depth_ball_session(seg, run, k_session=None, model="da2-metric-indoor-large", correction="faces",
                             min_facing=0.7, pool="segments", depth_window=None, z_max=4.0, min_cells=200,
                             mask_names=None, mask_dilate_px=8, **_):
    """Method B with the session's ball correction: s = median(k_session D_net / z_slam) over the
    same background cells and keyframes as scale_depth_ball (fit="scale"). k_session is pooled
    over every segment of the session (session_k with `pool`, the framework passes it; the
    segment's own ball is not needed, so segments where the ball never shows in a keyframe get a
    scale too). correction / min_facing / pool say how k_session was pooled (recorded here).
    Diagnostics: the segment's own k_ball (NaN without ball samples) and s_own_k, the scale with
    it (= method B with fit="scale" and the same parameters)."""
    if pool not in SESSION_POOLS:
        raise ValueError(f"pool: one of {SESSION_POOLS}, got {pool!r}")
    if correction not in ("faces", "disk"):
        raise ValueError(f"correction: 'faces' or 'disk', got {correction!r}")
    if k_session is None:
        return {"s": float("nan"), "ok": False, "k_session": None,
                "error": "Bsession needs k_session, pooled over all segments by the framework "
                         "(slam.pipeline.impl_analysis.scale_run); the legacy CLI does not pool it"}
    if not np.isfinite(k_session) or k_session <= 0:
        return {"s": float("nan"), "ok": False, "k_session": k_session,
                "error": "no segment of the run had ball samples to pool k_session from"}
    ctx, err = _depth_inputs(seg, run, model)
    if err is not None:
        return err
    if depth_window and not any(np.isfinite(ctx["S"]["T_cb"][i, 0, 0]) for i in ctx["kf_t"]):
        return {"s": float("nan"), "ok": False, "k_session": float(k_session),
                "error": "depth_window keeps background near this segment's own ball depth, but the "
                         "ball is in no keyframe"}
    valid = _run_valid_cells(seg, ctx, mask_names, mask_dilate_px)
    ratios, per_kf = background_ratios(ctx, valid, float(k_session), 0.0, z_max, min_cells, depth_window)
    if not per_kf:
        return {"s": float("nan"), "ok": False, "k_session": k_session,
                "error": "no keyframe with enough valid background"}
    s = float(np.median(np.concatenate(ratios)))
    pr = np.array([(d, zt) for d, zt, _ in ball_depth_pairs(ctx, correction, min_facing)]).reshape(-1, 2)
    k_own, s_own = float("nan"), float("nan")
    if len(pr):
        k_own = float(np.median(pr[:, 1] / pr[:, 0]))
        r_own, _ = background_ratios(ctx, valid, k_own, 0.0, z_max, min_cells, depth_window)
        s_own = float(np.median(np.concatenate(r_own))) if r_own else float("nan")
    return {"s": s, "ok": True, "k_session": float(k_session), "pool": pool, "k_ball": k_own,
            "ball_samples": int(len(pr)), "s_own_k": s_own, "s_per_keyframe": per_kf, "model": model,
            "correction": correction, "depth_window": depth_window}


def cross_check(primary, checks, threshold):
    """Primary scale result + cross-check results {name: result} -> {s, ok, flagged, flagged_by,
    checks: {name: {s, ok, diff}}}. s and ok are ALWAYS the primary's; a check only flags:
    diff = s_check / s - 1 where both succeeded, |diff| > threshold flags the segment
    (threshold None: diffs are recorded, nothing is flagged)."""
    s, ok = float(primary["s"]), bool(primary.get("ok"))
    out_checks, flagged_by = {}, []
    for name, r in checks.items():
        c_ok = bool(r.get("ok"))
        c = {"s": float(r["s"]) if c_ok else float("nan"), "ok": c_ok, "diff": None}
        if ok and c_ok:
            c["diff"] = c["s"] / s - 1
            if threshold is not None and abs(c["diff"]) > threshold:
                flagged_by.append(name)
        out_checks[name] = c
    return {"s": s, "ok": ok, "flagged": bool(flagged_by), "flagged_by": flagged_by, "checks": out_checks}


def scale_b_with_a_check(seg, run, model="da2-metric-indoor-large", threshold=0.10, **_):
    """B is the scale; A is computed where possible and only compared with it."""
    b = estimate(seg, run, "B" if model == DEPTH_MODELS[0] else f"B:{model}")
    a = estimate(seg, run, "A")
    cc = cross_check(b, {"A": a}, threshold)
    ca = cc["checks"]["A"]
    return {"s": cc["s"], "ok": cc["ok"], "s_B": float(b["s"]), "B_ok": bool(b.get("ok")),
            "s_A": ca["s"], "A_ok": ca["ok"], "threshold": threshold, "ab_diff": ca["diff"],
            "flagged": cc["flagged"], "model": model}


METHODS = {"none": scale_none, "native": scale_native, "tiles": scale_tiles, "A": scale_static_ball,
           "B": scale_depth_ball, "B+Acheck": scale_b_with_a_check, "Bsession": scale_depth_ball_session}
TAKES_MODEL = ("B", "B+Acheck", "Bsession")
COMPOSITE_METHODS = ("B+Acheck",)        # built from other methods; not a config-level method
# methods that need a session-level quantity computed over every segment first (keyword -> what):
# the caller (slam.pipeline.impl_analysis.scale_run) pools it with session_k_of_run and passes it
SESSION_METHODS = {"Bsession": "k_session"}
# keyword arguments added after CACHE_VERSION 2 caches were written: left out of the provenance
# while at their default, so those caches stay valid (same result)
_LATE_KW_DEFAULTS = {"mask_names": None, "mask_dilate_px": 8}


# ------------------------------------------------------------------ interface
def _provenance(seg, run, m, kw):
    """What a cached result depends on: code version, effective parameters, upstream files."""
    fn = METHODS[m]
    params = {k: v.default for k, v in inspect.signature(fn).parameters.items()
              if v.default is not inspect.Parameter.empty}
    params.update(kw)
    for k, d in _LATE_KW_DEFAULTS.items():
        if k in params and params[k] == d:
            del params[k]
    files = [seg / "slam" / f"{run}.npz", seg / "gt.npz"]
    if m in TAKES_MODEL:
        files.append(seg / "depth" / f"{run}_{params.get('model', DEPTH_MODELS[0])}.npz")
    up = {f.name: [f.stat().st_mtime_ns, f.stat().st_size] if f.exists() else None for f in files}
    return {"version": CACHE_VERSION, "params": params, "upstream": up}


def estimate(seg, run, method, cache=True, **cfg):
    """Scale result dict for one segment; method may be a fallback chain 'A,B'.

    Cached per (run, method, option, parameters) in <segment>/scale/; a cache entry is reused
    only if its code version, effective parameters and upstream file stamps still match, and
    failures are never cached (they are cheap to recompute and may be transient)."""
    r = None
    for spec in method.split(","):
        m, _, opt = spec.partition(":")
        if m not in METHODS:
            raise KeyError(f"unknown scale method {m!r}; known {sorted(METHODS)}")
        if opt and m not in TAKES_MODEL:
            raise ValueError(f"{spec!r}: only {TAKES_MODEL} take an option (the depth model)")
        if opt and opt not in DEPTH_MODELS:
            raise ValueError(f"{spec!r}: unknown depth model; known {DEPTH_MODELS}")
        kw = dict(cfg)
        if opt:
            kw["model"] = opt
        tag = "" if not cfg else "_" + hashlib.sha1(json.dumps(sorted(cfg.items()), default=str)
                                                    .encode()).hexdigest()[:8]
        p = seg / "scale" / f"{run}_{m}{'-' + opt if opt else ''}{tag}.json"
        prov = _provenance(seg, run, m, kw)
        r = None
        if cache and p.exists():
            c = json.load(open(p))
            if c.get("ok") and c.get("provenance") == json.loads(json.dumps(prov, default=str)):
                r = c
        if r is None:
            r = METHODS[m](seg, run, **kw)
            r["method"] = spec
            if r.get("ok"):
                r["provenance"] = prov
                (seg / "scale").mkdir(exist_ok=True)
                json.dump(r, open(p, "w"), indent=1, default=str)
        if r.get("ok"):
            return r
    return r


def get_scale(seg, run, method):
    """Just s (NaN if every method in the chain failed)."""
    return float(estimate(seg, run, method)["s"])


# ------------------------------------------------------------------ CLI
def cmd_estimate(a):
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        r = estimate(seg, a.run, a.method, cache=not a.overwrite)
        extra = {"A": lambda r: f"accepted {r.get('accepted')} of {r.get('windows')} windows",
                 "B": lambda r: f"k_ball {r.get('k_ball', float('nan')):.3f} ({r.get('ball_samples', 0)} ball samples)"}
        print(f"{seg.name}: s = {float(r['s']):.4f} ({r['method']}, {'ok' if r['ok'] else 'FAILED: ' + str(r.get('error', ''))}) "
              f"{extra.get(r['method'].partition(':')[0], lambda r: '')(r)}")


def cmd_eval(a):
    methods = a.methods.split(";")
    rows = []
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        o = estimate(seg, a.run, "tiles")
        row = {"segment": seg.name, "oracle": o["s"]}
        for m in methods:
            r = estimate(seg, a.run, m)
            row[m] = r["s"] if r.get("ok") else float("nan")
        rows.append(row)
    L = [f"# Scale methods vs the tile oracle ({a.session}, run {a.run})", "",
         "| segment | oracle s | " + " | ".join(f"{m} s | {m} err %" for m in methods) + " |",
         "|---|---|" + "---|---|" * len(methods)]
    for r in rows:
        cells = []
        for m in methods:
            e = 100 * (r[m] / r["oracle"] - 1) if np.isfinite(r[m]) and np.isfinite(r["oracle"]) else np.nan
            cells += [f"{r[m]:.3f}" if np.isfinite(r[m]) else "-", f"{e:+.1f}" if np.isfinite(e) else "-"]
        L.append(f"| {r['segment']} | {r['oracle']:.3f} | " + " | ".join(cells) + " |")
    L.append("")
    summ = {}
    for m in methods:
        e = np.array([100 * (r[m] / r["oracle"] - 1) for r in rows if np.isfinite(r[m]) and np.isfinite(r["oracle"])])
        summ[m] = {"segments_ok": int(np.isfinite([r[m] for r in rows]).sum()), "segments": len(rows),
                   "n_compared": int(len(e)),
                   "abs_err_pct_median": float(np.median(np.abs(e))) if len(e) else None,
                   "abs_err_pct_p90": float(np.percentile(np.abs(e), 90)) if len(e) else None,
                   "bias_pct_median": float(np.median(e)) if len(e) else None}
        L.append(f"- **{m}**: scale on {summ[m]['segments_ok']}/{len(rows)} segments; error vs oracle over "
                 f"{summ[m]['n_compared']} with tile GT: |error| median "
                 f"{summ[m]['abs_err_pct_median'] if summ[m]['abs_err_pct_median'] is not None else float('nan'):.1f}%, "
                 f"p90 {summ[m]['abs_err_pct_p90'] if summ[m]['abs_err_pct_p90'] is not None else float('nan'):.1f}%, "
                 f"bias {summ[m]['bias_pct_median'] if summ[m]['bias_pct_median'] is not None else float('nan'):+.1f}%")
    ev = C.WORK / a.session / "eval"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / f"scale_{a.run}.md").write_text("\n".join(L) + "\n")
    json.dump({"rows": rows, "summary": summ}, open(ev / f"scale_{a.run}.json", "w"), indent=1, default=float)
    print("\n".join(L))


def _err_stats(errs):
    e = np.array([x for x in errs if x is not None and np.isfinite(x)])
    if not len(e):
        return {"n": 0}
    return {"n": int(len(e)), "abs_median": float(np.median(np.abs(e))),
            "abs_p90": float(np.percentile(np.abs(e), 90)), "bias_median": float(np.median(e))}


def cmd_crosscheck(a):
    """Summary for a B-primary spec with A cross-check: scale error vs the oracle, the
    cross-check flags, and label errors next to the oracle-scale labels (with and without the
    flagged segments). Writes <work>/<session>/eval/scale_<run>_<spec>.md/.json (new files)."""
    from slam.labels import STEPS, check_labels, label_name
    segs = sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]"))
    rows = []
    for seg in segs:
        r = estimate(seg, a.run, a.method)
        o = estimate(seg, a.run, "tiles")
        so = float(o["s"]) if o.get("ok") else np.nan
        rel = (lambda s: float(s / so - 1) if np.isfinite(s) and np.isfinite(so) else None)
        rows.append({"segment": seg.name, "oracle": so, "s": float(r["s"]), "ok": bool(r.get("ok")),
                     "s_A": r.get("s_A"), "s_B": r.get("s_B"), "ab_diff": r.get("ab_diff"),
                     "flagged": bool(r.get("flagged")), "threshold": r.get("threshold"),
                     "err": rel(float(r["s"])) if r.get("ok") else None,
                     "err_A": rel(r["s_A"]) if r.get("A_ok") else None,
                     "err_B": rel(r["s_B"]) if r.get("B_ok") else None})
    flagged = [r["segment"] for r in rows if r["flagged"]]
    both = [r for r in rows if r["ab_diff"] is not None]
    cov = sum(r["ok"] for r in rows)
    st_all = _err_stats([r["err"] for r in rows])
    st_kept = _err_stats([r["err"] for r in rows if not r["flagged"]])
    name = label_name(a.run, a.method)
    lab = check_labels(a.session, name)
    lab_t = check_labels(a.session, a.run)                          # oracle (tiles) scale labels
    lab_x = check_labels(a.session, name, exclude=set(flagged))
    lab_tx = check_labels(a.session, a.run, exclude=set(flagged))
    pct = (lambda v, f="+.1f": "-" if v is None else format(100 * v, f))
    L = [f"# Scale {a.method} on {a.session}, run {a.run}", "",
         "B is the scale on every segment; A (static ball) is only a cross-check: |s_A/s_B - 1| > "
         f"{100 * next((r['threshold'] for r in rows if r['threshold'] is not None), 0.10):.0f}% flags a segment "
         "(recorded only; s and the segment are kept).", "",
         "## Scale error vs the tile oracle (s/s_oracle - 1)", "",
         "| set | segments with a scale | compared (tile GT) | abs err median | abs err p90 | bias (median) |",
         "|---|---|---|---|---|---|",
         f"| all | {cov}/{len(rows)} | {st_all['n']} | {pct(st_all.get('abs_median'), '.1f')}% | "
         f"{pct(st_all.get('abs_p90'), '.1f')}% | {pct(st_all.get('bias_median'))}% |",
         f"| without flagged | {cov - len(flagged)}/{len(rows)} | {st_kept['n']} | {pct(st_kept.get('abs_median'), '.1f')}% | "
         f"{pct(st_kept.get('abs_p90'), '.1f')}% | {pct(st_kept.get('bias_median'))}% |", "",
         "## Cross-check A vs B", "",
         f"Segments where both A and B give a scale: {len(both)} ({', '.join(r['segment'] for r in both)}). "
         f"Flagged: {len(flagged)}" + (f" ({', '.join(flagged)})" if flagged else "") + ".", "",
         "| segment | A/B - 1 | A err vs oracle | B err vs oracle | flagged | which is wrong |",
         "|---|---|---|---|---|---|"]
    for r in both:
        wrong = "-"
        if r["flagged"] and r["err_A"] is not None and r["err_B"] is not None:
            wrong = "A" if abs(r["err_A"]) > abs(r["err_B"]) else "B"
        L.append(f"| {r['segment']} | {pct(r['ab_diff'])}% | {pct(r['err_A'])}% | {pct(r['err_B'])}% | "
                 f"{'yes' if r['flagged'] else ''} | {wrong} |")
    L += ["", "## Label error: tool_t->tool_t+dt position [mm], median / p90, vs tile labels", "",
          "| labels | anchors | " + " | ".join(f"{j / 15:.2f} s" for j in STEPS) + " |",
          "|---|---|" + "---|" * len(STEPS)]

    def lrow(title, res):
        b = res["by_step"]
        return (f"| {title} | {res['anchors']} | " + " | ".join(
            f"{b[j]['pos_mm_median']:.1f} / {b[j]['pos_mm_p90']:.1f}" if j in b else "-" for j in STEPS) + " |")
    L += [lrow(f"{a.run}, scale {a.method}", lab), lrow(f"{a.run}, tile (oracle) scale", lab_t)]
    if flagged:
        L += [lrow(f"{a.run}, scale {a.method}, without flagged", lab_x),
              lrow(f"{a.run}, tile scale, without flagged", lab_tx)]
    L += ["", "Label anchors exist only where the tile labels (>= 2 tiles, 70% coverage) also exist."]
    ev = C.WORK / a.session / "eval"
    ev.mkdir(parents=True, exist_ok=True)
    tag = a.method.replace(",", "+").replace(":", "-")
    (ev / f"scale_{a.run}_{tag}.md").write_text("\n".join(L) + "\n")
    json.dump({"rows": rows, "flagged": flagged, "scale_all": st_all, "scale_without_flagged": st_kept,
               "labels": lab, "labels_tiles": lab_t, "labels_without_flagged": lab_x,
               "labels_tiles_without_flagged": lab_tx}, open(ev / f"scale_{a.run}_{tag}.json", "w"),
              indent=1, default=float)
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["estimate", "eval", "crosscheck"])
    ap.add_argument("--session", required=True)
    ap.add_argument("--run", default="E3")
    ap.add_argument("--method", default="A")
    ap.add_argument("--methods", default="A;B;A,B", help="semicolon-separated specs")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    {"estimate": cmd_estimate, "eval": cmd_eval, "crosscheck": cmd_crosscheck}[a.cmd](a)


if __name__ == "__main__":
    main()
