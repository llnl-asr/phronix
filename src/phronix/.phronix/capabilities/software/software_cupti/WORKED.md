# What worked: software_cupti

- [tool:cupti_probe] Compile the probe (cuptiGetTimestamp, cuptiActivityEnable(CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL), cuptiGetVersion) with `gcc probe.c -I$CUDA_ROOT/include -L$CUDA_ROOT/lib64 -lcupti -o probe` and run it on a compute node with `LD_LIBRARY_PATH=$CUDA_ROOT/lib64:$LD_LIBRARY_PATH ./probe`; 0 / non-zero ts / CUPTI_SUCCESS means the backend will work (2026-08-26, cuda-12.6.0, CUPTI_API_VERSION=24).
- [dftracer/cuda/build] `DFTRACER_ENABLE_CUDA_TRACING=ON DFTRACER_CUDA_PATH=<cuda-root> pip install --no-binary dftracer <src>`; configure log shows `[DFTRACER] found CUPTI at <root>/include`.
