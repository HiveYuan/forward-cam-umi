"""Masks' held-object gate on the segment frames: wrist width (as run in exp023-028) vs the new head width."""
import json, glob, numpy as np
from slam import config as C
from slam import masks_sam3v2 as S
RUNS = "/home/student/yuanliu-hawaii/work/runs"
VIEWS = {"yam_glove5_take1": "exp023_preroll_glove5_take1", "yam_glove5_take2": "exp024_preroll_glove5_take2",
         "yam_glove6_take1": "exp025_preroll_glove6_take1", "yam_glove6_take2": "exp026_preroll_glove6_take2",
         "yam_glove7": "exp027_preroll_glove7", "yam_glove8": "exp028_preroll_glove8"}
tot = dict(n=0, d=0, w=0, h=0, wf=0, hf=0); per = []
for sess, exp in VIEWS.items():
    head = S.load_gripper_wrist(C.gt_dir(sess) / "gripper_head.npz")      # same layout loader
    for seg in sorted(glob.glob(f"{RUNS}/{exp}/main/view/{sess}/segments/ep*")):
        try: z = np.load(f"{seg}/masks/motion.npz")
        except FileNotFoundError: continue
        fj = json.load(open(f"{seg}/frames.json")); wall = np.array([f["wall"] for f in fj["frames"]])
        ser = head.get(fj["episode"]["episode_index"])
        wh = S.frame_widths(wall, ser[0], ser[1], 0.12) if ser is not None else np.full(len(wall), np.nan)
        gh = S.held_gate(wh, 0.45, True); gw = z["held_gate"].astype(bool)
        tot["n"] += len(wall); tot["d"] += int((gh != gw).sum()); tot["w"] += int(gw.sum()); tot["h"] += int(gh.sum())
        tot["wf"] += int(np.isfinite(z["width"]).sum()); tot["hf"] += int(np.isfinite(wh).sum())
        per.append(((gh != gw).mean(), sess, seg.split("/")[-1]))
print(f"{len(per)} segments, {tot['n']} frames (preroll included): width available wrist {100*tot['wf']/tot['n']:.1f}% / head "
      f"{100*tot['hf']/tot['n']:.1f}%; held wrist {tot['w']} / head {tot['h']}; gate differs on {tot['d']} frames "
      f"({100*tot['d']/tot['n']:.2f}%)")
per.sort(reverse=True); print("worst segments:", [(s, e, round(100 * f, 1)) for f, s, e in per[:5]])
print("segments with any change:", sum(f > 0 for f, _, _ in per))
