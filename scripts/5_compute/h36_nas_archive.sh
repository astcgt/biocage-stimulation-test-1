#!/bin/bash
# h36_nas_archive.sh — move finished human_study/al_v2 sets to the personal NAS dir and leave symlinks in place
# (PI 2026-11-03: /raid is not needed for compute now, archive to NAS, NAS cap 3 TB). Paths keep working through the symlinks
# (collect_split, h34, e04/e05 read through them; NFS read ~200 MB/s, so re-evaluation is slower but possible).
# usage: bash scripts/5_compute/h36_nas_archive.sh <set> [<set> ...]        log: human_study/nas_archive.log
# A set is skipped when a FEBio process mentions it on its command line, when the NAS usage would exceed the cap, or when the
# verification rsync (dry run, itemized) still lists differences; the source is removed only after a clean verification.
set -u
P=/raid/jupyter-alz.ee09/projects/claude-work/biocage_simulation_test_oct2026
SRC=$P/human_study/al_v2
DST=/mnt/jp/alz.ee09/biocage_simulation_test_oct2026/human_study/al_v2
LOG=$P/human_study/nas_archive.log
CAP_GB=3000
mkdir -p "$DST"
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }
for s in "$@"; do
  if [ -L "$SRC/$s" ]; then log "skip $s: already a symlink"; continue; fi
  if [ ! -d "$SRC/$s" ]; then log "skip $s: no such set"; continue; fi
  if pgrep -af febio | grep -q "/$s/"; then log "skip $s: a FEBio process is using it"; continue; fi
  used=$(du -s --block-size=1G /mnt/jp/alz.ee09 2>/dev/null | cut -f1); size=$(du -s --block-size=1G "$SRC/$s" | cut -f1)
  if [ $((used + size)) -gt $CAP_GB ]; then log "stop at $s: NAS usage ${used} GB + ${size} GB would exceed ${CAP_GB} GB"; break; fi
  log "copy $s (${size} GB) ..."
  if ! rsync -a --partial "$SRC/$s/" "$DST/$s/" >> "$LOG" 2>&1; then log "FAILED rsync $s (source kept)"; continue; fi
  diff=$(rsync -a --dry-run --itemize-changes "$SRC/$s/" "$DST/$s/" | grep -v '^\.d' | head -5)
  if [ -n "$diff" ]; then log "VERIFY FAILED $s (source kept): $diff"; continue; fi
  mv "$SRC/$s" "$SRC/.$s.moved" && ln -s "$DST/$s" "$SRC/$s" && rm -rf "$SRC/.$s.moved" && log "moved $s -> $DST/$s (symlink left)"
done
log "done; NAS usage $(du -s --block-size=1G /mnt/jp/alz.ee09 | cut -f1) GB; /raid free $(df --output=avail -BG /raid | tail -1)"
