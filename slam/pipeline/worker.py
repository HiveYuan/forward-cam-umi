"""Runs one step implementation inside its own Python environment.

  <env python> -m slam.pipeline.worker <job.json>

The orchestrator writes job.json; the worker configures slam.config for the experiment's
data (session settings, raw/detection/work paths), imports the implementation and calls
func(Job). Implementations only use the Job API below, so they stay independent of the
orchestrator.
"""
import importlib
import json
import sys
import time
import traceback
from pathlib import Path

from slam.pipeline import cache as CA
from slam.pipeline import view as V


class Job:
    """What an implementation gets.

    params      full parameters of this node (dict)
    exec        execution-only knobs (e.g. jobs)
    node        {id, step, name, impl, key}
    data        the config's data section; session = data['session']
    segments    segment names to produce (already-finished ones are skipped by todo())
    out_dir     cache entry (producers) or analysis directory (analysis steps)
    inputs      {node id: entry dict(step, name, dir, key, params[, run, model])} upstream
    analysis    the config's analysis spec (scale/labels/evaluate/report) for analysis steps
    """

    def __init__(self, spec):
        self.spec = spec
        self.params = spec["params"]
        self.exec = spec.get("exec", {})
        self.node = spec["node"]
        self.data = spec["data"]
        self.session = self.data["session"]
        self.segments = spec["segments"]
        self.out_dir = Path(spec["out_dir"])
        self.inputs = spec.get("inputs", {})
        self.analysis = spec.get("analysis", {})
        self.experiment = spec.get("experiment", {})
        self.scratch = Path(spec["scratch"])

    # ---------------------------------------------------------------- producers
    def todo(self):
        """Segments of this job not yet published in the cache entry."""
        return CA.missing_segments(self.out_dir, self.segments)

    def input_view(self, seg, extra=()):
        """A scratch segment directory in the legacy layout, holding this node's inputs
        (symlinks into the cache). Implementations may write outputs into it and then
        publish selected files with publish()."""
        d = self.scratch / "view" / self.session / "segments" / seg
        if d.exists():
            import shutil
            shutil.rmtree(d)
        V.link_segment(d, seg, list(self.inputs.values()) + list(extra))
        gt = self.scratch / "view" / self.session / "gt"
        if not gt.exists():
            gt.parent.mkdir(parents=True, exist_ok=True)
            gt.symlink_to(Path(self.data["gt_dir"]))
        return d

    def view_root(self):
        return self.scratch / "view"

    def tmp(self, seg):
        return CA.tmp_dir(self.out_dir, seg)

    def publish(self, seg, tmp):
        return CA.commit_segment(self.out_dir, seg, tmp)

    def input_of(self, step, name=None):
        """The single upstream entry of a step (optionally by config name)."""
        c = [e for e in self.inputs.values() if e["step"] == step and (name is None or e["name"] == name)]
        if len(c) != 1:
            raise KeyError(f"{self.node['id']}: expected one '{step}' input named {name!r}, found {len(c)}")
        return c[0]

    def pool_kwargs(self):
        """ProcessPoolExecutor kwargs so pool children see this job's slam.config (Python 3.14
        starts them with forkserver, which does not inherit configure())."""
        return {"initializer": configure, "initargs": (self.spec,)}

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {self.node['id']}: {msg}", flush=True)


def configure(spec):
    """Point slam.config at the experiment's data (session settings and paths)."""
    from slam import config as C
    d = spec["data"]
    s = {"head_stem": d["head_stem"], "intrinsics": d["intrinsics"], "glove": d["glove"],
         "tile_layout": d["tile_layout"]}
    s.update(spec.get("session_extra", {}))
    C.SESSIONS[d["session"]] = s
    C.RAW = Path(d["raw_dir"])
    C.DET_CACHE = Path(d["det_cache_dir"])
    if spec.get("work"):
        C.WORK = Path(spec["work"])
    # the session's GT (tile head poses, ball poses, gripper widths) comes from data.gt_dir,
    # whatever C.WORK is (producers run with C.WORK = <work>, not a view)
    gt, sess, orig = Path(d["gt_dir"]), d["session"], getattr(C, "_gt_dir_orig", C.gt_dir)
    C._gt_dir_orig = orig
    C.gt_dir = lambda name: gt if name == sess else orig(name)


def main():
    spec = json.load(open(sys.argv[1]))
    configure(spec)
    mod, fn = spec["func"].split(":")
    job = Job(spec)
    t0 = time.time()
    try:
        result = getattr(importlib.import_module(mod), fn)(job)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    out = Path(spec["result_file"])
    json.dump({"ok": True, "runtime_s": time.time() - t0, "result": result}, open(out, "w"),
              indent=1, default=str)


if __name__ == "__main__":
    main()
