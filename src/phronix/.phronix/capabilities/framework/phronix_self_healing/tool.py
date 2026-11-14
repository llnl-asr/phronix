"""phronix_self_healing: diagnosing and repairing the framework itself (framework process capability, converted from dftracer-agents skill phronix-self-healing).

phronix_self_healing_plan renders the procedure as an ordered checklist (predictor); phronix_self_healing_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-self-healing'
VALIDATOR = 'phronix_self_healing_check'
FACTS = ["needs_restart", "repeated_repair"]
STEPS = [{'id': 'I1',
  'step': "phronix_status() (or capability_list) for {goal}: which layers exist, which are writable, where learning is written; many 'broken tool' "
          'reports are writes to a layer nobody reads.',
  'done_when': 'status read'},
 {'id': 'I2',
  'step': 'Match the symptom to its cause with the table: skills_sync, agents_sync (edit the YAML template), permissions_sync, hooks_sync, '
          "graph_ensure(force=True), restart, or read the server's stderr.",
  'done_when': 'cause and repair named'},
 {'id': 'I3',
  'step': 'Verify the diagnosis before repairing: read the actual file, run the actual tool, list the actual directory.',
  'done_when': 'diagnosis confirmed on real state'},
 {'id': 'R2',
  'step': "Edit the source of truth, never the generated artifact (a file with 'generated-by: phronix'): agents/*.yaml, common-sections.yaml, "
          '<layer>/skills/<name>/, permissions.yaml.',
  'done_when': 'source edited, then synced'},
 {'id': 'I4',
  'step': 'Fix the class, not just the instance: a startup self-heal check, a capability that detects the bad state, a guard in the producing tool, '
          'or a privacy rule.',
  'done_when': 'class-level guard added or explicitly ruled out'},
 {'id': 'R3',
  'step': 'The fix needs a server restart: stop, name the exact tools needed, and wait; do not fill the gap by hand.',
  'done_when': 'restart need stated',
  'when': 'needs_restart'},
 {'id': 'X1',
  'step': 'The same repair was made before: it is deterministic; turn it into a tool (capability_new).',
  'done_when': 'tool proposed',
  'when': 'repeated_repair'},
 {'id': 'I5',
  'step': 'Prove the heal: verify_run(target=...) (or capability_verify); if nothing covers it, write a corrector encoding the breakage; then record '
          'symptom -> root cause -> exact fix (lesson_add / skill_write_lesson).',
  'done_when': 'verification passes and lesson recorded'}]
RULES = [{'id': 'R1',
  'rule': 'Fix the tool; never reproduce its job by hand: a manual workaround introduces drift and leaves the tool broken for the next session.'},
 {'id': 'R2', 'rule': "Edit the source, never the generated artifact; a 'generated-by: phronix' marker means you are in the wrong file."},
 {'id': 'R3', 'rule': 'When a fix needs a server restart, stop and say so; name the tools and wait, do not fill the gap by hand.'},
 {'id': 'R4', 'rule': 'A heal is a prediction: prove it (phronix-verification R1).'}]
RECORD_FIELDS = ['symptom', 'status_checked', 'cause', 'repair', 'verified_diagnosis', 'edited_files', 'manual_workaround', 'class_fix', 'proof', 'lesson']
CHECKS = [{'check': 'symptom_stated', 'kind': 'nonempty', 'field': 'symptom', 'fix': 'state the symptom as observed'},
 {'check': 'status_first',
  'kind': 'true',
  'field': 'status_checked',
  'fix': 'run phronix_status() first: the write may have gone to another layer (I1, P2)'},
 {'check': 'cause_named', 'kind': 'nonempty', 'field': 'cause', 'fix': 'match the symptom to its cause (I2 table)'},
 {'check': 'repair_named', 'kind': 'nonempty', 'field': 'repair', 'fix': 'name the repair (sync command, source edit, restart)'},
 {'check': 'diagnosis_verified',
  'kind': 'true',
  'field': 'verified_diagnosis',
  'fix': 'verify on the actual file/tool/directory before repairing (I3)'},
 {'check': 'no_generated_edit',
  'kind': 'absent',
  'field': 'edited_files',
  'pattern': '(\\.claude/agents/|\\.opencode/agents/|\\.github/agents/|\\.codex/agents/|\\.claude/skills/)',
  'fix': 'edit the source of truth (YAML template, layer skill dir) and re-sync; rendered files are build artifacts (R2, P1)'},
 {'check': 'no_workaround', 'kind': 'false', 'field': 'manual_workaround', 'fix': 'fix the tool, do not reproduce its job by hand (R1, P3)'},
 {'check': 'class_considered',
  'kind': 'nonempty',
  'field': 'class_fix',
  'fix': 'say what would catch this class automatically (self-heal check, detector capability, guard, privacy rule) (I4)'},
 {'check': 'heal_proven',
  'kind': 'nonempty',
  'field': 'proof',
  'fix': 'run verify_run / capability_verify on what you fixed; write a corrector if nothing covers it (I5, R4)'},
 {'check': 'lesson_recorded', 'kind': 'regex', 'field': 'lesson', 'pattern': '->|→', 'fix': 'record symptom -> root cause -> exact fix (I5)'}]


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
    def phronix_self_healing_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-self-healing procedure for one framework misbehaviour as an ordered checklist: status, match symptom to cause, verify, fix the class, prove the heal, record the lesson. Use it before applying the phronix-self-healing procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: needs_restart (the fix added or edited a capability that only a server restart can load), repeated_repair (the same repair has been made before); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_self_healing_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_self_healing_check(record: dict) -> dict:
        "Check a framework repair record: status was read, the symptom has a cause and a repair, the diagnosis was verified on the real file/tool, the fix is in the source (not a generated artifact) and not a manual workaround, a class-level guard was considered, the heal was proven and recorded as symptom -> cause -> fix. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields symptom, status_checked, cause, repair, verified_diagnosis, edited_files, manual_workaround, class_fix, proof, lesson). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
