---
name: workload_ipic3d
description: iPIC3D (KTH-HPC/iPIC3D, 3D particle-in-cell plasma simulation, C++/CMake, MPI + parallel HDF5 / VTK output) - build, input decks, MPI topology, annotation, traced runs and its Rabbit storage mapping, as tools plus what each step taught us. Load for any iPIC3D build, smoke, baseline, optimization or Rabbit integration.
---
Cross-references: [[software_flux]] [[ropt_alloc]] [[system_tuolumne]] [[system_hetchy]] [[rabbit-software-hdf5]] [[dftracer-annotate-cpp]] [[tools_parallel]]

## Rules
- Source: `git@github.com:KTH-HPC/iPIC3D.git` (ssh; https prompts for credentials on LLNL nodes), ref `master` (no `main`, no release tags). Build HDF5 1.14 from source (never the system 1.10.5).
- Before configuring: `ipic3d_source_check(src)` - every fix it reports missing must be applied to the tree that is built (the dftracer session's `source/` or `annotated/` copy, not the app dir).
- Configure with exactly `ipic3d_cmake_args(hdf5_root, dftracer_cmake_dir)`; after any configure that found the wrong HDF5, delete `build/CMakeCache.txt` and `build/CMakeFiles` first.
- Every run's deck is a copy made by `ipic3d_input(base, out, ranks, save_dir, restart_dir, write_method, ncycles)` and checked with `ipic3d_input_check` right before submission. The rank count decides XLEN x YLEN x ZLEN (`ipic3d_topology`).
- Output (SaveDirName/RestartDirName) goes to the site parallel filesystem or a Rabbit mount, never the NFS project space: Tuolumne `/p/lustre5/$USER`, hetchy `/p/lslide/$USER` (Lustre) or `/p/vast1/$USER`.
- Run the binary by absolute path (`install/bin/iPIC3D` or `install_ann/bin/iPIC3D`) with the Cray PE runtime dirs, `<hdf5_1.14>/lib` and (traced) the dftracer lib64 on LD_LIBRARY_PATH (`tuolumne_runtime_env`).
- Tracing: function mode only (preload=false); annotate the entry point and the I/O layer (`iPIC3D.cpp`, `inputoutput/phdf5.cpp`, `inputoutput/ParallelIO.cpp`, `inputoutput/OutputWrapperFPP.cpp`, `main/iPIC3Dlib.cpp`, `main/Collective.cpp` entry macros only) with DFTRACER_CPP_FUNCTION, comp=io; never per-particle/per-cell helpers.
- Rabbit mapping: `ipic3d_rabbit_mapping(nodes, usable)` with the types `ropt_alloc_probe_result` says are usable.

## Constraints
- XLEN*YLEN*ZLEN must equal nodes*ppn, and each must divide its cell count.
- The default decks use WriteMethod=pvtk (shared VTK via collective MPI-IO): the HDF5 path is exercised only with `shdf5`.
- With restart + particle output on, the per-process restart<rank>.hdf and proc<rank>.hdf are large (~12 GB for the 64x64x32 demo deck on 32 ranks): size Rabbit XFS for it.
- gfs2 shares only within one chassis (<= 16 nodes, `--coral2-chassis=1`); beyond that the shared VTK needs Rabbit Lustre.

## Corner cases
### `N processes cant be mapped into X x Y x Z matrix: Change XLEN,YLEN,ZLEN in method VCtopology3D.init()`
The deck's XLEN*YLEN*ZLEN differs from the rank count (ScalingTestGEM3D.inp is 4x4x2 = 32; a 4x32 job is 128). Fix: `ipic3d_input(..., ranks=128)` -> 8x8x2. Verify: `ipic3d_input_check(out, 128)` passes. (confirmed 2026-10-13)
### `add_library cannot create imported target "hdf5::hdf5" because another target with the same name already exists`
FindHDF5 already created it. Fix: guard with if(NOT TARGET hdf5::hdf5) (ipic3d_source_check reports it). (confirmed 2026-10-23)
### `call to 'size' is ambiguous` in ParallelIO.cpp
The free template size(T(&)[n]) clashes with std::size. Fix: rename to array_size (definition + calls; at ParallelIO.cpp:369,693,879,1070,1218 in 81af283). (confirmed 2026-10-23)
### `undefined reference to H5Fcreate` (H5open, H5Dwrite, H5LTmake_dataset_int ...) at the executable link
HDF5 linked PRIVATE in iPIC3Dlib, so it does not propagate. Fix: link PUBLIC in iPIC3Dlib; adding HDF5 to the executable alone does not help. (confirmed 2026-10-14)
### `Warning! ***HDF5 library version mismatched error*** Headers are 1.10.5, library is 1.14.3` (abort)
The system 1.10.5 headers are used. Fix: `-DCMAKE_CXX_FLAGS=-I<hdf5_1.14>/include` and CMP0074=NEW (both in ipic3d_cmake_args); verify `ldd install/bin/iPIC3D | grep hdf5` shows the 1.14 library. (confirmed 2026-10-23)
### `use of undeclared identifier 'builtin_expect'` (Particles3D.cpp:769)
RelWithDebInfo passes -DNDEBUG and include/asserts.h defines the macro only without it. Fix: `-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2` (in ipic3d_cmake_args); do not edit asserts.h. (confirmed 2026-10-13)
### `dftracer/dftracer.h: No such file or directory` / `Could not find dftracerConfig.cmake` (annotated build)
The annotated CMakeLists has no dftracer dependency. Fix: find_package(dftracer REQUIRED) + PUBLIC dftracer_core on iPIC3Dlib, configure with dftracer_cmake_dir. (confirmed 2026-10-23)
### `use of undeclared identifier 'u00'` in Collective.cpp after annotation
Automatic brace insertion moved declarations of braceless bodies into an inner scope. Fix: restore Collective.cpp and insert only function-entry macros in ReadInput, ReadRestart, read_field_restart, read_particles_restart, save. Automatic annotation of the I/O files also needs the MPI/HDF5/project include flags (else 0 functions found). (confirmed 2026-10-23)
### `libmpi_cray.so.12: cannot open shared object file`
Cray PE runtime dirs missing from LD_LIBRARY_PATH (detached submitters, bare shells): `tuolumne_runtime_env`. (confirmed 2026-10-21)
### Output path does not exist on hetchy
hetchy has no /p/lustre5; its parallel filesystems are /p/lslide (Lustre) and /p/vast1 (VAST over NFS). `ipic3d_input_check` reports a /p/<fs> that does not exist on the machine. (confirmed 2026-11-04)

## Parallel plan
Builds on [[tools_parallel]]. What is independent here, and what is not:
- Issued together in one message: `ipic3d_topology`, `ipic3d_cmake_args` and `ipic3d_rabbit_mapping` (pure) together with `ipic3d_source_check` (reads the source tree); checks of different decks or trees side by side. The tool code itself has no slow per-item loop (source_check reads a handful of files and stops at the first annotated one).
- Sequential, because each needs the previous answer: `ipic3d_topology` -> `ipic3d_input` (it writes the process grid) -> `ipic3d_input_check`; `ipic3d_rabbit_mapping` before `ipic3d_input` when Save/Restart dirs go to Rabbit mounts; `ipic3d_source_check` passes before configure/build.

## Corrector
Predictors: `ipic3d_topology`, `ipic3d_input`, `ipic3d_cmake_args`, `ipic3d_rabbit_mapping`. Validators: `ipic3d_input_check` (deck vs the run), `ipic3d_source_check` (tree vs the known fixes). A failed check names the fault and its fix; fix the deck or the tree, then check again.

## Self-heal
- A build error not listed here: compare with the Corner cases' error texts first; if new, fix it, verify, and add it here with capability_update.
- A newer upstream iPIC3D where a source check misfires (fix no longer needed or pattern changed): reproduce with a check, adjust `source_check`, capability_update.

## Self-learn
- Anything new explored with iPIC3D (a build error, an input parameter, a measured mapping, a run on a new system) becomes a capability: here via capability_update (error -> cause -> fix -> verify, dated); system facts go to the system_<machine> capability; one-off notes to LESSONS.md.

## Measured results
- Tuolumne, 1 node, GEM3D 64x64x32, 32 ranks, pvtk + restart: restart/proc -> Rabbit XFS (15 GiB), VTK -> shared GFS2 (1 GiB): app 22 s -> 18 s, traced I/O 3.66x (restart 3.7x, proc 7.1x, VTK 2.8x), one run each (2026-10-23).
- Paper (REX-IO iPIC3D on Rabbits, 4 nodes): restart (93.6% of I/O, file per process) -> XFS 10-14x; field/moment (collective, 0.5-1 MB) -> Rabbit Lustre 14-25x; hybrid 4.85x I/O, 1.45x overall.
