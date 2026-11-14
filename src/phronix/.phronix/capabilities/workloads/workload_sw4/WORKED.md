# What worked: workload_sw4

## sw4/build/make
configs/make.inc with proj/hdf5/fftw/zfp/sz = no, openmp = yes, CXX=<mpic++>, FC=<ftn>, EXTRA_LINK_FLAGS `-fopenmp -L$(CRAY_LIBSCI_PREFIX_DIR)/lib -lsci_cray_mp -Wl,-rpath,$(CRAY_LIBSCI_PREFIX_DIR)/lib`; delete `#pragma ivdep` at 6 sites; `make` builds optimize_mp/.

## sw4/annotate/cpp
Rename src/*.C -> *.cpp (+4 Makefile refs), clang_annotate_file(language="cpp", compile_flags="-std=c++11 -I<annotated>/src -I<annotated>/src/double -I<mpi include>", exclude_functions='["getDepth"]'); fix include placement in EW.C/RandomizedMaterial.C and INIT placement in main.C.

## sw4/run/2node
LOH.1 copy with h=75, t=9.0: `flux run -N2 -n16 -c11` with OMP_NUM_THREADS=11, `fileio path=<pfs dir>`: 89-112 s, outputs byte-identical to pristine.

## tool:workload_sw4_recipe
Renders the above; workload_sw4_check passes a make.inc with libsci and no ivdep.
