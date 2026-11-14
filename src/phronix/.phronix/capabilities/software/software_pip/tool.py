"""software_pip: pip / PEP 517-518 builds off a pyproject.toml: build-backend detection (mesonpy -> Meson underneath, setuptools.build_meta, hatchling.build), editable vs non-editable install, --no-build-isolation in HPC venvs, forwarding project meson -D options through --config-settings=setup-args, extras, [project.scripts] CLI names, and CC/CXX/LD_LIBRARY_PATH ordering before pip. Load for any project installed with `pip install` off a pyproject.toml, or when the build step under pip cannot find a system dependency the active shell sees (build isolation), a meson option such as use_system_flux cannot be passed, or a compiled extension picks the wrong compiler."""
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


def _SOFTWARE_PIP_judge(commands, rules):
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
    def software_pip_recipe(section: str = "") -> str:
        """The build/run/env recipe software_pip knows, as structured JSON: detect, env_order, install, lesson_tagging, why_no_build_isolation.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (detect, env_order, install, lesson_tagging, why_no_build_isolation); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_pip_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_PIP_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_pip", "sections": sorted(_SOFTWARE_PIP_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_PIP_RULES]})

    @mcp.tool()
    def software_pip_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_pip's rules: no_build_isolation; meson_opts_via_setup_args; cc_before_pip.

        Use on a proposed recipe or command list before running it, and after software_pip_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_PIP_judge(commands, _SOFTWARE_PIP_RULES))


_SOFTWARE_PIP_RECIPE = {'detect': {'file': 'pyproject.toml with a [build-system] table',
            'read_first': '[build-system].build-backend',
            'backends': {'mesonpy': 'Meson underneath; meson-python drives meson setup/compile/install; load '
                                    'software_meson; pass -D options via '
                                    '--config-settings=setup-args="-Doption=value"',
                         'setuptools.build_meta': 'classic setup.py / setup.cfg semantics',
                         'hatchling.build': 'Hatch-managed, usually no compiled extension'},
            'cli_names': '[project.scripts] entries (use for smoke-test commands)',
            'extras': '[project.optional-dependencies] groups (dev, otel, plot, ...): install only when needed, e.g. '
                      "pip install '.[dev]'"},
 'install': {'default': 'pip install --no-build-isolation -e .',
             'non_editable': 'pip install --no-build-isolation .   (when the backend forbids/mishandles editable '
                             'with a compiled extension)',
             'meson_option': 'pip install --no-build-isolation --config-settings=setup-args="-D<option>=<value>" .',
             'prereq_with_no_build_isolation': 'pip install <[build-system].requires> (e.g. meson meson-python '
                                               'ninja) into the venv first'},
 'why_no_build_isolation': 'isolated build env does not see loaded modules, compiler wrappers or module-provided '
                           'pkg-config paths, so meson/cmake underneath cannot find system deps',
 'env_order': ['module load <compiler/mpi/...>',
               'activate the venv',
               'export CC=<cc> CXX=<cxx> LD_LIBRARY_PATH=<...>',
               'pip install ...'],
 'lesson_tagging': '(system, dependency) pair per lesson'}

_SOFTWARE_PIP_RULES = [{'id': 'no_build_isolation',
  'kind': 'require_if',
  'pattern': '--no-build-isolation',
  'when': 'pip3?\\s+install\\s+[^\\n]*(\\s|^)(-e\\s+)?[\'"]?\\.(\\[[^\\]]*\\])?[\'"]?(\\s|$)',
  'why': 'In HPC session venvs build isolation hides loaded modules, compiler wrappers and pkg-config paths from the '
         'build backend.',
  'fix': 'Install the [build-system].requires into the venv and add --no-build-isolation.'},
 {'id': 'meson_opts_via_setup_args',
  'kind': 'forbid',
  'pattern': 'pip3?\\s+install\\s[^\\n]*\\s-D\\w+=',
  'why': 'pip does not accept meson -D options directly; they must go through config-settings.',
  'fix': 'Use --config-settings=setup-args="-D<option>=<value>".'},
 {'id': 'cc_before_pip',
  'kind': 'forbid',
  'pattern': 'pip3?\\s+install[^\\n]*&&\\s*export\\s+(CC|CXX|LD_LIBRARY_PATH)=',
  'why': 'The pip subprocess re-sources nothing: CC/CXX/LD_LIBRARY_PATH must be set before pip install runs.',
  'fix': 'Export CC, CXX and LD_LIBRARY_PATH on an earlier line, before pip install.'}]
