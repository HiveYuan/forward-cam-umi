"""Physical-interpretation checks of the Bsession error claims (read only on the view)."""
import importlib.util, json, sys
from pathlib import Path
import numpy as np

REPO = Path("/home/student/yuanliu-hawaii/head-cam-umi-slam")
spec = importlib.util.spec_from_file_location("diag", REPO / "experiments/exp005_session_scale/diagnosis.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
from slam import scale as SC, geometry as G, evaluate as EV

VIEW = "/home/student/yuanliu-hawaii/work/runs/exp007_v2_session_scale/main/view"
OUT = Path(sys.argv[1])
root = D.configure(VIEW, "/home/student/yuanliu-hawaii/work/yam_glove7/gt")
diag = json.load(open(OUT.parent.parent / "diag_E3_v2.json"))
rows = {r["segment"]: r for r in diag["rows"]}
ks = diag["k_session"]["segments"]["k_session"]
res = {}
for seg in sorted(root.glob("ep[0-9][0-9]")):
    n = seg.name
    ctx, err = SC._depth_inputs(seg, "E3", D.MODEL)
    valid = SC._run_valid_cells(seg, ctx, ["motion", "tiles"], 8)
    W, H = ctx["size"]; S = ctx["S"]; z = ctx["z"]
    s_o = rows[n]["s_oracle"]
    # ball samples
    pr = np.array([(d, zt, i) for d, zt, i in SC.ball_depth_pairs(ctx)]).reshape(-1, 3)
    # tiles mask, motion mask
    tm = np.unpackbits(np.load(seg / "masks" / "tiles.npz")["masked"], axis=-1, count=W).astype(bool)
    mm = np.unpackbits(np.load(seg / "masks" / "motion.npz")["masked"], axis=-1, count=W).astype(bool)
    vc, uc = np.mgrid[0:H // 8, 0:W // 8]
    rays = np.linalg.inv(ctx["K"]) @ np.stack([8 * uc.ravel() + 3.5, 8 * vc.ravel() + 3.5, np.ones(uc.size)])
    T_sc = z["T_slam_cam"]
    kf_ok = np.isfinite(T_sc[ctx["kf_t"]]).all((1, 2))
    if "kf_pose_cw" in z.files:
        kf_ok &= np.isfinite(z["kf_pose_cw"]).all(1)
    bg_net, bg_droid, bg_t, tile_z, tile_r, rtab_z, rtab_r, rtab_frac, kf_R = [], [], [], [], [], [], [], [], []
    for j, i in enumerate(ctx["kf_t"]):
        d8 = ctx["depth"][j].astype(float).reshape(H // 8, 8, W // 8, 8).mean((1, 3))
        disp = ctx["disp"][j]
        zs = 1.0 / np.clip(disp, 1e-6, None)
        m = valid[i] & np.isfinite(d8) & (d8 > 0.1) & (d8 < 4.0) & (disp > 1e-3) & np.isfinite(disp)
        m[:1], m[-1:], m[:, :1], m[:, -1:] = False, False, False, False
        used = kf_ok[j] and m.sum() >= 200
        if used:
            bg_net.append(d8[m]); bg_droid.append(zs[m]); bg_t.append(np.full(m.sum(), i))
            kf_R.append((int(i), float(np.median(d8[m] / zs[m]))))
        if S["strict"][i]:
            T_cw = G.inv(S["T_wc"][i][None])[0]
            n_c, p_c = T_cw[:3, 2], T_cw[:3, 3]
            zp = ((n_c @ p_c) / (n_c @ rays)).reshape(H // 8, W // 8)
            cell = tm[i].reshape(H // 8, 8, W // 8, 8).all((1, 3)) & ~mm[i].reshape(H // 8, 8, W // 8, 8).any((1, 3))
            cell[:1], cell[-1:], cell[:, :1], cell[:, -1:] = False, False, False, False
            ok = cell & (zp > 0.1) & (zp < 4.0)
            if ok.sum() >= 20:
                tile_z.append(zp[ok]); tile_r.append(zp[ok] / d8[ok])
            if used and np.isfinite(s_o or np.nan):
                # R's own cells that lie on the table plane (DROID depth, oracle-scaled, within 10% of the plane)
                onp = m & (zp > 0.1) & (np.abs(s_o * zs / zp - 1) < 0.10)
                rtab_frac.append((int(onp.sum()), int(m.sum())))
                if onp.sum() >= 20:
                    rtab_z.append(zp[onp]); rtab_r.append(zp[onp] / d8[onp])
    cat = lambda a: np.concatenate(a) if a else np.zeros(0)
    bg_net, bg_droid, bg_t = cat(bg_net), cat(bg_droid), cat(bg_t)
    tile_z, tile_r, rtab_z, rtab_r = cat(tile_z), cat(tile_r), cat(rtab_z), cat(rtab_r)
    q = lambda a: [float(np.percentile(a, p)) for p in (10, 50, 90)] if len(a) else None
    e = {"k": rows[n]["k"], "k_need": rows[n]["k_need"], "k_tile": rows[n]["k_tile"], "tile_kf": rows[n]["tile_keyframes"],
         "s_o": s_o, "err": rows[n]["err_session"],
         "ball_z_q": q(pr[:, 1]) if len(pr) else None, "ball_netz_q": q(pr[:, 0]) if len(pr) else None,
         "bg_metric_net_q": q(ks * bg_net), "bg_metric_droid_q": q(s_o * bg_droid) if s_o else None,
         "tile_z_q": q(tile_z), "n_tile_cells": int(len(tile_z)),
         "rtab_cells_frac": (sum(a for a, _ in rtab_frac) / max(1, sum(b for _, b in rtab_frac))) if rtab_frac else None,
         "k_rtab": float(np.median(rtab_r)) if len(rtab_r) >= 50 else None, "rtab_z_q": q(rtab_z),
         "kf_R": kf_R}
    # correction vs depth: tile cells, R table cells, background with DROID*s_o as truth
    bins = [0.2, 0.35, 0.45, 0.55, 0.7, 0.9, 1.2, 1.6, 2.5, 4.0]
    def binned(zv, rv):
        out = []
        for a, b in zip(bins[:-1], bins[1:]):
            sel = (zv >= a) & (zv < b)
            out.append((a, b, int(sel.sum()), float(np.median(rv[sel])) if sel.sum() >= 30 else None))
        return out
    e["tile_curve"] = binned(tile_z, tile_r) if len(tile_z) else None
    e["rtab_curve"] = binned(rtab_z, rtab_r) if len(rtab_z) else None
    if s_o:
        e["bg_curve_droid"] = binned(s_o * bg_droid, s_o * bg_droid / bg_net)   # 'truth' = oracle-scaled DROID depth
        # within-episode log-log slope of truth/net vs truth on tile cells
    if len(tile_z) >= 100:
        e["tile_slope"] = float(np.polyfit(np.log(tile_z), np.log(tile_r), 1)[0])
        lo = tile_z < np.percentile(tile_z, 50)
        e["tile_k_near_far"] = [float(np.median(tile_r[lo])), float(np.median(tile_r[~lo])),
                                float(np.median(tile_z[lo])), float(np.median(tile_z[~lo]))]
        # bootstrap over keyframes is approximated by split-half over cells sorted by frame below
    # oracle on thirds with diagnostics
    Tsc = z["T_slam_cam"].astype(float)
    th = []
    for idx in np.array_split(np.arange(len(Tsc)), 3):
        mk = np.zeros(len(Tsc), bool); mk[idx] = True
        m3 = S["strict"] & mk & np.isfinite(Tsc).all((1, 2))
        info = {"strict": int(m3.sum())}
        if m3.sum() >= 10:
            s3, r3 = EV.segment_scale({**S, "strict": S["strict"] & mk}, Tsc)
            dst = S["T_wc"][m3, :3, 3]
            info.update(oracle=float(s3), res_mm=1000 * float(r3),
                        travel_mm=1000 * float(np.linalg.norm(dst - dst.mean(0), axis=1).max()),
                        rms_travel_mm=1000 * float(np.sqrt(((dst - dst.mean(0)) ** 2).sum(1).mean())))
            rng = np.random.default_rng(1); bs = []
            ii = np.where(m3)[0]
            for _ in range(300):
                pick = rng.choice(ii, len(ii)); st = np.zeros(len(Tsc), bool); st[pick] = True
                src, dd = Tsc[pick, :3, 3], S["T_wc"][pick, :3, 3]
                try:
                    bs.append(G.umeyama_scale(src, dd)[0])
                except Exception:
                    pass
            info["boot_sd_rel"] = float(np.std(np.log(bs)))
        # network-based scale (k_s * median d_net / z_droid) of the keyframes in this third: independent of tiles
        kr = [r for i, r in kf_R if idx[0] <= i <= idx[-1]]
        info["net_scale"] = float(ks * np.median(kr)) if kr else None
        info["n_kf"] = len(kr)
        th.append(info)
    e["thirds"] = th
    mall = S["strict"] & np.isfinite(Tsc).all((1, 2))
    if mall.sum() >= 10:
        so, ro = EV.segment_scale(S, Tsc)
        e["oracle_res_mm"] = 1000 * ro
        dst = S["T_wc"][mall, :3, 3]
        e["oracle_travel_mm"] = 1000 * float(np.linalg.norm(dst - dst.mean(0), axis=1).max())
        e["n_strict"] = int(mall.sum())
    res[n] = e
    print(n, "done", flush=True)
json.dump(res, open(OUT, "w"), indent=1, default=float)
