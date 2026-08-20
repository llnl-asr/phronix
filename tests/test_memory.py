"""Memory: the write path's guarantees, and retrieval's ranking and link-walking."""
from __future__ import annotations

from phronix import memory
from phronix.memory_graph import parse_links, recall, render_digest, score_memory, tokenize


class TestWrite:
    def test_round_trip(self, isolated_layers):
        result = memory.write("test-fact", "A one-line description.", "The body.")
        assert result["status"] == "ok"
        assert result["action"] == "created"
        assert result["layer"] == "project"

        loaded = memory.read("test-fact")
        assert loaded is not None
        assert "The body." in loaded["content"]
        assert "type: project" in loaded["content"]

    def test_second_write_updates_rather_than_duplicating(self, isolated_layers):
        memory.write("test-fact", "First.", "Body one.")
        second = memory.write("test-fact", "Second.", "Body two.")
        assert second["action"] == "updated"
        assert len(memory.listing()) == 1

    def test_content_is_redacted_and_the_redaction_reported(self, isolated_layers):
        result = memory.write("p", "d", "config lives at /home/alice/cfg")
        assert result["redacted"]
        assert "/home/alice" not in memory.read("p")["content"]
        assert "$HOME/cfg" in memory.read("p")["content"]

    def test_user_type_is_refused(self, isolated_layers):
        """A profile of a person cannot be made safe by redaction."""
        result = memory.write("who", "d", "b", type="user")
        assert result["status"] == "error"
        assert "never allowed" in result["error"]

    def test_unknown_type_is_refused(self, isolated_layers):
        assert memory.write("x", "d", "b", type="nonsense")["status"] == "error"

    def test_index_is_rebuilt_not_appended(self, isolated_layers):
        """A rebuilt index drops deleted memories; an appended one accumulates ghosts."""
        memory.write("alpha", "First memory.", "body")
        memory.write("beta", "Second memory.", "body")
        index = (isolated_layers["store"] / "memory" / "MEMORY.md").read_text()
        assert index.count("(alpha.md)") == 1
        assert "(beta.md)" in index

        (isolated_layers["store"] / "memory" / "beta.md").unlink()
        memory.reindex(isolated_layers["store"] / "memory")
        assert "(beta.md)" not in (isolated_layers["store"] / "memory" / "MEMORY.md").read_text()


class TestRetrieval:
    def test_tokenize_splits_hyphenated_slugs(self):
        terms = tokenize("always-function-mode")
        assert "function" in terms and "mode" in terms

    def test_tokenize_drops_stopwords_and_short_tokens(self):
        assert tokenize("the and a for") == []

    def test_parse_links_normalises_aliases_and_anchors(self):
        assert parse_links("see [[a|alias]] and [[b#section]] and [[a]]") == ["a", "b"]

    def test_coverage_beats_raw_frequency(self):
        """3-of-3 terms once each must outrank 1 term forty times."""
        broad = {"name": "x", "description": "", "body": "alpha beta gamma", "links": []}
        narrow = {"name": "y", "description": "", "body": "alpha " * 40, "links": []}
        terms = ["alpha", "beta", "gamma"]
        assert score_memory(broad, terms) > score_memory(narrow, terms)

    def test_name_hits_outrank_body_hits(self):
        by_name = {"name": "deploy-process", "description": "", "body": "", "links": []}
        by_body = {"name": "other", "description": "", "body": "deploy", "links": []}
        assert score_memory(by_name, ["deploy"]) > score_memory(by_body, ["deploy"])

    def test_link_expansion_pulls_in_a_non_matching_neighbour(self):
        """This is why links are load-bearing: the neighbour matches nothing itself."""
        corpus = [
            {"name": "hit", "description": "about widgets", "type": "", "body": "widgets [[side]]",
             "links": ["side"], "file": "hit.md", "chars": 10},
            {"name": "side", "description": "unrelated wording", "type": "", "body": "nothing",
             "links": [], "file": "side.md", "chars": 10},
        ]
        results = recall("widgets", memories=corpus)
        names = {r["name"]: r["via"] for r in results}
        assert names["hit"] == "match"
        assert names["side"] == "hit"

    def test_dangling_links_are_tolerated(self):
        """The conventions allow a link to a memory not written yet."""
        corpus = [{"name": "hit", "description": "widgets", "type": "", "body": "[[ghost]]",
                   "links": ["ghost"], "file": "hit.md", "chars": 10}]
        assert [r["name"] for r in recall("widgets", memories=corpus)] == ["hit"]

    def test_digest_truncates_within_budget(self):
        results = [{"name": f"m{i}", "description": "x" * 100, "via": "match"} for i in range(20)]
        digest = render_digest(results, budget_chars=200)
        assert len(digest) < 400
        assert "more (memory_recall" in digest
