"""Scale and label errors with the reference (tile-fitted scale) noise taken out.

The per-episode oracle s_o is a Umeyama fit of the SLAM camera centres to the strict tile head
poses (slam.evaluate.segment_scale). Its own uncertainty is estimated per episode by a moving-block
bootstrap over those frames (blocks of BLOCK consecutive fit frames, since tile-pose noise is
correlated in time), giving sd_ref = sd(log s_o*). Then:

  1. reliable subset: episodes with sd_ref <= MAX_SD_REF; scale errors (B: exp006, Bsession:
     exp007) and tool-label errors (B, Bsession, oracle) on that subset only;
  2. all episodes, noise-corrected: var_method = var(log(1+err)) - mean(sd_ref^2)  (reference noise
     independent of the method's error); bias as plain and inverse-variance weighted mean.
The selection uses the tile data only, never the method's error.

  V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
  PYTHONPATH=. $V experiments/exp007_v2_session_scale/error_sources/refnoise.py --out <json>
Read only on the exp006 / exp007 analysis views.
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

from slam import geometry as G
from slam import labels as L
from slam import scale as SC

REPO = Path(__file__).resolve().parents[3]
WORK = Path("/home/student/yuanliu-hawaii/work/runs")
GT = "/home/student/yuanliu-hawaii/work/yam_glove7/gt"
SESSION = "yam_glove7"
BLOCK, N_BOOT, MAX_SD_REF, SEED = 13, 2000, 0.03, 0
LABEL = {"horizon": 100, "chunk_H": [15, 30, 50, 100], "label_steps": (1, 2, 4, 8, 15, 30, 60, 100)}

spec = importlib.util.spec_from_file_location("diag", REPO / "experiments/exp005_session_scale/diagnosis.py")
DG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DG)


def use_view(exp):
    return DG.configure(WORK / exp / "main" / "view", GT)


def oracle_bootstrap(seg, run, rng):
    S = SC._segment(seg)
    T = SC._run(seg, run)[0]["T_slam_cam"].astype(float)
    m = S["strict"] & np.isfinite(T).all((1, 2))
    src, dst = T[m, :3, 3], S["T_wc"][m, :3, 3]
    n = len(src)
    if n < 10:
        return None
    s0 = G.umeyama_scale(src, dst)[0]
    nb = int(np.ceil(n / BLOCK))
    starts_max = max(n - BLOCK, 0)
    logs = []
    for _ in range(N_BOOT):
        st = rng.integers(0, starts_max + 1, nb)
        idx = (st[:, None] + np.arange(min(BLOCK, n))[None]).ravel()[:n]
        d = dst[idx]
        if np.linalg.norm(d - d.mean(0), axis=1).max() < 0.01:
            continue
        logs.append(np.log(G.umeyama_scale(src[idx], d)[0]))
    travel = float(np.linalg.norm(dst - dst.mean(0), axis=1).max())
    return {"s_o": float(s0), "n_fit_frames": int(n), "sd_ref": float(np.std(logs)),
            "boot_ok": len(logs), "head_travel_m": travel}


def stats(e):
    e = 100 * np.asarray(e, float)
    if not len(e):
        return None
    return {"n": int(len(e)), "abs_median": float(np.median(np.abs(e))), "abs_p90": float(np.percentile(np.abs(e), 90)),
            "bias_median": float(np.median(e)), "rms": float(np.sqrt(np.mean(e ** 2))),
            "abs_max": float(np.abs(e).max()), "n_over_10": int((np.abs(e) > 10).sum()),
            "n_over_20": int((np.abs(e) > 20).sum())}


def label_stats(exp, name, exclude):
    use_view(exp)
    anchors = list(L.anchor_errors(SESSION, name, LABEL["horizon"], set(exclude)))
    st = L.step_stats(anchors, name, LABEL["horizon"], set(exclude), LABEL["label_steps"])
    ch = L.chunk_stats(anchors, LABEL["chunk_H"])
    b = st["by_step"].get(15) or st["by_step"].get("15") or {}
    c100 = ch.get(100) or ch.get("100") or {}
    return {"anchors": st.get("anchors"), "pos_1s_median": b.get("pos_mm_median"), "pos_1s_p90": b.get("pos_mm_p90"),
            "chunk100_mean": c100.get("pos_mm_mean")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    sc7 = json.load(open(REPO / "experiments/exp007_v2_session_scale/results/scale_E3.json"))
    sc6 = json.load(open(REPO / "experiments/exp006_sam3_v2/results/scale_E3.json"))
    e7 = {r["segment"]: r for r in sc7["rows"]}
    e6 = {r["segment"]: r for r in sc6["rows"]}
    root = use_view("exp007_v2_session_scale")
    rows = []
    for seg in sorted(root.glob("ep[0-9][0-9]")):
        r7, r6 = e7[seg.name], e6[seg.name]
        if r7["err"] is None:
            continue
        assert abs(r7["oracle_s"] - r6["oracle_s"]) < 1e-12, seg.name      # same SLAM run, same oracle
        bo = oracle_bootstrap(seg, "E3", rng)
        assert abs(bo["s_o"] - r7["oracle_s"]) < 1e-9 * r7["oracle_s"], seg.name
        rows.append({"segment": seg.name, **bo, "err_Bsession": r7["err"], "err_B": r6["err"]})
    sd = np.array([r["sd_ref"] for r in rows])
    good = sd <= MAX_SD_REF
    out = {"params": {"block_frames": BLOCK, "n_boot": N_BOOT, "max_sd_ref": MAX_SD_REF, "seed": SEED},
           "rows": rows, "excluded": [r["segment"] for r, g in zip(rows, good) if not g]}
    for meth in ("Bsession", "B"):
        e = np.array([r[f"err_{meth}"] for r in rows])
        le = np.log1p(e)
        var_m = float(np.var(le) - np.mean(sd ** 2))
        w = 1 / (np.var(le) + sd ** 2)
        out[meth] = {"all": stats(e), "reliable": stats(e[good]),
                     "all_log": {"mean": float(np.mean(le)), "sd": float(np.std(le)),
                                 "mean_sd_ref": float(np.sqrt(np.mean(sd ** 2))),
                                 "sd_method_noise_corrected": float(np.sqrt(max(var_m, 0))),
                                 "bias_weighted": float(np.sum(w * le) / np.sum(w))},
                     "reliable_log": {"mean": float(np.mean(le[good])), "sd": float(np.std(le[good])),
                                      "mean_sd_ref": float(np.sqrt(np.mean(sd[good] ** 2)))}}
    excl = out["excluded"] + [s for s in ("ep07", "ep16")]          # no oracle at all
    out["labels"] = {
        "all": {"B": label_stats("exp006_sam3_v2", "E3@B+Acheck", []),
                "Bsession": label_stats("exp007_v2_session_scale", "E3@Bsession+Acheck", []),
                "oracle": label_stats("exp007_v2_session_scale", "E3", [])},
        "reliable": {"B": label_stats("exp006_sam3_v2", "E3@B+Acheck", excl),
                     "Bsession": label_stats("exp007_v2_session_scale", "E3@Bsession+Acheck", excl),
                     "oracle": label_stats("exp007_v2_session_scale", "E3", excl)}}
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    print("episode  fit_frames  travel_m  sd_ref%  err_Bsession%  err_B%")
    for r in sorted(rows, key=lambda r: -r["sd_ref"]):
        print(f"{r['segment']}  {r['n_fit_frames']:4d}  {r['head_travel_m']:.3f}  {100 * r['sd_ref']:5.1f}  "
              f"{100 * r['err_Bsession']:+6.1f}  {100 * r['err_B']:+6.1f}")
    print("excluded (sd_ref > %.0f%%):" % (100 * MAX_SD_REF), out["excluded"])
    for meth in ("Bsession", "B"):
        print(meth, json.dumps({k: out[meth][k] for k in ("all", "reliable")}))
        print("   log:", json.dumps(out[meth]["all_log"]), json.dumps(out[meth]["reliable_log"]))
    print("labels", json.dumps(out["labels"], indent=1))


if __name__ == "__main__":
    main()
