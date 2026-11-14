---
name: software_meson
description: Meson build system: detection (meson.build project(), meson_version, meson.options / meson_options.txt option() names, pyproject.toml build-backend mesonpy -> install through pip), meson setup / compile / install, in-place reconfigure, dependency() resolution (pkg-config -> CMake config -> wrap fallback) and project candidate lists (system pkg-config, _prefix option, sibling checkout, container installs), plus native meson support in session_configure / session_build_install / session_build_annotated. Load for any project whose top level is meson.build / meson.options, or on 'Dependency X found: NO', 'Unsupported build tool: meson', a silently ignored -D option typo, or 'implicit declaration of function strdup' under Cray clang with c_std=c99.
---
Cross-references: [[software_pip]] [[software_cmake]] [[software_autotools]] [[software_gcc]] [[software_flux_fiction]] [[software_flux]] [[system_tuolumne]] [[system_container]] [[capability_builder]]

# software_meson

Converted from dftracer-agents skill `software-meson`. Tools: `software_meson_recipe` (predictor) and `software_meson_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Confirm top-level `meson.build` with `project(<name>, '<lang>', ...)`; grep `meson_version:` for the minimum Meson version.
- Read `meson.options` (or legacy `meson_options.txt`) `option()` names BEFORE session_configure: option names are project-specific (e.g. `use_system_flux`, `flux_prefix`) and a `-D` typo may be silently ignored.
- `pyproject.toml` with `build-backend = "mesonpy"` (requires meson-python, meson) means install with `pip install -e .` (or non-editable) / `python -m build`, not hand-rolled `meson setup` (see software_pip).
- Direct flow: `meson setup <builddir> -Doption_name=value ...`, `meson compile -C <builddir>`, `meson install -C <builddir>`.
- Re-running `meson setup` on an existing builddir with new `-D` options reconfigures in place: no `rm -rf` needed.
- `dependency('<name>', required: true)` resolves pkg-config -> CMake config files -> subproject wrap fallback; on failure read the exact 'Dependency X found: NO' line, do not guess.
- When meson.build builds a candidate list (system pkg-config, explicit `_prefix` option, workspace sibling checkout, container-installs dir), run `pkg-config --exists <name>` FIRST before assuming a sibling checkout or container build is needed because a README says so.
- Do not build an optional dependency just because a sibling-directory convention for it exists in the candidate list.
- Since 2026-07-16 session_configure / session_build_install / session_build_annotated support meson natively: no `custom_build_cmd` for the plain flow; check the tool's error before falling back.

## Constraints
- Lessons are per (system, dependency) pair: which dependency() resolves via pkg-config, needs a _prefix / use_system_* option, a sibling checkout or a module load varies by system (Tuolumne Cray PE vs generic Linux vs container) and dependency (flux-core, HDF5, jansson, MPI...). Cross-link site halves into system_<machine>.
- Linking against a dependency with no .pc file (only a CMake config, or nothing) is a per-project meson.build gap that the generic session tooling cannot fix (dftracer case: software_flux_fiction).

## Corner cases
### `Dependency X found: NO`
pkg-config, CMake config and wrap fallback all failed for X. Read which dependency() line failed; fix PKG_CONFIG_PATH / the project's _prefix option / module load for that dependency only.

### README recommends a podman container with sibling flux-core / flux-sched checkouts
Only needed when system flux-core is absent. Run `pkg-config --exists flux-core`; on Tuolumne it succeeds (flux 0.86.0 in the standard environment) so -Duse_system_flux=true avoids the container path. flux-sched was not needed for the jobtap plugin. Re-check per system. (2026-07-16)

### `implicit declaration of function 'strdup'` under Cray clang with c_std=c99 / warning_level=2
Cray clang strict C99 does not expose POSIX declarations; -D_POSIX_C_SOURCE did NOT fix it. Fix: add_project_arguments('-D_GNU_SOURCE', language: 'c') (or in c_args). (Tuolumne, 2026-07-16)

### `Unsupported build tool: meson` from session tools
Pre-2026-07-16 tooling. Current session_configure / session_build_install / session_build_annotated have meson branches; the old workaround was custom_build_cmd = meson setup <build_dir> <source_dir> -D... && ninja -C <build_dir> && ninja -C <build_dir> install.

### A -D option seems to have no effect
Option name typo or not declared in meson.options; meson may not error in all cases. Fix: compare against option() names; check `meson configure <builddir>` output.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_meson_recipe` renders the recipe; validator `software_meson_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_rm_builddir_to_reconfigure` fails: Re-run meson setup <builddir> -D... (or meson configure <builddir> -D...) without deleting the builddir. Then render with `software_meson_recipe` and validate again.
- `compile_install_with_C` fails: Use meson compile -C <builddir> and meson install -C <builddir>. Then render with `software_meson_recipe` and validate again.
- `gnu_source_not_posix` fails: Use add_project_arguments('-D_GNU_SOURCE', language: 'c'). Then render with `software_meson_recipe` and validate again.
- `pkgconfig_probe_before_sibling` fails: Run pkg-config --exists <name> first; only fall back to a sibling checkout or container if it fails. Then render with `software_meson_recipe` and validate again.

## Self-heal
- If a meson dependency fails, check `pkg-config --exists <name>` on this system before patching meson.build or building sibling checkouts.

## Self-learn
- Record each new meson lesson tagged with its (system, dependency) pair; project-specific meson.build gaps go to that project's capability.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_meson via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- 2026-07-16 (Tuolumne, flux-core, flux-fiction): system flux-core via pkg-config with -Duse_system_flux=true; no sibling checkout, no flux-sched, no container.
- 2026-07-16 (Tuolumne, Cray clang): add_project_arguments('-D_GNU_SOURCE', language: 'c') fixes strdup implicit-declaration under c_std=c99.
- 2026-07-16: native meson in session_configure / session_build_install / session_build_annotated (no custom_build_cmd).

## Source: dftracer-agents `software-meson` (verbatim, headings demoted)
_Original description:_ Meson build system detection, configure/build/install flow, dependency() resolution (pkg-config vs workspace/prefix fallbacks), and meson-python packaging. Load this skill for any project whose top level is meson.build / meson.options.

#### Detection

- Top-level `meson.build` with `project(<name>, '<lang>', ...)` — grep for
  `meson_version:` to confirm the minimum Meson version required.
- `meson.options` (or legacy `meson_options.txt`) holds project-specific
  `option()` declarations — always read this BEFORE calling
  `session_configure`, since the exact option names (e.g. `use_system_flux`,
  `flux_prefix`) are project-specific and configure will silently ignore an
  unrecognized `-D` flag name typo rather than erroring loudly in all cases.
- `pyproject.toml` with `build-backend = "mesonpy"` and
  `requires = ["meson-python>=...", "meson>=..."]` means the project is
  installed via `pip install .` (or `python -m build`), NOT `meson setup` +
  `ninja install` directly — pip/meson-python drives the meson configure+
  compile+install internally. Prefer `pip install -e .` (or non-editable if
  editable isn't supported) over hand-rolling `meson setup builddir`.

#### Configure / build flow (when driving meson directly, no pyproject wrapper)

```
meson setup <builddir> -Doption_name=value ...
meson compile -C <builddir>
meson install -C <builddir>
```

- Re-running `meson setup` on an existing builddir with new `-D` options
  reconfigures in place; you do not need to `rm -rf` the builddir first.
- `dependency('<name>', required: true)` resolution order is typically:
  pkg-config → CMake config files → meson subproject wrap fallback. If a
  dependency is missing and there's no wrap fallback, configure fails at
  that `dependency()` call with a clear "Dependency X found: NO" line — read
  the exact line, don't guess which dependency broke.
- A project may deliberately support several ways to locate an external
  library it depends on (system pkg-config, an explicit `_prefix` option, a
  workspace-relative sibling checkout, or a container-installs directory) by
  building a list of "candidates" in its own `meson.build` and searching them
  in order — check for a system-installed version via `pkg-config --exists
  <name>` FIRST before assuming a sibling checkout or container build is
  required just because a README recommends it.

#### Lessons are per-system and per-dependency, not universal

Meson itself is portable, but WHICH `dependency()` resolves via pkg-config,
which needs a `_prefix`/`use_system_*` option, and which needs a sibling
checkout or module load varies by system (Tuolumne Cray PE vs a generic
Linux box vs a container) and by which software the project depends on
(flux-core, HDF5, jansson, MPI, ...). Tag every lesson below with the
`(system, dependency)` pair it was observed on — don't generalize a
system-specific pkg-config/module finding into "meson always does X".
Cross-link the system-specific side of the lesson into the relevant
`system-<system>` skill too when it's about the site, not about meson.

#### Lessons

- **(Tuolumne, flux-core) flux-fiction 2026-07-16: `use_system_flux` boolean
  option lets a meson-based C+Python project skip building its own C
  dependency (flux-core) from a sibling checkout entirely when the dependency
  is already present on the system.** Symptom: README recommends a podman
  container with sibling `flux-core`/`flux-sched` checkouts. Root cause:
  that's only needed when system flux-core isn't installed. Fix: run
  `pkg-config --exists flux-core` first — on Tuolumne this succeeded (flux
  0.86.0 is part of the site's standard environment), so
  `-Duse_system_flux=true` (often the default) avoided the whole
  container/sibling-checkout path. On a system WITHOUT a site-wide flux
  install, expect to need `flux_prefix` or the sibling-checkout candidate
  instead — re-check `pkg-config --exists` per system rather than assuming
  this result transfers. `flux-sched` was NOT required at all for this
  project's C jobtap plugin on Tuolumne — don't build an optional dependency
  just because a sibling directory convention exists for it in the
  `meson.build` candidate list.
- **(Tuolumne, Cray clang) flux-fiction 2026-07-16: a meson project built with
  `c_std=c99`/`warning_level=2` default_options can fail to compile with
  `strdup()`/other POSIX-but-not-C99 functions "implicit declaration"
  under Cray clang, even though the same source compiles fine on GCC/regular
  clang.** Root cause: Cray clang's strict C99 mode doesn't pull in POSIX
  declarations, and the traditional `_POSIX_C_SOURCE` feature-test macro did
  NOT fix it here (retried and still failed — see
  `03_meson_compile_posix.log` in the flux-fiction session artifacts). Fix:
  add `-D_GNU_SOURCE` to the project's meson `c_args` (e.g. in `src/meson.build`
  via `add_project_arguments('-D_GNU_SOURCE', language: 'c')`), which is
  honored more reliably across compilers than `_POSIX_C_SOURCE` even in
  strict `c_std=c99` mode. Check for this whenever a meson C target on
  Tuolumne/Cray clang reports an implicit-declaration error for a libc/POSIX
  function that isn't strict C99.

- **(session tooling) 2026-07-16: native meson support landed in
  `session_configure`/`session_build_install`/`session_build_annotated`
  (branches added in `session_tools.py`).** Prior to this date those tools
  raised `"Unsupported build tool: meson"` and required a hand-rolled
  `custom_build_cmd` (`meson setup <build_dir> <source_dir> -D... && ninja -C
  <build_dir> && ninja -C <build_dir> install`). A fresh session should not
  need `custom_build_cmd` for the plain configure/build/install flow anymore
  — check the tool's error message before assuming the workaround is still
  needed. Note: linking against a dependency that has no `.pc`/pkg-config
  file (only a CMake config, or nothing at all) is a per-project meson.build
  gap, not something the generic session tooling can fix — see
  `software-flux-fiction` for the dftracer-specific case.
