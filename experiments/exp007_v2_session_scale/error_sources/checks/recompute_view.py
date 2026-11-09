"""Independent recompute from the analysis view (read only). Writes only a JSON next to this script."""
import json, sys, glob
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/student/yuanliu-hawaii/head-cam-umi-slam/experiments/exp005_session_scale")
import diagnosis as DG
from slam import scale as SC, evaluate as EV, geometry as G

VIEW = "/home/student/yuanliu-hawaii/work/runs/exp007_v2_session_scale/main/view"
root = DG.configure(VIEW, "/home/student/yuanliu-hawaii/work/yam_glove7/gt")
segs = sorted(root.glob("ep[0-9][0-9]"))
MODEL = "da2-metric-indoor-large"
out = {}
ks_list = {}
ctxs = {}
for seg in segs:
    ctx, err = SC._depth_inputs(seg, "E3", MODEL)
    assert err is None, err
    ctxs[seg.name] = ctx
    pr = np.array([(d, z) for d, z, _ in SC.ball_depth_pairs(ctx)]).reshape(-1, 2)
    ks_list[seg.name] = pr
k_own = {n: float(np.median(p[:, 1] / p[:, 0])) for n, p in ks_list.items() if len(p)}
ks = float(np.median(list(k_own.values())))
print("k_session recomputed", ks, "n", len(k_own))
for seg in segs:
    n = seg.name; ctx = ctxs[n]
    valid = SC._run_valid_cells(seg, ctx, ["motion", "tiles"], 8)
    r1, pk1 = SC.background_ratios(ctx, valid, 1.0, 0.0, 4.0, 200, None)
    rk, pkk = SC.background_ratios(ctx, valid, ks, 0.0, 4.0, 200, None)
    R = float(np.median(np.concatenate(r1)))
    s_sess = float(np.median(np.concatenate(rk)))
    # gate crossing: cells valid & disp ok whose network depth lies where the gates differ
    W, H = ctx["size"]; nx = 0; nall = 0; bg_depth = []
    for j, i in enumerate(ctx["kf_t"]):
        d8 = ctx["depth"][j].astype(float).reshape(H // 8, 8, W // 8, 8).mean((1, 3))
        m = valid[i] & np.isfinite(d8) & (ctx["disp"][j] > 1e-3) & np.isfinite(ctx["disp"][j])
        m[:1], m[-1:], m[:, :1], m[:, -1:] = False, False, False, False
        g1 = (d8 > 0.1) & (d8 < 4.0); gk = (ks * d8 > 0.1) & (ks * d8 < 4.0)
        nx += int((m & (g1 != gk)).sum()); nall += int(m.sum())
        bg_depth.append(ks * d8[m & gk])
    bg = np.concatenate(bg_depth) if bg_depth else np.array([np.nan])
    S = ctx["S"]; T = ctx["z"]["T_slam_cam"].astype(float)
    s_o, res = EV.segment_scale(S, T)
    # table depth on tile cells (true plane depth) and the ball's metric depth
    tm = np.unpackbits(np.load(seg / "masks" / "tiles.npz")["masked"], axis=-1, count=W).astype(bool)
    mm = np.unpackbits(np.load(seg / "masks" / "motion.npz")["masked"], axis=-1, count=W).astype(bool)
    vc, uc = np.mgrid[0:H // 8, 0:W // 8]
    rays = np.linalg.inv(ctx["K"]) @ np.stack([8 * uc.ravel() + 3.5, 8 * vc.ravel() + 3.5, np.ones(uc.size)])
    zt, kt = [], []
    for j, i in enumerate(ctx["kf_t"]):
        if not S["strict"][i]:
            continue
        Tcw = G.inv(S["T_wc"][i][None])[0]
        nc, pc = Tcw[:3, 2], Tcw[:3, 3]
        z = ((nc @ pc) / (nc @ rays)).reshape(H // 8, W // 8)
        cell = tm[i].reshape(H // 8, 8, W // 8, 8).all((1, 3)) & ~mm[i].reshape(H // 8, 8, W // 8, 8).any((1, 3))
        cell[:1], cell[-1:], cell[:, :1], cell[:, -1:] = False, False, False, False
        ok = cell & (z > 0.1) & (z < 4.0)
        if ok.sum() < 20:
            continue
        d8 = ctx["depth"][j].astype(float).reshape(H // 8, 8, W // 8, 8).mean((1, 3))
        zt.append(z[ok]); kt.append(z[ok] / d8[ok])
    pr = ks_list[n]
    scache = glob.glob(str(seg / "scale" / "E3_Bsession_*.json"))
    sc = json.load(open(scache[0]))["s"] if scache else None
    tc = json.load(open(seg / "scale" / "E3_tiles.json"))["s"] if (seg / "scale" / "E3_tiles.json").exists() else None
    out[n] = {"k": k_own.get(n), "R": R, "s_sess": s_sess, "s_o": float(s_o), "res": res, "gate_cross": nx, "cells": nall,
              "same_kf": len(pk1) == len(pkk), "bg_med": float(np.nanmedian(bg)), "bg_p25": float(np.nanpercentile(bg, 25)),
              "bg_p75": float(np.nanpercentile(bg, 75)),
              "ball_z_med": float(np.median(pr[:, 1])) if len(pr) else None,
              "ball_z_min": float(pr[:, 1].min()) if len(pr) else None, "ball_z_max": float(pr[:, 1].max()) if len(pr) else None,
              "table_z_med": float(np.median(np.concatenate(zt))) if zt else None,
              "k_tile": float(np.median(np.concatenate(kt))) if kt else None, "tile_kf": len(kt),
              "cache_s_sess": sc, "cache_s_o": tc}
    print(n, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out[n].items()})
json.dump({"ks": ks, "eps": out}, open(Path(__file__).with_name("view_recompute.json"), "w"), indent=1)
