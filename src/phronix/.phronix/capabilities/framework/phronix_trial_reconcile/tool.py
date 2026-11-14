"""phronix_trial_reconcile: reconciling the results of parallel solution trials (framework process capability, converted from dftracer-agents skill phronix-trial-reconcile).

phronix_trial_reconcile_plan renders the procedure as an ordered checklist (predictor); phronix_trial_reconcile_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-trial-reconcile'
VALIDATOR = 'phronix_trial_reconcile_check'
FACTS = ["none_passed", "one_passed", "several_passed"]
STEPS = [{'id': 'I1',
  'step': "Read the trial table for {goal} as evidence about the ranking: record e.g. 'the metric ranked B first and C solved it'.",
  'done_when': 'ranking finding recorded'},
 {'id': 'I2',
  'step': 'Several passed: the fix is what the passing candidates agree on; where they differ prefer the smaller change; record it was confirmed by '
          'more than one candidate; failures become one-line lessons saying whether the implementation or the idea failed.',
  'done_when': "solution written from the passing candidates' agreement",
  'when': 'several_passed'},
 {'id': 'I2b',
  'step': "Exactly one passed: skill_load winner and losers; the winner's steps are the spine; fold in what a loser did better (cheaper check, more "
          'direct tool, a generalising step); retire the rest by name. Merging is not concatenation.',
  'done_when': "one merged skill on the winner's spine",
  'when': 'one_passed'},
 {'id': 'I3.1',
  'step': 'None passed: name what every approach took for granted, written as a claim that could be false (do not refine the least-bad).',
  'done_when': 'shared assumption stated as a falsifiable claim',
  'when': 'none_passed'},
 {'id': 'I3.2',
  'step': 'Check that claim with a command whose output settles it: a run, not an argument.',
  'done_when': 'command and its output recorded',
  'when': 'none_passed'},
 {'id': 'I3.3',
  'step': 'Say which failures the claim explains (one of four is probably not it).',
  'done_when': 'explained failures listed',
  'when': 'none_passed'},
 {'id': 'I3.4',
  'step': 'Produce candidates against the corrected understanding and record them with research_add_approach.',
  'done_when': 'new approaches recorded',
  'when': 'none_passed'},
 {'id': 'I3b',
  'step': 'Carry every failed candidate forward as a named corner case: what it did, why it looked right, what it scored, naming the '
          'construct/site/subset.',
  'done_when': 'each failed candidate has a corner case'},
 {'id': 'I3c',
  'step': "Find which step's expectation first did not hold and call research_record_step_reached(topic, '<step>', '<what the output showed>'); if "
          'steps did not compose or an unplanned step was needed, say that.',
  'done_when': 'failing step recorded'},
 {'id': 'R2b',
  'step': "Link every candidate skill ([[name]]) from the subject's skill with one line each on the idea and what the tests did; do not copy them "
          'in.',
  'done_when': 'all candidates linked'},
 {'id': 'I4',
  'step': "State outcome (does it fix this task's tests), cost (tokens, time) and transfer (how much applies to a different task in this subject), "
          'in that order.',
  'done_when': 'three scores stated'},
 {'id': 'R0',
  'step': "Read back: the skill's ## Instructions contain the fix (file, function, line, change) and every cited label resolves.",
  'done_when': 'someone could fix it from the Instructions alone'}]
RULES = [{'id': 'R0', 'rule': 'A skill that solves a problem must say how to solve it (see phronix_skill_authoring R0/R0b).'},
 {'id': 'R1', 'rule': 'A losing approach is not wrong in every part: take the parts measured to work and say which trial each came from.'},
 {'id': 'R2', 'rule': 'Do not refine the least-bad candidate: furthest is not closest.'},
 {'id': 'R2b', 'rule': "The subject's skill is the way in to the candidates: link them all, winners and losers; do not copy them in."}]
RECORD_FIELDS = ['ranking_finding',
 'passed',
 'candidates',
 'branch',
 'shared_assumption',
 'assumption_check',
 'corner_cases',
 'step_reached',
 'links',
 'outcome',
 'cost',
 'transfer',
 'instructions']
CHECKS = [{'check': 'ranking_recorded',
  'kind': 'nonempty',
  'field': 'ranking_finding',
  'fix': "record what the table says about the research metric's ranking (I1)"},
 {'check': 'branch_known', 'kind': 'one_of', 'field': 'branch', 'values': ['several', 'one', 'none'], 'fix': 'branch is several, one or none passed'},
 {'check': 'assumption_stated',
  'kind': 'nonempty',
  'field': 'shared_assumption',
  'when': {'field': 'branch', 'equals': 'none'},
  'fix': 'none passed: name the assumption every approach shared, as a claim that could be false; do not refine the least-bad (I3, R2)'},
 {'check': 'assumption_checked',
  'kind': 'nonempty',
  'field': 'assumption_check',
  'when': {'field': 'branch', 'equals': 'none'},
  'fix': 'check the shared assumption with a command whose output settles it (I3 step 2)'},
 {'check': 'failures_carried',
  'kind': 'min_items',
  'field': 'corner_cases',
  'n': 1,
  'when': {'field': 'branch', 'in': ['one', 'none']},
  'fix': 'carry each failed candidate forward as a named corner case with what it scored (I3b)'},
 {'check': 'step_recorded', 'kind': 'nonempty', 'field': 'step_reached', 'fix': 'record which step failed with research_record_step_reached (I3c)'},
 {'check': 'candidates_linked',
  'kind': 'each_regex',
  'field': 'links',
  'pattern': '\\[\\[.+\\]\\]',
  'fix': 'link every candidate skill with [[name]], winners and losers (R2b)'},
 {'check': 'outcome_cost_transfer', 'kind': 'nonempty', 'field': 'transfer', 'fix': 'state outcome, cost and transfer, in that order (I4)'},
 {'check': 'instructions_present',
  'kind': 'min_items',
  'field': 'instructions',
  'n': 1,
  'when': {'field': 'branch', 'in': ['several', 'one']},
  'fix': "the merged skill's Instructions must carry the fix (R0)"}]


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
    def phronix_trial_reconcile_plan(goal: str, facts: dict = None) -> dict:
        "Render the trial-reconcile procedure as an ordered checklist, branching on how many candidates passed: several (agreement), one (winner's spine), none (shared assumption). Use it before applying the phronix-trial-reconcile procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: several_passed (more than one candidate passed), one_passed (exactly one candidate passed), none_passed (no candidate passed); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_trial_reconcile_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_trial_reconcile_check(record: dict) -> dict:
        "Check a reconciliation record: ranking finding recorded, outcome branch consistent with the pass count, failures carried as named corner cases, failing step recorded, every candidate linked, outcome/cost/transfer stated, and (none passed) a falsifiable shared assumption checked by a command. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields ranking_finding, passed, candidates, branch, shared_assumption, assumption_check, corner_cases, step_reached, links, outcome, cost, transfer, instructions). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
