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
# Resolve env.sh NEXT TO THIS SCRIPT, not from a hardcoded path: corona-llm/
# symlinks these scripts and carries its own env.sh, and a hardcoded default
# would have every corona invocation silently load Tuolumne's paths and arch.
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"

GATEWAY_PORT=${GATEWAY_PORT:-4000}
BASE_PORT=${BASE_PORT:-8050}
# Per-node shape, defaulted BY THE CLUSTER's env.sh rather than by this file.
# Tuolumne is 4 MI300A per node with 96 cores; corona is 8 MI50 per node with
# 48. GPUS_PER_NODE counts SERVERS per node and GPUS_PER_SERVER how many GPUs
# each one gets, which is how a model larger than one card's VRAM is served:
# gpt-oss-120b is 63 GB against the MI50's 32, so it runs as GPUS_PER_NODE=1
# GPUS_PER_SERVER=8 (one server sharded across the node) where on Tuolumne's
# 128 GB APUs it is simply one server per GPU.
GPUS_PER_NODE=${GPUS_PER_NODE:-${FLEET_GPUS_PER_NODE:-4}}
GPUS_PER_SERVER=${GPUS_PER_SERVER:-${FLEET_GPUS_PER_SERVER:-1}}
CORES_PER_SERVER=${CORES_PER_SERVER:-${FLEET_CORES_PER_SERVER:-22}}
GATEWAY_CORES=${GATEWAY_CORES:-${FLEET_GATEWAY_CORES:-8}}
LLM_KEY=${LLM_KEY:-${FLEET_KEY:-sk-tuolumne}}
# Defaults are the measured ones, not the historical ones:
#   solo      one slot per GPU, so a conversation's prompt cache is never
#             evicted by another agent's (prefill was 77% of GPU time).
#   reference the sampling gpt-oss was evaluated with (temp 1.0, top-p 1.0,
#             top-k disabled). `diverse` truncated the distribution twice.
#   medium    the reasoning effort published SWE-bench work uses; low is not a
#             setting the model was evaluated under.
export PROFILE=${PROFILE:-${FLEET_PROFILE:-solo}}
export SAMPLING=${SAMPLING:-reference}
export GPTOSS_EFFORT=${GPTOSS_EFFORT:-low}
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

# No `-t` on any `flux run` below.
#
# Inside an allocation a job inherits the instance's lifetime, and naming a
# duration longer than what remains is refused outright:
#
#   flux-run: ERROR: job duration (1h) exceeds remaining instance lifetime (48m)
#
# Measured: with 48 minutes left on the allocation, staging asked for `-t 60m`,
# both `dbcast` and its `dcp` fallback were rejected before doing any work, and
# the deploy went on to launch servers whose weights had never been copied —
# reporting `INCOMPLETE 0/63387346208` and then waiting for a fleet that could
# not start. A ceiling that is only ever wrong near the end of an allocation is
# worse than none: it fails exactly when time is shortest.

# ---- 1. stage weights onto each node's SSD -------------------------------------
_stage_with_dcp() {  # $1 = model key, $2 = source, $3 = leaf name
    local key=$1 from=$2 leaf=$3
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
            flux run -N1 -n "$PPN" --requires="host:$h" \
                bash -c "module load $MPIFILEUTILS_MODULE >/dev/null 2>&1
                         mkdir -p '$MODEL_CACHE'
                         exec dcp '$from' '$MODEL_CACHE/$leaf'" \
                > "$RUNDIR/dcp-$h-$key.log" 2>&1
            echo "    $h: rc=$?"
        ) &
        pids+=($!)
    done
    for pid in "${pids[@]}"; do wait "$pid"; done
}

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
    missing=$(flux run -N "$NNODES" --requires="$HOSTSPEC" --tasks-per-node 1 \
        bash -c "got=\$(du -s --block-size=1 '$MODEL_CACHE/$leaf' 2>/dev/null | cut -f1)
                 [ \"\${got:-0}\" -ge '$size' ] || hostname" 2>/dev/null | sort -u | tr '\n' ' ')
    missing=${missing// /}
    if [ -z "$missing" ]; then
        echo "  ${ALIAS[$key]}: already staged on all $NNODES node(s)"
        return 0
    fi

    echo "  ${ALIAS[$key]}: staging $(numfmt --to=iec "${size:-0}" 2>/dev/null) to $MODEL_CACHE"
    # `dbcast` for a single file: read the source ONCE, then propagate.
    #
    # The alternative below runs one `dcp` per node, which means every node
    # independently reads the whole model out of Lustre — N nodes, N full reads
    # of the same 60 GB, all hitting the same filesystem at once. `dbcast` exists
    # for exactly this shape: it reads the source once and spreads it node to
    # node, so the cost stops scaling with the node count.
    #
    #   https://mpifileutils.readthedocs.io/en/v0.11.1/dbcast.1.html
    #
    # It broadcasts ONE FILE, so a sharded model staged as a directory still
    # takes the per-node `dcp` path.
    #
    # TWO tasks per node, not one. dbcast refuses fewer:
    #
    #   dbcast.c:624 ERROR: Must run with at least two tasks per node
    #
    # Reasoning that its tree is over ranks and one per node avoids resending
    # was wrong — it needs a second task on each node to write while the first
    # receives. And the failure was silent: the wrapper returned rc=0, so the
    # `dcp` fallback never fired and the deploy went on to launch servers whose
    # weights had never been copied.
    local pids=() h
    if [ -f "$from" ]; then
        echo "    dbcast: one read of the source, propagated across $NNODES node(s)"
        flux run -N "$NNODES" --requires="$HOSTSPEC" --tasks-per-node 2 \
            bash -c "module load $MPIFILEUTILS_MODULE >/dev/null 2>&1
                     mkdir -p '$MODEL_CACHE'
                     exec dbcast '$from' '$MODEL_CACHE/$leaf'" \
            > "$RUNDIR/dbcast-$key.log" 2>&1
        local rc=$?
        # Trust the BYTES, not the exit code.
        #
        # dbcast reported rc=0 while copying nothing — its error went to the log
        # and the launcher still exited clean. A staging step that says it
        # succeeded and leaves an empty destination is worse than one that
        # fails, because the fallback is skipped and the servers start anyway.
        local staged
        staged=$(flux run -N "$NNODES" --requires="$HOSTSPEC" --tasks-per-node 1 \
                 bash -c "du -s --block-size=1 '$MODEL_CACHE/$leaf' 2>/dev/null | cut -f1" \
                 2>/dev/null | sort -n | head -1)
        echo "    dbcast: rc=$rc, smallest copy $(numfmt --to=iec "${staged:-0}" 2>/dev/null)"
        if [ $rc -ne 0 ] || [ "${staged:-0}" -lt "$size" ]; then
            # Fall back rather than fail the deploy: a staging method that does
            # not work here should cost time, not the run.
            echo "    dbcast did not stage the file (see $RUNDIR/dbcast-$key.log)"
            echo "    — falling back to dcp"
            _stage_with_dcp "$key" "$from" "$leaf"
        fi
    else
        # A directory. dbcast takes a file, so this keeps the per-node copy.
        _stage_with_dcp "$key" "$from" "$leaf"
    fi

    flux run -N "$NNODES" --requires="$HOSTSPEC" --tasks-per-node 1 \
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
        jid=$(flux submit -N1 -n1 -c "$CORES_PER_SERVER" -g "$GPUS_PER_SERVER" --requires="host:$h" \
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

# Rebuild the gateway config from the replicas that ACTUALLY registered.
#
# The config below is written from the host x GPU loop this deploy INTENDS to
# launch, before any of it exists — which is the right thing at that moment,
# because the gateway has to start before the fleet is warm. It is the wrong
# thing to leave in place afterwards.
#
# Measured: asked for 8 nodes x 4 GPUs it advertised 32 backends and aliases
# `@0..@31`; 23 servers ever came up. The consequences ran for a whole
# benchmark — the shared name load-balanced onto backends that were never there
# (`500 InternalServerError`), every pinned alias past the real count returned
# `400: Invalid model name`, and the advertised capacity was a third larger than
# the fleet, so the sizing arithmetic over-subscribed it by that much again.
#
# `$RUNDIR/nodes/*.json` is what each replica writes as it comes up — the same
# source `cluster.json`'s `servers` field already trusts. Rebuilding from it
# once the readiness wait is over makes the config describe the fleet, and
# renumbers the aliases contiguously so a client counting `@0..@N-1` cannot land
# in a hole.
rebuild_config_from_records() {
    local PBENCH_PY=${BENCH_PY:-/p/lustre5/haridev/phronix-bench/venv/bin/python}
    [ -x "$PBENCH_PY" ] || PBENCH_PY=$(command -v python3)
    [ -n "$PBENCH_PY" ] || { echo "  no python to rebuild the config with"; return 1; }
    local records=("$RUNDIR"/nodes/*.json)
    [ -e "${records[0]}" ] || { echo "  no node records; leaving the config as written"; return 1; }

    local live
    live=$("$PBENCH_PY" - "$RUNDIR" "$MODEL_ALIAS" <<'EOF'
import glob, json, os, sys

run_dir, alias = sys.argv[1], sys.argv[2]
seen = []
for path in sorted(glob.glob(os.path.join(run_dir, "nodes", "*.json"))):
    try:
        with open(path) as handle:
            row = json.load(handle)
    except Exception:
        continue
    host, port = row.get("host"), row.get("port")
    if host and port and (host, port) not in seen:
        seen.append((host, port))

lines = ["model_list:"]
for index, (host, port) in enumerate(seen):
    for name in (alias, f"{alias}@{index}"):
        lines += [f"  - model_name: {name}",
                  "    litellm_params:",
                  f"      model: openai/{alias}",
                  f"      api_base: http://{host}:{port}/v1",
                  "      api_key: dummy",
                  "      rpm: 100000"]
print("\n".join(lines))
print(len(seen), file=sys.stderr)
EOF
) || return 1
    [ -n "$live" ] || return 1

    cp "$CFG" "$CFG.as-intended"
    {
        echo "$live"
        sed -n '/^router_settings:/,$p' "$CFG.as-intended"
    } > "$CFG"
    echo "  gateway config rebuilt from $(grep -c 'api_base' "$CFG") backend entr(ies)"
    return 0
}

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
YAML
  echo "  master_key: $LLM_KEY"
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
    printf '  "gateway": {"host": "%s", "port": %s, "job": "%s", "key": "%s"},\n' \
      "$GW_HOST" "$GATEWAY_PORT" "$gwid" "$LLM_KEY"
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
READY_PY=${BENCH_PY:-/p/lustre5/haridev/phronix-bench/venv/bin/python}
[ -x "$READY_PY" ] || READY_PY=$(command -v python3)

deadline=$((SECONDS + ${READY_TIMEOUT:-1200}))
total=$((NNODES * GPUS_PER_NODE))
# Stop when the fleet is FULL, or when it has stopped growing.
#
# This only ever broke on `ready == total`, where total is what was ASKED for —
# so a deploy that lands 23 of 32 servers polls for the whole 20-minute
# READY_TIMEOUT after the last one came up, and the script looks hung while the
# fleet has been serving for a quarter of an hour. Measured exactly that.
#
# A count that has not moved for three polls in a row is the fleet's real size:
# a server still loading its weights makes progress somewhere in that 90s, and
# one that is never coming up does not. The deadline is still the outer bound,
# for the case where nothing has come up at all and there is nothing to settle.
STABLE_POLLS=${STABLE_POLLS:-3}
previous=-1
unchanged=0
while (( SECONDS < deadline )); do
    # Health checked DIRECTLY, not through a Flux job.
    #
    # This ran `flux run -N$NNODES ... -t 5m` every 30 seconds purely to curl
    # localhost on each node — so every poll queued for an allocation of the
    # whole fleet, competed with the servers it was waiting for, and could sit
    # in the scheduler longer than the interval it was meant to sample.
    #
    # The server ports answer from here. Measured: all 24 backends probed from
    # the login node in well under a second. So ask them, in parallel, and spend
    # no scheduler resources at all.
    ready=$(HOSTS_CSV="$(IFS=,; echo "${HOSTS[*]}")" \
            GPUS="$GPUS_PER_NODE" BASE="$BASE_PORT" \
            "$READY_PY" - <<'EOF' 2>/dev/null
import os, urllib.request
from concurrent.futures import ThreadPoolExecutor

hosts = [h for h in os.environ.get("HOSTS_CSV", "").split(",") if h]
gpus = int(os.environ.get("GPUS", "4"))
base = int(os.environ.get("BASE", "8050"))
targets = [f"http://{h}:{base + g}/health" for h in hosts for g in range(gpus)]


def up(url):
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            return response.status == 200
    except Exception:
        return False


if targets:
    with ThreadPoolExecutor(max_workers=min(64, len(targets))) as pool:
        print(sum(pool.map(up, targets)))
else:
    print(0)
EOF
)
    ready=${ready:-0}
    # What actually REGISTERED, from the per-GPU records each server writes as
    # it starts — the same source `status.sh` counts, and the reason the two
    # disagreed: status said "23/23 up" while this waited for 32 and looked hung.
    registered=$(ls "$RUNDIR"/nodes/*.json 2>/dev/null | wc -l)
    if [ "$registered" -gt 0 ] && [ "$total" -ne "$registered" ]; then
        echo "  ${ready}/$total ready  (${registered} server(s) ever registered)"
    else
        echo "  ${ready}/$total ready"
    fi
    [ "$ready" = "$total" ] && break
    # Every server that registered is healthy AND no new one appeared since the
    # last poll: that is the fleet, whatever was asked for.
    #
    # Both halves are needed. Without the healthy check this exits while servers
    # are still loading; without the "no new ones" check it exits at the first
    # poll, when two have registered, two are healthy, and thirty are still
    # starting — which is worse than waiting too long.
    if [ "$registered" -gt 0 ] && [ "$ready" = "$registered" ] \
       && [ "$registered" = "${seen_registered:--1}" ]; then
        echo "  all ${ready} registered server(s) are healthy — continuing"
        break
    fi
    seen_registered=$registered

    if [ "$ready" = "$previous" ]; then
        unchanged=$((unchanged + 1))
    else
        unchanged=0
    fi
    previous=$ready
    if [ "$unchanged" -ge "$STABLE_POLLS" ] && [ "$ready" -gt 0 ]; then
        echo "  settled at ${ready}/$total after $((STABLE_POLLS * 30))s with no change"
        echo "  — the rest are not coming up; continuing with what is serving"
        break
    fi
    sleep 30
done

# Correct the gateway now that the fleet's real shape is known.
#
# Only when it came up SHORT: a full fleet already matches what was written, and
# restarting a healthy gateway for an identical config would drop in-flight
# requests for nothing.
if [ "${ready:-0}" != "$total" ] && [ "${ready:-0}" -gt 0 ]; then
    echo
    echo "=== ${ready}/${total} replica(s) came up — correcting the gateway"
    if rebuild_config_from_records; then
        # Restart the gateway so it loads the corrected list. The replicas are
        # untouched and keep their weights; this is the gateway process only.
        flux cancel "$gwid" 2>/dev/null && echo "  cancelled gateway $gwid"
        sleep 3
        gwid=$(flux submit -N1 -n1 -c "$GATEWAY_CORES" --requires="host:$GW_HOST" \
                --job-name="litellm-$GW_HOST" --output="$RUNDIR/litellm.log" \
                "$LLM_SCRIPTS/gateway-node.sh" "$CFG" "$GATEWAY_PORT")
        echo "  gateway restarted as $gwid"
        deadline=$((SECONDS + 180))
        until curl -sf -m 4 "http://$GW_HOST:$GATEWAY_PORT/health/liveliness" > /dev/null; do
            (( SECONDS < deadline )) || { echo "  gateway did not come back; see $RUNDIR/litellm.log"; break; }
            sleep 3
        done
    fi
fi

write_cluster_json "${ready:-0}/$total"

echo
echo "================================================================="
echo "Gateway:   http://$GW_HOST:$GATEWAY_PORT   (key: $LLM_KEY)"
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
echo "Stop:      flux proxy <alloc> $(basename "$LLM_SCRIPTS")/stop.sh"
echo "================================================================="
