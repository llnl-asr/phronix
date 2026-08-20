"""The skill library as a relational store: schema parsing, index-first search, authoring.

The schema's guarantees are what make retrieval work — one subject per skill,
stable labels, an index that matches the content, references that resolve. Each
test here pins one of them.
"""
from __future__ import annotations

from phronix import skill_schema as schema
from phronix import skills


def _write(store, name, skill_md, lessons_md=None):
    directory = store / "skills" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(skill_md)
    if lessons_md is not None:
        (directory / "LESSONS.md").write_text(lessons_md)
    return directory


def _skill(name, description="a description that is comfortably long enough",
           subject="the subject", body=""):
    return (f"---\nname: {name}\ndescription: {description}\n"
            f"subject: {subject}\ntype: skill\n---\n\n"
            "## Index\n\n| Label | Section | Covers |\n| --- | --- | --- |\n\n" + body)


# ---------------------------------------------------------------------------
# Schema parsing
# ---------------------------------------------------------------------------

class TestSchemaParsing:
    def test_block_labels_and_bodies(self):
        blocks = schema.parse_blocks(
            "## Rules\n\n### R1 — First rule\n\nbody one\n\n### R2 — Second\n\nbody two\n")
        assert [b["label"] for b in blocks] == ["R1", "R2"]
        assert blocks[0]["kind"] == "rule"
        assert blocks[0]["title"] == "First rule"
        assert blocks[0]["body"] == "body one"

    def test_all_three_dash_forms_parse(self):
        """Em dash, en dash and hyphen all get typed; rejecting any is a trap."""
        for dash in ("—", "–", "-"):
            blocks = schema.parse_blocks(f"### I1 {dash} Title\n\nbody\n")
            assert blocks and blocks[0]["title"] == "Title"

    def test_a_block_stops_at_the_next_section(self):
        """Otherwise a block silently swallows everything after it."""
        blocks = schema.parse_blocks("### R1 — A rule\n\nbody\n\n## References\n\ntrailing\n")
        assert "trailing" not in blocks[0]["body"]

    def test_index_rows_parse_and_skip_the_header(self):
        rows = schema.parse_index(
            "## Index\n\n| Label | Section | Covers |\n| --- | --- | --- |\n"
            "| `R1` | Rules | what it covers |\n")
        assert rows == [{"label": "R1", "section": "Rules", "covers": "what it covers"}]

    def test_references_capture_the_label(self):
        found = schema.parse_references("see [[other-skill#R3]] and [[plain-skill]]")
        assert found[0] == {"skill": "other-skill", "label": "R3", "raw": "[[other-skill#R3]]"}
        assert found[1]["label"] is None

    def test_references_are_deduped(self):
        assert len(schema.parse_references("[[a#R1]] [[a#R1]] [[a#R2]]")) == 2

    def test_block_scalar_description_is_folded(self):
        fields, _ = schema.parse_frontmatter(
            "---\nname: x\ndescription: >\n  first line\n  second line\n---\n\n## Index\n")
        assert fields["description"] == "first line second line"

    def test_next_label_never_reuses_a_number(self, isolated_layers):
        """A recycled label silently redirects every existing reference."""
        directory = _write(isolated_layers["store"], "s",
                           _skill("s", body="## Rules\n\n### R1 — a\n\nb\n\n### R3 — c\n\nd\n"))
        parsed = schema.parse_skill(directory)
        assert schema.next_label(parsed, "rule") == "R4"

    def test_render_index_lists_every_block(self):
        blocks = schema.parse_blocks("### I1 — Step\n\nb\n\n### R1 — Rule\n\nb\n")
        rendered = schema.render_index(blocks)
        assert "| `I1` | Instructions | Step |" in rendered
        assert "| `R1` | Rules | Rule |" in rendered

    def test_refresh_index_replaces_a_stale_table(self, isolated_layers):
        text = _skill("s", body="## Rules\n\n### R1 — A rule\n\nbody\n")
        assert "| `R1` |" not in text
        assert "| `R1` | Rules | A rule |" in schema.refresh_index(text)

    def test_upsert_block_replaces_in_place(self):
        text = "## Rules\n\n### R1 — Old title\n\nold body\n"
        updated = schema.upsert_block(text, "Rules", "R1", "New title", "new body")
        assert "New title" in updated and "Old title" not in updated
        assert updated.count("### R1") == 1

    def test_upsert_block_creates_a_missing_section(self):
        updated = schema.upsert_block("## Index\n", "Rules", "R1", "T", "b")
        assert "## Rules" in updated and "### R1 — T" in updated


# ---------------------------------------------------------------------------
# Index-first search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_index_rows_drive_the_subject_match(self, isolated_layers):
        _write(isolated_layers["store"], "widget-build",
               _skill("widget-build", description="building widgets from source",
                      subject="building widgets",
                      body="## Rules\n\n### R1 — Link order\n\nput -lpthread last\n"))
        result = skills.search("how do I build a widget")
        assert result["status"] == "ok"
        assert result["results"][0]["skill"] == "widget-build"

    def test_matching_blocks_come_back_with_their_labels(self, isolated_layers):
        _write(isolated_layers["store"], "widget-build",
               _skill("widget-build", description="building widgets from source",
                      subject="building widgets",
                      body="## Rules\n\n### R1 — Link order matters\n\n"
                           "put -lpthread last on the command line\n"))
        top = skills.search("widget link order")["results"][0]
        assert any(b["label"] == "R1" for b in top["blocks"])
        assert "pthread" in top["blocks"][0]["body"]

    def test_a_body_mention_does_not_hijack_the_subject(self, isolated_layers):
        """Phase one must not let block bodies vote, or every passing mention wins."""
        _write(isolated_layers["store"], "about-widgets",
               _skill("about-widgets", description="everything about widgets",
                      subject="widgets"))
        _write(isolated_layers["store"], "about-sprockets",
               _skill("about-sprockets", description="everything about sprockets",
                      subject="sprockets",
                      body="## Rules\n\n### R1 — Note\n\nwidgets widgets widgets\n"))
        assert skills.search("widgets")["results"][0]["skill"] == "about-widgets"

    def test_a_matched_index_row_expands_the_query(self, isolated_layers):
        """The index describes the subject in ITS vocabulary, not the asker's.

        The query says "rollout", which appears nowhere in the block. The index row
        that matches it also says "canary", and that expansion is what reaches the
        block titled "Canary first".
        """
        _write(isolated_layers["store"], "deploys",
               _skill("deploys", description="shipping the service to production",
                      subject="deployment",
                      body="## Index\n\n| Label | Section | Covers |\n| --- | --- | --- |\n"
                           "| `R1` | Rules | canary rollout percentage |\n\n"
                           "## Rules\n\n### R1 — Canary first\n\n"
                           "send five percent of traffic before the fleet\n"))
        top = skills.search("rollout")["results"][0]
        assert top["index_matches"][0]["label"] == "R1"
        assert any(b["label"] == "R1" for b in top["blocks"])

    def test_lessons_are_excluded_from_skill_search(self, isolated_layers):
        """Skill search answers "how"; lessons answer "what went wrong"."""
        _write(isolated_layers["store"], "s",
               _skill("s", description="a subject about frobnication", subject="frobnication"),
               "## Lessons\n\n### L1 — Frobnication broke\n\nit exploded\n")
        top = skills.search("frobnication")["results"][0]
        assert all(b["kind"] != "lesson" for b in top["blocks"])

    def test_lessons_are_returned_when_asked_for(self, isolated_layers):
        _write(isolated_layers["store"], "s",
               _skill("s", description="a subject about frobnication", subject="frobnication"),
               "## Lessons\n\n### L1 — Frobnication broke\n\nit exploded\n")
        result = skills.search("frobnication", kinds=["lesson", "pitfall"])
        assert any(b["label"] == "L1"
                   for r in result["results"] for b in r["blocks"])

    def test_all_stopwords_query_is_rejected(self, isolated_layers):
        assert skills.search("how should this be done")["status"] == "error"

    def test_no_match_reports_the_available_subjects(self, isolated_layers):
        result = skills.search("zzzznonexistentsubject")
        assert result["status"] == "no_match"
        assert result["available_subjects"]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

class TestLoad:
    def test_label_returns_exactly_one_block(self, isolated_layers):
        _write(isolated_layers["store"], "s",
               _skill("s", body="## Rules\n\n### R1 — First\n\naaa\n\n### R2 — Second\n\nbbb\n"))
        entry = skills.load("s", label="R2")["loaded"][0]
        assert entry["content"] == "bbb"
        assert entry["title"] == "Second"

    def test_unknown_label_lists_what_exists(self, isolated_layers):
        _write(isolated_layers["store"], "s",
               _skill("s", body="## Rules\n\n### R1 — First\n\naaa\n"))
        entry = skills.load("s", label="R9")["loaded"][0]
        assert "no block labelled" in entry["error"]
        assert entry["available_labels"] == ["R1"]

    def test_section_returns_the_group(self, isolated_layers):
        _write(isolated_layers["store"], "s",
               _skill("s", body="## Instructions\n\n### I1 — Step\n\naaa\n\n"
                                "## Rules\n\n### R1 — Rule\n\nbbb\n"))
        entry = skills.load("s", section="Rules")["loaded"][0]
        assert "bbb" in entry["content"] and "aaa" not in entry["content"]

    def test_lessons_file_is_loadable_explicitly(self, isolated_layers):
        _write(isolated_layers["store"], "s", _skill("s"),
               "## Lessons\n\n### L1 — A lesson\n\nbody\n")
        entry = skills.load("s", file="LESSONS.md")["loaded"][0]
        assert "A lesson" in entry["content"]

    def test_references_come_back_with_the_block(self, isolated_layers):
        _write(isolated_layers["store"], "s",
               _skill("s", body="## Rules\n\n### R1 — R\n\nsee [[other#R2]]\n"))
        entry = skills.load("s", label="R1")["loaded"][0]
        assert entry["references"][0]["skill"] == "other"

    def test_index_of_is_the_cheap_orientation(self, isolated_layers):
        _write(isolated_layers["store"], "s",
               _skill("s", body="## Rules\n\n### R1 — A rule\n\nbody\n"))
        # The generated files carry a real index; a hand-written one may not, so
        # refresh before asserting on it.
        path = isolated_layers["store"] / "skills" / "s" / "SKILL.md"
        path.write_text(schema.refresh_index(path.read_text()))
        result = skills.index_of("s")
        assert result["status"] == "ok"
        assert result["index"][0]["label"] == "R1"


# ---------------------------------------------------------------------------
# Authoring
# ---------------------------------------------------------------------------

class TestAuthoring:
    def test_create_makes_a_schema_shaped_skill(self, isolated_layers):
        result = skills.create("new-subject", "A description long enough to be useful.",
                               subject="the new subject")
        assert result["status"] == "ok"
        parsed = schema.parse_skill(isolated_layers["store"] / "skills" / "new-subject")
        assert parsed["subject"] == "the new subject"
        assert "Index" in parsed["sections"]

    def test_association_requires_two_subjects(self, isolated_layers):
        result = skills.create("join", "d", kind="association", subjects=["only-one"])
        assert result["status"] == "error"
        assert "two subjects" in result["error"]

    def test_association_records_its_pair(self, isolated_layers):
        skills.create("a-on-b", "A description long enough to be useful.",
                      kind="association", subjects=["a", "b"])
        parsed = schema.parse_skill(isolated_layers["store"] / "skills" / "a-on-b")
        assert parsed["type"] == "association"
        assert parsed["subjects"] == ["a", "b"]

    def test_write_block_allocates_a_label_and_refreshes_the_index(self, isolated_layers):
        skills.create("s", "A description long enough to be useful.")
        first = skills.write_block("s", "rule", "Never do this", "because it breaks")
        second = skills.write_block("s", "rule", "Nor this", "same reason")
        assert (first["label"], second["label"]) == ("R1", "R2")
        assert first["reference"] == "[[s#R1]]"

        parsed = schema.parse_skill(isolated_layers["store"] / "skills" / "s")
        assert {row["label"] for row in parsed["index"]} == {"R1", "R2"}

    def test_instructions_and_rules_number_independently(self, isolated_layers):
        skills.create("s", "A description long enough to be useful.")
        assert skills.write_block("s", "instruction", "Step", "do it")["label"] == "I1"
        assert skills.write_block("s", "rule", "Constraint", "never")["label"] == "R1"

    def test_write_block_routes_a_lesson_kind_instead_of_rejecting(self, isolated_layers):
        """A lesson sent to the wrong tool is filed, not dropped.

        This asserted the opposite until a benchmark run showed what rejection
        costs: an agent recorded a real symptom-and-root-cause, got back an error
        naming the tool it should have used, did not retry, and the only piece of
        learning in the whole run was lost. Knowledge arriving through the wrong
        door is still knowledge.
        """
        result = skills.write_block("s", "lesson", "Title", "Body of the lesson.")
        assert result["status"] != "error", result
        assert result["routed_to"] == "LESSONS.md"
        lessons = isolated_layers["store"] / "skills" / "s" / "LESSONS.md"
        assert "Body of the lesson." in lessons.read_text()

    def test_write_block_still_rejects_an_unknown_kind(self, isolated_layers):
        result = skills.write_block("s", "nonsense", "t", "b")
        assert result["status"] == "error"
        assert "instruction|rule|reference" in result["error"]

    def test_write_block_redacts(self, isolated_layers):
        skills.create("s", "A description long enough to be useful.")
        skills.write_block("s", "rule", "Config path", "config lives at /home/someone/cfg")
        text = (isolated_layers["store"] / "skills" / "s" / "SKILL.md").read_text()
        assert "/home/someone" not in text and "$HOME/cfg" in text

    def test_duplicate_title_is_not_added_twice(self, isolated_layers):
        skills.create("s", "A description long enough to be useful.")
        skills.write_block("s", "rule", "Same title", "body")
        again = skills.write_block("s", "rule", "Same title", "body")
        assert again["status"] == "already_present"

    def test_write_block_reports_verification_coverage(self, isolated_layers):
        skills.create("s", "A description long enough to be useful.")
        result = skills.write_block("s", "rule", "T", "b")
        assert result["verification"]["covered"] is False
        assert "verify_new" in result["verification"]["next"]


class TestLessons:
    def test_lesson_goes_to_the_lessons_file(self, isolated_layers):
        result = skills.write_lesson("s", "symptom -> cause -> fix",
                                     description="A description long enough.")
        assert result["label"] == "L1"
        assert result["file"].endswith("LESSONS.md")
        skill_md = (isolated_layers["store"] / "skills" / "s" / "SKILL.md").read_text()
        assert "symptom -> cause -> fix" not in skill_md

    def test_pitfall_and_lesson_number_independently(self, isolated_layers):
        skills.write_lesson("s", "a trap", kind="pitfall", description="d long enough here")
        assert skills.write_lesson("s", "an incident", kind="lesson")["label"] == "L1"
        assert skills.write_lesson("s", "another trap", kind="pitfall")["label"] == "P2"

    def test_a_lesson_creates_the_skill_file_too(self, isolated_layers):
        """A LESSONS.md orphaned from any subject is unreachable by retrieval."""
        skills.write_lesson("brand-new", "a lesson", description="A description long enough.")
        directory = isolated_layers["store"] / "skills" / "brand-new"
        assert (directory / "SKILL.md").is_file()
        assert (directory / "LESSONS.md").is_file()

    def test_lesson_is_dated(self, isolated_layers):
        skills.write_lesson("s", "the thing broke", description="d long enough here",
                            when="2026-01-15")
        text = (isolated_layers["store"] / "skills" / "s" / "LESSONS.md").read_text()
        assert "**2026-01-15**" in text

    def test_lesson_is_redacted(self, isolated_layers):
        result = skills.write_lesson("s", "broke at /home/someone/x",
                                     description="d long enough here")
        assert result["redacted"]
        text = (isolated_layers["store"] / "skills" / "s" / "LESSONS.md").read_text()
        assert "/home/someone" not in text

    def test_duplicate_lesson_is_not_appended(self, isolated_layers):
        skills.write_lesson("s", "same text", description="d long enough here")
        assert skills.write_lesson("s", "same text")["status"] == "already_present"

    def test_writing_to_a_bundled_skill_forks_it_preserving_content(self, isolated_layers):
        """A shadow that dropped the bundled content would look like lost knowledge."""
        result = skills.write_lesson("phronix-privacy", "a project-specific note")
        assert result["action"] == "forked"
        assert result["layer"] == "project"
        skill_md = (isolated_layers["store"] / "skills" / "phronix-privacy" / "SKILL.md").read_text()
        assert "Keep the lesson, drop the provenance" in skill_md


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

class TestInstall:
    def test_symlinks_every_skill_into_the_harness_directories(self, isolated_layers):
        project = isolated_layers["project"]
        skills.install_skills(target_root=project)
        link = project / ".claude" / "skills" / "phronix-self-learning"
        assert link.is_symlink() and (link / "SKILL.md").is_file()
        assert (project / ".opencode" / "skills" / "phronix-privacy").is_symlink()

    def test_is_idempotent(self, isolated_layers):
        project = isolated_layers["project"]
        skills.install_skills(target_root=project)
        second = skills.install_skills(target_root=project)
        assert all(i["action"] == "already_installed" for i in second["installed"])

    def test_an_unrelated_existing_skill_is_namespaced_not_clobbered(self, isolated_layers):
        project = isolated_layers["project"]
        theirs = project / ".claude" / "skills" / "phronix-privacy"
        theirs.mkdir(parents=True)
        (theirs / "SKILL.md").write_text("the user's own skill")

        skills.install_skills(target_root=project)
        assert (theirs / "SKILL.md").read_text() == "the user's own skill"
        assert (project / ".claude" / "skills" / "phronix-phronix-privacy").is_symlink()

    def test_a_stale_link_is_repointed_when_a_higher_layer_shadows(self, isolated_layers):
        project = isolated_layers["project"]
        skills.install_skills(target_root=project)
        link = project / ".claude" / "skills" / "phronix-privacy"
        assert "src/phronix" in str(link.resolve())

        _write(isolated_layers["store"], "phronix-privacy", _skill("phronix-privacy"))
        skills.install_skills(target_root=project)
        assert str(link.resolve()).startswith(str(isolated_layers["store"]))


class TestRankingRegressions:
    """Ranking bugs found by end-to-end use. Each looked like a plausible answer,
    which is what makes them worth pinning: a wrong result that looks right is
    more expensive than no result."""

    def test_the_section_column_is_not_scored(self, isolated_layers):
        """`section` holds one of three fixed values, so scoring it made any query
        containing "reference" or "rule" match every skill in the library."""
        _write(isolated_layers["store"], "unrelated",
               _skill("unrelated", description="a subject about frobnication",
                      subject="frobnication",
                      body="## Index\n\n| Label | Section | Covers |\n| --- | --- | --- |\n"
                           "| `X1` | References | see elsewhere |\n\n"
                           "## References\n\n### X1 — See\n\nelsewhere\n"))
        result = skills.search("reference")
        assert all(r["skill"] != "unrelated" for r in result.get("results", []))

    def test_a_lesson_is_found_by_its_symptom_text(self, isolated_layers):
        """An error message appears in no index; gating lessons on the index made
        exactly the most valuable entry unreachable."""
        _write(isolated_layers["store"], "workload-thing",
               _skill("workload-thing", description="building the thing from source",
                      subject="building the thing"),
               "## Pitfalls\n\n### P1 — undefined reference to pthread_create\n\n"
               "-lpthread was placed before the objects\n")
        result = skills.search("pthread_create undefined reference",
                               kinds=["pitfall", "lesson"])
        assert result["results"][0]["skill"] == "workload-thing"
        assert result["results"][0]["blocks"][0]["label"] == "P1"

    def test_a_weak_index_match_does_not_suppress_the_lesson_fallback(self, isolated_layers):
        """The trigger is "no usable blocks", not "no index match" — otherwise one
        unrelated description match returns results with no content in them."""
        _write(isolated_layers["store"], "decoy",
               _skill("decoy", description="a subject mentioning pthread in passing",
                      subject="decoys",
                      body="## Rules\n\n### R1 — Unrelated\n\nnothing useful\n"))
        _write(isolated_layers["store"], "real",
               _skill("real", description="something else entirely", subject="reality"),
               "## Pitfalls\n\n### P1 — pthread_create fails\n\nthe real answer\n")
        result = skills.search("pthread_create", kinds=["pitfall", "lesson"])
        assert result["results"][0]["skill"] == "real"

    def test_results_without_matching_blocks_are_not_returned_for_lessons(self, isolated_layers):
        _write(isolated_layers["store"], "empty-lessons",
               _skill("empty-lessons", description="a subject about widgets",
                      subject="widgets"))
        result = skills.search("widgets", kinds=["pitfall", "lesson"])
        assert result["status"] == "no_match" or all(
            r["blocks"] for r in result.get("results", []))
