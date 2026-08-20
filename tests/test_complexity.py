"""Complexity assessment: the direction of each signal, and the intrinsic floor.

The signal *directions* are the framework's thesis expressed as arithmetic —
accumulated prose raises the model requirement, deterministic tools lower it. A
regression that flipped one would silently invert the incentive the whole design
rests on, so each direction is pinned individually.
"""
from __future__ import annotations

from phronix import complexity, skills


def _subject(name, rules=0, instructions=0, pitfalls=0, lessons=0, references=0):
    return skills.define(
        name=name,
        description=f"A subject called {name}, described at sufficient length.",
        subject=name,
        instructions=[{"title": f"Step {i}", "body": "do a thing"}
                      for i in range(1, instructions + 1)] or None,
        rules=[{"title": f"Rule {i}", "body": "a constraint"}
               for i in range(1, rules + 1)] or None,
        references=[{"title": f"Ref {i}", "body": "see elsewhere"}
                    for i in range(1, references + 1)] or None,
        pitfalls=[{"title": f"Trap {i}", "body": "a trap"}
                  for i in range(1, pitfalls + 1)] or None,
        lessons=[{"title": f"Incident {i}", "body": "it broke"}
                 for i in range(1, lessons + 1)] or None,
    )


def _agent(name, level="level_2", skills_used=None, tools=None, intrinsic="moderate",
           prose="A short body."):
    from phronix.agents import define_agent

    return define_agent(
        name=name, description=f"An agent called {name}, described at length here.",
        model_level=level, sections=[{"title": "What you do", "body": prose}],
        tools=tools or [], skills=skills_used or [], sync=False,
    )


def _set_intrinsic(store, name, value):
    path = store / "agents" / f"{name}.yaml"
    lines = path.read_text().split("\n")
    idx = next(i for i, l in enumerate(lines) if l.startswith("model_level:"))
    lines.insert(idx + 1, f"intrinsic: {value}")
    path.write_text("\n".join(lines))


class TestSignalDirections:
    def test_more_rules_raise_the_score(self, isolated_layers):
        low = complexity.signals_for([], [], 0)["signals"]["reasoning_demand"]
        _subject("few", rules=1)
        _subject("many", rules=15)
        from phronix.skills import get

        few = complexity.signals_for([get("few")], [], 0)["signals"]["reasoning_demand"]
        many = complexity.signals_for([get("many")], [], 0)["signals"]["reasoning_demand"]
        assert low <= few < many

    def test_rules_weigh_double_against_instructions(self, isolated_layers):
        """A rule says what makes a reasonable action wrong; that is the judgment."""
        _subject("ruled", rules=4)
        _subject("stepped", instructions=4)
        from phronix.skills import get

        ruled = complexity.signals_for([get("ruled")], [], 0)["signals"]["reasoning_demand"]
        stepped = complexity.signals_for([get("stepped")], [], 0)["signals"]["reasoning_demand"]
        assert ruled == 2 * stepped

    def test_pitfalls_and_lessons_raise_the_score(self, isolated_layers):
        _subject("clean", rules=2)
        _subject("trappy", rules=2, pitfalls=6, lessons=6)
        from phronix.skills import get

        clean = complexity.score_from(
            complexity.signals_for([get("clean")], [], 0)["signals"])
        trappy = complexity.score_from(
            complexity.signals_for([get("trappy")], [], 0)["signals"])
        assert trappy > clean

    def test_mcp_tool_coverage_lowers_the_score(self, isolated_layers):
        """The only downward signal, and the lever the whole framework aims at."""
        _subject("s", rules=6)
        from phronix.skills import get

        subject = get("s")
        manual = complexity.score_from(
            complexity.signals_for([subject], ["Read", "Bash", "Edit"], 0)["signals"])
        tooled = complexity.score_from(
            complexity.signals_for(
                [subject], ["mcp__phronix__a", "mcp__phronix__b", "mcp__phronix__c"],
                0)["signals"])
        assert tooled < manual

    def test_no_tools_does_not_read_as_full_coverage(self, isolated_layers):
        """0/0 must not discount the requirement to zero."""
        assert complexity.signals_for([], [], 0)["signals"]["tool_coverage"] == 0.0

    def test_integration_breadth_rises_with_subjects_and_references(self, isolated_layers):
        _subject("one", rules=2)
        _subject("two", rules=2, references=4)
        from phronix.skills import get

        narrow = complexity.signals_for([get("one")], [], 0)["signals"]["integration_breadth"]
        broad = complexity.signals_for([get("one"), get("two")], [], 0)["signals"]["integration_breadth"]
        assert broad > narrow

    def test_unverified_subjects_raise_the_score(self, isolated_layers):
        """A claim that can be checked costs less judgment than one that cannot."""
        _subject("s", rules=3)
        from phronix.skills import get

        signals = complexity.signals_for([get("s")], [], 0)["signals"]
        assert signals["unverified_fraction"] == 1.0

    def test_prose_length_raises_the_score(self, isolated_layers):
        short = complexity.signals_for([], [], 100)["signals"]["instruction_load"]
        long = complexity.signals_for([], [], 9000)["signals"]["instruction_load"]
        assert long > short

    def test_signals_saturate_rather_than_run_away(self, isolated_layers):
        assert complexity.signals_for([], [], 10 ** 9)["signals"]["instruction_load"] == 1.0


class TestBanding:
    def test_bands_are_ordered_and_cover_the_range(self):
        assert complexity.level_for(0.0) == "level_1"
        assert complexity.level_for(0.30) == "level_2"
        assert complexity.level_for(0.50) == "level_3"
        assert complexity.level_for(1.0) == "level_4"

    def test_effort_tracks_the_same_score(self):
        assert complexity.effort_for(0.0) == "low"
        assert complexity.effort_for(0.9) == "max"

    def test_score_is_clamped(self):
        assert complexity.score_from({"reasoning_demand": 10.0}) == 1.0
        assert complexity.score_from({"tool_coverage": 10.0}) == 0.0


class TestIntrinsicFloor:
    def test_the_floor_raises_a_low_scoring_agent(self, isolated_layers):
        """A planner is level_4 work while loading one skill and calling tools."""
        _agent("planner-ish", level="level_4", tools=["mcp__phronix__a"])
        _set_intrinsic(isolated_layers["store"], "planner-ish", "max")
        result = complexity.assess_agent("planner-ish")
        assert result["level_from_scope"] == "level_1"
        assert result["recommended_level"] == "level_4"
        assert result["drift"] is False

    def test_measurement_can_raise_above_the_floor(self, isolated_layers):
        """The floor is a minimum, not a cap."""
        _subject("heavy", rules=20, pitfalls=12, lessons=8, references=8)
        _agent("loaded", level="level_4", skills_used=["heavy"], tools=["Read"],
               prose="x" * 9000)
        _set_intrinsic(isolated_layers["store"], "loaded", "low")
        result = complexity.assess_agent("loaded")
        assert result["intrinsic_floor"] == "level_1"
        assert result["recommended_level"] == "level_4"

    def test_the_floor_is_named_in_the_drivers(self, isolated_layers):
        _agent("floored", level="level_4")
        _set_intrinsic(isolated_layers["store"], "floored", "max")
        assert "intrinsic=max" in complexity.assess_agent("floored")["drivers"][0]

    def test_default_intrinsic_is_moderate(self, isolated_layers):
        _agent("plain", level="level_2")
        assert complexity.assess_agent("plain")["intrinsic"] == "moderate"


class TestDriftAndImpact:
    def test_drift_is_reported_when_the_declaration_is_stale(self, isolated_layers):
        _subject("heavy", rules=20, pitfalls=12, lessons=8)
        _agent("understated", level="level_1", skills_used=["heavy"], tools=["Read"])
        assert complexity.assess_agent("understated")["drift"] is True

    def test_reassess_all_lists_only_the_drifted(self, isolated_layers):
        _subject("heavy", rules=20, pitfalls=12, lessons=8)
        _agent("understated", level="level_1", skills_used=["heavy"], tools=["Read"])
        _agent("correct", level="level_2")
        report = complexity.reassess_all()
        drifted = {entry["agent"] for entry in report["drift"]}
        assert "understated" in drifted and "correct" not in drifted

    def test_agents_using_finds_the_dependents(self, isolated_layers):
        _subject("shared", rules=2)
        _agent("uses-it", skills_used=["shared"])
        _agent("does-not")
        assert complexity.agents_using("shared") == ["uses-it"]

    def test_impact_names_the_affected_agents(self, isolated_layers):
        _subject("shared", rules=2)
        _agent("uses-it", level="level_2", skills_used=["shared"])
        impact = complexity.impact_of("shared")
        assert impact["agents_affected"] == ["uses-it"]

    def test_a_skill_write_reports_its_impact(self, isolated_layers):
        """This is where the self-learning loop closes."""
        _subject("shared", rules=2)
        _agent("uses-it", level="level_2", skills_used=["shared"])
        result = skills.write_lesson("shared", "something broke today")
        assert result["complexity_impact"]["agents_affected"] == ["uses-it"]

    def test_assessment_is_deterministic(self, isolated_layers):
        _subject("s", rules=5, pitfalls=3)
        _agent("a", skills_used=["s"], tools=["Read", "mcp__phronix__x"])
        first = complexity.assess_agent("a")
        second = complexity.assess_agent("a")
        assert first == second


def test_assess_task_infers_subjects_from_the_description(isolated_layers):
    result = complexity.assess_task("how do I write a corrector for a lesson")
    assert result["status"] == "ok"
    assert "phronix-verification" in result["subjects"]
    assert result["recommended_level"] in complexity._LEVEL_ORDER


def test_a_missing_agent_is_reported_not_raised(isolated_layers):
    assert complexity.assess_agent("no-such-agent")["status"] == "not_found"
