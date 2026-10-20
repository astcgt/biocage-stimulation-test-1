#!/bin/bash
# Live resource usage of this study's simulations (your user only) + cumulative ledger.
# usage: bash scripts/my_usage.sh          (or: watch -n 10 bash scripts/my_usage.sh)
cd "$(dirname "$0")/.."
U=$(whoami)
echo "=== $(date '+%F %T')   node load: $(cut -d' ' -f1-3 /proc/loadavg)   cores: $(nproc)"

echo "--- CPU (FEBio processes of $U)"
pids=$(pgrep -u "$U" -f 'febio4 -i' | tr '\n' ' ')
if [ -z "$pids" ]; then echo "none running"; else
  n=0; tot_cpu=0; tot_rss=0; pinned=0
  for p in $pids; do
    read cpu rss et <<<"$(ps -o pcpu=,rss=,etime= -p $p)"
    aff=$(taskset -cp $p 2>/dev/null | awk -F': ' '{print $2}')
    cores=$(python3 -c "s='$aff';print(sum((int(b)-int(a)+1) if '-' in r else 1 for r in s.split(',') for a,b in [r.split('-') if '-' in r else (r,r)]))" 2>/dev/null)
    dir=$(readlink /proc/$p/cwd | sed "s#.*/human_study/##")
    printf "  %-38s cores %-3s cpu %6s%%  mem %5.1f GB  running %s\n" "$dir" "$cores" "$cpu" "$(echo "$rss/1048576" | bc -l)" "$et"
    n=$((n+1)); pinned=$((pinned+cores)); tot_cpu=$(echo "$tot_cpu+$cpu" | bc); tot_rss=$((tot_rss+rss))
  done
  printf "  TOTAL: %d runs, %d pinned cores, %.0f%% CPU (= %.1f cores busy), %.1f GB RAM\n" $n $pinned $tot_cpu $(echo "$tot_cpu/100" | bc -l) $(echo "$tot_rss/1048576" | bc -l)
fi

echo "--- GPU (processes of $U)"
mine=0
while IFS=, read -r pid uuid mem; do
  [ -z "$pid" ] && continue
  if [ "$(ps -o user= -p $pid 2>/dev/null)" = "$U" ]; then
    idx=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | grep "$uuid" | cut -d, -f1)
    echo "  GPU $idx  pid $pid  mem$mem"; mine=1
  fi
done < <(nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader)
[ $mine = 0 ] && echo "  none"

echo "--- progress"
python3 scripts/progress_report.py
echo "--- cumulative (ledger, finished batches only)"
python3 - <<'EOF'
import json
d = json.load(open('human_study/resources_ledger.json'))['entries']
print(f"  {len(d)} batches, {sum(e['core_h'] for e in d):.1f} core-hours, {sum(e['gpu_h'] for e in d):.2f} GPU-hours")
EOF
