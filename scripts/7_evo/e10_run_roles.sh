#!/bin/bash
# Run one round of the independent roles (headless Claude, one process each, own permissions). usage: e10_run_roles.sh <round> <role...>
cd "$(dirname "$0")/../.."
R=$(printf "r%04d" "$1"); shift
MODEL=claude-opus-5-5
for role in "$@"; do
  mkdir -p human_study/evo/roles/$role human_study/evo/board/$R
  allow=(Read Glob Grep WebSearch WebFetch "Write(human_study/evo/roles/$role/**)" "Edit(human_study/evo/roles/$role/**)"
         "Write(human_study/evo/board/$R/$role.json)" "Edit(human_study/evo/board/$R/$role.json)")
  [ $role = redteam ] && allow+=("Write(human_study/evo/findings/**)" "Edit(human_study/evo/findings/**)" "Bash(python -I human_study/evo/roles/redteam/*)")
  [ $role = verifier ] && allow+=("Bash(python scripts/7_evo/gpufe/gate1_patch.py human_study/evo/roles/verifier/*)" "Bash(python -I human_study/evo/roles/verifier/*)")
  [ $role = safety ] && allow+=("Bash(python -I human_study/evo/roles/safety/*)")
  prompt="$(cat scripts/7_evo/roles/common.md scripts/7_evo/roles/$role.md)
Round: $R. Start now."
  ( CUDA_VISIBLE_DEVICES=5 claude -p "$prompt" --model $MODEL --allowed-tools "${allow[@]}" --output-format json \
      > human_study/evo/roles/$role/$R.session.json 2> human_study/evo/roles/$role/$R.err
    echo "$(date -Is) $role $R exit $?" >> human_study/evo/roles/rounds.log ) &
done
wait
