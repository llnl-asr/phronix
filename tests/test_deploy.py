"""Deployment: idempotency, drift detection, and not clobbering the user's files.

`deploy` runs against somebody else's repository, so the two things that matter
are that re-running changes nothing and that it never destroys content it did not
write. `--check` exists to gate CI, which makes a false positive expensive: a
check that reports drift on an up-to-date tree gets disabled within a week.
"""
from __future__ import annotations

import json

from phronix.cli import main as cli


def _deploy(project, *extra, capsys=None):
    argv = ["deploy", "--target", str(project), "--no-link-memory", *extra]
    return cli(argv)


class TestIdempotency:
    def test_a_fresh_project_reports_changes(self, isolated_layers, capsys):
        assert _deploy(isolated_layers["project"]) == 0
        assert "Deployed" in capsys.readouterr().out

    def test_the_second_run_changes_nothing(self, isolated_layers, capsys):
        _deploy(isolated_layers["project"])
        capsys.readouterr()
        assert _deploy(isolated_layers["project"]) == 0
        out = capsys.readouterr().out
        assert "Already current" in out
        assert "change(s)" not in out

    def test_every_step_reports_up_to_date_on_a_repeat(self, isolated_layers, capsys):
        _deploy(isolated_layers["project"])
        capsys.readouterr()
        _deploy(isolated_layers["project"], "--json")
        report = json.loads(capsys.readouterr().out)
        assert report["changed"] == 0
        assert all(v == [] for v in report["changes"].values())

    def test_it_produces_the_full_workspace(self, isolated_layers):
        project = isolated_layers["project"]
        _deploy(project)
        for path in (".phronix/skills", ".phronix/verifiers",
                     ".claude/agents/phronix-router.md",
                     ".opencode/agents/phronix-router.md",
                     ".github/agents/phronix-router.agent.md",
                     ".codex/agents/phronix-router.toml",
                     ".claude/skills/phronix-self-learning",
                     ".claude/settings.json", ".mcp.json",
                     ".claude/hooks/phronix_context_hook.py",
                     "CLAUDE.md", "AGENTS.md"):
            assert (project / path).exists(), path


class TestCheckMode:
    def test_check_on_a_fresh_project_reports_drift(self, isolated_layers, capsys):
        assert _deploy(isolated_layers["project"], "--check") == 1
        assert "Out of date" in capsys.readouterr().out

    def test_check_writes_nothing(self, isolated_layers):
        project = isolated_layers["project"]
        _deploy(project, "--check")
        assert not (project / ".claude").exists()

    def test_check_on_a_deployed_project_is_clean(self, isolated_layers, capsys):
        project = isolated_layers["project"]
        _deploy(project)
        capsys.readouterr()
        assert _deploy(project, "--check") == 0
        assert "Up to date" in capsys.readouterr().out

    def test_check_detects_a_deleted_artifact(self, isolated_layers, capsys):
        project = isolated_layers["project"]
        _deploy(project)
        (project / ".claude" / "agents" / "phronix-router.md").unlink()
        capsys.readouterr()
        assert _deploy(project, "--check") == 1
        assert "phronix-router.md" in capsys.readouterr().out

    def test_check_clears_after_a_repair(self, isolated_layers, capsys):
        project = isolated_layers["project"]
        _deploy(project)
        (project / ".claude" / "agents" / "phronix-router.md").unlink()
        _deploy(project)
        capsys.readouterr()
        assert _deploy(project, "--check") == 0


class TestSafety:
    def test_a_projects_own_instructions_survive(self, isolated_layers):
        project = isolated_layers["project"]
        (project / "CLAUDE.md").write_text("# Ours\n\nDo not touch this line.\n")
        _deploy(project)
        assert "Do not touch this line." in (project / "CLAUDE.md").read_text()

    def test_an_unrelated_agent_file_is_reported_not_overwritten(self, isolated_layers, capsys):
        project = isolated_layers["project"]
        theirs = project / ".claude" / "agents" / "phronix-router.md"
        theirs.parent.mkdir(parents=True)
        theirs.write_text("hand-written")
        _deploy(project)
        assert theirs.read_text() == "hand-written"
        assert "left alone" in capsys.readouterr().out

    def test_a_failing_step_does_not_abort_the_others(self, isolated_layers, capsys, monkeypatch):
        """A partial deploy is recoverable; a deploy that stops at step two is not."""
        import phronix.permissions as permissions

        def boom(*_args, **_kwargs):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(permissions, "sync_permissions", boom)
        assert _deploy(isolated_layers["project"], "--json") == 1
        report = json.loads(capsys.readouterr().out)
        assert any("simulated failure" in f for f in report["failed"])
        # The steps after the failing one still ran.
        assert report["changes"]["mcp"]


def test_init_is_an_alias_for_deploy(isolated_layers, capsys):
    assert cli(["init", "--target", str(isolated_layers["project"]),
                "--no-link-memory"]) == 0
    assert "Deployed" in capsys.readouterr().out
