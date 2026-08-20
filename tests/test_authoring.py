"""Declarative authoring: idempotency, label stability, and reference protection.

Idempotency is the property the whole tool exists for — an agent unsure whether a
call took effect must be able to just run it again. Every test that pins it is
guarding against a regression that would silently turn "re-run safely" into
"re-run appends".
"""
from __future__ import annotations

from pathlib import Path

from phronix import agents, skills

SPEC = dict(
    name="deploy-service",
    description="Shipping the service to production, including canary rollout and rollback.",
    subject="deploying the service",
    instructions=[{"title": "Build the image", "body": "Run make image."},
                  {"title": "Canary first", "body": "Five percent before the fleet."}],
    rules=[{"title": "Never deploy on Friday", "body": "Nobody is around to roll back."}],
    references=[{"title": "Redaction before logs ship", "body": "See [[phronix-privacy#R1]]."}],
)


def _skill_path(store, name="deploy-service"):
    return store / "skills" / name / "SKILL.md"


class TestSkillDefineIdempotency:
    def test_second_identical_call_writes_nothing(self, isolated_layers):
        first = skills.define(**SPEC)
        assert first["action"] == "created"
        before = _skill_path(isolated_layers["store"]).read_bytes()

        second = skills.define(**SPEC)
        assert second["action"] == "unchanged"
        assert second["files_written"] == []
        assert _skill_path(isolated_layers["store"]).read_bytes() == before

    def test_label_numbering_is_history_dependent_by_design(self, isolated_layers):
        """Label stability and history independence cannot both hold; stability wins.

        Numbering above what a prior definition used is what keeps an existing
        `[[skill#R1]]` pointing at the same content. The cost is that defining over
        an unrelated earlier skill numbers differently than defining into an empty
        directory — and `label` pinning is the escape hatch when that matters.
        """
        skills.define(name="deploy-service", description="Something else entirely here.",
                      subject="something else",
                      rules=[{"title": "Old rule", "body": "old body"}])
        over_existing = skills.define(**SPEC)
        assert over_existing["labels"]["R2"] == "Never deploy on Friday"

        import shutil

        shutil.rmtree(isolated_layers["store"] / "skills" / "deploy-service")
        assert skills.define(**SPEC)["labels"]["R1"] == "Never deploy on Friday"

    def test_pinned_labels_make_it_history_independent(self, isolated_layers):
        pinned = {**SPEC, "rules": [{"label": "R1", **SPEC["rules"][0]}]}
        skills.define(name="deploy-service", description="Something else entirely here.",
                      subject="something else",
                      rules=[{"title": "Old rule", "body": "old body"}])
        skills.define(**pinned)
        over_existing = _skill_path(isolated_layers["store"]).read_text()

        import shutil

        shutil.rmtree(isolated_layers["store"] / "skills" / "deploy-service")
        skills.define(**pinned)
        assert _skill_path(isolated_layers["store"]).read_text() == over_existing

    def test_sections_are_emitted_in_a_fixed_order(self, isolated_layers):
        skills.define(**SPEC)
        text = _skill_path(isolated_layers["store"]).read_text()
        assert text.index("## Index") < text.index("## Instructions")
        assert text.index("## Instructions") < text.index("## Rules")
        assert text.index("## Rules") < text.index("## References")

    def test_the_index_is_generated_from_the_blocks(self, isolated_layers):
        skills.define(**SPEC)
        text = _skill_path(isolated_layers["store"]).read_text()
        for label, title in (("I1", "Build the image"), ("R1", "Never deploy on Friday"),
                             ("X1", "Redaction before logs ship")):
            assert f"| `{label}` |" in text and title in text

    def test_a_removed_block_is_actually_removed(self, isolated_layers):
        skills.define(**SPEC)
        skills.define(**{**SPEC, "instructions": [SPEC["instructions"][0]]})
        text = _skill_path(isolated_layers["store"]).read_text()
        assert "Canary first" not in text
        assert "| `I2` |" not in text


class TestLabelStability:
    def test_editing_a_body_does_not_renumber(self, isolated_layers):
        first = skills.define(**SPEC)
        edited = skills.define(**{
            **SPEC,
            "rules": [{"title": "Never deploy on Friday", "body": "Different body now."}],
        })
        assert edited["labels"]["R1"] == "Never deploy on Friday"
        assert first["labels"]["I2"] == edited["labels"]["I2"]

    def test_an_explicit_label_is_honoured(self, isolated_layers):
        result = skills.define(**{
            **SPEC,
            "rules": [{"label": "R7", "title": "Pinned", "body": "b"}],
        })
        assert "R7" in result["labels"]

    def test_a_new_block_gets_a_fresh_number(self, isolated_layers):
        skills.define(**SPEC)
        result = skills.define(**{
            **SPEC,
            "rules": [*SPEC["rules"], {"title": "Second rule", "body": "b"}],
        })
        assert result["labels"]["R2"] == "Second rule"

    def test_inserting_at_the_top_does_not_shift_existing_labels(self, isolated_layers):
        """Positional numbering would renumber everything below and break references."""
        skills.define(**SPEC)
        result = skills.define(**{
            **SPEC,
            "instructions": [{"title": "New first step", "body": "b"}, *SPEC["instructions"]],
        })
        assert result["labels"]["I1"] == "Build the image"
        assert result["labels"]["I2"] == "Canary first"
        assert result["labels"]["I3"] == "New first step"


class TestReferenceProtection:
    def _cite(self):
        skills.define(name="oncall-rotation",
                      description="Who is on call and what they are expected to cover.",
                      subject="the on-call rotation",
                      rules=[{"title": "Weekend coverage",
                              "body": "Related: [[deploy-service#R1]]."}])

    def test_dropping_a_cited_label_is_refused(self, isolated_layers):
        skills.define(**SPEC)
        self._cite()
        result = skills.define(**{**SPEC, "rules": []})
        assert result["status"] == "would_break_references"
        assert "R1" in result["dropped_labels"]
        assert result["referenced_by"][0]["from"] == "oncall-rotation"

    def test_allow_relabel_overrides_the_refusal(self, isolated_layers):
        skills.define(**SPEC)
        self._cite()
        result = skills.define(**{**SPEC, "rules": [], "allow_relabel": True})
        assert result["status"] == "ok"

    def test_dropping_an_uncited_label_is_allowed(self, isolated_layers):
        skills.define(**SPEC)
        assert skills.define(**{**SPEC, "rules": []})["status"] == "ok"

    def test_omitting_lessons_does_not_count_as_dropping_them(self, isolated_layers):
        """Recorded lessons are the most expensive content to reproduce."""
        skills.define(**{**SPEC, "pitfalls": [{"title": "A trap", "body": "avoid it"}]})
        result = skills.define(**SPEC)
        assert result["status"] == "ok"
        lessons = isolated_layers["store"] / "skills" / "deploy-service" / "LESSONS.md"
        assert "A trap" in lessons.read_text()


class TestSkillDefineValidation:
    def test_a_skill_with_no_instructions_or_rules_is_refused(self, isolated_layers):
        result = skills.define(name="empty", description="A description long enough here.")
        assert result["status"] == "error"
        assert "instruction or rule" in result["error"]

    def test_an_association_needs_two_subjects(self, isolated_layers):
        result = skills.define(name="join", description="A description long enough here.",
                               kind="association", subjects=["only-one"],
                               rules=[{"title": "t", "body": "b"}])
        assert result["status"] == "error"

    def test_an_association_records_its_pair(self, isolated_layers):
        skills.define(name="a-on-b", description="A description long enough here.",
                      kind="association", subjects=["phronix-privacy", "phronix-memory"],
                      rules=[{"title": "Combined rule", "body": "b"}])
        text = _skill_path(isolated_layers["store"], "a-on-b").read_text()
        assert "type: association" in text
        assert "subjects: phronix-privacy, phronix-memory" in text

    def test_content_is_redacted(self, isolated_layers):
        skills.define(**{**SPEC,
                         "rules": [{"title": "Paths", "body": "config at /home/someone/x"}]})
        text = _skill_path(isolated_layers["store"]).read_text()
        assert "/home/someone" not in text and "$HOME/x" in text

    def test_the_structural_corrector_verdict_comes_back(self, isolated_layers):
        result = skills.define(**SPEC)
        assert result["corrector"]["status"] == "pass"
        assert result["corrector"]["findings"] == []


class TestAgentDefine:
    SECTIONS = [{"title": "What you do", "body": "Drive a deployment."},
                {"include": "predictor-corrector"}]

    def _define(self, **overrides):
        kwargs = dict(
            name="deploy-runner",
            description="Runs a production deployment end to end; use when shipping a release.",
            model_level="level_3",
            sections=self.SECTIONS,
            tools=["Read", "Bash"],
            skills=["phronix-verification"],
            sync=False,
        )
        kwargs.update(overrides)
        return agents.define_agent(**kwargs)

    def test_second_identical_call_writes_nothing(self, isolated_layers):
        first = self._define()
        assert first["action"] == "created"
        path = Path(first["file"])
        before = path.read_bytes()
        assert self._define()["action"] == "unchanged"
        assert path.read_bytes() == before

    def test_key_order_is_fixed(self, isolated_layers):
        text = Path(self._define()["file"]).read_text()
        order = [text.index(f"{k}:") for k in
                 ("name", "description", "model_level", "tools", "skills", "sections")]
        assert order == sorted(order)

    def test_the_written_template_loads_back(self, isolated_layers):
        """A template that writes but does not load looks successful and breaks the sync."""
        from phronix.agent_templates import load_common_sections, load_template

        loaded = load_template(Path(self._define()["file"]), load_common_sections())
        assert loaded["name"] == "deploy-runner"
        assert any("corrector" in s["body"].lower() for s in loaded["sections"])

    def test_a_pinned_model_id_is_refused(self, isolated_layers):
        result = self._define(model_level="opus")
        assert result["status"] == "error" and "model_level" in result["error"]

    def test_an_unknown_include_is_refused_before_writing(self, isolated_layers):
        result = self._define(sections=[{"include": "no-such-section"}])
        assert result["status"] == "error"
        assert "unknown shared section" in result["error"]

    def test_a_nonexistent_skill_is_refused(self, isolated_layers):
        result = self._define(skills=["no-such-skill"])
        assert result["status"] == "error"
        assert "do not exist" in result["error"]

    def test_no_sections_is_refused(self, isolated_layers):
        assert self._define(sections=[])["status"] == "error"

    def test_the_structural_corrector_verdict_comes_back(self, isolated_layers):
        assert self._define()["corrector"]["status"] == "pass"

    def test_it_renders_for_every_harness_when_synced(self, isolated_layers):
        result = self._define(sync=True)
        assert result["sync"]["summary"]
        project = isolated_layers["project"]
        for path in (".claude/agents/deploy-runner.md",
                     ".opencode/agents/deploy-runner.md",
                     ".github/agents/deploy-runner.agent.md",
                     ".codex/agents/deploy-runner.toml"):
            assert (project / path).is_file(), path
