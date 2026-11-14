"""phronix_skill_authoring: authoring and growing skill files (framework process capability, converted from dftracer-agents skill phronix-skill-authoring).

phronix_skill_authoring_plan renders the procedure as an ordered checklist (predictor); phronix_skill_authoring_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-skill-authoring'
VALIDATOR = 'phronix_skill_authoring_check'
FACTS = ["existing_subject", "outgrown", "pair_of_subjects", "solves_problem"]
STEPS = [{'id': 'I1',
  'step': "Decide whether {goal} is a new subject: if an existing skill's subject covers it, add a block there; otherwise skill_create(name, "
          'description, subject). Never widen an existing skill to fit.',
  'done_when': 'the target skill (existing or new) is named'},
 {'id': 'I1b',
  'step': 'Add the block to the existing skill whose subject covers it (skip skill_create).',
  'done_when': 'the existing skill is named',
  'when': 'existing_subject'},
 {'id': 'I2',
  'step': 'Write the description as the retrieval signal: one or two sentences, what the subject is and when to load it, with the words someone '
          'would search (tool name, error phrase, task verb).',
  'done_when': 'description names the subject and the trigger words'},
 {'id': 'I3',
  'step': 'Add blocks one idea each with skill_write(kind=instruction|rule|reference); labels and the Index are allocated/regenerated for you, never '
          'hand-written.',
  'done_when': 'every block is one idea, written through skill_write'},
 {'id': 'I4',
  'step': 'Link instead of restating: cite [[other-skill#R2]] rather than copying content from another subject.',
  'done_when': 'no copied block from another subject'},
 {'id': 'I5',
  'step': "Create an association skill (skill_create(name='x-on-y', kind='association', subjects='x, y')) holding only references and rules true of "
          'the combination.',
  'done_when': 'association skill holds no instructions of its own',
  'when': 'pair_of_subjects'},
 {'id': 'I6',
  'step': 'Split the outgrown skill, in order of preference: extract a capability (deterministic core), split by subject and link, externalise '
          'reference material into sibling files loaded with skill_load(file=...).',
  'done_when': 'each resulting part covers one subject',
  'when': 'outgrown'},
 {'id': 'R0',
  'step': 'Write the steps that fix the problem into ## Instructions: file, function, line and what to change it to, in order; never leave '
          'Instructions empty or put the how in a reference.',
  'done_when': 'someone could fix it from the Instructions alone',
  'when': 'solves_problem'},
 {'id': 'R0c',
  'step': 'Name every way it can still go wrong: the wrong construct with the right words (exception type, operator), matching the surrounding '
          'style, the incomplete subset of sites, the expected collateral test.',
  'done_when': 'each step lists the plausible wrong reading and why it fails',
  'when': 'solves_problem'},
 {'id': 'R0b',
  'step': "Read the skill back: every bare label (I1, X15) must be a section of this skill; another skill's section is [[skill#X1]]; no "
          'research-record approach identifiers.',
  'done_when': 'every cited label resolves'}]
RULES = [{'id': 'R0', 'rule': 'A skill that solves a problem must say how to solve it: non-empty Instructions with file, function, line and the change.'},
 {'id': 'R0b',
  'rule': 'Every label you cite must resolve: bare X1 is this skill; another skill is [[skill#X1]]; never a research-record identifier.'},
 {'id': 'R0c',
  'rule': 'Be specific to THIS task and name every way it can go wrong (wrong construct, surrounding style, incomplete subset, expected '
          'collateral).'},
 {'id': 'R1', 'rule': 'One skill covers exactly one subject.'},
 {'id': 'R2', 'rule': 'Labels are stable keys and are never reused.'},
 {'id': 'R3', 'rule': 'The Index is generated, never hand-edited.'},
 {'id': 'R4', 'rule': 'Pitfalls and lessons never go in SKILL.md; they live in LESSONS.md.'},
 {'id': 'R5', 'rule': 'A block states the rule before the rationale.'},
 {'id': 'R6', 'rule': 'Never edit a skill file by hand: use skill_write / skill_write_lesson.'},
 {'id': 'R7', 'rule': 'A higher layer replaces a skill wholesale; writing to a shadowed skill forks the whole file first.'}]
RECORD_FIELDS = ['name',
 'subject',
 'description',
 'instructions',
 'labels_defined',
 'labels_cited',
 'solves_problem',
 'failure_modes',
 'contains_lessons',
 'index_hand_written']
CHECKS = [{'check': 'name_given', 'kind': 'nonempty', 'field': 'name', 'fix': 'name the skill'},
 {'check': 'one_subject',
  'kind': 'nonempty',
  'field': 'subject',
  'fix': 'state the one subject this skill covers (R1); if it needs two, split or make an association skill (I5)'},
 {'check': 'description_signal',
  'kind': 'min_len',
  'field': 'description',
  'n': 40,
  'fix': 'write the description as the retrieval signal: what and when, with tool names and error phrases (I2)'},
 {'check': 'instructions_present',
  'kind': 'min_items',
  'field': 'instructions',
  'n': 1,
  'fix': '## Instructions must hold the steps; Rules and References are supporting material (R0)'},
 {'check': 'instructions_concrete',
  'kind': 'each_regex',
  'field': 'instructions',
  'pattern': '[\\w/.-]+\\.\\w+|`[^`]+`|\\(\\)',
  'when': {'field': 'solves_problem', 'equals': True},
  'fix': "each instruction of a solution skill names the exact file, function or code (R0c): no 'validate the input'"},
 {'check': 'failure_modes_named',
  'kind': 'min_items',
  'field': 'failure_modes',
  'n': 1,
  'when': {'field': 'solves_problem', 'equals': True},
  'fix': 'name the plausible wrong readings (wrong construct, surrounding style, incomplete subset, expected collateral) (R0c)'},
 {'check': 'labels_resolve',
  'kind': 'nonempty',
  'field': 'labels_defined',
  'fix': 'list the labels this skill defines so cited labels can be resolved (R0b)'},
 {'check': 'no_lessons_in_skill',
  'kind': 'false',
  'field': 'contains_lessons',
  'fix': 'move pitfalls and dated lessons to LESSONS.md with skill_write_lesson (R4)'},
 {'check': 'index_generated',
  'kind': 'false',
  'field': 'index_hand_written',
  'fix': 'never hand-write the Index or labels: write blocks through skill_write (R3, R6)'}]


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
    def phronix_skill_authoring_plan(goal: str, facts: dict = None) -> dict:
        "Render the skill-authoring procedure for a new or restructured skill as an ordered checklist: subject decision, description, one-idea blocks, links, association skills, splitting, and the R0 read-back. Use it before applying the phronix-skill-authoring procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: existing_subject (an existing skill's subject already covers this), pair_of_subjects (two subjects interact in ways neither owns alone), outgrown (the skill has outgrown its subject (agents use one block; description no longer fits; blocks contradict)), solves_problem (the skill claims to solve a specific problem (a solution skill)); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_skill_authoring_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_skill_authoring_check(record: dict) -> dict:
        "Check a drafted skill record against the schema: one subject, a searchable description, non-empty executable Instructions, every cited bare label defined in the skill, no lessons/pitfalls inside SKILL.md, no hand-written Index, and (for a solution skill) the exact construct and the failure modes named. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields name, subject, description, instructions, labels_defined, labels_cited, solves_problem, failure_modes, contains_lessons, index_hand_written). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
