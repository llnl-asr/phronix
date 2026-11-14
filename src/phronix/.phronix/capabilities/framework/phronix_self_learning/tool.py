"""phronix_self_learning: recording what a session learned so the next one inherits it (framework process capability, converted from dftracer-agents skill phronix-self-learning).

phronix_self_learning_plan renders the procedure as an ordered checklist (predictor); phronix_self_learning_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-self-learning'
VALIDATOR = 'phronix_self_learning_check'
FACTS = ["generic_rule", "nothing_learned"]
STEPS = [{'id': 'I1',
  'step': 'Check before you act for {goal}: context_skills/context_memory (knowledge_search, lesson_search) and act on what comes back.',
  'done_when': 'existing knowledge read'},
 {'id': 'R1',
  'step': 'Say explicitly that nothing new was learned (silence is indistinguishable from skipping the step).',
  'done_when': "explicit 'nothing new' recorded",
  'when': 'nothing_learned'},
 {'id': 'I2',
  'step': 'Enumerate what actually happened: every error and what actually fixed it, every non-obvious ordering/flag/version/path, every user answer '
          'and correction, every procedure done by hand more than once; include the working recipe (R2).',
  'done_when': 'candidate list written',
  'unless': 'nothing_learned'},
 {'id': 'I3',
  'step': 'Route each item to its tier: fixed procedure -> capability_new; step -> skill instruction; constraint -> skill rule; trap -> pitfall; '
          'dated symptom->cause->fix -> lesson; durable fact -> memory(project); user guidance -> memory(feedback) WITH why; rule for every agent -> '
          'common-sections.yaml + agents_sync.',
  'done_when': 'every item has a tier',
  'unless': 'nothing_learned'},
 {'id': 'R8',
  'step': 'A rule for every agent: add it to common-sections.yaml, include: it, agents_sync.',
  'done_when': 'shared section added and synced',
  'when': 'generic_rule'},
 {'id': 'I4',
  'step': 'De-duplicate: search for each item; if recorded, do not restate, but say whether the new finding contradicts or sharpens the entry.',
  'done_when': 'duplicates dropped, contradictions flagged',
  'unless': 'nothing_learned'},
 {'id': 'I5',
  'step': 'Write, then read back what you wrote as a session with no context would.',
  'done_when': 'read back',
  'unless': 'nothing_learned'},
 {'id': 'I6',
  'step': 'Prove it (verify_run / verify_new corrector), then privacy_scan(): everything written is committed and shared.',
  'done_when': 'verification passes and scan clean',
  'unless': 'nothing_learned'}]
RULES = [{'id': 'R1', 'rule': 'Recording is mandatory; if nothing new was learned, say so explicitly.'},
 {'id': 'R2', 'rule': 'The working recipe counts as a lesson: record the exact commands, flags, versions and paths that succeeded.'},
 {'id': 'R3', 'rule': 'Never put a deterministic procedure in prose: write the capability.'},
 {'id': 'R4', 'rule': 'Never put a judgment call in a capability: it is a skill.'},
 {'id': 'R5', 'rule': 'Lead with the symptom as it actually appears: paste the error text.'},
 {'id': 'R6', 'rule': 'Record the root cause, not the first hypothesis; earlier tries only as labelled dead ends.'},
 {'id': 'R7', 'rule': "Appending is safe; rewriting, deleting or changing an agent's behaviour needs the user's confirmation."},
 {'id': 'R8', 'rule': 'A generic rule must reach every agent: common-sections.yaml, include:, agents_sync.'}]
RECORD_FIELDS = ['checked_existing', 'nothing_learned', 'items', 'privacy_scan']
CHECKS = [{'check': 'checked_existing',
  'kind': 'true',
  'field': 'checked_existing',
  'fix': 'search skills, lessons and memory first and act on what comes back (I1)'},
 {'check': 'explicit_outcome',
  'kind': 'min_items',
  'field': 'items',
  'n': 1,
  'when': {'field': 'nothing_learned', 'in': [None, False]},
  'fix': 'enumerate what happened (I2), or set nothing_learned=true explicitly (R1)'},
 {'check': 'items_routed',
  'kind': 'each_if',
  'field': 'items',
  'then': {'key': 'tier',
           'test': 'one_of',
           'values': ['capability', 'instruction', 'rule', 'pitfall', 'lesson', 'memory_project', 'memory_feedback', 'common_section']},
  'when': {'field': 'items', 'filled': True},
  'fix': 'route every item to a tier (I3 table)'},
 {'check': 'items_have_text',
  'kind': 'each_has',
  'field': 'items',
  'keys': ['tier', 'text'],
  'when': {'field': 'items', 'filled': True},
  'fix': 'every item needs its tier and its text'},
 {'check': 'lessons_lead_with_symptom',
  'kind': 'each_if',
  'field': 'items',
  'if': {'key': 'tier', 'equals': 'lesson'},
  'then': {'key': 'text', 'test': 'regex', 'pattern': '->|→'},
  'when': {'field': 'items', 'filled': True},
  'fix': "a lesson is '<error text as it appears> -> root cause -> fix' (R5, R6, P1)"},
 {'check': 'feedback_has_why',
  'kind': 'each_if',
  'field': 'items',
  'if': {'key': 'tier', 'equals': 'memory_feedback'},
  'then': {'key': 'text', 'test': 'regex', 'pattern': 'why'},
  'when': {'field': 'items', 'filled': True},
  'fix': 'user guidance goes to a feedback memory WITH the why (I3)'},
 {'check': 'rewrites_confirmed',
  'kind': 'each_if',
  'field': 'items',
  'if': {'key': 'action', 'in': ['rewrite', 'delete', 'change_agent']},
  'then': {'key': 'confirmed', 'test': 'true'},
  'when': {'field': 'items', 'filled': True},
  'fix': "append without asking, but a rewrite, delete or agent-behaviour change needs the user's confirmation (R7)"},
 {'check': 'privacy_clean',
  'kind': 'one_of',
  'field': 'privacy_scan',
  'values': ['clean'],
  'when': {'field': 'items', 'filled': True},
  'fix': 'run privacy_scan() after writing and redact until clean (I6)'}]


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
    def phronix_self_learning_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-self-learning end-of-session procedure as an ordered checklist: check existing knowledge, enumerate what happened, route each item to its tier, de-duplicate, write and read back, prove, privacy-scan. Use it before applying the phronix-self-learning procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: nothing_learned (the session genuinely learned nothing new), generic_rule (an item is a rule every agent should follow); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_self_learning_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_self_learning_check(record: dict) -> dict:
        "Check a session-learning record: existing knowledge was checked, items were enumerated (or 'nothing new' said explicitly), each item has a tier, lessons lead with the error text and give root cause and fix, working recipes are included, rewrites have user confirmation, and the privacy scan is clean. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields checked_existing, nothing_learned, items, privacy_scan). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
