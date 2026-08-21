#!/bin/bash
# Build llama-cpp-turboquant for MI300A (gfx942) on Tuolumne.
# Run inside an allocation, e.g.
#   flux batch -N1 -t 120m --queue=pbatch --output=$LLM_ROOT/logs/build.log tuolumne-llm/build.sh
set -euo pipefail
source "${LLM_SCRIPTS:-/usr/WS2/haridev/phronix/tuolumne-llm}/env.sh"

cd "$LLAMA_SRC"
HIPCXX="$ROCM_PATH/llvm/bin/clang++" \
cmake -S . -B "$LLAMA_BUILD" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER="$ROCM_PATH/llvm/bin/clang" \
    -DCMAKE_CXX_COMPILER="$ROCM_PATH/llvm/bin/clang++" \
    -DGGML_HIP=ON \
    -DGPU_TARGETS=$GPU_TARGET \
    -DAMDGPU_TARGETS=$GPU_TARGET \
    -DGGML_HIP_MMQ_MFMA=ON \
    -DGGML_HIP_GRAPHS=ON \
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
