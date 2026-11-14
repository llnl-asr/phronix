"""phronix_solution_candidate: turning one researched approach into an executable solution skill (framework process capability, converted from dftracer-agents skill phronix-solution-candidate).

phronix_solution_candidate_plan renders the procedure as an ordered checklist (predictor); phronix_solution_candidate_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-solution-candidate'
VALIDATOR = 'phronix_solution_candidate_check'
FACTS = ["approach_proved_wrong", "tools_exist"]
STEPS = [{'id': 'I1',
  'step': "Write what to DO for the approach '{goal}', in order, for an agent that has never seen the task and cannot ask you; conclusions, promise "
          'and ruled-out ideas stay in the research record.',
  'done_when': 'the skill is an ordered list of actions'},
 {'id': 'I2',
  'step': 'For each step name the tool and its arguments where one exists; otherwise one instruction a reader follows without inferring anything. '
          "'Investigate whether' is research leaking in: decide it now or build the tool that decides it.",
  'done_when': 'every step names a tool call or a single unambiguous instruction'},
 {'id': 'I2b',
  'step': 'Name the exact tool call with arguments for each step that has one (e.g. probe_ignore_paths_matrix(path=...)).',
  'done_when': 'tool steps carry arguments',
  'when': 'tools_exist'},
 {'id': 'I3',
  'step': 'Give every step its own check: what proves it worked, so a failure surfaces at the step that caused it.',
  'done_when': 'each step has a check'},
 {'id': 'R1',
  'step': 'State the approach at its fairest: do not hedge toward rivals or soften a claim you believe.',
  'done_when': 'no hedging toward other approaches'},
 {'id': 'R1b',
  'step': "Say plainly the approach is wrong (that is a result); do not widen the skill to cover someone else's idea.",
  'done_when': 'the skill says it is wrong and why',
  'when': 'approach_proved_wrong'},
 {'id': 'R2', 'step': 'Keep it short: lead with the action, one idea per block, split rather than combine.', 'done_when': 'no block holds two ideas'}]
RULES = [{'id': 'R1',
  'rule': "Give your approach its fairest statement; if it is wrong, say so plainly rather than widening it to cover someone else's idea."},
 {'id': 'R2', 'rule': 'Short, because every block is read forever: lead with the action, one idea per block.'},
 {'id': 'R3', 'rule': 'Yours is kept and linked, whatever the outcome: write it to stand on its own, including if it loses.'}]
RECORD_FIELDS = ['approach', 'steps', 'wrong_if']
CHECKS = [{'check': 'one_approach', 'kind': 'nonempty', 'field': 'approach', 'fix': 'name the ONE approach this candidate states'},
 {'check': 'steps_present', 'kind': 'min_items', 'field': 'steps', 'n': 1, 'fix': 'write what to DO, in order (I1)'},
 {'check': 'each_step_has_check',
  'kind': 'each_has',
  'field': 'steps',
  'keys': ['do', 'check'],
  'fix': 'every step carries its own check: what proves it worked (I3)'},
 {'check': 'no_research_leak',
  'kind': 'absent',
  'field': 'steps',
  'pattern': 'investigate whether|we concluded|might be worth',
  'fix': "'investigate whether' is research leaking into a solution: decide it now, or build the tool that decides it (I2)"},
 {'check': 'falsifiable',
  'kind': 'nonempty',
  'field': 'wrong_if',
  'fix': "say which step's check failing shows the approach is wrong, so a losing candidate is informative (I3, R3)"}]


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
    def phronix_solution_candidate_plan(goal: str, facts: dict = None) -> dict:
        "Render the candidate-writing procedure for one approach as an ordered checklist: steps not story, a tool per step, a check per step, fairest statement, short blocks. Use it before applying the phronix-solution-candidate procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: tools_exist (MCP tools exist for some of the steps), approach_proved_wrong (the approach turned out to be wrong while writing it); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_solution_candidate_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_solution_candidate_check(record: dict) -> dict:
        "Check a candidate solution skill record: one approach, ordered steps each with a check, a tool named where one exists, no research leaking in ('investigate whether'), and a statement of what would show the approach is wrong. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields approach, steps, wrong_if). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
