"""software_cmake: CMake build system: detection (top-level CMakeLists.txt, project(), option(), find_package CONFIG vs MODULE vs pkg-config), the session_configure / session_build_install / session_build_annotated flow, dftracer injection through CMAKE_PREFIX_PATH, and stale-cache repair. Load for any project whose top level is CMakeLists.txt, or on 'Could not find a package configuration file provided by dftracer', a silently ignored -D option, or a stale CMakeCache.txt pointing at a deleted compiler/prefix."""
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


def _SOFTWARE_CMAKE_judge(commands, rules):
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
    def software_cmake_recipe(section: str = "") -> str:
        """The build/run/env recipe software_cmake knows, as structured JSON: annotated, build_install, configure, detect, dftracer_discovery, stale_cache_fix.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (annotated, build_install, configure, detect, dftracer_discovery, stale_cache_fix); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_cmake_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_CMAKE_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_cmake", "sections": sorted(_SOFTWARE_CMAKE_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_CMAKE_RULES]})

    @mcp.tool()
    def software_cmake_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_cmake's rules: no_pkgconfig_dftracer; no_whole_build_wipe_for_cache; cmake_out_of_source; no_find_package_with_wheel.

        Use on a proposed recipe or command list before running it, and after software_cmake_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_CMAKE_judge(commands, _SOFTWARE_CMAKE_RULES))


_SOFTWARE_CMAKE_RECIPE = {'detect': {'files': ['CMakeLists.txt'],
            'confirm': ['project(<name> ...)', 'cmake_minimum_required(VERSION ...)'],
            'read_first': ['option(...) declarations', 'find_package / find_library / pkg_check_modules calls']},
 'configure': {'tool': 'session_configure(run_id, extra_cmake_flags=...)',
               'command': 'cmake -S source -B build -DCMAKE_INSTALL_PREFIX=install -DCMAKE_BUILD_TYPE=RelWithDebInfo '
                          '<extra_cmake_flags>'},
 'build_install': {'tool': 'session_build_install(run_id, jobs=<n>)',
                   'commands': ['make -j<jobs>', 'make install'],
                   'dirs': {'original': 'build/', 'annotated': 'build_ann/'},
                   'generator': 'Unix Makefiles (not Ninja) by default'},
 'annotated': {'tool': 'session_build_annotated(run_id, extra_cmake_flags=...)',
               'auto_flags': ['-DCMAKE_PREFIX_PATH=<dftracer_install_prefix> (after session_install_dftracer)']},
 'dftracer_discovery': {'source_built_prefix': 'find_package(dftracer CONFIG) via CMAKE_PREFIX_PATH / dftracer_DIR',
                        'prerelease_or_compose_wheel': 'find_package BROKEN (2026-11-13): -I<pkg>/include '
                                                       '-L<pkg>/lib64 -ldftracer_core, or manual IMPORTED target',
                        'fails': 'pkg_check_modules(dftracer) for a source-built install (no .pc shipped)'},
 'stale_cache_fix': 'rm build/CMakeCache.txt (only that file), then reconfigure'}

_SOFTWARE_CMAKE_RULES = [{'id': 'no_pkgconfig_dftracer',
  'kind': 'forbid',
  'pattern': 'pkg_check_modules\\s*\\([^)]*dftracer|pkg-config\\s+[^|;]*dftracer',
  'why': 'dftracer ships no .pc file, so pkg-config lookups of dftracer fail.',
  'fix': 'Find dftracer with find_package(dftracer CONFIG) and CMAKE_PREFIX_PATH / dftracer_DIR.'},
 {'id': 'no_whole_build_wipe_for_cache',
  'kind': 'forbid',
  'pattern': 'rm\\s+-r[f]?\\s+\\S*build/?\\s*$',
  'why': 'A stale cache is fixed by deleting build/CMakeCache.txt only, not the whole build tree.',
  'fix': 'Replace the rm -rf of the build dir with rm build/CMakeCache.txt.'},
 {'id': 'cmake_out_of_source',
  'kind': 'require_if',
  'pattern': 'cmake\\s+.*-B\\s*\\S+',
  'when': '(^|\\s)cmake\\s+(?!--build|--install)',
  'why': 'session_configure configures out of source with -S source -B build.',
  'fix': 'Configure with cmake -S <source> -B <build>.'},
 {'id': 'no_find_package_with_wheel',
  'kind': 'forbid_if',
  'pattern': 'find_package\\s*\\(\\s*dftracer',
  'when': 'pip install[^\\n]*--pre[^\\n]*dftracer|dftracer-compose',
  'why': "the prerelease/compose wheel's CMake config is broken for consumers (2026-11-13).",
  'fix': 'Link the install directly (-I/-L/-ldftracer_core) or define a manual IMPORTED target.'}]
