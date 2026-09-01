"""Shared fixtures.

Every test that touches the store gets an isolated three-layer setup. Without
this, a test run would read the developer's real ``~/.phronix`` and write into
the repository's own bundled layer — so results would depend on the machine, and
a failing test could leave real learning behind.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def framework_bundled_root(tmp_path_factory):
    """A copy of the framework's bundled layer, WITHOUT the learned corpus.

    Built once for the session. Copied rather than symlinked: `which_layer`
    resolves the path it is given, and a symlink resolves back into the real
    tree — so every lookup reported the real layer and the isolation did
    nothing while appearing to work.
    """
    root = tmp_path_factory.mktemp("framework-bundled")
    real = Path(__file__).resolve().parent.parent / "src" / "phronix" / ".phronix"
    if real.is_dir():
        for entry in sorted(real.iterdir()):
            if entry.name in ("capabilities", "research"):
                continue
            target = root / entry.name
            if entry.is_dir():
                shutil.copytree(entry, target, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(entry, target)
    # Present but empty: absent would make `layers()` drop the layer entirely.
    for kind in ("capabilities", "research"):
        (root / kind).mkdir(exist_ok=True)
    return root


@pytest.fixture(autouse=True)
def isolated_bundled_layer(framework_bundled_root, monkeypatch):
    """Every test sees the FRAMEWORK's bundled layer, not the learned corpus.

    The bundled layer is read by every lookup, and the store now lives under
    the package — which is the point: a finding has to survive a clone rather
    than living as long as one checkout. The cost is that a test writing a
    skill to a temp store still FINDS the packaged one and asserts against it.
    Measured: eight tests failed the moment 856 files landed in the package,
    every one of them passing on an empty store and testing nothing. The suite
    also went from 27s to 7m21s, re-reading a corpus no test wanted.

    The framework's own content stays — tests legitimately load
    `phronix-task-research` and the agent templates — while `capabilities/`
    and `research/`, which hold what runs have LEARNED, are empty. A test that
    wants learned content writes its own.
    """
    monkeypatch.setenv("PHRONIX_BUNDLED_ROOT", str(framework_bundled_root))
    return framework_bundled_root


@pytest.fixture
def real_bundled_layer(monkeypatch):
    """Opt OUT of the isolation, for tests about the real packaged layer.

    A handful of tests are about the shipped store itself — where it lives,
    that it is writable in a git worktree, that a project links into it. Those
    must see the real thing; everything else must not.
    """
    monkeypatch.delenv("PHRONIX_BUNDLED_ROOT", raising=False)
    from phronix.layers import bundled_root

    return bundled_root()


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
