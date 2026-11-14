"""phronix_agent_authoring: authoring and evolving agent definitions (framework process capability, converted from dftracer-agents skill phronix-agent-authoring).

phronix_agent_authoring_plan renders the procedure as an ordered checklist (predictor); phronix_agent_authoring_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-agent-authoring'
VALIDATOR = 'phronix_agent_authoring_check'
FACTS = ["behaviour_change", "overrides_bundled", "shared_rule"]
STEPS = [{'id': 'I1',
  'step': 'Write the template for {goal}: name (= filename stem), description (what it does AND when to dispatch to it), model_level, effort, tools, '
          'skills, sections (include: shared blocks).',
  'done_when': 'the YAML template exists with every key'},
 {'id': 'I2',
  'step': 'Pick the capability level: level_1 deterministic orchestration and tool plumbing; level_2 routing, planning, limited reasoning; level_3 '
          'analysis, diagnosis, stage-to-stage decisions; level_4 deep synthesis and cross-cutting reasoning. Never a model id.',
  'done_when': 'model_level is set to a level'},
 {'id': 'I3',
  'step': 'Scope the tools: list only what the agent needs, with neutral (Claude) names (Read, Bash, mcp__phronix__skill_load); converters reshape '
          'them per harness.',
  'done_when': 'the tools list is minimal and uses neutral names'},
 {'id': 'R4',
  'step': 'Put the rule in common-sections.yaml once and include: it where needed, instead of editing every template.',
  'done_when': 'the shared section exists and is included',
  'when': 'shared_rule'},
 {'id': 'P2',
  'step': 'Prefer a project-specific shared section include:d into the bundled agent over a same-name project template (which replaces the bundled '
          'one and stops its future improvements).',
  'done_when': 'the choice to override (or not) is stated with its reason',
  'when': 'overrides_bundled'},
 {'id': 'R5',
  'step': 'Ask the user to confirm the behaviour change before applying it (appending a lesson is additive and safe; changing behaviour is not).',
  'done_when': "the user's confirmation is recorded",
  'when': 'behaviour_change'},
 {'id': 'P1',
  'step': 'Check every skill the template references exists (a missing one is silently absent guidance).',
  'done_when': 'every skills entry resolves'},
 {'id': 'I4',
  'step': 'Run agents_sync to re-render every harness copy, then ask the user to reload the harness. Never edit a rendered file.',
  'done_when': 'agents_sync ran and the user was asked to reload'}]
RULES = [{'id': 'R1',
  'rule': 'Never edit a rendered agent file (.claude/agents/*.md, .opencode/agents/*.md, .github/agents/*.agent.md, .codex/agents/*.toml): build '
          'artifacts, reverted by the next sync.'},
 {'id': 'R2',
  'rule': "The description is the dispatch signal: say what it does and when to use it ('Reviews changed code for reuse...; use after a feature "
          "lands, not for bug hunting')."},
 {'id': 'R3', 'rule': 'Never hard-code a model id in a template: use model_level.'},
 {'id': 'R4', 'rule': 'A rule for every agent goes in common-sections.yaml: add once, include: where needed, then agents_sync.'},
 {'id': 'R5', 'rule': "Changing agent behaviour needs the user's confirmation."},
 {'id': 'R6', 'rule': 'Codex renders no tools key, by design (no per-tool allow/deny; the boundary is sandbox_mode).'}]
RECORD_FIELDS = ['name',
 'file_stem',
 'description',
 'model_level',
 'tools',
 'skills',
 'missing_skills',
 'edited_rendered_files',
 'behaviour_change',
 'user_confirmed',
 'synced']
CHECKS = [{'check': 'name_matches_stem', 'kind': 'nonempty', 'field': 'name', 'fix': 'name the agent; it must match the filename stem (I1)'},
 {'check': 'description_dispatchable',
  'kind': 'regex',
  'field': 'description',
  'pattern': '\\b(use|when|after|before|for)\\b.{3,}',
  'fix': "say what it does AND when to dispatch to it; 'Reviews code' is unusable (R2)"},
 {'check': 'level_not_model',
  'kind': 'one_of',
  'field': 'model_level',
  'values': ['level_1', 'level_2', 'level_3', 'level_4'],
  'fix': 'use model_level level_1..level_4, never a model id (R3, I2)'},
 {'check': 'no_model_id',
  'kind': 'absent',
  'field': '*',
  'pattern': '\\"model\\": \\"|claude-[a-z0-9]|gpt-\\d|\\bopus\\b|\\bsonnet\\b|\\bhaiku\\b',
  'fix': 'remove the pinned model id; a model upgrade is a one-line edit in models.yaml (R3)'},
 {'check': 'tools_scoped',
  'kind': 'max_items',
  'field': 'tools',
  'n': 25,
  'fix': 'list only what the agent needs: every tool schema sits in context for the whole session (I3)'},
 {'check': 'tools_present', 'kind': 'min_items', 'field': 'tools', 'n': 1, 'fix': 'list the tools the agent needs, with neutral (Claude) names (I3)'},
 {'check': 'skills_exist',
  'kind': 'max_items',
  'field': 'missing_skills',
  'n': 0,
  'fix': 'create or fix the referenced skill; a missing skill is silently absent guidance (P1)'},
 {'check': 'no_rendered_edits',
  'kind': 'max_items',
  'field': 'edited_rendered_files',
  'n': 0,
  'fix': 'revert the edit to the rendered file and change the template, then agents_sync (R1)'},
 {'check': 'behaviour_change_confirmed',
  'kind': 'true',
  'field': 'user_confirmed',
  'when': {'field': 'behaviour_change', 'equals': True},
  'fix': 'ask the user to confirm the behaviour change before applying it (R5)'},
 {'check': 'synced',
  'kind': 'true',
  'field': 'synced',
  'fix': 'run agents_sync and ask the user to reload the harness; an unsynced change exists only in the template (I4)'}]


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
    def phronix_agent_authoring_plan(goal: str, facts: dict = None) -> dict:
        "Render the agent-authoring procedure for one agent template as an ordered checklist: write the template, pick the capability level, scope the tools, put shared rules in common-sections.yaml, confirm behaviour changes with the user, render with agents_sync and reload. Use it before applying the phronix-agent-authoring procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: behaviour_change (the change alters how an existing agent behaves (not just appends a lesson)), shared_rule (the rule applies to every agent), overrides_bundled (a project template of the same name as a bundled agent is being written); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_agent_authoring_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_agent_authoring_check(record: dict) -> dict:
        "Check a proposed agent template (as an object): name matches the file stem, a dispatchable description (what AND when), a capability level not a model id, a short scoped tool list with neutral names, skills that exist, no edits to rendered files, user confirmation for a behaviour change, agents_sync run. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields name, file_stem, description, model_level, tools, skills, missing_skills, edited_rendered_files, behaviour_change, user_confirmed, synced). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
