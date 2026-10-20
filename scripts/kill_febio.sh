#!/bin/bash
# Kill only this user's FEBio processes running inside this project, optionally only those whose working
# directory ENDS WITH the given case path (exact case dir, so case_A_x does not also kill case_A_x_ref).
# usage: scripts/kill_febio.sh <case-dir-path-suffix, e.g. cage_test/case_A_push_ant>
set -u
PROJ="$(cd "$(dirname "$0")/.." && pwd -P)"; FRAG="${1:?case dir fragment required}"
for p in $(pgrep -u "$(id -u)" -f "febio4 -i"); do
  cwd=$(readlink /proc/$p/cwd) || continue
  FRAG="${FRAG%/}"; [[ "$cwd" == "$PROJ"/* && "$cwd" == *"/$FRAG" ]] || continue
  echo "kill $p $cwd"; kill "$p"
done
