---
name: workload_gromacs
description: GROMACS (molecular dynamics, CMake, C++/HIP/Fortran) build on Tuolumne - CMake 3.28+, -DGMX_BUILD_MANUAL=OFF (sphinx_copybutton error at make install), HDF5 1.14 from source (system 1.10.5 rejected), MPI/HIP flags. Load for gromacs, gmx mdrun, "Could not import extension sphinx_copybutton", gromacs_pdf.
---
Cross-references: [[software_cmake]], [[software_hdf5]], [[system_tuolumne]], [[software_rocm]], [[software_mpi]]

# workload_gromacs

GROMACS (GROningen MAchine for Chemical Simulations): molecular dynamics simulation package. Build system: CMake.
Languages: C++, CUDA/HIP, Fortran, Python bindings. Converted from dftracer-agents' `workload-gromacs` skill.
`workload_gromacs_recipe` renders the recipe below; `workload_gromacs_check` rules on a proposed command list.

## Rules
- **CMake 3.28+ required** (system default 3.24.2 is too old): `module load cmake/3.29.2` on Tuolumne.
- HDF5 optional but recommended for checkpoint I/O. MPI support via `-DGMX_MPI=ON`. GPU: `-DGMX_GPU=HIP` for AMD MI300A (ROCm).
- Required configure flags:
  ```bash
  cmake -S source -B build \
    -DCMAKE_INSTALL_PREFIX=<install_dir> \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DGMX_MPI=ON \
    -DGMX_GPU=HIP \
    -DGMX_OPENMP=ON \
    -DGMX_DOUBLE=OFF \
    -DBUILD_TESTING=OFF \
    -DGMX_BUILD_HELP=OFF \
    -DGMX_BUILD_MANUAL=OFF \
    -DGMX_INSTALL_LEGACY_API=ON \
    -DHDF5_DIR=<session_hdf5_prefix> \
    -DMPI_C_COMPILER=/opt/cray/pe/mpich/9.0.1/ofi/crayclang/20.0/bin/mpicc \
    -DMPI_CXX_COMPILER=/opt/cray/pe/mpich/9.0.1/ofi/crayclang/20.0/bin/mpicxx
  ```
- **Critical: disable the documentation build.** GROMACS docs require the `sphinx_copybutton` Python module, not available in
  the system anaconda environment. The docs build fails even with `-DGMX_BUILD_HELP=OFF`. Always add `-DGMX_BUILD_MANUAL=OFF`
  to skip PDF manual generation entirely. Without it the build succeeds for all binaries but fails at the very end during
  `make install` when building the PDF manual with Sphinx, blocking the install step (observed 2026-08-07, Tuolumne, GROMACS main).
- HDF5 integration: GROMACS can use HDF5 for the checkpoint format. System HDF5 1.10.5 is detected but rejected (requires
  1.10.7+). Build HDF5 1.14.x from source per [[software_hdf5]] in the session workspace:
  ```bash
  curl -fkL https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.3/src/hdf5-1.14.3.tar.gz \
    -o hdf5-1.14.3.tar.gz
  tar xf hdf5-1.14.3.tar.gz && cd hdf5-1.14.3
  CC=mpicc ./configure --prefix=$PWD/../hdf5_1.14 --enable-parallel --enable-shared \
    --enable-build-mode=production --with-zlib=/usr
  make -j8 && make install
  cd .. && sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/' \
    hdf5_1.14/include/H5Apublic.h
  ```
  Then pass `-DHDF5_DIR=$PWD/hdf5_1.14` to the GROMACS cmake.

## Constraints
- Do not install `sphinx_copybutton` into the system Python (no sudo).
- Do not modify GROMACS's `docs/manual/CMakeLists.txt` (would diverge from upstream).
- `workload_gromacs_recipe` / `_check` render and check text only; they never build or run.

## Corner cases
- Symptom of the docs trap:
  ```
  sphinx.errors.ExtensionError: Could not import extension sphinx_copybutton
  (exception: No module named 'sphinx_copybutton')
  make[2]: *** [docs/manual/CMakeFiles/gromacs_pdf.dir/build.make:71: docs/manual/gromacs.tex] Error 2
  ```
  `-DGMX_BUILD_HELP=OFF` only disables HTML help, not the PDF manual; the PDF target builds unconditionally during `make install`.
- Smoke test: TBD. A typical GROMACS smoke uses `gmx mdrun` on a small test system; add the command here after the first
  successful build.
- Failed configurations (appended during optimization loops): none recorded yet.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_gromacs_check`, repair the proposed commands, then call `workload_gromacs_recipe` and the check again:
- `manual_off` / `help_off`: add `-DGMX_BUILD_MANUAL=OFF` / `-DGMX_BUILD_HELP=OFF` to the cmake configure line.
- `cmake_version`: load `cmake/3.29.2` (3.28+).
- `no_system_hdf5`: build HDF5 1.14.x from source (recipe `dependencies.hdf5`) and point `-DHDF5_DIR` at it.
- `no_sphinx_install`, `no_docs_cmake_edit`: drop the step; the CMake flag is the fix.
- `input` (inconclusive): pass the command list. The same failure twice stops the loop for the user.

## Self-heal
On a failed build, match the error to Corner cases and LESSONS.md (`lesson_search` the error text first); if the recipe or a
rule here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: a new GROMACS procedure (smoke command, run sizing, annotation scope) verified by
hand is added to this capability (`capability_update`), new software met on the way becomes its own `software_<x>`; each new
error -> cause -> fix goes to LESSONS.md, each verified recipe to WORKED.md.

## What works
- 2026-08-07, Tuolumne, GROMACS main: configure with the flags above (incl. `-DGMX_BUILD_MANUAL=OFF`) and HDF5 1.14.3 built
  from source; binaries build and `make install` completes.
