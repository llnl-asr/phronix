# Lessons: workload_scaffold

- [L-2e69021c] dftracer native extension broken in the ScaFFold venv -> site default python 3.13 -> ml load python/3.11.5 for install and run (2026)
- [L-a4d3a951] ScaFFold run ends with 'double free or corruption (!prev)' -> dftracer built with crayclang mpicc links libmpi_cray.so.12 next to the preloaded libmpi_gnu.so.12 -> build dftracer with the GNU MPICH wrapper (mpich/9.1.0/ofi/gnu/11.2/bin/mpicc) (2026)
- [L-9442624a] ScaFFold 'RuntimeError: Error in dlopen: libcaffe2_nvrtc.so' -> dftracer's gotcha dlopen interception breaks torch's RPATH lookup -> put <venv>/lib/python3.11/site-packages/torch/lib on LD_LIBRARY_PATH (2026)
- [L-cd81acb0] ScaFFold exits 134 (SIGABRT) after all work with a complete trace -> preloaded ROCm libomp + MKL libmkl_gnu_thread are two OpenMP runtimes under gotcha (bisected; KMP_DUPLICATE_LIB_OK, OMP_NUM_THREADS, MKL_THREADING_LAYER do not help) -> runners tolerate rc 134 only and validate the trace (2026)
- [L-971f6a9e] ScaFFold double free with two dftracer inits -> generate_fractals.py called initialize_log() while worker.py inits at import (cli.py imports both) -> use dftracer.get_instance() in generate_fractals.py (2026)
- [L-f415ff64] ScaFFold ValueError at 32 ranks -> train and val volume counts must both exceed ranks and batch_size*world_size <= training samples -> n_categories=20, n_instances_used_per_fractal=24 (160 volumes, val 48 / train 112) (2026)
- [L-8ae75e59] ScaFFold diagnosed metadata/small-I/O bound -> broken stack (wrong python, crayclang-vs-GNU MPI) hid MPI events and mis-sized POSIX transfers -> re-baseline on the corrected stack: read+write 3:1 over metadata, barrier stall = rank-0 checkpoint (2026)
- [L-02aa4e80] MPI_Barrier looked like ~65% of wall time -> measured on a 2-second training run -> at 749.9 s of training it is ~2%; never rank bottlenecks from a seconds-long run (2026)
- [L-98e173cd] ScaFFold profile had no HIP interception -> DFTRACER_ENABLE_HIP_TRACING not exported (ROCm on CMAKE_PREFIX_PATH is not enough) -> export DFTRACER_ENABLE_HIP_TRACING=ON; install pydftracer from its own @develop (2026)
- [L-b731a6bc] ScaFFold training job unschedulable forever with dftracer_service -> torchrun-hpc forces --exclusive, the daemon holds 1 core/node; dftracer_service start under flux run never returns -> no daemon with torchrun-hpc; start daemons with flux submit (2026)
- [L-82ca93c8] /dev/shm checkpoint staging +6.3% -> tmpfs and Lustre are different devices so shutil.move is read+write -> reject; use hardlink_best (temp + os.replace + os.link) -2.5% (2026)
