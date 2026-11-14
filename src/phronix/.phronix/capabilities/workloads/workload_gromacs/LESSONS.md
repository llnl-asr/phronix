# Lessons: workload_gromacs

- [L-9a1f0c21] GROMACS `make install` fails with "sphinx.errors.ExtensionError: Could not import extension sphinx_copybutton" although -DGMX_BUILD_HELP=OFF (Tuolumne, Cray PE, Python 3.13.2 anaconda, GROMACS main) -> -DGMX_BUILD_HELP=OFF only disables HTML help; the PDF manual target builds unconditionally during make install and its Sphinx config needs sphinx_copybutton, absent from the system Python -> add -DGMX_BUILD_MANUAL=OFF; do not install sphinx_copybutton (no sudo) or edit docs/manual/CMakeLists.txt (2026-08-07)
- [L-3c7e5d90] GROMACS configure detects the system HDF5 1.10.5 and rejects it -> GROMACS needs HDF5 1.10.7+ -> build HDF5 1.14.3 from source in the session (parallel, shared, production; patch H5Apublic.h chid_t -> hid_t) and pass -DHDF5_DIR (2026-08-07)
- [L-5b20e8d4] GROMACS CMake configure fails on the default cmake -> system default 3.24.2 < required 3.28 -> module load cmake/3.29.2 (2026-08-07)
