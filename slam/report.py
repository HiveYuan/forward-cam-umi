#!/usr/bin/env python3
"""Collect the evaluation outputs of a session into one markdown report.

Reads <work>/<session>/eval/{summary.json, gt_noise.json, labels_<run>.json} and the
per-segment mask/SLAM metadata; writes <work>/<session>/eval/report.md.

  python -m slam.report --session yam_glove7 --runs E1,E2,E3
"""
import argparse
import json

import numpy as np

from slam import config as C

DT_SHOW = ["0.08", "0.5", "1.0", "2.0", "6.67"]


def cell(s, k="median"):
    return "-" if not s or not s.get("n") else f"{s[k]:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--runs", default="E1,E2,E3")
    a = ap.parse_args()
    ev = C.WORK / a.session / "eval"
    S = json.load(open(ev / "summary.json"))
    runs = ["static"] + [r for r in a.runs.split(",") if r in S["runs"]]
    L = [f"# SLAM evaluation: {a.session}", ""]

    segs = sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]"))
    nf = sum(len(json.load(open(s / "frames.json"))["frames"]) for s in segs)
    L += [f"{len(segs)} segments, {nf} frames. Ground truth: tile head poses with >= 2 tiles "
          f"({sum(v['in_ep_strict'] for v in S['segments'].values())} of "
          f"{sum(v['in_ep'] for v in S['segments'].values())} in-episode frames).", ""]

    for metric, title in (("rot_err_deg", "Head rotation error cam_t->cam_t+dt [deg], median / p95"),
                          ("trans_err_mm", "Head translation error, tile-fitted scale [mm], median / p95"),
                          ("label_pos_err_mm", "Label tool_t->tool_t+dt position error [mm], median / p95"),
                          ("label_rot_err_deg", "Label rotation error [deg], median / p95")):
        L += [f"## {title}", "", "| run | " + " | ".join(f"{d} s" for d in DT_SHOW) + " |",
              "|---|" + "---|" * len(DT_SHOW)]
        for r in runs:
            b = S["runs"][r]["by_dt"]
            L.append(f"| {r} | " + " | ".join(f"{cell(b[d][metric])} / {cell(b[d][metric], 'p95')}"
                                              for d in DT_SHOW) + " |")
        L.append("")
    n = S["runs"]["static"]["by_dt"]
    L += ["Pairs: " + ", ".join(f"{d} s: {n[d]['rot_err_deg'].get('n', 0)}" for d in DT_SHOW), ""]

    L += ["## Tracking failures and keyframes", "", "| run | fail % (dt 0.08 s, err > 2 deg) | keyframes / segment | runtime s / segment | valid pixels |",
          "|---|---|---|---|---|"]
    for r in runs[1:]:
        info = [v[r] for v in S["segments"].values() if r in v]
        f = S["runs"][r]["track_fail_frac"]
        L.append(f"| {r} | {100 * f:.2f} | {np.mean([i['n_keyframes'] for i in info]):.1f} | "
                 f"{np.mean([i['runtime_s'] for i in info]):.0f} | {100 * np.mean([i['valid_frac'] for i in info]):.0f}% |")
    L.append("")

    L += ["## Rotation error at dt = 0.5 s by head rotation speed [deg/s]: median (n)", "",
          "| run | " + " | ".join(S["runs"]["static"]["by_speed_dt0.5"]) + " |",
          "|---|" + "---|" * len(S["runs"]["static"]["by_speed_dt0.5"])]
    for r in runs:
        b = S["runs"][r]["by_speed_dt0.5"]
        L.append(f"| {r} | " + " | ".join(f"{cell(v)} ({v.get('n', 0)})" for v in b.values()) + " |")
    L.append("")

    L += ["## Per segment: rotation error at dt = 1 s, median [deg]", "",
          "| segment | GT frames | " + " | ".join(runs[1:]) + " |", "|---|---|" + "---|" * len(runs[1:])]
    for sname, info in S["segments"].items():
        L.append(f"| {sname} | {info['in_ep_strict']} | " +
                 " | ".join(cell(S["runs"][r]["per_segment_dt1"].get(sname)) for r in runs[1:]) + " |")
    L.append("")

    if (ev / "gt_noise.json").exists():
        g = json.load(open(ev / "gt_noise.json"))
        L += ["## Ground-truth noise floor (2-tile solves)", "",
              f"From {g['frames_with_all_tiles']} frames with all 4 tiles, comparing disjoint tile pairs.", "",
              "| | rot deg median / p95 | trans mm median / p95 |", "|---|---|---|"]
        for dt, v in g["by_dt"].items():
            if v.get("n"):
                L.append(f"| same tiles, dt {dt} s (n={v['n']}) | {v['rot_deg_median']:.2f} / {v['rot_deg_p95']:.2f} | "
                         f"{v['trans_mm_median']:.1f} / {v['trans_mm_p95']:.1f} |")
        t = g["tile_switch"]
        L += [f"| tile set changes between ends (n={t['n']}) | {t['rot_deg_median']:.2f} / {t['rot_deg_p95']:.2f} | "
              f"{t['trans_mm_median']:.1f} / {t['trans_mm_p95']:.1f} |", ""]

    lab = [(r, ev / f"labels_{r}.json") for r in runs[1:]]
    lab = [(r, json.load(open(p))) for r, p in lab if p.exists()]
    if lab:
        steps = sorted({int(j) for _, d in lab for j in d["by_step"]})
        L += ["## End-to-end labels on the 15 fps training timeline vs tile labels (tile-fitted scale)", "",
              "Position error [mm] median / p90 of tool_t->tool_t+dt.", "",
              "| run | anchors | " + " | ".join(f"{j / 15:.2f} s" for j in steps) + " |",
              "|---|---|" + "---|" * len(steps)]
        for r, d in lab:
            b = d["by_step"]
            L.append(f"| {r} | {d['anchors']} | " + " | ".join(
                f"{b[str(j)]['pos_mm_median']:.1f} / {b[str(j)]['pos_mm_p90']:.1f}" if str(j) in b else "-"
                for j in steps) + " |")
        L.append("")

    (ev / "report.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
