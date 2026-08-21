#!/bin/bash
# Shared environment for the Tuolumne (MI300A / gfx942) llama.cpp deployment.
# Scripts live in the repo; all data (clone, venv, models, logs) lives on lustre5.
export LLM_ROOT=${LLM_ROOT:-/p/lustre5/haridev/llm-tuolumne}
_self=${BASH_SOURCE[0]:-/usr/WS2/haridev/phronix/tuolumne-llm/env.sh}
export LLM_SCRIPTS="$(cd "$(dirname "$_self")" && pwd)"

export ROCM_PATH=/opt/rocm-7.2.1
export HIP_PATH=$ROCM_PATH
export PATH=/usr/tce/packages/cmake/cmake-3.29.2/bin:$ROCM_PATH/bin:$LLM_ROOT/venv/bin:$PATH
export LD_LIBRARY_PATH=$ROCM_PATH/lib:${LD_LIBRARY_PATH:-}
export GPU_TARGET=gfx942

export LLAMA_SRC=$LLM_ROOT/src/llama-cpp-turboquant
export LLAMA_BUILD=$LLAMA_SRC/build-mi300a
export LLAMA_SERVER=$LLAMA_BUILD/bin/llama-server

export MODEL_NEMOTRON=$LLM_ROOT/models/nemotron/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q8_0.gguf
export MODEL_NEMOTRON_MTP=$LLM_ROOT/models/nemotron/mtp-NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q8_0.gguf
export MODEL_MUSE=$LLM_ROOT/models/muse-glimmer/Muse-Glimmer-30B-Q8_0.gguf
export MODEL_MUSE_MMPROJ=$LLM_ROOT/models/muse-glimmer/mmproj-Muse-Glimmer-30B-Q8_0.gguf
export MODEL_ORNITH=$LLM_ROOT/models/ornith/Ornith-1.5-35B-Q8_0.gguf

# The mixture's models. US-origin, and chosen for ACTIVE parameters and tool
# training rather than headline size: the 30B-A3B above activates ~3B per token,
# which is why it calls one tool and then drifts.
#
#   gptoss120  OpenAI, 117B total / ~5B active, post-trained for agentic tool use
#   gptoss20   OpenAI, same training, small and fast
#   nemosuper  NVIDIA, dense 49B — ~16x the active parameters of A3B
export MODEL_GPTOSS120=$LLM_ROOT/models/gpt-oss-120b/gpt-oss-120b-MXFP4.gguf
export MODEL_GPTOSS20=$LLM_ROOT/models/gpt-oss-20b/gpt-oss-20b-MXFP4.gguf
export MODEL_NEMOSUPER=$LLM_ROOT/models/nemotron-super-49b/Q8_0/Llama-3_3-Nemotron-Super-49B-v1_5-Q8_0-00001-of-00002.gguf
