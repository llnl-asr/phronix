---
name: software_ygm
description: YGM (github.com/llnl/ygm), LLNL's header-only C++20 async MPI messaging library, annotated with dftracer: include <dftracer/dftracer.h> in every annotated header (split .hpp/.ipp), manual annotation of .ipp files (clang_extract_functions returns 0), linking dftracer through a manual IMPORTED target (-DDFTRACER_ROOT), PrgEnv-gnu + gcc-native/11.2 instead of Cray-clang 20 (spdlog/fmt consteval error), from-source dftracer with DFTRACER_ENABLE_MPI=ON / CRAYMPICH / BRAHMA_MPI_VERSION=900001 built with the SAME MPI wrapper, and the test_comm.cpp smoke test. Load for YGM builds/annotation, or on DFTRACER_CPP_* undefined inside ygm detail headers, 0 functions from clang_extract_functions on comm.ipp, `consteval` not a constant expression in fmt under Cray-clang, undefined dftracer symbols at link, or both libmpi_cray and libmpi_gnu_112 in one process. Benchmark runs live in workload_ygm_bench.
---
Cross-references: [[workload_ygm_bench]] [[workload_ygm]] [[software_mpi]] [[software_cmake]] [[software_gcc]] [[system_tuolumne]] [[tools_dftracer]] [[dftracer_annotate_cpp]] [[dftracer_build]] [[capability_builder]]

# software_ygm

Converted from dftracer-agents skill `software-ygm`. Tools: `software_ygm_recipe` (predictor) and `software_ygm_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- YGM is header-only, CMake, C++20 required (not C++17: Boost 1.87 and spdlog/fmt use C++20). Boost, Cereal, spdlog are auto-fetched by FetchContent. `YGM_BUILD_TESTS=ON` builds the CTest suite under test/.
- Add `#include <dftracer/dftracer.h>` right after `#pragma once` in every annotated header (collective.hpp, comm.ipp, comm_router.hpp, comm_environment.hpp, mpi.hpp) instead of relying on include order; YGM has multiple test entry points (test_comm.cpp, test_comm_2.cpp, test_barrier.cpp, ...).
- If relying on include order: the entry .cpp must include <dftracer/dftracer.h> BEFORE <ygm/comm.hpp> (CP9), or DFTRACER_CPP_* macros in transitively included .ipp/detail headers are undefined.
- clang_extract_functions / clang_annotate_file return 0 functions (not an error) for .ipp files defining Class::method of a class declared in a sibling .hpp (no -I to resolve <ygm/...>): annotate by hand with the same Rule 0 / comp= criteria, verify with a real compiler + clang_lint_annotations.
- YGM's CMakeLists.txt does not link dftracer: add a manual IMPORTED target for libdftracer_core.so, link it into the `ygm` interface target, driven by -DDFTRACER_ROOT=<dftracer prefix>. The prerelease wheel's dftracer-config.cmake is broken.
- On Tuolumne use PrgEnv-gnu + gcc-native/11.2 + the cray-mpich GNU wrapper (/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/mpicc, mpicxx): Cray-clang 20.1.6 fails on FetchContent'd spdlog/fmt (`consteval` not a constant expression). `rm -rf build_ann` before switching compilers on an existing tree.
- The prebuilt/prerelease dftracer wheel has no MPI (ldd libdftracer_core.so shows no MPI libs): fine for FUNCTION-mode C++ tracing; for MPI-IO interception build from source with DFTRACER_CMAKE_ARGS `-DDFTRACER_ENABLE_MPI=ON -DDFTRACER_MPI_IMPL=CRAYMPICH -DBRAHMA_MPI_VERSION=900001`.
- Build dftracer with the SAME compiler/MPI wrapper as the annotated app; mixing Cray-clang MPI and PrgEnv-gnu loads libmpi_cray.so.12 and libmpi_gnu_112.so.12 into one process (double-free-at-exit risk). Verify with `ldd libdftracer_core.so | grep mpi`.
- Nested layout annotated/source/CMakeLists.txt: call session_build_annotated with build_subdir="source".
- Smoke test: test/test_comm.cpp single process; expect CPP_APP events (post_new_irecv, check_completed_sends, local_process_incoming, barrier_reduce_counts, priv_barrier, comm_setup) plus POSIX and dftracer init/metadata (194 events in the recorded run).
- ygm-bench running/scaling (DFTRACER_CPP_INIT/FINI, hot-loop over-annotation, MPI_Iallreduce rank-density collapse, irecv buffer OOM, >=10-min scaled config) belongs to workload_ygm_bench, not here.

## Constraints
- Facts discovered on Tuolumne (Cray PE, cray-mpich 9.0.1, gcc-native 11.2 / GCC 11.2.1); other systems need their own matching toolchain.
- YGM is software (annotated/instrumented), not a workload; ygm-bench is the workload.

## Corner cases
### DFTRACER_CPP_* undefined inside ygm/detail/*.ipp
Cause: dftracer.h included after <ygm/comm.hpp> in some entry .cpp. Fix: include dftracer.h in every annotated header after #pragma once.

### clang_extract_functions returns 0 functions for comm.ipp
Cause: out-of-line Class::method definitions with unresolved <ygm/...> includes. Fix: manual annotation, verify with compiler + clang_lint_annotations (2026-08-04 lesson log).

### `consteval` ... is not a constant expression in fmt (Cray-clang 20.1.6)
Cause: FetchContent'd spdlog/bundled fmt vs Cray-clang 20. Fix: PrgEnv-gnu + gcc-native/11.2 + GNU cray-mpich wrappers; rm -rf build_ann first.

### Undefined dftracer symbols when linking annotated YGM tests
Cause: YGM CMake has no dftracer knowledge; packaged dftracer-config.cmake broken. Fix: IMPORTED target via -DDFTRACER_ROOT linked into ygm.

### Both libmpi_cray.so.12 and libmpi_gnu_112.so.12 loaded; crash at exit
Cause: dftracer built with Cray-clang MPI, app with PrgEnv-gnu. Fix: rebuild dftracer with the app's MPI wrapper; ldd | grep mpi.

### session_build_annotated ignores build_subdir
Cause: wiring bug (fixed) where build_subdir was honored only by custom_build_cmd for cmake/autotools/meson. Fix: use a fixed dftracer-agents; pass build_subdir="source".

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_ygm_recipe` renders the recipe; validator `software_ygm_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `ygm_no_cray_clang` fails: module load PrgEnv-gnu gcc-native/11.2 and use the cray-mpich GNU mpicc/mpicxx; rm -rf build_ann first. Then render with `software_ygm_recipe` and validate again.
- `ygm_cxx20` fails: Use -DCMAKE_CXX_STANDARD=20 (or leave YGM's default). Then render with `software_ygm_recipe` and validate again.
- `dftracer_mpi_impl_craympich` fails: Add -DDFTRACER_MPI_IMPL=CRAYMPICH -DBRAHMA_MPI_VERSION=900001 to DFTRACER_CMAKE_ARGS. Then render with `software_ygm_recipe` and validate again.
- `brahma_mpi_version` fails: Add -DBRAHMA_MPI_VERSION=900001. Then render with `software_ygm_recipe` and validate again.
- `verify_single_mpi_runtime` fails: Run ldd <prefix>/lib/libdftracer_core.so | grep mpi and confirm it matches the app's MPI. Then render with `software_ygm_recipe` and validate again.
- `annotated_build_links_dftracer` fails: Pass -DDFTRACER_ROOT=<dftracer prefix> to the annotated cmake configure. Then render with `software_ygm_recipe` and validate again.

## Self-heal
- After any compiler switch, wipe build_ann and re-run ldd on libdftracer_core.so and the test binary to confirm one MPI runtime.

## Self-learn
- Record new YGM header/annotation patterns and toolchain combinations that build cleanly, with system and versions.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_ygm via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, Tuolumne) PrgEnv-gnu + gcc-native/11.2 + cray-mpich 9.0.1 GNU mpicc/mpicxx, C++20, dftracer.h in each annotated header, IMPORTED dftracer target via -DDFTRACER_ROOT: test_comm.cpp smoke produced 194 events incl. CPP_APP comm/collective/barrier events.

## Source: dftracer-agents `software-ygm` (verbatim, headings demoted)
_Original description:_ Build/annotation caveats for YGM (github.com/llnl/ygm) — LLNL's header-only C++ MPI messaging library — discovered on Tuolumne (Cray PE). YGM is annotated/instrumented by dftracer (software-* naming, not workload-* — see [[feedback-software-vs-workload-naming]]); ygm-bench is the benchmark workload that exercises it.

#### What YGM is

`github.com/llnl/ygm` — a header-only C++ MPI messaging/communication
library (async, active-message style). CMake build system, C++20 required
(not C++17 — YGM's dependencies, especially Boost 1.87 and spdlog/fmt, use
C++20 features). Dependencies (Boost, Cereal, spdlog) are auto-fetched via
CMake `FetchContent` during configure — no manual dependency install needed.
Optional `YGM_BUILD_TESTS=ON` builds the CTest suite under `test/`.

`github.com/llnl/ygm-bench` is the companion benchmark suite that exercises
YGM as a library — treat it as the workload driven by this software, the same
way an MPI application is the workload driven by [[software-mpi]].

#### Annotation: header-only + split .ipp implementation needs care

YGM's implementation is split: `include/ygm/comm.hpp` declares the `comm`
class, `include/ygm/detail/comm.ipp` (included at the bottom of comm.hpp)
defines its method bodies out-of-line. Same pattern for
`collective.hpp`/`comm_router.hpp`/`mpi.hpp`/`comm_environment.hpp`.

- **Include order matters** (CP9 in [[dftracer-annotation-lessons]]): the
  entry `.cpp`'s `#include <dftracer/dftracer.h>` must come BEFORE
  `#include <ygm/comm.hpp>`, or every DFTRACER_CPP_* macro used inside the
  transitively-included `.ipp`/detail headers is undefined at parse time.
- **Better fix, used in this session**: don't rely on include order at all —
  add `#include <dftracer/dftracer.h>` directly to each annotated header
  (`collective.hpp`, `comm.ipp`, `comm_router.hpp`, `comm_environment.hpp`,
  `mpi.hpp`), right after `#pragma once`. This makes each header
  self-contained regardless of what includes it in what order, and matters
  because YGM has MULTIPLE test `.cpp` entry points (`test_comm.cpp`,
  `test_comm_2.cpp`, `test_barrier.cpp`, ...) — fixing include order in only
  ONE entry point leaves every other TU broken.
- `clang_extract_functions`/`clang_annotate_file` return 0 functions (not an
  error) for `.ipp` files that define `Class::method(...)` for a class
  declared in a sibling `.hpp` — no `-I` param to resolve `<ygm/...>` include
  paths. Manual annotation fallback required (same Rule 0 / comp= criteria
  applied by hand, verified via a real compiler + `clang_lint_annotations`).
  See [[dftracer-annotation-lessons]] LESSONS_LOG.md 2026-08-04.

#### Build: CMakeLists.txt does not link dftracer by default

Annotating source files with `#include <dftracer/dftracer.h>` does NOT wire
the build to find/link `libdftracer_core.so` — YGM's `CMakeLists.txt` has no
knowledge of dftracer. Add a manual `IMPORTED` target (the packaged
`dftracer-config.cmake` from the prerelease wheel is broken — see
[[tools-dftracer]] "Prebuilt prerelease wheel's CMake package is broken") and
link it into the `ygm` interface target, driven by a `-DDFTRACER_ROOT=...`
flag pointing at the dftracer install prefix.

#### Build: Cray-clang 20 vs spdlog/fmt — use PrgEnv-gnu

YGM's FetchContent'd spdlog (bundled fmt) fails to compile under Cray-clang
20.1.6 with a `consteval`-not-constant-expression error. Switch to
`PrgEnv-gnu` + `gcc-native/11.2` + the matching cray-mpich GNU wrapper
(`/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/mpicc`/`mpicxx`) — GCC 11.2.1
compiles cleanly. Full detail in [[system-tuolumne]]. `rm -rf build_ann`
before switching compilers on an existing CMake build tree.

#### Smoke test

`test/test_comm.cpp` is a good minimal single-process smoke-test entry
point — confirmed producing real `CPP_APP`-category trace events from the
annotated comm/collective/barrier functions (`post_new_irecv`,
`check_completed_sends`, `local_process_incoming`, `barrier_reduce_counts`,
`priv_barrier`, `comm_setup`, etc.) plus `POSIX` and `dftracer` init/metadata
events. 194 total events on a single-rank run — confirms FUNCTION-mode
tracing works end-to-end for this library without needing dftracer's own
MPI-IO interception (the prerelease wheel has none linked in — see
[[tools-dftracer]]).

#### ygm-bench: the traced benchmark, not part of this skill

`ygm-bench` (github.com/llnl/ygm-bench) is the traced BENCHMARK/workload that
exercises YGM — same role IOR plays for [[software-hdf5]]/[[software-mpi]].
Building it against this session's annotated YGM tree, its own
`DFTRACER_CPP_INIT`/`FINI` requirement, the hot-loop over-annotation +
selective-aggregation fix, the `MPI_Iallreduce` rank-density collapse, irecv
buffer OOM tuning, and the confirmed >=10-minute scaled-run config all live in
**[[workload-ygm-bench]]** — load that skill for anything about running or
scaling ygm-bench. This skill (`software-ygm`) stays scoped to the YGM
library itself: its own annotation/build/smoke-test caveats.

#### Build: from-source dftracer, and matching its MPI ABI to YGM's own toolchain

The prebuilt/prerelease dftracer wheel has NO MPI support compiled in
(`ldd libdftracer_core.so` shows zero MPI libs) — fine for FUNCTION-mode
C++ tracing alone but insufficient if MPI-IO interception is ever needed.
For a from-source build, pass `DFTRACER_ENABLE_MPI=ON`,
`DFTRACER_MPI_IMPL=CRAYMPICH`, `BRAHMA_MPI_VERSION=900001` via
`DFTRACER_CMAKE_ARGS`, and **build dftracer itself with the SAME compiler/MPI
wrapper as the annotated app** (see [[software-mpi]] and
[[system-tuolumne]]). Building dftracer with Cray-clang+MPI while the app is
built with `PrgEnv-gnu` links two different MPI runtimes
(`libmpi_cray.so.12` AND `libmpi_gnu_112.so.12`) into the same process — a
documented double-free-at-exit crash risk, not just an inefficiency. Verify
with `ldd libdftracer_core.so | grep mpi` before trusting a from-source
build. See [[tools-dftracer]] for the prebuilt-vs-source decision and the
czgitlab source URL.

#### Session layout note

The repo is nested as `annotated/source/CMakeLists.txt` (matching the
top-level `source/` tree), so `session_build_annotated` needs
`build_subdir="source"` — this exposed and got a real fix for a
`session_build_annotated` wiring bug where `build_subdir` was silently
ignored for cmake/autotools/meson (only the `custom_build_cmd` escape hatch
honored it before the fix, in
`src/dftracer_agents/mcp_tools/tools/session/session_tools.py`). See
[[dftracer-annotation-lessons]] LESSONS_LOG.md.

#### Related

- [[workload-ygm-bench]] — LLNL's ygm-bench (github.com/llnl/ygm-bench), the
  traced benchmark that exercises this annotated tree: build steps, hot-loop
  over-annotation + selective-aggregation fix, MPI_Iallreduce rank-density
  collapse, irecv buffer OOM tuning, confirmed scaled-run config.
- [[software-mpi]] — MPI-IO/ROMIO, Cray MPICH ABI-matching details.
- [[system-tuolumne]] — Cray-clang20/spdlog-fmt compiler pitfall, PrgEnv-gnu recipe.
- [[tools-dftracer]] — prebuilt-vs-source dftracer decision, czgitlab source URL.
