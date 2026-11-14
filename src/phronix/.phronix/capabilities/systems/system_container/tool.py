"""system_container: System profile for Docker/Podman container environments: detected by /.dockerenv or a container* hostname (or user selection); no HPC module system, package-manager installs (apt-get / yum), MPI launched with plain `mpirun -n <N>` if present (check `which mpirun`), session temp under workspaces/<session>/tmp/. Load when system_detect reports `container`, on 'module: command not found', when srun/flux are absent, or when deciding whether sudo / package installs are allowed."""
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


def _SYSTEM_CONTAINER_judge(commands, rules):
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
    def system_container_recipe(section: str = "") -> str:
        """The build/run/env recipe system_container knows, as structured JSON: detect, modules, mpi, packages, paths, privileges.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (detect, modules, mpi, packages, paths, privileges); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_container_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_CONTAINER_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_container", "sections": sorted(_SYSTEM_CONTAINER_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_CONTAINER_RULES]})

    @mcp.tool()
    def system_container_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_container's rules: no_module_system; mpirun_launcher; mpirun_checked; sudo_only_for_packages; noninteractive_install.

        Use on a proposed recipe or command list before running it, and after system_container_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_CONTAINER_judge(commands, _SYSTEM_CONTAINER_RULES))


_SYSTEM_CONTAINER_RECIPE = {'detect': {'any_of': ['test -f /.dockerenv', 'hostname matches ^container', 'user explicitly selects container']},
 'privileges': {'sudo': 'available; use only for package-manager installs',
                'fence': 'agent permission fence: no sudo otherwise, no writes outside the project root'},
 'modules': None,
 'packages': {'debian_ubuntu': 'sudo apt-get install -y <package>',
              'rhel_rocky': 'sudo yum install -y <package>',
              'python': 'virtualenv under workspaces/<session>/ (see software_pip)'},
 'mpi': {'check': 'which mpirun',
         'launcher': 'mpirun -n <N> <cmd>',
         'install_debian': 'sudo apt-get install -y openmpi-bin libopenmpi-dev'},
 'paths': {'session_tmp': 'workspaces/<session>/tmp/',
           'ephemeral_scratch': '/tmp (lost on restart)',
           'write_scope': 'workspaces/<session>/*',
           'cwd': 'workspaces/<session>/...'}}

_SYSTEM_CONTAINER_RULES = [{'id': 'no_module_system',
  'kind': 'forbid',
  'pattern': '^\\s*module\\s+(load|purge|swap|use)\\b',
  'why': 'Containers have no HPC module system.',
  'fix': 'Install with apt-get/yum or use a virtualenv / direct paths.'},
 {'id': 'mpirun_launcher',
  'kind': 'forbid',
  'pattern': '^\\s*(srun|jsrun|flux\\s+(run|submit|alloc))\\b',
  'why': 'No Slurm/Flux in a container; MPI is launched with mpirun directly.',
  'fix': 'Use mpirun -n <N> <cmd>.'},
 {'id': 'mpirun_checked',
  'kind': 'require_if',
  'pattern': '(which|command\\s+-v)\\s+mpirun',
  'when': '\\bmpirun\\b',
  'why': 'MPI may not be installed in the image.',
  'fix': 'Check which mpirun (install via package manager if missing) before launching.'},
 {'id': 'sudo_only_for_packages',
  'kind': 'forbid',
  'pattern': '\\bsudo\\s+(?!(apt-get|apt|yum|dnf)\\s+install\\b)',
  'why': 'sudo is tolerated only for package-manager installs; the agent fence forbids it otherwise.',
  'fix': 'Drop sudo, or restrict it to apt-get/yum install.'},
 {'id': 'noninteractive_install',
  'kind': 'forbid',
  'pattern': '\\b(apt-get|apt|yum|dnf)\\s+install\\b(?!.*\\s-y\\b)',
  'why': 'Package installs must be non-interactive in an agent session.',
  'fix': 'Pass -y.'}]
