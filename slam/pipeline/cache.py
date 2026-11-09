"""Content-addressed cache of producer outputs: <work>/cache/<step>/<key>/.

  manifest.json   what the key stands for (step, impl, version, params, data fingerprints,
                  upstream keys) and who created it; written once
  epNN/           one finished segment; created by an atomic rename of a temporary
                  directory, so a directory named epNN is always complete
  .tmp-*          unfinished work (removed on the next run)
  .lock           flock held while a run computes into this entry
"""
import fcntl
import json
import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

SEG_RE = re.compile(r"^ep\d\d$")


def root(work):
    return Path(work) / "cache"


def node_dir(work, step, key):
    return root(work) / step / key


def done_segments(d):
    d = Path(d)
    if not d.exists():
        return set()
    return {p.name for p in d.iterdir() if p.is_dir() and SEG_RE.match(p.name)}


def missing_segments(d, segments):
    have = done_segments(d)
    return [s for s in segments if s not in have]


def tmp_dir(d, seg):
    """Fresh temporary directory for one segment's output (inside the entry, same filesystem)."""
    p = Path(d) / f".tmp-{seg}-{os.getpid()}"
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


def commit_segment(d, seg, tmp):
    """Atomically publish tmp as <d>/<seg>. If another process published it first, keep
    theirs and drop ours. Returns the final path."""
    final = Path(d) / seg
    try:
        os.rename(tmp, final)
    except OSError:
        if final.is_dir():
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            raise
    return final


def clean_tmp(d):
    for p in Path(d).glob(".tmp-*"):
        shutil.rmtree(p, ignore_errors=True)


def write_manifest(d, manifest):
    """Write manifest.json once. If it exists, the identity fields must agree (they define
    the key, so a mismatch means a hash collision or a hand-edited cache)."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "manifest.json"
    ident = ("step", "impl", "version", "params", "data", "deps", "tag")
    if p.exists():
        old = json.load(open(p))
        for k in ident:
            if json.dumps(old.get(k), sort_keys=True) != json.dumps(manifest.get(k), sort_keys=True):
                raise RuntimeError(f"{p}: existing manifest differs in '{k}'")
        return old
    tmp = d / f".manifest-{os.getpid()}.json"
    json.dump(manifest, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, p)
    return manifest


@contextmanager
def lock(d, wait_s=None):
    """Exclusive lock on a cache entry (other runs computing the same key wait)."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    f = open(d / ".lock", "w")
    t0 = time.time()
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if wait_s is not None and time.time() - t0 > wait_s:
                f.close()
                raise TimeoutError(f"{d} is locked by another run")
            time.sleep(5)
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()
