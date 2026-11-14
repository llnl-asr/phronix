---
name: software_autotools
description: Autotools (autoconf/automake/libtool) build system: detection (configure.ac + Makefile.am needing autoreconf -fi vs a checked-in configure script from a release tarball), the session_configure / session_build_install / session_build_annotated flow, dftracer injection through PKG_CONFIG_PATH / CPPFLAGS / LDFLAGS (there is no generic --with-dftracer flag), and stale .deps/ cleanup. Load for any project with configure.ac / Makefile.am or a checked-in configure script, or on 'configure: error: unrecognized option --with-...', a config.status failure from stale .deps/ directories, or dftracer headers/libs not found by the annotated configure.
---
Cross-references: [[software_cmake]] [[software_meson]] [[software_pip]] [[software_gcc]] [[tools_dftracer]] [[system_tuolumne]] [[capability_builder]]

# software_autotools

Converted from dftracer-agents skill `software-autotools`. Tools: `software_autotools_recipe` (predictor) and `software_autotools_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- `configure.ac` + `Makefile.am` at the source root and no `configure` means not bootstrapped: run `autoreconf -fi` before `./configure`.
- A checked-in `configure` with no `configure.ac` is already bootstrapped (release tarballs): do not run `autoreconf`.
- Read the `AC_ARG_WITH` / `AC_ARG_ENABLE` macros in `configure.ac` before passing `extra_configure_flags`: they name the project's own `--with-*` / `--enable-*` flags, and an unrecognised flag usually errors loudly (unlike CMake / Meson, which silently ignore).
- Configure / build through the MCP tools: `session_configure(run_id, extra_configure_flags="--with-mpi --disable-shared ...")` then `session_build_install(run_id, jobs=<n>)`; annotated tree with `session_build_annotated(run_id)`.
- `session_configure` bootstraps with `autoreconf -fi` only if `configure.ac` exists and `configure` does not, then runs `./configure --prefix=<install> --disable-dependency-tracking <extra_configure_flags>`; `--disable-dependency-tracking` is always added (avoids a common `config.status` failure from stale `.deps/`).
- `session_configure` and `session_build_annotated` delete any `.deps/` under `source/` / `annotated/` and `build/` / `build_ann/` before configuring.
- `session_build_annotated` injects dftracer through env vars, not `--with-dftracer=<prefix>` (no such generic flag): `PKG_CONFIG_PATH=<prefix>/lib/pkgconfig`, `CPPFLAGS=-I<prefix>/include`, `LDFLAGS=-L<prefix>/lib -Wl,-rpath,<prefix>/lib`.

## Constraints
- Env-var injection only works if the project's `configure.ac` actually honours PKG_CONFIG_PATH / CPPFLAGS / LDFLAGS (via `PKG_CHECK_MODULES` or plain `AC_CHECK_HEADER` / `AC_CHECK_LIB`); if it hard-codes include paths, a project-specific patch is needed and belongs to that project's workload_<app> / software_<app> capability.
- Lessons are per (system, dependency) pair, not universal: which detection macro a project uses (`PKG_CHECK_MODULES` vs `AC_CHECK_LIB` vs a hand-rolled `AC_ARG_WITH` prefix flag) and which system paths are searched vary. Tag each lesson; site-specific halves go to the system_<machine> capability.
- Keep a single project's `configure.ac` quirks in that project's own capability; only cross-project autotools lessons go here.

## Corner cases
### `config.status` failure from stale `.deps/` directories
A `.deps/` left by a previous configure with different flags. Fix: the session tools already delete `.deps/` and pass `--disable-dependency-tracking`; if configuring by hand, remove `.deps/` under the source and build trees and add `--disable-dependency-tracking`.

### `configure: error: unrecognized option` / `--with-dftracer` not recognised
There is no generic `--with-dftracer` flag; autotools errors on unknown options. Fix: inject PKG_CONFIG_PATH / CPPFLAGS / LDFLAGS (what session_build_annotated does) and only pass flags declared by AC_ARG_WITH / AC_ARG_ENABLE.

### dftracer headers/libs still not found after env injection
The project's configure.ac hard-codes include/lib paths instead of probing CPPFLAGS / LDFLAGS / pkg-config. Fix: a project-specific patch, recorded in that project's capability.

### `autoreconf` run on a release tarball
A checked-in configure without configure.ac is already bootstrapped; re-bootstrapping can fail on missing macros or mismatched autotools versions. Fix: just run ./configure.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_autotools_recipe` renders the recipe; validator `software_autotools_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_with_dftracer_flag` fails: Inject dftracer via PKG_CONFIG_PATH=<prefix>/lib/pkgconfig, CPPFLAGS=-I<prefix>/include, LDFLAGS=-L<prefix>/lib -Wl,-rpath,<prefix>/lib. Then render with `software_autotools_recipe` and validate again.
- `disable_dependency_tracking` fails: Add --disable-dependency-tracking to the ./configure line. Then render with `software_autotools_recipe` and validate again.
- `configure_has_prefix` fails: Pass --prefix=<install>. Then render with `software_autotools_recipe` and validate again.
- `ldflags_rpath_with_dftracer_lib` fails: Add -Wl,-rpath,<dftracer_prefix>/lib to LDFLAGS. Then render with `software_autotools_recipe` and validate again.

## Self-heal
- If session_configure's command line differs from the recipe (flags, bootstrap condition), trust the tool's output and correct the recipe with capability_update.

## Self-learn
- Record a NEW cross-project autotools lesson here, tagged with its (system, dependency) pair; single-project configure.ac quirks go to that project's capability.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_autotools via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, from the source skill) session_configure -> session_build_install for the original tree; session_build_annotated for the annotated tree with dftracer injected via PKG_CONFIG_PATH / CPPFLAGS / LDFLAGS.

## Source: dftracer-agents `software-autotools` (verbatim, headings demoted)
_Original description:_ Autotools (autoconf/automake/libtool) build system detection, bootstrap/configure/build/install flow via session_configure/session_build_install/session_build_annotated, PKG_CONFIG_PATH/CPPFLAGS/LDFLAGS dftracer injection, and per-system/per-dependency lesson tagging. Load this skill for any project with configure.ac/Makefile.am or a checked-in configure script.

#### Detection

- `configure.ac` + `Makefile.am` at the source root (not yet bootstrapped) —
  needs `autoreconf -fi` before `./configure` exists.
- A checked-in `configure` script with no `configure.ac` — already
  bootstrapped (common for release tarballs); do not run `autoreconf`.
- `AC_ARG_WITH`/`AC_ARG_ENABLE` macros in `configure.ac` name the project's
  own `--with-*`/`--enable-*` flags — read these before calling
  `session_configure` with `extra_configure_flags`, since an unrecognized
  flag usually errors loudly (unlike CMake/Meson's silent-ignore behavior).

#### Configure / build / install flow (via MCP tools)

```
session_configure(run_id, extra_configure_flags="--with-mpi --disable-shared ...")
session_build_install(run_id, jobs=<n>)
```

or for the annotated tree:

```
session_build_annotated(run_id)
```

- `session_configure` bootstraps with `autoreconf -fi` only if `configure.ac`
  exists and `configure` does not, then runs
  `./configure --prefix=<install> --disable-dependency-tracking <extra_configure_flags>`.
  `--disable-dependency-tracking` is always added — it avoids a common
  `config.status` failure from stale `.deps/` directories.
- Both `session_configure` and `session_build_annotated` proactively delete
  any `.deps/` directories found under `source/`/`annotated/` and `build/`/
  `build_ann/` before configuring — a stale `.deps/` from a previous
  configure with different flags is a common autotools failure mode.
- `session_build_annotated` injects dftracer discovery via environment
  variables (not `--with-dftracer=<prefix>`, since that flag doesn't exist
  generically across projects): `PKG_CONFIG_PATH=<prefix>/lib/pkgconfig`,
  `CPPFLAGS=-I<prefix>/include`, `LDFLAGS=-L<prefix>/lib -Wl,-rpath,<prefix>/lib`.
  This only works if the project's own `configure.ac` actually probes
  `PKG_CONFIG_PATH`/`CPPFLAGS`/`LDFLAGS` (via `PKG_CHECK_MODULES` or plain
  `AC_CHECK_HEADER`/`AC_CHECK_LIB`) — if it hard-codes include paths instead,
  you'll need a project-specific patch (record that in the project's own
  `workload-<app>`/`software-<app>` skill, not here).

#### Lessons are per-system and per-dependency, not universal

Autotools itself is portable, but which dependency-detection macro a
project's `configure.ac` uses (`PKG_CHECK_MODULES` vs `AC_CHECK_LIB` vs a
hand-rolled `AC_ARG_WITH` prefix flag), and which system paths get searched,
varies by system and dependency. Tag every lesson with the
`(system, dependency)` pair observed; cross-link the system-specific half
into `system-<system>` when it's about the site, not autotools itself.

#### Lessons

(none recorded yet for this repo's sessions beyond what's captured in
per-project `workload-<app>` skills. Record a NEW cross-project autotools
lesson here; keep a single project's `configure.ac` quirks in that project's
own skill.)
