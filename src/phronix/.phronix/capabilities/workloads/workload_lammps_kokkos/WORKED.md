# What worked: workload_lammps_kokkos

## lammps_kokkos/build/hip
`cmake -C <src>/cmake/presets/elcapitan_kokkos.cmake -DPKG_KOKKOS=ON -DBUILD_MPI=ON <src>/cmake`, link `-lmpi` from mpich 9.0.1 and `-lmpi_gtl_hsa` + rpath from mpich 9.1.0 gtl; `flux run -N1 -n1 -c 96 bash -c "cd <build> && make -j 96"`.

## lammps_kokkos/run/2node
`flux run -N2 -n8 -g1 -c22` with HSA_XNACK=1 MPICH_GPU_SUPPORT_ENABLED=1, `lmp -k on g 1 -sf kk -in <copy of in.lj>`: 1M atoms x 1000 steps 4.2 s loop.

## lammps_kokkos/annotate/cpp
50-file scope, exclude per-atom/lattice functions, add back the Kokkos dispatchers, rename main.cpp finalize helper, INIT after MPI_Init and FINI on all 7 exits.

## tool:workload_lammps_kokkos_recipe
Renders the above; workload_lammps_kokkos_check passes the preset configure and the 2-node launch.
