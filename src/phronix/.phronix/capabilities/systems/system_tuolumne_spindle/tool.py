"""system_tuolumne_spindle: Spindle scalable library / Python-module loader on Tuolumne (TOSS 4 / Cray): on by default at level `medium` for every flux job via the flux shell plugin (`/etc/flux/shell/lua.d/spindle.lua`), its levels (off/low/medium/high), how to set them (`SPINDLE_FLUXOPT` exported BEFORE `flux run`/`flux proxy`, `FLUX_SPINDLE`, `-o spindle.level=`), how to verify it ran (`FLUX_SPINDLE_REALPATH`), its exclusivity with `-o fastload=on`, and the measured 2026-07-22 A/B where `SPINDLE_FLUXOPT=disable` was 3-4x faster to first training step than either Spindle level for a 4-node PyTorch job. Load for any job startup-latency / import-storm investigation (Python/PyTorch/PyG/h5py jobs with long time-to-first-step), when a `SPINDLE_FLUXOPT` setting seems to have no effect, or before crediting a startup delta to Spindle. For Spindle assertion hangs use software_spindle_probe."""
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


def _SYSTEM_TUOLUMNE_SPINDLE_judge(commands, rules):
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
    def system_tuolumne_spindle_recipe(section: str = "") -> str:
        """The build/run/env recipe system_tuolumne_spindle knows, as structured JSON: ab_protocol, default, fastload, levels, measured, recommendation, set_level, skip_conditions, source, standalone_cli, verify.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (ab_protocol, default, fastload, levels, measured, recommendation, set_level, skip_conditions, source, standalone_cli, verify); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_tuolumne_spindle_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_TUOLUMNE_SPINDLE_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_tuolumne_spindle", "sections": sorted(_SYSTEM_TUOLUMNE_SPINDLE_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_TUOLUMNE_SPINDLE_RULES]})

    @mcp.tool()
    def system_tuolumne_spindle_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_tuolumne_spindle's rules: spindle_env_before_flux; spindle_valid_level; no_fastload_with_spindle_level; no_standalone_spindle_cli; prefer_env_over_level_flag.

        Use on a proposed recipe or command list before running it, and after system_tuolumne_spindle_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_TUOLUMNE_SPINDLE_judge(commands, _SYSTEM_TUOLUMNE_SPINDLE_RULES))


_SYSTEM_TUOLUMNE_SPINDLE_RECIPE = {'default': {'active': 'every non-instance flux job (not nested flux start / flux broker)',
             'level': 'medium',
             'plugin_lua': '/etc/flux/shell/lua.d/spindle.lua',
             'plugin_lib': 'libspindleflux.so',
             'module_target': '/collab/usr/global/tools/spindle/toss_4_x86_64_ib_cray_live/',
             'needs': 'nothing (no module load, wrapper or flag)'},
 'skip_conditions': ['SPINDLE_FLUXOPT=disable in the job environment',
                     '-o fastload=... requested (mutually exclusive)'],
 'levels': {'high': 'reloc aout + libs + exec targets + python .py/.pyc/.pyo',
            'medium': 'default; balance for minimal debugging impact; libs; Python file relocation not confirmed',
            'low': 'most relocation off; file-existence cache only',
            'off': 'Spindle disabled',
            'disable': 'SPINDLE_FLUXOPT value that skips the plugin'},
 'set_level': {'env_priority': ['SPINDLE_FLUXOPT', 'FLUX_SPINDLE', 'default medium'],
               'env': 'export SPINDLE_FLUXOPT=<high|medium|low|off|disable>  # in the shell BEFORE flux run / flux '
                      'proxy',
               'flag': 'flux run -N4 -n16 -g1 -o spindle.level=high bash run_script.sh  # accepted, effect '
                       'unconfirmed',
               'disable': 'export SPINDLE_FLUXOPT=disable'},
 'verify': {'plugin_ran': 'env | grep FLUX_SPINDLE_REALPATH  (inside the job)',
            'effect': 'A/B time-to-first-step (or dftracer import-phase events) with SPINDLE_FLUXOPT=disable vs '
                      'unset vs high',
            'level_semantics': 'strings <spindle-install>/lib/libspindleflux.so | grep level'},
 'ab_protocol': {'arms': ['disable', 'medium (unset)', 'high'],
                 'replicates_per_arm': 5,
                 'allocation': 'dedicated, --exclusive',
                 'metric': 'import-to-first-training-step latency (or aggregate import-phase dftracer events)',
                 'same_scale': True},
 'measured': {'date': '2026-07-22',
              'workload': 'PECAN (PyTorch + PyG + HDF5)',
              'scale': '4 nodes x 16 ranks (8-node allocation)',
              'metric': 'import-to-first-training-step seconds',
              'disable': {'mean': 47.3, 'stdev': 14.7, 'min': 36.4, 'max': 65.9, 'cv': 0.31},
              'medium': {'mean': 153.5, 'stdev': 17.8, 'min': 143.7, 'max': 185.1, 'cv': 0.12},
              'high': {'mean': 146.4, 'stdev': 2.6, 'min': 143.5, 'max': 149.1, 'cv': 0.02},
              'single_replicate_earlier': {'disable': 98, 'high': 167},
              'verdict': 'disable 3-4x faster than either Spindle level; medium ~= high'},
 'recommendation': {'python_dl_4_8_nodes': 'export SPINDLE_FLUXOPT=disable',
                    'large_rank_counts': 'untested; A/B before adopting any level'},
 'fastload': {'lua': '/etc/flux/shell/lua.d/fastload.lua',
              'mechanism': 'LD_AUDIT + libfastload2.so + GLIBC_TUNABLES hwcaps',
              'activation': 'only if shell.options.spindle == nil and fastload == on',
              'covers_python': False,
              'combine_with_spindle_level': False},
 'standalone_cli': {'path': '/usr/bin/spindle',
                    'parsers': ['SRun', 'JSRun', 'LSF', 'OpenMPI', '--hostbin=EXECUTABLE'],
                    'flux_parser': False,
                    'use': 'not recommended; use the flux shell plugin'},
 'source': 'https://github.com/hpc/Spindle'}

_SYSTEM_TUOLUMNE_SPINDLE_RULES = [{'id': 'spindle_env_before_flux',
  'kind': 'require_if',
  'pattern': '(?s)((export\\s+)?(SPINDLE_FLUXOPT|FLUX_SPINDLE)=\\S+.*\\bflux\\s+(run|proxy|submit|batch|alloc)\\b)',
  'when': 'SPINDLE_FLUXOPT|FLUX_SPINDLE=',
  'why': 'The flux shell plugin reads SPINDLE_FLUXOPT at job-shell init; setting it after/inside the launched script '
         'is a silent no-op.',
  'fix': 'export SPINDLE_FLUXOPT=<level> in the submitting shell before flux run / flux proxy.'},
 {'id': 'spindle_valid_level',
  'kind': 'forbid',
  'pattern': '(SPINDLE_FLUXOPT|FLUX_SPINDLE|spindle\\.level)=(?!(high|medium|low|off|disable)\\b)\\S+',
  'why': 'Valid values are high, medium, low, off (and disable for SPINDLE_FLUXOPT).',
  'fix': 'Use one of high|medium|low|off|disable.'},
 {'id': 'no_fastload_with_spindle_level',
  'kind': 'forbid',
  'pattern': 'fastload=on.*spindle\\.level|spindle\\.level.*fastload=on',
  'why': 'fastload and Spindle are mutually exclusive startup accelerators in the flux shell plugin ordering.',
  'fix': 'Pick one: Spindle (covers Python modules) or fastload.'},
 {'id': 'no_standalone_spindle_cli',
  'kind': 'forbid',
  'pattern': '(^|[;&|]\\s*)(/usr/bin/)?spindle\\s+(mpirun|srun|flux|--hostbin)',
  'why': 'The standalone spindle CLI has no Flux launcher parser; the flux shell plugin is already wired in.',
  'fix': 'Drop the spindle wrapper; control Spindle with SPINDLE_FLUXOPT before flux run.'},
 {'id': 'prefer_env_over_level_flag',
  'kind': 'forbid',
  'pattern': '-o\\s*spindle\\.level=',
  'why': '-o spindle.level= is accepted but its effect was never confirmed; only the exported env var had a measured '
         'effect.',
  'fix': 'export SPINDLE_FLUXOPT=<level> before flux run instead of -o spindle.level=.'}]
