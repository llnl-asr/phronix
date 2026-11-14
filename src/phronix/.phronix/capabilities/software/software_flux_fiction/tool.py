"""software_flux_fiction: Flux-Fiction (Flux scheduling emulator: Meson-built C jobtap plugin emu-jobtap.so + Python package) build, dftracer linking, annotation and run facts: annotate the EMULATED job timeline with manual log_event (simulated time from FakeTimeController, one event per allocated node tagged mhost), DFTRACER_INC_METADATA=1, explicit initialize_log/finalize, CFLAGS/LDFLAGS dftracer link for Meson, session-venv editable install, Flux Python bindings deps, MockAdapter diagnostic. Load when building or annotating flux-fiction, or on: "call to undeclared function 'strdup'; ISO C99 and later do not support implicit function declarations"; 'log_event(): incompatible function arguments'; trace with no job_submit/job_start/job_complete or no args; dependency('dftracer') not found; emu-jobtap.so not found; FileExistsError from create_run_root; missing ../test-inputs file; "Unknown service method 'sched.quiescent': Function not implemented"; 'TypeError: Object of type method is not JSON serializable'."""
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


def _SOFTWARE_FLUX_FICTION_judge(commands, rules):
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
    def software_flux_fiction_recipe(section: str = "") -> str:
        """The build/run/env recipe software_flux_fiction knows, as structured JSON: annotation, c99_fix, deps_tuolumne, detect, dftracer_link, install_layout, run, runtime_env, verify.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (annotation, c99_fix, deps_tuolumne, detect, dftracer_link, install_layout, run, runtime_env, verify); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_flux_fiction_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_FLUX_FICTION_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_flux_fiction", "sections": sorted(_SOFTWARE_FLUX_FICTION_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_FLUX_FICTION_RULES]})

    @mcp.tool()
    def software_flux_fiction_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_flux_fiction's rules: inc_metadata_with_dftracer; no_pkgconfig_dftracer; no_cmake_prefix_on_meson; annotated_build_links_dftracer; no_posix_c_source_for_strdup; log_event_args_tuples; mhost_one_event_per_node; no_reserved_hhash; simulated_time_not_wallclock; config_cwd.

        Use on a proposed recipe or command list before running it, and after software_flux_fiction_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_FLUX_FICTION_judge(commands, _SOFTWARE_FLUX_FICTION_RULES))


_SOFTWARE_FLUX_FICTION_RECIPE = {'detect': {'build_system': 'Meson (meson.build, default_options c_std=c99) + Python package',
            'native': 'src/jobtap shared_module emu-jobtap.so',
            'python_api': 'flux_fiction.api.client.FluxFiction',
            'cli': 'flux-fiction-run config.toml [--tag <name>] [--no-faketime] [--run-dir <dir>]'},
 'deps_tuolumne': {'jansson': 'system, pkg-config --exists jansson (2.14+)',
                   'flux-core': 'system, pkg-config --exists flux-core; meson -Duse_system_flux=true (default)',
                   'flux-sched': 'not required for the build',
                   'flux_python_bindings': '/usr/lib64/flux/python3.12 (pure Python; usable from 3.13 via '
                                           'PYTHONPATH)',
                   'venv_pip': ['cffi', 'pyyaml', 'ply', 'jsonschema']},
 'c99_fix': {'file': 'src/meson.build (jobtap shared_module)',
             'c_args': ['-Wall', '-Wextra', '-I<flux_include_dir>', '-D_GNU_SOURCE'],
             'not': '-D_POSIX_C_SOURCE=200112L (ignored by Cray clang under -std=c99)'},
 'dftracer_link': {'why': 'no dftracer.pc; meson.build uses cc.find_library for flux-core only; CMAKE_PREFIX_PATH '
                          'ineffective',
                   'meson_setup': 'CFLAGS="-I<dft>/include" LDFLAGS="-L<dft>/lib64 -Wl,-rpath,<dft>/lib64 '
                                  '-ldftracer_core" meson setup <build_dir> <source_dir> -Dprefix=${PREFIX} '
                                  '-Duse_system_flux=true',
                   'session_venv_dft': '<session_venv>/lib/python3.13/site-packages/dftracer',
                   'editable': 'CFLAGS=... LDFLAGS=... <session_venv>/bin/pip install -e annotated/source/ '
                               '--config-settings=build-dir=<fresh_build_dir>',
                   'build_isolation': 'keep it (no --no-build-isolation unless meson, meson-python, ninja are in the '
                                      'venv)',
                   'verify': 'ldd emu-jobtap.so -> libdftracer_core.so.* under the session venv',
                   'fresh_build_dir': True,
                   'venv_check': 'pip show pydftracer returns a version'},
 'install_layout': {'python': '<prefix>/lib/python<X.Y>/site-packages/flux_fiction/',
                    'plugin': '<prefix>/lib/python<X.Y>/site-packages/flux_fiction/_native/emu-jobtap.so',
                    'locator': 'flux_fiction.cli.jobtap_path.jobtap_plugin_path() (searches bundled, '
                               '<repo>/build/emu-jobtap.so, <repo>/build/<subdir>/{,src/}emu-jobtap.so)',
                    'rpath': 'install_rpath = flux-core lib dir (relocatable)'},
 'runtime_env': {'DFTRACER_ENABLE': '1',
                 'DFTRACER_INC_METADATA': '1',
                 'DFTRACER_LOG_FILE': '<WS>/traces/<run>/trace',
                 'DFTRACER_DATA_DIR': 'all',
                 'DFTRACER_TIME_METRIC': 'NS (log_event times in ns)',
                 'LD_LIBRARY_PATH': '/opt/cray/pe/cce/20.0.0/cce/x86_64/lib:/opt/cray/pe/cce/20.0.0/cce/x86_64/lib/default64:/usr/lib64:<session_venv>/lib/python3.13/site-packages/dftracer/lib64',
                 'PYTHONPATH': '/usr/lib64/flux/python3.12',
                 'FLUX_FICTION_JOBTAP_SO': '<build_dir>/src/emu-jobtap.so (required for a custom build-dir)'},
 'run': {'mock': {'config': 'mock_config.toml (backend = "mock")', 'cwd': 'annotated/source'},
         'real': {'config': 'src/config.toml',
                  'cwd': 'annotated/source/src',
                  'command': 'flux-fiction-run config.toml --tag <tag> --no-faketime',
                  'blocker': 'sched.quiescent missing in Fluxion 0.52.0'},
         'harness': 'starts its own nested Flux broker; needs Flux Python bindings importable',
         'retry': 'fresh --run-dir / --tag each attempt',
         'real_smoke': 'tiny test-inputs CSV (single node, few jobs) + hard timeout; partial .pfw.gz with real '
                       'events counts as smoke evidence'},
 'annotation': {'manual_log_event': {'module': '_core/engine.py Simulation',
                                     'functions': ['add_event(self, time, callback)',
                                                   'submit_job(self, job)',
                                                   'start_job(self, jobid)',
                                                   'complete_job(self, job)'],
                                     'low_priority': ['_next_event_time(self)'],
                                     'api': 'dftracer.get_instance().log_event(name, cat, start_time, duration, '
                                            'int_args, string_args, float_args)',
                                     'cat': 'simulation',
                                     'names': ['job_submit', 'job_start', 'job_complete'],
                                     'time_source': '_core/faketime.py FakeTimeController.advance_to / '
                                                    'current_effective_time / target_time (never time.time())',
                                     'units': 'nanoseconds'},
                'args_format': {'int_args': {'job_id': '(0, int(jobid))'},
                                'string_args': {'mhost': '(0, node_id)'},
                                'tag_type': '0 = TagType.KEY'},
                'per_node': 'nodes, _src = self.adapter.nodelist_lookup(jobid); job.allocated_nodes = nodes; for '
                            "node_id in [str(n) for n in sorted(nodes)] or ['']: log_event(... string_args={'mhost': "
                            '(0, node_id)})',
                'reserved_keys': ['hhash', 'fhash'],
                'entry_point': {'file': 'cli/support/run_api_experiment.py',
                                'init': 'dftracer.python.dftracer.initialize_log(logfile=..., data_dir=...)',
                                'finalize': 'in finally: around main'},
                'auto_decorator_ok': ['generic file/network I/O (wall-clock)',
                                      '_adapters/flux/* real RPCs (per-function judgment)'],
                'never_decorate': ['@property methods such as _core/models.py Job.jobspec'],
                'order': 'manual simulated-clock pass first, then python_annotate_project for the rest'},
 'verify': {'events': 'reader / event_count for job_submit, job_start, job_complete with mhost args',
            'per_node': 'a job on N nodes yields N job_start and N job_complete events'}}

_SOFTWARE_FLUX_FICTION_RULES = [{'id': 'inc_metadata_with_dftracer',
  'kind': 'require_if',
  'pattern': 'DFTRACER_INC_METADATA=1',
  'when': 'DFTRACER_ENABLE=1',
  'why': 'Without DFTRACER_INC_METADATA=1 every log_event args payload (mhost, job_id) is silently dropped.',
  'fix': 'Set DFTRACER_INC_METADATA=1 alongside DFTRACER_ENABLE/LOG_FILE/DATA_DIR.'},
 {'id': 'no_pkgconfig_dftracer',
  'kind': 'forbid',
  'pattern': 'dependency\\(\\s*[\'"]dftracer|pkg-config\\s+[^|;\\n]*dftracer',
  'why': "dftracer ships no .pc file, so meson dependency('dftracer') / pkg-config never resolve.",
  'fix': 'Pass CFLAGS=-I<dft>/include and LDFLAGS=-L<dft>/lib64 -Wl,-rpath,<dft>/lib64 -ldftracer_core at meson '
         'setup / pip install time.'},
 {'id': 'no_cmake_prefix_on_meson',
  'kind': 'forbid_if',
  'pattern': '-DCMAKE_PREFIX_PATH',
  'when': 'meson\\s+setup|pip\\s+install\\s+-e',
  'why': 'CMAKE_PREFIX_PATH is a CMake convention; it has no effect on this Meson project.',
  'fix': 'Use CFLAGS/LDFLAGS pointing at the dftracer install.'},
 {'id': 'annotated_build_links_dftracer',
  'kind': 'require_if',
  'pattern': 'LDFLAGS=[^\\n]*-ldftracer_core',
  'when': '(meson\\s+setup|pip\\s+install\\s+-e)[^\\n]*(annotated|build_ann)',
  'why': 'The annotated jobtap plugin needs libdftracer_core and meson.build has no dftracer dependency.',
  'fix': 'Prefix the configure/install with LDFLAGS="-L<dft>/lib64 -Wl,-rpath,<dft>/lib64 -ldftracer_core" (and '
         'CFLAGS=-I<dft>/include).'},
 {'id': 'no_posix_c_source_for_strdup',
  'kind': 'forbid',
  'pattern': '-D_POSIX_C_SOURCE',
  'why': 'Cray clang ignores _POSIX_C_SOURCE under strict -std=c99, so strdup stays undeclared.',
  'fix': 'Use -D_GNU_SOURCE in the jobtap shared_module c_args.'},
 {'id': 'log_event_args_tuples',
  'kind': 'forbid',
  'pattern': '(int_args|string_args|float_args)\\s*=\\s*\\{\\s*[\'"][^\'"]+[\'"]\\s*:\\s*(?![\\s(])',
  'why': "The native log_event requires (tag_type, value) tuples; bare values raise 'incompatible function "
         "arguments', silently swallowed.",
  'fix': 'Write {"job_id": (0, int(jobid))} / {"mhost": (0, node_id)}.'},
 {'id': 'mhost_one_event_per_node',
  'kind': 'forbid',
  'pattern': 'mhost[^\\n]*[\'"],\\s*[\'"]\\.join',
  'why': 'A comma-joined node list in mhost cannot be grouped per node.',
  'fix': 'Loop over the allocated nodes and call log_event once per node with string_args={"mhost": (0, node_id)}.'},
 {'id': 'no_reserved_hhash',
  'kind': 'forbid',
  'pattern': '(string_args|int_args)[^\\n]*[\'"]hhash[\'"]',
  'why': 'hhash is reserved and populated by the trace indexer from the real hostname.',
  'fix': 'Use the custom key mhost.'},
 {'id': 'simulated_time_not_wallclock',
  'kind': 'forbid',
  'pattern': 'log_event\\([^\\n]*time\\.(time|perf_counter|monotonic)(_ns)?\\(',
  'why': 'Job events must carry the simulated clock (FakeTimeController), not wall-clock time.',
  'fix': "Derive start_time/duration (ns) from FakeTimeController / the Job's simulated timestamps."},
 {'id': 'config_cwd',
  'kind': 'forbid',
  'pattern': 'flux-fiction-run\\s+src/config\\.toml',
  'why': 'remap_path() resolves config-relative paths against the CWD; src/config.toml from annotated/source '
         'resolves ../test-inputs one level too high.',
  'fix': 'cd annotated/source/src and run flux-fiction-run config.toml.'}]
