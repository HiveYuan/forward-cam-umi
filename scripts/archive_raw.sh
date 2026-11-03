#!/bin/bash
# Copy finished recordings from the local raw directory to the NAS archive.
#
# Recording and processing happen on the local NVMe (data/raw ->
# /mnt/nvme/pilot/raw): recording over NFS dropped ~0.5 s of frames at every
# 60 s segment boundary and detection read 4K video at network speed
# (2026-11-02). The NAS keeps the archive copy; this script only adds to it,
# never deletes. Dot-files (unfinished takes, segments, journals) stay local.
#
#   scripts/archive_raw.sh                 # everything in data/raw
#   scripts/archive_raw.sh yam_glove9      # one session (its files + takes)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SRC="$ROOT/data/raw"
DST=/mnt/nas/nvme_archive/pilot/raw
[ -d "$DST" ] || { echo "NAS archive not mounted: $DST" >&2; exit 1; }
if [ $# -gt 0 ]; then
    args=(); for s in "$@"; do args+=(--include="${s}_*" --include="${s}.*"); done
    rsync -a --info=progress2 --exclude='.*' "${args[@]}" --exclude='*' "$SRC/" "$DST/"
else
    rsync -a --info=progress2 --exclude='.*' --exclude='nas' "$SRC/" "$DST/"
fi
echo "archived to $DST"
