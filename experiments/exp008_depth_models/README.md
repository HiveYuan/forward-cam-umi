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
