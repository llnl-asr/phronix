"""software_meson: Meson build system: detection (meson.build project(), meson_version, meson.options / meson_options.txt option() names, pyproject.toml build-backend mesonpy -> install through pip), meson setup / compile / install, in-place reconfigure, dependency() resolution (pkg-config -> CMake config -> wrap fallback) and project candidate lists (system pkg-config, _prefix option, sibling checkout, container installs), plus native meson support in session_configure / session_build_install / session_build_annotated. Load for any project whose top level is meson.build / meson.options, or on 'Dependency X found: NO', 'Unsupported build tool: meson', a silently ignored -D option typo, or 'implicit declaration of function strdup' under Cray clang with c_std=c99."""
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


def _SOFTWARE_MESON_judge(commands, rules):
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
    def software_meson_recipe(section: str = "") -> str:
        """The build/run/env recipe software_meson knows, as structured JSON: cray_clang_c99, dependency_resolution, detect, direct_flow, known_sites, lesson_tagging, reconfigure, session_tools.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (cray_clang_c99, dependency_resolution, detect, direct_flow, known_sites, lesson_tagging, reconfigure, session_tools); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_meson_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_MESON_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_meson", "sections": sorted(_SOFTWARE_MESON_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_MESON_RULES]})

    @mcp.tool()
    def software_meson_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_meson's rules: no_rm_builddir_to_reconfigure; compile_install_with_C; gnu_source_not_posix; pkgconfig_probe_before_sibling.

        Use on a proposed recipe or command list before running it, and after software_meson_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_MESON_judge(commands, _SOFTWARE_MESON_RULES))


_SOFTWARE_MESON_RECIPE = {'detect': {'files': ['meson.build', 'meson.options (or legacy meson_options.txt)'],
            'confirm': ["project(<name>, '<lang>', ...)", 'meson_version: (minimum Meson version)'],
            'read_first': 'option() declarations in meson.options (project-specific names; -D typo may be silently '
                          'ignored)',
            'pip_wrapped': {'marker': 'pyproject.toml build-backend = "mesonpy", requires = ["meson-python>=...", '
                                      '"meson>=..."]',
                            'install': 'pip install -e . (or non-editable / python -m build), see software_pip'}},
 'direct_flow': ['meson setup <builddir> -D<option>=<value> ...',
                 'meson compile -C <builddir>',
                 'meson install -C <builddir>'],
 'reconfigure': 're-run meson setup on the existing builddir with new -D options (in place, no rm -rf)',
 'session_tools': {'native_since': '2026-07-16',
                   'tools': ['session_configure', 'session_build_install', 'session_build_annotated'],
                   'legacy_workaround': 'custom_build_cmd: meson setup <build_dir> <source_dir> -D... && ninja -C '
                                        '<build_dir> && ninja -C <build_dir> install'},
 'dependency_resolution': {'order': ['pkg-config', 'CMake config files', 'subproject wrap fallback'],
                           'failure_line': 'Dependency <X> found: NO',
                           'candidate_lists': ['system pkg-config',
                                               'explicit <dep>_prefix option',
                                               'workspace-relative sibling checkout',
                                               'container-installs directory'],
                           'probe_first': 'pkg-config --exists <name>'},
 'cray_clang_c99': {'symptom': 'implicit declaration of strdup() etc. with c_std=c99',
                    'fix': "add_project_arguments('-D_GNU_SOURCE', language: 'c')",
                    'does_not_fix': '-D_POSIX_C_SOURCE'},
 'known_sites': {'tuolumne': {'flux-core': 'pkg-config finds flux 0.86.0 (standard environment) -> '
                                           '-Duse_system_flux=true',
                              'flux-sched': 'not needed for flux-fiction jobtap plugin'}},
 'lesson_tagging': '(system, dependency) pair per lesson'}

_SOFTWARE_MESON_RULES = [{'id': 'no_rm_builddir_to_reconfigure',
  'kind': 'forbid',
  'pattern': 'rm\\s+-r[f]?\\s+\\S*build\\S*[^\\n]*&&\\s*meson\\s+setup',
  'why': 'meson setup on an existing builddir with new -D options reconfigures in place.',
  'fix': 'Re-run meson setup <builddir> -D... (or meson configure <builddir> -D...) without deleting the builddir.'},
 {'id': 'compile_install_with_C',
  'kind': 'forbid',
  'pattern': 'meson\\s+(compile|install)(?![^\\n]*-C\\s*\\S+)',
  'why': 'meson compile / install run against a builddir given with -C <builddir>.',
  'fix': 'Use meson compile -C <builddir> and meson install -C <builddir>.'},
 {'id': 'gnu_source_not_posix',
  'kind': 'forbid',
  'pattern': '-D_POSIX_C_SOURCE',
  'why': 'Under Cray clang c_std=c99, -D_POSIX_C_SOURCE did not fix strdup implicit declarations (2026-07-16).',
  'fix': "Use add_project_arguments('-D_GNU_SOURCE', language: 'c')."},
 {'id': 'pkgconfig_probe_before_sibling',
  'kind': 'require_if',
  'pattern': 'pkg-config\\s+--exists',
  'when': 'git\\s+clone[^\\n]*flux-(core|sched)|podman',
  'why': 'A system-installed dependency (e.g. flux-core on Tuolumne) makes the sibling checkout / container path '
         'unnecessary.',
  'fix': 'Run pkg-config --exists <name> first; only fall back to a sibling checkout or container if it fails.'}]
