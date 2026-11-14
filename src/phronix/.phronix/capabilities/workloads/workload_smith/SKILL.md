---
name: workload_smith
description: Smith (LLNL/smith, formerly Serac) 3D implicit thermal-structural FEM on MFEM (C++20, CMake+BLT, MPI): group-gated prebuilt TPLs, codevelop from-source dependency chain, std::format/<format> and SuperLU/STRUMPACK upstream build bugs, no smith driver binary, composable_thermo_mechanics as run target, annotation flags and the hot GetElementVDofs accessor. Load for smith, serac, "no member named 'format' in namespace 'std'", SuperLUSolver errors.
---
Cross-references: [[software_cmake]], [[software_hdf5]], [[software_papi]], [[software_mpi]], [[system_tuolumne]], [[tools_dftracer_utils]], [[workload_laghos]]

# workload_smith

Converted from dftracer-agents' `workload-smith` skill (all of its content is under Rules, verbatim with headings demoted).
`workload_smith_recipe` renders the recipe the skill knows as JSON (predictor); `workload_smith_check` rules on a proposed recipe or command list (validator).

## Rules

### Smith (LLNL) — build, annotate, trace

Smith is a **3D implicit nonlinear thermal-structural simulation code** built on
**MFEM**, formerly named Serac (`LLNL-CODE-805541`, still `readthedocs/serac`,
`codecov/serac`). C++20, CMake + **BLT**, MPI required. Pre-alpha: interfaces
churn, and some targets in `develop` do not compile.

#### RULE 1 — the prebuilt TPL stack is group-gated; plan to build it yourself

`host-configs/<system>-*.cmake` point every TPL at a shared workspace tree owned by a
restricted project group (mode `drwxrws---`). If you are not in that group the
whole stack is `Permission denied` and **every** host-config is unusable as-is.
The host-config is still valuable — read it for the *validated toolchain* and
TPL version pins, then rebuild those TPLs into the session workspace.

#### RULE 2 — use `SMITH_ENABLE_CODEVELOP=ON`; it collapses the dependency stack

Codevelop builds **MFEM, Axom, Tribol, gretl and ContinuationSolvers from the
in-tree submodules** in one CMake project. That reduces the from-source TPL list
to a tractable set:

| TPL | why | notes |
| --- | --- | --- |
| METIS 5.1.0 | MFEM (`MFEM_USE_METIS_5` is hardcoded ON) | `github.com/mfem/tpls` mirror; `make config cc=$CC` |
| ParMETIS 4.0.3 | `PARMETIS_DIR` is a hard `smith_assert_is_directory` | same mirror |
| hypre | MFEM | builds in ~90 s |
| HDF5 | Conduit (serial HDF5 is sufficient) | build from source, never the Cray module |
| camp | hard `FATAL_ERROR` if `CAMP_DIR` unset | needs `-DBLT_SOURCE_DIR=<smith>/cmake/blt` |
| Conduit | hard `FATAL_ERROR` if `CONDUIT_DIR` unset | BLT lives at `<conduit>/src/blt`, **not** `<conduit>/blt` |
| SuperLU_DIST | **not optional** — see RULE 4 | needs ParMETIS + BLAS/LAPACK |

Umpire, RAJA, Sundials, PETSc, Caliper, Adiak, Enzyme, NetCDF are genuinely
optional. STRUMPACK is *nearly* optional — see RULE 5.

Initialise submodules first (`axom` alone is ~277 MB).

#### RULE 3 — Smith needs a C++20 `<format>`, i.e. a modern libstdc++

Smith uses `std::format`. Clang picks up the system libstdc++, which on TOSS4 is
too old. Point the compiler at a GCC 13+ toolset:
`--gcc-toolchain=/opt/rh/gcc-toolset-13/root/usr` in `CMAKE_C_FLAGS` and
`CMAKE_CXX_FLAGS`, plus `-Wl,-rpath,<toolset>/lib/gcc/x86_64-redhat-linux/13`.

**Upstream bug:** ~33 Smith sources use `std::format` **without including
`<format>`** (e.g. `src/smith/infrastructure/logger.cpp`). libstdc++ 13 does not
pull it in transitively, so the build dies at `no member named 'format' in
namespace 'std'`. Fix it *scoped to Smith's own targets* so you do not invalidate
the ccache for MFEM/Axom/Tribol — add to `src/CMakeLists.txt` and
`examples/CMakeLists.txt`:

```cmake
add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-include$<SEMICOLON>format>)
```

#### RULE 4 — SuperLU_DIST is a hard requirement, not an option

`src/smith/numerics/equation_solver.hpp` declares `smith::SuperLUSolver` with
`mfem::SuperLURowLocMatrix` / `mfem::SuperLUSolver` members **outside any
`#ifdef MFEM_USE_SUPERLU`** (unlike the STRUMPACK block right below it, which is
guarded). Without SuperLU_DIST, `smith_numerics` cannot compile.

Because Smith sets `set(MFEM_USE_SUPERLU ON CACHE BOOL "")` — a *cache* set — it
cannot flip an already-cached `OFF`. **Adding `SUPERLUDIST_DIR` to an existing
build dir silently does nothing**; you must configure a fresh build directory.

#### RULE 5 — one unguarded STRUMPACK use blocks every example

`src/smith/physics/solid_mechanics_contact.hpp` constructs a `StrumpackSolver`
for the AMGF filtered-subspace solver with no `#ifdef MFEM_USE_STRUMPACK`. It is
header code, so it breaks **all** examples even ones with no contact. Either
build STRUMPACK (needs ScaLAPACK, ~1 h) or guard it. `filter_solver_` is a
`std::unique_ptr<mfem::Solver>`, so SuperLU_DIST substitutes cleanly:

```cpp
#ifdef MFEM_USE_STRUMPACK
      filter_solver_ = std::make_unique<StrumpackSolver>(filter_solver_print_level, comm);
#else
      filter_solver_ = std::make_unique<SuperLUSolver>(filter_solver_print_level, comm);
#endif
```

#### RULE 6 — there is NO `smith` driver binary; run an example

`src/drivers/CMakeLists.txt` has its `smith_add_executable(... smith_driver ...)`
**commented out upstream**. Uncommenting it does not help: `src/drivers/smith.cpp`
is stale against the current API and fails with 12 × *"no matching constructor
for initialization of `smith::SolidMechanics<p,dim>` / `HeatTransfer<p,dim>`"*.
Do not spend time on it.

Runnable binaries are the **examples** (`build/examples/`):
`composable_thermo_mechanics`, `composable_thermo_mechanics_advanced`,
`composable_solid_mechanics`, `simple_conduction`, `buckling_cylinder`, plus
`bin/partitioner`. `SMITH_ENABLE_BENCHMARKS=ON` does **not** work — BLT cannot
find a gbenchmark submodule and configure fails.

**Best trace/smoke target: `composable_thermo_mechanics`** — a coupled 3D
thermo-mechanics run that matches Smith's actual purpose. It takes no CLI
arguments; size it *in source*:

```cpp
mfem::Mesh::MakeCartesian3D(80, 20, 20, mfem::Element::HEXAHEDRON, 1.0, 0.1, 0.1)  // was 8,2,2
for (int step = 0; step < 5; ++step)                                               // was 2
```
That is ~81 s on 2 nodes × 16 ranks (CPU, MPI-only), a good 1-3 min smoke size.

#### RULE 7 — annotate the EXAMPLE's `main`, not just `src/`

The examples are the entry points, so if you scope annotation to `src/` only,
**no `DFTRACER_CPP_INIT`/`FINI` is emitted anywhere** and every trace file is
written **0 bytes** with the app still exiting `rc=0`. This is silent. Put
`DFTRACER_CPP_INIT` / `REGION_START` immediately **after** the
`smith::ApplicationManager` constructor (that is what calls `MPI_Init`) and
`REGION_END` → `FINI` before the final `return`.

**Annotator trap seen here:** in an entry file the tool inserted
`REGION_END` + `FINI` before a `SLIC_ERROR_ROOT_IF(...)` — a *conditionally*
aborting macro, not a return. Execution continues past it, so the tracer was
finalised before the whole simulation. Always read `main` top-to-bottom and
delete any END/FINI pair that is not immediately before a `return`/`exit`.

#### RULE 8 — compile flags for the clang annotator

Smith sources use quoted project includes (`#include "smith/physics/mesh.hpp"`),
so the annotator needs **`-I <tree>/src`** (the compile-DB entry
`-I<tree>/src/smith/infrastructure/../..` resolves to `<tree>/src/smith` and is
*not* enough). Also add `-isystem <tree>/gretl/src` and the dftracer include dir.
Without them clang emits a fatal "file not found", the brace-insertion safety
pass self-disables, and functions get mis-reported as "trivial". Extract the rest
of the flags from `compile_commands.json` (`CMAKE_EXPORT_COMPILE_COMMANDS=ON`)
rather than hand-writing them — Axom/MFEM/Conduit contribute ~20 `-isystem` paths.

Parsing one Smith `.cpp` costs minutes because of the Axom+MFEM header mass;
expect client-side MCP timeouts and always grep the file before retrying.

#### RULE 9 — measured tracing cost, and the hot accessor

2 nodes × 16 ranks, 80×20×20 hexes, 5 steps, full-feature FUNCTION-mode tracing:

| binary | wall |
| --- | --- |
| pristine | 81 s |
| annotated, `DFTRACER_ENABLE=0` | 82 s (instrumentation ≈ free) |
| annotated, tracing on | 201 s (**2.5×**) |

The overhead is concentrated in one per-element accessor: `GetElementVDofs`
(`numerics/functional/element_restriction.cpp`) was ~61 % of all app events on
rank 0. Pass it to `clang_annotate_file(exclude_functions=[...])` if you need
low-overhead traces.

#### Event inventory actually obtained (2 nodes x 16 ranks, CPU MPI build)

32 app traces = **21,600,641** events; 2 service traces = **48,645** events.

| layer | cat | events | note |
| --- | --- | ---: | --- |
| MPI point-to-point | `p2p` | 14,950,641 | hypre CG halo exchange |
| MPI environment | `env` | 5,625,383 | comm/rank/type queries |
| MPI communicator ops | `comm` | 494,130 | |
| MPI collectives | `collective` | 16,518 | |
| STDIO | `STDIO` | 179,928 | |
| **App annotation** | `CPP_APP` (type 9) | 166,042 | 83 distinct functions fired |
| POSIX | `POSIX` | 121,791 | |
| dftracer metadata | `dftracer` (type 1) | 38,393 | |
| PAPI counters | `papi` (type 11) | 7,815 | |
| node system | `sys` (type 7) | 40,158 | service traces |
| node I/O | `io` (type 7) | 7,038 | service traces |
| node network | `net` (type 7) | 1,242 | service traces |
| **variorum power** | `gpu`, **type 13** | 207 | service traces |

GPU kernel-dispatch / memory-copy events are legitimately **absent** — this is a
CPU-only build with `DFTRACER_HIP_TRACING_ENABLE` undefined. Note that variorum
still reports a `gpu` power category: that is node-level power telemetry, not GPU
kernel tracing.

PAPI: `PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS` all landed, every
sample with `args.multiplex == 0` (**exact**, not scaled) — 4 counters against
this node's 5-counter budget. Read `multiplex` from the compute-node run; a
login-node probe can report a different value.

Annotation liveness: **83 of 249** instrumented sites fired. The unfired ones are
code paths this example does not exercise — Lua/Inlet input parsing
(`*_input.cpp`, `cli.cpp`), Tribol contact, PETSc solvers, trust-region solvers,
mesh-file readers and `StateManager` output (the example builds its problem
programmatically and writes no output).

Reading the traces: `dftracer_stats --report categories` hits the known
"Events Scanned: 0" bug. Use `dftracer_reader --mode lines` and aggregate the
NDJSON. Two schema traps: **`type` is a top-level field**, not under `args`, and
reader output lines may carry a leading `[`/`,` or a trailing `,` — strip them or
a naive `line.startswith('{')` filter silently drops ~50% of the events.

#### Related

[[system_tuolumne]] [[software_cmake]] [[software_papi]] [[dftracer-annotate-cpp]]
[[dftracer-trace-utils]] [[workload_laghos]] (also MFEM-based)

## Constraints
- Never use the group-gated prebuilt TPL tree; rebuild TPLs into the session workspace.
- Patch the <format> include scoped to Smith's own targets (src/, examples/) so the MFEM/Axom/Tribol ccache stays valid.
- SuperLU_DIST added to an existing build dir does nothing: configure a fresh build directory.
- `workload_smith_recipe` / `_check` render and check text only.

## Corner cases
- `no member named 'format' in namespace 'std'` -> ~33 sources use std::format without <format> -> add_compile_options(-include format) in src/ and examples/ CMakeLists.
- smith_numerics does not compile without SuperLU_DIST (SuperLUSolver unguarded in equation_solver.hpp); MFEM_USE_SUPERLU is a cache set, so a stale OFF sticks.
- Every example fails without STRUMPACK (unguarded StrumpackSolver in solid_mechanics_contact.hpp) -> guard with #ifdef MFEM_USE_STRUMPACK, else SuperLUSolver.
- Annotating only src/ gives no INIT/FINI: every trace 0 bytes with rc=0 (silent) -> annotate the example's main.
- Annotator put REGION_END+FINI before SLIC_ERROR_ROOT_IF (a conditional abort, not a return) -> delete END/FINI pairs not immediately before return/exit.
- Without -I <tree>/src clang emits a fatal 'file not found', the brace pass self-disables and functions are mis-reported trivial.
- dftracer_stats 'Events Scanned: 0' bug -> dftracer_reader --mode lines; strip leading [ / , and trailing , (else ~50% of events dropped).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_smith_check`, repair the proposed commands (or the recipe input), then call `workload_smith_recipe` and `workload_smith_check` again:
- `codevelop_on`: add -DSMITH_ENABLE_CODEVELOP=ON.
- `gcc13_toolchain`: add --gcc-toolchain=/opt/rh/gcc-toolset-13/root/usr to C/CXX flags and the gcc 13 rpath.
- `superlu_dist`: build SuperLU_DIST, pass -DSUPERLUDIST_DIR, use a fresh build dir.
- `no_benchmarks`: remove SMITH_ENABLE_BENCHMARKS=ON.
- `no_smith_driver`: run build/examples/composable_thermo_mechanics instead.
- `no_cray_hdf5`: build serial HDF5 from source.
- `no_group_tpls`: drop -C host-configs/...; pass session TPL prefixes.
- `annotate_src_include`: add -I <tree>/src -isystem <tree>/gretl/src and the dftracer include to compile_flags.
- `input` (inconclusive): pass the proposed command list.
Attempts follow measured progress; the same failure twice stops the loop for the user.

## Self-heal
On a failed build or run, match the error to Corner cases and LESSONS.md (`lesson_search` the error text first), apply the fix
through the recipe, rerun. If the recipe or a rule here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: a new procedure for this workload verified by hand is added to this capability
(`capability_update`), new software or a new system met on the way becomes its own `software_<x>` / `system_<x>`; each new
error -> cause -> fix goes to LESSONS.md, each verified recipe to WORKED.md and What works.

## What works
- Codevelop build with METIS 5.1.0, ParMETIS 4.0.3, hypre, serial HDF5, camp, Conduit and SuperLU_DIST from source, gcc-toolset-13, the <format> and STRUMPACK guards (Tuolumne, CPU MPI).
- composable_thermo_mechanics at 80x20x20 hexes, 5 steps, 2 nodes x 16 ranks: 81 s pristine, 82 s annotated DFTRACER_ENABLE=0, 201 s traced; 21,600,641 app events + 48,645 service events; PAPI 4 counters exact (multiplex 0); 83 of 249 sites fired.
