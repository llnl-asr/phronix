"""The skill library: a relational store of subjects, read and grown through labels.

A skill is one **subject** and only one, described by labelled blocks with stable
keys (see :mod:`phronix.skill_schema`). Two files per skill:

``SKILL.md``    Index, Instructions (``I*``), Rules (``R*``), References (``X*``).
                This is what *skill* search returns: how to do the thing.
``LESSONS.md``  Pitfalls (``P*``) and Lessons (``L*``). This is what *memory*
                search returns: what went wrong before.

Three jobs live here because they share the schema:

**Retrieval.** :func:`search` is index-first — it matches the Index catalogue,
then expands the query with the terms of the rows that matched, then scores blocks
with the expanded query. Matching bodies directly finds whatever happens to share
vocabulary with the question; matching the index first finds the *subject*, and
only then looks inside it.

**Authoring.** :func:`write_block` adds an instruction or rule under a freshly
allocated label and regenerates the Index. :func:`write_lesson` routes to
``LESSONS.md`` instead, because a lesson is not an instruction and putting it in
``SKILL.md`` is how skill files turn into undifferentiated essays.

**Exposure.** :func:`install_skills` symlinks skills into the harness discovery
directories for the two harnesses that read them from disk.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from phronix.skill_schema import (
    BLOCK_KINDS,
    LESSONS_FILE,
    SKILL_FILE,
    blocks_by_kind,
    find_block,
    next_label,
    parse_blocks,
    parse_frontmatter,
    parse_references,
    parse_skill,
    refresh_index,
    scaffold_lessons,
    scaffold_skill,
    split_sections,
    upsert_block,
)

#: Where each harness discovers skill directories, relative to a workspace root.
#: Copilot and Codex have no skill-file convention; they reach the library through
#: the ``skill_*`` and ``context_*`` MCP tools.
HARNESS_SKILL_DIRS = {
    "claude": ".claude/skills",
    "opencode": ".opencode/skills",
}

_STOPWORDS = frozenset("""
and are but for from has have how not the that this was were what when where why
with you your can will its about into than then they there their use using does
did done should would could must need needs any all one two get got make made
""".split())


#: Longest body accepted per block kind, in characters.
#:
#: Instructions and rules are *directives* and are read on every retrieval that
#: matches them, so their length is a tax on every future session. Lessons get
#: more room because a symptom-and-root-cause naturally carries evidence, but not
#: unlimited room.
#:
#: These are not stylistic preferences; they are the enforcement half of "clear,
#: concise, constrained". A measured run wrote a 12 KB skill of six multi-page
#: instructions, one of which contained the correct fix as a buried sub-bullet.
#: Three subsequent attempts retrieved that skill and none acted on it: the
#: signal was there and the length destroyed it. A prompt asking for brevity did
#: not prevent that, because nothing checked.
def _tuned(key: str, fallback):
    """A tuning value, falling back to what the code shipped with.

    Read through a function rather than bound at import: the MCP server reloads
    tuning on its refresh sweep, and a module-level constant would hold the
    value the process started with.
    """
    try:
        from phronix.tuning import get

        return get(key, fallback)
    except Exception:
        return fallback


BLOCK_LIMITS = {
    "rule": _tuned("skills.block_limits.rule", 1000),
    "instruction": _tuned("skills.block_limits.instruction", 1400),
    "reference": _tuned("skills.block_limits.reference", 1400),
    "lesson": _tuned("skills.block_limits.lesson", 3000),
    "pitfall": _tuned("skills.block_limits.pitfall", 3000),
}


def _length_error(kind: str, title: str, body: str) -> Optional[Dict[str, Any]]:
    """Reject an over-long block, saying exactly how to make it acceptable.

    Rejecting rather than truncating: silently cutting a body would leave a
    half-sentence in the store presented as complete knowledge, which is worse
    than an error the writer can act on. The message names the limit and the
    remedy so the fix is mechanical.
    """
    limit = BLOCK_LIMITS.get(kind)
    if limit is None or len(body) <= limit:
        return None
    return {
        "status": "error",
        "error": (
            f"body is {len(body)} characters; the limit for kind={kind!r} is "
            f"{limit}. Split it into separate blocks, one idea each, and lead "
            "each with its directive. Long blocks are retrieved in full and are "
            "routinely skimmed past — a buried instruction is the same as a "
            "missing one. Keep the actionable statement; drop the investigation "
            "narrative."),
        "limit": limit,
        "length": len(body),
    }


def _is_learned(name: str) -> bool:
    """Whether a skill was learned here rather than shipped in the package.

    By layer, which is where the distinction actually lives: the bundled layer
    is the installed package and everything else was written by a run. Asking
    the layer beats any naming convention, because a learned skill about flask
    is named for flask and nothing in the name says who wrote it.
    """
    try:
        from phronix.layers import layers

        for layer in layers():
            homes = [Path(layer.root) / "skills" / name]
            homes += (Path(layer.root) / "capabilities" / "tasks").glob(f"*/{name}")
            for home in homes:
                if (home / "SKILL.md").is_file():
                    return layer.name != "bundled"
    except Exception:
        pass
    return False


def _log_retrieval(kind: str, query: str, names: List[str]) -> None:
    """Append a retrieval record when ``PHRONIX_RETRIEVAL_LOG`` names a file.

    Off unless explicitly enabled, and best-effort when on. It exists so that
    "which skills did this session actually use?" is a measured fact rather than
    something scraped out of a transcript — the benchmark's reuse-rate depends on
    it, and a scraped answer there would make the headline learning metric only
    as trustworthy as a regex over log output.

    **Searches that match nothing are logged too**, with an empty ``skills`` list.
    They cost nothing downstream — reuse is computed from skill names, so a record
    with none contributes none — and they answer a question an empty file cannot:
    whether the agent searched at all. Those two states looked identical during
    the first benchmark runs, and a store whose only skills are about the
    framework itself returns nothing for every domain query, so "no hits" is the
    *expected* early state rather than a sign the wiring is broken.
    """
    path = os.environ.get("PHRONIX_RETRIEVAL_LOG")
    if not path:
        return
    try:
        record = {"at": time.time(), "kind": kind, "query": query[:200],
                  "skills": names,
                  # Which phase asked. "Did the task use what was learned" is
                  # really two questions — research may load a skill and then
                  # hand the solve a plan that never mentions it — and a log
                  # without this cannot tell them apart. Set by the caller that
                  # launches the agent, so an unset value means "not run under
                  # the benchmark" rather than "unknown phase".
                  "phase": os.environ.get("PHRONIX_PHASE", ""),
                  "stage": os.environ.get("PHRONIX_STAGE", ""),
                  # Learned here, or shipped with the framework. Reuse of a
                  # bundled skill says the library works; reuse of a learned one
                  # says the LEARNING works, and only the second is what this
                  # benchmark exists to measure.
                  "learned": sorted(n for n in names if _is_learned(n))}
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except OSError:
        pass  # observability must never fail the retrieval it observes


def _terms(text: str) -> List[str]:
    seen, out = set(), []
    for token in re.split(r"[^\w]+", text.lower()):
        if len(token) > 2 and token not in _STOPWORDS and token not in seen:
            seen.add(token)
            out.append(token)
    return out


# ---------------------------------------------------------------------------
# The library
# ---------------------------------------------------------------------------

def iter_skills() -> List[Dict[str, Any]]:
    """Every visible skill, parsed to the schema and merged across layers."""
    from phronix.layers import skill_dirs, which_layer

    out: List[Dict[str, Any]] = []
    for _, directory in sorted(skill_dirs().items()):
        skill = parse_skill(directory)
        skill["layer"] = which_layer(directory)
        out.append(skill)
    return out


def get(name: str) -> Optional[Dict[str, Any]]:
    """One skill by frontmatter name or directory name."""
    wanted = name.strip().lower()
    for skill in iter_skills():
        if wanted in (str(skill["name"]).lower(), str(skill["dir_name"]).lower()):
            return skill
    return None


# ---------------------------------------------------------------------------
# Index-first search
# ---------------------------------------------------------------------------

#: Minimum share of a query's *discriminating power* a skill must account for.
#:
#: Weighted, not a plain term count, because plain counting fails in both
#: directions on real queries. "pylint recursive mode ignoring ignore-paths
#: configuration" matched framework skills on the single word "mode" and looked
#: like a hit; "redact usernames and home paths before writing" matched
#: phronix-privacy on 2 of 6 terms and looked like a miss. Counting cannot
#: separate those — one word that appears in every skill and one that appears in
#: exactly one are not worth the same, and rarity is precisely what says which
#: subject a question is about.
MIN_TERM_COVERAGE = _tuned("skills.min_term_coverage", 0.30)


def _term_weights(skills: List[Dict[str, Any]], terms: List[str]) -> Dict[str, float]:
    """How much each query term discriminates, by inverse document frequency.

    A term in most skills' catalogues ("mode", "paths", "file") says almost
    nothing about which subject is wanted; a term in one or none ("redact",
    "pylint") says almost everything. Weighting by ``log(N / (1 + df))`` makes a
    match on a rare term worth many matches on common ones, which is what the
    coverage floor then thresholds on.

    A term matching *nothing* keeps its full weight deliberately: an unmatched
    rare term is strong evidence the library does not cover this question, and it
    should drag coverage down rather than be quietly ignored.
    """
    import math

    total = max(len(skills), 1)
    weights: Dict[str, float] = {}
    for term in terms:
        frequency = sum(
            1 for skill in skills
            if term in f"{skill['name']} {skill.get('subject', '')}".lower().replace("-", " ")
            or term in str(skill["description"]).lower()
            or any(term in row["covers"].lower() for row in skill["index"]))
        # +1 floor so a term present in every skill still carries a little weight
        # rather than zero, which would let an all-common-terms query match freely.
        weights[term] = math.log(total / (1 + frequency)) + 0.1
    return weights


def _score_index(skill: Dict[str, Any], terms: List[str],
                 weights: Optional[Dict[str, float]] = None) -> Tuple[float, List[Dict[str, str]]]:
    """Score a skill by its catalogue: subject, description, and Index rows.

    Deliberately does NOT look at block bodies. Phase one answers "which subject
    is this question about?", and body text is exactly the noise that makes that
    question hard — a passing mention of a term in one paragraph should not make a
    whole subject look relevant.
    """
    subject = f"{skill['name']} {skill.get('subject', '')}".lower().replace("-", " ")
    description = str(skill["description"]).lower()

    total = 0.0
    matched = set()
    for term in terms:
        if term in subject:
            total += 8.0
            matched.add(term)
        if term in description:
            total += 4.0
            matched.add(term)

    rows: List[Dict[str, str]] = []
    for row in skill["index"]:
        # Only `covers` is scored. The `section` column holds one of three fixed
        # values — Instructions, Rules, References — so it carries no information
        # about the subject and actively creates false matches: any query
        # containing the word "reference" or "rule" otherwise matched every skill
        # in the library at once.
        haystack = row["covers"].lower()
        hits = [t for t in terms if t in haystack]
        if hits:
            total += 3.0 * len(hits)
            matched.update(hits)
            rows.append(row)

    if not matched:
        return 0.0, []

    # A single incidental word must not admit a whole subject.
    #
    # Scoring only had to beat zero, so one generic term carried an entire skill
    # into the results. Measured on a real benchmark task: the query "pylint
    # recursive mode ignoring ignore-paths configuration" returned five framework
    # skills — about model levels, capability authoring and profiling — on the
    # strength of the word "mode" alone. Not one domain term matched anything,
    # which was the correct answer: nothing in the store was about pylint.
    #
    # Returning noise there is worse than returning nothing, in a specific way.
    # An empty result tells an agent it is the first to meet this problem, which
    # is true and useful and costs a few hundred tokens. Five irrelevant skills
    # tell it the system has knowledge, spend thousands of tokens of context
    # proving otherwise, and teach it that searching is not worth doing.
    if weights:
        available = sum(weights.get(t, 1.0) for t in terms) or 1.0
        coverage = sum(weights.get(t, 1.0) for t in matched) / available
    else:
        coverage = len(matched) / len(terms)
    if len(terms) >= 3 and coverage < MIN_TERM_COVERAGE:
        return 0.0, []
    return total * (0.5 + 0.5 * coverage), rows


def _score_block(block: Dict[str, Any], terms: List[str]) -> float:
    """Score one labelled block. Title carries more weight than body."""
    title = block["title"].lower()
    body = block["body"].lower()
    total = 0.0
    matched = 0
    for term in terms:
        hit = False
        if term in title:
            total += 5.0
            hit = True
        count = body.count(term)
        if count:
            total += 1.0 + min(count, 4) * 0.25
            hit = True
        if hit:
            matched += 1
    if not matched:
        return 0.0
    return total * (0.5 + 0.5 * (matched / len(terms)))


def _has_blocks(ranked: List[Tuple[float, Dict[str, Any], List[Dict[str, str]]]],
                terms: List[str], wanted_kinds: List[str]) -> bool:
    """Whether any ranked subject actually contains a block matching *terms*."""
    for _, skill, _ in ranked:
        pool = [*skill["blocks"], *skill["lesson_blocks"]]
        if any(_score_block(b, terms) > 0 for b in pool if b["kind"] in wanted_kinds):
            return True
    return False


def search(query: str, max_results: int = 5, max_blocks: int = 4,
           kinds: Optional[List[str]] = None) -> Dict[str, Any]:
    """Index-first search: find the subject, then the blocks within it.

    Two phases, and the order is the design:

    1. **Index.** Score each skill's subject, description and Index rows. This
       identifies which *subject* the question is about, without block bodies
       voting — a term appearing once in some paragraph must not make an unrelated
       subject look relevant.
    2. **Expand and match.** Fold the matched Index rows' ``covers`` text into the
       query, then score the blocks of the surviving skills with the expanded
       terms. The index rows describe the subject in the skill's own vocabulary,
       which is usually not the asker's — that expansion is what bridges the two.

    Returns the Index rows AND the matching blocks, never whole files.
    """
    base_terms = _terms(query)
    if not base_terms:
        return {"status": "error",
                "error": f"no usable terms in {query!r} — name the subject you need"}

    wanted_kinds = kinds or ["instruction", "rule", "reference"]

    library = iter_skills()
    weights = _term_weights(library, base_terms)
    ranked = []
    for skill in library:
        score, rows = _score_index(skill, base_terms, weights)
        if score > 0:
            ranked.append((score, skill, rows))
    ranked.sort(key=lambda t: (-t[0], t[1]["name"]))
    ranked = ranked[:max_results]

    # A lessons search must not be gated on the index, which catalogues SKILL.md
    # only. A pitfall whose symptom text appears nowhere in the index — an error
    # message, typically — would be unreachable, and that is precisely the entry
    # most worth finding.
    #
    # The trigger is "the index phase produced no usable BLOCKS", not "the index
    # matched nothing". A query like "pthread_create undefined reference" matches
    # some unrelated skill's description on the word "reference", which is enough
    # to suppress the fallback while returning results with no content in them —
    # worse than no answer, because it looks like one.
    if set(wanted_kinds) & {"lesson", "pitfall"} and not _has_blocks(ranked, base_terms,
                                                                    wanted_kinds):
        ranked = []
        for skill in iter_skills():
            best = max((_score_block(b, base_terms) for b in skill["lesson_blocks"]
                        if b["kind"] in wanted_kinds), default=0.0)
            if best > 0:
                ranked.append((best, skill, []))
        ranked.sort(key=lambda t: (-t[0], t[1]["name"]))
        ranked = ranked[:max_results]

    if not ranked:
        return {"status": "no_match",
                "error": f"no skill's index matches {query!r}",
                "available_subjects": sorted(
                    s.get("subject") or s["name"] for s in iter_skills())}

    results: List[Dict[str, Any]] = []
    for score, skill, rows in ranked:
        expanded = list(base_terms)
        for row in rows:
            for term in _terms(row["covers"]):
                if term not in expanded:
                    expanded.append(term)

        # Draw from whichever file holds the requested kinds. Lessons and pitfalls
        # live in LESSONS.md and are retrieved by memory search, not skill search.
        pool = [*skill["blocks"], *skill["lesson_blocks"]]
        candidates = [b for b in pool if b["kind"] in wanted_kinds]
        scored = sorted(((_score_block(b, expanded), b) for b in candidates),
                        key=lambda p: -p[0])
        blocks = [
            {"label": b["label"], "kind": b["kind"], "title": b["title"],
             "body": b["body"], "score": round(s, 2)}
            for s, b in scored if s > 0
        ][:max_blocks]

        results.append({
            "skill": skill["name"],
            "subject": skill.get("subject") or skill["name"],
            "type": skill.get("type", "skill"),
            "layer": skill["layer"],
            "description": skill["description"],
            "score": round(score, 2),
            "index_matches": rows,
            "blocks": blocks,
            "has_lessons": skill["has_lessons_file"],
        })

    _log_retrieval("search", query, [r["skill"] for r in results if r["blocks"]])
    return {"status": "ok", "query": query, "count": len(results), "results": results}


def load(name: str, label: str = "", section: str = "",
         file: str = SKILL_FILE) -> Dict[str, Any]:
    """Load a skill: one labelled block, one section, or the whole file.

    ``label`` is the addressable unit and the one to prefer — ``R3`` returns
    exactly one constraint. ``section`` returns a whole group (all Rules). Neither
    returns the file, which is what makes partial loading real.
    """
    requested = [n.strip() for n in name.split(",") if n.strip()]
    loaded: List[Dict[str, Any]] = []
    missing: List[str] = []

    for want in requested:
        skill = get(want)
        if skill is None:
            missing.append(want)
            continue

        entry: Dict[str, Any] = {"skill": skill["name"], "layer": skill["layer"],
                                 "subject": skill.get("subject") or skill["name"]}
        if label:
            block = find_block(skill, label)
            if block is None:
                entry["error"] = f"no block labelled {label!r}"
                entry["available_labels"] = [
                    b["label"] for b in [*skill["blocks"], *skill["lesson_blocks"]]]
            else:
                entry.update({"label": block["label"], "kind": block["kind"],
                              "title": block["title"], "content": block["body"],
                              "references": parse_references(block["body"])})
            loaded.append(entry)
            continue

        text = skill["lessons_text"] if file == LESSONS_FILE else skill["skill_text"]
        if file not in (SKILL_FILE, LESSONS_FILE):
            sibling = Path(skill["dir"]) / file
            if not sibling.is_file():
                missing.append(f"{want} (file={file!r} not found)")
                continue
            text = sibling.read_text(encoding="utf-8", errors="replace")

        if section:
            sections = split_sections(text)
            key = next((k for k in sections if k.lower() == section.lower()), None)
            if key is None:
                key = next((k for k in sections if section.lower() in k.lower()), None)
            if key is None:
                entry["error"] = f"no section matching {section!r}"
                entry["available_sections"] = sorted(sections)
                loaded.append(entry)
                continue
            text = sections[key]
            entry["section"] = key

        entry["content"] = text
        entry["references"] = parse_references(text)
        loaded.append(entry)

    _log_retrieval("load", name, [str(e.get("skill")) for e in loaded if e.get("content")])
    result: Dict[str, Any] = {"status": "ok" if loaded else "not_found", "loaded": loaded}
    if missing:
        result["missing"] = missing
        result["available"] = sorted(s["name"] for s in iter_skills())
    return result


def index_of(name: str) -> Dict[str, Any]:
    """The Index catalogue of one skill — the cheapest possible orientation."""
    skill = get(name)
    if skill is None:
        return {"status": "not_found", "error": f"no skill named {name!r}"}
    return {
        "status": "ok",
        "skill": skill["name"],
        "subject": skill.get("subject") or skill["name"],
        "type": skill.get("type", "skill"),
        "description": skill["description"],
        "index": skill["index"],
        "has_lessons": skill["has_lessons_file"],
        "usage": "skill_load(name=..., label='R3') for one block.",
    }


# ---------------------------------------------------------------------------
# Authoring
# ---------------------------------------------------------------------------

def create(name: str, description: str, subject: str = "",
           kind: str = "skill", subjects: Optional[List[str]] = None,
           layer: Optional[str] = None) -> Dict[str, Any]:
    """Create an empty skill (or association skill) in the schema's shape."""
    from phronix.layers import resolve_write_layer, skill_dirs
    from phronix.privacy import anonymize, current_users

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        return {"status": "error", "error": "name must contain letters or digits"}
    if kind not in ("skill", "association"):
        return {"status": "error", "error": "kind must be 'skill' or 'association'"}
    if kind == "association" and len(subjects or []) < 2:
        return {"status": "error",
                "error": "an association skill joins two subjects; pass subjects=[a, b]. "
                         "Its whole purpose is to hold what is true only of the pair."}
    if slug in skill_dirs():
        return {"status": "exists", "skill": slug,
                "hint": "add a block with skill_write instead of recreating the skill"}

    target = resolve_write_layer(layer)
    directory = skill_home(slug, target, subject or "")
    directory.mkdir(parents=True, exist_ok=True)
    users = current_users()
    (directory / SKILL_FILE).write_text(anonymize(scaffold_skill(
        slug, description, subject or slug, kind, subjects), extra_users=users))
    _mark_dirty(f"skill_create:{slug}")
    return {"status": "ok", "skill": slug, "type": kind, "layer": target.name,
            "file": str(directory / SKILL_FILE),
            "next": "Add instructions with skill_write(kind='instruction', ...) and "
                    "constraints with kind='rule'. Keep it to ONE subject; link to "
                    "others with references rather than restating them."}


def define(
    name: str,
    description: str,
    subject: str = "",
    instructions: Optional[List[Dict[str, str]]] = None,
    rules: Optional[List[Dict[str, str]]] = None,
    references: Optional[List[Dict[str, str]]] = None,
    pitfalls: Optional[List[Dict[str, str]]] = None,
    lessons: Optional[List[Dict[str, str]]] = None,
    kind: str = "skill",
    subjects: Optional[List[str]] = None,
    layer: Optional[str] = None,
    allow_relabel: bool = False,
) -> Dict[str, Any]:
    """Create or update a skill declaratively. Idempotent.

    The arguments fully determine the file: blocks not listed are removed, the
    Index is generated, sections are emitted in a fixed order, and the result is
    byte-identical for the same input. Re-running is a no-op that reports
    ``unchanged``.

    This is the difference from :func:`write_block`, which appends one block per
    call and therefore cannot be safely re-run. Use ``define`` to state what a
    skill *should be*; use ``write_block`` to add a single thing to what it
    already is.

    Labels are preserved across updates by title (see
    :func:`phronix.skill_schema.assign_labels`), so editing a block's body never
    renumbers it. A change that would break an incoming reference from another
    skill is refused unless *allow_relabel* — a dangling foreign key is worse than
    a rejected edit, because nothing downstream reports it.
    """
    from phronix.layers import resolve_write_layer, skill_dirs
    from phronix.privacy import anonymize, current_users
    from phronix.skill_schema import (
        assign_labels, parse_references as _parse_refs, render_lessons, render_skill,
    )

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        return {"status": "error", "error": "name must contain letters or digits"}
    if kind not in ("skill", "association"):
        return {"status": "error", "error": "kind must be 'skill' or 'association'"}
    if kind == "association" and len(subjects or []) < 2:
        return {"status": "error",
                "error": "an association skill joins two subjects; pass subjects=[a, b]"}
    if kind == "skill" and not (instructions or rules):
        return {"status": "error",
                "error": "a skill needs at least one instruction or rule — one with "
                         "neither says nothing about how to do anything"}

    users = current_users()

    def clean(entries: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        out = []
        for entry in entries or []:
            title = anonymize(str(entry.get("title", "")), extra_users=users).strip()
            body = anonymize(str(entry.get("body", "")), extra_users=users).strip()
            if not title or not body:
                continue
            out.append({"title": title, "body": body, "label": entry.get("label")})
        return out

    existing_dir = skill_dirs().get(slug)
    prior = parse_skill(existing_dir) if existing_dir else None
    prior_titles = {}
    if prior:
        for block in [*prior["blocks"], *prior["lesson_blocks"]]:
            prior_titles[block["title"]] = block["label"]

    blocks: List[Dict[str, Any]] = []
    for entries, block_kind in ((instructions, "instruction"), (rules, "rule"),
                                (references, "reference")):
        blocks += assign_labels(clean(entries), block_kind, prior_titles)
    lesson_blocks: List[Dict[str, Any]] = []
    for entries, block_kind in ((pitfalls, "pitfall"), (lessons, "lesson")):
        lesson_blocks += assign_labels(clean(entries), block_kind, prior_titles)

    # Refuse to strand an incoming foreign key. Lesson labels only count as
    # dropped when lessons were actually supplied — omitting them leaves
    # LESSONS.md untouched, so reporting its labels as dropped would refuse an
    # edit that removes nothing.
    replacing_lessons = bool(pitfalls or lessons)
    dropped = _dropped_labels(prior, blocks + lesson_blocks,
                              include_lessons=replacing_lessons)
    broken = _incoming_references(slug, dropped) if dropped else []
    if broken and not allow_relabel:
        return {
            "status": "would_break_references",
            "skill": slug,
            "dropped_labels": sorted(dropped),
            "referenced_by": broken,
            "next": "These labels are cited from other skills. Keep them (pass an explicit "
                    "`label` on the block), update the citing skills first, or re-run with "
                    "allow_relabel=True if the references are meant to go.",
        }

    target = resolve_write_layer(layer)
    # An existing skill is updated where it already lives; only a new one is
    # placed by the rule. Moving a skill on update would strand every path
    # already recorded against it.
    here = existing_home(slug)
    directory = (here if here is not None and str(here).startswith(str(target.root))
                 else skill_home(slug, target, subject or ""))
    directory.mkdir(parents=True, exist_ok=True)

    skill_text = render_skill(slug, anonymize(description, extra_users=users).strip(),
                              anonymize(subject or slug, extra_users=users).strip(),
                              blocks, kind, subjects)
    written: List[str] = []
    skill_path = directory / SKILL_FILE
    if not skill_path.exists() or skill_path.read_text() != skill_text:
        skill_path.write_text(skill_text)
        written.append(SKILL_FILE)

    lessons_path = directory / LESSONS_FILE
    if lesson_blocks:
        lessons_text = render_lessons(slug, subject or slug, lesson_blocks)
        if not lessons_path.exists() or lessons_path.read_text() != lessons_text:
            lessons_path.write_text(lessons_text)
            written.append(LESSONS_FILE)
    # Never silently delete recorded lessons: they are the most expensive content
    # in the store to reproduce, and a caller that simply omitted the argument did
    # not mean "discard everything anyone ever learned here".
    #
    # Reported separately from `written`: it is a note about what was NOT done, and
    # counting it as a write would make an otherwise-unchanged call report
    # "updated" — destroying the idempotency signal the caller relies on.
    preserved = (bool(lessons_path.exists() and prior and prior["lesson_blocks"]
                      and not lesson_blocks))

    if written:
        _mark_dirty(f"skill_define:{slug}")

    from phronix.correctors import correct

    return {
        "status": "ok",
        "action": "unchanged" if not written else ("created" if prior is None else "updated"),
        "skill": slug,
        "layer": target.name,
        "files_written": written,
        **({"lessons_preserved": f"{LESSONS_FILE} left alone — pass lessons/pitfalls "
                                 "to replace them"} if preserved else {}),
        "labels": {b["label"]: b["title"] for b in blocks + lesson_blocks},
        "corrector": correct("skill", slug),
        "verification": _verification_status(slug),
            "complexity_impact": _complexity_impact(slug),
    }


def _dropped_labels(prior: Optional[Dict[str, Any]], blocks: List[Dict[str, Any]],
                    include_lessons: bool = True) -> set:
    if prior is None:
        return set()
    before = {b["label"] for b in prior["blocks"]}
    if include_lessons:
        before |= {b["label"] for b in prior["lesson_blocks"]}
    return before - {b["label"] for b in blocks}


def _incoming_references(slug: str, labels: set) -> List[Dict[str, str]]:
    """Which other skills cite the labels about to disappear."""
    out: List[Dict[str, str]] = []
    for other in iter_skills():
        if other["dir_name"] == slug:
            continue
        for reference in parse_references(other["skill_text"]):
            if reference["skill"] == slug and reference["label"] in labels:
                out.append({"from": other["name"], "reference": reference["raw"]})
    return out


def _writable_copy(skill_name: str, filename: str, scaffold: str,
                   layer: Optional[str]) -> Tuple[Path, str, Any]:
    """Resolve the file to edit in the write layer, forking from a lower layer.

    Forking copies the whole existing file first, so the shadowing copy is a
    superset. A shadow that silently dropped the bundled content would look
    exactly like the framework losing knowledge.
    """
    from phronix.layers import resolve_write_layer, skill_dirs

    target = resolve_write_layer(layer)
    existing = skill_dirs().get(skill_name)
    dest_dir = (existing if existing is not None
                and str(existing).startswith(str(target.root))
                else skill_home(skill_name, target))

    if existing is not None and str(existing).startswith(str(target.root)):
        action = "updated"
    elif existing is not None:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for candidate in (SKILL_FILE, LESSONS_FILE):
            source = existing / candidate
            if source.is_file() and not (dest_dir / candidate).exists():
                (dest_dir / candidate).write_text(
                    source.read_text(encoding="utf-8", errors="replace"))
        action = "forked"
    else:
        action = "created"

    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / filename
    if not path.exists():
        path.write_text(scaffold)
    return path, action, target


@contextlib.contextmanager
def _exclusive(path: Path):
    """Hold an exclusive lock on *path* for a read-modify-write.

    Skills are written by more than one thing at once. With tasks running
    concurrently, two of them may write the same subject skill; and the
    background learner writes lessons into skills while tasks are writing
    blocks into them. The sequence here is read, allocate the next label from
    what was read, then write — so two writers read the same file, both decide
    the label is `I4`, and the second write erases the first.

    That is worse than losing a block. The label is a stable key: everything
    that already points at `[[skill#I4]]` now points at whichever body won, and
    nothing anywhere records that it changed.

    Advisory, on a sidecar file, because the lock must outlive any single open
    of the file being rewritten.
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except OSError:
            pass                      # a filesystem without locks is still usable
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()


#: Skills that are the framework's own METHOD, and stay in `skills/`.
#:
#: Everything else a run writes down is an ANSWER to one problem — a fix, a
#: subject's findings, a solution — and answers belong under `capabilities/`,
#: filed by topic, where `--fresh` filters them by provenance and an MCP lookup
#: finds them by subject.
#:
#: The two have different audiences. `skills/` is read by every task on every
#: repository: how to plan, how to explore, how to judge. A fix for one bug in
#: one project is not method, and mixing them means a from-scratch run inherits
#: another task's answer while believing it started clean — measured: six
#: near-duplicate `column-domain` skills reached a fresh run through the
#: bundled skeleton, none of them written by it.
CORE_SKILL_PREFIX = "phronix-"


def is_core_skill(name: str) -> bool:
    """Is this the framework's own method, rather than one problem's answer?"""
    return str(name).startswith(CORE_SKILL_PREFIX)


def skill_home(slug: str, target: Any, subject: str = "") -> Path:
    """The directory a skill's files live in, for the layer *target*.

    THE one place that decides. Every writer goes through this — the scaffold,
    the renderer, the lesson file, the association — because a second opinion
    about where a skill lives is a skill written to one place and read from
    another.

    Keyed on the SLUG, never on the subject. The subject is free text and the
    same skill is legitimately re-declared with a different one — "deploying
    the service" today, "something else" tomorrow — and a home derived from it
    moves when the prose does, stranding every path already recorded against
    the skill. `subject` is accepted and ignored so callers that have one need
    no special case.
    """
    del subject                       # deliberately not part of the location
    if is_core_skill(slug):
        return target.dir("skills") / slug
    from phronix.capabilities import TASK_CAPABILITY_DIR, task_slug

    return (target.dir("capabilities") / TASK_CAPABILITY_DIR
            / task_slug(slug) / slug)


def existing_home(slug: str) -> Optional[Path]:
    """Where this skill already is, whichever store holds it."""
    from phronix.layers import skill_dirs

    return skill_dirs().get(slug)


def write_block(skill: str, kind: str, title: str, body: str,
                description: str = "", layer: Optional[str] = None,
                replace: bool = False) -> Dict[str, Any]:
    """Add an instruction, rule or reference block under a new label.

    The label is allocated from the highest number in use and never recycled: a
    reused label silently redirects every existing cross-reference to different
    content, which is the one failure stable keys exist to prevent.

    The Index is regenerated afterwards, so the catalogue cannot drift from what
    the file actually contains.

    **A lesson or pitfall is routed to LESSONS.md rather than rejected.** This
    used to return an error whose text named the correct tool — the call knew
    where the content belonged and refused to put it there. Measured against a
    real session, that cost the system its only piece of learning: an agent
    recorded a genuine symptom-and-root-cause for a sympy dimension bug, got the
    error back, did not retry, and the lesson was lost. In a system whose premise
    is that nothing is learned twice, a near-miss on an enum is not a reason to
    discard knowledge. The call is redirected and says so in ``routed_to``.
    """
    from phronix.privacy import anonymize, current_users

    if kind in ("lesson", "pitfall"):
        result = write_lesson(skill, body, kind=kind, title=title,
                              description=description, layer=layer)
        if isinstance(result, dict):
            result = dict(result)
            result["routed_to"] = "LESSONS.md"
            result["note"] = (f"kind={kind!r} belongs in LESSONS.md; written there "
                              "rather than rejected. Use skill_write_lesson directly "
                              "to skip this hop.")
        return result

    if kind not in ("instruction", "rule", "reference"):
        return {"status": "error",
                "error": f"kind={kind!r} must be instruction|rule|reference "
                         "(or lesson|pitfall, which is routed to LESSONS.md)."}

    slug = re.sub(r"[^a-z0-9]+", "-", skill.lower()).strip("-")
    users = current_users()
    clean_title = anonymize(title, extra_users=users).strip()
    clean_body = anonymize(body, extra_users=users).strip()
    if not clean_title or not clean_body:
        return {"status": "error", "error": "title and body are both required"}

    too_long = _length_error(kind, clean_title, clean_body)
    if too_long:
        return too_long

    path, action, target = _writable_copy(
        slug, SKILL_FILE,
        scaffold_skill(slug, description or f"The {slug} subject.", slug), layer)

    parsed = parse_skill(path.parent)
    existing = next((b for b in parsed["blocks"]
                     if b["title"].lower() == clean_title.lower()
                     and b["kind"] == kind), None)

    if existing is not None and not replace:
        return {"status": "already_present", "skill": slug, "file": str(path)}

    if existing is not None:
        # Refresh in place, keeping the label.
        #
        # For a GENERATED block that states current state — the research
        # checkpoint, the ranked playbook — "already present" is not a safe
        # no-op, it is a stale answer served forever. The checkpoint froze at
        # whatever the first research stage wrote, so every retry resumed from a
        # picture several stages out of date while reporting success.
        #
        # The label is kept rather than reallocated, which is consistent with
        # never recycling one: it still designates the same subject matter, and
        # every `[[skill#Xn]]` pointing at it stays correct.
        label = existing["label"]
        with _exclusive(path):
            text = upsert_block(
                path.read_text(encoding="utf-8", errors="replace"),
                BLOCK_KINDS[kind]["section"], label, clean_title, clean_body)
            path.write_text(refresh_index(text))
        _mark_dirty(f"skill_write:{slug}:{label}")
        return {"status": "ok", "action": "refreshed", "skill": slug,
                "label": label, "kind": kind, "file": str(path),
                "layer": target.name, "reference": f"[[{slug}#{label}]]",
                "verification": _verification_status(slug),
                "complexity_impact": _complexity_impact(slug)}

    # The label is allocated from the file as it is INSIDE the lock, not from
    # the copy parsed earlier: between those two moments another writer may have
    # taken the label this one was about to use.
    with _exclusive(path):
        current = path.read_text(encoding="utf-8", errors="replace")
        label = next_label(parse_skill(path.parent), kind)
        text = upsert_block(current, BLOCK_KINDS[kind]["section"], label,
                            clean_title, clean_body)
        path.write_text(refresh_index(text))
    _mark_dirty(f"skill_write:{slug}:{label}")

    return {"status": "ok", "action": action, "skill": slug, "label": label,
            "kind": kind, "file": str(path), "layer": target.name,
            "reference": f"[[{slug}#{label}]]",
            "verification": _verification_status(slug),
            "complexity_impact": _complexity_impact(slug)}


def write_lesson(skill: str, lesson: str, kind: str = "lesson", title: str = "",
                 description: str = "", layer: Optional[str] = None,
                 when: Optional[str] = None) -> Dict[str, Any]:
    """Record a pitfall or a dated lesson into the skill's ``LESSONS.md``.

    Lessons live in a separate file from instructions on purpose. "How do I do
    this?" and "what went wrong last time?" are different questions retrieved by
    different tools — mixing them means every retrieval of either drags in the
    other, and the file grows until nobody can load a part of it.
    """
    from phronix.privacy import anonymize, current_users, find_identifiers

    if kind not in ("lesson", "pitfall"):
        return {"status": "error", "error": "kind must be 'lesson' or 'pitfall'"}

    slug = re.sub(r"[^a-z0-9]+", "-", skill.lower()).strip("-")
    if not slug:
        return {"status": "error", "error": "skill name must contain letters or digits"}

    users = current_users()
    redacted = find_identifiers(lesson, extra_users=users)
    clean = anonymize(lesson, extra_users=users).strip()
    if not clean:
        return {"status": "error", "error": "lesson is empty after redaction"}

    too_long = _length_error(kind, title, clean)
    if too_long:
        return too_long

    # Create the skill file too when the skill is brand new, so a lesson never
    # produces a LESSONS.md orphaned from any subject.
    #
    # The action from the FIRST call is the meaningful one. By the time the second
    # runs, the fork has already placed the skill in the write layer, so it would
    # report "updated" and hide the fact that a bundled skill was just shadowed.
    _, action, _ = _writable_copy(
        slug, SKILL_FILE,
        scaffold_skill(slug, description or f"The {slug} subject.", slug), layer)
    path, _, target = _writable_copy(slug, LESSONS_FILE, scaffold_lessons(slug), layer)

    text = path.read_text(encoding="utf-8", errors="replace")
    if clean in text:
        return {"status": "already_present", "skill": slug, "file": str(path)}

    parsed = parse_skill(path.parent)
    label = next_label(parsed, kind)
    stamp = when or date.today().isoformat()
    heading = anonymize(title, extra_users=users).strip() or clean.split(".")[0][:70]
    body = f"**{stamp}** — {clean}" if kind == "lesson" else clean

    path.write_text(upsert_block(text, BLOCK_KINDS[kind]["section"], label, heading, body))
    _mark_dirty(f"skill_lesson:{slug}:{label}")

    return {"status": "ok", "action": action, "skill": slug, "label": label,
            "kind": kind, "file": str(path), "layer": target.name,
            "reference": f"[[{slug}#{label}]]", "redacted": redacted,
            "verification": _verification_status(slug),
            "complexity_impact": _complexity_impact(slug)}


def _mark_dirty(reason: str) -> None:
    try:
        from phronix.knowledge_graph import mark_dirty

        mark_dirty(reason)
    except Exception:
        pass  # retrieval degrades to the next hash sweep; never fail a write


def _complexity_impact(skill: str) -> Dict[str, Any]:
    """Which agents this change affects, and whether their level requirement moved.

    Reported on every write because this is where the self-learning loop closes.
    A lesson recorded into a subject changes the judgment burden of every agent
    that loads it; without surfacing that, learning accumulates in the skills and
    the agents depending on them silently fall out of calibration.

    Best-effort: assessment must never fail a write.
    """
    try:
        from phronix.complexity import impact_of

        return impact_of(skill)
    except Exception as exc:
        return {"skill": skill, "note": f"could not assess impact: {exc}"}


def _verification_status(skill: str) -> Dict[str, Any]:
    """Whether this skill has a corrector, and what to do about it."""
    try:
        from phronix.verification import covers

        names = covers("skill", skill)
    except Exception:
        return {"covered": None, "note": "could not determine verifier coverage"}

    if names:
        return {"covered": True, "verifiers": names,
                "next": f"Run verify_run(target={skill!r}) to confirm it still holds."}
    return {
        "covered": False, "verifiers": [],
        "next": (f"No corrector covers {skill!r}. Write one with verify_new(kind='skill', "
                 f"target={skill!r}, claim=...) — an unfalsifiable claim in a shared skill "
                 "gets trusted long after it stops being true."),
    }


# ---------------------------------------------------------------------------
# The install
# ---------------------------------------------------------------------------

def _is_ours(link: Path) -> bool:
    from phronix.layers import which_layer

    try:
        return link.is_symlink() and which_layer(link.resolve()) is not None
    except OSError:
        return False


def install_skills(target_root: Optional[Path] = None,
                   harnesses: Optional[List[str]] = None,
                   merge: bool = True) -> Dict[str, Any]:
    """Symlink every visible skill into each harness's discovery directory.

    Idempotent and merge-safe: an existing link of ours is left alone, a stale one
    (the skill moved layers) is repointed, and a name colliding with an unrelated
    user skill is installed as ``phronix-<name>`` rather than overwriting it.
    """
    from phronix.layers import project_root, skill_dirs

    root = Path(target_root) if target_root else (project_root() or Path.cwd())
    available = skill_dirs()
    installed: List[Dict[str, str]] = []
    conflicts: List[str] = []
    targets: List[str] = []

    for harness in (harnesses or list(HARNESS_SKILL_DIRS)):
        dest_root = root / HARNESS_SKILL_DIRS[harness]
        dest_root.mkdir(parents=True, exist_ok=True)
        targets.append(str(dest_root))

        for name, source in sorted(available.items()):
            dest = dest_root / name

            if _is_ours(dest):
                if dest.resolve() == source.resolve():
                    installed.append({"harness": harness, "name": name,
                                      "action": "already_installed"})
                else:
                    dest.unlink()
                    dest.symlink_to(source, target_is_directory=True)
                    installed.append({"harness": harness, "name": name, "action": "repointed"})
                continue

            if not dest.exists() and not dest.is_symlink():
                dest.symlink_to(source, target_is_directory=True)
                installed.append({"harness": harness, "name": name, "action": "linked"})
                continue

            if not merge:
                conflicts.append(str(dest))
                continue

            namespaced = dest_root / f"phronix-{name}"
            if _is_ours(namespaced):
                installed.append({"harness": harness, "name": namespaced.name,
                                  "action": "already_installed"})
            elif not namespaced.exists() and not namespaced.is_symlink():
                namespaced.symlink_to(source, target_is_directory=True)
                installed.append({"harness": harness, "name": namespaced.name,
                                  "action": "linked_namespaced"})
            else:
                conflicts.append(str(dest))

    return {"targets": targets, "installed": installed, "conflicts": conflicts}


def ensure_skills_setup(target_root: Optional[Path] = None,
                        force: bool = False) -> Dict[str, Any]:
    """Startup self-heal step: re-link skills, repairing anything stale or missing.

    No state-file fast path. :func:`install_skills` is a handful of ``stat`` calls,
    and a state file that says "done" while the directory has been deleted is the
    exact failure that leaves a workspace with no skills and no error.
    """
    result = install_skills(target_root=target_root)
    changed = [i for i in result["installed"] if i["action"] != "already_installed"]
    return {"status": "installed" if changed or force else "already_done",
            "changed": changed, **result}


def main() -> None:
    """Entry point for ``phronix-install-skills``."""
    import argparse

    from phronix.layers import project_root

    parser = argparse.ArgumentParser(
        prog="phronix-install-skills",
        description="Symlink every visible phronix skill into the harness discovery "
                    "directories (.claude/skills, .opencode/skills).",
    )
    parser.add_argument("--target", default=None)
    parser.add_argument("--harness", choices=[*HARNESS_SKILL_DIRS, "all"], default="all")
    parser.add_argument("--list", action="store_true", help="Print visible skills and exit.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list:
        for skill in iter_skills():
            marker = "assoc" if skill.get("type") == "association" else "skill"
            print(f"{skill['layer']:8s} {marker:6s} {skill['name']:32s} "
                  f"{len(skill['blocks']):3d} blocks  {skill['description'][:50]}")
        return

    root = (Path(args.target).expanduser().resolve() if args.target
            else (project_root() or Path.cwd()))
    harnesses = None if args.harness == "all" else [args.harness]
    result = install_skills(target_root=root, harnesses=harnesses)

    if args.json:
        print(json.dumps(result, indent=2))
        return
    for target in result["targets"]:
        print(f"Skills directory: {target}")
    for item in result["installed"]:
        marker = {"linked": "+", "linked_namespaced": "+", "repointed": "~"}.get(
            item["action"], "=")
        print(f"  {marker} [{item['harness']}] {item['name']}")
    for conflict in result["conflicts"]:
        print(f"  ! conflict, left alone: {conflict}")


if __name__ == "__main__":
    main()
