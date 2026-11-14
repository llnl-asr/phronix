"""phronix_research_plan: plan a research pass (framework process capability, converted from dftracer-agents skill phronix-research-plan).

phronix_research_plan_plan renders the procedure as an ordered checklist (predictor); phronix_research_plan_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-research-plan'
VALIDATOR = 'phronix_research_plan_check'
FACTS = ["empty_diff", "retry", "scouts_active"]
STEPS = [{'id': 'I1',
  'step': 'Summarise the problem of {goal} from exchange.md before anything else: the change tried (diff), the target tests still failing, the '
          "pytest output, the agent's own account; record it with research_observe(what=..., stage='plan').",
  'done_when': 'summary recorded',
  'when': 'retry'},
 {'id': 'I1b',
  'step': "The diff is empty: nothing was edited; the plan's first job is to find out why the attempt could not act.",
  'done_when': "first aspect is 'why the attempt could not act'",
  'when': 'empty_diff'},
 {'id': 'I2a',
  'step': 'Fix the metric: research_define_fom(...) derived from THIS task, with measure stating exactly how it is obtained, before any approach '
          'exists.',
  'done_when': 'figure of merit recorded with measure'},
 {'id': 'I2b', 'step': 'research_declare_corpus(...) with the axes along which cases differ here.', 'done_when': 'axes declared'},
 {'id': 'I3',
  'step': 'research_add_instances(...) in the same breath: at least twenty, spread across the axes, with negative cases (the one that should NOT '
          'match), relative and absolute, nested and top-level.',
  'done_when': '>= 20 diverse instances incl. negatives'},
 {'id': 'I4', 'step': 'research_split(...) before you finish (20% held back as unseen).', 'done_when': 'split recorded'},
 {'id': 'I5',
  'step': 'research_prior(question=...) for what the store holds; list settled aspects for cheap re-check, but spend no NEW aspect on covered '
          'ground.',
  'done_when': 'prior consulted'},
 {'id': 'I5b',
  'step': "Decompose the problem into 3-6 STEPS (what has to become true, in order; the last usually 'do not break what works'); each step has a "
          "`where`. Ways of doing a step go on it via research_add_approach(..., aspect='<step>'), never as aspects.",
  'done_when': '3-6 steps named for what must become true'},
 {'id': 'I6',
  'step': 'Make every `where` different (file and function); if two ideas share one, move along an axis (layer, lifecycle, direction, polarity, '
          'scope, time) until they differ.',
  'done_when': 'all wheres distinct'},
 {'id': 'R2',
  'step': "Record ideas with research_add_aspects (append); research_set_aspects replaces the list and would erase the scouts' ideas.",
  'done_when': 'aspects appended',
  'when': 'scouts_active'},
 {'id': 'R3',
  'step': 'Record every distinct idea the failure supports: three is the floor, not the target.',
  'done_when': 'all distinct ideas recorded'}]
RULES = [{'id': 'R1',
  'rule': 'The metric comes first: downstream is arithmetic over trials; a stage stopped at its budget still files metric + corpus + what it has.'},
 {'id': 'R2', 'rule': 'Ideas are appended (research_add_aspects), not replaced; repeats are dropped and named back: a request for a different axis.'},
 {'id': 'R3', 'rule': 'Three ideas is the floor, not the target: every surviving idea is explored and tried; the fourth costs a slot, not a round.'},
 {'id': 'X1', 'rule': 'No approaches yet: naming a candidate in the plan commits the investigation to it.'},
 {'id': 'Stage', 'rule': 'Do not edit or fix anything in this stage: it decides how the question is answered, not the answer.'}]
RECORD_FIELDS = ['summary', 'fom', 'axes', 'instances', 'split', 'prior_consulted', 'aspects', 'aspects_mode']
CHECKS = [{'check': 'summary_recorded',
  'kind': 'min_len',
  'field': 'summary',
  'n': 40,
  'fix': "summarise exchange.md (diff, failing tests, pytest output, the agent's account) and research_observe it before planning (I1)"},
 {'check': 'fom_measured',
  'kind': 'nonempty',
  'field': 'fom.measure',
  'fix': 'research_define_fom with `measure` stating exactly how the number is obtained, before any approach (I2, R1)'},
 {'check': 'axes_declared', 'kind': 'min_items', 'field': 'axes', 'n': 2, 'fix': 'research_declare_corpus with the axes cases differ along (I2)'},
 {'check': 'twenty_instances',
  'kind': 'min_items',
  'field': 'instances',
  'n': 20,
  'fix': 'add at least 20 instances in the same breath as the axes; ten decides everything on two unseen cases (I3, I4)'},
 {'check': 'has_negatives',
  'kind': 'regex',
  'field': 'instances',
  'pattern': '"negative": true',
  'fix': 'add negative cases (should NOT match): a change that ignores everything passes every positive (I3)'},
 {'check': 'split_done', 'kind': 'true', 'field': 'split', 'fix': 'call research_split before you finish (I4)'},
 {'check': 'prior_consulted', 'kind': 'true', 'field': 'prior_consulted', 'fix': 'research_prior(question=...) before choosing aspects (I5)'},
 {'check': 'three_to_six_steps',
  'kind': 'min_items',
  'field': 'aspects',
  'n': 3,
  'fix': 'decompose into 3-6 steps; fewer means a step is really several (I5b, R3)'},
 {'check': 'not_more_than_six',
  'kind': 'max_items',
  'field': 'aspects',
  'n': 6,
  'fix': 'more than six steps means writing the patch, not the method (I5b)'},
 {'check': 'aspects_have_where',
  'kind': 'each_has',
  'field': 'aspects',
  'keys': ['name', 'where'],
  'fix': 'give every step a `where` (file, and function if known) (I5b, I6)'},
 {'check': 'steps_not_ways',
  'kind': 'absent',
  'field': 'aspects',
  'pattern': '"name": "(A\\d+\\s*:|Option \\d|Approach \\d)',
  'fix': 'aspects are steps named for what must become true; numbered candidates are ways: attach them with research_add_approach(..., '
         'aspect=<step>) (I5b)'},
 {'check': 'distinct_wheres',
  'kind': 'unique',
  'field': 'aspects',
  'key': 'where',
  'fix': 'two aspects with the same `where` are one idea: move one along an axis (layer, lifecycle, direction, polarity, scope, time) (I6)'},
 {'check': 'appended',
  'kind': 'one_of',
  'field': 'aspects_mode',
  'values': ['append'],
  'fix': "use research_add_aspects (append); research_set_aspects would erase the scouts' ideas (R2)"}]


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
    def phronix_research_plan_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-research-plan stage as an ordered checklist: summarise the attempt, define the figure of merit, declare and fill and split the corpus, consult prior knowledge, decompose into steps with distinct wheres, append (never replace) aspects. Use it before applying the phronix-research-plan procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: retry (this is a retry: exchange.md from the failed attempt is given), empty_diff (the failed attempt's diff is empty (nothing was edited)), scouts_active (scouts are adding ideas to the same plan); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_research_plan_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_research_plan_check(record: dict) -> dict:
        "Check a research plan record: problem summary recorded, metric with how it is measured, at least 20 instances including negatives and a split, 3-6 aspects named as steps (no 'A1:'/'Option N' names), each with a distinct `where`, and aspects appended rather than replaced. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields summary, fom, axes, instances, split, prior_consulted, aspects, aspects_mode). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
