"""Small SE(3)/SO(3) helpers shared by evaluation and labels (numpy, batched)."""
import numpy as np


def inv(T):
    """Inverse of (..., 4, 4) rigid transforms."""
    R, t = T[..., :3, :3], T[..., :3, 3]
    out = np.zeros_like(T)
    Rt = np.swapaxes(R, -1, -2)
    out[..., :3, :3] = Rt
    out[..., :3, 3] = -(Rt @ t[..., None])[..., 0]
    out[..., 3, 3] = 1.0
    return out


def rot_angle_deg(R):
    """Rotation angle of (..., 3, 3) rotation matrices, in degrees."""
    c = (np.trace(R, axis1=-2, axis2=-1) - 1) / 2
    return np.degrees(np.arccos(np.clip(c, -1.0, 1.0)))


def rodrigues(rvec):
    """(N, 3) rotation vectors -> (N, 3, 3)."""
    rvec = np.atleast_2d(np.asarray(rvec, float))
    th = np.linalg.norm(rvec, axis=1)
    k = rvec / np.where(th > 1e-12, th, 1.0)[:, None]
    Kx = np.zeros((len(rvec), 3, 3))
    Kx[:, 0, 1], Kx[:, 0, 2] = -k[:, 2], k[:, 1]
    Kx[:, 1, 0], Kx[:, 1, 2] = k[:, 2], -k[:, 0]
    Kx[:, 2, 0], Kx[:, 2, 1] = -k[:, 1], k[:, 0]
    s, c = np.sin(th)[:, None, None], np.cos(th)[:, None, None]
    return np.eye(3) + s * Kx + (1 - c) * Kx @ Kx


def rt_to_T(rvec, tvec):
    rvec = np.atleast_2d(rvec)
    T = np.tile(np.eye(4), (len(rvec), 1, 1))
    T[:, :3, :3] = rodrigues(rvec)
    T[:, :3, 3] = np.atleast_2d(tvec).reshape(len(rvec), 3)
    return T


def umeyama_scale(src, dst):
    """Similarity (s, R, t) minimising |dst - (s R src + t)|^2 for (N, 3) point sets."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    U, S, Vt = np.linalg.svd(xd.T @ xs / len(src))
    D = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[2, 2] = -1
    R = U @ D @ Vt
    var_s = (xs ** 2).sum() / len(src)
    s = np.trace(np.diag(S) @ D) / var_s
    return s, R, mu_d - s * R @ mu_s


def quat_to_R(q_xyzw):
    x, y, z, w = np.asarray(q_xyzw, float).T
    return np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                     2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                     2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
                    -1).reshape(-1, 3, 3)


def R_to_quat(R):
    """(N, 3, 3) -> (N, 4) [x y z w], w >= 0."""
    R = np.asarray(R, float).reshape(-1, 3, 3)
    q = np.zeros((len(R), 4))
    for n, M in enumerate(R):
        tr = np.trace(M)
        if tr > 0:
            s = np.sqrt(tr + 1.0) * 2
            q[n] = [(M[2, 1] - M[1, 2]) / s, (M[0, 2] - M[2, 0]) / s, (M[1, 0] - M[0, 1]) / s, s / 4]
        else:
            i = int(np.argmax(np.diag(M)))
            j, k = (i + 1) % 3, (i + 2) % 3
            s = np.sqrt(1.0 + M[i, i] - M[j, j] - M[k, k]) * 2
            q[n, i] = s / 4
            q[n, j] = (M[j, i] + M[i, j]) / s
            q[n, k] = (M[k, i] + M[i, k]) / s
            q[n, 3] = (M[k, j] - M[j, k]) / s
    q *= np.where(q[:, 3:] < 0, -1.0, 1.0)
    return q / np.linalg.norm(q, axis=1, keepdims=True)
