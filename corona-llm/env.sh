#!/bin/bash
# Shared environment for the corona (MI50/MI60, gfx906) llama.cpp deployment.
#
# This file is the ONLY thing that differs between corona-llm/ and
# tuolumne-llm/: every other script in this directory is a symlink to its
# Tuolumne counterpart, and each one resolves `env.sh` next to ITSELF. Sourcing
# this file is therefore what makes a shared script a corona script.
#
# Why corona is worth having at all: it is the cluster you can actually get an
# allocation on. Tuolumne's queue is the binding constraint on how many
# benchmark groups run in a day, and corona's pdebug/pbatch usually schedule
# immediately.
#
# What is different, and why each difference is not cosmetic:
#
#   GPU        8 x MI50/MI60 (gfx906, Vega20), 32 GB DISCRETE HBM per card,
#              1.0 TB/s. Tuolumne is 4 x MI300A (gfx942, CDNA3) with 128 GB of
#              UNIFIED memory at 5.3 TB/s. Two consequences run through
#              everything below: a model that fits one Tuolumne GPU may need
#              several corona GPUs, and gfx906 predates MFMA.
#   ROCm       5.7.1, and NOT by preference. gfx906 was dropped from rocBLAS
#              after the 5.x line: /opt/rocm-6.0.3, 6.1.3, 6.2.0 and 6.4.3 all
#              ship ZERO gfx906 kernel libraries, where 5.7.1 ships 156. A
#              build against a 6.x/7.x toolchain compiles and then fails at
#              runtime with no rocBLAS kernels for the device.
#   Cores      48 per node (2 x EPYC 7402 24-core), against Tuolumne's 96 — so
#              6 cores per server across 8 GPUs, not 22 across 4.
#   Staging    /l/ssd, 3.5 TB of NVMe, same as Tuolumne. This is the reason a
#              corona fleet is practical: the weights are read off the PFS once
#              per node and served from local disk thereafter.
#   Storage    /p/lustre3 — /p/lustre5 is Tuolumne's and is NOT mounted here,
#              so the clone, the venv and the GGUFs are a separate copy.
export LLM_ROOT=${LLM_ROOT:-/p/lustre3/haridev/llm-corona}
_self=${BASH_SOURCE[0]:-/usr/WS2/haridev/phronix/corona-llm/env.sh}
export LLM_SCRIPTS="$(cd "$(dirname "$_self")" && pwd)"

# 5.7.1 is the last ROCm on this machine with gfx906 rocBLAS kernels. Verify
# before changing it:  ls /opt/rocm-<v>/lib/rocblas/library/ | grep -c gfx906
export ROCM_PATH=${ROCM_PATH:-/opt/rocm-5.7.1}
export HIP_PATH=$ROCM_PATH
export PATH=/usr/tce/packages/cmake/cmake-3.29.2/bin:$ROCM_PATH/bin:$LLM_ROOT/venv/bin:$PATH
export LD_LIBRARY_PATH=$ROCM_PATH/lib:${LD_LIBRARY_PATH:-}
export GPU_TARGET=gfx906

# MFMA is a CDNA instruction (gfx908 and later). gfx906 is GCN/Vega20 and has
# none, so the matrix-core MMQ path must be compiled out rather than left to
# fail at kernel launch. HIP graphs are off for the same conservatism: they are
# the least-exercised path on a deprecated architecture and buy little at one
# request per slot.
export HIP_MMQ_MFMA=${HIP_MMQ_MFMA:-OFF}
export HIP_GRAPHS=${HIP_GRAPHS:-OFF}

# The fork's CMake refuses anything below ROCm 6.1 outright, and gfx906 exists
# in no ROCm at or above it — the two constraints have no overlap, so the floor
# has to be lowered by hand and the build has to prove itself by compiling.
# `build.sh` passes this through as GGML_HIP_MIN_VERSION; the guard in
# ggml/src/ggml-hip/CMakeLists.txt was changed from a literal 6.1 to read it.
export HIP_MIN_VERSION=${HIP_MIN_VERSION:-5.7}

# Host compiler for the CPU backend. NOT the ROCm clang: 5.7.1's clang 17
# crashes with a frontend ICE (exit 70) on ggml-cpu/arch/x86/repack.cpp. It
# compiles the gfx906 device kernels without complaint, so only the host half
# moves to gcc.
export HOST_CC=${HOST_CC:-/usr/tce/packages/gcc/gcc-12.1.1/bin/gcc}
export HOST_CXX=${HOST_CXX:-/usr/tce/packages/gcc/gcc-12.1.1/bin/g++}

# ROCm 5.7's amd_hip_bf16.h declares __float2bfloat16 and friends `__host__
# __device__` with EXTERNAL linkage and no `inline`, so every translation unit
# that includes it emits its own definition and the link fails with 20
# duplicate symbols. ROCm 6 made them inline; 5.7 cannot be fixed without
# editing a system header.
#
# Allowing the duplicates is exact rather than approximate here: every copy
# comes from the same header text, so they are the same function, and the
# linker is being told to stop objecting to a definition it would otherwise
# pick arbitrarily between identical candidates.
export EXTRA_LINKER_FLAGS=${EXTRA_LINKER_FLAGS:--Wl,--allow-multiple-definition}

# Separate build tree from Tuolumne's on purpose — same source, different arch,
# and a shared build directory would silently serve gfx942 objects here.
export LLAMA_SRC=$LLM_ROOT/src/llama-cpp-turboquant
export LLAMA_BUILD=$LLAMA_SRC/build-mi50
export LLAMA_SERVER=$LLAMA_BUILD/bin/llama-server

# ---- fleet shape (deploy.sh reads the FLEET_* names) ------------------------
# GPUS_PER_NODE is SERVERS per node; GPUS_PER_SERVER is how many GPUs each one
# gets. 8x1 is right for any model that fits 32 GB. gpt-oss-120b does not
# (63 GB), so it is served as ONE server sharded across all eight cards:
#
#   GPUS_PER_NODE=1 GPUS_PER_SERVER=8 CORES_PER_SERVER=44 \
#       flux proxy <alloc> corona-llm/deploy.sh gptoss120
#
# That trades eight independent replicas for one, which on a 32 GB card is not
# a choice — the alternative is a server that dies part-way through loading.
export FLEET_GPUS_PER_NODE=${FLEET_GPUS_PER_NODE:-8}
export FLEET_GPUS_PER_SERVER=${FLEET_GPUS_PER_SERVER:-1}
export FLEET_CORES_PER_SERVER=${FLEET_CORES_PER_SERVER:-5}
export FLEET_GATEWAY_CORES=${FLEET_GATEWAY_CORES:-4}
export FLEET_PROFILE=${FLEET_PROFILE:-corona}
export FLEET_KEY=${FLEET_KEY:-sk-corona}
export LLAMA_THREADS=${LLAMA_THREADS:-5}

# gfx906 is not covered by llama.cpp's HIP flash-attention kernels, and `on`
# fails the server at startup rather than falling back. `auto` lets the build
# decide.
export LLAMA_FLASH_ATTN=${LLAMA_FLASH_ATTN:-auto}

# The venv here, not Tuolumne's — /p/lustre5 is not mounted on corona, and the
# hardcoded fallback in deploy.sh would fall through to `python3` silently.
export BENCH_PY=${BENCH_PY:-$LLM_ROOT/venv/bin/python}

# ---- models -----------------------------------------------------------------
# Sizes are against 32 GB per card:
#   gpt-oss-20b   ~12 GB  fits one GPU, 8 replicas per node
#   gpt-oss-120b  ~63 GB  needs the whole node (GPUS_PER_SERVER=8)
# The 30B-A3B Q8_0 models (~32 GB) do NOT leave room for KV on one card and are
# deliberately absent rather than listed and broken.
export MODEL_GPTOSS120=$LLM_ROOT/models/gpt-oss-120b/gpt-oss-120b-MXFP4.gguf
export MODEL_GPTOSS20=$LLM_ROOT/models/gpt-oss-20b/gpt-oss-20b-MXFP4.gguf
