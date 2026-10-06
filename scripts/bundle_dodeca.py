#!/usr/bin/env python3
"""P0 pass 2: bundle-adjust dodecahedron marker-to-body transforms.

Model: body frame = frame of the reference marker (most-observed id).
Unknowns: se3 pose of each other marker in body frame, + body pose per frame.
Observations: detected 4-corner image points of each marker.
Minimize reprojection error with intrinsics frozen (from C0754 calibration).

Frame selection: low-velocity frames only, subsampled for coverage.
Validation: per-frame single-marker PnP solutions compared in body frame
(translation spread of the body origin), reported per marker pair.

NOTE: marker edge length defaults to 15mm nominal — all translations scale
linearly with the true printed size; measure with calipers and re-run with
--marker-mm to get metric output.

Usage: python scripts/bundle_dodeca.py --npz=<detections.npz>[,more] [options]
  --npz=A,B         detection caches from detect_parallel.py (merged)
  --intr=PATH       intrinsics of the camera that filmed them
                    (default calib/C0754_intrinsics.json — the robot's Sony)
  --marker-mm=F     caliper edge of THIS ball's faces (default 15.0 nominal)
  --ball-ids=25-35  ids that are ball faces; "a-b" or "a,b,c" (default 0-10)
  --out=PATH        free-bundle json (default calib/C0755_dodeca_bundle.json)
  --max-nfev=N      optimizer budget (default 2000)
This is pass 2 of 3: its output seeds bundle_dodeca_ideal.py (--init=).
"""
if any(a in ("-h", "--help") for a in __import__("sys").argv[1:]):
    print(__doc__.strip())
    raise SystemExit(0)
import sys
import json
import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

NPZS = ["calib/C0755_dodeca_detections.npz",
        "calib/C0756_dodeca_detections.npz"]  # merged; indices offset per clip
INTR = "calib/C0754_intrinsics.json"
OUT = "calib/C0755_dodeca_bundle.json"
MARKER_MM = 15.0
MAX_NFEV = 2000
BALL_IDS = set(range(11))   # robot ball: ids 0-10 (glove ball: --ball-ids=25-35)
for a in sys.argv[1:]:
    if a.startswith("--marker-mm="):
        MARKER_MM = float(a.split("=")[1])
    elif a.startswith("--npz="):
        NPZS = a.split("=")[1].split(",")
    elif a.startswith("--out="):
        OUT = a.split("=")[1]
    elif a.startswith("--max-nfev="):
        MAX_NFEV = int(a.split("=")[1])
    elif a.startswith("--intr="):          # camera that filmed the take
        INTR = a.split("=")[1]
    elif a.startswith("--ball-ids="):      # "25-35" or "25,26,27,..."
        v = a.split("=")[1]
        BALL_IDS = (set(range(int(v.split("-")[0]), int(v.split("-")[1]) + 1))
                    if "-" in v else {int(x) for x in v.split(",")})
    elif a.startswith("--max-vel="):       # px/s stillness gate (see below)
        MAX_VEL_ARG = float(a.split("=")[1])
MARKER_M = MARKER_MM / 1000.0

intr = json.load(open(INTR))
K = np.array(intr["camera_matrix"])
dist = np.array(intr["dist_coeffs"])

frames = {}
for ci, npz_path in enumerate(NPZS):
    data = np.load(npz_path)
    off = ci * 1_000_000  # keep clips' frame indices disjoint (velocity pairing gap)
    for k in data["frame_indices"]:
        frames[int(k) + off] = (data[f"i{k}"], data[f"c{k}"])
idxs = sorted(frames.keys())
print(f"merged {len(NPZS)} clips: {len(idxs)} frames with detections")

# marker object points in its own frame (z=0 plane, centered)
h = MARKER_M / 2
OBJ = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], np.float64)

def pnp(corners):
    ok, rvec, tvec = cv2.solvePnP(OBJ, corners.astype(np.float64), K, dist,
                                  flags=cv2.SOLVEPNP_IPPE_SQUARE)
    return (rvec.ravel(), tvec.ravel()) if ok else None

def pnp_both(corners):
    """Both IPPE candidate solutions with their reprojection errors."""
    try:
        n, rvecs, tvecs, errs = cv2.solvePnPGeneric(
            OBJ, corners.astype(np.float64).reshape(-1, 1, 2), K, dist,
            flags=cv2.SOLVEPNP_IPPE_SQUARE)
    except cv2.error:
        return []
    errs = np.asarray(errs).ravel()
    return [(rvecs[i].ravel(), tvecs[i].ravel(), float(errs[i]))
            for i in range(n)]

# ---------- velocity filter ----------
# Stillness gate. 150 px/s was tuned for a 1/60 s-shutter camera (motion
# blur smears corners). The B0587 runs a 0.2 ms shutter — no blur even at
# full rotation speed — so a glove calibration take, which is MOSTLY motion,
# should use --max-vel=600 or more; at 150 the rarely-shown faces lose every
# co-visible frame and drop out of the bundle (2026-10-06: faces 27/34).
MAX_VEL = globals().get("MAX_VEL_ARG", 150.0)  # px/s
vel = {}
prev = None
for k in idxs:
    ids, c = frames[k]
    cent = {int(i): cc.mean(axis=0) for i, cc in zip(ids, c)}
    if prev is not None and k - prev[0] <= 4:
        common = set(cent) & set(prev[1])
        if common:
            disp = np.mean([np.linalg.norm(cent[i] - prev[1][i]) for i in common])
            vel[k] = disp / ((k - prev[0]) / 29.97)
    prev = (k, cent)
still = [k for k in idxs if vel.get(k, np.inf) < MAX_VEL and len(frames[k][0]) >= 2]
print(f"{len(idxs)} frames w/ detections; {len(still)} still (<{MAX_VEL}px/s) with >=2 markers")

# subsample stills: keep at most one frame per 6 (0.2s) to cut redundancy
sel = []
for k in still:
    if not sel or k - sel[-1] >= 6:
        sel.append(k)
print(f"{len(sel)} frames selected for bundle")

# ---------- co-visibility ----------
from collections import Counter
seen = Counter()
pair = Counter()
for k in sel:
    ids = sorted(set(int(i) for i in frames[k][0]))
    seen.update(ids)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            pair[(ids[a], ids[b])] += 1
print("marker frame counts:", dict(sorted(seen.items())))
print("co-visibility pairs:", dict(sorted(pair.items())))

# BALL_IDS is set from --ball-ids above (default 0-10); non-ball ids in the
# detections (tails/bases) are ignored by the bundle
markers = sorted(m for m in seen.keys() if m in BALL_IDS)
excluded = sorted(m for m in seen.keys() if m not in BALL_IDS)
if excluded:
    print(f"excluding non-ball ids: {excluded}")
REF = max(markers, key=lambda m: seen[m])
print(f"reference marker: {REF}")

# check connectivity to REF
import itertools
adj = {m: set() for m in markers}
for (a, b), n in pair.items():
    if n >= 3 and a in adj and b in adj:
        adj[a].add(b); adj[b].add(a)
reach, stack = {REF}, [REF]
while stack:
    m = stack.pop()
    for n2 in adj[m]:
        if n2 not in reach:
            reach.add(n2); stack.append(n2)
drop = [m for m in markers if m not in reach]
if drop:
    print(f"WARNING: markers {drop} not connected to ref by >=3 co-obs; excluded")
markers = [m for m in markers if m in reach]

# ---------- initialization ----------
def to_mat(rvec, tvec):
    M = np.eye(4); M[:3, :3] = cv2.Rodrigues(np.asarray(rvec))[0]; M[:3, 3] = tvec
    return M

def geo_dist_deg(Ma, Mb):
    Rrel = Ma[:3, :3].T @ Mb[:3, :3]
    return np.degrees(np.abs(R.from_matrix(Rrel).magnitude()))

def robust_avg(mats):
    """Medoid-seeded robust average; returns (mean_mat, n_inliers, spread_mm)."""
    if len(mats) < 3:
        return None, 0, np.inf
    # medoid by summed rotation geodesic + translation distance
    n = len(mats)
    D = np.zeros((n, n))
    for a in range(n):
        for b in range(a + 1, n):
            dr = geo_dist_deg(mats[a], mats[b])
            dt = np.linalg.norm(mats[a][:3, 3] - mats[b][:3, 3]) * 1000
            D[a, b] = D[b, a] = dr + dt  # 1deg ~ 1mm weighting
    med = int(np.argmin(D.sum(axis=1)))
    inl = [i for i in range(n)
           if geo_dist_deg(mats[i], mats[med]) < 10
           and np.linalg.norm(mats[i][:3, 3] - mats[med][:3, 3]) < 0.010]
    if len(inl) < 3:
        return None, len(inl), np.inf
    sub = [mats[i] for i in inl]
    t = np.mean([M[:3, 3] for M in sub], axis=0)
    quats = np.array([R.from_matrix(M[:3, :3]).as_quat() for M in sub])
    q0 = quats[0]
    quats[np.sum(quats * q0, axis=1) < 0] *= -1
    q = quats.mean(axis=0); q /= np.linalg.norm(q)
    M = np.eye(4); M[:3, :3] = R.from_quat(q).as_matrix(); M[:3, 3] = t
    spread = float(np.std([np.linalg.norm(m2[:3, 3] - t) for m2 in sub]) * 1000)
    return M, len(inl), spread

# pairwise relative transforms from all 2x2 IPPE candidate combinations,
# keeping per-frame the combination most consistent with the pair's medoid
def pair_samples(m, n2):
    cands = []
    for k in sel:
        ids, c = frames[k]
        dd = {int(i): cc for i, cc in zip(ids, c)}
        if m in dd and n2 in dd:
            sm, sn = pnp_both(dd[m]), pnp_both(dd[n2])
            frame_opts = [np.linalg.inv(to_mat(a[0], a[1])) @ to_mat(b[0], b[1])
                          for a in sm for b in sn]
            if frame_opts:
                cands.append(frame_opts)
    if len(cands) < 3:
        return []
    # first pass: use best-reproj combo (index 0) to find a medoid
    first = [opts[0] for opts in cands]
    M0, _, _ = robust_avg(first)
    if M0 is None:
        M0 = first[0]
    # second pass: per frame pick the candidate combo closest to M0
    picked = []
    for opts in cands:
        d = [geo_dist_deg(o, M0) + np.linalg.norm(o[:3, 3] - M0[:3, 3]) * 1000
             for o in opts]
        picked.append(opts[int(np.argmin(d))])
    return picked

# build edges with robust relative transforms
edges = {}
for (a, b), cnt in pair.items():
    if cnt < 5 or a not in markers or b not in markers:
        continue
    Mab, n_inl, spread = robust_avg(pair_samples(a, b))
    if Mab is not None and n_inl >= 5:
        edges[(a, b)] = (Mab, n_inl, spread)
print(f"{len(edges)} usable edges")
for (a, b), (_, n_inl, spread) in sorted(edges.items()):
    print(f"  edge {a}-{b}: {n_inl} inliers, t-spread {spread:.1f}mm")

# max-weight spanning tree from REF (weight = inlier count)
T_body = {REF: np.eye(4)}
pool = dict(edges)
while True:
    best, bw = None, -1
    for (a, b), (Mab, n_inl, _) in pool.items():
        if (a in T_body) != (b in T_body) and n_inl > bw:
            best, bw = (a, b), n_inl
    if best is None:
        break
    a, b = best
    Mab = pool.pop(best)[0]
    if a in T_body:
        T_body[b] = T_body[a] @ Mab
    else:
        T_body[a] = T_body[b] @ np.linalg.inv(Mab)
markers = [m for m in markers if m in T_body]
print(f"initialized {len(markers)} markers: {markers}")

# body pose per frame init: PnP on all visible markers' corners vs body-frame obj pts
def body_obj_img(k, Tb):
    ids, c = frames[k]
    op, ip = [], []
    for i, cc in zip(ids, c):
        i = int(i)
        if i in Tb:
            P = (Tb[i] @ np.hstack([OBJ, np.ones((4, 1))]).T).T[:, :3]
            op.append(P); ip.append(cc)
    if not op:
        return None, None
    return np.concatenate(op), np.concatenate(ip).astype(np.float64)

cam_pose = {}
use = []
for k in sel:
    op, ip = body_obj_img(k, T_body)
    if op is None or len(op) < 8:
        continue
    ok, rvec, tvec = cv2.solvePnP(op, ip, K, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        continue
    proj, _ = cv2.projectPoints(op, rvec, tvec, K, dist)
    frame_rms = np.sqrt(((proj.reshape(-1, 2) - ip) ** 2).sum(axis=1).mean())
    if frame_rms < 50:  # drop frames whose init is inconsistent with the model
        cam_pose[k] = (rvec.ravel(), tvec.ravel())
        use.append(k)
print(f"{len(use)} frames in bundle (init frame rms < 50px)")

# ---------- bundle adjustment ----------
opt_markers = [m for m in markers if m != REF]
mi = {m: i for i, m in enumerate(opt_markers)}

def pack():
    x = []
    for m in opt_markers:
        M = T_body[m]
        x.extend(cv2.Rodrigues(M[:3, :3])[0].ravel()); x.extend(M[:3, 3])
    for k in use:
        r, t = cam_pose[k]
        x.extend(r); x.extend(t)
    return np.array(x)

def unpack(x):
    Tb = {REF: np.eye(4)}
    for m in opt_markers:
        o = 6 * mi[m]
        Tb[m] = to_mat(x[o:o+3], x[o+3:o+6])
    off = 6 * len(opt_markers)
    cp = {}
    for j, k in enumerate(use):
        o = off + 6 * j
        cp[k] = (x[o:o+3], x[o+3:o+6])
    return Tb, cp

# precompute observation list: (frame, marker, corners)
obs = []
for k in use:
    ids, c = frames[k]
    for i, cc in zip(ids, c):
        if int(i) in T_body:
            obs.append((k, int(i), cc.astype(np.float64)))
print(f"{len(obs)} marker observations, {4*len(obs)} points")

# --- vectorized residuals: batch Rodrigues via scipy, manual projection ---
fi = {k: j for j, k in enumerate(use)}
obs_m = np.array([mi.get(m, -1) for _, m, _ in obs])       # -1 = REF (identity)
obs_f = np.array([fi[k] for k, _, _ in obs])
obs_uv = np.stack([cc for _, _, cc in obs])                # (N,4,2)
fx_, fy_, cx_, cy_ = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
k1, k2, p1, p2, k3 = dist

def residuals(x):
    nm = len(opt_markers)
    mr = x[:6 * nm].reshape(nm, 6)
    fr = x[6 * nm:].reshape(len(use), 6)
    Rm = R.from_rotvec(mr[:, :3]).as_matrix()              # (nm,3,3)
    Rf = R.from_rotvec(fr[:, :3]).as_matrix()              # (nf,3,3)
    # marker corners in body frame, per observation
    P = np.empty((len(obs), 4, 3))
    ref_mask = obs_m < 0
    P[ref_mask] = OBJ
    nz = ~ref_mask
    P[nz] = np.einsum("oij,cj->oci", Rm[obs_m[nz]], OBJ) + mr[obs_m[nz], None, 3:]
    # to camera frame
    X = np.einsum("oij,ocj->oci", Rf[obs_f], P) + fr[obs_f, None, 3:]
    xn = X[..., 0] / X[..., 2]
    yn = X[..., 1] / X[..., 2]
    r2 = xn * xn + yn * yn
    rad = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 * r2 * r2
    xd = xn * rad + 2 * p1 * xn * yn + p2 * (r2 + 2 * xn * xn)
    yd = yn * rad + p1 * (r2 + 2 * yn * yn) + 2 * p2 * xn * yn
    u = fx_ * xd + cx_
    v = fy_ * yd + cy_
    return np.stack([u - obs_uv[..., 0], v - obs_uv[..., 1]], axis=-1).ravel()

# sparse jacobian pattern: each obs row block touches its marker + frame params
from scipy.sparse import lil_matrix
n_par = 6 * len(opt_markers) + 6 * len(use)
J = lil_matrix((8 * len(obs), n_par), dtype=np.uint8)
for o in range(len(obs)):
    rows = slice(8 * o, 8 * o + 8)
    if obs_m[o] >= 0:
        J[rows, 6 * obs_m[o]:6 * obs_m[o] + 6] = 1
    off = 6 * len(opt_markers) + 6 * obs_f[o]
    J[rows, off:off + 6] = 1

x0 = pack()
r0 = residuals(x0)
print(f"init rms: {np.sqrt((r0**2).mean()):.3f} px")
sol = least_squares(residuals, x0, method="trf", loss="huber", f_scale=2.0,
                    x_scale="jac", jac_sparsity=J.tocsr(), max_nfev=MAX_NFEV, verbose=0)
rf = residuals(sol.x)
print(f"pass1 rms: {np.sqrt((rf**2).mean()):.3f} px (status {sol.status})")

# drop observations with high residual (blur/misdetection), rebuild, re-solve
obs_rms = np.sqrt((rf.reshape(-1, 4, 2) ** 2).sum(axis=2).mean(axis=1))
keep_obs = obs_rms < 3.0
print(f"dropping {int((~keep_obs).sum())}/{len(obs)} obs with rms>=3px")
obs = [o for o, kk in zip(obs, keep_obs) if kk]
obs_m = obs_m[keep_obs]; obs_f = obs_f[keep_obs]; obs_uv = obs_uv[keep_obs]
J = lil_matrix((8 * len(obs), n_par), dtype=np.uint8)
for o in range(len(obs)):
    rows = slice(8 * o, 8 * o + 8)
    if obs_m[o] >= 0:
        J[rows, 6 * obs_m[o]:6 * obs_m[o] + 6] = 1
    off = 6 * len(opt_markers) + 6 * obs_f[o]
    J[rows, off:off + 6] = 1
sol = least_squares(residuals, sol.x, method="trf", loss="huber", f_scale=2.0,
                    x_scale="jac", jac_sparsity=J.tocsr(), max_nfev=MAX_NFEV, verbose=0)
rf = residuals(sol.x)
rms = np.sqrt((rf**2).mean())
print(f"final rms: {rms:.3f} px (status {sol.status}, nfev {sol.nfev})")
T_body, cam_pose = unpack(sol.x)

# ---------- validation: single-marker solutions ----------
# Body-origin implied by each marker alone, IPPE ambiguity resolved against the
# bundle's frame pose. Deviation from the bundle body origin is decomposed into
# camera-depth vs lateral; per-marker we separate systematic bias (mean vector
# in body frame = glue/print defect signal) from random scatter (PnP noise).
per_marker_body_dev = {m: [] for m in markers}   # deviation vectors in body frame
per_marker_cam_dev = {m: [] for m in markers}    # (depth_mm, lateral_mm)
n_val = 0
for k in use:
    rvec_f, tvec_f = cam_pose[k]
    T_cam_body_bundle = to_mat(rvec_f, tvec_f)
    Rcb = T_cam_body_bundle[:3, :3]
    origin_bundle = T_cam_body_bundle[:3, 3]
    ids, c = frames[k]
    got = 0
    for i, cc in zip(ids, c):
        i = int(i)
        if i not in T_body:
            continue
        # bundle-predicted marker pose in camera frame, for disambiguation
        T_pred = T_cam_body_bundle @ T_body[i]
        best = None
        for rv, tv, err in pnp_both(cc):
            Mc = to_mat(rv, tv)
            dr = geo_dist_deg(Mc, T_pred)
            if best is None or dr < best[0]:
                best = (dr, Mc)
        if best is None or best[0] > 25:  # no candidate consistent with prior
            continue
        T_cam_body_single = best[1] @ np.linalg.inv(T_body[i])
        dev_cam = T_cam_body_single[:3, 3] - origin_bundle
        # depth = component along camera ray to body origin
        ray = origin_bundle / np.linalg.norm(origin_bundle)
        depth = float(dev_cam @ ray)
        lat = float(np.linalg.norm(dev_cam - depth * ray))
        per_marker_cam_dev[i].append((depth * 1000, lat * 1000))
        per_marker_body_dev[i].append(Rcb.T @ dev_cam * 1000)
        got += 1
    n_val += got > 0

print(f"\nvalidation over {n_val} frames (deviation of single-face body origin "
      f"from bundle solution):")
print("  id    n   bias|mm| (systematic)   depth-sd   lat-sd   lat-bias")
bias_report = {}
for m in markers:
    dv = np.array(per_marker_body_dev[m])
    cd = np.array(per_marker_cam_dev[m])
    if len(dv) < 5:
        print(f"  {m:3d} {len(dv):4d}   (too few obs)")
        continue
    bias = dv.mean(axis=0)
    lat_bias = float(np.linalg.norm(cd[:, 1].mean()))
    bias_report[m] = {"bias_vec_mm": bias.tolist(),
                      "bias_norm_mm": float(np.linalg.norm(bias)),
                      "depth_sd_mm": float(cd[:, 0].std()),
                      "lat_sd_mm": float(cd[:, 1].std()),
                      "n": int(len(dv))}
    print(f"  {m:3d} {len(dv):4d}      {np.linalg.norm(bias):6.2f}          "
          f"{cd[:,0].std():6.2f}    {cd[:,1].std():5.2f}    {lat_bias:5.2f}")
spreads = np.array([np.linalg.norm(b["bias_vec_mm"]) for b in bias_report.values()])

out = {
    "video": ["data/raw/C0755.MP4", "data/raw/C0756.MP4"],
    "intrinsics": INTR,
    "marker_edge_mm_ASSUMED": MARKER_MM,
    "scale_note": "all translations scale linearly with true marker edge; re-run with --marker-mm=<caliper value>",
    "reference_marker": int(REF),
    "markers": {str(m): T_body[m].tolist() for m in markers},
    "n_frames": len(use), "n_observations": len(obs),
    "rms_px": float(rms),
    "per_marker_validation": {str(m): v for m, v in bias_report.items()},
    "bias_norm_mm": {"median": float(np.median(spreads)),
                     "max": float(spreads.max())},
}
with open(OUT, "w") as f:
    json.dump(out, f, indent=2)
print(f"\nwrote {OUT}")
