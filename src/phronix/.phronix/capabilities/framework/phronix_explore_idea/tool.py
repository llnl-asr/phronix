"""phronix_explore_idea: explore one idea from the plan (framework process capability, converted from dftracer-agents skill phronix-explore-idea).

phronix_explore_idea_plan renders the procedure as an ordered checklist (predictor); phronix_explore_idea_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-explore-idea'
VALIDATOR = 'phronix_explore_idea_check'
FACTS = ["out_of_time", "step_needs_nothing"]
STEPS = [{'id': 'I0',
  'step': 'Scope to ONE STEP of the plan: {goal}. Find how THIS step is done concretely (file, function, change).',
  'done_when': 'the step is restated'},
 {'id': 'I2',
  'step': 'capability_list first: a probe_ tool that reproduces this failure or runs this check returns in one call what costs five by hand.',
  'done_when': 'probe tools checked'},
 {'id': 'I0.ways',
  'step': 'Find SEVERAL genuinely different ways to do the step (different place: earlier/later, caller vs callee, input vs handling, configure vs '
          'code); record each with research_add_approach(..., aspect=<this step>) and a hypothesis that says what would show it wrong.',
  'done_when': 'each way recorded with aspect and a falsifiable hypothesis',
  'unless': 'step_needs_nothing'},
 {'id': 'I0.none', 'step': 'The step needs NOTHING: say so as the result.', 'done_when': 'recorded as a finding', 'when': 'step_needs_nothing'},
 {'id': 'I1',
  'step': 'Try it, do not describe it: edit your own worktree, run the failing case and the tests around it.',
  'done_when': 'each way was run',
  'unless': 'step_needs_nothing'},
 {'id': 'I2.build',
  'step': 'Anything you did twice: build it with capability_new instead of doing it a third time.',
  'done_when': 'no step repeated by hand'},
 {'id': 'I3',
  'step': 'research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...) as you go; a failure is a result, stated precisely.',
  'done_when': 'observations recorded'},
 {'id': 'I4',
  'step': 'Write the finding: what was tried (redoable), what happened (numbers), what it rules in and out, what is still unknown; mark partial if '
          'partial.',
  'done_when': 'finding recorded'},
 {'id': 'I4.partial',
  'step': 'The budget ran out: mark the finding partial and say what is still unknown.',
  'done_when': 'partial marked',
  'when': 'out_of_time'}]
RULES = [{'id': 'R1',
  'rule': 'Ideas are explored in parallel, not in order: in sequence the third is shaped by the first two, giving three variations of one reading '
          'instead of three readings.'},
 {'id': 'X1', 'rule': 'Do not build the solution here: an explorer sees one third of the evidence.'},
 {'id': 'I0', 'rule': 'Two ways that would be carried out in the same place are the same way described twice.'}]
RECORD_FIELDS = ['step', 'ways', 'tried', 'result', 'rules_in', 'rules_out', 'unknown', 'partial', 'worked']
CHECKS = [{'check': 'step_named', 'kind': 'nonempty', 'field': 'step', 'fix': 'name the one plan step explored (I0)'},
 {'check': 'ways_recorded',
  'kind': 'each_has',
  'field': 'ways',
  'keys': ['where', 'hypothesis'],
  'fix': 'record each way with where it is done and a hypothesis that would show it wrong (research_add_approach aspect=step) (I0)'},
 {'check': 'tried_concretely',
  'kind': 'min_len',
  'field': 'tried',
  'n': 10,
  'fix': 'say what was tried concretely enough to redo: file, function, change (I4)'},
 {'check': 'result_measured',
  'kind': 'nonempty',
  'field': 'result',
  'fix': "say what happened when it ran, in numbers where there are numbers; 'did not work' tells the build stage nothing (I3/I4)"},
 {'check': 'worked_flag',
  'kind': 'one_of',
  'field': 'worked',
  'values': [True, False, 'partial'],
  'fix': 'set worked true/false/partial: a failure is a result (I3)'},
 {'check': 'rules_out', 'kind': 'nonempty', 'field': 'rules_out', 'fix': 'say what the result rules out (I4)'},
 {'check': 'unknown_when_partial',
  'kind': 'nonempty',
  'field': 'unknown',
  'when': {'field': 'partial', 'equals': True},
  'fix': 'a partial finding must say what is still unknown (I4)'},
 {'check': 'no_final_solution',
  'kind': 'absent',
  'field': 'result',
  'pattern': 'final solution|the answer is',
  'fix': 'do not decide the solution here; report the finding for the build stage (X1)'}]


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
    def phronix_explore_idea_plan(goal: str, facts: dict = None) -> dict:
        "Render the explore-one-idea procedure as an ordered checklist: scope to this step, look for a probe tool, find genuinely different ways, try each, record observations and the finding. Use it before applying the phronix-explore-idea procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: step_needs_nothing (the step turned out to need no change), out_of_time (the budget ran out mid-way); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_explore_idea_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_explore_idea_check(record: dict) -> dict:
        "Check an exploration finding: what was tried (file, function, change), what happened (numbers), what it rules in/out, what is unknown, partial marked, ways that differ in place (not one way twice), and failures stated precisely. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields step, ways, tried, result, rules_in, rules_out, unknown, partial, worked). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
