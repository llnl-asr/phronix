"""phronix_learning_capture: capturing repeated research observations as skills and tools (framework process capability, converted from dftracer-agents skill phronix-learning-capture).

phronix_learning_capture_plan renders the procedure as an ordered checklist (predictor); phronix_learning_capture_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-learning-capture'
VALIDATOR = 'phronix_learning_capture_check'
FACTS = ["block_exists", "procedure", "skill_missing"]
STEPS = [{'id': 'I1',
  'step': 'Take the observations of {goal}; call research_notice for counts. Write down every observation; the count decides HOW (once: with '
          'context; again same conditions: widen; again other task: generalise; contradicted: add the condition or retire), not WHETHER. Failures '
          'count double.',
  'done_when': 'every observation has a planned block'},
 {'id': 'I2',
  'step': 'graph_query the finding in your own words, then graph_get_node on the ids returned, to find the block that already says it in different '
          'words.',
  'done_when': 'the covering block (or none) is known'},
 {'id': 'I3', 'step': 'Update that block in place by its label (L3, I2).', 'done_when': 'block updated by label', 'when': 'block_exists'},
 {'id': 'I3.new',
  'step': 'Write one new short block (directive first, one line of why, one idea) in the KIND-OF-WORK skill; reference a neighbouring block by label '
          'rather than copying it.',
  'done_when': 'one block written',
  'unless': 'block_exists'},
 {'id': 'R6',
  'step': 'The kind-of-work skill does not exist: create it with skill_write; never fall back to phronix-learning-capture/reconcile.',
  'done_when': 'kind-of-work skill created',
  'when': 'skill_missing'},
 {'id': 'I4',
  'step': "The repeats are steps: capability_list(), then capability_new(name='probe_...', category=<kind of work>); it is live within the minute.",
  'done_when': 'probe_ tool built with category',
  'when': 'procedure'},
 {'id': 'I5',
  'step': "One line per finding: TOOL: <name> or NO-TOOL: <why not>; end the cycle with research_observe(topic='learning'): tool verdicts, what was "
          'written, already covered, too thin, and whether the graph lookup found the block you later found by hand.',
  'done_when': 'cycle reported'}]
RULES = [{'id': 'R0',
  'rule': 'A skill that solves a problem must say how in its Instructions (file, function, line, change); every cited label must resolve (R0b).'},
 {'id': 'R0c', 'rule': 'A solution skill is as specific as you can make it, and names every way it can still go wrong.'},
 {'id': 'R1', 'rule': "Capture is additive; merging, restructuring and reindexing are reconcile's job."},
 {'id': 'R2', 'rule': "Write for the kind of work in a METHOD skill; the specific form belongs in the problem's solution skill."},
 {'id': 'R3', 'rule': 'Say what failed, not what to abandon.'},
 {'id': 'R4', 'rule': "Write it small rather than not at all; only 'a tool was called' and single-task-only observations deserve nothing."},
 {'id': 'R5', 'rule': 'Never block the pipeline: no long analyses, no held locks, no rewriting a skill another stage is reading.'},
 {'id': 'R6', 'rule': 'Never write into your own skills; the kind of work is the target.'},
 {'id': 'R7', 'rule': 'A tool is filed under the kind of work it belongs to (category=).'}]
RECORD_FIELDS = ['kind', 'findings', 'graph_lookup_found', 'observed']
CHECKS = [{'check': 'kind_of_work',
  'kind': 'one_of',
  'field': 'kind',
  'values': ['bash', 'python', 'traversal', 'tests', 'patch', 'matching', 'config', 'git', 'measurement', 'tooling'],
  'fix': 'name the kind of work you were handed (bash, python, traversal, tests, patch, matching, config, git, measurement, tooling)'},
 {'check': 'findings_listed',
  'kind': 'each_has',
  'field': 'findings',
  'keys': ['target', 'text', 'tool_verdict'],
  'fix': 'list each finding with its target skill, its block text and its tool verdict (I5)'},
 {'check': 'tool_verdicts',
  'kind': 'regex',
  'field': 'findings',
  'pattern': '"tool_verdict": "(TOOL|NO-TOOL): ',
  'fix': 'give every finding a TOOL: <name> or NO-TOOL: <why not> verdict (I5)'},
 {'check': 'not_own_skill',
  'kind': 'absent',
  'field': 'findings',
  'pattern': '"target": "phronix-learning-(capture|reconcile)"',
  'fix': 'write to the kind-of-work skill, never into phronix-learning-capture/reconcile (R6)'},
 {'check': 'tool_has_category',
  'kind': 'each_if',
  'field': 'findings',
  'if': {'key': 'tool_verdict', 'regex': '^TOOL:'},
  'then': {'key': 'category', 'test': 'nonempty'},
  'fix': 'file the tool with category=<kind of work> so the next task of that kind finds it (R7)'},
 {'check': 'no_refuted_approach',
  'kind': 'absent',
  'field': 'findings',
  'pattern': 'falsified|no longer a valid approach|does not work\\b',
  'fix': 'say what failed (the implementation, where), not that the approach is refuted (R3)'},
 {'check': 'blocks_short',
  'kind': 'absent',
  'field': 'findings',
  'pattern': '"text": "[^"]{600,}',
  'fix': 'a block is a directive plus one line of why; split rather than combine (I3, R4)'},
 {'check': 'graph_lookup_reported',
  'kind': 'one_of',
  'field': 'graph_lookup_found',
  'values': [True, False],
  'fix': 'report whether the graph lookup in I2 found the block you later found by hand (I5)'},
 {'check': 'cycle_observed', 'kind': 'true', 'field': 'observed', 'fix': "end the cycle with research_observe(topic='learning') (I5)"}]


def _get(rec, field):
    cur = rec
    for part in field.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _filled(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict, tuple)):
        return len(v) > 0
    return True


def _applies(rec, c):
    w = c.get("when")
    if not w:
        return True
    v = _get(rec, w["field"])
    if "equals" in w:
        return v == w["equals"]
    if "in" in w:
        return v in w["in"]
    if "filled" in w:
        return _filled(v) == bool(w["filled"])
    return True


def _one(rec, c):
    """Run one declarative check; returns (ok, detail)."""
    kind = c["kind"]
    field = c.get("field", "*")
    v = rec if field == "*" else _get(rec, field)
    if kind == "nonempty":
        return _filled(v), (f"{field} present" if _filled(v) else f"{field} missing or empty")
    if kind == "one_of":
        return v in c["values"], f"{field}={v!r}; allowed {c['values']}"
    if kind == "min_items":
        n = len(v) if isinstance(v, (list, tuple, dict)) else 0
        return n >= c["n"], f"{field} has {n} item(s), needs >= {c['n']}"
    if kind == "max_items":
        n = len(v) if isinstance(v, (list, tuple, dict)) else 0
        return n <= c["n"], f"{field} has {n} item(s), allowed <= {c['n']}"
    if kind == "min_len":
        n = len(v) if isinstance(v, str) else 0
        return n >= c["n"], f"{field} is {n} characters, needs >= {c['n']}"
    if kind == "regex":
        s = v if isinstance(v, str) else json.dumps(v, default=str)
        ok = v is not None and re.search(c["pattern"], s, re.I | re.M) is not None
        return ok, (f"{field} matches {c['pattern']!r}" if ok else f"{field} does not match {c['pattern']!r}")
    if kind == "absent":
        s = v if isinstance(v, str) else json.dumps(v, default=str)
        m = re.search(c["pattern"], s or "", re.I | re.M)
        return m is None, ("not found" if m is None else f"found {m.group(0)[:60]!r} in {field}")
    if kind == "date":
        ok = isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}", v) is not None
        return ok, f"{field}={v!r} (YYYY-MM-DD)"
    if kind == "true":
        return v is True, f"{field}={v!r}, must be true"
    if kind == "false":
        return v is False or v is None, f"{field}={v!r}, must be false or absent"
    if kind == "number":
        ok = isinstance(v, (int, float)) and not isinstance(v, bool)
        lo, hi = c.get("min"), c.get("max")
        ok = ok and (lo is None or v >= lo) and (hi is None or v <= hi)
        return ok, f"{field}={v!r} must be a number in [{lo}, {hi}]"
    if kind == "each_has":
        items = v if isinstance(v, list) else []
        bad = [i for i, it in enumerate(items) if not (isinstance(it, dict) and all(_filled(it.get(k)) for k in c["keys"]))]
        ok = bool(items) and not bad
        return ok, (f"every {field} item has {c['keys']}" if ok else f"{field} items {bad or 'none'} lack one of {c['keys']}")
    if kind == "each_regex":
        items = v if isinstance(v, list) else []
        bad = [str(it)[:40] for it in items if not re.search(c["pattern"], it if isinstance(it, str) else json.dumps(it, default=str), re.I)]
        ok = bool(items) and not bad
        return ok, (f"every {field} item matches {c['pattern']!r}" if ok else f"{field} items not matching {c['pattern']!r}: {bad or 'none given'}")
    if kind in ("each_if", "unique"):
        items = [it for it in (v if isinstance(v, list) else []) if isinstance(it, dict) and _match(it, c.get("if"))]
        if kind == "unique":
            vals = [json.dumps(it.get(c["key"]), sort_keys=True, default=str) for it in items if _filled(it.get(c["key"]))]
            dup = sorted({x for x in vals if vals.count(x) > 1})
            return not dup, ("distinct " + c["key"] if not dup else f"{field} items share {c['key']}: {', '.join(dup)[:120]}")
        t = c["then"]
        bad = [i for i, it in enumerate(items) if not _test(it.get(t["key"]), t)]
        sel = f" with {c['if']['key']} {c['if'].get('equals', c['if'].get('in', c['if'].get('regex')))!r}" if c.get("if") else ""
        return not bad, (f"{len(items)} {field} item(s){sel} satisfy {t['key']} {t['test']}" if not bad
                         else f"{field} item(s) {bad}{sel} fail {t['key']} {t['test']} {t.get('pattern', t.get('values', ''))!r}")
    return False, f"unknown check kind {kind!r}"


def _match(item, cond):
    if not cond:
        return True
    v = item.get(cond["key"])
    if "equals" in cond:
        return v == cond["equals"]
    if "in" in cond:
        return v in cond["in"]
    if "regex" in cond:
        return isinstance(v, str) and re.search(cond["regex"], v) is not None
    return _filled(v)


def _test(v, t):
    """Predicate on one item's value: nonempty, true, number, regex, absent, one_of, min_len."""
    test = t["test"]
    if test == "nonempty":
        return _filled(v)
    if test == "true":
        return v is True
    if test == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if test == "one_of":
        return v in t["values"]
    if test == "min_len":
        return isinstance(v, str) and len(v) >= t["n"]
    s = v if isinstance(v, str) else ("" if v is None else json.dumps(v, default=str))
    found = re.search(t["pattern"], s, re.I | re.M) is not None
    return found if test == "regex" else not found


def _plan(goal, facts):
    if not isinstance(goal, str) or not goal.strip():
        return {"status": "error", "error": "goal is required: say concretely what this procedure is being applied to"}
    if facts is not None and not isinstance(facts, dict):
        return {"status": "error", "error": "facts must be an object of named booleans/values, e.g. {" + ", ".join(repr(k) + ": true" for k in FACTS[:2]) + "}"}
    facts = facts or {}
    unknown = sorted(k for k in facts if k not in FACTS)
    out, skipped = [], []
    for s in STEPS:
        if s.get("when") and not facts.get(s["when"]):
            skipped.append({"id": s["id"], "because": f"fact {s['when']} is not set"})
            continue
        if s.get("unless") and facts.get(s["unless"]):
            skipped.append({"id": s["id"], "because": f"fact {s['unless']} is set"})
            continue
        out.append({"n": len(out) + 1, "id": s["id"], "step": s["step"].replace("{goal}", goal.strip()), "done_when": s["done_when"]})
    return {"status": "ok", "skill": SKILL, "goal": goal.strip(), "checklist": out, "skipped": skipped, "rules": RULES,
            "record_fields": RECORD_FIELDS, "validator": VALIDATOR, "unknown_facts": unknown}


def _check(record):
    if isinstance(record, str):
        try:
            record = json.loads(record)
        except ValueError:
            return {"status": "fail", "checks": [{"check": "record_json", "ok": False, "detail": "record is not JSON",
                                                   "fix": "pass the record as an object with the fields " + ", ".join(RECORD_FIELDS)}]}
    if not isinstance(record, dict):
        return {"status": "fail", "checks": [{"check": "record_object", "ok": False, "detail": f"record is {type(record).__name__}",
                                               "fix": "pass the record as an object with the fields " + ", ".join(RECORD_FIELDS)}]}
    res = []
    for c in CHECKS:
        if not _applies(record, c):
            res.append({"check": c["check"], "ok": True, "detail": "not applicable", "fix": ""})
            continue
        ok, detail = _one(record, c)
        res.append({"check": c["check"], "ok": ok, "detail": detail, "fix": "" if ok else c["fix"]})
    if not record:
        return {"status": "inconclusive", "checks": res, "problem": "empty record: nothing to rule on"}
    return {"status": "pass" if all(r["ok"] for r in res) else "fail", "checks": res}


def register(mcp):
    @mcp.tool()
    def phronix_learning_capture_plan(goal: str, facts: dict = None) -> dict:
        "Render one capture cycle for a kind of work as an ordered checklist: count repeats, find the covering block in the graph, update or write one short block in the kind-of-work skill, build a probe_ tool when the repeat is a procedure, report the cycle. Use it before applying the phronix-learning-capture procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: procedure (the repeats describe steps (a procedure) rather than a fact), skill_missing (the kind-of-work skill does not exist yet), block_exists (the graph found a block that already says it); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_learning_capture_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_learning_capture_check(record: dict) -> dict:
        "Check a capture-cycle report: kind of work named, every finding has a TOOL:/NO-TOOL: verdict, nothing written into phronix-learning-capture/reconcile, tools filed with category=<kind>, blocks short, failures phrased as implementation, and the graph-lookup outcome reported. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields kind, findings, graph_lookup_found, observed). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
