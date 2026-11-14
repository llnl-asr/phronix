# What worked: software_rocm

- [tool:hip_init_order] In every GPU process: `import torch` (load only) -> `dftracer.initialize_log()` -> first GPU touch. For Ray workers, a sitecustomize.py on PYTHONPATH gated on DFTRACER_ENABLE == "1" that imports torch.
- [dftracer/hip/build] `export ROCM_PATH=<rocm-prefix>; export HIP_PATH=$ROCM_PATH; export CMAKE_PREFIX_PATH=$ROCM_PATH:$CMAKE_PREFIX_PATH; DFTRACER_ENABLE_HIP_TRACING=ON pip install --no-binary dftracer <src>` (ROCm >= 6.2), then confirm HIP_RUNTIME_API/KERNEL_DISPATCH in a real GPU trace (2026-08-05).
- [tool:torch_profiler_with_hip] torch.profiler.profile(activities=[CPU, CUDA], record_shapes=True, profile_memory=True, with_stack=False, schedule=schedule(wait=2, warmup=1, active=5, repeat=1), on_trace_ready=dftracer.python.torch.trace_handler); stop before dftracer.finalize().
- [af3/jax/env] XLA_PYTHON_CLIENT_PREALLOCATE=false on MI300A: -77% peak memory, -4.9% wall (2026-08-02, small scale).
