#!/bin/bash
# latest progress line of every worker (future runs write logs/progress/worker_gpu<N>.log)
cd "$(dirname "$0")/.."
for f in logs/progress/worker_gpu*.log; do [ -f "$f" ] && tail -n 1 "$f"; done
