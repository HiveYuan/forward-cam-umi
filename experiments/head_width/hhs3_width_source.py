"""Locate HHs3 gripper breakpoints (line intersection from the samples on either side) and measure the distance
to the nearest frame time of each camera. Source camera: distances near 0; other cameras: spread over +-half a
frame period."""
import json, glob, numpy as np, pandas as pd
RAW = "/home/student/yuanliu-hawaii/head-cam-umi/data/raw"
man = [e for e in json.load(open("/home/student/yuanliu-hawaii/head-cam-umi-p2/calib/hhs3_manifest.json"))["episodes"] if e["method"] == "verified"]
df = pd.concat([pd.read_parquet(f) for f in glob.glob("/home/student/.cache/huggingface/lerobot/pilot_glove_HHs3/data/**/*.parquet", recursive=True)])
gr = {h: np.stack(g["action"].values)[:, 6].astype(float) for h, g in df.groupby("episode_index")}
def stems(sess):
    base, take = sess.split("_take") if "_take" in sess else (sess, None)
    suf = ".take1" if take == "1" else ""
    return {c: f"{RAW}/{base}_{c}{suf}_ts.json" for c in ("b0587b", "b0587", "fish")}
cache = {}
def times(p):
    if p not in cache: cache[p] = np.array([r["wall"] for r in json.load(open(p))])
    return cache[p]
D = {c: [] for c in ("b0587b", "b0587", "fish")}
for e in man:
    g = gr[e["hhs3"]]; dt = 1 / 37.5; t = e["t0"] + np.arange(len(g)) * dt
    for j in range(1, len(g) - 2):
        s1 = (g[j] - g[j - 1]) / dt; s2 = (g[j + 2] - g[j + 1]) / dt
        if abs(s2 - s1) < 0.5: continue
        # L1: g[j] + s1 (x - t[j]); L2: g[j+1] + s2 (x - t[j+1])
        tau = (g[j + 1] - g[j] + s1 * t[j] - s2 * t[j + 1]) / (s1 - s2)
        if not (t[j] < tau < t[j + 1]): continue
        # consistency: the middle segment must be explained by one breakpoint (both lines meet the samples)
        for c, p in stems(e["session"]).items():
            T = times(p); i = np.searchsorted(T, tau)
            D[c].append(min(abs(tau - T[max(i - 1, 0)]), abs(T[min(i, len(T) - 1)] - tau)))
for c, d in D.items():
    d = 1000 * np.array(d)
    print(f"{c:7s}: n {len(d)}, |tau - nearest frame| median {np.median(d):.2f} ms, p25 {np.percentile(d,25):.2f}, "
          f"<1 ms {100*np.mean(d<1):.0f}%, <2 ms {100*np.mean(d<2):.0f}%")
