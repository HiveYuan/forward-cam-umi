import importlib.util, json, sys
from pathlib import Path
import numpy as np
REPO = Path("/home/student/yuanliu-hawaii/head-cam-umi-slam")
spec = importlib.util.spec_from_file_location("diag", REPO / "experiments/exp005_session_scale/diagnosis.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
from slam import scale as SC, geometry as G, evaluate as EV
root = D.configure("/home/student/yuanliu-hawaii/work/runs/exp007_v2_session_scale/main/view", "/home/student/yuanliu-hawaii/work/yam_glove7/gt")
phys = json.load(open(sys.argv[1]))
nine = ['ep04','ep08','ep09','ep19','ep20','ep22','ep25','ep26','ep29']
for seg in sorted(root.glob("ep[0-9][0-9]")):
    n = seg.name
    if phys[n]["k_need"] is None: continue
    S = EV.load_segment(seg); z = np.load(seg / "slam" / "E3.npz")
    kf = z["kf_t"]; N = len(S["k"]); Tsc = z["T_slam_cam"].astype(float)
    used = [i for i, _ in phys[n]["kf_R"]]
    st = np.where(S["strict"] & np.isfinite(Tsc).all((1, 2)))[0]
    frac_kf_strict = np.mean([S["strict"][i] for i in used])
    # oracle restricted to strict frames within +-1 s (30 frames) of a used keyframe
    near = np.zeros(N, bool)
    for i in used: near[max(0, i - 15):i + 16] = True
    s_near, _ = EV.segment_scale({**S, "strict": S["strict"] & near}, Tsc)
    line = f"{n} {'*' if n in nine else ' '} N {N} kf_used at {np.round(np.array(used)/N,2).tolist()} strict span {st.min()/N:.2f}-{st.max()/N:.2f} kf_strict {frac_kf_strict:.2f} s_o {phys[n]['s_o']:.3f} s_o_near_kf {s_near:.3f} ({int((S['strict']&near).sum())} fr)"
    print(line)
    if n == "ep29":
        m = S["strict"] & np.isfinite(Tsc).all((1, 2))
        src, dst = Tsc[m, :3, 3], S["T_wc"][m, :3, 3]
        s, R, t = G.umeyama_scale(src, dst)
        res = np.linalg.norm(dst - (s * (R @ src.T).T + t), axis=1)
        idx = np.where(m)[0]
        print("  ep29 strict frames", idx.tolist())
        print("  residual mm", np.round(1000 * res, 1).tolist())
        fr = idx < N // 3
        s2, *_ = G.umeyama_scale(src[~fr], dst[~fr]); print("  without first-third frames", s2, "first-third tiles", S["tiles"][idx[fr]].tolist())
        print("  tile travel of first-third frames vs middle mean (mm)", np.round(1000*np.linalg.norm(dst[fr]-dst[~fr].mean(0),axis=1)).tolist(), "slam travel*s", np.round(1000*s2*np.linalg.norm(src[fr]-src[~fr].mean(0),axis=1)).tolist())
