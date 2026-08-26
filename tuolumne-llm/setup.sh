#!/bin/bash
# One-time setup on lustre5: venv, llama.cpp clone, model downloads.
set -euo pipefail
# Resolve env.sh NEXT TO THIS SCRIPT, not from a hardcoded path: corona-llm/
# symlinks these scripts and carries its own env.sh, and a hardcoded default
# would have every corona invocation silently load Tuolumne's paths and arch.
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"

mkdir -p "$LLM_ROOT"/{src,models,logs}

# --- venv (pypi.org directly; the site pip.conf points at an unreachable mirror)
if [[ ! -x $LLM_ROOT/venv/bin/python ]]; then
    python3 -m venv "$LLM_ROOT/venv"
fi
PIP_CONFIG_FILE=/dev/null "$LLM_ROOT/venv/bin/pip" install -q -U -i https://pypi.org/simple \
    pip "huggingface_hub[cli]" hf_transfer "litellm[proxy]" "fastapi==0.115.12"

# --- llama.cpp fork (turboquant KV cache + MTP speculation)
if [[ ! -d $LLAMA_SRC/.git ]]; then
    git clone --depth 1 -b feature/turboquant-kv-cache \
        https://github.com/TheTom/llama-cpp-turboquant.git "$LLAMA_SRC"
fi

# --- models (Q8_0 everywhere, per notes)
export HF_HOME=$LLM_ROOT/hf-cache
HF=$LLM_ROOT/venv/bin/hf
dl(){ $HF download "$1" "$2" --local-dir "$LLM_ROOT/models/$3"; }
dl ggml-org/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q8_0.gguf     nemotron
dl ggml-org/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF mtp-NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q8_0.gguf nemotron
dl unsloth/Muse-Glimmer-30B-GGUF     Muse-Glimmer-30B-Q8_0.gguf        muse-glimmer
dl unsloth/Muse-Glimmer-30B-GGUF     mmproj-Muse-Glimmer-30B-Q8_0.gguf muse-glimmer
dl ornith-ai/Ornith-1.5-35B-A3B-GGUF Ornith-1.5-35B-Q8_0.gguf          ornith
echo SETUP_DONE
