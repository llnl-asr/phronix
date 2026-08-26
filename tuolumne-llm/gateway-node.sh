#!/bin/bash
# Run the LiteLLM gateway on a compute node.  Args: <litellm.yaml> <port>
set -uo pipefail
# Resolve env.sh NEXT TO THIS SCRIPT, not from a hardcoded path: corona-llm/
# symlinks these scripts and carries its own env.sh, and a hardcoded default
# would have every corona invocation silently load Tuolumne's paths and arch.
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"
CFG=$1
PORT=$2
echo "[$(hostname)] LiteLLM gateway on port $PORT, config $CFG"
exec "$LLM_ROOT/venv/bin/litellm" --config "$CFG" --host 0.0.0.0 --port "$PORT"
