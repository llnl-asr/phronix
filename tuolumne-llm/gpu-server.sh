#!/bin/bash
# Run ONE llama-server on the single GPU Flux assigned to this job.
#   gpu-server.sh <model-key> <gpu-index> <port>
#
# Flux binds the GPU (submit with -g1), so this script must NOT set
# ROCR_VISIBLE_DEVICES/HIP_VISIBLE_DEVICES itself: setting both made every server
# past GPU 0 select an empty device set and silently fall back to CPU inference.
#
# The pid is recorded in $LLM_ROOT/logs/pids/<host>-<port>.pid and a JSON record in
# $RUNDIR/nodes/<host>-<port>.json, for status.sh and reap-node.sh.
set -uo pipefail
source "${LLM_SCRIPTS:-/usr/WS2/haridev/phronix/tuolumne-llm}/env.sh"
source "$LLM_SCRIPTS/profiles.sh"

key=$1
gpu=$2
port=$3
HOSTN=$(hostname)
PIDDIR=$LLM_ROOT/logs/pids
RUNDIR=${RUNDIR:-$LLM_ROOT/logs/latest}
mkdir -p "$LLM_ROOT/logs/servers" "$PIDDIR" "$RUNDIR/nodes"
log=$LLM_ROOT/logs/servers/${HOSTN}-gpu${gpu}-${key}.log

read -r -a PROFILE_ARGS <<< "$(profile_args)" || exit 1

# Prefer a copy staged on this node's local SSD.
#
# Weights come off lustre otherwise, and gpt-oss-120b is 63 GB: eight nodes
# starting together ask the PFS for half a terabyte at once and it does not
# share it evenly — 20 of 32 servers healthy at five minutes, three whole nodes
# still short of ready at fourteen. `stage-models.sh` copies each model to
# MODEL_CACHE with dcp beforehand; this picks it up if it is there and falls
# back to the PFS silently if it is not, so staging is an optimisation rather
# than a dependency.
#
# Compared by size, not by mtime: dcp preserves neither, and a half-copied file
# that loads is worse than one that obviously is not there.
MODEL_CACHE=${MODEL_CACHE:-/l/ssd/$(id -un)/models}

prefer_local() {  # $1 = path on the PFS -> echoes the path to actually load
    local remote=$1 leaf local_path
    # A sharded model is staged as its directory.
    if [[ $(basename "$remote") == *-00001-of-* ]]; then
        leaf=$(basename "$(dirname "$remote")")
        local_path=$MODEL_CACHE/$leaf/$(basename "$remote")
    else
        leaf=$(basename "$remote")
        local_path=$MODEL_CACHE/$leaf
    fi
    if [[ -f $local_path ]] &&
       [[ $(stat -c %s "$local_path" 2>/dev/null) == $(stat -c %s "$remote" 2>/dev/null) ]]; then
        echo "$local_path"
    else
        echo "$remote"
    fi
}

for _v in MODEL_NEMOTRON MODEL_MUSE MODEL_ORNITH \
          MODEL_GPTOSS120 MODEL_GPTOSS20 MODEL_NEMOSUPER; do
    [[ -n ${!_v:-} ]] || continue
    _resolved=$(prefer_local "${!_v}")
    if [[ $_resolved != ${!_v} ]]; then
        echo "[$HOSTN] gpu$gpu: loading $_v from local SSD"
    fi
    printf -v "$_v" '%s' "$_resolved"
done

# Reap a leftover server of ours on this port: flux cancel kills the wrapper but
# not always the server, and an orphan makes this launch die with
# "exiting due to HTTP server error".
pf=$PIDDIR/$HOSTN-$port.pid
if [[ -f $pf ]]; then
    old=$(cat "$pf" 2>/dev/null)
    if [[ $old =~ ^[0-9]+$ ]] && kill -0 "$old" 2>/dev/null &&
       [[ -O /proc/$old && $(readlink -f "/proc/$old/exe" 2>/dev/null) == "$LLAMA_SERVER" ]]; then
        echo "[$HOSTN] reaping stale llama-server pid $old (port $port)"
        kill -TERM "$old" 2>/dev/null
        for _ in {1..20}; do kill -0 "$old" 2>/dev/null || break; sleep 1; done
        kill -0 "$old" 2>/dev/null && kill -KILL "$old" 2>/dev/null
    fi
    rm -f "$pf"
fi

# Sampling. Greedy is reproducible and, for this workload, actively harmful.
#
# `--temp 0 --top-k 1` is argmax: one deterministic line of thought, repeated.
# That is right for a benchmark comparing runs of the same prompt, and wrong for
# an agent generating CANDIDATES — the research pipeline asks for several
# aspects to investigate and several approaches to try, and argmax returns the
# same first idea every time. Measured on the greedy fleet: the identical trace
# line emitted six times in one second, and aspects=0/approaches=0 recorded
# across a whole six-task run.
#
# So the default now samples — but at the values the model was EVALUATED with,
# which is a different question from "does it sample at all".
#
# OpenAI's reference for gpt-oss is temperature 1.0, top-p 1.0, top-k DISABLED.
# Both of the settings this file used before were off it in opposite directions,
# and each is a trap of its own:
#
#   * top-k is never zero by default. llama.cpp defaults to 40 and transformers
#     to 50, so a config that simply does not mention top-k is truncating the
#     distribution to the top 40 tokens and reporting a score for a model that
#     was not measured that way. `diverse` did exactly this, and added min-p
#     0.05 on top, truncating twice.
#   * argmax is not the safe conservative choice. `--temp 0 --top-k 1` is a
#     different distribution from the reference, not a sharper version of it,
#     and it breaks candidate generation outright (see above).
#
#   SAMPLING=reference (default)  temp 1.0, top-p 1.0, top-k 0, min-p 0.0
#   SAMPLING=diverse              temp 0.7, top-p 0.95, top-k 40, min-p 0.05
#   SAMPLING=greedy               temp 0, top-p 1, top-k 1
#
# `--seed 1` stays in all three: sampling with a fixed seed is still repeatable
# given the same request, which keeps a rerun diagnosable.
#
# The penalties below are neutral for the same reason and must stay that way. A
# reasoning model revisits its own tokens by design; penalising repetition
# damages the traces the benchmark exists to measure.
case "${SAMPLING:-reference}" in
    greedy)
        SAMPLE_ARGS=(--temp 0 --top-p 1.0 --top-k 1 --min-p 0.0) ;;
    diverse)
        SAMPLE_ARGS=(--temp "${LLAMA_TEMP:-0.7}" --top-p "${LLAMA_TOP_P:-0.95}"
                     --top-k "${LLAMA_TOP_K:-40}" --min-p "${LLAMA_MIN_P:-0.05}") ;;
    reference)
        # top-k 0 is the disable value in llama.cpp and must be explicit.
        SAMPLE_ARGS=(--temp "${LLAMA_TEMP:-1.0}" --top-p "${LLAMA_TOP_P:-1.0}"
                     --top-k "${LLAMA_TOP_K:-0}" --min-p "${LLAMA_MIN_P:-0.0}") ;;
    *) echo "SAMPLING must be reference|diverse|greedy, not '$SAMPLING'" >&2
       exit 1 ;;
esac

args=("${PROFILE_ARGS[@]}" -ngl 999 --flash-attn on --jinja --metrics
      "${SAMPLE_ARGS[@]}" --seed 1
      --repeat-penalty 1.0 --repeat-last-n 0
      -fit off --host 0.0.0.0 --port "$port")
case "$key" in
    nemotron)
        # MTP speculation is opt-in (NEMOTRON_MTP=1): this fork rejects the
        # ggml-org mtp-*.gguf sidecar ("blk.0.attn_norm.weight not found") and the
        # main gguf carries no MTP layers, so it is off by default.
        spec=()
        if [[ ${NEMOTRON_MTP:-0} == 1 ]]; then
            spec=(-md "$MODEL_NEMOTRON_MTP" --spec-type draft-mtp
                  --spec-draft-n-max 3 --spec-draft-p-min 0.5)
        fi
        args=(-m "$MODEL_NEMOTRON" "${spec[@]+"${spec[@]}"}"
              --alias nemotron-3.5 --reasoning off --reasoning-budget 0 "${args[@]}") ;;
    muse)
        args=(-m "$MODEL_MUSE" --mmproj "$MODEL_MUSE_MMPROJ" --alias muse-glimmer "${args[@]}") ;;
    ornith)
        args=(-m "$MODEL_ORNITH" --alias ornith-1.5 "${args[@]}") ;;
    gptoss120|gptoss20)
        # Settings that matter for agent work on gpt-oss.
        #
        # `--reasoning on` with a real budget: this model was post-trained to
        # think before acting, and the failure we are fixing is an agent that
        # calls one tool and drifts. `reasoning_effort` is a harmony-template
        # parameter, so it goes through --chat-template-kwargs rather than a
        # flag of its own.
        #
        # Low effort, and a hard ceiling on thinking.
        #
        # Measured across the fleet: 189,193,540 prompt tokens against 5,228,544
        # generated — 36 prompt tokens per generated one — and prefill (86,570s)
        # costing MORE GPU time than decode (73,445s). An agent loop re-sends
        # its whole conversation every turn, so tokens the model thinks now are
        # tokens it re-reads on every later turn. Reasoning is charged twice.
        #
        # `--reasoning-budget` is the ceiling that matters: effort is a hint the
        # model may ignore, and a budget is arithmetic. Raise both for a run
        # where resolve-rate is the only thing that counts and time is free.
        #
        # MEDIUM, not low, and the budget is why that is affordable.
        #
        # Low effort was chosen from the prefill arithmetic above, which is
        # sound as far as it goes — but it is off the contract this benchmark
        # is measuring. Published SWE-bench work on gpt-oss uses medium or
        # high, and reports the two scoring alike; low is not a setting the
        # model was evaluated under, so a resolve-rate produced at low effort
        # is not a number that can be compared to a published one.
        #
        # The two controls are independent, which is what makes the middle
        # ground real: effort selects the reasoning STYLE the template asks
        # for, and the budget caps how long it may go on. Medium effort under
        # a 2048-token ceiling buys the on-contract behaviour while keeping the
        # bounded latency that the ceiling, not the effort hint, was providing.
        gptoss=(--reasoning on
                --reasoning-budget "${GPTOSS_THINK_BUDGET:-2048}"
                --chat-template-kwargs
                "{\"reasoning_effort\":\"${GPTOSS_EFFORT:-medium}\"}")
        ;;&
    gptoss120)
        # EAGLE3 drafts ship alongside these weights; speculation is opt-in
        # (GPTOSS_SPEC=1) because decode is ~80% of GPU time here and a draft
        # model typically buys 1.5-2.5x on exactly that.
        spec=()
        if [[ ${GPTOSS_SPEC:-0} == 1 && -f ${MODEL_GPTOSS120_DRAFT:-} ]]; then
            spec=(-md "$MODEL_GPTOSS120_DRAFT" --spec-draft-n-max 3)
        fi
        args=(-m "$MODEL_GPTOSS120" "${spec[@]+"${spec[@]}"}"
              "${gptoss[@]}" --alias gpt-oss-120b "${args[@]}") ;;
    gptoss20)
        args=(-m "$MODEL_GPTOSS20" "${gptoss[@]}"
              --alias gpt-oss-20b "${args[@]}") ;;
    nemosuper)
        args=(-m "$MODEL_NEMOSUPER" --alias nemotron-super-49b "${args[@]}") ;;
    *) echo "unknown model key: $key" >&2; exit 1 ;;
esac

echo "[$HOSTN] gpu$gpu -> $key port $port profile=${PROFILE:-throughput} devices=${ROCR_VISIBLE_DEVICES:-<flux>} (log: $log)"
"$LLAMA_SERVER" "${args[@]}" > "$log" 2>&1 &
pid=$!
echo "$pid" > "$pf"
printf '{"host":"%s","gpu":%d,"port":%d,"model":"%s","pid":%d,"profile":"%s","log":"%s","pidfile":"%s"}\n' \
    "$HOSTN" "$gpu" "$port" "$key" "$pid" "${PROFILE:-throughput}" "$log" "$pf" \
    > "$RUNDIR/nodes/$HOSTN-$port.json"

trap 'kill $pid 2>/dev/null; sleep 2; kill -KILL $pid 2>/dev/null; rm -f "$pf"' EXIT TERM INT
wait $pid
