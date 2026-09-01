"""End-to-end: bootstrap a project, then verify the loop actually closes.

The single most important assertion in this file is
``test_learning_lands_in_the_committed_project_layer``. Everything else in
phronix exists to make that true — if a lesson written during a session does not
end up in a file the next clone will see, the framework has failed at its one
job, however well the individual pieces work.
"""
from __future__ import annotations

import json

from phronix import agents, bootstrap, capabilities, memory, permissions, skills


class TestBootstrap:
    def test_creates_the_layer_and_wires_the_instructions(self, isolated_layers):
        project = isolated_layers["project"]
        result = bootstrap.ensure_workspace_setup(project, link_memory=False)
        assert result["status"] == "installed"

        for kind in ("skills", "agents", "memory", "capabilities"):
            assert (project / ".phronix" / kind).is_dir()
        assert (project / ".phronix" / "README.md").is_file()

        for name in ("CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md"):
            text = (project / name).read_text()
            assert bootstrap.BLOCK_START in text and bootstrap.BLOCK_END in text

    def test_preserves_a_projects_own_instructions(self, isolated_layers):
        project = isolated_layers["project"]
        (project / "CLAUDE.md").write_text("# Our rules\n\nDo not touch this.\n")
        bootstrap.ensure_workspace_setup(project, link_memory=False)
        text = (project / "CLAUDE.md").read_text()
        assert "Do not touch this." in text
        assert bootstrap.BLOCK_START in text

    def test_refreshes_its_block_without_duplicating_it(self, isolated_layers):
        project = isolated_layers["project"]
        bootstrap.ensure_workspace_setup(project, link_memory=False)
        bootstrap.ensure_workspace_setup(project, link_memory=False)
        assert (project / "CLAUDE.md").read_text().count(bootstrap.BLOCK_START) == 1

    def test_memory_link_migrates_files_already_written_by_the_harness(self, isolated_layers, tmp_path, monkeypatch):
        """Those files are the whole point; refusing on a non-empty directory loses them."""
        monkeypatch.setattr(bootstrap.Path, "home", staticmethod(lambda: tmp_path / "fakehome"))
        project = isolated_layers["project"]
        harness_dir = bootstrap.claude_memory_dir(project)
        harness_dir.mkdir(parents=True)
        (harness_dir / "existing.md").write_text("written by the harness")

        bootstrap.ensure_workspace_setup(project, link_memory=True)
        assert harness_dir.is_symlink()
        assert (project / ".phronix" / "memory" / "existing.md").read_text() == "written by the harness"


class TestRenderAndInstall:
    def test_agents_render_for_every_harness(self, isolated_layers):
        project = isolated_layers["project"]
        result = agents.install_agents(target_root=project)
        assert not result["conflicts"]
        for path in (".claude/agents/phronix-router.md",
                     ".opencode/agents/phronix-router.md",
                     ".github/agents/phronix-router.agent.md",
                     ".codex/agents/phronix-router.toml"):
            assert (project / path).is_file()

    def test_rerendering_is_a_no_op(self, isolated_layers):
        project = isolated_layers["project"]
        agents.install_agents(target_root=project)
        second = agents.sync_agents(target_root=project)
        assert second["changed"] == []

    def test_a_users_own_agent_file_is_never_overwritten(self, isolated_layers):
        project = isolated_layers["project"]
        theirs = project / ".claude" / "agents" / "phronix-router.md"
        theirs.parent.mkdir(parents=True)
        theirs.write_text("hand-written by the user")
        result = agents.install_agents(target_root=project)
        assert str(theirs) in result["conflicts"]
        assert theirs.read_text() == "hand-written by the user"

    def test_a_stale_rendered_file_is_refreshed(self, isolated_layers):
        project = isolated_layers["project"]
        agents.install_agents(target_root=project)
        target = project / ".claude" / "agents" / "phronix-router.md"
        target.write_text("# generated-by: phronix (claude)\nstale\n")
        result = agents.sync_agents(target_root=project)
        assert any(i["name"] == "phronix-router.md" and i["action"] == "refreshed"
                   for i in result["installed"])


class TestPermissions:
    def test_mcp_tools_are_discovered_not_hand_listed(self, isolated_layers):
        names = permissions.discover_mcp_tool_names()
        assert {"skill_write", "memory_write", "graph_query", "capability_new"} <= set(names)

    def test_claude_render_denies_and_allows_correctly(self, isolated_layers):
        rendered = permissions.render_claude(permissions.load_policy())
        assert "Bash(sudo *)" in rendered["deny"]
        assert "Write(/etc/*)" in rendered["deny"]
        # Claude's dialect is a single trailing star — see TestPermissionDialects.
        assert "Edit(.phronix/*)" in rendered["allow"]
        assert "mcp__phronix__skill_write" in rendered["allow"]
        # The "**": ask catch-all is Claude's own default; emitting it changes nothing.
        assert not any(rule.endswith("(**)") for rule in rendered["allow"] + rendered["deny"])

    def test_opencode_render_puts_the_catch_all_first(self, isolated_layers):
        """Last match wins there; the reverse order silently collapses the policy."""
        rendered = permissions.render_opencode(permissions.load_policy())
        edit_globs = list(rendered["edit"])
        assert edit_globs[0] == "**"
        assert edit_globs[-1] == ".phronix/**"
        assert rendered["edit"][".phronix/**"] == "allow"

    def test_syncing_preserves_unrelated_settings_keys(self, isolated_layers):
        project = isolated_layers["project"]
        settings = project / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"env": {"MY_VAR": "1"}}))
        permissions.sync_permissions(project)
        data = json.loads(settings.read_text())
        assert data["env"] == {"MY_VAR": "1"}
        assert "permissions" in data


class TestCapabilities:
    def test_a_valid_capability_is_saved_and_loads(self, isolated_layers):
        source = (
            "def register(mcp):\n"
            "    @mcp.tool()\n"
            "    def echo(text: str) -> str:\n"
            '        """Echo text."""\n'
            "        return text\n"
        )
        result = capabilities.new("echo_tool", "Echo things.", source=source)
        assert result["status"] == "ok"
        assert result["layer"] == "project"

        registered = []

        class FakeMCP:
            def tool(self):
                def decorate(fn):
                    registered.append(fn.__name__)
                    return fn
                return decorate

        loaded = capabilities.load_all(FakeMCP())
        assert loaded["failed"] == []
        assert "echo_tool" in loaded["loaded"]
        assert registered == ["echo"]

    def test_a_module_without_register_is_rejected_before_it_is_saved(self, isolated_layers):
        result = capabilities.new("bad", "d", source="x = 1\n")
        assert result["status"] == "error"
        assert "register(mcp)" in result["error"]
        assert not (isolated_layers["store"] / "capabilities" / "bad.py").exists()

    def test_a_syntax_error_is_rejected_before_it_is_saved(self, isolated_layers):
        result = capabilities.new("bad", "d", source="def register(mcp):\n  (\n")
        assert result["status"] == "error"
        assert "syntax error" in result["error"]

    def test_the_scaffold_is_itself_valid(self, isolated_layers):
        result = capabilities.new("scaffolded", "A scaffolded tool.")
        assert result["status"] == "ok" and result["scaffolded"]

    def test_a_broken_capability_does_not_take_down_the_others(self, isolated_layers):
        """A self-building system whose own learning can brick it is worse than one that learns nothing."""
        directory = isolated_layers["store"] / "capabilities"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "good.py").write_text("def register(mcp):\n    pass\n")
        (directory / "broken.py").write_text("def register(mcp):\n    raise RuntimeError('boom')\n")

        loaded = capabilities.load_all(object())
        assert "good" in loaded["loaded"]
        assert [f["name"] for f in loaded["failed"]] == ["broken"]
        assert "boom" in loaded["failed"][0]["error"]

    def test_names_must_be_snake_case(self, isolated_layers):
        assert capabilities.new("Bad-Name", "d")["status"] == "error"


def test_learning_lands_in_the_committed_project_layer(isolated_layers):
    """The whole promise: what a session learns is inherited by the next clone.

    Not "is written somewhere" — written to a path INSIDE the repository, so it is
    committed with the code it is about. A lesson stranded in site-packages or in
    an untracked home directory is a lesson the next person never sees.
    """
    project = isolated_layers["project"]
    bootstrap.ensure_workspace_setup(project, link_memory=False)

    skills.write_lesson("workload-thing", "symptom -> cause -> fix",
                        description="Lessons for thing.")
    memory.write("project-state", "Where the work stands.", "Body.")
    capabilities.new("helper", "A helper.", source="def register(mcp):\n    pass\n")

    # An answer, so it lands under capabilities; `skills/` holds only method.
    for path in (".phronix/capabilities/skills/workload-thing/SKILL.md",
                 ".phronix/memory/project-state.md",
                 ".phronix/memory/MEMORY.md",
                 # Never loose at the top of the tree: the `--fresh` filter
                 # keys on the directory, so a loose capability is served to
                 # every from-scratch run for good.
                 ".phronix/capabilities/tools/general/helper.py"):
        full = project / path
        assert full.is_file(), f"{path} was not written into the project layer"
        assert not full.is_symlink(), f"{path} must be a real file, not a link out of the repo"

    # And a fresh read finds them through the merged view.
    assert "workload-thing" in {s["name"] for s in skills.iter_skills()}
    assert "project-state" in {m["name"] for m in memory.listing()}
    assert "helper" in {c["name"] for c in capabilities.listing()}


class TestToolDiscovery:
    """Discovery drives the permission allowlist, so a phantom entry pre-approves
    a tool that does not exist — wrong, and silent, because it never fails."""

    def test_a_docstring_example_is_not_counted_as_a_tool(self, isolated_layers):
        from phronix.permissions import _tool_names_in

        source = (
            'def register(mcp):\n'
            '    @mcp.tool()\n'
            '    def real_tool() -> str:\n'
            '        """Shows how to write one::\n\n'
            '            @mcp.tool()\n'
            '            def example_from_the_docs() -> str: ...\n'
            '        """\n'
            '        return "x"\n'
        )
        assert _tool_names_in(source) == ["real_tool"]

    def test_the_mounted_subservice_form_is_recognised(self):
        from phronix.permissions import _tool_names_in

        source = ("class S:\n"
                  "    def r(self):\n"
                  "        @self.sub.tool()\n"
                  "        def mounted() -> str: ...\n")
        assert _tool_names_in(source) == ["mounted"]

    def test_a_broken_file_still_contributes_what_it_can(self):
        from phronix.permissions import _tool_names_in

        source = "@mcp.tool()\ndef survivor():\n    (\n"
        assert _tool_names_in(source) == ["survivor"]

    def test_the_bundled_roster_has_no_phantoms(self, isolated_layers):
        from phronix.permissions import discover_mcp_tool_names

        names = discover_mcp_tool_names()
        assert "count_todos" not in names, "a docstring example leaked into the allowlist"
        assert {"skill_define", "agent_define", "verify_run", "complexity_assess"} <= set(names)


class TestPermissionDialects:
    """Each harness spells the same policy differently, and each difference here
    is one that fails SILENTLY when got wrong — a rule that is present, reads
    correctly, and never fires."""

    def test_claude_uses_a_single_trailing_star(self, isolated_layers):
        """Claude's dialect is `/*`; the policy and OpenCode use `/**`. Without
        the conversion `Edit(.phronix/**)` matches nothing at all."""
        rendered = permissions.render_claude(permissions.load_policy())
        assert "Edit(.phronix/*)" in rendered["allow"]
        assert not any(r.endswith("/**)") for r in rendered["allow"] + rendered["deny"])

    def test_claude_glob_conversion_is_exact(self):
        assert permissions._claude_glob(".phronix/**") == ".phronix/*"
        assert permissions._claude_glob("**") == "**"
        assert permissions._claude_glob("src/x.py") == "src/x.py"

    def test_opencode_orders_the_catch_all_first(self, isolated_layers):
        """Last match wins there; the reverse order collapses the whole policy
        into "ask for everything"."""
        rendered = permissions.render_opencode(permissions.load_policy())
        assert list(rendered["edit"])[0] == "**"
        assert list(rendered["edit"])[-1] == ".phronix/**"

    def test_opencode_puts_deny_after_allow_in_bash(self, isolated_layers):
        rendered = permissions.render_opencode(permissions.load_policy())
        keys = list(rendered["bash"])
        assert keys.index("sudo *") > keys.index("ls *")
        assert rendered["bash"]["sudo *"] == "deny"

    def test_read_is_allow_only_not_tiered(self, isolated_layers):
        """Reads are allow-by-default in OpenCode; rendering the ask catch-all
        would make every read of the project's own source prompt."""
        rendered = permissions.render_opencode(permissions.load_policy())
        assert "**" not in rendered["read"]
        assert rendered["read"][".phronix/**"] == "allow"

    def test_glob_and_grep_are_not_path_scoped(self, isolated_layers):
        """They ask with the SEARCH pattern, never a path, so a path glob there
        would be coverage we do not actually have."""
        rendered = permissions.render_opencode(permissions.load_policy())
        assert "glob" not in rendered and "grep" not in rendered

    def test_an_invalid_coverage_mode_is_loud(self, isolated_layers):
        import pytest

        policy = {"paths": [{"glob": "**", "mode": "ask"}],
                  "path_scoped_tools": {"edit": "nonsense"}}
        with pytest.raises(ValueError, match="tiers"):
            permissions.render_opencode(policy)

    def test_mcp_tools_render_per_dialect(self, isolated_layers):
        policy = permissions.load_policy()
        claude = permissions.render_claude(policy)
        opencode = permissions.render_opencode(policy)
        assert any(r.startswith("mcp__phronix__") for r in claude["allow"])
        # OpenCode ids tools as sanitize(server)_sanitize(tool); one glob covers all.
        assert opencode["phronix_*"] == "allow"
        assert not any(k.startswith("mcp__") for k in opencode)

    def test_an_explicit_tool_list_is_honoured_in_both(self, isolated_layers):
        policy = {"paths": [], "mcp_tools": ["mcp__phronix__skill_load"]}
        assert "mcp__phronix__skill_load" in permissions.render_claude(policy)["allow"]
        assert permissions.render_opencode(policy)["phronix_skill_load"] == "allow"

    def test_privilege_escalation_is_denied(self, isolated_layers):
        rendered = permissions.render_claude(permissions.load_policy())
        for rule in ("Bash(sudo *)", "Bash(su *)", "Bash(curl * | sh)"):
            assert rule in rendered["deny"], rule

    def test_writes_outside_the_project_are_denied(self, isolated_layers):
        rendered = permissions.render_claude(permissions.load_policy())
        for prefix in ("/etc", "/usr", "/var", "/root", "/home"):
            assert f"Write({prefix}/*)" in rendered["deny"]

    def test_copilot_and_codex_are_reported_not_applicable(self, isolated_layers):
        result = permissions.sync_permissions(isolated_layers["project"])
        assert result["copilot"] == "not_applicable"
        assert result["codex"] == "not_applicable"
