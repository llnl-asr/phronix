#!/bin/bash
# Build llama-cpp-turboquant for corona's MI50/MI60 (gfx906) on ROCm 5.7.1.
#
# Not a symlink to tuolumne-llm/build.sh, because this architecture needs the
# SOURCE patched before that script can run. The bind is structural:
#
#   * gfx906 rocBLAS kernels exist ONLY in ROCm 5.7.1 on this machine. Every
#     6.x and 7.x install here ships zero (`ls $ROCM/lib/rocblas/library |
#     grep -c gfx906`), so a newer toolchain builds and then finds no kernels
#     for the device at runtime.
#   * The fork's CMake demands ROCm >= 6.1, and its CUDA-ported code calls
#     two-argument `cudaStreamWaitEvent`, which is 6.0+ HIP.
#
# The two requirements do not overlap, so the older toolchain wins — it is the
# only one that can produce working kernels — and the source is adjusted to
# compile under it. Both patches below are idempotent and narrow; anything
# wider than this belongs upstream, not here.
#
#   flux batch -N1 -t 60m --queue=pdebug \
#       --output=$LLM_ROOT/logs/build.log corona-llm/build.sh
set -euo pipefail
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"

cd "$LLAMA_SRC"

# --- patch 1: the version floor --------------------------------------------
# A literal `6.1` becomes the GGML_HIP_MIN_VERSION cache variable that build.sh
# passes through, so the floor is a build option rather than an edit.
guard=ggml/src/ggml-hip/CMakeLists.txt
if grep -q 'VERSION_LESS 6.1' "$guard"; then
    sed -i 's|if (${hip_VERSION} VERSION_LESS 6.1)|if (${hip_VERSION} VERSION_LESS ${GGML_HIP_MIN_VERSION})|
            s|message(FATAL_ERROR "At least ROCM/HIP V6.1 is required")|message(FATAL_ERROR "At least ROCM/HIP V${GGML_HIP_MIN_VERSION} is required")|' "$guard"
    echo "patched: $guard (version floor now GGML_HIP_MIN_VERSION)"
fi

# --- patch 2: cudaStreamWaitEvent's third argument --------------------------
# ROCm 5.7's hipStreamWaitEvent takes (stream, event, flags) with no default.
# 6.0 added the default, and the ported CUDA code calls it with two arguments:
#
#   ggml-cuda.cu:4198: no matching function for call to 'hipStreamWaitEvent'
#
# The flag argument is 0 in CUDA's own two-argument form, so an inline wrapper
# supplying it is exactly equivalent rather than an approximation.
vendor=ggml/src/ggml-cuda/vendors/hip.h
if grep -q '^#define cudaStreamWaitEvent hipStreamWaitEvent$' "$vendor"; then
    python3 - "$vendor" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
text = text.replace(
    "#define cudaStreamWaitEvent hipStreamWaitEvent",
    """// ROCm < 6.0 has no default for hipStreamWaitEvent's flags argument, and the
// ported CUDA code calls the two-argument form. CUDA's two-argument
// cudaStreamWaitEvent passes 0, so this is the same call, not a substitute.
static inline hipError_t cudaStreamWaitEvent(hipStream_t stream, hipEvent_t event,
                                             unsigned int flags = 0) {
    return hipStreamWaitEvent(stream, event, flags);
}""")
open(path, "w").write(text)
PY
    echo "patched: $vendor (cudaStreamWaitEvent flags default)"
fi

exec "$LLM_SCRIPTS/../tuolumne-llm/build.sh"
