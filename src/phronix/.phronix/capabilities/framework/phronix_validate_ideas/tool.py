"""phronix_validate_ideas: judge whether a plan's ideas are worth exploring (framework process capability, converted from dftracer-agents skill phronix-validate-ideas).

phronix_validate_ideas_plan renders the procedure as an ordered checklist (predictor); phronix_validate_ideas_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-validate-ideas'
VALIDATOR = 'phronix_validate_ideas_check'
FACTS = ["fewer_than_three"]
STEPS = [{'id': 'I1',
  'step': 'Judge each idea of {goal}: could change what we do; answerable in two minutes by trying something; independent of the others; not already '
          'settled.',
  'done_when': 'each idea judged on the four tests'},
 {'id': 'I2', 'step': 'Drop a bad idea with a one-line reason; do not rewrite it into a different idea.', 'done_when': 'each drop has a reason'},
 {'id': 'I2b',
  'step': "Judge the SET: compare each idea's `where`; two in the same file/function are one idea; send the list back naming which two clashed and "
          'where. Ask for a `where` when missing.',
  'done_when': 'no two kept ideas share a where'},
 {'id': 'I2c',
  'step': "Judge the decomposition: jointly sufficient, ordered, separately checkable, and includes 'the cases that already work still work'.",
  'done_when': 'the four method properties answered'},
 {'id': 'I2r',
  'step': 'Record survivors with research_set_aspects in priority order (the list written IS the list explored).',
  'done_when': 'research_set_aspects called'},
 {'id': 'I3', 'step': 'State how many good ideas remain; do not pad to three.', 'done_when': 'count stated'},
 {'id': 'I3b',
  'step': 'Fewer than three: the plan runs again; name the rejections specifically so the next plan does not repeat them.',
  'done_when': 'rejections named specifically',
  'when': 'fewer_than_three'},
 {'id': 'X1',
  'step': 'Judge from what you were given and stop: a lookup or two at most, no wandering through skills, memories or probes.',
  'done_when': 'verdict recorded'}]
RULES = [{'id': 'R1', 'rule': 'The corrector is unbudgeted and the predictor is not: judging a list of three is bounded by the list.'},
 {'id': 'X1', 'rule': 'Judge from what you were given, and stop: an unrecorded judgement is worth less than a quick one.'},
 {'id': 'X2', 'rule': 'Do not explore, and do not solve.'}]
RECORD_FIELDS = ['ideas', 'decomposition', 'recorded', 'count']
CHECKS = [{'check': 'ideas_judged',
  'kind': 'each_has',
  'field': 'ideas',
  'keys': ['name', 'keep', 'reason'],
  'fix': 'keep or drop every idea with a one-line reason (I2)'},
 {'check': 'kept_have_where',
  'kind': 'each_if',
  'field': 'ideas',
  'if': {'key': 'keep', 'equals': True},
  'then': {'key': 'where', 'test': 'nonempty'},
  'fix': 'an idea with no where cannot be checked for overlap: ask for one (I2b)'},
 {'check': 'no_overlap',
  'kind': 'unique',
  'field': 'ideas',
  'if': {'key': 'keep', 'equals': True},
  'key': 'where',
  'fix': 'two kept ideas investigate the same place: they are one idea; send the list back naming which two clashed and where (I2b)'},
 {'check': 'decomposition_judged',
  'kind': 'each_has',
  'field': 'decomposition',
  'keys': ['sufficient', 'ordered', 'checkable', 'no_regressions'],
  'fix': 'judge the steps as a method: sufficient, ordered, checkable, includes not breaking things (I2c)'},
 {'check': 'recorded',
  'kind': 'regex',
  'field': 'recorded',
  'pattern': 'research_set_aspects',
  'fix': 'record survivors with research_set_aspects in priority order (I2)'},
 {'check': 'count_stated', 'kind': 'number', 'field': 'count', 'min': 0, 'max': 3, 'fix': 'state how many good ideas remain, 0-3; do not pad (I3)'}]


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
    def phronix_validate_ideas_plan(goal: str, facts: dict = None) -> dict:
        "Render the idea-validation procedure as an ordered checklist: judge each idea, drop bad ones with a reason, judge the set for overlap and the decomposition, record survivors in priority order, state the count. Use it before applying the phronix-validate-ideas procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: fewer_than_three (fewer than three good ideas remain); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_validate_ideas_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_validate_ideas_check(record: dict) -> dict:
        "Check an idea-validation verdict: each idea kept or dropped with a one-line reason, every kept idea names its 'where', no two kept ideas share a 'where', the decomposition judged (sufficient/ordered/checkable/no-regressions), survivors recorded via research_set_aspects, and the count stated and not padded. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields ideas, decomposition, recorded, count). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
