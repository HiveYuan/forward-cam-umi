"""The batch report of slam.ingest: experiments/batches/<batch>/report.md and summary.json."""
import json
import time
from pathlib import Path

from slam import config as C


def _load(p):
    p = Path(p)
    return json.load(open(p)) if p.exists() else None


def _f(x, nd=1, pct=False):
    if x is None:
        return "–"
    return f"{100 * x:.{nd}f}%" if pct else f"{x:.{nd}f}"


def session_rows(ing, sessions):
    rows = []
    for ds in sessions:
        s = ing.st(ds)
        exp = s.get("experiment")
        sj = ing.session_json(ds) or {}
        sc = _load(C.REPO / "experiments" / exp / "results" / f"scale_{ing.b['slam']['run']}.json") if exp else None
        xc = _load(C.gt_dir(ds) / "width_crosscheck.json") if ds in C.SESSIONS else None
        drops = {}
        for r in sj.get("rows", []):
            for w in r.get("dropped", []):
                key = ("scale failed" if w.startswith("scale") else "no SLAM" if w.startswith("no SLAM") else
                       "gripper coverage" if w.startswith("gripper coverage") else w)
                drops[key] = drops.get(key, 0) + 1
        v = sj.get("verdict") or {}
        status = (f"failed: {s['failed']}" if s.get("failed") else
                  "held: " + "; ".join(s.get("held") or []) if s.get("export") == "held" else
                  s.get("export") or ("SLAM done" if s.get("slam") else ("prep done" if s.get("prep") else "pending")))
        rows.append({"session": ds, "experiment": exp, "configured": len(sj.get("rows", [])) or None,
                     "kept": len(sj["kept"]) if "kept" in sj else None, "drops": drops,
                     "slam_valid": v.get("slam_valid"), "label_err_1s_mm": v.get("label_err_1s_mm"),
                     "scale_abs_err_median": (sc or {}).get("summary", {}).get("abs_err_median"),
                     "scale_bias_median": (sc or {}).get("summary", {}).get("bias_median"),
                     "width_head_vs_wrist": ({"median": xc.get("median_abs"), "p90": xc.get("p90_abs")} if xc else None),
                     "status": status, "accepted_by_review": sj.get("accepted_by_review", False)})
    return rows


def arm_row(exp, label=None):
    """Physical errors of an arm's best robot-val checkpoint (relative arms: val.json; joint arms: physical_fk.json)."""
    res = C.REPO / "experiments" / exp / "results"
    val = _load(res / "val.json")
    if val is None:
        return None
    phys = (val.get("physical") or {}).get("best", {}).get("robot")
    fk = _load(res / "physical_fk.json")
    if phys is None and fk:
        phys = fk["physical"]["best"]["robot"]
    best = str(val.get("best_step_robot_val"))
    loss = next((c["robot"]["loss"] for c in val["checkpoints"] if str(c["step"]) == best), None)
    if phys is None:
        return {"arm": label or exp, "exp": exp, "loss": loss}
    return {"arm": label or exp, "exp": exp, "step": best, "loss": loss,
            "pos": [phys["pos_mm"][k] for k in ("j14", "j49", "j99", "chunk_mean")],
            "rot": phys["rot_deg"]["chunk_mean"], "grip": phys["grip"]["chunk_mean"]}


def collected_row(val_json, label):
    """Physical errors on the collected val set at the run's best checkpoint (val.json from slam.val_rel)."""
    val = _load(val_json)
    if not val or "collected" not in ((val.get("physical") or {}).get("best") or {}):
        return None
    phys = val["physical"]["best"]["collected"]
    step = val["physical"]["best"]["step"]
    loss = next((c["collected"]["loss"] for c in val["checkpoints"] if c["step"] == step), None)
    return {"arm": label, "step": step, "loss": loss,
            "pos": [phys["pos_mm"][k] for k in ("j14", "j49", "j99", "chunk_mean")],
            "rot": phys["rot_deg"]["chunk_mean"], "grip": phys["grip"]["chunk_mean"]}


def what_if(ing, sessions):
    """Episodes kept per session under the batch's gates and looser ones, recomputed from the export's per-episode
    rows (sessions/<ds>.json): changing the gates needs a re-export only, never SLAM again."""
    from slam.collect_dataset import gate_session
    g0 = ing.b["gates"]
    variants = [("current", g0)]
    for cov in (0.6, 0.5):
        if cov < g0["grip_coverage_min"]:
            variants.append((f"coverage >= {cov}", {**g0, "grip_coverage_min": cov}))
    variants.append(("coverage >= 0.5, no session holds", {**g0, "grip_coverage_min": min(0.5, g0["grip_coverage_min"]),
                                                            "slam_valid_min": 0.0, "max_rejected_fraction": 1.0,
                                                            "label_err_1s_mm_max": 1e9}))
    data, md_rows, tot = {}, [], {name: [0, 0] for name, _ in variants}
    for ds in sessions:
        sj = ing.session_json(ds)
        if not sj or not sj.get("rows"):
            continue
        err = (sj.get("verdict") or {}).get("label_err_1s_mm")
        cells, data[ds] = [], {}
        for name, g in variants:
            kept, _, v = gate_session(sj["rows"], err, g)
            data[ds][name] = {"kept": len(kept), "held": v["held"], "reasons": v["reasons"], "slam_valid": v["slam_valid"]}
            cells.append(f"{len(kept)}{' (held)' if v['held'] else ''}")
            tot[name][0] += len(kept)
            tot[name][1] += 0 if v["held"] else len(kept)
        sv = (sj.get("verdict") or {}).get("slam_valid")
        md_rows.append(f"| {ds} | {len(sj['rows'])} | " + " | ".join(cells) + f" | {_f(sv, 1, True)} | {_f(err)} |")
    if not md_rows:
        return None
    names = [n for n, _ in variants]
    md = ["## What other gates would keep", "",
          "Episodes kept per session (\"held\": the session itself fails a gate and would not be mixed). Recomputed from "
          "the exported per-episode rows: a change of gates needs a re-export only (minutes), not SLAM. The last "
          "column set keeps every episode with a SLAM pose, a scale and gripper coverage >= 0.5, and holds no session.",
          "", "| session | configured | " + " | ".join(names) + " | SLAM valid (current, kept steps) | label error 1 s (mm) |",
          "|---|---|" + "---|" * len(names) + "---|---|", *md_rows,
          "| **total (not held)** | | " + " | ".join(f"**{tot[n][1]}** of {tot[n][0]}" for n in names) + " | | |", ""]
    return {"md": md, "data": {"variants": dict(variants), "sessions": data,
                               "totals": {n: {"kept": tot[n][0], "kept_not_held": tot[n][1]} for n in names}}}


def build(ing, sessions, mix_root=None):
    b = ing.b
    rows = session_rows(ing, sessions)
    L = [f"# Batch {b['batch']}", ""]
    if b.get("description"):
        L += [b["description"], ""]
    L += [f"Generated by `python -m slam.ingest` on {time.strftime('%F %T')} from "
          f"[`{Path(b['_path']).name}`](../{Path(b['_path']).name}). Bucket `{b['bucket']}`; wrist "
          f"`{b['wrist']}`; raw videos `{b['raw_policy']}`.", ""]
    if ing.stop_reason:
        L += [f"**Waiting for review:** {ing.stop_reason}", ""]
    L += ["## Sessions", "",
          "| session | experiment | episodes kept | dropped | SLAM valid | label error at 1 s (mm) | scale abs err / bias "
          "(median) | width head vs wrist (median / p90, cmd) | status |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        drops = ", ".join(f"{k} {n}" for k, n in r["drops"].items()) or "–"
        kept = f"{r['kept']} / {r['configured']}" if r["kept"] is not None else "–"
        sc = (f"{_f(r['scale_abs_err_median'], 1, True)} / {_f(r['scale_bias_median'], 1, True)}"
              if r["scale_abs_err_median"] is not None else "–")
        w = r["width_head_vs_wrist"]
        wx = f"{_f(w['median'], 3)} / {_f(w['p90'], 3)}" if w else "–"
        st = r["status"] + (" (accepted after review)" if r["accepted_by_review"] else "")
        L.append(f"| {r['session']} | {r['experiment'] or '–'} | {kept} | {drops} | {_f(r['slam_valid'], 1, True)} | "
                 f"{_f(r['label_err_1s_mm'])} | {sc} | {wx} | {st} |")
    tot = sum(r["kept"] or 0 for r in rows)
    L += ["", f"Episodes kept in total: {tot}. Gates: {json.dumps(b['gates'])}. Episodes come from each experiment's "
          "config (field-QC FAILs and session exclusions removed, review overrides applied: "
          f"{json.dumps(b['overrides']) if b['overrides'] else 'none'}).", ""]
    summary = {"batch": b["batch"], "sessions": rows, "episodes_kept": tot}
    wi = what_if(ing, sessions)
    if wi:
        L += wi["md"]
        summary["what_if"] = wi["data"]
    if mix_root is not None:
        mj, vj = _load(ing.dir / "mix.json"), _load(ing.dir / "verify.json")
        L += ["## Training dataset", "",
              f"`{mix_root}`: {mj['base_episodes']} episodes of `{b['dataset']['base']['repo']}` (unchanged, same "
              f"indices) + {mj['new_episodes']} collected episodes from {len(mj['shards'])} shards.", ""]
        if vj:
            c, bg = vj["collected"], vj["base_glove"]
            m = vj["motion_1s"]
            L += ["| | gripper p1 / p50 / p99 (cmd) | 1 s glove motion median / p90 (mm) | mean direction of moves > 20 mm |",
                  "|---|---|---|---|",
                  f"| base glove (HHs3) | {' / '.join(map(str, bg['gripper_p1_p50_p99']))} | "
                  f"{m['base_glove']['median_mm']:.1f} / {m['base_glove']['p90_mm']:.1f} | {m['base_glove']['mean_direction']} |",
                  f"| collected | {' / '.join(map(str, c['gripper_p1_p50_p99']))} | "
                  f"{m['collected']['median_mm']:.1f} / {m['collected']['p90_mm']:.1f} | {m['collected']['mean_direction']} |",
                  "", f"Collected steps: {c['steps']}, SLAM valid {100 * c['slam_valid']:.1f}%."
                  + (f" Frames: `{Path(vj['contact_sheet']).name}` in `{ing.dir}`." if vj.get("contact_sheet") else ""), ""]
        summary["mix"] = {"mix": mj, "verify": vj}
    arms = [a["exp"] for a in b["train"]]
    if arms:
        L += ["## Policies", "",
              "Best robot-val checkpoint, robot val episodes, VAE latent 0. Position error of the predicted chunk "
              "(mm) at steps 14 / 49 / 99 and the chunk mean; rotation and gripper chunk means.", "",
              "| arm | val loss | pos j14 | pos j49 | pos j99 | pos chunk mean | rot (deg) | gripper |",
              "|---|---|---|---|---|---|---|---|"]
        ref = b["reference"]
        r0 = arm_row(ref["exp"])
        if r0 is not None:
            pv = ref.get("paper_val")
            r0["arm"] = (f"Yosub paper G48, joint space (paper val {pv:.3f}; physical errors from our reproduction "
                         f"{ref['exp']}, val {r0['loss']:.3f})" if pv is not None and r0.get("loss") is not None
                         else f"Yosub paper G48, joint space ({ref['exp']})")
            if pv is not None:
                r0["loss"] = pv
        table = [r0]
        table += [arm_row(e) for e in b["compare"]] + [arm_row(e) for e in arms]
        tpl = {a["exp"]: arm_row(a["template"]) for a in b["train"]}
        for r in table:
            if r is None:
                continue
            if "pos" not in r:
                L.append(f"| {r['arm']} | {_f(r.get('loss'), 3)} | – | – | – | – | – | – |")
                continue
            p = r["pos"]
            rel = ""
            t = tpl.get(r["exp"])
            if t and "pos" in t:
                rel = f" ({100 * (p[3] / t['pos'][3] - 1):+.0f}% vs {t['exp']})"
            L.append(f"| {r['arm']} | {_f(r['loss'], 3)} | {p[0]:.1f} | {p[1]:.1f} | {p[2]:.1f} | {p[3]:.1f}{rel} | "
                     f"{r['rot']:.1f} | {r['grip']:.3f} |")
        L += ["", "Joint-space and relative val losses are in different units; compare the physical errors.", ""]
        summary["policies"] = [r for r in table if r]
        # the collected val set: the new arms, and the earlier arms (trained without these sessions)
        cv_rows = []
        for e in ing.crossval_arms():
            cv_rows.append(collected_row(ing.dir / "crossval" / e / "val.json", f"{e} (without the collected data)"))
        for e in arms:
            cv_rows.append(collected_row(C.REPO / "experiments" / e / "results" / "val.json", e))
        cv_rows = [r for r in cv_rows if r]
        if cv_rows:
            vj = _load(Path(mix_root) / "meta" / "val_episodes_collected.json") if mix_root else None
            n = len(vj["val_episodes"]) if vj else "?"
            L += ["### Collected val", "",
                  f"The {n} held-out collected episodes (meta/val_episodes_collected.json: "
                  f"{100 * b['dataset']['val_fraction']:.0f}% per session, evenly spread). Same checkpoints as above; "
                  f"every row scored with the loss masks {ing.crossval_masks()} (the same anchors and steps).", "",
                  "| arm | val loss | pos j14 | pos j49 | pos j99 | pos chunk mean | rot (deg) | gripper |",
                  "|---|---|---|---|---|---|---|---|"]
            for r in cv_rows:
                p = r["pos"]
                L.append(f"| {r['arm']} | {_f(r['loss'], 3)} | {p[0]:.1f} | {p[1]:.1f} | {p[2]:.1f} | {p[3]:.1f} | "
                         f"{r['rot']:.1f} | {r['grip']:.3f} |")
            L.append("")
            summary["collected_val"] = cv_rows
    return "\n".join(L) + "\n", summary
