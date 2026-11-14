# What worked: software_mpi

- [tool:mpiio_hints_wrapper] wrapper.sh: `#!/bin/bash; export MPICH_MPIIO_HINTS="*:romio_cb_write=enable:cb_buffer_size=67108864"; exec "$@"`, then `flux proxy $JOB flux run -N 2 -n 192 --env LD_LIBRARY_PATH=<libs> bash wrapper.sh <binary> <args>`.
- [flashx/checkpoint/mpiio] cb_nodes=16 + CRAY_CB_NODES_MULTIPLIER=2 + 16 x 4 MB Lustre stripes raised aggregators 2 -> 16 and cut critical-path write 6.80 s -> 1.45 s (2026-07-08, 384 ranks).
- [tool:mpi4py_cray] pip download mpi4py --no-deps; unzip; patchelf --set-rpath "<venv>/lib:<cray-mpich>/lib" mpi4py/MPI.mpich.*.so; ln -sf <cray-mpich>/lib/libmpi_cray.so.12 <venv>/lib/libmpi.so.12; re-zip; MPI4PY_MPIABI=mpich pip install --force-reinstall --no-deps <patched.whl>; verify `python -c "from mpi4py import MPI; print(MPI.Get_version())"` (2026-07-09, Python 3.13, cray-mpich 9.1.0).
- [tool:aggregator_count] dftracer_view -d <split_dir> --query 'cat == "POSIX"' --stream --no-metadata piped into a script counting distinct pids with pwrite/write ret >= 1048576.
