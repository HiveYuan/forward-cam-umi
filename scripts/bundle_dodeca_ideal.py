#!/usr/bin/env python3
"""P0 pass 3: dodecahedron-prior bundle.

Face normals are constrained to the ideal regular-dodecahedron directions
(12 icosahedron-vertex normals; 11 printed faces assigned from the free
bundle). Per face we estimate only print-plausible deviations:
  phi_i  in-plane spin about the face normal        (free)
  d_i    face-plane distance from body center        (~inradius + defect)
  o_i    2D in-plane center offset                   (weak prior to 0)
Plus per-frame camera pose. Body frame = ideal dodecahedron frame.

Init from the free-bundle solutions (755-only preferred, 756-only fallback).
"""
import sys
import json
import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R
from scipy.sparse import lil_matrix

NPZS = ["calib/C0755_dodeca_detections.npz", "calib/C0756_dodeca_detections.npz"]
INTR = "calib/C0754_intrinsics.json"
INIT_BUNDLES = ["calib/tmp_bundle_755only.json", "calib/tmp_bundle_756only.json"]
OUT = "calib/dodeca_bundle_ideal.json"
MARKER_MM_ARG = None
for a in sys.argv[1:]:
    if a.startswith("--npz="):
        NPZS = a.split("=")[1].split(",")
    elif a.startswith("--out="):
        OUT = a.split("=")[1]
    elif a.startswith("--intr="):          # camera that filmed the take
        INTR = a.split("=")[1]
    elif a.startswith("--init="):          # pass-2 free bundle(s) to seed from
        INIT_BUNDLES = a.split("=")[1].split(",")
    elif a.startswith("--marker-mm="):     # caliper edge of THIS ball's print
        MARKER_MM_ARG = float(a.split("=")[1])
MARKER_MM = 14.54 if MARKER_MM_ARG is None else MARKER_MM_ARG   # robot ball default
MARKER_M = MARKER_MM / 1000.0
SIGMA_O = 0.0005   # 0.5mm prior sd on in-plane offsets
SIGMA_D = 0.0015   # 1.5mm prior sd on per-face distance about the mean
PRIOR_W = 1.0      # px-equivalent weight per mm-normalized prior residual

intr = json.load(open(INTR))
K = np.array(intr["camera_matrix"]); dist = np.array(intr["dist_coeffs"])
fx_, fy_, cx_, cy_ = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
k1, k2, p1, p2, k3 = dist

frames = {}
for ci, p in enumerate(NPZS):
    data = np.load(p)
    off = ci * 1_000_000
    for k in data["frame_indices"]:
        frames[int(k) + off] = (data[f"i{k}"], data[f"c{k}"])
idxs = sorted(frames.keys())

h = MARKER_M / 2
OBJ = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], np.float64)

# ---------- velocity + selection (same policy as free bundle) ----------
vel, prev = {}, None
for k in idxs:
    ids, c = frames[k]
    cent = {int(i): cc.mean(axis=0) for i, cc in zip(ids, c)}
    if prev is not None and k - prev[0] <= 4:
        common = set(cent) & set(prev[1])
        if common:
            disp = np.mean([np.linalg.norm(cent[i] - prev[1][i]) for i in common])
            vel[k] = disp / ((k - prev[0]) / 29.97)
    prev = (k, cent)
still = [k for k in idxs if vel.get(k, np.inf) < 150.0 and len(frames[k][0]) >= 2]
sel = []
for k in still:
    if not sel or k - sel[-1] >= 6:
        sel.append(k)
print(f"{len(sel)} frames selected")

# ---------- ideal dodecahedron ----------
PHI = (1 + 5 ** 0.5) / 2
ico = []
for a in (1, -1):
    for b in (PHI, -PHI):
        ico += [(0, a, b), (a, b, 0), (b, 0, a)]
IDEAL = np.array(ico, float)
IDEAL /= np.linalg.norm(IDEAL, axis=1, keepdims=True)   # 12 face normals

def basis(n):
    """Fixed orthonormal frame with z = n."""
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(a, n); x /= np.linalg.norm(x)
    y = np.cross(n, x)
    return np.column_stack([x, y, n])

# ---------- init: free-bundle poses, align ideal frame ----------
init = {}
for pth in INIT_BUNDLES:
    b = json.load(open(pth))
    for m, M in b["markers"].items():
        if int(m) not in init:
            init[int(m)] = np.array(M)
markers = sorted(init.keys())
print(f"init faces: {markers}")

# re-center: free-bundle body origin sits on the reference face, not the ball
# center. Fit center c0 from face planes (n_i . c0 + r = n_i . p_i), subtract.
A = np.stack([init[m][:3, 2] for m in markers])
dvec = np.array([init[m][:3, 2] @ init[m][:3, 3] for m in markers])
Mls = np.hstack([A, np.ones((len(markers), 1))])
solc, *_ = np.linalg.lstsq(Mls, dvec, rcond=None)
c0 = solc[:3]
print(f"re-centering init by {np.round(c0*1000,2)}mm (inradius est {solc[3]*1000:.2f}mm)")
for m in markers:
    init[m] = init[m].copy()
    init[m][:3, 3] = init[m][:3, 3] - c0

# find rotation G (meas body -> ideal) + assignment, greedy over best matches
meas_n = {m: init[m][:3, 2] for m in markers}
best = None
# search over rotations aligning each (meas pair) to each (ideal pair)
ms = markers
for i0 in range(len(ms)):
    for j0 in range(len(IDEAL)):
        # align meas normal i0 to ideal j0, then try second pair to fix roll
        for i1 in range(len(ms)):
            if i1 == i0:
                continue
            for j1 in range(len(IDEAL)):
                if j1 == j0:
                    continue
                A = np.column_stack([meas_n[ms[i0]], meas_n[ms[i1]]])
                B = np.column_stack([IDEAL[j0], IDEAL[j1]])
                if abs(A[:, 0] @ A[:, 1] - B[:, 0] @ B[:, 1]) > 0.05:
                    continue
                # Kabsch on the two directions + their cross products
                A3 = np.column_stack([A, np.cross(A[:, 0], A[:, 1])])
                B3 = np.column_stack([B, np.cross(B[:, 0], B[:, 1])])
                U, _, Vt = np.linalg.svd(B3 @ A3.T)
                G = U @ np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))]) @ Vt
                # assignment cost
                cost, assign = 0.0, {}
                usedj = set()
                ok = True
                for m in ms:
                    v = G @ meas_n[m]
                    j = int(np.argmax(IDEAL @ v))
                    if j in usedj or IDEAL[j] @ v < np.cos(np.radians(20)):
                        ok = False
                        break
                    usedj.add(j); assign[m] = j
                    cost += np.degrees(np.arccos(np.clip(IDEAL[j] @ v, -1, 1)))
                if ok and (best is None or cost < best[0]):
                    best = (cost, G, dict(assign))
cost, G, assign = best
print(f"ideal alignment: total normal error {cost:.1f} deg over {len(ms)} faces "
      f"(mean {cost/len(ms):.2f})")
print("assignment:", assign)

NB = {m: basis(IDEAL[assign[m]]) for m in markers}   # body-frame face basis
mi = {m: i for i, m in enumerate(markers)}

# init params from rotated free solution
phi0, d0, o0 = {}, {}, {}
for m in markers:
    Rm = G @ init[m][:3, :3]
    t = G @ init[m][:3, 3]
    n = IDEAL[assign[m]]
    d0[m] = float(t @ n)
    op = NB[m].T @ (t - d0[m] * n)
    o0[m] = op[:2]
    # in-plane spin: angle of NB^T Rm about z
    Rrel = NB[m].T @ Rm
    phi0[m] = float(np.arctan2(Rrel[1, 0] - Rrel[0, 1], Rrel[0, 0] + Rrel[1, 1]))
print("init d (mm):", {m: round(d0[m]*1000, 2) for m in markers})

def face_mat(phi, d, ox, oy, m):
    Rz = np.array([[np.cos(phi), -np.sin(phi), 0],
                   [np.sin(phi), np.cos(phi), 0], [0, 0, 1]])
    M = np.eye(4)
    M[:3, :3] = NB[m] @ Rz
    M[:3, 3] = d * IDEAL[assign[m]] + NB[m] @ np.array([ox, oy, 0.0])
    return M

def T_body_all(x):
    out = {}
    for m in markers:
        o = 4 * mi[m]
        out[m] = face_mat(x[o], x[o+1], x[o+2], x[o+3], m)
    return out

# frame pose init via PnP against constructed model
x_face0 = []
for m in markers:
    x_face0 += [phi0[m], d0[m], o0[m][0], o0[m][1]]
x_face0 = np.array(x_face0)
Tb0 = T_body_all(x_face0)

cam_pose, use = {}, []
for k in sel:
    ids, c = frames[k]
    op, ip = [], []
    for i, cc in zip(ids, c):
        i = int(i)
        if i in Tb0:
            P = (Tb0[i] @ np.hstack([OBJ, np.ones((4, 1))]).T).T[:, :3]
            op.append(P); ip.append(cc)
    if not op or sum(len(o) for o in op) < 8:
        continue
    op = np.concatenate(op); ip = np.concatenate(ip).astype(np.float64)
    ok, rvec, tvec = cv2.solvePnP(op, ip, K, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        continue
    proj, _ = cv2.projectPoints(op, rvec, tvec, K, dist)
    if np.sqrt(((proj.reshape(-1, 2) - ip) ** 2).sum(1).mean()) < 50:
        cam_pose[k] = (rvec.ravel(), tvec.ravel())
        use.append(k)
print(f"{len(use)} frames in bundle")

obs = []
for k in use:
    ids, c = frames[k]
    for i, cc in zip(ids, c):
        if int(i) in Tb0:
            obs.append((k, int(i), cc.astype(np.float64)))
fi = {k: j for j, k in enumerate(use)}
obs_m = np.array([mi[m] for _, m, _ in obs])
obs_f = np.array([fi[k] for k, _, _ in obs])
obs_uv = np.stack([cc for _, _, cc in obs])
print(f"{len(obs)} observations")

NF = len(markers)
N_FACE_PAR = 4 * NF

def residuals(x):
    Tb = T_body_all(x)
    fr = x[N_FACE_PAR:].reshape(len(use), 6)
    Rf = R.from_rotvec(fr[:, :3]).as_matrix()
    Tmats = np.stack([Tb[m] for m in markers])
    P = np.einsum("oij,cj->oci", Tmats[obs_m, :3, :3], OBJ) + Tmats[obs_m, None, :3, 3]
    X = np.einsum("oij,ocj->oci", Rf[obs_f], P) + fr[obs_f, None, 3:]
    xn = X[..., 0] / X[..., 2]; yn = X[..., 1] / X[..., 2]
    r2 = xn * xn + yn * yn
    rad = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 ** 3
    xd = xn * rad + 2 * p1 * xn * yn + p2 * (r2 + 2 * xn * xn)
    yd = yn * rad + p1 * (r2 + 2 * yn * yn) + 2 * p2 * xn * yn
    u = fx_ * xd + cx_; v = fy_ * yd + cy_
    rep = np.stack([u - obs_uv[..., 0], v - obs_uv[..., 1]], -1).ravel()
    # priors: in-plane offsets ~0; face distances ~ their mean
    fp = x[:N_FACE_PAR].reshape(NF, 4)
    dmean = fp[:, 1].mean()
    pri = np.concatenate([
        PRIOR_W * fp[:, 2:].ravel() / SIGMA_O,
        PRIOR_W * (fp[:, 1] - dmean) / SIGMA_D,
    ])
    return np.concatenate([rep, pri])

J = lil_matrix((8 * len(obs) + 3 * NF, N_FACE_PAR + 6 * len(use)), dtype=np.uint8)
for o in range(len(obs)):
    rows = slice(8 * o, 8 * o + 8)
    J[rows, 4 * obs_m[o]:4 * obs_m[o] + 4] = 1
    off = N_FACE_PAR + 6 * obs_f[o]
    J[rows, off:off + 6] = 1
base = 8 * len(obs)
for i in range(NF):
    J[base + 2 * i, 4 * i + 2] = 1
    J[base + 2 * i + 1, 4 * i + 3] = 1
for i in range(NF):     # dmean couples all d's
    J[base + 2 * NF + i, [4 * j + 1 for j in range(NF)]] = 1

x0 = np.concatenate([x_face0] + [np.concatenate(cam_pose[k]) for k in use])
r0 = residuals(x0)
print(f"init rms (reproj part): {np.sqrt((r0[:8*len(obs)]**2).mean()):.3f} px")
sol = least_squares(residuals, x0, method="trf", loss="huber", f_scale=2.0,
                    x_scale="jac", jac_sparsity=J.tocsr(), max_nfev=20000,
                    xtol=1e-12, ftol=1e-10, verbose=0)
rf = residuals(sol.x)
rep = rf[:8 * len(obs)]
obs_rms = np.sqrt((rep.reshape(-1, 4, 2) ** 2).sum(2).mean(1))
keep = obs_rms < 3.0
print(f"pass1 reproj rms {np.sqrt((rep**2).mean()):.3f}px (status {sol.status}, "
      f"nfev {sol.nfev}); dropping {int((~keep).sum())}/{len(obs)} obs")
# where do the dropped obs live? (face id x clip)
from collections import Counter
dropped = Counter()
for (k, m, _), kk in zip(obs, keep):
    if not kk:
        dropped[(m, "C0756" if k >= 1_000_000 else "C0755")] += 1
tot = Counter()
for (k, m, _) in obs:
    tot[(m, "C0756" if k >= 1_000_000 else "C0755")] += 1
print("drop fraction by face x clip:")
for key in sorted(tot):
    print(f"  id {key[0]:2d} {key[1]}: {dropped[key]:3d}/{tot[key]:3d}")
obs = [o for o, kk in zip(obs, keep) if kk]
obs_m = obs_m[keep]; obs_f = obs_f[keep]; obs_uv = obs_uv[keep]
J = lil_matrix((8 * len(obs) + 3 * NF, N_FACE_PAR + 6 * len(use)), dtype=np.uint8)
for o in range(len(obs)):
    rows = slice(8 * o, 8 * o + 8)
    J[rows, 4 * obs_m[o]:4 * obs_m[o] + 4] = 1
    off = N_FACE_PAR + 6 * obs_f[o]
    J[rows, off:off + 6] = 1
base = 8 * len(obs)
for i in range(NF):
    J[base + 2 * i, 4 * i + 2] = 1
    J[base + 2 * i + 1, 4 * i + 3] = 1
for i in range(NF):
    J[base + 2 * NF + i, [4 * j + 1 for j in range(NF)]] = 1
sol = least_squares(residuals, sol.x, method="trf", loss="huber", f_scale=2.0,
                    x_scale="jac", jac_sparsity=J.tocsr(), max_nfev=20000,
                    xtol=1e-12, ftol=1e-10, verbose=0)
rf = residuals(sol.x)
rep = rf[:8 * len(obs)]
rms = float(np.sqrt((rep**2).mean()))
print(f"final reproj rms: {rms:.3f} px (status {sol.status}, nfev {sol.nfev})")

fp = sol.x[:N_FACE_PAR].reshape(NF, 4)
dmm = fp[:, 1] * 1000
print(f"\nfitted face-plane distances (mm), mean {dmm.mean():.2f}:")
for m in markers:
    i = mi[m]
    print(f"  id {m}: d={dmm[i]:6.2f}  proud={dmm[i]-dmm.mean():+5.2f}  "
          f"offset=({fp[i,2]*1000:+.2f},{fp[i,3]*1000:+.2f})mm  spin={np.degrees(fp[i,0]):7.2f}deg")

Tb = T_body_all(sol.x)
out = {
    "video": ["data/raw/C0755.MP4", "data/raw/C0756.MP4"],
    "intrinsics": INTR,
    "marker_edge_mm": MARKER_MM,
    "model": "ideal-dodecahedron prior: normals fixed to icosahedral directions; "
             "per-face spin, plane distance, in-plane offset fitted",
    "body_frame": "ideal dodecahedron frame (from icosahedral alignment)",
    "assignment": {str(m): int(assign[m]) for m in markers},
    "markers": {str(m): Tb[m].tolist() for m in markers},
    "face_plane_distance_mm": {str(m): float(dmm[mi[m]]) for m in markers},
    "inradius_mm": float(dmm.mean()),
    "n_frames": len(use), "n_observations": len(obs),
    "rms_px": rms,
}
with open(OUT, "w") as f:
    json.dump(out, f, indent=2)
print(f"wrote {OUT}")
