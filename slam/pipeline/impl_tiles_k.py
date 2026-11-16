"""Masks step (tile_geometry_k): slam.tiles' tile masks for segments whose frames are not consecutive.

undistort_crop_resample keeps a subset of a 60 fps segment's frames, while gt.npz still holds the tile poses of
every original frame. slam.tiles.segment_tile_masks looks a pose's wall time up as wall[k - first k] and
slam_world_poses expects a SLAM pose for every posed frame; both assume consecutive frames. This module carries
the same algorithm with the frames matched by their original index k (wall times of the posed frames from the
head video's timestamps; the SLAM alignment uses the posed frames the run has). slam/tiles.py is untouched, so
tile_geometry and its caches are unchanged; on consecutive frames the result is identical.
"""
import json
import time

import cv2
import numpy as np

from slam import config as C
from slam import geometry as G
from slam import tiles as T


def slam_world_poses_k(seg, run, gt):
    """slam.tiles.slam_world_poses on the posed frames that the SLAM run has a pose for."""
    p = seg / "slam" / f"{run}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    k_all, T_sc = z["k"], z["T_slam_cam"].astype(float)
    idx = {int(k): i for i, k in enumerate(k_all)}
    have = np.array([int(k) in idx for k in gt["cam_k"]], bool)
    if have.sum() < 3:
        return None
    sel = np.array([idx[int(k)] for k in gt["cam_k"][have]], int)
    ok = np.isfinite(T_sc[sel]).all((1, 2))
    if ok.sum() < 3:
        return None
    sel = sel[ok]
    T_wc = G.inv(gt["T_cam_world"][have][ok])
    U, _, Vt = np.linalg.svd((T_wc[:, :3, :3] @ np.swapaxes(T_sc[sel, :3, :3], 1, 2)).sum(0))
    R = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    cs = (R @ T_sc[sel, :3, 3].T).T
    A = np.concatenate([cs.reshape(-1, 1), np.tile(np.eye(3), (len(sel), 1))], 1)
    x = np.linalg.lstsq(A, T_wc[:, :3, 3].reshape(-1), rcond=None)[0]
    s, t = x[0], x[1:]
    Tw = np.tile(np.eye(4), (len(k_all), 1, 1))
    Tw[:, :3, :3] = R @ T_sc[:, :3, :3]
    Tw[:, :3, 3] = s * (R @ T_sc[:, :3, 3].T).T + t
    return {int(k): Ti for k, Ti in zip(k_all, G.inv(Tw))}


def segment_tile_masks_k(seg, session, walls_by_k, margin_mm=10.0, max_gap_s=0.5, grow_mm_per_s=100.0,
                         slam_fallback="E1", slam_margin_mm=25.0):
    """slam.tiles.segment_tile_masks with frames matched by k (walls_by_k: original index -> wall time)."""
    Tt, edge, tile_m, _ = T.layout_tiles(session)
    fj = json.load(open(seg / "frames.json"))
    fr = fj["frames"]
    W, H = fj["size"]
    gt = np.load(seg / "gt.npz")
    z = np.load(seg / "tiles.npz")
    pose_w = {int(k): (Tm, walls_by_k[int(k)]) for k, Tm in zip(gt["cam_k"], gt["T_cam_world"])}
    pk = np.array(sorted(pose_w))
    pwall = np.array([pose_w[k][1] for k in pk])
    masked = np.zeros((len(fr), H, W), bool)
    slam_cw = slam_world_poses_k(seg, slam_fallback, gt) if slam_fallback else None
    n_pose = n_near = n_slam = n_none = 0
    for i, f in enumerate(fr):
        m = np.zeros((H, W), np.uint8)
        src = None
        if f["k"] in pose_w:
            src, gap = pose_w[f["k"]][0], 0.0
            n_pose += 1
        elif len(pk):
            j = int(np.argmin(np.abs(pwall - f["wall"])))
            gap = abs(pwall[j] - f["wall"])
            if gap <= max_gap_s:
                src = pose_w[int(pk[j])][0]
                n_near += 1
        if src is None and slam_cw is not None and f["k"] in slam_cw and np.isfinite(slam_cw[f["k"]]).all():
            src, gap = slam_cw[f["k"]], slam_margin_mm / grow_mm_per_s
            n_slam += 1
        if src is None:
            n_none += 1
        else:
            half = tile_m / 2 + margin_mm / 1000.0 + grow_mm_per_s / 1000.0 * gap
            sq = np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]])
            for tid, Tm in Tt.items():
                uv = T.project_output((Tm[:3, :3] @ sq.T).T + Tm[:3, 3], np.asarray(src), fj)
                if uv is not None:
                    cv2.fillConvexPoly(m, np.round(uv * 16).astype(np.int32), 1, cv2.LINE_8, 4)
        sel = z["det_k"] == f["k"]
        scale = (tile_m + 2 * margin_mm / 1000.0) / edge
        for c in z["det_corners"][sel]:
            uv = T.to_output_px(c, fj)
            ctr = uv.mean(0)
            uv = ctr + (uv - ctr) * scale
            cv2.fillConvexPoly(m, np.round(uv * 16).astype(np.int32), 1, cv2.LINE_8, 4)
        masked[i] = m > 0
    meta = {"margin_mm": margin_mm, "max_gap_s": max_gap_s, "grow_mm_per_s": grow_mm_per_s,
            "slam_fallback": slam_fallback, "slam_margin_mm": slam_margin_mm, "frames_pose": n_pose,
            "frames_near_pose": n_near, "frames_slam": n_slam, "frames_no_pose": n_none, "match": "k"}
    return masked, meta


def run_tile_geometry_k(job):
    p = job.params
    fb = p["slam_fallback"]
    if fb:
        e = job.input_of("slam", fb)
        job.log(f"slam fallback: run {fb} (key {e['key']})")
    s = C.session(job.session)
    walls = [x["wall"] for x in json.load(open(C.RAW / f"{s['head_stem']}_ts.json"))]
    walls_by_k = dict(enumerate(walls))
    out = {}
    for seg in job.todo():
        t0 = time.time()
        view = job.input_view(seg)
        if fb and not (view / "slam" / f"{fb}.npz").exists():
            raise FileNotFoundError(f"{seg}: slam fallback {view / 'slam' / f'{fb}.npz'} missing")
        masked, meta = segment_tile_masks_k(view, job.session, walls_by_k, margin_mm=p["margin_mm"],
                                            max_gap_s=p["max_gap_s"], grow_mm_per_s=p["grow_mm_per_s"],
                                            slam_fallback=fb, slam_margin_mm=p["slam_margin_mm"])
        tmp = job.tmp(seg)
        np.savez_compressed(tmp / "masked.npz", masked=np.packbits(masked, axis=-1), meta=json.dumps(meta))
        job.publish(seg, tmp)
        out[seg] = {**{k: meta[k] for k in ("frames_pose", "frames_near_pose", "frames_slam",
                                            "frames_no_pose")},
                    "masked_frac": float(masked.mean())}
        job.log(f"{seg}: " + json.dumps(out[seg]) + f" {time.time() - t0:.0f}s")
    return out
