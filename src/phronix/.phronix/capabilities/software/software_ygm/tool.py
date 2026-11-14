"""software_ygm: YGM (github.com/llnl/ygm), LLNL's header-only C++20 async MPI messaging library, annotated with dftracer: include <dftracer/dftracer.h> in every annotated header (split .hpp/.ipp), manual annotation of .ipp files (clang_extract_functions returns 0), linking dftracer through a manual IMPORTED target (-DDFTRACER_ROOT), PrgEnv-gnu + gcc-native/11.2 instead of Cray-clang 20 (spdlog/fmt consteval error), from-source dftracer with DFTRACER_ENABLE_MPI=ON / CRAYMPICH / BRAHMA_MPI_VERSION=900001 built with the SAME MPI wrapper, and the test_comm.cpp smoke test. Load for YGM builds/annotation, or on DFTRACER_CPP_* undefined inside ygm detail headers, 0 functions from clang_extract_functions on comm.ipp, `consteval` not a constant expression in fmt under Cray-clang, undefined dftracer symbols at link, or both libmpi_cray and libmpi_gnu_112 in one process. Benchmark runs live in workload_ygm_bench."""
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


def _SOFTWARE_YGM_judge(commands, rules):
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
    def software_ygm_recipe(section: str = "") -> str:
        """The build/run/env recipe software_ygm knows, as structured JSON: annotation, dftracer_from_source, link_dftracer, project, session, smoke, toolchain_tuolumne.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (annotation, dftracer_from_source, link_dftracer, project, session, smoke, toolchain_tuolumne); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_ygm_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_YGM_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_ygm", "sections": sorted(_SOFTWARE_YGM_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_YGM_RULES]})

    @mcp.tool()
    def software_ygm_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_ygm's rules: ygm_no_cray_clang; ygm_cxx20; dftracer_mpi_impl_craympich; brahma_mpi_version; verify_single_mpi_runtime; annotated_build_links_dftracer.

        Use on a proposed recipe or command list before running it, and after software_ygm_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_YGM_judge(commands, _SOFTWARE_YGM_RULES))


_SOFTWARE_YGM_RECIPE = {'project': {'repo': 'github.com/llnl/ygm',
             'type': 'header-only C++ MPI async messaging',
             'build': 'CMake',
             'cxx_standard': 20,
             'deps_fetchcontent': ['Boost 1.87', 'Cereal', 'spdlog (bundled fmt)'],
             'tests': '-DYGM_BUILD_TESTS=ON (test/)',
             'benchmark': 'github.com/llnl/ygm-bench -> workload_ygm_bench'},
 'toolchain_tuolumne': {'modules': ['PrgEnv-gnu', 'gcc-native/11.2'],
                        'CC': '/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/mpicc',
                        'CXX': '/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/mpicxx',
                        'avoid': 'Cray-clang 20.1.6 (fmt consteval error)',
                        'on_switch': 'rm -rf build_ann'},
 'annotation': {'headers': ['include/ygm/collective.hpp',
                            'include/ygm/detail/comm.ipp',
                            'comm_router.hpp',
                            'comm_environment.hpp',
                            'mpi.hpp'],
                'include': '#include <dftracer/dftracer.h> right after #pragma once in each',
                'ipp_files': 'manual annotation (clang tools return 0 functions); verify with compiler + '
                             'clang_lint_annotations'},
 'link_dftracer': {'method': 'manual IMPORTED target for libdftracer_core.so linked into the ygm interface target',
                   'flag': '-DDFTRACER_ROOT=<dftracer prefix>',
                   'avoid': "prerelease wheel's dftracer-config.cmake (broken)"},
 'dftracer_from_source': {'DFTRACER_CMAKE_ARGS': ['-DDFTRACER_ENABLE_MPI=ON',
                                                  '-DDFTRACER_MPI_IMPL=CRAYMPICH',
                                                  '-DBRAHMA_MPI_VERSION=900001'],
                          'same_mpi_wrapper_as_app': True,
                          'verify': 'ldd <prefix>/lib/libdftracer_core.so | grep mpi  # one runtime only'},
 'session': {'build_annotated': 'session_build_annotated(run_id, build_subdir="source")  # '
                                'annotated/source/CMakeLists.txt'},
 'smoke': {'entry': 'test/test_comm.cpp',
           'ranks': 1,
           'expect_events': 194,
           'expect_names': ['post_new_irecv',
                            'check_completed_sends',
                            'local_process_incoming',
                            'barrier_reduce_counts',
                            'priv_barrier',
                            'comm_setup']}}

_SOFTWARE_YGM_RULES = [{'id': 'ygm_no_cray_clang',
  'kind': 'forbid_if',
  'pattern': '\\b(module\\s+(load|swap)|ml)\\b[^\\n]*PrgEnv-cray',
  'when': 'ygm',
  'flags': 'i',
  'why': "Cray-clang 20.1.6 fails on YGM's FetchContent'd spdlog/fmt (consteval not a constant expression).",
  'fix': 'module load PrgEnv-gnu gcc-native/11.2 and use the cray-mpich GNU mpicc/mpicxx; rm -rf build_ann first.'},
 {'id': 'ygm_cxx20',
  'kind': 'forbid',
  'pattern': 'CMAKE_CXX_STANDARD=(98|11|14|17)\\b',
  'why': 'YGM and its deps (Boost 1.87, spdlog/fmt) require C++20.',
  'fix': "Use -DCMAKE_CXX_STANDARD=20 (or leave YGM's default)."},
 {'id': 'dftracer_mpi_impl_craympich',
  'kind': 'require_if',
  'pattern': 'DFTRACER_MPI_IMPL=CRAYMPICH',
  'when': 'DFTRACER_ENABLE_MPI=ON',
  'why': 'From-source dftracer with MPI on Cray MPICH needs DFTRACER_MPI_IMPL=CRAYMPICH.',
  'fix': 'Add -DDFTRACER_MPI_IMPL=CRAYMPICH -DBRAHMA_MPI_VERSION=900001 to DFTRACER_CMAKE_ARGS.'},
 {'id': 'brahma_mpi_version',
  'kind': 'require_if',
  'pattern': 'BRAHMA_MPI_VERSION=900001',
  'when': 'DFTRACER_MPI_IMPL=CRAYMPICH',
  'why': 'brahma needs the Cray MPICH version (900001 for cray-mpich 9.0.1) when MPI interception is on.',
  'fix': 'Add -DBRAHMA_MPI_VERSION=900001.'},
 {'id': 'verify_single_mpi_runtime',
  'kind': 'require_if',
  'pattern': 'ldd[^\\n]*libdftracer_core[^\\n]*\\|\\s*grep[^\\n]*mpi',
  'when': 'DFTRACER_ENABLE_MPI=ON',
  'why': 'dftracer built with a different MPI wrapper than the app loads two MPI runtimes (double-free at exit).',
  'fix': "Run ldd <prefix>/lib/libdftracer_core.so | grep mpi and confirm it matches the app's MPI."},
 {'id': 'annotated_build_links_dftracer',
  'kind': 'require_if',
  'pattern': '-DDFTRACER_ROOT=',
  'when': 'cmake[^\\n]*build_ann',
  'why': "YGM's CMakeLists.txt does not link dftracer; the manual IMPORTED target is driven by -DDFTRACER_ROOT.",
  'fix': 'Pass -DDFTRACER_ROOT=<dftracer prefix> to the annotated cmake configure.'}]
