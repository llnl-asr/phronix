"""phronix_context_economy: retrieving context without loading whole documents (framework process capability, converted from dftracer-agents skill phronix-context-economy).

phronix_context_economy_plan renders the procedure as an ordered checklist (predictor); phronix_context_economy_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-context-economy'
VALIDATOR = 'phronix_context_economy_check'
FACTS = ["code_task", "editing_shared", "sparse_results", "stale_graph"]
STEPS = [{'id': 'I1',
  'step': 'Open {goal} with both retrieval tools: context_skills(task=...) for how to do it AND context_memory(topic=...) for what went wrong before '
          '(or context_for_task for both; in the store: knowledge_search and lesson_search).',
  'done_when': 'both stores were searched'},
 {'id': 'I2',
  'step': 'Read the index_matches (catalogue rows) before the blocks; they often show the block you want is one you did not ask for.',
  'done_when': 'index matches were read'},
 {'id': 'I3',
  'step': 'Follow every [[other-skill#label]] reference in the blocks you got: the link is where the rest of the answer lives.',
  'done_when': 'cited references were read'},
 {'id': 'I4',
  'step': 'Locate code with the graph: graph_query(scope=project, question=...) -> file:line, mode=explain for callers/callees; open only the files '
          'it names.',
  'done_when': 'files were located by the graph before reading',
  'when': 'code_task'},
 {'id': 'R3',
  'step': 'Before editing a shared symbol, run graph_query(mode=affected, symbol=..., depth=2) and state the blast radius.',
  'done_when': 'the blast radius is stated',
  'when': 'editing_shared'},
 {'id': 'I5',
  'step': "Reformulate rather than widen: try the subject's vocabulary; ignore generic BFS nodes. After two failed reformulations reading the whole "
          'file is allowed (R5).',
  'done_when': 'a reformulated search found it, or two reformulations failed',
  'when': 'sparse_results'},
 {'id': 'R4',
  'step': 'A line number that does not match the file is a stale graph: graph_ensure(force=True), then query again; no manual search.',
  'done_when': 'graph rebuilt and re-queried',
  'when': 'stale_graph'}]
RULES = [{'id': 'R1',
  'rule': 'Never load a whole skill: retrieval tools return the exact labelled blocks; whole loads only for an exhaustive checklist walk.'},
 {'id': 'R2', 'rule': 'Locate before you read: ask the graph, then open only the file:line it names.'},
 {'id': 'R3', 'rule': 'Run affected before editing anything shared, and state the blast radius.'},
 {'id': 'R4', 'rule': 'Trust the graph over your recollection; a mismatched line number means graph_ensure(force=True).'},
 {'id': 'R5',
  'rule': 'Reading the whole file is sometimes right: small file, exhaustive walk, about to rewrite it, or nothing after two reformulations.'}]
RECORD_FIELDS = ['task',
 'skills_query',
 'memory_query',
 'index_matches_read',
 'files_read',
 'located_by_graph',
 'edits_shared',
 'blast_radius',
 'whole_skill_loaded',
 'whole_load_reason']
CHECKS = [{'check': 'task_named', 'kind': 'nonempty', 'field': 'task', 'fix': 'name the task the context was gathered for'},
 {'check': 'skills_searched',
  'kind': 'nonempty',
  'field': 'skills_query',
  'fix': 'search skills (context_skills / knowledge_search): how to do it (I1)'},
 {'check': 'memory_searched',
  'kind': 'nonempty',
  'field': 'memory_query',
  'fix': 'also search memory (context_memory / lesson_search): what went wrong before; one query finds only the stronger store (I1, P1)'},
 {'check': 'index_first', 'kind': 'true', 'field': 'index_matches_read', 'fix': 'read the index matches before the blocks (I2)'},
 {'check': 'located_first',
  'kind': 'true',
  'field': 'located_by_graph',
  'when': {'field': 'files_read', 'filled': True},
  'fix': 'locate with graph_query before reading files; open only the file:line it names (R2)'},
 {'check': 'blast_radius',
  'kind': 'nonempty',
  'field': 'blast_radius',
  'when': {'field': 'edits_shared', 'equals': True},
  'fix': 'run graph_query(mode=affected) and state the blast radius before editing (R3)'},
 {'check': 'whole_load_justified',
  'kind': 'one_of',
  'field': 'whole_load_reason',
  'values': ['exhaustive walk', 'small file', 'about to rewrite', 'nothing after two reformulations'],
  'when': {'field': 'whole_skill_loaded', 'equals': True},
  'fix': 'do not load a whole skill; retrieve the labelled blocks (R1); whole loads only for the R5 reasons'}]


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
    def phronix_context_economy_plan(goal: str, facts: dict = None) -> dict:
        "Render the context-economy procedure for a task as an ordered checklist: both retrieval tools, index matches first, follow references, graph for code, affected before shared edits, reformulate rather than widen. Use it before applying the phronix-context-economy procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: code_task (the task needs code located in a tree), editing_shared (the task edits a symbol others use), sparse_results (a search returned little or generic nodes), stale_graph (a returned line number did not match the file); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_context_economy_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_context_economy_check(record: dict) -> dict:
        "Check a context-gathering log: both stores (skills and memory) were searched, index matches were read, files were located through the graph before being read, the blast radius was stated before editing shared code, and no whole skill was loaded without a reason. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields task, skills_query, memory_query, index_matches_read, files_read, located_by_graph, edits_shared, blast_radius, whole_skill_loaded, whole_load_reason). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
