"""software_mpifileutils: mpifileutils (dcp, dsync, drm, dwalk, dcmp, dtar, dchmod, dstripe, ddup, dfind, dreln, dbcast, dbz2): MPI-parallel replacements for cp/rsync/rm/find/diff/tar/chmod on Lustre/GPFS/VAST. Load whenever a copy, sync, delete, compare, archive, permission change, restripe or inventory touches more than a few GB or ~10k files on a shared parallel filesystem; on `ml mpifileutils` failing (ambiguous default), a verified move whose `du` byte totals mismatch although file counts match (FAIL verify ... bytes:X/Y), or a drm aimed at a session workspace (blocked by the guard_rm_drm hook)."""
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


def _SOFTWARE_MPIFILEUTILS_judge(commands, rules):
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
    def software_mpifileutils_recipe(section: str = "") -> str:
        """The build/run/env recipe software_mpifileutils knows, as structured JSON: drm_policy, launch, module, threshold, tools, verify_cross_fs, workflow.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (drm_policy, launch, module, threshold, tools, verify_cross_fs, workflow); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_mpifileutils_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_MPIFILEUTILS_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_mpifileutils", "sections": sorted(_SOFTWARE_MPIFILEUTILS_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_MPIFILEUTILS_RULES]})

    @mcp.tool()
    def software_mpifileutils_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_mpifileutils's rules: pin_mpifileutils_version; launch_via_scheduler; no_drm_in_session_workspace; no_du_byte_verify; verify_after_copy.

        Use on a proposed recipe or command list before running it, and after software_mpifileutils_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_MPIFILEUTILS_judge(commands, _SOFTWARE_MPIFILEUTILS_RULES))


_SOFTWARE_MPIFILEUTILS_RECIPE = {'module': {'load': 'module load mpifileutils/0.12',
            'versions': ['0.11.1', '0.12'],
            'bad': 'ml mpifileutils (ambiguous default)'},
 'launch': {'command': 'flux run -n <N> -q pdebug <tool> [flags] <args>',
            'tasks': '8-16 for TB-range metadata/copy',
            'queue': 'pdebug; real allocation only for >10TB or >10M files'},
 'threshold': {'use_mpifileutils_above': 'a few GB or ~10k files on a shared parallel FS',
               'serial_below': 'a few GB / a few thousand files'},
 'tools': {'dcp': 'cp -r',
           'dsync': 'rsync -a (deltas; --batch-files checkpoint/restart)',
           'drm': 'rm -rf (restricted)',
           'dwalk': 'find + summarize (--text, --sort, --output/--input cache)',
           'dcmp': 'diff -r / cmp',
           'dchmod': 'chmod -R / chown -R (--group, --mode)',
           'dtar': 'tar',
           'dstripe': 'restripe existing Lustre files',
           'ddup': 'find duplicates',
           'dfind': 'find (--user --size --type --atime, --input)',
           'dreln': 'rewrite symlinks to a new path',
           'dbcast': 'broadcast a file to node-local storage',
           'dbz2': 'parallel bzip2',
           'experimental': ['dgrep', 'dparallel', 'dsh', 'dfilemaker']},
 'workflow': ['flux run -n 8 -q pdebug dwalk --text <tree>',
              'flux run -n 16 -q pdebug dcp|dsync <src> <dst>',
              'flux run -n 16 -q pdebug dcmp <src> <dst>',
              'flux run -n 16 -q pdebug drm <src>  # outside workspaces/<session>/',
              'quota -v'],
 'verify_cross_fs': {'never': 'du -sb / du --apparent-size comparison',
                     'filebytes': "find <dir> -type f -printf '%s\\n' | awk '{s+=$1} END{print s+0}'",
                     'count': 'find <dir> -type f | wc -l',
                     'per_file': "rsync -a --dry-run --itemize-changes <src>/ <dst>/ | grep -cE '^[<>ch]'  # 0 = "
                                 'clean',
                     'at_scale': 'dcmp',
                     'order': 'verify while the source exists; delete only after pass'},
 'drm_policy': {'allowed': 'outside workspaces/<session>/, e.g. /p/lustre5/$USER/...',
                'workspace': 'rm -rf through the normal permission flow',
                'hook': '.claude/hooks/guard_rm_drm.sh'}}

_SOFTWARE_MPIFILEUTILS_RULES = [{'id': 'pin_mpifileutils_version',
  'kind': 'forbid',
  'pattern': '\\b(module\\s+load|ml)\\s+mpifileutils(?!/)\\b',
  'why': 'Two mpifileutils versions exist; the unversioned load fails (ambiguous default).',
  'fix': 'module load mpifileutils/0.12'},
 {'id': 'launch_via_scheduler',
  'kind': 'forbid',
  'pattern': '^\\s*(dcp|dsync|drm|dwalk|dcmp|dtar|dchmod|dstripe|ddup|dfind|dreln|dbcast|dbz2)\\s',
  'why': 'mpifileutils tools are MPI programs launched with flux run -n <N>; run bare they get one rank (no '
         'parallelism).',
  'fix': 'Prefix with flux run -n 8 -q pdebug (or srun on Slurm).'},
 {'id': 'no_drm_in_session_workspace',
  'kind': 'forbid',
  'pattern': '\\bdrm\\b[^\\n]*workspaces/',
  'why': 'drm is a bulk MPI delete with no per-file confirmation; it must never target workspaces/<session>/.',
  'fix': 'Use rm -rf through the normal permission flow for workspace paths; drm only on scratch like '
         '/p/lustre5/$USER.'},
 {'id': 'no_du_byte_verify',
  'kind': 'forbid',
  'pattern': '\\bdu\\b[^\\n]*(--apparent-size|\\s-s?bs?\\b)',
  'why': 'du -b / --apparent-size counts directory inodes, which differ across filesystems (phantom deltas up to 111 '
         'MB).',
  'fix': "Compare find -type f -printf '%s' sums and counts, then rsync --dry-run --itemize-changes or dcmp."},
 {'id': 'verify_after_copy',
  'kind': 'require_if',
  'pattern': '\\bdcmp\\b|rsync\\s[^\\n]*--dry-run[^\\n]*--itemize-changes|rsync\\s[^\\n]*--itemize-changes[^\\n]*--dry-run',
  'when': '\\b(dcp|dsync)\\b',
  'why': 'Exit code 0 is not proof of a correct copy at this scale; verify per file while the source exists.',
  'fix': 'Add flux run -n 16 dcmp <src> <dst> (or rsync -a --dry-run --itemize-changes) before deleting the source.'}]
