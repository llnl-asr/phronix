#!/bin/bash
# Run the SWE-bench comparison against the local LLM cluster.
#
#   swe-agent-bench.sh                              # 6 tasks, both arms
#   swe-agent-bench.sh --tasks lite-300.txt         # the full Lite split
#   swe-agent-bench.sh --tasks-per-node 8 --nodes tuolumne1746,tuolumne1183
#   swe-agent-bench.sh --phronix-only --watch       # iterate on the pipeline
#   swe-agent-bench.sh --candidates 3               # try the top 3 plans in
#                                                   # parallel, keep the best
#   swe-agent-bench.sh --dry-run                    # show what would run
#   swe-agent-bench.sh --list-models                # what this backend serves
#
# NOTE: without --dry-run this STOPS any run in progress before starting its
# own. Use --dry-run to inspect the configuration.
#
# Harness x backend — the harness is the agent, the backend is where the model
# lives, and they vary independently:
#
#   --harness opencode --backend cluster     local GPU fleet (default)
#   --harness opencode --backend livai       site gateway, OPENAI_API_KEY
#   --harness claude   --backend anthropic   Claude Code on Sonnet 5
#   --harness claude   --backend cluster     Claude Code on the local fleet
#   --harness claude   --backend livai       Claude Code via the site gateway
#
# Numbers from different harnesses are NOT comparable — different system
# prompts, different event streams. Bare-versus-phronix WITHIN one harness and
# one backend is the comparison this benchmark is for.
#
# This exists because the invocation has three parts that are easy to get wrong
# and silent when they are:
#
#   * It must run ON a compute node. The agents talk to the cluster gateway,
#     which refuses connections from the login node and answers in 7 ms from a
#     compute node. Launched from the login node the run comes up, produces no
#     patches, and reports "agent produced no patch" for every task.
#
#   * It must go over ssh, not `flux run`. A flux sub-job's cgroup starves
#     opencode: it exits 245 with no output there and works over ssh, which is
#     the same path podman already uses for containers.
#
#   * Containers must be pruned first. Every container holds kernel session
#     keys against a per-user quota of 200; a killed run leaves its containers
#     behind, and the next run dies on every task with "unable to join session
#     keyring: disk quota exceeded", which names neither containers nor keys.
#
# The endpoint, model, credential and provider all come from the cluster's own
# cluster.json, so there is nothing to keep in sync by hand.
set -uo pipefail

PROJECT=/usr/WS2/haridev/phronix
BENCH=/p/lustre5/haridev/phronix-bench
CLUSTER=${CLUSTER:-/usr/workspace/haridev/phronix/${PHRONIX_FLEET:-tuolumne-llm}/cluster.json}

HARNESS=opencode
#: Where the model comes from.
#:
#:   cluster    the local GPU fleet, via its own cluster.json
#:   livai      the site gateway (needs OPENAI_API_KEY)
#:   anthropic  Anthropic directly, for Claude Code
#:
#: This decides more than a URL: a `cluster` run must execute ON a compute node,
#: because the gateway refuses connections from the login node. The other two
#: are reachable from anywhere, so they run where they always did.
BACKEND=${BACKEND:-cluster}
MODEL_OVERRIDE=""
TASKS=$BENCH/fast-6.txt
NODE=""
NODES=""
TASKS_PER_NODE=6
PHRONIX_ONLY=""
SERIAL_ARMS=""
WATCH=""
LIST_MODELS=""
DRY_RUN=""
KEEP_RUNNING=""
#: Attempt first, research only on failure. The default, because it is the
#: process: try the task, and if that works there is nothing to research; if it
#: fails, the failure is the most useful input research can have. --research-
#: first restores the old order for a comparison that wants it.
RESEARCH_FIRST=""
#: How many of the research pass's ideas get attempted against the real tests.
#:
#: Three, matching the three the plan is asked for. Each is a separate attempt
#: in its own container, evaluated by the benchmark's own tests, run in
#: parallel — so three candidates cost one attempt's wall clock on a fleet with
#: capacity, and the target tests settle which idea was right rather than a
#: proxy metric measured on a corpus research built itself.
CANDIDATES=${CANDIDATES:-3}
FILL_FLEET=""
EXTRA=()

usage() { sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

while [ $# -gt 0 ]; do
  case "$1" in
    --tasks)          TASKS="$2"; shift 2;;
    --tasks-per-node) TASKS_PER_NODE="$2"; shift 2;;
    --node)           NODE="$2"; shift 2;;
    --nodes)          NODES="$2"; shift 2;;
    --harness)        HARNESS="$2"; shift 2;;
    --backend)        BACKEND="$2"; shift 2;;
    --model)          MODEL_OVERRIDE="$2"; shift 2;;
    --cluster)        CLUSTER="$2"; shift 2;;
    --phronix-only)   PHRONIX_ONLY=1; shift;;
    --serial-arms)    SERIAL_ARMS=1; shift;;
    --research-first) RESEARCH_FIRST=1; shift;;
    --tries)          EXTRA+=(--tries "$2"); shift 2;;
    --candidates)     CANDIDATES="$2"; shift 2;;
    --reuse)          EXTRA+=(--reuse); shift;;
    --watch)          WATCH=1; shift;;
    --list-models)    LIST_MODELS=1; shift;;
    --dry-run)        DRY_RUN=1; shift;;
    --keep-running)   KEEP_RUNNING=1; shift;;
    --fill-fleet)     FILL_FLEET=1; shift;;
    -h|--help)        usage;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2;;
  esac
done

[ -f "$TASKS" ] || TASKS="$BENCH/$TASKS"
[ -f "$TASKS" ] || { echo "no such task file: $TASKS" >&2; exit 2; }

case "$HARNESS" in opencode|claude) ;; *)
  echo "--harness must be opencode or claude, not '$HARNESS'" >&2; exit 2;; esac

# Resolve the backend into the flags the runner takes, and decide where the
# runner itself has to live.
BACKEND_ARGS=()
case "$BACKEND" in
  cluster)
    [ -f "$CLUSTER" ] || { echo "no cluster config: $CLUSTER (is the fleet up?)" >&2; exit 2; }
    BACKEND_ARGS=(--cluster "$CLUSTER")
    # The endpoint, model, key and provider all come from the fleet's own
    # record, so there is nothing to keep in sync by hand.
    NEEDS_COMPUTE_NODE=1
    ;;
  livai)
    # Not a hard failure while only listing: "what can I run" is a reasonable
    # question to ask before finding the credential, and `${VAR:?}` answers it
    # with a raw bash error naming a line number.
    if [ -z "${OPENAI_API_KEY:-}" ]; then
      if [ -n "$LIST_MODELS" ]; then
        echo "note: OPENAI_API_KEY is unset, so livai cannot be queried" >&2
      else
        echo "livai needs OPENAI_API_KEY" >&2
        exit 2
      fi
    fi
    if [ "$HARNESS" = claude ]; then
      # Claude Code speaks the Anthropic wire format; the arm points
      # ANTHROPIC_BASE_URL at whatever --base-url names, so this only works if
      # the gateway serves /v1/messages.
      echo "note: claude+livai requires the gateway to speak the Anthropic API" >&2
    fi
    BACKEND_ARGS=(--base-url https://livai-api.llnl.gov/v1 --provider livai
                  --model "${MODEL_OVERRIDE:-claude-sonnet-4.5}")
    NEEDS_COMPUTE_NODE=0
    ;;
  anthropic)
    [ "$HARNESS" = claude ] || {
      echo "--backend anthropic is for --harness claude (opencode has no Anthropic path)" >&2
      exit 2; }
    BACKEND_ARGS=(--provider anthropic --model "${MODEL_OVERRIDE:-claude-sonnet-5}")
    NEEDS_COMPUTE_NODE=0
    ;;
  *) echo "--backend must be cluster, livai or anthropic, not '$BACKEND'" >&2; exit 2;;
esac
[ -n "$MODEL_OVERRIDE" ] && [ "$BACKEND" = cluster ] &&   BACKEND_ARGS+=(--model "$MODEL_OVERRIDE")

# What this backend can actually serve.
#
# Worth asking rather than assuming: a model name the endpoint does not serve
# fails at the first API call of the first task, and looks like a broken agent
# rather than a typo. `--list-models` prints the list and stops; otherwise the
# chosen model is checked against it and a mismatch is a loud warning.
list_models() {
  case "$BACKEND" in
    cluster)
      python3 - "$CLUSTER" <<'PY'
import json, sys, urllib.request
cfg = json.load(open(sys.argv[1]))
g = cfg.get("gateway") or {}
url = f"http://{g.get('host')}:{g.get('port')}/v1/models"
req = urllib.request.Request(url)
if g.get("key"):
    req.add_header("Authorization", f"Bearer {g['key']}")
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        for m in json.load(r).get("data", []):
            print(m.get("id"))
except Exception:
    # The gateway may be unreachable from here (it refuses the login node);
    # the fleet's own record is the fallback and is usually enough.
    seen = set()
    for name in cfg.get("models") or [cfg.get("alias") or cfg.get("model")]:
        if name and name not in seen:
            seen.add(name)
            print(name)
PY
      ;;
    livai)
      python3 - <<'PY'
import json, os, sys, urllib.request
key = os.environ.get("OPENAI_API_KEY", "")
req = urllib.request.Request("https://livai-api.llnl.gov/v1/models",
                             headers={"Authorization": f"Bearer {key}"})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        for m in sorted(x.get("id", "") for x in json.load(r).get("data", [])):
            print(m)
except Exception as exc:
    print(f"(could not reach livai: {str(exc).splitlines()[0]})",
          file=sys.stderr)
PY
      ;;
    anthropic)
      python3 - <<'PY'
import json, os, sys, urllib.request
# Claude Code authenticates however it is configured; this listing only needs a
# key if one is set. Without it, fall back to naming what the harness supports.
key = (os.environ.get("ANTHROPIC_API_KEY")
       or os.environ.get("ANTHROPIC_AUTH_TOKEN") or "")
if key:
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            for m in json.load(r).get("data", []):
                print(m.get("id"))
        raise SystemExit
    except SystemExit:
        raise
    except Exception as exc:
        print(f"(could not reach Anthropic: {str(exc).splitlines()[0]})",
              file=sys.stderr)
print("claude-opus-5")
print("claude-sonnet-5")
print("claude-haiku-4-5-20251001")
PY
      ;;
  esac
}

if [ -n "$LIST_MODELS" ]; then
  echo "models available on backend '$BACKEND':"
  list_models | sed 's/^/  /'
  exit 0
fi

# Where the runner itself lives. Defaults to the first node of the list, or to
# whichever single-node allocation is running — the agents must be able to reach
# the gateway, and only a compute node can.
if [ -z "$NODE" ]; then
  if [ -n "$NODES" ]; then
    NODE=${NODES%%,*}
  else
    NODE=$(flux jobs -a --no-header 2>/dev/null |
           awk '$5=="R" && $6==1 {print $NF; exit}')
    case "$NODE" in *\[*) NODE=$(flux hostlist -e "$NODE" 2>/dev/null | awk '{print $1}');; esac
  fi
fi
[ -n "$NODE" ] || { echo "no node to run on; pass --node or --nodes" >&2; exit 2; }
NODES=${NODES:-$NODE}

# What is actually serving, so the banner describes this run rather than a
# default nobody chose.
if [ "$BACKEND" = cluster ]; then
  read -r MODEL GATEWAY < <(python3 - "$CLUSTER" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
g = d.get("gateway") or {}
# Deduplicated: a fleet serving one model on four GPUs records it four
# times, and "gpt-oss-120b,gpt-oss-120b,gpt-oss-120b,gpt-oss-120b" is not a
# model name anything can be checked against.
listed = d.get("models") or [d.get("alias") or d.get("model") or "?"]
seen, models = set(), []
for name in listed:
    if name and name not in seen:
        seen.add(name)
        models.append(name)
print(",".join(models), f"http://{g.get('host')}:{g.get('port')}/v1")
PY
)
else
  MODEL=${MODEL_OVERRIDE:-$([ "$BACKEND" = anthropic ] && echo claude-sonnet-5 || echo claude-sonnet-4.5)}
  GATEWAY=$([ "$BACKEND" = anthropic ] && echo "api.anthropic.com" || echo "https://livai-api.llnl.gov/v1")
fi

# An explicit choice overrides whatever the fleet lists first.
[ -n "$MODEL_OVERRIDE" ] && MODEL=$MODEL_OVERRIDE

# Check each model this run may ask for. A name the endpoint does not serve
# fails at the first API call of the first task and reads as a broken agent.
AVAILABLE=$(list_models 2>/dev/null)
if [ -n "$AVAILABLE" ]; then
  for want in ${MODEL//,/ }; do
    printf '%s\n' "$AVAILABLE" | grep -qxF "$want" && continue
    echo "WARNING: '$want' is not in the models this backend reports:" >&2
    printf '%s\n' "$AVAILABLE" | sed 's/^/    /' >&2
    echo "  (continuing; --list-models shows them, --model chooses one)" >&2
  done
fi

# How much of the fleet this run will actually use.
#
# Measured, not assumed: a task unit (one task in one arm) occupies about half a
# slot, because it spends much of its life checking out repos, running tests and
# evaluating patches rather than talking to the model. Sampled against a live
# 12-unit run: 2, 9, 8, 7, 6 requests in flight.
#
# So the tasks needed to fill a fleet is capacity / (0.53 x arms) — roughly 120
# concurrent tasks for a 128-slot fleet with two arms. A six-task run uses about
# 5% of it, which is the correct outcome for six tasks and not a fault: spare
# capacity is only waste when work is waiting on it.
ARMS_COUNT=$([ -n "$PHRONIX_ONLY" ] && echo 1 || echo 2)
NODE_COUNT=$(printf '%s' "$NODES" | tr ',' '\n' | grep -c .)

read -r CAPACITY WANT_TASKS < <(python3 - "$CLUSTER" "$ARMS_COUNT" <<'PY' 2>/dev/null || echo "0 0"
import sys
sys.path.insert(0, "/usr/WS2/haridev/phronix/tests")
from benchmark.cluster import ClusterConfig
try:
    spec = ClusterConfig.load(sys.argv[1])
    print(spec.capacity(), spec.tasks_to_fill(int(sys.argv[2])))
except Exception:
    print(0, 0)
PY
)

#: Tasks one node can hold at once, whatever the fleet could serve.
#:
#: Each task is a container, and a container costs cores for its test runs plus
#: about two kernel session keys against a per-user quota of 200. This is the
#: limit that binds long before the GPUs do.
MAX_TASKS_PER_NODE=${MAX_TASKS_PER_NODE:-16}

if [ -n "$FILL_FLEET" ] && [ "${CAPACITY:-0}" -gt 0 ]; then
  per_node=$(( (WANT_TASKS + NODE_COUNT - 1) / NODE_COUNT ))
  [ "$per_node" -gt "$MAX_TASKS_PER_NODE" ] && per_node=$MAX_TASKS_PER_NODE
  [ "$per_node" -lt 1 ] && per_node=1
  TASKS_PER_NODE=$per_node
fi

ARMS_NOTE="both arms"
[ -n "$PHRONIX_ONLY" ] && ARMS_NOTE="phronix only"

cat <<BANNER
harness  : $HARNESS ($ARMS_NOTE)
model    : $MODEL
gateway  : $GATEWAY
tasks    : $TASKS ($(grep -cvE '^\s*(#|$)' "$TASKS") task(s))
runner   : $([ "${NEEDS_COMPUTE_NODE:-1}" = 1 ] \
             && echo "$NODE (over ssh; the login node cannot reach the cluster gateway)" \
             || echo "$(hostname) (containers on $NODE)")
placement: $TASKS_PER_NODE task(s) per node on $NODES
fleet    : $(python3 - <<PY
cap, want = ${CAPACITY:-0}, ${WANT_TASKS:-0}
here = $TASKS_PER_NODE * $NODE_COUNT * $ARMS_COUNT
if not cap:
    print("capacity unknown")
else:
    use = min(100.0, 100.0 * here * 0.53 / cap)
    note = "" if use >= 60 else f"  (--fill-fleet would raise this; {want} concurrent tasks fills it)"
    print(f"{cap} slots, this run will use ~{use:.0f}%{note}")
PY
)
BANNER

# The runner script that lands on the compute node. Written out rather than
# quoted inline: every previous attempt to inline this lost a `cd` or a quote
# and failed somewhere unhelpful.
# Per-invocation, not shared: two concurrent runs writing one launcher and one
# log meant the second truncated the first's output and they raced on the file.
STAMP=$(date +%m%d-%H%M%S)-$$
#: A real opencode binary rather than the npx wrapper.
#:
#: The wrapper resolves and extracts the package on every invocation into a
#: cache every private HOME symlinks, so concurrent agents race on it and one
#: execs a half-written binary — rc 126, zero steps, recorded as "agent produced
#: no patch". Every attempt of a six-task run failed that way.
INSTALLED_OPENCODE=${INSTALLED_OPENCODE:-/p/lustre5/haridev/opencode-install/node_modules/.bin/opencode}
[ -x "$INSTALLED_OPENCODE" ] || INSTALLED_OPENCODE=""

# Computed here rather than expanded inside the heredoc, where a multi-line
# default silently produced an empty flag and the run went back to
# researching before it had tried anything.
RETRY_FLAG="--research-on-retry"
[ -n "$RESEARCH_FIRST" ] && RETRY_FLAG=""

# Through EXTRA, which `run-benchmark.sh` forwards verbatim to the CLI.
#
# As its own line it was parsed by `run-benchmark.sh`, which does not know the
# flag and refuses: "unknown option: --attempt-candidates".
[ "${CANDIDATES:-1}" -gt 1 ] && EXTRA+=(--attempt-candidates "$CANDIDATES")

LAUNCHER=/p/lustre5/haridev/.swe-agent-bench-$HARNESS-$STAMP.sh
cat > "$LAUNCHER" <<EOF
#!/bin/bash
cd $PROJECT || exit 2
${INSTALLED_OPENCODE:+export PHRONIX_OPENCODE_BIN=$INSTALLED_OPENCODE}
exec bash scripts/run-benchmark.sh \\
  --harness $HARNESS \\
  ${BACKEND_ARGS[*]} \\
  --tasks $TASKS \\
  --tasks-per-node $TASKS_PER_NODE \\
  --nodes $NODES \\
  ${PHRONIX_ONLY:+--phronix-only} \\
  ${SERIAL_ARMS:+--serial-arms} \\
  $RETRY_FLAG \\
  ${KEEP_RUNNING:+--no-kill} \\
  ${EXTRA[@]:-}
EOF
chmod +x "$LAUNCHER"

if [ -n "$DRY_RUN" ]; then
  echo
  echo "would run:"
  sed 's/^/  /' "$LAUNCHER"
  echo "(--dry-run: nothing started, nothing stopped)"
  exit 0
fi

# Stop whatever is running and remove its containers, on every node that will
# hold tasks. `kill.sh` prunes; without it the keyring quota kills the next run.
#
# This is why --dry-run exists: checking the banner by running the script
# stopped a benchmark that was mid-flight, because everything below happens
# before the first line of output anyone reads.
echo
if [ -n "$KEEP_RUNNING" ]; then
  # Two benchmarks can share a node: a task is one container and a couple of
  # kernel session keys, and the quota is 200. What they must NOT share is the
  # teardown — `kill.sh` matches on the benchmark run path and would stop the
  # other run's agents along with nothing of its own.
  #
  # The cost is that stale containers from an earlier run are not pruned, so
  # watch the key usage if you stack several of these.
  echo "leaving any running benchmark alone (--keep-running)"
else
  echo "clearing previous run..."
  for h in ${NODES//,/ }; do
    ssh -n -o BatchMode=yes "$h" "BENCH_NODES='${NODES//,/ }' bash $PROJECT/scripts/kill.sh" \
      2>/dev/null | sed 's/^/  /' | tail -2
  done
  sleep 3
fi

# Re-render the harness config before the run.
#
# The agents a run uses are generated from the YAML templates under
# .phronix/agents/, and a run that starts on a stale render measures whatever
# was there last time. Cheap and idempotent — it compares content and writes
# only what differs — so it is worth doing every time rather than remembering
# to. Each task checkout then symlinks the result, so a change here reaches
# every task without copying anything.
echo "refreshing harness config..."
PY=/p/lustre5/haridev/phronix-bench/venv/bin/python

# Pin the harness to THIS run's provider and model, then re-render.
#
# A rendered agent carries its model, so an agent naming a different endpoint
# than the run does is a run measuring something nobody chose — the opencode
# agents shipped `model: ollama/qwen3-coder:480b-cloud` while the run asked for
# `tuolumne/gpt-oss-120b`. Pinning goes to `active-models.json`, the local
# choice, so which fleet is up today is not committed for everyone.
"$PY" - "$HARNESS" "$([ "$BACKEND" = anthropic ] && echo anthropic || \
                      python3 -c "
import json,sys
try: print(json.load(open('$CLUSTER')).get('gateway') and 'tuolumne' or 'livai')
except Exception: print('livai')" 2>/dev/null)" "$MODEL" <<'PY' 2>/dev/null | sed 's/^/  /'
import sys
from phronix.harness_models import pin_harness
harness, provider, model = sys.argv[1], sys.argv[2], sys.argv[3].split(",")[0]
got = pin_harness(harness, provider, model)
print(f"pinned {got['harness']} -> {got['provider']}/{got['model']}")
PY

"$PY" -m phronix.cli sync agents 2>/dev/null | sed 's/^/  /' | tail -1 \
  || echo "  (sync skipped: phronix not importable from here)"

LOG=/p/lustre5/haridev/bench-$HARNESS-$STAMP.log
if [ "${NEEDS_COMPUTE_NODE:-1}" = 1 ]; then
  # The local cluster's gateway refuses connections from the login node, and the
  # agents are what talk to it — so the runner has to be where they can reach.
  ssh -n -o BatchMode=yes "$NODE" \
    "setsid nohup $LAUNCHER > $LOG 2>&1 < /dev/null & sleep 5; echo 'started on $NODE'" \
    2>/dev/null | tail -1
else
  # livai and Anthropic are reachable from anywhere, so the runner stays here
  # and only the containers go to the node over ssh, as they always did.
  setsid nohup "$LAUNCHER" > "$LOG" 2>&1 < /dev/null &
  sleep 5
  echo "started here (containers on $NODE)"
fi

# The run directory is what everything else is keyed on, so wait for it rather
# than guessing.
for _ in $(seq 1 30); do
  RUN=$(grep -oE "$BENCH/runs/[a-z]+-[0-9-]+" "$LOG" 2>/dev/null | head -1)
  [ -n "$RUN" ] && break
  sleep 3
done

echo
if [ -n "${RUN:-}" ]; then
  echo "run      : $RUN"
  echo "watch    : $PROJECT/scripts/status.sh"
  echo "pipeline : $PROJECT/scripts/research-progress.sh"
  echo "stop     : ssh $NODE bash $PROJECT/scripts/kill.sh"
else
  echo "the runner did not report a run directory; see $LOG" >&2
  tail -5 "$LOG" >&2
  exit 1
fi

if [ -n "$WATCH" ]; then
  echo
  sleep 60
  exec bash "$PROJECT/scripts/status.sh" "$RUN"
fi
