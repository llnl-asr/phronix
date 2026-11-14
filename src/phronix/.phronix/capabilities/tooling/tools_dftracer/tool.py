"""tools_dftracer: The dftracer PyPI package (C core + CMake build): package trio (dftracer-utils, pydftracer, pybind11), install sources (default: the PyPI prerelease composed for the run with `dftracer[modules]` + `dftracer-compose`; source builds only on request), source-build env (CC/CXX/LD_LIBRARY_PATH and DFTRACER_ENABLE_* before pip), session-local vs shared venv, runtime env (DFTRACER_INC_METADATA), the broken packaged CMake config for C++ consumers, dftracer_service 0-byte traces, and dftracer_merge sharp edges. Load before any session_install_dftracer call, or on: `ModuleNotFoundError: No module named 'dftracer.python'`, `only virtual member functions can be marked 'override'` in brahma/posix.h, `The imported target dftracer_core references the file /project/build/...`, `brahma_DIR` not found, `CXXABI_1.3.13`/`GLIBCXX_3.4.29` not found, `hwloc reports the number of cores (1) mod the number of sockets (2) is not zero`, a 0-byte `service_<host>.pfw.gz`, `No .pfw or .pfw.gz files found in directory`, `Output file should have .pfw extension`, empty event args, or 'dftracer works but X sub-feature (MPI/HDF5/PAPI) is missing'."""
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


def _TOOLS_DFTRACER_judge(commands, rules):
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
    def tools_dftracer_recipe(section: str = "") -> str:
        """The build/run/env recipe tools_dftracer knows, as structured JSON: cmake_consumer, install_default, install_pypi_pre_sdist, install_source, merge, order, packages, reinstall, runtime_env, service, stale_brahma_check, trace_bind_check, tuolumne_link, venv.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (cmake_consumer, install_default, install_pypi_pre_sdist, install_source, merge, order, packages, reinstall, runtime_env, service, stale_brahma_check, trace_bind_check, tuolumne_link, venv); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what tools_dftracer_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _TOOLS_DFTRACER_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "tools_dftracer", "sections": sorted(_TOOLS_DFTRACER_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _TOOLS_DFTRACER_RULES]})

    @mcp.tool()
    def tools_dftracer_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against tools_dftracer's rules: no_uncomposed_prerelease; prerelease_needs_compose; source_build_cc_cxx_first; no_manual_clone_cmake; no_find_package_on_prerelease; inc_metadata_with_enable; service_stop_wait_flush; merge_output_pfw; no_dftracer_compact; no_blind_lstdcxxfs.

        Use on a proposed recipe or command list before running it, and after tools_dftracer_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_TOOLS_DFTRACER_judge(commands, _TOOLS_DFTRACER_RULES))


_TOOLS_DFTRACER_RECIPE = {'packages': {'dftracer': 'C core, tracing runtime, CMake build',
              'dftracer-utils': 'trace-utils bindings (split/merge/read)',
              'pydftracer': 'dftracer.python annotation API',
              'pybind11': 'build dep',
              'dftracer-modules': 'prebuilt optional modules wheel (prerelease)',
              'requires': ['dftracer-utils', 'pybind11', 'pydftracer', 'setuptools', 'setuptools-scm'],
              'repos': 'github.com/llnl-asr/{dftracer,dftracer-utils,pydftracer,dfanalyzer,dfdiagnoser}',
              'install_order': ['dftracer', 'dftracer-utils']},
 'install_default': {'mode': 'prebuilt="compose" (session_install_dftracer default, 2026-11)',
                     'commands': ['${PREFIX}/venv/bin/pip install --pre "dftracer[modules]" dftracer-modules',
                                  '${PREFIX}/venv/bin/dftracer-compose --enable mpi,hdf5 --disable '
                                  'papi,hwloc,hip,cuda',
                                  '${PREFIX}/venv/bin/dftracer_install_info --composition'],
                     'modules': ['mpi (common MPIs + Cray MPICH)',
                                 'hdf5 (serial, parallel)',
                                 'papi',
                                 'hwloc',
                                 'hip (rocprofiler-sdk)',
                                 'cuda (CUPTI)'],
                     'verify': 'tool result compose.linked / compose.absent, or dftracer_install_info --composition',
                     'absent_fix': "load the library's module in env.sh, re-run scripts/compose_dftracer.sh",
                     'never': 'prebuilt="prerelease" (uncomposed: POSIX, STDIO, annotations only)'},
 'install_source': {'when': 'user asks, or a non-release branch/fork',
                    'tool': 'session_install_dftracer(prebuilt="auto", dftracer_ref=<ref>, dftracer_repo=<repo>)',
                    'pip': 'pip install "git+https://github.com/llnl-asr/dftracer.git@<ref>"',
                    'env_before_pip': {'CC': "$(which mpicc) or the app's C compiler",
                                       'CXX': "$(which mpic++) / mpicxx or the app's C++ compiler",
                                       'LD_LIBRARY_PATH': '<compiler-runtime-lib-dirs>:/usr/lib64 (Cray '
                                                          'PE):$LD_LIBRARY_PATH',
                                       'DFTRACER_ENABLE_PYTHON': 'ON',
                                       'DFTRACER_ENABLE_HDF5': 'ON only if the app uses HDF5 (+ HDF5_ROOT / '
                                                               'HDF5_DIR)',
                                       'DFTRACER_BUILD_TYPE': '<type>',
                                       'MPICC/MPICXX': 'set by the tool'},
                    'verify': ['grep -E "PAPI_TRACING_ENABLE|MPI_ENABLE|HIP_TRACING_ENABLE" '
                               '<prefix>/include/dftracer/core/dftracer_config.hpp',
                               'ldd <prefix>/lib64/libdftracer_core.so | grep -i mpi  # exactly one libmpi'],
                    'never': 'manual git clone + cmake'},
 'install_pypi_pre_sdist': {'tool': 'session_install_dftracer(dftracer_repo="pypi-pre", mpi=True, papi=False, '
                                    'hip=False, variorum=False, hdf5=False)',
                            'pip_flags': '--no-binary dftracer --no-deps',
                            'avoid': '--no-binary :all:',
                            'extract_to': '<WS>/tmp/dftracer_sdist',
                            'verify': ['dftracer_config.hpp: DFTRACER_MPI_ENABLE 1',
                                       'libdftracer_core.so links libmpi_cray']},
 'order': 'build the app first, then dftracer against its compiler/MPI/venv (app_built_override=True for hand-built '
          'apps)',
 'venv': {'rule': 'session-local venv shared by dftracer and the app; never the shared framework venv',
          'verify': 'python -c "from dftracer.python import dftracer, dft_fn"'},
 'reinstall': ['rm -rf <venv>/lib/pythonX.Y/site-packages/dftracer <venv>/bin/dftracer_service',
               'pip uninstall -y dftracer pydftracer dftracer-utils',
               'or: session_remove_path(relpath="venv", recursive=True)'],
 'stale_brahma_check': 'grep -c readv <venv>/lib/pythonX.Y/site-packages/dftracer/include/brahma/interface/posix.h  '
                       '# 0 = stale',
 'runtime_env': {'DFTRACER_ENABLE': '1',
                 'DFTRACER_LOG_FILE': '<trace prefix>',
                 'DFTRACER_DATA_DIR': '<data dirs>',
                 'DFTRACER_INC_METADATA': '1 (else event args dropped)',
                 'DFTRACER_VARIORUM_LIBRARY': 'path to libvariorum.so (>= 0.8) when not the system one',
                 'DFTRACER_DISABLE_VARIORUM_POWER': '1 on 2-socket nodes with a 1-core service'},
 'cmake_consumer': {'broken': 'find_package(dftracer CONFIG) against the prerelease wheel (IMPORTED_LOCATION '
                              '/project/build/..., brahma required)',
                    'works': '-I<pkg>/include -L<pkg>/lib64 -ldftracer_core (session_build_annotated, generated .pc)',
                    'imported_target': ['add_library(dftracer_core_imported SHARED IMPORTED)',
                                        'set_target_properties(dftracer_core_imported PROPERTIES IMPORTED_LOCATION '
                                        '"${DFTRACER_ROOT}/lib64/libdftracer_core.so" INTERFACE_INCLUDE_DIRECTORIES '
                                        '"${DFTRACER_ROOT}/include")',
                                        'target_link_libraries(<target> PRIVATE dftracer_core_imported)'],
                    'dftracer_root': '<venv>/lib/pythonX.Y/site-packages/dftracer'},
 'service': {'placement': 'one dftracer_service per node, pinned to one core (-N n -n n -c1)',
             'two_socket_variorum': 'export DFTRACER_DISABLE_VARIORUM_POWER=1 (or -c2)',
             'check_err': '<log_dir>/dftracer_server_<host>.err',
             'variorum_linkage': 'ldd $(which dftracer_service) | grep variorum',
             'stop_wait': ['"$DFT_SVC_BIN" stop "$DFT_SVC_DIR"',
                           'T="${DFTRACER_LOG_FILE}_$(hostname).pfw.gz"',
                           'for _i in $(seq 1 60); do [ -s "$T" ] && break; sleep 1; done',
                           '[ -s "$T" ] || echo "WARN: service trace $T still empty after 60s" >&2'],
             'slurm': 'service as a long-lived step (start, wait for flag file, stop, wait for flush); app as a '
                      'separate --overlap step on the same --nodelist'},
 'merge': {'tool': 'dftracer_merge (no dftracer_compact)',
           'recursive': False,
           'output_ext': '.pfw (+ --compress for .pfw.gz)',
           'example': 'dftracer_merge -d "$leaf/raw/<set>" -o "$leaf/compacted/<set>.pfw" --compress --force'},
 'tuolumne_link': {'lstdcxxfs': 'only if a std::filesystem test link fails without it',
                   'rpath': 'patchelf libs in dftracer/lib64 so /opt/cray/pe/gcc-libs precedes /usr/lib64; ldd '
                            'clean'},
 'trace_bind_check': 'end record cfg.bind:0 with build.mpi:1 = initialized before INIT (pre-main constructors)'}

_TOOLS_DFTRACER_RULES = [{'id': 'no_uncomposed_prerelease',
  'kind': 'forbid',
  'pattern': 'prebuilt\\s*=\\s*[\\"\']prerelease[\\"\']',
  'why': 'The uncomposed prerelease wheel traces POSIX, STDIO and annotations only (no MPI/HDF5/PAPI).',
  'fix': 'Use the default prebuilt="compose".'},
 {'id': 'prerelease_needs_compose',
  'kind': 'require_if',
  'pattern': 'dftracer-compose\\b',
  'when': 'pip\\s+install\\s+(--pre\\s+)?[\\"\']?dftracer(\\[modules\\])?[\\"\']?(\\s|$).*|pip\\s+install\\s+--pre\\b.*dftracer',
  'why': 'A prerelease install without dftracer-compose links none of the optional modules (MPI, HDF5, PAPI...).',
  'fix': 'Install dftracer[modules] dftracer-modules and run dftracer-compose --enable <features>.'},
 {'id': 'source_build_cc_cxx_first',
  'kind': 'require_if',
  'pattern': '(?s)export\\s+CC=.*export\\s+CXX=.*pip\\s+install',
  'when': 'pip\\s+install\\s+[\\"\']?git\\+https://github\\.com/llnl-asr/dftracer',
  'why': "dftracer's pip install compiles a C/C++ extension; without CC/CXX bound to the app's compiler/MPI it links "
         'the wrong ABI.',
  'fix': 'export CC/CXX (and LD_LIBRARY_PATH, DFTRACER_ENABLE_*) before pip install.'},
 {'id': 'no_manual_clone_cmake',
  'kind': 'forbid',
  'pattern': 'git\\s+clone\\s+\\S*llnl-asr/dftracer(\\.git)?(\\s|$)',
  'why': 'Source builds go through session_install_dftracer / pip (CMake two-pass bootstrap), never a manual clone + '
         'cmake.',
  'fix': 'session_install_dftracer(prebuilt="auto", dftracer_ref=..., dftracer_repo=...).'},
 {'id': 'no_find_package_on_prerelease',
  'kind': 'forbid_if',
  'pattern': 'find_package\\s*\\(\\s*dftracer\\b',
  'when': '--pre\\b|dftracer-compose|dftracer-modules',
  'why': "The prerelease wheel's CMake config references build-machine paths (/project/build/...) and requires an "
         'unshipped brahma.',
  'fix': 'Link -I<pkg>/include -L<pkg>/lib64 -ldftracer_core or use a manual IMPORTED target.'},
 {'id': 'inc_metadata_with_enable',
  'kind': 'require_if',
  'pattern': 'DFTRACER_INC_METADATA=1',
  'when': 'DFTRACER_ENABLE=1',
  'why': "Without DFTRACER_INC_METADATA=1 every event's args payload (comp=, tags) is silently dropped.",
  'fix': 'export DFTRACER_INC_METADATA=1 alongside DFTRACER_ENABLE=1.'},
 {'id': 'service_stop_wait_flush',
  'kind': 'require_if',
  'pattern': '\\[\\s*-s\\s+\\S+\\s*\\]',
  'when': 'dftracer_service\\S*\\s+stop|DFT_SVC_BIN\\S*\\s+stop',
  'why': 'stop returns before the async flush; ending the step kills the daemon and leaves a 0-byte trace.',
  'fix': 'Poll until the service trace is non-empty (for ...; do [ -s "$T" ] && break; sleep 1; done).'},
 {'id': 'merge_output_pfw',
  'kind': 'forbid',
  'pattern': 'dftracer_merge\\b.*-o\\s+\\S+\\.pfw\\.gz',
  'why': 'dftracer_merge rejects a .pfw.gz output name (Output file should have .pfw extension).',
  'fix': 'Use -o <name>.pfw --compress.'},
 {'id': 'no_dftracer_compact',
  'kind': 'forbid',
  'pattern': '(^|[;&|]\\s*)dftracer_compact\\b',
  'why': 'There is no dftracer_compact in current builds; dftracer_merge is the compaction tool.',
  'fix': 'dftracer_merge -d <leaf> -o <out>.pfw --compress.'},
 {'id': 'no_blind_lstdcxxfs',
  'kind': 'forbid',
  'pattern': '-lstdc\\+\\+fs\\b',
  'why': "On Tuolumne Cray clang picks gcc-toolset-13's static libstdc++fs.a and the dftracer_service link fails.",
  'fix': 'Add -lstdc++fs only if a std::filesystem test link fails without it.'}]
