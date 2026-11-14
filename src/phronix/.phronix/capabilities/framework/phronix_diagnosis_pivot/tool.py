"""phronix_diagnosis_pivot: diagnosing a failure that has stopped moving (framework process capability, converted from dftracer-agents skill phronix-diagnosis-pivot).

phronix_diagnosis_pivot_plan renders the procedure as an ordered checklist (predictor); phronix_diagnosis_pivot_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-diagnosis-pivot'
VALIDATOR = 'phronix_diagnosis_pivot_check'
FACTS = ["edits_not_run"]
STEPS = [{'id': 'I1',
  'step': "Name what both attempts at {goal} took for granted, as a claim someone could disprove (e.g. 'this function is the one that produces the "
          "output').",
  'done_when': 'the assumption is written as a falsifiable claim'},
 {'id': 'I2',
  'step': 'Check whether your edits even run on this path: a print, breakpoint or deliberate exception that cannot be true unless the edit runs '
          '(shadowing module, installed copy, unreached branch).',
  'done_when': 'proven executed, or proven not executed'},
 {'id': 'I2.fix',
  'step': 'The edits never ran: fix where they land (the module actually imported, the checkout vs installed copy, the reached branch) before '
          'changing any logic.',
  'done_when': 'the edit is proven to execute',
  'when': 'edits_not_run'},
 {'id': 'I3',
  'step': 'Read what the test asks for, literally, word by word: exact string, exact value, exact exception type; diff what was wanted against what '
          'was produced. Where they differ by a word, the word is the bug.',
  'done_when': 'wanted and produced are written side by side'},
 {'id': 'I4',
  'step': 'Take a different path (another file, mechanism, or reading of the test) and state in one line what makes it different from what failed '
          'twice; check research_ruled_out first.',
  'done_when': 'the one-line difference is stated and it is not in research_ruled_out'},
 {'id': 'R2',
  'step': 'Check the new plan is not the same edit with better values (re-indent, move, rename, constant change): would it still fail for the reason '
          'the last one did? If yes, go back to I1.',
  'done_when': 'the new plan would not fail for the same reason'}]
RULES = [{'id': 'R1', 'rule': 'An identical failure is evidence, not noise: it says the idea is wrong rather than the execution; do not retry or tidy.'},
 {'id': 'R2',
  'rule': 'The same edit with better values is not a new approach; a plan that leads back to a failed edit means the diagnosis is wrong: go back to '
          'I1.'}]
RECORD_FIELDS = ['failure', 'assumption', 'edits_run', 'wanted', 'produced', 'new_path', 'differs_because', 'same_edit']
CHECKS = [{'check': 'failure_quoted', 'kind': 'nonempty', 'field': 'failure', 'fix': 'quote the identical failure (tests, reason, missing text)'},
 {'check': 'assumption_stated',
  'kind': 'min_len',
  'field': 'assumption',
  'n': 15,
  'fix': 'state what both attempts assumed, as a claim that could be false (I1); you cannot pivot away from an unstated assumption'},
 {'check': 'edits_proven_to_run',
  'kind': 'one_of',
  'field': 'edits_run',
  'values': ['yes', 'no'],
  'fix': 'prove whether the edited code executes on this path (print/breakpoint/deliberate exception) (I2)'},
 {'check': 'test_read_literally', 'kind': 'nonempty', 'field': 'wanted', 'fix': 'write what the assertion wants, literally (I3)'},
 {'check': 'produced_recorded', 'kind': 'nonempty', 'field': 'produced', 'fix': 'write what the code produced next to what was wanted (I3)'},
 {'check': 'new_path', 'kind': 'nonempty', 'field': 'new_path', 'fix': 'name the different file, mechanism or reading of the test (I4)'},
 {'check': 'differs_stated',
  'kind': 'nonempty',
  'field': 'differs_because',
  'fix': 'say in one line what makes the new path different from what failed twice; if you cannot, you have not pivoted (I4)'},
 {'check': 'not_same_edit',
  'kind': 'false',
  'field': 'same_edit',
  'fix': 'the same edit with better values is not a new approach: go back to I1 (R2)'}]


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
    def phronix_diagnosis_pivot_plan(goal: str, facts: dict = None) -> dict:
        "Render the diagnosis-pivot procedure after two identical failures as an ordered checklist: name the shared assumption, prove the edits run, read the test literally, take a different path and say why it differs. Use it before applying the phronix-diagnosis-pivot procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: edits_not_run (the check showed the edited code is not executed on this path); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_diagnosis_pivot_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_diagnosis_pivot_check(record: dict) -> dict:
        "Check a pivot record: the shared assumption is stated as a falsifiable claim, the edits were proven to execute, the assertion was read literally (wanted vs produced), and the new path names why it differs from what failed twice and is not the same edit with better values. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields failure, assumption, edits_run, wanted, produced, new_path, differs_because, same_edit). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
