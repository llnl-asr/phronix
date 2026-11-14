# What worked: tools_dftracer

- [tool:dftracer-compose] 2026-11-13, tuolumne, dftracer 2.2.0.post57.dev0: in the app venv with its modules loaded, `pip install --pre "dftracer[modules]" dftracer-modules`, `dftracer-compose --enable mpi,hdf5 --disable papi,hwloc,hip,cuda`, `dftracer_install_info --composition` shows what is linked.
- [tool:session_install_dftracer] 2026-09-30: `session_install_dftracer(dftracer_repo="pypi-pre", mpi=True, papi=False, hip=False, variorum=False, hdf5=False)` built from the sdist only; `dftracer_config.hpp` showed `DFTRACER_MPI_ENABLE 1` and libdftracer_core.so linked libmpi_cray.
- [ygm/build/dftracer_imported_target] 2026-08-04: `add_library(dftracer_core_imported SHARED IMPORTED)` with IMPORTED_LOCATION `${DFTRACER_ROOT}/lib64/libdftracer_core.so` and include dir `${DFTRACER_ROOT}/include`, `-DDFTRACER_ROOT=<venv>/lib/pythonX.Y/site-packages/dftracer`, instead of find_package(dftracer).
- [tool:dftracer_merge] `dftracer_merge -d "$leaf/raw/papi_set1" -o "$leaf/compacted/papi_set1.pfw" --compress --force` (one call per leaf directory).
