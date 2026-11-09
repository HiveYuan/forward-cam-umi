"""exp005 step 1: where does the long tail of scale method B come from?

Method B is s = k * R per segment: k = median(metric / network depth) over the ball samples,
R = median(network depth / DROID depth) over the mask-valid background cells of the keyframes
(the cell selection does not move with k here, so s is exactly linear in k). With the tile
oracle s_o, the k the segment needed is k_need = s_o / R, and with the session's k_s
(median of the per-segment k):

    1 + err_B = k / k_need = (k / k_s) * (k_s / k_need)
      (a) k / k_s       the segment's own k deviates from the session's: pooling k removes it
      (b) k_need / k_s  the segment needs another correction than the session's: pooling k
                        cannot remove it (err with k_s = k_s / k_need - 1)

What (b) is, from the tiles as ground truth of the background: the table plane (tile pose of
the keyframe) gives the true depth on the tile cells (1/8 cells fully inside the tile mask and
outside the motion mask), so
    k_tile        = median(true depth / network depth) on them: the network's true correction
                    at the table, to compare with k (ball) and k_need;
    droid_vs_tile = median(true depth / DROID depth) / s_o - 1: DROID's depth on the table vs
                    its own trajectory scale (only meaningful where the run does not mask the
                    tiles, i.e. E2; E3 masks them, so DROID's depth there is unconstrained);
    oracle_thirds = the tile oracle on each third of the segment (DROID scale consistency).

Run on the analysis view of a finished run (read only; writes only --out):
  V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
  PYTHONPATH=. $V experiments/exp005_session_scale/diagnosis.py \
      --view <work>/runs/exp005_session_scale/main/view --run E3 --masks motion,tiles --out diag_E3.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

from slam import config as C
from slam import evaluate as EV
from slam import geometry as G
from slam import scale as SC

SESSION = "yam_glove7"
MODEL = "da2-metric-indoor-large"
B_PARAMS = {"z_max": 4.0, "min_cells": 200, "depth_window": None}     # exp003 / exp005 B parameters


def configure(view, gt_dir):
    """slam.config for the view (as slam.pipeline.worker.configure does)."""
    C.SESSIONS[SESSION] = {"head_stem": "yam_glove7_b0587b", "intrinsics": "B0587b_f3_intrinsics.json",
                           "glove": "yosub", "tile_layout": "workspace_tiles_pilot_v3.json"}
    C.WORK = Path(view)
    orig = C.gt_dir
    C.gt_dir = lambda name: Path(gt_dir) if name == SESSION else orig(name)
    return C.segments_dir(SESSION)


def ratio_scale(ctx, valid, k):
    """B's s for correction k (fit scale): median of k D_net / z_slam over the background
    -> (s, keyframes used, background cells used)."""
    r, per = SC.background_ratios(ctx, valid, k, 0.0, **B_PARAMS)
    return (float(np.median(np.concatenate(r))) if r else float("nan")), len(per), int(sum(len(x) for x in r))


def tile_truth(seg, ctx, s_o):
    """k_tile, DROID depth vs trajectory on the tile cells (table plane z = 0 of the tile layout)."""
    W, H = ctx["size"]
    S = ctx["S"]
    tm = np.unpackbits(np.load(seg / "masks" / "tiles.npz")["masked"], axis=-1, count=W).astype(bool)
    mm = np.unpackbits(np.load(seg / "masks" / "motion.npz")["masked"], axis=-1, count=W).astype(bool)
    vc, uc = np.mgrid[0:H // 8, 0:W // 8]
    rays = np.linalg.inv(ctx["K"]) @ np.stack([8 * uc.ravel() + 3.5, 8 * vc.ravel() + 3.5, np.ones(uc.size)])
    kt, st, n_kf = [], [], 0
    for j, i in enumerate(ctx["kf_t"]):
        if not S["strict"][i]:
            continue
        T_cw = G.inv(S["T_wc"][i][None])[0]
        n_c, p_c = T_cw[:3, 2], T_cw[:3, 3]
        z = ((n_c @ p_c) / (n_c @ rays)).reshape(H // 8, W // 8)          # depth of the table plane
        cell = tm[i].reshape(H // 8, 8, W // 8, 8).all((1, 3)) & ~mm[i].reshape(H // 8, 8, W // 8, 8).any((1, 3))
        cell[:1], cell[-1:], cell[:, :1], cell[:, -1:] = False, False, False, False
        ok = cell & (z > 0.1) & (z < 4.0)
        if ok.sum() < 20:
            continue
        n_kf += 1
        d8 = ctx["depth"][j].astype(float).reshape(H // 8, 8, W // 8, 8).mean((1, 3))
        disp = ctx["disp"][j]
        good = ok & np.isfinite(disp) & (disp > 1e-3)
        kt.append(z[ok] / d8[ok])
        st.append(z[good] * disp[good])
    k_tile = float(np.median(np.concatenate(kt))) if kt else float("nan")
    s_tile = float(np.median(np.concatenate(st))) if st else float("nan")
    return k_tile, n_kf, s_tile / s_o - 1 if np.isfinite(s_o) else float("nan")


def oracle_thirds(ctx):
    S, T = ctx["S"], ctx["z"]["T_slam_cam"].astype(float)
    out = []
    for idx in np.array_split(np.arange(len(T)), 3):
        m = np.zeros(len(T), bool)
        m[idx] = True
        s3, _ = EV.segment_scale({**S, "strict": S["strict"] & m}, T)
        out.append({"oracle": float(s3), "strict_frames": int((S["strict"] & m).sum())})
    return out


def diagnose(segs, run, masks):
    ctxs, valids, samples = {}, {}, {}
    for seg in segs:
        ctx, err = SC._depth_inputs(seg, run, MODEL)
        if err is not None:
            raise RuntimeError(f"{seg.name}: {err['error']}")
        ctxs[seg.name] = ctx
        valids[seg.name] = SC._run_valid_cells(seg, ctx, masks, 8)
        samples[seg.name] = np.array([(d, z) for d, z, _ in SC.ball_depth_pairs(ctx)]).reshape(-1, 2)
    sess = {p: SC.session_k(samples, p) for p in SC.SESSION_POOLS}
    ks = sess["segments"]["k_session"]
    rows = []
    for seg in segs:
        n, ctx, valid = seg.name, ctxs[seg.name], valids[seg.name]
        pr = samples[n]
        k = float(np.median(pr[:, 1] / pr[:, 0])) if len(pr) else float("nan")
        o = SC.scale_tiles(seg, run)
        s_o = float(o["s"]) if o.get("ok") else float("nan")
        R, n_kf, n_cells = ratio_scale(ctx, valid, 1.0)
        s_b = ratio_scale(ctx, valid, k)[0] if np.isfinite(k) else float("nan")
        s_s = ratio_scale(ctx, valid, ks)[0]
        s_s2 = ratio_scale(ctx, valid, sess["samples"]["k_session"])[0]
        k_tile, n_tile, droid_vs_tile = tile_truth(seg, ctx, s_o)
        rel = (lambda s: s / s_o - 1 if np.isfinite(s) and np.isfinite(s_o) else None)
        rows.append({"segment": n, "k": k, "ball_samples": int(len(pr)), "z_ball_m": float(np.median(pr[:, 1])) if len(pr) else None,
                     "keyframes_used": n_kf, "background_cells": n_cells, "s_oracle": s_o if np.isfinite(s_o) else None,
                     "oracle_align_res_mm": o.get("align_res_mm"), "R": R,
                     "k_need": s_o / R if np.isfinite(s_o) else None, "s_B": s_b, "err_B": rel(s_b),
                     "s_session": s_s, "err_session": rel(s_s), "err_session_pool_samples": rel(s_s2),
                     "k_dev": k / ks - 1 if np.isfinite(k) else None,
                     "k_need_dev": s_o / R / ks - 1 if np.isfinite(s_o) else None,
                     "k_tile": k_tile if np.isfinite(k_tile) else None, "tile_keyframes": n_tile,
                     "droid_depth_vs_trajectory_on_tiles": droid_vs_tile if np.isfinite(droid_vs_tile) else None,
                     "oracle_thirds": oracle_thirds(ctx),
                     "max_rel_s_B_minus_kR": abs(s_b - k * R) / s_b if np.isfinite(s_b) else None})
    return {"run": run, "masks": masks, "k_session": sess, "rows": rows, "summary": summarize(rows, ks)}


def _stats(e):
    e = 100 * np.asarray(e, float)
    return {"n": int(len(e)), "abs_median": float(np.median(np.abs(e))), "abs_p90": float(np.percentile(np.abs(e), 90)),
            "bias_median": float(np.median(e)), "rms": float(np.sqrt(np.mean(e ** 2))), "abs_max": float(np.abs(e).max()),
            "n_over_10": int((np.abs(e) > 10).sum()), "n_over_20": int((np.abs(e) > 20).sum())}


def summarize(rows, ks):
    R = [r for r in rows if r["s_oracle"] is not None]
    k = np.array([r["k"] for r in R])
    kn = np.array([r["k_need"] for r in R])
    a, b = np.log(k / ks), np.log(kn / ks)
    cab = float(np.cov(a, b, bias=True)[0, 1])
    eb, es = np.array([r["err_B"] for r in R]), np.array([r["err_session"] for r in R])
    debias = (lambda e: (1 + e) / np.exp(np.median(np.log1p(e))) - 1)
    T = [r for r in R if r["tile_keyframes"] >= 5]
    lt, lk, lkn = (np.log([r[x] for r in T]) for x in ("k_tile", "k", "k_need"))
    dv = np.array([r["droid_depth_vs_trajectory_on_tiles"] for r in R if r["droid_depth_vs_trajectory_on_tiles"] is not None])
    return {
        "B": _stats(eb), "Bsession": _stats(es),
        "Bsession_pool_samples": _stats([r["err_session_pool_samples"] for r in R]),
        "in_sample_debiased": {"B": _stats(debias(eb)), "Bsession": _stats(debias(es))},
        "pooling_helps": int((np.abs(es) < np.abs(eb) - 0.02).sum()),
        "pooling_hurts": int((np.abs(es) > np.abs(eb) + 0.02).sum()),
        "var_log_errB": float(np.var(a - b)), "var_a_k_dev": float(np.var(a)), "var_b_k_need_dev": float(np.var(b)),
        "two_cov_ab": 2 * cab, "corr_ab": float(np.corrcoef(a, b)[0, 1]),
        "best_shrinkage_slope": cab / float(np.var(a)), "best_shrinkage_resid_var": float(np.var(b) - cab ** 2 / np.var(a)),
        "median_k_need": float(np.median(kn)), "k_session_vs_median_k_need": float(ks / np.median(kn) - 1),
        "tile_segments": len(T), "corr_log_k_tile_k_need": float(np.corrcoef(lt, lkn)[0, 1]),
        "corr_log_k_tile_k_ball": float(np.corrcoef(lt, lk)[0, 1]),
        "median_abs_k_need_over_k_tile": float(np.median(np.abs(np.exp(lkn - lt) - 1))),
        "median_abs_k_ball_over_k_tile": float(np.median(np.abs(np.exp(lk - lt) - 1))),
        "sd_log_k_tile": float(np.std(lt)),
        "droid_vs_tile_abs_median": float(np.median(np.abs(dv))) if len(dv) else None,
        "droid_vs_tile_abs_p90": float(np.percentile(np.abs(dv), 90)) if len(dv) else None,
        "corr_background_cells_err_session": float(np.corrcoef([r["background_cells"] for r in R], es)[0, 1]),
        "corr_ball_depth_err_session": float(np.corrcoef([r["z_ball_m"] for r in R], es)[0, 1]),
        "max_rel_s_B_minus_kR": max(r["max_rel_s_B_minus_kR"] for r in R),
    }


def table(res):
    f = (lambda x: "-" if x is None or not np.isfinite(x) else f"{100 * x:+.1f}")
    L = ["| segment | own k (samples) | k/k_s - 1 % | k_need/k_s - 1 % | k_tile (tile kf) | err B % | err Bsession % |",
         "|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        kt = f"{r['k_tile']:.3f} ({r['tile_keyframes']})" if r["k_tile"] is not None else "-"
        L.append(f"| {r['segment']} | {r['k']:.3f} ({r['ball_samples']}) | {f(r['k_dev'])} | {f(r['k_need_dev'])} | {kt} | "
                 f"{f(r['err_B'])} | {f(r['err_session'])} |")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", required=True, help="analysis view root (<work>/runs/<exp>/main/view)")
    ap.add_argument("--run", default="E3")
    ap.add_argument("--masks", default="motion,tiles", help="the run's masks (B's background cells)")
    ap.add_argument("--gt-dir", default="/home/student/yuanliu-hawaii/work/yam_glove7/gt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root = configure(a.view, a.gt_dir)
    segs = sorted(root.glob("ep[0-9][0-9]"))
    res = diagnose(segs, a.run, [m for m in a.masks.split(",") if m])
    s = res["summary"]
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(table(res))
    print(json.dumps({k: v for k, v in s.items() if not isinstance(v, dict)}, indent=1, default=float))
    for m in ("B", "Bsession", "Bsession_pool_samples"):
        print(m, json.dumps(s[m]))


if __name__ == "__main__":
    main()
