"""phronix_research_as_tools: prefer calling an existing probe tool over re-deriving a fact by hand, and turn any procedure you repeat into a tool the next stage can call in one step (framework process capability, converted from dftracer-agents skill phronix-research-as-tools).

phronix_research_as_tools_plan renders the procedure as an ordered checklist (predictor); phronix_research_as_tools_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-research-as-tools'
VALIDATOR = 'phronix_research_as_tools_check'
FACTS = ["judgement", "probe_exists", "second_use"]
STEPS = [{'id': 'I1',
  'step': 'Before reproducing, checking or extracting a fact for {goal} by hand: knowledge_search, then capability_list for a probe_ tool that '
          'already does it (the store persists across tasks on this repository).',
  'done_when': 'existing probes listed'},
 {'id': 'I1b', 'step': 'Call the existing probe instead of the five-call hand derivation.', 'done_when': 'probe called', 'when': 'probe_exists'},
 {'id': 'I2',
  'step': 'Second time doing it: stop and capability_new a tool, only if it is a deterministic procedure (same inputs, same answer) AND will be '
          'asked again (next aspect, tune stage, retry, another task).',
  'done_when': 'tool proposed',
  'when': 'second_use',
  'unless': 'judgement'},
 {'id': 'I2b',
  'step': 'Judgement calls do not become tools: build a tool that MEASURES what an approach does, never one that decides whether it is right; keep '
          'the deciding in the skill.',
  'done_when': 'decision left in prose; any tool only measures',
  'when': 'judgement'},
 {'id': 'I3',
  'step': 'Name the tool for the question, not the mechanism (probe_ignore_paths_applied_recursively, not probe_run_pylint).',
  'done_when': 'name states the question',
  'when': 'second_use'},
 {'id': 'X1',
  'step': 'Do not tool a one-off: a procedure used once that nothing will ask again stays a shell command.',
  'done_when': 'no single-use probe added',
  'unless': 'second_use'}]
RULES = [{'id': 'R1',
  'rule': 'Tuning runs the same procedure tens of times; built as a tool early it becomes tens of fast calls, done by hand the stage hits its budget '
          'with most approaches unmeasured.'},
 {'id': 'R2',
  'rule': 'The tool outlives the task: a probe runs, a skill must be re-read and re-judged; a tool built on the last try of a failing task is still '
          'worth building.'},
 {'id': 'X1',
  'rule': 'Do not tool a one-off: every tool is listed to every future agent, and single-use probes cost every later task the time to read past '
          'them.'}]
RECORD_FIELDS = ['question', 'searched_existing', 'existing_probe', 'deterministic', 'uses_so_far', 'asked_again_by', 'decides_judgement', 'tool_name', 'built']
CHECKS = [{'check': 'question_stated', 'kind': 'nonempty', 'field': 'question', 'fix': 'state the question the step answers'},
 {'check': 'searched_first',
  'kind': 'true',
  'field': 'searched_existing',
  'fix': 'knowledge_search and capability_list for a probe before doing it by hand (I1)'},
 {'check': 'built_only_deterministic',
  'kind': 'true',
  'field': 'deterministic',
  'when': {'field': 'built', 'equals': True},
  'fix': 'only a deterministic procedure becomes a tool; leave judgement in the skill (I2)'},
 {'check': 'built_not_judgement',
  'kind': 'false',
  'field': 'decides_judgement',
  'when': {'field': 'built', 'equals': True},
  'fix': 'a tool measures what an approach does; it never decides whether it is right (I2)'},
 {'check': 'built_on_second_use',
  'kind': 'number',
  'field': 'uses_so_far',
  'min': 2,
  'when': {'field': 'built', 'equals': True},
  'fix': 'build the tool the second time, not the first: a one-off is a shell command (I2, X1)'},
 {'check': 'asked_again',
  'kind': 'nonempty',
  'field': 'asked_again_by',
  'when': {'field': 'built', 'equals': True},
  'fix': 'name who will ask again (next aspect, tune stage, retry, another task); otherwise do not tool it (X1)'},
 {'check': 'named_for_question',
  'kind': 'absent',
  'field': 'tool_name',
  'pattern': '^probe_(run|exec|call|invoke)_',
  'when': {'field': 'built', 'equals': True},
  'fix': 'name it for the question it answers, not the command it runs (I3)'},
 {'check': 'probe_prefix',
  'kind': 'regex',
  'field': 'tool_name',
  'pattern': '^probe_[a-z0-9_]+$',
  'when': {'field': 'built', 'equals': True},
  'fix': 'name probe tools probe_<question> (I3)'}]


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
    def phronix_research_as_tools_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-research-as-tools procedure for one research step as an ordered checklist: look for an existing probe, decide whether to build one (second time, deterministic, asked again), name it for the question. Use it before applying the phronix-research-as-tools procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: probe_exists (an existing probe_ tool already answers the question), second_use (this procedure has already been done once in this pass (or by another aspect)), judgement (the step is a judgement call (whether an approach is right)); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_research_as_tools_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_research_as_tools_check(record: dict) -> dict:
        "Check a probe-tool decision record: capability_list/knowledge_search was consulted first, a tool is built only for a deterministic procedure that will be asked again (second use), never for a judgement call or a one-off, and its name is the question it answers. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields question, searched_existing, existing_probe, deterministic, uses_so_far, asked_again_by, decides_judgement, tool_name, built). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
