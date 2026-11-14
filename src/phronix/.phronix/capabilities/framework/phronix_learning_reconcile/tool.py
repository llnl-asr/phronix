"""phronix_learning_reconcile: reconciling learned skills into one true copy, and improving the learner (framework process capability, converted from dftracer-agents skill phronix-learning-reconcile).

phronix_learning_reconcile_plan renders the procedure as an ordered checklist (predictor); phronix_learning_reconcile_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-learning-reconcile'
VALIDATOR = 'phronix_learning_reconcile_check'
FACTS = ["case_grew", "falsified", "learner_pattern", "siblings"]
STEPS = [{'id': 'I1',
  'step': 'Work one subject ({goal}): graph_query it, graph_get_node on the returned ids, and read the whole set before changing any of it.',
  'done_when': 'the neighbourhood is read'},
 {'id': 'I1b',
  'step': "graph_query the subject's neighbours; where several name the same repository, file and defect, merge them into one topic skill named for "
          "the topic; fold siblings' blocks in by label; leave each old name as a pointer skill ('superseded, merged into [[topic]]'). Do not merge "
          "a raced task's solution-<subject>-<plan> candidates.",
  'done_when': 'one topic skill plus pointer skills',
  'when': 'siblings'},
 {'id': 'I1c',
  'step': 'Shape the topic skill: description in the words a later task uses (repository, file, defect), body opens with the answer, then one case '
          'per instance: situation, what worked with what, what settled it (the target test); failures in the same table with the check that killed '
          'them.',
  'done_when': 'topic skill has answer + case table'},
 {'id': 'I1c.split',
  'step': 'A case grew past a few lines: move it to its own skill and leave a one-line row linking [[name]].',
  'done_when': 'case moved and linked',
  'when': 'case_grew'},
 {'id': 'I2',
  'step': 'Merge duplicate blocks: keep the block whose label is already referenced, fold in what the other said better, update by label; keep BOTH '
          'specifics (R0c, R1); if a condition would be lost, leave both and link them.',
  'done_when': 'one copy of each fact'},
 {'id': 'I3', 'step': 'Where a block depends on another, link it by label instead of restating.', 'done_when': 'dependencies are references'},
 {'id': 'I4',
  'step': "Retire or rewrite a falsified lesson, naming the observations that falsified it. Ask what was shown: 'this code did not work' -> rewrite "
          'with that detail; retire the approach only when the evidence rules out the idea; unsure -> keep it and record the doubt.',
  'done_when': 'retirements name evidence and scope',
  'when': 'falsified'},
 {'id': 'I5',
  'step': "Read research_observe(topic='learning'); a pattern across cycles (not one awkward cycle) becomes a block on phronix-learning-capture or "
          'this skill.',
  'done_when': 'pattern written as a block',
  'when': 'learner_pattern'},
 {'id': 'R3',
  'step': "Report merges, references added and retirements; 'no duplicates, nothing falsified' is a correct report.",
  'done_when': 'report written'}]
RULES = [{'id': 'R0', 'rule': 'A skill that solves a problem must say how in its Instructions; every cited label must resolve (R0b).'},
 {'id': 'R0c', 'rule': 'Merging must not make a solution skill more general: keep both specifics, carry failures and scores forward.'},
 {'id': 'R1', 'rule': 'Merging is lossy; keep the sharper wording; if a condition would be lost they are not duplicates.'},
 {'id': 'R2', 'rule': 'Never rewrite what a stage is reading: one block at a time through the skill tools; a minute is a budget.'},
 {'id': 'R3', 'rule': 'A skill that is only reorganised was not reconciled.'},
 {'id': 'I4', 'rule': 'A failed attempt does not falsify the approach it was attempting.'}]
RECORD_FIELDS = ['subject', 'merged_subjects', 'merges', 'references', 'retirements', 'pointers', 'reorganised_only']
CHECKS = [{'check': 'subject_named', 'kind': 'nonempty', 'field': 'subject', 'fix': 'work one subject at a time and name it (I1)'},
 {'check': 'merges_keep_label',
  'kind': 'each_has',
  'field': 'merges',
  'keys': ['kept_label', 'folded_label'],
  'when': {'field': 'merges', 'filled': True},
  'fix': 'each merge names the kept (already referenced) label and the folded one (I2)'},
 {'check': 'merges_keep_specifics',
  'kind': 'absent',
  'field': 'merges',
  'pattern': '"result": "(validate names|[^"]{0,25})"',
  'fix': 'the merged block must still name the file, function and line of both specifics; summarising them destroys the skill (R0c, R1)'},
 {'check': 'retirements_have_evidence',
  'kind': 'each_has',
  'field': 'retirements',
  'keys': ['label', 'falsified_by', 'scope'],
  'when': {'field': 'retirements', 'filled': True},
  'fix': 'name the observations that falsified it and whether the idea or only the implementation was ruled out (I4)'},
 {'check': 'retire_idea_not_attempt',
  'kind': 'each_if',
  'field': 'retirements',
  'if': {'key': 'scope', 'in': ['attempt', 'implementation']},
  'then': {'key': 'action', 'test': 'absent', 'pattern': '^retire'},
  'fix': 'a failed attempt does not falsify the approach: rewrite the lesson with what the code did instead of retiring it (I4)'},
 {'check': 'pointers_for_merged_names',
  'kind': 'nonempty',
  'field': 'pointers',
  'when': {'field': 'merged_subjects', 'filled': True},
  'fix': 'leave each old subject name as a pointer skill to the topic (I1b)'},
 {'check': 'not_reorganise_only',
  'kind': 'false',
  'field': 'reorganised_only',
  'fix': 'report merges, references and retirements; a reorganisation alone changes nothing retrieved (R3)'}]


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
    def phronix_learning_reconcile_plan(goal: str, facts: dict = None) -> dict:
        "Render one reconcile cycle for a subject as an ordered checklist: graph neighbourhood, sibling-topic merge, topic-skill shape, duplicate merge by label, references, retirement on evidence, learner self-improvement, report. Use it before applying the phronix-learning-reconcile procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: siblings (neighbouring subjects name the same repository, file and defect), falsified (research_notice shows a lesson stopped working), learner_pattern (a way of learning repeatedly fails or works across cycles), case_grew (a case grew past a few lines); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_learning_reconcile_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_learning_reconcile_check(record: dict) -> dict:
        "Check a reconcile-cycle report: subject named, actions are merges/references/retirements (not reorganisation), each merge keeps the referenced label and both specifics, each retirement names the falsifying observations and says the idea (not only the attempt) was ruled out, and pointer skills left for merged names. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields subject, merged_subjects, merges, references, retirements, pointers, reorganised_only). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
