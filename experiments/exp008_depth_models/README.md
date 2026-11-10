# exp008_depth_models

**What.** The depth + ball scale (Bsession, the current default) with metric depth networks that can
take the camera intrinsics, against DA2 (exp007). Everything upstream is exp007's, unchanged
(cache hits): `sam3_v2` motion masks, tile masks, DROID-SLAM E3.

| depth node | network | how our K enters | weights (revision) |
|---|---|---|---|
| `da2` | Depth Anything V2 Metric Indoor Large | not at all (baseline, = exp007) | `depth-anything/Depth-Anything-V2-Metric-Indoor-Large-hf` @ d2fc6a9 |
| `uniK` | UniDepth V2 ViT-L | K -> ray embedding that conditions the depth decoder | `lpiccinelli/unidepth-v2-vitl14` @ 52b349b |
| `uni` | UniDepth V2 ViT-L | none: its own camera estimate (K ablation) | same |
| `m3d` | Metric3D v2 ViT-L | canonical camera: depth x fx_resized / 1000 | `JUGGHM/Metric3D` `metric_depth_vit_large_800k.pth` @ 80d2d14 |
| `da3m` | Depth Anything 3 metric (DA3METRIC-LARGE) | depth x f_proc / 300 (f at the 504 px processing resolution) | `depth-anything/DA3METRIC-LARGE` @ 4010e39 |
| `moge` | MoGe-2 ViT-L (normal) | fov_x fixes the focal of the depth recovery; the metric scale head sees the image only | `Ruicheng/moge-2-vitl-normal` @ cb0e8bb |
| `dproK` | Depth Pro | depth = fx / (canonical inverse depth x W) with K's fx | `apple/DepthPro-hf` @ de816c8 |
| `dpro` | Depth Pro | the same with its own FOV head (legacy `B:depth-pro`; K ablation) | same |

Wrappers: `slam/depth_models.py` (one loader per family), framework implementations in
`slam/pipeline/impl_depth_models.py` (registry: `unidepth_v2`, `metric3d_v2`, `da3_metric`, `moge2`,
`depth_pro_f`).

The framework has one primary scale per SLAM run, so E3 is declared once per depth model
(`E3_<node>`). The aliases have identical parameters, hence the same cache key and the same
trajectory. Per alias:
- primary `Bsession` (exp005/exp007 parameters);
- checks `B` (per-episode ball correction) and the new `Bnet`: the network's metric depth as is,
  k = 1, no ball, on B's background cells. Flags at 10% are informational only and are ignored
  here;
- labels and evaluation with the primary.

**Why.** exp007's error sources: the Bsession error is about half a bias (about -7%: DA2's
correction grows with distance, and the ball is nearer than the background) and half an
episode-to-episode spread (sd about 9%, 6.5% on the 22 well-tiled episodes), which follows DA2's
metric scale on the background. DA2 does not take the intrinsics.

Expectations from the research (2026-11-09) and a 4-frame smoke test on ep10:
- DA2 over-estimates depth about 1.77x. Only about 4% of that can come from the field of view: at DA2's
  input size (518x924) our focal is 577 px against Hypersim's ~598 px. The rest is domain (close-range
  tabletop).
- The camera is fixed, so a constant FOV error is absorbed by the ball. What K can remove is the
  per-image focal guess of a network that estimates its own camera (UniDepth without K guessed
  578-708 px on the 4 frames; true 598).
- The models that use K for the scale: UniDepth V2, Metric3D v2, DA3 metric, Depth Pro (with K).
  MoGe-2's scale is image-only.
- Smoke test, true / network depth on tile cells (4 ep10 keyframes):
  - DA2 0.56-0.59;
  - UniDepth K 0.90-0.98, without K 0.84-0.98;
  - Metric3D 0.91-0.98;
  - DA3 metric 0.96-1.11;
  - MoGe-2 0.79-0.96;
  - Depth Pro K 0.81-0.93, own FOV 0.80-0.92.

What is measured:
1. Scale error vs the tile oracle per network × {Bsession, B, Bnet}: |err| median / p90, bias,
   spread. Reported on all 28 episodes and on the 22 with at least 3 tile-visible keyframes (as in
   exp007, `exp007_v2_session_scale/error_sources/tile_keyframes.json`).
2. Tool labels at 1 s / 2 s / chunk with each network's Bsession.
3. Without SLAM: network depth against the true table depth on tile cells (post-hoc,
   `table_depth.py`): raw bias, episode-to-episode spread and dependence on distance. This is the
   direct test of a "steadier metric scale".

```
V=/home/student/yuanliu-hawaii/.venv-headcam/bin/python
$V -m slam.run experiments/exp008_depth_models/config.yaml
```

## Environment `mdepth` (conda)

Built 2026-11-09 for UniDepth V2, Metric3D v2, DA3 and MoGe-2 (Depth Pro runs in `sam2`, transformers):

```
conda create -n mdepth python=3.11
pip install torch==2.7.1 torchvision==0.22.1 xformers==0.0.31.post1 --index-url https://download.pytorch.org/whl/cu126
cd /home/student/yuanliu-hawaii/third_party      # UniDepth @ 8d8cfe4, Metric3D @ eb5b6fa, MoGe @ 74fbce0, Depth-Anything-3 @ 3d835ec
pip install --no-deps -e UniDepth -e Depth-Anything-3 -e MoGe
pip install "numpy>=2,<2.3" einops huggingface-hub safetensors timm opencv-python-headless pillow scipy tqdm \
    omegaconf imageio mmengine transformers==4.57.1 wandb moviepy==1.0.3 trimesh plyfile pycolmap evo \
    "git+https://github.com/EasternJournalist/utils3d-moge.git@62f09d58509485564e24d5d9f6aac9ee9ebc0c37"
```

- `--no-deps`: DA3 pins numpy < 2 and MoGe's current release (MoGe-3) pulls a compiled extension
  (FlexGEMM). Neither is needed for inference of the models used here.
- Metric3D is loaded from the checkout (hubconf.py), with one local patch:
  `third_party_patches/Metric3D/`. Its old `xformers.components` API is missing in this xformers,
  so it uses plain attention.
- The exact package versions are in `run.json`.

## Results

The run took 20.2 min: 7 depth nodes (about 1-3 min each), then the analysis of 8 aliases. Run at
b113213. run.json records a change during the run: `compare.py` (post-hoc, untracked, not executed
by the run) was written meanwhile.

The DA2 alias reproduces exp007 exactly: Bsession |err| median 7.84%, labels 4.5 / 15.0 mm at 1 s.
Full tables are in [`compare.md`](compare.md) (`compare.py`, read only on the run's results and
view).

**Scale error vs the tile oracle, 22 episodes with >= 3 tile-visible keyframes** (|err| median /
p90, bias = signed median, spread = sd of log(1 + err); Bsession and Bnet differ only by the
constant k_session, so they share the spread):

| network | Bsession (ball, pooled) | Bnet (no ball) | spread | k_session |
|---|---|---|---|---|
| DA2 metric indoor (exp007) | 6.9 / 11.4%, -5.5% | 66.9 / 77.3%, +66.9% | 6.6% | 0.566 |
| **DA3 metric + K** | 17.6 / 21.0%, -17.6% | **3.1 / 6.9%, +0.8%** | **4.9%** | 0.817 |
| MoGe-2 (fov from K) | 18.8 / 24.4%, -18.8% | 4.2 / 10.2%, +3.2% | 6.2% | 0.787 |
| Metric3D v2 + K | 6.7 / 11.4%, -6.2% | 9.0 / 13.9%, +9.0% | 5.3% | 0.861 |
| UniDepth V2 + K | 9.4 / 12.6%, -9.4% | 6.5 / 16.1%, +6.5% | 5.6% | 0.851 |
| UniDepth V2, own camera | 8.8 / 11.9%, -8.6% | 4.6 / 16.3%, +4.6% | 6.1% | 0.873 |
| Depth Pro + K | 14.6 / 23.1%, -14.6% | 10.2 / 19.5%, +10.2% | 7.5% | 0.775 |
| Depth Pro, own FOV | 15.8 / 22.9%, -15.8% | 16.8 / 26.1%, +16.8% | 9.0% | 0.722 |

On all 28 episodes: DA3 + K with Bnet gives 3.1 / 9.4% and bias -0.1%, against 7.8 / 17.4% for
exp007's default.

**Without SLAM: true / network depth on tile cells** (keyframes with a strict tile pose; 1 = metric):

| network | pooled median | spread over episodes (sd log, 22) | log-log slope vs depth | at 0.35-0.55 / 0.9-1.2 m |
|---|---|---|---|---|
| DA2 | 0.586 | 10.4% | +0.35 | 0.44 / 0.64 |
| DA3 metric + K | 0.957 | 7.5% | +0.28 | 0.97 / 1.02 |
| MoGe-2 | 0.919 | 8.4% | +0.28 | 0.74 / 0.95 |
| Metric3D v2 + K | 0.918 | 5.7% | +0.26 | 0.76 / 0.97 |
| UniDepth V2 + K | 0.925 | 3.2% | +0.07 | 0.85 / 0.95 |
| Depth Pro + K | 0.905 | 8.3% | +0.01 | 0.87 / 0.91 |

**Focal estimated by the networks themselves** (fx of K = 598.3 px):
- UniDepth: median 576, p10-p90 548-639, sd 6.9%.
- Depth Pro's FOV head: median 647, p10-p90 562-749, sd 11.6%.

**Labels with Bsession** (the primary here), 1 s median / p90:
- DA2 4.5 / 15.0 mm; Metric3D 4.6 / 15.8; UniDepth + K 4.9 / 18.6;
- Depth Pro + K 5.7 / 22.9; MoGe-2 6.4 / 26.6; DA3 6.6 / 25.9.
- The labels with Bnet are in exp009.

**Reading.**
- **The best scale is DA3 metric + K used as is, without the ball.** |err| 3.1% median, 6.9% p90,
  bias about 0 (22 episodes). It needs no marker, which suits in-the-wild data.
- **The ball over-corrects every new network.** k_session is 0.72-0.87, below what the episodes
  needed (k_need median 0.86-0.99) and below the networks' ratio on the table (0.86-0.96). They
  over-estimate the depth of the small hand-held ball relative to the surfaces. DA3, for example,
  reads 0.97 on the table at 0.35-0.55 m but 0.82 on the ball. Bsession therefore turns a small
  positive bias into a larger negative one (-6 to -19%).
  - For DA3, MoGe-2, UniDepth and Depth Pro + K, Bnet beats Bsession on the median.
  - For Metric3D it is the other way round (6.7% vs 9.0%); Depth Pro without K is about equal.
  - The ball is not a reliable depth reference for these networks. It was not one for DA2 either
    (exp007: the ball sits about 10% off the table's curve); with DA2 the two biases partly
    cancelled.
- **The episode-to-episode spread improves only moderately**: 6.6% (DA2) to 4.9% (DA3). This is
  what no constant correction can remove.
- **Intrinsics help where the network's own focal estimate is poor.**
  - Depth Pro: with K, the spread drops from 9.0 to 7.5% and the Bnet bias from +16.8 to +10.2%.
  - UniDepth, whose own estimate is closer: K changes little (scale spread 6.1 to 5.6%, table
    spread 3.6 to 3.2% on the 22 episodes).
  - Taking K is not enough on its own: DA3 and MoGe-2 beat UniDepth and Depth Pro on the scale.
- **DA2's distance dependence explains exp007's bias.** Its slope is +0.35, from 0.44 at 0.45 m to
  0.70 at 1.4 m. The new networks are flatter: UniDepth +0.07, Depth Pro +0.01, the others about
  +0.27.
- **The table check and the scale rank the networks differently.** UniDepth is the most consistent
  on the tiles (spread 3.2%), yet its Bnet scale is biased by +6.5%. R uses the whole background
  (table, walls, objects) against DROID's depth, while tile cells are table cells at about 0.85 m.
