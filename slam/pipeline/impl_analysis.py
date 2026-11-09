"""Analysis steps: scale, labels, evaluate (venv, CPU). Called as func(job) by the worker.

They run on the analysis view (slam.config.WORK = <work>/runs/<exp>/<variant>/view: the legacy
segment layout over the cached producer outputs) through the stable modules slam.scale,
slam.labels, slam.evaluate and slam.tiles, and write the analysis results contract into
job.out_dir (read by the report):

  scale      scale_<run>.json / .md      per SLAM run with a scale block: primary s per segment,
                                         cross-check flags, errors vs the tile oracle; with a
                                         session method (slam.scale.SESSION_METHODS, e.g. Bsession)
                                         "session": {method: k_session and the per-segment k},
                                         pooled over every segment before the segments are scaled
  labels     labels_<run>.json           tool labels with the tile-oracle scale vs tile labels
             labels_<run>@<label>.json   the same with the run's configured scale
                                         (check_labels by_step + chunk metrics + kept_episodes,
                                         without_flagged when the scale flagged segments)
  evaluate   eval_oracle/, eval_<label>/ slam.evaluate summary.{json,md} (+ pairs.csv)
             gt_noise.json               slam.tiles noise
             analysis.json               index of all of the above + SLAM run facts + the
                                         evaluate parameters {"evaluate": {"fail_deg", "dts"}}
                                         (the tracking-failure threshold the report prints)

The scale label of a run is primary + "+<check>check" per check, e.g. "B+Acheck".
"""
import argparse
import inspect
import json
import math

import numpy as np

from slam import config as C


# ---------------------------------------------------------------------- helpers
def scale_label(block):
    """Scale label of a run's scale block, e.g. B with check A -> 'B+Acheck'."""
    return block["primary"] + "".join(f"+{c}check" for c in block["checks"])


def _finite(x):
    return x is not None and not isinstance(x, bool) and math.isfinite(float(x))


def _clean(o):
    """JSON-safe copy: NaN/inf -> None, numpy scalars/arrays -> Python."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(o) else None
    return o


def _compact(r, max_list=4):
    """A slam.scale.estimate() result without the cache provenance and without long lists
    (replaced by their length, n_<key>)."""
    out = {}
    for k, v in r.items():
        if k == "provenance":
            continue
        if isinstance(v, (list, tuple)) and len(v) > max_list:
            out[f"n_{k}"] = len(v)
            continue
        out[k] = v
    return _clean(out)


def _dump(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=float)


def _scale_rows(job, run):
    """{segment: s or None} and the flagged segments from scale_<run>.json."""
    sj = json.load(open(job.out_dir / f"scale_{run}.json"))
    return ({r["segment"]: (r["s"] if r["ok"] else None) for r in sj["rows"]},
            list(sj["summary"]["flagged"]), sj["label"])


# ---------------------------------------------------------------------- scale
def method_kwargs(job, run, method, params):
    """Configured parameters of a scale method -> slam.scale keyword arguments. A method that
    reads metric depth names a depth node ('depth', '_depth_node'): its model becomes `model`;
    the run's masks and dilation become mask_names / mask_dilate_px where the method takes them."""
    from slam import scale as SC
    kw = {k: v for k, v in params.items() if k not in ("depth", "_depth_node")}
    if "_depth_node" in params:
        kw["model"] = job.inputs[params["_depth_node"]]["params"]["model"]
    sig = inspect.signature(SC.METHODS[method]).parameters
    if "mask_names" in sig:
        kw["mask_names"] = list(job.analysis["slam_runs"][run]["masks"])
    if "mask_dilate_px" in sig:
        d = job.analysis["slam_runs"][run].get("dilate_px")
        kw["mask_dilate_px"] = 8 if d is None else d
    return kw


def _err_summary(errs):
    from slam.scale import _err_stats
    st = _err_stats(errs)
    return {"n_compared": st["n"], "abs_err_median": st.get("abs_median"),
            "abs_err_p90": st.get("abs_p90"), "bias_median": st.get("bias_median")}


def session_inputs(job, run, methods, kw):
    """Session-level inputs of the session methods among `methods` (slam.scale.SESSION_METHODS),
    computed over every segment of the run before any segment is estimated:
    Bsession -> slam.scale.session_k_of_run (the ball samples of all segments pooled with the
    method's `pool`, using its depth model, correction and min_facing). Returns {method: result};
    {} when no method is a session method."""
    from slam import scale as SC
    out = {}
    seg_root = C.segments_dir(job.session)
    for m in methods:
        if SC.SESSION_METHODS.get(m) != "k_session":
            continue
        p = kw[m]
        out[m] = SC.session_k_of_run([seg_root / s for s in job.segments], run,
                                     model=p.get("model", SC.DEPTH_MODELS[0]), correction=p["correction"],
                                     min_facing=p["min_facing"], pool=p["pool"])
    return out


def scale_run(job, run, block):
    """Per segment: oracle, primary and checks (slam.scale.estimate), cross_check -> result dict.
    A session method (primary or check) first gets its session quantity from every segment
    (session_inputs, e.g. k_session), recorded under "session" in the result."""
    from slam import scale as SC
    primary, checks, thr = block["primary"], list(block["checks"]), block["flag_threshold"]
    methods = [primary] + checks
    kw = {m: method_kwargs(job, run, m, block["methods"].get(m, {})) for m in methods}
    session = session_inputs(job, run, methods, kw)
    for m, r in session.items():
        kw[m][SC.SESSION_METHODS[m]] = r["k_session"]
        job.log(f"{run} {m}: k_session {r['k_session']:.4f} ({r['pool']}: {r['n_segments']} segments, "
                f"{r['n_samples']} ball samples; per-segment k p10-p90 {r['k_segment_p10']:.3f}-"
                f"{r['k_segment_p90']:.3f})")
    seg_root = C.segments_dir(job.session)
    rows = []
    for name in job.segments:
        seg = seg_root / name
        o = SC.estimate(seg, run, "tiles")
        so = float(o["s"]) if o.get("ok") else float("nan")
        res = {m: SC.estimate(seg, run, m, **kw[m]) for m in methods}
        cc = SC.cross_check(res[primary], {c: res[c] for c in checks}, thr)

        def rel(s):
            return float(s / so - 1) if _finite(s) and _finite(so) else None
        rows.append({"segment": name, "s": cc["s"] if cc["ok"] else None, "ok": cc["ok"],
                     "oracle_s": so if _finite(so) else None,
                     "err": rel(cc["s"]) if cc["ok"] else None,
                     "primary": _compact(res[primary]),
                     "checks": {c: {**cc["checks"][c], "err": rel(cc["checks"][c]["s"]) if cc["checks"][c]["ok"] else None}
                                for c in checks},
                     "flagged": cc["flagged"], "flagged_by": cc["flagged_by"]})
    meth = {primary: {"segments_ok": sum(r["ok"] for r in rows), **_err_summary([r["err"] for r in rows])}}
    for c in checks:
        meth[c] = {"segments_ok": sum(r["checks"][c]["ok"] for r in rows),
                   **_err_summary([r["checks"][c]["err"] for r in rows])}
    summary = {"segments": len(rows), "segments_ok": sum(r["ok"] for r in rows),
               **_err_summary([r["err"] for r in rows]),
               "flagged": [r["segment"] for r in rows if r["flagged"]],
               "both": [r["segment"] for r in rows if r["ok"] and all(c["ok"] for c in r["checks"].values())],
               "without_flagged": _err_summary([r["err"] for r in rows if not r["flagged"]]),
               "methods": meth}
    res = {"run": run, "label": scale_label(block), "primary": primary, "checks": checks,
           "flag_threshold": thr, "methods": block["methods"], "rows": rows, "summary": summary}
    if session:                                  # only then: other runs' files keep their keys
        res["session"] = session
    return _clean(res)


def scale_md(res, session):
    pct = (lambda v, f="+.1f": "-" if v is None else format(100 * v, f))
    num = (lambda v: "-" if v is None else f"{v:.4f}")
    checks, thr = res["checks"], res["flag_threshold"]
    L = [f"# Scale {res['label']} on {session}, run {res['run']}", "",
         f"s = {res['primary']} on every segment where it succeeds" +
         (f"; checks {', '.join(checks)} only compare: |s_check/s - 1| > {100 * thr:.0f}% flags the "
          "segment (recorded; s and the segment are kept)." if checks else "."), "",
         "| segment | oracle s | s | err % | " + "".join(f"{c} s | {c}/s - 1 % | {c} err % | " for c in checks)
         + "flagged |",
         "|---|---|---|---|" + "---|---|---|" * len(checks) + "---|"]
    for r in res["rows"]:
        cells = [r["segment"], num(r["oracle_s"]), num(r["s"]), pct(r["err"])]
        for c in checks:
            x = r["checks"][c]
            cells += [num(x["s"]), pct(x["diff"]), pct(x["err"])]
        cells.append(", ".join(r["flagged_by"]) if r["flagged"] else "")
        L.append("| " + " | ".join(cells) + " |")
    s = res["summary"]

    def line(title, st, ok=None):
        return (f"| {title} | {'' if ok is None else ok} | {st['n_compared']} | {pct(st['abs_err_median'], '.1f')} | "
                f"{pct(st['abs_err_p90'], '.1f')} | {pct(st['bias_median'])} |")
    L += ["", "Scale error vs the tile oracle (s/s_oracle - 1), over segments with tile GT:", "",
          "| set | segments with a scale | compared | abs err median % | abs err p90 % | bias median % |",
          "|---|---|---|---|---|---|",
          line(f"{res['label']}, all", s, f"{s['segments_ok']}/{s['segments']}"),
          line(f"{res['label']}, without flagged", s["without_flagged"])]
    for m, st in s["methods"].items():
        L.append(line(f"method {m} alone", st, f"{st['segments_ok']}/{s['segments']}"))
    L += ["", f"Flagged: {len(s['flagged'])}" + (f" ({', '.join(s['flagged'])})" if s["flagged"] else "") +
          f". Primary and every check succeeded on {len(s['both'])}" +
          (f" ({', '.join(s['both'])})" if s["both"] else "") + "."]
    L += session_md(res)
    return "\n".join(L) + "\n"


def session_md(res):
    """Markdown lines on the session quantities of a scale result (none without a session method):
    k_session per session method; for a session primary, per segment the segment's own k and
    the scale it would give (s_own_k, = method B with fit scale and the same parameters) next to s."""
    if not res.get("session"):
        return []
    pct = (lambda v, f="+.1f": "-" if v is None else format(100 * v, f))
    num = (lambda v, f=".4f": "-" if v is None else format(v, f))
    L = []
    for m, r in res["session"].items():
        L += ["", f"## Session ball correction ({m})", "",
              f"k_session = {num(r['k_session'])} (pool {r['pool']}: {r['n_segments']} segments with ball samples, "
              f"{r['n_samples']} samples); per-segment k p10 / p25 / p75 / p90 = "
              f"{' / '.join(num(r[f'k_segment_p{q}'], '.3f') for q in (10, 25, 75, 90))}."]
    if res["primary"] not in res["session"]:
        return L
    ks = res["session"][res["primary"]]["k_session"]
    L += ["", f"Per segment: own k (ball samples), s with the own k (= B) and with k_session (= {res['primary']}), "
          "errors vs the tile oracle:", "",
          "| segment | own k | ball samples | k/k_session - 1 % | s own k | err own k % | s | err % |",
          "|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        p, so = r["primary"], r["oracle_s"]
        k, s_own = p.get("k_ball"), p.get("s_own_k")
        e_own = s_own / so - 1 if s_own is not None and so is not None else None
        L.append(f"| {r['segment']} | {num(k, '.3f')} | {p.get('ball_samples', '-')} | "
                 f"{pct(k / ks - 1 if k is not None and ks else None)} | {num(s_own)} | {pct(e_own)} | "
                 f"{num(r['s'])} | {pct(r['err'])} |")
    return L


def run_scale(job):
    out = {}
    for run, block in (job.analysis.get("scale") or {}).items():
        res = scale_run(job, run, block)
        _dump(res, job.out_dir / f"scale_{run}.json")
        (job.out_dir / f"scale_{run}.md").write_text(scale_md(res, job.session))
        s = res["summary"]
        job.log(f"{run} {res['label']}: {s['segments_ok']}/{s['segments']} segments, |err| median "
                f"{s['abs_err_median']}, flagged {s['flagged']}")
        out[run] = {"label": res["label"], "segments_ok": s["segments_ok"], "abs_err_median": s["abs_err_median"],
                    "flagged": s["flagged"]}
    return out


# ---------------------------------------------------------------------- labels
def label_result(session, name, ev, exclude=(), kept=None):
    """check_labels() output + chunk metrics (+ kept_episodes) of label file <name>."""
    from slam import labels as L
    horizon, chunk_H = ev["horizon"], list(ev["chunk_H"])
    anchors = list(L.anchor_errors(session, name, horizon, exclude))
    res = L.step_stats(anchors, name, horizon, exclude, tuple(ev["label_steps"]))
    res["chunk"] = (L.chunk_stats(anchors, chunk_H) if max(chunk_H) <= horizon
                    else L.chunk_labels(session, name, chunk_H, exclude))
    if kept is not None:
        res["kept_episodes"] = int(sum(k for s, k in kept.items() if s not in exclude))
    return res


def run_labels(job):
    from slam import labels as L
    from slam.evaluate import load_tool_offset
    p = job.params
    fixed = {"fps": L.FPS, "label_tol_s": L.LABEL_TOL, "min_coverage": L.MIN_COVERAGE,
             "bridge_s": L.BRIDGE, "min_episode_s": L.MIN_EPISODE}
    bad = {k: (p[k], v) for k, v in fixed.items() if p[k] != v}
    if bad:
        raise ValueError("labels: these parameters are fixed in slam.labels (config value, slam.labels "
                         f"value): {bad}; a different value needs a new labels implementation")
    if p["gripper"] not in ("wrist", "dataset"):
        raise ValueError(f"labels.gripper: 'wrist' or 'dataset', got {p['gripper']!r}")
    session, ev = job.session, p
    seg_root = C.segments_dir(session)
    segs = [seg_root / s for s in job.segments]
    T_bt = load_tool_offset(session)
    grip = L.load_gripper(session, p["gripper"])
    job.log(f"gripper widths ({p['gripper']}) for {len(grip)} episodes" if grip else
            "no gripper widths: pose-only coverage")
    for seg in segs:
        L.build_segment(seg, "tiles", "tiles", T_bt, grip)
    out = {}
    for run in (job.analysis.get("labels") or {}).get("runs", []):
        builds = []                                   # (label name, {segment: keep})
        kept = {seg.name: bool(L.build_segment(seg, run, "tiles", T_bt, grip)["keep"]) for seg in segs}
        builds.append((L.label_name(run, "tiles"), kept))
        flagged = []
        if run in (job.analysis.get("scale") or {}):
            smap, flagged, label = _scale_rows(job, run)
            kept = {seg.name: bool(L.build_segment(seg, run, label, T_bt, grip,
                                                   scale=(smap.get(seg.name), label))["keep"]) for seg in segs}
            builds.append((L.label_name(run, label), kept))
        for name, kept in builds:
            res = label_result(session, name, ev, (), kept)
            if flagged:
                res["without_flagged"] = label_result(session, name, ev, set(flagged), kept)
            _dump(_clean(res), job.out_dir / f"labels_{name}.json")
            b1 = res["by_step"].get(15) or {}
            job.log(f"labels {name}: {res['kept_episodes']} episodes kept, {res['anchors']} anchors, "
                    f"1 s position error median {b1.get('pos_mm_median')}")
            out[name] = {"kept_episodes": res["kept_episodes"], "anchors": res["anchors"]}
    return out


# ---------------------------------------------------------------------- evaluate
def slam_facts(session, run, segments):
    """Per-run SLAM facts from the trajectories' meta: mean keyframes and runtime per segment,
    mean valid (unmasked) fraction, and the fraction of frames with a pose (pooled)."""
    kf, rt, vf, n_tr, n_fr = [], [], [], 0, 0
    for s in segments:
        p = C.segments_dir(session) / s / "slam" / f"{run}.npz"
        if not p.exists():
            continue
        z = np.load(p)
        meta = json.loads(str(z["meta"]))
        for lst, key in ((kf, "n_keyframes"), (rt, "runtime_s"), (vf, "valid_frac")):
            if meta.get(key) is not None:
                lst.append(float(meta[key]))
        tr = z["tracked"] if "tracked" in z.files else np.isfinite(z["T_slam_cam"]).all((1, 2))
        n_tr, n_fr = n_tr + int(tr.sum()), n_fr + len(tr)
    mean = (lambda x: float(np.mean(x)) if x else None)
    return {"keyframes_per_segment": mean(kf), "runtime_s_per_segment": mean(rt), "valid_frac": mean(vf),
            "tracked_frac": n_tr / n_fr if n_fr else None}


def gt_noise(session, segments):
    """slam.tiles noise output (dict) on the view's segments."""
    from slam import tiles as T
    if hasattr(T, "noise_floor"):
        return T.noise_floor(session, [C.segments_dir(session) / s for s in segments])
    T.cmd_noise(argparse.Namespace(session=session))          # writes <WORK>/<session>/eval/gt_noise.json
    return json.load(open(C.WORK / session / "eval" / "gt_noise.json"))


def run_evaluate(job):
    from slam import evaluate as EV
    p, an, session, out = job.params, job.analysis, job.session, job.out_dir
    runs = list((an.get("evaluate") or {}).get("runs", []))
    scale_cfg = an.get("scale") or {}
    dts, fail = list(p["dts"]), p["fail_deg"]
    result = {}
    S = EV.evaluate_session(session, runs, out / "eval_oracle", dts=dts, fail_deg=fail)
    result["eval_oracle"] = {r: S["runs"][r]["track_fail_frac"] for r in runs}
    groups = {}
    for r in runs:
        if r in scale_cfg:
            groups.setdefault(scale_label(scale_cfg[r]), []).append(r)
    for label, rs in groups.items():
        smaps = {r: _scale_rows(job, r)[0] for r in rs}

        def scale_fn(seg, run, s_oracle, smaps=smaps):
            s = smaps[run].get(seg.name)
            return float(s) if s is not None else np.nan
        S = EV.evaluate_session(session, rs, out / f"eval_{label}", scale_fn, dts=dts, fail_deg=fail,
                                scale_name=label)
        result[f"eval_{label}"] = {r: S["runs"][r]["scale_ok_segments"] for r in rs}
    if p["gt_noise"]:
        _dump(gt_noise(session, job.segments), out / "gt_noise.json")
    lab_runs = (an.get("labels") or {}).get("runs", [])
    idx = {"runs": {}, "gt_noise": "gt_noise.json" if p["gt_noise"] else None, "segments": list(job.segments),
           "evaluate": {"fail_deg": float(fail), "dts": [float(d) for d in dts]}}
    exists = (lambda f: f if f is not None and (out / f).exists() else None)
    for run in (an.get("slam_runs") or {r: None for r in runs}):
        blk = scale_cfg.get(run)
        label = scale_label(blk) if blk else None
        idx["runs"][run] = {
            "scale_label": label,
            "scale": exists(f"scale_{run}.json" if blk else None),
            "labels": {"oracle": exists(f"labels_{run}.json" if run in lab_runs else None),
                       "scaled": exists(f"labels_{run}@{label}.json" if run in lab_runs and blk else None)},
            "eval": {"oracle": "eval_oracle" if run in runs else None,
                     "scaled": f"eval_{label}" if blk and run in runs else None},
            "slam": slam_facts(session, run, job.segments)}
    _dump(_clean(idx), out / "analysis.json")
    return result
