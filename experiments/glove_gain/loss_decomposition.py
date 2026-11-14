"""Normalized L1 of the predicted chunk (VAE latent 0) on robot val, split by action group and horizon, for the
best checkpoints of T48 / G-tile48 / G-slam48 (relative actions, anchor_pose). Which dimensions carry the loss,
and where does glove data help or hurt?"""
import json, sys
from pathlib import Path
import numpy as np, torch, yaml
import packaging.version  # lerobot pretrained.py uses packaging.version without importing it
sys.path.insert(0, "/home/student/yuanliu-hawaii/head-cam-umi-slam")
from slam import config as C
from slam.val_rel import make_loader, val_episode_sets
torch.set_num_threads(16)
GROUPS = {"trans": slice(0, 3), "rot6d": slice(3, 9), "grip": slice(9, 10)}
HB = {"j0-14": slice(0, 15), "j15-49": slice(15, 50), "j50-99": slice(50, 100)}
out = {}
for e in sys.argv[1:]:
    cfg = yaml.safe_load(open(f"/home/student/yuanliu-hawaii/head-cam-umi-slam/experiments/{e}/config.yaml"))
    v = json.load(open(f"/home/student/yuanliu-hawaii/head-cam-umi-slam/experiments/{e}/results/val.json"))
    ck = Path(cfg["output_dir"]) / "checkpoints" / f"{v['best_step_robot_val']:06d}" / "pretrained_model"
    stats = json.load(open(C.REPO / cfg["relative"]["stats"]))
    mean, std = np.asarray(stats["action"]["mean"]), np.asarray(stats["action"]["std"]) + 1e-8
    from lerobot.policies import make_pre_post_processors
    from lerobot.policies.act.modeling_act import ACTPolicy
    pol = ACTPolicy.from_pretrained(str(ck)); pol.to("cpu"); pol.eval()
    pre, _ = make_pre_post_processors(pol.config, str(ck), preprocessor_overrides={"device_processor": {"device": "cpu"}})
    L = make_loader(cfg, val_episode_sets(cfg["dataset"]["root"])["robot"], 100, stats, 16, 4)
    E, V = [], []
    with torch.no_grad():
        for batch in L:
            raw, pad = batch["action"].double().numpy(), batch["action_is_pad"].numpy()
            b = pre({k: (x.to("cpu") if torch.is_tensor(x) else x) for k, x in batch.items()})
            pred = pol.predict_action_chunk(b).double().numpy()
            E.append(np.abs(pred - (raw - mean) / std)); V.append(~pad)
    E, V = np.concatenate(E), np.concatenate(V)
    r = {"l1_all": float(E[V].mean())}
    for g, s in GROUPS.items():
        r[g] = float(E[..., s][V].mean())
        for h, hs in HB.items():
            r[f"{g}@{h}"] = float(E[:, hs, s][V[:, hs]].mean())
    r["share"] = {g: float(E[..., s][V].sum() / E[V].sum()) for g, s in GROUPS.items()}
    out[e] = r
    print(e, json.dumps({k: (round(x, 4) if isinstance(x, float) else {kk: round(vv, 3) for kk, vv in x.items()}) for k, x in r.items()}), flush=True)
json.dump(out, open("/tmp/claude-1000/-home-student-yuanliu-hawaii/9f49c78d-96f2-5bcc-a33a-91f109ae187a/scratchpad/decomp.json", "w"), indent=1)
