#!/usr/bin/env python3
"""Camera pose from the workspace tiles (AprilTag 36h11, ids 1-5).

The tiles define a WORLD frame shared between rigs: a glove session recorded
in another lab, with its camera wherever its mount put it, lands in the same
frame as ours as long as the tiles sit at the same places relative to the
task. On our side one hand-eye gives world -> robot base; on any side this
script gives camera -> world.

Two commands:

  layout  — export the tile layout from a static camera's footage. Per-tile
            PnP on sampled frames, medians, then a world frame anchored on
            the tiles themselves (origin = tile ORIGIN's centre, x toward
            tile XREF's centre, z = mean tile normal pointing up). Writes
            calib/workspace_tiles_<name>.json with every tile's pose in the
            world frame, in mm. Reproduce it elsewhere with a tape measure:
            the file is the drawing.
  solve   — camera -> world for a stream, from the layout: multi-tile PnP on
            every sampled frame (all corners of all decoded tiles against
            their world coordinates). For a static camera the per-frame
            spread is the precision; the median is the answer. Writes
            calib/<stem>_cam_world.json (T_cam_world = world expressed in the
            camera frame, 4x4, metres) and prints the residuals.

Usage:
  python scripts/tiles_pose.py layout <stem> --intr calib/B0587_intrinsics.json \
      --tags calib/tags36h11_<unit>.json --name pilot [--origin 5 --xref 4] [--stride 50]
  python scripts/tiles_pose.py solve  <stem> --intr calib/B0587_intrinsics.json \
      --tags calib/tags36h11_<unit>.json --layout calib/workspace_tiles_pilot.json [--stride 50]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labels_lib as L  # noqa: E402

ROOT = Path(__file__).parent.parent.resolve()   # the tree the script was invoked from, not the symlink target


def tag_obj(edge_m):
    h = edge_m / 2
    return np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], float)


def detector():
    p = cv2.aruco.DetectorParameters()
    p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
    return cv2.aruco.ArucoDetector(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11), p)


def sample_frames(stem, stride):
    """Sequential grab() with decode every `stride` frames: seeking a 4K
    MJPEG container by frame index re-scans it each time (minutes per
    pass); grab() just advances the demuxer."""
    cap = cv2.VideoCapture(str(ROOT / f"data/raw/{stem}.mkv"))
    k, misses = 0, 0
    while misses < 50:
        if not cap.grab():
            # a corrupt packet (seen at some stream starts) fails grab();
            # read() resyncs the decoder past it. Give up after 50 in a row.
            ok, _ = cap.read()
            misses += 1
            if not ok and misses >= 5:
                break
            k += 1
            continue
        misses = 0
        if k % stride == 0:
            ok, im = cap.retrieve()
            if ok:
                yield k, cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        k += 1
    cap.release()


def to_T(rv, tv):
    T = np.eye(4)
    T[:3, :3], _ = cv2.Rodrigues(np.asarray(rv, float).reshape(3, 1))
    T[:3, 3] = np.asarray(tv, float).ravel()
    return T


def cmd_layout(a):
    K, dist = L.load_intrinsics(a.intr)
    tags = json.load(open(a.tags))
    ids_ok = set(int(i) for i in tags["ids"])
    edge = tags["edge_mm"] / 1000.0
    det = detector()
    obj = tag_obj(edge)
    poses = {}
    n_frames = 0
    for k, g in sample_frames(a.stem, a.stride):
        n_frames += 1
        cs, ids, _ = det.detectMarkers(g)
        if ids is None:
            continue
        for i, c in zip(ids.ravel(), cs):
            i = int(i)
            if i not in ids_ok:
                continue
            ok, rv, tv = cv2.solvePnP(obj, c.reshape(4, 2).astype(float), K, dist,
                                      flags=cv2.SOLVEPNP_IPPE_SQUARE)
            if ok:
                poses.setdefault(i, []).append(to_T(rv, tv))
    if not poses:
        sys.exit("no tiles decoded")
    med = {}
    for i, Ts in poses.items():
        Ts = np.array(Ts)
        t = np.median(Ts[:, :3, 3], 0)
        # rotation: median rotation vector relative to the first (tiles are
        # static; spread is noise)
        rvs = np.array([cv2.Rodrigues(T[:3, :3])[0].ravel() for T in Ts])
        R, _ = cv2.Rodrigues(np.median(rvs, 0).reshape(3, 1))
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, t
        dev = np.linalg.norm(Ts[:, :3, 3] - t, axis=1) * 1000
        med[i] = (T, len(Ts), float(np.median(dev)))
        print(f"tile {i}: {len(Ts)}/{n_frames} frames, position spread median {np.median(dev):.1f} mm")
    if a.origin not in med or a.xref not in med:
        sys.exit(f"origin tile {a.origin} or x-ref tile {a.xref} not seen; pick others")
    # world frame in the camera: origin at tile ORIGIN, x toward XREF, z = mean tile normal (+z of the tag frame)
    o = med[a.origin][0][:3, 3]
    x = med[a.xref][0][:3, 3] - o
    x /= np.linalg.norm(x)
    z = np.mean([T[:3, 2] for T, _, _ in med.values()], 0)
    z -= (z @ x) * x
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    T_cam_world = np.eye(4)
    T_cam_world[:3, 0], T_cam_world[:3, 1], T_cam_world[:3, 2], T_cam_world[:3, 3] = x, y, z, o
    T_world_cam = np.linalg.inv(T_cam_world)
    layout = {"name": a.name, "dict": "36h11", "edge_mm": tags["edge_mm"],
              "frame": f"origin = centre of tile {a.origin}; +x toward centre of tile {a.xref}; "
                       f"+z = tile normal (up); +y = z cross x. Units mm.",
              "source": {"stem": a.stem, "intrinsics": a.intr, "frames_sampled": n_frames},
              "tiles": {}}
    for i, (T, n, spread) in sorted(med.items()):
        Tw = T_world_cam @ T
        layout["tiles"][str(i)] = {"xyz_mm": (Tw[:3, 3] * 1000).round(1).tolist(),
                                   "rvec": cv2.Rodrigues(Tw[:3, :3])[0].ravel().round(4).tolist(),
                                   "frames": n, "spread_mm": round(spread, 1)}
    layout["T_cam_world_source"] = T_cam_world.tolist()
    out = ROOT / f"calib/workspace_tiles_{a.name}.json"
    json.dump(layout, open(out, "w"), indent=1)
    print(f"\nlayout (mm, world frame):")
    for i, t in layout["tiles"].items():
        print(f"  tile {i}: x {t['xyz_mm'][0]:7.1f}  y {t['xyz_mm'][1]:7.1f}  z {t['xyz_mm'][2]:6.1f}")
    ids = sorted(layout["tiles"])
    print("tile-to-tile centre distances (tape-measure these):")
    for p in range(len(ids)):
        for q in range(p + 1, len(ids)):
            d = np.linalg.norm(np.array(layout["tiles"][ids[p]]["xyz_mm"]) - np.array(layout["tiles"][ids[q]]["xyz_mm"]))
            print(f"  {ids[p]}-{ids[q]}: {d:6.1f} mm")
    print(f"wrote {out}")


def solve_frame(corners_by_id, layout, K, dist):
    """Multi-tile PnP: all corners of all decoded tiles vs world coordinates."""
    edge = layout["edge_mm"] / 1000.0
    obj_t = tag_obj(edge)
    O, I = [], []
    for i, c in corners_by_id.items():
        t = layout["tiles"].get(str(i))
        if t is None:
            continue
        Tw = to_T(t["rvec"], np.array(t["xyz_mm"]) / 1000.0)
        O.append((Tw[:3, :3] @ obj_t.T).T + Tw[:3, 3])
        I.append(c.reshape(4, 2).astype(float))
    if not O:
        return None
    O, I = np.concatenate(O), np.concatenate(I)
    flags = cv2.SOLVEPNP_IPPE_SQUARE if len(O) == 4 else cv2.SOLVEPNP_SQPNP
    ok, rv, tv = cv2.solvePnP(O, I, K, dist, flags=flags)
    if not ok:
        return None
    if len(O) > 4:
        ok, rv, tv = cv2.solvePnP(O, I, K, dist, rvec=rv, tvec=tv, useExtrinsicGuess=True,
                                  flags=cv2.SOLVEPNP_ITERATIVE)
    proj, _ = cv2.projectPoints(O, rv, tv, K, dist)
    rms = float(np.sqrt(((proj.reshape(-1, 2) - I) ** 2).sum(1).mean()))
    return to_T(rv, tv), rms, len(O) // 4


def cmd_solve(a):
    K, dist = L.load_intrinsics(a.intr)
    layout = json.load(open(a.layout))
    tags = json.load(open(a.tags))
    ids_ok = set(int(i) for i in tags["ids"])
    det = detector()
    Ts, rms, nt, ks = [], [], [], []
    for k, g in sample_frames(a.stem, a.stride):
        cs, ids, _ = det.detectMarkers(g)
        if ids is None:
            continue
        by = {int(i): c for i, c in zip(ids.ravel(), cs) if int(i) in ids_ok}
        r = solve_frame(by, layout, K, dist)
        if r is None:
            continue
        T, e, n = r
        Ts.append(T); rms.append(e); nt.append(n); ks.append(k)
    if not Ts:
        sys.exit("no frames solved")
    Ts = np.array(Ts)
    t_med = np.median(Ts[:, :3, 3], 0)
    rv_med = np.median([cv2.Rodrigues(T[:3, :3])[0].ravel() for T in Ts], 0)
    T_med = to_T(rv_med, t_med)
    dev = np.linalg.norm(Ts[:, :3, 3] - t_med, axis=1) * 1000
    print(f"{a.stem}: {len(Ts)} frames solved; tiles per frame median {np.median(nt):.0f}; "
          f"reprojection RMS median {np.median(rms):.2f} px; camera position spread "
          f"median {np.median(dev):.1f} mm, p90 {np.percentile(dev, 90):.1f} mm")
    print(f"  camera in world (mm): {np.round(np.linalg.inv(T_med)[:3, 3] * 1000, 1)}")
    out = ROOT / f"calib/{a.stem}_cam_world.json"
    json.dump({"stem": a.stem, "layout": a.layout, "T_cam_world": T_med.tolist(),
               "n_frames": len(Ts), "rms_px_median": float(np.median(rms)),
               "pos_spread_mm_median": float(np.median(dev)),
               "per_frame": [{"k": int(k), "T_cam_world": T.tolist(), "rms": float(e), "tiles": int(n)}
                             for k, T, e, n in zip(ks, Ts, rms, nt)] if a.per_frame else None},
              open(out, "w"), indent=1)
    print(f"wrote {out}")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)
p1 = sub.add_parser("layout")
p1.add_argument("stem"); p1.add_argument("--intr", required=True); p1.add_argument("--tags", required=True)
p1.add_argument("--name", required=True); p1.add_argument("--origin", type=int, default=5)
p1.add_argument("--xref", type=int, default=4); p1.add_argument("--stride", type=int, default=50)
p2 = sub.add_parser("solve")
p2.add_argument("stem"); p2.add_argument("--intr", required=True); p2.add_argument("--tags", required=True)
p2.add_argument("--layout", required=True); p2.add_argument("--stride", type=int, default=50)
p2.add_argument("--per-frame", action="store_true", help="keep every sampled frame's pose (moving camera)")
a = ap.parse_args()
cmd_layout(a) if a.cmd == "layout" else cmd_solve(a)
