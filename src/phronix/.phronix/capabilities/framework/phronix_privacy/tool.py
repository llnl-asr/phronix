"""phronix_privacy: redacting usernames, home paths, hostnames and job ids from shared knowledge (framework process capability, converted from dftracer-agents skill phronix-privacy).

phronix_privacy_plan renders the procedure as an ordered checklist (predictor); phronix_privacy_check rules on the record the
procedure produced (validator). Both are deterministic and never run anything."""
import json
import re

SKILL = 'phronix-privacy'
VALIDATOR = 'phronix_privacy_check'
FACTS = ["new_leak_class", "path_rule", "scan_dirty"]
STEPS = [{'id': 'I1.1', 'step': "privacy_scan() over what {goal} adds: anything but 'clean' blocks.", 'done_when': 'scan result recorded'},
 {'id': 'I1.2', 'step': 'privacy_redact() to apply the redaction.', 'done_when': 'redaction applied', 'when': 'scan_dirty'},
 {'id': 'I1.3',
  'step': 'privacy_scan() again to confirm: do not assume the redaction covered what it reported.',
  'done_when': 're-scan is clean',
  'when': 'scan_dirty'},
 {'id': 'I2',
  'step': 'privacy_suspects(): review each suspect honestly (most are version strings or hex hashes; some are real leaks a scan would never find), '
          'even when the scan was clean.',
  'done_when': 'every suspect is either a new rule or dismissed with a reason'},
 {'id': 'I3',
  'step': 'Teach the redactor, do not patch the file: privacy_add_pattern(regex, replacement, reason, structure_safe=True).',
  'done_when': 'pattern added',
  'when': 'new_leak_class'},
 {'id': 'I3b',
  'step': "The rule changes a path's component count: set structure_safe=False so it is skipped for .patch/.diff (would break patch -pN).",
  'done_when': 'structure_safe=False set',
  'when': 'path_rule'},
 {'id': 'I4',
  'step': 'Report what you dismissed, each with its reason, so the decision can be revisited.',
  'done_when': 'dismissed list with reasons in the report'}]
RULES = [{'id': 'R1',
  'rule': 'Keep the lesson, drop the provenance: strip usernames, real names, emails, handles; absolute user paths ($HOME, $PROJECT_ROOT, '
          '$SCRATCH_ROOT); job ids and session UUIDs (<job-id>, <uuid>); hostnames with node numbers (<cluster><node>); any secret.'},
 {'id': 'R2', 'rule': 'Never store a profile of a person: type: user memories are rejected; the whole document is the identity.'},
 {'id': 'R3',
  'rule': 'Do not over-redact: published citations, software names with digits, loopback and private-range addresses, uid=0 and existing '
          'placeholders are left alone.'},
 {'id': 'R4', 'rule': 'Verify deterministically, never by reading: privacy_scan() is the check.'},
 {'id': 'R5', 'rule': 'Promotion is publication: phronix contribute refuses on findings rather than quietly redacting.'},
 {'id': 'R6', 'rule': 'Write examples with placeholders (<user>, <host>, <job-id>), not plausible names: angle-bracket placeholders are exempt.'}]
RECORD_FIELDS = ['target', 'scan_before', 'redacted', 'scan_after', 'suspects_run', 'dismissed', 'patterns_added', 'patched_files_by_hand', 'text']
CHECKS = [{'check': 'target_named', 'kind': 'nonempty', 'field': 'target', 'fix': "name what was swept (the files or the run's additions)"},
 {'check': 'scan_before_known',
  'kind': 'one_of',
  'field': 'scan_before',
  'values': ['clean', 'findings'],
  'fix': 'record the first privacy_scan result: clean or findings (I1)'},
 {'check': 'redacted_on_findings',
  'kind': 'true',
  'field': 'redacted',
  'when': {'field': 'scan_before', 'equals': 'findings'},
  'fix': 'run privacy_redact() on findings (I1)'},
 {'check': 'rescanned_clean',
  'kind': 'one_of',
  'field': 'scan_after',
  'values': ['clean'],
  'when': {'field': 'scan_before', 'equals': 'findings'},
  'fix': 're-run privacy_scan() after redacting and repeat until clean; never assume the redaction covered it (I1, R4)'},
 {'check': 'suspects_run',
  'kind': 'true',
  'field': 'suspects_run',
  'fix': 'run privacy_suspects() even on a clean scan: a clean scan says nothing about unencoded leak classes (I2, P3)'},
 {'check': 'dismissals_reasoned',
  'kind': 'each_has',
  'field': 'dismissed',
  'keys': ['suspect', 'reason'],
  'when': {'field': 'dismissed', 'filled': True},
  'fix': 'give every dismissed suspect a reason (I4)'},
 {'check': 'class_not_file',
  'kind': 'false',
  'field': 'patched_files_by_hand',
  'fix': 'fix the rule, not the file: privacy_add_pattern for the class (I3, P2)'},
 {'check': 'no_user_paths',
  'kind': 'absent',
  'field': 'text',
  'pattern': '(/usr/WS\\d|/usr/work[s]pace/|/g/g\\d+/|/home/[a-z]|/p/(?:lustre|vast|gpfs)\\d?/[a-z]|/User[s]/[A-Za-z])',
  'fix': 'replace absolute user paths with $HOME / $PROJECT_ROOT / $SCRATCH_ROOT (R1)'},
 {'check': 'no_emails', 'kind': 'absent', 'field': 'text', 'pattern': '[\\w.+-]+@[\\w-]+\\.[a-z]{2,}', 'fix': 'remove email addresses (R1)'},
 {'check': 'no_uuids',
  'kind': 'absent',
  'field': 'text',
  'pattern': '\\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\b',
  'fix': 'replace session UUIDs with <uuid> (R1)'},
 {'check': 'no_job_ids',
  'kind': 'absent',
  'field': 'text',
  'pattern': '\\b(job[ _-]?id|jobid|flux job|slurm job)[:= ]+[A-Za-z0-9]{4,}',
  'fix': 'replace job ids with <job-id> (R1)'}]


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
    def phronix_privacy_plan(goal: str, facts: dict = None) -> dict:
        "Render the phronix-privacy sweep as an ordered checklist: scan, redact, re-scan, hunt suspects, teach the redactor a new leak class, report dismissed suspects. Use it before applying the phronix-privacy procedure so its steps are followed in order and none is skipped. Args: goal (required: what the procedure is applied to, concretely), facts (optional object; known keys: scan_dirty (the first privacy_scan reported findings), new_leak_class (privacy_suspects found a leak class the rules do not know), path_rule (the new rule changes a path's component count (structure_safe=False)); a fact switches its conditional steps on or off). Deterministic: renders, never runs anything. Returns {status, skill, goal, checklist: [{n, id, step, done_when}], skipped, rules, record_fields, validator, unknown_facts}, or {status: error, error} when goal is empty. Validate the finished record with phronix_privacy_check."
        return _plan(goal, facts)

    @mcp.tool()
    def phronix_privacy_check(record: dict) -> dict:
        "Check a privacy sweep record: the final scan is clean (after a redact, re-scanned), privacy_suspects was run, every dismissed suspect has a reason, every new leak class became a pattern (not a file patch), and the published text carries no user path, email or job id. Use it after the procedure, on the record it produced, before the step is called done. Arg: record (object; fields target, scan_before, redacted, scan_after, suspects_run, dismissed, patterns_added, patched_files_by_hand, text). Deterministic. Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}; inconclusive for an empty record. Each failed check names its fix; the skill's Corrector says how to repair and re-run."
        return _check(record)
