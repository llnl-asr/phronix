# What worked: system_matrix

- [matrix/toolchain/modules] Sourced script: `module load gcc/12.1.1-magic; module load mvapich2/2.3.7; module load cuda/12.6.0; export CUDA_HOME=/usr/tce/packages/cuda/cuda-12.6.0; export CC=$(command -v mpicc) CXX=$(command -v mpicxx)`, then `which mpicc nvcc` (2026-08-26).
- [minife/cuda/sweep] 1176-run genesis sweep: pdebug for N=1 (~5.5 runs/min), one non-blocking sbatch per node scale on pci (2026-08-26).
- [tool:nvidia-smi] GPU power as ordinary user: `nvidia-smi --query-gpu=index,power.draw,utilization.gpu,memory.used --format=csv,noheader,nounits` on a compute node.
- [tool:pip] `export PIP_INDEX_URL=https://wci-repo.llnl.gov/repository/pypi-group/simple PIP_TRUSTED_HOST=wci-repo.llnl.gov PIP_EXTRA_INDEX_URL=` before pip install in a fresh venv.
- [tool:dftracer_mpi_symbols] `nm -DC libdftracer_core.so | grep -c 'MPIDFTracer::MPI_'` ~298 and `grep -c 'MPIIODFTracer::MPI_'` ~59 after the MVAPICH patches.
- [xsbench/mvapich2/run] dftracer develop + dftracer_reentry_guard.patch: 8/8 clean 4-rank runs with PAPI.
- [genesis/slurm/multinode] `sbatch --parsable -p pci -N<n> --exclusive --gres=gpu:4 ...`; daemon `srun --jobid=<J> --overlap --wait=0 --nodelist=<csv> -N<n> -n<n> -c1`; app `srun --jobid=<J> --overlap --mem=0 --kill-on-bad-exit=1 --nodelist=<csv> ...`.
