# What worked: workload_vpic_kokkos

## vpic/devel/configure
`vpic_cmake_args`: Cray cc/CC, `-DBUILD_INTERNAL_KOKKOS=ON -DENABLE_KOKKOS_OPENMP=ON -DENABLE_KOKKOS_CUDA=OFF -DVPIC_USE_LEGACY_PARTICLE_ARRAY=ON
-DCMAKE_BUILD_TYPE=Release`; write_functions adds `-DHDF5_ROOT=<hdf5> -DHDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON`; `vpic_build_check` passes.

## vpic/deck/compile
`<build>/bin/vpic deck.cxx` (not install/bin/vpic); annotated install: symlink install_ann/deck, install_ann/src, install_ann/libvpic.a and add the
dftracer -I/-L/-rpath/-ldftracer_core flags to the generated wrapper.

## vpic/smoke/run
sample/Weibel/Weibel.cxx at 4-16 ranks on one node, under a minute; run line from `vpic_run_command` (--tpp, GLIBC_TUNABLES static TLS, absolute path).

## vpic/baseline/run
`vpic_deck_prepare` short_pulse (640x640, nppc 100, 80 steps, all I/O on, 2x1x2 topology): 4 ranks x 24 threads, ~5 GB in ~12 s on 1 node.

## vpic/optimize/energy_reduction
Species half of PATCH #1 (energy_p_local + one mp_allsum_d) in build_ann/: `make vpic` 12 s + deck relink 10 s; rundata/energies byte-identical at
128 ranks (2026-07-14). Field half reverted (struct growth segfault).

## tool:workload_vpic_kokkos_recipe
Renders the recipe as JSON; `workload_vpic_kokkos_check` rules on proposed commands incl. the portability_test rank count.
