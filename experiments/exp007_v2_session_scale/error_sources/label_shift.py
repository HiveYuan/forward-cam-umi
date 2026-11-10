"""Scale errors in millimetres: how far each scale moves the tool labels.

For every episode, the label file built with a scale (Bsession: exp007, B: exp006) and the one built
with the tile-fitted oracle scale (exp007 `E3`) lie on the same 15 fps training timeline (slam.labels).
Rotation is scale-free, so the difference of the relative chunks tool_t -> tool_t+j is a pure
translation shift, |e| * |head translation over j steps| (e = s/s_o - 1). Statistics are taken over
anchors t where the SLAM label is gap-free (no tile requirement):
  1 s = step j 15, 2 s = j 30, chunk = mean over j = 1..100 (truncated at the episode end, as the
  label metric's chunk), for three populations: all 28 episodes with an oracle, the 22 with >= 3
  tile-visible keyframes, and the 10 episodes that carry the label metric's anchors (kept tile labels).

  V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
  PYTHONPATH=. $V experiments/exp007_v2_session_scale/error_sources/label_shift.py --out <json>
Read only on the exp006 / exp007 analysis views (adapted from the independent check in this folder's history).
"""
import argparse
import json
from pathlib import Path

import numpy as np

from slam import relative as Rel

HERE = Path(__file__).resolve().parent
RUNS = Path("/home/student/yuanliu-hawaii/work/runs")
VIEWS = {"Bsession": ("exp007_v2_session_scale", "E3@Bsession+Acheck"), "B": ("exp006_sam3_v2", "E3@B+Acheck")}
ORACLE = ("exp007_v2_session_scale", "E3")
H = 100


def seg_root(exp):
    return RUNS / exp / "main" / "view" / "yam_glove7" / "segments"


def shifts(name, meth):
    """Per anchor: {j: shift mm} for the gap-free steps of the chunk."""
    A = np.load(seg_root(VIEWS[meth][0]) / name / "labels" / f"{VIEWS[meth][1]}.npz")
    O = np.load(seg_root(ORACLE[0]) / name / "labels" / f"{ORACLE[1]}.npz")
    assert len(A["t"]) == len(O["t"]) and np.allclose(A["t"], O["t"]), name
    ok = ~A["gap"]
    out = []
    for t in np.nonzero(ok)[0]:
        ra, pad = Rel.relative_chunk(A["T_ref_tool"], t, H)
        ro, _ = Rel.relative_chunk(O["T_ref_tool"], t, H)
        js = [j for j in range(1, H + 1) if not pad[j - 1] and ok[min(t + j, len(ok) - 1)]]
        if js:
            out.append({j: 1000 * float(np.linalg.norm(ra[j - 1][:3, 3] - ro[j - 1][:3, 3])) for j in js})
    return out


def stats(x):
    x = np.asarray(x)
    return {"n": int(len(x)), "median_mm": float(np.median(x)), "p90_mm": float(np.percentile(x, 90)),
            "rms_mm": float(np.sqrt(np.mean(x ** 2))), "max_mm": float(x.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    err = {r["segment"]: r for r in json.load(open(HERE / "refnoise.json"))["rows"]}
    rows = sorted(err)
    keep = set(json.load(open(HERE / "tile_keyframes.json"))["keep"])
    lab = [n for n in rows if bool(np.load(seg_root(ORACLE[0]) / n / "labels" / "tiles.npz")["keep"])]
    pops = {"all": rows, "tile_kf_ge3": sorted(keep), "label_metric_episodes": lab}
    res = {"label_metric_episodes": lab, "stats": {}}
    for meth in VIEWS:
        per = {n: shifts(n, meth) for n in rows}
        res["stats"][meth] = {}
        for pop, names in pops.items():
            an = [s for n in names for s in per[n]]
            sg = [np.sign(err[n][f"err_{meth}"]) for n in names for _ in per[n]]      # sign of the scale error
            res["stats"][meth][pop] = {"1s": stats([s[15] for s in an if 15 in s]),
                                       "2s": stats([s[30] for s in an if 30 in s]),
                                       "chunk": stats([np.mean(list(s.values())) for s in an]),
                                       "signed_median_1s_mm": float(np.median([g * s[15] for g, s in zip(sg, an) if 15 in s])),
                                       "signed_median_chunk_mm": float(np.median([g * np.mean(list(s.values())) for g, s in zip(sg, an)]))}
    json.dump(res, open(a.out, "w"), indent=1)
    print("label-metric episodes:", lab)
    for meth in VIEWS:
        for pop in pops:
            r = res["stats"][meth][pop]
            print(f"{meth:8s} {pop:22s} " + "  ".join(
                f"{k} {r[k]['median_mm']:.2f}/{r[k]['p90_mm']:.2f}/max {r[k]['max_mm']:.1f} (n {r[k]['n']})" for k in ("1s", "2s", "chunk"))
                  + f"  signed median 1s {r['signed_median_1s_mm']:+.2f} chunk {r['signed_median_chunk_mm']:+.2f}")


if __name__ == "__main__":
    main()
