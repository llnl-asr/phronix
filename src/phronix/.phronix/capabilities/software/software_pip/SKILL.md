---
name: software_pip
description: pip / PEP 517-518 builds off a pyproject.toml: build-backend detection (mesonpy -> Meson underneath, setuptools.build_meta, hatchling.build), editable vs non-editable install, --no-build-isolation in HPC venvs, forwarding project meson -D options through --config-settings=setup-args, extras, [project.scripts] CLI names, and CC/CXX/LD_LIBRARY_PATH ordering before pip. Load for any project installed with `pip install` off a pyproject.toml, or when the build step under pip cannot find a system dependency the active shell sees (build isolation), a meson option such as use_system_flux cannot be passed, or a compiled extension picks the wrong compiler.
---
Cross-references: [[software_meson]] [[software_cmake]] [[software_gcc]] [[software_flux_fiction]] [[tools_moirai_venv]] [[system_tuolumne]] [[capability_builder]]

# software_pip

Converted from dftracer-agents skill `software-pip`. Tools: `software_pip_recipe` (predictor) and `software_pip_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Read `[build-system].build-backend` in the top-level pyproject.toml before anything else.
- `build-backend = "mesonpy"`: the real build system is Meson; also load software_meson, and pass project meson `-D` options as `pip install . --config-settings=setup-args="-Doption=value"`.
- `setuptools.build_meta`: classic setup.py / setup.cfg semantics. `hatchling.build`: Hatch-managed, usually no compiled extension.
- Use `[project.scripts]` entries (not a guess) as the CLI names on PATH after install when writing a smoke-test command.
- Install extras (`pip install '.[dev]'`) only when that extra's contents are needed for the pipeline stage at hand; never blanket-install every extra.
- Default: `pip install --no-build-isolation -e .`; if the backend forbids or mishandles editable installs with a compiled extension: `pip install --no-build-isolation .`.
- With `--no-build-isolation`, first install the `[build-system].requires` packages (meson, meson-python, ...) into the venv yourself.
- Set CC / CXX and LD_LIBRARY_PATH (and load modules) BEFORE `pip install` for compiled-extension backends: the pip subprocess re-sources nothing.

## Constraints
- Lessons are per (system, dependency) pair: needed extras, whether --no-build-isolation is required and extra linker flags depend on the system's modules/toolchain and the project's native dependencies. Do not generalise 'pip always needs X' from one project; cross-link site halves into system_<machine>.

## Corner cases
### Build under pip cannot find a system dependency the active shell finds (Dependency X found: NO / not found)
Build isolation creates an ephemeral env that does not see loaded modules, compiler wrappers or module-provided pkg-config paths. Fix: pip install --no-build-isolation after installing [build-system].requires into the venv.

### Plain `pip install .` cannot set a project meson option (e.g. use_system_flux)
Fix: pip install --no-build-isolation --config-settings=setup-args="-Duse_system_flux=true" . (Tuolumne, flux-core, 2026-07-16).

### Compiled extension built with the wrong compiler / missing runtime lib
CC/CXX/LD_LIBRARY_PATH were set after pip started or not exported. Fix: load modules and export CC, CXX, LD_LIBRARY_PATH before pip install.

### Editable install fails for a compiled-extension backend
Some backends forbid or mishandle -e with compiled extensions. Fix: non-editable pip install --no-build-isolation .

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_pip_recipe` renders the recipe; validator `software_pip_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_build_isolation` fails: Install the [build-system].requires into the venv and add --no-build-isolation. Then render with `software_pip_recipe` and validate again.
- `meson_opts_via_setup_args` fails: Use --config-settings=setup-args="-D<option>=<value>". Then render with `software_pip_recipe` and validate again.
- `cc_before_pip` fails: Export CC, CXX and LD_LIBRARY_PATH on an earlier line, before pip install. Then render with `software_pip_recipe` and validate again.

## Self-heal
- If a pip build fails only inside the isolated build env, retry with --no-build-isolation after installing the build requirements, before patching the project.

## Self-learn
- Record each new pip lesson tagged with its (system, dependency) pair; site-specific halves go to the system capability.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_pip via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- 2026-07-16 (Tuolumne, flux-core, flux-fiction): pip install --no-build-isolation --config-settings=setup-args="-Duse_system_flux=true" . for a mesonpy project with a use_system_flux meson option.

## Source: dftracer-agents `software-pip` (verbatim, headings demoted)
_Original description:_ pip / PEP 517-518 build-backend detection (setuptools, mesonpy, hatchling, ...), editable vs non-editable install choice, and venv/module-load ordering on HPC systems. Load this skill for any project installed via `pip install` off a pyproject.toml.

#### Detection

- Top-level `pyproject.toml` with a `[build-system]` table — read
  `build-backend` before doing anything:
  - `build-backend = "mesonpy"` → the real build system is Meson underneath;
    pip/meson-python drives `meson setup`/`compile`/`install` internally.
    Load [[software-meson]] too, since project-specific meson `-D` options
    are passed through pip via
    `pip install . --config-settings=setup-args="-Doption=value"`.
  - `setuptools.build_meta` → classic `setup.py`/`setup.cfg` semantics apply.
  - `hatchling.build` → Hatch-managed, usually no compiled extension.
- `[project.scripts]` entries tell you the CLI names that will land on PATH
  after install — use these (not a guess) when writing a smoke-test command.
- `[project.optional-dependencies]` groups (e.g. `dev`, `otel`, `plot`) are
  extras — install with `pip install '.[dev]'` when the extra's contents
  (test deps, optional instrumentation) are actually needed for the pipeline
  stage at hand; don't blanket-install every extra by default.

#### Configure / build flow

```
pip install --no-build-isolation -e .        # editable, reuses env's own meson/ninja
# or, if the backend forbids/mishandles editable with a compiled extension:
pip install --no-build-isolation .
```

- `--no-build-isolation` is usually necessary in HPC session venvs: build
  isolation creates an ephemeral env that won't see already-loaded
  site-specific toolchain state (compiler wrappers, module-provided
  pkg-config paths), so the meson/cmake configure step underneath can fail to
  find system dependencies it would find if driven from the active shell.
  Install the `[build-system].requires` packages (meson, meson-python, etc.)
  into the venv yourself first when using `--no-build-isolation`.
- Compiled-extension backends need `CC`/`CXX` and `LD_LIBRARY_PATH` set
  BEFORE `pip install` runs, same ordering requirement as a raw
  configure/cmake build — the pip subprocess does not re-source anything.

#### Lessons are per-system and per-dependency, not universal

Which extras are needed, whether `--no-build-isolation` is required, and
whether a compiled extension needs extra linker flags all depend on the
specific system's module/toolchain setup and the specific project's native
dependencies — tag lessons with the `(system, dependency)` pair observed, and
cross-link the system-specific half into `system-<system>` rather than
generalizing "pip always needs X" from one project.

#### Lessons

- **(Tuolumne, flux-core) flux-fiction 2026-07-16:** `pyproject.toml` used
  `build-backend = "mesonpy"` with a `use_system_flux` meson option — when
  installing via pip rather than `meson setup` directly, that option must be
  forwarded as
  `pip install --no-build-isolation --config-settings=setup-args="-Duse_system_flux=true" .`
  (or via `flux_prefix` similarly) since plain `pip install .` has no way to
  pass project-specific meson `-D` flags otherwise.
