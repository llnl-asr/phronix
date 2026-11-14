"""phronix_build_solution: turn what the explored ideas found into the solution (framework process capability, converted from dftracer-agents skill phronix-build-solution).

phronix_build_solution_plan renders the procedure as an ordered checklist (predictor); phronix_build_solution_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-build-solution'
VALIDATOR = 'phronix_build_solution_check'
FACTS = ["thin_findings", "two_ideas_combine"]
STEPS = [{'id': 'I5',
  'step': 'Open the skill for {goal} with the problem it solves: the symptom (what was observed wrong), the case (the failing test or smallest '
          'input), the cause (where in the code the behaviour comes from).',
  'done_when': 'symptom, case and cause are the first paragraph'},
 {'id': 'I1',
  'step': 'Write the solution as an ordered pipeline of steps, each one thing done, with a way to tell whether it worked (not an essay, not a '
          'description of the bug).',
  'done_when': 'every step has an action and a check'},
 {'id': 'I2',
  'step': 'Build every deterministic step (same inputs, same answer: reproduce, locate a call site, apply a known edit, run a check, compare '
          'before/after) as an MCP tool with capability_new, named for the question it answers.',
  'done_when': 'each deterministic step names its tool'},
 {'id': 'I3',
  'step': 'Keep as prose only what needs judgement: which step when a check is ambiguous, the trade-off between two fixes, what to look at when the '
          'reproduction does not reproduce.',
  'done_when': 'the prose holds only judgement a competent agent could not work out alone'},
 {'id': 'I4',
  'step': 'Build from all three findings including the failures: one line each on what was tried and did not work, stated as what failed (where the '
          'check was added, which path it missed), not as an idea to abandon.',
  'done_when': "every failed direction is a 'what failed' line next to the step it would tempt"},
 {'id': 'I4b',
  'step': 'Combine the parts the two ideas found: the solution is their combination.',
  'done_when': 'both parts appear in the pipeline',
  'when': 'two_ideas_combine'},
 {'id': 'X1',
  'step': 'Do not explore: build the solution the thin findings support and say plainly what is unverified.',
  'done_when': 'unverified parts are marked',
  'when': 'thin_findings'},
 {'id': 'I5b',
  'step': 'List the corner cases: for every step, what a smaller model would plausibly write instead and why it fails (look-alike constructs, '
          'insufficient subsets with their score, neighbouring style that will be copied, the test a correct fix breaks); specific to this task.',
  'done_when': 'each step has its task-specific corner cases'},
 {'id': 'R0',
  'step': 'Read it back: could someone fix the problem from the Instructions alone (file, function, line, what to change it to)? Every cited label '
          'must resolve to a section of this skill.',
  'done_when': 'Instructions are self-sufficient and every label resolves'},
 {'id': 'I6',
  'step': 'Attach it by subject (not instance id), call graph_ensure, and record the pipeline with research_record_pipeline / '
          'research_adopt_pipeline.',
  'done_when': 'graph_ensure ran and the pipeline is recorded'}]
RULES = [{'id': 'R0',
  'rule': 'A skill that solves a problem must say how to solve it: the Instructions contain the steps that fix it (file, function, line, what to '
          'change it to); every cited label resolves.'},
 {'id': 'R1',
  'rule': 'This stage has no clock: its input is fixed, it may not explore, and its output (tools and skill) is the only thing that survives the '
          'task.'},
 {'id': 'X1', 'rule': 'Do not explore here: if the findings are thin, build what they support and say what is unverified.'},
 {'id': 'I2', 'rule': 'If a step reads as prose but has one correct answer given its inputs, it is a tool you have not built yet.'}]
RECORD_FIELDS = ['problem',
 'steps',
 'tools_built',
 'judgement',
 'failed_directions',
 'corner_cases',
 'unresolved_labels',
 'unverified',
 'attached_subject',
 'graph_ensured',
 'pipeline_recorded']
CHECKS = [{'check': 'problem_symptom', 'kind': 'nonempty', 'field': 'problem.symptom', 'fix': 'open with the symptom: what was observed to be wrong (I5)'},
 {'check': 'problem_case', 'kind': 'nonempty', 'field': 'problem.case', 'fix': 'name the failing test or the smallest input that shows it (I5)'},
 {'check': 'problem_cause', 'kind': 'nonempty', 'field': 'problem.cause', 'fix': 'say where in the code the behaviour comes from (I5)'},
 {'check': 'instructions_not_empty',
  'kind': 'min_items',
  'field': 'steps',
  'n': 1,
  'fix': 'the Instructions must hold the steps that fix the problem: file, function, line, what to change it to (R0)'},
 {'check': 'steps_checkable',
  'kind': 'each_has',
  'field': 'steps',
  'keys': ['action', 'check'],
  'fix': 'each step is one thing done with a way to tell whether it worked (I1)'},
 {'check': 'deterministic_steps_are_tools',
  'kind': 'each_if',
  'field': 'steps',
  'if': {'key': 'deterministic', 'equals': True},
  'then': {'key': 'tool', 'test': 'nonempty'},
  'fix': 'build the deterministic step as an MCP tool with capability_new and name it in the step (I2)'},
 {'check': 'failures_not_abandonments',
  'kind': 'absent',
  'field': 'failed_directions',
  'pattern': "does not work|doesn't work|abandon|is falsified|no longer valid",
  'fix': 'say what failed (where it was implemented and what it missed), not what to abandon (I4)'},
 {'check': 'corner_cases_listed',
  'kind': 'min_items',
  'field': 'corner_cases',
  'n': 1,
  'fix': 'list per step what a smaller model would write instead and why it fails (I5b)'},
 {'check': 'labels_resolve',
  'kind': 'max_items',
  'field': 'unresolved_labels',
  'n': 0,
  'fix': 'every label cited must be a section of this skill; a research approach id is not one (R0, R0b)'},
 {'check': 'attached_by_subject',
  'kind': 'absent',
  'field': 'attached_subject',
  'pattern': '__|-\\d{3,}$',
  'fix': 'attach to the subject the problem belongs to, not the instance id (I6)'},
 {'check': 'graph_linked', 'kind': 'true', 'field': 'graph_ensured', 'fix': 'call graph_ensure after writing (I6)'},
 {'check': 'pipeline_recorded',
  'kind': 'true',
  'field': 'pipeline_recorded',
  'fix': 'record the pipeline with research_record_pipeline / research_adopt_pipeline (I6)'}]


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
    def phronix_build_solution_plan(goal: str, facts: dict = None) -> dict:
        "Render the build-solution procedure for one task's explored findings as an ordered checklist: problem statement first, pipeline of checkable steps, every deterministic step built as a capability, judgement as prose, failed directions stated as what failed, corner cases, attach and record the pipeline. Use it before applying the phronix-build-solution procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: thin_findings (the explored findings are thin or partly unverified), two_ideas_combine (two ideas each found part of the answer); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_build_solution_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_build_solution_check(record: dict) -> dict:
        "Check a drafted solution skill (as an object): it opens with symptom, case and cause; its Instructions hold ordered steps with file/function and what to change, each with a check; deterministic steps are tools; failures are stated as what failed, not what to abandon; corner cases are listed; every cited label resolves; it is attached by subject and the pipeline recorded. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields problem, steps, tools_built, judgement, failed_directions, corner_cases, unresolved_labels, unverified, attached_subject, graph_ensured, pipeline_recorded). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
