#!/usr/bin/env python3
"""From collected sessions in the bucket to a trained policy with one command (design approved 2026-11-16).

A batch is a YAML file (experiments/batches/<batch>.yaml, see experiments/batches/README.md): which sessions, the
review overrides, the wrist / raw-video policies, the gates, the dataset to append to and the arms to train.
  python -m slam.ingest start  experiments/batches/<batch>.yaml   # detached; log <work>/ingest/<batch>/ingest.log
  python -m slam.ingest run    experiments/batches/<batch>.yaml   # foreground
  python -m slam.ingest status experiments/batches/<batch>.yaml
Every stage is skipped when its outputs exist, so a stopped or failed run continues where it was.

Per session, three lanes run side by side (CPU: 1-3, GPU: 4, export: 5-6):
 1 fetch   the session's small files and its head video from the bucket (sizes checked against the bucket;
           <video>.fingerprint written, slam.pipeline.hashing)
 2 check   slam.collect check; calibration prerequisites. A missing unit calibration or tile layout STOPS the
           batch: those need a human look (slam.collect bundles / toolframe / holds / layout, then overlays)
 3 prep    slam.collect prep. wrist: crosscheck_transient downloads the wrist video, runs the cross-check and
           deletes the local copy (the bucket keeps it); keep keeps it; none skips the cross-check
 4 slam    the session's experiment config (slam.collect.build_config with the batch's overrides; an existing
           experiment with the identical config is reused), committed; slam.run under the GPU lock; results
           committed
 5 gate    slam.collect_dataset export: episodes without SLAM / scale / gripper coverage are dropped; a session
           failing a gate is HELD (not mixed) until the batch lists it in accept_held
 6 export  the session's LeRobot shard; raw_policy delete_after_export then deletes the local head video
Then for the batch (only when no session is held, blocked or failed):
 7 mix     base dataset + shards (slam.collect_dataset mix), then slam.collect_dataset verify
 8 train   per arm: a config from the template arm with the mix, the template's episodes + the collected ones,
           committed; train + val under the GPU lock with >= min_free_gb free; optimizer states deleted; committed
 9 report  experiments/batches/<batch>/report.md (+ summary.json), committed
Commits are local; nothing is pushed.
"""
import argparse
import copy
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from slam import config as C

V = os.environ.get("V", "/home/student/yuanliu-hawaii/.venv-headcam/bin/python")
L52 = os.environ.get("L52", "/home/student/miniconda3/envs/lerobot52/bin/python")
ENV_SH = os.environ.get("INGEST_ENV_SH", "/home/student/.config/yuanliu/env.sh")
GPU_LOCK = Path(os.environ.get("GPU_LOCK", str(C.WORK / "locks" / "gpu.lock")))
EXPORT_HELD = 3

DEFAULTS = {
    "bucket": None,                      # gs://<bucket>/<prefix>: <prefix>/data/raw, <prefix>/calib
    "sessions": [],                      # names, or {glob: "yuan_slam_*"} over the bucket's sessions
    "overrides": {},                     # {session: {include: [eps], exclude: [eps]}} after review
    "wrist": "crosscheck_transient",     # crosscheck_transient | keep | none
    "raw_policy": "keep",                # keep | delete_after_export
    "min_free_gb": 40,
    "gates": {"label_err_1s_mm_max": 8.0, "slam_valid_min": 0.9, "grip_coverage_min": 0.7,
              "max_rejected_fraction": 0.3},
    "accept_held": [],
    "slam": {"run": "E3", "masks": "sam3_v2_head", "gripper": "head", "target_fps": 26.27,
             "scale": None},             # None: the template's scale; {primary: Bpar, params: {...}} replaces it
    "dataset": {"base": {"repo": "pilot_mix_gHs3_rel_slam_v3",
                         "root": str(C.WORK / "lerobot" / "pilot_mix_gHs3_rel_slam_v3"),
                         "glove_first_episode": 178},
                "out": None, "out_root": str(C.WORK / "lerobot"), "shard_root": str(C.WORK / "lerobot" / "shards"),
                "fps": 15.0, "slow": 2.5, "bridge_s": 0.3, "gripper_median_s": 0.3, "grip_label_tol_s": 0.12,
                "task": "base_glove",
                "val_fraction": 0.1},        # per session, evenly spread in recording order: "collected val"
    "train": [],                         # [{exp, template, sessions: all | [names], overrides: {dotted: value}}]
    "compare": [],                       # earlier arms for the report's table
    "reference": {"exp": "exp049_joint_G48",  # Yosub's paper arm (arm 4, mix_gHs3_48, joint space): our reproduction
                  "paper_val": 0.2946},       # gives the physical errors; his published robot val is shown with them
    "commit": True,                      # false: write configs / results / report but commit nothing (tests)
}


def _merge(d, u):
    out = copy.deepcopy(d)
    for k, v in (u or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_batch(path):
    import yaml
    raw = yaml.safe_load(open(path))
    unknown = set(raw) - set(DEFAULTS) - {"batch", "description"}
    if unknown:
        raise SystemExit(f"{path}: unknown keys {sorted(unknown)}")
    b = _merge(DEFAULTS, raw)
    if not b.get("batch") or not re.fullmatch(r"[A-Za-z0-9_.-]+", b["batch"]):
        raise SystemExit(f"{path}: `batch` must be a plain name")
    if not b["bucket"]:
        raise SystemExit(f"{path}: `bucket` is required")
    if b["wrist"] not in ("crosscheck_transient", "keep", "none"):
        raise SystemExit(f"{path}: wrist must be crosscheck_transient, keep or none")
    if b["raw_policy"] not in ("keep", "delete_after_export"):
        raise SystemExit(f"{path}: raw_policy must be keep or delete_after_export")
    if b["train"] and not b["dataset"]["out"]:
        raise SystemExit(f"{path}: dataset.out is required to train")
    if isinstance(raw.get("reference"), str):              # reference: <exp> is shorthand for {exp: <exp>}
        b["reference"] = {"exp": raw["reference"], "paper_val": None}
    b["dataset"]["slam_run"] = b["slam"]["run"]
    b["_path"] = str(Path(path).resolve())
    return b


def batch_dir(b):
    p = C.WORK / "ingest" / b["batch"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def free_gb():
    st = os.statvfs(str(C.WORK))
    return st.f_bavail * st.f_frsize / 1e9


def sh_env():
    env = dict(os.environ, HEADCAM_DATA_REPO=str(C.COLLECT_REPO), COLLECT_REPO=str(C.COLLECT_REPO),
               PYTHONPATH=os.pathsep.join(filter(None, [str(C.REPO), os.environ.get("PYTHONPATH")])))
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    env.setdefault("HF_TOKEN_PATH", "/home/student/.config/yuanliu/hf_token")
    return env


# ---------------------------------------------------------------- bucket
def bucket_ls(url, tries=3):
    """{object name: size} for a gcloud storage ls pattern (empty when nothing matches). A failing gcloud (network,
    credentials) is retried, then raises RuntimeError: it must not look like an empty bucket."""
    for i in range(tries):
        r = subprocess.run(["gcloud", "storage", "ls", "-l", url], capture_output=True, text=True)
        if r.returncode == 0 or "matched no objects" in r.stderr:
            break
        time.sleep(10 * (i + 1))
    else:
        raise RuntimeError(f"gcloud storage ls {url} failed: {r.stderr.strip()[-300:]}")
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit() and parts[-1].startswith("gs://"):
            out[parts[-1].rsplit("/", 1)[1]] = int(parts[0])
    return out


class Stop(Exception):
    """The batch cannot continue without a human decision."""


class Ingest:
    def __init__(self, batch_path):
        self.b = load_batch(batch_path)
        self.dir = batch_dir(self.b)
        (self.dir / "logs").mkdir(exist_ok=True)
        self.raw = C.COLLECT_REPO / "data/raw"
        self.state_p = self.dir / "state.json"
        self.state = json.load(open(self.state_p)) if self.state_p.exists() else {"sessions": {}}
        self.lock, self.git_lock = threading.Lock(), threading.Lock()
        self.stop_reason = None
        self.prep_done, self.slam_done = {}, {}

    # ------------------------------------------------------------ bookkeeping
    def log(self, msg):
        line = f"[{time.strftime('%F %T')}] {msg}"
        print(line, flush=True)

    def st(self, ds):
        return self.state["sessions"].setdefault(ds, {})

    def set(self, ds, **kv):
        with self.lock:
            self.st(ds).update(kv)
            tmp = self.state_p.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(self.state, f, indent=1)
            tmp.replace(self.state_p)

    def run(self, cmd, log_name, env=None, cwd=None):
        cmd = [str(c) for c in cmd]
        lp = self.dir / "logs" / log_name
        with open(lp, "a") as f:
            f.write(f"\n# {time.strftime('%F %T')} {' '.join(cmd)}\n")
            f.flush()
            rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env or sh_env(),
                                cwd=str(cwd or C.REPO)).returncode
        return rc

    def git(self, *a, check=True):
        r = subprocess.run(["git", "-C", str(C.REPO), *a], capture_output=True, text=True)
        if check and r.returncode:
            raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()}")
        return r.stdout

    def commit(self, paths, msg):
        if not self.b["commit"]:
            self.log(f"(commit: false) not committed: {msg}")
            return None
        with self.git_lock:
            self.git("add", *[str(p) for p in paths])
            if not self.git("diff", "--cached", "--name-only").strip():
                return None
            self.git("commit", "-q", "-m", f"{msg}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
            sha = self.git("rev-parse", "--short", "HEAD").strip()
            self.log(f"committed {sha}: {msg}")
            return sha

    def wait_disk(self, need_gb, what):
        t0 = time.time()
        while free_gb() < need_gb:
            if self.stop_reason:
                raise Stop(self.stop_reason)
            if time.time() - t0 > 2 * 3600:
                raise Stop(f"{what}: {free_gb():.0f} GB free, {need_gb:.0f} GB needed for 2 h; free disk space "
                           f"(or set raw_policy: delete_after_export) and run again")
            self.log(f"{what}: waiting for disk ({free_gb():.0f} GB free, {need_gb:.0f} GB needed)")
            time.sleep(300)

    # ------------------------------------------------------------ sessions
    def resolve_sessions(self):
        s = self.b["sessions"]
        if isinstance(s, list):
            return list(s)
        names = bucket_ls(f"{self.b['bucket']}/data/raw/*_session.json")
        found = sorted(n[: -len("_session.json")] for n in names if fnmatch.fnmatch(n[: -len("_session.json")], s["glob"]))
        return found

    def fetch(self, ds, name, dst_dir, big=False):
        """Download one bucket object (data/raw or calib) if it is missing or its size differs."""
        sub = "calib" if dst_dir.name == "calib" else "data/raw"
        dst = dst_dir / name
        try:
            sizes = bucket_ls(f"{self.b['bucket']}/{sub}/{name}")
        except RuntimeError as ex:
            if dst.exists():
                self.log(f"{ds}: WARN bucket not reachable ({ex}); using the local {name}")
                return True
            raise
        if name not in sizes:
            return False
        if dst.exists() and dst.stat().st_size == sizes[name]:
            return True
        if big:
            self.wait_disk(sizes[name] / 1e9 + self.b["min_free_gb"], f"{ds}: download {name}")
            self.log(f"{ds}: downloading {name} ({sizes[name] / 1e9:.1f} GB)")
        dst_dir.mkdir(parents=True, exist_ok=True)
        rc = self.run(["gcloud", "storage", "cp", f"{self.b['bucket']}/{sub}/{name}", str(dst_dir) + "/"],
                      f"{ds}_fetch.log")
        if rc or not dst.exists() or dst.stat().st_size != sizes[name]:
            if dst.exists():
                dst.unlink()
            raise RuntimeError(f"{ds}: download of {name} failed or has the wrong size")
        return True

    def head_video(self, ds):
        return self.raw / f"{C.session(ds)['head_stem']}.mkv"

    def ensure_head(self, ds):
        """The head video on disk (downloaded again after delete_after_export) with a fresh fingerprint sidecar."""
        from slam.pipeline import hashing as H
        mkv = self.head_video(ds)
        if not mkv.exists() and not self.fetch(ds, mkv.name, self.raw, big=True):
            raise RuntimeError(f"{ds}: {mkv.name} is neither on disk nor in the bucket")
        H.write_sidecar(mkv)
        return mkv

    def stage_fetch(self, ds):
        try:
            small = [n for n in bucket_ls(f"{self.b['bucket']}/data/raw/{ds}_*") if not n.endswith(".mkv")]
        except RuntimeError as ex:
            if not (self.raw / f"{ds}_session.json").exists():
                raise
            self.log(f"{ds}: WARN bucket not reachable ({ex}); using the local files")
            small = []
        if small and f"{ds}_session.json" not in small:
            raise Stop(f"{ds}: no {ds}_session.json in {self.b['bucket']}/data/raw")
        for n in small:
            self.fetch(ds, n, self.raw)
        # the session registers itself from its metadata (slam.config); refresh the registry in this process
        if ds not in C.SESSIONS:
            C._register_collected()
        s = C.session(ds)
        for name in filter(None, [s["intrinsics"], s.get("wrist_intrinsics"), s["tile_layout"]]):
            n = Path(name).name
            if not ((C.CALIB / name).exists() or (C.CALIB / n).exists() or (C.COLLECT_REPO / "calib" / n).exists()):
                self.fetch(ds, n, C.COLLECT_REPO / "calib")
        mkv = self.head_video(ds)
        side = mkv.with_name(mkv.name + ".fingerprint")
        if not mkv.exists() and side.exists() and self.prep_outputs_ok(ds, wrist=False):
            # deleted after processing; stage_slam / stage_export download it again if they still need it
            self.log(f"{ds}: head video deleted after processing (fingerprint kept), not fetched now")
            return
        self.ensure_head(ds)

    def calib_check(self, ds):
        from slam import collect as K
        s = C.session(ds)
        missing = [f"{k} ({p.name})" for k, p in K.unit_files(s["glove"]).items() if not p.exists()]
        if missing:
            raise Stop(f"{ds}: glove unit {s['glove']} lacks {', '.join(missing)}. Calibrate it once "
                       f"(docs/SLAM_COLLECTION.md section 5: slam.collect bundles, toolframe, holds) and review the "
                       f"overlays, then run the batch again")
        if not (C.CALIB / s["tile_layout"]).exists():
            take = (json.load(open(self.raw / f"{ds}_session.json")).get("tiles") or {}).get("layout_take")
            raise Stop(f"{ds}: tile layout {s['tile_layout']} is not solved: python -m slam.collect layout {take} "
                       f"--unit {s['glove']} --intr {s['intrinsics']}, check it, then run the batch again")

    def wants_wrist(self, ds):
        return self.b["wrist"] != "none" and bool(C.session(ds).get("wrist_intrinsics"))

    def prep_outputs_ok(self, ds, wrist=None):
        gt, stem = C.gt_dir(ds), C.session(ds)["head_stem"]
        ok = all((gt / f).exists() for f in ("ball_poses.npz", f"{stem}_cam_world.json", "gripper_head.npz"))
        if wrist is None:
            wrist = self.wants_wrist(ds)
        return ok and (not wrist or (gt / "width_crosscheck.json").exists())

    def stage_prep(self, ds):
        if self.prep_outputs_ok(ds):
            return "done"
        fish = self.raw / f"{ds}_fish.mkv"
        wrist = self.wants_wrist(ds)
        if wrist and not (C.gt_dir(ds) / "width_crosscheck.json").exists():
            if not self.fetch(ds, fish.name, self.raw, big=True):
                self.log(f"{ds}: no wrist video in the bucket; prep without the cross-check")
                wrist = False
        self.run([V, "-m", "slam.collect", "check", ds], f"{ds}_check.log")
        self.log(f"{ds}: prep")
        rc = self.run([V, "-m", "slam.collect", "prep", ds], f"{ds}_prep.log")
        if rc:
            raise RuntimeError(f"{ds}: slam.collect prep failed (rc {rc}, logs/{ds}_prep.log)")
        if wrist and self.b["wrist"] == "crosscheck_transient" and fish.exists():
            if (C.gt_dir(ds) / "width_crosscheck.json").exists():
                fish.unlink()
                self.log(f"{ds}: cross-check written; local wrist video deleted (the bucket keeps it)")
            else:
                self.log(f"{ds}: cross-check missing; wrist video kept for inspection")
        if not self.prep_outputs_ok(ds, wrist=wrist):
            raise RuntimeError(f"{ds}: prep outputs incomplete (logs/{ds}_prep.log)")
        return "done"

    # ------------------------------------------------------------ SLAM
    def experiment_for(self, ds):
        """The experiment whose config equals the one this batch wants (reused), else a new colNNN."""
        import yaml
        from slam import collect as K
        sl, ov = self.b["slam"], self.b["overrides"].get(ds) or {}
        kw = dict(masks=sl["masks"], gripper=sl["gripper"], target_fps=sl["target_fps"],
                  include=ov.get("include", []), exclude=ov.get("exclude", []), scale=sl.get("scale"))
        want, _, _ = K.build_config(ds, "x", **kw)
        want.pop("experiment")
        same = []
        for p in sorted((C.REPO / "experiments").glob("col[0-9][0-9][0-9]_*/config.yaml")):
            c = yaml.safe_load(open(p))
            if (c.get("data") or {}).get("session") == ds:
                c.pop("experiment", None)
                if c == want:
                    same.append(p.parent.name)
        if same:
            done = [e for e in same if self.slam_complete(e)]
            return (done or same)[-1], False
        nums = [int(p.name[3:6]) for p in (C.REPO / "experiments").glob("col[0-9][0-9][0-9]_*")]
        exp = f"col{max(nums, default=0) + 1:03d}_{ds}"
        cfg, head, warn = K.build_config(ds, exp, **kw)
        for w in warn:
            self.log(f"{ds}: WARN {w}")
        out = C.REPO / "experiments" / exp / "config.yaml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(K.config_text(cfg, head))
        self.commit([out], f"{exp}: SLAM config for {ds} (batch {self.b['batch']})")
        return exp, True

    @staticmethod
    def slam_complete(exp):
        p = C.REPO / "experiments" / exp / "run.json"
        if not p.exists():
            return False
        inv = json.load(open(p)).get("invocations") or []
        return bool(inv) and inv[-1].get("status") == "complete"

    def stage_slam(self, ds):
        exp, new = self.experiment_for(ds)
        self.set(ds, experiment=exp)
        if self.slam_complete(exp):
            return exp
        with self.git_lock:
            dirty = [l for l in self.git("status", "--porcelain").splitlines()
                     if not re.search(r"experiments/[^/]+/(results|run\.json|\.results\.tmp)", l)]
        if dirty:
            raise Stop(f"{ds}: the work tree of {C.REPO} is not clean ({dirty[:3]}); slam.run refuses to run")
        self.ensure_head(ds)
        self.log(f"{ds}: slam.run {exp} (its GPU nodes wait for the GPU lock)")
        # slam.run takes the GPU lock itself per GPU node (orchestrator.gpu_slot). Never wrap it in `flock GPU_LOCK`:
        # the child would re-open the file and wait on its parent's lock forever (2026-11-16).
        rc = self.run([V, "-m", "slam.run", f"experiments/{exp}/config.yaml"], f"{exp}_run.log",
                      env={**sh_env(), "SLAM_GPU_LOCK": str(GPU_LOCK)})
        if rc or not self.slam_complete(exp):
            raise RuntimeError(f"{ds}: slam.run {exp} failed (rc {rc}, logs/{exp}_run.log)")
        self.commit([C.REPO / "experiments" / exp / "results", C.REPO / "experiments" / exp / "run.json"],
                    f"{exp}: results, run.json")
        return exp

    # ------------------------------------------------------------ gate + export
    def session_json(self, ds):
        p = self.dir / "sessions" / f"{ds}.json"
        return json.load(open(p)) if p.exists() else None

    def export_reusable(self, sj, exp):
        """An earlier export of the same experiment with the same gates, dataset params and builder."""
        from slam import collect_dataset as CD
        d = self.b["dataset"]
        return bool(sj and sj.get("experiment") == exp and sj.get("shard") and Path(sj["shard"]).exists()
                    and sj.get("gates") == self.b["gates"] and sj.get("builder_version") == CD.BUILDER_VERSION
                    and sj.get("params") == {k: d[k] for k in CD.EXPORT_PARAMS}
                    and sj.get("base") == d["base"]["repo"])

    def stage_export(self, ds):
        exp = self.st(ds)["experiment"]
        sj = self.session_json(ds)
        if self.export_reusable(sj, exp):
            status = "exported"
        else:
            self.ensure_head(ds)
            self.log(f"{ds}: gate + export ({exp})")
            rc = self.run([L52, "-m", "slam.collect_dataset", "export", "--batch", self.b["_path"], "--session", ds,
                           "--exp", exp], f"{ds}_export.log")
            sj = self.session_json(ds)
            if rc == EXPORT_HELD:
                self.set(ds, export="held", held=sj["verdict"]["reasons"])
                self.log(f"{ds}: HELD by the gates: {'; '.join(sj['verdict']['reasons'])}")
                return "held"
            if rc:
                raise RuntimeError(f"{ds}: export failed (rc {rc}, logs/{ds}_export.log)")
            status = "exported"
        self.set(ds, export=status, shard=sj["shard"], kept=len(sj["kept"]), configured=len(sj["rows"]))
        if self.b["raw_policy"] == "delete_after_export":
            mkv = self.head_video(ds)
            if mkv.exists():
                from slam.pipeline import hashing as H
                H.write_sidecar(mkv)                      # always from the file being deleted, never a stale one
                mkv.unlink()
                self.log(f"{ds}: local head video deleted (raw_policy delete_after_export; fingerprint kept)")
        return status

    # ------------------------------------------------------------ lanes
    def lane(self, name, sessions, step, wait_on=None, done=None):
        try:
            for ds in sessions:
                if wait_on is not None:
                    wait_on[ds].wait()
                    if self.st(ds).get("failed"):
                        if done is not None:
                            done[ds].set()
                        continue
                if self.stop_reason:
                    break
                try:
                    step(ds)
                except Stop as ex:
                    self.stop_reason = self.stop_reason or str(ex)
                    self.log(f"STOP: {ex}")
                    self.set(ds, failed=f"stopped: {ex}")
                except (Exception, SystemExit) as ex:     # this session fails; the others go on
                    # (SystemExit: slam.collect helpers exit on bad input; in a thread it would end the lane)
                    self.log(f"{ds}: FAILED in {name}: {type(ex).__name__}: {ex}")
                    self.set(ds, failed=f"{name}: {type(ex).__name__}: {ex}")
                finally:
                    if done is not None:
                        done[ds].set()
        finally:
            if done is not None:                          # a stop or a crash: never leave a later lane waiting
                for ds in sessions:
                    done[ds].set()

    def cpu_step(self, ds):
        if self.st(ds).get("failed"):
            self.set(ds, failed=None)
        self.stage_fetch(ds)
        self.calib_check(ds)
        self.stage_prep(ds)
        self.set(ds, prep="done")

    def gpu_step(self, ds):
        self.set(ds, slam=self.stage_slam(ds))

    def export_step(self, ds):
        self.stage_export(ds)

    def run_sessions(self, sessions):
        self.prep_done = {ds: threading.Event() for ds in sessions}
        self.slam_done = {ds: threading.Event() for ds in sessions}
        lanes = [threading.Thread(target=self.lane, args=("fetch/prep", sessions, self.cpu_step, None, self.prep_done)),
                 threading.Thread(target=self.lane, args=("slam", sessions, self.gpu_step, self.prep_done, self.slam_done)),
                 threading.Thread(target=self.lane, args=("export", sessions, self.export_step, self.slam_done, None))]
        for t in lanes:
            t.start()
        for t in lanes:
            t.join()

    # ------------------------------------------------------------ batch stages
    def stage_mix(self, sessions):
        d = self.b["dataset"]
        out = Path(d["out_root"]) / d["out"]
        shards = [self.st(ds)["shard"] for ds in sessions]
        mj = self.dir / "mix.json"
        if out.exists():
            have = json.load(open(mj))["shards"] if mj.exists() else None
            if have != [Path(s).name for s in shards]:
                raise Stop(f"{out} exists with other shards ({have}); name a new dataset.out in the batch file")
        else:
            self.log(f"mix: {d['base']['repo']} + {len(shards)} shards -> {d['out']}")
            rc = self.run([L52, "-m", "slam.collect_dataset", "mix", "--batch", self.b["_path"], "--shards", *shards],
                          "mix.log")
            if rc:
                raise Stop(f"mix failed (rc {rc}, logs/mix.log)")
        vj = self.dir / "verify.json"
        fresh = (vj.exists() and mj.exists() and json.load(open(vj)).get("dataset") == str(out)
                 and json.load(open(vj)).get("mix_time") == json.load(open(mj)).get("time"))
        if not fresh:                                      # verify.json of this very mix build, or verify again
            rc = self.run([L52, "-m", "slam.collect_dataset", "verify", "--batch", self.b["_path"]], "verify.log")
            if rc:
                raise Stop(f"verification of {out} failed (logs/verify.log, verify.json)")
        v = json.load(open(self.dir / "verify.json"))
        if v.get("problems"):
            raise Stop(f"verification of {out}: {v['problems']}")
        return out

    def train_config(self, arm, mix_root):
        import yaml
        from slam.relative_dataset import load_episode_list
        exp, tpl = arm["exp"], arm["template"]
        tcfg = yaml.safe_load(open(C.REPO / "experiments" / tpl / "config.yaml"))
        base_eps = load_episode_list(C.REPO / tcfg["dataset"]["episodes"])
        coll = json.load(open(mix_root / "meta" / "collected_episodes.json"))
        use = arm.get("sessions", "all")
        add = sorted(e for s, sp in coll.items() if use == "all" or s in use for e in sp["train"])  # val held out
        edir = C.REPO / "experiments" / exp
        edir.mkdir(parents=True, exist_ok=True)
        (edir / "train_episodes.txt").write_text(" ".join(str(e) for e in base_eps + add) + "\n")
        cfg = copy.deepcopy(tcfg)
        cfg["experiment"] = exp
        cfg["dataset"] = {"repo": mix_root.name, "root": str(mix_root),
                          "episodes": f"experiments/{exp}/train_episodes.txt"}
        cfg["output_dir"] = str(C.WORK / "train" / exp)
        if arm.get("overrides"):
            cfg["overrides"] = {**(cfg.get("overrides") or {}), **arm["overrides"]}
        head = (f"# {exp}: {tpl} on {mix_root.name} (batch {self.b['batch']}): the template's {len(base_eps)} "
                f"episodes ({tcfg['dataset']['episodes']}) + {len(add)} collected episodes "
                f"({'all sessions' if use == 'all' else ', '.join(use)}; the collected val episodes, "
                f"meta/val_episodes_collected.json, held out); everything else as {tpl}.\n"
                f"# Written by python -m slam.ingest.\n")
        (edir / "config.yaml").write_text(head + yaml.safe_dump(cfg, sort_keys=False, width=120))
        self.commit([edir / "config.yaml", edir / "train_episodes.txt"],
                    f"{exp}: training config (batch {self.b['batch']})")
        return cfg

    @staticmethod
    def train_finished(cfg):
        """The run's final checkpoint exists (lerobot writes checkpoints/last from the first save on)."""
        tc = json.load(open(C.REPO / cfg["base_train_config"]))
        steps = int((cfg.get("overrides") or {}).get("steps", tc["steps"]))
        return (Path(cfg["output_dir"]) / "checkpoints" / f"{steps:06d}" / "pretrained_model").exists()

    def stage_train(self, arm, mix_root):
        import yaml
        exp = arm["exp"]
        edir = C.REPO / "experiments" / exp
        cfg = yaml.safe_load(open(edir / "config.yaml")) if (edir / "config.yaml").exists() else None
        if cfg is not None and cfg["dataset"]["root"] != str(mix_root):
            if Path(cfg["output_dir"]).exists() or (edir / "results").exists():
                raise Stop(f"{exp} was trained on {cfg['dataset']['root']}, not {mix_root}; give the arm a new exp name")
            cfg = None                                     # an unused config for another mix: rewrite it
        if cfg is None:
            cfg = self.train_config(arm, mix_root)
        if (edir / "results" / "val.json").exists():
            return "done"
        out = Path(cfg["output_dir"])
        if not self.train_finished(cfg):
            if out.exists():
                raise Stop(f"{exp}: {out} exists without a finished training; look at it, remove it, run again")
            self.wait_disk(self.b["min_free_gb"], f"{exp}: train")
            self.log(f"{exp}: train (waits for the GPU lock)")
            # train_rel / val_rel take no lock themselves, so flock serialises them with slam.run and the queues
            rc = self.run(["flock", GPU_LOCK, L52, "-m", "slam.train_rel", f"experiments/{exp}/config.yaml"],
                          f"{exp}_train.log")
            if rc or not self.train_finished(cfg):
                raise Stop(f"{exp}: training failed (rc {rc}, logs/{exp}_train.log)")
        self.log(f"{exp}: val")
        rc = self.run(["flock", GPU_LOCK, L52, "-m", "slam.val_rel", f"experiments/{exp}/config.yaml"], f"{exp}_val.log")
        if rc:
            raise Stop(f"{exp}: validation failed (rc {rc}, logs/{exp}_val.log)")
        for p in out.glob("checkpoints/*/training_state"):
            shutil.rmtree(p)
        self.commit([p for p in (edir / "results", edir / "run.json") if p.exists()], f"{exp}: results")
        return "done"

    def crossval_arms(self):
        """Earlier relative arms evaluated on the collected val set: the templates of the trained arms + compare."""
        import yaml
        out = []
        for e in [a["template"] for a in self.b["train"]] + list(self.b["compare"]):
            p = C.REPO / "experiments" / e / "config.yaml"
            if e not in out and p.exists() and (yaml.safe_load(open(p)) or {}).get("relative"):
                out.append(e)
        return out

    def crossval_masks(self):
        """Loss masks every collected-val row is scored with: the trained arms' (their template's) masks, so that
        all rows see the same anchors and steps (exp052 trained with [] would otherwise score filler poses)."""
        import yaml
        if not self.b["train"]:
            return ["slam_valid", "ik_unreached"]
        t = yaml.safe_load(open(C.REPO / "experiments" / self.b["train"][0]["template"] / "config.yaml"))
        return list((t.get("relative") or {}).get("masks", ["slam_valid", "ik_unreached"]))

    def stage_crossval(self, exp, mix_root):
        """Arm `exp` (trained without the collected sessions) on their val episodes, at its best robot-val step."""
        import yaml
        odir = self.dir / "crossval" / exp
        if (odir / "val.json").exists():
            return "done"
        val = json.load(open(C.REPO / "experiments" / exp / "results" / "val.json"))
        cfg = yaml.safe_load(open(C.REPO / "experiments" / exp / "config.yaml"))
        cfg["dataset"] = {**cfg["dataset"], "repo": mix_root.name, "root": str(mix_root)}
        cfg["relative"] = {**cfg["relative"], "masks": self.crossval_masks()}
        odir.mkdir(parents=True, exist_ok=True)
        (odir / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False, width=120))
        self.log(f"{exp}: on the collected val episodes (step {val['best_step_robot_val']})")
        rc = self.run(["flock", GPU_LOCK, L52, "-m", "slam.val_rel", odir / "config.yaml", "--run-dir", cfg["output_dir"],
                       "--out", odir, "--sets", "collected", "--only-step", val["best_step_robot_val"]],
                      f"crossval_{exp}.log")
        if rc:
            raise Stop(f"{exp}: cross-evaluation failed (rc {rc}, logs/crossval_{exp}.log)")
        return "done"

    # ------------------------------------------------------------ report
    def report(self, sessions, mix_root=None):
        from slam import ingest_report as R
        md, summary = R.build(self, sessions, mix_root)
        rdir = C.REPO / "experiments" / "batches" / self.b["batch"]
        rdir.mkdir(parents=True, exist_ok=True)
        (rdir / "report.md").write_text(md)
        json.dump(summary, open(rdir / "summary.json", "w"), indent=1)
        self.commit([rdir], f"batch {self.b['batch']}: report")
        return rdir / "report.md"

    def acquire(self):
        """One runner per batch, whether started by `start`, `run` or a driver script (Python's open() is not
        inherited by the subprocesses, so they cannot hold it)."""
        import fcntl
        self._lockf = open(self.dir / "ingest.lock", "w")
        try:
            fcntl.flock(self._lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"batch {self.b['batch']} is already running (lock {self.dir / 'ingest.lock'})")
        (self.dir / "ingest.pid").write_text(f"{os.getpid()}\n")

    def main(self):
        self.acquire()
        sessions = self.resolve_sessions()
        if not sessions:
            raise SystemExit("no sessions")
        self.log(f"batch {self.b['batch']}: {len(sessions)} sessions: {', '.join(sessions)}")
        self.run_sessions(sessions)
        failed = {ds: self.st(ds)["failed"] for ds in sessions if self.st(ds).get("failed")}
        held = [ds for ds in sessions if self.st(ds).get("export") == "held"]
        if self.stop_reason or failed or held:
            rp = self.report(sessions)
            why = ([f"stopped: {self.stop_reason}"] if self.stop_reason else []) + \
                  [f"{ds} failed: {w}" for ds, w in failed.items()] + \
                  [f"{ds} held: {'; '.join(self.st(ds).get('held') or [])}" for ds in held]
            self.log("BATCH WAITS FOR REVIEW:\n  " + "\n  ".join(why) + f"\n  report: {rp}")
            return 2
        mix_root = None
        try:
            if self.b["dataset"]["out"]:
                mix_root = self.stage_mix(sessions)
                for arm in self.b["train"]:
                    self.state.setdefault("train", {})[arm["exp"]] = self.stage_train(arm, mix_root)
                if self.b["train"] and (mix_root / "meta" / "val_episodes_collected.json").exists():
                    for e in self.crossval_arms():
                        self.stage_crossval(e, mix_root)
        except Stop as ex:
            self.stop_reason = str(ex)
            self.log(f"STOP: {ex}")
        rp = self.report(sessions, mix_root)
        self.log(f"{'BATCH WAITS FOR REVIEW' if self.stop_reason else 'BATCH DONE'}: report {rp}")
        return 2 if self.stop_reason else 0


# ---------------------------------------------------------------- status / start
def runner_active(d):
    """Whether some runner holds the batch's lock (Ingest.acquire)."""
    import fcntl
    p = Path(d) / "ingest.lock"
    if not p.exists():
        return False
    with open(p, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
    return False


def cmd_status(a):
    b = load_batch(a.batch)
    ing = Ingest(a.batch)
    sessions = b["sessions"] if isinstance(b["sessions"], list) else sorted(ing.state["sessions"])
    print(f"batch {b['batch']}  (state {ing.state_p})  free {free_gb():.0f} GB")
    print(f"{'session':16} {'head':>5} {'prep':>5} {'xchk':>5} {'experiment':28} {'slam':>5} {'export':>9} {'kept':>9}  note")
    for ds in sessions:
        s = ing.st(ds)
        reg = ds in C.SESSIONS
        stem = C.session(ds)["head_stem"] if reg else None
        mkv = ing.raw / f"{stem}.mkv" if reg else None
        head = "yes" if mkv and mkv.exists() else ("fp" if mkv and mkv.with_name(mkv.name + ".fingerprint").exists() else "-")
        prep = "yes" if reg and ing.prep_outputs_ok(ds, wrist=False) else "-"
        xchk = "yes" if reg and (C.gt_dir(ds) / "width_crosscheck.json").exists() else "-"
        exp = s.get("experiment", "")
        slam = "done" if exp and Ingest.slam_complete(exp) else "-"
        kept = f"{s['kept']}/{s['configured']}" if s.get("kept") is not None else ""
        note = s.get("failed") or ("; ".join(s.get("held") or []))
        print(f"{ds:16} {head:>5} {prep:>5} {xchk:>5} {exp:28} {slam:>5} {s.get('export', '-'):>9} {kept:>9}  {note or ''}")
    d = b["dataset"]
    if d["out"]:
        out = Path(d["out_root"]) / d["out"]
        print(f"mix {out}: {'yes' if out.exists() else '-'}")
    for arm in b["train"]:
        r = C.REPO / "experiments" / arm["exp"] / "results" / "val.json"
        print(f"train {arm['exp']}: {'done' if r.exists() else '-'}")
    pid = ing.dir / "ingest.pid"
    if pid.exists():
        print(f"runner pid {pid.read_text().strip()}: {'running' if runner_active(ing.dir) else 'not running'}  "
              f"log {ing.dir / 'ingest.log'}")


def cmd_start(a):
    b = load_batch(a.batch)
    d = batch_dir(b)
    if runner_active(d):
        raise SystemExit(f"already running (pid {(d / 'ingest.pid').read_text().strip()}); log {d / 'ingest.log'}")
    cmd = (f"source {ENV_SH} 2>/dev/null; exec {sys.executable} -m slam.ingest run {Path(a.batch).resolve()}")
    log = open(d / "ingest.log", "a")
    p = subprocess.Popen(["setsid", "bash", "-c", cmd], stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, cwd=str(C.REPO), env=sh_env())
    print(f"started pid {p.pid}; log {d / 'ingest.log'}; status: python -m slam.ingest status {a.batch}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("run", "start", "status"):
        sub.add_parser(c).add_argument("batch")
    a = ap.parse_args()
    if a.cmd == "run":
        sys.exit(Ingest(a.batch).main())
    {"start": cmd_start, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
