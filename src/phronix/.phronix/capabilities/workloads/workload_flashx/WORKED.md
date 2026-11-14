# What worked: workload_flashx

## flashx/build/hdf5
HDF5 1.14.3 (and 1.14.5) from the HDF Group FTP mirror, parallel shared production install into `<WS>/hdf5_1.14`, `H5Apublic.h` chid_t -> hid_t patch (2026-07-08).

## flashx/build/sedov3d
`git submodule update --init --recursive`; `HDF5_PATH=<WS>/hdf5_1.14 bash setup Sedov -auto -3d +parallelIO`; `object/Makefile.h`: GNU 11.2 Cray MPICH wrappers, MPI_PATH=/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2, HDF5_PATH=<WS>/hdf5_1.14, FFLAGS += -fallow-argument-mismatch; `make -j` in `object/` -> `object/flashx`; `ldd` shows `<WS>/hdf5_1.14/lib/libhdf5.so.310` (2026-07-08).

## flashx/annotate/function
C IO layer auto-annotated (66 files) + `object/dftracer_init_fini.c` constructor/destructor shim (`MACHOBJ += dftracer_init_fini.o`, recreated after setup); single-rank Sedov smoke: 6566 events, HDF5 5236 / POSIX 696 / C_APP 552 (2026-07-08).

## flashx/run/production
`production_run.sh` exporting LD_LIBRARY_PATH (HDF5 lib, dftracer lib64, CCE lib), DFTRACER_ENABLE=1, DFTRACER_INIT=PRELOAD, DFTRACER_DATA_DIR=all, DFTRACER_INC_METADATA=1, DFTRACER_LOG_FILE=<WS>/traces/raw/<run>, LD_PRELOAD=<dft lib64>/libdftracer_preload.so, MPICH_GPU_SUPPORT_ENABLED=0, HDF5_USE_FILE_LOCKING=FALSE, `cd object && ./flashx`; launched with `flux proxy <alloc> flux run -N <n> -n $((n*48)) --exclusive ./production_run.sh`; no module load inside.

## flashx/optimize/io
384 ranks / 8 nodes Sedov 3D (nblockx=9, lrefine_max=2), 18 checkpoints ~6.7 GB on Lustre: `+parallelIO` -> + `MPICH_MPIIO_HINTS=*:romio_cb_write=enable:cb_nodes=16` + `CRAY_CB_NODES_MULTIPLIER=2` + `lfs setstripe` 16 x 4 MB: critical-path write 11.09 s -> 1.45 s (2026-07-08).

## tool:workload_flashx_recipe
Renders the above as JSON (variants smoke, production_384, io_opt3); `workload_flashx_check` fails Cray ftn, par argv and env through flux proxy, passes the WORKED build lines.
