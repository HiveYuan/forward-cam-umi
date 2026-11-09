"""Report step: canonical metrics, report.md, comparison with other experiments, and the
reproducibility check of a `--repro` run.

job.spec:
  variants          {variant: analysis results dir}: 'main', plus 'repro1', ... after --repro
  repro             None or {node, base_keys: {node id: key}, runs: [{variant, keys: {node id: key}}]}
  experiments_root  the repository's experiments/ (other experiments' results/ are only read)
  work              work root; producer outputs in <work>/cache/<step>/<key>/epNN/
job.params: {compare: [experiment names], dt_show: [s, ...]}

Writes into job.out_dir (= experiments/<exp>/results/):
  metrics.json      canonical numbers of the main variant (schema below)
  report.md         short tables, then side by side with every experiment in `compare`
  copies            the main variant's scale_*.json/.md, labels_*.json, eval_*/summary.{json,md},
                    gt_noise.json, analysis.json (never pairs.csv)
  repro.json, repro.md   after --repro: headline metric deltas and trajectory differences of
                    every recomputed SLAM node vs main; repro.md starts with a tolerance table

metrics.json:
  {"experiment", "variant", "n_segments",
   "runs": {run: {"head": {"rot_deg": {dt: stat}, "rot_deg_same_tiles": {dt: stat},
                           "trans_mm": {scale_name: {dt: stat}},
                           "label_pos_mm_pairs": {scale_name: {dt: stat}},
                           "label_rot_deg_pairs": {scale_name: {dt: stat}}},
                  "track_fail_frac": float|null,
                  "slam": {"keyframes_per_segment", "runtime_s_per_segment", "valid_frac"[, "tracked_frac"]},
                  "scale": null | {"label", "primary", "checks", "segments", "segments_ok", "n_compared",
                                   "abs_err_median", "abs_err_p90", "bias_median", "flagged",
                                   "without_flagged", "methods"},
                  "labels": {scale_name: {"anchors", "by_step": {j: {...}}}},
                  "chunk": {scale_name: {H: {...}}}}},
   "gt_noise": {...} | null,
   "evaluate": {"fail_deg": float|null, "dts": [s, ...]|null}}
  stat = slam.evaluate.stats() dict; dt keys are strings as in the legacy summary.json ("0.08",
  "1.0"); scale_name = "oracle" (tile-fitted scale) or the run's scale label ("B+Acheck").
  Error fractions are fractions. "static" (head motion = identity, no SLAM) is kept as a
  baseline run with head metrics only (track_fail_frac, slam and scale null).
  evaluate = the evaluation parameters: fail_deg is the tracking-failure threshold behind
  track_fail_frac (analysis.json "evaluate"; 2.0 for the legacy adapter; null = unknown, a
  results dir without it), dts the evaluated pair intervals. The report prints the threshold
  and marks comparisons between experiments evaluated with different (or unknown) fail_deg.

Experiments without metrics.json (exp000_legacy) are read by legacy_metrics(), which builds
the same structure from the legacy files (results/eval/, results/<label>_eval/).
"""
import json
import math
import shutil
from pathlib import Path

import numpy as np

ORACLE = "oracle"
LEGACY_SCALE_LABEL = "B+Acheck"          # exp000_legacy's configured scale (decision 2026-11-08)
LEGACY_FAIL_DEG = 2.0                    # slam.evaluate.FAIL_DEG when exp000_legacy was evaluated
LABEL_FPS = 15.0
STAT_KEYS = ("n", "median", "p90", "p95", "mean")
HEAD_ORACLE = {"rot_deg": "rot_err_deg", "rot_deg_same_tiles": "rot_err_deg_same_tiles"}
HEAD_SCALED = {"trans_mm": "trans_err_mm", "label_pos_mm_pairs": "label_pos_err_mm",
               "label_rot_deg_pairs": "label_rot_err_deg"}
SCALE_STATS = ("n_compared", "abs_err_median", "abs_err_p90", "bias_median")
SLAM_KEYS = ("keyframes_per_segment", "runtime_s_per_segment", "valid_frac")


# ====================================================================== small helpers
def _read(p):
    with open(p) as f:
        return json.load(f)


def _write_json(p, obj):
    p = Path(p)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(_clean(obj), f, indent=1)
    tmp.replace(p)


def _clean(x):
    """JSON-safe copy: numpy scalars -> python, non-finite floats -> None, keys -> str."""
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return _clean(x.tolist())
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if math.isfinite(x) else None
    return x


def _finite(v):
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool) \
        and math.isfinite(float(v))


def _num(v):
    return float(v) if _finite(v) else None


def _mean(values):
    x = [float(v) for v in values if _finite(v)]
    return float(np.mean(x)) if x else None


def _agg(v):
    """A per-segment quantity as one number: numbers as they are, dicts/lists -> mean."""
    if isinstance(v, dict):
        return _mean(v.values())
    if isinstance(v, (list, tuple)):
        return _mean(v)
    return _num(v)


def dt_key(d):
    return str(float(d))


def scale_label(primary, checks):
    return primary + "".join(f"+{c}check" for c in checks)


def parse_scale_label(label):
    """'B+Acheck' -> ('B', ['A'])."""
    parts = label.split("+")
    return parts[0], [p[:-len("check")] for p in parts[1:] if p.endswith("check")]


def _sorted_num(keys):
    return sorted(keys, key=lambda k: float(k))


def _stat(x):
    """slam.evaluate.stats plus the maximum."""
    from slam.evaluate import stats
    x = np.asarray(x, float)
    s = stats(x)
    if s.get("n"):
        s["max"] = float(np.nanmax(x[np.isfinite(x)]))
    return s


# ====================================================================== canonical metrics
def head_block(evals, run):
    """evals: {scale_name: legacy slam.evaluate summary.json (or None)}. Rotation is
    scale-free and taken from the oracle evaluation; translation and the pair labels per scale."""
    out = {k: {} for k in list(HEAD_ORACLE) + list(HEAD_SCALED)}
    o = evals.get(ORACLE)
    if o and run in o.get("runs", {}):
        by = o["runs"][run]["by_dt"]
        for k, src in HEAD_ORACLE.items():
            out[k] = {d: by[d][src] for d in by if src in by[d]}
    for name, S in evals.items():
        if not S or run not in S.get("runs", {}) or (run == "static" and name != ORACLE):
            continue
        by = S["runs"][run]["by_dt"]
        for k, src in HEAD_SCALED.items():
            out[k][name] = {d: by[d][src] for d in by if src in by[d]}
    return out


def slam_from_segments(summary, run):
    """Per-segment means from the evaluate summary's segment info (as slam.report does)."""
    info = [v[run] for v in (summary or {}).get("segments", {}).values() if isinstance(v, dict) and run in v]
    return {"keyframes_per_segment": _mean(i.get("n_keyframes") for i in info),
            "runtime_s_per_segment": _mean(i.get("runtime_s") for i in info),
            "valid_frac": _mean(i.get("valid_frac") for i in info)}


def scale_block(sc):
    """scale_<run>.json (analysis contract) -> canonical scale block."""
    s = sc.get("summary", {})
    out = {"label": sc.get("label") or scale_label(sc["primary"], sc.get("checks", [])),
           "primary": sc.get("primary"), "checks": list(sc.get("checks") or [])}
    for k in ("segments", "segments_ok") + SCALE_STATS:
        out[k] = s.get(k)
    out["flagged"] = list(s.get("flagged") or [])
    wf = s.get("without_flagged")
    out["without_flagged"] = {k: wf.get(k) for k in SCALE_STATS} if wf else None
    out["methods"] = {m: {k: v.get(k) for k in ("segments_ok",) + SCALE_STATS}
                      for m, v in (s.get("methods") or {}).items()}
    return out


def legacy_scale_block(cc, label=LEGACY_SCALE_LABEL):
    """Legacy `slam.scale crosscheck` output (eval/scale_<run>_<label>.json: rows with s, ok,
    s_A, s_B, err, err_A, err_B as fractions; scale_all / scale_without_flagged as
    {n, abs_median, abs_p90, bias_median}) -> canonical scale block."""
    from slam.scale import _err_stats

    def conv(st):
        st = st or {}
        return {"n_compared": int(st.get("n", 0)), "abs_err_median": st.get("abs_median"),
                "abs_err_p90": st.get("abs_p90"), "bias_median": st.get("bias_median")}
    primary, checks = parse_scale_label(label)
    rows = cc["rows"]
    out = {"label": label, "primary": primary, "checks": checks, "segments": len(rows),
           "segments_ok": int(sum(bool(r.get("ok")) for r in rows))}
    out.update(conv(cc.get("scale_all")))
    out["flagged"] = list(cc.get("flagged") or [])
    out["without_flagged"] = conv(cc.get("scale_without_flagged"))
    out["methods"] = {}
    for m in [primary] + checks:
        ok = int(sum(_finite(r.get(f"s_{m}")) for r in rows))
        out["methods"][m] = {"segments_ok": ok, **conv(_err_stats([r.get(f"err_{m}") for r in rows]))}
    return out


def labels_entry(lab):
    return {"anchors": lab.get("anchors"), "by_step": {str(j): v for j, v in (lab.get("by_step") or {}).items()}}


def _summary_path(base, rel):
    if not rel:
        return None
    p = Path(base) / rel
    if p.is_dir():
        p = p / "summary.json"
    return p if p.exists() else None


def discover_index(res):
    """analysis.json-shaped index of a results dir that has no analysis.json (file names of
    the analysis contract)."""
    res = Path(res)
    o = res / "eval_oracle" / "summary.json"
    S = _read(o) if o.exists() else {"runs": {}, "segments": {}}
    runs = [r for r in S["runs"] if r != "static"]
    for p in sorted(res.glob("scale_*.json")) + sorted(res.glob("labels_*.json")):
        name = p.stem.split("_", 1)[1].split("@")[0]
        if name not in runs and name != "tiles":
            runs.append(name)
    idx = {"runs": {}, "gt_noise": "gt_noise.json" if (res / "gt_noise.json").exists() else None,
           "segments": sorted(S.get("segments", {})),
           "evaluate": {"fail_deg": S.get("fail_deg"), "dts": S.get("dts")}}     # fail_deg: unknown
    for run in runs:
        sc = res / f"scale_{run}.json"
        label = _read(sc).get("label") if sc.exists() else None
        lo, ls = res / f"labels_{run}.json", res / f"labels_{run}@{label}.json"
        es = res / f"eval_{label}" / "summary.json"
        idx["runs"][run] = {
            "scale_label": label, "scale": sc.name if sc.exists() else None,
            "labels": {"oracle": lo.name if lo.exists() else None,
                       "scaled": ls.name if label and ls.exists() else None},
            "eval": {"oracle": "eval_oracle" if run in S["runs"] else None,
                     "scaled": f"eval_{label}" if label and es.exists() else None},
            "slam": None}
    return idx


def build_metrics(base, index, experiment, variant, scale_reader=scale_block):
    """Canonical metrics from an analysis.json-shaped index whose paths are relative to base."""
    base = Path(base)
    cache = {}

    def summary(rel):
        p = _summary_path(base, rel)
        if p is None:
            return None
        if p not in cache:
            cache[p] = _read(p)
        return cache[p]

    def load(rel):
        return _read(base / rel) if rel and (base / rel).exists() else None

    runs_idx = index.get("runs", {})
    oracle_any = next((summary(r["eval"]["oracle"]) for r in runs_idx.values()
                       if (r.get("eval") or {}).get("oracle") and summary(r["eval"]["oracle"])), None)
    runs = {}
    if oracle_any and "static" in oracle_any.get("runs", {}):
        runs["static"] = {"head": head_block({ORACLE: oracle_any}, "static"), "track_fail_frac": None,
                          "slam": None, "scale": None, "labels": {}, "chunk": {}}
    for run, r in runs_idx.items():
        ev = r.get("eval") or {}
        label = r.get("scale_label")
        evals = {ORACLE: summary(ev.get("oracle"))}
        if label and ev.get("scaled"):
            evals[label] = summary(ev.get("scaled"))
        o = evals[ORACLE]
        tf = o["runs"][run].get("track_fail_frac") if o and run in o.get("runs", {}) else None
        sl = r.get("slam")
        if sl:
            slam = {k: _agg(sl.get(k)) for k in SLAM_KEYS}
            if "tracked_frac" in sl:
                slam["tracked_frac"] = _agg(sl.get("tracked_frac"))
        else:
            slam = slam_from_segments(o, run) if o else {k: None for k in SLAM_KEYS}
        sc = load(r.get("scale"))
        labs, chunk = {}, {}
        for kind, name in (("oracle", ORACLE), ("scaled", label)):
            lab = load((r.get("labels") or {}).get(kind)) if name else None
            if lab is None:
                continue
            labs[name] = labels_entry(lab)
            if lab.get("chunk"):
                chunk[name] = {str(h): v for h, v in lab["chunk"].items()}
        runs[run] = {"head": head_block(evals, run), "track_fail_frac": _num(tf), "slam": slam,
                     "scale": scale_reader(sc) if sc else None, "labels": labs, "chunk": chunk}
    segs = index.get("segments") or sorted((oracle_any or {}).get("segments", {}))
    ev = index.get("evaluate") or {}
    evaluate = {"fail_deg": _num(ev.get("fail_deg")),
                "dts": ev.get("dts") if ev.get("dts") is not None else (oracle_any or {}).get("dts")}
    return _clean({"experiment": experiment, "variant": variant, "n_segments": len(segs),
                   "runs": runs, "gt_noise": load(index.get("gt_noise")), "evaluate": evaluate})


def results_index(res):
    p = Path(res) / "analysis.json"
    return _read(p) if p.exists() else discover_index(res)


def variant_metrics(res, experiment, variant):
    return build_metrics(res, results_index(res), experiment, variant)


def legacy_index(res, label=LEGACY_SCALE_LABEL):
    """Index over exp000_legacy's results/: eval/ (oracle scale), <label>_eval/ (configured
    scale), eval/scale_<run>_<label>.json, eval/labels_<run>[@<label>].json, eval/gt_noise.json."""
    res = Path(res)
    S = _read(res / "eval" / "summary.json")
    sp = res / f"{label}_eval" / "summary.json"
    Ss = _read(sp) if sp.exists() else {"runs": {}}
    runs = {}
    for run in S["runs"]:
        if run == "static":
            continue
        sc = f"eval/scale_{run}_{label}.json"
        has_sc = (res / sc).exists()
        lo, ls = f"eval/labels_{run}.json", f"eval/labels_{run}@{label}.json"
        scaled = run in Ss["runs"]
        runs[run] = {"scale_label": label if (has_sc or scaled) else None, "scale": sc if has_sc else None,
                     "labels": {"oracle": lo if (res / lo).exists() else None,
                                "scaled": ls if (res / ls).exists() else None},
                     "eval": {"oracle": "eval", "scaled": f"{label}_eval" if scaled else None},
                     "slam": None}
    return {"runs": runs, "gt_noise": "eval/gt_noise.json" if (res / "eval" / "gt_noise.json").exists() else None,
            "segments": sorted(S["segments"]), "evaluate": {"fail_deg": LEGACY_FAIL_DEG, "dts": S.get("dts")}}


def legacy_metrics(res, experiment="exp000_legacy", label=LEGACY_SCALE_LABEL):
    """Canonical metrics of a pre-framework results/ dir (exp000_legacy). No chunk metrics."""
    return build_metrics(res, legacy_index(res, label), experiment, "legacy",
                         scale_reader=lambda cc: legacy_scale_block(cc, label))


def load_experiment(root, name):
    """(metrics or None, source description) of experiments/<name>."""
    res = Path(root) / name / "results"
    if (res / "metrics.json").exists():
        return _read(res / "metrics.json"), f"`{name}/results/metrics.json`"
    if (res / "eval" / "summary.json").exists():
        return legacy_metrics(res, name), (f"legacy adapter over `{name}/results/` (eval/, "
                                           f"{LEGACY_SCALE_LABEL}_eval/; no chunk metrics)")
    return None, f"not found: no `{name}/results/metrics.json`"


# ====================================================================== copying
COPY_PATTERNS = ("scale_*.json", "scale_*.md", "labels_*.json", "gt_noise.json", "analysis.json")


def copy_small_files(src, dst):
    """The main variant's small analysis files -> results/ (never pairs.csv)."""
    src, dst = Path(src), Path(dst)
    out = []
    if src.resolve() == dst.resolve():
        return out
    for pat in COPY_PATTERNS:
        for p in sorted(src.glob(pat)):
            if p.is_file():
                shutil.copy2(p, dst / p.name)
                out.append(p.name)
    for d in sorted(src.glob("eval_*")):
        if not d.is_dir():
            continue
        for f in ("summary.json", "summary.md"):
            if (d / f).is_file():
                (dst / d.name).mkdir(parents=True, exist_ok=True)
                shutil.copy2(d / f, dst / d.name / f)
                out.append(f"{d.name}/{f}")
    return out


# ====================================================================== formatting
def _f(v, fmt=".2f", mul=1.0):
    return "-" if not _finite(v) else format(float(v) * mul, fmt)


def _s(st, key="median", fmt=".2f"):
    return "-" if not st or not st.get("n") else _f(st.get(key), fmt)


def _pct(v, fmt=".1f"):
    return _f(v, fmt, 100.0) + "%" if _finite(v) else "-"


def fail_deg_of(m):
    """The tracking-failure threshold [deg] of canonical metrics (None = unknown)."""
    return _num(((m or {}).get("evaluate") or {}).get("fail_deg"))


def _deg(v):
    return "?" if not _finite(v) else format(float(v), "g")


def _row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _table(header, rows):
    return [_row(header), "|" + "---|" * len(header)] + [_row(r) for r in rows] + [""]


def _scale_names(run_m):
    """Scale names of a run: oracle first, then the configured label."""
    names = [ORACLE]
    lab = (run_m.get("scale") or {}).get("label")
    others = set(run_m["head"]["trans_mm"]) | set(run_m.get("labels", {})) | set(run_m.get("chunk", {}))
    if lab:
        names.append(lab)
    names += sorted(n for n in others if n not in names)
    return names


def _configured(run_m):
    """The run's configured scale label (None if it has none)."""
    n = _scale_names(run_m)
    return n[1] if len(n) > 1 else None


def _sname(name):
    return "oracle (tiles)" if name == ORACLE else name


def _steps(lab_by_name):
    keys = set()
    for lab in lab_by_name:
        keys |= set((lab or {}).get("by_step", {}))
    return _sorted_num(keys)


def _step_dt(j):
    return f"{int(j) / LABEL_FPS:.2f} s"


def _chunk_hs(chunks):
    keys = set()
    for c in chunks:
        keys |= set(c or {})
    return _sorted_num(keys)


# ====================================================================== report.md (this experiment)
def render_main(m, dts, scale_files=None):
    """Tables of one experiment's canonical metrics. scale_files: {run: scale_<run>.json dict}
    for details only the contract file has (flag threshold)."""
    scale_files = scale_files or {}
    runs = list(m["runs"])
    slam_runs = [r for r in runs if r != "static"]
    L = []
    hdr = ["run"] + [f"{d} s" for d in dts]
    L += ["## Head rotation error cam_t->cam_t+dt [deg], median / p95", ""]
    L += _table(hdr, [[r] + [f"{_s(m['runs'][r]['head']['rot_deg'].get(d))} / "
                             f"{_s(m['runs'][r]['head']['rot_deg'].get(d), 'p95')}" for d in dts] for r in runs])
    rows = []
    for r in slam_runs:
        tr = m["runs"][r]["head"]["trans_mm"]
        for name in _scale_names(m["runs"][r]):
            if name in tr:
                rows.append([r, _sname(name)] + [f"{_s(tr[name].get(d))} / {_s(tr[name].get(d), 'p95')}" for d in dts])
    L += ["## Head translation error [mm], median / p95", ""]
    L += _table(["run", "scale"] + hdr[1:], rows)
    L += ["## Tracking, keyframes, runtime", ""]
    rows = []
    for r in slam_runs:
        x = m["runs"][r]
        sl = x.get("slam") or {}
        rows.append([r, _pct(x.get("track_fail_frac"), ".2f"), _f(sl.get("keyframes_per_segment"), ".1f"),
                     _f(sl.get("runtime_s_per_segment"), ".0f"), _pct(sl.get("valid_frac"), ".0f")])
    L += _table(["run", f"track fail (dt 0.08 s, err > {_deg(fail_deg_of(m))} deg)", "keyframes / segment",
                 "runtime s / segment", "valid pixels"], rows)

    sc_runs = [r for r in slam_runs if m["runs"][r].get("scale")]
    if sc_runs:
        L += ["## Scale error vs the tile oracle (s / s_oracle - 1)", ""]
        rows = []
        for r in sc_runs:
            b = m["runs"][r]["scale"]
            thr = scale_files.get(r, {}).get("flag_threshold")
            note = f" (flag \\|check/primary - 1\\| > {100 * thr:.0f}%)" if thr is not None and b.get("checks") else ""
            rows.append([r, b["label"] + note, f"{b.get('segments_ok')}/{b.get('segments')}", b.get("n_compared"),
                         _pct(b.get("abs_err_median")), _pct(b.get("abs_err_p90")), _pct(b.get("bias_median")),
                         ", ".join(b.get("flagged") or []) or "-"])
            wf = b.get("without_flagged")
            if wf and b.get("flagged"):
                ok = b.get("segments_ok")
                rows.append([r, f"{b['label']}, without flagged", f"{ok - len(b['flagged'])}/{b.get('segments')}" if ok is not None else "-",
                             wf.get("n_compared"), _pct(wf.get("abs_err_median")), _pct(wf.get("abs_err_p90")),
                             _pct(wf.get("bias_median")), ""])
            for meth, v in (b.get("methods") or {}).items():
                role = "primary" if meth == b.get("primary") else "check"
                rows.append([r, f"{b['label']}, method {meth} ({role})", f"{v.get('segments_ok')}/{b.get('segments')}",
                             v.get("n_compared"), _pct(v.get("abs_err_median")), _pct(v.get("abs_err_p90")),
                             _pct(v.get("bias_median")), ""])
        L += _table(["run", "scale", "segments with a scale", "compared (tile GT)", "abs err median",
                     "abs err p90", "bias (median)", "flagged"], rows)
        L += ["s is always the primary's; checks only flag segments (nothing is changed or dropped).", ""]

    lab_rows = [(r, name, m["runs"][r]["labels"][name]) for r in slam_runs
                for name in _scale_names(m["runs"][r]) if name in m["runs"][r].get("labels", {})]
    if lab_rows:
        steps = _steps(x for _, _, x in lab_rows)
        for key, title, fmt in (("pos_mm", "position error [mm]", ".1f"), ("rot_deg", "rotation error [deg]", ".2f")):
            L += [f"## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt {title}, "
                  "median / p90", ""]
            rows = []
            for r, name, lab in lab_rows:
                b = lab["by_step"]
                rows.append([r, _sname(name), lab.get("anchors")] + [
                    f"{_f(b[j].get(key + '_median'), fmt)} / {_f(b[j].get(key + '_p90'), fmt)}" if j in b else "-"
                    for j in steps])
            L += _table(["run", "scale", "anchors"] + [_step_dt(j) for j in steps], rows)
    ch_rows = [(r, name) for r in slam_runs for name in _scale_names(m["runs"][r]) if name in m["runs"][r].get("labels", {})]
    if ch_rows:
        hs = _chunk_hs(m["runs"][r].get("chunk", {}).get(name) for r, name in ch_rows)
        L += ["## Chunk-length label error: mean over anchors of the mean error over steps 1..H, "
              "position [mm] / rotation [deg]", ""]
        if hs:
            rows = []
            for r, name in ch_rows:
                c = m["runs"][r].get("chunk", {}).get(name) or {}
                rows.append([r, _sname(name), next((c[h].get("anchors") for h in hs if h in c), "-")] + [
                    f"{_f(c[h].get('pos_mm_mean'), '.1f')} / {_f(c[h].get('rot_deg_mean'), '.2f')}" if h in c else "-"
                    for h in hs])
            L += _table(["run", "scale", "anchors"] + [f"H={h} ({int(h) / LABEL_FPS:.2f} s)" for h in hs], rows)
        else:
            L += ["-", ""]
    L += render_gt_noise(m.get("gt_noise"))
    return L


def render_gt_noise(g):
    if not g:
        return []
    L = ["## Ground-truth noise floor (slam.tiles noise, 2-tile solves)", "",
         f"From {g.get('frames_with_all_tiles')} frames with all 4 tiles, comparing disjoint tile pairs.", ""]
    rows = []
    for dt, v in (g.get("by_dt") or {}).items():
        if v.get("n"):
            rows.append([f"same tiles, dt {dt} s", v["n"], f"{_f(v.get('rot_deg_median'))} / {_f(v.get('rot_deg_p95'))}",
                         f"{_f(v.get('trans_mm_median'), '.1f')} / {_f(v.get('trans_mm_p95'), '.1f')}"])
    t = g.get("tile_switch")
    if t and t.get("n"):
        rows.append(["tile set changes between the ends", t["n"], f"{_f(t.get('rot_deg_median'))} / {_f(t.get('rot_deg_p95'))}",
                     f"{_f(t.get('trans_mm_median'), '.1f')} / {_f(t.get('trans_mm_p95'), '.1f')}"])
    return L + _table(["pairs", "n", "rot deg median / p95", "trans mm median / p95"], rows)


# ====================================================================== comparison tables
def _ctable(title, key_cols, groups, keys, exps, cell, show=None):
    """Side-by-side table: one row per key (tuple of key cells, displayed through show()),
    one column group per experiment; cell(metrics, key) -> list of len(groups) strings."""
    hdr = list(key_cols) + [f"{name}{' ' + g if g else ''}" for name, _ in exps for g in groups]
    rows = []
    for k in keys:
        r = list(show(k) if show else k)
        for _, m in exps:
            r += cell(m, k) if m is not None else ["-"] * len(groups)
        rows.append(r)
    return [f"### {title}", ""] + _table(hdr, rows)


def _run(m, run):
    return (m or {}).get("runs", {}).get(run)


def _scale_of(m, run, kind):
    x = _run(m, run)
    if x is None:
        return None
    return ORACLE if kind == "oracle" else _configured(x)


def render_compare(exps, dts, sources):
    """exps: [(name, metrics)], the first is this experiment. sources: {name: description}."""
    me = exps[0][1]
    runs = list(me["runs"])
    slam_runs = [r for r in runs if r != "static"]
    L = ["## Comparison with other experiments", ""]
    for name, _ in exps[1:]:
        L.append(f"- {name}: {sources.get(name, '')}")
    only = {name: [r for r in (m or {}).get("runs", {}) if r not in me["runs"]] for name, m in exps[1:]}
    for name, rr in only.items():
        if rr:
            L.append(f"- runs only in {name} (not shown): {', '.join(rr)}")
    L += ["", "Rows: what this experiment has. \"configured\" = each experiment's own scale method "
          "(labels in the scale table); \"-\" = not available.", ""]

    def head(metric, kind, groups):
        def cell(m, k):
            run, sk, d = (k[0], k[1], k[2]) if len(k) == 3 else (k[0], None, k[1])
            x = _run(m, run)
            if x is None:
                return ["-"] * len(groups)
            if sk is None:
                st = x["head"][metric].get(d)
            else:
                name = _scale_of(m, run, sk)
                st = (x["head"][metric].get(name) or {}).get(d) if name else None
            return [_s(st, g) for g in groups]
        return cell

    L += _ctable("Head rotation error [deg]", ["run", "dt"], ["median", "p95"],
                 [(r, d) for r in runs for d in dts], exps, head("rot_deg", None, ["median", "p95"]))
    L += _ctable("Head translation error [mm]", ["run", "scale", "dt"], ["median", "p95"],
                 [(r, sk, d) for r in slam_runs for sk in ("oracle", "configured") for d in dts
                  if sk == "oracle" or _configured(me["runs"][r])], exps, head("trans_mm", True, ["median", "p95"]))

    fds = {name: fail_deg_of(m) for name, m in exps if m is not None}
    same_fd = len(set(fds.values())) == 1 and None not in fds.values()

    def misc(m, k):
        x = _run(m, k[0])
        if x is None:
            return ["-"]
        sl = x.get("slam") or {}
        tf = _pct(x.get("track_fail_frac"), ".2f")
        if not same_fd and tf != "-":
            tf += f" (> {_deg(fail_deg_of(m))} deg)"
        return [{"track fail": tf,
                 "keyframes / segment": _f(sl.get("keyframes_per_segment"), ".1f"),
                 "runtime s / segment": _f(sl.get("runtime_s_per_segment"), ".0f"),
                 "valid pixels": _pct(sl.get("valid_frac"), ".0f")}[k[1]]]
    fd_title = f"err > {_deg(next(iter(fds.values())))} deg" if same_fd else "err > each experiment's fail_deg"
    tab = _ctable(f"Tracking failures (dt 0.08 s, {fd_title}), keyframes, runtime", ["run", "quantity"], [""],
                  [(r, q) for r in slam_runs for q in ("track fail", "keyframes / segment", "runtime s / segment",
                                                        "valid pixels")], exps, misc)
    if not same_fd:
        why = "differ" if None not in fds.values() else "differ or are unknown"
        tab[1:1] = ["", f"**Tracking-failure thresholds {why}**: " + ", ".join(
            f"{name} {_deg(v)} deg" for name, v in fds.items()) + "; the track fail rows are not comparable."]
    L += tab

    sc_runs = [r for r in slam_runs if me["runs"][r].get("scale")]
    if sc_runs:
        meths = {}
        for r in sc_runs:
            ms = []
            for _, m in exps:
                for meth in ((_run(m, r) or {}).get("scale") or {}).get("methods") or {}:
                    if meth not in ms:
                        ms.append(meth)
            meths[r] = ms
        qs = ["scale label", "segments with a scale", "compared (tile GT)", "abs err median", "abs err p90",
              "bias (median)", "flagged", "without flagged: abs err median / p90"]

        def scale_cell(m, k):
            b = (_run(m, k[0]) or {}).get("scale")
            if not b:
                return ["-"]
            q = k[1]
            if isinstance(q, tuple):
                v = (b.get("methods") or {}).get(q[1])
                return [f"{v.get('segments_ok')}/{b.get('segments')}, n {v.get('n_compared')}: "
                        f"{_pct(v.get('abs_err_median'))} / {_pct(v.get('abs_err_p90'))} / {_pct(v.get('bias_median'))}"
                        if v else "-"]
            wf = b.get("without_flagged") or {}
            return [{"scale label": b.get("label"), "segments with a scale": f"{b.get('segments_ok')}/{b.get('segments')}",
                     "compared (tile GT)": str(b.get("n_compared")), "abs err median": _pct(b.get("abs_err_median")),
                     "abs err p90": _pct(b.get("abs_err_p90")), "bias (median)": _pct(b.get("bias_median")),
                     "flagged": ", ".join(b.get("flagged") or []) or "-",
                     "without flagged: abs err median / p90":
                         f"{_pct(wf.get('abs_err_median'))} / {_pct(wf.get('abs_err_p90'))}" if wf else "-"}[q]]
        keys = [(r, q) for r in sc_runs for q in qs + [("method", x) for x in meths[r]]]

        def show_q(k):
            q = k[1]
            return (k[0], f"method {q[1]}: segments ok, n: abs err median / p90 / bias" if isinstance(q, tuple) else q)
        L += _ctable("Scale error vs the tile oracle (configured scale)", ["run", "quantity"], [""], keys, exps,
                     scale_cell, show_q)

    lab_keys = []
    for r in slam_runs:
        for sk in ("oracle", "configured"):
            labs = [((_run(m, r) or {}).get("labels") or {}).get(_scale_of(m, r, sk) or "") for _, m in exps]
            if labs[0]:                                  # rows this experiment has
                lab_keys += [(r, sk, "anchors")] + [(r, sk, j) for j in _steps(labs)]
    if lab_keys:
        def lab(key, groups):
            def cell(m, k):
                name = _scale_of(m, k[0], k[1])
                x = ((_run(m, k[0]) or {}).get("labels") or {}).get(name or "")
                if not x:
                    return ["-"] * len(groups)
                if k[2] == "anchors":
                    return [str(x.get("anchors"))] + [""] * (len(groups) - 1)
                b = x["by_step"].get(k[2])
                fmt = ".1f" if key == "pos_mm" else ".2f"
                return [_f(b.get(f"{key}_{g}"), fmt) if b else "-" for g in groups]
            return cell
        def show(k):
            return (k[0], k[1], k[2] if k[2] == "anchors" else _step_dt(k[2]))
        for key, title in (("pos_mm", "Tool label position error tool_t->tool_t+dt [mm]"),
                           ("rot_deg", "Tool label rotation error [deg]")):
            L += _ctable(title, ["run", "scale", "dt"], ["median", "p90"], lab_keys, exps,
                         lab(key, ["median", "p90"]), show)

        ch_keys = []
        for r in slam_runs:
            for sk in ("oracle", "configured"):
                chs = [((_run(m, r) or {}).get("chunk") or {}).get(_scale_of(m, r, sk) or "") for _, m in exps]
                labs = [((_run(m, r) or {}).get("labels") or {}).get(_scale_of(m, r, sk) or "") for _, m in exps]
                if labs[0]:
                    ch_keys += [(r, sk, h) for h in (_chunk_hs(chs) or ["-"])]

        def ch_cell(m, k):
            c = ((_run(m, k[0]) or {}).get("chunk") or {}).get(_scale_of(m, k[0], k[1]) or "") or {}
            v = c.get(k[2])
            return [_f(v.get("pos_mm_mean"), ".1f"), _f(v.get("rot_deg_mean"), ".2f")] if v else ["-", "-"]
        L += _ctable("Chunk-length label error, mean over anchors of the mean over steps 1..H",
                     ["run", "scale", "H"], ["pos mm", "rot deg"], ch_keys, exps, ch_cell)

    gkeys = []
    for _, m in exps:
        g = (m or {}).get("gt_noise") or {}
        for dt, v in (g.get("by_dt") or {}).items():
            if v.get("n") and ("same tiles", dt) not in gkeys:
                gkeys.append(("same tiles", dt))
    gkeys.append(("tile set changes", "-"))

    def g_cell(m, k):
        g = (m or {}).get("gt_noise") or {}
        v = g.get("tile_switch") if k[0] == "tile set changes" else (g.get("by_dt") or {}).get(k[1])
        if not v or not v.get("n"):
            return ["-", "-", "-"]
        return [str(v["n"]), f"{_f(v.get('rot_deg_median'))} / {_f(v.get('rot_deg_p95'))}",
                f"{_f(v.get('trans_mm_median'), '.1f')} / {_f(v.get('trans_mm_p95'), '.1f')}"]
    if any((m or {}).get("gt_noise") for _, m in exps):
        L += _ctable("Ground-truth noise floor", ["pairs", "dt"], ["n", "rot deg med / p95", "trans mm med / p95"],
                     gkeys, exps, g_cell)
    return L


# ====================================================================== reproducibility
def headline_items(m, dts):
    """Headline numbers of a canonical metrics dict: [(row, col, value, kind)], kind in
    deg/mm/frac/count (for formatting). Rows group the columns of one quantity (dts, steps, H)."""
    out = []
    for run, x in m["runs"].items():
        if run == "static":
            continue
        h = x["head"]
        for g in ("median", "p95"):
            for d in dts:
                out.append((f"{run} head rotation {g} [deg]", f"{d} s", (h["rot_deg"].get(d) or {}).get(g), "deg"))
        for name in _scale_names(x):
            if name not in h["trans_mm"]:
                continue
            kind = "oracle" if name == ORACLE else name
            for g in ("median", "p95"):
                for d in dts:
                    out.append((f"{run} head translation {g}, {kind} scale [mm]", f"{d} s",
                                (h["trans_mm"][name].get(d) or {}).get(g), "mm"))
        out.append((f"{run} tracking failures", "", x.get("track_fail_frac"), "frac"))
        out.append((f"{run} keyframes / segment", "", (x.get("slam") or {}).get("keyframes_per_segment"), "count"))
        b = x.get("scale")
        if b:
            row = f"{run} scale {b['label']} error vs oracle"
            out += [(row, "abs median", b.get("abs_err_median"), "frac"),
                    (row, "abs p90", b.get("abs_err_p90"), "frac"),
                    (row, "bias", b.get("bias_median"), "frac")]
        for name in _scale_names(x):
            lab = (x.get("labels") or {}).get(name)
            if not lab:
                continue
            kind = "oracle" if name == ORACLE else name
            for key, unit in (("pos_mm", "mm"), ("rot_deg", "deg")):
                for j in _sorted_num(lab["by_step"]):
                    out.append((f"{run} label {key.split('_')[0]} median, {kind} scale [{unit}]", _step_dt(j),
                                lab["by_step"][j].get(f"{key}_median"), unit))
            c = (x.get("chunk") or {}).get(name) or {}
            for key, unit in (("pos_mm", "mm"), ("rot_deg", "deg")):
                for hh in _sorted_num(c):
                    out.append((f"{run} chunk mean {key.split('_')[0]}, {kind} scale [{unit}]", f"H={hh}",
                                c[hh].get(f"{key}_mean"), unit))
    return out


def metric_deltas(main, rep, dts):
    a = {(r, c): (v, k) for r, c, v, k in headline_items(main, dts)}
    out = []
    for r, c, v, k in headline_items(rep, dts):
        m0 = a.get((r, c), (None, k))[0]
        out.append({"row": r, "col": c, "kind": k, "main": _num(m0), "repro": _num(v),
                    "delta": _num(v) - _num(m0) if _finite(v) and _finite(m0) else None})
    seen = {(d["row"], d["col"]) for d in out}
    for (r, c), (v, k) in a.items():
        if (r, c) not in seen:
            out.append({"row": r, "col": c, "kind": k, "main": _num(v), "repro": None, "delta": None})
    return out


def scale_s_diffs(main_sc, rep_sc):
    """Per-segment s_repro / s_main - 1 of two scale_<run>.json files."""
    sm = {r["segment"]: r.get("s") for r in main_sc.get("rows", [])}
    per = {}
    for r in rep_sc.get("rows", []):
        a, b = sm.get(r["segment"]), r.get("s")
        per[r["segment"]] = float(b / a - 1) if _finite(a) and _finite(b) and a != 0 else None
    d = np.array([abs(v) for v in per.values() if v is not None])
    worst = max((s for s in per if per[s] is not None), key=lambda s: abs(per[s]), default=None)
    return {"per_segment": per, "n": int(len(d)),
            "abs_median": float(np.median(d)) if len(d) else None,
            "abs_max": float(d.max()) if len(d) else None, "worst": worst,
            "flagged_main": main_sc.get("summary", {}).get("flagged"),
            "flagged_repro": rep_sc.get("summary", {}).get("flagged")}


def trajectory_extent(c):
    """Largest distance between two camera centres (N, 3)."""
    best = 0.0
    for i in range(0, len(c), 256):
        d = np.linalg.norm(c[i:i + 256, None, :] - c[None, :, :], axis=-1)
        best = max(best, float(d.max()))
    return best


def compare_trajectories(T_main, T_rep, wall, dts):
    """Differences of two trajectories of the same frames (NaN rows = untracked).

    rot_diff[dt]  angle(R_rel_main^T R_rel_repro) [deg] of cam_t->cam_t+dt for every frame pair
                  (slam.evaluate.pairs_for pairing on the wall times) tracked in both
    sim3          repro camera centres Sim3-aligned (Umeyama) onto main: RMS residual, the
                  extent of the main trajectory (largest centre distance), their ratio, the scale
    """
    from slam import evaluate as EV
    from slam import geometry as G
    T_main, T_rep = np.asarray(T_main, float), np.asarray(T_rep, float)
    if T_main.shape != T_rep.shape:
        raise ValueError(f"trajectory shapes differ: {T_main.shape} vs {T_rep.shape}")
    ok_m = np.isfinite(T_main).all((1, 2))
    ok_r = np.isfinite(T_rep).all((1, 2))
    ok = ok_m & ok_r
    S = {"wall": np.asarray(wall, float), "strict": ok, "in_ep": np.ones(len(ok), bool)}
    rot = {}
    for d in dts:
        P = EV.pairs_for(S, float(d))
        if len(P) == 0:
            rot[dt_key(d)] = np.zeros(0)
            continue
        a, b = P[:, 0], P[:, 1]
        rm = G.inv(T_main[a]) @ T_main[b]
        rr = G.inv(T_rep[a]) @ T_rep[b]
        rot[dt_key(d)] = G.rot_angle_deg(np.swapaxes(rm[:, :3, :3], 1, 2) @ rr[:, :3, :3])
    sim3 = {"n": int(ok.sum()), "rms": None, "extent": None, "rms_over_extent": None, "scale": None}
    if ok.sum() >= 3:
        cm, cr = T_main[ok, :3, 3], T_rep[ok, :3, 3]
        ext = trajectory_extent(cm)
        if ext > 0 and np.ptp(cr, axis=0).max() > 0:
            s, R, t = G.umeyama_scale(cr, cm)
            res = cm - (s * (R @ cr.T).T + t)
            rms = float(np.sqrt((res ** 2).sum(1).mean()))
            sim3.update(rms=rms, extent=ext, rms_over_extent=rms / ext, scale=float(s))
    return {"n_frames": int(len(ok)), "tracked_main": int(ok_m.sum()), "tracked_repro": int(ok_r.sum()),
            "rot_diff": rot, "sim3": sim3}


def _frames_json(work, slam_key, seg, extra_dirs=()):
    """frames.json of a segment: the preprocess entry the SLAM entry was computed from
    (its manifest's deps), else a view directory."""
    cands = []
    man = Path(work) / "cache" / "slam" / slam_key / "manifest.json"
    if man.exists():
        pk = (_read(man).get("deps") or {}).get("preprocess")
        if isinstance(pk, str):
            cands.append(Path(work) / "cache" / "preprocess" / pk / seg / "frames.json")
    cands += [Path(d) / seg / "frames.json" for d in extra_dirs]
    for p in cands:
        if p.exists():
            return p
    return None


def _n_keyframes(out):
    n = out["meta"].get("n_keyframes")
    if n is None and "kf_t" in out:
        n = len(out["kf_t"])
    return None if n is None else int(n)


def compare_slam_node(work, key_main, key_rep, segments, dts, view_dirs=()):
    """Trajectory differences of one SLAM node between two cache keys, per segment and pooled."""
    from slam.backends import base as B
    work = Path(work)
    per, pooled = {}, {dt_key(d): [] for d in dts}
    for seg in segments:
        pm = work / "cache" / "slam" / key_main / seg / "traj.npz"
        pr = work / "cache" / "slam" / key_rep / seg / "traj.npz"
        if not (pm.exists() and pr.exists()):
            per[seg] = {"error": f"missing {'main' if not pm.exists() else 'repro'} traj.npz"}
            continue
        om, orp = B.load_output(pm), B.load_output(pr)
        fj = _frames_json(work, key_main, seg, view_dirs)
        if fj is not None:
            fr = _read(fj)["frames"]
            wall, times = np.array([f["wall"] for f in fr], float), "frames.json"
        else:                                          # nominal 30 fps on the original frame index
            wall, times = np.asarray(om["k"], float) / 30.0, "frame index / 30 fps"
        if len(wall) != len(om["T_slam_cam"]) or not np.array_equal(om["k"], orp["k"]):
            per[seg] = {"error": "frame lists differ between main and repro (or frames.json)"}
            continue
        c = compare_trajectories(om["T_slam_cam"], orp["T_slam_cam"], wall, dts)
        kf = (_n_keyframes(om), _n_keyframes(orp))
        e = {"n_frames": c["n_frames"], "tracked_main": c["tracked_main"], "tracked_repro": c["tracked_repro"],
             "times": times, "rot_diff_deg": {d: _stat(v) for d, v in c["rot_diff"].items()}, "sim3": c["sim3"],
             "keyframes": {"main": kf[0], "repro": kf[1],
                           "diff": kf[1] - kf[0] if None not in kf else None}}
        per[seg] = e
        for d, v in c["rot_diff"].items():
            pooled[d].append(v)
    ok = [v for v in per.values() if "error" not in v]
    roe = [v["sim3"]["rms_over_extent"] for v in ok if v["sim3"]["rms_over_extent"] is not None]
    kfd = [v["keyframes"]["diff"] for v in ok if v["keyframes"]["diff"] is not None]
    worst_sim3 = max((s for s, v in per.items() if "error" not in v and v["sim3"]["rms_over_extent"] is not None),
                     key=lambda s: per[s]["sim3"]["rms_over_extent"], default=None)
    pooled_st = {d: _stat(np.concatenate(v) if v else np.zeros(0)) for d, v in pooled.items()}
    worst_seg = {}
    for d in pooled:
        cand = [(v["rot_diff_deg"][d].get("median"), s) for s, v in per.items()
                if "error" not in v and v["rot_diff_deg"][d].get("n")]
        if cand:
            mx = max(cand)
            worst_seg[d] = {"segment": mx[1], "median": mx[0]}
    return {"key_main": key_main, "key_repro": key_rep, "segments_compared": len(ok),
            "segments_missing": sorted(s for s, v in per.items() if "error" in v),
            "rot_diff_deg_pooled": pooled_st, "rot_diff_worst_segment_median": worst_seg,
            "sim3_rms_over_extent": {"n": len(roe), "median": float(np.median(roe)) if roe else None,
                                     "max": float(max(roe)) if roe else None, "worst": worst_sim3},
            "keyframes": {"segments_differing": int(sum(d != 0 for d in kfd)), "segments": len(kfd),
                          "max_abs_diff": int(max(abs(d) for d in kfd)) if kfd else None,
                          "mean_diff": float(np.mean(kfd)) if kfd else None},
            "per_segment": per}


def build_repro(job, main_metrics, dts):
    rp = job.spec.get("repro")
    if not rp:
        return None
    variants = job.spec["variants"]
    main_dir = Path(variants["main"])
    work = Path(job.spec["work"])
    view_dirs = [main_dir.parent / "view" / job.session / "segments"]
    out = {"node": rp["node"], "dt_show": dts, "segments": len(job.segments),
           "base_keys": rp.get("base_keys", {}), "variants": {}}
    main_idx = results_index(main_dir)
    for r in rp.get("runs", []):
        v = r["variant"]
        vdir = Path(variants[v])
        m = variant_metrics(vdir, job.experiment.get("name"), v)
        rep_idx = results_index(vdir)
        sdiff = {}
        for run, ri in main_idx.get("runs", {}).items():
            a = ri.get("scale")
            b = (rep_idx.get("runs", {}).get(run) or {}).get("scale")
            if a and b and (main_dir / a).exists() and (vdir / b).exists():
                sdiff[run] = scale_s_diffs(_read(main_dir / a), _read(vdir / b))
        traj = {}
        for nid, key in sorted(rp.get("base_keys", {}).items()):
            rk = (r.get("keys") or {}).get(nid)
            if not nid.startswith("slam.") or rk is None:
                continue
            job.log(f"repro {v}: comparing {nid} trajectories ({key} vs {rk})")
            traj[nid] = compare_slam_node(work, key, rk, job.segments, dts, view_dirs)
        out["variants"][v] = {"keys": r.get("keys", {}), "metrics": metric_deltas(main_metrics, m, dts),
                              "scale_s": sdiff, "trajectories": traj}
    return out


def _max_finite(values):
    """Largest finite value (None if there is none: nothing was compared)."""
    x = [float(v) for v in values if _finite(v)]
    return max(x) if x else None


def _fmt_kind(v, kind, delta=False, signed=None):
    """Value (delta=False) or difference (delta=True: finer, signed unless signed=False)."""
    if not _finite(v):
        return "-"
    sign = "+" if (delta if signed is None else signed) else ""
    if kind == "frac":
        return format(100 * v, sign + ".2f") + ("pp" if delta else "%")
    if kind == "mm":
        return format(v, sign + (".2f" if delta else ".1f"))
    if kind == "count":
        return format(v, sign + ".1f")
    return format(v, sign + (".3f" if delta else ".2f"))


def render_repro(rep, exp):
    vs = list(rep["variants"])
    L = [f"# Reproducibility: {exp}, {rep['node']} recomputed {len(vs)} time(s)", "",
         f"Same configuration; {rep['node']} recomputed under a cache tag ({', '.join(vs)}) and every "
         "step downstream of it rerun. Differences vs the main run. Rotation difference = "
         "angle(R_rel_main^T R_rel_repro) of cam_t->cam_t+dt over all frame pairs tracked in both; "
         "Sim3 = repro camera centres aligned to main by a similarity, RMS residual / largest centre "
         "distance of the main trajectory.", ""]
    # ---------------- tolerance table: one row per quantity, columns joined over dt / step / H
    rows_order, groups = [], {}
    for v in vs:
        for d in rep["variants"][v]["metrics"]:
            if d["row"] not in groups:
                rows_order.append(d["row"])
                groups[d["row"]] = {}
            groups[d["row"]].setdefault(d["col"], {"kind": d["kind"], "main": d["main"], "deltas": {}})
            groups[d["row"]][d["col"]]["deltas"][v] = d["delta"]
    trows = []
    for row in rows_order:
        cols = groups[row]
        names = [c for c in cols if c]
        label = row + (f" ({' / '.join(names)})" if names else "")
        main = " / ".join(_fmt_kind(c["main"], c["kind"]) for c in cols.values())
        per_v = [" / ".join(_fmt_kind(c["deltas"].get(v), c["kind"], True) for c in cols.values()) for v in vs]
        mx = " / ".join(_fmt_kind(max((abs(c["deltas"][v]) for v in vs if _finite(c["deltas"].get(v))),
                                      default=None), c["kind"], True, False) for c in cols.values())
        trows.append([label, main] + per_v + [mx])
    s_runs = sorted({run for v in vs for run in rep["variants"][v]["scale_s"]})
    for run in s_runs:
        cells = []
        for v in vs:
            sd = rep["variants"][v]["scale_s"].get(run)
            cells.append(f"{_pct(sd.get('abs_median'), '.2f')} / {_pct(sd.get('abs_max'), '.2f')}"
                         + (f" ({sd['worst']})" if sd and sd.get("worst") else "") if sd else "-")
        mx = _max_finite((rep["variants"][v]["scale_s"].get(run) or {}).get("abs_max") for v in vs)
        trows.append([f"{run} per-segment scale \\|s_repro/s_main - 1\\| median / max", "-"] + cells + [_pct(mx, ".2f")])
    nodes = sorted({n for v in vs for n in rep["variants"][v]["trajectories"]})
    dts = [dt_key(d) for d in rep["dt_show"]]
    for nid in nodes:
        T = {v: rep["variants"][v]["trajectories"].get(nid) for v in vs}
        for g in ("median", "p95", "max"):
            cells = [" / ".join(_f((t["rot_diff_deg_pooled"].get(d) or {}).get(g), ".3f") for d in dts) if t else "-"
                     for t in T.values()]
            mx = " / ".join(_f(_max_finite((t["rot_diff_deg_pooled"].get(d) or {}).get(g) for t in T.values() if t),
                               ".3f") for d in dts)
            trows.append([f"{nid} rotation difference, pooled {g} [deg] ({' / '.join(d + ' s' for d in dts)})", "-"]
                         + cells + [mx])
        cells = [(f"{_pct(t['sim3_rms_over_extent']['median'], '.2f')} / {_pct(t['sim3_rms_over_extent']['max'], '.2f')}"
                  + (f" ({t['sim3_rms_over_extent']['worst']})" if t['sim3_rms_over_extent'].get('worst') else ""))
                 if t else "-" for t in T.values()]
        mx = _max_finite(t["sim3_rms_over_extent"]["max"] for t in T.values() if t)
        trows.append([f"{nid} Sim3-aligned centre RMS / extent, median / max over segments", "-"] + cells + [_pct(mx, ".2f")])
        cells = [f"{t['keyframes']['segments_differing']}/{t['keyframes']['segments']} segments, "
                 f"max {_f(t['keyframes']['max_abs_diff'], '.0f')}" if t and t["keyframes"]["segments"] else "-"
                 for t in T.values()]
        mx = _max_finite(t["keyframes"]["max_abs_diff"] for t in T.values() if t)
        trows.append([f"{nid} keyframe count: segments differing, max \\|diff\\|", "-"] + cells + [_f(mx, ".0f")])
    L += ["## Tolerance", "",
          "Main value, repro - main per repeat, and the largest \\|difference\\| (pp = percentage points).", ""]
    L += _table(["quantity", "main"] + [f"{v} - main" for v in vs] + ["max \\|diff\\|"], trows)
    # ---------------- per-segment trajectory details
    for v in vs:
        for nid, t in rep["variants"][v]["trajectories"].items():
            L += [f"## {v}: {nid} per segment", "",
                  f"Keys: main {t['key_main']}, repro {t['key_repro']}. Rotation difference median / p95 [deg].", ""]
            rows = []
            for seg, e in t["per_segment"].items():
                if "error" in e:
                    rows.append([seg] + ["-"] * len(dts) + [e["error"], "-", "-"])
                    continue
                rows.append([seg] + [f"{_s(e['rot_diff_deg'].get(d), 'median', '.3f')} / {_s(e['rot_diff_deg'].get(d), 'p95', '.3f')}"
                                     for d in dts]
                            + [_pct(e["sim3"]["rms_over_extent"], ".2f"),
                               f"{e['tracked_main']} / {e['tracked_repro']} of {e['n_frames']}",
                               f"{e['keyframes']['main']} / {e['keyframes']['repro']}"])
            L += _table(["segment"] + [f"{d} s" for d in dts] + ["Sim3 RMS / extent", "tracked main / repro",
                                                                  "keyframes main / repro"], rows)
    return "\n".join(L) + "\n"


# ====================================================================== entry point
def run_report(job):
    params = job.params
    dts = [dt_key(d) for d in params.get("dt_show", [])]
    variants = job.spec["variants"]
    main_dir = Path(variants["main"])
    out = Path(job.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    exp = job.experiment.get("name") or out.parent.name

    metrics = variant_metrics(main_dir, exp, "main")
    _write_json(out / "metrics.json", metrics)
    copied = copy_small_files(main_dir, out)
    job.log(f"metrics.json written; copied {len(copied)} files from {main_dir}")

    scale_files = {}
    for run, r in results_index(main_dir).get("runs", {}).items():
        if r.get("scale") and (main_dir / r["scale"]).exists():
            scale_files[run] = _read(main_dir / r["scale"])

    exps, sources = [(exp, metrics)], {}
    root = Path(job.spec.get("experiments_root") or out.parent.parent)
    for name in params.get("compare", []):
        if name == exp:
            continue
        m, src = load_experiment(root, name)
        exps.append((name, m))
        sources[name] = src
        job.log(f"compare {name}: {src}")

    rep = build_repro(job, metrics, dts)
    L = [f"# {exp}: report (variant main)", "",
         f"{metrics['n_segments']} segments. Runs: {', '.join(r for r in metrics['runs'] if r != 'static')} "
         "(static = head motion identity, no SLAM). Ground truth: tile head poses; "
         "\"oracle (tiles)\" = per-segment scale fitted to the tile poses (evaluation only).", ""]
    L += render_main(metrics, dts, scale_files)
    if rep:
        L += ["## Reproducibility", "",
              f"{rep['node']} recomputed {len(rep['variants'])} time(s): see `repro.md` (tolerance table) and `repro.json`.", ""]
    if len(exps) > 1:
        L += render_compare(exps, dts, sources)
    (out / "report.md").write_text("\n".join(L) + "\n")
    result = {"metrics": str(out / "metrics.json"), "report": str(out / "report.md"), "copied": len(copied),
              "compare": sources}
    if rep:
        _write_json(out / "repro.json", rep)
        (out / "repro.md").write_text(render_repro(rep, exp))
        result["repro"] = str(out / "repro.md")
    job.log(f"report -> {out / 'report.md'}")
    return result
