#!/bin/bash
# Serve SEVERAL models at once across the allocation, behind one gateway.
#
#   flux proxy <alloc-jobid> tuolumne-llm/run-cluster-moe.sh
#   MODELS="nemotron:3 ornith:3 muse:2" ... run-cluster-moe.sh
#
# `run-cluster.sh` puts one model on every GPU. This puts a different model on
# each GROUP of nodes and lists them all in one LiteLLM config, so a client can
# ask for any of them by name against a single endpoint.
#
# Why: the research pipeline generates candidates — aspects to investigate,
# approaches to try — and candidates from one model with greedy decoding are one
# line of thought repeated. Measured on the single-model fleet: five phronix
# tool calls across a six-task run, aspects=0 and approaches=0 in every record,
# and the same trace line emitted six times in one second. Asking three
# different models the same question is the cheapest source of genuine
# diversity available, and diversity is the whole point of the stage.
#
# The split is by node because a GPU holds one model: 128 GB of HBM against
# 30-38 GB of weights plus a megabyte-per-slot KV pool.
set -euo pipefail
source "${LLM_SCRIPTS:-/usr/WS2/haridev/phronix/tuolumne-llm}/env.sh"

GATEWAY_PORT=${GATEWAY_PORT:-4000}
BASE_PORT=${BASE_PORT:-8050}
GPUS_PER_NODE=${GPUS_PER_NODE:-4}
export PROFILE=${PROFILE:-wide}

#: One model per GPU, in GPU order, repeated on every node.
#:
#: Four models, four GPUs, so every node serves the whole mixture and each model
#: gets one replica per node — eight replicas across the allocation. Placing
#: them per GPU rather than per node means a node failure costs one replica of
#: each rather than every replica of one.
#:
#: Chosen for ACTIVE parameters and tool training, not headline size. The
#: incumbent 30B-A3B activates ~3B per token, which is why it called one tool
#: and drifted; gpt-oss was post-trained for agentic tool use, and
#: Nemotron-Super is dense.
MODELS=${MODELS:-"gptoss120 nemosuper gptoss20 nemotron"}

declare -A ALIAS=([nemotron]=nemotron-3.5 [muse]=muse-glimmer [ornith]=ornith-1.5
                  [gptoss120]=gpt-oss-120b [gptoss20]=gpt-oss-20b
                  [nemosuper]=nemotron-super-49b)

RUNDIR=$LLM_ROOT/logs/run-$(date +%Y%m%d-%H%M%S)
mkdir -p "$RUNDIR/nodes"
ln -sfn "$RUNDIR" "$LLM_ROOT/logs/latest"

read -r -a ALL_HOSTS <<< "$(flux hostlist -e "$(flux getattr hostlist)")"
echo "allocation has ${#ALL_HOSTS[@]} node(s): ${ALL_HOSTS[*]}"

# ---- assign one model per GPU, the same way on every node --------------------
read -r -a GPU_MODEL <<< "$MODELS"
for key in "${GPU_MODEL[@]}"; do
    [[ -n ${ALIAS[$key]:-} ]] || { echo "unknown model '$key'"; exit 1; }
done
if (( ${#GPU_MODEL[@]} != GPUS_PER_NODE )); then
    echo "MODELS lists ${#GPU_MODEL[@]} model(s) for $GPUS_PER_NODE GPU(s);" \
         "GPU g serves model g % ${#GPU_MODEL[@]}" >&2
fi

echo "plan (per node):"
for ((g = 0; g < GPUS_PER_NODE; g++)); do
    key=${GPU_MODEL[$((g % ${#GPU_MODEL[@]}))]}
    echo "  gpu$g -> $key (${ALIAS[$key]})"
done

# ---- launch one llama-server per GPU, with that node's model -----------------
#
# Every server starts at once, on every node, reading its own local copy.
#
# Startup used to be lustre-bound: eight nodes asking the PFS for half a
# terabyte together left 20 of 32 servers healthy at five minutes and three
# whole nodes short of ready at fourteen. Staggering hid that by serialising it.
#
# `stage-models.sh` removes the cause instead — each node holds the weights on
# its own SSD, so there is no shared resource left to contend for and no reason
# to wait between nodes. The four servers on a node read the same local file,
# and the page cache serves the second through fourth from memory.
#
# STAGGER is kept for the unstaged case: without a local copy this is back to
# reading the PFS, and then the wait is worth it.
STAGGER=${STAGGER:-0}
for h in "${ALL_HOSTS[@]}"; do
    for ((g = 0; g < GPUS_PER_NODE; g++)); do
        key=${GPU_MODEL[$((g % ${#GPU_MODEL[@]}))]}
        port=$((BASE_PORT + g))
        jid=$(flux submit -N1 -n1 -c 22 -g 1 --requires="host:$h" \
                --job-name="llama-$h-gpu$g" --output="$RUNDIR/$h-gpu$g.flux.log" \
                --env=RUNDIR="$RUNDIR" --env=PROFILE="$PROFILE" \
                "$LLM_SCRIPTS/gpu-server.sh" "$key" "$g" "$port")
        echo "$jid $h gpu$g $key" >> "$RUNDIR/jobs.txt"
        echo "submitted $jid on $h gpu$g port $port ($key)"
    done
    [ "${STAGGER:-0}" -gt 0 ] && sleep "$STAGGER"
done

# ---- one LiteLLM config listing every model ---------------------------------
CFG=$RUNDIR/litellm.yaml
{
  echo "model_list:"
  for h in "${ALL_HOSTS[@]}"; do
      for ((g = 0; g < GPUS_PER_NODE; g++)); do
          alias=${ALIAS[${GPU_MODEL[$((g % ${#GPU_MODEL[@]}))]}]}
          port=$((BASE_PORT + g))
          echo "  - model_name: $alias"
          echo "    litellm_params:"
          echo "      model: openai/$alias"
          echo "      api_base: http://$h:$port/v1"
          echo "      api_key: dummy"
          echo "      rpm: 100000"
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
echo "wrote $CFG"

# ---- gateway -----------------------------------------------------------------
GW_HOST=${ALL_HOSTS[0]}
echo "starting LiteLLM gateway on $GW_HOST:$GATEWAY_PORT"
gwid=$(flux submit -N1 -n1 -c 4 --requires="host:$GW_HOST" \
        --job-name="litellm-$GW_HOST" --output="$RUNDIR/litellm.log" \
        "$LLM_SCRIPTS/gateway-node.sh" "$CFG" "$GATEWAY_PORT")
echo "$gwid $GW_HOST gateway" >> "$RUNDIR/jobs.txt"

deadline=$((SECONDS + 600))
until curl -sf -m 5 -H "Authorization: Bearer sk-tuolumne" \
      "http://$GW_HOST:$GATEWAY_PORT/v1/models" >/dev/null 2>&1; do
    (( SECONDS < deadline )) || { echo "TIMEOUT waiting for gateway; see $RUNDIR/litellm.log"; exit 1; }
    sleep 5
done

# ---- cluster.json ------------------------------------------------------------
#
# `models` is a list here, where the single-model script writes one `alias`.
# The client reads this file rather than being told what is deployed, so a
# mixture that is not recorded is a mixture the benchmark cannot use.
{
  printf '{\n'
  printf '  "run_dir": "%s",\n' "$RUNDIR"
  printf '  "profile": "%s",\n' "$PROFILE"
  printf '  "models": [%s],\n' \
    "$(for key in "${GPU_MODEL[@]}"; do printf '"%s",' "${ALIAS[$key]}"; done | sed 's/,$//')"
  printf '  "alias": "%s",\n' "${ALIAS[${GPU_MODEL[0]}]}"
  printf '  "gateway": {"host": "%s", "port": %s, "job": "%s", "key": "sk-tuolumne"},\n' \
    "$GW_HOST" "$GATEWAY_PORT" "$gwid"
  printf '  "servers": [\n'
  cat "$RUNDIR"/nodes/*.json | paste -sd, - | sed 's/,/,\n    /g; s/^/    /'
  printf '\n  ]\n}\n'
} > "$RUNDIR/cluster.json"
cp "$RUNDIR/cluster.json" "$LLM_SCRIPTS/cluster.json"
echo "wrote $RUNDIR/cluster.json and $LLM_SCRIPTS/cluster.json"

echo
echo "================================================================="
echo "Gateway ready:  http://$GW_HOST:$GATEWAY_PORT   (master key: sk-tuolumne)"
echo "Models:         $(for key in "${GPU_MODEL[@]}"; do printf '%s ' "${ALIAS[$key]}"; done)"
echo "Profile:        $PROFILE"
echo "Run dir:        $RUNDIR"
echo "Stop with:      flux proxy <alloc> tuolumne-llm/stop.sh"
echo "================================================================="
