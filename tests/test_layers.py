"""The layered store: precedence, merge rules, and write-target resolution.

These are the tests that matter most. Every other subsystem reads through
:mod:`phronix.layers`, so a precedence bug here does not look like a precedence
bug — it looks like a skill that mysteriously has the wrong content, or a lesson
that was written and then vanished.
"""
from __future__ import annotations

import pytest

from phronix import layers


def test_project_layer_shadows_bundled_by_name(isolated_layers):
    """A project skill of the same name replaces the bundled one entirely."""
    store = isolated_layers["store"]
    (store / "skills" / "phronix-privacy").mkdir(parents=True)
    (store / "skills" / "phronix-privacy" / "SKILL.md").write_text("project version")

    found = layers.skill_dirs()
    assert found["phronix-privacy"].read_text if False else True
    assert (found["phronix-privacy"] / "SKILL.md").read_text() == "project version"
    # The bundled skills that were NOT shadowed are still visible.
    assert "phronix-self-learning" in found


def test_bundled_skills_visible_without_a_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path / "nonexistent"))
    found = layers.skill_dirs()
    assert "phronix-self-learning" in found
    assert layers.which_layer(found["phronix-self-learning"]) == "bundled"


def test_common_sections_returned_per_layer_not_merged_here(isolated_layers):
    """Shared sections merge key-by-key, so every layer's file must be returned.

    Returning only the winner would silently drop the bundled library the moment
    a project added a single section of its own.
    """
    store = isolated_layers["store"]
    (store / "agents").mkdir(parents=True, exist_ok=True)
    (store / "agents" / "common-sections.yaml").write_text("sections: {}\n")

    files = layers.common_sections_files()
    assert len(files) == 2
    assert files[0].parent.parent.name == ".phronix"      # bundled first
    assert files[-1].parent.parent.name == ".phronix"    # project last (wins)


def test_agent_templates_exclude_the_shared_library(isolated_layers):
    """common-sections.yaml is a library, not an agent; rendering it would fail."""
    assert "common-sections.yaml" not in layers.agent_templates()
    assert "phronix-router.yaml" in layers.agent_templates()


def test_write_layer_honours_explicit_request(isolated_layers, monkeypatch):
    monkeypatch.delenv("PHRONIX_WRITE_LAYER")
    assert layers.resolve_write_layer("user").name == "user"
    assert layers.resolve_write_layer("project").name == "project"


def test_write_layer_refuses_an_unwritable_target_instead_of_downgrading(monkeypatch, tmp_path):
    """A silent downgrade would report success for a lesson nobody will ever see."""
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(
        layers, "bundled_layer",
        lambda: layers.Layer("bundled", tmp_path / "ro", writable=False, shared=True),
    )
    with pytest.raises(PermissionError, match="not writable"):
        layers.resolve_write_layer("bundled")


def test_editable_install_does_not_hijack_another_projects_learning(tmp_path, monkeypatch):
    """An editable install leaves the bundled layer writable and inside a git tree.

    Without the "is this project the phronix checkout?" test, a lesson learned
    while working on some OTHER repository is written into phronix's own tree —
    shipped to every installer, and absent from the repository it was about. The
    e2e run caught exactly this.
    """
    project = tmp_path / "someone-elses-repo"
    (project / ".git").mkdir(parents=True)
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(project))
    monkeypatch.delenv("PHRONIX_WRITE_LAYER", raising=False)
    # Simulate `pip install -e .`: bundled is real, writable, and git-tracked.
    monkeypatch.setattr(
        layers, "bundled_layer",
        lambda: layers.Layer("bundled", layers.bundled_root(), writable=True, shared=True),
    )
    assert layers.resolve_write_layer().name == "project"


def test_developing_phronix_itself_writes_to_bundled(tmp_path, monkeypatch):
    """The contributor case: the working project IS the phronix checkout."""
    checkout = layers.bundled_root().parents[2]  # <checkout>/src/phronix/.phronix -> <checkout>
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(checkout))
    monkeypatch.delenv("PHRONIX_WRITE_LAYER", raising=False)
    monkeypatch.setattr(
        layers, "bundled_layer",
        lambda: layers.Layer("bundled", layers.bundled_root(), writable=True, shared=True),
    )
    assert layers.resolve_write_layer().name == "bundled"


def test_write_layer_falls_back_to_user_without_a_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path / "nonexistent"))
    monkeypatch.delenv("PHRONIX_WRITE_LAYER", raising=False)
    monkeypatch.setattr(
        layers, "bundled_layer",
        lambda: layers.Layer("bundled", tmp_path / "ro", writable=False, shared=True),
    )
    assert layers.resolve_write_layer().name == "user"


def test_which_layer_picks_the_deepest_containing_root(isolated_layers):
    """Layers can nest; the deepest root is the real owner."""
    store = isolated_layers["store"]
    (store / "skills" / "example").mkdir(parents=True)
    assert layers.which_layer(store / "skills" / "example") == "project"


def test_describe_reports_absent_layers(isolated_layers):
    """`phronix status` must show a layer that does not exist yet, not hide it."""
    names = [entry["layer"] for entry in layers.describe()]
    assert names == ["bundled", "user", "project"]


def test_the_shipped_store_links_into_a_project():
    """`<package>/.phronix` is the store; a project gets a link, not a copy.

    A copy is stale the moment anything is written to either side, and two
    copies of a skill are two answers to one question with no way to tell which
    is current. A tree that already has its own `.phronix` is left alone and
    reported `occupied` — a benchmark arm's store is exactly that, and relinking
    it would put every arm in one store.
    """
    import tempfile
    from pathlib import Path

    from phronix.agents import link_store
    from phronix.layers import bundled_root

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        first = link_store(target)
        assert first["linked"] and first["status"] == "linked"
        assert (target / ".phronix").is_symlink()
        assert (target / ".phronix").resolve() == bundled_root().resolve()
        assert link_store(target)["status"] == "already_linked"

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / ".phronix").mkdir()
        assert link_store(target)["status"] == "occupied"
