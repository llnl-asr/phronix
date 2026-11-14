"""phronix_capability_authoring: authoring MCP tools the framework builds for itself (framework process capability, converted from dftracer-agents skill phronix-capability-authoring).

phronix_capability_authoring_plan renders the procedure as an ordered checklist (predictor); phronix_capability_authoring_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-capability-authoring'
VALIDATOR = 'phronix_capability_authoring_check'
FACTS = ["judgement_needed", "running_server"]
STEPS = [{'id': 'I1',
  'step': 'Decide whether {goal} should be code at all: could the rule be written so two competent people produce byte-identical output? Then check '
          'capability_list() (knowledge_search first) for an overlapping tool.',
  'done_when': 'the byte-identical answer and the overlap search are recorded'},
 {'id': 'X1',
  'step': 'It needs judgement: write it as a skill instead (phronix-skill-authoring R1) and stop here.',
  'done_when': 'routed to a skill',
  'when': 'judgement_needed'},
 {'id': 'I2',
  'step': "Nail the interface: inputs, the returned keys, and what happens on each failure mode (never a bare 'failed').",
  'done_when': 'inputs, outputs and every failure mode are written',
  'unless': 'judgement_needed'},
 {'id': 'I3',
  'step': 'Write the docstring first, for a model: one line what it does; when to reach for it (the trigger); every argument (meaning, format, if '
          'omitted); the return shape with its keys.',
  'done_when': 'the docstring has all four parts',
  'unless': 'judgement_needed'},
 {'id': 'I4',
  'step': 'Implement the module contract: a module docstring, top-level register(mcp), tools decorated @mcp.tool(), paths taken as arguments, errors '
          'as {status: error, error: <specific>}.',
  'done_when': 'the module compiles and register(mcp) declares the tool',
  'unless': 'judgement_needed'},
 {'id': 'R6',
  'step': 'Choose the layer by who should inherit it: project (assumes this repo; the default), user (your environment), bundled (genuinely '
          'general).',
  'done_when': 'the layer and its reason are stated',
  'unless': 'judgement_needed'},
 {'id': 'I5',
  'step': 'Finish the wiring: permissions_sync; say a restart is needed explicitly; verify_new a corrector on a known input; skill_write the reason '
          'it exists.',
  'done_when': 'permissions synced, restart stated, verifier added, reason documented',
  'unless': 'judgement_needed'},
 {'id': 'P3',
  'step': 'Tell the caller the new tool is not callable until the server restarts (running servers hold closures captured at registration).',
  'done_when': 'the restart requirement is in the report',
  'when': 'running_server'}]
RULES = [{'id': 'R1',
  'rule': 'Deterministic work becomes code, not prose: prose is re-derived slightly differently on every read, and drift stops a system being '
          'reproducible.'},
 {'id': 'R2', 'rule': 'Never hard-code a judgement call in a tool: it is applied silently and confidently where it is wrong.'},
 {'id': 'R3',
  'rule': "Fail loudly and specifically ({status: error, error: 'path X does not exist'}); never return a partial result as success; never swallow "
          'an exception into an empty string.'},
 {'id': 'R4', 'rule': 'Take paths as arguments, never hard-code them: an absolute path from the authoring machine is a leak and a bug.'},
 {'id': 'R5',
  'rule': 'Do not wrap a single command with no added value; wrap when there is validation, error interpretation, or a multi-step sequence worth '
          'freezing.'},
 {'id': 'R6', 'rule': 'Choose the layer by who should inherit it (project / user / bundled); when in doubt, project.'}]
RECORD_FIELDS = ['name',
 'byte_identical',
 'overlapping_tools',
 'docstring',
 'error_examples',
 'hardcoded_paths',
 'judgement_calls',
 'single_command_wrapper',
 'layer',
 'layer_reason',
 'restart_stated',
 'verifier',
 'silent_defaults']
CHECKS = [{'check': 'should_be_code',
  'kind': 'true',
  'field': 'byte_identical',
  'fix': 'if two competent people would not produce byte-identical output, it is a skill, not a capability (I1, X1)'},
 {'check': 'no_overlap',
  'kind': 'max_items',
  'field': 'overlapping_tools',
  'n': 0,
  'fix': 'extend the existing tool instead of adding a second one that splits usage (I1)'},
 {'check': 'docstring_when',
  'kind': 'regex',
  'field': 'docstring',
  'pattern': '\\b(use|when|before|after)\\b',
  'fix': 'the docstring must say when to reach for the tool (I3 part 2)'},
 {'check': 'docstring_returns',
  'kind': 'regex',
  'field': 'docstring',
  'pattern': '\\breturns?\\b',
  'fix': 'name the returned keys in the docstring (I3 part 4)'},
 {'check': 'errors_specific',
  'kind': 'absent',
  'field': 'error_examples',
  'pattern': '\\"(failed|error|)\\"',
  'fix': "return {status: error, error: <what and where>}, never a bare 'failed' (R3)"},
 {'check': 'errors_given',
  'kind': 'min_items',
  'field': 'error_examples',
  'n': 1,
  'fix': 'design the error path for each failure mode before implementing (I2)'},
 {'check': 'no_hardcoded_paths', 'kind': 'max_items', 'field': 'hardcoded_paths', 'n': 0, 'fix': 'take paths as arguments (R4)'},
 {'check': 'no_judgement_calls',
  'kind': 'max_items',
  'field': 'judgement_calls',
  'n': 0,
  'fix': 'move the judgement into a skill; the tool takes it as an argument (R2)'},
 {'check': 'no_silent_defaults',
  'kind': 'max_items',
  'field': 'silent_defaults',
  'n': 0,
  'fix': 'make a version/path/mode that matters an explicit argument and echo it in the output (P2)'},
 {'check': 'adds_value',
  'kind': 'false',
  'field': 'single_command_wrapper',
  'fix': 'do not wrap a single command with no validation, interpretation or sequence (R5)'},
 {'check': 'layer_chosen',
  'kind': 'one_of',
  'field': 'layer',
  'values': ['project', 'user', 'bundled'],
  'fix': 'choose project, user or bundled by who should inherit it; when in doubt, project (R6)'},
 {'check': 'bundled_is_general',
  'kind': 'nonempty',
  'field': 'layer_reason',
  'when': {'field': 'layer', 'equals': 'bundled'},
  'fix': 'say why it assumes nothing project-specific; a one-repo tool in bundled fails for everyone else (P1)'},
 {'check': 'restart_stated',
  'kind': 'true',
  'field': 'restart_stated',
  'fix': 'say explicitly that a restart is needed before the tool is callable (I5, P3)'},
 {'check': 'verifier',
  'kind': 'nonempty',
  'field': 'verifier',
  'fix': 'add a verifier that exercises the tool on a known input (verify_new / checks.json) (I5, X2)'}]


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
    def phronix_capability_authoring_plan(goal: str, facts: dict = None) -> dict:
        "Render the capability-authoring procedure for one proposed tool as an ordered checklist: decide code vs skill, check for an existing tool, fix the interface and failure modes, write the docstring first, implement register(mcp), wire it (permissions, restart, verifier, reason). Use it before applying the phronix-capability-authoring procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: judgement_needed (the right answer depends on reading the situation), running_server (the target server holds tool closures and must restart for a new tool); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_capability_authoring_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_capability_authoring_check(record: dict) -> dict:
        "Check a proposed tool design (as an object): the byte-identical test passed, no overlapping tool exists, the docstring has what/when/args/returns, errors are specific, no hard-coded paths or judgement calls, not a bare single-command wrapper, a layer chosen with its reason, the restart and a verifier stated. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields name, byte_identical, overlapping_tools, docstring, error_examples, hardcoded_paths, judgement_calls, single_command_wrapper, layer, layer_reason, restart_stated, verifier, silent_defaults). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
