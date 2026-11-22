#!/bin/bash
# Block until the account's FEBio threads + N fit in the CPU quota (cgroup cpu.max = 32 cores; the lane drivers that call h18 / h47
# directly have no quota check of their own - on 2026-11-20 the account ran ~45 threads, everything crawled and the watchdog stopped
# two runs for 'no progress'). Counts the threads asked for by every running febio4 of this user (OMP_NUM_THREADS in its environment).
# 2026-11-21 foreman: check and admit under flock, and an admitted caller leaves a reservation (N threads, LEASE s) that later checks
# also count until its febio4 has started (20:36 two lanes passed together, both saw 26 + 6 <= 32, account ran 38 threads, 43 %
# periods throttled). During the lease a started run is counted twice: errs toward waiting. Reservations live in /tmp (gone at reboot).
# usage: wait_quota.sh <threads to add> [limit=32]
N=$1; LIM=${2:-32}; LEASE=${WAIT_QUOTA_LEASE:-240}
R=${TMPDIR:-/tmp}/wait_quota_$(id -u); mkdir -p $R
admit() {
  flock -w 120 9 || return 1
  used=0
  for p in /proc/[0-9]*; do
    [ "$(cat $p/comm 2>/dev/null)" = febio4 ] || continue
    [ "$(stat -c %u $p 2>/dev/null)" = "$(id -u)" ] || continue
    t=$(tr '\0' '\n' < $p/environ 2>/dev/null | sed -n 's/^OMP_NUM_THREADS=//p' | head -1); used=$((used + ${t:-4}))
  done
  now=$(date +%s)
  for f in $R/res.*; do
    [ -f "$f" ] || continue
    read t0 n < "$f" || continue
    if [ $((now - ${t0:-0})) -ge $LEASE ]; then rm -f "$f"; else used=$((used + ${n:-0})); fi
  done
  [ $((used + N)) -le $LIM ] || return 1
  echo "$now $N" > $R/res.$$.$now
}
while true; do
  ( admit ) 9>$R/lock && exit 0
  sleep $((60 + RANDOM % 60))
done
