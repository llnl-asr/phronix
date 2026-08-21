#!/bin/bash
# Serve nemotron-3.5 on all four GPUs of a node, two slots each.
#
#   llama-servers.sh start     # launch one server per GPU
#   llama-servers.sh status    # ports, health, slot occupancy, VRAM
#   llama-servers.sh stop      # stop only the servers this script started
#
# Why four servers rather than one with `-np 8`:
#
# `--parallel` DIVIDES a single KV pool; it does not multiply it. One server at
# `-c 512000 -np 8` gives each slot 64k, and the client workload here has
# already produced a single 185,437-token request (visible as
# `llamacpp:n_tokens_max` on the running server). Those requests would fail
# outright rather than queue. Four independent servers have four independent
# pools, so each slot keeps a full 256k.
#
# It also beats tensor-parallel across the four GPUs (`--split-mode row`), which
# optimises single-stream latency. This workload is many concurrent agents and
# is decode-bound — measured 164 tok/s of generation against 8,170 tok/s of
# prefill, with decode accounting for 80% of GPU-busy time. That is batch-size-1
# behaviour on a 3B-active MoE, so what it needs is aggregate throughput, not a
# faster single stream.
set -uo pipefail

MODEL=${MODEL:-/p/vast1/marathe1/models/nemotron/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q8_0.gguf}
ALIAS=${ALIAS:-nemotron-3.5}
BASE_PORT=${BASE_PORT:-8050}
GPUS=${GPUS:-0 1 2 3}
LOG_DIR=${LOG_DIR:-/var/tmp/llama-servers}
PID_FILE="$LOG_DIR/pids"

# Slots per server, and the pool they share.
#
# 512000 / 2 = 256k per slot, which keeps today's per-request ceiling intact
# while doubling concurrency. If a server dies at startup with an allocation
# failure, this pair is what to halve: `-c 256000 -np 1` is the configuration
# known to fit, and one slot per GPU still gives 4x what a single server does.
CTX=${CTX:-512000}
SLOTS=${SLOTS:-2}

# Flash attention, and the KV quantisation it enables.
#
# `--cache-type-v` REQUIRES flash attention in llama.cpp; quantising V without
# it is rejected. Together they roughly halve KV memory, which is what makes
# 512k per server affordable alongside 33.6 GB of weights on an 80 GB card.
#
# q8_0 KV is close to lossless for this use. If output quality is ever in
# question, drop the two cache-type lines first and keep flash attention.
#
# Builds older than the on/off/auto form take a bare `--flash-attn`; if the
# server rejects the argument, set FLASH="--flash-attn".
FLASH=${FLASH:-"--flash-attn on"}
KV_QUANT=${KV_QUANT:-"--cache-type-k q8_0 --cache-type-v q8_0"}

# Extra flags the current deployment already relies on.
#
# `--jinja` is not optional: tool calling works against this server today, and
# the client is an agent framework that is useless without it.
#
# `--metrics` and `--slots` are how the client watches queue depth. It reads
# those endpoints instead of sending probe requests, so monitoring adds no load
# to the thing it is measuring.
EXTRA=${EXTRA:-"--jinja --metrics --slots"}

ports() {
  local i port=$BASE_PORT
  for i in $GPUS; do
    echo "$port"
    port=$((port + 1))
  done
}

start() {
  [ -f "$MODEL" ] || { echo "model not found: $MODEL" >&2; exit 2; }
  command -v llama-server >/dev/null || { echo "llama-server not on PATH" >&2; exit 2; }
  mkdir -p "$LOG_DIR"

  if [ -s "$PID_FILE" ] && running; then
    echo "servers already running; use 'stop' first" >&2
    exit 2
  fi
  : > "$PID_FILE"

  local port=$BASE_PORT gpu
  for gpu in $GPUS; do
    echo "gpu $gpu -> port $port"
    CUDA_VISIBLE_DEVICES=$gpu nohup llama-server \
      -m "$MODEL" \
      --alias "$ALIAS" \
      --host 0.0.0.0 --port "$port" \
      -ngl 999 \
      -c "$CTX" \
      -np "$SLOTS" \
      $FLASH \
      $KV_QUANT \
      $EXTRA \
      > "$LOG_DIR/gpu$gpu.log" 2>&1 &
    echo "$! $gpu $port" >> "$PID_FILE"
    port=$((port + 1))
  done

  echo
  echo "waiting for health (a 512k context takes a minute to allocate)..."
  local ok=0 waited=0 p
  while [ "$waited" -lt 300 ]; do
    ok=0
    for p in $(ports); do
      curl -sf -m 5 "http://localhost:$p/health" >/dev/null 2>&1 && ok=$((ok + 1))
    done
    [ "$ok" -eq "$(ports | wc -l)" ] && break
    sleep 5
    waited=$((waited + 5))
  done

  if [ "$ok" -ne "$(ports | wc -l)" ]; then
    echo
    echo "only $ok/$(ports | wc -l) came up. The usual cause is KV allocation:"
    echo "  CTX=256000 SLOTS=1 $0 start"
    echo "Check the logs: $LOG_DIR/gpu*.log"
    exit 1
  fi
  echo "all $(ports | wc -l) servers healthy"
  echo
  status
}

running() {
  local pid rest found=0
  while read -r pid rest; do
    [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null && found=1
  done < "$PID_FILE"
  [ "$found" -eq 1 ]
}

status() {
  echo "endpoints (give these to the client, comma separated):"
  local p list=""
  for p in $(ports); do
    list="${list:+$list,}http://$(hostname):$p/v1"
  done
  echo "  $list"
  echo

  printf "  %-6s %-9s %-8s %-10s %s\n" port health slots deferred "generate tok/s"
  for p in $(ports); do
    local health slots deferred rate
    health=$(curl -sf -m 5 "http://localhost:$p/health" >/dev/null 2>&1 \
             && echo ok || echo DOWN)
    slots="-"; deferred="-"; rate="-"
    if [ "$health" = ok ]; then
      # From the server's own counters; no request is sent to the model.
      eval "$(curl -sf -m 5 "http://localhost:$p/metrics" 2>/dev/null | awk '
        /^llamacpp:requests_processing /   {printf "slots=%d;",   $2}
        /^llamacpp:requests_deferred /     {printf "deferred=%d;", $2}
        /^llamacpp:predicted_tokens_seconds / {printf "rate=%.0f;", $2}')"
    fi
    printf "  %-6s %-9s %-8s %-10s %s\n" "$p" "$health" "$slots" "$deferred" "$rate"
  done

  echo
  nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu \
             --format=csv,noheader 2>/dev/null | sed 's/^/  gpu /'
}

stop() {
  [ -f "$PID_FILE" ] || { echo "nothing recorded in $PID_FILE"; exit 0; }
  local pid gpu port
  while read -r pid gpu port; do
    [ -n "${pid:-}" ] || continue
    if kill -0 "$pid" 2>/dev/null; then
      echo "stopping gpu $gpu (port $port, pid $pid)"
      kill "$pid"
    fi
  done < "$PID_FILE"
  sleep 3
  # Only PIDs this script recorded are touched; an unrelated llama-server on
  # this host is left alone.
  while read -r pid gpu port; do
    [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
  done < "$PID_FILE"
  : > "$PID_FILE"
  echo "stopped"
}

case "${1:-start}" in
  start)  start ;;
  status) status ;;
  stop)   stop ;;
  *) echo "usage: $0 [start|status|stop]" >&2; exit 2 ;;
esac
