# What worked: workload_ior

## ior/build/configure
`touch NEWS AUTHORS && autoreconf -fi -I config`; `CFLAGS="-g -O2 -Wno-incompatible-function-pointer-types -fcommon" LDFLAGS="-fuse-ld=bfd" ./configure --without-hdf5 --without-ncmpi --prefix=<install>`; `make clean && make -j8`.

## ior/build/hdf5
`make distclean`; remove `.deps src/.deps autom4te.cache config.status config.log Makefile`; `CPPFLAGS=-I<hdf5>/include LDFLAGS="-L<hdf5>/lib -Wl,-rpath,<hdf5>/lib" LIBS="-lhdf5 -lz" ./configure --with-hdf5=yes`; `grep USE_HDF5_AIORI config.h` shows 1 (2026-07-24).

## ior/install/dftracer
Tuolumne 2026-07-06: private copy of Cray HDF5 1.14.3.7 (crayclang) include dir with the chid_t -> hid_t sed, lib symlinked; `module unload cray-hdf5-parallel`; `DFTRACER_ENABLE_MPI=ON DFTRACER_ENABLE_HDF5=ON DFTRACER_ENABLE_FTRACING=ON DFTRACER_ENABLE_HIP_TRACING=OFF DFTRACER_DISABLE_HWLOC=ON MPI_C_COMPILER=$(which mpicc) MPI_CXX_COMPILER=$(which mpicxx) HDF5_ROOT=<patched> HDF5_DIR=<patched> pip install --no-cache-dir --force-reinstall --no-deps -v git+https://github.com/llnl-asr/dftracer.git@develop`; dftracer_config.hpp shows MPI/HDF5/FTRACING == 1.

## ior/annotated/build
In `<ws>/annotated/source`: `autoreconf -fi -I config`; `CFLAGS="-g -O2 -Wno-incompatible-function-pointer-types -fcommon -I<dft>/include" LDFLAGS="-fuse-ld=bfd -L<dft>/lib64 -Wl,-rpath,<dft>/lib64 -Wl,--allow-shlib-undefined -Wl,--no-as-needed" LIBS="-ldftracer_core -lstdc++"` with `LD_LIBRARY_PATH=<dft>/lib64:<python-3.13 module lib>:$LD_LIBRARY_PATH`; `make -C src -j8 install` (2026-07-24).

## ior/smoke/run
`./src/ior -a POSIX -b 1m -t 1m -s 1 -F -C -o /tmp/ior_smoke_test` (single process; containers with OpenMPI root: `OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 mpirun -np 1 --allow-run-as-root ...`).

## ior/optimize/vast
VAST NVMe, 192 ranks / 2 nodes, `MPICH_MPIIO_HINTS="*:romio_cb_write=enable"`, `-a HDF5 -b 64m -t 16m -s 4 -c -Y`: 168.8 s -> 112.9 s, write 352 -> 557 MiB/s, read 1705 -> 1991 MiB/s.

## ior/analyze
`cluster_type=local cluster_n_workers=1`, checkpoint mode, fresh `.dftindex`; inside a flux allocation with default worker sizing: full read of 64 procs / 1.75M events in ~9 s.

## tool:workload_ior_recipe
Renders the above as JSON (variants vast_hdf5_romio_opt, lustre_hdf5_shared_baseline, lustre_hdf5_fpp_4k); `workload_ior_check` fails `--with-hdf5=<path>` and passes the WORKED configure lines.
