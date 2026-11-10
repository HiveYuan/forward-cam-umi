"""Cross-session comparison of the scale: the current default (DA2 metric indoor + Bsession, ball corrected,
pooled per session) vs the candidate (DA3 metric + K, Bnet: the network's depth as is, no ball), on glove7
(exp007 / exp009), glove8 (exp010) and glove6 take 1 (exp012). Read only: each experiment's results/ and analysis view.

Per session and pooled over all sessions:
  scale    error vs the tile-fitted scale per episode (results/scale_<run>.json): |err| median / p90, bias
           (signed median), spread (sd of log(1 + err)), episodes > 10% / > 20%; on all episodes with a
           tile-fitted scale and on those with >= 3 tile-visible keyframes (DROID keyframes with a strict tile
           pose, as exp007/error_sources/tile_keyframes.json).
  labels   tool-label position error vs the tile labels, per anchor (slam.labels.anchor_errors on the view's
           label files, the framework's own computation): 1 s and 2 s median / p90, chunk H = 100 mean; with the
           tile-fitted (oracle) scale for reference.

  V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
  PYTHONPATH=. $V experiments/cross_session/summarize.py
"""
import importlib.util
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUNS = Path("/home/student/yuanliu-hawaii/work/runs")
# label, session, default (experiment, run, scale label), candidate (experiment, run, scale label)
SESSIONS = [
    ("glove6 take 1", "yam_glove6_take1", ("exp012_glove6_take1", "E3_da2", "Bsession+Acheck"),
     ("exp012_glove6_take1", "E3_da3m", "Bnet+Acheck")),
    ("glove7", "yam_glove7", ("exp007_v2_session_scale", "E3", "Bsession+Acheck"),
     ("exp009_net_scale", "E3_da3m", "Bnet+Acheck")),
    ("glove8", "yam_glove8", ("exp010_glove8", "E3_da2", "Bsession+Acheck"),
     ("exp010_glove8", "E3_da3m", "Bnet+Acheck")),
]
METHODS = (("default", "DA2 + Bsession (ball)"), ("candidate", "DA3 metric + K, Bnet (no ball)"))


def configure(view, session):
    """Point slam.config at an experiment's analysis view (as the framework's worker does)."""
    from slam import config as C
    C.WORK = Path(view)
    C.SESSIONS.setdefault(session, {**C.SESSIONS["yam_glove7"], "head_stem": f"{session}_b0587b"})
    gt = Path(view) / session / "gt"
    orig = getattr(C, "_gt_dir_orig", C.gt_dir)
    C._gt_dir_orig = orig
    C.gt_dir = lambda name: gt if name == session else orig(name)
    return C.segments_dir(session)


def tile_keyframes(seg_root, run):
    from slam import scale as SC
    out = {}
    for seg in sorted(seg_root.glob("ep[0-9][0-9]")):
        S = SC._segment(seg)
        kf = np.load(seg / "slam" / f"{run}.npz")["kf_t"]
        out[seg.name] = int(S["strict"][kf].sum())
    return out


def err_stats(e):
    e = np.array([x for x in e if x is not None], float)
    if not len(e):
        return None
    return {"n": int(len(e)), "abs_median": float(np.median(np.abs(e))), "abs_p90": float(np.percentile(np.abs(e), 90)),
            "bias_median": float(np.median(e)), "spread_sd_log": float(np.std(np.log1p(e), ddof=1)) if len(e) > 1 else None,
            "n_gt10": int((np.abs(e) > 0.10).sum()), "n_gt20": int((np.abs(e) > 0.20).sum())}


def anchors(seg_root, session, name):
    from slam import labels as L
    rows = []
    for _, _, e in L.anchor_errors(session, name, 100):
        d = {j: p for j, p, _ in e}
        rows.append((d.get(15), d.get(30), float(np.mean([p for j, p, _ in e])) if e else None))
    return rows


def label_stats(rows):
    out = {"anchors": len(rows)}
    for i, k in ((0, "1s"), (1, "2s")):
        v = np.array([r[i] for r in rows if r[i] is not None])
        out[k] = [float(np.median(v)), float(np.percentile(v, 90)), int(len(v))] if len(v) else None
    v = np.array([r[2] for r in rows if r[2] is not None])
    out["chunk100_mean"] = float(v.mean()) if len(v) else None
    return out


def main():
    res, pooled = {}, {m: {"all": [], "tkf3": [], "labels": []} for m, _ in METHODS}
    pooled["oracle"] = {"labels": []}
    for label, session, *specs in SESSIONS:
        r = {"session": session}
        missing = [s[0] for s in specs if not (REPO / "experiments" / s[0] / "results" / f"scale_{s[1]}.json").exists()]
        if missing:
            print(f"{label}: not run yet ({', '.join(missing)})")
            continue
        for (m, _), (exp, run, slabel) in zip(METHODS, specs):
            sj = json.load(open(REPO / "experiments" / exp / "results" / f"scale_{run}.json"))
            seg_root = configure(RUNS / exp / "main" / "view", session)
            tkf = tile_keyframes(seg_root, run)
            errs = {x["segment"]: x["err"] for x in sj["rows"]}
            keep = [s for s, n in tkf.items() if n >= 3]
            r[m] = {"exp": exp, "run": run, "all": err_stats(list(errs.values())),
                    "tkf3": err_stats([errs[s] for s in keep if s in errs]),
                    "k_session": (sj.get("session") or {}).get("Bsession", {}).get("k_session"),
                    "flagged": sj["summary"]["flagged"], "episodes": len(sj["rows"])}
            pooled[m]["all"] += [e for e in errs.values() if e is not None]
            pooled[m]["tkf3"] += [errs[s] for s in keep if errs.get(s) is not None]
            lab = anchors(seg_root, session, f"{run}@{slabel}")
            r[m]["labels"] = label_stats(lab)
            pooled[m]["labels"] += lab
            if m == "candidate":                         # the oracle-scale labels of the same trajectory
                orc = anchors(seg_root, session, run)
                r["oracle_labels"] = label_stats(orc)
                pooled["oracle"]["labels"] += orc
                r["tile_keyframes_ge3"] = len(keep)
        res[label] = r
        print(f"{label}: done", flush=True)
    res["_pooled"] = {m: {"all": err_stats(pooled[m]["all"]), "tkf3": err_stats(pooled[m]["tkf3"]),
                          "labels": label_stats(pooled[m]["labels"])} for m, _ in METHODS}
    res["_pooled"]["oracle_labels"] = label_stats(pooled["oracle"]["labels"])
    json.dump(res, open(HERE / "summary.json", "w"), indent=1, default=float)
    write_md(res)


def write_md(res):
    p = lambda v, f=".1f": "-" if v is None else format(100 * v, f)
    sess = [k for k in res if not k.startswith("_")]
    L = ["# Scale across sessions: DA2 + Bsession (default) vs DA3 metric + K, Bnet (no ball)", "",
         "Generated by `summarize.py` from each experiment's results and analysis view.", ""]
    for sub, title in (("all", "all episodes with a tile-fitted scale"),
                       ("tkf3", "episodes with >= 3 tile-visible keyframes")):
        L += [f"## Scale error vs the tile-fitted scale, {title}", "",
              "| session | episodes | default \\|err\\| med / p90 | default bias | default spread | default >10% / >20% | "
              "**DA3 Bnet \\|err\\| med / p90** | DA3 bias | DA3 spread | DA3 >10% / >20% |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        rows = [(s, res[s]["default"][sub], res[s]["candidate"][sub]) for s in sess] + \
               [("**all sessions**", res["_pooled"]["default"][sub], res["_pooled"]["candidate"][sub])]
        for s, a, b in rows:
            if a is None or b is None:
                L.append(f"| {s} | 0 | | | | | | | | |")
                continue
            L.append(f"| {s} | {a['n']} | {p(a['abs_median'])} / {p(a['abs_p90'])} | {p(a['bias_median'], '+.1f')} | "
                     f"{p(a['spread_sd_log'])} | {a['n_gt10']} / {a['n_gt20']} | **{p(b['abs_median'])} / {p(b['abs_p90'])}** | "
                     f"{p(b['bias_median'], '+.1f')} | {p(b['spread_sd_log'])} | {b['n_gt10']} / {b['n_gt20']} |")
        L.append("")
    L += ["## Tool labels: position error vs the tile labels (mm)", "",
          "| session | anchors | oracle scale 1 s med / p90 | default 1 s | **DA3 Bnet 1 s** | oracle 2 s | default 2 s | "
          "**DA3 2 s** | oracle / default / **DA3** chunk H=100 mean |",
          "|---|---|---|---|---|---|---|---|---|"]
    f2 = lambda x: "-" if x is None else f"{x[0]:.1f} / {x[1]:.1f}"
    f1 = lambda x: "-" if x is None else f"{x:.1f}"
    rows = [(s, res[s]["oracle_labels"], res[s]["default"]["labels"], res[s]["candidate"]["labels"]) for s in sess] + \
           [("**all sessions**", res["_pooled"]["oracle_labels"], res["_pooled"]["default"]["labels"],
             res["_pooled"]["candidate"]["labels"])]
    for s, o, a, b in rows:
        L.append(f"| {s} | {b['anchors']} | {f2(o['1s'])} | {f2(a['1s'])} | **{f2(b['1s'])}** | {f2(o['2s'])} | "
                 f"{f2(a['2s'])} | **{f2(b['2s'])}** | {f1(o['chunk100_mean'])} / {f1(a['chunk100_mean'])} / "
                 f"**{f1(b['chunk100_mean'])}** |")
    L += ["", "## Per session: ball correction and cross-check flags", "",
          "| session | experiments | episodes | >= 3 tile keyframes | DA2 k_session | A flags (default) | A flags (DA3) |",
          "|---|---|---|---|---|---|---|"]
    for s in sess:
        d, c = res[s]["default"], res[s]["candidate"]
        ex = d["exp"] if d["exp"] == c["exp"] else f"{d['exp']}, {c['exp']}"
        L.append(f"| {s} | {ex} | {d['episodes']} | {res[s]['tile_keyframes_ge3']} | "
                 f"{'-' if d['k_session'] is None else format(d['k_session'], '.3f')} | {len(d['flagged'])} | {len(c['flagged'])} |")
    open(HERE / "summary.md", "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
