# What worked: workload_minife

## minife/openmp45-opt/build
Tuolumne: `module load rocm/6.4.2; module load rocmcc/6.4.2-cce-20.0.0-magic; module load cray-mpich/9.0.1; module load papi/7.2.0.2`
(last, alone); CC/CXX = the cray-mpich-9.0.1-rocmcc-6.4.2-cce-20.0.0-magic mpiamdclang/mpiamdclang++; ice4hpc Makefile-openmp45-opt as
openmp45-opt/src/Makefile; `ln -sfn ../openmp45/{basic,fem,utils}` in openmp45-opt; commit abe3288; session_install_dftracer hip=True.

## minife/openmp45-opt/baseline
4 nodes x 4 ranks, `miniFE.x nx=768 ny=768 nz=768` (~3 m 45 s, ~9 GB/rank): 1,165,631 events (PAPI 738,930; MPI 83,557; HIP 32,553;
CPP_APP 18,789; POSIX/STDIO 53,074; dftracer_service 233,310), 13/16 ranks with PAPI on; DFTRACER_ENABLE_PAPI_TRACING=0 gives 16/16.

## minife/openmp45-opt/annotate
The 24 functions of the SKILL.md table (DFTRACER_CPP_FUNCTION + UPDATE comp), REGION_END + FINI before both finalize_mpi() wrappers,
hot per-element/timer functions excluded.

## minife/cuda/build
H100 + mvapich2: `NVCC = nvcc -ccbin mpicxx -Xcompiler -fopenmp`, `-gencode=arch=compute_90,code="sm_90,compute_90"`, `-lnvToolsExt`,
`-Xlinker -rpath -Xlinker` for CUDA and dftracer lib64; `#include <nvtx3/nvToolsExt.h>` in src/CudaELLMatrix.hpp.

## minife/cuda/run
`--gres=gpu:4` + `num_devices=4`, `--kill-on-bad-exit=1`, outer `timeout`: ranks map 1:1 onto GPUs for ppn 1/2/4.

## tool:workload_minife_recipe
Renders the above as JSON (variant filter); `workload_minife_check` rules on proposed commands.
