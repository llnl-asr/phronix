"""Deterministic correctors — the anchor that keeps learning honest.

Every act of learning and every act of healing is a **predictor**. An agent
observes a session and predicts "this is the root cause", "this fix works", "this
tool behaves correctly", "this agent should now do X". Predictions are useful and
they are also, individually, unreliable — a model that is right most of the time
still writes a confidently wrong lesson often enough to poison a shared knowledge
base.

A **corrector** is the deterministic counterpart. It takes the artifact the
predictor produced and answers, by a fixed algorithm with no model in the loop,
whether it is well-formed and internally consistent. Same input, same verdict,
every time, on every machine.

This module is the *built-in* corrector layer: every skill, capability and agent
gets one automatically, with no authoring required, because the alternative is a
knowledge base whose verified fraction starts at zero and stays there. What these
check is **structural and referential correctness** — the class of error that is
both the most common and the most mechanically detectable:

===========  ==================================================================
skill        frontmatter parses; ``name`` matches the directory; the description
             is substantive; sections parse; ``[[wikilinks]]`` resolve; lessons
             are dated and non-empty; no identifying content
capability   the module compiles; defines ``register(mcp)``; registers at least
             one tool; every tool has a docstring with argument and return
             documentation; no identifying content
agent        the template validates; every ``include:`` resolves; the model level
             is well-formed; referenced skills exist; renders for all four
             harnesses without raising; no identifying content
===========  ==================================================================

What a built-in corrector deliberately does NOT check is whether a lesson's
*claim about the world* is true — "this flag fixes that error" cannot be settled
by any fixed algorithm over the text. That is what an authored verifier
(:mod:`phronix.verification`) is for. The two are complementary and are reported
separately, so "structurally sound" is never mistaken for "demonstrably true".
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

#: A finding: one thing that is wrong, with enough detail to fix it without
#: re-deriving the diagnosis.
def _finding(check: str, detail: str, severity: str = "fail") -> Dict[str, str]:
    return {"check": check, "detail": detail, "severity": severity}


def _verdict(findings: List[Dict[str, str]], checked: List[str]) -> Dict[str, Any]:
    """Roll findings into a status.

    ``warn`` findings do not fail the corrector. They are real but not
    disqualifying — a skill with a thin description is worse than one with a good
    description and better than no skill at all, and failing it would push authors
    toward not writing skills.
    """
    failures = [f for f in findings if f["severity"] == "fail"]
    return {
        "status": "fail" if failures else "pass",
        "checks_run": checked,
        "findings": findings,
        "evidence": (
            f"{len(checked)} deterministic checks; "
            f"{len(failures)} failed, {len(findings) - len(failures)} warnings"
        ),
    }


def _privacy_findings(text: str, label: str) -> List[Dict[str, str]]:
    from phronix.privacy import current_users, find_identifiers

    hits = sorted(set(find_identifiers(text, extra_users=current_users())))
    if not hits:
        return []
    return [_finding("privacy", f"{label} contains identifying content: "
                                f"{', '.join(hits[:5])}")]


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

_LESSON_RE = re.compile(r"^\s*[-*]\s+\*\*(\d{4}-\d{2}-\d{2})\*\*\s*(?:—|--|-)\s*(\S.*)$",
                        re.MULTILINE)

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _without_code(text: str) -> str:
    """Strip fenced blocks and inline code spans.

    Markdown inside code is an EXAMPLE, not a reference. Checks that scan prose
    for references — wikilinks, most obviously — produce a false positive on every
    documentation-shaped skill without this, and a check that cries wolf on
    correct content is a check people turn off.
    """
    return _INLINE_CODE_RE.sub(" ", _FENCE_RE.sub(" ", text))


def correct_skill(name: str) -> Dict[str, Any]:
    """Deterministically check a skill against the relational schema.

    This is where "clear, concise, constrained" stops being advice and becomes
    mechanical. The schema's guarantees — one subject per skill, unique stable
    labels, an index that matches the content, references that resolve to real
    blocks, lessons kept out of ``SKILL.md`` — are all checkable, and every one of
    them silently degrades retrieval when violated.
    """
    from phronix.layers import skill_dirs
    from phronix.skill_schema import (
        BLOCK_KINDS, LESSONS_FILE, SKILL_FILE, SKILL_TYPES,
        parse_references, parse_skill, render_index, split_sections,
    )

    checked: List[str] = []
    findings: List[Dict[str, str]] = []

    directory = skill_dirs().get(name)
    if directory is None:
        return {"status": "fail", "checks_run": ["exists"],
                "findings": [_finding("exists", f"no skill named {name!r} is visible")],
                "evidence": "skill not found"}

    checked.append("skill_file_present")
    if not (directory / SKILL_FILE).is_file():
        findings.append(_finding("skill_file_present", f"{directory} has no {SKILL_FILE}"))
        return _verdict(findings, checked)

    skill = parse_skill(directory)
    text = skill["skill_text"]

    # -- identity -----------------------------------------------------------
    # Reported separately from the individual field checks below. A file with no
    # frontmatter at all fails several of them at once, and one clear "there is no
    # frontmatter" beats three confusing consequences of that fact.
    checked.append("frontmatter_parses")
    from phronix.skill_schema import parse_frontmatter

    fields, _ = parse_frontmatter(text)
    if not fields:
        findings.append(_finding(
            "frontmatter_parses",
            "no YAML frontmatter; the skill has no name, description or subject, so "
            "index-first retrieval cannot reach it at all"))

    checked.append("name_matches_directory")
    if skill["name"] != directory.name:
        findings.append(_finding(
            "name_matches_directory",
            f"frontmatter name {skill['name']!r} != directory {directory.name!r}; the skill "
            "is then loadable by one name and invisible by the other"))

    checked.append("declares_one_subject")
    if skill.get("type") not in SKILL_TYPES:
        findings.append(_finding("declares_one_subject",
                                 f"type {skill.get('type')!r} must be one of "
                                 f"{'|'.join(SKILL_TYPES)}"))
    elif skill["type"] == "skill" and not skill.get("subject"):
        findings.append(_finding(
            "declares_one_subject",
            "no `subject:` in frontmatter. A skill covers ONE subject; naming it is what "
            "keeps two skills from half-covering the same ground", severity="warn"))
    elif skill["type"] == "association" and len(skill.get("subjects") or []) < 2:
        findings.append(_finding(
            "declares_one_subject",
            "an association skill must list the two subjects it joins in `subjects:` — "
            "that is its entire reason to exist"))

    checked.append("description_substantive")
    description = skill["description"].strip()
    if not description:
        findings.append(_finding("description_substantive", "no description"))
    elif len(description) < 30:
        findings.append(_finding(
            "description_substantive",
            f"description is {len(description)} chars; it is the main retrieval signal, so "
            "a short one makes the skill unfindable", severity="warn"))

    # -- schema shape -------------------------------------------------------
    sections = split_sections(text)
    checked.append("required_sections_present")
    lowered = {k.lower() for k in sections}
    if "index" not in lowered:
        findings.append(_finding("required_sections_present",
                                 "no `## Index`; index-first retrieval has nothing to match "
                                 "against and the skill is reachable only by luck"))
    if skill["type"] == "skill" and not any(
            s in lowered for s in ("instructions", "rules")):
        findings.append(_finding(
            "required_sections_present",
            "no `## Instructions` and no `## Rules` — a skill with neither says nothing "
            "about how to do anything"))

    checked.append("labels_unique_and_well_formed")
    seen: Dict[str, int] = {}
    for block in [*skill["blocks"], *skill["lesson_blocks"]]:
        if block["kind"] == "unknown":
            findings.append(_finding(
                "labels_unique_and_well_formed",
                f"label {block['label']!r} uses an unknown prefix; expected one of "
                f"{', '.join(sorted(s['prefix'] for s in BLOCK_KINDS.values()))}"))
        seen[block["label"]] = seen.get(block["label"], 0) + 1
    for label, count in seen.items():
        if count > 1:
            findings.append(_finding(
                "labels_unique_and_well_formed",
                f"label {label!r} is used {count} times; a duplicate key makes every "
                f"[[{name}#{label}]] reference ambiguous"))

    checked.append("blocks_in_their_own_section")
    for block in skill["blocks"]:
        expected = BLOCK_KINDS.get(block["kind"], {}).get("section")
        if expected and expected.lower() not in lowered:
            findings.append(_finding(
                "blocks_in_their_own_section",
                f"{block['label']} is a {block['kind']} but there is no `## {expected}` "
                "section for it to live under"))

    # -- the index is the catalogue; it must not drift ----------------------
    checked.append("index_matches_content")
    indexed = {row["label"] for row in skill["index"]}
    present = {b["label"] for b in skill["blocks"]}
    for label in sorted(present - indexed):
        findings.append(_finding(
            "index_matches_content",
            f"{label} exists but is not in the Index; index-first search will never "
            "reach it"))
    for label in sorted(indexed - present):
        findings.append(_finding(
            "index_matches_content",
            f"Index lists {label}, which no block defines; retrieval will route to "
            "content that is not there"))

    # -- foreign keys -------------------------------------------------------
    checked.append("references_resolve")
    known = skill_dirs()
    for reference in parse_references(_without_code(text)):
        target = known.get(reference["skill"])
        if target is None:
            findings.append(_finding(
                "references_resolve",
                f"{reference['raw']} names no visible skill", severity="warn"))
            continue
        if reference["label"]:
            other = parse_skill(target)
            if not any(b["label"] == reference["label"]
                       for b in [*other["blocks"], *other["lesson_blocks"]]):
                findings.append(_finding(
                    "references_resolve",
                    f"{reference['raw']} points at a label that does not exist in "
                    f"{reference['skill']}"))

    # -- separation of concerns --------------------------------------------
    checked.append("lessons_are_separate")
    for heading in sections:
        if heading.lower() in ("lessons", "pitfalls"):
            findings.append(_finding(
                "lessons_are_separate",
                f"`## {heading}` is in {SKILL_FILE}; pitfalls and lessons belong in "
                f"{LESSONS_FILE}, because skill search and memory search answer different "
                "questions and must not drag in each other's content"))

    checked.append("lessons_file_well_formed")
    if skill["has_lessons_file"]:
        stray = [b["label"] for b in skill["lesson_blocks"]
                 if b["kind"] not in ("lesson", "pitfall")]
        if stray:
            findings.append(_finding(
                "lessons_file_well_formed",
                f"{LESSONS_FILE} contains non-lesson blocks {stray}; instructions and rules "
                f"belong in {SKILL_FILE}"))

    # -- privacy ------------------------------------------------------------
    checked.append("privacy")
    findings.extend(_privacy_findings(text, SKILL_FILE))
    if skill["has_lessons_file"]:
        findings.extend(_privacy_findings(skill["lessons_text"], LESSONS_FILE))

    return _verdict(findings, checked)


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

_TOOL_DEF_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_.]*\.tool\(\)\s*def\s+(\w+)\s*\(")


def correct_capability(name: str) -> Dict[str, Any]:
    """Deterministically check that a capability compiles, registers and documents itself."""
    from phronix.capabilities import ENTRY_POINT
    from phronix.layers import capability_files

    checked: List[str] = []
    findings: List[Dict[str, str]] = []

    path = capability_files().get(f"{name}.py")
    if path is None:
        return {"status": "fail", "checks_run": ["exists"],
                "findings": [_finding("exists", f"no capability named {name!r} is visible")],
                "evidence": "capability not found"}

    source = path.read_text(encoding="utf-8", errors="replace")

    checked.append("compiles")
    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        findings.append(_finding("compiles", f"line {exc.lineno}: {exc.msg}"))
        return _verdict(findings, checked)

    checked.append("defines_register")
    if not re.search(rf"(?m)^def\s+{ENTRY_POINT}\s*\(", source):
        findings.append(_finding("defines_register",
                                 f"no module-level `def {ENTRY_POINT}(mcp):`"))

    # Registration is exercised against a recording stub rather than inspected
    # statically: a tool registered inside a loop or a helper is invisible to a
    # regex, and reporting it as missing would be a false failure.
    checked.append("registers_a_tool")
    recorded: List[Any] = []

    class _Recorder:
        def tool(self, *args, **kwargs):
            def decorate(fn):
                recorded.append(fn)
                return fn
            return decorate

    try:
        from phronix.verification import _load_module  # shared import machinery

        module = _load_module(path)
        register = getattr(module, ENTRY_POINT, None)
        if callable(register):
            register(_Recorder())
        if not recorded:
            findings.append(_finding("registers_a_tool",
                                     "register(mcp) ran but registered no tools"))
    except Exception as exc:
        findings.append(_finding("registers_a_tool",
                                 f"register(mcp) raised: {type(exc).__name__}: {exc}"))

    checked.append("tools_documented")
    for fn in recorded:
        doc = (fn.__doc__ or "").strip()
        if not doc:
            findings.append(_finding(
                "tools_documented",
                f"tool {fn.__name__!r} has no docstring; that is the ONLY description a "
                "model sees, so the tool will be either unused or misused"))
            continue
        if len(doc) < 40:
            findings.append(_finding(
                "tools_documented",
                f"tool {fn.__name__!r} has a {len(doc)}-char docstring; state what it does, "
                "when to use it, its arguments and its return shape", severity="warn"))
        has_args = bool(getattr(fn, "__code__", None) and fn.__code__.co_argcount)
        if has_args and "Args:" not in doc and "args:" not in doc.lower():
            findings.append(_finding(
                "tools_documented",
                f"tool {fn.__name__!r} takes arguments but documents none", severity="warn"))
        if "return" not in doc.lower():
            findings.append(_finding(
                "tools_documented",
                f"tool {fn.__name__!r} does not document its return shape; a caller that "
                "has to guess will guess wrong", severity="warn"))

    checked.append("privacy")
    findings.extend(_privacy_findings(source, str(path.name)))

    return _verdict(findings, checked)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def correct_agent(name: str) -> Dict[str, Any]:
    """Deterministically check that an agent template validates and renders everywhere."""
    from phronix.agent_templates import HARNESSES, RENDERERS, load_common_sections, load_template
    from phronix.layers import agent_templates, skill_dirs

    checked: List[str] = []
    findings: List[Dict[str, str]] = []

    path = agent_templates().get(f"{name}.yaml")
    if path is None:
        return {"status": "fail", "checks_run": ["exists"],
                "findings": [_finding("exists", f"no agent template named {name!r} is visible")],
                "evidence": "agent template not found"}

    checked.append("template_validates")
    try:
        template = load_template(path, load_common_sections())
    except Exception as exc:
        findings.append(_finding("template_validates", f"{type(exc).__name__}: {exc}"))
        return _verdict(findings, checked)

    checked.append("name_matches_filename")
    if template["name"] != path.stem:
        findings.append(_finding(
            "name_matches_filename",
            f"template name {template['name']!r} != filename {path.stem!r}; the rendered "
            "file lands under a name the router will not dispatch to"))

    checked.append("description_substantive")
    description = str(template.get("description", "")).strip()
    if len(description) < 40:
        findings.append(_finding(
            "description_substantive",
            "the description is the dispatch signal — state what the agent does AND when "
            "to reach for it", severity="warn"))

    checked.append("sections_non_empty")
    for i, section in enumerate(template["sections"]):
        if not section["body"].strip():
            findings.append(_finding("sections_non_empty", f"sections[{i}] has an empty body"))

    checked.append("skills_exist")
    known = set(skill_dirs())
    for skill in template.get("skills") or []:
        if skill not in known:
            findings.append(_finding(
                "skills_exist",
                f"declares skill {skill!r}, which is not visible; the agent will be told to "
                "load something that does not exist"))

    checked.append("renders_for_every_harness")
    try:
        from phronix.agent_templates import resolve_harness_models

        models = resolve_harness_models()
        for harness in HARNESSES:
            rendered = RENDERERS[harness](template, models[harness])
            if not rendered.strip():
                findings.append(_finding("renders_for_every_harness",
                                         f"{harness} rendered empty"))
    except Exception as exc:
        findings.append(_finding("renders_for_every_harness",
                                 f"{type(exc).__name__}: {exc}"))

    checked.append("privacy")
    findings.extend(_privacy_findings(path.read_text(errors="replace"), path.name))

    return _verdict(findings, checked)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

CORRECTORS = {
    "skill": correct_skill,
    "capability": correct_capability,
    "agent": correct_agent,
}


def correct(kind: str, target: str) -> Dict[str, Any]:
    """Run the built-in deterministic corrector for one artifact."""
    corrector = CORRECTORS.get(kind)
    if corrector is None:
        return {"status": "not_applicable", "checks_run": [], "findings": [],
                "evidence": f"no built-in corrector for kind {kind!r}"}
    try:
        return corrector(target)
    except Exception as exc:
        # A corrector that raises is a bug in the corrector, reported as `error`
        # rather than `fail` so it cannot be mistaken for a finding about the
        # artifact.
        import traceback

        return {"status": "error", "checks_run": [], "findings": [],
                "evidence": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=4)}


def correct_all(kind: str = "") -> List[Dict[str, Any]]:
    """Run built-in correctors across every artifact (optionally of one kind)."""
    from phronix.capabilities import listing as capability_listing
    from phronix.layers import agent_templates
    from phronix.skills import iter_skills

    targets: List[tuple] = []
    if kind in ("", "skill"):
        targets += [("skill", s["name"]) for s in iter_skills()]
    if kind in ("", "capability"):
        targets += [("capability", c["name"]) for c in capability_listing()]
    if kind in ("", "agent"):
        targets += [("agent", Path(f).stem) for f in agent_templates()]

    return [{"kind": k, "target": t, **correct(k, t)} for k, t in targets]
