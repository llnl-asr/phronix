"""phronix_verification: deterministic correctors that prove learned and healed things still hold (framework process capability, converted from dftracer-agents skill phronix-verification).

phronix_verification_plan renders the procedure as an ordered checklist (predictor); phronix_verification_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-verification'
VALIDATOR = 'phronix_verification_check'
FACTS = ["red_result"]
STEPS = [{'id': 'I1',
  'step': 'Run what already exists: verify_coverage() (orphaned_verifiers, broken_verifiers, never_run all need fixing) and verify_run().',
  'done_when': 'coverage gaps listed'},
 {'id': 'I2',
  'step': "Write the claim for {goal} so it could be wrong ('the flag is spelled --jobs', not 'the service works').",
  'done_when': 'claim is falsifiable'},
 {'id': 'I3',
  'step': 'Fill the five facets in order: assumptions (what must be true for the check to mean anything), inputs (each with a resolve callable), '
          'constraints (the claim), invariants (sampled before and after), outputs (what must exist afterwards, in what shape).',
  'done_when': 'all five facets filled'},
 {'id': 'I4',
  'step': 'verify_new(kind, target, claim, source) then verify_run(name=...): a corrector that never executed is not evidence.',
  'done_when': 'corrector has run'},
 {'id': 'I5',
  'step': 'Diagnose the red result before changing anything: (1) claim always wrong -> fix entry, record what made it plausible; (2) claim rotted -> '
          'update, keep old as dated note; (3) corrector wrong -> fix corrector; (4) assumption miscategorised as constraint -> move it.',
  'done_when': 'cause named among the four',
  'when': 'red_result'}]
RULES = [{'id': 'R1', 'rule': 'Nothing is learned or healed until its corrector runs: verify_run(target=...) after every write and every fix.'},
 {'id': 'R2',
  'rule': 'Every check must be deterministic: no model calls, clock/calendar branching, randomness, or network unless the claim is about the '
          'network.'},
 {'id': 'R3', 'rule': 'A failed assumption is inconclusive, never a failure.'},
 {'id': 'R4', 'rule': 'An invariant violation invalidates the whole run.'},
 {'id': 'R5', 'rule': 'A spec with no constraints and no outputs is rejected.'},
 {'id': 'R6', 'rule': 'Never make a check pass by removing what it checked.'},
 {'id': 'R7', 'rule': 'error is not fail: error = broken corrector/malformed spec; fail = claim did not hold; reported separately.'},
 {'id': 'R8',
  'rule': 'Do not duplicate the built-in structural correctors (frontmatter, labels, index, references, compilation, docstrings, renderability, '
          'privacy).'}]
RECORD_FIELDS = ['claim', 'assumptions', 'inputs', 'constraints', 'invariants', 'outputs', 'deterministic', 'ran', 'verdict', 'diagnosis']
CHECKS = [{'check': 'claim_falsifiable',
  'kind': 'absent',
  'field': 'claim',
  'pattern': '^\\s*$|\\b(works|is fine|is ok|looks right)\\s*\\.?\\s*$',
  'fix': 'write the claim so it could be wrong (I2)'},
 {'check': 'claim_present', 'kind': 'nonempty', 'field': 'claim', 'fix': 'state the claim the corrector checks (I2)'},
 {'check': 'has_constraint_or_output',
  'kind': 'regex',
  'field': '*',
  'pattern': '\\"(constraints|outputs)\\": \\[\\s*\\"',
  'fix': 'a spec with no constraints and no outputs cannot fail; state at least one (R5)'},
 {'check': 'env_in_assumptions',
  'kind': 'absent',
  'field': 'constraints',
  'pattern': 'installed|reachable|available|exists on (the )?path|module load',
  'fix': 'an environment precondition is an assumption, not a constraint: move it (I5 case 4, R3)'},
 {'check': 'no_trivial_constraint',
  'kind': 'absent',
  'field': 'constraints',
  'pattern': 'lambda[^:]*:\\s*True|^\\s*true\\s*$',
  'fix': 'a constraint nothing can turn red checks nothing: delete or replace it (R6, P3)'},
 {'check': 'deterministic',
  'kind': 'true',
  'field': 'deterministic',
  'fix': 'remove model calls, clock branching, randomness and unneeded network from the check (R2)'},
 {'check': 'ran', 'kind': 'true', 'field': 'ran', 'fix': 'verify_run(name=...): a corrector that never executed is not evidence (I4, R1)'},
 {'check': 'verdict_known',
  'kind': 'one_of',
  'field': 'verdict',
  'values': ['pass', 'fail', 'error', 'inconclusive'],
  'fix': 'verdict is pass, fail, error (broken corrector) or inconclusive (assumption failed) (R3, R7)'},
 {'check': 'red_diagnosed',
  'kind': 'one_of',
  'field': 'diagnosis',
  'values': ['claim_wrong', 'claim_rotted', 'corrector_wrong', 'assumption_as_constraint'],
  'when': {'field': 'verdict', 'equals': 'fail'},
  'fix': 'diagnose a red result into one of the four causes before changing anything (I5)'}]


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
    def phronix_verification_plan(goal: str, facts: dict = None) -> dict:
        "Render the corrector-authoring procedure as an ordered checklist: run what exists, make the claim falsifiable, fill the five facets, write and run it, diagnose a red result. Use it before applying the phronix-verification procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: red_result (a corrector came back red (fail)); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_verification_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_verification_check(record: dict) -> dict:
        "Check a verifier spec / verdict record: falsifiable claim, five facets with at least one constraint or output, environment preconditions under assumptions not constraints, deterministic, actually run, and a red result diagnosed into one of the four causes. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields claim, assumptions, inputs, constraints, invariants, outputs, deterministic, ran, verdict, diagnosis). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
