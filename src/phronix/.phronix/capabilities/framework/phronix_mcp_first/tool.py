"""phronix_mcp_first: repairing MCP tools instead of working around them (framework process capability, converted from dftracer-agents skill mcp-first).

phronix_mcp_first_plan renders the procedure as an ordered checklist (predictor); phronix_mcp_first_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'mcp-first'
VALIDATOR = 'phronix_mcp_first_check'
FACTS = ["cannot_repair_in_budget", "new_or_renamed_tool", "workload_fact"]
STEPS = [{'id': 'I2.1',
  'step': "Read the error of the failed tool for {goal} as a defect report: name the gap in the tool (e.g. 'Unsupported build tool: unknown' is a "
          'gap in detection, not a fact about the app).',
  'done_when': 'the gap in the tool is written down in one sentence'},
 {'id': 'I2.2',
  'step': 'Fix the tool: find its module (dftracer-agents: src/dftracer_agents/mcp_tools/tools/; a capability: capability_get then '
          'capability_update), make it handle the case, and say in a comment why the case exists.',
  'done_when': "the tool's code handles the case, with a comment saying why",
  'unless': 'cannot_repair_in_budget'},
 {'id': 'I3.1',
  'step': 'Re-call the tool. The server reloads itself on a changed tool file (--reload); never ask anyone to restart a server. If the very next '
          'call fails the same way, wait a moment and try once more.',
  'done_when': 'the re-called tool returned success',
  'unless': 'cannot_repair_in_budget'},
 {'id': 'I3.2',
  'step': 'A NEW or RENAMED tool needs the client to reconnect (the tool list is sent at connection time); say so explicitly.',
  'done_when': 'the reconnect need is stated',
  'when': 'new_or_renamed_tool'},
 {'id': 'I2.4',
  'step': 'Record it so the fix survives: a lesson on this capability (lesson_add with the error text as evidence).',
  'done_when': 'lesson recorded',
  'unless': 'cannot_repair_in_budget'},
 {'id': 'I2.4b',
  'step': 'Also write a memory entry (memory_write) for the fact about the workload.',
  'done_when': 'memory written',
  'when': 'workload_fact'},
 {'id': 'I2.5',
  'step': 'Stop and report the tool defect (the tool, the error, why it could not be repaired). Stopping is acceptable; silently succeeding by hand '
          'is not.',
  'done_when': 'the defect is reported and the step is marked stopped',
  'when': 'cannot_repair_in_budget'}]
RULES = [{'id': 'I1',
  'rule': 'If an MCP tool exists for a job, it is the only way to do that job; Bash for it is forbidden even when faster, even when the tool just '
          'failed.'},
 {'id': 'I2', 'rule': 'A tool failure is a repair task, not a detour: read, fix, re-call, record.'},
 {'id': 'I3', 'rule': 'A repair is live immediately (--reload); there is never a reason to end a turn waiting for a human to restart something.'},
 {'id': 'I1b', 'rule': 'Use Bash freely for what no tool covers: inspecting the tree, reading logs, checking whether a fix worked.'}]
RECORD_FIELDS = ['tool', 'error', 'outcome', 'fix', 'recalled', 'lesson', 'workaround_used', 'defect_report']
CHECKS = [{'check': 'tool_named', 'kind': 'nonempty', 'field': 'tool', 'fix': 'name the MCP tool that failed'},
 {'check': 'error_quoted', 'kind': 'nonempty', 'field': 'error', 'fix': "quote the tool's error text: it is the defect report"},
 {'check': 'outcome_known',
  'kind': 'one_of',
  'field': 'outcome',
  'values': ['repaired', 'stopped'],
  'fix': "outcome is 'repaired' or 'stopped'; 'worked around' is not an outcome"},
 {'check': 'no_workaround', 'kind': 'false', 'field': 'workaround_used', 'fix': 'undo the Bash workaround; repair the tool and re-call it (I1)'},
 {'check': 'fix_described',
  'kind': 'nonempty',
  'field': 'fix',
  'when': {'field': 'outcome', 'equals': 'repaired'},
  'fix': 'say what changed in the tool and why the case exists (I2 step 2)'},
 {'check': 'recalled_after_fix',
  'kind': 'true',
  'field': 'recalled',
  'when': {'field': 'outcome', 'equals': 'repaired'},
  'fix': 're-call the tool after the fix; the run continues through the tool, not around it (I2 step 3, I3)'},
 {'check': 'lesson_recorded',
  'kind': 'nonempty',
  'field': 'lesson',
  'when': {'field': 'outcome', 'equals': 'repaired'},
  'fix': 'lesson_add the fix with the error text as evidence (I2 step 4)'},
 {'check': 'defect_reported',
  'kind': 'nonempty',
  'field': 'defect_report',
  'when': {'field': 'outcome', 'equals': 'stopped'},
  'fix': 'report the tool defect: tool, error, why it could not be repaired in budget'}]


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
    def phronix_mcp_first_plan(goal: str, facts: dict = None) -> dict:
        "Render the mcp-first repair procedure for a failed (or about-to-be-bypassed) MCP tool as an ordered checklist: read the error as a defect report, fix the tool, re-call it, record the fix, or stop and report. Use it before applying the mcp-first procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: cannot_repair_in_budget (the tool cannot be repaired within the step's budget), new_or_renamed_tool (the repair added or renamed a tool (needs a client reconnect)), workload_fact (what was learnt is a fact about the workload, not the tool); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_mcp_first_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_mcp_first_check(record: dict) -> dict:
        "Check a tool-failure repair record: the failing tool and its error are named, the tool (not a Bash workaround) was fixed, it was re-called, and the fix was recorded as a lesson, or the run stopped with the defect reported. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields tool, error, outcome, fix, recalled, lesson, workaround_used, defect_report). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
