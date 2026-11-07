#!/usr/bin/env python3
"""Tile detections per segment frame, the ground-truth noise floor, and E3 tile masks.

  detect  re-detect the 36h11 workspace tiles on the raw 4K frames of each segment
          (same detector as scripts/head_pose_fast.py: half-res detection, full-res
          cornerSubPix) -> <segment>/tiles.npz (det_k, det_id, det_corners raw px)
  noise   ground-truth noise floor: on frames where all 4 tiles are detected, solve the
          head pose from two disjoint tile pairs (3 splits) and compare the two solutions.
          Most strict GT frames are 2-tile solves, so the floor is that of 2-tile GT:
          by_dt          relative motion cam_a->cam_b from pair A vs pair B, / sqrt(2):
                         the floor when the SAME tiles are seen at both ends (per-tile
                         layout errors cancel)
          tile_switch    |A - B| of the absolute poses in one frame: the error of a
                         relative motion whose two ends see DIFFERENT tile sets, which
                         includes the fixed per-tile layout bias
          -> <work>/<session>/eval/gt_noise.json
  masks   E3 tile masks: each tile's printed square (75 mm) plus a margin, projected
          with the frame's tile pose (or the nearest pose within --max-gap s, with a
          margin growing with the gap; else the --slam-fallback run's trajectory aligned
          to the segment's tile poses by a similarity transform, with a wider margin),
          plus the detected tag quads scaled to the paper size. Tiles half hidden behind
          an object are not detected, so pose projection is what covers them.
          -> <segment>/masks/tiles.npz (packbits of (T, H, W), True = masked)

  python -m slam.tiles detect --session yam_glove7 --jobs 8
  python -m slam.tiles noise  --session yam_glove7
  python -m slam.tiles masks  --session yam_glove7
"""
import argparse
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

from slam import config as C
from slam import geometry as G
from slam.preprocess import packet_pts

DTS_NOISE = [0.08, 0.5, 1.0, 2.0]


def tag_obj(edge_m):
    h = edge_m / 2
    return np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], float)


def layout_tiles(session):
    s = C.session(session)
    lay = json.load(open(C.CALIB / s["tile_layout"]))
    tags = json.load(open(C.CALIB / f"tags36h11_{s['glove']}.json"))
    T = {int(i): G.rt_to_T(t["rvec"], np.array(t["xyz_mm"]) / 1000.0)[0] for i, t in lay["tiles"].items()}
    return T, lay["edge_mm"] / 1000.0, tags.get("tile_mm", 75) / 1000.0, set(tags["ids"])


# ---------------------------------------------------------------- detect
def detect_segment(session, seg, pts, ts):
    s = C.session(session)
    fr = json.load(open(seg / "frames.json"))["frames"]
    k0, k1 = fr[0]["k"], fr[-1]["k"]
    _, _, _, ids_ok = layout_tiles(session)
    p = cv2.aruco.DetectorParameters()
    p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_NONE
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), p)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)
    intr = json.load(open(C.CALIB / s["intrinsics"]))
    W, H = intr["width"], intr["height"]
    t0, t1 = pts[k0] - 0.01, pts[k1] + 0.01
    n_want = k1 - k0 + 1
    cmd = ["ffmpeg", "-v", "error", "-copyts", "-ss", f"{max(t0 - 1, 0):.3f}", "-i",
           str(C.RAW / f"{s['head_stem']}.mkv"), "-vf", f"select='between(t,{t0:.4f},{t1:.4f})'",
           "-fps_mode", "passthrough", "-frames:v", str(n_want), "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    K, I, Cs, n = [], [], [], 0
    while True:
        buf = proc.stdout.read(W * H)
        if len(buf) < W * H:
            break
        g = np.frombuffer(buf, np.uint8).reshape(H, W)
        cs, ids, _ = det.detectMarkers(cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
        if ids is not None:
            for i, c in zip(ids.ravel(), cs):
                if int(i) in ids_ok:
                    c2 = (c.reshape(4, 2) * 2).astype(np.float32)
                    K.append(k0 + n)
                    I.append(int(i))
                    Cs.append(cv2.cornerSubPix(g, c2, (5, 5), (-1, -1), crit))
        n += 1
    if proc.wait() != 0 or n != n_want:
        raise RuntimeError(f"{seg.name}: decoded {n}/{n_want} frames")
    np.savez(seg / "tiles.npz", det_k=np.array(K, int), det_id=np.array(I, int),
             det_corners=np.array(Cs, float).reshape(-1, 4, 2))
    return f"{seg.name}: {len(K)} tile detections in {n} frames"


def cmd_detect(a):
    s = C.session(a.session)
    ts = np.array([x["wall"] for x in json.load(open(C.RAW / f"{s['head_stem']}_ts.json"))])
    pts = packet_pts(C.RAW / f"{s['head_stem']}.mkv")
    segs = [g for g in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]"))
            if a.overwrite or not (g / "tiles.npz").exists()]
    with ProcessPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(detect_segment, a.session, g, pts, ts): g for g in segs}
        for f in as_completed(futs):
            print(f.result(), flush=True)


# ---------------------------------------------------------------- noise
def solve_tiles(corners_by_id, Tt, edge, K, D):
    """Multi-tile PnP on the given tiles only (world->cam), SQPNP + iterative refine."""
    O, I = [], []
    obj = tag_obj(edge)
    for i, c in corners_by_id.items():
        O.append((Tt[i][:3, :3] @ obj.T).T + Tt[i][:3, 3])
        I.append(c)
    O, I = np.concatenate(O), np.concatenate(I)
    ok, rv, tv = cv2.solvePnP(O, I, K, D, flags=cv2.SOLVEPNP_SQPNP)
    ok, rv, tv = cv2.solvePnP(O, I, K, D, rvec=rv, tvec=tv, useExtrinsicGuess=True,
                              flags=cv2.SOLVEPNP_ITERATIVE)
    return G.rt_to_T(rv.ravel(), tv.ravel())[0]


def cmd_noise(a):
    s = C.session(a.session)
    intr = json.load(open(C.CALIB / s["intrinsics"]))
    K, D = np.array(intr["camera_matrix"]), np.array(intr["dist_coeffs"]).ravel()
    Tt, edge, _, _ = layout_tiles(a.session)
    tile_ids = sorted(Tt)
    splits = [((tile_ids[0], tile_ids[1]), (tile_ids[2], tile_ids[3])),
              ((tile_ids[0], tile_ids[2]), (tile_ids[1], tile_ids[3])),
              ((tile_ids[0], tile_ids[3]), (tile_ids[1], tile_ids[2]))]
    res = {str(dt): [] for dt in DTS_NOISE}
    per_frame = []
    n_frames = 0
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        z = np.load(seg / "tiles.npz")
        fr = json.load(open(seg / "frames.json"))["frames"]
        wall = {f["k"]: f["wall"] for f in fr}
        by_k = {}
        for k, i, c in zip(z["det_k"], z["det_id"], z["det_corners"]):
            by_k.setdefault(int(k), {})[int(i)] = c
        full = {k: d for k, d in by_k.items() if set(tile_ids) <= set(d)}
        n_frames += len(full)
        sols = {}
        for k, d in full.items():
            sols[k] = [(G.inv(solve_tiles({i: d[i] for i in A}, Tt, edge, K, D)[None])[0],
                        G.inv(solve_tiles({i: d[i] for i in B}, Tt, edge, K, D)[None])[0]) for A, B in splits]
        for k in full:
            for A_, B_ in sols[k]:
                per_frame.append((G.rot_angle_deg(A_[:3, :3].T @ B_[:3, :3]),
                                  1000 * np.linalg.norm(A_[:3, 3] - B_[:3, 3])))
        ks = np.array(sorted(full))
        wk = np.array([wall[k] for k in ks])
        for dt in DTS_NOISE:
            for ka, wa in zip(ks, wk):
                j = np.argmin(np.abs(wk - wa - dt))
                if abs(wk[j] - wa - dt) > 0.021:
                    continue
                kb = ks[j]
                for (A_a, B_a), (A_b, B_b) in zip(sols[ka], sols[kb]):
                    rA, rB = G.inv(A_a[None])[0] @ A_b, G.inv(B_a[None])[0] @ B_b
                    res[str(dt)].append((G.rot_angle_deg(rA[:3, :3].T @ rB[:3, :3]) / np.sqrt(2),
                                         1000 * np.linalg.norm(rA[:3, 3] - rB[:3, 3]) / np.sqrt(2)))
    pf = np.array(per_frame).reshape(-1, 2)
    out = {"frames_with_all_tiles": n_frames,
           "tile_switch": {
               "n": len(pf), "rot_deg_median": float(np.median(pf[:, 0])),
               "rot_deg_p95": float(np.percentile(pf[:, 0], 95)),
               "trans_mm_median": float(np.median(pf[:, 1])), "trans_mm_p95": float(np.percentile(pf[:, 1], 95))},
           "method": "by_dt: same tiles at both ends, (A vs B relative motion) / sqrt(2); "
                     "tile_switch: |A - B| absolute, i.e. ends seeing different tile pairs", "by_dt": {}}
    for dt, v in res.items():
        v = np.array(v).reshape(-1, 2)
        out["by_dt"][dt] = {"n": len(v)} if not len(v) else {
            "n": len(v), "rot_deg_median": float(np.median(v[:, 0])), "rot_deg_p95": float(np.percentile(v[:, 0], 95)),
            "trans_mm_median": float(np.median(v[:, 1])), "trans_mm_p95": float(np.percentile(v[:, 1], 95))}
    dst = C.WORK / a.session / "eval"
    dst.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(dst / "gt_noise.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- masks
def to_output_px(pts_raw, fj):
    """Raw distorted sensor px (N, 2) -> output image px, via the segment's undistortion."""
    u = fj["undistort"]
    K, D, Ku = np.array(u["K_src"]), np.array(u["dist"]), np.array(u["K_undist"])
    p = cv2.undistortPoints(pts_raw.reshape(-1, 1, 2).astype(np.float64), K, D, P=Ku).reshape(-1, 2)
    sy = u["h_scaled"] / u["src_size"][1]
    return np.stack([(p[:, 0] + 0.5) * u["scale"] - 0.5, (p[:, 1] + 0.5) * sy - 0.5 - u["crop_top"]], 1)


def project_output(Pw, T_cw, fj):
    """World points (N, 3) -> output image px with the output pinhole K (undistorted)."""
    Pc = (T_cw[:3, :3] @ Pw.T).T + T_cw[:3, 3]
    if np.any(Pc[:, 2] <= 0.05):
        return None
    Ko = np.array(fj["K"])
    uv = (Ko @ Pc.T).T
    return uv[:, :2] / uv[:, 2:]


def slam_world_poses(seg, run, gt):
    """world->cam for every frame from a SLAM run aligned to the tile poses (Sim3:
    rotation from the orientations, scale and offset from the camera centres)."""
    p = seg / "slam" / f"{run}.npz"
    if not p.exists() or len(gt["cam_k"]) < 3:
        return None
    z = np.load(p)
    k_all, T_sc = z["k"], z["T_slam_cam"].astype(float)
    idx = {int(k): i for i, k in enumerate(k_all)}
    sel = [idx[int(k)] for k in gt["cam_k"]]
    T_wc = G.inv(gt["T_cam_world"])
    U, _, Vt = np.linalg.svd((T_wc[:, :3, :3] @ np.swapaxes(T_sc[sel, :3, :3], 1, 2)).sum(0))
    R = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    cs = (R @ T_sc[sel, :3, 3].T).T
    A = np.concatenate([cs.reshape(-1, 1), np.tile(np.eye(3), (len(sel), 1))], 1)
    x = np.linalg.lstsq(A, T_wc[:, :3, 3].reshape(-1), rcond=None)[0]
    s, t = x[0], x[1:]
    T = np.tile(np.eye(4), (len(k_all), 1, 1))
    T[:, :3, :3] = R @ T_sc[:, :3, :3]
    T[:, :3, 3] = s * (R @ T_sc[:, :3, 3].T).T + t
    return {int(k): Ti for k, Ti in zip(k_all, G.inv(T))}


def cmd_masks(a):
    Tt, edge, tile_m, _ = layout_tiles(a.session)
    for seg in sorted(C.segments_dir(a.session).glob("ep[0-9][0-9]")):
        fj = json.load(open(seg / "frames.json"))
        fr = fj["frames"]
        W, H = fj["size"]
        gt = np.load(seg / "gt.npz")
        z = np.load(seg / "tiles.npz")
        wall = np.array([f["wall"] for f in fr])
        pose_w = {int(k): (T, wall[int(k) - fr[0]["k"]]) for k, T in zip(gt["cam_k"], gt["T_cam_world"])}
        pk = np.array(sorted(pose_w))
        pwall = np.array([pose_w[k][1] for k in pk])
        masked = np.zeros((len(fr), H, W), bool)
        slam_cw = slam_world_poses(seg, a.slam_fallback, gt) if a.slam_fallback else None
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
                if gap <= a.max_gap:
                    src = pose_w[int(pk[j])][0]
                    n_near += 1
            if src is None and slam_cw is not None:
                src, gap = slam_cw[f["k"]], a.slam_margin_mm / a.grow_mm_per_s
                n_slam += 1
            if src is None:
                n_none += 1
            else:
                half = tile_m / 2 + a.margin_mm / 1000.0 + a.grow_mm_per_s / 1000.0 * gap
                sq = np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]])
                for tid, T in Tt.items():
                    uv = project_output((T[:3, :3] @ sq.T).T + T[:3, 3], np.asarray(src), fj)
                    if uv is not None:
                        cv2.fillConvexPoly(m, np.round(uv * 16).astype(np.int32), 1, cv2.LINE_8, 4)
            sel = z["det_k"] == f["k"]
            scale = (tile_m + 2 * a.margin_mm / 1000.0) / edge
            for c in z["det_corners"][sel]:
                uv = to_output_px(c, fj)
                ctr = uv.mean(0)
                uv = ctr + (uv - ctr) * scale
                cv2.fillConvexPoly(m, np.round(uv * 16).astype(np.int32), 1, cv2.LINE_8, 4)
            masked[i] = m > 0
        (seg / "masks").mkdir(exist_ok=True)
        np.savez_compressed(seg / "masks" / "tiles.npz", masked=np.packbits(masked, axis=-1),
                            meta=json.dumps({"margin_mm": a.margin_mm, "max_gap_s": a.max_gap,
                                             "grow_mm_per_s": a.grow_mm_per_s, "slam_fallback": a.slam_fallback,
                                             "slam_margin_mm": a.slam_margin_mm, "frames_pose": n_pose,
                                             "frames_near_pose": n_near, "frames_slam": n_slam,
                                             "frames_no_pose": n_none}))
        print(f"{seg.name}: pose {n_pose}, nearest pose {n_near}, slam {n_slam}, none {n_none}; "
              f"masked {100 * masked.mean():.2f}% of pixels", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["detect", "noise", "masks"])
    ap.add_argument("--session", required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--margin-mm", type=float, default=10.0, help="added around the 75 mm printed square")
    ap.add_argument("--max-gap", type=float, default=0.5, help="s; use the nearest tile pose within this")
    ap.add_argument("--grow-mm-per-s", type=float, default=100.0, help="extra margin per s of pose gap")
    ap.add_argument("--slam-fallback", default="E1", help="SLAM run used where no tile pose is near ('' = off)")
    ap.add_argument("--slam-margin-mm", type=float, default=25.0, help="extra margin with the SLAM fallback")
    a = ap.parse_args()
    {"detect": cmd_detect, "noise": cmd_noise, "masks": cmd_masks}[a.cmd](a)


if __name__ == "__main__":
    main()
