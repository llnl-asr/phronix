#!/bin/bash
# Run the LiteLLM gateway on a compute node.  Args: <litellm.yaml> <port>
set -uo pipefail
source "${LLM_SCRIPTS:-/usr/WS2/haridev/phronix/tuolumne-llm}/env.sh"
CFG=$1
PORT=$2
echo "[$(hostname)] LiteLLM gateway on port $PORT, config $CFG"
exec "$LLM_ROOT/venv/bin/litellm" --config "$CFG" --host 0.0.0.0 --port "$PORT"
