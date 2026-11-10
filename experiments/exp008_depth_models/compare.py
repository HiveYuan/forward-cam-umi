"""exp008 post-hoc comparison of the depth networks (read only: the run's results/ and its view).

Per network (E3 alias):
  scale     Bsession / B / Bnet error vs the tile oracle (results/scale_<alias>.json), on all episodes with
            tile GT (28) and on the 22 with >= 3 tile-visible keyframes (exp007 error_sources list):
            |err| median / p90, bias (median), spread (sd of log(1 + err)), rms, episodes > 10% / > 20%.
  k         k_session (Bsession), sd over episodes of log k (own ball correction) and of log k_need =
            log(s_oracle / R), R = Bnet's s (median network / DROID depth on the background). For
            Bsession, 1 + err = k_session / k_need, so sd(log k_need) is Bsession's spread.
  labels    tool-label position error with Bsession (results/metrics.json): 1 s, 2 s, chunk H = 100 mean.
  table     without SLAM: true depth (tile plane, strict tile pose) / network depth on tile cells of the
            keyframes (cells fully inside a tile, not motion-masked, as exp007's physics check):
            pooled median (raw bias), per-episode median -> sd of log over episodes (spread), within-
            episode log-log slope vs true depth (depth dependence), |1 - ratio| median after dividing
            each keyframe by its own median (shape error).
  focal     where the network estimates its own focal (fx_pred in depth.npz): median, p10-p90 vs K's fx.

  V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
  PYTHONPATH=. $V experiments/exp008_depth_models/compare.py
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
VIEW = "/home/student/yuanliu-hawaii/work/runs/exp008_depth_models/main/view"
GT = "/home/student/yuanliu-hawaii/work/yam_glove7/gt"
ALIASES = {"E3_da2": "DA2 metric indoor (no K)", "E3_uniK": "UniDepth V2 + K", "E3_uni": "UniDepth V2, own camera",
           "E3_m3d": "Metric3D v2 + K", "E3_da3m": "DA3 metric + K", "E3_moge": "MoGe-2 (fov from K)",
           "E3_dproK": "Depth Pro + K", "E3_dpro": "Depth Pro, own FOV"}
KEEP22 = json.load(open(REPO / "experiments/exp007_v2_session_scale/error_sources/tile_keyframes.json"))["keep"]


def err_stats(errs):
    e = np.array([x for x in errs if x is not None], float)
    if not len(e):
        return None
    lg = np.log1p(e)
    return {"n": int(len(e)), "abs_median": float(np.median(np.abs(e))), "abs_p90": float(np.percentile(np.abs(e), 90)),
            "bias_median": float(np.median(e)), "spread_sd_log": float(np.std(lg, ddof=1)) if len(e) > 1 else None,
            "rms": float(np.sqrt(np.mean(e ** 2))), "max_abs": float(np.max(np.abs(e))),
            "n_gt10": int((np.abs(e) > 0.10).sum()), "n_gt20": int((np.abs(e) > 0.20).sum())}


def sd_log(x):
    x = np.array([v for v in x if v is not None and np.isfinite(v) and v > 0], float)
    return float(np.std(np.log(x), ddof=1)) if len(x) > 1 else None


def scale_part(res, alias):
    sj = json.load(open(res / f"scale_{alias}.json"))
    out = {"k_session": sj["session"]["Bsession"]["k_session"]}
    rows = {r["segment"]: r for r in sj["rows"]}
    per = {}
    for seg, r in rows.items():
        so = r["oracle_s"]
        bn = r["checks"]["Bnet"]
        per[seg] = {"oracle": so, "err_Bsession": r["err"], "err_B": r["checks"]["B"]["err"], "err_Bnet": bn["err"],
                    "k_own": r["primary"].get("k_ball"), "R": bn["s"] if bn["ok"] else None,
                    "k_need": (so / bn["s"]) if (so and bn["ok"] and bn["s"]) else None}
    for subset, segs in (("all", list(per)), ("keep22", KEEP22)):
        o = {}
        for m in ("Bsession", "B", "Bnet"):
            o[m] = err_stats([per[s][f"err_{m}"] for s in segs if s in per])
        o["k_own_sd_log"] = sd_log([per[s]["k_own"] for s in segs if s in per and per[s]["oracle"]])
        o["k_need_sd_log"] = sd_log([per[s]["k_need"] for s in segs if s in per])
        o["k_need_median"] = float(np.median([per[s]["k_need"] for s in segs if s in per and per[s]["k_need"]]))
        out[subset] = o
    out["per_segment"] = per
    return out


def label_part(metrics, alias):
    r = metrics["runs"][alias]
    lab = [k for k in r["labels"] if k != "oracle"][0]
    bs = r["labels"][lab]["by_step"]
    ch = r["chunk"][lab]
    return {"label": lab, "anchors": r["labels"][lab]["anchors"],
            "1s": [bs["15"]["pos_mm_median"], bs["15"]["pos_mm_p90"]], "2s": [bs["30"]["pos_mm_median"], bs["30"]["pos_mm_p90"]],
            "chunk100_mean": ch["100"]["pos_mm_mean"], "chunk30_mean": ch["30"]["pos_mm_mean"],
            "oracle_1s": [r["labels"]["oracle"]["by_step"]["15"]["pos_mm_median"], r["labels"]["oracle"]["by_step"]["15"]["pos_mm_p90"]],
            "oracle_chunk100_mean": r["chunk"]["oracle"]["100"]["pos_mm_mean"]}


def table_part(root, alias, model):
    from slam import scale as SC, geometry as G
    pooled_r, pooled_z, per_seg, shape, slopes = [], [], {}, [], []
    fx_pred = []
    for seg in sorted(root.glob("ep[0-9][0-9]")):
        ctx, err = SC._depth_inputs(seg, alias, model)
        if err is not None:
            raise RuntimeError(f"{seg.name} {alias}: {err}")
        D = np.load(seg / "depth" / f"{alias}_{model}.npz")
        if "fx_pred" in D.files:
            fx_pred += [float(x) for x in D["fx_pred"] if np.isfinite(x)]
        S, K = ctx["S"], ctx["K"]
        W, H = ctx["size"]
        tm = np.unpackbits(np.load(seg / "masks" / "tiles.npz")["masked"], axis=-1, count=W).astype(bool)
        mm = np.unpackbits(np.load(seg / "masks" / "motion.npz")["masked"], axis=-1, count=W).astype(bool)
        vc, uc = np.mgrid[0:H // 8, 0:W // 8]
        rays = np.linalg.inv(K) @ np.stack([8 * uc.ravel() + 3.5, 8 * vc.ravel() + 3.5, np.ones(uc.size)])
        rs, zs = [], []
        for j, i in enumerate(ctx["kf_t"]):
            if not S["strict"][i]:
                continue
            d8 = ctx["depth"][j].astype(float).reshape(H // 8, 8, W // 8, 8).mean((1, 3))
            T_cw = G.inv(S["T_wc"][i][None])[0]
            n_c, p_c = T_cw[:3, 2], T_cw[:3, 3]
            zp = ((n_c @ p_c) / (n_c @ rays)).reshape(H // 8, W // 8)
            cell = tm[i].reshape(H // 8, 8, W // 8, 8).all((1, 3)) & ~mm[i].reshape(H // 8, 8, W // 8, 8).any((1, 3))
            cell[:1], cell[-1:], cell[:, :1], cell[:, -1:] = False, False, False, False
            ok = cell & (zp > 0.1) & (zp < 4.0) & np.isfinite(d8) & (d8 > 0)
            if ok.sum() < 20:
                continue
            r = zp[ok] / d8[ok]
            rs.append(r); zs.append(zp[ok])
            shape.append(np.abs(r / np.median(r) - 1))
        if rs:
            r, z = np.concatenate(rs), np.concatenate(zs)
            per_seg[seg.name] = {"k_tile": float(np.median(r)), "cells": int(len(r)), "keyframes": len(rs),
                                 "z_median": float(np.median(z))}
            pooled_r.append(r); pooled_z.append(z)
            if len(r) >= 100 and np.ptp(np.log(z)) > 0.2:
                slopes.append(float(np.polyfit(np.log(z), np.log(r), 1)[0]))
    r, z = np.concatenate(pooled_r), np.concatenate(pooled_z)
    bins = [0.35, 0.55, 0.7, 0.9, 1.2, 1.6]
    curve = []
    for a, b in zip(bins[:-1], bins[1:]):
        sel = (z >= a) & (z < b)
        curve.append([a, b, int(sel.sum()), float(np.median(r[sel])) if sel.sum() >= 30 else None])
    kt = [v["k_tile"] for v in per_seg.values()]
    kt22 = [per_seg[s]["k_tile"] for s in KEEP22 if s in per_seg]
    out = {"pooled_median": float(np.median(r)), "cells": int(len(r)), "episodes": len(per_seg),
           "k_tile_sd_log": sd_log(kt), "k_tile_sd_log_keep22": sd_log(kt22),
           "slope_median": float(np.median(slopes)) if slopes else None, "n_slopes": len(slopes),
           "shape_abs_median": float(np.median(np.concatenate(shape))), "curve": curve, "per_segment": per_seg}
    if fx_pred:
        out["fx_pred"] = {"n": len(fx_pred), "median": float(np.median(fx_pred)),
                          "p10": float(np.percentile(fx_pred, 10)), "p90": float(np.percentile(fx_pred, 90)),
                          "sd_log": sd_log(fx_pred)}
    return out


def main():
    spec = importlib.util.spec_from_file_location("diag", REPO / "experiments/exp005_session_scale/diagnosis.py")
    Dg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(Dg)
    root = Dg.configure(VIEW, GT)
    res = EXP / "results"
    metrics = json.load(open(res / "metrics.json"))
    cfg = __import__("yaml").safe_load(open(EXP / "config.yaml"))
    out = {}
    for alias, title in ALIASES.items():
        dn = cfg["scale"][alias]["methods"]["Bsession"]["depth"]
        model = cfg["depth"][dn]["params"]["model"]
        out[alias] = {"title": title, "model": model, "scale": scale_part(res, alias),
                      "labels": label_part(metrics, alias), "table": table_part(root, alias, model)}
        print(alias, "done", flush=True)
    K = json.load(open(root / "ep00" / "frames.json"))["K"]
    out["_meta"] = {"fx_true": K[0][0], "keep22": KEEP22}
    json.dump(out, open(EXP / "compare.json", "w"), indent=1, default=float)
    write_md(out)


def write_md(o):
    p = lambda v, f="+.1f": "-" if v is None else format(100 * v, f)
    n = lambda v, f=".3f": "-" if v is None else format(v, f)
    A = [a for a in o if not a.startswith("_")]
    L = ["# exp008: depth networks compared (post-hoc, `compare.py`)", ""]
    for subset, title in (("keep22", "22 episodes with >= 3 tile-visible keyframes"), ("all", "all 28 episodes with tile GT")):
        L += [f"## Scale error vs the tile oracle, {title}", "",
              "| network | Bsession \\|err\\| med / p90 | bias | spread (sd log) | >10% / >20% | B \\|err\\| med / p90 | B spread | "
              "Bnet (no ball) \\|err\\| med / p90 | Bnet bias | Bnet spread | k_session |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for a in A:
            s = o[a]["scale"]
            bs, b, bn = s[subset]["Bsession"], s[subset]["B"], s[subset]["Bnet"]
            L.append(f"| {o[a]['title']} | {p(bs['abs_median'], '.1f')} / {p(bs['abs_p90'], '.1f')} | {p(bs['bias_median'])} | "
                     f"{p(bs['spread_sd_log'], '.1f')} | {bs['n_gt10']} / {bs['n_gt20']} | {p(b['abs_median'], '.1f')} / "
                     f"{p(b['abs_p90'], '.1f')} | {p(b['spread_sd_log'], '.1f')} | {p(bn['abs_median'], '.1f')} / "
                     f"{p(bn['abs_p90'], '.1f')} | {p(bn['bias_median'])} | {p(bn['spread_sd_log'], '.1f')} | {n(s['k_session'])} |")
        L.append("")
    L += ["## Labels with Bsession (position error, mm; 989 anchors in exp007)", "",
          "| network | 1 s median / p90 | 2 s median / p90 | chunk H=30 mean | chunk H=100 mean |", "|---|---|---|---|---|"]
    for a in A:
        lb = o[a]["labels"]
        L.append(f"| {o[a]['title']} | {lb['1s'][0]:.1f} / {lb['1s'][1]:.1f} | {lb['2s'][0]:.1f} / {lb['2s'][1]:.1f} | "
                 f"{lb['chunk30_mean']:.1f} | {lb['chunk100_mean']:.1f} |")
    lb = o[A[0]]["labels"]
    L += [f"| oracle scale | {lb['oracle_1s'][0]:.1f} / {lb['oracle_1s'][1]:.1f} | | | {lb['oracle_chunk100_mean']:.1f} |", ""]
    L += ["## Without SLAM: true / network depth on tile cells", "",
          "| network | pooled median (1 = metric) | spread over episodes (sd log; 22) | depth slope (log-log, median) | "
          "shape \\|err\\| median | 0.35-0.55 / 0.55-0.7 / 0.7-0.9 / 0.9-1.2 / 1.2-1.6 m |", "|---|---|---|---|---|---|"]
    for a in A:
        t = o[a]["table"]
        cv = " / ".join(n(c[3]) for c in t["curve"])
        L.append(f"| {o[a]['title']} | {n(t['pooled_median'])} | {p(t['k_tile_sd_log'], '.1f')} ({p(t['k_tile_sd_log_keep22'], '.1f')}) | "
                 f"{n(t['slope_median'], '+.3f')} | {p(t['shape_abs_median'], '.1f')} | {cv} |")
    L += ["", "## Own focal estimates (networks run without K)", "", f"K's fx = {o['_meta']['fx_true']:.1f} px.", "",
          "| network | keyframes | median | p10 - p90 | sd log |", "|---|---|---|---|---|"]
    for a in A:
        f = o[a]["table"].get("fx_pred")
        if f and a in ("E3_uni", "E3_dpro", "E3_uniK", "E3_dproK"):
            L.append(f"| {o[a]['title']} | {f['n']} | {f['median']:.1f} | {f['p10']:.1f} - {f['p90']:.1f} | {p(f['sd_log'], '.1f')} |")
    L += ["", "## Ball correction vs what each episode needed (sd of log over episodes)", "",
          "| network | own k (ball), 22 | k_need, 22 | k_need median, 22 |", "|---|---|---|---|"]
    for a in A:
        s = o[a]["scale"]["keep22"]
        L.append(f"| {o[a]['title']} | {p(s['k_own_sd_log'], '.1f')} | {p(s['k_need_sd_log'], '.1f')} | {n(s['k_need_median'])} |")
    open(EXP / "compare.md", "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
