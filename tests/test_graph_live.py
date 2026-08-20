"""End-to-end knowledge-graph checks, skipped when ``graphify`` is not installed.

Kept separate from the unit tests so the suite stays runnable without the CLI, and
so a skip here is visible as "the live path was not exercised" rather than hidden
inside a passing file.
"""
from __future__ import annotations

import shutil

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("graphify") is None,
    reason="graphify CLI not installed; the live graph path cannot be exercised",
)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Build the knowledge graph once for the module — a rebuild takes seconds."""
    import os

    tmp = tmp_path_factory.mktemp("graph")
    os.environ["PHRONIX_CACHE"] = str(tmp / "cache")
    os.environ["PHRONIX_HOME"] = str(tmp / "home")
    os.environ["PHRONIX_PROJECT_ROOT"] = str(tmp / "nonexistent")

    from phronix.knowledge_graph import ensure

    result = ensure("knowledge", force=True)
    assert not result.get("error"), result
    return result


def test_graph_builds_over_the_bundled_store(built):
    assert built["rebuilt"] is True
    assert built["nodes"] > 100
    assert built["staged_files"] > 10


def test_second_ensure_is_a_cache_hit(built):
    """Freshness is content-hashed; a no-op rebuild would cost seconds every query."""
    from phronix.knowledge_graph import ensure

    again = ensure("knowledge")
    assert again["rebuilt"] is False
    assert again["reason"] == "up to date"


def test_dirty_flag_forces_a_rebuild(built):
    """A lesson written mid-session must be findable in the same session."""
    from phronix.knowledge_graph import ensure, mark_dirty

    mark_dirty("test")
    assert ensure("knowledge")["rebuilt"] is True


def test_skill_retrieval_returns_a_section_not_a_document(built):
    from phronix.knowledge_graph import find_docs

    result = find_docs("what happens when an assumption is not met", store="skills")
    assert result["status"] == "ok"
    top = result["results"][0]
    assert top["artifact"] == "phronix-verification"
    assert "assumption" in top["heading"].lower()
    # A section, not the whole file: the file node's label is the filename.
    assert not top["heading"].endswith(".md")
    assert top["text"].lstrip().startswith("#")


def test_retrieved_paths_are_real_and_openable(built):
    """Paths are stage-relative in the graph; handing one back unmapped is useless."""
    from pathlib import Path

    from phronix.knowledge_graph import find_docs

    for hit in find_docs("redact a username", store="skills")["results"]:
        assert Path(hit["source_file"]).is_file(), hit["source_file"]


def test_stores_are_disjoint(built):
    from phronix.knowledge_graph import find_docs

    skills = find_docs("skill", store="skills")
    assert all("-skills/" in h["source_file"] or "/skills/" in h["source_file"]
               for h in skills["results"])


def test_all_stopwords_query_is_rejected_clearly(built):
    from phronix.knowledge_graph import find_docs

    result = find_docs("how should this be done", store="skills")
    assert result["status"] == "error"
    assert "stopwords" in result["error"]
