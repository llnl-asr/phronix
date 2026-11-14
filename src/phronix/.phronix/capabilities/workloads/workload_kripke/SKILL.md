---
name: workload_kripke
description: Kripke (LLNL Sn transport proxy, C++17 + RAJA/Umpire/CHAI, BLT/CMake superbuild): configure the inner cmake/kripke project, 8 submodules, RAJA extras off, annotation compile flags, functions the cost filter wrongly skips (sweepSubdomain, SweepComm), FINI before Comm::finalize, headers not to annotate, run decomposition and the MPI_Testany polling hot spot. Load for kripke, 'The BLT submodule is not present', 'CAMP submodule not initialized', functions: 0.
---
Cross-references: [[software_cmake]], [[software_papi]], [[software_mpi]], [[system_tuolumne]], [[tools_dftracer]]

# workload_kripke

Converted from dftracer-agents' `workload-kripke` skill (all of its content is under Rules, verbatim with headings demoted).
`workload_kripke_recipe` renders the recipe the skill knows as JSON (predictor); `workload_kripke_check` rules on a proposed recipe or command list (validator).

## Rules

### workload-kripke

Kripke solves the discrete-ordinates (Sn) Boltzmann transport equation
(Kobayashi benchmark 3i). ~5k lines of its own C++ plus RAJA/Umpire/CHAI/BLT
submodules. Annotated/instrumented by dftracer, so it is `workload-*` here
because it is a traced scientific proxy app.

Related: [[system_tuolumne]], [[software_papi]], [[dftracer-annotate-cpp]],
[[tools_dftracer]], [[software_cmake]].

#### Build

**Submodules are mandatory and there are eight of them.** `git submodule
update --init --recursive` before anything; without it CMake fails with
"The BLT submodule is not present." or "CAMP submodule not initialized".

**The top-level `CMakeLists.txt` is a superbuild, not the app.** It wraps the
real project in `ExternalProject_Add(kripke_ep ...)` purely so it can build
the bundled `adiak` first when `ENABLE_CALIPER=On`. With Caliper off (the
default) that layer buys nothing and only hides the build. **Configure the
inner project directly:**

```bash
cmake <src>/cmake/kripke \
  -DKRIPKE_SOURCE_ROOT=<src> \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX \
  -DENABLE_MPI=On -DENABLE_OPENMP=On \
  -DENABLE_TESTS=Off -DENABLE_EXAMPLES=Off \
  -DBLT_SOURCE_DIR=<src>/blt
```

`KRIPKE_SOURCE_ROOT` is required (the inner CMakeLists `FATAL_ERROR`s without
it) and is the only thing the superbuild was passing down.

Two flags worth setting that the project does not set for you: RAJA's
`-DRAJA_ENABLE_EXERCISES=Off -DRAJA_ENABLE_EXAMPLES=Off -DRAJA_ENABLE_TESTS=Off
-DRAJA_ENABLE_BENCHMARKS=Off`. Kripke's own `ENABLE_EXAMPLES=Off` does NOT
reach RAJA, so a default build spends most of its wall time compiling ~100
RAJA tutorial binaries you will never run. Also build the `kripke.exe` target
by name rather than `all`.

`KRIPKE_ARCH` is `Sequential` by default and is silently overridden by whichever
of `ENABLE_OPENMP` / `ENABLE_CUDA` / `ENABLE_HIP` is on. The banner the binary
prints ("Architecture: OpenMP") is the authoritative confirmation.

**CPU (MPI+OpenMP) vs GPU (HIP).** The CPU build is a few minutes and needs
nothing but RAJA. The HIP path additionally requires `ENABLE_CHAI=On`, which
drags in CAMP + Umpire + CHAI compiled for the GPU — a much larger and more
fragile build. Choose CPU unless GPU kernel tracing is the actual goal.

#### Annotation (dftracer, C++ RAII mode)

26 `.cpp` files under `src/`. `clang_annotate_project` handles them in one
pass **only if you pass `compile_flags`** — every Kripke source includes
`KripkeConfig.h` (generated into the build dir) plus RAJA and camp headers,
and a header clang cannot find is a fatal parse error that yields
`functions: 0` with a green status:

```
-std=c++17 -I<src>/src -I<build>/include
-I<src>/tpl/raja/include -I<build>/raja/include
-I<src>/tpl/raja/tpl/camp/include -I<build>/raja/tpl/camp/include
-I<mpi>/include
```

`<build>/include` and `<build>/raja/include` are generated; reusing the
pristine baseline build's copies is fine.

**Exclude the submodules** — `["/tpl/", "/blt/", "/scripts/", "/host-configs/"]`.
Kripke's own tree is 26 files; the full `annotated/` tree is ~1900.

##### The cost filter skips two functions you must add back by hand

The AST cost heuristic scores a function by its own body, so Kripke's two
most important entry points look trivial and are skipped, because each is
just a timer macro plus a dispatch:

| function | file | why it matters |
| --- | --- | --- |
| `Kripke::Kernel::sweepSubdomain` | `Kripke/Kernel/SweepSubdomain.cpp` | the hot sweep kernel — ~50% of solve time |
| `SweepComm::addSubdomain` / `workRemaining` / `readySubdomains` / `markComplete` | `Kripke/ParallelComm/SweepComm.cpp` | the entire parallel-sweep communication layer |

`Kripke::Generate::generateEnergy` is skipped for the same reason while its
five `Generate/*` siblings are annotated. Add all of these with
`clang_insert_line` (`DFTRACER_CPP_FUNCTION()` + a `comp` UPDATE: `"cpu"` for
the kernel/generate ones, `"comm"` for SweepComm).

Genuinely trivial and correctly skipped: `Core/BaseVar.cpp`, `Core/DataStore.cpp`,
`Core/MemoryManager.cpp` (ctors and getters only).

##### FINI must precede `Kripke::Core::Comm::finalize()`

Kripke never calls `MPI_Finalize` directly — it is wrapped in
`Kripke::Core::Comm::finalize()` (`src/Kripke/Core/Comm.h`). The annotator's
teardown anchor and `clang_lint_annotations` rule L3 both match the literal
symbol, so both are satisfied while `DFTRACER_CPP_REGION_END` + `FINI` sit
*after* MPI teardown. Move them above the call by hand:

```cpp
  DFTRACER_CPP_REGION_END(main);
  DFTRACER_CPP_FINI();
  Kripke::Core::Comm::finalize();
```

`usage()` also calls `Comm::finalize()` and then `exit(1)` on the bad-argument
path, so it needs its own `DFTRACER_CPP_FINI()` or that exit loses the trace.
`main`'s early `exit(1)` on `vars.checkValues()` is handled correctly by the
tool.

##### Do NOT annotate Kripke's headers

Unlike apps whose solver lives in headers, Kripke's does not, and its headers
are actively hostile to instrumentation:

* `Kripke/Arch/*.h` (LTimes, LPlusTimes, Scattering, Source, Population,
  SweepSubdomains) are ~2700 lines of pure RAJA *policy typedefs* — no
  executable functions at all.
* `Core/Field.h`, `Core/Set.h`, `Core/VarLayout.h`, `VarTypes.h` are
  per-element accessors called inside RAJA kernels. Instrumenting them would
  emit events per zone per direction per group.
* `Core/Comm.h` is the ONLY header with real work — eight thin `MPI_Allreduce`
  / `MPI_Scan` / `MPI_Init` / `MPI_Finalize` wrappers — and dftracer's brahma
  interception already records every one of them natively as `collective` /
  `comm` events. Annotating it adds a duplicate layer, not coverage.

#### Running

Kripke decomposes space over ranks as `--procs x,y,z`, whose product must equal
the rank count, and `--zones` must divide evenly by it. It writes no data files
of its own, so the only I/O in a trace is startup (`/proc`, `/sys`, libraries)
plus stdout.

Measured shape (MI300A node, 2 nodes x 4 ranks, 23 cores/rank, `OMP_NUM_THREADS=23`):
`--zones 96,96,96 --niter 15 --procs 2,2,2` runs ~45 s and produces ~930k
events with full annotation + PAPI. Scale `niter` for longer runs; wall time is
close to linear in it.

`--zones 16,16,16 --niter 5` at one rank is a good few-second local probe.

##### Event-count shape, and the one hot spot

The parallel sweep is a **polling loop**: `SweepSolver` spins on
`workRemaining()` -> `readySubdomains()` -> `testRecieves()` -> `MPI_Testany`.
At 8 ranks that alone was ~156k events per name and 159k `MPI_Testany` calls —
about 70% of the whole trace. This is real and useful signal (it is exactly
where sweep-efficiency loss shows up), but it dominates the event budget, and
it grows with rank count and with how long any rank waits. If a Kripke trace is
unexpectedly huge, this is why; drop the three `SweepComm`/`ParallelComm`
polling functions before blaming the tracer.

Instrumentation overhead measured with `DFTRACER_ENABLE=0`: ~0.6% on wall time,
with particle counts bit-identical to the pristine baseline.

#### Verification checklist

* banner shows `MPI Enabled: Yes`, `OpenMP Enabled: Yes`, `Architecture: OpenMP`
* `ldd kripke.exe | grep dftracer` shows `libdftracer_core.so`
* run the annotated binary with `DFTRACER_ENABLE=0` and diff the per-iteration
  `particle count=` lines against the pristine build — they must match exactly
* in the trace: `CPP_APP` present AND `sweepSubdomain` present (if the second
  is missing, the cost-filter skip above was not repaired)

## Constraints
- Choose the CPU (MPI+OpenMP) build unless GPU kernel tracing is the goal.
- Annotate only Kripke's 26 src/*.cpp; never its headers or the submodules.
- `workload_kripke_recipe` / `_check` render and check text only.

## Corner cases
- clang_annotate_project without compile_flags: KripkeConfig.h not found -> 'functions: 0' with a green status.
- The cost filter skips sweepSubdomain (~50% of solve time), SweepComm::addSubdomain/workRemaining/readySubdomains/markComplete and Generate::generateEnergy -> add with clang_insert_line (DFTRACER_CPP_FUNCTION() + comp cpu/comm).
- Kripke wraps MPI_Finalize in Kripke::Core::Comm::finalize(): the annotator anchor and lint L3 are satisfied while REGION_END/FINI sit after MPI teardown -> move them above the call; usage() needs its own FINI before Comm::finalize()/exit(1); main's early exit(1) on vars.checkValues() is handled.
- A huge trace is the SweepSolver polling loop (~156k events per name, 159k MPI_Testany at 8 ranks, ~70% of events): drop the three SweepComm/ParallelComm polling functions before blaming the tracer.
- KRIPKE_ARCH banner ('Architecture: OpenMP') is authoritative; the CMake default Sequential is overridden by ENABLE_OPENMP/CUDA/HIP.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_kripke_check`, repair the proposed commands (or the recipe input), then call `workload_kripke_recipe` and `workload_kripke_check` again:
- `source_root`: add -DKRIPKE_SOURCE_ROOT=<src>.
- `superbuild`: configure <src>/cmake/kripke instead of the top-level CMakeLists.
- `raja_extras_off`: add the four -DRAJA_ENABLE_*=Off flags; build kripke.exe by name.
- `submodules`: run git submodule update --init --recursive after the clone.
- `no_header_annotation`: drop header annotate calls.
- `compile_flags_given`: pass the compile_flags from the recipe.
- `exclude_tpl`: exclude /tpl/, /blt/, /scripts/, /host-configs/.
- `procs_given`: add --procs x,y,z with product = ranks.
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
- CPU build via inner cmake/kripke with RAJA extras off, `make kripke.exe`; banner MPI Yes / OpenMP Yes / Architecture OpenMP.
- 2 nodes x 4 ranks x 23 threads (MI300A): `--zones 96,96,96 --niter 15 --procs 2,2,2` ~45 s, ~930k events with full annotation + PAPI; DFTRACER_ENABLE=0 overhead ~0.6%, particle counts bit-identical.
