# Lessons: workload_af3

- [L-f3ba3e47] AF3 annotated import fails 'TypeError: unsupported callable' (data/pipeline.py::_get_protein_msa_and_templates, model/pipeline/inter_chain_bonds.py) -> @_dft.log above @functools.cache calls inspect.getfullargspec on the lru_cache wrapper -> functools.cache/lru_cache outermost, @_dft.log innermost (2026-07-29)
- [L-869cd6c4] AF3 ROCm jax_triton patch had no effect -> override lines appended after the stock try/except AttributeError: raise ImportError block (dead code) -> replace that block with get_compute_capability = None / get_serialized_metadata = None; verify import and grep (2026-07-29)
- [L-65908e0b] AF3 dftracer produced no trace and no error -> dftracer C extension needs Cray CCE runtime libs on LD_LIBRARY_PATH before the venv activates, else NoOpProfiler -> export them first (2026-07-29)
- [L-2fd74ffa] AF3 run_inference scaling misattributed to MSA depth -> per-seed time scales as N_bucket^2.02 plus ~32-43 s JIT compile per process -> split seed 1 from seeds 2+ via absl timestamps before attributing (2026-08-02)
- [L-3458a5d3] AF3 large-input wall time -> 1280 bucket pads 1085 tokens (~18% waste) -> 64-aligned 1088 bucket: 1077-1097 s -> 793 s at 1e66 (2026-08-02)
- [L-95b29a1a] AF3 XLA_PYTHON_CLIENT_PREALLOCATE=false gave nothing at 1e66 (1109 s) -> win came from CPU featurization memory pressure, 9.9% of 1e66 wall -> keep it scale-limited to 1eby-class inputs (2026-08-02)
- [L-870df2fe] AF3 optimized CIF differs by thousands of lines -> GPU run-to-run nondeterminism (baseline vs itself too) -> compare ptm/iptm/ranking_score, not CIF bytes (2026-08-02)
- [L-218b7368] AF3 --flash_attention_implementation=triton gives identical timing to xla -> triton path needs Ampere+ and the ROCm probe is nulled: silent fallback -> do not credit it (jaxlib 0.4.34, jax_rocm60, ROCm 6.0.0) (2026-08-02)
- [L-16075129] AF3 --jax_compilation_cache_dir cache hit then 'RESOURCE_EXHAUSTED: Failed to instantiate HIP graph: HIP_ERROR_OutOfMemory' -> HIP command-buffer/graph path -> untested workaround XLA_FLAGS=--xla_gpu_enable_command_buffer= (2026-08-02)
