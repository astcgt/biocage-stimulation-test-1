#!/bin/bash
# Block until the account's FEBio threads + N fit in the CPU quota (cgroup cpu.max = 32 cores; the lane drivers that call h18 / h47
# directly have no quota check of their own - on 2026-11-20 the account ran ~45 threads, everything crawled and the watchdog stopped
# two runs for 'no progress'). Counts the threads asked for by every running febio4 of this user (OMP_NUM_THREADS in its environment).
# 2026-11-21 foreman: check and admit under flock, and an admitted caller leaves a reservation (N threads, LEASE s) that later checks
# also count until its febio4 has started (20:36 two lanes passed together, both saw 26 + 6 <= 32, account ran 38 threads, 43 %
# periods throttled). During the lease a started run is counted twice: errs toward waiting. Reservations live in /tmp (gone at reboot).
# 2026-11-22 foreman (DECISIONS 2026-11-22 10:2x ops): 10:20 the account ran 38 threads - a lane between two FEBio runs (insertion
# ended, window not started) holds no febio4, its 6 threads were not counted and two waiters passed. Now (1) a live h18 / h47 python
# wrapper counts its <cores> argument (same patterns as h51 busy_threads, bash wrappers skipped) and a febio4 counts its OMP threads
# only if no h18 / h47 wrapper is its ancestor (h55 ASTM, hand runs); (2) a passing check is repeated after CONFIRM s (default 30,
# lock held) and admits only if it still passes (10:20 gap was 16 s). wait_quota.sh --count prints the current count and exits.
# usage: wait_quota.sh <threads to add> [limit=32]   |   wait_quota.sh --count
N=$1; LIM=${2:-32}; LEASE=${WAIT_QUOTA_LEASE:-240}; CONFIRM=${WAIT_QUOTA_CONFIRM:-30}
R=${TMPDIR:-/tmp}/wait_quota_$(id -u); mkdir -p $R
count() {
  local me p a t w q used=0
  me=$(id -u)
  for q in $(pgrep -u $me -x febio4); do             # febio4 runs: OMP threads unless an h18 / h47 wrapper is an ancestor
    p=/proc/$q; w=0
    while [ -n "$q" ] && [ "$q" -gt 1 ] 2>/dev/null; do
      q=$(sed -n 's/^PPid:[[:space:]]*//p' /proc/$q/status 2>/dev/null)
      [ -n "$q" ] || break
      a=$(tr '\0' ' ' < /proc/$q/cmdline 2>/dev/null)
      case "$(cat /proc/$q/comm 2>/dev/null)" in bash|sh|dash) ;; *)
        if [[ "$a" =~ h18_run_gpu_case\.py\ [0-9]+\ [^\ ]+\ [0-9]+ || "$a" =~ h47_restart_pilot\.py\ run\ [^\ ]+\ [0-9]+\ [0-9]+ ]]; then w=1; fi ;;
      esac
    done
    [ $w = 1 ] && continue
    t=$(tr '\0' '\n' < $p/environ 2>/dev/null | sed -n 's/^OMP_NUM_THREADS=//p' | head -1); used=$((used + ${t:-4}))
  done
  for q in $(pgrep -u $me -f 'h18_run_gpu_case\.py|h47_restart_pilot\.py'); do   # h18 / h47 wrappers (python only): <cores>
    p=/proc/$q
    case "$(cat $p/comm 2>/dev/null)" in python*) ;; *) continue ;; esac
    a=$(tr '\0' ' ' < $p/cmdline 2>/dev/null)
    if [[ "$a" =~ h18_run_gpu_case\.py\ [0-9]+\ [^\ ]+\ ([0-9]+) ]]; then used=$((used + BASH_REMATCH[1]))
    elif [[ "$a" =~ h47_restart_pilot\.py\ run\ [^\ ]+\ [0-9]+\ ([0-9]+) ]]; then used=$((used + BASH_REMATCH[1])); fi
  done
  now=$(date +%s)
  for f in $R/res.*; do
    [ -f "$f" ] || continue
    read t0 n < "$f" || continue
    if [ $((now - ${t0:-0})) -ge $LEASE ]; then rm -f "$f"; else used=$((used + ${n:-0})); fi
  done
  echo $used
}
[ "$1" = --count ] && { count; exit 0; }
admit() {
  flock -w 120 9 || return 1
  [ $(( $(count) + N )) -le $LIM ] || return 1
  sleep $CONFIRM
  [ $(( $(count) + N )) -le $LIM ] || return 1
  echo "$(date +%s) $N" > $R/res.$$.$(date +%s)
}
while true; do
  ( admit ) 9>$R/lock && exit 0
  sleep $((60 + RANDOM % 60))
done
