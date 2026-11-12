"""Step implementations: metadata only (no heavy imports), so the orchestrator can plan
without torch. The function named in `func` is imported by the worker inside `env`.

Every implementation lists ALL its parameters with their defaults in `params`; a config
must give every one of them (spec.normalize_params rejects missing and unknown keys), so
an experiment's config.yaml is the complete description of what ran.

What else enters an implementation's cache key (orchestrator.Runner.fingerprints):
  code_files     repo-relative Python files it executes, hashed as their syntax tree without
                 comments and docstrings (hashing.source_hash): a code change recomputes,
                 a comment or formatting change does not
  binaries       absolute glob patterns of compiled extensions / installed sources, byte-hashed
  code_inputs    git checkouts (third-party code with local patches), commit + diff contents
  env_packages   package versions in the impl's environment (candidates; absent ones skipped)
                 plus that environment's Python version
  tools          external programs (e.g. ffmpeg), by their version line
  version        bump by hand for an output change none of the above captures
`choices` restricts parameter values (checked when the config is loaded).
"""
from dataclasses import dataclass, field

PRODUCER_STEPS = ("preprocess", "tiles", "masks", "slam", "depth")
ANALYSIS_STEPS = ("mask_compare", "scale", "labels", "evaluate", "error_decomp", "report")

DROID_ROOT = "/home/student/yuanliu-hawaii/third_party/DROID-SLAM"


@dataclass(frozen=True)
class Impl:
    step: str
    name: str
    env: str                       # key of envs.ENVS
    func: str                      # "module:function", called as func(job) in the worker
    params: dict                   # every parameter with its default
    version: int = 1
    gpu_gb: float = 0.0            # free GPU memory required before it starts (0 = CPU only)
    per_segment_process: bool = False   # one worker process per segment (clean GPU state)
    data_inputs: tuple = ()        # spec.DATA_FILES names whose fingerprints enter the key
    code_inputs: tuple = ()        # git checkouts whose state enters the key
    doc: str = ""
    exec_params: dict = field(default_factory=dict)   # execution-only knobs, not hashed
    code_files: tuple = ()         # repo-relative .py files run by this impl (AST-hashed)
    binaries: tuple = ()           # absolute glob patterns, byte-hashed
    env_packages: tuple = ()       # distribution names whose versions enter the key
    tools: tuple = ()              # external programs whose version enters the key
    choices: dict = field(default_factory=dict)       # param -> allowed values


CONDA_ENVS = "/home/student/miniconda3/envs"
CV_PKGS = ("numpy", "opencv-python", "opencv-python-headless", "opencv-contrib-python")
TORCH_PKGS = ("torch", "transformers", "safetensors") + CV_PKGS
THIRD_PARTY = "/home/student/yuanliu-hawaii/third_party"
MDEPTH_PKGS = ("torch", "torchvision", "xformers", "numpy", "timm", "einops", "huggingface-hub",
               "safetensors") + CV_PKGS


_IMPLS = [
    # ------------------------------------------------------------------ preprocess
    Impl("preprocess", "undistort_crop", "venv", "slam.pipeline.impl_preprocess:run_preprocess",
         {"preroll_s": 5.0, "width": 960, "alpha": 0.0, "jpg_quality": 95},
         data_inputs=("video", "video_ts", "episodes", "intrinsics", "gt_cam_world", "gt_ball_poses"),
         exec_params={"jobs": 8},
         code_files=("slam/preprocess.py", "slam/pipeline/impl_preprocess.py"),
         env_packages=CV_PKGS, tools=("ffmpeg",),
         doc="slam.preprocess: [episode start - preroll, episode end], undistort (alpha), "
             "area-resize to width, centre-crop to a multiple of 8; gt.npz slices of the tile and ball poses"),
    # ------------------------------------------------------------------ tiles
    Impl("tiles", "apriltag_36h11", "venv", "slam.pipeline.impl_tiles:run_tile_detect",
         {"detect_scale": 0.5, "subpix_win": 5},
         data_inputs=("video", "video_ts", "intrinsics", "tile_layout", "tags"),
         exec_params={"jobs": 8},
         code_files=("slam/tiles.py", "slam/pipeline/impl_tiles.py", "slam/preprocess.py", "slam/geometry.py"),
         env_packages=CV_PKGS, tools=("ffmpeg",),
         doc="slam.tiles detect: 36h11 workspace tiles on the raw frames of each segment"),
    # ------------------------------------------------------------------ masks
    Impl("masks", "sam2_points", "sam2", "slam.pipeline.impl_masks:run_sam2_points",
         {"model": "facebook/sam2.1-hiera-large",
          "revision": "665f8e2ad61cf5f53d65644ff27c8ee525124610",
          "dtype": "bfloat16", "prompt_every": 30,
          "prompts": {"glove": ["ball", "flange"], "hand": [[-0.141, -0.0026, 0.1014]]}},
         gpu_gb=12.0, data_inputs=("handeye",),
         code_files=("slam/masks.py", "slam/pipeline/impl_masks.py", "slam/geometry.py"),
         env_packages=TORCH_PKGS, choices={"dtype": ("bfloat16", "float16", "float32")},
         doc="slam.masks: SAM2 video propagation from body-frame points projected with the ball pose"),
    Impl("masks", "sam3_text_points", "sam3", "slam.pipeline.impl_masks_sam3:run_sam3_text_points",
         {"model": "facebook/sam3", "revision": "3c879f39826c281e95690f02c7821c4de09afae7",
          "dtype": "bfloat16", "text_prompts": ["hand", "arm", "cable"],
          "point_prompts": {"glove": ["ball", "flange"]}, "prompt_every": 30, "require_postprocess": True},
         gpu_gb=12.0, data_inputs=("handeye",),
         code_files=("slam/masks_sam3.py", "slam/masks.py", "slam/pipeline/impl_masks_sam3.py",
                     "slam/pipeline/impl_masks.py", "slam/geometry.py"),
         binaries=("/home/student/.cache/huggingface/hub/kernels--kernels-community--cv-utils/snapshots/*/build/"
                   "*-x86_64-linux/*.so",),
         env_packages=TORCH_PKGS + ("kernels",), choices={"dtype": ("bfloat16", "float16", "float32")},
         doc="slam.masks_sam3: SAM3 text prompts (body parts) + SAM3 tracker points from the ball pose "
             "(rig, held object), union"),
    Impl("masks", "sam3_v2", "sam3", "slam.pipeline.impl_masks_sam3v2:run_sam3_v2",
         {"model": "facebook/sam3", "revision": "3c879f39826c281e95690f02c7821c4de09afae7",
          "dtype": "bfloat16", "text_prompts": ["hand", "arm", "cable"], "seed_prompts": ["hand", "arm"],
          "attach_px": 8, "border_px": -1, "leak_ratio": 3.0, "split_components": True,
          "rig_points": ["ball", [-0.0852, -0.0324, 0.0655], [-0.0623, -0.0177, 0.1004], [-0.0865, -0.0568, 0.0937]],
          "rig_negative_points": [],
          "hand_points": [[-0.141, -0.0026, 0.1014], [-0.141, 0.0574, 0.1314]],
          "held_points": [[-0.0943, -0.1071, 0.0855]], "held_width_max": 0.45, "held_after_open": True,
          "width_tol_s": 0.12,
          "prompt_every": 10, "require_postprocess": True},
         gpu_gb=14.0, data_inputs=("handeye", "gt_gripper_wrist"),
         code_files=("slam/masks_sam3v2.py", "slam/masks_sam3.py", "slam/masks.py",
                     "slam/pipeline/impl_masks_sam3v2.py", "slam/pipeline/impl_masks.py", "slam/geometry.py"),
         binaries=("/home/student/.cache/huggingface/hub/kernels--kernels-community--cv-utils/snapshots/*/build/"
                   "*-x86_64-linux/*.so",),
         env_packages=TORCH_PKGS + ("kernels",), choices={"dtype": ("bfloat16", "float16", "float32")},
         doc="slam.masks_sam3v2: SAM3 text instances minus masklet leaks (area > leak_ratio x the masklet's lower "
             "quartile), kept only if attached to the wearer (tracked rig / hand / held object; plus border-touching "
             "seed prompts when border_px >= 0); SAM3 tracker for rig, hand and held object "
             "(fingertip point while the gripper width <= held_width_max), every prompt_every frames"),
    Impl("masks", "tile_geometry", "venv", "slam.pipeline.impl_tiles:run_tile_geometry",
         {"margin_mm": 10.0, "max_gap_s": 0.5, "grow_mm_per_s": 100.0, "slam_fallback": None,
          "slam_margin_mm": 25.0},
         data_inputs=("tile_layout", "tags"),
         code_files=("slam/tiles.py", "slam/pipeline/impl_tiles.py", "slam/preprocess.py", "slam/geometry.py"),
         env_packages=CV_PKGS,
         doc="slam.tiles masks: printed tile squares projected with the tile pose (nearest pose, "
             "else the slam_fallback run aligned to the tile poses) + detected quads"),
    # ------------------------------------------------------------------ slam
    Impl("slam", "droid", "droid", "slam.pipeline.impl_slam:run_slam",
         {"weights": {"path": f"{DROID_ROOT}/droid.pth",
                      "sha256": "46476ef64cde45a97504910d6f3de2eef7b398ec1c6e4e668815c29076024526"},
          "dilate_px": 8, "buffer": 0, "beta": 0.3, "filter_thresh": 2.4, "warmup": 8,
          "keyframe_thresh": 4.0, "frontend_thresh": 16.0, "frontend_window": 25,
          "frontend_radius": 2, "frontend_nms": 1, "backend_thresh": 22.0, "backend_radius": 2,
          "backend_nms": 3, "seed": 0},
         gpu_gb=18.0, per_segment_process=True, code_inputs=(DROID_ROOT,),
         code_files=("slam/backends/droid.py", "slam/backends/base.py", "slam/droid_masked.py",
                     "slam/pipeline/impl_slam.py"),
         binaries=(f"{DROID_ROOT}/*.so", f"{CONDA_ENVS}/droid/lib/python3.10/site-packages/lietorch*.so",
                   f"{CONDA_ENVS}/droid/lib/python3.10/site-packages/lietorch/*.py"),
         env_packages=("torch", "lietorch", "droid_backends", "torch_scatter") + CV_PKGS,
         doc="slam.backends.droid: masked DROID-SLAM (BA weights x valid(src) x valid(matched), "
             "masked keyframe selection), global BA at the end"),
    Impl("slam", "droid_preroll", "droid", "slam.pipeline.impl_slam_preroll:run_slam_preroll",
         {"weights": {"path": f"{DROID_ROOT}/droid.pth",
                      "sha256": "46476ef64cde45a97504910d6f3de2eef7b398ec1c6e4e668815c29076024526"},
          "dilate_px": 8, "buffer": 0, "beta": 0.3, "filter_thresh": 2.4, "warmup": 8,
          "keyframe_thresh": 4.0, "frontend_thresh": 16.0, "frontend_window": 25,
          "frontend_radius": 2, "frontend_nms": 1, "backend_thresh": 22.0, "backend_radius": 2,
          "backend_nms": 3, "seed": 0, "preroll_s": 1.0},
         gpu_gb=18.0, per_segment_process=True, code_inputs=(DROID_ROOT,),
         code_files=("slam/backends/droid.py", "slam/backends/base.py", "slam/droid_masked.py",
                     "slam/pipeline/impl_slam_preroll.py"),
         binaries=(f"{DROID_ROOT}/*.so", f"{CONDA_ENVS}/droid/lib/python3.10/site-packages/lietorch*.so",
                   f"{CONDA_ENVS}/droid/lib/python3.10/site-packages/lietorch/*.py"),
         env_packages=("torch", "lietorch", "droid_backends", "torch_scatter") + CV_PKGS,
         doc="droid on the frames from preroll_s before the episode start only (the segment keeps the 5 s "
             "preroll for frames and masks; earlier frames get no pose): no initialization on pre-episode "
             "head turns (2026-11-11)"),
    Impl("slam", "droid_adaptive", "droid", "slam.pipeline.impl_slam_adaptive:run_slam_adaptive",
         {"weights": {"path": f"{DROID_ROOT}/droid.pth",
                      "sha256": "46476ef64cde45a97504910d6f3de2eef7b398ec1c6e4e668815c29076024526"},
          "dilate_px": 8, "buffer": 0, "beta": 0.3, "filter_thresh": 2.4, "warmup": 8,
          "keyframe_thresh": 4.0, "frontend_thresh": 16.0, "frontend_window": 25,
          "frontend_radius": 2, "frontend_nms": 1, "backend_thresh": 22.0, "backend_radius": 2,
          "backend_nms": 3, "seed": 0, "turn_deg_s": 120.0, "short_preroll_s": 1.0},
         gpu_gb=18.0, per_segment_process=True, code_inputs=(DROID_ROOT,),
         code_files=("slam/backends/droid.py", "slam/backends/base.py", "slam/droid_masked.py",
                     "slam/pipeline/impl_slam_preroll.py", "slam/pipeline/impl_slam_adaptive.py"),
         binaries=(f"{DROID_ROOT}/*.so", f"{CONDA_ENVS}/droid/lib/python3.10/site-packages/lietorch*.so",
                   f"{CONDA_ENVS}/droid/lib/python3.10/site-packages/lietorch/*.py"),
         env_packages=("torch", "lietorch", "droid_backends", "torch_scatter") + CV_PKGS,
         doc="droid from the segment's 5 s preroll; re-run from short_preroll_s before the episode when the "
             "first run turns faster than turn_deg_s before the episode (no initialization on pre-episode "
             "head turns; decision 2026-11-12)"),
    # ------------------------------------------------------------------ depth
    Impl("depth", "hf_depth", "sam2", "slam.pipeline.impl_depth:run_depth",
         {"model": "da2-metric-indoor-large",
          "repo": "depth-anything/Depth-Anything-V2-Metric-Indoor-Large-hf",
          "revision": "d2fc6a93601aabb1139a3bf0ebfcb4e89c67817f"},
         gpu_gb=6.0,
         code_files=("slam/depth.py", "slam/pipeline/impl_depth.py"),
         env_packages=TORCH_PKGS, choices={"model": ("da2-metric-indoor-large", "depth-pro")},
         doc="slam.depth: transformers metric depth on the SLAM run's keyframes (scale method B)"),
    # networks that can take the camera K (slam.depth_models; exp008). `model` is the file label of the
    # output (depth/<run>_<model>.npz in the view), so variants of one network need distinct labels.
    Impl("depth", "unidepth_v2", "mdepth", "slam.pipeline.impl_depth_models:run_depth_model",
         {"model": "unidepth-v2-vitl14", "repo": "lpiccinelli/unidepth-v2-vitl14",
          "revision": "52b349b514bd8b47642f67ac78cb7b5dc5c51dd9", "use_intrinsics": True, "resolution_level": None},
         gpu_gb=6.0, code_inputs=(f"{THIRD_PARTY}/UniDepth",),
         code_files=("slam/depth_models.py", "slam/pipeline/impl_depth_models.py"),
         env_packages=MDEPTH_PKGS,
         doc="UniDepth V2: K -> ray embedding conditioning the depth decoder (use_intrinsics), else its own camera"),
    Impl("depth", "metric3d_v2", "mdepth", "slam.pipeline.impl_depth_models:run_depth_model",
         {"model": "metric3d-v2-vitl", "repo": "JUGGHM/Metric3D",
          "revision": "80d2d1410afb4b23cd9d18c6be9144483d4b70b6",
          "checkpoint": "metric_depth_vit_large_800k.pth", "input_size": [616, 1064]},
         gpu_gb=6.0, code_inputs=(f"{THIRD_PARTY}/Metric3D",),
         code_files=("slam/depth_models.py", "slam/pipeline/impl_depth_models.py"),
         env_packages=MDEPTH_PKGS + ("mmengine",),
         doc="Metric3D v2 (hubconf recipe): canonical camera f = 1000 px, depth * fx_resized / 1000"),
    Impl("depth", "da3_metric", "mdepth", "slam.pipeline.impl_depth_models:run_depth_model",
         {"model": "da3-metric-large", "repo": "depth-anything/DA3METRIC-LARGE",
          "revision": "4010e39f3634a45bc60553321fb49fb760bd594e", "process_res": 504,
          "process_res_method": "upper_bound_resize", "canonical_focal": 300.0},
         gpu_gb=6.0, code_inputs=(f"{THIRD_PARTY}/Depth-Anything-3",),
         code_files=("slam/depth_models.py", "slam/pipeline/impl_depth_models.py"),
         env_packages=MDEPTH_PKGS,
         choices={"process_res_method": ("upper_bound_resize", "lower_bound_resize")},
         doc="DA3METRIC-LARGE: depth * f_proc / 300 with f_proc = mean(fx, fy) of K at the processing resolution"),
    Impl("depth", "moge2", "mdepth", "slam.pipeline.impl_depth_models:run_depth_model",
         {"model": "moge-2-vitl-normal", "repo": "Ruicheng/moge-2-vitl-normal",
          "revision": "cb0e8bbd6b1e243589717c78e750b1ba4c093acf", "use_intrinsics": True,
          "resolution_level": 9, "use_fp16": True},
         gpu_gb=6.0, code_inputs=(f"{THIRD_PARTY}/MoGe",),
         code_files=("slam/depth_models.py", "slam/pipeline/impl_depth_models.py"),
         env_packages=MDEPTH_PKGS + ("utils3d-moge",),
         doc="MoGe-2: fov_x from K fixes the focal of the depth recovery; metric scale from an image-only head"),
    Impl("depth", "depth_pro_f", "sam2", "slam.pipeline.impl_depth_models:run_depth_model",
         {"model": "depth-pro-f", "repo": "apple/DepthPro-hf",
          "revision": "de816c8ce7168afcb231f96d501d72b869d0beda", "use_intrinsics": True},
         gpu_gb=6.0,
         code_files=("slam/depth_models.py", "slam/pipeline/impl_depth_models.py"),
         env_packages=TORCH_PKGS,
         doc="Depth Pro (transformers): metric depth with K's focal (use_intrinsics) or its FOV head's"),
    # ------------------------------------------------------------------ analysis
    Impl("mask_compare", "default", "venv", "slam.pipeline.impl_mask_compare:run_mask_compare",
         {"reference": "", "candidates": [""], "dilate_px": 8, "overlays_per_segment": 4},
         doc="mask sets vs a reference mask set: per-frame IoU, coverage, extra area, DROID-cell "
             "agreement after dilation; overlay images in the run directory"),
    Impl("scale", "default", "venv", "slam.pipeline.impl_analysis:run_scale", {},
         doc="per SLAM run: primary scale method + cross-checks (slam.scale); s is always the primary's"),
    Impl("labels", "default", "venv", "slam.pipeline.impl_analysis:run_labels",
         {"fps": 15.0, "label_tol_s": 0.12, "min_coverage": 0.7, "bridge_s": 0.5,
          "min_episode_s": 1.0, "gripper": "wrist",
          "label_steps": [1, 2, 4, 8, 15, 30, 60, 100], "horizon": 100, "chunk_H": [15, 30, 50, 100]},
         data_inputs=("gt_gripper_wrist",), choices={"gripper": ("wrist", "dataset")},
         doc="slam.labels build/check: tool poses on the build_dataset 15 fps grid; error vs the tile "
             "labels per step (label_steps) and averaged over chunks of length H (chunk_H)"),
    Impl("evaluate", "default", "venv", "slam.pipeline.impl_analysis:run_evaluate",
         {"dts": [0.08, 0.25, 0.5, 1.0, 2.0, 4.0, 6.67], "fail_deg": 2.0, "gt_noise": True},
         doc="slam.evaluate (head motion vs tiles), slam.tiles noise (GT noise floor)"),
    Impl("error_decomp", "default", "venv", "slam.pipeline.impl_error_decomp:run_error_decomp",
         {"label_steps": [1, 2, 4, 8, 15, 30, 60, 100], "horizon": 100, "chunk_H": [15, 30, 50, 100],
          "speed_bins_deg_s": [0.0, 10.0, 30.0], "speed_window_s": 0.5},
         doc="label error with each part of the head motion cam_t->cam_t+dt replaced by the tile GT: "
             "SLAM or tile rotation x configured or tile-oracle scale (what perfect rotation / scale buys)"),
    Impl("report", "default", "venv", "slam.pipeline.impl_report:run_report",
         {"compare": [], "dt_show": [0.08, 0.5, 1.0, 2.0, 6.67]},
         doc="results/metrics.json + report.md, side by side with other experiments"),
]

IMPLS = {(i.step, i.name): i for i in _IMPLS}
assert len(IMPLS) == len(_IMPLS), "duplicate (step, impl)"


def get(step, name):
    try:
        return IMPLS[(step, name)]
    except KeyError:
        known = sorted(n for s, n in IMPLS if s == step)
        raise KeyError(f"unknown implementation {name!r} for step {step!r}; known: {known}") from None


def register(impl):
    """Add an implementation (e.g. from a test or a new backend module)."""
    if (impl.step, impl.name) in IMPLS:
        raise KeyError(f"{impl.step}/{impl.name} already registered")
    IMPLS[(impl.step, impl.name)] = impl
    return impl
