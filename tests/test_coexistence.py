"""Phronix installed beside another agent framework in the same project.

The dftracer-agents project is the real case: it renders its own harness
hooks, agents and MCP config into the same `.claude/` directory phronix
writes to. Two frameworks sharing one harness directory is the normal case,
not an exotic one, and everything here is a bug that actually happened when
phronix was installed into that project.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from phronix import hooks

pytestmark = pytest.mark.usefixtures("isolated_bundled_layer")

# What the OTHER framework installs. Named exactly as dftracer-agents does,
# because the collisions below are all about the names.
OTHER_HOOK = "inject_context.py"
OTHER_GUARD = "guard_rm_drm.sh"


def _install_other(root: Path) -> None:
    """Render a second framework's hooks the way dftracer-agents does."""
    hooks_dir = root / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / OTHER_HOOK).write_text("#!/usr/bin/env python3\n# other framework\n")
    (hooks_dir / OTHER_GUARD).write_text("#!/usr/bin/env bash\n# other framework\n")
    settings = root / ".claude" / "settings.json"
    data = json.loads(settings.read_text()) if settings.exists() else {}
    data.setdefault("hooks", {})
    data["hooks"].setdefault("UserPromptSubmit", []).append(
        {"hooks": [{"type": "command", "command": f"python3 .claude/hooks/{OTHER_HOOK}"}]})
    data["hooks"].setdefault("PreToolUse", []).append(
        {"matcher": "Bash",
         "hooks": [{"type": "command", "command": f"bash .claude/hooks/{OTHER_GUARD}"}]})
    settings.write_text(json.dumps(data, indent=2) + "\n")


def _commands(root: Path) -> list[str]:
    data = json.loads((root / ".claude" / "settings.json").read_text())
    return [h.get("command", "")
            for groups in data.get("hooks", {}).values()
            for g in groups for h in g.get("hooks", [])]


def test_hook_script_name_is_namespaced() -> None:
    """The generic name belongs to nobody, so phronix must not take it.

    Sharing `inject_context.py` meant whoever synced last overwrote the
    other's script -- and each framework's "is this entry mine?" test matched
    the other's settings entry, so the clobber reported itself as
    "already current".
    """
    assert hooks.HOOK_SCRIPT_NAME.startswith("phronix")
    # Not merely prefixed: a substring test on the generic name still matches
    # `phronix_inject_context.py`, which is how the second collision survived
    # the first fix.
    assert OTHER_HOOK not in hooks.HOOK_SCRIPT_NAME


def test_sync_writes_every_script_it_advertises(tmp_path: Path) -> None:
    """A settings entry pointing at a missing script fails every turn.

    The sync path used to write the prompt hook and advertise the edit guard,
    installing only the first -- so every Edit was gated on a file that was
    never created.
    """
    import importlib.util
    hooks.sync_claude_hooks(tmp_path)
    for command in _commands(tmp_path):
        argv = command.split()
        if "-m" in argv:                       # a module (the learner's recorder): it must be importable
            mod = argv[argv.index("-m") + 1]
            assert importlib.util.find_spec(mod), f"advertised but not importable: {command}"
            continue
        script = tmp_path / argv[-1]
        assert script.is_file(), f"advertised but not installed: {command}"


def test_does_not_disturb_another_framework(tmp_path: Path) -> None:
    _install_other(tmp_path)
    before = (tmp_path / ".claude" / "hooks" / OTHER_HOOK).read_text()

    hooks.sync_claude_hooks(tmp_path)

    assert (tmp_path / ".claude" / "hooks" / OTHER_HOOK).read_text() == before
    commands = _commands(tmp_path)
    assert any(OTHER_HOOK in c for c in commands), "the other framework's hook was dropped"
    assert any(hooks.HOOK_SCRIPT_NAME in c for c in commands), "phronix's hook is missing"
    assert any(OTHER_GUARD in c for c in commands), "the other framework's guard was dropped"


def test_repeated_syncs_are_stable(tmp_path: Path) -> None:
    """Neither framework may accumulate or drop entries on re-sync."""
    _install_other(tmp_path)
    hooks.sync_claude_hooks(tmp_path)
    first = sorted(_commands(tmp_path))

    for _ in range(3):
        hooks.sync_claude_hooks(tmp_path)

    assert sorted(_commands(tmp_path)) == first
