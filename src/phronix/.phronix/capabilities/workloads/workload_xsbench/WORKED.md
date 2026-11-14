# What worked: workload_xsbench

## xsbench/openmp-threading/build
`export CC=$(which mpicc) CXX=$(which mpic++)`; `cd <WS>/source/openmp-threading && make MPI=yes -j8`; annotated:
`make MPI=yes -j8 CFLAGS="-std=gnu99 -Wall -O3 -fopenmp -DOPENMP -DMPI -I<dft>/include" LDFLAGS="-lm -L<dft>/lib64 -ldftracer_core -Wl,-rpath,<dft>/lib64"`;
session_install_dftracer(hip=False, hdf5=False).

## xsbench/openmp-threading/annotate
clang_annotate_project, then clang_annotate_file Simulation.c (restored pristine) with exclude_functions of calculate_micro_xs,
calculate_macro_xs, grid_search, grid_search_nuclide, pick_mat, fast_forward_LCG, LCG_random_double, quickSort_parallel_internal_i_d,
quickSort_parallel_internal_d_i; Main.c INIT/START out of #ifdef MPI, END/FINI unconditional; FINI in io.c print_CLI_error.

## xsbench/openmp-threading/run
`./XSBench -m event -s large -l 200000000 -t 22 -G unionized`, 2 nodes x 4 ranks: ~55 s simulation, ~4.0-5.1 M lookups/s per rank
(21% tracing cost), checksum 437675 identical to the unmodified binary.

## xsbench/cuda/build
Add MPI init/finalize under #ifdef MPI to cuda/Main.cu; `make CC="nvcc -ccbin g++" CFLAGS="... -arch=sm_90 -DMPI -DMPICH_SKIP_MPICXX -I<mpi>/include -I<dft>/include"
LDFLAGS="-lm -L<mpi>/lib -lmpi -L<dft>/lib64 -ldftracer_core -Xlinker -rpath ..."`; event mode only; 1-rank -s small ~5 s.

## tool:workload_xsbench_recipe
Renders the above as JSON; `workload_xsbench_check` rules on proposed commands.
