#!/bin/bash
# Record what each node's memory is doing, so a node that dies leaves evidence.
#
#   scripts/node-watch.sh --nodes a,b,c --out DIR [--interval 30]
#   scripts/node-watch.sh --run <run-dir> --nodes a,b,c        # writes into the run
#
# Two nodes have been lost mid-benchmark — `tuolumne1344` and `tuolumne1391`,
# both of them the node hosting the runner — and each time the post-mortem was
# the same: the node reboots, its `dmesg` goes with it, Flux records no drain
# reason, and there is nothing left to distinguish "the kernel OOMed" from "the
# hardware failed". Sampling from OUTSIDE the node is the only record that
# survives the node.
#
# Each sample line is one node, JSON, with the memory and load it reported and
# the heaviest resident processes. The line that matters is the LAST one before
# a node goes quiet: `unreachable` with no preceding rise in `used` is a machine
# that fell over, and a climb to the memory ceiling is one that was pushed.
set -uo pipefail

NODES=""
OUT=""
INTERVAL=30

while [ $# -gt 0 ]; do
  case "$1" in
    --nodes)    NODES="$2"; shift 2;;
    --out)      OUT="$2"; shift 2;;
    --run)      OUT="$2/node-watch"; shift 2;;
    --interval) INTERVAL="$2"; shift 2;;
    -h|--help)  sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done
[ -n "$NODES" ] || { echo "need --nodes" >&2; exit 2; }
[ -n "$OUT" ]   || { echo "need --out or --run" >&2; exit 2; }

mkdir -p "$OUT"
LOG=$OUT/memory.jsonl
echo "watching ${NODES} every ${INTERVAL}s -> $LOG"

# `timeout` around every ssh, and never a bare one.
#
# A dead node does not refuse connections, it stops answering — so an ssh to it
# blocks for the TCP timeout, and a watcher that polls nodes in series stops
# reporting the LIVE ones the moment one dies. That is precisely when its output
# matters most, so each node is polled in its own background shell.
sample_node() {   # sample_node <host>
  local h=$1 now
  now=$(date +%s)
  local raw
  raw=$(timeout 15 ssh -n -o BatchMode=yes -o ConnectTimeout=10 "$h" '
      read _ total avail_junk < <(grep MemTotal /proc/meminfo)
      mem=$(awk "/^MemTotal:/{t=\$2}/^MemAvailable:/{a=\$2}END{printf \"%d %d\", t, a}" /proc/meminfo)
      load=$(cut -d" " -f1-3 /proc/loadavg)
      procs=$(ps -eo rss=,comm= --sort=-rss | head -5 | awk "{printf \"%s:%s \", \$2, \$1}")
      nproc_run=$(pgrep -c . 2>/dev/null || echo 0)
      # /tmp is TMPFS on these nodes, so anything a container writes there is
      # held in RAM and counts against the same pool the processes do. A node
      # can therefore die of "disk" usage that never touched a disk.
      tmp_pct=$(df --output=pcent /tmp 2>/dev/null | tail -1 | tr -dc 0-9)
      ssd_pct=$(df --output=pcent /l/ssd 2>/dev/null | tail -1 | tr -dc 0-9)
      echo "$mem|$load|$procs|$nproc_run|${tmp_pct:-0}|${ssd_pct:-0}"
  ' 2>/dev/null)

  if [ -z "$raw" ]; then
    printf '{"t":%s,"host":"%s","state":"unreachable"}\n' "$now" "$h" >> "$LOG"
    return
  fi
  local mem load procs nprocs tmp_pct ssd_pct total avail
  IFS='|' read -r mem load procs nprocs tmp_pct ssd_pct <<< "$raw"
  total=${mem%% *}; avail=${mem##* }
  printf '{"t":%s,"host":"%s","state":"up","mem_total_kb":%s,"mem_avail_kb":%s,"used_pct":%.1f,"load":"%s","procs":"%s","nprocs":%s,"tmpfs_pct":%s,"ssd_pct":%s}\n' \
    "$now" "$h" "${total:-0}" "${avail:-0}" \
    "$(awk "BEGIN{if(${total:-0}>0) printf \"%.1f\", (1-${avail:-0}/${total:-1})*100; else print 0}")" \
    "$load" "${procs% }" "${nprocs:-0}" "${tmp_pct:-0}" "${ssd_pct:-0}" >> "$LOG"
}

trap 'echo "node-watch stopping"; exit 0' TERM INT

while :; do
  for h in ${NODES//,/ }; do
    sample_node "$h" &
  done
  wait
  sleep "$INTERVAL"
done
