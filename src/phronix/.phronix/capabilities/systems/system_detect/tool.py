"""system_detect: Detect the current HPC/container system with mcp__dftracer__system_detect (hostname with trailing digits stripped -> resources/systems.yaml lookup returning module load order, env vars, MPI launcher, notes) and route to its system_<name> capability, or register a new system with mcp__dftracer__system_save. Load at the start of any dftracer session, when the system is unknown, when system_detect returns 'not in systems.yaml', or at session close to persist newly learned system nuances."""
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


def _SYSTEM_DETECT_judge(commands, rules):
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
    def system_detect_recipe(section: str = "") -> str:
        """The build/run/env recipe system_detect knows, as structured JSON: allowed_bash, detect, known_systems, report, session_close, tools, unknown_flow.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (allowed_bash, detect, known_systems, report, session_close, tools, unknown_flow); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_detect_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_DETECT_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_detect", "sections": sorted(_SYSTEM_DETECT_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_DETECT_RULES]})

    @mcp.tool()
    def system_detect_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_detect's rules: save_name_no_digits; detect_before_save; module_read_only; no_build_or_run; no_sudo.

        Use on a proposed recipe or command list before running it, and after system_detect_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_DETECT_judge(commands, _SYSTEM_DETECT_RULES))


_SYSTEM_DETECT_RECIPE = {'detect': {'tool': 'mcp__dftracer__system_detect()',
            'algorithm': 'hostname with trailing digits stripped -> resources/systems.yaml',
            'returns': ['module load order', 'env vars', 'MPI launcher', 'notes']},
 'known_systems': {'tuolumne': 'AMD MI300A APU, Cray PE, Flux, no sudo (system_tuolumne)',
                   'tioga': 'AMD MI250X, Cray PE, Flux (system_tioga)',
                   'matrix': 'NVIDIA H100 + Sapphire Rapids, Slurm (system_matrix)',
                   'dane': 'CPU-only Sapphire Rapids, Slurm (system_dane)',
                   'container': 'Docker/Podman, sudo available, mpirun (system_container)'},
 'unknown_flow': ['offer tuolumne / container / other',
                  'ask system name (hostname base, no digits) + modules/compilers/env vars',
                  'mcp__dftracer__system_save(name=<base>, ...)',
                  'confirm saved to resources/systems.yaml'],
 'session_close': 'mcp__dftracer__system_save(name="<system>", notes="<updated notes>", ...)',
 'tools': ['mcp__dftracer__system_detect', 'mcp__dftracer__system_list', 'mcp__dftracer__system_save'],
 'allowed_bash': ['module list', 'module avail'],
 'report': 'active system + whether sudo is permitted'}

_SYSTEM_DETECT_RULES = [{'id': 'save_name_no_digits',
  'kind': 'forbid',
  'pattern': 'system_save\\([^)]*name\\s*=\\s*[\\"\'][A-Za-z_-]*\\d+[\\"\']',
  'why': 'System names are the hostname base with trailing digits stripped.',
  'fix': 'Use the base name (e.g. tuolumne, not tuolumne1001).'},
 {'id': 'detect_before_save',
  'kind': 'require_if',
  'pattern': 'system_detect',
  'when': 'system_save',
  'why': 'Register a system only after system_detect reported it unknown.',
  'fix': 'Call mcp__dftracer__system_detect() first.'},
 {'id': 'module_read_only',
  'kind': 'forbid',
  'pattern': '^\\s*module\\s+(load|purge|swap|unload|use)\\b',
  'why': 'Detection is read-only: only module list / avail.',
  'fix': 'Use module list / module avail.'},
 {'id': 'no_build_or_run',
  'kind': 'forbid',
  'pattern': '^\\s*(make|cmake|ninja|meson|pip3?\\s+install|mpirun|srun|flux\\s+run)\\b',
  'why': 'Detection never builds or runs applications.',
  'fix': 'Hand off to the build/run stage after detection.'},
 {'id': 'no_sudo',
  'kind': 'forbid',
  'pattern': '\\bsudo\\b',
  'why': 'The permission fence forbids sudo.',
  'fix': 'Drop sudo; detection needs none.'}]
