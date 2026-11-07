"""DROID-SLAM with motion masks, as subclasses (third_party/DROID-SLAM is unmodified
apart from its own local build patches).

Masks enter in two places (design doc, "DROID-SLAM"):
  1. Bundle-adjustment weights. Every BA call (frontend, global backend, trajectory
     filler) goes through DepthVideo.ba(target, weight, ..., ii, jj). There each
     residual's weight is multiplied by valid_i(p) * valid_j(p'), where p is the
     source cell in frame ii and p' = target is its matched position in frame jj.
     So a background pixel whose match lands on the hand in the other frame is
     dropped too. The images and the flow network are untouched.
  2. Keyframe selection. MotionFilter adds a keyframe when the mean flow magnitude
     exceeds a threshold; the mean is taken over cells valid in both frames, so a
     moving hand does not trigger keyframes.

Masks are looked up by frame index (video.tstamp holds the image index i passed to
track()), so keyframe removal and the filler's temporary entries need no bookkeeping.

valid masks are float tensors (T, H/8, W/8) on the GPU, 1 = usable, 0 = masked.
"""
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

DROID_ROOT = Path("/home/student/yuanliu-hawaii/third_party/DROID-SLAM")
sys.path.insert(0, str(DROID_ROOT / "droid_slam"))

import lietorch  # noqa: E402
import geom.projective_ops as pops  # noqa: E402
from depth_video import DepthVideo  # noqa: E402
from droid_backend import DroidBackend  # noqa: E402
from droid_frontend import DroidFrontend  # noqa: E402
from droid_net import DroidNet  # noqa: E402
from modules.corr import CorrBlock  # noqa: E402
from motion_filter import MotionFilter, autocast  # noqa: E402
from trajectory_filler import PoseTrajectoryFiller  # noqa: E402


def valid_grid(masked, dilate_px=8):
    """Full-res masked (T, H, W) bool -> valid (T, H/8, W/8) float.

    Dilate by dilate_px at full resolution, then a 1/8 cell is invalid if ANY of its
    64 pixels is masked."""
    m = torch.as_tensor(masked, dtype=torch.float32)[:, None]
    if dilate_px > 0:
        k = 2 * dilate_px + 1
        m = F.max_pool2d(m, k, stride=1, padding=dilate_px)
    m = F.max_pool2d(m, 8, stride=8)
    return (1.0 - m[:, 0]).contiguous()


class MaskedDepthVideo(DepthVideo):
    def __init__(self, *a, valid=None, **kw):
        super().__init__(*a, **kw)
        self.valid = valid            # (T, h, w) float on cuda, or None = vanilla DROID

    def edge_valid(self, target, ii, jj):
        """target (E, 2, h, w) matched coords (x, y) in frame jj at 1/8 res -> (E, h, w)."""
        fi = self.tstamp[ii].round().long()
        fj = self.tstamp[jj].round().long()
        vi = self.valid[fi]
        h, w = vi.shape[-2:]
        gx = target[:, 0] / (w - 1) * 2 - 1
        gy = target[:, 1] / (h - 1) * 2 - 1
        vj = F.grid_sample(self.valid[fj][:, None], torch.stack([gx, gy], -1),
                           mode="bilinear", padding_mode="border", align_corners=True)[:, 0]
        return vi * (vj > 0.5).float()

    def ba(self, target, weight, eta, ii, jj, t0=1, t1=None, itrs=2, lm=1e-4, ep=0.1,
           motion_only=False):
        if self.valid is not None and len(ii) > 0:
            weight = weight * self.edge_valid(target, ii, jj)[:, None]
        return super().ba(target, weight, eta, ii, jj, t0, t1, itrs, lm, ep, motion_only)


class MaskedMotionFilter(MotionFilter):
    """MotionFilter.track with the flow-magnitude mean taken over valid cells."""

    def __init__(self, *a, valid=None, min_valid_frac=0.05, **kw):
        super().__init__(*a, **kw)
        self.valid = valid
        self.min_valid_frac = min_valid_frac
        self.last_t = None

    @autocast(enabled=True)
    @torch.no_grad()
    def track(self, tstamp, image, depth=None, intrinsics=None):
        if self.valid is None:
            return super().track(tstamp, image, depth, intrinsics)
        Id = lietorch.SE3.Identity(1,).data.squeeze()
        ht, wd = image.shape[-2] // 8, image.shape[-1] // 8
        image = image.cuda()
        inputs = image[None, :, [2, 1, 0]].to(self.device) / 255.0
        inputs = inputs.sub_(self.MEAN).div_(self.STDV)
        gmap = self._MotionFilter__feature_encoder(inputs)

        if self.video.counter.value == 0:
            net, inp = self._MotionFilter__context_encoder(inputs[:, [0]])
            self.net, self.inp, self.fmap = net, inp, gmap
            self.last_t = int(tstamp)
            self.video.append(tstamp, image[0], Id, 1.0, depth, intrinsics / 8.0, gmap,
                              net[0, 0], inp[0, 0])
            return

        coords0 = pops.coords_grid(ht, wd, device=self.device)[None, None]
        corr = CorrBlock(self.fmap[None, [0]], gmap[None, [0]])(coords0)
        _, delta, weight = self.update(self.net[None], self.inp[None], corr)
        mag = delta.norm(dim=-1)[0, 0]                                   # (h, w) at last keyframe
        m = self.valid[self.last_t] * self.valid[int(tstamp)]
        if m.sum() >= self.min_valid_frac * m.numel():
            motion = (mag * m).sum() / m.sum()
        else:                                                            # almost all masked
            motion = mag.mean()
        if motion.item() > self.thresh:
            self.count = 0
            net, inp = self._MotionFilter__context_encoder(inputs[:, [0]])
            self.net, self.inp, self.fmap = net, inp, gmap
            self.last_t = int(tstamp)
            self.video.append(tstamp, image[0], None, None, depth, intrinsics / 8.0, gmap,
                              net[0], inp[0])
        else:
            self.count += 1


class MaskedDroid:
    """droid.Droid with the masked video and motion filter (no visualiser)."""

    def __init__(self, args, valid=None):
        self.args = args
        self.net = DroidNet()
        sd = OrderedDict((k.replace("module.", ""), v) for k, v in torch.load(args.weights).items())
        for k in ("update.weight.2.weight", "update.weight.2.bias",
                  "update.delta.2.weight", "update.delta.2.bias"):
            sd[k] = sd[k][:2]
        self.net.load_state_dict(sd)
        self.net.to("cuda:0").eval()
        self.video = MaskedDepthVideo(args.image_size, args.buffer, stereo=False, valid=valid)
        self.filterx = MaskedMotionFilter(self.net, self.video, thresh=args.filter_thresh, valid=valid)
        self.frontend = DroidFrontend(self.net, self.video, args)
        self.backend = DroidBackend(self.net, self.video, args)
        self.traj_filler = PoseTrajectoryFiller(self.net, self.video)

    def track(self, tstamp, image, intrinsics):
        with torch.no_grad():
            self.filterx.track(tstamp, image, None, intrinsics)
            self.frontend()

    def terminate(self, stream):
        """Global BA, then fill non-keyframes. Returns per-frame poses (N, 7)
        [tx ty tz qx qy qz qw] of the camera in the SLAM frame (slam->cam)."""
        del self.frontend
        torch.cuda.empty_cache()
        self.backend(7)
        torch.cuda.empty_cache()
        self.backend(12)
        n_kf = self.video.counter.value
        kf = {"kf_t": self.video.tstamp[:n_kf].round().long().cpu().numpy(),
              "kf_pose_cw": self.video.poses[:n_kf].cpu().numpy(),     # world->cam, lietorch [t q]
              "kf_disp": self.video.disps[:n_kf].cpu().numpy()}        # 1/8-res inverse depth
        traj = self.traj_filler(stream)
        return traj.inv().data.cpu().numpy(), kf
