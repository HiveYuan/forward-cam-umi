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
