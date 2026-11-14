"""tools_pydftracer: pydftracer, the Python annotation API package (`dftracer.python`: `dft_fn` / `dftracer.initialize_log` / `finalize`, the `@_dft.log` decorator) that every python_annotate_file / python_annotate_project output imports: install, the import check that must pass before a smoke test, the hidden `typing_extensions` runtime dependency, the stale `dftracer.logger` / `dftracer_fn` API (re-annotate, never shim), and the same-venv rule. Load before any Python annotation build or smoke-test step, or on `ModuleNotFoundError: No module named 'dftracer.python'`, `No module named 'dftracer.logger'`, or `No module named 'typing_extensions'` from an annotated app."""
import json
import re


def _flatten(v):
    if isinstance(v, str):
        return v.splitlines()
    if isinstance(v, dict):
        return [x for i in v.values() for x in _flatten(i)]
    if isinstance(v, list):
        return [x for i in v for x in _flatten(i)]
    return []


def _TOOLS_PYDFTRACER_judge(commands, rules):
    """Apply the rules (forbid / require / require_if / forbid_if regexes) to the proposed commands."""
    items = commands
    if isinstance(commands, str):
        s = commands.strip()
        if s[:1] in "[{":
            try:
                items = json.loads(s)
            except ValueError:
                items = s
    lines = [ln for ln in _flatten(items) if ln.strip()]
    if not lines:
        return {"status": "inconclusive", "checks": [], "verdicts": {},
                "detail": "no commands given: pass the proposed command lines or recipe"}
    text = "\n".join(lines)
    out, verdicts = [], {}
    for r in rules:
        fl = re.I if "i" in r.get("flags", "") else 0
        pat = re.compile(r["pattern"], fl)
        when = re.compile(r["when"], fl) if r.get("when") else None
        kind = r["kind"]
        applies = when is None or bool(when.search(text))
        ok, detail = True, "not applicable"
        if applies and kind in ("forbid", "forbid_if"):
            bad = [ln for ln in lines if pat.search(ln)]
            ok = not bad
            detail = ("found: " + bad[0][:160]) if bad else "absent, as required"
        elif applies and kind in ("require", "require_if"):
            ok = bool(pat.search(text))
            detail = "present" if ok else "missing: " + r["pattern"]
        verdicts[r["id"]] = "n/a" if not applies else ("pass" if ok else "fail")
        out.append({"check": r["id"], "ok": ok, "detail": detail if ok else detail + " -- " + r["why"],
                    "fix": "" if ok else r["fix"]})
    return {"status": "fail" if any(not c["ok"] for c in out) else "pass", "checks": out, "verdicts": verdicts}


def register(mcp):

    @mcp.tool()
    def tools_pydftracer_recipe(section: str = "") -> str:
        """The build/run/env recipe tools_pydftracer knows, as structured JSON: api, error, install, package, stale_api, venv, verify.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (api, error, install, package, stale_api, venv, verify); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what tools_pydftracer_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _TOOLS_PYDFTRACER_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "tools_pydftracer", "sections": sorted(_TOOLS_PYDFTRACER_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _TOOLS_PYDFTRACER_RULES]})

    @mcp.tool()
    def tools_pydftracer_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against tools_pydftracer's rules: no_stale_logger_api; no_logger_shim; import_check_not_bare; typing_extensions_with_install; verify_dftracer_python_import.

        Use on a proposed recipe or command list before running it, and after tools_pydftracer_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_TOOLS_PYDFTRACER_judge(commands, _TOOLS_PYDFTRACER_RULES))


_TOOLS_PYDFTRACER_RECIPE = {'package': {'pypi': 'pydftracer',
             'module': 'dftracer.python',
             'installed_via': 'dftracer dependency (Requires: ... pydftracer ...)',
             'extra_runtime_dep': 'typing_extensions (undeclared, 2026-07-16)'},
 'api': ['from dftracer.python import dftracer, dft_fn as DFTracerFn',
         '_dft = DFTracerFn("<category>")',
         '_dft_log = dftracer.initialize_log(logfile=None, data_dir=None, process_id=None)',
         '@_dft.log',
         'def some_function(...): ...',
         '_dft_log.finalize()'],
 'stale_api': {'import': 'from dftracer.logger import dftracer_fn',
               'decorator': '@dftracer_fn(comp="cpu")',
               'fix': 're-annotate from pristine source via python_annotate_file / python_annotate_project; no shim'},
 'verify': 'python -c "from dftracer.python import dftracer, dft_fn"  # in the app\'s venv, before any smoke test',
 'install': {'preferred': 'session_install_dftracer (pulls pydftracer)',
             'explicit': 'pip install pydftracer typing_extensions',
             'github_develop': 'pip install "git+https://github.com/llnl-asr/dftracer.git@develop" && pip install '
                               'typing_extensions'},
 'venv': 'the same venv the annotated app is installed into and run from',
 'error': "ModuleNotFoundError: No module named 'dftracer.python'"}

_TOOLS_PYDFTRACER_RULES = [{'id': 'no_stale_logger_api',
  'kind': 'forbid',
  'pattern': 'from\\s+dftracer\\.logger\\s+import|@?dftracer_fn\\s*\\(',
  'why': 'dftracer.logger / dftracer_fn is a stale API absent from develop; the current API is dftracer.python.',
  'fix': 'Re-annotate from pristine source with python_annotate_file (dftracer.python, dft_fn).'},
 {'id': 'no_logger_shim',
  'kind': 'forbid',
  'pattern': 'dftracer/logger\\.py|sys\\.modules\\[\\s*[\\"\']dftracer\\.logger',
  'why': 'A compatibility shim hides annotation-tool/API drift.',
  'fix': 'Delete the shim and re-annotate the affected files.'},
 {'id': 'import_check_not_bare',
  'kind': 'forbid',
  'pattern': '-c\\s+[\\"\']\\s*import\\s+dftracer\\s*[\\"\']',
  'why': 'import dftracer can succeed while pydftracer (dftracer.python) is missing.',
  'fix': 'Check python -c "from dftracer.python import dftracer, dft_fn".'},
 {'id': 'typing_extensions_with_install',
  'kind': 'require_if',
  'pattern': 'typing_extensions',
  'when': 'pip\\s+install\\b.*(pydftracer|dftracer)',
  'why': 'typing_extensions is an undeclared runtime dependency of the dftracer.python import.',
  'fix': 'pip install typing_extensions in the same venv.'},
 {'id': 'verify_dftracer_python_import',
  'kind': 'require_if',
  'pattern': 'from\\s+dftracer\\.python\\s+import\\s+dftracer,\\s*dft_fn',
  'when': 'pip\\s+install\\b.*(pydftracer|dftracer)|python_annotate|smoke',
  'why': "Annotated files fail at import unless dftracer.python imports in the app's venv; verify before the smoke "
         'test.',
  'fix': 'Run python -c "from dftracer.python import dftracer, dft_fn" before the smoke test.'}]
