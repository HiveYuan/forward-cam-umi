"""Stable hashes: canonical JSON, file fingerprints, cache keys.

Everything here is pure (no environment state) so it is unit-tested directly.
"""
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

KEY_LEN = 16
QUICK_CHUNK = 8 << 20            # bytes hashed at each end of a large file


def canonical(obj):
    """JSON text that is identical for equal values: sorted keys, no whitespace, tuples as
    lists, floats in repr form (5.0 and 5 differ on purpose: params are type-normalised
    before hashing, see spec.normalize_params)."""
    def fix(o):
        if isinstance(o, dict):
            return {str(k): fix(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [fix(v) for v in o]
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, float) and not math.isfinite(o):
            raise ValueError(f"non-finite float {o!r} cannot be hashed")
        if o is None or isinstance(o, (bool, int, float, str)):
            return o
        raise TypeError(f"cannot hash value of type {type(o).__name__}: {o!r}")
    return json.dumps(fix(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def quick_file_hash(path, chunk=QUICK_CHUNK):
    """Size + sha256 of the first and last `chunk` bytes: for multi-GB videos. Identical
    across copies of the file (no mtime), changes with any re-encode or truncation."""
    size = os.path.getsize(path)
    h = hashlib.sha256(str(size).encode())
    with open(path, "rb") as f:
        h.update(f.read(chunk))
        if size > 2 * chunk:
            f.seek(size - chunk)
            h.update(f.read(chunk))
        else:
            h.update(f.read())
    return f"quick:{size}:{h.hexdigest()}"


def file_fingerprint(path, quick_above=256 << 20):
    """Full sha256 for normal files, quick hash above `quick_above` bytes; None if missing."""
    p = Path(path)
    if not p.exists():
        return None
    if p.is_dir():
        raise IsADirectoryError(f"{p}: fingerprint a file, not a directory")
    if p.stat().st_size > quick_above:
        return quick_file_hash(p)
    return "sha256:" + sha256_file(p)


GIT_PINNED = ["-c", "core.abbrev=40", "-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false",
              "-c", "color.ui=never", "-c", "core.quotePath=true"]
DIFF_OPTS = ["--no-ext-diff", "--no-color", "--no-textconv", "--full-index",
             "--src-prefix=a/", "--dst-prefix=b/"]


def _git(repo, *a):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    env.pop("GIT_EXTERNAL_DIFF", None)
    return subprocess.run(["git", *GIT_PINNED, "-C", str(repo), *a], capture_output=True, text=True,
                          check=True, env=env).stdout


def git_state(repo):
    """Commit, dirty flag and hashes of the uncommitted changes of a git checkout and of each
    submodule's own commit and diff (contents, not just a '-dirty' marker): identifies e.g. a
    patched third-party repo. Git output options are pinned so user config cannot change it."""
    commit = _git(repo, "rev-parse", "HEAD").strip()
    diff = _git(repo, "diff", "HEAD", *DIFF_OPTS, "--submodule=short")
    status = _git(repo, "status", "--porcelain", "--untracked-files=no")
    subs = {}
    if (Path(repo) / ".gitmodules").exists():
        for line in _git(repo, "submodule", "status", "--recursive").splitlines():
            path = line[1:].split()[1]
            sub = Path(repo) / path
            sdiff = _git(sub, "diff", "HEAD", *DIFF_OPTS)
            subs[path] = {"commit": _git(sub, "rev-parse", "HEAD").strip(),
                          "diff_sha256": sha256_text(sdiff) if sdiff.strip() else None}
    return {"commit": commit, "dirty": bool(status.strip()),
            "diff_sha256": sha256_text(diff) if diff.strip() else None,
            "submodules": subs}


def git_patches(repo):
    """{path: diff text} of the uncommitted changes of a checkout ('.') and of each submodule,
    exactly the texts whose sha256 git_state() records (empty diffs left out)."""
    out = {}
    d = _git(repo, "diff", "HEAD", *DIFF_OPTS, "--submodule=short")
    if d.strip():
        out["."] = d
    if (Path(repo) / ".gitmodules").exists():
        for line in _git(repo, "submodule", "status", "--recursive").splitlines():
            path = line[1:].split()[1]
            sd = _git(Path(repo) / path, "diff", "HEAD", *DIFF_OPTS)
            if sd.strip():
                out[path] = sd
    return out


def patch_file_name(path, text):
    """File name under third_party_patches/<checkout>/ for a diff text."""
    stem = "root" if path == "." else path.replace("/", "__")
    return f"{stem}_{sha256_text(text)[:12]}.diff"


def _ast_canon(node):
    """Version-stable serialisation of a syntax tree (node type + non-empty fields)."""
    import ast
    if isinstance(node, ast.AST):
        out = [type(node).__name__]
        for f in node._fields:
            v = _ast_canon(getattr(node, f, None))
            if v not in (None, []):
                out.append([f, v])
        return out
    if isinstance(node, list):
        return [_ast_canon(x) for x in node]
    return repr(node) if node is not None else None


def source_hash(path):
    """Hash of a Python file's code: its syntax tree without docstrings, so comments,
    formatting and docstrings do not change it but any code change does."""
    import ast
    tree = ast.parse(Path(path).read_text(), filename=str(path))
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            b = n.body
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) \
                    and isinstance(b[0].value.value, str):
                n.body = b[1:] or [ast.Pass()]
    return "ast:" + sha256_text(json.dumps(_ast_canon(tree), separators=(",", ":")))


def glob_hashes(pattern):
    """{path: sha256} of the files matching an absolute glob pattern (error if none)."""
    import glob
    files = sorted(p for p in glob.glob(pattern) if os.path.isfile(p))
    if not files:
        raise FileNotFoundError(f"no file matches {pattern}")
    return {p: "sha256:" + sha256_file(p) for p in files}


def node_key(step, impl, version, params, data, deps, tag=None):
    """Cache key of a producer node.

    step, impl, version  which code produced it (version is bumped by hand when an
                         implementation's output changes for the same parameters)
    params               the full, normalised parameter set
    data                 {input name: fingerprint} of the data files the impl reads
    deps                 {role: key or sorted list of keys} of upstream producers
    tag                  optional extra salt (e.g. 'repro1' to recompute on purpose)
    Node names chosen in a config (e.g. 'E3', 'motion') are deliberately not part of it."""
    payload = {"step": step, "impl": impl, "version": int(version), "params": params,
               "data": data, "deps": deps}
    if tag:
        payload["tag"] = str(tag)
    return sha256_text(canonical(payload))[:KEY_LEN]
