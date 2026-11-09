"""Python environments the steps run in, and their package snapshots for run.json.

Override an interpreter with SLAM_PY_<NAME> (e.g. SLAM_PY_SAM3=/path/to/python)."""
import json
import os
import subprocess
import sys
from pathlib import Path

CONDA = Path(os.environ.get("CONDA_ROOT", "/home/student/miniconda3"))
ENVS = {
    "venv": "/home/student/yuanliu-hawaii/.venv-headcam/bin/python",   # numpy, cv2, pyyaml
    "droid": str(CONDA / "envs/droid/bin/python"),                     # DROID-SLAM
    "sam2": str(CONDA / "envs/sam2/bin/python"),                       # SAM2, depth (transformers)
    "sam3": str(CONDA / "envs/sam3/bin/python"),                       # SAM3
    "lerobot": str(CONDA / "envs/lerobot/bin/python"),                 # LeRobot export
}


def python(env):
    exe = os.environ.get(f"SLAM_PY_{env.upper()}", ENVS.get(env))
    if exe is None:
        raise KeyError(f"unknown environment {env!r}; known {sorted(ENVS)}")
    if not Path(exe).exists():
        raise FileNotFoundError(f"environment {env!r}: interpreter {exe} does not exist")
    return exe


def is_conda(exe):
    return (Path(exe).parent.parent / "conda-meta").is_dir()


def snapshot(env):
    """{python, executable, kind, packages: {name: version}} of an environment."""
    exe = python(env)
    ver = subprocess.run([exe, "-c", "import sys; print(sys.version.split()[0])"],
                         capture_output=True, text=True, check=True).stdout.strip()
    out = {"python": ver, "executable": exe}
    prefix = Path(exe).parent.parent
    pk = {}
    if is_conda(exe):
        out["kind"] = "conda"
        r = subprocess.run([str(CONDA / "bin/conda"), "list", "-p", str(prefix), "--json"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            for p in json.loads(r.stdout):
                pk[p["name"]] = f"{p['version']} ({p.get('channel', '?')}, {p.get('build_string', '')})"
    else:
        out["kind"] = "venv"
    r = subprocess.run([exe, "-m", "pip", "list", "--format=json", "--disable-pip-version-check"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        for p in json.loads(r.stdout):
            pk.setdefault(p["name"], p["version"])
    out["packages"] = dict(sorted(pk.items(), key=lambda kv: kv[0].lower()))
    return out


def this_env_name():
    for k, v in ENVS.items():
        if Path(v).resolve() == Path(sys.executable).resolve():
            return k
    return None
