"""phronix_self_research: researching how a task should be done before doing it (framework process capability, converted from dftracer-agents skill phronix-self-research).

phronix_self_research_plan renders the procedure as an ordered checklist (predictor); phronix_self_research_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-self-research'
VALIDATOR = 'phronix_self_research_check'
FACTS = ["covered", "same_file_failures", "tool_subject"]
STEPS = [{'id': 'I1',
  'step': "research_assess(task='{goal}'): on covered load the named skills and proceed; on gap research before attempting. Do not substitute your "
          'own familiarity.',
  'done_when': 'covered/gap recorded'},
 {'id': 'I1b',
  'step': 'Covered: load the named skills and proceed; do not write a second parallel account.',
  'done_when': 'skills loaded',
  'when': 'covered'},
 {'id': 'I2',
  'step': 'research_define_fom(topic, name, direction, target, measure): prefer a number the task is already judged on (target tests passing, '
          'regressions as a constraint).',
  'done_when': 'FoM with measure recorded',
  'unless': 'covered'},
 {'id': 'I3',
  'step': 'Characterise the subject: a bug in a library (issue tracker, commits, changelog), using a tool (docs, --help), an algorithm/format (spec, '
          'reference implementation), an environment/build problem (release notes, version in play).',
  'done_when': 'kind written in the approach summaries',
  'unless': 'covered'},
 {'id': 'I4',
  'step': 'Look it up externally before reading the code: the issue as filed, whether fixed upstream, the fixing commit; WebSearch then WebFetch; '
          'research_add_approach(..., source=<url>).',
  'done_when': 'external sources recorded',
  'unless': 'covered'},
 {'id': 'I5',
  'step': 'For a tool: run --help of the command and subcommand, read the docs of the exact option (default, interactions), find a worked example; '
          'record the confirmed commands/options.',
  'done_when': 'tool surface recorded',
  'when': 'tool_subject'},
 {'id': 'I6',
  'step': 'Ground each external finding in this checkout at this version; record findings that do not match with what was looked for.',
  'done_when': 'each finding located or recorded as not matching',
  'unless': 'covered'},
 {'id': 'I7',
  'step': 'At least two genuinely different approaches with research_add_approach and whatever was measured (Grep/Read every code path, Bash runs).',
  'done_when': '>= 2 approaches',
  'unless': 'covered'},
 {'id': 'R5',
  'step': 'Record the exclusion: the cause is not in the file the attempts kept changing; look elsewhere.',
  'done_when': 'exclusion recorded',
  'when': 'same_file_failures'},
 {'id': 'I10',
  'step': 'research_add_instance with phases train (discovery), validate (tuning), test (unseen; written before tuning and never consulted).',
  'done_when': 'instances in all three phases',
  'unless': 'covered'},
 {'id': 'I11',
  'step': "research_record_trial for every trial, failures included, then research_evaluate_approach: only 'confirmed' (validate AND unseen test) "
          'licenses a skill.',
  'done_when': 'approach status set',
  'unless': 'covered'},
 {'id': 'I8',
  'step': 'research_write_plan(topic, steps) tagged deterministic|judgement; build deterministic steps with capability_new, judgement steps as skill '
          'blocks.',
  'done_when': 'plan tagged, tools built',
  'unless': 'covered'},
 {'id': 'I9',
  'step': 'research_verify(topic) before acting; after executing, research_record_achieved(topic, value) and research_verify again; report the '
          'predicted vs achieved gap.',
  'done_when': 'verified twice, achieved recorded',
  'unless': 'covered'}]
RULES = [{'id': 'R1', 'rule': 'Never compare approaches before the figure of merit exists (research_choose refuses).'},
 {'id': 'R2', 'rule': 'A figure of merit must state how it is measured.'},
 {'id': 'R3', 'rule': 'Record rejected approaches with their numbers.'},
 {'id': 'R4', 'rule': 'Deterministic steps become capabilities, never prose.'},
 {'id': 'R5', 'rule': 'Repeated failure in one location is evidence to look elsewhere: record the exclusion.'},
 {'id': 'R6', 'rule': "Every approach records its source; at least one from outside the local checkout (research_verify 'evidence')."},
 {'id': 'R7',
  'rule': "Measure the figure of merit; a prediction cannot decide (research_choose inconclusive; corrector fails 'constraints' on a predicted "
          'winner).'},
 {'id': 'R8', 'rule': 'Only the unseen test instances confirm or falsify; failing train/validate does not refute.'},
 {'id': 'R9', 'rule': 'Keep unconfirmed approaches as backups (research_backups); a retry starts there, never from nothing.'}]
RECORD_FIELDS = ['coverage', 'fom', 'kind', 'approaches', 'instances', 'chosen', 'plan_steps']
CHECKS = [{'check': 'coverage_assessed', 'kind': 'one_of', 'field': 'coverage', 'values': ['covered', 'gap'], 'fix': 'call research_assess first (I1)'},
 {'check': 'fom_measure',
  'kind': 'nonempty',
  'field': 'fom.measure',
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'research_define_fom with how the number is measured, before comparing (I2, R1, R2)'},
 {'check': 'kind_characterised',
  'kind': 'one_of',
  'field': 'kind',
  'values': ['library_bug', 'tool_usage', 'algorithm_or_format', 'environment_or_build'],
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'characterise the subject before searching (I3)'},
 {'check': 'two_approaches',
  'kind': 'min_items',
  'field': 'approaches',
  'n': 2,
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'record at least two genuinely different approaches (I7)'},
 {'check': 'approaches_sourced',
  'kind': 'each_has',
  'field': 'approaches',
  'keys': ['name', 'source'],
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'every approach records where it came from (R6)'},
 {'check': 'external_source',
  'kind': 'regex',
  'field': 'approaches',
  'pattern': '"source": "(https?://|issue|commit|doc|upstream)',
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'at least one approach must come from outside the checkout: issue, upstream commit, docs (I4, R6)'},
 {'check': 'rejected_have_numbers',
  'kind': 'each_if',
  'field': 'approaches',
  'if': {'key': 'status', 'equals': 'rejected'},
  'then': {'key': 'measured', 'test': 'number'},
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'record a rejected approach with its measured number (R3)'},
 {'check': 'unseen_test_set',
  'kind': 'regex',
  'field': 'instances',
  'pattern': '"phase": "test"',
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'write test instances before tuning, and never consult them while tuning (I10)'},
 {'check': 'chosen_confirmed',
  'kind': 'one_of',
  'field': 'chosen.status',
  'values': ['confirmed'],
  'when': {'field': 'chosen', 'filled': True},
  'fix': "only 'confirmed' (passing validate AND unseen test) licenses writing it up; keep others as backups (I11, R8, R9)"},
 {'check': 'chosen_measured',
  'kind': 'true',
  'field': 'chosen.measured',
  'when': {'field': 'chosen', 'filled': True},
  'fix': 'apply the candidate and pass the real measurement=; a predicted value cannot decide (R7)'},
 {'check': 'plan_tagged',
  'kind': 'each_if',
  'field': 'plan_steps',
  'then': {'key': 'type', 'test': 'one_of', 'values': ['deterministic', 'judgement']},
  'when': {'field': 'coverage', 'equals': 'gap'},
  'fix': 'tag every plan step deterministic or judgement and build the deterministic ones as capabilities (I8, R4)'}]


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
    def phronix_self_research_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-self-research procedure as an ordered checklist: coverage gate, figure of merit, characterise, external lookup, ground in code, rival approaches, instances by phase, tune/confirm, deterministic vs judgement plan, verify and record achieved. Use it before applying the phronix-self-research procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: covered (research_assess returned covered), tool_subject (the subject is a tool (learn its surface) rather than a defect), same_file_failures (several attempts changed the same file and the target still fails); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_self_research_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_self_research_check(record: dict) -> dict:
        "Check a research record: coverage was assessed, the figure of merit states how it is measured, at least two approaches each with a source (one external), rejected ones with numbers, test instances written before tuning, the chosen approach confirmed on the unseen test set with a measured (not predicted) value, plan steps tagged deterministic/judgement. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields coverage, fom, kind, approaches, instances, chosen, plan_steps). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
