#!/usr/bin/env bash
# Quick view of this user's top CPU processes and GPU processes (nvidia-smi) for the BIOCAGE runs.

echo "=== CPU (My Processes) ==="
ps -u "$USER" -o pid,pcpu,comm --sort=-pcpu | head -7

echo
echo "=== GPU (My Processes) ==="

nvidia-smi pmon -s um -c 1 | awk -v pids="$(ps -u "$USER" -o pid=)" '
BEGIN {
    n = split(pids, a, /[[:space:]]+/)
    for (i = 1; i <= n; i++)
        if (a[i] != "") own[a[i]] = 1

    printf "%-5s %-10s %-7s %-7s %-10s\n", \
        "GPU", "PID", "SM%", "MEM%", "VRAM(MB)"
}
$1 ~ /^[0-9]+$/ && ($2 in own) {
    printf "%-5s %-10s %-7s %-7s %-10s\n", \
        $1, $2, $4, $5, $6
    found = 1
}
END {
    if (!found) print "No GPU processes detected"
}'
