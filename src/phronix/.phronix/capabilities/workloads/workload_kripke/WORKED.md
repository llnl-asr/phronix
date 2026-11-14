# What worked: workload_kripke

## kripke/build/cpu
`cmake <src>/cmake/kripke -DKRIPKE_SOURCE_ROOT=<src> -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_MPI=On -DENABLE_OPENMP=On -DENABLE_TESTS=Off -DENABLE_EXAMPLES=Off -DBLT_SOURCE_DIR=<src>/blt -DRAJA_ENABLE_EXERCISES=Off -DRAJA_ENABLE_EXAMPLES=Off -DRAJA_ENABLE_TESTS=Off -DRAJA_ENABLE_BENCHMARKS=Off`, `make kripke.exe`.

## kripke/annotate/cpp
clang_annotate_project with the recipe compile_flags, excluding /tpl/ /blt/ /scripts/ /host-configs/; add sweepSubdomain, SweepComm and generateEnergy by hand; FINI before Comm::finalize().

## kripke/run/2node
`--zones 96,96,96 --niter 15 --procs 2,2,2`, 2 nodes x 4 ranks, OMP_NUM_THREADS=23: ~45 s.

## tool:workload_kripke_recipe
Renders the above; workload_kripke_check passes the inner-project configure.
