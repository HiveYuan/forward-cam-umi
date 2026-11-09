"""Report step (slam.pipeline.impl_report): canonical metrics, legacy adapter, comparison
tables, reproducibility check (python -m slam.tests.test_report).

test_legacy_* read experiments/exp000_legacy/results (in the repository); everything else is
synthetic and written to temporary directories.
"""
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

from slam import geometry as G
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
    keys = ("rot_err_deg", "trans_err_mm", "label_pos_err_mm", "label_rot_err_deg", "gt_rot_deg", "gt_trans_mm",
            "rot_err_deg_same_tiles", "trans_err_mm_same_tiles")
    S = {"dts": DTS, "runs": {}, "segments": {}}
    for i, seg in enumerate(segs):
        S["segments"][seg] = {"n_frames": 100, "in_ep": 60, "in_ep_strict": 40}
        for r in runs:
            if r != "static":
                S["segments"][seg][r] = {"scale": 0.5, "align_res_mm": 4.0, "n_keyframes": 10 + i,
                                         "runtime_s": 30.0 + i, "valid_frac": 0.8}
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
        lab["chunk"] = {str(h): {"anchors": 80, "pos_mm_mean": float(rng.uniform(2, 8)), "pos_mm_median": 3.0,
                                 "pos_mm_p90": 9.0, "rot_deg_mean": float(rng.uniform(0.2, 0.8)),
                                 "rot_deg_median": 0.4, "rot_deg_p90": 1.0, "pooled_pos_mm_mean": 4.0,
                                 "pooled_rot_deg_mean": 0.5} for h in HS}
    return lab


def make_results(d, seed=0, shift=0.0, s_factor=None, fail_deg=2.0):
    """Synthetic analysis results dir (contract layout): runs E1 (no scale) and E3 (B+Acheck)."""
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
    json.dump(fake_labels(rng, "E3"), open(d / "labels_E3.json", "w"))
    json.dump(fake_labels(rng, "E3@B+Acheck"), open(d / "labels_E3@B+Acheck.json", "w"))
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
        assert set(m) == {"experiment", "variant", "runs", "n_segments", "gt_noise", "evaluate"}
        assert m["experiment"] == "expT" and m["variant"] == "main" and m["n_segments"] == 4
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
        theta, jump = 0.3, 100
        for seg in segs:
            n = 240
            k = 5000 + np.arange(n)
            fr = {"frames": [{"i": i, "k": int(k[i]), "wall": 100.0 + i / 30.0, "in_episode": True} for i in range(n)]}
            fdir = work / "cache" / "preprocess" / "PRE" / seg
            fdir.mkdir(parents=True)
            json.dump(fr, open(fdir / "frames.json", "w"))
            T = random_traj(rng, n)
            T2 = sim3(T, 1.3, G.rodrigues([[0.0, 0.0, 1.0]])[0], np.ones(3))
            if seg == "ep01":
                T2[jump:, :3, :3] = G.rodrigues([[np.radians(theta), 0, 0]])[0] @ T2[jump:, :3, :3]
                T2[:4] = np.nan
            _write_traj(work / "cache" / "slam" / "KMAIN" / seg / "traj.npz", T, k, 12)
            _write_traj(work / "cache" / "slam" / "KREP" / seg / "traj.npz", T2, k, 13 if seg == "ep01" else 12)
        for key in ("KMAIN", "KREP"):
            json.dump({"deps": {"preprocess": "PRE", "masks": []}}, open(work / "cache" / "slam" / key / "manifest.json", "w"))
        repro = {"node": "slam.E3", "base_keys": {"slam.E3": "KMAIN", "depth.da2@E3": "DMAIN"},
                 "runs": [{"variant": "repro1", "keys": {"slam.E3": "KREP", "depth.da2@E3": "DREP"}}]}
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


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
