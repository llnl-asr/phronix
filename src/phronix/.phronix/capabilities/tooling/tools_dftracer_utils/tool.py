"""tools_dftracer_utils: dftracer-utils, the Python binding package for the trace-utils CLI (split, merge, reader, event_count, comparator, aggregator, stats, reconstruct, replay, organize, pgzip, tar on .pfw/.pfw.gz traces): install verification (`import dftracer_utils`), its place in the dftracer / pydftracer / dftracer-utils trio, the session-venv rule, and the known `dftracer_stats --report categories|summary` failure on compacted traces (`No chunk statistics in index for <file>`, `Events processed: 0` from `dftracer_index --rebuild-summaries`) with its workaround. Load before any trace post-processing step (session_split_traces, reader, event_count, comparator, stats) or on a 'dftracer partially works' report."""
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


def _TOOLS_DFTRACER_UTILS_judge(commands, rules):
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
    def tools_dftracer_utils_recipe(section: str = "") -> str:
        """The build/run/env recipe tools_dftracer_utils knows, as structured JSON: category_count_workaround, package, stats, tools, trio_check, venv, verify.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (category_count_workaround, package, stats, tools, trio_check, venv, verify); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what tools_dftracer_utils_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _TOOLS_DFTRACER_UTILS_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "tools_dftracer_utils", "sections": sorted(_TOOLS_DFTRACER_UTILS_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _TOOLS_DFTRACER_UTILS_RULES]})

    @mcp.tool()
    def tools_dftracer_utils_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against tools_dftracer_utils's rules: no_stats_report_on_compacted; no_rebuild_summaries_reliance; no_framework_venv_repair; verify_import_after_install; check_trio_not_one.

        Use on a proposed recipe or command list before running it, and after tools_dftracer_utils_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_TOOLS_DFTRACER_UTILS_judge(commands, _TOOLS_DFTRACER_UTILS_RULES))


_TOOLS_DFTRACER_UTILS_RECIPE = {'package': {'pypi': 'dftracer-utils',
             'summary': 'Python binding for dftracer-utils',
             'import': 'dftracer_utils',
             'required_by': ['dftracer', 'dftracer-agents', 'dftracer-analyzer'],
             'installed_via': 'dftracer (transitive)'},
 'tools': ['split',
           'merge',
           'reader',
           'event_count',
           'comparator',
           'aggregator',
           'stats',
           'reconstruct',
           'replay',
           'organize',
           'pgzip',
           'tar'],
 'verify': ['python -c "import dftracer_utils"', 'run the MCP wrapper (e.g. event_count) on a real .pfw.gz'],
 'trio_check': {'dftracer': 'python -c "import dftracer"',
                'pydftracer': 'python -c "from dftracer.python import dftracer, dft_fn"',
                'dftracer_utils': 'python -c "import dftracer_utils"'},
 'venv': 'session-local; never repair the shared framework venv in place',
 'stats': {'raw_traces': 'dftracer_stats -d <raw_dir> --index-dir <idx> --report categories|top-names  # works '
                         '(2026-09-30)',
           'compacted_traces': 'BROKEN: dftracer_index --rebuild-summaries -> Events processed: 0; dftracer_stats '
                               '--report categories|summary|detailed -> No chunk statistics in index for <file> '
                               '(2026-08-02)',
           'totals': 'event_count (mcp__dftracer__event_count / dftracer_event_count) unaffected'},
 'category_count_workaround': ['import gzip, json, collections',
                               'cats = collections.Counter()',
                               'for chunk_path in all_chunks:  # every chunk in the compact dir, not a sample',
                               "    for line in gzip.open(chunk_path, 'rt'):",
                               "        line = line.strip().rstrip(',')",
                               "        if not line or line in ('[', ']'): continue",
                               "        try: cats[json.loads(line).get('cat')] += 1",
                               '        except Exception: pass']}

_TOOLS_DFTRACER_UTILS_RULES = [{'id': 'no_stats_report_on_compacted',
  'kind': 'forbid',
  'pattern': 'dftracer_stats\\b(?=.*compact).*--report\\s+(categories|summary|detailed)\\b',
  'why': "On compacted traces the index has no chunk statistics: every file fails with 'No chunk statistics in "
         "index'.",
  'fix': 'Use event_count for totals and the full-chunk gzip/json category parse; or run stats on the raw per-rank '
         'dir.'},
 {'id': 'no_rebuild_summaries_reliance',
  'kind': 'forbid',
  'pattern': 'dftracer_index\\b.*--rebuild-summaries',
  'why': '--rebuild-summaries processes 0 events (bloom filters only), so summaries stay empty.',
  'fix': 'Skip it; use event_count / raw-trace dftracer_stats / the category parse.'},
 {'id': 'no_framework_venv_repair',
  'kind': 'forbid',
  'pattern': 'dftracer-agents/\\.venv/bin/(pip|python\\S*\\s+-m\\s+pip)\\s+install',
  'why': "The shared framework venv is the framework's own environment; never repair it for a session.",
  'fix': 'Install a session-local dftracer (session_install_dftracer), which pulls in dftracer-utils.'},
 {'id': 'verify_import_after_install',
  'kind': 'require_if',
  'pattern': 'import\\s+dftracer_utils',
  'when': 'pip\\s+install\\b.*dftracer',
  'why': 'pip show alone does not prove the binding imports.',
  'fix': 'Run python -c "import dftracer_utils" after the install.'},
 {'id': 'check_trio_not_one',
  'kind': 'require_if',
  'pattern': 'from\\s+dftracer\\.python\\s+import',
  'when': 'import\\s+dftracer_utils',
  'why': 'dftracer-utils working does not prove pydftracer is installed; the three fail independently.',
  'fix': 'Also run python -c "from dftracer.python import dftracer, dft_fn".'}]
