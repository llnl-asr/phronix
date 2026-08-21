#!/bin/bash
# Launch a multi-node llama.cpp fleet + LiteLLM gateway INSIDE an existing Flux allocation.
#
#   flux proxy <alloc-jobid> tuolumne-llm/run-cluster.sh
#
# One llama-server per MI300A GPU (4/node); node jobs take 88 of 96 cores so the
# gateway job still fits on a serving node (22 cores per GPU job of 96).
# whole allocation, then a LiteLLM proxy on the head node load-balancing across
# every replica of each model.
set -euo pipefail
source "${LLM_SCRIPTS:-/usr/WS2/haridev/phronix/tuolumne-llm}/env.sh"

GATEWAY_PORT=${GATEWAY_PORT:-4000}
BASE_PORT=${BASE_PORT:-8050}
GPUS_PER_NODE=${GPUS_PER_NODE:-4}
export PROFILE=${PROFILE:-throughput}
# One model, replicated on every GPU of every node; LiteLLM load-balances across
# the replicas. Pick it with MODEL=nemotron|muse|ornith.
MODEL_KEY=${MODEL:-nemotron}
declare -A ALIAS=([nemotron]=nemotron-3.5 [muse]=muse-glimmer [ornith]=ornith-1.5)
[[ -n ${ALIAS[$MODEL_KEY]:-} ]] || { echo "MODEL must be one of: ${!ALIAS[*]}"; exit 1; }
MODEL_ALIAS=${ALIAS[$MODEL_KEY]}

RUNDIR=$LLM_ROOT/logs/run-$(date +%Y%m%d-%H%M%S)
mkdir -p "$RUNDIR"
ln -sfn "$RUNDIR" "$LLM_ROOT/logs/latest"

read -r -a ALL_HOSTS <<< "$(flux hostlist -e "$(flux getattr hostlist)")"
# NNODES / GPUS_PER_NODE let you bring the fleet up in stages:
#   NNODES=1 GPUS_PER_NODE=1 ... then 1x4, then 2x4, then all nodes.
HOSTS=("${ALL_HOSTS[@]:0:${NNODES:-${#ALL_HOSTS[@]}}}")
echo "Using ${#HOSTS[@]}/${#ALL_HOSTS[@]} node(s), $GPUS_PER_NODE GPU(s) each: ${HOSTS[*]}"

# ---- launch one job per GPU (Flux binds the GPU; see gpu-server.sh) ----------
for h in "${HOSTS[@]}"; do
    for ((g = 0; g < GPUS_PER_NODE; g++)); do
        port=$((BASE_PORT + g))
        jid=$(flux submit -N1 -n1 -c 22 -g 1 --requires="host:$h" \
                --job-name="llama-$h-gpu$g" --output="$RUNDIR/$h-gpu$g.flux.log" \
                --env=RUNDIR="$RUNDIR" --env=PROFILE="$PROFILE" \
                "$LLM_SCRIPTS/gpu-server.sh" "$MODEL_KEY" "$g" "$port")
        echo "$jid $h gpu$g $MODEL_KEY" >> "$RUNDIR/jobs.txt"
        echo "submitted $jid on $h gpu$g port $port"
    done
done

# ---- build the LiteLLM config ------------------------------------------------
CFG=$RUNDIR/litellm.yaml
{
  echo "model_list:"
  for h in "${HOSTS[@]}"; do
      for ((g = 0; g < GPUS_PER_NODE; g++)); do
          port=$((BASE_PORT + g))
          echo "  - model_name: $MODEL_ALIAS"
          echo "    litellm_params:"
          echo "      model: openai/$MODEL_ALIAS"
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

# ---- wait for every backend to report healthy --------------------------------
echo "waiting for backends (up to 30 min)..."
deadline=$((SECONDS + 1800))
for h in "${HOSTS[@]}"; do
    for ((g = 0; g < GPUS_PER_NODE; g++)); do
        port=$((BASE_PORT + g))
        until curl -sf "http://$h:$port/health" > /dev/null; do
            (( SECONDS < deadline )) || { echo "TIMEOUT waiting for $h:$port"; exit 1; }
            sleep 10
        done
        echo "  up: $h:$port"
    done
done

# ---- gateway (on a compute node, not the login node) -------------------------
# Prefer a node in the allocation that is not serving a model; otherwise the first
# serving node (LiteLLM is light next to a llama-server).
if (( ${#ALL_HOSTS[@]} > ${#HOSTS[@]} )); then
    GW_HOST=${GATEWAY_HOST:-${ALL_HOSTS[${#HOSTS[@]}]}}
else
    GW_HOST=${GATEWAY_HOST:-${HOSTS[0]}}
fi
echo "starting LiteLLM gateway on $GW_HOST:$GATEWAY_PORT"
gwid=$(flux submit -N1 -n1 -c 8 --requires="host:$GW_HOST" \
        --job-name="litellm-$GW_HOST" --output="$RUNDIR/litellm.log" \
        "$LLM_SCRIPTS/gateway-node.sh" "$CFG" "$GATEWAY_PORT")
echo "$gwid $GW_HOST gateway" >> "$RUNDIR/jobs.txt"

deadline=$((SECONDS + 300))
until curl -sf "http://$GW_HOST:$GATEWAY_PORT/health/liveliness" > /dev/null; do
    (( SECONDS < deadline )) || { echo "TIMEOUT waiting for gateway; see $RUNDIR/litellm.log"; exit 1; }
    sleep 3
done
HEAD=$GW_HOST

# ---- cluster.json: the record status.sh and stop.sh work from ----------------
{
  printf '{\n  "run_dir": "%s",\n  "model": "%s",\n  "alias": "%s",\n  "profile": "%s",\n' \
      "$RUNDIR" "$MODEL_KEY" "$MODEL_ALIAS" "$PROFILE"
  printf '  "gateway": {"host": "%s", "port": %s, "job": "%s", "key": "sk-tuolumne"},\n' \
      "$GW_HOST" "$GATEWAY_PORT" "$gwid"
  printf '  "servers": [\n'
  cat "$RUNDIR"/nodes/*.json | paste -sd, - | sed 's/,/,\n    /g; s/^/    /'
  printf '\n  ]\n}\n'
} > "$RUNDIR/cluster.json"
ln -sfn "$RUNDIR/cluster.json" "$LLM_ROOT/logs/cluster.json"
# The project reads this one: current fleet, in-repo, next to the scripts.
cp "$RUNDIR/cluster.json" "$LLM_SCRIPTS/cluster.json"
echo "wrote $RUNDIR/cluster.json and $LLM_SCRIPTS/cluster.json"
cat <<EOF

=================================================================
Gateway ready:  http://$HEAD:$GATEWAY_PORT   (master key: sk-tuolumne)
Model:          $MODEL_ALIAS  (on every GPU)
Replicas:       $((${#HOSTS[@]} * GPUS_PER_NODE)) llama-server processes
Run dir:        $RUNDIR
Config:         $LLM_SCRIPTS/cluster.json (copy in $RUNDIR)
Status:         tuolumne-llm/status.sh
Stop with:      flux proxy <alloc> tuolumne-llm/stop.sh
Try:  curl http://$HEAD:$GATEWAY_PORT/v1/chat/completions \\
        -H 'Authorization: Bearer sk-tuolumne' -H 'Content-Type: application/json' \\
        -d '{"model":"$MODEL_ALIAS","messages":[{"role":"user","content":"hi"}]}'
=================================================================
EOF
