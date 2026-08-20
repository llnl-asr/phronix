"""The corrector tier: built-in structural checks, and the five-facet spec runner.

The facet-semantics tests are the load-bearing ones. If a failed *assumption* ever
reports as ``fail`` rather than ``inconclusive``, every machine missing a
dependency turns red, people learn to ignore the signal, and the genuine failures
go with it — which is a worse outcome than having no verification at all.
"""
from __future__ import annotations

import pytest

from phronix import correctors, verification


def _write_verifier(store, name, body):
    directory = store / "verifiers"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.py").write_text(body)


def _write_skill(store, name, text):
    directory = store / "skills" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(text)


# ---------------------------------------------------------------------------
# Built-in structural correctors
# ---------------------------------------------------------------------------

class TestBuiltinCorrectors:
    def test_every_bundled_artifact_is_structurally_clean(self, isolated_layers):
        """What ships must pass its own correctors, or the discipline is theatre."""
        problems = [
            (r["kind"], r["target"], f)
            for r in correctors.correct_all()
            for f in r["findings"]
        ]
        assert problems == []

    def test_skill_missing_frontmatter_is_caught(self, isolated_layers):
        _write_skill(isolated_layers["store"], "bare", "## Just a heading\n")
        result = correctors.correct("skill", "bare")
        assert any(f["check"] == "frontmatter_parses" for f in result["findings"])

    def test_skill_name_mismatch_is_a_failure(self, isolated_layers):
        _write_skill(isolated_layers["store"], "declared-a",
                     "---\nname: declared-b\ndescription: a description long enough\n---\n")
        result = correctors.correct("skill", "declared-a")
        assert result["status"] == "fail"
        assert any(f["check"] == "name_matches_directory" for f in result["findings"])

    def test_identifying_content_in_a_skill_fails(self, isolated_layers):
        _write_skill(isolated_layers["store"], "leaky",
                     "---\nname: leaky\ndescription: a description long enough here\n---\n\n"
                     "## S\n\nconfig at /home/someuser/cfg\n")
        result = correctors.correct("skill", "leaky")
        assert result["status"] == "fail"
        assert any(f["check"] == "privacy" for f in result["findings"])

    def test_reference_inside_code_is_not_a_dangling_link(self, isolated_layers):
        """A skill documenting the reference syntax must not fail for showing it."""
        _write_skill(isolated_layers["store"], "docs-skill",
                     "---\nname: docs-skill\ndescription: a description long enough here\n"
                     "subject: documenting\ntype: skill\n---\n\n"
                     "## Index\n\n## Rules\n\n### R1 — Syntax\n\n"
                     "Link with `[[name]]` or:\n\n```\n[[other#R1]]\n```\n")
        result = correctors.correct("skill", "docs-skill")
        assert not any(f["check"] == "references_resolve" for f in result["findings"])

    def test_a_reference_to_a_missing_skill_is_warned(self, isolated_layers):
        _write_skill(isolated_layers["store"], "linky",
                     "---\nname: linky\ndescription: a description long enough here\n"
                     "subject: linking\ntype: skill\n---\n\n"
                     "## Index\n\n## Rules\n\n### R1 — See also\n\nSee [[no-such-skill]].\n")
        findings = correctors.correct("skill", "linky")["findings"]
        assert any(f["check"] == "references_resolve" and f["severity"] == "warn"
                   for f in findings)

    def test_a_reference_to_a_missing_label_is_a_failure(self, isolated_layers):
        """A broken foreign key is worse than a missing one: it looks checked."""
        _write_skill(isolated_layers["store"], "linky",
                     "---\nname: linky\ndescription: a description long enough here\n"
                     "subject: linking\ntype: skill\n---\n\n"
                     "## Index\n\n## Rules\n\n### R1 — See also\n\n"
                     "See [[phronix-privacy#R99]].\n")
        result = correctors.correct("skill", "linky")
        assert result["status"] == "fail"
        assert any(f["check"] == "references_resolve" for f in result["findings"])

    def test_duplicate_labels_are_a_failure(self, isolated_layers):
        _write_skill(isolated_layers["store"], "dup",
                     "---\nname: dup\ndescription: a description long enough here\n"
                     "subject: duplication\ntype: skill\n---\n\n"
                     "## Index\n\n## Rules\n\n### R1 — One\n\na\n\n### R1 — Two\n\nb\n")
        result = correctors.correct("skill", "dup")
        assert result["status"] == "fail"
        assert any(f["check"] == "labels_unique_and_well_formed" for f in result["findings"])

    def test_index_drift_is_caught_both_ways(self, isolated_layers):
        """An index that lies routes retrieval to content that is not there."""
        _write_skill(isolated_layers["store"], "drifted",
                     "---\nname: drifted\ndescription: a description long enough here\n"
                     "subject: drifting\ntype: skill\n---\n\n"
                     "## Index\n\n| Label | Section | Covers |\n| --- | --- | --- |\n"
                     "| `R7` | Rules | a block that does not exist |\n\n"
                     "## Rules\n\n### R1 — Real block\n\nbody\n")
        findings = correctors.correct("skill", "drifted")["findings"]
        details = " ".join(f["detail"] for f in findings if f["check"] == "index_matches_content")
        assert "R1 exists but is not in the Index" in details
        assert "Index lists R7" in details

    def test_lessons_in_the_skill_file_are_a_failure(self, isolated_layers):
        """Skill search and memory search must not drag in each other's content."""
        _write_skill(isolated_layers["store"], "mixed",
                     "---\nname: mixed\ndescription: a description long enough here\n"
                     "subject: mixing\ntype: skill\n---\n\n"
                     "## Index\n\n## Rules\n\n### R1 — A rule\n\nb\n\n"
                     "## Lessons\n\n### L1 — An incident\n\nit broke\n")
        result = correctors.correct("skill", "mixed")
        assert result["status"] == "fail"
        assert any(f["check"] == "lessons_are_separate" for f in result["findings"])

    def test_a_skill_with_no_subject_is_warned(self, isolated_layers):
        _write_skill(isolated_layers["store"], "subjectless",
                     "---\nname: subjectless\ndescription: a description long enough here\n"
                     "type: skill\n---\n\n## Index\n\n## Rules\n\n### R1 — R\n\nb\n")
        findings = correctors.correct("skill", "subjectless")["findings"]
        assert any(f["check"] == "declares_one_subject" for f in findings)

    def test_a_skill_with_no_index_is_a_failure(self, isolated_layers):
        _write_skill(isolated_layers["store"], "noindex",
                     "---\nname: noindex\ndescription: a description long enough here\n"
                     "subject: s\ntype: skill\n---\n\n## Rules\n\n### R1 — R\n\nb\n")
        result = correctors.correct("skill", "noindex")
        assert result["status"] == "fail"
        assert any(f["check"] == "required_sections_present" for f in result["findings"])

    def test_capability_without_register_fails(self, isolated_layers):
        directory = isolated_layers["store"] / "capabilities"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "noreg.py").write_text("x = 1\n")
        result = correctors.correct("capability", "noreg")
        assert result["status"] == "fail"
        assert any(f["check"] == "defines_register" for f in result["findings"])

    def test_capability_tool_without_a_docstring_fails(self, isolated_layers):
        """The docstring is the only description a model sees."""
        directory = isolated_layers["store"] / "capabilities"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "undoc.py").write_text(
            "def register(mcp):\n"
            "    @mcp.tool()\n"
            "    def thing() -> str:\n"
            "        return 'x'\n"
        )
        result = correctors.correct("capability", "undoc")
        assert result["status"] == "fail"
        assert any(f["check"] == "tools_documented" for f in result["findings"])

    def test_capability_registering_nothing_fails(self, isolated_layers):
        directory = isolated_layers["store"] / "capabilities"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "empty.py").write_text("def register(mcp):\n    pass\n")
        result = correctors.correct("capability", "empty")
        assert any(f["check"] == "registers_a_tool" for f in result["findings"])

    def test_agent_referencing_a_missing_skill_fails(self, isolated_layers):
        import yaml

        directory = isolated_layers["store"] / "agents"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "bad-agent.yaml").write_text(yaml.safe_dump({
            "name": "bad-agent",
            "description": "A description that is comfortably long enough to pass.",
            "model_level": "level_2",
            "skills": ["no-such-skill"],
            "sections": [{"title": "t", "body": "b"}],
        }))
        result = correctors.correct("agent", "bad-agent")
        assert result["status"] == "fail"
        assert any(f["check"] == "skills_exist" for f in result["findings"])

    def test_a_missing_target_is_reported_not_raised(self, isolated_layers):
        assert correctors.correct("skill", "nope")["status"] == "fail"

    def test_unknown_kind_is_not_applicable(self, isolated_layers):
        assert correctors.correct("memory", "x")["status"] == "not_applicable"


# ---------------------------------------------------------------------------
# The five-facet spec runner
# ---------------------------------------------------------------------------

_PASSING = '''
SPEC = {
    "kind": "skill", "target": "t", "claim": "a falsifiable claim",
    "assumptions": [{"name": "a", "check": lambda ctx: True}],
    "inputs": [{"name": "value", "required": True, "resolve": lambda ctx: 42}],
    "constraints": [{"name": "c", "check": lambda ctx: ctx["value"] == 42}],
    "invariants": [{"name": "i", "sample": lambda ctx: "stable"}],
    "outputs": [{"name": "o", "check": lambda ctx: (True, "produced")}],
}
'''


class TestFacetSemantics:
    def test_all_facets_passing_is_a_pass(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "good", _PASSING)
        result = verification.run(name="good")
        assert result["status"] == "pass"
        entry = result["results"][0]
        assert set(entry["facets"]) == set(verification.FACETS)
        assert all(r["ok"] for facet in entry["facets"].values() for r in facet)

    def test_unmet_assumption_is_inconclusive_not_fail(self, isolated_layers):
        """The single most important distinction in the design."""
        _write_verifier(isolated_layers["store"], "gated", '''
SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "assumptions": [{"name": "dependency", "detail": "not installed here",
                     "check": lambda ctx: False}],
    "constraints": [{"name": "never_reached", "check": lambda ctx: False}],
}
''')
        result = verification.run(name="gated")
        assert result["status"] == "inconclusive"
        assert "unmet assumptions" in result["results"][0]["evidence"]
        # The constraint must NOT have been evaluated — running it would make the
        # gate pointless and could have side effects the assumption guarded against.
        assert result["results"][0]["facets"]["constraints"] == []

    def test_unresolved_required_input_is_inconclusive(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "noinput", '''
SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "inputs": [{"name": "missing", "required": True, "resolve": lambda ctx: None}],
    "constraints": [{"name": "c", "check": lambda ctx: True}],
}
''')
        assert verification.run(name="noinput")["status"] == "inconclusive"

    def test_optional_input_that_does_not_resolve_does_not_gate(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "optin", '''
SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "inputs": [{"name": "maybe", "required": False, "resolve": lambda ctx: None}],
    "constraints": [{"name": "c", "check": lambda ctx: True}],
}
''')
        assert verification.run(name="optin")["status"] == "pass"

    def test_failed_constraint_is_a_fail_and_names_the_facet(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "bad", '''
SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "constraints": [{"name": "the_claim", "check": lambda ctx: (False, "observed 3, wanted 4")}],
}
''')
        result = verification.run(name="bad")
        assert result["status"] == "fail"
        assert "constraints.the_claim" in result["results"][0]["evidence"]
        assert "observed 3, wanted 4" in result["results"][0]["evidence"]

    def test_violated_invariant_fails_even_when_constraints_pass(self, isolated_layers):
        """Verifying something must not change it."""
        _write_verifier(isolated_layers["store"], "mutating", '''
_calls = []

def _sample(ctx):
    _calls.append(1)
    return len(_calls)

SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "constraints": [{"name": "fine", "check": lambda ctx: True}],
    "invariants": [{"name": "changed", "sample": _sample}],
}
''')
        result = verification.run(name="mutating")
        assert result["status"] == "fail"
        assert "changed during verification" in result["results"][0]["evidence"]

    def test_failed_output_is_a_fail(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "noout", '''
SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "constraints": [{"name": "c", "check": lambda ctx: True}],
    "outputs": [{"name": "artifact", "check": lambda ctx: False}],
}
''')
        assert verification.run(name="noout")["status"] == "fail"

    def test_a_raising_check_is_recorded_not_propagated(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "boom", '''
def _explode(ctx):
    raise RuntimeError("kaboom")

SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "constraints": [{"name": "explodes", "check": _explode}],
}
''')
        result = verification.run(name="boom")
        assert result["status"] == "fail"
        assert "kaboom" in result["results"][0]["evidence"]

    def test_check_return_shapes_are_all_accepted(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "shapes", '''
SPEC = {
    "kind": "skill", "target": "t", "claim": "c",
    "constraints": [
        {"name": "bare_bool", "check": lambda ctx: True},
        {"name": "tuple", "check": lambda ctx: (True, "evidence")},
        {"name": "dict", "check": lambda ctx: {"ok": True, "evidence": "e"}},
    ],
}
''')
        assert verification.run(name="shapes")["status"] == "pass"


class TestSpecValidation:
    def test_a_spec_with_no_constraints_or_outputs_is_rejected(self, isolated_layers):
        """It cannot fail, so it proves nothing while looking like coverage."""
        _write_verifier(isolated_layers["store"], "vacuous", '''
SPEC = {"kind": "skill", "target": "t", "claim": "c", "assumptions": []}
''')
        result = verification.run(name="vacuous")
        assert result["status"] == "error"
        assert "proves nothing" in result["results"][0]["evidence"]

    def test_missing_required_metadata_is_reported(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "nometa", '''
SPEC = {"kind": "skill", "constraints": [{"name": "c", "check": lambda ctx: True}]}
''')
        result = verification.run(name="nometa")
        assert result["status"] == "error"
        assert "target" in result["results"][0]["evidence"]

    def test_non_callable_check_is_reported(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "notcallable", '''
SPEC = {"kind": "skill", "target": "t", "claim": "c",
        "constraints": [{"name": "c", "check": "not a function"}]}
''')
        assert verification.run(name="notcallable")["status"] == "error"

    def test_an_unimportable_verifier_is_reported_not_dropped(self, isolated_layers):
        """A check that silently vanishes looks like coverage never written."""
        _write_verifier(isolated_layers["store"], "broken", "import nonexistent_module\n")
        result = verification.run(name="broken")
        assert result["status"] == "error"
        assert verification.coverage()["broken_verifiers"] == ["broken"]

    def test_new_rejects_a_module_without_a_spec(self, isolated_layers):
        result = verification.new("x", "skill", "t", "claim", source="def verify(c): pass\n")
        assert result["status"] == "error"
        assert "SPEC" in result["error"]

    def test_new_rejects_an_empty_claim(self, isolated_layers):
        assert verification.new("x", "skill", "t", "  ")["status"] == "error"

    def test_new_rejects_an_unknown_kind(self, isolated_layers):
        assert verification.new("x", "nonsense", "t", "c")["status"] == "error"

    def test_the_scaffold_is_syntactically_valid_but_proves_nothing(self, isolated_layers):
        """It must save, and it must not be mistaken for real coverage."""
        result = verification.new("scaffolded", "skill", "t", "a claim")
        assert result["status"] == "ok" and result["scaffolded"]
        # No constraints yet -> the runner reports it as a malformed (vacuous) spec.
        assert verification.run(name="scaffolded")["status"] == "error"


class TestAggregationAndCoverage:
    def test_builtin_correctors_are_included_by_default(self, isolated_layers):
        result = verification.run(kind="skill")
        assert any(r["source"] == "builtin" for r in result["results"])

    def test_builtin_can_be_excluded(self, isolated_layers):
        result = verification.run(kind="skill", include_builtin=False)
        assert all(r["source"] == "authored" for r in result["results"])

    def test_inconclusive_alone_does_not_read_as_failure(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "gated", '''
SPEC = {"kind": "skill", "target": "zzz-nonexistent", "claim": "c",
        "assumptions": [{"name": "a", "check": lambda ctx: False}],
        "constraints": [{"name": "c", "check": lambda ctx: True}]}
''')
        result = verification.run(name="gated")
        assert result["status"] == "inconclusive"

    def test_coverage_counts_authored_verifiers_only(self, isolated_layers):
        """Built-in correctors cover everything, so counting them hides the real gap."""
        report = verification.coverage()
        assert report["structurally_corrected"] == report["total_artifacts"]
        assert report["claim_verified"] < report["total_artifacts"]

    def test_coverage_flags_an_orphaned_verifier(self, isolated_layers):
        _write_verifier(isolated_layers["store"], "orphan", '''
SPEC = {"kind": "skill", "target": "deleted-long-ago", "claim": "c",
        "constraints": [{"name": "c", "check": lambda ctx: True}]}
''')
        assert "orphan" in verification.coverage()["orphaned_verifiers"]

    def test_covers_links_a_verifier_to_its_target(self, isolated_layers):
        assert verification.covers("skill", "phronix-privacy") == ["privacy_rules_hold"]
        assert verification.covers("skill", "phronix-memory") == []

    def test_no_match_is_distinguished_from_a_pass(self, isolated_layers):
        result = verification.run(name="does-not-exist")
        assert result["status"] == "no_verifiers"


class TestWritePathsReportCoverage:
    def test_skill_write_reports_a_missing_corrector(self, isolated_layers):
        from phronix.skills import write_lesson

        result = write_lesson("brand-new-skill", "a lesson", description="d")
        assert result["verification"]["covered"] is False
        assert "verify_new" in result["verification"]["next"]

    def test_skill_write_reports_an_existing_corrector(self, isolated_layers):
        from phronix.skills import write_lesson

        result = write_lesson("phronix-privacy", "another lesson")
        assert result["verification"]["covered"] is True
        assert "privacy_rules_hold" in result["verification"]["verifiers"]

    def test_capability_new_reports_a_missing_corrector(self, isolated_layers):
        from phronix.capabilities import new

        result = new("thing", "d", source="def register(mcp):\n    pass\n")
        assert result["verification"]["covered"] is False


def test_bundled_verifiers_pass_on_this_checkout(isolated_layers):
    """The correctors that ship must hold for the code that ships with them."""
    result = verification.run(include_builtin=False)
    failures = [r for r in result["results"] if r["status"] in ("fail", "error")]
    assert failures == [], [(r["name"], r["evidence"]) for r in failures]
