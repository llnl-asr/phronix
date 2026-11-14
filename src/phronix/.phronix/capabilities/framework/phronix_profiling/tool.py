"""phronix_profiling: measuring what a session costs, per step (framework process capability, converted from dftracer-agents skill phronix-profiling).

phronix_profiling_plan renders the procedure as an ordered checklist (predictor); phronix_profiling_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-profiling'
VALIDATOR = 'phronix_profiling_check'
FACTS = ["collector_down", "parallel_steps"]
STEPS = [{'id': 'I1',
  'step': 'Export the env before launching the harness: eval "$(phronix_stack env)" && claude. Exporting afterwards does not help; the harness reads '
          'OTEL_* at startup.',
  'done_when': "OTEL_* set in the harness's own environment"},
 {'id': 'I2',
  'step': 'profile_bind(run_id=..., tags={...}) for {goal} as early as the session gets an identity; rebinding the same id is a safe no-op, a '
          'different id starts fresh.',
  'done_when': 'run bound'},
 {'id': 'I3',
  'step': 'Bracket every step: profile_step_begin(step=..., agent=..., model_level=...) ... profile_step_end(step=..., status=...); reuse the step '
          'id EXACTLY on a retry.',
  'done_when': 'every step has begin/end with model_level'},
 {'id': 'R1', 'step': 'End each step with its real status: ok, failed, partial or skipped.', 'done_when': 'statuses honest'},
 {'id': 'I4',
  'step': 'profile_report(): read Unattributed (brackets wrong if large), Retries, and cross_check.events_dropped (telemetry lost, bill '
          'understated), not only the total.',
  'done_when': 'three figures read and reported'},
 {'id': 'R3',
  'step': 'Say that the per-step split between parallel steps is an estimate (totals stay exact).',
  'done_when': 'estimate stated',
  'when': 'parallel_steps'},
 {'id': 'R2',
  'step': "No collector: profile tools return 'disabled'; continue the work, never skip a step for profiling.",
  'done_when': 'work continued',
  'when': 'collector_down'}]
RULES = [{'id': 'R1', 'rule': 'Report the real status of a step: failed, partial or skipped honestly; the profile is evidence.'},
 {'id': 'R2', 'rule': 'Profiling never fails a session: tools degrade to disabled; a blocking profile call is a profiling bug.'},
 {'id': 'R3', 'rule': 'Per-step attribution is exact only for sequential work; with parallel steps the split is an estimate, say so.'},
 {'id': 'R4', 'rule': 'Never restart the collector mid-session: the profile lives in memory; restart discards the cost accounting so far.'}]
RECORD_FIELDS = ['run_id', 'env_exported_before_launch', 'steps', 'unattributed_fraction', 'events_dropped', 'parallel', 'parallel_noted', 'collector_restarted']
CHECKS = [{'check': 'env_before_launch',
  'kind': 'true',
  'field': 'env_exported_before_launch',
  'fix': 'export with eval "$(phronix_stack env)" BEFORE launching the harness, then relaunch (I1, P1)'},
 {'check': 'run_bound', 'kind': 'nonempty', 'field': 'run_id', 'fix': 'profile_bind(run_id=...) as early as the session has an identity (I2)'},
 {'check': 'steps_bracketed',
  'kind': 'each_has',
  'field': 'steps',
  'keys': ['step', 'model_level', 'status'],
  'fix': 'bracket every step with profile_step_begin/end and pass model_level (I3)'},
 {'check': 'status_honest',
  'kind': 'each_regex',
  'field': 'steps',
  'pattern': '"status": "(ok|failed|partial|skipped)"',
  'fix': 'status is ok, failed, partial or skipped (R1)'},
 {'check': 'stable_step_ids',
  'kind': 'absent',
  'field': 'steps',
  'pattern': '"step": "[^"]*(\\d{8}|\\d{2}:\\d{2}|attempt ?\\d|try ?\\d|retry ?\\d)',
  'fix': 'reuse the step id exactly on a retry; no timestamp or attempt number in it (I3, P2)'},
 {'check': 'unattributed_small',
  'kind': 'number',
  'field': 'unattributed_fraction',
  'min': 0,
  'max': 0.25,
  'fix': 'fix the brackets before reading the per-step table: most cost fell outside every step window (I4, P3)'},
 {'check': 'no_dropped_events',
  'kind': 'number',
  'field': 'events_dropped',
  'min': 0,
  'max': 0,
  'fix': 'telemetry was lost (cross_check.events_dropped): the bill is understated; say so and check the collector (I4)'},
 {'check': 'parallel_flagged',
  'kind': 'true',
  'field': 'parallel_noted',
  'when': {'field': 'parallel', 'equals': True},
  'fix': 'say the per-step split of parallel steps is an estimate (R3)'},
 {'check': 'collector_not_restarted',
  'kind': 'false',
  'field': 'collector_restarted',
  'fix': 'never restart the collector mid-session; the accounting so far is lost (R4)'}]


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
    def phronix_profiling_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-profiling procedure as an ordered checklist: env exported before the harness, bind once, bracket each step with model_level, report honest statuses, read the report's three figures. Use it before applying the phronix-profiling procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: parallel_steps (two or more steps ran genuinely in parallel), collector_down (no collector is running (profiling degrades to disabled)); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_profiling_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_profiling_check(record: dict) -> dict:
        "Check a session profile record: env exported before launch, a bound run id, every step bracketed with a model_level and an honest status, step ids without timestamps or attempt numbers, a small unattributed share, no dropped events, and parallel splits flagged as estimates. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields run_id, env_exported_before_launch, steps, unattributed_fraction, events_dropped, parallel, parallel_noted, collector_restarted). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
