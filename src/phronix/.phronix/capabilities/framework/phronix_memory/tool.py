"""phronix_memory: the durable memory store of facts, decisions and guidance (framework process capability, converted from dftracer-agents skill phronix-memory).

phronix_memory_plan renders the procedure as an ordered checklist (predictor); phronix_memory_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-memory'
VALIDATOR = 'phronix_memory_check'
FACTS = ["is_procedure", "is_subject_pitfall", "project_specific"]
STEPS = [{'id': 'I1',
  'step': "Choose memory or a skill for {goal}: a skill answers 'how do I do X?' (procedures, constraints); a memory answers 'what is true here?' "
          '(decisions, constraints, state, guidance).',
  'done_when': 'the fact is classified as memory or skill'},
 {'id': 'I1b',
  'step': 'It is a procedure: write it to the skill/capability instead (capability_new or capability_update) and stop here.',
  'done_when': 'routed to a skill',
  'when': 'is_procedure'},
 {'id': 'X1',
  'step': "It is a pitfall or dated incident about one subject: lesson_add it to that capability's LESSONS.md instead of the memory store.",
  'done_when': 'routed to LESSONS.md',
  'when': 'is_subject_pitfall'},
 {'id': 'I2',
  'step': "Pick the type by what the fact is: project (current state, what 'done' means), feedback (Why: and How to apply:), reference (what the "
          'resource is for), lesson (the symptom as it actually appears).',
  'done_when': 'type chosen and its must-include part written',
  'unless': 'is_procedure'},
 {'id': 'I3',
  'step': 'Write a description that retrieves: a specific sentence with the words someone would search, not a label; convert relative dates to '
          'absolute.',
  'done_when': 'description is a specific sentence with absolute dates',
  'unless': 'is_procedure'},
 {'id': 'I4',
  'step': 'Link liberally with [[wikilinks]] to related memories/capabilities (retrieval walks one hop; a link to a not-yet-written memory marks one '
          'worth writing).',
  'done_when': 'at least one [[link]] present',
  'unless': 'is_procedure'},
 {'id': 'R4',
  'step': 'Check the write layer (phronix_status / where memory_write writes): project reaches everyone who clones the repo, user only you, bundled '
          'everyone who installs.',
  'done_when': 'layer matches who should inherit it',
  'unless': 'is_procedure'},
 {'id': 'R3',
  'step': 'Memory is committed and shared: run the privacy check (phronix_privacy) on the entry before writing; never write type: user.',
  'done_when': 'privacy scan clean',
  'unless': 'is_procedure'}]
RULES = [{'id': 'R1', 'rule': 'A feedback memory without a Why is incomplete: it is misapplied the first time the situation differs.'},
 {'id': 'R2', 'rule': 'Names are stable slugs; writing the same name updates: a memory holds the current truth, not versions of it.'},
 {'id': 'R3', 'rule': 'Memory is committed and shared: privacy rules apply (phronix-privacy R1); type: user is rejected outright.'},
 {'id': 'R4', 'rule': 'The write layer decides who inherits the memory (project / user / bundled); check the active target first.'},
 {'id': 'R5',
  'rule': 'Injection is tiered and deduplicated by design: standing rules once per session, each memory once per session, nothing when nothing new '
          'is relevant.'}]
RECORD_FIELDS = ['name', 'type', 'description', 'body', 'links', 'layer']
CHECKS = [{'check': 'slug_name',
  'kind': 'regex',
  'field': 'name',
  'pattern': '^[a-z0-9][a-z0-9_-]{1,80}$',
  'fix': 'use a stable lowercase slug name (R2); the same name updates the memory'},
 {'check': 'type_allowed',
  'kind': 'one_of',
  'field': 'type',
  'values': ['project', 'feedback', 'reference', 'lesson'],
  'fix': 'type is project, feedback, reference or lesson; type: user is rejected (R3, phronix-privacy R2)'},
 {'check': 'description_specific',
  'kind': 'min_len',
  'field': 'description',
  'n': 40,
  'fix': 'rewrite the description as a specific sentence with the words someone would search, not a label (I3, P1)'},
 {'check': 'no_relative_dates',
  'kind': 'absent',
  'field': 'description',
  'pattern': '\\b(yesterday|today|tomorrow|last (week|month|year)|next (week|month)|recently)\\b',
  'fix': 'convert relative dates to absolute YYYY-MM-DD (I3)'},
 {'check': 'body_present', 'kind': 'nonempty', 'field': 'body', 'fix': 'write the fact itself in body'},
 {'check': 'feedback_has_why',
  'kind': 'regex',
  'field': 'body',
  'pattern': 'why:',
  'when': {'field': 'type', 'equals': 'feedback'},
  'fix': "a feedback memory needs a 'Why:' line (R1)"},
 {'check': 'feedback_has_how',
  'kind': 'regex',
  'field': 'body',
  'pattern': 'how to apply:',
  'when': {'field': 'type', 'equals': 'feedback'},
  'fix': "a feedback memory needs a 'How to apply:' line (I2)"},
 {'check': 'lesson_has_symptom',
  'kind': 'regex',
  'field': 'body',
  'pattern': '(->|→|symptom)',
  'when': {'field': 'type', 'equals': 'lesson'},
  'fix': 'a lesson memory is symptom -> root cause -> exact fix, the symptom as it actually appears (I2)'},
 {'check': 'linked',
  'kind': 'regex',
  'field': '*',
  'pattern': '\\[\\[[^\\]]+\\]\\]',
  'fix': 'add at least one [[wikilink]] to a related memory or capability (I4, P3)'},
 {'check': 'layer_known',
  'kind': 'one_of',
  'field': 'layer',
  'values': ['project', 'user', 'bundled'],
  'fix': 'name the write layer: project (repo), user (you only) or bundled (R4, P2)'},
 {'check': 'no_identifying_detail',
  'kind': 'absent',
  'field': '*',
  'pattern': '(/usr/WS\\d|/g/g\\d+/|/home/[a-z]|/p/(?:lustre|vast|gpfs)\\d?/|[\\w.+-]+@[\\w-]+\\.[\\w.]+)',
  'fix': 'memory is committed and shared: replace user paths and emails with placeholders ($HOME, <user>) (R3)'}]


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
    def phronix_memory_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-memory procedure for recording one fact as an ordered checklist: memory or skill, the type, a description that retrieves, links, the write layer, the privacy check. Use it before applying the phronix-memory procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: is_procedure (the fact answers 'how do I do X' (it belongs in a skill/capability, not memory)), is_subject_pitfall (it is a pitfall or dated incident about one subject (goes to that subject's LESSONS.md)), project_specific (the fact is about this repository/project (project layer, not user)); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_memory_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_memory_check(record: dict) -> dict:
        "Check a memory entry before it is written: a stable slug name, an allowed type (never user), a specific description with no relative dates, Why/How to apply for feedback, the symptom for a lesson, at least one [[link]], and no identifying detail. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields name, type, description, body, links, layer). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
