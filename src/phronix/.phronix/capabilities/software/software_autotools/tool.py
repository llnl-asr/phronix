"""software_autotools: Autotools (autoconf/automake/libtool) build system: detection (configure.ac + Makefile.am needing autoreconf -fi vs a checked-in configure script from a release tarball), the session_configure / session_build_install / session_build_annotated flow, dftracer injection through PKG_CONFIG_PATH / CPPFLAGS / LDFLAGS (there is no generic --with-dftracer flag), and stale .deps/ cleanup. Load for any project with configure.ac / Makefile.am or a checked-in configure script, or on 'configure: error: unrecognized option --with-...', a config.status failure from stale .deps/ directories, or dftracer headers/libs not found by the annotated configure."""
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


def _SOFTWARE_AUTOTOOLS_judge(commands, rules):
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
    def software_autotools_recipe(section: str = "") -> str:
        """The build/run/env recipe software_autotools knows, as structured JSON: annotated, build_install, configure, detect, lesson_tagging, switch_compiler.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (annotated, build_install, configure, detect, lesson_tagging, switch_compiler); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_autotools_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_AUTOTOOLS_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_autotools", "sections": sorted(_SOFTWARE_AUTOTOOLS_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_AUTOTOOLS_RULES]})

    @mcp.tool()
    def software_autotools_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_autotools's rules: no_with_dftracer_flag; disable_dependency_tracking; configure_has_prefix; ldflags_rpath_with_dftracer_lib.

        Use on a proposed recipe or command list before running it, and after software_autotools_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_AUTOTOOLS_judge(commands, _SOFTWARE_AUTOTOOLS_RULES))


_SOFTWARE_AUTOTOOLS_RECIPE = {'detect': {'needs_bootstrap': {'files': ['configure.ac', 'Makefile.am'],
                                'absent': 'configure',
                                'action': 'autoreconf -fi'},
            'already_bootstrapped': {'files': ['configure'],
                                     'absent': 'configure.ac',
                                     'action': 'run ./configure directly, never autoreconf'},
            'read_first': ["AC_ARG_WITH(...) and AC_ARG_ENABLE(...) in configure.ac (the project's own "
                           '--with-*/--enable-* flags)',
                           'PKG_CHECK_MODULES / AC_CHECK_HEADER / AC_CHECK_LIB calls (how dependencies are found)'],
            'unknown_flag_behaviour': 'usually errors loudly (unlike CMake/Meson silent ignore)'},
 'configure': {'tool': 'session_configure(run_id, extra_configure_flags="--with-mpi --disable-shared ...")',
               'bootstrap': 'autoreconf -fi (only if configure.ac exists and configure does not)',
               'command': './configure --prefix=<install> --disable-dependency-tracking <extra_configure_flags>',
               'always_added': ['--disable-dependency-tracking'],
               'pre_clean': 'deletes .deps/ under source/ or annotated/ and build/ or build_ann/'},
 'build_install': {'tool': 'session_build_install(run_id, jobs=<n>)',
                   'commands': ['make -j<jobs>', 'make install'],
                   'dirs': {'original': 'build/', 'annotated': 'build_ann/'}},
 'annotated': {'tool': 'session_build_annotated(run_id)',
               'env_injection': {'PKG_CONFIG_PATH': '<dftracer_prefix>/lib/pkgconfig',
                                 'CPPFLAGS': '-I<dftracer_prefix>/include',
                                 'LDFLAGS': '-L<dftracer_prefix>/lib -Wl,-rpath,<dftracer_prefix>/lib'},
               'not_used': '--with-dftracer=<prefix> (no such generic flag)',
               'requires': 'configure.ac probes these via PKG_CHECK_MODULES or AC_CHECK_HEADER/AC_CHECK_LIB; else '
                           'project-specific patch'},
 'switch_compiler': 're-run configure with the new CC/CXX, then make clean (see software_gcc)',
 'lesson_tagging': '(system, dependency) pair per lesson'}

_SOFTWARE_AUTOTOOLS_RULES = [{'id': 'no_with_dftracer_flag',
  'kind': 'forbid',
  'pattern': '--with-dftracer(=|\\s|$)',
  'why': 'There is no generic --with-dftracer configure flag; autotools errors on unknown options.',
  'fix': 'Inject dftracer via PKG_CONFIG_PATH=<prefix>/lib/pkgconfig, CPPFLAGS=-I<prefix>/include, '
         'LDFLAGS=-L<prefix>/lib -Wl,-rpath,<prefix>/lib.'},
 {'id': 'disable_dependency_tracking',
  'kind': 'require_if',
  'pattern': '--disable-dependency-tracking',
  'when': '(^|[\\s;&])(\\./|\\S*/)?configure(\\s|$)',
  'why': 'session_configure always adds --disable-dependency-tracking to avoid config.status failures from stale '
         '.deps/.',
  'fix': 'Add --disable-dependency-tracking to the ./configure line.'},
 {'id': 'configure_has_prefix',
  'kind': 'require_if',
  'pattern': 'configure\\s.*--prefix=\\S+',
  'when': '(^|[\\s;&])(\\./|\\S*/)?configure(\\s|$)',
  'why': "session_configure installs into the session's install/ prefix; without --prefix make install writes to "
         '/usr/local.',
  'fix': 'Pass --prefix=<install>.'},
 {'id': 'ldflags_rpath_with_dftracer_lib',
  'kind': 'require_if',
  'pattern': 'LDFLAGS=[^\\n]*-Wl,-rpath,',
  'when': 'LDFLAGS=[^\\n]*-L\\S*dft',
  'flags': 'i',
  'why': 'session_build_annotated sets LDFLAGS with both -L<prefix>/lib and -Wl,-rpath,<prefix>/lib so the annotated '
         'binary finds libdftracer at run time.',
  'fix': 'Add -Wl,-rpath,<dftracer_prefix>/lib to LDFLAGS.'}]
