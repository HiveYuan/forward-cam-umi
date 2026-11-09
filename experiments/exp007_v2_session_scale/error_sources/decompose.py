"""Decompose the Bsession scale error (exp007: SAM3 v2 masks, DROID E3) into sources.

Bsession: s_i = k_s * R_i, oracle s_o,i = k_need,i * R_i  =>  1 + err_i = k_s / k_need,i  (exact here).
In logs: e_i = log(1 + err_i) = -b_i,  b_i = log(k_need,i / k_s).
Split b_i = t_i + r_i with the tile truth on the table:
  t_i = log(k_tile,i / k_s): depth network's true correction on the background (table) vs the session's
        ball-based correction -> near/far compression (mean) + the network's per-episode background scale (spread)
  r_i = log(k_need,i / k_tile,i): what the network's table correction does not explain -> DROID's depth vs its
        own trajectory scale, background other than the table, tile-oracle noise.
Mean squared log error = mean(b)^2 + var(t) + var(r) + 2 cov(t, r).
"""
import json, sys
import numpy as np
d = json.load(open(sys.argv[1]))
ks = d["k_session"]["segments"]["k_session"]
R = [r for r in d["rows"] if r["s_oracle"] is not None]
b_all = np.array([np.log(r["k_need"] / ks) for r in R])
e_all = np.array([r["err_session"] for r in R])
print(f"k_session {ks:.4f}; episodes with oracle {len(R)}")
print(f"check: max |exp(-b) - 1 - err| = {np.max(np.abs(np.exp(-b_all) - 1 - e_all)):.2e}")
msle = np.mean(b_all ** 2)
print(f"ALL {len(R)}: mean b {np.mean(b_all):+.4f} (median {np.median(b_all):+.4f}), sd {np.std(b_all):.4f}, "
      f"rms log err {np.sqrt(msle):.4f}; bias^2 share {np.mean(b_all)**2/msle:.1%}, spread share {np.var(b_all)/msle:.1%}")
T = [r for r in R if r["tile_keyframes"] >= 5]
t = np.array([np.log(r["k_tile"] / ks) for r in T]); rr = np.array([np.log(r["k_need"] / r["k_tile"]) for r in T])
b = t + rr
m = np.mean(b ** 2)
cov = np.cov(t, rr, bias=True)[0, 1]
print(f"\nTILE SUBSET {len(T)} (>=5 tile keyframes): rms log err {np.sqrt(m):.4f} (all-episode rms {np.sqrt(msle):.4f})")
print(f"  mean b {np.mean(b):+.4f} = mean t {np.mean(t):+.4f} + mean r {np.mean(rr):+.4f}")
print(f"  var b {np.var(b):.5f} = var t {np.var(t):.5f} + var r {np.var(rr):.5f} + 2cov {2*cov:+.5f}  (corr {np.corrcoef(t, rr)[0,1]:+.2f})")
parts = {"bias (mean b)^2": np.mean(b)**2, "network per-episode spread var(t)": np.var(t),
         "rest var(r)": np.var(rr), "2 cov(t,r)": 2*cov}
for k, v in parts.items():
    print(f"  {k:36s} {v:.5f}  share {v/m:+.1%}  (as sd {np.sign(v)*np.sqrt(abs(v)):+.3f})")
print(f"  bias split: t mean {np.mean(t):+.4f} (network: table correction vs ball correction), r mean {np.mean(rr):+.4f}")
print(f"  median k_tile {np.median([r['k_tile'] for r in T]):.3f}, median k_ball (own k) {np.median([r['k'] for r in T]):.3f}, k_s {ks:.3f}")
def st(e):
    e = 100*np.asarray(e); return f"|err| median {np.median(np.abs(e)):.1f}%, p90 {np.percentile(np.abs(e),90):.1f}%, rms {np.sqrt(np.mean(e**2)):.1f}%, max {np.max(np.abs(e)):.1f}%"
print("\nCOUNTERFACTUALS")
print(f"  Bsession as is (all {len(R)}):             {st(e_all)}")
deb = np.exp(-(b_all - np.mean(b_all))) - 1
print(f"  bias removed (in-sample, all):        {st(deb)}")
print(f"  Bsession on tile subset ({len(T)}):         {st(np.exp(-b)-1)}")
print(f"  k = k_tile per episode (network correction known): {st(np.exp(-rr)-1)}")
print(f"  bias removed only, tile subset:       {st(np.exp(-(b-np.mean(b)))-1)}")
# within-episode scale changes: oracle on thirds
spr = []
for r in R:
    th = [x["oracle"] for x in r["oracle_thirds"] if x["strict_frames"] >= 20 and x["oracle"] and np.isfinite(x["oracle"])]
    if len(th) >= 2:
        spr.append((r["segment"], np.std(np.log(th)), len(th)))
sd_in = np.array([s for _, s, _ in spr])
print(f"\nWITHIN-EPISODE: oracle on thirds (>=20 strict frames, >=2 thirds): {len(spr)} episodes; "
      f"sd of log oracle across thirds: median {np.median(sd_in):.3f}, mean-square-root {np.sqrt(np.mean(sd_in**2)):.3f}, max {sd_in.max():.3f}")
print("  largest:", sorted(spr, key=lambda x: -x[1])[:5])
# k_session uncertainty (median of per-episode k): bootstrap
rng = np.random.default_rng(0)
kk = np.array([r["k"] for r in d["rows"] if r["k"] is not None and np.isfinite(r["k"])])
bs = [np.median(rng.choice(kk, len(kk))) for _ in range(5000)]
print(f"\nk_session bootstrap ({len(kk)} episodes): sd {np.std(bs)/ks:.1%} of k_session, 90% CI {np.percentile(bs,5)/ks-1:+.1%} .. {np.percentile(bs,95)/ks-1:+.1%}")
print("\nworst episodes (err, t, r):")
for r in sorted(R, key=lambda r: r["err_session"])[:6]:
    tt = np.log(r["k_tile"]/ks) if r["k_tile"] and r["tile_keyframes"] >= 1 else None
    rr_ = np.log(r["k_need"]/r["k_tile"]) if r["k_tile"] and r["tile_keyframes"] >= 1 else None
    print(f"  {r['segment']}: err {100*r['err_session']:+.1f}%  t {('%+.3f' % tt) if tt is not None else '-'}  r {('%+.3f' % rr_) if rr_ is not None else '-'}  tile kf {r['tile_keyframes']}  thirds {[round(x['oracle'],3) if x['oracle'] else None for x in r['oracle_thirds']]}")
