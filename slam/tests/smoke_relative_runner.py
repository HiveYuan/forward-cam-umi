# Manual smoke test (training env, CPU): RelativeRunner through eval_grid's interface vs slam.deploy_rel replay-policy.
"""RelativeRunner through eval_grid's interface with a mock robot (fk from the recorded poses, ik = seed) and a mock
head camera (the dataset frames): its chunks must equal replay_policy's (same images, same states)."""
import json, sys
import numpy as np, torch, yaml
import packaging.version  # noqa: F401
sys.path.insert(0, "/home/student/yuanliu-hawaii/head-cam-umi-p2")
from slam import relative_dataset as RD
from slam.deploy_rel import RelativeRunner
cfgp = "/home/student/yuanliu-hawaii/head-cam-umi-slam/experiments/exp053_rel_Gslam48_startstate/config.yaml"
cfg = yaml.safe_load(open(cfgp)); v = json.load(open(cfgp.replace("config.yaml", "results/val.json")))
ck = f"{cfg['output_dir']}/checkpoints/{v['best_step_robot_val']:06d}/pretrained_model"
root = cfg["dataset"]["root"]
df = RD.read_columns(root); df = df[df["episode_index"] == 15].reset_index(drop=True)
A = RD.pose_T(np.stack(df["anchor_pose"].values).astype(float)); grip = np.stack(df["observation.state"].values).reshape(-1)
from lerobot.datasets.lerobot_dataset import LeRobotDataset
ds = LeRobotDataset(cfg["dataset"]["repo"], root=root, episodes=[15])
class Kin:
    def __init__(self): self.i = 0
    def fk(self, q): return A[int(q[0])]                      # q[0] carries the step index in this mock
    def ik(self, T, site, init_q, **kw): return True, init_q
class Head: frame = None
kin, head = Kin(), Head()
r = RelativeRunner("exp053", ck, "startpose_gripper", kin, head, "cpu", "pick red block into bin")
r.reset()
ref = np.load("/tmp/claude-1000/-home-student-yuanliu-hawaii/9f49c78d-96f2-5bcc-a33a-91f109ae187a/scratchpad/replay/exp053_rel_Gslam48_startstate_ep15.npz")["chunks"]
worst = 0.0
for t in range(20):
    img = (ds[t]["observation.images.b0587b"].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8)   # RGB HWC
    head.frame = img[:, :, ::-1].copy()                                                                   # BGR like CamReader
    q = np.array([t, 0, 0, 0, 0, 0], float)
    obs = r.obs(q, grip[t])
    obs2 = {k: v.copy() for k, v in obs.items()}
    out = r.act(obs)
    chunk = r.planner.buf[t][-1]                                                                          # newest prediction for tick t
    worst = max(worst, float(np.abs(r.policy(__import__("lerobot.policies.utils", fromlist=["x"]).prepare_observation_for_inference(obs2, torch.device("cpu"), "x", "yam")) - ref[t]).max()))
print("act() output shape", out.shape, "; max |runner chunk - replay chunk| over 20 ticks:", f"{worst:.2e}")
