# exp007_v2_session_scale

**What.** The current defaults (decisions of 2026-11-09, `experiments/README.md`) on yam_glove7:
- the producers are exp006's, unchanged (cache hits): `sam3_v2` motion masks, tile masks, masked
  DROID-SLAM E3 and its DA2 keyframe depth;
- scale primary `Bsession` with the A cross-check, using exp005's parameters;
- labels, evaluation and the exp004 error decomposition on E3;
- the report compares with exp005 (Bsession on the first SAM3 masks) and exp006 (B on the same masks).

It is an analysis-only run. E1 is in the config only because the tile masks depend on it (their
fallback run).

**Why.** exp006 measured the v2 masks with scale B. exp005 measured Bsession only on the first SAM3
masks (exp003). This experiment gives the baseline of the configuration now in use, against which
later SLAM backends (AMB3R) are compared.

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp007_v2_session_scale/config.yaml
```

## Results

(filled in after the run)
