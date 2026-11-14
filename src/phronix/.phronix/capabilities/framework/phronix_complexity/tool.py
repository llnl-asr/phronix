"""phronix_complexity: measuring task complexity and choosing the model level (framework process capability, converted from dftracer-agents skill phronix-complexity).

phronix_complexity_plan renders the procedure as an ordered checklist (predictor); phronix_complexity_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-complexity'
VALIDATOR = 'phronix_complexity_check'
FACTS = ["drift_down", "drift_up", "intrinsic_hard", "store_changed"]
STEPS = [{'id': 'I5',
  'step': 'Declare the intrinsic floor for {goal} (intrinsic: low|moderate|high|max in the template): measurement can raise a level above it, never '
          'lower it below.',
  'done_when': 'intrinsic is declared in the template',
  'when': 'intrinsic_hard'},
 {'id': 'I1',
  'step': 'Assess {goal} before dispatch: complexity_assess(agent=...) for a defined agent, complexity_assess(task=..., skills=[...], tools=[...]) '
          'for ad-hoc work. The result is computed from counts over the store, no model in the loop.',
  'done_when': 'a measured level with drivers is in hand'},
 {'id': 'I2',
  'step': "Read the drivers (each signal's contribution largest-first with its counts), not just the verdict; argue with the number you disagree "
          'with.',
  'done_when': 'the top drivers and their counts are written down'},
 {'id': 'I3',
  'step': 'The store changed: complexity_impact(skill=<what changed>) to see who is affected, then complexity_reassess() for every agent.',
  'done_when': 'every affected agent is reassessed',
  'when': 'store_changed'},
 {'id': 'I4.up',
  'step': 'Drift up: the subject accumulated rules and pitfalls. First ask whether that procedure should become a capability (P2); otherwise raise '
          'with agent_define(model_level=...).',
  'done_when': 'a capability was built or model_level raised',
  'when': 'drift_up'},
 {'id': 'I4.down',
  'step': 'Drift down: enough work became MCP capabilities that the agent mostly orchestrates. Lower it with agent_define(model_level=...) and claim '
          'the saving (R5).',
  'done_when': 'model_level lowered',
  'when': 'drift_down'}]
RULES = [{'id': 'R1', 'rule': 'Levels are measured, not guessed; the measurement is deterministic and explainable so it can be argued with.'},
 {'id': 'R2', 'rule': 'Thinking raises the level; tools lower it: tool_coverage is the only signal that lowers the requirement.'},
 {'id': 'R3', 'rule': 'Rules count double against instructions: recognising which constraint applies is judgment.'},
 {'id': 'R4', 'rule': 'Never pin a model id to buy a level: change model_level.'},
 {'id': 'R5', 'rule': 'A downward drift is a result worth claiming: leaving the agent at the old level wastes the work.'}]
RECORD_FIELDS = ['subject', 'measured_level', 'drivers', 'declared_level', 'intrinsic', 'drift', 'action', 'model_id']
CHECKS = [{'check': 'subject_named', 'kind': 'nonempty', 'field': 'subject', 'fix': 'name the agent or task that was assessed'},
 {'check': 'measured_level',
  'kind': 'one_of',
  'field': 'measured_level',
  'values': ['level_1', 'level_2', 'level_3', 'level_4'],
  'fix': 'run complexity_assess and record its level (level_1..level_4)'},
 {'check': 'drivers_read',
  'kind': 'each_has',
  'field': 'drivers',
  'keys': ['signal', 'contribution'],
  'fix': 'record the drivers (signal, contribution, counts) from complexity_assess, not just the verdict (I2)'},
 {'check': 'declared_level',
  'kind': 'one_of',
  'field': 'declared_level',
  'values': ['level_1', 'level_2', 'level_3', 'level_4'],
  'fix': "record the agent's declared model_level"},
 {'check': 'drift_named', 'kind': 'one_of', 'field': 'drift', 'values': ['up', 'down', 'none'], 'fix': 'drift is up, down or none'},
 {'check': 'drift_acted_on',
  'kind': 'nonempty',
  'field': 'action',
  'when': {'field': 'drift', 'in': ['up', 'down']},
  'fix': 'apply the drift: agent_define(model_level=...) (or build the capability on a drift up, P2); a downward drift is worth claiming (R5)'},
 {'check': 'no_model_id',
  'kind': 'absent',
  'field': '*',
  'pattern': '"model_id": "[^"]+"|claude-|gpt-|opus|sonnet|haiku',
  'fix': 'never pin a model id to buy a level; change model_level (R4)'}]


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
    def phronix_complexity_plan(goal: str, facts: dict = None) -> dict:
        "Render the complexity procedure for an agent or task as an ordered checklist: assess, read the drivers, set an intrinsic floor when function outweighs scope, reassess after store changes, apply a drift in the right direction. Use it before applying the phronix-complexity procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: store_changed (a lesson, rule or capability was just added to a subject this agent loads), intrinsic_hard (the agent is hard because of what it does (planner, synthesiser), not what it loads), drift_up (the measured level is above the declared one), drift_down (the measured level is below the declared one); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_complexity_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_complexity_check(record: dict) -> dict:
        "Check a level-assessment record: the subject assessed, the measured level and its drivers with counts, the declared level, the drift direction and the action taken (raise/lower via model_level, never a model id), and the intrinsic floor respected. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields subject, measured_level, drivers, declared_level, intrinsic, drift, action, model_id). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
