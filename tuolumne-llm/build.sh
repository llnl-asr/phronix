#!/bin/bash
# Build llama-cpp-turboquant for the GPU named by env.sh (GPU_TARGET).
#
#   tuolumne-llm/build.sh  -> gfx942 (MI300A), MFMA on
#   corona-llm/build.sh    -> gfx906 (MI50),   MFMA OFF — see below
#
# HOST_CC/HOST_CXX compile the CPU backend; HIPCXX always compiles the device
# code. They are separable because ROCm 5.7.1's clang 17 crashes outright on
# ggml-cpu/arch/x86/repack.cpp (frontend ICE, exit 70) while compiling the
# gfx906 device kernels perfectly well — so corona builds the host half with
# gcc and the device half with hipcc.
#
# Run inside an allocation, e.g.
#   flux batch -N1 -t 120m --queue=pbatch --output=$LLM_ROOT/logs/build.log tuolumne-llm/build.sh
set -euo pipefail
# Resolve env.sh NEXT TO THIS SCRIPT, not from a hardcoded path: corona-llm/
# symlinks these scripts and carries its own env.sh, and a hardcoded default
# would have every corona invocation silently load Tuolumne's paths and arch.
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"

cd "$LLAMA_SRC"
HIPCXX="$ROCM_PATH/llvm/bin/clang++" \
cmake -S . -B "$LLAMA_BUILD" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER="${HOST_CC:-$ROCM_PATH/llvm/bin/clang}" \
    -DCMAKE_CXX_COMPILER="${HOST_CXX:-$ROCM_PATH/llvm/bin/clang++}" \
    -DCMAKE_SHARED_LINKER_FLAGS="${EXTRA_LINKER_FLAGS:-}" \
    -DCMAKE_EXE_LINKER_FLAGS="${EXTRA_LINKER_FLAGS:-}" \
    -DGGML_HIP=ON \
    -DGGML_HIP_MIN_VERSION=${HIP_MIN_VERSION:-6.1} \
    -DGPU_TARGETS=$GPU_TARGET \
    -DAMDGPU_TARGETS=$GPU_TARGET \
    -DGGML_HIP_MMQ_MFMA=${HIP_MMQ_MFMA:-ON} \
    -DGGML_HIP_GRAPHS=${HIP_GRAPHS:-ON} \
    -DGGML_BLAS=OFF \
    -DGGML_RPC=OFF \
    -DCMAKE_DISABLE_FIND_PACKAGE_BLAS=ON \
    -DCMAKE_DISABLE_FIND_PACKAGE_LAPACK=ON \
    -DCMAKE_DISABLE_FIND_PACKAGE_MPI=ON \
    -DLLAMA_CURL=ON \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=OFF

cmake --build "$LLAMA_BUILD" --config Release -j "$(nproc)"
ls -l "$LLAMA_SERVER"
echo BUILD_DONE
