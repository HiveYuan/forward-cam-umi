"""SLAM step, impl droid_adaptive: the droid backend from 5 s before the episode (the segment's preroll),
re-run from short_preroll_s before the episode when the first run shows a fast head turn in the preroll
(decision 2026-11-12).

Why: a fast head turn before the episode (looking away and back, e.g. to the terminal where episodes are
marked) makes DROID initialize on it, and the trajectory can get spurious translations; every episode
with a scale error above 50% had one (2026-11-11). Starting the backend 1 s before every episode removes
those failures but loses accuracy on the others, so the short start is used only where a turn is seen.
Offline on 167 segments (exp023-exp028), this rule gave a scale error of 5.8 / 15.0% (median / p90)
against 6.6 / 19.0% for 5 s everywhere, 2 instead of 6 episodes above 50%, and the same rotation error.

Detection (no tiles): the first run's camera rotation between consecutive frames whose later frame lies
before the episode start, divided by their time step; a turn = any value above turn_deg_s. The output
is the second run (frames before its start get no pose, as droid_preroll) or the first run, so every
downstream step reads it unchanged. meta records the decision: preroll_peak_deg_s and its time before
the episode, short_start (bool), first_frame.
Parameters: the droid backend's + turn_deg_s + short_preroll_s.
"""
import json

import numpy as np

from slam.backends import base as B
from slam.pipeline.impl_slam_preroll import expand, subset


def preroll_peak(T_slam_cam, t, t_start):
    """(peak rotation speed in deg/s, its time relative to t_start) over consecutive frame pairs whose later
    frame is before t_start; (0.0, None) when there is no such pair with poses at both ends."""
    R = np.asarray(T_slam_cam, float)[:, :3, :3]
    ok = np.isfinite(R).all((1, 2))
    i = np.where(ok[:-1] & ok[1:] & (t[1:] < t_start) & (np.diff(t) > 0))[0]
    if not len(i):
        return 0.0, None
    dR = np.einsum("nji,njk->nik", R[i], R[i + 1])
    ang = np.degrees(np.arccos(np.clip((np.trace(dR, axis1=1, axis2=2) - 1) / 2, -1, 1))) / (t[i + 1] - t[i])
    j = int(np.argmax(ang))
    return float(ang[j]), float(t[i[j] + 1] - t_start)


def run_adaptive(backend, inp, t_start, params, turn_deg_s, short_preroll_s):
    """The decision and the run(s) for one segment -> (SlamOutput over all frames, decision dict)."""
    out = backend.run(inp, params)
    first_runtime = out.meta.get("runtime_s")
    peak, t_peak = preroll_peak(out.T_slam_cam, inp.t, t_start)
    info = {"preroll_peak_deg_s": peak, "preroll_peak_t_rel_s": t_peak, "turn_deg_s": turn_deg_s,
            "short_preroll_s": short_preroll_s, "short_start": bool(peak > turn_deg_s), "first_frame": 0,
            "runtime_first_run_s": first_runtime}
    if info["short_start"]:
        keep = inp.t >= t_start - short_preroll_s - 1e-6
        if not keep.any():
            raise RuntimeError(f"no frame after t_start - {short_preroll_s} s")
        i0 = int(np.argmax(keep))
        out = expand(backend.run(subset(inp, i0), params), len(inp), i0)
        info["first_frame"] = i0
    out.meta.update(info)
    return out, info


def run_slam_adaptive(job):
    params = dict(job.params)
    turn = float(params.pop("turn_deg_s"))
    short = float(params.pop("short_preroll_s"))
    if turn <= 0 or short < 0:
        raise ValueError(f"turn_deg_s must be > 0 and short_preroll_s >= 0, got {turn}, {short}")
    mask_names = [e["name"] for e in job.inputs.values() if e["step"] == "masks"]
    backend = B.get("droid")
    results = {}
    for seg in job.todo():
        view = job.input_view(seg)
        inp = B.load_input(view, mask_names)
        t_start = json.load(open(view / "frames.json"))["episode"]["t_start"]
        out, info = run_adaptive(backend, inp, t_start, params, turn, short)
        job.log(f"{seg}: {len(inp)} frames, preroll peak {info['preroll_peak_deg_s']:.0f} deg/s -> "
                f"{'short start (' + str(short) + ' s), first frame ' + str(info['first_frame']) if info['short_start'] else '5 s start'}")
        tmp = job.tmp(seg)
        meta = B.save_output(tmp / "traj.npz", out, inp, job.node["impl"], job.params)
        (tmp / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
        job.publish(seg, tmp)
        keep_k = ("n_frames", "n_tracked", "n_keyframes", "runtime_s", "peak_gpu_gb", "valid_frac", "masks_used",
                  "preroll_peak_deg_s", "preroll_peak_t_rel_s", "short_start", "first_frame")
        results[seg] = {k: meta.get(k) for k in keep_k}
    return results
