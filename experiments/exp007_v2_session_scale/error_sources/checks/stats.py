import json, itertools
import numpy as np
from scipy import stats as SS
from pathlib import Path
D = str(Path(__file__).resolve().parent.parent) + "/"     # error_sources/
d = json.load(open(D + "diag_E3_v2.json")); v = json.load(open(D + "checks/view_recompute.json"))
ks = d["k_session"]["segments"]["k_session"]
rows = {r["segment"]: r for r in d["rows"]}
print("ks json", ks, "ks view", v["ks"])
# C1 from view
E = [n for n in sorted(v["eps"]) if np.isfinite(v["eps"][n]["s_o"])]
print("C1 n", len(E), "missing", [n for n in v["eps"] if n not in E])
c1 = [abs((v["eps"][n]["s_sess"] / v["eps"][n]["s_o"]) - ks / (v["eps"][n]["s_o"] / v["eps"][n]["R"])) for n in E]
print("C1 max |s/s_o - ks/k_need| from view:", max(c1), " max |err_view - err_json|:",
      max(abs(v["eps"][n]["s_sess"] / v["eps"][n]["s_o"] - 1 - rows[n]["err_session"]) for n in E),
      " cache s match:", max(abs(v["eps"][n]["s_sess"] - v["eps"][n]["cache_s_sess"]) for n in v["eps"]))
err = np.array([v["eps"][n]["s_sess"] / v["eps"][n]["s_o"] - 1 for n in E])
e = np.log1p(err)
print("\nC2 n", len(e))
for name, x in (("log", e), ("rel", err)):
    ms = np.mean(x ** 2)
    print(f"  {name}: mean {x.mean():+.4f} median {np.median(x):+.4f} sd0 {x.std():.4f} sd1 {x.std(ddof=1):.4f} rms {np.sqrt(ms):.4f}  bias share {x.mean()**2/ms:.3f} spread share {x.var()/ms:.3f}")
print("  exp(mean log)-1", np.expm1(e.mean()), " median |err|", np.median(abs(err)), "p90", np.percentile(abs(err), 90))
# shares w/o ep29, robustness
for drop in (["ep29"], ["ep29", "ep05"]):
    m = np.array([n not in drop for n in E]); x = e[m]; ms = np.mean(x**2)
    print(f"  drop {drop}: n {m.sum()} mean {x.mean():+.4f} sd {x.std():.4f} rms {np.sqrt(ms):.4f} bias share {x.mean()**2/ms:.3f}")
# bootstrap of bias share
rng = np.random.default_rng(1)
bs = []
for _ in range(10000):
    x = rng.choice(e, len(e)); bs.append(x.mean()**2 / np.mean(x**2))
print("  bias share bootstrap 90% CI", np.percentile(bs, [5, 95]), " SE of mean log", e.std(ddof=1)/np.sqrt(len(e)))

# C3
T19 = [n for n in E if rows[n]["tile_keyframes"] >= 5]
kneed = {n: v["eps"][n]["s_o"] / v["eps"][n]["R"] for n in E}
print("\nC3 tile subset n", len(T19))
print("  median own k: all30", np.median([v["eps"][n]["k"] for n in v["eps"]]), "28", np.median([v["eps"][n]["k"] for n in E]), "19", np.median([v["eps"][n]["k"] for n in T19]))
print("  median k_tile: 19", np.median([v["eps"][n]["k_tile"] for n in T19]), " all with tile_kf>=1 (", sum(v["eps"][n]["k_tile"] is not None for n in E), ")", np.median([v["eps"][n]["k_tile"] for n in E if v["eps"][n]["k_tile"] is not None]))
print("  median k_need: 28", np.median(list(kneed.values())), " 19", np.median([kneed[n] for n in T19]), " geo-mean 28", np.exp(np.mean(np.log(list(kneed.values())))))
lt = np.log([v["eps"][n]["k_tile"] for n in T19]); lk = np.log([v["eps"][n]["k"] for n in T19]); ln = np.log([kneed[n] for n in T19])
dd = lt - lk
print(f"  paired log(k_tile/k_ball) on 19: mean {dd.mean():+.4f} median {np.median(dd):+.4f} sd {dd.std(ddof=1):.4f} t {dd.mean()/(dd.std(ddof=1)/np.sqrt(19)):.2f} pos {np.sum(dd>0)}/19 wilcoxon p {SS.wilcoxon(dd).pvalue:.4f}")
dd2 = lt - np.log(ks)
print(f"  log(k_tile/ks) on 19: mean {dd2.mean():+.4f} median {np.median(dd2):+.4f} pos {np.sum(dd2>0)}/19; t {dd2.mean()/(dd2.std(ddof=1)/np.sqrt(19)):.2f}")
b19 = ln - np.log(ks); r19 = ln - lt
print(f"  bias on 19: mean b {b19.mean():+.4f} = t {dd2.mean():+.4f} + r {r19.mean():+.4f}; 9 low-tile mean b {np.mean([np.log(kneed[n]/ks) for n in E if n not in T19]):+.4f}")
bz = [v["eps"][n]["ball_z_med"] for n in v["eps"]]; bg = [v["eps"][n]["bg_med"] for n in v["eps"]]; tz = [v["eps"][n]["table_z_med"] for n in v["eps"] if v["eps"][n]["table_z_med"]]
print(f"  ball z median per ep: {min(bz):.2f}-{max(bz):.2f} (samples min {min(v['eps'][n]['ball_z_min'] for n in v['eps']):.2f} max {max(v['eps'][n]['ball_z_max'] for n in v['eps']):.2f}); bg (ks-corrected) median {min(bg):.2f}-{max(bg):.2f} median {np.median(bg):.2f}; table true depth {min(tz):.2f}-{max(tz):.2f} median {np.median(tz):.2f}")
# within-episode: does ball depth predict k? (compression with distance)
zb = np.array([v["eps"][n]["ball_z_med"] for n in v["eps"]]); kk = np.array([v["eps"][n]["k"] for n in v["eps"]])
print(f"  corr(ball z, log k) over 30: {np.corrcoef(zb, np.log(kk))[0,1]:+.2f}")
tzz = np.array([v["eps"][n]["table_z_med"] for n in T19])
print(f"  corr(table z, log k_tile) 19: {np.corrcoef(tzz, lt)[0,1]:+.2f}")

# C4
print("\nC4 debias")
def st(x): x = 100 * np.abs(x); return f"med {np.median(x):.2f} p90 {np.percentile(x,90):.2f} rms {np.sqrt(np.mean(x**2)):.2f} max {x.max():.2f}"
print("  as is       ", st(err))
print("  in-sample mean-log   ", st(np.expm1(e - e.mean())))
print("  in-sample median-log ", st(np.expm1(e - np.median(e))))
loo = np.array([e[i] - np.delete(e, i).mean() for i in range(len(e))])
loo_m = np.array([e[i] - np.median(np.delete(e, i)) for i in range(len(e))])
print("  LOO mean-log         ", st(np.expm1(loo)))
print("  LOO median-log       ", st(np.expm1(loo_m)))
lt19 = np.array([e[E.index(n)] for n in T19])
other = np.array([e[i] for i, n in enumerate(E) if n not in T19])
print("  calibrate on 19 tile eps, apply to 28:", st(np.expm1(e - lt19.mean())), " factor", np.exp(-lt19.mean()))
# 2-fold random splits
rs = np.random.default_rng(2); meds, p90s = [], []
for _ in range(2000):
    p = rs.permutation(len(e)); a, b = p[:14], p[14:]
    x = np.concatenate([e[a] - e[b].mean(), e[b] - e[a].mean()]); meds.append(np.median(abs(np.expm1(x)))); p90s.append(np.percentile(abs(np.expm1(x)), 90))
print(f"  2-fold split (calib on 14, test 14): median |err| {100*np.median(meds):.2f} (5-95 {100*np.percentile(meds,5):.1f}-{100*np.percentile(meds,95):.1f}), p90 {100*np.median(p90s):.2f}")

# C5
print("\nC5 n", len(T19), T19)
print(f"  sd log k_tile {lt.std():.4f} (ddof1 {lt.std(ddof=1):.4f}); sd log k_need {ln.std():.4f}; sd log k_ball {lk.std():.4f}")
c_tn = np.corrcoef(lt, ln)[0, 1]; c_tk = np.corrcoef(lt, lk)[0, 1]; c_kn = np.corrcoef(lk, ln)[0,1]
print(f"  corr(lt,ln) {c_tn:.3f} spearman {SS.spearmanr(lt, ln)[0]:.3f}; corr(lt,lk) {c_tk:.3f} spearman {SS.spearmanr(lt, lk)[0]:.3f}; corr(lk,ln) {c_kn:.3f}")
sl = np.polyfit(lt, ln, 1)[0]; print(f"  slope ln on lt {sl:.3f}, R2 {c_tn**2:.3f}; var(ln) {ln.var():.5f} var(ln-lt) {(ln-lt).var():.5f}, resid var after regression {ln.var()*(1-c_tn**2):.5f}")
def fisher(r, n): z = np.arctanh(r); s = 1/np.sqrt(n-3); return np.tanh([z-1.645*s, z+1.645*s])
print("  90% CI tile-need", fisher(c_tn, 19), " tile-ball", fisher(c_tk, 19))
def dropk(a, b, k):
    vals = [np.corrcoef(np.delete(a, list(c)), np.delete(b, list(c)))[0, 1] for c in itertools.combinations(range(len(a)), k)]
    return min(vals), max(vals)
for k in (1, 2):
    print(f"  drop-{k}: tile-need {dropk(lt, ln, k)}, tile-ball {dropk(lt, lk, k)}")
i_t = np.argmin([np.corrcoef(np.delete(lt, i), np.delete(ln, i))[0,1] for i in range(19)]); print("   most influential for tile-need:", T19[i_t])
i_t = np.argmax([np.corrcoef(np.delete(lt, i), np.delete(lk, i))[0,1] for i in range(19)]); print("   most raising tile-ball:", T19[i_t], [ (T19[i], round(np.corrcoef(np.delete(lt, i), np.delete(lk, i))[0,1],2)) for i in range(19)])
# k_tile on all episodes with tile_kf>=1
A = [n for n in E if v["eps"][n]["k_tile"] is not None]
la = np.log([v["eps"][n]["k_tile"] for n in A]); lna = np.log([kneed[n] for n in A]); lka = np.log([v["eps"][n]["k"] for n in A])
print(f"  with tile_kf>=1 n={len(A)}: corr tile-need {np.corrcoef(la, lna)[0,1]:.3f}, tile-ball {np.corrcoef(la, lka)[0,1]:.3f}")

# C6
print("\nC6")
low = [n for n in E if rows[n]["tile_keyframes"] < 5]
print("  low group", low, len(low))
dev = (e - e.mean()) ** 2
m = np.array([n in low for n in E])
print(f"  share of sum sq dev from low group: {dev[m].sum()/dev.sum():.3f}; mean log err low {e[m].mean():+.4f} high {e[~m].mean():+.4f}; var low {e[m].var():.5f} high {e[~m].var():.5f}")
within = (m.sum()*e[m].var() + (~m).sum()*e[~m].var()) / len(e); between = e.var() - within
print(f"  total var {e.var():.5f} = within {within:.5f} + between {between:.5f} ({between/e.var():.2f})")
for drop in ("ep29",):
    mm = np.array([n != drop for n in E]); ee = e[mm]; ll = m[mm]; dv = (ee-ee.mean())**2
    print(f"  without {drop}: low share {dv[ll].sum()/dv.sum():.3f}")
print("  share of sum-sq (incl bias) from low:", (e[m]**2).sum()/(e**2).sum())
# random 9-episode groups: expected share 9/28=0.32
print("  per-ep sq dev low:", {n: round(float(dev[E.index(n)]/dev.sum()),3) for n in low})
# thirds stability per group
def thirds_sd(n):
    th = [x["oracle"] for x in rows[n]["oracle_thirds"] if x["strict_frames"] >= 20 and x["oracle"] and np.isfinite(x["oracle"])]
    return (np.std(np.log(th)), len(th)) if len(th) >= 2 else (None, len(th))
for grp, name in ((low, "low"), ([n for n in E if n not in low], "high")):
    t = [(n, thirds_sd(n)) for n in grp]
    vals = [x[0] for _, x in t if x[0] is not None]
    print(f"  {name}: thirds evaluable {len(vals)}/{len(grp)}, sd log thirds median {np.median(vals) if vals else None}, values { {n: (round(x[0],3) if x[0] is not None else None, x[1]) for n, x in t} }")
    print(f"     oracle align res mm median {np.median([rows[n]['oracle_align_res_mm'] for n in grp]):.2f}")
print("  ep20 thirds", rows["ep20"]["oracle_thirds"]); print("  ep29 thirds", rows["ep29"]["oracle_thirds"])
# strict frame counts per group
print("  strict frames per ep:", {n: sum(x["strict_frames"] for x in rows[n]["oracle_thirds"]) for n in E})

# C7
kk = np.array([v["eps"][n]["k"] for n in sorted(v["eps"])])
for seed in (0, 1, 2):
    r = np.random.default_rng(seed); bsm = np.array([np.median(r.choice(kk, 30)) for _ in range(20000)])
    print(f"\nC7 seed {seed}: sd {bsm.std()/ks:.4f}, 90% CI {np.percentile(bsm,5)/ks-1:+.4f} {np.percentile(bsm,95)/ks-1:+.4f}")
lkk = np.log(kk); print(f"  sd log k over 30 {lkk.std(ddof=1):.4f}; asymptotic sd of median 1.2533*sd/sqrt(30) = {1.2533*lkk.std(ddof=1)/np.sqrt(30):.4f}; SE of mean log k_need (28) {np.log(list(kneed.values())).std(ddof=1)/np.sqrt(28):.4f}")
