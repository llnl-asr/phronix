---
name: workload_minibude
description: miniBUDE (UoB-HPC molecular-docking mini-app, C++/CMake, many parallel-model backends) - the HIP backend on MI300A, the two annotation traps unique to its single-TU/header-only layout, run sizing, and what a full-feature dftracer trace of it actually contains. Load for any miniBUDE build, annotation or tracing session; bude, fasten_main, "Only Release or Debug is supported", "Unknown argument -I", missing CPP_APP spans.
---
Cross-references: [[system_tuolumne]], [[software_rocm]], [[software_papi]], [[software_cmake]], [[dftracer_annotate_cpp]], [[tools_dftracer_utils]]

# workload_minibude

Bristol University Docking Engine mini-app: one energy-evaluation kernel (`fasten_main`) run repeatedly over a fixed pose
deck. CMake, `-DMODEL=<backend>` picks exactly one of
`serial;omp;ocl;std-indices;std-ranges;hip;cuda;kokkos;sycl;acc;raja;tbb;thrust`. Converted from dftracer-agents'
`workload-minibude` skill; `workload_minibude_recipe` renders the recipe, `workload_minibude_check` rules on a command list.

**It is NOT an MPI application.** There is no `mpi.h`, no `MPI_` symbol anywhere in `src/`. A "2-node run" means N independent
single-process instances launched across N nodes. **MPI trace categories are legitimately ABSENT: never report that as a defect.**

## Rules
### Build (HIP backend, AMD MI300A / gfx942)
The HIP model's only required flag is the compiler; it does NOT set an offload arch, so pass one explicitly or hipcc guesses
from the *build* host (a GPU-less login node guesses wrong).
```
-DCMAKE_BUILD_TYPE=Release          # MANDATORY
-DMODEL=hip
-DCMAKE_CXX_COMPILER=<rocm>/bin/hipcc
-DCXX_EXTRA_FLAGS=--offload-arch=gfx942
```
- **`CMAKE_BUILD_TYPE` must be `Release` or `Debug`, nothing else.** `CMakeLists.txt` has a hard
  `FATAL_ERROR: Only Release or Debug is supported`. `session_configure` / `session_build_annotated` default to
  `RelWithDebInfo`, so **every** call must pass `-DCMAKE_BUILD_TYPE=Release` in `extra_cmake_flags` (a later `-D` wins).
- Prefer HIP over `omp` on an AMD GPU system: it is what produces GPU events.

### Linking dftracer into it
miniBUDE has no `find_package`, so `CMAKE_PREFIX_PATH` injection does nothing. Wire it through the project's own escape
hatches, using only single-token `-D` values:
```
-DCMAKE_CXX_FLAGS=-I<dftracer>/include
-DCXX_EXTRA_LIBRARIES=<dftracer>/lib64/libdftracer_core.so
-DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath,<dftracer>/lib64
-DCXX_EXTRA_FLAGS=--offload-arch=gfx942
```
`cmake --install` **strips the rpath** ("Set runtime path ... to \"\""). Run the binary from `build_ann/`, not
`install_ann/bin/`, or re-add `LD_LIBRARY_PATH`.

### Annotation: two traps unique to this app
miniBUDE is **one translation unit**. `src/main.cpp` is the only `.cpp`; the entire backend lives in `src/<model>/fasten.hpp`.

**Trap 1: `main()` does all its work AFTER the tracer is shut down.** `main` ends with
`return run<USE_PPWI>(params, wgsizes, ppwis) ? ... : ...;`. `clang_annotate_project` correctly follows the
"REGION_END -> FINI -> return" rule and inserts both **before** that line, which puts deck loading, every kernel launch and
validation *after* `DFTRACER_CPP_FINI()`. The trace still looks plausible (metadata, POSIX, GPU events all appear) but contains
**no app-annotation span for the actual computation**. Fix: hoist the call out of the return statement:
```cpp
  const bool dft_run_ok = run<USE_PPWI>(params, wgsizes, ppwis);
  DFTRACER_CPP_REGION_END(main);
  DFTRACER_CPP_FINI();
  return dft_run_ok ? EXIT_SUCCESS : EXIT_FAILURE;
```
Generalises: whenever `main`'s last statement is `return <call-that-does-the-work>(...)`, the annotator's correct macro
ordering silently traces nothing. Check the line immediately following `DFTRACER_CPP_FINI()` on every annotated `main`.

**Trap 2: the interesting functions are in a header, so the annotator skips them.** `clang_annotate_project` only discovers
`.c/.cpp/.cxx/.cc`, and the general rule is "never annotate headers". Here the rule's reason (ODR / multiple TUs) does not apply:
`fasten.hpp` is included by exactly one TU. Add RAII guards by hand to the **host-side** methods only:
- `IMPL_CLS::fasten(...)`: the whole GPU phase (alloc, launch loop, memcpy, free)
- `IMPL_CLS::enumerateDevices()`

Do **not** touch `__global__ fasten_main` (device code) or `checkError`. No `#include <dftracer/dftracer.h>` is needed in the
header: `main.cpp` includes dftracer before it includes `<model>/fasten.hpp`. Also annotate by hand in `main.cpp` (the cost
filter skips them): `readNStruct<T>` (the deck reader: tag `comp=io` and `path`) and `run<Ns...>`.

With both traps fixed, an annotated run yields these `CPP_APP` spans per process: `main, run, parseParams, readNStruct x4,
evaluate, fasten, enumerateDevices, selectDevice, validate, dumpResults, showHumanReadable`: 14 spans/rank.

### Run sizing
`-i N` gives **N + 2** kernel launches (`totalIterations() = iterations + warmupIterations(2)`), each a full `fasten_main`
dispatch. At `-p 8 -w 64` on MI300A one launch is ~13.2 ms:

| target wall time | flag |
| --- | --- |
| ~15 s | `-i 1000` |
| ~70 s | `-i 5000` |
| ~130 s | `-i 10000` |

`-p`/`-w` accept CSV lists and auto-tune every combination: a 2-element `-p` list doubles the wall time. Pass `-o <file>` to
make it write the energies (~512 KB) so the run exercises POSIX `write`; without it miniBUDE writes no data file at all. Point
`-o` at the session's Lustre `dataset/` dir. Deck lives at `data/bm1` (65 536 poses) / `data/bm2`; pass it with `--deck <dir>`.
The deck path must be the **annotated** tree's copy when running the annotated binary.

## Constraints
What a maximal dftracer trace of miniBUDE contains. Measured: 2 nodes x 1 process, HIP backend, `-i 5000`, dftracer built with
HIP + PAPI + variorum + hwloc; 122 362 app events + 39 010 service events.

| layer | category | per rank | note |
| --- | --- | --- | --- |
| app annotation | `CPP_APP` | 14 | only after fixing both traps above |
| GPU kernels | `KERNEL_DISPATCH` | ~5 000 | = `-i` + 2, plus ~3 rocclr copy kernels |
| GPU runtime | `HIP_RUNTIME_API` | ~10 000 | 2 per launch (launch + sync) |
| GPU copies | `MEMORY_COPY` | 6 | 5 H2D allocations + 1 D2H result |
| GPU scratch | `SCRATCH_MEMORY` | 1 | |
| GPU page migration | `PAGE_MIGRATION` | **0** | expected: explicit `hipMalloc`, no managed memory |
| hw counters | `papi` | ~670 | one sample per `DFTRACER_PAPI_SAMPLE_INTERVAL_MS` |
| POSIX | `POSIX` | ~1 350 | mostly ROCm/hwloc sysfs probing + the `-o` write |
| STDIO | `STDIO` | ~38 500 | dominated by ROCm runtime `fopen/fgets/fclose` on sysfs, NOT the app |
| MPI | - | **0** | expected: miniBUDE has no MPI |
| HDF5 | - | **0** | expected: miniBUDE has no HDF5 |

Node-level (`dftracer_service`, one daemon per node, `type 7` + `type 13`): `sys` (cpu/mem), `io` (per-block-device), `net`
(per-NIC), and `gpu`/`power` (`type 13`, variorum) carrying `socket_<n>.GPU_<n>` watts.

STDIO dwarfing everything is normal here and is *not* app I/O: it is the ROCm runtime enumerating sysfs at init. Do not read it as
a miniBUDE I/O bottleneck. The recipe/check tools render and check text only.

## Corner cases
Tooling notes hit on this app:
- **`extra_cmake_flags` cannot carry a multi-token `-D` value.** A space splits it into separate cmake args
  (`CMake Error: Unknown argument -I...`); a `;` truncates the whole command at the shell (`source directory ... does not contain
  CMakeLists.txt`). Express everything as single-token `-D` flags: that is why the include goes in `CMAKE_CXX_FLAGS` and the rpath
  in `CMAKE_EXE_LINKER_FLAGS` rather than both in `CXX_EXTRA_FLAGS`.
- **`session_build_annotated` needs `build_subdir="source"`** for the standard `annotated/source/` layout, or it points cmake at
  `annotated/` and reports the misleading "does not appear to contain CMakeLists.txt".
- **`clang_syntax_check` is useless on this project**: it hardcodes `g++ -std=c++14` with no way to pass `-D` or a standard, so it
  fails on `std::optional`, structured bindings and the undefined `MODEL`/`IMPL_CLS` macros. None of those errors are annotation
  defects. The authoritative check is `session_build_annotated` itself. `clang_lint_annotations` works fine and should still be run.
- No MPI/HDF5 categories in the trace: expected, not a defect.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_minibude_check`, repair the proposed commands, then call `workload_minibude_recipe` and the check again:
- `build_type_release` / `no_relwithdebinfo`: pass `-DCMAKE_BUILD_TYPE=Release` in every configure / `extra_cmake_flags`.
- `offload_arch`: add `-DCXX_EXTRA_FLAGS=--offload-arch=gfx942`.
- `single_token_d`: split into single-token `-D` flags (include in CMAKE_CXX_FLAGS, lib in CXX_EXTRA_LIBRARIES, rpath in CMAKE_EXE_LINKER_FLAGS).
- `no_prefix_path`: drop CMAKE_PREFIX_PATH; use the escape-hatch flags above.
- `no_install_bin`: run from `build_ann/` (or re-add LD_LIBRARY_PATH).
- `no_mpi_launch`: launch independent single-process instances.
- `deck_given`: add `--deck <tree>/data/bm1` (the annotated tree's copy for the annotated binary).
- `input` (inconclusive): pass the command list. The same failure twice stops the loop for the user.

## Self-heal
On a failed build or a trace missing CPP_APP spans, match the error to Corner cases, Rules (traps) and LESSONS.md
(`lesson_search` the error text first); if the recipe or a rule here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: another backend (omp, cuda, kokkos ...) or system verified by hand is added here
(`capability_update`); new software met on the way becomes its own `software_<x>`. Each new error -> cause -> fix goes to
LESSONS.md, each verified recipe to WORKED.md.

## What works
- MI300A APU, HIP backend: `valid: true`, `max_diff_%: 0.008`, ~3780 GFLOP/s at `-p 8 -w 64`.
- 2 nodes x 1 process, `-i 5000`, both traps fixed: 14 CPP_APP spans/rank, ~5 000 KERNEL_DISPATCH, 122 362 app + 39 010 service events.
