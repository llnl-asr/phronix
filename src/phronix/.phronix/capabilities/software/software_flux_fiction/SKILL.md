---
name: software_flux_fiction
description: Flux-Fiction (Flux scheduling emulator: Meson-built C jobtap plugin emu-jobtap.so + Python package) build, dftracer linking, annotation and run facts: annotate the EMULATED job timeline with manual log_event (simulated time from FakeTimeController, one event per allocated node tagged mhost), DFTRACER_INC_METADATA=1, explicit initialize_log/finalize, CFLAGS/LDFLAGS dftracer link for Meson, session-venv editable install, Flux Python bindings deps, MockAdapter diagnostic. Load when building or annotating flux-fiction, or on: "call to undeclared function 'strdup'; ISO C99 and later do not support implicit function declarations"; 'log_event(): incompatible function arguments'; trace with no job_submit/job_start/job_complete or no args; dependency('dftracer') not found; emu-jobtap.so not found; FileExistsError from create_run_root; missing ../test-inputs file; "Unknown service method 'sched.quiescent': Function not implemented"; 'TypeError: Object of type method is not JSON serializable'.
---
Cross-references: [[software_meson]] [[software_flux]] [[software_mpi]] [[software_pip]] [[tools_pydftracer]] [[tools_dftracer]] [[dftracer_annotate]] [[dftracer_build]] [[system_tuolumne]] [[capability_builder]]

# software_flux_fiction

Converted from dftracer-agents skill `software-flux-fiction`. Tools: `software_flux_fiction_recipe` (predictor) and `software_flux_fiction_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Goal is the RUNTIME OF THE EMULATED JOBS on the simulation clock, not the emulator's wall-clock profile: a job simulated for 10 min must appear as ~10 simulated minutes, not the 2ms the Python function took.
- Annotate the job-emulation lifecycle in `_core/engine.py` `Simulation` with manual `log_event(name, cat, start_time, duration, ...)` (dftracer-annotate-python Rule 8), not `@_dft.log`: `add_event` (clock-tick primitive), `submit_job`, `start_job`, `complete_job` (span = job's simulated start -> finish from `_core/models.py` `Job`). `_next_event_time` is low-priority bookkeeping (auto or manual both fine).
- Read simulated time from `_core/faketime.py` `FakeTimeController` (`advance_to` / `current_effective_time` / `target_time`), never `time.time()`. Times in NANOSECONDS (DFTRACER_TIME_METRIC=NS).
- `start_job`/`complete_job`: emit ONE event PER allocated node (nodes from `self.adapter.nodelist_lookup(jobid)`, stored in `job.allocated_nodes` for reuse), same start_time/duration, only `string_args={"mhost": (0, node_id)}` differing. Never a comma-joined node list; never fake pid/tid; never use the reserved `hhash` key.
- `int_args`/`string_args`/`float_args` values must be `(tag_type, value)` tuples, tag_type 0 (`TagType.KEY`); bare values raise 'incompatible function arguments', silently swallowed by the surrounding `except Exception`.
- `_adapters/flux/*`: decide per function - real Flux RPC latency -> auto decorator; relayed simulated job event -> manual log_event with simulated time.
- Never decorate `@property` methods (e.g. `Job.jobspec`) with `@_dft.log` (TypeError: Object of type method is not JSON serializable).
- Do the manual simulated-clock pass first, then run the generic python annotate tool over the rest for Rule-0 I/O.
- Add `dftracer.python.dftracer.initialize_log(logfile=..., data_dir=...)` at the entry point (`cli/support/run_api_experiment.py`) and `finalize()` in a `finally:` block - no auto-init from env vars, no flush on sys.exit(0).
- Set `DFTRACER_INC_METADATA=1` with `DFTRACER_ENABLE=1`, `DFTRACER_LOG_FILE`, `DFTRACER_DATA_DIR` on every run, or all args (mhost, job_id) are dropped.
- Meson strict C99 on Cray clang: add `-D_GNU_SOURCE` to the jobtap shared_module c_args (`_POSIX_C_SOURCE` is ignored).
- Link dftracer into the Meson build through `CFLAGS=-I<dft>/include` and `LDFLAGS=-L<dft>/lib64 -Wl,-rpath,<dft>/lib64 -ldftracer_core` at `meson setup` / `pip install -e` time: dftracer ships no .pc, `dependency('dftracer')` never resolves, `-DCMAKE_PREFIX_PATH` has no effect on Meson.
- Always use a FRESH meson build dir when CFLAGS/LDFLAGS change (`meson setup --reconfigure` keeps the cached ones).
- Run from the directory the config's relative paths were written against: `src/config.toml` from `annotated/source/src`, `mock_config.toml` from `annotated/source`.
- Use a fresh `--run-dir`/`--tag` per retry (existing run dir -> FileExistsError).
- Verify manual events are in the trace with reader/event_count, not just exit 0.

## Constraints
- Tuolumne's stock sched-fluxion-qmanager 0.52.0 lacks the `sched.quiescent` RPC; no alternative module, no config knob. Real-backend runs block after alloc/sim_exec_start_cb; only a patched flux-sched (project container) provides it.
- `backend = "mock"` (MockAdapter) runs cleanly end-to-end and validates build/install/annotation, but bypasses the real Flux/jobtap integration.
- flux-sched is not a build dependency; do not build it for a basic build.
- Flux Python bindings exist only for python3.12 (`/usr/lib64/flux/python3.12`); they are pure Python and work from a 3.13 venv via PYTHONPATH.

## Corner cases
### error: call to undeclared function 'strdup'; ISO C99 and later do not support implicit function declarations
src/jobtap/ff_otel.c under Meson default_options c_std=c99 on Cray clang. Fix: c_args += '-D_GNU_SOURCE' in src/meson.build shared_module.

### log_event(): incompatible function arguments (or silently zero job_* events)
args dict values passed bare. Fix: {"job_id": (0, int(jobid))}. Check the trace with reader/event_count because the except Exception hides it.

### Trace events present but args (mhost, job_id) missing
DFTRACER_INC_METADATA unset. Fix: DFTRACER_INC_METADATA=1.

### log_event silently no-ops everywhere
No initialize_log() at the entry point (logger is None). Fix: initialize_log(logfile=..., data_dir=...) in run_api_experiment.py and finalize() in finally:.

### Missing ../test-inputs/*.csv
remap_path() resolves against process CWD, not config dir. Fix: cwd=annotated/source/src with config.toml.

### Unknown service method 'sched.quiescent': Function not implemented
Fluxion 0.52.0 does not implement it. Use backend=mock to validate the pipeline, or a tiny test-inputs CSV with a hard timeout and accept partial .pfw.gz traces as smoke evidence.

### emu-jobtap.so not found after pip install -e with custom build-dir
jobtap_path.py only searches bundled resources and <repo>/build/... . Fix: FLUX_FICTION_JOBTAP_SO=<path>.

### FileExistsError from create_run_root
Run dir from a previous attempt. Fix: new --run-dir/--tag.

### emu-jobtap.so links the framework venv's libdftracer_core
Reused old meson build dir with cached CFLAGS/LDFLAGS. Fix: fresh build-dir; verify with ldd that libdftracer_core.so resolves under the session venv.

### import flux fails in the session venv
Missing cffi, pyyaml, ply, jsonschema, or PYTHONPATH not pointing at /usr/lib64/flux/python3.12.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_flux_fiction_recipe` renders the recipe; validator `software_flux_fiction_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `inc_metadata_with_dftracer` fails: Set DFTRACER_INC_METADATA=1 alongside DFTRACER_ENABLE/LOG_FILE/DATA_DIR. Then render with `software_flux_fiction_recipe` and validate again.
- `no_pkgconfig_dftracer` fails: Pass CFLAGS=-I<dft>/include and LDFLAGS=-L<dft>/lib64 -Wl,-rpath,<dft>/lib64 -ldftracer_core at meson setup / pip install time. Then render with `software_flux_fiction_recipe` and validate again.
- `no_cmake_prefix_on_meson` fails: Use CFLAGS/LDFLAGS pointing at the dftracer install. Then render with `software_flux_fiction_recipe` and validate again.
- `annotated_build_links_dftracer` fails: Prefix the configure/install with LDFLAGS="-L<dft>/lib64 -Wl,-rpath,<dft>/lib64 -ldftracer_core" (and CFLAGS=-I<dft>/include). Then render with `software_flux_fiction_recipe` and validate again.
- `no_posix_c_source_for_strdup` fails: Use -D_GNU_SOURCE in the jobtap shared_module c_args. Then render with `software_flux_fiction_recipe` and validate again.
- `log_event_args_tuples` fails: Write {"job_id": (0, int(jobid))} / {"mhost": (0, node_id)}. Then render with `software_flux_fiction_recipe` and validate again.
- `mhost_one_event_per_node` fails: Loop over the allocated nodes and call log_event once per node with string_args={"mhost": (0, node_id)}. Then render with `software_flux_fiction_recipe` and validate again.
- `no_reserved_hhash` fails: Use the custom key mhost. Then render with `software_flux_fiction_recipe` and validate again.
- `simulated_time_not_wallclock` fails: Derive start_time/duration (ns) from FakeTimeController / the Job's simulated timestamps. Then render with `software_flux_fiction_recipe` and validate again.
- `config_cwd` fails: cd annotated/source/src and run flux-fiction-run config.toml. Then render with `software_flux_fiction_recipe` and validate again.

## Self-heal
- If a trace lacks job_submit/job_start/job_complete events, temporarily raise logging to debug to expose the swallowed log_event exception, then fix the args.
- If ldd shows the wrong libdftracer_core, rebuild into a new build dir with the session venv's CFLAGS/LDFLAGS.

## Self-learn
- Record whether a patched Fluxion implementing sched.quiescent becomes available on a system, and the real-backend recipe once it runs end to end.
- Update the list of simulated-clock functions if _core/engine.py changes.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_flux_fiction via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (2026-07-17) MockAdapter run with DFTRACER_ENABLE=1 DFTRACER_INC_METADATA=1 DFTRACER_DATA_DIR=all, PYTHONPATH=/usr/lib64/flux/python3.12, FLUX_FICTION_JOBTAP_SO set: job_submit/job_start/job_complete events with mhost, job_id args in the trace.
- CFLAGS/LDFLAGS-injected dftracer link for meson setup and for pip install -e (pip build isolation inherits them).
- System jansson (2.14+) and flux-core via pkg-config with use_system_flux=true on Tuolumne.

## Source: dftracer-agents `software-flux-fiction` (verbatim, headings demoted)
_Original description:_ > Flux-Fiction-specific knowledge: build system (Meson), dependency quirks, C99 standard handling on Cray clang, and the priority annotation focus (job-emulation lifecycle using the simulated/faketime clock). Flux-Fiction is software being annotated/instrumented by dftracer (a scheduling emulator/ tool), not a traced scientific workload — load this skill when building or annotating flux-fiction.

#### Annotation focus: the emulated JOB's runtime, not the emulator's own wall-clock profile (MANDATORY priority)

**This is NOT performance-profiling flux-fiction itself.** The goal is to
capture, in the dftracer trace, the RUNTIME OF THE EMULATED COMPONENTS —
i.e. how long each simulated job/step took according to the simulation's own
clock — not how long the Python code doing the emulating took to execute in
real wall-clock time. A job that the simulator "runs" for a simulated 10
minutes might be emulated by a Python function that returns in 2ms; the trace
event for that job must record ~10 simulated minutes as its duration, NOT the
2ms of real execution time the auto `@_dft.log` decorator would capture.
Prioritize annotating the job-emulation components (below) over generic
Rule-0 file/network I/O elsewhere in the tree — that incidental I/O can use
the normal auto-decorator, since IT genuinely happens at wall-clock speed.

**Known job-emulation lifecycle functions (as of 2026-07-16, `_core/engine.py`
`Simulation` class) that drive the discrete-event simulation clock and MUST
use the manual `log_event(name, cat, start_time, duration, ...)` API (see
`dftracer-annotate-python` Rule 8) instead of the auto `@_dft.log` decorator:**
- `Simulation.add_event(self, time, callback)` — schedules a discrete-event
  callback at a given SIMULATED `time`; this is the core clock-tick primitive.
- `Simulation.submit_job(self, job)` / `start_job(self, jobid)` /
  `complete_job(self, job)` — the three job-lifecycle transitions. The trace
  event for each must represent the JOB's own emulated timeline (its
  submit/alloc/start/finish timestamps, read off `job`'s own state/model —
  see `_core/models.py`'s `Job` class), NOT the wall-clock time the Python
  function itself took to run, and NOT the simulator's own tick duration
  either. E.g. `complete_job`'s event should span from the job's simulated
  start time to its simulated finish time — that's the "runtime of the
  emulated component" this trace exists to capture.

**Node grouping (`mhost`) — MANDATORY on `start_job`/`complete_job` (fixed
2026-07-16):** without this, every job's trace event looks like it ran on the
single real host running the emulator process, since all of flux-fiction's
job emulation happens in ONE Python process regardless of how many simulated
nodes a job was "allocated." dftracer's native trace format fixes `pid`/`tid`
per-process at init time (confirmed by inspecting the native
`dftracer.dftracer` C-extension directly — `log_event` has no per-call
hostname/pid override) — leave `pid`/`tid` as whatever dummy/constant values
the process has; do NOT try to fake them.

Instead, tag each event with a custom string_args key `"mhost"` — deliberately
NOT the same as `"hhash"` (the RESERVED short-name confirmed in
`dftracer/utils/indexer.py`'s own docstring: `"resolving fhash/hhash values"`,
which the trace indexer/analyzer already populates from the real process
hostname). `mhost` ("manual host") is a separate, fixed value we control
ourselves specifically so downstream analysis/viz tooling can override node
grouping with it WITHOUT colliding with or overwriting the indexer's own
native `hhash` column.

**Emit ONE event PER allocated node, never one event with a comma-joined
node-list string (corrected 2026-07-17).** A single event tagged
`mhost="20,21,...,29"` cannot be grouped/filtered per-node by a trace
viewer — the whole point of `mhost` is per-node grouping, same as per-MPI-rank
tracing emits one event per rank. Loop over the allocated nodes and call
`log_event` once per node, with the SAME `start_time`/`duration` and only
`mhost` differing:
```python
nodes, _src = self.adapter.nodelist_lookup(jobid)   # real allocated node IDs from Flux
job.allocated_nodes = nodes                          # stored so complete_job() reuses it, no second RPC
node_ids = [str(n) for n in sorted(nodes)] if nodes else [""]
for node_id in node_ids:
    dftracer.get_instance().log_event(
        name="job_start",
        cat="simulation",
        start_time=sim_start_time_ns,   # SAME for every per-node event (NANOSECONDS, DFTRACER_TIME_METRIC=NS)
        duration=gap_ns,                # SAME for every per-node event
        int_args={"job_id": (0, int(jobid))},
        string_args={"mhost": (0, node_id)},   # only this differs per event
    )
```
This means a job allocated 10 nodes produces 10 `job_start` events (and 10
`job_complete` events) instead of 1 — that's correct and expected, not
duplication.
- `Simulation._next_event_time(self)` — determines the next simulated tick;
  this is simulator bookkeeping, not a job's own runtime — a lightweight
  auto-decorated or manual event is fine here, low priority either way.

**Related components to check when doing this properly:**
- `_core/faketime.py`: `FakeTimeController.advance_to`/`current_effective_time`/
  `target_time` are the actual simulated-clock source of truth — read simulated
  time FROM here for the `start_time`/`duration` args passed to `log_event`,
  never from `time.time()`.
- `_adapters/flux/*` (adapter, journal, modules, resources): these bridge to
  REAL Flux RPCs (e.g. `sched.quiescent`) — decide per-function whether a
  given call represents real wall-clock RPC latency (auto decorator is
  correct there) or a simulated-time job event being relayed (manual
  `log_event` with simulated time is correct there instead). Don't
  blanket-treat this directory as either category.
- `_core/models.py`: `Job` class — holds job state/timestamps the simulation
  tracks; do NOT decorate `@property` methods like `jobspec` with `@_dft.log`
  (see Rule 3 in `dftracer-annotate-python` — this already caused a real
  `TypeError: Object of type method is not JSON serializable` bug here).

This is a manual-judgment annotation pass, not something
`python_annotate_project`'s blanket Rule-0 sweep can get right automatically
— identify the simulated-clock-driven functions first, annotate those with
manual `log_event` calls, THEN run the generic tool over the rest of the file
for ordinary Rule-0 I/O/lifecycle coverage.

**`log_event()` `int_args`/`string_args` MUST be `(tag_type_int, value)` tuples,
not bare values (fixed 2026-07-17).** The native `dftracer.python` C extension
requires each `int_args`/`string_args`/`float_args` dict value to be a 2-tuple
`(tag_type, value)` — `tag_type` is `TagType.KEY.value` = `0` for a normal tag
(see `dftracer/python/common.py`'s `TagValue.value()`: `(int(self._tag_type),
self._value)`). Passing a bare value (`{"job_id": 123}` instead of
`{"job_id": (0, 123)}`) raises `log_event(): incompatible function arguments`
— and because every manual `log_event` call in this file is wrapped in a
broad `except Exception: logger.debug(...)`, this failure is SILENT at normal
log levels: the process runs to completion, looks successful, but ships a
trace with zero `job_submit`/`job_start`/`job_complete`/`mhost` events. Always
verify manually-annotated `log_event` calls actually appear in the trace
output (via `reader`/`event_count`), not just that the process exits 0.

**dftracer Python FUNCTION-mode requires an explicit
`dftracer.python.dftracer.initialize_log(logfile=..., data_dir=...)` call at
the process entry point — no auto-init from env vars.** Confirmed 2026-07-17:
without this call, `dftracer.get_instance().log_event(...)` silently no-ops
(`self.logger is None` internally) everywhere in the process, not just in the
manually-annotated files. flux-fiction's CLI entry point
(`cli/support/run_api_experiment.py`) needed this added. Also: the trace file
is only flushed on an explicit `.finalize()` call (or a caught
`SIGABRT`/`SIGINT`/`SIGTERM`) — a normal `sys.exit(0)` does NOT auto-flush, so
`finalize()` must run in a `finally:` block around the entry point's main
logic.

**`remap_path()` resolves config-relative paths against the process's actual
CWD, not the config file's own directory (confirmed 2026-07-17).** A config
like `job_traces = "../test-inputs/10-multi-node.csv"` resolves differently
depending on where `flux-fiction-run` is invoked FROM — running with
`cwd=annotated/source` and `flux-fiction-run src/config.toml` resolves
`../test-inputs` one level too high (missing file); running with
`cwd=annotated/source/src` and `flux-fiction-run config.toml` resolves
correctly to `annotated/source/test-inputs/...`. Always run from the same
directory the config's own relative paths were written against — for the
canonical `src/config.toml` layout, that means `cwd=annotated/source/src`.

**Real Flux backend limitation (confirmed 2026-07-17, unfixable from a
session): Tuolumne's stock `sched-fluxion-qmanager` 0.52.0 does not implement
the `sched.quiescent` RPC** flux-fiction's jobtap plugin depends on for
step-synchronization — `Unknown service method 'sched.quiescent': Function
not implemented`. No `module avail flux-sched`/`fluxion` alternative exists on
this system, and no flux-fiction config option skips the quiescent probe. Per
`README.md`, this RPC must be provided by the scheduler itself — the
"recommended dev environment" flux-sched (built inside the project's own
podman container, see the Quickstart section) is apparently a patched fork
that implements it; system Fluxion does not. Jobs get partway (`alloc`/
`sim_exec_start_cb`) before permanently blocking. **`MockAdapter`
(`backend = "mock"` in the config) is confirmed to run cleanly end-to-end and
is the right tool for verifying the build/install/annotation pipeline itself
is sound** — it deliberately bypasses the real Flux/jobtap integration, so
don't mistake a clean mock run for the real backend working; use mock only as
a diagnostic to isolate infra bugs from this specific real-Flux-scheduler gap.

**Session-venv Python deps for the system flux-core Python bindings
(`/usr/lib64/flux/python3.12/`): `cffi`, `pyyaml`, `ply`, `jsonschema`.**
Confirmed 2026-07-17 — these are required by `import flux` even though the
bindings themselves are pure Python (no compiled-extension ABI mismatch
despite the session venv being Python 3.13 vs the bindings' `python3.12` path
in their install location).

**`DFTRACER_INC_METADATA=1` is REQUIRED for `int_args`/`string_args`/`float_args`
to appear in trace events at all (confirmed 2026-07-17, final piece of this
session's verification).** Defined in
`dftracer/include/dftracer/core/common/constants.h:18` as
`#define DFTRACER_INC_METADATA "DFTRACER_INC_METADATA"`. Without it, every
`log_event(...)` call (manual OR auto-decorated) writes its `name`/`cat`/
`start_time`/`duration` correctly but silently drops the entire `args`
payload — this looked exactly like a missing/broken `mhost` tag until this
env var was set, at which point `job_submit`/`job_start`/`job_complete`
events correctly showed `{'hhash': ..., 'mhost': '20,21,...,29', 'job_id':
..., 'trace_idx': ...}`. Set it alongside `DFTRACER_ENABLE=1`/
`DFTRACER_LOG_FILE`/`DFTRACER_DATA_DIR` for every run, not just this one.

Full confirmed reproduction recipe (MockAdapter diagnostic; swap
`mock_config.toml`/`backend="mock"` for `src/config.toml` + real Flux once
the `sched.quiescent` blocker above is resolved on a system with a patched
Fluxion):
```bash
DFTRACER_ENABLE=1 DFTRACER_INC_METADATA=1 \
DFTRACER_LOG_FILE=<WS>/traces/.../trace DFTRACER_DATA_DIR=all \
LD_LIBRARY_PATH=<CCE lib dirs>:/usr/lib64:<venv>/dftracer/lib64 \
PYTHONPATH=/usr/lib64/flux/python3.12 \
FLUX_FICTION_JOBTAP_SO=<build_ann>/src/emu-jobtap.so \
<venv>/bin/flux-fiction-run mock_config.toml --tag <tag> --no-faketime
```
(run from `annotated/source/` for `mock_config.toml`; `src/config.toml`
must be run from `annotated/source/src/` per the `remap_path()` CWD quirk
above).

Cross-references: [[dftracer-build-app]] [[software-mpi]]

---

#### Build — Flux-Fiction (Meson + C + Python)

##### strdup() fails in strict C99 mode on Cray clang

**Symptom:**
```
error: call to undeclared function 'strdup'; ISO C99 and later do not support implicit function declarations
```

Occurs in `src/jobtap/ff_otel.c` when Meson's `default_options: ['c_std=c99']` enforces strict
C99 compliance.

**Root cause:** `strdup()` is a POSIX function not available in strict C99 mode without
a feature test macro. Traditional feature test macros (`_POSIX_C_SOURCE=200112L`) are
ignored by Cray clang when `-std=c99` is strict.

**Fix:** Use `-D_GNU_SOURCE` in the Meson c_args for the jobtap shared_module. This works
reliably on Cray clang even in strict C99 mode:

```python
# In src/meson.build, shared_module c_args:
c_args: ['-Wall', '-Wextra', '-I' + flux_include_dir, '-D_GNU_SOURCE']
```

Rationale: GNU_SOURCE is more permissive and supported across all major compilers (Cray clang,
GCC, LLVM). Unlike `_POSIX_C_SOURCE`, it persists even when `-std=c99` is enforced.

---

#### Build — Dependencies (Tuolumne)

##### jansson is available system-wide

On Tuolumne: `pkg-config --exists jansson` succeeds (2.14+). No need to build from source.

##### flux-core is available system-wide

On Tuolumne: `flux version` works, `pkg-config --exists flux-core` succeeds. Meson's
`use_system_flux=true` (the default) will find flux-core headers and libraries without
needing a workspace sibling checkout (`../flux-core` or `container-installs/flux-core`).

##### flux-sched is NOT required for flux-fiction

The README recommends it in the dev environment, but the Meson build has no hard dependency
on flux-sched. Do not attempt to build or install it for the basic build to succeed.

---

#### Install — Python Package + Native Plugin

##### Installation layout (Meson)

Meson installs:
1. Python package: `<prefix>/lib/python<X.Y>/site-packages/flux_fiction/`
2. Native plugin (C): `<prefix>/lib/python<X.Y>/site-packages/flux_fiction/_native/emu-jobtap.so`

The `flux_fiction.cli.jobtap_path.jobtap_plugin_path()` function dynamically locates the plugin.

##### Plugin is always relocatable RPATH

The Meson build uses `install_rpath: jobtap_rpath` (pointing to flux-core's lib dir).
The plugin can be moved as long as flux-core libraries are findable via `LD_LIBRARY_PATH` or the RPATH.

---

#### Run — Smoke Test

##### flux-fiction-run harness is a convenience wrapper

The installed CLI includes `flux-fiction-run config.toml [--tag <name>] [--no-faketime]`,
which wraps the base `flux-fiction` API. It prepares a run directory, copies config, and
launches a fresh Flux instance. The base API is at `flux_fiction.api.client.FluxFiction`.

##### Requires active flux instance and Flux Python bindings

The emulator drives through the Flux Python bindings. Any run must have a Flux instance
active with `flux-core` Python bindings importable from the PYTHONPATH where flux_fiction
was installed.

---

#### Linking dftracer into the annotated build (Meson)

flux-fiction's `src/meson.build` resolves its only C dependency (flux-core)
via manual `cc.find_library`/`cc.has_header` candidate search, not
`dependency('<name>')` — and there is no `dftracer.pc` pkg-config file
shipped with a dftracer install (only CMake config files under
`lib64/cmake/dftracer/`). This means meson's `dependency('dftracer')` will
never resolve here, and a project-agnostic `-DCMAKE_PREFIX_PATH=<dftracer>`
flag (the cmake-project convention) has no effect on a meson project either.

**Fix:** point `CFLAGS`/`LDFLAGS` at the dftracer install directly when
configuring:
```
CFLAGS="-I<dftracer_prefix>/include" \
LDFLAGS="-L<dftracer_prefix>/lib64 -Wl,-rpath,<dftracer_prefix>/lib64 -ldftracer_core" \
meson setup <build_dir> <source_dir> -Dprefix=... -Duse_system_flux=true
```
Meson picks up `CFLAGS`/`LDFLAGS` as native default compile/link args at
`meson setup` time. This is a flux-fiction-specific `meson.build` gap (no
`dependency('dftracer')` call was added for the jobtap `shared_module`
target), not something generic session build tooling can resolve — see
`software-meson` for the general native-meson-support note.

---

#### Build against a session-local venv (not the shared framework venv)

If the shared framework venv's `dftracer` package lacks the Python bindings
(`dftracer.python`/`dft_fn`, see `software-flux-fiction` linkage note above
and the `feedback_dftracer_aiml_venv` memory entry), retarget the whole
build+install at a session-local venv that has BOTH `dftracer` and
`pydftracer` installed (`pip show pydftracer` should return a real version,
not "not found"):

1. **Editable install of `annotated/source` into that venv**, using a fresh
   meson build dir (do NOT reuse/reconfigure the `install_ann` build dir from
   an earlier framework-venv build — it caches the old `CFLAGS`/`LDFLAGS` and
   `meson setup --reconfigure` will not re-pick-up new ones):
   ```
   DFT=<session_venv>/lib/python3.13/site-packages/dftracer
   CFLAGS="-I$DFT/include" \
   LDFLAGS="-L$DFT/lib64 -Wl,-rpath,$DFT/lib64 -ldftracer_core" \
     <session_venv>/bin/pip install -e annotated/source/ \
     --config-settings=build-dir=<fresh_build_dir>
   ```
   `--no-build-isolation` will fail here unless `meson`/`meson-python`/`ninja`
   are already installed in the session venv — easier to let pip's build
   isolation install its own copy of meson-python and just pass
   `CFLAGS`/`LDFLAGS` through the environment (pip's isolated build still
   inherits them).

2. **Re-verify `emu-jobtap.so` links against the SESSION venv's dftracer C
   libs**, not the framework venv's — `ldd` on the freshly-built plugin
   should show `libdftracer_core.so.*` resolving under
   `<session_venv>/lib/python3.13/site-packages/dftracer/lib64/`, not
   `/usr/workspace/.../  .venv/...`.

3. **`flux-fiction`'s `jobtap_path.py` candidate search does not know about
   a meson-python editable-install build dir** (it only checks
   `bundled resources`, `<repo>/build/emu-jobtap.so`, and
   `<repo>/build/<subdir>/{,src/}emu-jobtap.so`) — a `pip install -e` with
   `--config-settings=build-dir=<custom>` outside the repo tree will not be
   found automatically. Set `FLUX_FICTION_JOBTAP_SO=<path-to-emu-jobtap.so>`
   explicitly when running `flux-fiction-run` in this situation.

4. **The session venv also needs the Flux Python bindings' own runtime deps**
   installed separately: `cffi`, `pyyaml`, `ply`, `jsonschema` — these are not
   flux-fiction dependencies per se, they're what `/usr/lib64/flux/python3.1x/flux`
   (the system flux-core Python bindings) imports transitively. On Tuolumne
   there is no `python3.13` build of the flux bindings (only up to 3.12), but
   the bindings are pure Python (no compiled `.so` beyond a separate `_flux`
   C extension) — pointing `PYTHONPATH` at `/usr/lib64/flux/python3.12`
   works fine under a 3.13 venv, since it's a single generation off.

5. **Runtime env needed for the actual smoke test/run**, all at once:
   ```
   LD_LIBRARY_PATH=/opt/cray/pe/cce/20.0.0/cce/x86_64/lib:/opt/cray/pe/cce/20.0.0/cce/x86_64/lib/default64:/usr/lib64:<session_venv>/lib/python3.13/site-packages/dftracer/lib64
   PYTHONPATH=/usr/lib64/flux/python3.12
   FLUX_FICTION_JOBTAP_SO=<path-to-emu-jobtap.so-under-custom-build-dir>
   ```

6. **`flux-fiction-run`'s harness launches its own nested Flux broker** — a
   `--run-dir` that already exists from a prior attempt makes `create_run_root`
   raise `FileExistsError`; always use a fresh `--run-dir`/`--tag` per retry.

7. **Fluxion 0.52.0 on Tuolumne does not implement the `sched.quiescent` RPC**
   that flux-fiction's jobtap plugin depends on for step-synchronization
   (`job-manager.err[0]: sched.quiescent failed/unsupported: Unknown service
   method`). The emulator still submits/processes jobs (confirmed via journal
   events and real dftracer trace events emitted), but the quiescence
   probe loop can run long/hang for a full job-trace smoke test on this
   sched-fluxion version. For a SHORT smoke test, either use a very small
   `test-inputs/*.csv` (single node, few jobs) and a hard timeout with the
   understanding it may need to be killed rather than exit(0), or treat
   partial trace output (real `.pfw.gz` files with real event counts) as
   sufficient smoke-test evidence rather than waiting for full completion.
