"""phronix_task_tracker: keeping one task's running record (framework process capability, converted from dftracer-agents skill phronix-task-tracker).

phronix_task_tracker_plan renders the procedure as an ordered checklist (predictor); phronix_task_tracker_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-task-tracker'
VALIDATOR = 'phronix_task_tracker_check'
FACTS = ["no_evidence", "other_task_id"]
STEPS = [{'id': 'I4',
  'step': 'The record mentions a different task id: say so and start a new record; never merge two tasks.',
  'done_when': 'a new record started',
  'when': 'other_task_id'},
 {'id': 'I1a',
  'step': 'Restate ## The problem for {goal} from the evidence (not copied from the issue), in two or three lines.',
  'done_when': 'problem restated'},
 {'id': 'I1b',
  'step': 'Add one line under ## How it has been approached for this phase: what it tried, not how it went.',
  'done_when': 'one approach line added'},
 {'id': 'I1c', 'step': 'Bank confirmed results under ## What worked with what confirmed them.', 'done_when': 'each worked entry names its evidence'},
 {'id': 'I1d',
  'step': "Add failures under ## What did not work as '<tried> -> <happened> -> <why not the answer>'.",
  'done_when': 'each entry has a why'},
 {'id': 'I3',
  'step': 'The phase produced no evidence: record that in one line under ## Notes.',
  'done_when': 'one Notes line',
  'when': 'no_evidence'},
 {'id': 'I2',
  'step': 'Reorganise the whole file, never discard: merge two entries about one thing into one holding both facts; attach later explanations in '
          'place; move entries a result contradicted, with the evidence; most recent last within a section; group long sections with sub-bullets.',
  'done_when': 'no entry dropped, no disorder'},
 {'id': 'R1',
  'step': 'Check no What-did-not-work entry still true was removed; an entry moves only when a test now passes or a result showed the reason wrong.',
  'done_when': 'every still-true failure present'},
 {'id': 'R2', 'step': 'A repeated finding becomes a count on the existing entry, not a new entry.', 'done_when': 'no entry appears twice'}]
RULES = [{'id': 'R1', 'rule': 'Never delete a failure that is still true; it moves only when something changed it, carrying that evidence.'},
 {'id': 'R2', 'rule': 'Nothing appears twice; a repeat is a count, not a new entry.'},
 {'id': 'I2', 'rule': 'Reorganise every time; never discard.'},
 {'id': 'I3', 'rule': 'Record evidence, never impressions.'},
 {'id': 'I4', 'rule': "One task; never carry another task's record into this one. What crosses tasks is a SKILL, written deliberately."},
 {'id': 'role', 'rule': 'The tracker does not attempt, fix or research: recording is the whole job.'}]
RECORD_FIELDS = ['task_id', 'problem', 'approached', 'worked', 'did_not_work', 'notes', 'other_task_ids']
CHECKS = [{'check': 'task_id', 'kind': 'nonempty', 'field': 'task_id', 'fix': 'the record is for one named task (I4)'},
 {'check': 'problem_restated', 'kind': 'nonempty', 'field': 'problem', 'fix': 'restate The problem from the evidence each pass (I1)'},
 {'check': 'approaches_listed',
  'kind': 'min_items',
  'field': 'approached',
  'n': 1,
  'fix': 'one line per attempt/pass under How it has been approached (I1)'},
 {'check': 'failures_have_why',
  'kind': 'each_regex',
  'field': 'did_not_work',
  'pattern': '->.*->',
  'when': {'field': 'did_not_work', 'filled': True},
  'fix': "each What-did-not-work entry is '<tried> -> <happened> -> <why it is not the answer>' (I1, I3)"},
 {'check': 'no_impressions',
  'kind': 'absent',
  'field': '*',
  'pattern': 'needs more work|seems (fine|ok)|probably works|nearly solved',
  'fix': 'replace impressions with the test result, error or diff behind them (I3)'},
 {'check': 'single_task',
  'kind': 'max_items',
  'field': 'other_task_ids',
  'n': 0,
  'fix': 'the record mentions another task: start a new record rather than merging (I4)'},
 {'check': 'no_duplicates',
  'kind': 'regex',
  'field': '*',
  'pattern': '^(?![\\s\\S]*\\"([^\\"]{12,})\\"[\\s\\S]*\\"\\1\\")',
  'fix': 'an entry appears twice: make the repeat a count on the existing entry (R2)'}]


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
    def phronix_task_tracker_plan(goal: str, facts: dict = None) -> dict:
        "Render the tracker-fold procedure as an ordered checklist: restate the problem, one line per approach, bank what worked with evidence, what did not work with why, reorganise without discarding, count repeats. Use it before applying the phronix-task-tracker procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: other_task_id (the given record mentions a different task id), no_evidence (the phase produced no evidence (ran and changed nothing, or died)); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_task_tracker_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_task_tracker_check(record: dict) -> dict:
        "Check a tracker.md record: the four sections plus Notes in order, one task id, every What-did-not-work entry carries what happened and why, entries trace to evidence, no duplicate entries,; compare against the previous version by hand for dropped failures (R1). Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields task_id, problem, approached, worked, did_not_work, notes, other_task_ids). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
