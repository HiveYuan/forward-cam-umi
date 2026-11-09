# exp003_droid_sam3

**What.** exp001 with exp002's SAM3 motion masks: masked DROID-SLAM
- E1: no masks; identical to exp001, from the cache; only used to fill the tile masks;
- E2: motion masks;
- E3: motion + tile masks, the main setting.

Scale B with an A cross-check (|A/B − 1| > 10% flags a segment). Labels and evaluation as in
exp001. Compared side by side with exp000_legacy and exp001_sam2_baseline (same framework, SAM2
masks).

**Why.** Step 3 of the plan (due 11-11): switch the masks to SAM3 and rerun DROID before treating
the mask module as fixed. If SAM3 is clearly worse, find the cause first.

**Reported metrics:**
- head rotation and translation error vs Δt (0.08 / 0.5 / 1 / 2 / 6.67 s);
- tracking failure rate;
- scale error vs the tile oracle (coverage, median, p90, bias, flagged segments);
- tool label position and rotation error vs Δt (0.07–6.67 s);
- mean label error per chunk length H = 15 / 30 / 50 / 100.

```
HF_TOKEN_PATH=~/.config/yuanliu/hf_token $V -m slam.run experiments/exp003_droid_sam3/config.yaml
```

**Result (2026-11-08, commit 3e1c086, 105 min).** With the SAM3 masks, DROID is at least as good
as with SAM2 (exp001; E2 compared with exp000):

| E3 | SAM3 (exp003) | SAM2 (exp001) |
|---|---|---|
| head rotation median, 1 s / 2 s / 6.67 s | 0.52° / 0.64° / 0.73° | 0.53° / 0.59° / 0.62° |
| head rotation p95, 1 s | 2.17° | 2.32° |
| tracking failure | 0.21% | 0.34% |
| B+Acheck scale median / p90 | 5.4% / 20.1% | 5.8% / 21.4% |
| label position at 1 s, B scale | 5.7 mm | 5.9 mm |
| chunk mean, H = 15 / 30 / 50 / 100, B scale | 5.5 / 7.9 / 9.5 / 10.9 mm | 5.7 / 8.3 / 10.2 / 11.9 mm |

E2 (motion masks only) matches exp000's SAM2 E2 within 0.02°; its tracking failure is 0.00%
(SAM2 0.04%).
