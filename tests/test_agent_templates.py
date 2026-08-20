"""Agent rendering: the four harness dialects, and the include mechanism.

The dialect assertions look pedantic and are not. Each one encodes a difference
that is easy to get wrong and silent when wrong: an OpenCode ``tools:`` key that
should be ``permission:`` is simply ignored, leaving an agent with no boundary at
all; a Codex file with a ``tools`` key advertises a permission model Codex does
not have.
"""
from __future__ import annotations

import pytest
import yaml

from phronix import agent_templates as at


@pytest.fixture
def rendered(isolated_layers):
    return at.render_all(target_root=isolated_layers["project"])


class TestIncludes:
    def test_bundled_templates_all_load(self, isolated_layers):
        """A typo in an `include:` breaks rendering for every harness at once."""
        templates = at.load_all_templates()
        assert {t["name"] for t in templates} >= {"phronix-router", "phronix-learner"}
        for template in templates:
            assert all(s["body"].strip() for s in template["sections"])

    def test_unknown_include_is_a_loud_error(self, isolated_layers, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(yaml.safe_dump({
            "name": "bad", "description": "d", "model_level": "level_1",
            "sections": [{"include": "no-such-section"}],
        }))
        with pytest.raises(at.TemplateError, match="unknown common section"):
            at.load_template(path)

    def test_project_common_sections_merge_over_bundled(self, isolated_layers):
        """Key-by-key, so adding one section does not drop the bundled library."""
        agents = isolated_layers["store"] / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        (agents / "common-sections.yaml").write_text(yaml.safe_dump({
            "sections": {"privacy": {"title": "Our privacy rule", "body": "project text"}}
        }))
        common = at.load_common_sections()
        assert common["privacy"]["body"] == "project text"
        assert "self-learning" in common  # bundled entries survived

    def test_model_level_must_be_well_formed(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(yaml.safe_dump({
            "name": "bad", "description": "d", "model_level": "opus",
            "sections": [{"title": "t", "body": "b"}],
        }))
        with pytest.raises(at.TemplateError, match="model_level"):
            at.load_template(path, common={})


class TestDialects:
    def test_claude_uses_a_model_class_and_a_comma_string(self, rendered):
        text = rendered["claude"][".claude/agents/phronix-router.md"]
        fields = yaml.safe_load(text.split("---\n")[1])
        assert fields["model"] in ("haiku", "sonnet", "opus")
        assert isinstance(fields["tools"], str) and ", " in fields["tools"]
        assert isinstance(fields["skills"], str)

    def test_opencode_denies_all_then_allows_the_listed_tools(self, rendered):
        text = rendered["opencode"][".opencode/agents/phronix-router.md"]
        fields = yaml.safe_load(text.split("---\n")[1])
        assert fields["mode"] == "subagent"
        assert fields["permission"]["*"] == "deny"
        assert fields["permission"]["phronix_skill_search"] == "allow"
        assert fields["permission"]["read"] == "allow"
        assert "tools" not in fields

    def test_copilot_uses_a_tool_list_with_slash_separated_mcp_names(self, rendered):
        text = rendered["copilot"][".github/agents/phronix-router.agent.md"]
        fields = yaml.safe_load(text.split("---\n")[1])
        assert isinstance(fields["tools"], list)
        assert "phronix/skill_search" in fields["tools"]

    def test_codex_emits_toml_without_a_tools_key(self, rendered):
        """Codex has no per-tool allow/deny; a tools key would imply one exists."""
        text = rendered["codex"][".codex/agents/phronix-router.toml"]
        assert text.startswith("# generated-by: phronix (codex)")
        assert "developer_instructions = \"\"\"" in text
        assert 'sandbox_mode = "workspace-write"' in text
        assert "\ntools = " not in text

    def test_every_harness_renders_every_template(self, rendered):
        counts = {h: len(files) for h, files in rendered.items()}
        assert len(set(counts.values())) == 1
        assert counts["claude"] >= 6


class TestSkillPreamble:
    def test_present_for_harnesses_without_a_skills_key(self, rendered):
        for harness, path in (("opencode", ".opencode/agents/phronix-router.md"),
                              ("copilot", ".github/agents/phronix-router.agent.md")):
            assert "Locate your skills via the graph first" in rendered[harness][path]

    def test_absent_for_claude_which_loads_skills_natively(self, rendered):
        text = rendered["claude"][".claude/agents/phronix-router.md"]
        assert "Locate your skills via the graph first" not in text


class TestTomlEscaping:
    def test_quotes_and_backslashes_survive(self):
        """Backslashes must be escaped FIRST or quote-escaping is re-escaped."""
        out = at._toml_multiline('say "hi" \\ there')
        assert out == '"""\nsay \\"hi\\" \\\\ there"""'

    def test_a_triple_quote_in_the_body_does_not_terminate_the_string(self):
        assert '\\"\\"\\"' in at._toml_multiline('a """ b')


class TestGenerationMarker:
    def test_every_rendered_file_is_stamped(self, rendered):
        """The marker is how the installer tells our file from a user's own."""
        for files in rendered.values():
            for content in files.values():
                assert "# generated-by: phronix" in content
