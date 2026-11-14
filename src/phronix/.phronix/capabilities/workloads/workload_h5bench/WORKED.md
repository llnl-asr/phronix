# What worked: workload_h5bench

## h5bench/build/hdf5
HDF5 1.14.3 from `https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.3/src/hdf5-1.14.3.tar.gz`, `CC=mpicc ./configure --prefix=<ws>/hdf5_1.14 --enable-parallel --enable-shared --enable-build-mode=production --with-zlib=/usr`, `make -j8 && make install`, chid_t -> hid_t sed on `include/H5Apublic.h`; session.json pointed at it, session_install_dftracer re-run.

## h5bench/build/configure
`cmake -S source -B build -DH5BENCH_ALL=ON`; all 7 `h5bench_*` binaries present.

## h5bench/annotated/link
After session_install_dftracer: `sed -i 's/-ldftracer\b/-ldftracer_core/g'` in `build_ann/CMakeCache.txt` and every `CMakeFiles/**/link.txt`, `-ldftracer_core` at the end of the cc line; `MPI_C_WORKS:BOOL=TRUE`, `MPI_CXX_WORKS:BOOL=TRUE` in the cache; Cray CCE runtime lib dirs on LD_LIBRARY_PATH for runs.

## h5bench/smoke/write
INI config (MEM_PATTERN=CONTIG FILE_PATTERN=CONTIG TIMESTEPS=3 DELAYED_CLOSE_TIMESTEPS=0 COLLECTIVE_DATA=NO COLLECTIVE_METADATA=NO NUM_DIMS=1 DIM_1=1048576 DIM_2=1 DIM_3=1), `mpirun -np 2 ./h5bench_write <cfg> <out>.h5`, `DFTRACER_ENABLE=1 DFTRACER_INIT=FUNCTION DFTRACER_DATA_DIR=all DFTRACER_LOG_FILE=<prefix>`.

## h5bench/run/read
Phase 1 `DFTRACER_ENABLE=0 ./h5bench_write write_for_read.cfg read.h5` (CONTIG, same dims), phase 2 `DFTRACER_ENABLE=1 ... ./h5bench_read read.cfg read.h5`.

## h5bench/optimize/write
Tuolumne lustre5, 768 ranks, DIM_1=2097152 INTERLEAVED: wrapper script exporting `MPICH_MPIIO_HINTS="*:romio_cb_write=enable:cb_nodes=16"` and `CRAY_CB_NODES_MULTIPLIER=2`, `lfs setstripe -c 16 -S 4M` on a fresh output dir: +490.5% median POSIX BW, ranges non-overlapping (2026-07-10).

## tool:workload_h5bench_recipe
Renders the above as JSON (variants write_opt_768, write_minimal_romio_192, hdf5_iotest_768, exerciser_768, read_768); `workload_h5bench_check` fails `-ldftracer` and DELAYED_CLOSE_TIMESTEPS=2 and passes the WORKED lines.
