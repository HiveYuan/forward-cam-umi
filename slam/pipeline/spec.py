"""Experiment config: loading, strict validation, and the producer graph.

config.yaml (all parameters written out; see experiments/README.md):

  experiment: exp001_sam2_baseline         # must equal the experiment directory name
  data: {session, episodes, head_stem, intrinsics, glove, tile_layout, raw_dir, det_cache_dir, gt_dir}
  preprocess: {impl, params}
  tiles:      {impl, params}
  masks:      {<name>: {impl, params}, ...}
  slam:       {<run>: {impl, masks: [<mask name>, ...], params}, ...}
  depth:      {<name>: {impl, runs: [<run>, ...], params}, ...}
  scale:      {<run>: {primary, checks, flag_threshold, methods: {<method>: {params}}}, ...}
  labels:     {runs: [...], params}
  evaluate:   {runs: [...], params}
  report:     {params}
  exec:       {jobs: N}                    # optional, execution only (not hashed)
"""
import copy
import inspect
import re
from dataclasses import dataclass, field
from pathlib import Path

from slam.pipeline import hashing as H
from slam.pipeline import registry as R

REPO = Path(__file__).resolve().parents[2]
CALIB = REPO / "calib"

DATA_KEYS = ("session", "episodes", "head_stem", "intrinsics", "glove", "tile_layout",
             "raw_dir", "det_cache_dir", "gt_dir")
TOP_KEYS = {"experiment", "description", "data", "preprocess", "tiles", "masks", "slam", "depth",
            "mask_compare", "scale", "labels", "evaluate", "error_decomp", "report", "exec"}
FREEFORM_PARAMS = {"prompts", "point_prompts"}           # dict-valued params whose keys are user content
# scale-method keyword arguments filled in by the framework, not by the config
SCALE_FRAMEWORK_KW = {"model", "mask_names", "mask_dilate_px", "k_session"}


class ConfigError(ValueError):
    pass


def data_files(data):
    """Named data inputs -> paths (fingerprinted into the cache keys of the nodes that read them)."""
    raw, gt = Path(data["raw_dir"]), Path(data["gt_dir"])
    stem, glove = data["head_stem"], data["glove"]
    return {
        "video": raw / f"{stem}.mkv",
        "video_ts": raw / f"{stem}_ts.json",
        "episodes": raw / f"{data['session']}_glove_episodes.json",
        "intrinsics": CALIB / data["intrinsics"],
        "tile_layout": CALIB / data["tile_layout"],
        "tags": CALIB / f"tags36h11_{glove}.json",
        "handeye": CALIB / f"handeye_glove_{glove}.json",
        "ball_bundle": CALIB / f"glove_{glove}_dodeca_bundle.json",
        "gt_cam_world": gt / f"{stem}_cam_world.json",
        "gt_ball_poses": gt / "ball_poses.npz",
        "gt_gripper_wrist": gt / "gripper_wrist.npz",
        "gt_gripper_head": gt / "gripper_head.npz",
        "gt_gripper_dataset": gt / "gripper.npz",
    }


# ---------------------------------------------------------------------- params
def _coerce(name, default, value):
    if default is None:
        return value
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ConfigError(f"{name}: expected bool, got {value!r}")
        return value
    if isinstance(default, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"{name}: expected a number, got {value!r}")
        return float(value)
    if isinstance(default, int):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{name}: expected an integer, got {value!r}")
        return value
    if isinstance(default, str):
        if not isinstance(value, str):
            raise ConfigError(f"{name}: expected a string, got {value!r}")
        return value
    if isinstance(default, list):
        if not isinstance(value, list):
            raise ConfigError(f"{name}: expected a list, got {value!r}")
        types = {type(x) for x in default}
        if len(types) == 1 and default and not isinstance(default[0], (list, dict)):
            return [_coerce(f"{name}[{i}]", default[0], v) for i, v in enumerate(value)]
        return copy.deepcopy(value)
    if isinstance(default, dict):
        if not isinstance(value, dict):
            raise ConfigError(f"{name}: expected a mapping, got {value!r}")
        if name.split(".")[-1] in FREEFORM_PARAMS or not default:
            return copy.deepcopy(value)
        return normalize_params(default, value, name)
    raise ConfigError(f"{name}: unsupported default type {type(default).__name__}")


def normalize_params(defaults, given, where="params"):
    """Every key of `defaults` must be given, no other key is allowed; values are coerced to
    the default's type (so 5 and 5.0 hash the same where a float is expected)."""
    given = {} if given is None else given
    if not isinstance(given, dict):
        raise ConfigError(f"{where}: expected a mapping, got {given!r}")
    missing = [k for k in defaults if k not in given]
    unknown = [k for k in given if k not in defaults]
    if missing or unknown:
        msg = [f"{where}: parameters must be written out in full"]
        if missing:
            msg.append("missing " + ", ".join(f"{k} (default {defaults[k]!r})" for k in missing))
        if unknown:
            msg.append("unknown " + ", ".join(unknown))
        raise ConfigError("; ".join(msg))
    return {k: _coerce(f"{where}.{k}", defaults[k], given[k]) for k in defaults}


SCALE_CHOICES = {"B": {"correction": ("faces", "disk"), "fit": ("scale", "affine")},
                 "Bsession": {"correction": ("faces", "disk"), "pool": ("segments", "samples")}}


def labels_fixed():
    """Label-grid parameters that slam.labels hard-codes (build_dataset's rules)."""
    from slam import labels as L
    return {"fps": L.FPS, "label_tol_s": L.LABEL_TOL, "min_coverage": L.MIN_COVERAGE,
            "bridge_s": L.BRIDGE, "min_episode_s": L.MIN_EPISODE}


def scale_method_defaults():
    """{method: {param: default}} from slam.scale's method signatures (config-facing params only)."""
    from slam import scale as SC
    out = {}
    for name, fn in SC.METHODS.items():
        if name in getattr(SC, "COMPOSITE_METHODS", ("B+Acheck",)):
            continue
        p = {k: v.default for k, v in inspect.signature(fn).parameters.items()
             if v.default is not inspect.Parameter.empty and k not in SCALE_FRAMEWORK_KW}
        if name in SC.TAKES_MODEL:
            p = {"depth": "", **p}                   # name of a depth node computed for the run
        out[name] = p
    return out


# ---------------------------------------------------------------------- graph
@dataclass
class Node:
    id: str                 # preprocess | tiles | masks.<name> | slam.<run> | depth.<name>@<run>
    step: str
    name: str
    impl: R.Impl
    params: dict
    deps: dict              # role -> node id, or list of node ids
    key: str = None
    data_fp: dict = field(default_factory=dict)
    hash_params: dict = None    # params as hashed (node names replaced, see compute_keys)

    def dep_ids(self):
        out = []
        for v in self.deps.values():
            out += v if isinstance(v, list) else [v]
        return out


def _need(cfg, key, where, kind=dict):
    if key not in cfg:
        raise ConfigError(f"{where}: missing '{key}'")
    if not isinstance(cfg[key], kind):
        raise ConfigError(f"{where}.{key}: expected {kind.__name__}")
    return cfg[key]


NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
RESERVED = {"tiles", "static", "oracle", "none", "all"}


def _check_name(name, where, reserved=True):
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ConfigError(f"{where}: names use letters, digits, '_' and '-' only, got {name!r}")
    if reserved and name in RESERVED:
        raise ConfigError(f"{where}: {name!r} is reserved")


def _check_choices(impl, params, where):
    for k, allowed in impl.choices.items():
        if params[k] not in allowed:
            raise ConfigError(f"{where}.params.{k}: one of {list(allowed)}, got {params[k]!r}")


def _impl_node(nid, step, name, block, where, extra=()):
    if not isinstance(block, dict) or "impl" not in block:
        raise ConfigError(f"{where}: needs 'impl' and 'params'")
    unknown = set(block) - {"impl", "params", *extra}
    if unknown:
        raise ConfigError(f"{where}: unknown keys {sorted(unknown)}; allowed {['impl', 'params', *extra]}")
    try:
        impl = R.get(step, block["impl"])
    except KeyError as err:
        raise ConfigError(f"{where}.impl: {err.args[0]}") from None
    params = normalize_params(impl.params, block.get("params"), f"{where}.params")
    _check_choices(impl, params, where)
    return Node(nid, step, name, impl, params, {})


def build(cfg):
    """Validate a loaded config; returns (producer nodes in topological order, analysis spec)."""
    unknown = set(cfg) - TOP_KEYS
    if unknown:
        raise ConfigError(f"unknown top-level keys {sorted(unknown)}")
    if not isinstance(cfg.get("experiment"), str):
        raise ConfigError("'experiment' (the experiment directory name) is required")
    data = _need(cfg, "data", "config")
    miss = [k for k in DATA_KEYS if k not in data]
    extra = [k for k in data if k not in DATA_KEYS]
    if miss or extra:
        raise ConfigError(f"data: missing {miss} / unknown {extra}")
    eps = data["episodes"]
    if not (eps == "all" or (isinstance(eps, list) and eps and
                             all(isinstance(e, int) and not isinstance(e, bool) for e in eps))):
        raise ConfigError("data.episodes: 'all' or a non-empty list of episode indices")

    nodes = {}
    pre = _impl_node("preprocess", "preprocess", "preprocess", _need(cfg, "preprocess", "config"), "preprocess")
    nodes[pre.id] = pre
    if "tiles" in cfg:
        t = _impl_node("tiles", "tiles", "tiles", cfg["tiles"], "tiles")
        t.deps = {"preprocess": pre.id}
        nodes[t.id] = t
    slam_cfg = _need(cfg, "slam", "config")
    for run in slam_cfg:
        _check_name(run, f"slam.{run}")
    for mname, block in (cfg.get("masks") or {}).items():
        _check_name(mname, f"masks.{mname}", reserved=False)
        n = _impl_node(f"masks.{mname}", "masks", mname, block, f"masks.{mname}")
        n.deps = {"preprocess": pre.id}
        if n.impl.name == "tile_geometry":
            if "tiles" not in nodes:
                raise ConfigError(f"masks.{mname}: tile_geometry needs the 'tiles' step")
            n.deps["tiles"] = "tiles"
            fb = n.params["slam_fallback"]
            if fb is not None:
                if fb not in slam_cfg:
                    raise ConfigError(f"masks.{mname}.params.slam_fallback: no slam run {fb!r}")
                n.deps["slam_fallback"] = f"slam.{fb}"
        nodes[n.id] = n
    for run, block in slam_cfg.items():
        n = _impl_node(f"slam.{run}", "slam", run, block, f"slam.{run}", extra=("masks",))
        masks = _need(block, "masks", f"slam.{run}", list)          # [] = no masks, but say so
        if not isinstance(masks, list) or any(f"masks.{m}" not in nodes for m in masks):
            raise ConfigError(f"slam.{run}.masks: list of names defined under 'masks', got {masks!r}")
        if len(set(masks)) != len(masks):
            raise ConfigError(f"slam.{run}.masks: duplicate names")
        n.deps = {"preprocess": pre.id, "masks": [f"masks.{m}" for m in masks]}
        nodes[n.id] = n
    seen_depth = {}
    for dname, block in (cfg.get("depth") or {}).items():
        _check_name(dname, f"depth.{dname}", reserved=False)
        runs = _need(block, "runs", f"depth.{dname}", list)
        proto = _impl_node("", "depth", dname, block, f"depth.{dname}", extra=("runs",))
        for run in runs:
            if f"slam.{run}" not in nodes:
                raise ConfigError(f"depth.{dname}.runs: no slam run {run!r}")
            dup = seen_depth.setdefault((run, proto.params["model"]), dname)
            if dup != dname:                               # they would share one view file
                raise ConfigError(f"depth.{dname}: run {run} already has model "
                                  f"{proto.params['model']} from depth.{dup}")
            nid = f"depth.{dname}@{run}"
            nodes[nid] = Node(nid, "depth", dname, proto.impl, proto.params,
                              {"preprocess": pre.id, "slam": f"slam.{run}"})

    order = _toposort(nodes)
    analysis = _analysis(cfg, nodes)
    return order, analysis


def _toposort(nodes):
    order, state = [], {}

    def visit(nid, path):
        if state.get(nid) == 2:
            return
        if state.get(nid) == 1:
            raise ConfigError(f"dependency cycle: {' -> '.join(path + [nid])}")
        state[nid] = 1
        for d in nodes[nid].dep_ids():
            if d not in nodes:
                raise ConfigError(f"{nid}: unknown dependency {d}")
            visit(d, path + [nid])
        state[nid] = 2
        order.append(nodes[nid])

    for nid in nodes:
        visit(nid, [])
    return order


def _analysis(cfg, nodes):
    runs = [n.name for n in nodes.values() if n.step == "slam"]
    depth_for = {}                                   # (run, depth name) -> node
    for n in nodes.values():
        if n.step == "depth":
            depth_for[(n.deps["slam"].split(".", 1)[1], n.name)] = n
    out = {"mask_compare": None, "scale": {}, "labels": None, "evaluate": None, "error_decomp": None,
           "report": None}
    defaults = scale_method_defaults()
    for run, block in (cfg.get("scale") or {}).items():
        w = f"scale.{run}"
        if run not in runs:
            raise ConfigError(f"{w}: no slam run {run!r}")
        extra = set(block) - {"primary", "checks", "flag_threshold", "methods"}
        if extra:
            raise ConfigError(f"{w}: unknown keys {sorted(extra)}")
        for k in ("primary", "checks", "flag_threshold", "methods"):
            if k not in block:
                raise ConfigError(f"{w}: missing '{k}' (checks: [] and flag_threshold: null if none)")
        primary = block.get("primary")
        checks = block.get("checks")
        if primary not in defaults:
            raise ConfigError(f"{w}.primary: one of {sorted(defaults)}")
        if primary == "tiles":
            raise ConfigError(f"{w}.primary: 'tiles' is the evaluation oracle, not a scale method")
        if not isinstance(checks, list) or any(c not in defaults or c in (primary, "tiles") for c in checks):
            raise ConfigError(f"{w}.checks: list of methods other than the primary and 'tiles'")
        if len(set(checks)) != len(checks):
            raise ConfigError(f"{w}.checks: duplicate methods")
        thr = block.get("flag_threshold")
        if checks:
            if isinstance(thr, bool) or not isinstance(thr, (int, float)) or not 0 < thr < 1:
                raise ConfigError(f"{w}.flag_threshold: a fraction in (0, 1) with checks, e.g. 0.10")
        elif thr is not None:
            raise ConfigError(f"{w}.flag_threshold: null without checks")
        methods = block.get("methods") or {}
        used = [primary] + checks
        need = [m for m in used if defaults[m]]
        if set(methods) != set(need):
            raise ConfigError(f"{w}.methods: give the parameters of exactly {need} (got {sorted(methods)})")
        mp = {}
        for m in used:
            mp[m] = normalize_params(defaults[m], methods.get(m, {}), f"{w}.methods.{m}")
            for k, allowed in SCALE_CHOICES.get(m, {}).items():
                if mp[m][k] not in allowed:
                    raise ConfigError(f"{w}.methods.{m}.{k}: one of {list(allowed)}, got {mp[m][k]!r}")
            if "depth" in mp[m]:
                dn = depth_for.get((run, mp[m]["depth"]))
                if dn is None:
                    raise ConfigError(f"{w}.methods.{m}.depth: no depth node '{mp[m]['depth']}' for run {run}")
                mp[m]["_depth_node"] = dn.id
        out["scale"][run] = {"primary": primary, "checks": checks,
                             "flag_threshold": float(thr) if thr is not None else None, "methods": mp}
    for step in ("mask_compare", "labels", "evaluate", "error_decomp", "report"):
        if step not in cfg:
            continue
        impl = R.get(step, "default")
        block = cfg[step]
        allowed = {"params"} if step in ("report", "mask_compare") else {"runs", "params"}
        if not isinstance(block, dict) or set(block) - allowed:
            raise ConfigError(f"{step}: a mapping with keys {sorted(allowed)}")
        params = normalize_params(impl.params, block.get("params"), f"{step}.params")
        _check_choices(impl, params, step)
        sel = []
        if step == "mask_compare":
            masks = [n.name for n in nodes.values() if n.step == "masks"]
            names = [params["reference"]] + list(params["candidates"])
            if not params["candidates"] or any(m not in masks for m in names) or len(set(names)) != len(names):
                raise ConfigError(f"mask_compare.params: reference and candidates must be distinct mask names "
                                  f"from {masks}, got {names}")
            if params["dilate_px"] < 0 or params["overlays_per_segment"] < 0:
                raise ConfigError("mask_compare.params: dilate_px and overlays_per_segment must be >= 0")
        elif step != "report":
            sel = _need(block, "runs", step, list)
            if any(r not in runs for r in sel):
                raise ConfigError(f"{step}.runs: list of slam runs {runs}")
            if step == "error_decomp" and any(r not in out["scale"] for r in sel):
                raise ConfigError("error_decomp.runs: every run needs a scale block (its configured scale)")
            if step == "error_decomp":
                b = params["speed_bins_deg_s"]
                if not b or b[0] < 0 or any(y <= x for x, y in zip(b, b[1:])) or params["speed_window_s"] <= 0:
                    raise ConfigError("error_decomp.params: speed_bins_deg_s strictly increasing from >= 0, "
                                      "speed_window_s > 0")
        if step == "labels":
            fixed = labels_fixed()
            bad = {k: (params[k], v) for k, v in fixed.items() if params[k] != v}
            if bad:
                raise ConfigError(f"labels.params: fixed in slam.labels (config, code): {bad}; "
                                  "another value needs a new labels implementation")
        out[step] = {"runs": sel, "params": params}
    return out


# ---------------------------------------------------------------------- keys
def impl_id(impl):
    return f"{impl.step}/{impl.name}"


def compute_keys(order, data_fp, code_fp, tags=None):
    """Fill node.key and node.data_fp. data_fp: {data input name: fingerprint};
    code_fp: {impl_id(impl): {name: fingerprint}} of each implementation's code, binaries,
    third-party checkouts, environment packages and tools (orchestrator.Runner.fingerprints).
    tags: {node id: salt}."""
    tags = tags or {}
    by_id = {n.id: n for n in order}
    for n in order:                                    # topological: deps first
        deps = {}
        for role, v in n.deps.items():
            deps[role] = sorted(by_id[d].key for d in v) if isinstance(v, list) else by_id[v].key
        fp = {k: data_fp[k] for k in n.impl.data_inputs}
        fp.update(code_fp[impl_id(n.impl)])
        n.data_fp = fp
        n.hash_params = hash_params(n)
        n.key = H.node_key(n.step, n.impl.name, n.impl.version, n.hash_params, fp, deps, tags.get(n.id))
    return order


def hash_params(n):
    """Parameters as they enter the key. A parameter naming an upstream node (tile_geometry's
    slam_fallback: a run name) enters through that node's key in deps, not through the name;
    a weights file enters through its sha256 (checked by the implementation), not its path."""
    out = {}
    for k, v in n.params.items():
        if k in n.deps and v is not None:
            v = f"<deps.{k}>"
        elif k == "weights" and isinstance(v, dict) and "sha256" in v:
            v = {**v, "path": "<by sha256>"}
        out[k] = v
    return out


def descendants(order, nid):
    """Ids of the nodes that depend (transitively) on nid, including nid."""
    out = {nid}
    for n in order:
        if any(d in out for d in n.dep_ids()):
            out.add(n.id)
    return out
