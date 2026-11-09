"""Report step (slam.pipeline.impl_report): canonical metrics, legacy adapter, comparison
tables, reproducibility check (python -m slam.tests.test_report).

test_legacy_* read experiments/exp000_legacy/results (in the repository); everything else is
synthetic and written to temporary directories.
"""
import json
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np

from slam import config as C
from slam import geometry as G
from slam import labels as Lb
from slam.evaluate import stats
from slam.pipeline import impl_report as R
from slam.pipeline.worker import Job

REPO = Path(__file__).resolve().parents[2]
LEGACY = REPO / "experiments" / "exp000_legacy" / "results"
DTS = [0.08, 0.25, 0.5, 1.0, 2.0, 4.0, 6.67]
DT_SHOW = [0.08, 0.5, 1.0, 2.0, 6.67]
STEPS = [1, 2, 4, 8, 15, 30, 60, 100]
HS = [15, 30, 50, 100]


# ---------------------------------------------------------------------- helpers
def make_job(out_dir, variants, compare=(), repro=None, work=None, segments=("ep00",), name="expT",
             experiments_root=None, scratch=None):
    spec = {"params": {"compare": list(compare), "dt_show": DT_SHOW},
            "node": {"id": "report", "step": "report", "name": "report", "impl": "default", "key": None},
            "data": {"session": "yam_glove7"}, "segments": list(segments), "out_dir": str(out_dir),
            "scratch": str(scratch or Path(out_dir) / "_scratch"), "experiment": {"name": name},
            "variants": {k: str(v) for k, v in variants.items()}, "repro": repro,
            "experiments_root": str(experiments_root or REPO / "experiments"), "work": str(work or out_dir)}
    return Job(spec)


def _err_summary(errs):
    e = np.array([x for x in errs if x is not None])
    if not len(e):
        return {"n_compared": 0, "abs_err_median": None, "abs_err_p90": None, "bias_median": None}
    return {"n_compared": int(len(e)), "abs_err_median": float(np.median(np.abs(e))),
            "abs_err_p90": float(np.percentile(np.abs(e), 90)), "bias_median": float(np.median(e))}


def contract_scale(rows_in, run, primary="B", checks=("A",), threshold=0.10):
    """scale_<run>.json of the analysis contract from simple rows {segment, oracle_s, s_<m>}:
    s = the primary's, checks flag |s_check/s - 1| > threshold."""
    rows = []
    for r in rows_in:
        so, sp = r.get("oracle_s"), r.get(f"s_{primary}")
        rel = (lambda s: float(s / so - 1) if s is not None and so is not None else None)
        ch, by = {}, []
        for c in checks:
            sc = r.get(f"s_{c}")
            diff = float(sc / sp - 1) if sc is not None and sp is not None else None
            ch[c] = {"s": sc, "ok": sc is not None, "diff": diff, "err": rel(sc)}
            if diff is not None and abs(diff) > threshold:
                by.append(c)
        rows.append({"segment": r["segment"], "s": sp, "ok": sp is not None, "oracle_s": so, "err": rel(sp),
                     "primary": {"s": sp, "ok": sp is not None}, "checks": ch, "flagged": bool(by), "flagged_by": by})
    flagged = [r["segment"] for r in rows if r["flagged"]]
    summ = {"segments": len(rows), "segments_ok": sum(r["ok"] for r in rows),
            **_err_summary([r["err"] for r in rows]), "flagged": flagged,
            "both": [r["segment"] for r in rows if r["ok"] and all(v["ok"] for v in r["checks"].values())],
            "without_flagged": _err_summary([r["err"] for r in rows if not r["flagged"]]),
            "methods": {primary: {"segments_ok": sum(r["ok"] for r in rows), **_err_summary([r["err"] for r in rows])}}}
    for c in checks:
        summ["methods"][c] = {"segments_ok": sum(r["checks"][c]["ok"] for r in rows),
                              **_err_summary([r["checks"][c]["err"] for r in rows])}
    return {"run": run, "label": R.scale_label(primary, list(checks)), "primary": primary, "checks": list(checks),
            "flag_threshold": threshold, "methods": {}, "rows": rows, "summary": summ}


def fake_summary(rng, runs, segs, shift=0.0):
    """slam.evaluate summary.json; the first segment has no scale (NaN, as slam.evaluate writes it)."""
    keys = ("rot_err_deg", "trans_err_mm", "label_pos_err_mm", "label_rot_err_deg", "gt_rot_deg", "gt_trans_mm",
            "rot_err_deg_same_tiles", "trans_err_mm_same_tiles")
    S = {"dts": DTS, "runs": {}, "segments": {}}
    for i, seg in enumerate(segs):
        S["segments"][seg] = {"n_frames": 100, "in_ep": 60, "in_ep_strict": 40}
        for r in runs:
            if r != "static":
                S["segments"][seg][r] = {"scale": float("nan") if i == 0 else 0.5, "align_res_mm": 4.0,
                                         "n_keyframes": 10 + i, "runtime_s": 30.0 + i, "valid_frac": 0.8}
    for r in runs:
        by = {str(d): {k: stats(rng.gamma(2.0, size=40) + shift) for k in keys} for d in DTS}
        S["runs"][r] = {"by_dt": by, "by_speed_dt0.5": {}, "per_segment_dt1": {}, "track_fail_frac": 0.01}
    return S


def fake_labels(rng, ref, chunk=True):
    lab = {"ref": ref, "anchors": 100, "excluded": [], "kept_episodes": 3,
           "by_step": {str(j): {"dt_s": j / 15, "n": 90, "pos_mm_median": float(rng.uniform(1, 9)),
                                "pos_mm_p90": 20.0, "rot_deg_median": float(rng.uniform(0.1, 1)),
                                "rot_deg_p90": 2.0} for j in STEPS}}
    if chunk:
        lab["chunk"] = {str(h): {"anchors": 79 if h == 15 else 80, "pos_mm_mean": float(rng.uniform(2, 8)), "pos_mm_median": 3.0,
                                 "pos_mm_p90": 9.0, "rot_deg_mean": float(rng.uniform(0.2, 0.8)),
                                 "rot_deg_median": 0.4, "rot_deg_p90": 1.0, "pooled_pos_mm_mean": 4.0,
                                 "pooled_rot_deg_mean": 0.5} for h in HS}
    return lab


ROT_LAB, ROT_CHUNK = ("rot_deg_median", "rot_deg_p90"), ("rot_deg_mean", "rot_deg_median", "rot_deg_p90",
                                                         "pooled_rot_deg_mean")


def make_results(d, seed=0, shift=0.0, s_factor=None, fail_deg=2.0, rot_scale_free=True):
    """Synthetic analysis results dir (contract layout): runs E1 (no scale) and E3 (B+Acheck).
    rot_scale_free: the scaled labels have the oracle's rotation numbers (as real ones do)."""
    rng = np.random.default_rng(seed)
    d = Path(d)
    segs = ["ep00", "ep01", "ep02", "ep03"]
    (d / "eval_oracle").mkdir(parents=True)
    (d / "eval_B+Acheck").mkdir()
    S = fake_summary(rng, ["static", "E1", "E3"], segs, shift)
    json.dump(S, open(d / "eval_oracle" / "summary.json", "w"))
    (d / "eval_oracle" / "summary.md").write_text("oracle\n")
    (d / "eval_oracle" / "pairs.csv").write_text("run,segment\n")
    json.dump(fake_summary(rng, ["static", "E3"], segs, shift), open(d / "eval_B+Acheck" / "summary.json", "w"))
    (d / "eval_B+Acheck" / "summary.md").write_text("scaled\n")
    (d / "eval_B+Acheck" / "pairs.csv").write_text("run,segment\n")
    s_factor = s_factor or {}
    rows = [{"segment": "ep00", "oracle_s": 0.50, "s_B": 0.52 * s_factor.get("ep00", 1), "s_A": None},
            {"segment": "ep01", "oracle_s": 0.60, "s_B": 0.50 * s_factor.get("ep01", 1), "s_A": 0.60},
            {"segment": "ep02", "oracle_s": None, "s_B": 0.40 * s_factor.get("ep02", 1), "s_A": None},
            {"segment": "ep03", "oracle_s": 0.70, "s_B": 0.66 * s_factor.get("ep03", 1), "s_A": 0.65}]
    json.dump(contract_scale(rows, "E3"), open(d / "scale_E3.json", "w"))
    (d / "scale_E3.md").write_text("# scale\n")
    lo, ls = fake_labels(rng, "E3"), fake_labels(rng, "E3@B+Acheck")
    if rot_scale_free:
        for j, b in ls["by_step"].items():
            b.update({k: lo["by_step"][j][k] for k in ROT_LAB})
        for h, c in ls["chunk"].items():
            c.update({k: lo["chunk"][h][k] for k in ROT_CHUNK})
    json.dump(lo, open(d / "labels_E3.json", "w"))
    json.dump(ls, open(d / "labels_E3@B+Acheck.json", "w"))
    json.dump({"frames_with_all_tiles": 40, "by_dt": {"0.08": {"n": 9, "rot_deg_median": 0.1, "rot_deg_p95": 0.4,
                                                               "trans_mm_median": 1.9, "trans_mm_p95": 5.7}},
               "tile_switch": {"n": 12, "rot_deg_median": 0.39, "rot_deg_p95": 1.2, "trans_mm_median": 7.5,
                               "trans_mm_p95": 27.6}}, open(d / "gt_noise.json", "w"))
    slam = {"keyframes_per_segment": {s: 10 + i for i, s in enumerate(segs)}, "runtime_s_per_segment": 31.5,
            "valid_frac": [0.8, 0.8, 0.8, 0.8], "tracked_frac": 1.0}
    json.dump({"runs": {"E1": {"scale_label": None, "scale": None, "labels": {"oracle": None, "scaled": None},
                               "eval": {"oracle": "eval_oracle", "scaled": None}, "slam": slam},
                        "E3": {"scale_label": "B+Acheck", "scale": "scale_E3.json",
                               "labels": {"oracle": "labels_E3.json", "scaled": "labels_E3@B+Acheck.json"},
                               "eval": {"oracle": "eval_oracle", "scaled": "eval_B+Acheck"}, "slam": slam}},
               "gt_noise": "gt_noise.json", "segments": segs, "evaluate": {"fail_deg": fail_deg, "dts": DTS}},
              open(d / "analysis.json", "w"))
    return d


def legacy_to_contract(src, dst, label="B+Acheck"):
    """Arrange exp000_legacy's files as an analysis results dir of the contract (a fake 'main'
    variant): eval_oracle/, eval_<label>/, scale_<run>.json (contract schema, recomputed from
    the legacy rows), labels_<run>[@<label>].json, gt_noise.json, analysis.json."""
    src, dst = Path(src), Path(dst)
    (dst / "eval_oracle").mkdir(parents=True)
    (dst / f"eval_{label}").mkdir()
    for a, b in (("eval", "eval_oracle"), (f"{label}_eval", f"eval_{label}")):
        for f in ("summary.json", "summary.md"):
            shutil.copy(src / a / f, dst / b / f)
    shutil.copy(src / "eval" / "gt_noise.json", dst / "gt_noise.json")
    S = json.load(open(src / "eval" / "summary.json"))
    idx = {"runs": {}, "gt_noise": "gt_noise.json", "segments": sorted(S["segments"]),
           "evaluate": {"fail_deg": 2.0, "dts": S["dts"]}}            # what the legacy evaluation used
    fin = (lambda v: v if v is not None and np.isfinite(v) else None)
    for run in [r for r in S["runs"] if r != "static"]:
        cc = json.load(open(src / "eval" / f"scale_{run}_{label}.json"))
        rows = [{"segment": r["segment"], "oracle_s": fin(r["oracle"]), "s_B": fin(r["s_B"]), "s_A": fin(r["s_A"])}
                for r in cc["rows"]]
        sc = contract_scale(rows, run, threshold=cc["rows"][0]["threshold"])
        assert sc["summary"]["flagged"] == cc["flagged"]
        json.dump(sc, open(dst / f"scale_{run}.json", "w"))
        shutil.copy(src / "eval" / f"scale_{run}_{label}.md", dst / f"scale_{run}.md")
        shutil.copy(src / "eval" / f"labels_{run}.json", dst / f"labels_{run}.json")
        shutil.copy(src / "eval" / f"labels_{run}@{label}.json", dst / f"labels_{run}@{label}.json")
        info = [v[run] for v in S["segments"].values() if run in v]
        idx["runs"][run] = {"scale_label": label, "scale": f"scale_{run}.json",
                            "labels": {"oracle": f"labels_{run}.json", "scaled": f"labels_{run}@{label}.json"},
                            "eval": {"oracle": "eval_oracle", "scaled": f"eval_{label}"},
                            "slam": {"keyframes_per_segment": {s: v[run]["n_keyframes"] for s, v in S["segments"].items()
                                                               if run in v},
                                     "runtime_s_per_segment": [i["runtime_s"] for i in info],
                                     "valid_frac": [i["valid_frac"] for i in info]}}
    json.dump(idx, open(dst / "analysis.json", "w"))
    return dst


MASK_SEGS = ["ep00", "ep01", "ep02", "ep03"]
MASK_PARTS = ["hand", "arm", "cable", "glove"]
MASK_QKEYS = ("iou", "recall", "precision", "extra_area", "missed_area", "cells_iou")


def mask_stat(x):
    """Mask stat of the mask_compare contract over the finite values (NaN entries when n = 0,
    as json.dump writes them)."""
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if not len(x):
        return {"n": 0, "median": float("nan"), "p10": float("nan"), "p90": float("nan"), "mean": float("nan")}
    return {"n": int(len(x)), "median": float(np.median(x)), "p10": float(np.percentile(x, 10)),
            "p90": float(np.percentile(x, 90)), "mean": float(np.mean(x))}


def make_mask_results(res, seed=0, cand="sam3", ref="sam2", dilate_px=8, parts=MASK_PARTS, per_seg=4,
                      empty_seg="ep02"):
    """mask_compare outputs (CONTRACT) of a variant results dir: masks_<cand>_vs_<ref>.json/.md in
    `res`, overlays in res/../overlays/<cand>_vs_<ref>/ (index.json + jpg stubs). Per-frame values
    are random; in `empty_seg` the candidate is empty in every frame (IoU 0, precision undefined:
    its precision stat has n 0 and NaN values, written as NaN literals)."""
    rng = np.random.default_rng(seed)
    res = Path(res)
    res.mkdir(parents=True, exist_ok=True)
    name = f"{cand}_vs_{ref}"
    segs, pooled = {}, {k: [] for k in MASK_QKEYS + ("area_ref", "area_cand")}
    pooled_parts = {p: [] for p in parts}
    for s_i, seg in enumerate(MASK_SEGS):
        n = 20 + 5 * s_i
        area_ref = rng.uniform(0.05, 0.2, n)
        if seg == empty_seg:
            v = {"iou": np.zeros(n), "recall": np.zeros(n), "precision": np.full(n, np.nan),
                 "extra_area": np.zeros(n), "missed_area": area_ref, "cells_iou": np.zeros(n)}
            area_cand, part = np.zeros(n), {p: np.zeros(n) for p in parts}
        else:
            iou = np.clip(rng.normal(0.9 - 0.1 * s_i, 0.05, n), 0, 1)
            v = {"iou": iou, "recall": np.clip(iou + 0.05, 0, 1), "precision": np.clip(iou + 0.02, 0, 1),
                 "extra_area": rng.uniform(0, 0.02, n), "missed_area": rng.uniform(0, 0.01, n),
                 "cells_iou": np.clip(iou + 0.03, 0, 1)}
            part = {p: rng.uniform(0, 0.05, n) for p in parts}
            area_cand = area_ref + v["extra_area"] - v["missed_area"]
        order = np.argsort(v["iou"], kind="stable")[:5]
        segs[seg] = {"frames": n, **{k: mask_stat(v[k]) for k in MASK_QKEYS},
                     "area_ref": float(area_ref.mean()), "area_cand": float(area_cand.mean()),
                     "part_area": {p: float(part[p].mean()) for p in parts},
                     "worst_frames": [[int(i), float(v["iou"][i])] for i in order]}
        for k in MASK_QKEYS:
            pooled[k] += list(v[k])
        pooled["area_ref"] += list(area_ref)
        pooled["area_cand"] += list(area_cand)
        for p in parts:
            pooled_parts[p] += list(part[p])
    med = {s: segs[s]["iou"]["median"] for s in MASK_SEGS}
    summ = {"frames": sum(x["frames"] for x in segs.values()), **{k: mask_stat(pooled[k]) for k in MASK_QKEYS},
            "area_ref": float(np.mean(pooled["area_ref"])), "area_cand": float(np.mean(pooled["area_cand"])),
            "part_area": {p: float(np.mean(pooled_parts[p])) for p in parts},
            "segments_iou_median_below_0.8": [s for s in MASK_SEGS if med[s] < 0.8],
            "worst_segments": [[s, med[s]] for s in sorted(MASK_SEGS, key=lambda s: med[s])[:5]]}
    mc = {"reference": ref, "candidate": cand, "dilate_px": dilate_px, "parts": list(parts), "segments": segs,
          "summary": summ}
    with open(res / f"masks_{name}.json", "w") as f:
        json.dump(mc, f, indent=1)                                  # NaN literals, as json.dump writes them
    (res / f"masks_{name}.md").write_text(f"# {name}\n")
    ov = res.parent / "overlays" / name
    ov.mkdir(parents=True, exist_ok=True)
    idx = []
    for seg in MASK_SEGS:
        n = segs[seg]["frames"]
        worst = [i for i, _ in segs[seg]["worst_frames"]]
        even = [i for i in np.linspace(0, n - 1, per_seg // 2).astype(int) if i not in worst[:per_seg // 2]]
        for kind, frames in (("even", even), ("worst", worst[:per_seg - len(even)])):
            for i in frames:
                f = f"{seg}_{i:06d}.jpg"
                (ov / f).write_bytes(b"\xff\xd8\xff\xd9")
                idx.append({"file": f, "segment": seg, "i": int(i), "iou": 0.5, "kind": kind})
    json.dump(idx, open(ov / "index.json", "w"))
    return mc


def md_section(md, heading_start):
    """Text of the first '## ' section whose heading starts with heading_start (no heading line)."""
    return next(b for b in md.split("\n## ")[1:] if b.startswith(heading_start)).split("\n", 1)[1].lstrip("\n")


def md_tables(text):
    """[(header, rows)] of every markdown table in a text."""
    out, cur = [], []
    for ln in text.splitlines() + [""]:
        if ln.startswith("|"):
            cur.append([c.strip() for c in ln.strip().strip("|").split(" | ")])
        elif cur:
            out.append((cur[0], cur[2:]))
            cur = []
    return out


def comparison_tables(md):
    """{title: (header, rows)} of the tables in the report's comparison section."""
    sec = md.split("## Comparison with other experiments", 1)[1]
    out = {}
    for block in sec.split("### ")[1:]:
        title, rest = block.split("\n", 1)
        lines = [ln for ln in rest.splitlines() if ln.startswith("|")]
        cells = [[c.strip() for c in ln.strip("|").split(" | ")] for ln in lines]
        out[title] = (cells[0], cells[2:])
    return out


def section_table(md, heading_start):
    """(header, rows, text after the table up to the next heading) of the first '## ' section
    whose heading starts with heading_start."""
    sec = next(b for b in md.split("\n## ")[1:] if b.startswith(heading_start))
    lines = sec.split("\n")
    tab = [ln for ln in lines if ln.startswith("|")]
    cells = [[c.strip() for c in ln.strip().strip("|").split(" | ")] for ln in tab]
    after = "\n".join(lines[max(i for i, ln in enumerate(lines) if ln.startswith("|")) + 1:])
    return cells[0], cells[2:], after


def strict_json(path):
    """json.load that refuses NaN / Infinity literals."""
    def bad(c):
        raise ValueError(f"non-strict JSON constant {c} in {path}")
    return json.loads(Path(path).read_text(), parse_constant=bad)


def random_traj(rng, n):
    rv = np.cumsum(rng.normal(scale=0.01, size=(n, 3)), 0)
    tv = np.cumsum(rng.normal(scale=0.005, size=(n, 3)), 0)
    return G.rt_to_T(rv, tv)


def sim3(T, s, Rg, tg):
    out = T.copy()
    out[:, :3, :3] = Rg @ T[:, :3, :3]
    out[:, :3, 3] = s * (Rg @ T[:, :3, 3].T).T + tg
    return out


# ---------------------------------------------------------------------- tests
def test_metrics_schema_synthetic():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        res = make_results(tmp / "main")
        out = tmp / "exp" / "results"
        r = R.run_report(make_job(out, {"main": res}))
        m = json.load(open(out / "metrics.json"))
        assert set(m) == {"experiment", "variant", "runs", "n_segments", "gt_noise", "evaluate", "masks"}
        assert m["experiment"] == "expT" and m["variant"] == "main" and m["n_segments"] == 4
        assert m["masks"] == {} and "Mask comparison" not in (out / "report.md").read_text()
        assert m["evaluate"] == {"fail_deg": 2.0, "dts": DTS}
        assert list(m["runs"]) == ["static", "E1", "E3"]
        S = json.load(open(res / "eval_oracle" / "summary.json"))
        Ss = json.load(open(res / "eval_B+Acheck" / "summary.json"))
        for run, x in m["runs"].items():
            assert set(x) == {"head", "track_fail_frac", "slam", "scale", "labels", "chunk"}
            h = x["head"]
            assert set(h) == {"rot_deg", "rot_deg_same_tiles", "trans_mm", "label_pos_mm_pairs", "label_rot_deg_pairs"}
            assert list(h["rot_deg"]) == [str(d) for d in DTS]
            assert h["rot_deg"]["1.0"] == S["runs"][run]["by_dt"]["1.0"]["rot_err_deg"]
            assert set(h["rot_deg"]["1.0"]) == set(R.STAT_KEYS)
            assert h["trans_mm"]["oracle"]["0.08"] == S["runs"][run]["by_dt"]["0.08"]["trans_err_mm"]
        e3 = m["runs"]["E3"]
        assert set(e3["head"]["trans_mm"]) == {"oracle", "B+Acheck"}
        assert e3["head"]["trans_mm"]["B+Acheck"]["2.0"] == Ss["runs"]["E3"]["by_dt"]["2.0"]["trans_err_mm"]
        assert e3["head"]["label_pos_mm_pairs"]["B+Acheck"]["1.0"] == Ss["runs"]["E3"]["by_dt"]["1.0"]["label_pos_err_mm"]
        assert set(m["runs"]["E1"]["head"]["trans_mm"]) == {"oracle"} and m["runs"]["E1"]["scale"] is None
        assert m["runs"]["static"]["slam"] is None and m["runs"]["static"]["track_fail_frac"] is None
        assert e3["track_fail_frac"] == 0.01
        assert e3["slam"] == {"keyframes_per_segment": 11.5, "runtime_s_per_segment": 31.5, "valid_frac": 0.8,
                              "tracked_frac": 1.0}
        sc = e3["scale"]
        assert set(sc) == {"label", "primary", "checks", "segments", "segments_ok", "n_compared", "abs_err_median",
                           "abs_err_p90", "bias_median", "flagged", "without_flagged", "methods"}
        assert sc["label"] == "B+Acheck" and sc["primary"] == "B" and sc["checks"] == ["A"]
        assert sc["segments"] == 4 and sc["segments_ok"] == 4 and sc["n_compared"] == 3
        errs = np.array([0.52 / 0.5 - 1, 0.5 / 0.6 - 1, 0.66 / 0.7 - 1])
        assert np.isclose(sc["abs_err_median"], np.median(np.abs(errs)))
        assert sc["flagged"] == ["ep01"]                        # A/B - 1 = +20%
        assert sc["without_flagged"]["n_compared"] == 2 and sc["methods"]["A"]["segments_ok"] == 2
        assert set(e3["labels"]) == {"oracle", "B+Acheck"} and set(e3["labels"]["oracle"]) == {"anchors", "by_step"}
        assert list(e3["labels"]["oracle"]["by_step"]) == [str(j) for j in STEPS]
        assert set(e3["chunk"]) == {"oracle", "B+Acheck"} and list(e3["chunk"]["oracle"]) == [str(h) for h in HS]
        assert m["gt_noise"]["tile_switch"]["n"] == 12
        # copies: small files only, never pairs.csv
        for f in ("analysis.json", "scale_E3.json", "scale_E3.md", "labels_E3.json", "labels_E3@B+Acheck.json",
                  "gt_noise.json", "eval_oracle/summary.json", "eval_oracle/summary.md",
                  "eval_B+Acheck/summary.json", "eval_B+Acheck/summary.md"):
            assert (out / f).is_file(), f
        assert not list(out.rglob("pairs.csv")) and r["copied"] == 10
        md = (out / "report.md").read_text()
        for title in ("Head rotation error", "Head translation error", "Tracking, keyframes", "Scale error vs the tile",
                      "position error [mm]", "rotation error [deg]", "Chunk-length", "noise floor"):
            assert title in md, title
        assert "H=100 (6.67 s)" in md and "| E3 | B+Acheck (flag" in md and "Comparison" not in md
        assert "track fail (dt 0.08 s, err > 2 deg)" in md
        # copies are strict JSON: the summaries' NaN -> null (originals untouched); NaN-free files unchanged
        for f in out.rglob("*.json"):
            strict_json(f)
        assert "NaN" in (res / "eval_oracle" / "summary.json").read_text()
        cp = strict_json(out / "eval_oracle" / "summary.json")
        assert cp["segments"]["ep00"]["E3"]["scale"] is None and cp["segments"]["ep01"]["E3"]["scale"] == 0.5
        assert cp["runs"] == S["runs"] and cp["dts"] == S["dts"]
        assert (out / "analysis.json").read_bytes() == (res / "analysis.json").read_bytes()
        # sample sizes under the head and label tables (fake stats: 40 pairs per dt; 90 anchors per step)
        _, _, after = section_table(md, "Head rotation error")
        assert after.strip() == "n [frame pairs]: 0.08 s: 40, 0.5 s: 40, 1.0 s: 40, 2.0 s: 40, 6.67 s: 40"
        _, _, after = section_table(md, "Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position")
        assert after.strip().startswith("n [anchors counting the step]: 0.07 s: 90, 0.13 s: 90, ")
        assert "pair-based" in md and "`eval_*/summary.md`" in md and "15 fps training timeline" in md
        # chunk table: anchors per H, mean / median, rotation once (scale-free), counted steps not recorded
        lab = json.load(open(res / "labels_E3.json"))
        hdr, rows, after = section_table(md, "Chunk-length label error")
        assert hdr == ["run", "quantity"] + [f"H={h} ({h / 15:.2f} s)" for h in HS]
        assert rows[0] == ["E3", "anchors", "79", "80", "80", "80"]
        by_q = {r[1]: r[2:] for r in rows}
        assert list(by_q) == ["anchors", "position [mm], oracle (tiles), mean / median",
                              "position [mm], B+Acheck, mean / median", "rotation [deg], every scale, mean / median"]
        assert by_q["position [mm], oracle (tiles), mean / median"] == [
            f"{lab['chunk'][str(h)]['pos_mm_mean']:.1f} / 3.0" for h in HS]
        assert by_q["rotation [deg], every scale, mean / median"] == [
            f"{lab['chunk'][str(h)]['rot_deg_mean']:.2f} / 0.40" for h in HS]
        assert R.SCALE_FREE in after and "not recorded in labels_*.json" in after
        assert "steps_median" not in m["runs"]["E3"]["chunk"]["oracle"]["15"]
        # without analysis.json the files are discovered: same numbers (slam falls back to the summary)
        (res / "analysis.json").unlink()
        m2 = R.variant_metrics(res, "expT", "main")
        e3b = m2["runs"]["E3"]
        assert e3b["slam"] == {"keyframes_per_segment": 11.5, "runtime_s_per_segment": 31.5, "valid_frac": 0.8}
        for k in ("head", "scale", "labels", "chunk", "track_fail_frac"):
            assert e3b[k] == e3[k], k
        assert m2["runs"]["E1"]["head"] == m["runs"]["E1"]["head"] and m2["n_segments"] == 4
        assert m2["evaluate"] == {"fail_deg": None, "dts": DTS}          # threshold unknown without the index
        assert "err > ? deg" in "\n".join(R.render_main(m2, ["1.0"]))


def test_legacy_adapter_headline():
    m = R.legacy_metrics(LEGACY)
    assert m["n_segments"] == 30 and list(m["runs"]) == ["static", "E1", "E2", "E3"]
    e3 = m["runs"]["E3"]
    assert round(e3["head"]["rot_deg"]["1.0"]["median"], 2) == 0.53                 # README key results
    assert [round(e3["head"]["rot_deg"][d]["p95"], 2) for d in ("0.08", "0.5", "1.0", "2.0", "6.67")] == \
        [0.66, 1.58, 2.32, 2.81, 0.92]
    sc = e3["scale"]
    assert sc["label"] == "B+Acheck" and round(100 * sc["abs_err_median"], 1) == 5.8
    assert round(100 * sc["abs_err_p90"], 1) == 21.4 and round(100 * sc["bias_median"], 1) == -5.3
    assert sc["n_compared"] == 28 and sc["segments_ok"] == 30 and sc["flagged"] == ["ep01", "ep12", "ep15"]
    a = sc["methods"]["A"]                                                            # slam/README.md: A 9/30, 5.1% / 11.1%
    assert a["segments_ok"] == 9 and round(100 * a["abs_err_median"], 1) == 5.1 and round(100 * a["abs_err_p90"], 1) == 11.1
    assert sc["methods"]["B"]["abs_err_median"] == sc["abs_err_median"]
    assert round(100 * m["runs"]["E2"]["scale"]["abs_err_median"], 1) == 10.3
    assert round(100 * m["runs"]["E1"]["scale"]["abs_err_p90"], 1) == 30.7
    assert [round(100 * m["runs"][r]["track_fail_frac"], 2) for r in ("E1", "E2", "E3")] == [1.93, 0.04, 0.34]
    lab = e3["labels"]
    assert lab["oracle"]["anchors"] == 989
    assert round(lab["oracle"]["by_step"]["15"]["pos_mm_median"], 1) == 4.0
    assert round(lab["B+Acheck"]["by_step"]["15"]["pos_mm_median"], 1) == 5.9
    assert round(lab["B+Acheck"]["by_step"]["15"]["pos_mm_p90"], 1) == 19.5
    assert e3["chunk"] == {} and set(e3["head"]["trans_mm"]) == {"oracle", "B+Acheck"}
    assert round(m["gt_noise"]["tile_switch"]["rot_deg_median"], 2) == 0.39
    assert m["evaluate"] == {"fail_deg": 2.0, "dts": DTS}


def test_legacy_roundtrip_report():
    """A fake 'main' variant arranged per the analysis contract from exp000_legacy's files gives
    the same canonical metrics as the legacy adapter, and the comparison tables agree column
    for column."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        res = legacy_to_contract(LEGACY, tmp / "main")
        out = tmp / "expF" / "results"
        R.run_report(make_job(out, {"main": res}, compare=["exp000_legacy"], name="expF"))
        mine = json.load(open(out / "metrics.json"))
        leg = R.legacy_metrics(LEGACY)
        for k in ("experiment", "variant"):
            mine.pop(k), leg.pop(k)
        assert mine == leg
        md = (out / "report.md").read_text()
        tabs = comparison_tables(md)
        assert len(tabs) == 8, list(tabs)
        n_cells = 0
        for title, (hdr, rows) in tabs.items():
            ng = sum(h.startswith("expF") for h in hdr)
            assert ng == sum(h.startswith("exp000_legacy") for h in hdr) and ng >= 1, title
            nk = len(hdr) - 2 * ng
            assert rows, title
            for r in rows:
                assert len(r) == len(hdr)
                assert r[nk:nk + ng] == r[nk + ng:], (title, r)
                n_cells += ng
        assert n_cells > 200
        assert "runs only in" not in md                       # the fake has E1, E2, E3 like exp000
        check_comparison_units(tabs)
        hdr, rows = tabs["Head rotation error [deg], n = frame pairs"]
        assert hdr == ["run", "dt [s]", "expF n", "expF median", "expF p95",
                       "exp000_legacy n", "exp000_legacy median", "exp000_legacy p95"]
        assert ["E3", "6.67", "88"] == rows[-1][:3]
        pos = next(t for t in tabs if t.startswith("Tool label position"))
        rot = next(t for t in tabs if t.startswith("Tool label rotation"))
        assert {r[1] for r in tabs[pos][1]} == {"oracle", "configured"} and tabs[pos][0][3] == "expF n"
        assert {r[1] for r in tabs[rot][1]} == {"every scale"} and rot.endswith(R.SCALE_FREE)
        assert ["E3", "every scale", "anchors", "989"] == next(r for r in tabs[rot][1] if r[0] == "E3")[:4]


def test_trajectory_known_perturbation():
    rng = np.random.default_rng(3)
    n, m_jump, theta = 300, 150, 0.5
    wall = 1000.0 + np.arange(n) / 30.0
    T = random_traj(rng, n)
    Rg = G.rodrigues([[0.3, -0.2, 0.9]])[0]
    T2 = sim3(T, 2.5, Rg, np.array([1.0, -2.0, 0.5]))
    c = R.compare_trajectories(T, T2, wall, DT_SHOW)
    for d in R.dt_key(1.0), R.dt_key(0.08):
        assert len(c["rot_diff"][d]) > 200 and c["rot_diff"][d].max() < 1e-5
    assert c["sim3"]["rms_over_extent"] < 1e-9 and np.isclose(c["sim3"]["scale"], 1 / 2.5)
    # rotation jump of theta deg (world frame) from frame m_jump on: pairs straddling it differ by theta
    T3 = T2.copy()
    Rj = G.rodrigues([np.radians(theta) * np.array([0.0, 0.6, 0.8])])[0]
    T3[m_jump:, :3, :3] = Rj @ T3[m_jump:, :3, :3]
    T3[[5, 6, 7]] = np.nan                                     # untracked in the repro
    c = R.compare_trajectories(T, T3, wall, [1.0, 0.08])
    a = c["rot_diff"]["1.0"]
    assert len(a) == n - 30 - 3                                 # dt = 30 frames; anchors 5-7 untracked
    big = a > theta / 2
    assert big.sum() == 30 and np.allclose(a[big], theta, atol=1e-6) and a[~big].max() < 1e-5
    a8 = c["rot_diff"]["0.08"]                                  # dt = 2.4 frames -> 2 (wall step 1/30)
    assert (a8 > theta / 2).sum() == 2
    assert c["tracked_main"] == n and c["tracked_repro"] == n - 3
    st = R._stat(a)
    assert np.isclose(st["max"], theta, atol=1e-6) and st["median"] < 1e-5
    # centre noise of known size: Sim3 RMS ~ noise RMS
    sig = 0.002
    T4 = T.copy()
    T4[:, :3, 3] += rng.normal(scale=sig, size=(n, 3))
    c = R.compare_trajectories(T, sim3(T4, 0.7, Rg, np.zeros(3)), wall, [1.0])
    assert abs(c["sim3"]["rms"] / (sig * np.sqrt(3)) - 1) < 0.1
    assert np.isclose(c["sim3"]["extent"], R.trajectory_extent(T[:, :3, 3]))
    assert abs(c["sim3"]["rms_over_extent"] - c["sim3"]["rms"] / c["sim3"]["extent"]) < 1e-15


def _write_traj(path, T, k, n_kf):
    from slam.backends import base as B
    n = len(T)
    inp = B.SlamInput(images=[f"{i:06d}.jpg" for i in range(n)], k=k, t=np.arange(n) / 30.0, K=np.eye(3),
                      size=(960, 536), mask_names=["motion"])
    tracked = np.isfinite(T).all((1, 2))
    out = B.SlamOutput(T_slam_cam=np.where(tracked[:, None, None], T, 0.0), tracked=tracked, metric=False,
                       kf_t=np.arange(n_kf), kf_disp=np.ones((n_kf, 536 // 8, 960 // 8)), meta={"n_keyframes": n_kf})
    path.parent.mkdir(parents=True, exist_ok=True)
    B.save_output(path, out, inp, "droid", {})


THETA, JUMP = 0.3, 100
REPRO = {"node": "slam.E3", "base_keys": {"slam.E3": "KMAIN", "depth.da2@E3": "DMAIN"},
         "runs": [{"variant": "repro1", "keys": {"slam.E3": "KREP", "depth.da2@E3": "DREP"}}]}


def make_slam_cache(work, segs, rng, perturbed=("ep01",)):
    """<work>/cache/slam/{KMAIN,KREP}/epNN/traj.npz (+ frames in the preprocess entry PRE named in
    the manifests). The repro trajectory is the main one, bit for bit, except in `perturbed`
    segments: Sim3-transformed, a rotation jump of THETA deg from frame JUMP, first 4 frames
    untracked, one keyframe more."""
    for seg in segs:
        n = 240
        k = 5000 + np.arange(n)
        fr = {"frames": [{"i": i, "k": int(k[i]), "wall": 100.0 + i / 30.0, "in_episode": True} for i in range(n)]}
        fdir = work / "cache" / "preprocess" / "PRE" / seg
        fdir.mkdir(parents=True)
        json.dump(fr, open(fdir / "frames.json", "w"))
        T = random_traj(rng, n)
        T2 = T.copy()
        if seg in perturbed:
            T2 = sim3(T, 1.3, G.rodrigues([[0.0, 0.0, 1.0]])[0], np.ones(3))
            T2[JUMP:, :3, :3] = G.rodrigues([[np.radians(THETA), 0, 0]])[0] @ T2[JUMP:, :3, :3]
            T2[:4] = np.nan
        _write_traj(work / "cache" / "slam" / "KMAIN" / seg / "traj.npz", T, k, 12)
        _write_traj(work / "cache" / "slam" / "KREP" / seg / "traj.npz", T2, k, 13 if seg in perturbed else 12)
    for key in ("KMAIN", "KREP"):
        json.dump({"deps": {"preprocess": "PRE", "masks": []}}, open(work / "cache" / "slam" / key / "manifest.json", "w"))


def test_repro_report():
    """--repro: metric deltas, per-segment scale differences and trajectory differences read from
    a synthetic cache (<work>/cache/slam/<key>/epNN/traj.npz, frames from the preprocess entry
    named in the slam manifest)."""
    rng = np.random.default_rng(5)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        main = make_results(tmp / "v_main", seed=1)
        rep = make_results(tmp / "v_rep", seed=1, shift=0.25, s_factor={"ep03": 1.02})
        work = tmp / "work"
        segs = ["ep00", "ep01"]
        theta = THETA
        make_slam_cache(work, segs, rng)
        repro = REPRO
        out = tmp / "exp" / "results"
        r = R.run_report(make_job(out, {"main": main, "repro1": rep}, repro=repro, work=work, segments=segs))
        assert r["repro"].endswith("repro.md")
        rj = json.load(open(out / "repro.json"))
        v = rj["variants"]["repro1"]
        d = {(x["row"], x["col"]): x for x in v["metrics"]}
        x = d[("E3 head rotation median [deg]", "1.0 s")]
        assert np.isclose(x["delta"], 0.25) and np.isclose(x["repro"] - x["main"], x["delta"])
        assert np.isclose(d[("E3 head translation p95, B+Acheck scale [mm]", "6.67 s")]["delta"], 0.25)
        assert d[("E3 tracking failures", "")]["delta"] == 0
        assert d[("E3 label pos median, oracle scale [mm]", "1.00 s")]["delta"] == 0      # same seed: same labels
        assert ("E3 chunk mean rot, B+Acheck scale [deg]", "H=100") in d
        sd = v["scale_s"]["E3"]
        assert np.isclose(sd["per_segment"]["ep03"], 0.02) and sd["per_segment"]["ep00"] == 0 and sd["worst"] == "ep03"
        t = v["trajectories"]["slam.E3"]
        assert set(v["trajectories"]) == {"slam.E3"} and t["segments_compared"] == 2
        e0, e1 = t["per_segment"]["ep00"], t["per_segment"]["ep01"]
        assert e0["times"] == "frames.json" and e0["rot_diff_deg"]["1.0"]["max"] < 1e-5
        assert e0["sim3"]["rms_over_extent"] < 1e-9 and e0["keyframes"] == {"main": 12, "repro": 12, "diff": 0}
        assert np.isclose(e1["rot_diff_deg"]["1.0"]["max"], theta, atol=1e-6)
        assert e1["tracked_repro"] == 236 and e1["rot_diff_deg"]["1.0"]["n"] == 240 - 30 - 4
        p = t["rot_diff_deg_pooled"]["1.0"]
        assert p["n"] == (240 - 30) + (240 - 30 - 4) and np.isclose(p["max"], theta, atol=1e-6)
        assert t["rot_diff_worst_segment_median"]["1.0"]["segment"] in segs
        assert t["keyframes"] == {"segments_differing": 1, "segments": 2, "max_abs_diff": 1, "mean_diff": 0.5}
        md = (out / "repro.md").read_text()
        assert "## Tolerance" in md and "slam.E3 rotation difference, pooled max [deg]" in md
        assert "| E3 head rotation median [deg] (0.08 s / 0.5 s / 1.0 s / 2.0 s / 6.67 s) |" in md
        assert "## repro1: slam.E3 per segment" in md
        assert "repro.md" in (out / "report.md").read_text()
        # bit identity: ep00 is the main trajectory bit for bit (stable angle: exactly 0), ep01 is not
        assert t["segments_bit_identical"] == 1 and e0["bit_identical"] is True and e1["bit_identical"] is False
        assert e0["rot_diff_deg"]["1.0"]["max"] == 0.0
        assert "| ep00 | yes |" in md and "| ep01 | no |" in md
        line = next(ln for ln in md.splitlines() if ln.startswith("- slam.E3 recomputed (repro1): "))
        assert line.startswith("- slam.E3 recomputed (repro1): outputs differ on 1/2 segments (bit-identical on 1); ")
        assert re.search(r"; \d+/\d+ metric deltas nonzero, largest \+0\.250 \(E\d head ", line), line
        assert line.endswith("; per-segment scale s differs by up to 2.00%"), line
        assert line in (out / "report.md").read_text().splitlines()
        # only the runs depending on slam.E3 (E3 via slam.E3, depth.da2@E3) are in the tolerance table;
        # E1's nonzero deltas (its analysis was rerun on a shifted fake) are summarised, not hidden
        assert rj["runs_recomputed"] == ["E3"]
        assert d[("E1 head rotation median [deg]", "1.0 s")]["run"] == "E1" and x["run"] == "E3"
        rows = [ln.split(" | ")[0].lstrip("| ") for ln in md.split("## Tolerance")[1].split("## repro1")[0].splitlines()
                if ln.startswith("| ")]
        assert not any(r.startswith("E1 ") for r in rows) and any(r.startswith("E3 head rotation") for r in rows)
        assert re.search(r"Not recomputed: E1 \(independent of slam\.E3.*\d+/\d+ metric deltas nonzero, "
                         r"largest \+0\.250 \(E1 head ", md)
        assert "Runs depending on slam.E3 (recomputed, listed below): E3." in md
        # rotation label / chunk rows are the same for both scales: one row each
        assert any(r.startswith("E3 label rot median, every scale (scale-free) [deg] (") for r in rows)
        assert any(r.startswith("E3 chunk mean rot, every scale (scale-free) [deg] (") for r in rows)
        assert not any("rot" in r and "B+Acheck scale" in r for r in rows)
        assert any(r.startswith("E3 label pos median, B+Acheck scale [mm]") for r in rows)
        assert "0.00% / 2.00% (ep03)" in md


def test_repro_bit_identical():
    """A recomputation that reproduces the SLAM outputs bit for bit and every metric: one line
    in report.md and at the top of repro.md; rotation differences exactly 0 (stable angle)."""
    rng = np.random.default_rng(7)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        main = make_results(tmp / "v_main", seed=2)
        rep = make_results(tmp / "v_rep", seed=2)
        work = tmp / "work"
        segs = ["ep00", "ep01"]
        make_slam_cache(work, segs, rng, perturbed=())
        out = tmp / "exp" / "results"
        R.run_report(make_job(out, {"main": main, "repro1": rep}, repro=REPRO, work=work, segments=segs))
        line = "- slam.E3 recomputed (repro1): outputs bit-identical on 2/2 segments; every metric delta 0"
        assert line in (out / "report.md").read_text().splitlines()
        md = (out / "repro.md").read_text()
        assert md.splitlines()[2] == line
        assert "rot_angle_deg_stable" in md and "exactly 0 for identical poses" in md
        t = json.load(open(out / "repro.json"))["variants"]["repro1"]["trajectories"]["slam.E3"]
        assert t["segments_bit_identical"] == 2 and all(e["bit_identical"] for e in t["per_segment"].values())
        assert all(st["n"] > 0 and st["max"] == 0.0 for st in t["rot_diff_deg_pooled"].values())
        assert "Not recomputed: E1 (independent of slam.E3" in md and "(every metric delta 0, see repro.json)" in md
        assert "| E3 per-segment scale \\|s_repro/s_main - 1\\| median / max | - | 0.00% / 0.00% | 0.00% |" in md
    # which runs a recomputed node (and its descendants) affects
    assert R.recomputed_runs(["slam.E3", "depth.da2@E3"], ["E1", "E3"]) == ["E3"]
    assert R.recomputed_runs(["depth.da2@E3"], ["E1", "E3"]) == ["E3"]
    assert R.recomputed_runs(["masks.motion", "slam.E3", "depth.da2@E3"], ["E1", "E3"]) == ["E3"]
    assert R.recomputed_runs(["slam.E1", "masks.tiles", "slam.E3", "depth.da2@E3"], ["E1", "E3"]) == ["E1", "E3"]
    assert R.recomputed_runs(["tiles", "masks.tiles", "slam.E3"], ["E1", "E3"]) == ["E1", "E3"]
    assert R.recomputed_runs(["preprocess", "slam.E1"], ["E1", "E3"]) == ["E1", "E3"]


def test_rotation_shown_once_only_when_scale_free():
    """Rotation label / chunk rows appear once ('every scale') when the scales agree, per scale
    otherwise."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for free in (True, False):
            res = make_results(tmp / f"main_{free}", rot_scale_free=free)
            out = tmp / f"exp_{free}" / "results"
            R.run_report(make_job(out, {"main": res}))
            md = (out / "report.md").read_text()
            hdr, rows, _ = section_table(md, "Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt rotation")
            _, prow, _ = section_table(md, "Tool labels (15 fps training timeline) vs tile labels: tool_t->tool_t+dt position")
            _, crows, after = section_table(md, "Chunk-length label error")
            rot_q = [r[1] for r in crows if r[1].startswith("rotation")]
            assert [r[1] for r in prow] == ["oracle (tiles)", "B+Acheck"]
            assert [r[1] for r in crows if r[1].startswith("position")] == [
                "position [mm], oracle (tiles), mean / median", "position [mm], B+Acheck, mean / median"]
            if free:
                assert [r[1] for r in rows] == ["every scale"] and R.SCALE_FREE in md
                assert rot_q == ["rotation [deg], every scale, mean / median"] and R.SCALE_FREE in after
            else:
                assert [r[1] for r in rows] == ["oracle (tiles)", "B+Acheck"] and R.SCALE_FREE not in md
                assert rot_q == ["rotation [deg], oracle (tiles), mean / median",
                                 "rotation [deg], B+Acheck, mean / median"]


def make_label_view(view, session, segs, rng, names=("E3", "E3@B+Acheck")):
    """Label files of an analysis view, <view>/<session>/segments/epNN/labels/{tiles,<name>}.npz:
    15 fps grids with gaps; the scaled file is the oracle one with translations x1.1 (same
    rotations). Returns {seg: mask of steps gap-free in both}."""
    oks = {}
    for i, seg in enumerate(segs):
        n = 70 + 20 * i
        t = 10.0 + np.arange(n) / 15.0
        d = Path(view) / session / "segments" / seg / "labels"
        d.mkdir(parents=True)
        gap_t, gap_s = np.zeros(n, bool), np.zeros(n, bool)
        gap_t[[5, 6, 30]] = True
        gap_s[[12, 50 + i]] = True
        T = random_traj(rng, n)
        np.savez(d / "tiles.npz", t=t, T_ref_tool=random_traj(rng, n), gap=gap_t, keep=np.array(True))
        for k, name in enumerate(names):
            Tn = T.copy()
            Tn[:, :3, 3] *= 1.0 + 0.1 * k
            np.savez(d / f"{name}.npz", t=t, T_ref_tool=Tn, gap=gap_s, keep=np.array(True))
        oks[seg] = ~gap_t & ~gap_s
    return oks


def expected_steps_median(oks, H):
    """Median over anchors (t gap-free, >= 1 counted step) of the counted steps j <= H: t + j
    inside the series and gap-free."""
    c = []
    for ok in oks.values():
        n = len(ok)
        for t in np.where(ok)[0]:
            k = sum(1 for j in range(1, H + 1) if t + j < n and ok[t + j])
            if k:
                c.append(k)
    return float(np.median(c))


def test_chunk_steps_recount_and_compare():
    """labels_*.json without the counted steps: the report recounts them from the analysis view's
    label files (checked against the file's anchor counts), shows them with mean / median per H,
    and says 'not recorded' when the recount does not match; the comparison chunk table shows
    the same per experiment."""
    rng = np.random.default_rng(11)
    session, segs = "yam_glove7", ["ep00", "ep01", "ep02"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        res = make_results(tmp / "run" / "main" / "results")
        oks = make_label_view(tmp / "run" / "main" / "view", session, segs, rng)
        old = C.WORK
        C.WORK = tmp / "run" / "main" / "view"
        try:
            for name, f in (("E3", "labels_E3.json"), ("E3@B+Acheck", "labels_E3@B+Acheck.json")):
                an = list(Lb.anchor_errors(session, name, 100))
                lab = Lb.step_stats(an, name, 100, (), tuple(STEPS))
                lab["chunk"] = Lb.chunk_stats(an, HS)
                json.dump(R._clean(lab), open(res / f, "w"))
        finally:
            C.WORK = old
        exps = tmp / "experiments"
        for name, compare in (("expA", []), ("expB", ["expA"])):
            R.run_report(make_job(exps / name / "results", {"main": res}, compare=compare, name=name,
                                  experiments_root=exps))
        exp_steps = {str(h): expected_steps_median(oks, h) for h in HS}
        assert exp_steps["100"] < 100 and exp_steps["15"] > 0               # truncated long chunks
        m = json.load(open(exps / "expB" / "results" / "metrics.json"))
        lab = json.load(open(res / "labels_E3.json"))
        for name in ("oracle", "B+Acheck"):
            ch = m["runs"]["E3"]["chunk"][name]
            assert {h: v["steps_median"] for h, v in ch.items()} == exp_steps
            assert {h: v["anchors"] for h, v in ch.items()} == {h: v["anchors"] for h, v in lab["chunk"].items()}
        assert "steps_median" not in lab["chunk"]["15"]                      # the analysis file is unchanged
        md = (exps / "expB" / "results" / "report.md").read_text()
        hdr, rows, after = section_table(md, "Chunk-length label error")
        by_q = {r[1]: r[2:] for r in rows}
        assert by_q["anchors"] == [str(lab["chunk"][str(h)]["anchors"]) for h in HS]
        assert by_q["counted steps per anchor, median"] == [R._count(exp_steps[str(h)]) for h in HS]
        c = lab["chunk"]
        assert by_q["position [mm], oracle (tiles), mean / median"] == [
            f"{c[str(h)]['pos_mm_mean']:.1f} / {c[str(h)]['pos_mm_median']:.1f}" for h in HS]
        assert by_q["rotation [deg], every scale, mean / median"] == [
            f"{c[str(h)]['rot_deg_mean']:.2f} / {c[str(h)]['rot_deg_median']:.2f}" for h in HS]
        assert f"(e.g. E3, H=100: {R._count(exp_steps['100'])} of 100)" in after
        assert "truncated chunks" in after and "not recorded" not in after
        # comparison: the same rows for both experiments, n / units in every table
        tabs = comparison_tables(md)
        title = next(t for t in tabs if t.startswith("Chunk-length"))
        hdr, rows = tabs[title]
        assert hdr == ["run", "scale", "quantity", "H [steps of 1/15 s]", "expB", "expA"] and title.endswith(R.SCALE_FREE)
        assert all(r[4] == r[5] != "-" for r in rows), rows
        steps_rows = [r for r in rows if r[2] == "counted steps per anchor, median"]
        assert [r[4] for r in steps_rows] == by_q["counted steps per anchor, median"]
        assert {r[1] for r in rows if r[2].startswith("rot")} == {"every scale"}
        assert [r[3] for r in steps_rows] == [f"{h} ({h / 15:.2f} s)" for h in HS]
        check_comparison_units(tabs)
        # a recount that does not reproduce the file's anchor counts is not used
        lab_s = json.load(open(res / "labels_E3@B+Acheck.json"))
        lab_s["chunk"]["30"]["anchors"] += 1
        json.dump(lab_s, open(res / "labels_E3@B+Acheck.json", "w"))
        out = tmp / "exp_bad" / "results"
        R.run_report(make_job(out, {"main": res}))
        m = json.load(open(out / "metrics.json"))
        assert "steps_median" not in m["runs"]["E3"]["chunk"]["B+Acheck"]["30"]
        assert m["runs"]["E3"]["chunk"]["oracle"]["30"]["steps_median"] == exp_steps["30"]
        _, rows, _ = section_table((out / "report.md").read_text(), "Chunk-length label error")
        by_q = {r[1]: r[2:] for r in rows}
        assert by_q["counted steps per anchor, median, B+Acheck"] == ["-"] * len(HS)
        assert by_q["counted steps per anchor, median, oracle (tiles)"] == [R._count(exp_steps[str(h)]) for h in HS]


def check_comparison_units(tabs):
    """Every dt column of the comparison tables has its unit in the header or in the values."""
    n_dt = 0
    for title, (hdr, rows) in tabs.items():
        for i, h in enumerate(hdr):
            if h.split(" ")[0] == "dt":
                n_dt += 1
                assert h == "dt [s]" or all(r[i].endswith(" s") or r[i] == "anchors" for r in rows), (title, h)
    assert n_dt >= 3


def test_fail_deg_printed_and_compared():
    """The report prints the configured tracking-failure threshold, and a comparison between
    experiments evaluated with different thresholds says so (title, note, every track fail cell)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for fd, name in ((3.0, "expA"), (2.0, "expB")):
            res = make_results(tmp / f"main_{name}", fail_deg=fd)
            out = tmp / name / "results"
            R.run_report(make_job(out, {"main": res}, compare=["exp000_legacy"], name=name))
            m = json.load(open(out / "metrics.json"))
            assert m["evaluate"]["fail_deg"] == fd
            md = (out / "report.md").read_text()
            assert f"track fail (dt 0.08 s, err > {fd:g} deg)" in md
            tabs = comparison_tables(md)
            title = next(t for t in tabs if t.startswith("Tracking failures"))
            hdr, rows = tabs[title]
            tf = [r for r in rows if r[1] == "track fail"]
            assert [r[0] for r in tf] == ["E1", "E3"]
            sec = md.split("### " + title, 1)[1].split("### ", 1)[0]
            if fd == 2.0:                                   # same threshold as exp000_legacy
                assert title == "Tracking failures (dt 0.08 s, err > 2 deg), keyframes, runtime"
                assert "differ" not in sec and all("deg" not in c for r in tf for c in r[2:])
            else:
                assert title == "Tracking failures (dt 0.08 s, err > each experiment's fail_deg), keyframes, runtime"
                assert "thresholds differ" in sec and "expA 3 deg, exp000_legacy 2 deg" in sec
                assert all(r[2].endswith("(> 3 deg)") and r[3].endswith("(> 2 deg)") for r in tf), tf
            kf = [r for r in rows if r[1] == "keyframes / segment"]
            assert all("deg" not in c for r in kf for c in r)


def test_repro_tables_nothing_compared():
    """Repro maxima are over finite values only; '-' when nothing was compared (no
    trajectories, no scale with a value in both variants), never 0."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        t = R.compare_slam_node(work, "KMAIN", "KREP", ["ep00", "ep01"], [1.0])      # no traj.npz at all
        assert t["segments_compared"] == 0 and t["segments_missing"] == ["ep00", "ep01"]
        assert t["keyframes"] == {"segments_differing": 0, "segments": 0, "max_abs_diff": None, "mean_diff": None}
        assert t["rot_diff_deg_pooled"]["1.0"] == {"n": 0} and t["sim3_rms_over_extent"]["max"] is None
        sc = contract_scale([{"segment": "ep00", "oracle_s": 0.5, "s_B": None, "s_A": None}], "E3")
        sd = R.scale_s_diffs(sc, sc)
        assert sd["n"] == 0 and sd["abs_max"] is None
        rep = {"node": "slam.E3", "dt_show": [1.0], "base_keys": {}, "segments": 2,
               "variants": {v: {"keys": {}, "metrics": [], "scale_s": {"E3": sd}, "trajectories": {"slam.E3": t}}
                            for v in ("repro1", "repro2")}}
        md = R.render_repro(rep, "expT")
        rows = {ln.split(" | ")[0].lstrip("| "): [c.strip() for c in ln.strip().strip("|").split(" | ")]
                for ln in md.splitlines() if ln.startswith("| ")}
        for title in ("E3 per-segment scale", "slam.E3 rotation difference, pooled max", "slam.E3 Sim3",
                      "slam.E3 keyframe count"):
            row = next(v for k, v in rows.items() if k.startswith(title))
            assert row[-1] == "-", (title, row)                # max |diff|
            assert all(c in ("-", "- / -") for c in row[1:]), (title, row)
        # finite values only: a NaN/None next to a finite value does not hide it
        assert R._max_finite([None, float("nan"), 0.25, 0.1]) == 0.25 and R._max_finite([None]) is None


def _mask_cells(st, fmt):
    """Expected report cells of a mask stat: n, median, p10, p90, mean."""
    f = (lambda v: f"{100 * v:.2f}%") if fmt == "area" else (lambda v: f"{v:.3f}")
    return [str(st["n"])] + [f(st[g]) for g in ("median", "p10", "p90", "mean")]


def test_mask_only_experiment():
    """An experiment without SLAM runs (masks + mask_compare only, no analysis.json): metrics.json
    with runs {}, evaluate / gt_noise null and the mask summary block; report.md with the mask
    section only; masks_*.json/.md copied (strict JSON); the overlays pointed to, not copied."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        work = tmp / "work"
        res = work / "runs" / "expM" / "main" / "results"
        mc = make_mask_results(res)
        out = tmp / "experiments" / "expM" / "results"
        r = R.run_report(make_job(out, {"main": res}, name="expM", work=work))      # job segments: ep00 only
        m = strict_json(out / "metrics.json")
        summ = mc["summary"]
        block = {"reference": "sam2", "candidate": "sam3", "dilate_px": 8, "parts": MASK_PARTS, "n_segments": 4,
                 **summ}
        assert m == {"experiment": "expM", "variant": "main", "n_segments": 4, "runs": {}, "gt_noise": None,
                     "evaluate": None, "masks": {"sam3_vs_sam2": block}}
        n_all = sum(mc["segments"][s]["frames"] for s in MASK_SEGS)
        assert summ["frames"] == n_all and summ["iou"]["n"] == n_all
        assert summ["precision"]["n"] == n_all - mc["segments"]["ep02"]["frames"]      # empty candidate in ep02
        # copies: the mask files only (strict JSON: ep02's NaN precision -> null), no overlay images
        assert sorted(p.name for p in out.rglob("*")) == ["masks_sam3_vs_sam2.json", "masks_sam3_vs_sam2.md",
                                                          "metrics.json", "report.md"]
        assert r["copied"] == 2
        assert "NaN" in (res / "masks_sam3_vs_sam2.json").read_text()
        cp = strict_json(out / "masks_sam3_vs_sam2.json")
        assert cp["segments"]["ep02"]["precision"] == {"n": 0, "median": None, "p10": None, "p90": None, "mean": None}
        assert cp["summary"] == summ and cp["segments"]["ep01"] == mc["segments"]["ep01"]
        # report.md: header, the mask section, nothing about SLAM
        md = (out / "report.md").read_text()
        assert md.splitlines()[:3] == ["# expM: report (variant main)", "",
                                       "4 segments. No SLAM runs (no head-motion evaluation); mask comparison only: "
                                       "sam3 vs sam2."]
        for title in ("Head rotation", "Head translation", "Tracking", "Scale error", "Tool labels", "Chunk-length",
                      "noise floor", "Comparison"):
            assert title not in md, title
        sec = md_section(md, "Mask comparison: sam3 vs sam2 (reference)")
        assert sec.startswith(f"{n_all} frames of 4 segments. Per frame") and "`masks_sam3_vs_sam2.md`" in sec
        (hdr, rows), (phdr, prows) = md_tables(sec)
        assert hdr == ["quantity", "n", "median", "p10", "p90", "mean"]
        assert rows == [["IoU"] + _mask_cells(summ["iou"], "share"),
                        ["recall (share of the reference covered by the candidate)"] + _mask_cells(summ["recall"], "share"),
                        ["precision (share of the candidate inside the reference)"] + _mask_cells(summ["precision"], "share"),
                        ["extra area: candidate only [% of frame]"] + _mask_cells(summ["extra_area"], "area"),
                        ["missed area: reference only [% of frame]"] + _mask_cells(summ["missed_area"], "area"),
                        ["DROID-cell IoU (masks dilated by 8 px)"] + _mask_cells(summ["cells_iou"], "share")]
        assert phdr == ["sam3 part", "mean area [% of frame]"]
        assert prows == [[p, f"{100 * summ['part_area'][p]:.2f}%"] for p in MASK_PARTS]
        lines = sec.splitlines()
        assert (f"Mean masked area [% of frame]: sam2 (reference) {100 * summ['area_ref']:.2f}%, "
                f"sam3 (candidate) {100 * summ['area_cand']:.2f}%.") in lines
        low = summ["segments_iou_median_below_0.8"]
        assert "ep02" in low and "ep00" not in low
        assert f"Segments with IoU median < 0.8: {', '.join(low)} ({len(low)} of 4)." in lines
        worst = ", ".join(f"{s} {v:.3f}" for s, v in summ["worst_segments"])
        assert f"Worst segments (IoU median): {worst}." in lines and worst.startswith("ep02 0.000, ")
        idx = json.load(open(res.parent / "overlays" / "sam3_vs_sam2" / "index.json"))
        ne = sum(e["kind"] == "even" for e in idx)
        ov = next(ln for ln in lines if ln.startswith("Overlay images"))
        assert ov.startswith("Overlay images (not copied into results/): `main/overlays/sam3_vs_sam2/` in the "
                             f"experiment's work run directory `<work>/runs/expM/` (<work> = `{work}`), "
                             f"{len(idx)} images: {ne} evenly spaced, {len(idx) - ne} lowest-IoU; "), ov
        assert len(idx) == 16 and 0 < ne < 16
        # overlays missing: said so; nothing else changes
        shutil.rmtree(res.parent / "overlays")
        out2 = tmp / "experiments" / "expM2" / "results"
        R.run_report(make_job(out2, {"main": res}, name="expM", work=work))
        md2 = (out2 / "report.md").read_text()
        assert ("Overlay images: not found (mask_compare writes them to `main/overlays/sam3_vs_sam2/` in the "
                "experiment's work run directory `<work>/runs/expM/`") in md2
        assert [ln for ln in md2.splitlines() if not ln.startswith("Overlay")] == \
            [ln for ln in md.splitlines() if not ln.startswith("Overlay")]
        # nothing at all in the results: still metrics.json and report.md (segments of the job)
        empty = tmp / "work" / "runs" / "expE" / "main" / "results"
        empty.mkdir(parents=True)
        out3 = tmp / "experiments" / "expE" / "results"
        R.run_report(make_job(out3, {"main": empty}, name="expE", segments=MASK_SEGS[:3]))
        assert strict_json(out3 / "metrics.json") == {"experiment": "expE", "variant": "main", "n_segments": 3,
                                                       "runs": {}, "gt_noise": None, "evaluate": None, "masks": {}}
        assert "3 segments. No SLAM runs (no head-motion evaluation); no analysis results." in \
            (out3 / "report.md").read_text()


def test_mask_compare_side_by_side():
    """Comparison with other experiments: the mask table has every experiment's comparisons side by
    side ('-' where an experiment has none, e.g. exp001's metrics.json without a masks block); a
    mask-only experiment shows no SLAM tables; a SLAM experiment's report and metrics only gain
    the mask section / block."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        work, exps = tmp / "work", tmp / "experiments"
        e1 = exps / "exp001_sam2_baseline" / "results"
        e1.mkdir(parents=True)
        shutil.copy(REPO / "experiments" / "exp001_sam2_baseline" / "results" / "metrics.json", e1)
        assert "masks" not in json.load(open(e1 / "metrics.json"))
        mcs = {}
        for name, seed, parts, compare in (("expA", 0, MASK_PARTS[:3], []),
                                           ("expB", 1, MASK_PARTS, ["expA", "exp001_sam2_baseline"])):
            res = work / "runs" / name / "main" / "results"
            mcs[name] = make_mask_results(res, seed=seed, parts=parts)
            R.run_report(make_job(exps / name / "results", {"main": res}, compare=compare, name=name,
                                  experiments_root=exps, work=work))
        md = (exps / "expB" / "results" / "report.md").read_text()
        assert "- runs only in exp001_sam2_baseline (not shown): static, E1, E3" in md
        assert "This experiment has no SLAM runs: the SLAM tables are left out." in md
        tabs = comparison_tables(md)
        title = "Mask comparison (per frame, pooled over every frame of every segment)"
        assert list(tabs) == [title]
        hdr, rows = tabs[title]
        assert hdr == ["comparison", "quantity", "expB", "expA", "exp001_sam2_baseline"]
        assert all(r[0] == "sam3_vs_sam2" and r[4] == "-" for r in rows)
        by_q = {r[1]: r[2:4] for r in rows}
        assert list(by_q)[:3] == ["reference / candidate", "dilate [px]", "segments / frames"]
        assert list(by_q)[-2:] == ["segments with IoU median < 0.8", "worst segments (IoU median)"]
        for i, name in enumerate(("expB", "expA")):
            s = mcs[name]["summary"]
            assert by_q["reference / candidate"][i] == "sam2 / sam3" and by_q["dilate [px]"][i] == "8"
            assert by_q["segments / frames"][i] == f"4 / {s['frames']}"
            assert by_q["IoU median / p10"][i] == f"{s['iou']['median']:.3f} / {s['iou']['p10']:.3f}"
            assert by_q["DROID-cell IoU median / p10"][i] == f"{s['cells_iou']['median']:.3f} / {s['cells_iou']['p10']:.3f}"
            assert by_q["extra area (candidate only) median / p90 [% of frame]"][i] == \
                f"{100 * s['extra_area']['median']:.2f}% / {100 * s['extra_area']['p90']:.2f}%"
            assert by_q["mean area reference / candidate [% of frame]"][i] == \
                f"{100 * s['area_ref']:.2f}% / {100 * s['area_cand']:.2f}%"
            assert by_q["part area: hand [% of frame]"][i] == f"{100 * s['part_area']['hand']:.2f}%"
            low = s["segments_iou_median_below_0.8"]
            assert by_q["segments with IoU median < 0.8"][i] == f"{len(low)}: {', '.join(low)}"
            assert by_q["worst segments (IoU median)"][i] == ", ".join(f"{a} {v:.3f}" for a, v in s["worst_segments"])
        assert by_q["part area: glove [% of frame]"] == [f"{100 * mcs['expB']['summary']['part_area']['glove']:.2f}%", "-"]
        # SLAM experiments: P without masks, T = the same results plus a mask comparison
        res_p = make_results(work / "runs" / "expP" / "main" / "results")
        res_t = make_results(work / "runs" / "expT" / "main" / "results")
        mc_t = make_mask_results(res_t, seed=3)
        for res, name in ((res_p, "expP"), (res_t, "expT")):
            R.run_report(make_job(exps / name / "results", {"main": res}, name="expX", work=work))
        mp = json.load(open(exps / "expP" / "results" / "metrics.json"))
        mt = json.load(open(exps / "expT" / "results" / "metrics.json"))
        assert mp["masks"] == {} and mt["masks"]["sam3_vs_sam2"]["iou"] == mc_t["summary"]["iou"]
        assert {k: v for k, v in mt.items() if k != "masks"} == {k: v for k, v in mp.items() if k != "masks"}
        md_p = (exps / "expP" / "results" / "report.md").read_text()
        md_t = (exps / "expT" / "results" / "report.md").read_text()
        assert md_t.startswith(md_p) and md_t[len(md_p):].startswith("## Mask comparison: sam3 vs sam2 (reference)\n")
        assert {p.name for p in (exps / "expT" / "results").iterdir()} - \
            {p.name for p in (exps / "expP" / "results").iterdir()} == {"masks_sam3_vs_sam2.json", "masks_sam3_vs_sam2.md"}
        # a SLAM experiment compared with a mask-only one: its SLAM tables as before, then the mask table
        R.run_report(make_job(exps / "expS" / "results", {"main": res_p}, compare=["expA"], name="expS",
                              experiments_root=exps, work=work))
        tabs = comparison_tables((exps / "expS" / "results" / "report.md").read_text())
        assert len(tabs) == 9 and list(tabs)[-1] == title and list(tabs)[0].startswith("Head rotation error")
        hdr, rows = tabs[title]
        assert hdr == ["comparison", "quantity", "expS", "expA"] and all(r[2] == "-" != r[3] for r in rows)
        hdr, rows = tabs["Head rotation error [deg], n = frame pairs"]
        assert all(c == "-" for r in rows for c in r[5:]) and all(c != "-" for r in rows for c in r[2:5])


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
