#!/usr/bin/env python3
"""Upload a pack_session hand-off manifest to Google Cloud Storage, keeping the repository layout
(`data/raw/...`, `calib/...`), so the receiving side mirrors it into its collect repo with one command.

  python scripts/pack_session.py <dataset> ... --unit yuan --marker-map calib/marker_map_glove_yuan.json \\
      --dest gs://head-cam-umi-raw/collect/yuan
  python scripts/upload_gcs.py data/raw/handoff_yuan.txt gs://head-cam-umi-raw/collect/yuan --dry-run
  python scripts/upload_gcs.py data/raw/handoff_yuan.txt gs://head-cam-umi-raw/collect/yuan
  # receiving side, into its COLLECT_REPO:
  gcloud storage rsync -r gs://head-cam-umi-raw/collect/yuan /home/student/yuanliu-hawaii/incoming/collect

A manifest, not a directory, is the unit: data/raw and calib also hold files that must not travel
(abandoned takes, *.local.json). Rules, the collection's own (raw files are never rewritten, names never
reused):
  - a file missing remotely is uploaded; one present with the same size is skipped, so a re-run resumes;
  - a sidecar (json/txt/log/csv) whose remote size differs is re-uploaded: metadata gains notes;
  - any other file (recordings, calibration views) whose remote size differs STOPS the run before anything
    is sent: a different file under the same name is a reused name, never something to overwrite;
  - nothing remote is ever deleted;
  - afterwards every manifest file must be present with its local size, and the manifest itself is
    stored under <dest>/manifests/ with a timestamp, the receipt the receiving side checks against.
The transfer is gcloud storage's own (parallel, chunked, retried, checksum-validated); this script only
decides what to send and checks what arrived. Same semantics as a `gcloud storage rsync` of a directory
(idempotent, never deletes), applied to a file list.
"""
import argparse
import collections
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIDECARS = {".json", ".txt", ".log", ".csv", ".jsonl"}


def read_manifest(path):
    """Repository-relative paths, one per line (pack_session's format); blanks and # comments skipped."""
    lines = [l.strip() for l in Path(path).read_text().splitlines()]
    return [l for l in lines if l and not l.startswith("#")]


def parse_listing(text, dest):
    """{path relative to dest: size} from `gcloud storage ls -l -r` output ('<size>  <time>  <url>')."""
    prefix, out = dest.rstrip("/") + "/", {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0].isdigit() and parts[2].startswith(prefix):
            out[parts[2][len(prefix):]] = int(parts[0])
    return out


def remote_sizes(dest):
    r = subprocess.run(["gcloud", "storage", "ls", "-l", "-r", dest.rstrip("/") + "/**"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        if "matched no objects" in r.stderr:
            return {}
        raise SystemExit(f"listing {dest} failed:\n{r.stderr.strip()}")
    return parse_listing(r.stdout, dest)


def plan(local, remote):
    """(upload, skip, conflicts) for {rel: size} on both sides; see the module rules."""
    upload, skip, conflicts = [], [], []
    for rel, size in local.items():
        if rel not in remote:
            upload.append(rel)
        elif remote[rel] == size:
            skip.append(rel)
        elif Path(rel).suffix.lower() in SIDECARS:
            upload.append(rel)
        else:
            conflicts.append(rel)
    return upload, skip, conflicts


def send(rels, dest):
    """One `gcloud storage cp -I` per parent directory, so each file lands at <dest>/<its relative path>."""
    by_dir = collections.defaultdict(list)
    for rel in rels:
        by_dir[str(Path(rel).parent)].append(rel)
    for d, files in sorted(by_dir.items()):
        target = f"{dest.rstrip('/')}/{d}/" if d != "." else dest.rstrip("/") + "/"
        print(f"==> {len(files)} file(s) -> {target}", flush=True)
        r = subprocess.run(["gcloud", "storage", "cp", "-I", target], input="\n".join(files) + "\n",
                           text=True, cwd=ROOT)
        if r.returncode != 0:
            raise SystemExit(f"gcloud storage cp to {target} failed (exit {r.returncode}, errors above); "
                             "nothing is deleted, a re-run sends only what is missing")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", help="pack_session's hand-off list, e.g. data/raw/handoff_yuan.txt")
    ap.add_argument("dest", help="gs://bucket/prefix mirroring the receiving repo root")
    ap.add_argument("--dry-run", action="store_true", help="show what would be sent, send nothing")
    a = ap.parse_args(argv)
    if not a.dest.startswith("gs://"):
        raise SystemExit("dest must be a gs:// URL")

    rels = read_manifest(ROOT / a.manifest if not Path(a.manifest).is_absolute() else a.manifest)
    missing = [r for r in rels if not (ROOT / r).is_file()]
    if missing:
        raise SystemExit("listed but not on disk:\n  " + "\n  ".join(missing))
    local = {r: (ROOT / r).stat().st_size for r in rels}
    remote = remote_sizes(a.dest)
    upload, skip, conflicts = plan(local, {r: remote[r] for r in remote if r in local})
    gb = lambda rs: sum(local[r] for r in rs) / 1e9  # noqa: E731
    print(f"{a.dest}: {len(rels)} files ({gb(rels):.2f} GB); to send {len(upload)} ({gb(upload):.2f} GB), "
          f"already there {len(skip)}, conflicts {len(conflicts)}")
    if conflicts:
        raise SystemExit("remote differs for (a reused name? nothing was sent):\n  " + "\n  ".join(
            f"{r}: local {local[r]} B, remote {remote[r]} B" for r in conflicts))
    if a.dry_run:
        for r in upload:
            print(f"  would send {local[r] / 1e9:7.3f} GB  {r}")
        return
    t0 = time.monotonic()
    if upload:
        send(upload, a.dest)
    after = remote_sizes(a.dest)
    bad = [r for r in rels if after.get(r) != local[r]]
    if bad:
        raise SystemExit("not arrived intact (re-run to resume):\n  " + "\n  ".join(
            f"{r}: local {local[r]} B, remote {after.get(r)}" for r in bad))
    receipt = f"{a.dest.rstrip('/')}/manifests/{Path(a.manifest).stem}_{time.strftime('%Y%m%d-%H%M%S')}.txt"
    subprocess.run(["gcloud", "storage", "cp", str(ROOT / a.manifest), receipt], check=True, capture_output=True)
    print(f"all {len(rels)} files present with their local sizes ({gb(rels):.2f} GB, "
          f"{(time.monotonic() - t0) / 60:.1f} min); receipt {receipt}\n"
          f"receiving side: gcloud storage rsync -r {a.dest.rstrip('/')} <COLLECT_REPO>")


if __name__ == "__main__":
    sys.exit(main())
