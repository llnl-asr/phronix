#!/bin/bash
# One-time setup for the corona fleet: venv, llama.cpp clone, model downloads.
#
# Separate from tuolumne-llm/setup.sh, not a symlink, because the two clusters
# share no filesystem — /p/lustre5 is not mounted on corona — and because the
# model list is different: on a 32 GB card only the models below fit.
#
# Run on a LOGIN node (this downloads; it does not need GPUs).
set -euo pipefail
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"

mkdir -p "$LLM_ROOT"/{src,models,logs}

# --- venv (pypi.org directly; the site pip.conf points at an unreachable mirror)
if [[ ! -x $LLM_ROOT/venv/bin/python ]]; then
    python3 -m venv "$LLM_ROOT/venv"
fi
# litellm >= 1.98: 1.79 numbered Anthropic content blocks wrong on the
# text-to-tool_use transition — it emitted a `content_block_delta` for an
# index it never opened and Claude Code dropped the turn with "API Error:
# Content block not found". See the README section on streaming.
PIP_CONFIG_FILE=/dev/null "$LLM_ROOT/venv/bin/pip" install -q -U -i https://pypi.org/simple \
    pip "huggingface_hub[cli]" hf_transfer "litellm[proxy]>=1.98" "fastapi==0.115.12"

# --- llama.cpp fork (turboquant KV cache + MTP speculation)
if [[ ! -d $LLAMA_SRC/.git ]]; then
    git clone --depth 1 -b feature/turboquant-kv-cache \
        https://github.com/TheTom/llama-cpp-turboquant.git "$LLAMA_SRC"
fi

# --- models
#
# MXFP4 only. The Q8_0 30B models Tuolumne serves are ~32 GB, which is the
# whole card here with nothing left for KV, so they are not downloaded rather
# than downloaded and unusable.
export HF_HOME=$LLM_ROOT/hf-cache
export HF_HUB_ENABLE_HF_TRANSFER=1
HF=$LLM_ROOT/venv/bin/hf
dl(){ $HF download "$1" "$2" --local-dir "$LLM_ROOT/models/$3"; }
dl ggml-org/gpt-oss-20b-GGUF  gpt-oss-20b-MXFP4.gguf  gpt-oss-20b
dl ggml-org/gpt-oss-120b-GGUF gpt-oss-120b-MXFP4.gguf gpt-oss-120b

echo "SETUP_DONE — next: flux alloc -N1 --queue=pdebug, then corona-llm/build.sh"
