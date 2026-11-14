---
name: software_cmake
description: CMake build system: detection (top-level CMakeLists.txt, project(), option(), find_package CONFIG vs MODULE vs pkg-config), the session_configure / session_build_install / session_build_annotated flow, dftracer injection through CMAKE_PREFIX_PATH, and stale-cache repair. Load for any project whose top level is CMakeLists.txt, or on 'Could not find a package configuration file provided by dftracer', a silently ignored -D option, or a stale CMakeCache.txt pointing at a deleted compiler/prefix.
---
Cross-references: [[software_autotools]] [[software_meson]] [[software_pip]] [[software_gcc]] [[tools_dftracer]] [[system_tuolumne]] [[capability_builder]] [[software_ygm]] [[software_flux_fiction]]

# software_cmake

Converted from dftracer-agents skill `software-cmake`. Tools: `software_cmake_recipe` (predictor) and `software_cmake_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Read the project's `option(...)` declarations before calling session_configure: CMake silently ignores an unrecognised `-D` flag instead of erroring.
- Check how each dependency is found before assuming `-DCMAKE_PREFIX_PATH=<prefix>` is enough: CONFIG mode (`<Name>Config.cmake`), MODULE mode (`Find<Name>.cmake`) or pkg-config (`pkg_check_modules`). dftracer ships CMake config files but no `.pc` file: `find_package(dftracer CONFIG)` works, `pkg_check_modules(dftracer)` does not. Exception: the prerelease/compose wheel's CONFIG package is broken (see Constraints and tools_dftracer).
- Configure / build through the MCP tools: `session_configure(run_id, extra_cmake_flags=...)` then `session_build_install(run_id, jobs=<n>)`; the annotated tree with `session_build_annotated(run_id, extra_cmake_flags=...)`.
- `session_configure` runs `cmake -S source -B build -DCMAKE_INSTALL_PREFIX=install -DCMAKE_BUILD_TYPE=RelWithDebInfo <extra_cmake_flags>`.
- `session_build_annotated` appends `-DCMAKE_PREFIX_PATH=<dftracer_install_prefix>` itself once `session_install_dftracer` ran: do not pass it again.
- `session_build_install` runs `make -j<jobs>` then `make install` in `build/` (or `build_ann/`): the Makefile generator, not Ninja, by default.

## Constraints
- Lessons are per (system, dependency) pair, not universal: tag each with where it was observed; site-specific halves go to the system_<machine> capability.
- Project-specific CMakeLists.txt quirks belong to that project's workload_<app> capability (e.g. h5bench's to workload_h5bench), not here.
- Reconciled with tools_dftracer (newer, 2026-11-13): for the prebuilt prerelease / dftracer-compose install, `find_package(dftracer CONFIG REQUIRED)` is BROKEN (dftracer-targets-release.cmake hardcodes the wheel build machine's `/project/build/...` IMPORTED_LOCATION and dftracer-config.cmake requires brahma, which the wheel does not ship). There, link the install directly (`-I<pkg>/include -L<pkg>/lib64 -ldftracer_core`, as session_build_annotated does) or define a manual IMPORTED target. The CONFIG path holds only for a dftracer built from source into a prefix.
- tools_dftracer (2026-11-13) mentions a generated `.pc` for the composed install; the source-built install ships none. Until verified, keep finding dftracer without pkg-config (rule no_pkgconfig_dftracer) and record which install was used.

## Corner cases
### Stale `CMakeCache.txt` referencing a deleted compiler or prefix
Re-running session_configure reconfigures in place, but a corrupted cache keeps the old compiler/prefix. Fix: delete `build/CMakeCache.txt` only, not the whole build tree, then configure again.

### `pkg_check_modules(dftracer)` fails while `find_package(dftracer CONFIG)` works
dftracer installs CMake config files but no pkg-config `.pc` file. Use the CONFIG path (CMAKE_PREFIX_PATH / dftracer_DIR).

### `The imported target dftracer_core references the file /project/build/.../libdftracer_core.so... does not exist` or `brahma_DIR` not found
The prerelease wheel's packaged CMake config is not relocatable and requires brahma (confirmed 2026-08-04 on YGM, again 2026-11-13 on 2.2.0.post57.dev0). Fix: skip find_package(dftracer); `add_library(dftracer_core_imported SHARED IMPORTED)` with IMPORTED_LOCATION ${DFTRACER_ROOT}/lib64/libdftracer_core.so and INTERFACE_INCLUDE_DIRECTORIES ${DFTRACER_ROOT}/include, or plain -I/-L/-ldftracer_core. See tools_dftracer.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_cmake_recipe` renders the recipe; validator `software_cmake_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_pkgconfig_dftracer` fails: Find dftracer with find_package(dftracer CONFIG) and CMAKE_PREFIX_PATH / dftracer_DIR. Then render with `software_cmake_recipe` and validate again.
- `no_whole_build_wipe_for_cache` fails: Replace the rm -rf of the build dir with rm build/CMakeCache.txt. Then render with `software_cmake_recipe` and validate again.
- `cmake_out_of_source` fails: Configure with cmake -S <source> -B <build>. Then render with `software_cmake_recipe` and validate again.
- `no_find_package_with_wheel` fails: Link the install directly (-I/-L/-ldftracer_core) or define a manual IMPORTED target. Then render with `software_cmake_recipe` and validate again.

## Self-heal
- If session_configure's command line differs from the recipe (generator, build type), trust the tool's output and correct the recipe with capability_update.

## Self-learn
- Record a new cross-project CMake lesson here, tagged with its (system, dependency) pair.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_cmake via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, from the source skill) session_configure -> session_build_install for the original tree, session_build_annotated for the annotated tree with CMAKE_PREFIX_PATH injected automatically after session_install_dftracer.

## Source: dftracer-agents `software-cmake` (verbatim, headings demoted)
_Original description:_ CMake build system detection, configure/build/install flow via session_configure/session_build_install/session_build_annotated, CMAKE_PREFIX_PATH dftracer injection, and per-system/per-dependency lesson tagging. Load this skill for any project whose top level is CMakeLists.txt.

#### Detection

- Top-level `CMakeLists.txt` with `project(<name> ...)`. Check for a
  `cmake_minimum_required(VERSION ...)` line to confirm the minimum version.
- Look for `option(...)` declarations for project-specific toggles before
  calling `session_configure` — an unrecognized `-D` flag name is silently
  ignored by CMake rather than erroring, so read the options first.
- `find_package(<name> ...)` / `find_library(...)` calls determine how a
  dependency is located — CONFIG mode (a `<Name>Config.cmake` file) vs MODULE
  mode (a `Find<Name>.cmake` script) vs pkg-config via
  `pkg_check_modules(...)`. Check which one dftracer or another dependency
  needs BEFORE assuming `-DCMAKE_PREFIX_PATH=<prefix>` alone is sufficient —
  dftracer currently ships CMake config files but no `.pc` file, so
  `find_package(dftracer CONFIG)` works but `pkg_check_modules(dftracer)`
  does not.

#### Configure / build / install flow (via MCP tools)

```
session_configure(run_id, extra_cmake_flags="-DENABLE_TESTS=OFF ...")
session_build_install(run_id, jobs=<n>)
```

or for the annotated tree:

```
session_build_annotated(run_id, extra_cmake_flags="...")
```

- `session_configure` runs `cmake -S source -B build -DCMAKE_INSTALL_PREFIX=install
  -DCMAKE_BUILD_TYPE=RelWithDebInfo <extra_cmake_flags>`.
- `session_build_annotated` automatically appends
  `-DCMAKE_PREFIX_PATH=<dftracer_install_prefix>` when
  `session_install_dftracer` was already called — you do not need to pass
  this yourself.
- `session_build_install` runs `make -j<jobs>` then `make install` inside
  `build/` (or `build_ann/` for the annotated tree) — this project uses the
  Makefile generator, not Ninja, by default.
- Re-running `session_configure` on an existing build dir reconfigures in
  place; no need to delete `build/` first unless CMake's cache is corrupted
  (symptom: stale `CMakeCache.txt` referencing a deleted compiler/prefix —
  fix by deleting `build/CMakeCache.txt` specifically, not the whole tree).

#### Lessons are per-system and per-dependency, not universal

CMake itself is portable, but whether `find_package` resolves a dependency
via CONFIG or MODULE mode, which system paths are searched, and what a
missing dependency's exact error looks like varies by system and by the
dependency itself. Tag every lesson below with the `(system, dependency)`
pair it was observed on. Cross-link the system-specific half into the
relevant `system-<system>` skill when it's about the site rather than CMake
itself.

#### Lessons

(none recorded yet for this repo's sessions beyond what's captured per
`workload-<app>` skills for specific projects — e.g. h5bench's CMake quirks
live in `workload-h5bench`. Record a NEW cross-project CMake lesson here;
keep project-specific CMakeLists.txt quirks in that project's own skill.)
