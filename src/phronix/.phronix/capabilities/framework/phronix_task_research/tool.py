"""phronix_task_research: fixing the specific failure a task is stuck on (framework process capability, converted from dftracer-agents skill phronix-task-research).

phronix_task_research_plan renders the procedure as an ordered checklist (predictor); phronix_task_research_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-task-research'
VALIDATOR = 'phronix_task_research_check'
FACTS = ["budget_exhausted", "needs_restructure", "open_has_traceback"]
STEPS = [{'id': 'I7',
  'step': "Read the solution skill's LESSONS.md first (skill_load with the lessons file): what earlier attempts tried and how each failed.",
  'done_when': 'earlier failures listed'},
 {'id': 'I6a',
  'step': 'Write PROBLEM: <the one failure you are solving> before looking at anything else, for {goal}.',
  'done_when': 'PROBLEM line written'},
 {'id': 'I1',
  'step': "Read tracker.md's Open section: the test and the assertion/error behind it is your subject.",
  'done_when': 'the open error is named'},
 {'id': 'I1b',
  'step': 'Open names a file and line: go there first; a traceback is a diagnosis already done.',
  'done_when': 'the traceback site read',
  'when': 'open_has_traceback'},
 {'id': 'I8',
  'step': "Retrieve the conversation a turn at a time: conversation_outline(), conversation_search('<symbol/file/approach>'), conversation_turn(-1); "
          'never read it whole.',
  'done_when': 'only needed turns read'},
 {'id': 'I6b',
  'step': 'Before each thing you try (and when changing direction), write APPROACH: <what you check and why it would settle it>.',
  'done_when': 'an APPROACH line per direction'},
 {'id': 'I2',
  'step': 'Keep Established: list what must keep passing and which part of the existing change produces it; change only the part that is wrong.',
  'done_when': 'must-keep-passing list written'},
 {'id': 'I3',
  'step': 'Check the diagnosis against Ruled out: landing on a ruled-out item means the diagnosis is wrong; say what is different or find another '
          'cause.',
  'done_when': 'no ruled-out item proposed again'},
 {'id': 'R1',
  'step': 'Diagnose the error, do not improve the area; if restructuring is genuinely needed, say why the narrow fix cannot work.',
  'done_when': 'fix is narrow or the restructure is justified'},
 {'id': 'R1b', 'step': 'Write the checkable reason the narrow fix cannot work.', 'done_when': 'reason stated', 'when': 'needs_restructure'},
 {'id': 'I4',
  'step': 'skill_write the fix into the EXISTING solution skill: the change (file, function, the line it becomes), why this form when an obvious '
          'alternative fails, what must keep passing.',
  'done_when': 'solution skill updated, no second skill founded'},
 {'id': 'I7b',
  'step': 'skill_write_lesson what the diagnosed attempt tried and how it failed, naming the tests it broke.',
  'done_when': 'lesson written'},
 {'id': 'R3',
  'step': 'Record both halves of a partial result: which tests pass and which do not by name, why the failing half fails, which approaches are now '
          'ruled out.',
  'done_when': 'both halves named'},
 {'id': 'I5',
  'step': 'Budget ran out: write the narrowest supportable cause and the next check; do not pad it into a confident fix.',
  'done_when': 'ANSWER states the uncertainty and the next check',
  'when': 'budget_exhausted'},
 {'id': 'I9',
  'step': 'Link the tracker history from the skill once (a reference block to tracker.md), do not paste it; call layout_check() and act on every '
          'issue.',
  'done_when': 'layout_check returns no issues'},
 {'id': 'R2', 'step': 'research_validate() and act on every issue until clean.', 'done_when': 'research_validate returns no issues'},
 {'id': 'R4',
  'step': 'solution_check(skill=...) on the skill and act on what it returns: the skill must CARRY the fix (a diff), not describe one.',
  'done_when': 'solution_check clean'},
 {'id': 'I6c',
  'step': 'Write ANSWER: <the fix, or the narrowest statement of the cause> once, and the three lines into the report file.',
  'done_when': 'ANSWER line written in the trace and the report file'}]
RULES = [{'id': 'R1', 'rule': 'Diagnose the error, do not improve the area.'},
 {'id': 'R2', 'rule': 'Validate the record (research_validate) and the layout (layout_check) before you finish; act on every issue.'},
 {'id': 'R3', 'rule': 'A partial result is evidence twice: name which part worked and which did not.'},
 {'id': 'R4', 'rule': 'A solution carries the fix; solution_check says whether yours does.'},
 {'id': 'I2', 'rule': 'A fix that regresses what is Established is not a fix.'},
 {'id': 'I3', 'rule': 'Do not re-try what is ruled out.'},
 {'id': 'I8', 'rule': 'Retrieve the conversation a turn at a time; never read it whole.'}]
RECORD_FIELDS = ['problem',
 'approaches',
 'answer',
 'open_failure',
 'fix',
 'must_keep_passing',
 'lesson',
 'retried_ruled_out',
 'new_skill_created',
 'research_validate_issues',
 'layout_check_issues',
 'solution_check_issues']
CHECKS = [{'check': 'problem_line', 'kind': 'nonempty', 'field': 'problem', 'fix': 'write PROBLEM first: the one failure you are solving (I6)'},
 {'check': 'approach_lines',
  'kind': 'min_items',
  'field': 'approaches',
  'n': 1,
  'fix': 'write an APPROACH line before each thing you try: a pass that reports only ANSWER cannot be audited (I6)'},
 {'check': 'answer_line',
  'kind': 'nonempty',
  'field': 'answer',
  'fix': "end with one ANSWER, even 'could not confirm X or Y; next check is Z' (I6, I5)"},
 {'check': 'open_failure_named', 'kind': 'nonempty', 'field': 'open_failure', 'fix': "start from tracker.md's Open: the test and its error (I1)"},
 {'check': 'fix_executable',
  'kind': 'each_has',
  'field': 'fix',
  'keys': ['file', 'change'],
  'fix': 'write the change precisely enough to apply: file, function, and what the line becomes (I4)'},
 {'check': 'keeps_established', 'kind': 'nonempty', 'field': 'must_keep_passing', 'fix': 'list what must keep passing from Established (I2)'},
 {'check': 'lesson_written',
  'kind': 'nonempty',
  'field': 'lesson',
  'fix': 'skill_write_lesson what the attempt tried and how it failed, naming broken tests (I7)'},
 {'check': 'no_ruled_out_retry',
  'kind': 'false',
  'field': 'retried_ruled_out',
  'fix': 'a diagnosis landing on Ruled out is the wrong diagnosis: say what is different or find another cause (I3)'},
 {'check': 'one_solution_skill',
  'kind': 'false',
  'field': 'new_skill_created',
  'fix': 'update the existing solution skill; two skills for one task split every retrieval (I4)'},
 {'check': 'record_valid',
  'kind': 'max_items',
  'field': 'research_validate_issues',
  'n': 0,
  'fix': 'act on every research_validate issue and call it again (R2)'},
 {'check': 'layout_ok',
  'kind': 'max_items',
  'field': 'layout_check_issues',
  'n': 0,
  'fix': 'act on every layout_check issue: a misfiled solution is never reused (I9, R2)'},
 {'check': 'carries_fix',
  'kind': 'max_items',
  'field': 'solution_check_issues',
  'n': 0,
  'fix': 'act on solution_check: the skill must carry the fix as a diff, not a description (R4)'}]


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
    def phronix_task_research_plan(goal: str, facts: dict = None) -> dict:
        "Render the one-failure research procedure as an ordered checklist: lessons first, PROBLEM line, the Open failure, keep Established, avoid Ruled out, write fix + lesson, validate record, layout and solution. Use it before applying the phronix-task-research procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: budget_exhausted (the budget ran out before the cause was certain), open_has_traceback (Open names an error with file and line), needs_restructure (the correct fix genuinely needs restructuring); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_task_research_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_task_research_check(record: dict) -> dict:
        "Check a task-research pass report: PROBLEM/APPROACH/ANSWER lines, the open failure named, the fix written into the existing solution skill (change, why-this-form, must-keep-passing), a lesson written, nothing ruled-out retried, and research_validate/layout_check/solution_check run clean. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields problem, approaches, answer, open_failure, fix, must_keep_passing, lesson, retried_ruled_out, new_skill_created, research_validate_issues, layout_check_issues, solution_check_issues). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
