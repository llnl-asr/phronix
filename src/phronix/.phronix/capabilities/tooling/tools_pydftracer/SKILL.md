---
name: tools_pydftracer
description: pydftracer, the Python annotation API package (`dftracer.python`: `dft_fn` / `dftracer.initialize_log` / `finalize`, the `@_dft.log` decorator) that every python_annotate_file / python_annotate_project output imports: install, the import check that must pass before a smoke test, the hidden `typing_extensions` runtime dependency, the stale `dftracer.logger` / `dftracer_fn` API (re-annotate, never shim), and the same-venv rule. Load before any Python annotation build or smoke-test step, or on `ModuleNotFoundError: No module named 'dftracer.python'`, `No module named 'dftracer.logger'`, or `No module named 'typing_extensions'` from an annotated app.
---
Cross-references: [[tools_dftracer]] [[tools_dftracer_utils]] [[dftracer_annotate_python]] [[dftracer_smoke]] [[dftracer_install]] [[software_flux_fiction]] [[capability_builder]]

# tools_pydftracer

Converted from dftracer-agents skill `tools-pydftracer`. Tools: `tools_pydftracer_recipe` (predictor) and `tools_pydftracer_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- pydftracer is a separate PyPI package from dftracer; it supplies the `dftracer.python` API that annotated files import: `from dftracer.python import dftracer, dft_fn as DFTracerFn`, `_dft = DFTracerFn("<category>")`, `_dft_log = dftracer.initialize_log(logfile=None, data_dir=None, process_id=None)`, `@_dft.log`, `_dft_log.finalize()`.
- Before any smoke test of annotated Python, run `python -c "from dftracer.python import dftracer, dft_fn"` in the app's venv; if it fails, fix the install first. `import dftracer` alone is not sufficient.
- pydftracer normally comes in as a dftracer dependency; if missing, reinstall dftracer cleanly into a fresh session venv, or `pip install pydftracer` (or the GitHub-develop dftracer install), matching the source session_install_dftracer uses.
- Install `typing_extensions` alongside: it is an undeclared runtime dependency of the `dftracer.python` import (2026-07-16).
- `dftracer.python` (`dft_fn`, `dftracer.initialize_log`) is the current API; `from dftracer.logger import dftracer_fn` / `@dftracer_fn(comp=...)` is stale (no `dftracer.logger` on develop, 2026-07-16).
- Never write a compatibility shim for `dftracer.logger`: re-annotate the affected files from pristine source with the MCP tool and delete any stopgap shim.
- pydftracer must be importable in the SAME venv the traced Python app is installed into and run from.

## Constraints
- Verification is the import check, not `pip show pydftracer`.

## Corner cases
### `ModuleNotFoundError: No module named 'dftracer.python'`
Cause: pydftracer not installed/importable in the app's venv (or an incomplete dftracer install, see tools_dftracer). Fix: reinstall dftracer cleanly into the session venv or `pip install pydftracer`. Verify: `python -c "from dftracer.python import dftracer, dft_fn"`.

### `from dftracer.python import ...` fails after a successful `pip install git+https://github.com/llnl-asr/dftracer.git@develop` (missing typing_extensions)
Cause: typing_extensions is not declared by dftracer or pydftracer. Fix: `pip install typing_extensions`, then re-run the import check. (2026-07-16, flux-fiction session)

### `No module named 'dftracer.logger'` / code uses `@dftracer_fn(comp="cpu")`
Stale pattern from an older manual/AST-fallback annotation pass. Fix: re-annotate from pristine source with python_annotate_file/python_annotate_project; remove any shim. (resolved 2026-07-16)

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `tools_pydftracer_recipe` renders the recipe; validator `tools_pydftracer_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_stale_logger_api` fails: Re-annotate from pristine source with python_annotate_file (dftracer.python, dft_fn). Then render with `tools_pydftracer_recipe` and validate again.
- `no_logger_shim` fails: Delete the shim and re-annotate the affected files. Then render with `tools_pydftracer_recipe` and validate again.
- `import_check_not_bare` fails: Check python -c "from dftracer.python import dftracer, dft_fn". Then render with `tools_pydftracer_recipe` and validate again.
- `typing_extensions_with_install` fails: pip install typing_extensions in the same venv. Then render with `tools_pydftracer_recipe` and validate again.
- `verify_dftracer_python_import` fails: Run python -c "from dftracer.python import dftracer, dft_fn" before the smoke test. Then render with `tools_pydftracer_recipe` and validate again.
- If annotated files mix `dftracer.logger` and `dftracer.python`, re-annotate the stale ones from pristine source rather than editing imports by hand.

## Self-heal
- If a pydftracer release declares typing_extensions, drop the typing_extensions rule with capability_update and record the version.

## Self-learn
- Record API drift between python_annotate_* output and the installed pydftracer as a dated lesson here.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this tool goes into tools_pydftracer via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (2026-07-16, flux-fiction) `pip install "git+https://github.com/llnl-asr/dftracer.git@develop"` + `pip install typing_extensions`, then `python -c "from dftracer.python import dftracer, dft_fn"` passes.

## Source: dftracer-agents `tools-pydftracer` (verbatim, headings demoted)
_Original description:_ pydftracer — the Python annotation API package (dftracer.python module, dft_fn/dftracer_fn decorators, initialize_log/finalize). Install verification, common ModuleNotFoundError, and the API surface every python_annotate_file-generated file depends on. Load this skill before any Python annotation build/smoke-test step.

#### What it provides

`pydftracer` is a separate PyPI package from `dftracer` (see [[tools-dftracer]])
that supplies the pure-Python decorator API every dftracer-annotated `.py` file
imports:

```python
from dftracer.python import dftracer, dft_fn as DFTracerFn

_dft = DFTracerFn("<category>")
_dft_log = dftracer.initialize_log(logfile=None, data_dir=None, process_id=None)

@_dft.log
def some_function(...): ...

_dft_log.finalize()
```

This is exactly the API `python_annotate_file`/`python_annotate_project`
generate (see `annotation_python.py`) — if this package isn't installed and
importable in the SAME venv the annotated app runs in, every annotated file
fails at import time with:
```
ModuleNotFoundError: No module named 'dftracer.python'
```

#### Verification (always do this before running a smoke test on annotated Python)

```bash
python -c "from dftracer.python import dftracer, dft_fn"
```
If this fails, do NOT proceed to the smoke test — fix the install first (see
[[tools-dftracer]] for the install-source options and the "dftracer without
pydftracer" bug pattern). Checking `import dftracer` alone is NOT sufficient —
the C-core package can be present and importable while `pydftracer` (and thus
`dftracer.python`) is missing.

#### Install

`pydftracer` is normally pulled in automatically as a `dftracer` dependency
(`pip show dftracer` → `Requires: ... pydftracer ...`). If it's missing despite
that, either:
- the `dftracer` install was incomplete/non-standard (see [[tools-dftracer]]
  bug note) — reinstall `dftracer` cleanly into a fresh session venv, or
- install it explicitly: `pip install pydftracer` (PyPI) or as part of a
  GitHub-develop pip install of the `dftracer` repo, whichever source
  `session_install_dftracer` is using for this session.

#### typing_extensions is a hidden runtime dependency

Observed 2026-07-16 (flux-fiction session): `pip install "git+https://github.com/llnl-asr/dftracer.git@develop"`
succeeds and installs `pydftracer`, but `from dftracer.python import dftracer, dft_fn`
still fails until `typing_extensions` is ALSO installed — it is not currently
declared as a dependency of either package. Install it alongside:
`pip install typing_extensions`. Verify with the import check above, not just
`pip show pydftracer` succeeding.

#### OPEN QUESTION — two different decorator API patterns seen across sessions (do not silently paper over)

The `python_annotate_file`/`python_annotate_project` MCP tools generate:
```python
from dftracer.python import dftracer, dft_fn as DFTracerFn
_dft = DFTracerFn("<category>")
@_dft.log
```
But at least one session observed a DIFFERENT pattern already present/expected
in annotated code:
```python
from dftracer.logger import dftracer_fn
@dftracer_fn(comp="cpu")
```
`dftracer.logger` does not exist on the `develop` branch installed 2026-07-16.
**RESOLVED 2026-07-16: `dftracer.python` (`dft_fn`, `dftracer.initialize_log`)
is the correct, current API** — the one `python_annotate_file`/
`python_annotate_project` actually generate. `dftracer.logger`/`dftracer_fn(...)`
was a stale pattern from files annotated by an older manual/AST-fallback pass
that predated (or diverged from) the MCP tool. **Do not write a compatibility
shim to make the old import path resolve** — a shim just hides an
annotation-tool/API drift bug. Fix it at the source: re-annotate the affected
file(s) from pristine source via the MCP tool so they use `dftracer.python`
like everything else, and delete any shim that was added as a stopgap.

#### Venv-sharing rule

The venv where `pydftracer` is importable MUST be the same venv the traced
Python app is installed into and run from — never install dftracer's Python
bindings into one venv and run the annotated app from another. See
[[feedback_dftracer_aiml_venv]].
