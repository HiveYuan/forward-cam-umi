#!/usr/bin/env python3
"""Monocular metric depth networks that can take the camera intrinsics (exp008).

Each family maps an RGB keyframe (the undistorted SLAM input, 960x536) and its pinhole K to metric
depth [m] at the input resolution. How K enters differs per network, so it is spelled out here:

  unidepth   UniDepth V2 (lpiccinelli-eth/UniDepth). With use_intrinsics, K becomes the per-pixel
             ray embedding that conditions the depth decoder (cross-attention "self-prompting");
             without, the network predicts its own camera. resolution_level None keeps UniDepth's
             default pixel bounds (0.2-0.6 MP): our 0.51 MP frame is used at native size (rounded up
             to a multiple of 14).
  metric3d   Metric3D v2 (YvanYin/Metric3D, hubconf.py recipe): keep-ratio resize into input_size
             (ViT: 616x1064), pad with the ImageNet mean, predict depth in the canonical camera
             (focal 1000 px), unpad, upsample, depth * fx_resized / 1000, clamp [0, 300].
  da3metric  Depth Anything 3 metric (DA3METRIC-LARGE): the network predicts depth for a canonical
             focal of 300 px at its processing resolution; metric depth = net * f_proc / 300 with
             f_proc = mean(fx, fy) of K scaled to the processed image (DA3's apply_metric_scaling).
  moge2      MoGe-2 (microsoft/MoGe, v2 model). With use_intrinsics, fov_x = the horizontal FOV of K
             fixes the focal when the affine-invariant point map is turned into depth (only the
             z-shift is solved); the metric scale itself comes from an image-only head on the CLS
             token, so K does not inform it. apply_mask=False: dense depth (no inf).
  depthpro   Apple Depth Pro (transformers DepthProForDepthEstimation): the network predicts canonical
             inverse depth; metric depth = f / (inverse depth * W). With use_intrinsics, f = fx of K
             (the FOV passed to the post-processing is K's horizontal FOV); without, f comes from
             Depth Pro's FOV head (what the legacy B:depth-pro used).

load(family, params) -> Predictor with .predict(rgb uint8 (H, W, 3), K (3, 3)) -> (depth float32
(H, W) metres, info dict). info["fx_used"] is the focal (pixels of the input image) that set the
scale, info["fx_pred"] the network's own estimate where it has one.

Heavy imports happen inside the loaders (this module is imported by the orchestrator's env).
"""
import math
import sys

import numpy as np

THIRD_PARTY = "/home/student/yuanliu-hawaii/third_party"
ROOTS = {"unidepth": f"{THIRD_PARTY}/UniDepth", "metric3d": f"{THIRD_PARTY}/Metric3D",
         "da3metric": f"{THIRD_PARTY}/Depth-Anything-3", "moge2": f"{THIRD_PARTY}/MoGe"}
FAMILIES = ("unidepth", "metric3d", "da3metric", "moge2", "depthpro")


def hfov_deg(K, W):
    return math.degrees(2 * math.atan(W / (2 * float(K[0][0]))))


class Predictor:
    def __init__(self, fn):
        self.fn = fn

    def predict(self, rgb, K):
        d, info = self.fn(rgb, np.asarray(K, float))
        d = np.asarray(d, np.float32)
        if d.shape != rgb.shape[:2]:
            raise RuntimeError(f"depth shape {d.shape} != image {rgb.shape[:2]}")
        return d, info


# ---------------------------------------------------------------------- loaders
def _unidepth(p):
    import torch
    from unidepth.models import UniDepthV2
    net = UniDepthV2.from_pretrained(p["repo"], revision=p["revision"]).to("cuda").eval()
    if p["resolution_level"] is not None:
        net.resolution_level = int(p["resolution_level"])

    @torch.no_grad()
    def fn(rgb, K):
        x = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1)
        cam = torch.from_numpy(K).float()[None] if p["use_intrinsics"] else None
        out = net.infer(x, cam)
        fx_pred = float(out["intrinsics"][0, 0, 0])
        return out["depth"][0, 0].float().cpu().numpy(), {
            "fx_used": float(K[0, 0]) if p["use_intrinsics"] else fx_pred, "fx_pred": fx_pred}
    return fn


def _metric3d(p):
    import cv2
    import torch
    from huggingface_hub import hf_hub_download
    sys.path.insert(0, ROOTS["metric3d"])
    try:
        from mmcv.utils import Config
    except ImportError:
        from mmengine import Config
    import hubconf
    from mono.model.monodepth_model import get_configured_monodepth_model
    arch = {"metric_depth_vit_large_800k.pth": "ViT-Large", "metric_depth_vit_giant2_800k.pth": "ViT-giant2",
            "metric_depth_vit_small_800k.pth": "ViT-Small"}[p["checkpoint"]]
    net = get_configured_monodepth_model(Config.fromfile(hubconf.MODEL_TYPE[arch]["cfg_file"]))
    ck = hf_hub_download(p["repo"], p["checkpoint"], revision=p["revision"])
    res = net.load_state_dict(torch.load(ck, map_location="cpu", weights_only=False)["model_state_dict"],
                              strict=False)
    missing = [k for k in res.missing_keys if not k.endswith("mask_token")]   # DINOv2's training-only token
    if missing:
        raise RuntimeError(f"Metric3D checkpoint is missing {len(missing)} keys, e.g. {missing[:3]}")
    net = net.to("cuda").eval()
    ih, iw = p["input_size"]
    mean = torch.tensor([123.675, 116.28, 103.53]).float()[:, None, None]
    std = torch.tensor([58.395, 57.12, 57.375]).float()[:, None, None]

    @torch.no_grad()
    def fn(rgb, K):
        h, w = rgb.shape[:2]
        sc = min(ih / h, iw / w)
        x = cv2.resize(rgb, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_LINEAR)
        ph, pw = ih - x.shape[0], iw - x.shape[1]
        pad = [ph // 2, ph - ph // 2, pw // 2, pw - pw // 2]
        x = cv2.copyMakeBorder(x, pad[0], pad[1], pad[2], pad[3], cv2.BORDER_CONSTANT,
                               value=[123.675, 116.28, 103.53])
        x = ((torch.from_numpy(x.transpose(2, 0, 1)).float() - mean) / std)[None].cuda()
        d, _, _ = net.inference({"input": x})
        d = d.squeeze()[pad[0]:d.shape[-2] - pad[1], pad[2]:d.shape[-1] - pad[3]]
        d = torch.nn.functional.interpolate(d[None, None], (h, w), mode="bilinear").squeeze()
        d = torch.clamp(d * (K[0, 0] * sc / 1000.0), 0, 300)
        return d.float().cpu().numpy(), {"fx_used": float(K[0, 0]), "fx_pred": None}
    return fn


def _da3metric(p):
    import torch
    from depth_anything_3.api import DepthAnything3
    net = DepthAnything3.from_pretrained(p["repo"], revision=p["revision"]).to("cuda").eval()

    @torch.no_grad()
    def fn(rgb, K):
        h, w = rgb.shape[:2]
        pred = net.inference([rgb], process_res=p["process_res"], process_res_method=p["process_res_method"])
        d = np.asarray(pred.depth[0], np.float32)                  # processed resolution
        hp, wp = d.shape
        f_proc = 0.5 * (K[0, 0] * wp / w + K[1, 1] * hp / h)
        d = torch.nn.functional.interpolate(torch.from_numpy(d)[None, None], (h, w), mode="bilinear",
                                            align_corners=False).squeeze().numpy()
        return d * f_proc / p["canonical_focal"], {"fx_used": float(K[0, 0]), "fx_pred": None,
                                                   "proc_hw": [int(hp), int(wp)]}
    return fn


def _moge2(p):
    import torch
    from moge.model.v2 import MoGeModel
    net = MoGeModel.from_pretrained(p["repo"], revision=p["revision"]).to("cuda").eval()

    @torch.no_grad()
    def fn(rgb, K):
        h, w = rgb.shape[:2]
        x = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float().cuda() / 255.0
        fov = hfov_deg(K, w) if p["use_intrinsics"] else None
        out = net.infer(x, resolution_level=p["resolution_level"], apply_mask=False, fov_x=fov,
                        use_fp16=p["use_fp16"])
        fx_pred = float(out["intrinsics"][0, 0]) * w                 # normalized intrinsics
        return out["depth"].float().cpu().numpy(), {"fx_used": fx_pred, "fx_pred": fx_pred}
    return fn


def _depthpro(p):
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    proc = AutoImageProcessor.from_pretrained(p["repo"], revision=p["revision"])
    net = AutoModelForDepthEstimation.from_pretrained(p["repo"], revision=p["revision"]).to("cuda").eval()

    @torch.no_grad()
    def fn(rgb, K):
        h, w = rgb.shape[:2]
        out = net(**proc(images=rgb, return_tensors="pt").to("cuda"))
        fov_pred = float(out.field_of_view[0])
        fx_pred = 0.5 * w / math.tan(math.radians(fov_pred) / 2)
        if p["use_intrinsics"]:
            out.field_of_view = torch.full_like(out.field_of_view, hfov_deg(K, w))
        d = proc.post_process_depth_estimation(out, target_sizes=[(h, w)])[0]["predicted_depth"]
        return d.float().cpu().numpy(), {"fx_used": float(K[0, 0]) if p["use_intrinsics"] else fx_pred,
                                         "fx_pred": fx_pred}
    return fn


LOADERS = {"unidepth": _unidepth, "metric3d": _metric3d, "da3metric": _da3metric, "moge2": _moge2,
           "depthpro": _depthpro}


def load(family, params):
    if family not in LOADERS:
        raise KeyError(f"unknown depth family {family!r}; known {FAMILIES}")
    return Predictor(LOADERS[family](params))
