# Lessons: software_mpi

- [L-02ae91e2] flux run drops the binary argument -> MPICH_MPIIO_HINTS value with colons passed via flux run --env -> Set it in a wrapper script and exec "$@" (undated)
- [L-9d99bbfb] romio_no_indep_rw silently dropped ('unrecognized value') -> Not supported on cray-mpich 9.0.1 -> Do not use it (undated)
- [L-6f325e28] Massive pwrite p95 regression (+2650%) with cb_nodes=56 on variable-size writes -> More aggregators fragment variable chunks -> Do not set cb_nodes for variable-size writes on Tuolumne lustre5 (undated)
- [L-97421811] Hints display echoes cb_nodes=8 but only 2 aggregators -> Cray MPICH ignores cb_nodes without CRAY_CB_NODES_MULTIPLIER -> cb_nodes + CRAY_CB_NODES_MULTIPLIER + wide stripe; verify aggregators from trace (>= 1 MiB writes per pid) (2026-07-08)
- [L-8cc2dc6d] VAST write BW 352 -> 95 MiB/s -> romio_ds_write=disable -> Keep data-sieving writes enabled on VAST (undated)
- [L-684b06c4] VAST read BW -70% -> romio_cb_read=enable on parallel NVMe -> Disable collective read buffering on VAST (undated)
- [L-0810c9eb] `fatal error: mpi.h: No such file or directory` in clang_syntax_check -> Cray PE mpicc include dirs come with a -I prefix -> Pass extra_include_dirs explicitly (undated)
- [L-8761dba0] mpi4py: `cannot load MPI library ... libmpi.so.12` -> manylinux wheel expects libmpi.so.12; Cray has libmpi_cray.so.12 -> Patch wheel RPATH, symlink libmpi.so.12 in the venv lib, MPI4PY_MPIABI=mpich (2026-07-09)
- [L-ad5b35c9] --no-binary=mpi4py build succeeds but install fails -> pip atomic rename onto NFS fails (Python 3.13) -> Extract the wheel manually instead (2026-07-09)
- [L-a55e9795] MPI_Barrier ~99% of MPI time / ~65% of wall on ScaFFold -> 2-second training run: startup, teardown and first-epoch stragglers dominated -> Rank bottlenecks only from runs with >= ~10 min training at a fixed budget; barrier was ~2% at 12 min (undated)
- [L-5e6b3734] Barrier dominates IOR / RAJAPerf profiles -> Barriers belong to the benchmark's own timing harness -> grep call sites, leave harness barriers; only collective-algorithm selection remains (MPICH_SHARED_MEM_COLL_OPT=1 measured no_change -1.6% on IOR) (2026-08-05)
- [L-a0d96dce] comparator reports MPI_Barrier p50 identical (167.79 ms) across variants -> Fixed time-bucket artifact -> Use mean/p95/p99 and wall clock (undated)
