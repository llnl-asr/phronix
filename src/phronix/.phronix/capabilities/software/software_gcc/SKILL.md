---
name: software_gcc
description: GCC / GNU toolchain, site-neutral: probing which GCC versions a site offers (module -t avail gcc, multiple module families), pairing GCC with an MPI wrapper (Cray per-compiler wrapper dirs vs site MPI modules that follow the loaded GCC), compiler -> MPI -> CC/CXX load order, switching compilers on an existing CMake/autotools/venv build, and GCC as the libstdc++ header provider for clang-based compilers ('Selected GCC installation:'). Points to the system_* capability that holds each site's module names. Load for any build that needs GCC/GNU instead of the site default compiler, or on mpicc using a different compiler than the gcc on PATH, CMake refusing a compiler change in CMakeCache.txt, or clang/hipcc failing on missing/old C++ standard-library headers.
---
Cross-references: [[software_mpi]] [[software_cmake]] [[software_autotools]] [[software_rocm]] [[system_detect]] [[system_tuolumne]] [[system_dane]] [[system_matrix]] [[system_tioga]] [[system_container]] [[capability_builder]]

# software_gcc

Converted from dftracer-agents skill `software-gcc`. Tools: `software_gcc_recipe` (predictor) and `software_gcc_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Site-neutral: never copy a module name from one system to another; re-derive it with the probes and read the matching system_* capability.
- Probe first: `module -t avail gcc`, `which gcc g++ gfortran`, `gcc --version | head -1`, `module -t avail <mpi-module>` (then list the MPI install's per-compiler wrapper dirs).
- Expect more than one GCC module family (vendor/PE family and site toolchain family) with different version sets and MPI pairing.
- The bare-shell `gcc` on PATH is often the newest site toolchain GCC, which may have no matching MPI wrapper; an installed GCC version does not imply an MPI build for it.
- Cray-style MPI has one wrapper dir per compiler family and version (`.../<mpi-version>/<fabric>/<family>/<compiler-version>/bin/mpicc`): list `.../<fabric>/gnu/` before choosing a GCC module.
- Site MPI modules (e.g. MVAPICH2 on LC commodity clusters) resolve to the build matching the loaded GCC when the compiler module is loaded first.
- Order: load/swap the compiler, THEN the MPI module, THEN `export CC=$(which mpicc) CXX=$(which mpicxx)`.
- Switching compilers: CMake pins the compiler in CMakeCache.txt and refuses a silent swap -> `rm -rf` the build dir; autotools -> re-run configure with the new CC and `make clean`; a venv with compiled wheels -> rebuild, do not mix.
- Clang-based compilers (Cray clang, hipcc, amdclang) take libstdc++ headers from an installed GCC: check `mpicxx -v` for `Selected GCC installation:` and choose the GCC toolset deliberately.
- A system missing from the site table means 'not yet recorded': run the probes, register the system (system_save) and add its row; never invent a pairing.

## Constraints
- Site-specific module names live in system_<machine> capabilities; this capability only holds the portable method and the pointer table.

## Corner cases
### `mpicc` wraps a different GCC than `gcc --version` reports
Bare-shell gcc is the newest site toolchain GCC, but the MPI wrapper exists only for specific versions. Fix: list the MPI per-compiler wrapper dirs, load the matching compiler module first, then MPI, then export CC/CXX from which mpicc/mpicxx.

### CMake refuses to change the compiler of an existing build dir
CMakeCache.txt pins CMAKE_C_COMPILER. Fix: rm -rf the build directory and reconfigure with the new CC/CXX (this is the exception to software_cmake's delete-only-the-cache advice).

### clang / hipcc build fails on missing or old C++ standard-library headers
The clang driver picked an old GCC installation for libstdc++. Verify with `mpicxx -v` -> `Selected GCC installation:`; choose the GCC toolset deliberately (Tuolumne details in system_tuolumne).

### Tuolumne: GNU + MPI build fails / no GNU mpicc for the chosen gcc
cray-mpich ships a GNU wrapper dir for gnu/11.2 only (checked under 9.0.1 and 9.1.0). Fix: PrgEnv-gnu + gcc-native/11.2.

### Matrix: CUDA rejects the host GCC
The CUDA version caps GCC (CUDA 12.6 supports GCC <= 13): pick GCC for CUDA first, MPI second.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_gcc_recipe` renders the recipe; validator `software_gcc_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `mpi_after_compiler` fails: Load/swap the compiler first, then the MPI module, then export CC/CXX. Then render with `software_gcc_recipe` and validate again.
- `cc_from_mpi_wrapper` fails: export CC=$(which mpicc) CXX=$(which mpicxx). Then render with `software_gcc_recipe` and validate again.
- `tuolumne_gnu_mpich_11_2` fails: Use PrgEnv-gnu + gcc-native/11.2 with cray-mpich. Then render with `software_gcc_recipe` and validate again.

## Self-heal
- When a site's pairing in the recipe disagrees with what the probes show, trust the probes and correct both this table and the system_<machine> capability.

## Self-learn
- After probing a new system, add its row to recipe.sites (and register it with system_save); keep module names in the system capability.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_gcc via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, from the source skill) Tuolumne GNU+MPI: PrgEnv-gnu + gcc-native/11.2 with cray-mpich (only gnu/11.2 wrapper dir exists).
- (undated, from the source skill) Dane dftracer build: GCC 12.1.1 toolchain module + an MVAPICH2 module that auto-selects the matching build.

## Source: dftracer-agents `software-gcc` (verbatim, headings demoted)
_Original description:_ GCC/GNU toolchain knowledge that is system-agnostic - how to find which GCC versions a site offers, pair GCC with an MPI wrapper, switch compilers on an existing build tree, and borrow GCC's C++ headers/libstdc++ for clang. Each fact points back to the system-* skill that holds the site-specific module names. Load for any build that needs GCC/GNU instead of the site default compiler.

#### Scope

This skill is deliberately site-neutral. It records what is true of GCC on any
HPC system and tells you where the site-specific module names live. Never copy
a module name from one system to another - re-derive it with the probes below
and read the matching `system-*` skill.

#### Probing what a site offers (any system)

```bash
module -t avail gcc            # Lmod: every gcc-related module, grouped by modulefile dir
which gcc g++ gfortran         # what is on PATH right now (may NOT be what an MPI wrapper uses)
gcc --version | head -1
module -t avail <mpi-module>   # then list the MPI install's per-compiler wrapper dirs
```

Findings to expect and distinguish:

- There can be MORE THAN ONE family of GCC modules (a vendor/PE family and a
  site toolchain family). They differ in version set and in how MPI is paired.
- The `gcc` on `PATH` in a bare shell is often the newest site toolchain GCC,
  which may have no matching MPI wrapper.
- A GCC version being installed does not mean an MPI build exists for it - see
  the next section.

#### Pairing GCC with MPI

- Cray-style MPI installs one wrapper directory PER compiler family and
  version (`.../<mpi-version>/<fabric>/<family>/<compiler-version>/bin/mpicc`).
  Only the versions actually present there can be used; list the directory
  before choosing a GCC module (`ls .../<fabric>/gnu/`).
- Site-MPI modules (e.g. MVAPICH2 on LC commodity clusters) instead resolve to
  a build matching the currently loaded GCC automatically when the compiler
  module is loaded first.
- Order matters: load/swap the compiler, THEN the MPI module, THEN
  `export CC=$(which mpicc) CXX=$(which mpicxx)` (see
  [[feedback-cc-cxx-mpi-selection]] in memory pointers).

#### Switching compilers on an existing build tree

- CMake pins the compiler in `CMakeCache.txt` and refuses to swap it silently:
  `rm -rf` the build directory first.
- Autotools: re-run `configure` with the new `CC`, and `make clean`.
- A Python venv with compiled wheels built under one compiler should be rebuilt
  rather than mixed.

#### GCC as a header/libstdc++ provider for clang

Clang-based compilers (Cray clang, hipcc, amdclang) locate libstdc++ headers
from an installed GCC toolchain. `mpicxx -v` prints `Selected GCC installation:`
- check it when a clang build fails on missing/old C++ standard-library
  headers, and choose the GCC toolset deliberately rather than inheriting
  whichever was found first. Details and the site's toolset path:
  [[system-tuolumne]].

#### Where the site-specific facts live

| System | GCC/GNU details | Read |
|---|---|---|
| Tuolumne (AMD MI300A, Cray PE, Flux) | Two GCC module families (Cray-PE `gcc-native` 10.3-13.2 and site toolchain `gcc` 10.3.1-13.3.1); bare-shell `gcc` is 13.3.1; cray-mpich ships a GNU wrapper dir for `gnu/11.2` ONLY (checked under both 9.0.1 and 9.1.0), so GNU+MPI means `PrgEnv-gnu` + `gcc-native/11.2` | [[system-tuolumne]] |
| Dane (CPU-only Sapphire Rapids, Slurm) | Site `gcc` 10.3.1-13.3.1; pairing used for dftracer: a GCC 12.1.1 toolchain module plus an MVAPICH2 module that auto-selects the matching build | [[system-dane]] |
| Matrix (H100 + Sapphire Rapids, Slurm) | Same GCC set as Dane; the CUDA version in use caps the usable GCC (CUDA 12.6 supports GCC <= 13), so pick GCC for CUDA first, MPI second | [[system-matrix]] |
| Tioga (AMD GPU, Cray PE) | Default environment is Cray compiler, not GCC; no GNU pairing recorded yet | [[system-tioga]] |
| Containers | Compiler comes from the image, not modules | [[system-container]] |

If the system is not in this table, run the probes above, then register the
system (`system_save`) and add its row here with a link to its `system-*`
skill. Do not invent a pairing: a missing row means "not yet recorded".

#### Related skills

[[software-mpi]], [[software-cmake]], [[software-autotools]],
[[software-rocm]], [[system-detect]]
