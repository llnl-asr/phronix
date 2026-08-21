#!/bin/bash
# Send one chat completion per served model through the LiteLLM gateway.
#   tuolumne-llm/smoke-test.sh <gateway-host> [port]
set -euo pipefail
HOST=${1:?usage: smoke-test.sh <gateway-host> [port]}
PORT=${2:-4000}
KEY=${GATEWAY_KEY:-sk-tuolumne}

echo "== models on http://$HOST:$PORT"
curl -sf -H "Authorization: Bearer $KEY" "http://$HOST:$PORT/v1/models" | head -c 2000; echo

for m in $(curl -sf -H "Authorization: Bearer $KEY" "http://$HOST:$PORT/v1/models" \
           | python3 -c 'import json,sys;print(" ".join(d["id"] for d in json.load(sys.stdin)["data"]))'); do
    echo "== $m"
    curl -sf "http://$HOST:$PORT/v1/chat/completions" \
        -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
        -d "{\"model\":\"$m\",\"max_tokens\":64,\"messages\":[{\"role\":\"user\",\"content\":\"In one sentence: what is Tuolumne?\"}]}" \
        | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["choices"][0]["message"]["content"])'
done
