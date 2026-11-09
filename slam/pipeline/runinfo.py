"""Provenance for run.json: git state, GPU, environments, weights."""
import os
import platform
import socket
import subprocess
from pathlib import Path

from slam.pipeline import envs as E
from slam.pipeline import hashing as H


def git_repo_state(repo, ignore=()):
    """Commit, branch, and whether the work tree is clean. Paths under `ignore` (repo-relative
    prefixes, e.g. the experiment's results/) do not count as dirty."""
    def git(*a):
        return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True,
                              check=True).stdout
    commit = git("rev-parse", "HEAD").strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    dirty = []
    for line in git("status", "--porcelain", "--untracked-files=all").splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        if not any(path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/") for p in ignore):
            dirty.append(line)
    return {"commit": commit, "branch": branch, "clean": not dirty, "dirty_files": dirty,
            "describe": git("describe", "--always", "--tags", "--dirty").strip()}


def gpu_info():
    q = "name,driver_version,memory.total,memory.used,memory.free"
    r = subprocess.run(["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    out = []
    for line in r.stdout.strip().splitlines():
        name, drv, tot, used, free = [x.strip() for x in line.split(",")]
        out.append({"name": name, "driver": drv, "memory_total_mb": int(tot),
                    "memory_used_mb": int(used), "memory_free_mb": int(free)})
    return out


def gpu_free_mb(index=0):
    g = gpu_info()
    return None if not g else g[index]["memory_free_mb"]


def host_info():
    return {"host": socket.gethostname(), "user": os.environ.get("USER"),
            "platform": platform.platform()}


def hf_weights(repo, revision):
    """Files of a Hugging Face snapshot in the local cache with their sha256 (LFS blobs are
    named by their sha256; small files are hashed)."""
    hub = Path(os.environ.get("HF_HUB_CACHE", Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"))
    snap = hub / ("models--" + repo.replace("/", "--")) / "snapshots" / revision
    if not snap.exists():
        return {"repo": repo, "revision": revision, "local": False}
    files = {}
    for p in sorted(snap.iterdir()):
        target = Path(os.path.realpath(p))
        name = target.name
        files[p.name] = name if len(name) == 64 else H.sha256_file(target)
    return {"repo": repo, "revision": revision, "local": True, "files_sha256": files}


def weights_of(nodes):
    """Model weights used by the producer nodes: {node id: identity}."""
    out = {}
    for n in nodes:
        p = n.params
        if isinstance(p.get("weights"), dict):
            w = dict(p["weights"])
            if Path(w.get("path", "")).exists():
                w["sha256_actual"] = H.sha256_file(w["path"])
            out[n.id] = w
        elif "revision" in p:
            repo = p.get("repo", p.get("model"))
            out[n.id] = hf_weights(repo, p["revision"])
    return out
