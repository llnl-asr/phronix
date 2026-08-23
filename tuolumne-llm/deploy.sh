#!/bin/bash
# One command: stage the weights onto every node's SSD, then serve them.
#
#   flux proxy <alloc-jobid> tuolumne-llm/deploy.sh
#   flux proxy <alloc-jobid> tuolumne-llm/deploy.sh gptoss120 nemosuper gptoss20 nemotron
#   PROFILE=agent SAMPLING=greedy flux proxy <alloc> tuolumne-llm/deploy.sh
#
# Arguments are one model key per GPU, in GPU order, repeated on every node.
# With one key, every GPU serves that model — 32 replicas of one model, which is
# what you want when one model is clearly best. With four, every node serves the
# whole mixture and each model gets one replica per node.
#
# What it does, in order:
#
#   1. Checks each node for a local copy of every model it will serve, and dcp's
#      the missing ones. Staging is skipped entirely when the copies are already
#      there, so re-deploying after a profile change costs nothing.
#   2. Launches one Flux job per GPU, all at once.
#   3. Starts the LiteLLM gateway and waits for the fleet to answer.
#   4. Writes cluster.json, which is what the benchmark reads.
#
# Why staging is not optional-by-default: every server otherwise reads its
# weights off lustre, and gpt-oss-120b is 63 GB. Eight nodes starting together
# ask the PFS for half a terabyte at once and it does not share it evenly —
# measured, 20 of 32 servers healthy at five minutes with three whole nodes
# still short of ready at fourteen, weights resident but KV not yet allocated.
# Nothing was broken; they were starved of read bandwidth. A local copy removes
# the shared resource instead of scheduling around it.
set -uo pipefail
source "${LLM_SCRIPTS:-/usr/WS2/haridev/phronix/tuolumne-llm}/env.sh"

GATEWAY_PORT=${GATEWAY_PORT:-4000}
BASE_PORT=${BASE_PORT:-8050}
GPUS_PER_NODE=${GPUS_PER_NODE:-4}
# Defaults are the measured ones, not the historical ones:
#   solo      one slot per GPU, so a conversation's prompt cache is never
#             evicted by another agent's (prefill was 77% of GPU time).
#   reference the sampling gpt-oss was evaluated with (temp 1.0, top-p 1.0,
#             top-k disabled). `diverse` truncated the distribution twice.
#   medium    the reasoning effort published SWE-bench work uses; low is not a
#             setting the model was evaluated under.
export PROFILE=${PROFILE:-solo}
export SAMPLING=${SAMPLING:-reference}
export GPTOSS_EFFORT=${GPTOSS_EFFORT:-medium}
export GPTOSS_THINK_BUDGET=${GPTOSS_THINK_BUDGET:-2048}

#: Node-local, on real disk. NOT /tmp — that is tmpfs on these nodes, so a
#: staged model would be held in RAM, taken straight out of what the weights and
#: KV need.
export MODEL_CACHE=${MODEL_CACHE:-/l/ssd/$(id -un)/models}

#: dcp ranks per node. High on purpose: a 60 GB file across many ranks keeps
#: both lustre's stripes and the local SSD's queues busy, and the node's 96
#: cores are idle while the fleet is down.
PPN=${PPN:-64}
MPIFILEUTILS_MODULE=${MPIFILEUTILS_MODULE:-mpifileutils/0.12}
SKIP_STAGE=${SKIP_STAGE:-0}

declare -A ALIAS=([nemotron]=nemotron-3.5 [muse]=muse-glimmer [ornith]=ornith-1.5
                  [gptoss120]=gpt-oss-120b [gptoss20]=gpt-oss-20b
                  [nemosuper]=nemotron-super-49b)
declare -A SOURCE=(
    [nemotron]="${MODEL_NEMOTRON:-}"   [muse]="${MODEL_MUSE:-}"
    [ornith]="${MODEL_ORNITH:-}"       [gptoss120]="${MODEL_GPTOSS120:-}"
    [gptoss20]="${MODEL_GPTOSS20:-}"   [nemosuper]="${MODEL_NEMOSUPER:-}"
)

# One model key per GPU. A single key fills every GPU with it.
if [ $# -gt 0 ]; then
    GPU_MODEL=("$@")
else
    read -r -a GPU_MODEL <<< "${MODELS:-gptoss120}"
fi
if (( ${#GPU_MODEL[@]} == 1 )); then
    for ((g = 1; g < GPUS_PER_NODE; g++)); do GPU_MODEL+=("${GPU_MODEL[0]}"); done
fi
for key in "${GPU_MODEL[@]}"; do
    [[ -n ${ALIAS[$key]:-} ]] || { echo "unknown model '$key' (have: ${!ALIAS[*]})" >&2; exit 2; }
    [[ -f ${SOURCE[$key]:-} ]] || { echo "no weights for '$key': ${SOURCE[$key]:-unset}" >&2; exit 2; }
done

RUNDIR=$LLM_ROOT/logs/run-$(date +%Y%m%d-%H%M%S)
mkdir -p "$RUNDIR/nodes"
ln -sfn "$RUNDIR" "$LLM_ROOT/logs/latest"

read -r -a ALL_HOSTS <<< "$(flux hostlist -e "$(flux getattr hostlist)")"
# NNODES serves on a PREFIX of the allocation, leaving the rest free for other
# work (the benchmark's containers, say). Unset means the whole allocation.
HOSTS=("${ALL_HOSTS[@]:0:${NNODES:-${#ALL_HOSTS[@]}}}")
NNODES=${#HOSTS[@]}
# Every `flux run -N$NNODES` below must land on THESE nodes, not on any N the
# scheduler likes: staging to and polling the wrong nodes is silent and wrong.
HOSTSPEC="host:$(IFS=,; echo "${HOSTS[*]}")"

echo "nodes    : $NNODES (${HOSTS[*]})"
echo "profile  : $PROFILE   sampling: $SAMPLING   effort: $GPTOSS_EFFORT (budget $GPTOSS_THINK_BUDGET)"
echo "placement:"
for ((g = 0; g < GPUS_PER_NODE; g++)); do
    key=${GPU_MODEL[$((g % ${#GPU_MODEL[@]}))]}
    echo "  gpu$g port $((BASE_PORT + g)) -> ${ALIAS[$key]}"
done

# ---- 1. stage weights onto each node's SSD -------------------------------------
stage_one() {  # $1 = model key
    local key=$1 src=${SOURCE[$1]} from leaf size
    # A sharded model is staged as its directory: llama.cpp opens the first
    # shard and finds its siblings beside it.
    if [[ $(basename "$src") == *-00001-of-* ]]; then
        from=$(dirname "$src"); leaf=$(basename "$from")
    else
        from=$src; leaf=$(basename "$src")
    fi
    size=$(du -sb "$from" 2>/dev/null | cut -f1)

    # Which nodes are missing it? Skipping the ones that have it is what makes
    # redeploying cheap.
    local missing
    missing=$(flux run -N "$NNODES" --requires="$HOSTSPEC" --tasks-per-node 1 -t 5m \
        bash -c "got=\$(du -s --block-size=1 '$MODEL_CACHE/$leaf' 2>/dev/null | cut -f1)
                 [ \"\${got:-0}\" -ge '$size' ] || hostname" 2>/dev/null | sort -u | tr '\n' ' ')
    missing=${missing// /}
    if [ -z "$missing" ]; then
        echo "  ${ALIAS[$key]}: already staged on all $NNODES node(s)"
        return 0
    fi

    echo "  ${ALIAS[$key]}: staging $(numfmt --to=iec "${size:-0}" 2>/dev/null) to $MODEL_CACHE"
    # ONE dcp per node, not one across the allocation.
    #
    # dcp assumes a SHARED destination and splits the work by rank. Pointed at a
    # node-local path it does exactly that — measured, a single collective copy
    # left each node holding a different fraction (7.9 GB, 15.9 GB, 23.8 GB ...)
    # because each rank wrote only its own chunk wherever it landed. The result
    # looks like a copy and loads like a corrupt file. So the ranks all go on
    # ONE host, and the hosts run concurrently.
    local pids=() h
    for h in "${HOSTS[@]}"; do
        (
            flux run -N1 -n "$PPN" --requires="host:$h" -t 60m \
                bash -c "module load $MPIFILEUTILS_MODULE >/dev/null 2>&1
                         mkdir -p '$MODEL_CACHE'
                         exec dcp '$from' '$MODEL_CACHE/$leaf'" \
                > "$RUNDIR/dcp-$h-$key.log" 2>&1
            echo "    $h: rc=$?"
        ) &
        pids+=($!)
    done
    for pid in "${pids[@]}"; do wait "$pid"; done

    flux run -N "$NNODES" --requires="$HOSTSPEC" --tasks-per-node 1 -t 10m \
        bash -c "got=\$(du -s --block-size=1 '$MODEL_CACHE/$leaf' 2>/dev/null | cut -f1)
                 if [ \"\${got:-0}\" -ge '$size' ]; then echo \"    \$(hostname): ok\"
                 else echo \"    \$(hostname): INCOMPLETE \${got:-0}/$size\"; fi" 2>&1 | sort
}

if [ "$SKIP_STAGE" != 1 ]; then
    echo
    echo "=== staging weights"
    for key in $(printf '%s\n' "${GPU_MODEL[@]}" | sort -u); do
        stage_one "$key"
    done
fi

# ---- 2. one Flux job per GPU, all at once -----------------------------------
#
# No stagger: every server now reads its own node's SSD, so there is no shared
# resource left to contend for. The four on a node read the same local file and
# the page cache serves the second through fourth from memory.
echo
echo "=== launching $((NNODES * GPUS_PER_NODE)) server(s)"
for h in "${HOSTS[@]}"; do
    for ((g = 0; g < GPUS_PER_NODE; g++)); do
        key=${GPU_MODEL[$((g % ${#GPU_MODEL[@]}))]}
        port=$((BASE_PORT + g))
        jid=$(flux submit -N1 -n1 -c 22 -g 1 --requires="host:$h" \
                --job-name="llama-$h-gpu$g" --output="$RUNDIR/$h-gpu$g.flux.log" \
                --env=RUNDIR="$RUNDIR" --env=PROFILE="$PROFILE" \
                --env=SAMPLING="$SAMPLING" --env=MODEL_CACHE="$MODEL_CACHE" \
                --env=GPTOSS_EFFORT="$GPTOSS_EFFORT" \
                --env=GPTOSS_THINK_BUDGET="$GPTOSS_THINK_BUDGET" \
                "$LLM_SCRIPTS/gpu-server.sh" "$key" "$g" "$port")
        echo "$jid $h gpu$g $key" >> "$RUNDIR/jobs.txt"
    done
done
echo "  submitted; weights load from local SSD"

# ---- 3. LiteLLM config and gateway ------------------------------------------
CFG=$RUNDIR/litellm.yaml
{
  echo "model_list:"
  # Every backend twice: once under the shared name, once under its own.
  #
  # The shared name load-balances, which is right for one-off calls. The pinned
  # names exist because an agent conversation re-sends its whole history every
  # turn, and llama.cpp caches that history PER SERVER — so a turn that lands on
  # a different backend re-processes everything from scratch.
  #
  # Measured on the load-balanced fleet: 189,193,540 prompt tokens against
  # 5,228,544 generated (36:1), with prefill costing more GPU time than decode
  # (86,570s vs 73,445s). A repeat request to the same backend reported 82 of 87
  # prompt tokens cached; scattered across 32 backends it reported 0.
  #
  # A client pins by ASKING FOR THE ALIAS, which both harnesses can do — one
  # passes `--model`, the other sets ANTHROPIC_MODEL. No gateway feature needed.
  index=0
  for h in "${HOSTS[@]}"; do
      for ((g = 0; g < GPUS_PER_NODE; g++)); do
          alias=${ALIAS[${GPU_MODEL[$((g % ${#GPU_MODEL[@]}))]}]}
          for name in "$alias" "$alias@$index"; do
              echo "  - model_name: $name"
              echo "    litellm_params:"
              echo "      model: openai/$alias"
              echo "      api_base: http://$h:$((BASE_PORT + g))/v1"
              echo "      api_key: dummy"
              echo "      rpm: 100000"
          done
          index=$((index + 1))
      done
  done
  cat <<'YAML'
router_settings:
  routing_strategy: least-busy
  num_retries: 2
litellm_settings:
  drop_params: true
  request_timeout: 1800
general_settings:
  master_key: sk-tuolumne
YAML
} > "$CFG"

GW_HOST=${HOSTS[0]}
gwid=$(flux submit -N1 -n1 -c 4 --requires="host:$GW_HOST" \
        --job-name="litellm-$GW_HOST" --output="$RUNDIR/litellm.log" \
        "$LLM_SCRIPTS/gateway-node.sh" "$CFG" "$GATEWAY_PORT")
echo "$gwid $GW_HOST gateway" >> "$RUNDIR/jobs.txt"

# ---- cluster.json: what the benchmark reads ---------------------------------
#
# Written BEFORE the readiness wait, not after.
#
# Everything in it — gateway, servers, models, pinned aliases — is known as soon
# as the jobs are submitted. Writing it afterwards meant an interrupted or
# timed-out wait left NO file, so the benchmark kept reading the previous
# deployment's: a run dir from the day before, no `pinned_models`, and therefore
# no cache affinity. The fleet was correct and the client could not tell.
#
# Rewritten again after the wait, so `ready` reflects reality when the wait
# completes normally.
write_cluster_json() {
  {
    printf '{\n'
    printf '  "run_dir": "%s",\n' "$RUNDIR"
    printf '  "profile": "%s",\n' "$PROFILE"
    printf '  "sampling": "%s",\n' "$SAMPLING"
    printf '  "ready": "%s",\n' "${1:-pending}"
    printf '  "pinned_models": %s,\n' \
      "$(python3 -c "
import json,sys
print(json.dumps([f'{sys.argv[1]}@{i}' for i in range(int(sys.argv[2]))]))" \
        "${ALIAS[${GPU_MODEL[0]}]}" "$((NNODES * GPUS_PER_NODE))")"
    printf '  "models": [%s],\n' \
      "$(printf '%s\n' "${GPU_MODEL[@]}" | sort -u | while read -r k; do printf '"%s",' "${ALIAS[$k]}"; done | sed 's/,$//')"
    printf '  "alias": "%s",\n' "${ALIAS[${GPU_MODEL[0]}]}"
    printf '  "gateway": {"host": "%s", "port": %s, "job": "%s", "key": "sk-tuolumne"},\n' \
      "$GW_HOST" "$GATEWAY_PORT" "$gwid"
    printf '  "servers": [\n'
    cat "$RUNDIR"/nodes/*.json 2>/dev/null | paste -sd, - | sed 's/,/,\n    /g; s/^/    /'
    printf '\n  ]\n}\n'
  } > "$RUNDIR/cluster.json.tmp"

  # Only replace the live file once the new one parses. A half-written
  # cluster.json is worse than a stale one: the benchmark fails to start rather
  # than starting against the wrong endpoint.
  if python3 -c "import json,sys; json.load(open(sys.argv[1]))" \
       "$RUNDIR/cluster.json.tmp" 2>/dev/null; then
    mv "$RUNDIR/cluster.json.tmp" "$RUNDIR/cluster.json"
    cp "$RUNDIR/cluster.json" "$LLM_SCRIPTS/cluster.json"
    return 0
  fi
  echo "WARNING: generated cluster.json is not valid JSON; keeping the old one" >&2
  return 1
}

write_cluster_json pending && echo "wrote $LLM_SCRIPTS/cluster.json"

echo
echo "=== waiting for the fleet"
deadline=$((SECONDS + ${READY_TIMEOUT:-1200}))
total=$((NNODES * GPUS_PER_NODE))
while (( SECONDS < deadline )); do
    ready=$(flux run -N "$NNODES" --requires="$HOSTSPEC" --tasks-per-node 1 -t 5m bash -c "
        n=0
        for g in \$(seq 0 $((GPUS_PER_NODE - 1))); do
            curl -sf -m 4 -o /dev/null http://localhost:\$(($BASE_PORT + g))/health && n=\$((n+1))
        done
        echo \$n" 2>/dev/null | paste -sd+ - | bc 2>/dev/null)
    echo "  ${ready:-0}/$total ready"
    [ "${ready:-0}" = "$total" ] && break
    sleep 30
done

write_cluster_json "${ready:-0}/$total"

echo
echo "================================================================="
echo "Gateway:   http://$GW_HOST:$GATEWAY_PORT   (key: sk-tuolumne)"
echo "Models:    $(printf '%s\n' "${GPU_MODEL[@]}" | sort -u | while read -r k; do printf '%s ' "${ALIAS[$k]}"; done)"
echo "Profile:   $PROFILE    Sampling: $SAMPLING"
echo "Weights:   $MODEL_CACHE (node-local)"
# What this fleet can serve, and the workload that would use it.
#
# Stated at deploy time because it is the number that decides whether a run is
# worth the allocation: a task unit (one task in one arm) occupies about half a
# slot — measured at 6.4 requests in flight for 12 units — so filling N slots
# takes roughly N / (0.53 x arms) concurrent tasks. Six tasks against 128 slots
# is 5% and correct for six tasks; it is not a fault, but it is worth knowing
# before reserving eight nodes for it.
SLOTS_EACH=$(curl -sf -m 8 "http://$GW_HOST:$BASE_PORT/props" 2>/dev/null \
             | python3 -c "import json,sys; print(json.load(sys.stdin).get('total_slots') or 0)" 2>/dev/null)
CAPACITY=$(( ${#HOSTS[@]} * GPUS_PER_NODE * ${SLOTS_EACH:-0} ))
if [ "$CAPACITY" -gt 0 ]; then
  echo "Capacity:  $CAPACITY concurrent request(s) — $((CAPACITY * 100 / 106)) task(s)" \
       "in flight (2 arms) would fill it"
fi
echo "Run dir:   $RUNDIR"
echo "Config:    $LLM_SCRIPTS/cluster.json"
echo "Stop:      flux proxy <alloc> tuolumne-llm/stop.sh"
echo "================================================================="
