# What worked: workload_af3

## af3/smoke/1eby
Default model dir (no --model_dir), input 1eby (18 MB MSA), CCE runtime libs on LD_LIBRARY_PATH before venv: ~110 s full run.

## af3/optimize/buckets
`--buckets=256,512,768,1024,1088,1536,2048,2560,3072,3584,4096,4608,5120` at 1e66: 793 s vs 1077-1097 s, ptm/iptm unchanged within noise (2026-08-02).

## af3/annotate/python
@functools.cache outermost, @_dft.log innermost; jax_triton try/except block replaced by two None assignments (2026-07-29).

## tool:workload_af3_recipe
Renders the above; workload_af3_check fails a CIF diff or triton flag.
