"""Shared fixtures.

Every test that touches the store gets an isolated three-layer setup. Without
this, a test run would read the developer's real ``~/.phronix`` and write into
the repository's own bundled layer — so results would depend on the machine, and
a failing test could leave real learning behind.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def isolated_layers(tmp_path, monkeypatch):
    """Point every layer at ``tmp_path`` and return the roots.

    ``PHRONIX_PROJECT_ROOT`` pins the project layer explicitly rather than
    relying on cwd detection, which would otherwise walk up and find the phronix
    repository itself.
    """
    home = tmp_path / "home"
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    home.mkdir(parents=True)

    monkeypatch.setenv("PHRONIX_HOME", str(home))
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PHRONIX_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("PHRONIX_WRITE_LAYER", "project")
    monkeypatch.delenv("PHRONIX_CONTEXT_STATE_DIR", raising=False)

    return {"home": home, "project": project, "store": project / ".phronix"}
