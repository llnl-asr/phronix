# What worked: workload_scaffold

## scaffold/install/venv
ml load python/3.11.5; ml cce/21.0.0 cray-mpich/9.1.0 rocm/7.1.1 rccl/fast-env-slows-mpi; one venv; pip install -e '.[rocmwci]' (torch 2.10.0+rocm710, mpi4py 4.1.1+mpich.9.1.0); patchelf torch MPI SONAME libmpi_gnu_112.so.12 -> libmpi_gnu.so.12; dftracer on GNU MPICH; import check prints 'all OK'.

## scaffold/baseline/run
flux run -N 8 -n 32 <venv>/bin/scaffold generate_fractals -c <cfg>; torchrun-hpc -N 8 -n 4 --gpus-per-proc 1 <venv>/bin/scaffold benchmark -c <cfg> (datagen_from_scratch: 0), torch/lib on LD_LIBRARY_PATH, rc 0 or 134 then validate the trace.

## scaffold/smoke/run
torchrun-hpc -N 1 -n 4 --gpus-per-proc 1 <venv>/bin/scaffold benchmark -c smoke_config.yml with epochs: 1, problem_scale: 5, n_categories: 1.

## scaffold/optimize/dataloader
dataloader_num_workers: 4 -> -33.7% train time at 32 ranks (range 15.3-33.7% across replicates).

## scaffold/baseline/profiled_4n
scripts/run_profiled.sh <run> <cfg> (4N x 4GPU, PROFILE_TORCH + DFTRACER_TORCH_PROFILE, torch.profiler schedule wait=5,warmup=2,active=10,repeat=3, on_trace_ready=dftracer.python.torch.trace_handler): 960 epochs in 28m17s on pdebug, 47,523,059 events, 0 truncated.

## tool:workload_scaffold_recipe
renders the above; workload_scaffold_check flags python 3.13, crayclang mpicc, missing torch/lib, epochs -1, daemon with torchrun-hpc.
