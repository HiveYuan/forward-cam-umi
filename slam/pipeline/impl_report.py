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
  report.md         short tables (sample sizes n under the head and label tables; rotation
                    label / chunk rows shown once when they are the same for every scale), a
                    'Mask comparison' section per masks_<cand>_vs_<ref>.json (pooled stats, mean
                    and per-part areas, low / worst segments, where the overlay images are), then
                    side by side with every experiment in `compare`; after --repro one line per
                    repro variant (bit-identical segments, largest metric delta). An experiment
                    without SLAM runs (no analysis.json: e.g. masks + mask_compare only) gets the
                    mask sections only.
  copies            the main variant's scale_*.json/.md, labels_*.json, eval_*/summary.{json,md},
                    gt_noise.json, analysis.json, masks_*.json/.md (never pairs.csv, never the
                    overlay images); JSON copies are strict JSON (NaN / Infinity literals -> null;
                    the originals are left as they are)
  repro.json, repro.md   after --repro: headline metric deltas (each with its "run") and
                    trajectory differences of every recomputed SLAM node vs main, plus
                    "runs_recomputed" (the runs depending on the recomputed node); repro.md starts
                    with the per-variant summary lines and a tolerance table of those runs

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
   "evaluate": {"fail_deg": float|null, "dts": [s, ...]|null} | null,
   "masks": {"<cand>_vs_<ref>": {"reference", "candidate", "dilate_px", "parts", "n_segments",
                                 + the file's "summary": "frames", "iou", "recall", "precision",
                                 "extra_area", "missed_area", "cells_iou" (mask stats), "area_ref",
                                 "area_cand", "part_area", "segments_iou_median_below_0.8",
                                 "worst_segments"}}}
  stat = slam.evaluate.stats() dict; dt keys are strings as in the legacy summary.json ("0.08",
  "1.0"); scale_name = "oracle" (tile-fitted scale) or the run's scale label ("B+Acheck").
  chunk[scale_name][H] = slam.labels.chunk_stats fields, plus "steps_median" (median number of
  counted steps j <= H per anchor) when labels_*.json has it or the report could recount it from
  the analysis view's label files (<variant>/view; recount checked against the file's anchor
  counts); absent otherwise.
  Error fractions are fractions. "static" (head motion = identity, no SLAM) is kept as a
  baseline run with head metrics only (track_fail_frac, slam and scale null).
  evaluate = the evaluation parameters: fail_deg is the tracking-failure threshold behind
  track_fail_frac (analysis.json "evaluate"; 2.0 for the legacy adapter; null = unknown, a
  results dir without it), dts the evaluated pair intervals. The report prints the threshold
  and marks comparisons between experiments evaluated with different (or unknown) fail_deg.
  evaluate is null when nothing was evaluated (no analysis.json and no eval_oracle/: an
  experiment without SLAM runs; runs is then {}, gt_noise null, and n_segments counts the
  segments of the mask comparisons, else the report job's segments).
  masks = one block per mask_compare output masks_<cand>_vs_<ref>.json of the results dir ({}
  when there is none, e.g. every SLAM-only experiment); mask stat = {"n", "median", "p10", "p90",
  "mean"} over frames (fractions; areas as fractions of the frame). The overlay images stay in
  the work run directory (<work>/runs/<exp>/<variant>/overlays/<cand>_vs_<ref>/); report.md
  points to them.

Experiments without metrics.json (exp000_legacy) are read by legacy_metrics(), which builds
the same structure from the legacy files (results/eval/, results/<label>_eval/).
"""
import json
import math
import re
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
        json.dump(_clean(obj), f, indent=1, allow_nan=False)
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


MASK_PREFIX = "masks_"
MASK_IOU_LOW = "segments_iou_median_below_0.8"       # key of the mask_compare summary


def mask_files(res):
    """{"<cand>_vs_<ref>": path} of the mask_compare outputs masks_<cand>_vs_<ref>.json in a
    results dir (file name order)."""
    return {p.stem[len(MASK_PREFIX):]: p for p in sorted(Path(res).glob(f"{MASK_PREFIX}*_vs_*.json"))
            if p.is_file()}


def masks_block(mc):
    """masks_<cand>_vs_<ref>.json (mask_compare contract) -> canonical metrics block: what was
    compared (reference, candidate, dilate_px, parts, n_segments) and the file's pooled summary."""
    out = {"reference": mc.get("reference"), "candidate": mc.get("candidate"), "dilate_px": mc.get("dilate_px"),
           "parts": list(mc.get("parts") or []), "n_segments": len(mc.get("segments") or {})}
    out.update(mc.get("summary") or {})
    return out


def masks_metrics(res):
    """{"<cand>_vs_<ref>": masks_block} of a results dir ({} without mask comparisons)."""
    return {name: masks_block(_read(p)) for name, p in mask_files(res).items()}


def mask_segments(res):
    """Segments of the mask comparisons of a results dir (union, sorted)."""
    segs = set()
    for p in mask_files(res).values():
        segs |= set(_read(p).get("segments") or {})
    return sorted(segs)


def _summary_path(base, rel):
    if not rel:
        return None
    p = Path(base) / rel
    if p.is_dir():
        p = p / "summary.json"
    return p if p.exists() else None


def discover_index(res):
    """analysis.json-shaped index of a results dir that has no analysis.json (file names of
    the analysis contract). Without eval_oracle/ nothing was evaluated: "evaluate" is None and
    the segments are those of the mask comparisons (an experiment without SLAM runs)."""
    res = Path(res)
    o = res / "eval_oracle" / "summary.json"
    S = _read(o) if o.exists() else {"runs": {}, "segments": {}}
    runs = [r for r in S["runs"] if r != "static"]
    for p in sorted(res.glob("scale_*.json")) + sorted(res.glob("labels_*.json")):
        name = p.stem.split("_", 1)[1].split("@")[0]
        if name not in runs and name != "tiles":
            runs.append(name)
    idx = {"runs": {}, "gt_noise": "gt_noise.json" if (res / "gt_noise.json").exists() else None,
           "segments": sorted(S.get("segments", {})) or mask_segments(res),
           "evaluate": {"fail_deg": S.get("fail_deg"), "dts": S.get("dts")}     # fail_deg: unknown
           if o.exists() else None}
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
    segs = index.get("segments") or sorted((oracle_any or {}).get("segments", {})) or mask_segments(base)
    ev = index.get("evaluate")
    if ev is None and "evaluate" in index and oracle_any is None:
        evaluate = None                                  # nothing evaluated (discover_index)
    else:
        ev = ev or {}
        evaluate = {"fail_deg": _num(ev.get("fail_deg")),
                    "dts": ev.get("dts") if ev.get("dts") is not None else (oracle_any or {}).get("dts")}
    return _clean({"experiment": experiment, "variant": variant, "n_segments": len(segs),
                   "runs": runs, "gt_noise": load(index.get("gt_noise")), "evaluate": evaluate,
                   "masks": masks_metrics(base)})


def results_index(res):
    p = Path(res) / "analysis.json"
    return _read(p) if p.exists() else discover_index(res)


def variant_metrics(res, experiment, variant):
    return build_metrics(res, results_index(res), experiment, variant)


def chunk_steps_median(view, session, lab):
    """{H: median number of counted steps j <= H per anchor} of a labels_*.json result (`lab`),
    recounted with slam.labels.anchor_errors on the label files of the analysis view
    (<view>/<session>/segments/epNN/labels/<lab['ref']>.npz, tiles.npz) - the anchors behind
    the file's chunk numbers. None when the view is missing or the recount does not reproduce
    the file's anchor counts (total, per chunk H, per by_step j)."""
    from slam import config as C
    from slam import labels as Lb
    chunk = lab.get("chunk") or {}
    if not chunk or not lab.get("ref") or not (Path(view) / session / "segments").is_dir():
        return None
    hs = _sorted_num(chunk)
    old = C.WORK
    C.WORK = Path(view)                               # slam.labels reads <WORK>/<session>/segments
    try:
        steps = [{j for j, _, _ in e}
                 for _, _, e in Lb.anchor_errors(session, lab["ref"], int(hs[-1]), lab.get("excluded") or ())]
    finally:
        C.WORK = old
    if len(steps) != lab.get("anchors"):
        return None
    for j, b in (lab.get("by_step") or {}).items():
        if int(j) <= int(hs[-1]) and sum(int(j) in s for s in steps) != b.get("n"):
            return None
    out = {}
    for h in hs:
        c = [n for n in (sum(j <= int(h) for j in s) for s in steps) if n]
        if len(c) != chunk[h].get("anchors"):
            return None
        out[h] = float(np.median(c)) if c else None
    return out


def add_chunk_steps(metrics, res, view, session, log=print):
    """Adds chunk[scale][H]["steps_median"] to canonical metrics where labels_*.json lacks it,
    recounted from the analysis view (chunk_steps_median). Returns {labels file: 'file' |
    'recounted' | 'not recorded'}."""
    res, done = Path(res), {}
    for run, r in results_index(res).get("runs", {}).items():
        x = metrics["runs"].get(run) or {}
        for kind, name in (("oracle", ORACLE), ("scaled", r.get("scale_label"))):
            rel = (r.get("labels") or {}).get(kind)
            ch = (x.get("chunk") or {}).get(name) if name else None
            if not ch or not rel or not (res / rel).exists():
                continue
            if all(_finite(v.get("steps_median")) for v in ch.values()):
                done[rel] = "file"
                continue
            st = chunk_steps_median(view, session, _read(res / rel))
            if st is None:
                done[rel] = "not recorded"
                continue
            for h, v in st.items():
                if h in ch:
                    ch[h]["steps_median"] = v
            done[rel] = "recounted"
    for rel, how in done.items():
        log(f"chunk counted steps per anchor of {rel}: {how}" + (f" (from {view})" if how == "recounted" else ""))
    return done


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
COPY_PATTERNS = ("scale_*.json", "scale_*.md", "labels_*.json", "gt_noise.json", "analysis.json",
                 f"{MASK_PREFIX}*.json", f"{MASK_PREFIX}*.md")


def copy_strict(src, dst):
    """Copy a file; a .json file as strict JSON: Python's json writes NaN / Infinity literals
    (e.g. slam.evaluate's summary.json), which become null in the copy. A JSON file without
    them is copied unchanged."""
    src, dst = Path(src), Path(dst)
    if src.suffix == ".json":
        obj = _read(src)
        clean = _clean(obj)
        if clean != obj:                                 # NaN != None (and NaN != NaN)
            tmp = dst.with_name(dst.name + ".tmp")
            with open(tmp, "w") as f:
                json.dump(clean, f, indent=1, allow_nan=False)
            tmp.replace(dst)
            return
    shutil.copy2(src, dst)


def copy_small_files(src, dst):
    """The main variant's small analysis files -> results/ (never pairs.csv)."""
    src, dst = Path(src), Path(dst)
    out = []
    if src.resolve() == dst.resolve():
        return out
    for pat in COPY_PATTERNS:
        for p in sorted(src.glob(pat)):
            if p.is_file():
                copy_strict(p, dst / p.name)
                out.append(p.name)
    for d in sorted(src.glob("eval_*")):
        if not d.is_dir():
            continue
        for f in ("summary.json", "summary.md"):
            if (d / f).is_file():
                (dst / d.name).mkdir(parents=True, exist_ok=True)
                copy_strict(d / f, dst / d.name / f)
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


def _h_label(h):
    return f"H={h} ({int(h) / LABEL_FPS:.2f} s)"


def _dt_s(d):
    return f"{d} s"


def _count(v):
    """A count or a median of counts: '49', '46.5', '-'."""
    if not _finite(v):
        return "-"
    return str(int(v)) if float(v).is_integer() else format(float(v), ".1f")


def _ns(by_col, cols, key="n"):
    """{col: n} of {col: stat dict}."""
    return {c: (by_col.get(c) or {}).get(key) for c in cols}


def _n_note(what, rows, cols, show_col):
    """Footnote with the sample size per column under a table. rows: [(row label, {col: n})];
    rows with the same n share a line (one line when all agree)."""
    if not rows:
        return []
    groups = {}
    for label, ns in rows:
        groups.setdefault(tuple(_count(ns.get(c)) for c in cols), []).append(label)

    def line(key):
        return ", ".join(f"{show_col(c)}: {n}" for c, n in zip(cols, key))
    if len(groups) == 1:
        return [f"n [{what}]: {line(next(iter(groups)))}", ""]
    return [f"n [{what}]:", ""] + [f"- {', '.join(labels)}: {line(k)}" for k, labels in groups.items()] + [""]


def _same(a, b, rel=1e-9):
    """Equal numbers up to float noise (two missing values are equal)."""
    if not (_finite(a) and _finite(b)):
        return _finite(a) == _finite(b)
    a, b = float(a), float(b)
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


LAB_ROT = ("n", "rot_deg_median", "rot_deg_p90")
CHUNK_ROT = ("anchors", "rot_deg_mean", "rot_deg_median", "rot_deg_p90")
CHUNK_COUNTS = ("anchors", "steps_median")
SCALE_FREE = "(rotation is scale-free: same for every scale)"
LABELS_NOTE = ("The \"Tool labels\" tables are the slam.labels check on the 15 fps training timeline: the relative "
               "chunk tool_t->tool_t+dt (dt = j/15 s) from the run's label file vs from the tile label file, over "
               "anchors t where both label series are gap-free (`labels_<run>[@<scale>].json`); the label columns "
               "of `eval_*/summary.md` are a different, pair-based metric: camera frame pairs at exactly dt with "
               "the ball poses at both ends, tile vs SLAM head motion (no 15 fps resampling, gaps or coverage "
               "rules).")


def _same_fields(dicts, fields):
    """True if two or more {key: {field: value}} dicts have the same keys and the same fields."""
    dicts = [d for d in dicts if d]
    if len(dicts) < 2 or any(set(d) != set(dicts[0]) for d in dicts):
        return False
    return all(_same(d[k].get(f), dicts[0][k].get(f)) for d in dicts[1:] for k in d for f in fields)


def _labels_scale_free(labs):
    """True if two or more scales' label entries ({anchors, by_step}) have the same rotation
    numbers: rotation does not depend on the scale, so the rows are shown once."""
    labs = [x for x in labs if x]
    return (len(labs) >= 2 and all(_same(x.get("anchors"), labs[0].get("anchors")) for x in labs)
            and _same_fields([x.get("by_step") or {} for x in labs], LAB_ROT))


# ====================================================================== report.md (this experiment)
def render_main(m, dts, scale_files=None):
    """Tables of one experiment's canonical metrics. scale_files: {run: scale_<run>.json dict}
    for details only the contract file has (flag threshold)."""
    scale_files = scale_files or {}
    runs = list(m["runs"])
    slam_runs = [r for r in runs if r != "static"]
    L = []
    hdr = ["run"] + [_dt_s(d) for d in dts]
    L += ["## Head rotation error cam_t->cam_t+dt [deg], median / p95", ""]
    rot = {r: m["runs"][r]["head"]["rot_deg"] for r in runs}
    L += _table(hdr, [[r] + [f"{_s(rot[r].get(d))} / {_s(rot[r].get(d), 'p95')}" for d in dts] for r in runs])
    L += _n_note("frame pairs", [(r, _ns(rot[r], dts)) for r in runs], dts, _dt_s)
    rows, nrows = [], []
    for r in slam_runs:
        tr = m["runs"][r]["head"]["trans_mm"]
        for name in _scale_names(m["runs"][r]):
            if name in tr:
                rows.append([r, _sname(name)] + [f"{_s(tr[name].get(d))} / {_s(tr[name].get(d), 'p95')}" for d in dts])
                nrows.append((f"{r} {_sname(name)}", _ns(tr[name], dts)))
    L += ["## Head translation error [mm], median / p95", ""]
    L += _table(["run", "scale"] + hdr[1:], rows)
    L += _n_note("frame pairs", nrows, dts, _dt_s)
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

    lab_runs = [r for r in slam_runs if m["runs"][r].get("labels")]
    if lab_runs:
        L += render_labels(m, lab_runs)
        L += render_chunk(m, lab_runs)
    L += render_gt_noise(m.get("gt_noise"))
    return L


def render_labels(m, lab_runs):
    """The two 'Tool labels' tables (by step): position per scale; rotation once per run when
    it is the same for every scale."""
    L = []
    lab_rows = [(r, name, m["runs"][r]["labels"][name]) for r in lab_runs
                for name in _scale_names(m["runs"][r]) if name in m["runs"][r]["labels"]]
    steps = _steps(x for _, _, x in lab_rows)
    free = {r: _labels_scale_free([x for rr, _, x in lab_rows if rr == r]) for r in lab_runs}
    for key, title, fmt in (("pos_mm", "position error [mm]", ".1f"), ("rot_deg", "rotation error [deg]", ".2f")):
        rot = key == "rot_deg"
        note = f" {SCALE_FREE}" if rot and any(free.values()) else ""
        L += [f"## Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt {title}, "
              f"median / p90{note}", ""]
        if not rot:
            L += [LABELS_NOTE, ""]
        rows, nrows, shown = [], [], set()
        for r, name, lab in lab_rows:
            if rot and free[r]:
                if r in shown:
                    continue
                shown.add(r)
                sname = "every scale"
            else:
                sname = _sname(name)
            b = lab["by_step"]
            rows.append([r, sname, lab.get("anchors")] + [
                f"{_f(b[j].get(key + '_median'), fmt)} / {_f(b[j].get(key + '_p90'), fmt)}" if j in b else "-"
                for j in steps])
            nrows.append((f"{r} {sname}", _ns(b, steps)))
        L += _table(["run", "scale", "anchors"] + [_step_dt(j) for j in steps], rows)
        L += _n_note("anchors counting the step", nrows, steps, _step_dt)
    return L


def render_chunk(m, lab_runs):
    """Chunk-length label error: per H the anchors, the median counted steps per anchor, and
    mean / median over anchors of position (per scale) and rotation (once when scale-free)."""
    L = ["## Chunk-length label error over steps 1..H: per anchor the mean error over its counted steps, "
         "then mean / median over anchors", ""]
    chunks = {r: m["runs"][r].get("chunk") or {} for r in lab_runs}
    hs = _chunk_hs(c for ch in chunks.values() for c in ch.values())
    if not hs:
        return L + ["-", ""]
    steps_known = any(_finite(v.get("steps_median")) for ch in chunks.values() for c in ch.values() for v in c.values())
    rows, any_free = [], False
    for r in lab_runs:
        ch = chunks[r]
        names = [n for n in _scale_names(m["runs"][r]) if n in ch]
        if not names:
            rows.append([r, "-"] + ["-"] * len(hs))
            continue
        counts_once = len(names) == 1 or _same_fields([ch[n] for n in names], CHUNK_COUNTS)
        rot_once = len(names) > 1 and _same_fields([ch[n] for n in names], CHUNK_ROT)
        any_free |= rot_once
        for q, f in (("anchors", "anchors"), ("counted steps per anchor, median", "steps_median")):
            if f == "steps_median" and not steps_known:
                continue
            for n in names[:1] if counts_once else names:
                rows.append([r, q if counts_once else f"{q}, {_sname(n)}"]
                            + [_count(ch[n][h].get(f)) if h in ch[n] else "-" for h in hs])

        def cells(n, key, fmt):
            return [f"{_f(ch[n][h].get(key + '_mean'), fmt)} / {_f(ch[n][h].get(key + '_median'), fmt)}"
                    if h in ch[n] else "-" for h in hs]
        for n in names:
            rows.append([r, f"position [mm], {_sname(n)}, mean / median"] + cells(n, "pos_mm", ".1f"))
        for n in names[:1] if rot_once else names:
            rows.append([r, f"rotation [deg], {'every scale' if rot_once else _sname(n)}, mean / median"]
                        + cells(n, "rot_deg", ".2f"))
    L += _table(["run", "quantity"] + [_h_label(h) for h in hs], rows)
    if any_free:
        L += [SCALE_FREE, ""]
    ex = next(((r, c[hs[-1]]["steps_median"]) for r in lab_runs for c in chunks[r].values()
               if _finite((c.get(hs[-1]) or {}).get("steps_median"))), None)
    L += ["Steps past the episode end or at label gaps are left out of an anchor's chunk, so the long H are "
          "truncated chunks: " + (f"the counted-steps row gives per H the median number of steps j <= H an anchor "
                                  f"counts (e.g. {ex[0]}, H={hs[-1]}: {_count(ex[1])} of {hs[-1]})." if ex else
                                  "the number of counted steps per anchor is not recorded in labels_*.json (the "
                                  "by-step tables' n says how many anchors count step j)."), ""]
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


# ---------------------------------------------------------------------- mask comparison
# (stat key, row label, format): "share" = fraction shown as 0.853, "area" = fraction of the frame in %
MASK_QS = (("iou", "IoU", "share"),
           ("recall", "recall (share of the reference covered by the candidate)", "share"),
           ("precision", "precision (share of the candidate inside the reference)", "share"),
           ("extra_area", "extra area: candidate only [% of frame]", "area"),
           ("missed_area", "missed area: reference only [% of frame]", "area"),
           ("cells_iou", "DROID-cell IoU (masks dilated by {d} px)", "share"))
MASK_NOTE = ("Per frame, then pooled over every frame of every segment. IoU = intersection / union (1 when both "
             "masks are empty); recall = share of the reference pixels the candidate covers; precision = share "
             "of the candidate pixels inside the reference; extra / missed area = candidate-only / reference-only "
             "pixels as a share of the frame; DROID-cell IoU = IoU of the 1/8-resolution cells DROID ignores, each "
             "mask dilated by {d} px at full resolution first (a cell is ignored when any of its pixels is "
             "masked: slam.droid_masked.valid_grid). An empty denominator counts 1 (two empty masks: IoU 1; empty "
             "reference: recall 1; empty candidate: precision 1), so n = frames.")


def _mstat(st, key, kind):
    if not st or not st.get("n"):
        return "-"
    return _pct(st.get(key), ".2f") if kind == "area" else _f(st.get(key), ".3f")


def _worst_list(worst):
    """[[segment, IoU median], ...] -> 'ep05 0.612, ep12 0.701'."""
    return ", ".join("{} {}".format(w[0], _f(w[1], ".3f")) for w in worst or [] if len(w) >= 2) or "-"


def _parts_of(b):
    """Part names of a masks block: the declared parts, then any other part with an area."""
    out = list(b.get("parts") or [])
    return out + [p for p in (b.get("part_area") or {}) if p not in out]


def overlay_info(variant_results, name, work=None):
    """Where mask_compare wrote the overlay images of a comparison: <variant>/overlays/<name>/
    next to the variant's results/ (never copied into the experiment's results/).
    {"dir": path relative to the run dir (<work>/runs/<exp>/), "run_dir", "exists", "images",
    "kinds": {kind: count}} from its index.json (else the *.jpg files)."""
    vdir = Path(variant_results).parent
    d, run_dir = vdir / "overlays" / name, vdir.parent
    shown = str(run_dir)
    if work:
        try:
            shown = "<work>/" + run_dir.resolve().relative_to(Path(work).resolve()).as_posix()
        except ValueError:
            pass
    out = {"dir": f"{vdir.name}/overlays/{name}/", "run_dir": shown, "exists": d.is_dir(), "images": None, "kinds": {}}
    if (d / "index.json").is_file():
        idx = _read(d / "index.json")
        if isinstance(idx, dict):                        # tolerate {"images": [...]} as well as [...]
            idx = next((v for v in idx.values() if isinstance(v, list)), [])
        out["images"] = len(idx)
        for e in idx:
            k = e.get("kind") if isinstance(e, dict) else None
            out["kinds"][k or "?"] = out["kinds"].get(k or "?", 0) + 1
    elif d.is_dir():
        out["images"] = len(list(d.glob("*.jpg")))
    return out


def _overlay_line(o, work=None, parts=True):
    where = f"`{o['dir']}` in the experiment's work run directory `{o['run_dir']}/`"
    if work and o["run_dir"].startswith("<work>/"):
        where += f" (<work> = `{work}`)"
    if not o["exists"]:
        return f"Overlay images: not found (mask_compare writes them to {where})."
    n = "?" if o["images"] is None else str(o["images"])
    kinds = o.get("kinds") or {}
    what = ""
    if kinds:
        what = ": " + ", ".join(f"{c} {'evenly spaced' if k == 'even' else 'lowest-IoU' if k == 'worst' else k}"
                                for k, c in kinds.items())
    return (f"Overlay images (not copied into results/): {where}, {n} images{what}; candidate "
            f"{'parts filled in distinct colours' if parts else 'filled in colour'}, reference outlined in white; "
            "`index.json` lists file, segment, frame i, IoU and kind.")


def render_masks(m, overlays=None, work=None):
    """'Mask comparison' section per masks block of canonical metrics. overlays: {name:
    overlay_info()} (the pointer line is left out for a name without one)."""
    overlays = overlays or {}
    L = []
    for name, b in (m.get("masks") or {}).items():
        ref, cand, d = b.get("reference"), b.get("candidate"), b.get("dilate_px")
        L += [f"## Mask comparison: {cand} vs {ref} (reference)", "",
              f"{_count(b.get('frames'))} frames of {b.get('n_segments')} segments. " + MASK_NOTE.format(d=_deg(d))
              + f" Per segment: `{MASK_PREFIX}{name}.md`.", ""]
        rows = []
        for key, label, kind in MASK_QS:
            st = b.get(key) or {}
            rows.append([label.format(d=_deg(d)), _n_cell(st)] + [_mstat(st, g, kind) for g in ("median", "p10", "p90", "mean")])
        L += _table(["quantity", "n", "median", "p10", "p90", "mean"], rows)
        L += [f"Mean masked area [% of frame]: {ref} (reference) {_pct(b.get('area_ref'), '.2f')}, "
              f"{cand} (candidate) {_pct(b.get('area_cand'), '.2f')}.", ""]
        parts = _parts_of(b)
        if parts:
            pa = b.get("part_area") or {}
            L += _table([f"{cand} part", "mean area [% of frame]"], [[p, _pct(pa.get(p), ".2f")] for p in parts])
            L += ["Parts may overlap; their union is the candidate mask.", ""]
        low = list(b.get(MASK_IOU_LOW) or [])
        L += [f"Segments with IoU median < 0.8: {', '.join(low) or 'none'} ({len(low)} of {b.get('n_segments')}).", "",
              f"Worst segments (IoU median): {_worst_list(b.get('worst_segments'))}.", ""]
        if name in overlays:
            L += [_overlay_line(overlays[name], work, bool(parts)), ""]
    return L


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
    """Scale name of kind 'oracle', 'configured' or 'any' (scale-free rows: the oracle's if the
    run has oracle labels, else the configured scale's)."""
    x = _run(m, run)
    if x is None:
        return None
    if kind == "any":
        return ORACLE if ORACLE in (x.get("labels") or {}) or ORACLE in (x.get("chunk") or {}) else _configured(x)
    return ORACLE if kind == "oracle" else _configured(x)


SK_SHOW = {"oracle": "oracle", "configured": "configured", "any": "every scale"}


def _n_cell(st):
    return "-" if not st or st.get("n") is None else _count(st.get("n"))


def render_compare(exps, dts, sources):
    """exps: [(name, metrics)], the first is this experiment. sources: {name: description}.
    The SLAM tables only when this experiment has runs; the mask table when any experiment has
    a mask comparison."""
    me = exps[0][1]
    L = ["## Comparison with other experiments", ""]
    for name, _ in exps[1:]:
        L.append(f"- {name}: {sources.get(name, '')}")
    only = {name: [r for r in (m or {}).get("runs", {}) if r not in me["runs"]] for name, m in exps[1:]}
    for name, rr in only.items():
        if rr:
            L.append(f"- runs only in {name} (not shown): {', '.join(rr)}")
    if me["runs"]:
        L += ["", "Rows: what this experiment has. \"configured\" = each experiment's own scale method "
              "(labels in the scale table); \"-\" = not available.", ""]
        L += _compare_slam(exps, dts)
    else:
        L += ["", "This experiment has no SLAM runs: the SLAM tables are left out. \"-\" = not available.", ""]
    return L + _compare_masks(exps)


def _compare_slam(exps, dts):
    """The SLAM tables of render_compare (rows: this experiment's runs)."""
    me = exps[0][1]
    runs = list(me["runs"])
    slam_runs = [r for r in runs if r != "static"]
    L = []

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
            return [_n_cell(st) if g == "n" else _s(st, g) for g in groups]
        return cell

    hg = ["n", "median", "p95"]                         # n = frame pairs
    L += _ctable("Head rotation error [deg], n = frame pairs", ["run", "dt [s]"], hg,
                 [(r, d) for r in runs for d in dts], exps, head("rot_deg", None, hg))
    L += _ctable("Head translation error [mm], n = frame pairs", ["run", "scale", "dt [s]"], hg,
                 [(r, sk, d) for r in slam_runs for sk in ("oracle", "configured") for d in dts
                  if sk == "oracle" or _configured(me["runs"][r])], exps, head("trans_mm", True, hg))

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

    def labs_of(r, sk, what="labels"):
        return [((_run(m, r) or {}).get(what) or {}).get(_scale_of(m, r, sk) or "") for _, m in exps]

    def both_free(r, check, what):
        """This experiment has both scales, and in every experiment that has both the
        numbers `check` compares are the same for the two (shown once, scale 'every scale')."""
        pairs = list(zip(labs_of(r, "oracle", what), labs_of(r, "configured", what)))
        if not (pairs[0][0] and pairs[0][1]) or _scale_of(me, r, "configured") is None:
            return False
        return all(check([a, b]) for a, b in pairs if a and b)

    lab_keys = {"pos_mm": [], "rot_deg": []}
    lab_free = False
    for r in slam_runs:
        free = both_free(r, _labels_scale_free, "labels")
        lab_free |= free
        for key in lab_keys:
            for sk in (("any",) if key == "rot_deg" and free else ("oracle", "configured")):
                labs = labs_of(r, sk)
                if labs[0]:                              # rows this experiment has
                    lab_keys[key] += [(r, sk, "anchors")] + [(r, sk, j) for j in _steps(labs)]
    if lab_keys["pos_mm"]:
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
                return [(_n_cell(b) if g == "n" else _f(b.get(f"{key}_{g}"), fmt)) if b else "-" for g in groups]
            return cell

        def show(k):
            return (k[0], SK_SHOW[k[1]], k[2] if k[2] == "anchors" else _step_dt(k[2]))
        lg = ["n", "median", "p90"]                     # n = anchors counting the step
        for key, title in (("pos_mm", "Tool label position error tool_t->tool_t+dt [mm], n = anchors counting the step"),
                           ("rot_deg", "Tool label rotation error [deg], n = anchors counting the step"
                            + (f" {SCALE_FREE}" if lab_free else ""))):
            L += _ctable(title, ["run", "scale", "dt"], lg, lab_keys[key], exps, lab(key, lg), show)

        ch_keys, ch_free = [], False
        steps_any = any(_finite(v.get("steps_median")) for _, m in exps for x in ((m or {}).get("runs") or {}).values()
                        for c in (x.get("chunk") or {}).values() for v in c.values())
        for r in slam_runs:
            sks = [sk for sk in ("oracle", "configured") if labs_of(r, sk)[0]]
            if not sks:
                continue
            hs = _chunk_hs(c for sk in sks for c in labs_of(r, sk, "chunk")) or ["-"]
            cnt = ["any"] if both_free(r, lambda cs: _same_fields(cs, CHUNK_COUNTS), "chunk") else sks
            rot = ["any"] if both_free(r, lambda cs: _same_fields(cs, CHUNK_ROT), "chunk") else sks
            ch_free |= rot == ["any"]
            for q, ss in (("anchors", cnt), ("steps", cnt if steps_any else []), ("pos", sks), ("rot", rot)):
                ch_keys += [(r, sk, q, h) for sk in ss for h in hs]

        def ch_cell(m, k):
            c = ((_run(m, k[0]) or {}).get("chunk") or {}).get(_scale_of(m, k[0], k[1]) or "") or {}
            v = c.get(k[3])
            if not v:
                return ["-"]
            if k[2] in ("anchors", "steps"):
                return [_count(v.get("anchors" if k[2] == "anchors" else "steps_median"))]
            key, fmt = ("pos_mm", ".1f") if k[2] == "pos" else ("rot_deg", ".2f")
            return [f"{_f(v.get(key + '_mean'), fmt)} / {_f(v.get(key + '_median'), fmt)}"]
        q_show = {"anchors": "anchors", "steps": "counted steps per anchor, median",
                  "pos": "pos mm, mean / median", "rot": "rot deg, mean / median"}
        L += _ctable("Chunk-length label error over steps 1..H, per anchor the mean over its counted steps, "
                     "then mean / median over anchors" + (f" {SCALE_FREE}" if ch_free else ""),
                     ["run", "scale", "quantity", "H [steps of 1/15 s]"], [""], ch_keys, exps, ch_cell,
                     lambda k: (k[0], SK_SHOW[k[1]], q_show[k[2]],
                                k[3] if k[3] == "-" else f"{k[3]} ({int(k[3]) / LABEL_FPS:.2f} s)"))

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
        L += _ctable("Ground-truth noise floor", ["pairs", "dt [s]"], ["n", "rot deg med / p95", "trans mm med / p95"],
                     gkeys, exps, g_cell)
    return L


MASK_CMP_QS = (("pair", "reference / candidate"), ("dilate", "dilate [px]"), ("size", "segments / frames"),
               ("iou", "IoU median / p10"), ("recall", "recall median / p10"),
               ("precision", "precision median / p10"),
               ("extra_area", "extra area (candidate only) median / p90 [% of frame]"),
               ("missed_area", "missed area (reference only) median / p90 [% of frame]"),
               ("cells_iou", "DROID-cell IoU median / p10"), ("area", "mean area reference / candidate [% of frame]"),
               ("low", "segments with IoU median < 0.8"), ("worst", "worst segments (IoU median)"))


def _compare_masks(exps):
    """Side-by-side mask comparison table: rows = every comparison (<cand>_vs_<ref>) of any
    experiment, this experiment's first; per-part areas after the pooled stats."""
    names = []
    for _, m in exps:
        for n in (m or {}).get("masks") or {}:
            if n not in names:
                names.append(n)
    if not names:
        return []
    parts = {n: [] for n in names}
    for _, m in exps:
        for n, b in ((m or {}).get("masks") or {}).items():
            parts[n] += [p for p in _parts_of(b) if p not in parts[n]]
    keys = []
    for n in names:
        qs = [q for q, _ in MASK_CMP_QS]
        keys += [(n, q) for q in qs[:-2]] + [(n, ("part", p)) for p in parts[n]] + [(n, q) for q in qs[-2:]]
    label = dict(MASK_CMP_QS)

    def cell(m, k):
        b = ((m or {}).get("masks") or {}).get(k[0])
        if not b:
            return ["-"]
        q = k[1]
        if isinstance(q, tuple):
            v = (b.get("part_area") or {}).get(q[1])
            return [_pct(v, ".2f")]
        if q in ("iou", "recall", "precision", "cells_iou"):
            st = b.get(q) or {}
            return [f"{_mstat(st, 'median', 'share')} / {_mstat(st, 'p10', 'share')}"]
        if q in ("extra_area", "missed_area"):
            st = b.get(q) or {}
            return [f"{_mstat(st, 'median', 'area')} / {_mstat(st, 'p90', 'area')}"]
        low = list(b.get(MASK_IOU_LOW) or [])
        return [{"pair": f"{b.get('reference')} / {b.get('candidate')}", "dilate": _deg(b.get("dilate_px")),
                 "size": f"{b.get('n_segments')} / {_count(b.get('frames'))}",
                 "area": f"{_pct(b.get('area_ref'), '.2f')} / {_pct(b.get('area_cand'), '.2f')}",
                 "low": f"{len(low)}: {', '.join(low)}" if low else "0",
                 "worst": _worst_list(b.get("worst_segments"))}[q]]

    def show(k):
        q = k[1]
        return (k[0], f"part area: {q[1]} [% of frame]" if isinstance(q, tuple) else label[q])
    tab = _ctable("Mask comparison (per frame, pooled over every frame of every segment)", ["comparison", "quantity"],
                  [""], keys, exps, cell, show)
    tab[1:1] = ["", "Rows: the mask comparisons of every experiment (<candidate>_vs_<reference>); details in each "
                "experiment's report.md and masks_*.md."]
    return tab


# ====================================================================== reproducibility
def headline_items(m, dts):
    """Headline numbers of a canonical metrics dict: [(run, row, col, value, kind)], kind in
    deg/mm/frac/count (for formatting). Rows group the columns of one quantity (dts, steps, H)."""
    items = []
    for run, x in m["runs"].items():
        if run != "static":
            items += [(run,) + it for it in _run_headline(run, x, dts)]
    return items


def _run_headline(run, x, dts):
    """headline_items() of one run: [(row, col, value, kind)]."""
    out = []
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
    a = {(r, c): (run, v, k) for run, r, c, v, k in headline_items(main, dts)}
    out = []
    for run, r, c, v, k in headline_items(rep, dts):
        m0 = a.get((r, c), (run, None, k))[1]
        out.append({"run": run, "row": r, "col": c, "kind": k, "main": _num(m0), "repro": _num(v),
                    "delta": _num(v) - _num(m0) if _finite(v) and _finite(m0) else None})
    seen = {(d["row"], d["col"]) for d in out}
    for (r, c), (run, v, k) in a.items():
        if (r, c) not in seen:
            out.append({"run": run, "row": r, "col": c, "kind": k, "main": _num(v), "repro": None, "delta": None})
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


def rot_angle_deg_stable(R):
    """Rotation angle [deg] of (..., 3, 3) matrices via atan2(sin, cos): accurate near 0, where
    the arccos of the trace (geometry.rot_angle_deg) has a floor of ~0.02 deg for poses stored
    in float32 (a trajectory compared with itself reads 0.019 deg)."""
    s = 0.5 * np.linalg.norm(np.stack([R[..., 2, 1] - R[..., 1, 2], R[..., 0, 2] - R[..., 2, 0],
                                       R[..., 1, 0] - R[..., 0, 1]], -1), axis=-1)
    c = 0.5 * (np.trace(R, axis1=-2, axis2=-1) - 1)
    return np.degrees(np.arctan2(s, c))


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
        rot[dt_key(d)] = rot_angle_deg_stable(np.swapaxes(rm[:, :3, :3], 1, 2) @ rr[:, :3, :3])
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
        arrays = [k for k in om if k != "meta" and isinstance(om[k], np.ndarray)]
        ident = all(k in orp and np.array_equal(om[k], orp[k], equal_nan=om[k].dtype.kind == "f")
                    for k in arrays) and set(arrays) == {k for k in orp if k != "meta" and isinstance(orp[k], np.ndarray)}
        e = {"bit_identical": bool(ident), "n_frames": c["n_frames"], "tracked_main": c["tracked_main"], "tracked_repro": c["tracked_repro"],
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
            "segments_bit_identical": int(sum(v.get("bit_identical", False) for v in ok)),
            "segments_missing": sorted(s for s, v in per.items() if "error" in v),
            "rot_diff_deg_pooled": pooled_st, "rot_diff_worst_segment_median": worst_seg,
            "sim3_rms_over_extent": {"n": len(roe), "median": float(np.median(roe)) if roe else None,
                                     "max": float(max(roe)) if roe else None, "worst": worst_sim3},
            "keyframes": {"segments_differing": int(sum(d != 0 for d in kfd)), "segments": len(kfd),
                          "max_abs_diff": int(max(abs(d) for d in kfd)) if kfd else None,
                          "mean_diff": float(np.mean(kfd)) if kfd else None},
            "per_segment": per}


def recomputed_runs(node_ids, runs):
    """The runs (of `runs`) whose results depend on recomputed producer nodes (the repro node
    and its descendants, spec.descendants): slam.<run> and depth.<name>@<run> name their run;
    masks.* only matter through the slam nodes depending on them (descendants, so listed too);
    any other node (preprocess, tiles) is shared by every run."""
    out = set()
    for nid in node_ids:
        step, _, name = nid.partition(".")
        if step == "slam":
            out.add(name)
        elif "@" in nid:
            out.add(nid.rsplit("@", 1)[1])
        elif step != "masks":
            return list(runs)
    return [r for r in runs if r in out]


def _run_of(d):
    """The run of a repro metric delta (older repro.json: the row's first word)."""
    return d.get("run") or d["row"].split(" ", 1)[0]


def repro_line(rep, v):
    """One sentence per repro variant: bit-identical SLAM outputs and the metric deltas, e.g.
    'slam.E3 recomputed (repro1): outputs bit-identical on 30/30 segments; every metric delta 0'."""
    x = rep["variants"][v]
    T = x.get("trajectories") or {}
    parts = []
    for nid, t in T.items():
        n, ok = t.get("segments_compared", 0), t.get("segments_bit_identical")
        miss = len(t.get("segments_missing") or [])
        tot = n + miss
        if not n:
            s = "outputs not compared"
        elif ok is None:
            s = f"outputs compared on {n}/{tot} segments (bit identity not recorded)"
        elif ok == n:
            s = f"outputs bit-identical on {ok}/{tot} segments"
        else:
            s = f"outputs differ on {n - ok}/{tot} segments (bit-identical on {ok})"
        if miss:
            s += f", {miss} segment(s) missing"
        parts.append(s if list(T) == [rep["node"]] else f"{nid} {s}")
    if not T:
        parts.append("no SLAM output recomputed")
    ms = x.get("metrics") or []
    parts.append(_delta_summary(ms))
    one_sided = [d for d in ms if _finite(d.get("main")) != _finite(d.get("repro"))]
    if one_sided:
        parts.append(f"{len(one_sided)} metrics present in only one variant")
    sc = [sd.get("abs_max") for sd in (x.get("scale_s") or {}).values() if sd and _finite(sd.get("abs_max"))]
    if any(sc):
        parts.append(f"per-segment scale s differs by up to {_pct(max(sc), '.2f')}")
    return f"{rep['node']} recomputed ({v}): " + "; ".join(parts)


def build_repro(job, main_metrics, dts):
    rp = job.spec.get("repro")
    if not rp:
        return None
    variants = job.spec["variants"]
    main_dir = Path(variants["main"])
    work = Path(job.spec["work"])
    view_dirs = [main_dir.parent / "view" / job.session / "segments"]
    runs = [r for r in main_metrics["runs"] if r != "static"]
    out = {"node": rp["node"], "dt_show": dts, "segments": len(job.segments),
           "base_keys": rp.get("base_keys", {}),
           "runs_recomputed": recomputed_runs(list(rp.get("base_keys") or {}) or [rp["node"]], runs),
           "variants": {}}
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


_ROT_ROW = re.compile(r"^(?P<pre>.+ rot[^,]*), (?P<scale>.+) scale \[deg\]$")


def _scale_free_rows(rows_order, groups, vs):
    """Tolerance rows of rotation (label / chunk) that are the same for every scale, main value
    and deltas: ({kept row: new label}, {dropped rows})."""
    by_pre = {}
    for row in rows_order:
        mt = _ROT_ROW.match(row)
        if mt:
            by_pre.setdefault(mt.group("pre"), []).append(row)
    relabel, drop = {}, set()
    for pre, rows in by_pre.items():
        g0 = groups[rows[0]]
        if len(rows) > 1 and all(
                set(groups[r]) == set(g0) and all(
                    _same(groups[r][c]["main"], g0[c]["main"])
                    and all(_same(groups[r][c]["deltas"].get(v), g0[c]["deltas"].get(v)) for v in vs) for c in g0)
                for r in rows[1:]):
            relabel[rows[0]] = f"{pre}, every scale (scale-free) [deg]"
            drop |= set(rows[1:])
    return relabel, drop


def _delta_summary(ds):
    """'every metric delta 0', or how many are nonzero and the largest per unit."""
    fin = [d for d in ds if _finite(d.get("delta"))]
    nz = [d for d in fin if d["delta"] != 0]
    if not nz:
        return "every metric delta 0" if fin else "no metric compared"
    worst = {}
    for d in nz:                                         # largest per unit (deg, mm, frac, count)
        if d["kind"] not in worst or abs(d["delta"]) > abs(worst[d["kind"]]["delta"]):
            worst[d["kind"]] = d
    return f"{len(nz)}/{len(fin)} metric deltas nonzero, largest " + ", ".join(
        f"{_fmt_kind(d['delta'], d['kind'], True)} ({d['row']}{' ' + d['col'] if d['col'] else ''})"
        for d in worst.values())


def render_repro(rep, exp):
    vs = list(rep["variants"])
    node = rep["node"]
    L = [f"# Reproducibility: {exp}, {node} recomputed {len(vs)} time(s)", ""]
    L += [f"- {repro_line(rep, v)}" for v in vs] + [""]
    L += [f"Same configuration; {node} recomputed under a cache tag ({', '.join(vs)}) and every "
          "step downstream of it rerun. Differences vs the main run. Rotation difference = "
          "angle(R_rel_main^T R_rel_repro) of cam_t->cam_t+dt over all frame pairs tracked in both, "
          "computed with rot_angle_deg_stable (atan2 of the sine and cosine parts: exactly 0 for identical "
          "poses, where the arccos of the trace reads up to ~0.02 deg for float32 poses); "
          "Sim3 = repro camera centres aligned to main by a similarity, RMS residual / largest centre "
          "distance of the main trajectory.", ""]
    # ---------------- runs: only those depending on the recomputed node are listed
    rec = rep.get("runs_recomputed")
    all_runs = []
    for v in vs:
        for d in rep["variants"][v]["metrics"]:
            if _run_of(d) not in all_runs:
                all_runs.append(_run_of(d))
    for v in vs:
        for run in rep["variants"][v]["scale_s"]:
            if run not in all_runs:
                all_runs.append(run)
    shown = all_runs if rec is None else [r for r in all_runs if r in rec]
    skipped = [r for r in all_runs if r not in shown]
    if rec is not None:
        L += [f"Runs depending on {node} (recomputed, listed below): {', '.join(rec) or 'none'}."]
        if skipped:
            ds = [d for v in vs for d in rep["variants"][v]["metrics"] if _run_of(d) in skipped]
            L += [f"Not recomputed: {', '.join(skipped)} (independent of {node}: the same cache entries as main, "
                  f"only the analysis was rerun); left out of the table ({_delta_summary(ds)}, see repro.json)."]
        L += [""]
    # ---------------- tolerance table: one row per quantity, columns joined over dt / step / H
    rows_order, groups = [], {}
    for v in vs:
        for d in rep["variants"][v]["metrics"]:
            if _run_of(d) not in shown:
                continue
            if d["row"] not in groups:
                rows_order.append(d["row"])
                groups[d["row"]] = {}
            groups[d["row"]].setdefault(d["col"], {"kind": d["kind"], "main": d["main"], "deltas": {}})
            groups[d["row"]][d["col"]]["deltas"][v] = d["delta"]
    relabel, drop = _scale_free_rows(rows_order, groups, vs)
    trows = []
    for row in rows_order:
        if row in drop:
            continue
        cols = groups[row]
        names = [c for c in cols if c]
        label = relabel.get(row, row) + (f" ({' / '.join(names)})" if names else "")
        main = " / ".join(_fmt_kind(c["main"], c["kind"]) for c in cols.values())
        per_v = [" / ".join(_fmt_kind(c["deltas"].get(v), c["kind"], True) for c in cols.values()) for v in vs]
        mx = " / ".join(_fmt_kind(max((abs(c["deltas"][v]) for v in vs if _finite(c["deltas"].get(v))),
                                      default=None), c["kind"], True, False) for c in cols.values())
        trows.append([label, main] + per_v + [mx])
    s_runs = sorted({run for v in vs for run in rep["variants"][v]["scale_s"] if run in shown})
    for run in s_runs:
        cells = []
        for v in vs:
            sd = rep["variants"][v]["scale_s"].get(run)
            cells.append(f"{_pct(sd.get('abs_median'), '.2f')} / {_pct(sd.get('abs_max'), '.2f')}"
                         + (f" ({sd['worst']})" if sd.get("worst") and sd.get("abs_max") else "") if sd else "-")
        mx = _max_finite((rep["variants"][v]["scale_s"].get(run) or {}).get("abs_max") for v in vs)
        trows.append([f"{run} per-segment scale \\|s_repro/s_main - 1\\| median / max", "-"] + cells + [_pct(mx, ".2f")])
    nodes = sorted({n for v in vs for n in rep["variants"][v]["trajectories"]})
    dts = [dt_key(d) for d in rep["dt_show"]]
    bit_rows = []
    for nid in nodes:
        T = {v: rep["variants"][v]["trajectories"].get(nid) for v in vs}
        cells = [f"{t.get('segments_bit_identical', '?')}/{t['segments_compared']}" if t else "-" for t in T.values()]
        bit_rows.append([f"{nid} outputs bit-identical (all traj.npz arrays), segments", "-"] + cells + [""])
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
    L += _table(["quantity", "main"] + [f"{v} - main" for v in vs] + ["max \\|diff\\|"], bit_rows + trows)
    # ---------------- per-segment trajectory details
    for v in vs:
        for nid, t in rep["variants"][v]["trajectories"].items():
            L += [f"## {v}: {nid} per segment", "",
                  f"Keys: main {t['key_main']}, repro {t['key_repro']}. Rotation difference median / p95 [deg].", ""]
            rows = []
            for seg, e in t["per_segment"].items():
                if "error" in e:
                    rows.append([seg, "-"] + ["-"] * len(dts) + [e["error"], "-", "-"])
                    continue
                bit = e.get("bit_identical")
                rows.append([seg, "-" if bit is None else ("yes" if bit else "no")]
                            + [f"{_s(e['rot_diff_deg'].get(d), 'median', '.3f')} / {_s(e['rot_diff_deg'].get(d), 'p95', '.3f')}"
                               for d in dts]
                            + [_pct(e["sim3"]["rms_over_extent"], ".2f"),
                               f"{e['tracked_main']} / {e['tracked_repro']} of {e['n_frames']}",
                               f"{e['keyframes']['main']} / {e['keyframes']['repro']}"])
            L += _table(["segment", "bit-identical"] + [f"{d} s" for d in dts]
                        + ["Sim3 RMS / extent", "tracked main / repro", "keyframes main / repro"], rows)
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
    if not metrics["n_segments"]:                       # nothing in the results names its segments
        metrics["n_segments"] = len(job.segments)
    add_chunk_steps(metrics, main_dir, main_dir.parent / "view", job.session, job.log)
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
    work = job.spec.get("work")
    overlays = {name: overlay_info(main_dir, name, work) for name in metrics["masks"]}
    L = [f"# {exp}: report (variant main)", ""]
    if metrics["runs"]:
        L += [f"{metrics['n_segments']} segments. Runs: {', '.join(r for r in metrics['runs'] if r != 'static')} "
              "(static = head motion identity, no SLAM). Ground truth: tile head poses; "
              "\"oracle (tiles)\" = per-segment scale fitted to the tile poses (evaluation only).", ""]
        L += render_main(metrics, dts, scale_files)
    else:
        what = ("mask comparison only: " + ", ".join(f"{b.get('candidate')} vs {b.get('reference')}"
                                                     for b in metrics["masks"].values())
                if metrics["masks"] else "no analysis results")
        L += [f"{metrics['n_segments']} segments. No SLAM runs (no head-motion evaluation); {what}.", ""]
    L += render_masks(metrics, overlays, work)
    if rep:
        L += ["## Reproducibility", "",
              f"{rep['node']} recomputed {len(rep['variants'])} time(s), every step downstream of it rerun; "
              "details in `repro.md` (tolerance table) and `repro.json`.", ""]
        L += [f"- {repro_line(rep, v)}" for v in rep["variants"]] + [""]
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
