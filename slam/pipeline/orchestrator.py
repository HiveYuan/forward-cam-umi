"""Run an experiment config: producers (cached), then analysis, then the report.

  python -m slam.run experiments/<exp>/config.yaml [--dry-run] [--repro slam.E3[=N]]

Layout:
  experiments/<exp>/config.yaml, README.md        written by hand, committed before running
  experiments/<exp>/run.json                      provenance of every invocation (appended)
  experiments/<exp>/results/                      small metrics (md/json), committed after
  <work>/cache/<step>/<key>/epNN/                 producer outputs, shared across experiments
  <work>/runs/<exp>/<variant>/{view,results}/     analysis (variant 'main', 'repro1', ...)
  <work>/runs/<exp>/logs/                         worker logs

Rules enforced here: the config must be committed and the work tree clean (except this
experiment's results/ and run.json) unless --allow-dirty; an experiment directory that
already ran with a different config is refused (start a new experiment instead).
"""
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from slam.pipeline import cache as CA
from slam.pipeline import envs as E
from slam.pipeline import hashing as H
from slam.pipeline import runinfo as RI
from slam.pipeline import spec as SP
from slam.pipeline import view as V

REPO = SP.REPO
WORK = Path(os.environ.get("SLAM_WORK", "/home/student/yuanliu-hawaii/work"))
ANALYSIS_ORDER = ("mask_compare", "scale", "labels", "evaluate", "error_decomp")
RECORDED_ENV_VARS = ("SLAM_WORK", "HEADCAM_DATA_REPO", "CUDA_VISIBLE_DEVICES", "PYTORCH_CUDA_ALLOC_CONF",
                     "HF_HOME", "HF_HUB_CACHE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_TOKEN_PATH",
                     "CONDA_ROOT", "SLAM_PY_VENV", "SLAM_PY_DROID", "SLAM_PY_SAM2", "SLAM_PY_SAM3",
                     "SLAM_PY_LEROBOT", "SLAM_GPU_LOCK")
ANALYSIS_DATA = ("gt_cam_world", "gt_ball_poses", "gt_gripper_head", "gt_gripper_wrist", "gt_gripper_dataset",
                 "ball_bundle", "handeye", "intrinsics", "tile_layout", "tags", "episodes")

# may be missing: a session without a wrist camera, sessions without a head width yet, no built-dataset
# reference; the steps that read one check it themselves (labels, sam3_v2_head)
OPTIONAL_DATA = ("gt_gripper_dataset", "gt_gripper_wrist", "gt_gripper_head")


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_config(path):
    import yaml
    text = Path(path).read_text()
    cfg = yaml.safe_load(text)
    if not isinstance(cfg, dict):
        raise SP.ConfigError(f"{path}: not a mapping")
    return cfg, H.sha256_text(text)


def segments_of(data, only=None):
    eps = json.load(open(Path(data["raw_dir"]) / f"{data['session']}_glove_episodes.json"))["episodes"]
    idx = [e["episode_index"] for e in eps]
    if data["episodes"] != "all":
        missing = set(data["episodes"]) - set(idx)
        if missing:
            raise SP.ConfigError(f"data.episodes: not in the session: {sorted(missing)}")
        idx = [i for i in idx if i in set(data["episodes"])]
    if only is not None:
        missing = set(only) - set(idx)
        if missing:
            raise SP.ConfigError(f"--episodes: not among the experiment's episodes: {sorted(missing)}")
        idx = [i for i in idx if i in set(only)]
    return [f"ep{i:02d}" for i in idx]


class Runner:
    def __init__(self, config_path, args):
        self.args = args
        self.config_path = Path(config_path).resolve()
        self.cfg, self.cfg_sha = load_config(self.config_path)
        self.order, self.analysis = SP.build(self.cfg)
        self.exp = self.cfg["experiment"]
        self.exp_dir = self.config_path.parent
        if self.exp_dir.name != self.exp:
            raise SP.ConfigError(f"experiment '{self.exp}' must live in a directory of that name "
                                 f"(config is in {self.exp_dir.name}/)")
        self.in_repo = REPO in self.exp_dir.parents
        if args.episodes and self.in_repo:
            raise SP.ConfigError("--episodes is only for scratch configs outside the repository; "
                                 "set data.episodes in the config instead")
        self.data = self.cfg["data"]
        self.exec = {"jobs": 8, **(self.cfg.get("exec") or {})}
        only = [int(x) for x in args.episodes.split(",")] if args.episodes else None
        self.segments = segments_of(self.data, only)
        if not self.segments:
            raise SP.ConfigError("no segments selected")
        self.run_root = WORK / "runs" / (self.exp if self.in_repo else f"_scratch/{self.exp}")
        self.log_dir = self.run_root / "logs"
        self.files = SP.data_files(self.data)
        self.record = {"nodes": [], "variants": {}}
        self._env_versions = {}

    # ---------------------------------------------------------------- planning
    def fingerprints(self):
        names = set(ANALYSIS_DATA)
        for n in self.order:
            names |= set(n.impl.data_inputs)
        fp = {}
        for k in sorted(names):
            fp[k] = H.file_fingerprint(self.files[k])
            if fp[k] is None and k not in OPTIONAL_DATA:
                raise FileNotFoundError(f"data input '{k}' missing: {self.files[k]}")
        code = {}
        for n in self.order:
            iid = SP.impl_id(n.impl)
            if iid not in code:
                code[iid] = self.impl_fingerprint(n.impl)
        return fp, code

    def patch_files(self):
        """{checkout: {path: repo-relative patch file or None}} for every patched third-party
        checkout a node runs; prints how to save a missing one (third_party_patches/README.md)."""
        out = {}
        for c in sorted({c for n in self.order for c in n.impl.code_inputs}):
            out[c] = {}
            for path, text in H.git_patches(c).items():
                f = REPO / "third_party_patches" / Path(c).name / H.patch_file_name(path, text)
                ok = f.exists() and f.read_text() == text
                out[c][path] = str(f.relative_to(REPO)) if ok else None
                if not ok:
                    print(f"WARNING: patch of {c} ({path}) is not saved in the repo; save it as "
                          f"{f.relative_to(REPO)} (see third_party_patches/README.md)", flush=True)
        return out

    def env_versions(self, env):
        """{python, packages: {normalised name: version}} of an environment (one subprocess)."""
        if env not in self._env_versions:
            code = ("import json, sys, importlib.metadata as m\n"
                    "d = {}\n"
                    "for x in m.distributions():\n"
                    "    d.setdefault((x.metadata['Name'] or '').lower().replace('_', '-'), x.version)\n"
                    "print(json.dumps({'python': sys.version.split()[0], 'packages': d}))")
            out = subprocess.run([E.python(env), "-c", code], capture_output=True, text=True, check=True)
            self._env_versions[env] = json.loads(out.stdout)
        return self._env_versions[env]

    def impl_fingerprint(self, impl):
        """Everything about an implementation's code that enters its nodes' keys (registry docstring)."""
        f = {}
        for rel in impl.code_files:
            f[f"src:{rel}"] = H.source_hash(REPO / rel)
        for g in impl.binaries:
            f.update({f"bin:{p}": h for p, h in H.glob_hashes(g).items()})
        for c in impl.code_inputs:
            f[f"git:{c}"] = H.git_state(c)
        if impl.env_packages:
            ev = self.env_versions(impl.env)
            f[f"python:{impl.env}"] = ev["python"]
            for pkg in impl.env_packages:
                v = ev["packages"].get(pkg.lower().replace("_", "-"))
                if v is not None:
                    f[f"pkg:{pkg}"] = v
        for t in impl.tools:
            f[f"tool:{t}"] = tool_version(t)
        return f

    def plan(self, tags=None):
        self.data_fp, self.code_fp = getattr(self, "data_fp", None), getattr(self, "code_fp", None)
        if self.data_fp is None:
            self.data_fp, self.code_fp = self.fingerprints()
        SP.compute_keys(self.order, self.data_fp, self.code_fp, tags)
        return self.order

    def entry(self, n):
        e = {"id": n.id, "step": n.step, "name": n.name, "key": n.key, "params": n.params,
             "dir": str(CA.node_dir(WORK, n.step, n.key))}
        if n.step == "depth":
            e["run"] = n.deps["slam"].split(".", 1)[1]
            e["model"] = n.params["model"]
        return e

    def print_plan(self, order):
        print(f"experiment {self.exp}: {len(self.segments)} segments, work {WORK}")
        for n in order:
            d = CA.node_dir(WORK, n.step, n.key)
            have = len(CA.done_segments(d) & set(self.segments))
            print(f"  {n.id:<24} {n.impl.env:<6} {n.impl.name:<16} key {n.key}  "
                  f"cached {have}/{len(self.segments)}")

    # ---------------------------------------------------------------- execution
    def spawn(self, env, spec, log_name):
        """Run a worker; stream its output to the console and a log file."""
        jobs = self.run_root / "jobs"
        jobs.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        jf = jobs / f"{log_name}.json"
        spec["result_file"] = str(jobs / f"{log_name}.result.json")
        Path(spec["result_file"]).unlink(missing_ok=True)
        json.dump(spec, open(jf, "w"), indent=1, default=str)
        cmd = [E.python(env), "-m", "slam.pipeline.worker", str(jf)]
        envv = dict(os.environ, PYTHONPATH=str(REPO), PYTHONUNBUFFERED="1")
        t0 = time.time()
        with open(self.log_dir / f"{log_name}.log", "a") as log:
            log.write(f"\n=== {now()} {' '.join(cmd)}\n")
            p = subprocess.Popen(cmd, cwd=REPO, env=envv, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                log.write(line)
                log.flush()
                print(f"  | {line}", end="", flush=True)
            rc = p.wait()
        if rc != 0:
            raise RuntimeError(f"worker {log_name} failed (exit {rc}); see {self.log_dir / (log_name + '.log')}")
        res = json.load(open(spec["result_file"]))
        res["wall_s"] = time.time() - t0
        return res

    def wait_gpu(self, need_gb, what):
        if need_gb <= 0:
            return None
        deadline = time.time() + 60 * self.args.gpu_wait_min
        while True:
            free = RI.gpu_free_mb()
            if free is None:
                raise RuntimeError("nvidia-smi failed: no GPU information")
            if free >= need_gb * 1024:
                return free
            if time.time() > deadline:
                raise RuntimeError(f"{what}: needs {need_gb} GB free GPU memory, {free / 1024:.1f} GB free")
            print(f"  waiting for GPU: {what} needs {need_gb} GB, {free / 1024:.1f} GB free", flush=True)
            time.sleep(60)

    @contextmanager
    def gpu_slot(self, need_gb, what):
        """Exclusive GPU use across slam.run invocations (a lock file under <work>), then wait
        for enough free memory (other users of the card are outside our control)."""
        if need_gb <= 0:
            yield None
            return
        p = Path(os.environ.get("SLAM_GPU_LOCK", WORK / "locks" / "gpu.lock"))
        p.parent.mkdir(parents=True, exist_ok=True)
        f = open(p, "w")
        try:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(f"  waiting for the GPU lock {p} (another slam.run is using the GPU)", flush=True)
                fcntl.flock(f, fcntl.LOCK_EX)
            yield self.wait_gpu(need_gb, what)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def base_spec(self, n=None):
        return {"data": self.data, "exec": self.exec, "experiment": {"name": self.exp, "dir": str(self.exp_dir)},
                "work": str(WORK)}

    def run_producer(self, n, by_id):
        d = CA.node_dir(WORK, n.step, n.key)
        todo = CA.missing_segments(d, self.segments)
        rec = {"id": n.id, "variant": self.variant, "tag": self.tags.get(n.id),
               "step": n.step, "impl": n.impl.name, "env": n.impl.env, "key": n.key,
               "cache_dir": str(d), "segments_cached": len(self.segments) - len(todo),
               "segments_computed": 0, "start": now()}
        self.record["nodes"].append(rec)
        if not todo:
            rec.update(status="hit", end=now())
            return rec
        with CA.lock(d):
            todo = CA.missing_segments(d, self.segments)
            if not todo:                                   # finished by another run while we waited
                rec.update(status="hit", segments_cached=len(self.segments), end=now())
                return rec
            CA.clean_tmp(d)
            CA.write_manifest(d, {"step": n.step, "impl": n.impl.name, "version": n.impl.version,
                                  "params": n.hash_params, "data": n.data_fp,
                                  "deps": {r: (sorted(by_id[x].key for x in v) if isinstance(v, list) else by_id[v].key)
                                           for r, v in n.deps.items()},
                                  "tag": self.tags.get(n.id), "key": n.key,
                                  "created": {"experiment": self.exp, "time": now(), "node": n.id,
                                              "git": self.git["commit"], "git_clean": self.git["clean"],
                                              "params_as_given": n.params}})
            spec = self.base_spec()
            spec.update(func=n.impl.func, params=n.params, node={"id": n.id, "step": n.step, "name": n.name,
                                                               "impl": n.impl.name, "key": n.key},
                        out_dir=str(d), inputs={x: self.entry(by_id[x]) for x in n.dep_ids()},
                        exec={**n.impl.exec_params, **{k: v for k, v in self.exec.items() if k in n.impl.exec_params}})
            batches = [[s] for s in todo] if n.impl.per_segment_process else [todo]
            results = []
            for b in batches:
                name = f"{n.id}.{n.key}" + (f".{b[0]}" if n.impl.per_segment_process else "")
                spec.update(segments=b, scratch=str(self.run_root / "scratch" / name))
                with self.gpu_slot(n.impl.gpu_gb, f"{n.id} {b[0]}") as free:
                    rec.setdefault("gpu_free_mb_at_start", free)
                    results.append(self.spawn(n.impl.env, spec, name))
                shutil.rmtree(self.run_root / "scratch" / name, ignore_errors=True)
            missing = CA.missing_segments(d, self.segments)
            if missing:
                raise RuntimeError(f"{n.id}: segments not produced: {missing}")
        rec.update(status="computed", segments_computed=len(todo), end=now(),
                   runtime_s=sum(r["runtime_s"] for r in results),
                   results=[r.get("result") for r in results][:50])
        return rec

    def run_producers(self, order):
        by_id = {n.id: n for n in order}
        for n in order:
            print(f"[{now()}] {n.id} ({n.impl.env}/{n.impl.name}, key {n.key})", flush=True)
            r = self.run_producer(n, by_id)
            print(f"    {r['status']}: {r['segments_cached']} cached, {r['segments_computed']} computed", flush=True)

    def run_analysis(self, variant, order):
        """Analysis on a fresh view of `order`'s cached outputs; results in <run_root>/<variant>/results."""
        root = self.run_root / variant
        vroot = root / "view"
        V.build(vroot, self.data["session"], self.segments, self.data["gt_dir"],
                [self.entry(n) for n in order])
        res_dir = root / "results"
        if res_dir.exists():
            shutil.rmtree(res_dir)
        res_dir.mkdir(parents=True)
        an = dict(self.analysis)
        an["slam_runs"] = {n.name: {"impl": n.impl.name, "masks": [by.split(".", 1)[1] for by in n.deps["masks"]],
                                    "dilate_px": n.params.get("dilate_px"), "key": n.key,
                                    "dir": str(CA.node_dir(WORK, n.step, n.key))}
                           for n in order if n.step == "slam"}
        rec = {"view": str(vroot), "results": str(res_dir), "steps": {}}
        for step in ANALYSIS_ORDER:
            if not self.analysis.get(step):
                continue
            from slam.pipeline import registry as R
            impl = R.get(step, "default")
            spec = self.base_spec()
            spec.update(func=impl.func, params=(self.analysis[step] or {}).get("params", {}) if step != "scale" else {},
                        node={"id": step, "step": step, "name": step, "impl": "default", "key": None},
                        out_dir=str(res_dir), inputs={n.id: self.entry(n) for n in order},
                        analysis=an, segments=self.segments, work=str(vroot), variant=variant,
                        scratch=str(root / "scratch" / step))
            print(f"[{now()}] {variant}: {step}", flush=True)
            r = self.spawn("venv", spec, f"{variant}.{step}")
            rec["steps"][step] = {"runtime_s": r["runtime_s"], "result": r.get("result")}
        self.record["variants"][variant] = rec
        return res_dir

    def run_report(self, variants):
        if self.analysis.get("report") is None:
            return
        from slam.pipeline import registry as R
        impl = R.get("report", "default")
        out = self.exp_dir / "results"
        tmp = self.exp_dir / ".results.tmp"
        if tmp.exists():
            shutil.rmtree(tmp)
        spec = self.base_spec()
        spec.update(func=impl.func, params=self.analysis["report"]["params"],
                    node={"id": "report", "step": "report", "name": "report", "impl": "default", "key": None},
                    out_dir=str(tmp), analysis=self.analysis, segments=self.segments,
                    variants={v: str(self.run_root / v / "results") for v in variants},
                    repro=self.repro_info, experiments_root=str(REPO / "experiments"),
                    scratch=str(self.run_root / "scratch" / "report"))
        print(f"[{now()}] report -> {out}", flush=True)
        self.spawn("venv", spec, "report")
        if out.exists():                                   # replaced only by a complete report
            shutil.rmtree(out)
        os.rename(tmp, out)

    # ---------------------------------------------------------------- run.json
    def run_json_path(self):
        return self.exp_dir / "run.json"

    def check_previous(self, keys):
        """Earlier invocations. A different config is refused; so is a completed run at another
        commit or with other cache keys (its results would be silently replaced). Resuming a
        failed run, or re-running a completed one unchanged (e.g. to add --repro), is allowed."""
        p = self.run_json_path()
        if not p.exists():
            if (self.exp_dir / "results").exists() and any((self.exp_dir / "results").iterdir()):
                raise SP.ConfigError(f"{self.exp_dir.name}/results exists without run.json; start a new experiment")
            return []
        inv = json.load(open(p)).get("invocations", [])
        for i in inv:
            if i.get("config_sha256") != self.cfg_sha:
                raise SP.ConfigError(f"{self.exp_dir.name} already ran with a different config "
                                     f"(sha {i['config_sha256'][:12]}); start a new experiment")
            if i.get("status") == "complete":
                if i["git"]["commit"] != self.git["commit"] or i.get("keys", keys) != keys:
                    raise SP.ConfigError(f"{self.exp_dir.name} already completed at commit "
                                         f"{i['git']['commit'][:10]} with other code or cache keys; "
                                         "start a new experiment")
        return inv

    def write_run_json(self, inv, previous):
        out = {"experiment": self.exp, "config": str(self.config_path.relative_to(REPO))
               if self.in_repo else str(self.config_path), "invocations": previous + [inv]}
        p = self.run_json_path()
        tmp = p.with_suffix(".json.tmp")
        json.dump(out, open(tmp, "w"), indent=1, default=str)
        os.replace(tmp, p)

    # ---------------------------------------------------------------- main
    def main(self):
        a = self.args
        rel = self.exp_dir.relative_to(REPO) if self.in_repo else None
        # run outputs of any experiment (this one, or one running alongside) are not code
        ignore = (["experiments/*/results", "experiments/*/run.json", "experiments/*/.results.tmp"]
                  if rel else [])
        self.git = RI.git_repo_state(REPO, ignore)
        self.tags, self.repro_info, self.variant = {}, None, "main"
        order = self.plan()
        self.print_plan(order)
        if a.repro:                                     # fail before computing anything
            node, _, n_rep = a.repro.partition("=")
            if node not in {n.id for n in order} or not (n_rep or "1").isdigit():
                raise SP.ConfigError(f"--repro: expected NODE[=N], NODE one of {[n.id for n in order]}; "
                                     f"got {a.repro!r}")
        if a.dry_run:
            return
        if self.in_repo:
            tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch",
                                      str(self.config_path)], capture_output=True).returncode == 0
            if not self.git["clean"] or not tracked:
                msg = ("config.yaml is not committed" if not tracked else
                       "work tree is not clean:\n  " + "\n  ".join(self.git["dirty_files"][:20]))
                if not a.allow_dirty:
                    raise SystemExit(f"refusing to run: {msg}\n(commit first, or --allow-dirty for a test)")
                print(f"WARNING: {msg}", flush=True)
        self.run_root.mkdir(parents=True, exist_ok=True)
        self._exp_lock = open(self.run_root / ".lock", "w")
        try:
            fcntl.flock(self._exp_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"another slam.run of {self.exp} is running") from None
        keys = {n.id: n.key for n in order}
        previous = self.check_previous(keys) if self.in_repo else []
        inv = {"start": now(), "status": "running",
               "command": list(getattr(sys, "orig_argv", [sys.executable] + sys.argv)),
               "env_vars": {k: os.environ[k] for k in RECORDED_ENV_VARS if k in os.environ},
               "cwd": os.getcwd(), "config_sha256": self.cfg_sha, "git": self.git, "keys": keys,
               "scratch": not self.in_repo, "segments": self.segments, "host": RI.host_info(),
               "gpu": RI.gpu_info(), "data_fingerprints": self.data_fp, "code_fingerprints": self.code_fp,
               "seeds": {n.id: n.params["seed"] for n in order if "seed" in n.params},
               "weights": RI.weights_of(order), "third_party_patches": self.patch_files(),
               "envs": {}, "record": self.record}
        for env in sorted({n.impl.env for n in order} | {"venv"}):
            try:
                inv["envs"][env] = E.snapshot(env)
            except Exception as err:                       # recorded, not fatal
                inv["envs"][env] = {"error": repr(err)}
        if self.in_repo:
            self.write_run_json(inv, previous)
        t0 = time.time()
        try:
            self.run_producers(order)
            variants = ["main"]
            self.run_analysis("main", order)
            if a.repro:
                node, _, n_rep = a.repro.partition("=")
                ids = {n.id for n in order}
                if node not in ids:
                    raise SP.ConfigError(f"--repro: unknown node {node!r}; nodes {sorted(ids)}")
                self.repro_info = {"node": node, "runs": []}
                for i in range(1, int(n_rep or 1) + 1):
                    tag = f"repro{i}"
                    affected = SP.descendants(order, node)
                    order_r = SP.compute_keys(_clone(order), self.data_fp, self.code_fp,
                                              {x: tag for x in affected if x == node})
                    print(f"[{now()}] repro {i}: recompute {node} (key {next(n.key for n in order_r if n.id == node)})")
                    self.tags, self.variant = {node: tag}, tag
                    self.run_producers(order_r)
                    self.run_analysis(tag, order_r)
                    variants.append(tag)
                    self.repro_info["runs"].append({"variant": tag, "keys": {n.id: n.key for n in order_r if n.id in affected}})
                self.repro_info["base_keys"] = {n.id: n.key for n in order if n.id in SP.descendants(order, node)}
            self.run_report(variants)
            inv["status"] = "complete"
        except BaseException as err:
            inv["status"] = "failed"
            inv["error"] = repr(err)
            raise
        finally:
            inv["end"] = now()
            inv["duration_s"] = time.time() - t0
            inv["repro"] = self.repro_info
            try:                                            # code must not change during a run
                g_end = RI.git_repo_state(REPO, ignore)
                inv["git_end"] = {"commit": g_end["commit"], "clean": g_end["clean"],
                                  "dirty_files": g_end["dirty_files"]}
                inv["git_changed_during_run"] = (g_end["commit"] != self.git["commit"]
                                                 or g_end["dirty_files"] != self.git["dirty_files"])
                if inv["git_changed_during_run"]:
                    print("WARNING: the repository changed while this run was going on (see run.json git_end)",
                          flush=True)
            except Exception as err:
                inv["git_end"] = {"error": repr(err)}
            try:
                inv["weights_end"] = RI.weights_of(order)        # incl. models downloaded meanwhile
            except Exception as err:
                inv["weights_end"] = {"error": repr(err)}
            if self.in_repo:
                self.write_run_json(inv, previous)
            else:
                self.run_root.mkdir(parents=True, exist_ok=True)     # a failure can precede any worker
                json.dump({"experiment": self.exp, "invocations": [inv]},
                          open(self.run_root / "run.json", "w"), indent=1, default=str)
        print(f"[{now()}] done: {self.exp} ({inv['duration_s'] / 60:.1f} min)")


def tool_version(name):
    exe = shutil.which(name)
    if exe is None:
        raise FileNotFoundError(f"tool {name!r} not found")
    out = subprocess.run([exe, "-version"], capture_output=True, text=True).stdout.splitlines()
    return f"{exe}: {out[0] if out else '?'}"


def _clone(order):
    import copy
    return [copy.copy(n) for n in order]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--dry-run", action="store_true", help="print the plan (keys, cache status) and exit")
    ap.add_argument("--allow-dirty", action="store_true", help="run with uncommitted changes (recorded)")
    ap.add_argument("--repro", default=None, metavar="NODE[=N]",
                    help="recompute NODE (e.g. slam.E3) N more times under a cache tag and compare")
    ap.add_argument("--episodes", default=None, help="scratch configs only: comma list of episodes")
    ap.add_argument("--gpu-wait-min", type=float, default=30.0, help="wait this long for free GPU memory")
    a = ap.parse_args(argv)
    Runner(a.config, a).main()


if __name__ == "__main__":
    main()
