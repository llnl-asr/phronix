"""The skill file schema — skills as a clean relational database, stored as markdown.

A skill library that grows without a schema becomes a pile of overlapping essays.
Two skills half-cover the same subject, neither is authoritative, and an agent
retrieving one gets a partial answer with no way to know what it is missing. The
fix is the same one relational design applies to data: **one subject per table,
stable keys, and explicit foreign keys instead of duplication.**

The mapping, kept deliberately literal:

=================  ==========================================================
relational         phronix
=================  ==========================================================
table              one skill = one subject, and *only* one
primary key        a labelled block (``R1``, ``I2``) unique within its skill
foreign key        ``[[other-skill#R3]]`` — a reference to a specific block
join table         an **association skill**: nothing but the links between two
                   subjects, plus what is true only of the combination
schema catalogue   the ``## Index`` table, which every file carries
=================  ==========================================================

File layout
-----------

``SKILL.md`` — what to do. Retrieved by skill search.

    frontmatter    name, description, subject, type
    ## Index       label -> section -> what it covers (the catalogue)
    ## Instructions  ### I1 — ...   step by step, how to do it
    ## Rules         ### R1 — ...   constraints you must follow
    ## References    ### X1 — ...   links to specific blocks in other skills

``LESSONS.md`` — what went wrong before. Retrieved by **memory** search, not skill
search.

    ## Pitfalls      ### P1 — ...   traps and their exact avoidance
    ## Lessons       ### L1 — ...   dated symptom -> root cause -> exact fix

The split is the point. "How do I do this?" and "what went wrong last time?" are
different questions; keeping them in one file means every retrieval of either one
drags in the other, and the file grows until nobody can load a part of it.

Why labels rather than heading text
-----------------------------------
A reference to ``[[software-postgres#R3]]`` survives the heading being reworded.
A reference to a heading's prose does not, and a silently-broken cross-reference
is worse than none — it looks like the link was checked.

Labels also make retrieval addressable: ``skill_load(name=..., label="R3")``
returns exactly one constraint, which is what makes "never load a whole skill"
achievable rather than aspirational.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

#: The file that holds instructions and rules — what skill search returns.
SKILL_FILE = "SKILL.md"

#: The file that holds pitfalls and lessons — what memory search returns.
LESSONS_FILE = "LESSONS.md"

#: Block kinds, their label prefix, and the section each lives under.
#:
#: Prefixes are single letters on purpose: they are typed into cross-references by
#: hand, and every extra character is another way to write a broken link.
BLOCK_KINDS: Dict[str, Dict[str, str]] = {
    "instruction": {"prefix": "I", "section": "Instructions", "file": SKILL_FILE},
    "rule": {"prefix": "R", "section": "Rules", "file": SKILL_FILE},
    "reference": {"prefix": "X", "section": "References", "file": SKILL_FILE},
    "pitfall": {"prefix": "P", "section": "Pitfalls", "file": LESSONS_FILE},
    "lesson": {"prefix": "L", "section": "Lessons", "file": LESSONS_FILE},
}

_PREFIX_TO_KIND = {spec["prefix"]: kind for kind, spec in BLOCK_KINDS.items()}

#: Sections of SKILL.md, in required order. Order is fixed so a reader (human or
#: model) always finds the same thing in the same place.
SKILL_SECTIONS = ("Index", "Instructions", "Rules", "References")
LESSONS_SECTIONS = ("Pitfalls", "Lessons")

#: Skill types. An ``association`` skill exists only to join two subjects; it
#: carries References and Rules that are true of the COMBINATION, and no
#: Instructions of its own — those belong to the subjects it joins.
SKILL_TYPES = ("skill", "association")

#: ``### R1 — Title`` (em dash, en dash or hyphen; all three get typed).
BLOCK_RE = re.compile(r"(?m)^###\s+([A-Z])(\d+)\s*(?:—|–|-{1,2})\s*(.+?)\s*$")

#: ``[[skill-name#R3]]`` or ``[[skill-name]]``.
REFERENCE_RE = re.compile(r"\[\[([a-z0-9][a-z0-9-]*)(?:#([A-Z]\d+))?\]\]")

#: One row of the Index table: ``| `R1` | Rules | what it covers |``
INDEX_ROW_RE = re.compile(r"^\|\s*`?([A-Z]\d+)`?\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
_SECTION_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")


class SchemaError(ValueError):
    """A skill file violates the schema."""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Split frontmatter fields from the body. Supports YAML block scalars."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fields: Dict[str, str] = {}
    block = match.group(1)
    for key_match in re.finditer(r"(?m)^([a-zA-Z_][\w-]*):[ \t]*(.*)$", block):
        key, value = key_match.group(1), key_match.group(2).strip()
        if value in (">", "|", ">-", "|-", ""):
            folded = []
            for line in block[key_match.end():].split("\n"):
                if line.strip() and not line.startswith((" ", "\t")):
                    break
                folded.append(line.strip())
            value = " ".join(p for p in folded if p).strip()
        fields[key] = value.strip('"').strip("'")
    return fields, text[match.end():]


def split_sections(body: str) -> Dict[str, str]:
    """``{heading: text}`` for every ``## `` section, heading line included."""
    out: Dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(body))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[match.group(1).strip()] = body[match.start():end].rstrip() + "\n"
    return out


def parse_blocks(text: str, source: str = "") -> List[Dict[str, Any]]:
    """Extract every labelled ``### <Label> — Title`` block with its body.

    A block runs to the next block or the next ``## `` section, whichever comes
    first — so a block never silently swallows the section that follows it.
    """
    blocks: List[Dict[str, Any]] = []
    matches = list(BLOCK_RE.finditer(text))
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_break = _SECTION_RE.search(text, start, end)
        if section_break:
            end = section_break.start()
        prefix, number, title = match.group(1), match.group(2), match.group(3)
        blocks.append({
            "label": f"{prefix}{number}",
            "prefix": prefix,
            "number": int(number),
            "kind": _PREFIX_TO_KIND.get(prefix, "unknown"),
            "title": title.strip(),
            "body": text[start:end].strip(),
            "line": text[:match.start()].count("\n") + 1,
            "source": source,
        })
    return blocks


def parse_index(text: str) -> List[Dict[str, str]]:
    """Rows of the ``## Index`` table: ``{label, section, covers}``."""
    sections = split_sections(text)
    block = next((v for k, v in sections.items() if k.lower() == "index"), "")
    rows: List[Dict[str, str]] = []
    for line in block.split("\n"):
        match = INDEX_ROW_RE.match(line.strip())
        if not match:
            continue
        label, section, covers = match.groups()
        if label.upper() in ("LABEL",):  # the header row
            continue
        rows.append({"label": label, "section": section, "covers": covers})
    return rows


def parse_references(text: str) -> List[Dict[str, Optional[str]]]:
    """Every ``[[skill#LABEL]]`` foreign key in *text*."""
    seen = set()
    out: List[Dict[str, Optional[str]]] = []
    for match in REFERENCE_RE.finditer(text):
        skill, label = match.group(1), match.group(2)
        key = (skill, label)
        if key in seen:
            continue
        seen.add(key)
        out.append({"skill": skill, "label": label, "raw": match.group(0)})
    return out


def parse_skill(directory: Path) -> Dict[str, Any]:
    """Parse one skill directory into its schema representation.

    Both files are optional in the sense that a missing ``LESSONS.md`` is normal
    for a new skill — it is created on the first lesson. A missing ``SKILL.md`` is
    not, and is reported by the corrector rather than raised here, so one broken
    skill cannot take down a whole library listing.
    """
    directory = Path(directory)
    skill_path = directory / SKILL_FILE
    lessons_path = directory / LESSONS_FILE

    skill_text = (skill_path.read_text(encoding="utf-8", errors="replace")
                  if skill_path.is_file() else "")
    lessons_text = (lessons_path.read_text(encoding="utf-8", errors="replace")
                    if lessons_path.is_file() else "")

    fields, body = parse_frontmatter(skill_text)
    blocks = parse_blocks(body, source=SKILL_FILE)
    lesson_blocks = parse_blocks(lessons_text, source=LESSONS_FILE)

    return {
        "name": fields.get("name") or directory.name,
        "dir_name": directory.name,
        "dir": str(directory),
        "description": fields.get("description", ""),
        "subject": fields.get("subject", ""),
        "type": (fields.get("type") or "skill").strip(),
        "subjects": [s.strip() for s in (fields.get("subjects") or "").split(",") if s.strip()],
        "skill_path": str(skill_path),
        "lessons_path": str(lessons_path),
        "has_skill_file": skill_path.is_file(),
        "has_lessons_file": lessons_path.is_file(),
        "index": parse_index(body),
        "blocks": blocks,
        "lesson_blocks": lesson_blocks,
        "sections": list(split_sections(body).keys()),
        "references": parse_references(body),
        "skill_text": skill_text,
        "lessons_text": lessons_text,
    }


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def blocks_by_kind(skill: Dict[str, Any], kind: str) -> List[Dict[str, Any]]:
    pool = skill["lesson_blocks"] if BLOCK_KINDS.get(kind, {}).get("file") == LESSONS_FILE \
        else skill["blocks"]
    return [b for b in pool if b["kind"] == kind]


def find_block(skill: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
    """Resolve a label to its block, searching both files."""
    wanted = label.strip().upper()
    for block in [*skill["blocks"], *skill["lesson_blocks"]]:
        if block["label"] == wanted:
            return block
    return None


def next_label(skill: Dict[str, Any], kind: str) -> str:
    """The next free label for *kind*, e.g. ``R4``.

    Numbers are never reused, even after a block is deleted. A recycled label
    silently redirects every existing reference to different content — the one
    failure mode stable keys exist to prevent.
    """
    spec = BLOCK_KINDS[kind]
    prefix = spec["prefix"]
    used = [b["number"] for b in [*skill["blocks"], *skill["lesson_blocks"]]
            if b["prefix"] == prefix]
    return f"{prefix}{max(used) + 1 if used else 1}"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_index(blocks: List[Dict[str, Any]]) -> str:
    """Render the ``## Index`` table from the blocks actually present.

    Generated rather than hand-maintained: an index that drifts from its content
    is worse than none, because retrieval reads the index first and would route
    to a block that no longer says what the index claims.
    """
    lines = ["## Index", "",
             "| Label | Section | Covers |",
             "| --- | --- | --- |"]
    for block in sorted(blocks, key=lambda b: (b["prefix"], b["number"])):
        section = BLOCK_KINDS.get(block["kind"], {}).get("section", "?")
        covers = block["title"].replace("|", "\\|")
        lines.append(f"| `{block['label']}` | {section} | {covers} |")
    return "\n".join(lines) + "\n"


#: The order sections are emitted in. Fixed, so a reader always finds the same
#: thing in the same place and a re-render never reshuffles the file.
_SECTION_ORDER = ("instruction", "rule", "reference")


def render_skill(
    name: str,
    description: str,
    subject: str,
    blocks: List[Dict[str, Any]],
    kind: str = "skill",
    subjects: Optional[List[str]] = None,
) -> str:
    """Render a complete ``SKILL.md`` deterministically from a full block list.

    **Pure.** Given the same blocks, the output is byte-identical on any machine:
    frontmatter keys in a fixed order, the Index generated from the blocks,
    sections in a fixed order, blocks ordered by label, one trailing newline.

    All history-dependence lives in :func:`assign_labels`, which decides *which*
    label each block gets. Keeping the two apart is deliberate: the rendering step
    can then be reasoned about and tested without any notion of prior state.
    """
    lines = ["---", f"name: {name}", f"description: {description}"]
    if subject:
        lines.append(f"subject: {subject}")
    lines.append(f"type: {kind}")
    if kind == "association" and subjects:
        lines.append(f"subjects: {', '.join(subjects)}")
    lines += ["---", ""]

    head = "\n".join(lines) + "\n"
    parts = [head, render_index(blocks)]

    for block_kind in _SECTION_ORDER:
        chosen = sorted((b for b in blocks if b["kind"] == block_kind),
                        key=lambda b: b["number"])
        if not chosen and block_kind == "reference":
            continue  # References are optional; an empty heading is noise
        parts.append(f"\n## {BLOCK_KINDS[block_kind]['section']}\n")
        for block in chosen:
            parts.append(
                f"\n### {block['label']} — {block['title']}\n\n{block['body'].strip()}\n")

    return "".join(parts)


def render_lessons(name: str, subject: str, blocks: List[Dict[str, Any]]) -> str:
    """Render a complete ``LESSONS.md`` deterministically. Same guarantees."""
    parts = [LESSONS_TEMPLATE.format(name=name).replace(
        "Pitfalls and dated lessons.", f"Pitfalls and dated lessons for **{subject}**.")]
    for block_kind in ("pitfall", "lesson"):
        chosen = sorted((b for b in blocks if b["kind"] == block_kind),
                        key=lambda b: b["number"])
        parts.append(f"\n## {BLOCK_KINDS[block_kind]['section']}\n")
        for block in chosen:
            parts.append(
                f"\n### {block['label']} — {block['title']}\n\n{block['body'].strip()}\n")
    return "".join(parts)


def assign_labels(
    entries: List[Dict[str, str]],
    kind: str,
    existing: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Turn declared blocks into labelled ones, preserving stable keys.

    Label assignment, in priority order:

    1. An explicit ``label`` on the entry wins. Once a block is referenced from
       elsewhere, passing its label is how you guarantee the reference survives a
       re-render.
    2. Otherwise, if a block with the same title already exists, its label is
       reused — so editing a block's *body* never renumbers it.
    3. Otherwise a fresh number, above every number already used for that prefix.

    **This step is history-dependent, and that is the deliberate trade.** Two
    properties are in tension and cannot both hold:

    * *label stability* — a block keeps its label across edits, so incoming
      ``[[skill#R3]]`` references survive;
    * *history independence* — the same arguments yield the same labels whatever
      the file contained before.

    Assigning purely by position would give the second and destroy the first:
    inserting a block at the top would renumber everything below it and silently
    break every incoming reference. Since a dangling foreign key is invisible to
    whoever holds it, stability wins.

    The consequence is that a skill defined over an unrelated earlier skill may
    number its blocks differently than one defined into an empty directory.
    Pass explicit ``label`` values when you need history independence too — that is
    what the first rule is for.

    What IS guaranteed unconditionally: the operation converges. Running the same
    definition twice produces no change the second time.
    """
    prefix = BLOCK_KINDS[kind]["prefix"]
    by_title = {t.lower(): label for t, label in (existing or {}).items()}
    taken = {int(label[1:]) for label in by_title.values()
             if label[:1] == prefix and label[1:].isdigit()}
    taken |= {int(str(e["label"])[1:]) for e in entries
              if e.get("label") and str(e["label"])[:1] == prefix
              and str(e["label"])[1:].isdigit()}

    out: List[Dict[str, Any]] = []
    for entry in entries:
        label = entry.get("label") or by_title.get(str(entry.get("title", "")).lower())
        if not label:
            number = 1
            while number in taken:
                number += 1
            label = f"{prefix}{number}"
        taken.add(int(str(label)[1:]))
        out.append({
            "kind": kind, "prefix": prefix, "number": int(str(label)[1:]),
            "label": str(label), "title": str(entry.get("title", "")).strip(),
            "body": str(entry.get("body", "")).strip(),
        })
    return out


SKILL_TEMPLATE = """---
name: {name}
description: {description}
subject: {subject}
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |

## Instructions

## Rules

## References
"""

ASSOCIATION_TEMPLATE = """---
name: {name}
description: {description}
subject: {subject}
type: association
subjects: {subjects}
---

## Index

| Label | Section | Covers |
| --- | --- | --- |

## Rules

## References
"""

LESSONS_TEMPLATE = """# Lessons — {name}

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons
"""


def scaffold_skill(name: str, description: str, subject: str,
                   kind: str = "skill", subjects: Optional[List[str]] = None) -> str:
    template = ASSOCIATION_TEMPLATE if kind == "association" else SKILL_TEMPLATE
    return template.format(
        name=name, description=description, subject=subject or name,
        subjects=", ".join(subjects or []),
    )


def scaffold_lessons(name: str) -> str:
    return LESSONS_TEMPLATE.format(name=name)


def upsert_block(text: str, section: str, label: str, title: str, body: str) -> str:
    """Insert or replace a labelled block under *section*, creating it if absent."""
    header = f"### {label} — {title}"
    entry = f"{header}\n\n{body.strip()}\n"

    existing = next((b for b in parse_blocks(text) if b["label"] == label), None)
    if existing is not None:
        pattern = re.compile(
            rf"(?m)^###\s+{re.escape(label)}\s*(?:—|–|-{{1,2}})\s*.*?$"
            rf"(?:(?!^###\s|^##\s).)*", re.DOTALL)
        return pattern.sub(entry.rstrip("\n"), text, count=1)

    sections = split_sections(text)
    target = next((k for k in sections if k.lower() == section.lower()), None)
    if target is None:
        return text.rstrip("\n") + f"\n\n## {section}\n\n{entry}"
    block = sections[target]
    return text.replace(block, block.rstrip("\n") + f"\n\n{entry}", 1)


def refresh_index(text: str) -> str:
    """Regenerate the ``## Index`` table in *text* from its blocks."""
    fields, body = parse_frontmatter(text)
    rendered = render_index(parse_blocks(body))
    sections = split_sections(body)
    target = next((k for k in sections if k.lower() == "index"), None)
    if target is None:
        new_body = rendered + "\n" + body.lstrip("\n")
    else:
        new_body = body.replace(sections[target], rendered + "\n", 1)
    head = text[:len(text) - len(body)] if body else text
    return head + new_body
