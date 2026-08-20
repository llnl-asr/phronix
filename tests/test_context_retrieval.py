"""Graph-backed retrieval: the split between "how to do it" and "what was learned".

These tests are unit tests of the ranking rules, driven through ``_score_doc`` and
the node-filtering helpers, so they run without ``graphify`` installed. The
end-to-end path (stage, build, query) is covered by the live check in
``test_graph_live.py``, which skips when the CLI is absent.

Each rule here exists because it was observed getting the ranking wrong, and the
comments say which failure it prevents — those are the regressions worth guarding.
"""
from __future__ import annotations

from phronix import knowledge_graph as kg


def _node(label, source_file, line=1):
    return {"label": label, "source_file": source_file,
            "source_location": f"L{line}", "file_type": "document", "id": label}


class TestStoreScoping:
    def test_store_filter_matches_the_staging_prefix(self):
        skill = _node("Sec", "bundled-skills/x/SKILL.md")
        memory = _node("Sec", "project-memory/y.md")
        assert kg._in_store(skill, "skills") and not kg._in_store(skill, "memory")
        assert kg._in_store(memory, "memory") and not kg._in_store(memory, "skills")

    def test_all_matches_every_store(self):
        assert kg._in_store(_node("S", "bundled-skills/x/SKILL.md"), "all")

    def test_artifact_name_is_derived_from_the_staged_path(self):
        assert kg._artifact_of("bundled-skills/phronix-privacy/SKILL.md") == "phronix-privacy"
        assert kg._artifact_of("project-memory/some-fact.md") == "some-fact"


class TestPreferSections:
    def test_whole_file_node_is_dropped_when_sections_exist(self):
        """Returning a file node IS loading the whole skill — the thing to avoid."""
        docs = [_node("SKILL.md", "bundled-skills/x/SKILL.md", 1),
                _node("A Section", "bundled-skills/x/SKILL.md", 10)]
        kept = kg._prefer_sections(docs)
        assert [n["label"] for n in kept] == ["A Section"]

    def test_whole_file_node_is_kept_when_there_are_no_sections(self):
        """A short memory with no headings would otherwise be unreachable."""
        docs = [_node("note.md", "project-memory/note.md", 1)]
        assert kg._prefer_sections(docs) == docs

    def test_other_files_are_unaffected(self):
        docs = [_node("a.md", "project-memory/a.md", 1),
                _node("b.md", "project-memory/b.md", 1),
                _node("Heading", "project-memory/b.md", 5)]
        kept = {n["label"] for n in kg._prefer_sections(docs)}
        assert kept == {"a.md", "Heading"}


class TestScoring:
    def test_empty_section_scores_zero_whatever_its_heading(self):
        """Every skill ends with a bare `## Lessons`; on heading weight alone those
        identical placeholders outranked all real content for any query with the
        word "lesson" in it."""
        node = _node("Lessons", "bundled-skills/x/SKILL.md")
        assert kg._score_doc(node, ["lesson"], "## Lessons\n\n") == 0.0

    def test_a_section_with_content_outranks_the_empty_placeholder(self):
        placeholder = _node("Lessons", "bundled-skills/x/SKILL.md")
        real = _node("Recording a lesson", "bundled-skills/y/SKILL.md")
        assert kg._score_doc(real, ["lesson"], "## Recording a lesson\n\nbody text\n") > \
               kg._score_doc(placeholder, ["lesson"], "## Lessons\n")

    def test_heading_hit_outranks_a_body_hit(self):
        heading = _node("Corrector design", "bundled-skills/x/SKILL.md")
        body = _node("Something else", "bundled-skills/x/SKILL.md")
        assert kg._score_doc(heading, ["corrector"], "## Corrector design\n\ntext\n") > \
               kg._score_doc(body, ["corrector"], "## Something else\n\nthe corrector\n")

    def test_body_only_match_still_scores(self):
        """Heading-only scoring was the original bug: it buried the real answer."""
        node = _node("Something else", "bundled-skills/x/SKILL.md")
        assert kg._score_doc(node, ["corrector"], "## Something else\n\nthe corrector\n") > 0

    def test_artifact_name_contributes(self):
        node = _node("Overview", "bundled-skills/phronix-privacy/SKILL.md")
        assert kg._score_doc(node, ["privacy"], "## Overview\n\ntext\n") > 0

    def test_coverage_beats_raw_frequency(self):
        """3-of-3 terms once each answers better than one term twenty times."""
        broad = _node("alpha beta", "bundled-skills/x/SKILL.md")
        narrow = _node("alpha", "bundled-skills/y/SKILL.md")
        terms = ["alpha", "beta", "gamma"]
        assert kg._score_doc(broad, terms, "## alpha beta\n\ngamma\n") > \
               kg._score_doc(narrow, terms, "## alpha\n\n" + "alpha " * 20)

    def test_no_match_is_zero(self):
        node = _node("Unrelated", "bundled-skills/x/SKILL.md")
        assert kg._score_doc(node, ["nothingmatches"], "## Unrelated\n\nbody\n") == 0.0

    def test_section_body_strips_the_heading_line(self):
        assert kg._section_body("## Heading\n\nbody\n").strip() == "body"
        assert kg._section_body("no heading here").strip() == "no heading here"


class TestStopwords:
    def test_interrogatives_are_dropped(self):
        """Agents phrase these as questions; scoring "how"/"when" swamps the signal."""
        for word in ("how", "what", "when", "where", "why", "does", "should"):
            assert word in kg._STOPWORDS

    def test_content_words_are_kept(self):
        for word in ("corrector", "assumption", "redact", "capability"):
            assert word not in kg._STOPWORDS
