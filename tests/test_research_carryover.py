"""Research has to survive the task that produced it, and be findable afterwards.

Two failures motivate this file, and both were silent — the system reported
success in each case.

The first: harvesting wrote a skill whose description was
``"What research established about ignore normalize paths."``. Retrieval scores
a skill's subject, description and Index rows, so a description made only of
words already in the name contributes nothing. A later task asking about
"ignore-paths not respected during recursive file discovery" scored the skill at
zero, reported a gap, and researched the subject again from scratch — with the
answer already in the store. Harvesting appeared to work; every block was
written; nothing was ever read back.

The second: the store lived in the run directory and was deleted with it, so
research bought at most one run and usually less, since a killed run contributed
nothing at all.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
from tests.skill_paths import skill_home_under, skill_names_under


def _record(store, topic="pylint-dev-pylint-7080"):
    """A research record shaped like the ones the benchmark actually produces."""
    directory = store / "research"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{topic}.json").write_text(json.dumps({
        "topic": topic,
        "slug": topic,
        "aspects": [
            {"name": "recursive-implementation",
             "question": "How does pylint implement recursive directory traversal "
                         "and where does it collect files?"},
            {"name": "ignore-paths-application",
             "question": "Where and when are ignore-paths patterns applied during "
                         "file collection?"},
        ],
        "approaches": [
            {"id": "A1", "name": "normalize-paths-before-ignore-check",
             "status": "confirmed", "measured": True,
             "hypothesis": "Paths are not normalised before the ignore check.",
             "source": "https://github.com/pylint-dev/pylint/pull/7080",
             "fom": 1.0},
        ],
        "fom": {"name": "target_tests_passing", "direction": "max", "target": 1.0,
                "measure": "fraction of target tests passing"},
        "corpus": {"dimensions": {"recursive_flag": [], "ignore_pattern_type": []}},
    }))
    return topic


def skill_text(name):
    """The instruction as an agent will receive it: pointer plus its skill.

    The stage prompts carry only the per-run INPUT now; the method lives in a
    skill, because a prompt in code is a method the system cannot edit — the
    learner improves skills, the graph indexes them, and reconcile keeps one
    copy of each fact, none of which reaches a string literal in a harness.
    So an assertion about what a stage is told has to read both halves.
    """
    from pathlib import Path
    root = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
            / "skills" / name / "SKILL.md")
    return root.read_text(encoding="utf-8")


def test_harvested_research_is_retrievable(isolated_layers):
    """The question a later task would ask must find what research established.

    Phrased as a bug report rather than in the skill's own vocabulary, because
    that is how the next task will arrive: it knows its symptom, not the name
    somebody else gave the subject.
    """
    from phronix import research, skills

    topic = _record(isolated_layers["store"])
    result = research.harvest(topic)
    assert result["status"] == "ok", result

    for question in (
        "pylint ignore-paths not respected during recursive file discovery",
        "ignore-paths regex does not match when using --recursive=y",
    ):
        found = skills.search(question, max_results=3)
        names = [hit.get("skill") for hit in found.get("results") or []]
        assert names, f"{question!r} found nothing — harvesting bought nothing"


def test_harvested_research_does_not_match_everything(isolated_layers):
    """The fix for the above must not be "make the description match any query".

    A skill that is retrieved for every question is as useless as one retrieved
    for none, and considerably more expensive.
    """
    from phronix import research, skills

    topic = _record(isolated_layers["store"])
    harvested = research.harvest(topic)["skill"]

    for unrelated in (
        "flask blueprint url_prefix is ignored when nesting blueprints",
        "sympy matrix determinant returns the wrong sign",
    ):
        found = skills.search(unrelated, max_results=3)
        names = [hit.get("skill") for hit in found.get("results") or []]
        assert harvested not in names, f"{harvested} leaked into {unrelated!r}"


def test_promotion_carries_the_run_and_not_the_framework(tmp_path):
    """A run contributes what it learned, and only what it learned.

    ``fresh_store`` seeds the bundled skills into every run store, so a naive
    promotion would copy the whole framework into the project layer, where it
    would shadow the bundled copy and then rot the moment the framework changed.
    """
    from phronix.layers import bundled_root
    from tests.benchmark.isolation import fresh_store, promote_store, seed_store

    first = tmp_path / "run1" / ".phronix"
    carry = tmp_path / "carry" / ".phronix"
    fresh_store(first)

    (first / "research").mkdir(parents=True, exist_ok=True)
    (first / "research" / "topic.json").write_text('{"topic": "topic"}')
    (skill_home_under(first, "learned-here")).mkdir(parents=True, exist_ok=True)
    (skill_home_under(first, "learned-here") / "SKILL.md").write_text("# learned\n")

    promoted = promote_store(first, carry)["promoted"]
    assert "research/topic.json" in promoted
    # An answer is promoted from its own home, not from `skills/`: that holds
    # only the framework's method, and a run's learning is an answer.
    assert "capabilities/skills/learned-here/SKILL.md" in promoted

    shipped = sorted(p.name for p in (bundled_root() / "skills").glob("*")
                     if p.is_dir())
    assert shipped, "expected the framework to ship skills"
    assert not any(f"skills/{name}/" in entry for entry in promoted
                   for name in shipped), promoted

    second = tmp_path / "run2" / ".phronix"
    fresh_store(second)
    seed_store(second, carry)
    assert (second / "research" / "topic.json").is_file()
    assert (skill_home_under(second, "learned-here") / "SKILL.md").is_file()


def test_amendment_to_a_bundled_skill_is_carried(tmp_path):
    """Improving a shipped skill is learning too, and must not be filtered out.

    The framework filter above works by comparing against the bundled copy, so a
    skill the run *modified* differs and travels. Getting this wrong in the other
    direction would silently discard the most valuable kind of learning: a
    correction to something the framework already teaches.
    """
    from phronix.layers import bundled_root
    from tests.benchmark.isolation import fresh_store, promote_store

    store = tmp_path / "run" / ".phronix"
    carry = tmp_path / "carry" / ".phronix"
    fresh_store(store)

    shipped = sorted(p.name for p in (bundled_root() / "skills").glob("*")
                     if p.is_dir())
    target = store / "skills" / shipped[0] / "LESSONS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text() if target.is_file() else ""
    target.write_text(existing + "\n## P99 — learned during the run\n")

    promoted = promote_store(store, carry)["promoted"]
    assert f"skills/{shipped[0]}/LESSONS.md" in promoted, promoted


def test_promotion_never_deletes(tmp_path):
    """Merge, never mirror: two runs finishing out of order must not erase
    each other's contributions."""
    from tests.benchmark.isolation import fresh_store, promote_store

    carry = tmp_path / "carry" / ".phronix"
    (skill_home_under(carry, "from-an-earlier-run")).mkdir(parents=True)
    (skill_home_under(carry, "from-an-earlier-run") / "SKILL.md").write_text("# earlier\n")

    store = tmp_path / "run" / ".phronix"
    fresh_store(store)
    (skill_home_under(store, "from-this-run")).mkdir(parents=True, exist_ok=True)
    (skill_home_under(store, "from-this-run") / "SKILL.md").write_text("# now\n")

    promote_store(store, carry)
    assert (skill_home_under(carry, "from-an-earlier-run") / "SKILL.md").is_file()
    assert (skill_home_under(carry, "from-this-run") / "SKILL.md").is_file()


def test_the_bare_arm_is_never_seeded():
    """Seeding the control with the treatment's learning would void the whole
    comparison, and nothing in the results would reveal it had happened."""
    from tests.benchmark.arms import build

    bare = build("opencode-bare", model="m", provider="p", base_url="u")
    assert not bare.uses_phronix


def _ranked_record(store, topic="ranked"):
    directory = store / "research"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{topic}.json").write_text(json.dumps({
        "topic": topic, "slug": topic,
        "aspects": [{"name": "ignore-paths-application",
                     "question": "Where are ignore-paths patterns applied during "
                                 "file collection?",
                     "where": "pylint config and file filtering logic"}],
        "fom": {"name": "target_tests_passing", "direction": "max", "target": 1.0,
                "measure": "fraction of target tests passing"},
        "corpus": {"dimensions": {"recursive_flag": []}},
        "approaches": [
            {"id": "A1", "name": "normalize-paths-before-ignore-check",
             "status": "potential", "measured": True,
             "metrics": {"target_tests_passing": 0.95},
             "hypothesis": "Paths are not normalised before the ignore check.",
             "summary": "expand_modules.py, before the ignore test",
             "source": "https://github.com/pylint-dev/pylint/pull/7080"},
            {"id": "A2", "name": "filter-in-recursive-loop",
             "status": "potential", "measured": True,
             "metrics": {"target_tests_passing": 0.40},
             "hypothesis": "Filter inside the walk instead.",
             "summary": "pylinter.py _discover_files"},
        ]}))
    return topic


def test_the_execution_plan_is_a_skill_holding_the_whole_research(isolated_layers):
    """The last stage produces the skill that solves the task, not a document.

    A plan scoped to one task is read once and dies with the run; the next task
    on the same subsystem then pays again for the same survey, the same aspects
    and the same evaluation. Filed as a skill under the subject, it is retrieved
    instead — so the test checks both that everything collected is present and
    that a later bug report actually finds it.
    """
    from phronix import research, skills

    topic = _ranked_record(isolated_layers["store"])
    result = research.playbook(topic)
    assert result["status"] == "ok", result

    text = (skill_home_under(isolated_layers["store"], result["skill"])
            / "SKILL.md").read_text()
    assert "How to solve" in text                     # the ranked approaches
    assert "How to evaluate" in text                  # the figure of merit
    assert "Sources consulted" in text                # where it came from
    assert "What has been investigated" in text       # ground already covered
    assert "normalize-paths-before-ignore-check" in text

    found = skills.search("ignore-paths not respected during recursive file discovery")
    assert result["skill"] in [h.get("skill") for h in found.get("results") or []]


def test_the_plan_ranks_by_measured_score(isolated_layers):
    """Best-first, and the ordering is arithmetic rather than argued."""
    from phronix import research

    topic = _ranked_record(isolated_layers["store"])
    ordered = research.playbook(topic)["ordered"]
    assert ordered == ["normalize-paths-before-ignore-check",
                       "filter-in-recursive-loop"], ordered


def test_every_approach_stays_potential_until_a_task_passes(isolated_layers):
    """Including the winner.

    Ranking first on a corpus the same session authored is a reason to try an
    approach first, not evidence that it is correct — the cases could have been
    shaped to suit it, and nothing in the record would show the difference.
    Solving the real task is what the corpus cannot fake.
    """
    from phronix import research

    topic = _ranked_record(isolated_layers["store"])
    research.playbook(topic)

    statuses = lambda: [a["status"] for a in research.load(topic)["approaches"]]
    assert statuses() == ["potential", "potential"], statuses()

    promoted = research.mark_working(topic)
    assert promoted["approach"] == "normalize-paths-before-ignore-check"
    assert statuses() == ["working", "potential"], statuses()


def test_marking_an_unknown_approach_says_so(isolated_layers):
    """Rather than silently promoting nothing, which would read as success."""
    from phronix import research

    topic = _ranked_record(isolated_layers["store"])
    result = research.mark_working(topic, "an-approach-nobody-proposed")
    assert result["status"] == "unknown"
    assert "normalize-paths-before-ignore-check" in result["known"]


def test_a_settled_aspect_is_found_across_topics(isolated_layers):
    """The lookup must cross topic boundaries or it never fires.

    Each task gets its own topic key, so a same-topic lookup would always miss:
    the second task on a subsystem would re-investigate ground the first one
    covered, at 300 seconds an aspect, three at a time.
    """
    from phronix import research

    store = isolated_layers["store"]
    (store / "research").mkdir(parents=True, exist_ok=True)
    (store / "research" / "first-task.json").write_text(json.dumps({
        "topic": "first-task", "slug": "first-task",
        "aspects": [{"name": "ignore-paths-application", "question": "Where?"}],
        "approaches": [{"name": "normalize-paths",
                        "aspect": "ignore-paths-application", "measured": True,
                        "status": "potential", "hypothesis": "not normalised",
                        "summary": "expand_modules.py", "source": "PR 7080"}]}))

    hit = research.settled_aspect("ignore-paths-application")
    assert hit is not None
    assert hit["from_topic"] == "first-task"
    assert "normalize-paths" in hit["findings"]


def test_an_unmeasured_aspect_is_not_settled(isolated_layers):
    """Investigated is not the same as established.

    An aspect that produced no measurement is unfinished. Treating it as settled
    would skip it on every future task and bury the fact that nobody ever got an
    answer.
    """
    from phronix import research

    store = isolated_layers["store"]
    (store / "research").mkdir(parents=True, exist_ok=True)
    (store / "research" / "first-task.json").write_text(json.dumps({
        "topic": "first-task", "slug": "first-task",
        "aspects": [{"name": "config-loading-order", "question": "How?"}],
        "approaches": [{"name": "reorder", "aspect": "config-loading-order",
                        "measured": False, "status": "potential"}]}))

    assert research.settled_aspect("config-loading-order") is None
    assert research.settled_aspect("never-investigated") is None


def test_filing_findings_is_never_truncated():
    """The investigation is on a clock; writing up what it found is not.

    A stage cut off mid-write-up loses everything the investigation paid for,
    which is strictly worse than not having investigated at all — the tokens are
    spent and nothing survives.
    """
    from tests.benchmark.arms import PhronixArm

    assert "build-solution" in PhronixArm.MUST_FINISH_STAGES
    assert "aspect" not in PhronixArm.MUST_FINISH_STAGES
    # The connective stages too: each one turns several paid-for stages into the
    # input for the next, so truncating one discards all of them.
    # `collect` is gone from the first pass — each aspect files its own
    # finding, so there was nothing left for it to reconcile. Its retry-path
    # counterpart survives, where several repairs DO have to be reconciled
    # against one failure.
    for stage in ("plan", "build-solution"):
        assert stage in PhronixArm.MUST_FINISH_STAGES, stage


def test_every_stage_the_driver_runs_has_a_budget():
    """A missing budget is a KeyError in the middle of a research pass."""
    from tests.benchmark.arms import PhronixArm

    # The pipeline is five stages: `survey` folded into `plan`, `collect`
    # dropped because each aspect files its own finding, `evaluate` dropped
    # because `tune` already measures against the corpus.
    for stage in ("plan", "explore"):
        assert stage in PhronixArm.STAGE_BUDGETS, stage

    # And `solution-skill` must NOT have one: it writes up what the timed
    # phases collected, so a budget there would put the write-up on a clock.
    assert "build-solution" not in PhronixArm.STAGE_BUDGETS
    assert "build-solution" in PhronixArm.UNTIMED_STAGES


def test_the_agents_own_summary_wins_over_a_derived_one():
    """A reconstruction of intent from a command line is a guess; the agent's
    own sentence is not."""
    from tests.benchmark.arms import LOG_SUMMARY_CHARS, describe_call

    stated = describe_call({"tool": "bash", "state": {"input": {
        "command": "cd /somewhere/long && pytest -k ignore_path",
        "description": "check ignore-paths is applied before recursive discovery"}}})
    assert "check ignore-paths is applied" in stated
    assert "pytest -k" not in stated

    # Without one, the fallback still says what is happening rather than how it
    # was spelled: a trace of flags and absolute paths is a trace nobody reads.
    derived = describe_call({"tool": "bash", "state": {"input": {
        "command": "cd /somewhere/long && pytest -k ignore_path"}}})
    assert derived == "running the test suite"
    assert "pytest" not in derived and "/somewhere/long" not in derived

    long_one = describe_call({"tool": "bash", "state": {"input": {
        "command": "x", "description": "y" * 300}}})
    assert len(long_one) <= LOG_SUMMARY_CHARS + 40


def test_both_harnesses_describe_the_same_call_the_same_way():
    """One describer, two adapters.

    This was written twice, once per harness event shape, and the copies drifted
    at once: a fix to how a search reads landed in one and not the other, so the
    same agent doing the same thing produced different trace lines depending on
    which harness ran it, and the runs stopped being comparable by eye.
    """
    from tests.benchmark.arms import describe_call, describe_claude_call

    for name, args in (("bash", {"command": "pytest tests/test_cli.py"}),
                       ("grep", {"pattern": "load_dotenv", "path": "src"}),
                       ("read", {"file_path": "/a/b/cli.py"})):
        opencode = describe_call({"tool": name, "state": {"input": args}})
        claude = describe_claude_call({"name": name, "input": args})
        assert opencode == claude, name


def test_commentary_is_prose_not_markdown():
    """The model writes headings, bullets and code spans; a trace reads none of
    them well."""
    from tests.benchmark.arms import LOG_SUMMARY_CHARS, say

    assert say("## Analysis") == ""
    assert say("```python\nx = 1\n```") == ""
    spoken = say("- **Root cause**: `load_dotenv` runs before the CLI defaults")
    assert spoken == "Root cause: load_dotenv runs before the CLI defaults"
    assert len(say("word " * 200)) <= LOG_SUMMARY_CHARS + 1


def _accumulated(store):
    """Two subsystems' worth of earlier research, as several runs would leave it."""
    directory = store / "research"
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in {
        "pylint-7080": {
            "aspects": [{"name": "ignore-paths-application",
                         "question": "Where are ignore-paths applied during "
                                     "recursive file discovery?"}],
            "approaches": [
                {"name": "normalize-paths-before-ignore-check",
                 "aspect": "ignore-paths-application", "measured": True,
                 "status": "working", "source": "PR 7080",
                 "hypothesis": "paths are not normalised before the ignore check"},
                {"name": "filter-inside-the-recursive-loop",
                 "aspect": "ignore-paths-application", "measured": True,
                 "status": "falsified",
                 "hypothesis": "filter during the walk instead"}]},
        "flask-5063": {
            "aspects": [{"name": "blueprint-nesting",
                         "question": "How are nested blueprint url prefixes "
                                     "composed?"}],
            "approaches": [{"name": "join-prefixes-at-registration",
                            "aspect": "blueprint-nesting", "measured": True,
                            "status": "potential",
                            "hypothesis": "prefixes join at registration"}]},
    }.items():
        body.update({"topic": name, "slug": name,
                     "fom": {"name": "target_tests_passing", "direction": "max",
                             "target": 1.0}})
        (directory / f"{name}.json").write_text(json.dumps(body))


def test_prior_work_finds_earlier_research_for_a_new_task(isolated_layers):
    """The lookup that makes carried research worth carrying.

    Every other lookup is keyed on the current topic, which is new by
    construction, so without this one a pass opens by surveying a subject the
    store already covers — which is what was happening.
    """
    from phronix import research

    _accumulated(isolated_layers["store"])
    found = research.prior_work(
        "pylint ignore-paths not respected during recursive file discovery")

    assert found["status"] == "ok"
    assert "normalize-paths-before-ignore-check" in found["already_tried"]
    assert found["known_working"] == ["normalize-paths-before-ignore-check"]
    assert found["known_refuted"] == ["filter-inside-the-recursive-loop"]
    assert "ignore-paths-application" in found["settled_aspects"]


def test_prior_work_does_not_offer_an_unrelated_subject(isolated_layers):
    """Reuse must be precise.

    A lookup that returns everything would be worse than none: the pass would
    plan around findings from a different subsystem, and the wrongness would be
    invisible because the output still looks like informed reuse.
    """
    from phronix import research

    _accumulated(isolated_layers["store"])

    flask = research.prior_work("nested flask blueprints lose their url prefix")
    assert [t["topic"] for t in flask["topics"]] == ["flask-5063"]

    unrelated = research.prior_work(
        "sympy simplify returns an unevaluated integral")
    assert unrelated["topics"] == []
    assert unrelated["already_tried"] == []
    assert "research it properly" in unrelated["advice"]


def test_one_subject_gets_one_skill_however_the_words_are_ordered(isolated_layers):
    """Two runs on the same subsystem must accumulate, not fork.

    The name was built by joining the shared vocabulary in frequency order, so
    it depended on how many approaches happened to mention each word. Two runs
    produced `ignore-normalize-paths` and `normalize-ignore-paths`: three words,
    two skills, and the carried research split across both — the exact "second
    parallel account of the same thing" the researcher is warned about, arriving
    by accident.
    """
    from phronix.research import _subject_of

    first = {"approaches": [{"name": "normalize-paths"},
                            {"name": "normalize-ignore"}],
             "aspects": [{"name": "ignore-paths"}, {"name": "paths-ignore"}]}
    second = {"approaches": [{"name": "ignore-paths"},
                             {"name": "ignore-normalize"}],
              "aspects": [{"name": "normalize-paths"},
                          {"name": "paths-normalize"}]}

    assert _subject_of(first, "t") == _subject_of(second, "t")


def test_an_existing_skill_is_reused_whatever_order_it_named_things(isolated_layers):
    """Stable ordering fixes new names; this fixes the ones already in the store.

    Without it, every record written before the ordering was stable would fork a
    second skill the first time it was re-harvested.
    """
    from phronix.research import _subject_of

    existing = skill_home_under(isolated_layers["store"], "normalize-ignore-paths")
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text(
        "---\nname: normalize-ignore-paths\ndescription: from an earlier run\n"
        "subject: normalize-ignore-paths\ntype: skill\n---\n\n"
        "## Instructions\n\n### I1 — something\n\nbody\n")

    record = {"approaches": [{"name": "normalize-paths"},
                             {"name": "normalize-ignore"}],
              "aspects": [{"name": "ignore-paths"}, {"name": "paths-ignore"}]}
    assert _subject_of(record, "t") == "normalize-ignore-paths"


def test_every_result_attribute_the_runner_assigns_exists_on_taskresult():
    """A typo in bookkeeping must not be able to delete a finished task.

    ``result.raw["promoted"] = ...`` was written against a field TaskResult does
    not have. It raised after the task had PASSED, the exception escaped to the
    per-ARM handler, and the phronix arm died at task 0 — losing the pass it had
    just earned and the five tasks it had not started. The bare arm finished
    normally alongside it, so the run produced a report of 1/6 against 0/6 that
    read as a result rather than as a crash.

    Greps the source rather than exercising the paths, because most of them need
    a container, and an assignment that only runs on the promotion path is
    exactly the one nobody exercises before a long run.
    """
    import re
    from pathlib import Path

    from tests.benchmark.metrics import TaskResult

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    # Assignments only. `result` also names subprocess results in this file, so
    # matching reads too would flag `result.stderr[-400:]` on a CompletedProcess.
    assigned = set(re.findall(r"\bresult\.([a-z_]+)\s*=(?!=)", source))
    assigned |= set(re.findall(r"\bresult\.([a-z_]+)\[[^\]]*\]\s*=(?!=)", source))

    known = set(TaskResult("x").__dict__)
    missing = sorted(assigned - known)
    assert not missing, f"runner.py assigns TaskResult fields that do not exist: {missing}"


def test_bookkeeping_failures_do_not_lose_the_task(tmp_path, monkeypatch):
    """Promotion raising must cost the promotion, not the result."""
    from tests.benchmark import runner as runner_module

    def explode(*_args, **_kwargs):
        raise RuntimeError("the carry root went away mid-run")

    monkeypatch.setattr(runner_module, "promote_store", explode)

    # The guard is in the source; assert it surrounds the call rather than
    # re-running a whole task, which needs a container.
    source = (tmp_path / "x")  # placeholder to keep the fixture honest
    text = runner_module.__file__
    body = open(text).read()
    # Anchored on the PROMOTION site specifically: `carry_root` is consulted in
    # more than one place now, and slicing from the first match once landed on
    # the fresh-mode seeding block instead.
    block = body[body.index("promoted = promote_store(") - 400:]
    block = block[:block.index("return result")]
    assert "try:" in block and "except Exception" in block, block[:400]


def test_an_evaluator_worktree_carries_the_harness_scaffolding():
    """An evaluator without `.opencode/` has no phronix tools, and says nothing.

    `git worktree add` checks out HEAD; the harness writes `.opencode/` into the
    checkout afterwards, so it is not in HEAD and not in the worktree. The
    project config is where the phronix MCP server is declared, so an evaluator
    started in a bare worktree comes up with none of the research tools and
    cannot record a trial.

    It fails quietly: the stage exits in about two seconds having recorded
    nothing, and the build stage then constructs the solution out of however
    many findings did survive — without any signal that an idea was explored by
    an agent that could not write down what it found.
    """
    import re
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    # `private_tree` is what hands an explorer its worktree, and exploring is
    # the only stage that takes one now.
    block = source[source.index("tree = checkout / SCRATCH_DIR"):]
    block = block[:block.index("        def drop_tree(")]

    assert ".opencode" in block, "the worktree never gets the project config"
    assert "symlink_to" in block or "copytree" in block, block[-400:]


def _session(monkeypatch, name, reuse=False):
    monkeypatch.setenv("PHRONIX_RESEARCH_SESSION", name)
    if reuse:
        monkeypatch.setenv("PHRONIX_RESEARCH_REUSE", "1")
    else:
        monkeypatch.delenv("PHRONIX_RESEARCH_REUSE", raising=False)


def test_a_session_sees_only_its_own_research(isolated_layers, monkeypatch):
    """Isolation has to be at the storage layer, not at the prompt.

    A run told to explore fresh, but able to read earlier research, will read
    it — and then it cannot answer the question it was set up to ask. So the
    session writes to its own folder and, without reuse, that folder is all it
    can see.
    """
    from phronix import research

    _session(monkeypatch, "run-alpha")
    research.add_approach("pylint-ignore", "normalize-paths",
                          "normalise before the ignore check",
                          hypothesis="paths are not normalised", source="PR 7080")
    assert research.list_topics() == ["pylint-ignore"]

    _session(monkeypatch, "run-beta")
    assert research.list_topics() == [], "a fresh session saw another's work"


def test_reuse_gathers_across_every_session(isolated_layers, monkeypatch):
    """"Reuse" means all session folders, not just the common one.

    A session that has not been synced yet still holds real findings, and the
    run that could use them is usually the one happening while it is still
    unsynced.
    """
    from phronix import research

    _session(monkeypatch, "run-alpha")
    research.add_approach("pylint-ignore", "normalize-paths",
                          "normalise before the ignore check",
                          hypothesis="paths are not normalised", source="PR 7080")

    _session(monkeypatch, "run-beta", reuse=True)
    assert research.list_topics() == ["pylint-ignore"]
    found = research.prior_work("pylint ignore paths normalise")
    assert "normalize-paths" in found["already_tried"]


def test_sync_folds_a_session_into_the_common_folder(isolated_layers, monkeypatch):
    """And leaves the session behind, since sessions are not what gets committed."""
    from phronix import research

    _session(monkeypatch, "run-alpha")
    research.add_approach("pylint-ignore", "normalize-paths",
                          "normalise before the ignore check",
                          hypothesis="paths are not normalised", source="PR 7080")
    result = research.sync_session("run-alpha")
    assert result["synced"] == ["pylint-ignore"]

    common = isolated_layers["store"] / "research"
    # One directory per SUBJECT: the record sits beside the skill it produced,
    # so a subject is one place rather than a file here and a skill elsewhere.
    assert (common / "skills" / "pylint-ignore" / "record.json").is_file()
    assert (common / "sessions" / "run-alpha").is_dir()

    # A brand-new session with reuse now finds it via the common folder.
    _session(monkeypatch, "run-gamma", reuse=True)
    assert research.list_topics() == ["pylint-ignore"]
    _session(monkeypatch, "run-gamma")
    assert research.list_topics() == []


def test_sync_merges_rather_than_overwrites(isolated_layers, monkeypatch):
    """Two sessions on one subject is normal as soon as a task list repeats a
    subsystem, and a plain copy lets whichever synced last erase the other."""
    from phronix import research

    _session(monkeypatch, "run-alpha")
    research.add_approach("shared", "approach-a", "does A", hypothesis="a")
    research.sync_session("run-alpha")

    _session(monkeypatch, "run-beta")
    research.add_approach("shared", "approach-b", "does B", hypothesis="b")
    research.sync_session("run-beta")

    common = json.loads(
        (isolated_layers["store"] / "research" / "skills" / "shared"
         / "record.json").read_text())
    names = sorted(a["name"] for a in common["approaches"])
    assert names == ["approach-a", "approach-b"], names


def test_writes_never_land_outside_the_current_session(isolated_layers, monkeypatch):
    """A record read from elsewhere is written back into THIS session.

    Otherwise a reusing run would edit another session's history in place, and
    the isolation would leak backwards: an earlier run's record would change
    after the fact, with nothing recording that it had.
    """
    from phronix import research

    _session(monkeypatch, "run-alpha")
    research.add_approach("shared", "approach-a", "does A", hypothesis="a")

    _session(monkeypatch, "run-beta", reuse=True)
    research.add_approach("shared", "approach-b", "does B", hypothesis="b")

    sessions = isolated_layers["store"] / "research" / "sessions"
    alpha = json.loads(
        (sessions / "run-alpha" / "skills" / "shared" / "record.json").read_text())
    assert [a["name"] for a in alpha["approaches"]] == ["approach-a"]
    assert (sessions / "run-beta" / "skills" / "shared" / "record.json").is_file()


def test_reuse_is_the_default_and_fresh_is_explicit():
    """Not paying twice for research is the point of keeping it."""
    from tests.benchmark.runner import RunConfig

    assert RunConfig(tasks=[]).research_reuse is True
    assert RunConfig(tasks=[]).research_on_retry is False


def test_fresh_seeds_only_the_framework(tmp_path):
    """`--fresh` must ignore task-specific skills and research, not the framework.

    A run with no bundled skills is not a clean evaluation of the approach; it
    is an evaluation of a different, crippled system.

    "The framework" is the pipeline's own skills, and nothing else in the
    bundle. This once asserted that everything shipped was seeded, which made
    the bundle's contents the definition of clean — so when two task skills
    were committed into the skeleton, every fresh run inherited a write-up of
    two of the tasks it was about to be measured on, and this test agreed.
    """
    from phronix.layers import bundled_root
    from tests.benchmark.isolation import fresh_store

    store = tmp_path / "run" / ".phronix"
    fresh_store(store)

    shipped = {p.name for p in (bundled_root() / "skills").glob("*") if p.is_dir()}
    seeded = {p.name for p in (store / "skills").glob("*") if p.is_dir()}
    framework = {name for name in shipped if name.startswith("phronix-")}

    assert framework and framework <= seeded, "the pipeline's own skills must be seeded"
    assert not (seeded - framework), (
        f"a fresh run inherited non-framework skills: {sorted(seeded - framework)}")
    assert not list((store / "research").glob("*.json"))
    assert not list((store / "capabilities").glob("*.py")), (
        "a fresh run must author its own tools, not inherit an earlier run's")


def test_fresh_ignores_the_learned_folder_entirely(tmp_path):
    """`--fresh` must not seed skills OR research from earlier runs.

    Both, not just research: a task-specific skill written by an earlier run
    carries the same answer the research does, so seeding skills while withholding
    research would leave the run "fresh" in name only — and the leak would be
    invisible, because a seeded skill looks identical to one the framework ships.
    """
    from tests.benchmark.isolation import fresh_store, promote_store, seed_store

    carry = tmp_path / "carry" / ".phronix"
    earlier = tmp_path / "earlier" / ".phronix"
    fresh_store(earlier)
    (skill_home_under(earlier, "learned-last-time")).mkdir(parents=True, exist_ok=True)
    (skill_home_under(earlier, "learned-last-time") / "SKILL.md").write_text("# learned\n")
    (earlier / "research").mkdir(parents=True, exist_ok=True)
    (earlier / "research" / "topic.json").write_text('{"topic": "topic"}')
    promote_store(earlier, carry)

    # Fresh: fresh_store only, no seed_store — what the runner does when
    # research_reuse is off.
    store = tmp_path / "fresh-run" / ".phronix"
    fresh_store(store)
    assert not (skill_home_under(store, "learned-last-time")).exists()
    assert not list((store / "research").glob("*.json"))

    # Reuse: the same carry root, seeded.
    reusing = tmp_path / "reusing-run" / ".phronix"
    fresh_store(reusing)
    seed_store(reusing, carry)
    assert (skill_home_under(reusing, "learned-last-time") / "SKILL.md").is_file()
    assert (reusing / "research" / "topic.json").is_file()


def test_session_working_state_is_not_promoted(tmp_path):
    """Sessions are working state; the common folder is the result.

    Promoting session folders would commit the intermediate state of every run
    that ever started, and `research/sessions/` is git-ignored precisely so that
    does not happen.
    """
    from tests.benchmark.isolation import fresh_store, promote_store

    store = tmp_path / "run" / ".phronix"
    carry = tmp_path / "carry" / ".phronix"
    fresh_store(store)
    sessions = store / "research" / "sessions" / "run-alpha"
    sessions.mkdir(parents=True)
    (sessions / "topic.json").write_text('{"topic": "topic"}')
    (store / "research" / "topic.json").write_text('{"topic": "topic"}')

    promoted = promote_store(store, carry)["promoted"]
    assert "research/topic.json" in promoted
    assert not any("sessions/" in entry for entry in promoted), promoted


def test_repeated_harvests_write_one_skill(isolated_layers):
    """Harvest runs after every stage; it must not found a new skill each time.

    The name came from the record's shared vocabulary, and that vocabulary
    shifts as approaches accumulate — so a six-task run produced thirty-two
    skills: `column-domain`, `column-domain-rule`, `based-column-domain`,
    `cases-column-domain`, `discover-normalize`, `discover-normalize-pattern`,
    and one called `check`. The task's knowledge ends up smeared across
    fragments, none complete, and there is no single skill to point the solve
    step at.
    """
    from phronix import research

    research.define_fom("t", "target_tests_passing", "max", 1.0, "run the tests")
    for name, aspect in (("discover-normalize-paths", "discovery"),
                         ("column-domain-check", "domain"),
                         ("normalize-return-value", "returns"),
                         ("check-function-boundary", "boundary")):
        research.add_approach("t", name, f"changes the {aspect}",
                              hypothesis=f"the {aspect} is wrong", source="probe")
        research.harvest("t")

    skills = skill_names_under(isolated_layers["store"])
    assert len(skills) == 1, skills


def test_the_topic_skill_is_pinned_and_readable(isolated_layers):
    """The harness names the skill in the solve prompt, so it has to be able to
    ask which one it is."""
    from phronix import research

    research.define_fom("t", "target_tests_passing", "max", 1.0, "run the tests")
    research.add_approach("t", "an-approach", "does a thing", hypothesis="h",
                          source="probe")
    harvested = research.harvest("t")["skill"]

    assert research.topic_skill("t") == harvested
    # Stable across further harvests.
    research.add_approach("t", "another-approach", "does another thing",
                          hypothesis="h2", source="probe")
    research.harvest("t")
    assert research.topic_skill("t") == harvested


def test_the_solve_step_is_pointed_at_the_skill_not_the_record():
    """The record is tens of KB of working detail the skill already summarises.

    Reading it back into the solve step is the token cost that made a researched
    attempt no cheaper than an unresearched one.
    """
    from tests.benchmark.arms import PHRONIX_PLAN_SUFFIX

    assert "{skill}" in PHRONIX_PLAN_SUFFIX
    assert "skill_load" in PHRONIX_PLAN_SUFFIX
    assert "Do not call `research_status`" in PHRONIX_PLAN_SUFFIX


def test_an_attempt_that_never_ran_is_not_a_stall():
    """Three 429s in a row ended a task that had had two real attempts.

    Each void attempt produced no patch, so all three hashed to the same empty
    digest and the stall detector read infrastructure failure as the agent going
    in circles — the one conclusion the data did not support.
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    block = source[source.index("patch_digest = _digest(patch_text)"):]
    block = block[:block.index("repeated = patch_digest in seen_patches")]
    assert "never_ran" in block and "continue" in block, block


def test_the_checkpoint_records_state_and_references_not_content(isolated_layers):
    """A retry must be able to resume rather than rebuild.

    The record runs to tens of kilobytes of working detail; pasting it into the
    next pass is what made a retry cost as much as a first attempt. The
    checkpoint states what is established, what is open and what is dead, and
    then *points* at where the detail lives.
    """
    from phronix import research

    research.define_fom("t", "target_tests_passing", "max", 1.0, "run the tests")
    research.set_aspects("t", [{"name": "answered", "question": "q1"},
                               {"name": "unanswered", "question": "q2"}])
    research.add_approach("t", "candidate", "in module a", hypothesis="h",
                          source="https://example.invalid/pr/1", aspect="answered")

    result = research.checkpoint("t")
    assert result["status"] == "ok"

    text = (skill_home_under(isolated_layers["store"], result["skill"])
            / "SKILL.md").read_text()
    assert "Where research on this subject stands" in text
    assert "Still open" in text
    assert "aspect not yet answered: unanswered" in text
    assert "https://example.invalid/pr/1" in text      # a reference, not the detail
    assert "Where the detail is" in text


def test_the_checkpoint_survives_a_pass_that_never_finished(isolated_layers):
    """It is written after every stage precisely so a truncated pass still
    leaves the next one somewhere to start."""
    from phronix import research

    # Only a survey's worth of state: no figure of merit measured, one candidate.
    research.define_fom("t", "target_tests_passing", "max", 1.0, "run the tests")
    research.add_approach("t", "early-guess", "somewhere", hypothesis="h",
                          source="issue tracker")
    assert research.checkpoint("t")["status"] == "ok"

    record = research.load("t")
    assert record["checkpoint"]["open"] >= 1


def test_research_time_accumulates_with_retries():
    """The tasks that need research most are the ones still failing on try four.

    A flat per-task budget gave them the least: sympy-24066 spent its whole
    allowance early, then made three more attempts with no ability to revise an
    approach that had already failed three times.
    """
    from tests.benchmark.arms import build

    arm = build("opencode-phronix", model="m", provider="p", base_url="u")
    first = arm.research_allowance(1)
    assert arm.research_allowance(2) == 2 * first
    assert arm.research_allowance(5) == 5 * first


def test_a_retry_is_told_to_resume_from_the_checkpoint():
    """Otherwise each attempt re-derives what the last one established."""
    from tests.benchmark.arms import PhronixArm

    note = PhronixArm.RESUME_NOTE
    assert "Where research on this subject stands" in note
    assert "{skill}" in note
    assert "Do not re-establish" in note


def _three_approaches(research, topic="t"):
    research.define_fom(topic, "target_tests_passing", "max", 1.0, "run the test")
    for name in ("normalise-at-the-source", "filter-in-the-walk",
                 "fix-the-comparison"):
        research.add_approach(topic, name, f"where {name} goes",
                              hypothesis=f"h for {name}", source="probe")
    return topic


def test_each_approach_gets_a_stable_key(isolated_layers):
    """Keys are four characters; names are not.

    Everything that refers to an approach — the ranked plan, the checkpoint, the
    record of what a task tried — had to spell out a full name. And a key is
    what lets the solve step say which candidate it is on without carrying that
    candidate's description around.
    """
    from phronix import research

    topic = _three_approaches(research)
    keys = [a["key"] for a in research.load(topic)["approaches"]]
    assert keys == ["A1", "A2", "A3"], keys

    # Re-recording the same approach keeps its key: a reused key would redirect
    # every existing reference to different content.
    research.add_approach(topic, "filter-in-the-walk", "revised summary",
                          hypothesis="revised", source="probe")
    by_name = {a["name"]: a["key"] for a in research.load(topic)["approaches"]}
    assert by_name["filter-in-the-walk"] == "A2"


def test_an_approach_can_be_fetched_by_key_alone(isolated_layers):
    """The solve step needs the detail of the candidate it is ON, not of the
    four it might reach later."""
    from phronix import research

    topic = _three_approaches(research)
    found = research.approach_detail(topic, "A2")
    assert found["status"] == "ok"
    assert found["approach"]["name"] == "filter-in-the-walk"
    assert research.approach_detail(topic, "A9")["status"] == "unknown"


def test_a_failed_approach_is_marked_and_then_refused(isolated_layers):
    """Only the success case existed, so "tried and lost" was indistinguishable
    from "never tried" — same status, same rank, proposed again next round."""
    from phronix import research

    topic = _three_approaches(research)
    research.mark_attempt_outcome(topic, "A1", worked=False,
                                  evidence="target test still failing")

    assert research.dead_approaches(topic) == ["A1:normalise-at-the-source"]

    again = research.add_approach(topic, "normalise-at-the-source", "same idea",
                                  hypothesis="h")
    assert again["status"] == "error"
    assert "already tried" in again["error"]

    # And something genuinely different is still welcome.
    assert research.add_approach(topic, "look-somewhere-else", "elsewhere",
                                 hypothesis="h2")["status"] == "ok"


def test_the_next_attempt_follows_the_next_live_approach(isolated_layers):
    """Not the one that just lost."""
    from phronix import research

    topic = _three_approaches(research)
    assert research.attempted_approach(topic) == "normalise-at-the-source"
    research.mark_attempt_outcome(topic, "A1", worked=False, evidence="failed")
    assert research.attempted_approach(topic) == "filter-in-the-walk"


def test_the_plan_never_lists_a_dead_approach_as_a_thing_to_try(isolated_layers):
    """Ranking sorts on the metric, and a failed approach keeps whatever it
    scored — so it was being numbered first in a list headed "try these in
    order", which is the loop this all exists to break."""
    from phronix import research

    topic = _three_approaches(research)
    research.mark_attempt_outcome(topic, "A1", worked=False, evidence="failed")
    research.playbook(topic)

    text = (skill_home_under(isolated_layers["store"],
                             research.topic_skill(topic))
            / "SKILL.md").read_text()
    ordered = text[text.index("1. `A"):text.index("**Already tried")]
    assert "A1" not in ordered, ordered
    assert "A2" in ordered and "A3" in ordered
    assert "`A1` normalise-at-the-source" in text     # listed, but as dead


def test_a_generated_block_refreshes_instead_of_going_stale(isolated_layers):
    """`write_block` reported `already_present` and changed nothing, so the
    checkpoint froze at whatever the first research stage wrote — every retry
    resumed from a picture several stages out of date, while reporting success.
    """
    from phronix import research, skills

    topic = _three_approaches(research)
    research.checkpoint(topic)
    research.mark_attempt_outcome(topic, "A1", worked=False,
                                  evidence="target test still failing")
    result = research.checkpoint(topic)
    assert result["block"] == "ok"

    text = (skill_home_under(isolated_layers["store"],
                             research.topic_skill(topic))
            / "SKILL.md").read_text()
    assert text.count("— Where research on this subject stands") == 1
    assert "A1" not in text.split("**Still open**")[1].split("**")[0]
    assert "target test still failing" in text

    # And the no-replace default still protects agent-written blocks.
    skills.write_block("some-skill", "rule", "A rule", "first body")
    second = skills.write_block("some-skill", "rule", "A rule", "second body")
    assert second["status"] == "already_present"


def test_the_solve_step_escalates_one_approach_at_a_time():
    """Reading every approach up front costs context on every task, including
    the ones the first approach solves — which is most of them."""
    from tests.benchmark.arms import PHRONIX_PLAN_SUFFIX

    assert "research_approach" in PHRONIX_PLAN_SUFFIX
    assert "One approach at a time" in PHRONIX_PLAN_SUFFIX
    assert "Only if it fails" in PHRONIX_PLAN_SUFFIX


def test_preflight_refuses_to_start_when_the_model_is_refusing(monkeypatch, tmp_path):
    """A run whose provider 429s produces attempt after attempt of "1 step, 0
    tokens" — indistinguishable from an agent that ran and did nothing.

    It happened twice. Once it took out three attempts of one task and was read
    as the agent going in circles; once it took out an entire run, both arms,
    before anyone read the trace. The provider says exactly what is wrong, and
    that message belongs before the run rather than buried in a transcript.
    """
    import io
    import json
    import urllib.error
    import urllib.request

    from tests.benchmark.runner import RunConfig, Runner

    runner = Runner.__new__(Runner)
    runner.config = RunConfig(tasks=["x"], out=tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "probe-key")

    def refuse(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "u", 429, "Too Many Requests", {},
            io.BytesIO(json.dumps({"error": {
                "message": "Budget has been exceeded! Max budget: 500.0"}}).encode()))

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    problem = runner._model_reachable()
    assert "429" in problem and "Budget has been exceeded" in problem

    # A healthy endpoint blocks nothing.
    class _Ok:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Ok())
    assert runner._model_reachable() == ""

    # Neither does a probe that simply cannot run — that is not evidence.
    def explode(*_args, **_kwargs):
        raise OSError("no route to host")

    monkeypatch.setattr(urllib.request, "urlopen", explode)
    assert runner._model_reachable() == ""


def test_research_that_never_started_stops_the_whole_run():
    """A phronix arm whose research never runs is not phronix.

    It degrades into a plain agent with extra scaffolding, and every number it
    then produces gets attributed to phronix — the most misleading state this
    benchmark can be in, because it looks like a result rather than a fault.

    It has happened twice for unrelated reasons: an exhausted API key, and a
    command built with the wrong harness's flags. Both times the run continued
    and the trace said "no phronix tools called", which reads as an agent
    ignoring its tools rather than one that never started.
    """
    from pathlib import Path

    from tests.benchmark.runner import ResearchCollapsed

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()

    # Raised when a phronix research pass reports no tool calls at all.
    assert "raise ResearchCollapsed(" in source
    assert 'not (research.get("steps") or 0)' in source

    # And it survives both handlers that would otherwise swallow it: the
    # per-attempt one ("a crashed attempt is data") and the per-arm one ("one
    # arm failing must not void the others").
    # Both harness-level failures are handled at the same two sites, and
    # neither is swallowed: the per-attempt handler ("a crashed attempt is
    # data") and the per-arm one ("one arm failing must not void the others").
    assert source.count("except (ResearchCollapsed, EnvironmentGone)") == 2
    assert "raise collapsed" in source
    assert issubclass(ResearchCollapsed, RuntimeError)


def test_every_harness_builds_its_own_command_for_every_phase():
    """Research and learn built opencode syntax inline while only the attempt
    path went through the seam, so the Claude arm invoked the Claude binary with
    `run --dir ... --auto --format json`. It exited in seven seconds with empty
    output — a half-supported harness, which is worse than an unsupported one.
    """
    from pathlib import Path

    from tests.benchmark.arms import build

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    # Only the two harnesses' own agent_command may name the binary.
    assert source.count("self.opencode_bin,") == 2, (
        "a phase is building a harness command inline again")

    for name in ("opencode-phronix", "claude-phronix"):
        arm = build(name, model="m", provider="p", base_url="u")
        command = arm.agent_command("p", Path("/w"), arm.attachments([Path("/f")]), "a")
        assert command[0], name
        assert any("/f" in part for part in command), (name, command)


def test_research_calls_counted_for_both_harness_stream_shapes():
    """The counter read only opencode's event shape.

    Claude Code emits tool calls as `tool_use` blocks inside an assistant
    message, so every Claude research pass reported zero tools while the trace
    showed a dozen. That string — "no phronix tools called" — is the diagnostic
    for research that never ran, the one harness-level failure this benchmark
    must not miss. Printing it on healthy passes trains the reader to ignore
    the only warning that matters.
    """
    import json

    from tests.benchmark.arms import PhronixOpenCodeArm

    opencode = json.dumps({"part": {"type": "tool",
                                    "tool": "mcp__phronix__research_rank"}})
    claude = json.dumps({
        "type": "assistant",
        "message": {"content": [
            {"type": "text", "text": "ranking now"},
            {"type": "tool_use", "name": "mcp__phronix__research_playbook"},
            {"type": "tool_use", "name": "Bash"},
        ]},
    })

    counts = PhronixOpenCodeArm._count_research_calls("\n".join([opencode, claude, "junk"]))
    assert counts == {"mcp__phronix__research_rank": 1,
                      "mcp__phronix__research_playbook": 1}, counts


def test_attempt_time_and_cost_separate_research_from_solving():
    """Research runs inside the attempt's wall clock, because it needs the
    exported checkout. Reporting `wall_s` next to `steps=` therefore billed a
    six-step attempt as 1020 seconds when 922 of them were research — and the
    baseline it is compared against has no research at all, so the comparison
    was against a number measuring something else.
    """
    from tests.benchmark.metrics import Attempt

    attempt = Attempt(index=1, wall_s=1020.0, research_s=922.0, learn_s=8.0,
                      cost_usd=0.19, research_cost_usd=0.31)
    assert attempt.solve_s == 90.0
    assert abs(attempt.cost_total_usd - 0.50) < 1e-9

    # Never negative, however the clocks disagree.
    assert Attempt(index=1, wall_s=1.0, research_s=5.0).solve_s == 0.0

    # And both reach results.jsonl, or status.sh cannot show the split.
    from dataclasses import asdict
    row = asdict(attempt)
    assert row["research_s"] == 922.0 and row["research_cost_usd"] == 0.31


def test_failed_approach_can_be_refined_when_it_was_right_but_incomplete(tmp_path,
                                                                         monkeypatch):
    """Blanket refusal was too blunt.

    pylint-7080 failed with the ignore check in exactly the right function and
    no path normalisation, so `./ignored_subdirectory/failing.py` never matched
    an anchored pattern. Right idea, one call short. Banning the name sent the
    next attempt looking elsewhere, away from an answer it was a line from.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "pylint-ignore-paths"
    research.define_fom(topic, "correctness", "max", 1.0, "target tests")
    added = research.add_approach(
        topic, "per-file-ignore-check", "check each yielded file",
        hypothesis="files yielded from the walk skip the ignore check")
    key = added["key"]
    research.mark_attempt_outcome(topic, "per-file-ignore-check", worked=False,
                                  evidence="target 0/1, file still linted")

    # The refusal now points at the way forward instead of only closing a door.
    refused = research.add_approach(topic, "per-file-ignore-check", "again",
                                    hypothesis="same as before")
    assert refused["status"] == "error"
    assert refused["refine_with"] == key
    assert "research_refine_approach" in refused["error"]

    # A rename dressed as a refinement is rejected: both fields must carry
    # substance, or this is the loophole the refusal exists to close.
    assert research.refine_approach(topic, key, "it failed", "try harder"
                                    )["status"] == "error"

    refined = research.refine_approach(
        topic, key,
        diagnosis=("test_ignore_path_recursive_current_dir printed "
                   "ignored_subdirectory/failing.py, so the check ran in the "
                   "right place and the path simply did not match"),
        change="normalise the path with os.path.normpath before matching")
    assert refined["status"] == "ok"
    assert refined["refines"] == key
    assert refined["key"] != key                       # keys are never recycled

    entries = {a["key"]: a for a in research.load(topic)["approaches"]}
    child = entries[refined["key"]]
    assert child["status"] == "potential"
    assert entries[key]["superseded_by"] == child["key"]
    # A revision starts unmeasured: inheriting the parent's numbers would let a
    # score obtained by the version that FAILED rank the version replacing it.
    assert child["metrics"] == {} and child["measured"] is False


def test_refinement_is_bounded_so_one_wrong_idea_cannot_eat_every_attempt(
        tmp_path, monkeypatch):
    """"Nearly right, one more tweak" is available forever if nothing stops it."""
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "bounded"
    research.add_approach(topic, "idea", "s", hypothesis="h")
    key = research.load(topic)["approaches"][0]["key"]

    diagnosis = ("the target test still fails with the same assertion, showing "
                 "the branch was entered and the case missed")
    change = "cover the remaining branch in the same function"

    for depth in range(1, research.MAX_REFINEMENTS + 1):
        research.mark_attempt_outcome(topic, key, worked=False)
        step = research.refine_approach(topic, key, diagnosis, change)
        assert step["status"] == "ok" and step["depth"] == depth
        key = step["key"]

    research.mark_attempt_outcome(topic, key, worked=False)
    exhausted = research.refine_approach(topic, key, diagnosis, change)
    assert exhausted["status"] == "error"
    assert "diagnosis is what is wrong" in exhausted["error"]


def test_failed_approach_is_burned_between_tries_not_after_the_task(tmp_path,
                                                                    monkeypatch):
    """The status the whole mechanism keys off was set too late.

    Marking happened once per task, after every attempt had run, so *within* a
    task nothing was ever on record as failed. Measured on pylint-7080: try 1
    implemented the top-ranked approach and failed; nothing recorded that; try
    2's research proposed a revision, `research_refine_approach` rejected it
    because the parent was not a failure, and the ranking still led with the
    unrefined version — so try 2 built the same incomplete fix and failed the
    same way. Refusal, refinement and burial were all built and all inert.
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()

    # Failure is marked inside the attempt, before the next research pass reads
    # the ranking; success is marked once, at the end of the task.
    attempt_body = source[source.index("def run_attempt"):
                          source.index("def _mark_outcome")]
    assert "_mark_outcome" in attempt_body and "worked=False" in attempt_body

    # And the end-of-task path must NOT mark failures: by then the burned
    # candidate has been replaced at the top of the ranking by one nothing has
    # tried, and marking there would burn an approach that never ran.
    tail = source[source.index("A task that PASSED"):]
    # Wider than it was: the success path now names the plans that solved it,
    # so the comment explaining why sits between the marker and the call.
    assert "worked=True" in tail[:1800]
    assert "worked=False" not in tail[:900]


def test_a_refinement_takes_its_parents_place_in_the_ranking(tmp_path, monkeypatch):
    """Refinements start unmeasured by design, so on score alone they sort below
    every approach the corpus happened to number — and the leading line of
    thinking silently drops to the bottom the moment it is improved. Observed:
    `append-trailing-sep-only` ranked first at 1.0 while the revision carrying
    the missing normalisation sat second, so the attempt implemented the version
    already known to be incomplete.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "ranking"
    research.define_fom(topic, "correctness", "max", 1.0, "target tests")
    research.add_approach(topic, "leader", "s", hypothesis="h",
                          metrics={"correctness": 1.0}, measurement="ran it")
    research.add_approach(topic, "other", "s", hypothesis="h",
                          metrics={"correctness": 0.5}, measurement="ran it")
    research.add_approach(topic, "unscored", "s", hypothesis="h")

    key = next(a["key"] for a in research.load(topic)["approaches"]
               if a["name"] == "leader")
    research.mark_attempt_outcome(topic, "leader", worked=False)
    refined = research.refine_approach(
        topic, key,
        diagnosis=("the target test printed the same assertion, so the branch "
                   "was entered and one case was missed"),
        change="normalise the path before matching")

    ranking = research.rank_approaches(topic)["ranking"]
    names = [r["name"] for r in ranking]

    # The revision leads, ahead of the 0.5 approach and the unscored one...
    assert names[0] == refined["approach"], names
    # ...the superseded parent is gone from the live list entirely...
    assert "leader" not in names
    # ...and it still carries no score of its own, so nothing downstream can
    # mistake the parent's measurement for the revision's.
    assert ranking[0]["score"] is None


def test_outcome_marking_uses_the_arms_own_store_resolution():
    """Setting PHRONIX_PROJECT_ROOT by hand was not enough, and failed quietly.

    A session run keeps its research under `research/sessions/<id>/`. Without
    `PHRONIX_RESEARCH_SESSION` the lookup resolved the empty common folder,
    found no record and returned `empty` — so the attempt failed, nothing was
    marked, and the burn-and-refine mechanism stayed inert through a whole run
    with no sign in the trace that anything had gone wrong.
    """
    from pathlib import Path

    from tests.benchmark.arms import build

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    marker = source[source.index("def _mark_outcome"):
                    source.index("def _diff_created")]

    # Through the seam that knows the whole environment, not a hand-set var.
    assert "arm._in_store" in marker
    assert "os.environ[\"PHRONIX_PROJECT_ROOT\"]" not in marker

    # And a failure to record is now REPORTED. The silence is what hid it.
    assert "approach-unmarked" in marker

    # Every arm the runner may call this on has the seam, not just phronix ones.
    for name in ("opencode-bare", "claude-phronix", "mini"):
        assert hasattr(build(name, model="m", provider="p", base_url="u"),
                       "_in_store"), name


def test_only_the_frozen_control_has_a_read_only_store():
    """`claude-phronix` inherited the base default and ran read-only.

    It is the arm that is supposed to accumulate. With `store_readonly` left
    True it got the CONTROL's configuration — a `:ro` mount and
    `PHRONIX_BENCH_FROZEN=1` on every research, attempt and learning pass —
    while being reported as the full claim. It also skipped outcome marking
    entirely, since that is gated on a writable store, which is why no approach
    was ever burned between tries no matter what else was fixed.
    """
    from tests.benchmark.arms import ARMS, build

    for name, cls in ARMS.items():
        arm = build(name, model="m", provider="p", base_url="u")
        if not arm.uses_phronix:
            continue
        expected = "frozen" in name
        assert arm.store_readonly is expected, (
            f"{name}: store_readonly={arm.store_readonly}, expected {expected}")
    assert build("claude-phronix", model="m", provider="p",
                 base_url="u").store_readonly is False


def test_phronix_tool_mining_reads_both_harness_transcripts(tmp_path):
    """"no phronix tools called" is the alarm for an agent that never started.

    Mining only opencode's shape raised it on every healthy Claude attempt and
    learning pass, which teaches the reader to ignore it.
    """
    import json

    from tests.benchmark.trace import _mine

    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join([
        json.dumps({"part": {"type": "tool", "tool": "mcp__phronix__skill_load",
                             "state": {"output": "ok"}}}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1",
             "name": "mcp__phronix__skill_write"},
            {"type": "tool_use", "id": "t2", "name": "Bash"}]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": [{"type": "text",
                          "text": '{"status": "error", "error": "block too long"}'}]}]}}),
    ]))

    counts, errors = _mine(transcript)
    assert counts == {"mcp__phronix__skill_load": 1,
                      "mcp__phronix__skill_write": 1}, counts
    # A rejected call is the most useful thing in this file, and it is only
    # visible once the result is joined back to the call that made it.
    assert errors and "skill_write" in errors[0]


def test_evaluation_scores_what_tuning_left_behind(tmp_path, monkeypatch):
    """Tuning may refine more than once, and each revision is a new key.

    Evaluating the key the stage started from would grade the version tuning
    already improved and throw the improvement away — which would make the
    whole tuning stage worthless while appearing to work.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "lineage"
    research.define_fom(topic, "correctness", "max", 1.0, "instances")
    research.add_approach(topic, "idea", "s", hypothesis="h")
    first = research.load(topic)["approaches"][0]["key"]

    key, diagnosis = first, ("the tuning instances failed with the branch "
                             "entered and one case unhandled")
    for _ in range(2):
        research.mark_attempt_outcome(topic, key, worked=False)
        key = research.refine_approach(topic, key, diagnosis,
                                       "handle the remaining case")["key"]

    assert research.final_revision(topic, first)["key"] == key
    assert research.final_revision(topic, key)["key"] == key
    assert research.final_revision(topic, "nope") is None


def test_a_corpus_too_small_to_hold_anything_out_says_so(tmp_path, monkeypatch):
    """A held-out set of two can be passed by accident — which then reads as
    `confirmed` and licenses writing the approach up as knowledge.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "small"
    research.add_instances(topic, [{"name": f"case-{i}", "behaviour": "b"}
                                   for i in range(8)])
    result = research.split(topic)
    assert result["status"] == "ok"          # a warning, not a refusal
    assert any("below the 20" in w for w in result["warnings"]), result["warnings"]
    assert result["counts"]["tuning"] + result["counts"]["held_out"] == 8

    research.add_instances(topic, [{"name": f"extra-{i}", "behaviour": "b"}
                                   for i in range(14)])
    bigger = research.split(topic)
    assert not any("below the 20" in w for w in bigger["warnings"])
    # 80:20, give or take where the rounding lands on 22 cases.
    assert bigger["counts"]["held_out"] >= 3

    # And the plan prompt asks for a corpus that can support it.
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm
    assert "twenty instances" in (Arm.PLAN_PROMPT
                                  + skill_text("phronix-research-plan"))
    assert "Negative cases" in (Arm.PLAN_PROMPT
                                  + skill_text("phronix-research-plan"))


def test_target_test_files_come_from_the_test_patch():
    """Two ways the file list was wrong, both of which voided whole instances.

    sympy's ids are bare function names, so splitting on `::` produced the
    FUNCTION NAME as a filename and handed pytest 31 paths that do not exist.
    And a test patch carries fixtures as well as tests — flask-4992 adds
    `tests/static/config.toml` — which makes pytest answer "found no tests" and
    collect nothing at all.
    """
    from tests.benchmark.runner import _test_files

    sympy = {"test_patch": "--- a/sympy/physics/units/tests/test_quantities.py\n"
                           "+++ b/sympy/physics/units/tests/test_quantities.py\n"}
    assert _test_files(sympy, ["test_issue_24062"]) == [
        "sympy/physics/units/tests/test_quantities.py"]

    flask = {"test_patch": "+++ b/tests/static/config.toml\n"
                           "+++ b/tests/test_config.py\n"}
    assert _test_files(flask, []) == ["tests/test_config.py"]

    # No patch: fall back to ids that actually carry a path.
    assert _test_files({}, ["tests/test_self.py::T::test_x"]) == ["tests/test_self.py"]
    assert _test_files({}, ["test_bare_name"]) == []


def test_bare_ids_match_the_node_ids_pytest_prints():
    """SWE-bench stores sympy ids as `test_Quantity_definition`; pytest prints
    `sympy/.../test_quantities.py::test_Quantity_definition`. A whole-id prefix
    test can never match one against the other, so every sympy instance scored
    0 of 30 on tests that had just printed PASSED — and the baseline then cached
    all 30 as pre-existing breakage.
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    body = source[source.index("    def passed(name: str) -> bool:"):
                  source.index("    f2p = {name:")]
    assert 'actual.split("::")[-1].startswith(name)' in body
    # A qualified id still matches on the whole thing, so one test cannot be
    # credited by another whose function name merely shares a prefix.
    assert 'if "::" in name:' in body


def test_a_runner_that_never_started_is_not_a_verdict():
    """Zero passes and zero failures cannot be produced by any patch: a patch
    that breaks everything still makes the tests RUN. Scoring it as "all tests
    failed" let a missing pytest read as a catastrophic patch three times over,
    consume every retry, and get cached as 30 pre-existing failures.
    """
    from pathlib import Path

    from tests.benchmark.runner import _any_test_ran

    assert not _any_test_ran("/opt/conda/bin/python: No module named pytest")
    assert not _any_test_ran("ERROR: found no tests\nno tests ran in 0.00s")
    assert _any_test_ran("FAILED tests/a.py::t - boom\n30 failed in 2.1s")
    assert _any_test_ran("PASSED tests/a.py::t")

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    # Not cached as breakage, and not retried: neither can help.
    assert "if verdict.get(\"runner_failed\"):" in source
    assert 'if (attempt.verdict or {}).get("runner_failed"):' in source
    # And pytest is installed into the CONTAINER, never the host: the instance
    # pins the versions its tests are written against.
    assert "installing it into the container" in source


def test_a_refinement_wins_a_tie_against_untried_approaches(tmp_path, monkeypatch):
    """Inheriting the parent's sort position is not enough when the parent
    SCORED: the refinement then ties with every other approach at that score and
    loses the tie to insertion order.

    The two are not equal evidence. A refinement exists because a real attempt
    was made, judged and diagnosed, and it carries a reproduction of the failure
    it fixes. Its rivals scored on a corpus the research session wrote for
    itself and have never been tried on anything.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "ties"
    research.define_fom(topic, "correctness", "max", 1.0, "instances")
    for name in ("tried-and-failed", "untried-a", "untried-b"):
        research.add_approach(topic, name, "s", hypothesis="h",
                              metrics={"correctness": 1.0}, measurement="corpus")

    key = next(a["key"] for a in research.load(topic)["approaches"]
               if a["name"] == "tried-and-failed")
    research.mark_attempt_outcome(topic, "tried-and-failed", worked=False,
                                  evidence="target test still failing")
    refined = research.refine_approach(
        topic, key,
        diagnosis=("the target test printed the same assertion, so the branch "
                   "ran and the relative path was never normalised"),
        change="normalise with os.path.normpath before matching")

    ranking = research.rank_approaches(topic)["ranking"]
    assert ranking[0]["name"] == refined["approach"], [r["name"] for r in ranking]
    # And the version it replaced is gone from the live list.
    assert "tried-and-failed" not in [r["name"] for r in ranking]


def test_the_figure_of_merit_cannot_be_renamed_once_measured(tmp_path, monkeypatch):
    """Renaming it silently unscores every measurement taken under the old name.

    `rank_approaches` reads each approach's metric BY NAME, so a renamed metric
    makes measured approaches read as unmeasured — they sort below approaches
    with worse numbers and below ones nobody measured at all. Measured on
    pylint-7080 across three runs: the refinement carrying the correct fix
    scored 1.0 under `recursive_discovery_ignore_accuracy`, a later stage
    redeclared the metric as `files_correctly_filtered`, and the refinement
    sorted below a 0.5. The attempt then implemented something else.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "fom-drift"
    research.define_fom(topic, "accuracy", "max", 1.0, "run the corpus")
    # Before anything is measured, changing your mind is free.
    assert research.define_fom(topic, "precision", "max", 1.0, "m")["status"] == "ok"

    research.add_approach(topic, "a", "s", hypothesis="h",
                          metrics={"precision": 1.0}, measurement="ran it")
    drifted = research.define_fom(topic, "files_filtered", "max", 1.0, "m")
    assert drifted["status"] == "error"
    assert "already" in drifted["error"] and "precision" in drifted["error"]
    assert drifted["measured_against_it"] == ["a"]

    # Re-declaring the SAME metric stays idempotent.
    assert research.define_fom(topic, "precision", "max", 1.0, "m")["status"] == "ok"
    assert research.load(topic)["fom"]["name"] == "precision"
    assert research.rank_approaches(topic)["ranking"][0]["score"] == 1.0


def test_one_worktree_helper_serves_every_parallel_stage():
    """Aspects and evaluators both need isolation for the same reason, and the
    symlinked `.opencode` is the part that is easy to forget: without it the
    agent comes up with no phronix tools and cannot record a trial at all,
    which fails quietly as "scores that were predictions".
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    assert source.count("git\", \"worktree\", \"add\"") == 1, (
        "worktree creation has been duplicated again")
    helper = source[source.index("def private_tree(label: str)"):
                    source.index("def drop_tree(tree: Path)")]
    assert ".opencode" in helper and "AGENTS.md" in helper


def test_a_failing_verifier_has_two_doors_and_both_are_actions():
    """Neither self-healing nor self-learning could fire from the attempt.

    Measured on pylint-7080: the skill produced the correct edit in six steps,
    the verifier then failed on a path with a leading `./`, and the attempt
    spent forty more steps concluding the fix "works when targeting src
    directly" — rediscovering the verifier's point and dismissing it in prose.
    The task failed on exactly that case. Nothing was healed and nothing was
    recorded, so the next attempt would have met the same verifier and made the
    same argument.
    """
    from tests.benchmark.arms import PHRONIX_PLAN_SUFFIX as suffix

    # Door one: the verifier is right, which it usually is.
    collapsed = " ".join(suffix.split())      # the prompt is hard-wrapped
    assert "your change is incomplete" in collapsed
    # Door two: it is wrong, so FIX it and RECORD it — heal, then learn.
    assert "verify_new" in suffix
    assert "skill_write_lesson" in suffix
    # And the third non-door is closed explicitly.
    assert "Investigating in prose and carrying on is not a third" in collapsed
    # Bounded, so the decision cannot become the work.
    assert "at most a few steps" in collapsed


def test_the_playbook_flags_a_patch_without_carrying_it(tmp_path, monkeypatch):
    """The list says which candidates come with a measured patch, in one word.

    The path itself stays out: the attempt gets it from `research_approach` for
    the single candidate it is on, so a plan listing five approaches does not
    carry five file paths nobody will open.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "flagged"
    research.define_fom(topic, "correctness", "max", 1.0, "corpus")
    research.add_approach(topic, "with-patch", "s", hypothesis="h",
                          metrics={"correctness": 1.0}, measurement="ran it")
    research.add_approach(topic, "without", "s", hypothesis="h")
    key = next(a["key"] for a in research.load(topic)["approaches"]
               if a["name"] == "with-patch")
    noted = research.record_change(topic, key, "--- a/x\n+++ b/x\n@@\n-a\n+b")

    ranked = research.rank_approaches(topic)["ranking"]
    assert ranked[0]["change_patch"] == noted["patch"]

    text = research.playbook(topic).get("body", "") or ""
    if text:
        assert "**patch on file**" in text
        # The flag, not the artefact.
        assert noted["patch"] not in text


def test_the_skill_is_a_sequence_of_steps_tools_first(tmp_path, monkeypatch):
    """The deliverable is a METHOD, not an answer.

    A ranked list of approaches tells an agent what to believe; a sequence of
    steps tells it what to run. Each step is tagged when the plan is written:
    deterministic steps get a capability built for them and are called by name,
    and only steps that genuinely need judgement arrive as prose — because a
    capability costs one tool call while an instruction is read, interpreted and
    acted on afresh by every task that loads the skill.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research, skills

    topic = "method"
    research.define_fom(topic, "correctness", "max", 1.0, "corpus")
    research.add_approach(topic, "a", "s", hypothesis="h",
                          metrics={"correctness": 1.0}, measurement="ran it")
    research.write_plan(topic, [
        {"title": "Find every comparison against the ignore pattern",
         "kind": "deterministic", "capability": "find_ignore_comparisons"},
        {"title": "Normalise the path before matching",
         "kind": "deterministic", "capability": "normalise_before_match"},
        {"title": "Decide whether the anchor belongs at the root",
         "kind": "judgement", "detail": "depends on how the project documents it"},
    ])
    research.playbook(topic)

    name = research.topic_skill(topic)
    body = "\n".join(d.get("content", "") for d in
                     (skills.load(name) or {}).get("loaded", []))

    # The tools are named so they can be called, in order.
    assert "find_ignore_comparisons" in body
    assert body.index("find_ignore_comparisons") < body.index("normalise_before_match")
    # The judgement step is labelled as one, not left looking like a missing tool.
    assert "judgement — no tool for this" in body


def test_a_deterministic_step_without_a_tool_is_reported_as_work_left_undone(
        tmp_path, monkeypatch):
    """Tagging a step deterministic and not building it is the failure mode:
    the plan reads as automated while every attempt still does it by hand.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research, skills

    topic = "unbuilt"
    research.define_fom(topic, "correctness", "max", 1.0, "corpus")
    research.add_approach(topic, "a", "s", hypothesis="h")
    research.write_plan(topic, [
        {"title": "Run the corpus", "kind": "deterministic", "capability": ""},
    ])
    research.playbook(topic)

    body = "\n".join(d.get("content", "") for d in
                     (skills.load(research.topic_skill(topic)) or {}).get("loaded", []))
    assert "no capability yet" in body and "capability_new" in body

    # And the corrector fails it, so this cannot pass as finished research.
    verdict = research.verify_plan(topic)
    invariants = [f for f in verdict.get("facets", [])
                  if f.get("facet") == "invariants"]
    assert invariants and invariants[0].get("verdict") != "pass", verdict


def test_a_vanished_container_host_stops_the_run():
    """A flux allocation hit its 24h wall limit mid-run.

    Every task after it spent two attempts rediscovering that no container
    could start, and produced a row reading `fail`, 0 steps, 0 tokens. One of
    those rows had a real patch in it that was simply never judged — which is
    worse than a missing row, because it reads as a measured failure of the arm.
    One task failing to get a container is bad luck; two in a row is the host.
    """
    from pathlib import Path

    from tests.benchmark.runner import EnvironmentGone, ResearchCollapsed

    assert issubclass(EnvironmentGone, RuntimeError)

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    assert "raise EnvironmentGone(" in source
    # Consecutive, not cumulative: a task that gets an environment clears it.
    assert "arm.tasks_without_environment = 0" in source
    assert "tasks_without_environment\", 0) >= 2" in source
    # And it ends the run rather than becoming rows, like a collapsed research
    # pass — handled at both sites that would otherwise swallow it.
    assert source.count("except (ResearchCollapsed, EnvironmentGone)") == 2

    # Every arm carries the counter the runner reaches for.
    from tests.benchmark.arms import build
    for name in ("claude-phronix", "opencode-bare", "mini"):
        assert hasattr(build(name, model="m", provider="p", base_url="u"),
                       "tasks_without_environment"), name


def test_an_approach_is_a_pipeline_and_the_winner_becomes_the_plan(
        tmp_path, monkeypatch):
    """An approach is a WAY of solving the problem, and a way is a sequence of
    steps — a name and a paragraph is a description of one.

    The tuning stage has just run those steps to measure the approach, so it is
    the one place the pipeline is known to be real. The winner's pipeline is
    then promoted to be the plan rather than rewritten at the end: the version
    typed at the end is the one nobody measured.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research

    topic = "pipelines"
    research.define_fom(topic, "correctness", "max", 1.0, "corpus")
    research.add_approach(topic, "best", "s", hypothesis="h",
                          metrics={"correctness": 1.0}, measurement="ran it")
    research.add_approach(topic, "second", "s", hypothesis="h",
                          metrics={"correctness": 0.5}, measurement="ran it")
    keys = {a["name"]: a["key"] for a in research.load(topic)["approaches"]}

    steps = [{"title": "Find the comparisons", "kind": "deterministic",
              "capability": "find_cmp"},
             {"title": "Normalise first", "kind": "deterministic",
              "capability": "normalise"}]
    noted = research.record_pipeline(topic, keys["best"], steps)
    assert noted["status"] == "ok" and noted["steps"] == 2
    assert noted["deterministic"] == ["Find the comparisons", "Normalise first"]
    research.record_pipeline(topic, keys["second"], [
        {"title": "Try the other layer", "kind": "deterministic",
         "capability": "other_layer"}])

    # An untagged step is refused here exactly as it is in a plan: one
    # definition, so a pipeline cannot fail validation at the moment it is
    # adopted — which would be the worst possible time to discover it.
    bad = research.record_pipeline(topic, keys["best"],
                                   [{"title": "x", "kind": "vibes"}])
    assert bad["status"] == "error" and "deterministic" in bad["error"]

    adopted = research.adopt_pipeline(topic)
    assert adopted["status"] == "ok" and adopted["key"] == keys["best"]
    assert [s["capability"] for s in research.load(topic)["plan"]] == [
        "find_cmp", "normalise"]
    assert research.load(topic)["plan_from"] == keys["best"]


def test_the_solution_file_carries_every_pipeline_best_first(tmp_path, monkeypatch):
    """An attempt that exhausts the leading approach needs the next one's STEPS,
    not a sentence about it — otherwise the fallback path is the unresearched
    attempt this whole apparatus exists to avoid.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import research, skills

    topic = "solution-file"
    research.define_fom(topic, "correctness", "max", 1.0, "corpus")
    for name, score, tool in (("best", 1.0, "win_tool"),
                              ("second", 0.6, "fallback_tool"),
                              ("third", 0.2, "last_tool")):
        research.add_approach(topic, name, "s", hypothesis="h",
                              metrics={"correctness": score}, measurement="ran")
        key = next(a["key"] for a in research.load(topic)["approaches"]
                   if a["name"] == name)
        research.record_pipeline(topic, key, [
            {"title": f"do it via {name}", "kind": "deterministic",
             "capability": tool}])
    research.adopt_pipeline(topic)
    research.playbook(topic)

    body = "\n".join(d.get("content", "") for d in
                     (skills.load(research.topic_skill(topic)) or {}).get("loaded", []))
    # The winner's pipeline is the plan; the others are there to fall back to.
    assert "win_tool" in body and "fallback_tool" in body and "last_tool" in body
    # Ranked: the fallback block is ordered by the same metric.
    assert body.index("fallback_tool") < body.index("last_tool")


def test_parallel_tasks_is_offered_and_its_cost_is_stated():
    """Tasks run in order for a reason, and overlapping them has a price.

    The learning claim is that task N benefits from tasks 1..N-1, and it only
    means something if every arm saw the same sequence. Running tasks
    concurrently makes `reused`, the learning rate and every carry-over number
    unattributable — so the mode exists for iterating on the pipeline, is
    recorded in the manifest, and says what it costs at the top of the run
    rather than only in a file nobody reads before believing the report.
    """
    from pathlib import Path

    from tests.benchmark.runner import RunConfig

    assert RunConfig(tasks=[]).parallel_tasks == 1, "ordered by default"

    source = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    loop = source[source.index("        planned = []"):
                  source.index("        # Let the background learner finish")]

    # Concurrent when asked, strictly ordered otherwise.
    assert "ThreadPoolExecutor(" in loop and "if width == 1:" in loop
    # And it says so, out loud, before any result is believed.
    assert "NOT valid in this mode" in loop

    # Results are written back in task order however they finished: the results
    # file is read as a sequence, and a shuffled one would show learning that is
    # only the order the tasks happened to complete in.
    assert "sorted(finished, key=lambda item: item[0])" in loop

    # It reaches the manifest, since that is what makes a number attributable.
    assert "parallel_tasks" in RunConfig(tasks=[]).to_dict()


def test_concurrent_writers_cannot_take_the_same_label(tmp_path, monkeypatch):
    """`write_block` reads, allocates the next label from what it read, then
    writes.

    With tasks running concurrently two of them may write the same subject
    skill, and the learner writes lessons into skills while tasks write blocks
    into them: two writers read the same file, both decide the label is `I4`,
    and the second write erases the first. That is worse than losing a block —
    the label is a stable key, so everything pointing at `[[skill#I4]]` now
    points at whichever body won, and nothing records that it changed.
    """
    import re
    import threading

    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import skills

    skills.create("shared", "a shared subject", subject="shared")

    def write(index):
        skills.write_block("shared", "instruction", f"Block {index}",
                           f"Body number {index}, long enough to be a real one.")

    threads = [threading.Thread(target=write, args=(i,)) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    content = (skills.load("shared") or {}).get("loaded", [{}])[0].get("content", "")
    labels = re.findall(r"^### (I\d+) — ", content, re.M)
    assert len(labels) == 10, f"blocks lost: {labels}"
    assert len(set(labels)) == 10, f"labels collided: {labels}"


def test_the_learner_reconciles_in_parallel_without_contradicting_itself():
    """One reconciler falls behind when many tasks report at once, and the
    obvious fix — run several — is the obvious way to get two agents writing
    opposite lessons into one skill.

    The split is by SUBJECT: a lesson about a subject goes to that subject's
    skill, so workers holding disjoint topics write disjoint files. Nothing has
    to coordinate at run time because nothing overlaps by construction.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    loop = source[source.index("    def start_learning(self, store_root: Path"):
                  source.index("    def _learning_products(")]

    # Partitioned by the KIND of operation, and a kind is never split across
    # workers: one kind, one skill, one writer.
    assert "buckets" in loop and 'candidate.get("kind")' in loop
    assert "min(groups, key=len).extend(topic_lines)" in loop
    # One worker per group. `task_pool`, not a bare `ThreadPoolExecutor`: its
    # workers inherit the task's compute node, and a bare pool would strand
    # every learner agent on whatever machine drove the run.
    assert "task_pool(len(groups))" in loop
    assert "split by\n" in loop or "split by " in loop

    # Bounded: each worker is an agent invocation, not a thread of arithmetic.
    assert 1 < Arm.LEARNING_WORKERS <= 8


def test_topics_are_kinds_of_work_not_tasks(tmp_path, monkeypatch):
    """What a finding is filed under decides whether it is ever reused.

    Filed by TASK, "a subprocess whose output you parse needs stderr merged"
    lands in that task's skill and helps the one instance that produced it.
    Filed by the KIND of operation, it lands with everything else learned about
    running subprocesses, and the next task in any repository retrieves it.

    A fixed vocabulary, because the point is accumulation: an open set fragments
    into forty topics of one observation each, and forty skills of one lesson
    each is a library nobody reads.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("PHRONIX_BUS", f"ipc://{tmp_path}/bus.sock")
    monkeypatch.setenv("PHRONIX_RESEARCH_TOPIC", "task-a")
    from phronix import research

    # Agents name things descriptively, so the vocabulary tolerates synonyms
    # rather than rejecting a report — a rejected report is one that stops
    # being made, and a report in the wrong bucket beats no report.
    assert research.operation_kind("subprocess") == "bash"
    assert research.operation_kind("pytest") == "tests"
    assert research.operation_kind("walk") == "traversal"
    assert research.operation_kind("something novel") == "other"

    research.observe("merge stderr into stdout or the parse loses the error",
                     worked=True, stage="tune", kind="subprocess")
    research.observe("os.walk yields ./ prefixed roots on a relative arg",
                     worked=False, stage="aspect", kind="walk")
    monkeypatch.setenv("PHRONIX_RESEARCH_TOPIC", "task-b")
    research.observe("walking with a relative root gives ./ prefixes",
                     worked=False, stage="aspect", kind="traversal")

    grouped = research.notice()
    by_kind = {c["kind"]: c for c in grouped["candidates"]}
    assert set(by_kind) == {"bash", "traversal"}

    # The two traversal reports are one finding worded twice, and seen in two
    # different tasks — which is what makes it worth generalising.
    traversal = by_kind["traversal"]
    assert traversal["count"] == 2 and traversal["across_tasks"] is True

    # Findings of different kinds never merge: the partition depends on it.
    assert by_kind["bash"]["count"] == 1


def test_one_learner_for_the_whole_job():
    """Arms run concurrently and tasks may too, so several of them reach
    `start_learning`.

    A per-instance guard gave one learner per ARM: two consumers of one stream,
    each with its own idea of what it had seen, which is how two reconcilers
    come to work the same findings and write lessons that contradict each other.
    """
    from pathlib import Path

    from tests.benchmark import arms as arms_module

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()

    # A process-wide claim, taken under a lock because the check and the start
    # are not atomic.
    assert "_LEARNER_LOCK = threading.Lock()" in source
    assert "global _LEARNER_OWNER" in source
    assert arms_module._LEARNER_OWNER is None, "a learner leaked from a test"

    loop = source[source.index("    def start_learning(self, store_root: Path"):
                  source.index("    def _learning_products(")]
    assert "if _LEARNER_OWNER is not None:" in loop
    assert "already running for this job" in loop
    # It consumes the bus, and the bus delivers each message once.
    assert "bus.Collector()" in loop and "research_mod.claim" in loop


def test_the_gate_paces_agent_starts_and_waits_out_a_closed_window():
    """The binding limit is the account, not the node.

    A five-hour usage window, once rejected, fails every later agent instantly:
    one `rate_limit_event`, exit 1, no tool calls. A run measured that as a
    collapsed research pipeline and stopped, which is the wrong response to an
    account that would have worked again on its own.
    """
    import time

    from tests.benchmark.arms import _LlmGate

    # Spacing forced rather than read from tuning: a deployment that sets
    # `llm.min_seconds_between_starts` to 0 — correct for a self-hosted server
    # that schedules its own queue — would otherwise make this assert nothing.
    import os

    gate = _LlmGate()
    monkey = {"llm.min_seconds_between_starts": 1.0,
              "llm.max_concurrent_agents": 4}
    import tests.benchmark.arms as arms_mod

    real = arms_mod._tuned
    was_hosted = os.environ.get(arms_mod.HOSTED_ENV)
    arms_mod._tuned = lambda key, fallback: monkey.get(key, fallback)
    # Pacing exists for the ACCOUNT's usage window, so it is a hosted-run
    # property. A local fleet has no window; see the local branch below.
    os.environ[arms_mod.HOSTED_ENV] = "1"
    os.environ[arms_mod.PACED_ENV] = "1"
    try:
        started = time.time()
        with gate.slot():
            pass
        with gate.slot():
            pass
        # Two starts cannot be simultaneous: spacing is what turns a burst into
        # a sustainable draw, and concurrency alone does not bound the rate.
        assert time.time() - started >= 1.0
    finally:
        arms_mod._tuned = real
        os.environ.pop(arms_mod.PACED_ENV, None)
        if was_hosted is None:
            os.environ.pop(arms_mod.HOSTED_ENV, None)
        else:
            os.environ[arms_mod.HOSTED_ENV] = was_hosted

    notes = []
    gate.rejected_until(time.time() + 10_000, notes.append)
    assert any("resets in" in note for note in notes)

    # Past the cap it proceeds rather than sitting silently for hours — a
    # visible failure beats an invisible stall.
    waited = time.time()
    gate._wait_for_window(notes.append)
    assert time.time() - waited < 5
    assert any("going ahead" in note for note in notes)


def test_a_local_fleet_is_not_paced_like_a_usage_window():
    """The cap of 8 and the 2s stagger are about the ACCOUNT, not the machine.

    A hosted subscription has a five-hour window that, once rejected, fails
    every agent for the rest of it, so the draw has to be paced. A local fleet
    has no window: the binding limit is the replica count, and the same
    argument that set 8 for hosted runs against it here — capping below the
    server's concurrency moves the queue into the client, where it shows up as
    nothing at all.

    Measured on a 16-node run: 64 replicas ready and idle, 20 tasks in two
    arms wanting attempt, research, track and learn agents, and the trace
    saying `waiting for one of 8 agent slots`.
    """
    import os

    import tests.benchmark.arms as arms_mod

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # The key and the default both switch on the same question.
    assert '"llm.max_concurrent_agents"' in source
    assert '"llm.max_concurrent_agents_local"' in source
    assert 'key, default = "llm.max_concurrent_agents_local", 64' in source
    assert '"llm.min_seconds_between_starts_local"' in source
    assert "2.0 if _paced_run() else 0.0" in source

    was = os.environ.get(arms_mod.HOSTED_ENV)
    try:
        os.environ.pop(arms_mod.HOSTED_ENV, None)
        os.environ.pop(arms_mod.PACED_ENV, None)
        assert arms_mod._paced_run() is False
        os.environ[arms_mod.PACED_ENV] = "1"
        assert arms_mod._paced_run() is True
        os.environ.pop(arms_mod.PACED_ENV, None)
    finally:
        if was is None:
            os.environ.pop(arms_mod.HOSTED_ENV, None)
        else:
            os.environ[arms_mod.HOSTED_ENV] = was

    # And the tuning file documents both, so the numbers are not folklore.
    tuning = Path(
        "src/phronix/.phronix/workspace/tuning.yaml").read_text(encoding="utf-8")
    assert "max_concurrent_agents_local: 64" in tuning
    assert "min_seconds_between_starts_local: 0.0" in tuning



def test_a_dry_account_is_not_reported_as_a_broken_pipeline():
    """Zero tool calls means both things; only one is a reason to stop."""
    from tests.benchmark.runner import ResearchCollapsed, UsageWindowClosed

    assert not issubclass(UsageWindowClosed, ResearchCollapsed)
    assert issubclass(UsageWindowClosed, RuntimeError)


def test_the_runner_starts_the_learner_it_later_stops():
    """`stop_learning` was called and `start_learning` was not.

    Every run drained an empty bus, and the observations the stages wrote were
    never generalised into anything. The symptom is silence, which reads exactly
    like a learner that ran and found no pattern — so nothing in the output
    distinguished a working learner from an absent one.
    """
    import inspect

    from tests.benchmark import runner

    # The calls, not the prose: a comment naming `stop_learning` sits above the
    # start, so searching the raw source finds the wrong one first.
    source = inspect.getsource(runner.Runner.run_arm)
    assert "arm.start_learning(" in source, "the learner is never started"
    assert source.index("arm.start_learning(") < source.index("arm.stop_learning("), \
        "the learner must be started before the tasks it listens to"


def test_every_method_the_learner_cycle_calls_exists():
    """The cycle called `research_env`, which does not exist.

    Every cycle raised AttributeError into the handler that swallows it, so the
    learner ran all run and wrote nothing — and the trace said "reconciling 1
    finding(s)", which reads exactly like a learner that is working. The loud
    failure line is what surfaced it; this keeps it from coming back.
    """
    import inspect
    import re

    from tests.benchmark.arms import ClaudePhronixArm

    source = inspect.getsource(ClaudePhronixArm.start_learning)
    for name in set(re.findall(r"self\.([a-z_]+)\(", source)):
        assert hasattr(ClaudePhronixArm, name), f"cycle calls missing self.{name}"


def test_everything_is_learned_not_only_what_repeats():
    """Repetition strengthens a lesson; it does not admit one.

    Gating on a second sighting was wrong in the direction that costs most: a
    finding reported once and never written down is rediscovered at full price
    by the next task, while the block that would have prevented it costs a few
    lines.
    """
    from phronix import research
    from tests.benchmark.arms import ClaudePhronixArm

    once = research.notice(0.0, [
        {"what": "merging stderr into stdout kept the parse error visible",
         "worked": True, "kind": "bash", "stage": "survey", "topic": "t1",
         "at": 100.0},
    ])
    # A single observation still produces a candidate to learn from.
    assert once["candidates"], "one report must still be learnable"
    assert not once["repeats"], "and it is correctly not yet a repeat"

    # The arm spends a cycle on it rather than waiting for a second sighting.
    assert ClaudePhronixArm.LEARNING_BATCH <= 1


def test_the_cluster_config_is_read_not_restated(tmp_path):
    """Hosts and ports change every time the cluster is rebuilt.

    Anything that copies them fails at the first API call of the first task,
    as a connection error rather than as a stale-config one.
    """
    import json

    from tests.benchmark import cluster as cluster_mod

    path = tmp_path / "cluster.json"
    path.write_text(json.dumps({
        "model": "nemotron", "alias": "nemotron-3.5",
        "gateway": {"host": "head1", "port": 4000, "key": "sk-test"},
        "servers": [{"host": "n1", "port": 8050}, {"host": "n1", "port": 8051},
                    {"host": "n2", "port": 8050}],
    }))
    spec = cluster_mod.load(path)
    assert spec.model == "nemotron-3.5"        # the alias is what servers answer to
    assert spec.api_key == "sk-test"
    assert spec.gateway_url == "http://head1:4000/v1"
    assert spec.endpoints() == ["http://head1:4000/v1"]
    assert len(spec.endpoints(direct=True)) == 3

    # Writing the provider leaves everything else in the file alone.
    config = tmp_path / "opencode.jsonc"
    config.write_text(json.dumps({"provider": {"other": {"keep": True}},
                                  "permission": {"edit": {"**": "ask"}}}))
    wired = cluster_mod.configure_opencode(spec, path=config)
    written = json.loads(config.read_text())
    assert written["provider"]["other"] == {"keep": True}
    assert written["permission"] == {"edit": {"**": "ask"}}
    assert wired["qualified"] == "tuolumne/nemotron-3.5"
    assert (written["provider"]["tuolumne"]["options"]["baseURL"]
            == "http://head1:4000/v1")


def test_claude_code_is_pointed_at_a_cluster_the_way_it_actually_reads():
    """Claude Code speaks the Anthropic wire format.

    Setting OPENAI_BASE_URL does nothing for it, which is the kind of
    misconfiguration that looks like a working run against the wrong model.
    """
    from tests.benchmark.arms import ClaudeArm

    arm = ClaudeArm(model="nemotron-3.5", provider="tuolumne",
                    base_url="http://head1:4000/v1", api_key="sk-test")
    env = arm.phronix_env({})
    # The ROOT, not the /v1 the OpenAI arms use: Claude Code appends
    # /v1/messages itself, so /v1 here yields /v1/v1/messages.
    assert env["ANTHROPIC_BASE_URL"] == "http://head1:4000"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "sk-test"
    assert env["ANTHROPIC_MODEL"] == "nemotron-3.5"

    # A real Anthropic endpoint keeps its own credentials and routing.
    plain = ClaudeArm(model="claude-sonnet-5", provider="anthropic",
                      base_url="https://api.anthropic.com")
    assert not [k for k in plain.phronix_env({}) if k.startswith("ANTHROPIC")]

    # And so does an `anthropic` run that never set a base_url at all.
    #
    # `base_url` defaults to the livai gateway whatever the provider is, so
    # gating on the URL pointed a --provider anthropic run at livai with no
    # credential for it: 401 Authentication Error on every call, thirty times
    # in one run. The provider is what says whether an endpoint was chosen.
    defaulted = ClaudeArm(model="claude-sonnet-5", provider="anthropic")
    assert not [k for k in defaulted.phronix_env({}) if k.startswith("ANTHROPIC")]


def test_tasks_spread_across_nodes_and_scale_with_the_fleet():
    """A task's containers run on the node it was assigned.

    Container work is what consumes cores — the agents mostly wait on the model
    — so spreading tasks across nodes is the only way past one node's core
    count. `--tasks-per-node` rather than a flat count because it stays correct
    when nodes are added.
    """
    from tests.benchmark.runner import RunConfig, Runner

    runner = Runner.__new__(Runner)
    runner.config = RunConfig(tasks=[], arms=[], out="/tmp/x", isolation="none",
                              nodes="n1, n2 ,n3", tasks_per_node=8)
    assert runner.nodes() == ["n1", "n2", "n3"]          # whitespace tolerated

    runner._runtimes = ["rt1", "rt2", "rt3"]
    # Round-robin: consecutive tasks land on different nodes rather than
    # filling one node before touching the next.
    assert [runner.runtime_for(i) for i in range(4)] == ["rt1", "rt2", "rt3", "rt1"]

    # A single --node still works and is just a one-element fleet.
    single = Runner.__new__(Runner)
    single.config = RunConfig(tasks=[], arms=[], out="/tmp/x",
                              isolation="none", node="only")
    assert single.nodes() == ["only"]


def test_stderr_is_drained_so_a_chatty_agent_cannot_deadlock(tmp_path):
    """A pipe holds ~64 KB, and nothing was reading stderr.

    An agent chatty enough to fill it blocked writing, and a process blocked on
    stderr writes no more stdout — so the reader waited for a line that could
    not come. Seven of ten tasks stalled this way while the model fleet sat
    almost idle, looking exactly like slow inference.
    """
    import sys

    from tests.benchmark.arms import stream_opencode

    # Write far more to stderr than a pipe buffer holds, then exit.
    script = tmp_path / "chatty.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('x' * 300000)\n"
        "sys.stdout.write('{\"type\":\"done\"}\\n')\n")

    stats = {}
    out, code = stream_opencode([sys.executable, str(script)], tmp_path, {},
                                timeout_s=60, on_call=lambda _t: None,
                                stats=stats)
    # Before the fix this never returned and the timeout was the only exit.
    assert code == 0
    assert '"type":"done"' in out
    assert not stats.get("truncated"), "it should finish, not hit the budget"
    assert stats.get("stderr"), "stderr must reach the caller, not be discarded"


def test_planning_keeps_going_until_it_has_candidates():
    """An empty plan cancelled the entire investigation, silently.

    `plan` records what to investigate and the fan-out spreads over what it
    recorded, so an empty list read as "nothing to investigate". Measured: five
    phronix tool calls across a six-task run, all `research_prior`, aspects=0 in
    every record — and the arm was scored as having researched.
    """
    import inspect

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    assert Arm.MIN_ASPECTS >= 2, "one aspect gives the fan-out nothing to spread"
    assert Arm.MAX_PLAN_RETRIES >= 1

    source = inspect.getsource(Arm.research)
    # Ask again, salvage what it wrote, and only then fall back.
    # `PLAN_MORE_PROMPT`, not a re-plan: the ideas already judged good are
    # kept and the next round is asked only for the shortfall.
    assert "PLAN_MORE_PROMPT" in source, "a short plan must be asked for more"
    assert "_aspects_from_text" in source, "prose plans must be salvaged"
    assert "DEFAULT_ASPECTS" in source, "and there must be a floor"

    # The retry prompt asks for the tool and nothing else: the planner has
    # already looked, so more exploration is exactly what it must not do.
    assert "research_set_aspects" in Arm.PLAN_MORE_PROMPT
    # It must ADD to what survived rather than start over, and it must carry
    # the judgement that said more were needed.
    # It must ADD to what survived rather than start over.
    assert "Keep the ones above" in Arm.PLAN_MORE_PROMPT
    assert "{kept}" in Arm.PLAN_MORE_PROMPT and "{report}" in Arm.PLAN_MORE_PROMPT


def test_a_prose_plan_is_salvaged_into_aspects():
    """A planner that narrates has done the thinking and skipped the filing."""
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    stream = (
        '{"type":"assistant","message":{"content":[{"type":"text","text":'
        '"Plan:\\n1. Find where the table header is built\\n'
        '2. Check whether host_matching changes it\\n'
        '- Which test asserts the Subdomain column\\n"}]}}')
    got = Arm._aspects_from_text(stream)
    assert len(got) == 3
    assert all(a["name"] and a["question"] for a in got)
    # Slugs are stable keys, so they must not collide.
    assert len({a["name"] for a in got}) == 3
    assert Arm._aspects_from_text("") == []


def test_aspects_spread_across_a_model_mixture():
    """Asking one greedy model four times returns its first idea four times.

    The servers decode at temperature 0 with top_k 1, so a single model cannot
    produce diverse candidates by construction — measured, the same trace line
    six times in one second. Different models disagree about where to look,
    which is the diversity the aspect phase was designed to have.
    """
    import inspect

    from tests.benchmark.arms import OpenCodeArm, PhronixOpenCodeArm as Arm

    flow = inspect.getsource(Arm.research)
    assert "roster[position % len(roster)]" in flow, "exploring must pick a backend"
    assert "roster[position % len(roster)]" in flow, "round-robin over the fleet"
    # One model is the ordinary case and must not change behaviour.
    assert "if len(roster) <= 1:" in flow

    # The override reaches the command, which is the only thing that varies.
    arm = OpenCodeArm(model="a", provider="p", base_url="http://x/v1")
    from pathlib import Path as _P
    assert "p/a" in arm.agent_command("hi", _P("/tmp"), [])
    assert "p/b" in arm.agent_command("hi", _P("/tmp"), [], "", "b")


def test_the_working_context_is_capped_below_what_the_fleet_offers(tmp_path):
    """More context made results worse, not better.

    The fleet serves 1,048,576 tokens per slot. Conversations grew to 155,548
    and quality fell: a 30B model with 3B active per token loses the thread long
    before its nominal window ends. Nothing is truncated — the agent simply
    works in the range it reasons well in.
    """
    import json

    from tests.benchmark import cluster as cluster_mod

    path = tmp_path / "cluster.json"
    path.write_text(json.dumps({
        "models": ["nemotron-3.5", "ornith-1.5"],
        "gateway": {"host": "h", "port": 4000, "key": "k"},
        "servers": [{"host": "n1", "port": 8050}],
        "limits": {"context": 1048576},
    }))
    spec = cluster_mod.load(path)
    assert spec.models == ["nemotron-3.5", "ornith-1.5"]
    assert spec.model == "nemotron-3.5"          # the first is the default

    config = tmp_path / "opencode.jsonc"
    cluster_mod.configure_opencode(spec, path=config)
    written = json.loads(config.read_text())["provider"]["tuolumne"]["models"]
    # Every served model is declared, so a stage can ask for any of them.
    assert set(written) == {"nemotron-3.5", "ornith-1.5"}
    # An explicit limit in the config overrides both defaults.
    assert list(written.values())[0]["limit"]["context"] == 1048576


def test_the_working_window_is_capped_even_when_the_server_offers_more(tmp_path):
    """Two ceilings, and the tighter one has to win.

    A probe-then-cap written as two separate steps let the first shadow the
    second: the probed 131,072 was written into `limits` and the cap was then
    read from `limits`, so it never applied. The window stayed at the server's
    maximum, which is the value that made decode collapse to 25 tok/s.
    """
    import json

    from tests.benchmark import cluster as cluster_mod

    path = tmp_path / "cluster.json"
    path.write_text(json.dumps({
        "models": ["m"], "gateway": {"host": "h", "port": 4000, "key": "k"},
        "servers": [{"host": "n1", "port": 8050}],
    }))                                    # no `limits`, backend unreachable
    spec = cluster_mod.load(path)
    config = tmp_path / "opencode.jsonc"
    cluster_mod.configure_opencode(spec, path=config)
    window = list(json.loads(config.read_text())["provider"]["tuolumne"]
                  ["models"].values())[0]["limit"]["context"]
    assert window == cluster_mod.CONTEXT_CAP
    assert window < 131072, "the cap must be tighter than the server's window"


def test_every_arm_accepts_a_model_override():
    """An override that drops the parameter is a TypeError mid-run.

    `agent_command` gained a `model` argument so a stage can be asked of a
    different model. The Claude arms override that method, and one that keeps
    the old signature fails at the first research stage with "takes from 4 to 5
    positional arguments but 6 were given" — which surfaces as a research pass
    that produced nothing, not as a signature mismatch.
    """
    import inspect

    from tests.benchmark import arms as arms_mod

    seen = 0
    for name in dir(arms_mod):
        cls = getattr(arms_mod, name)
        if not (isinstance(cls, type) and hasattr(cls, "agent_command")):
            continue
        if "agent_command" not in vars(cls):        # inherited, not overridden
            continue
        seen += 1
        params = inspect.signature(cls.agent_command).parameters
        assert "model" in params, f"{name}.agent_command drops `model`"
        assert params["model"].default == "", f"{name} must default to no override"
    assert seen >= 3, "expected several arms to override agent_command"


def test_feedback_names_the_literal_the_tests_wanted():
    """A containment assertion says exactly what is missing.

    The agent cannot read the grading tests, so it reasons from "the test still
    fails" and improves the mechanism instead. Measured twice on two different
    models: `flask routes` gained a correct, conditional, host-vs-subdomain
    column named "Domain" while the tests asserted "Subdomain" and "Host".
    Three attempts refined the logic; none renamed the header.
    """
    from tests.benchmark.runner import _feedback_note, _missing_literals

    detail = ('tests/test_cli.py:495: in test_subdomain\n'
              '    assert "Subdomain" in result.output\n'
              "E   AssertionError: assert 'Subdomain' in 'Domain  Endpoint'\n")
    assert _missing_literals(detail) == ["Subdomain"]

    # A literal that IS present is not reported: a false "this is missing"
    # sends the next attempt after the wrong thing.
    assert _missing_literals('assert "Domain" in \'Domain  Endpoint\'') == []

    note = _feedback_note(2, {"failure_detail": detail,
                              "fail_to_pass_failing": ["test_subdomain"]})
    assert "Subdomain" in note
    assert "did NOT find" in note


def test_a_retry_that_repeats_a_failed_edit_is_caught():
    """Locations alone let an attempt call the same edit a new idea."""
    from tests.benchmark.runner import _patch_changes, _repeats_earlier

    first = ('diff --git a/cli.py b/cli.py\n'
             '+    headers.insert(0, "Domain")\n'
             '+    widths.insert(0, max(len(d) for d in domains))\n')
    history = [{"attempt": 1, "added": _patch_changes(first)}]

    # Re-indented and re-spaced is still the same change.
    again = ('diff --git a/cli.py b/cli.py\n'
             '+        headers.insert(0,  "Domain")\n'
             '+        widths.insert(0, max(len(d) for d in domains))\n')
    assert _repeats_earlier(again, history) == 1

    # Changing the thing that actually mattered is not a repeat.
    fixed = ('diff --git a/cli.py b/cli.py\n'
             '+    headers.insert(0, "Subdomain")\n'
             '+    widths.insert(0, max(len(d) for d in domains))\n')
    assert _repeats_earlier(fixed, history) == 0

    # And the edits themselves reach the next attempt, so "do not repeat this"
    # is checkable rather than exhortatory.
    note = _feedback_note = __import__(
        "tests.benchmark.runner", fromlist=["_feedback_note"])._feedback_note(
        3, {"attempt_history": history + [{"attempt": 2, "added":
                                           _patch_changes(again)}]})
    assert "already tried and already failed" in note
    assert "Domain" in note


def test_progress_is_measured_by_the_failure_moving():
    """A different patch failing identically means the idea did not move.

    Pass/fail cannot tell a task closing in from one going in circles, so the
    signature is what failed — the tests still failing, the literals the
    assertions wanted, how many now pass — and deliberately NOT the patch.
    """
    from tests.benchmark.runner import _failure_signature, _feedback_note

    base = {"fail_to_pass_failing": ["t::test_host", "t::test_subdomain"],
            "failure_detail": 'assert "Subdomain" in \'Domain  Endpoint\'',
            "fail_to_pass_passed": 0}
    assert _failure_signature(base) == _failure_signature(dict(base))
    # One more test passing is progress even though the task still fails.
    assert _failure_signature(base) != _failure_signature(
        dict(base, fail_to_pass_passed=1))
    # So is failing on a different missing literal.
    assert _failure_signature(base) != _failure_signature(
        dict(base, failure_detail='assert "Host" in \'x\''))
    assert _failure_signature(None) == ""


def test_feedback_escalates_when_the_failure_stops_moving():
    """Same error twice is a pivot signal; three times is a stop signal."""
    from tests.benchmark.runner import _feedback_note

    def sections(same, moved):
        note = _feedback_note(same + 1, {"same_failure_count": same,
                                         "failure_moved": moved,
                                         "fail_to_pass_failing": ["t::x"]})
        return [l for l in note.splitlines() if l.startswith("## ")]

    assert any("This is progress" in s for s in sections(1, True))
    # Two identical failures: change the approach, not the details.
    assert any("has not moved" in s for s in sections(2, False))
    assert "PIVOT" in _feedback_note(3, {"same_failure_count": 2,
                                         "failure_moved": False})
    # Three: stop editing and go find out what actually runs.
    assert any("IDENTICALLY" in s for s in sections(3, False))


def test_the_candidate_lifecycle_is_skills_not_prompts():
    """A prompt in code is a method the system cannot improve.

    The learner rewrites skills, the graph indexes them, and reconcile keeps one
    copy of each fact — none of which reaches a string literal in a benchmark
    harness. So the harness carries the INPUT and the skill carries the METHOD.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    for name, skill in (("SOLUTION_SKILL_PROMPT", "phronix-solution-candidate"),
                        ("TRIAL_RECONCILE_PROMPT", "phronix-trial-reconcile"),
                        ("PIVOT_NOTE", "phronix-diagnosis-pivot")):
        text = getattr(Arm, name)
        assert f'skill_load("{skill}")' in text, f"{name} must point at {skill}"
        # Short, because it is an input rather than a method.
        assert len(text) < 700, f"{name} is carrying method, not input"


def test_every_named_skill_exists_on_disk():
    """A prompt naming a skill that was never written fails silently."""
    import re
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    bundled = Path("src/phronix/.phronix/skills")
    named = set()
    for attribute in dir(Arm):
        if not attribute.isupper():
            continue
        value = getattr(Arm, attribute, "")
        if isinstance(value, str):
            named |= set(re.findall(r'skill_load\("([a-z0-9-]+)"\)', value))
    assert named, "expected the prompts to name some skills"
    missing = [s for s in named if not (bundled / s / "SKILL.md").is_file()]
    assert not missing, f"prompts name skills that do not exist: {missing}"


def test_trials_are_scored_by_the_tasks_own_tests():
    """The research metric is a proxy; the target tests are the judge."""
    import inspect

    from tests.benchmark.runner import Runner

    source = inspect.getsource(Runner._race_plans)
    # Ranked by target tests passing, then by regressions avoided.
    assert "fail_to_pass_passed" in source
    assert "pass_to_pass_passed" in source
    # Each trial is isolated, or they would see each other's edits.
    assert "trial-" in source
    # One failing trial must not take the others with it.
    assert "except Exception" in source


def test_fleet_capacity_and_the_tasks_that_fill_it(tmp_path):
    """Spare capacity is only waste when work is waiting on it.

    A task unit does not occupy a slot continuously — it checks out repos, runs
    tests and evaluates patches between model calls. Measured against a live
    12-unit run: 2, 9, 8, 7, 6 requests in flight, mean 6.4, so a unit occupies
    about half a slot. Filling a fleet therefore takes roughly twice as many
    tasks as slots-per-arm, not one per slot.
    """
    import json

    from tests.benchmark.cluster import ClusterConfig

    spec = ClusterConfig({
        "gateway": {"host": "h", "port": 4000, "key": "k"},
        "servers": [{"host": f"n{i}", "port": 8050} for i in range(32)],
    })
    # Unreachable backends fall back to one slot each rather than claiming zero
    # capacity, so a recommendation is still possible offline.
    assert spec.capacity() == 32

    # The duty cycle is what makes the answer differ from "one task per slot".
    assert 0 < ClusterConfig.DUTY_CYCLE < 1
    two_arms = spec.tasks_to_fill(arms=2)
    one_arm = spec.tasks_to_fill(arms=1)
    assert one_arm == 2 * two_arms, "halving the arms doubles the tasks needed"
    assert two_arms > spec.capacity() / 2, "a unit occupies less than a whole slot"

    # No servers means no recommendation, not a division by zero.
    assert ClusterConfig({}).capacity() == 0
    assert ClusterConfig({}).tasks_to_fill() == 0


def test_claude_code_can_be_pointed_at_a_local_gateway():
    """Claude Code speaks Anthropic; a local gateway can too.

    Verified end to end against the fleet: LiteLLM serves /v1/messages in
    Anthropic shape, and the binary returns rc=0 running gpt-oss-120b through
    it. What the arm must get right is which variables to set and where to
    point them — the ROOT, since the CLI appends /v1/messages itself.
    """
    from tests.benchmark.arms import ClaudeArm

    arm = ClaudeArm(model="gpt-oss-120b", provider="tuolumne",
                    base_url="http://head:4000/v1", api_key="sk-local")
    env = arm.phronix_env({})
    assert env["ANTHROPIC_BASE_URL"] == "http://head:4000"   # no trailing /v1
    assert env["ANTHROPIC_AUTH_TOKEN"] == "sk-local"
    assert env["ANTHROPIC_MODEL"] == "gpt-oss-120b"
    # The small/fast model must move too, or background calls go elsewhere.
    assert env["ANTHROPIC_SMALL_FAST_MODEL"] == "gpt-oss-120b"


def test_opencode_entry_point_agents_render_as_primary():
    """opencode refuses a subagent asked for by name, and says so on stderr.

    Every attempt asked for `phronix-healer` and got "is a subagent, not a
    primary agent. Falling back to default agent" — then ran as the default,
    with none of the tool scoping the template describes. A configuration error
    that presents as an agent ignoring its instructions.
    """
    from pathlib import Path

    import yaml

    agents = Path("src/phronix/.phronix/agents")
    # The four the benchmark invokes by name.
    for name in ("phronix-healer", "phronix-researcher", "phronix-learner",
                 "phronix-always-on-learner"):
        template = yaml.safe_load((agents / f"{name}.yaml").read_text())
        assert template.get("mode") == "primary", f"{name} must be primary"

    # Everything else stays a subagent by default: a primary agent nothing
    # invokes by name is only clutter in the picker.
    router = yaml.safe_load((agents / "phronix-router.yaml").read_text())
    assert router.get("mode") in (None, "subagent")

    # And the renderer reads the field rather than hardcoding it, which is what
    # made every agent a subagent regardless of what it was for.
    import inspect

    from phronix import agent_templates

    source = inspect.getsource(agent_templates.render_opencode)
    assert 'template.get("mode")' in source
    assert '"mode": "subagent"' not in source


def test_linking_is_harness_setup_and_idempotent(tmp_path):
    """Whatever the harness reads gets linked, not just what we thought of.

    Linking the harness DIRECTORY rather than naming its contents means an
    agent, a skill or an MCP declaration added later comes along without this
    code being changed. Idempotent because a checkout is made per attempt, so
    this runs constantly.
    """
    from phronix.agents import HARNESS_DIRS, link_harness

    tree = tmp_path / "repo"
    (tree / ".git" / "info").mkdir(parents=True)

    first = link_harness(tree)
    assert first["status"] == "linked" and first["linked"]
    assert link_harness(tree)["status"] == "already_linked"
    assert (tree / ".opencode").is_symlink()

    # A tree with its own directory of that name belongs to the repository
    # under test; overwriting it would change what is being measured.
    theirs = tmp_path / "has-its-own"
    (theirs / ".opencode").mkdir(parents=True)
    assert link_harness(theirs)["linked"] is False

    # Every harness the benchmark drives has a directory declared.
    assert {"opencode", "claude"} <= set(HARNESS_DIRS)
    assert link_harness(tree, harness="nope")["status"] == "unknown-harness"


def test_agents_are_staged_where_opencode_will_look(tmp_path):
    """opencode resolves --agent against the directory it was pointed at.

    That is the task's checkout, not the phronix project, so the rendered
    definitions were invisible and a stale home copy answered instead.
    """
    from pathlib import Path

    from tests.benchmark.arms import OpenCodeArm

    checkout = tmp_path / "repo"
    (checkout / ".git" / "info").mkdir(parents=True)
    arm = OpenCodeArm(model="m", provider="p")
    staged = arm.stage_agents(checkout)
    assert staged > 0
    healer = checkout / ".opencode" / "agents" / "phronix-healer.md"
    assert healer.is_file()
    assert "mode: primary" in healer.read_text()

    # A symlink, not a copy: a copy goes stale the moment `phronix sync agents`
    # runs, and a stale definition fails silently.
    assert (checkout / ".opencode").is_symlink()
    assert arm.stage_agents(checkout) == staged        # idempotent

    # A repository that has its own .opencode is left alone.
    other = tmp_path / "has-its-own"
    (other / ".opencode").mkdir(parents=True)
    assert arm.stage_agents(other) == 0

    # It must not reach the patch the arm is judged on — belt (git exclude)
    # and braces (the diff's own pathspec exclusions).
    assert ".opencode/" in (checkout / ".git" / "info" / "exclude").read_text()
    import inspect

    from tests.benchmark.arms import Arm

    assert ":(exclude).opencode" in inspect.getsource(Arm.diff_checkout)

    # A checkout that cannot be written is the old behaviour, not a crash.
    assert OpenCodeArm(model="m", provider="p").stage_agents(
        tmp_path / "nonexistent" / "x" / "y" / "z") >= 0

    # Each harness links its OWN directory.
    from tests.benchmark.arms import ClaudeArm

    assert OpenCodeArm.harness_name == "opencode"
    assert ClaudeArm.harness_name == "claude"


def test_a_harness_can_be_pinned_to_the_model_the_run_uses(tmp_path):
    """A rendered agent carries its model, so it must name the run's endpoint.

    The opencode agents shipped `model: ollama/qwen3-coder:480b-cloud` while the
    run asked for `tuolumne/gpt-oss-120b`. An agent naming a different endpoint
    than the run is a run measuring something nobody chose.
    """
    import json

    from phronix.harness_models import (load_active_config, pin_harness,
                                        resolve_models)

    got = pin_harness("opencode", "tuolumne", "gpt-oss-120b",
                      target_root=tmp_path)
    assert got["status"] == "pinned"
    # Written where the RENDERER looks, not where a bare call would put it:
    # `active_models_path()` returns the write layer with no argument and
    # <target_root>/active-models.json with one, and the renderer always passes
    # a root. Pinning through the bare call wrote a file nothing read.
    assert got["file"] == str(tmp_path / "active-models.json")

    config = load_active_config(target_root=tmp_path)
    resolved = resolve_models(config, target_root=tmp_path)["opencode"]
    assert resolved["provider"] == "tuolumne"
    # One model at EVERY level: an endpoint serving a single model has no range
    # to spread across, and resolving through a column that never mentions it
    # yields UNRESOLVED or another provider's id.
    assert {resolved[f"level_{n}"] for n in (1, 2, 3, 4)} == {"gpt-oss-120b"}

    # An unpinned harness still resolves through the menu.
    other = resolve_models(config, target_root=tmp_path)["claude"]
    assert other["level_1"] != "gpt-oss-120b"


def test_a_task_sticks_to_one_backend_so_its_prefix_stays_cached():
    """An agent re-sends its whole conversation every turn.

    llama.cpp caches that history PER SERVER, so a turn landing on a different
    backend re-processes everything. Measured on the load-balanced fleet:
    189,193,540 prompt tokens against 5,228,544 generated — 36:1 — with prefill
    costing more GPU time than decode (86,570s vs 73,445s). A repeat request to
    the same backend reported 82 of 87 prompt tokens cached; scattered across 32
    backends it reported 0.
    """
    from tests.benchmark.arms import ClaudeArm, OpenCodeArm
    from tests.benchmark.cluster import ClusterConfig

    aliases = [f"m@{i}" for i in range(32)]
    spec = ClusterConfig({"alias": "m", "pinned_models": aliases,
                          "gateway": {"host": "h", "port": 4000},
                          "servers": [{"host": "n", "port": 1}]})
    assert spec.pinned_models() == aliases

    # Stable: a retry returns to the backend that still holds the history.
    first = spec.model_for("pylint-dev__pylint-7080")
    assert first in aliases
    assert spec.model_for("pylint-dev__pylint-7080") == first
    assert spec.model_for("pallets__flask-5063") != first or len(aliases) == 1

    # The two arms of one task pin to DIFFERENT backends.
    #
    # They were deliberately given the same one, on the reasoning that they
    # would share a warm prefix. They share none: the bare and phronix arms
    # send different system prompts and diverge from the first token. Once a
    # backend has a single slot that is not merely useless but harmful —
    # measured as requests queued while most of the fleet sat idle — so the pin
    # is keyed on arm AND task.
    task = {"instance_id": "pylint-dev__pylint-7080"}

    def pinned(arm_name):
        arm = OpenCodeArm(model="m", provider="p")
        arm.pinned_models = aliases
        arm.arm_name = arm_name
        return arm

    bare, phronix = pinned("claude-bare"), pinned("claude-phronix")
    assert bare.model_for_task(task) in aliases
    assert bare.model_for_task(task) == pinned("claude-bare").model_for_task(task)
    assert bare.model_for_task(task) != phronix.model_for_task(task)

    # A fanout is several conversations at once, so it walks outward from the
    # task's own pin rather than sending all of them to it.
    spread = bare.fanout_models(task, 5)
    assert spread[0] == bare.model_for_task(task)
    assert len(set(spread)) == 5
    assert spread == bare.fanout_models(task, 5)          # stable across retries
    assert len(bare.fanout_models(task, 99)) == len(aliases)   # capped at the fleet

    # Claude Code takes its model from the environment, not argv.
    claude = ClaudeArm(model="m", provider="tuolumne",
                       base_url="http://h:4000/v1", api_key="k")
    claude.pinned_for_env = first
    assert claude.phronix_env({})["ANTHROPIC_MODEL"] == first
    # The small/fast model must move with it, or background calls scatter.
    assert claude.phronix_env({})["ANTHROPIC_SMALL_FAST_MODEL"] == first

    # A fleet with no pinned aliases falls back to the shared name rather than
    # asking for a model the gateway does not serve.
    assert ClusterConfig({"alias": "m"}).model_for("x") == "m"
    assert OpenCodeArm(model="m", provider="p").model_for_task(task) == ""
    assert OpenCodeArm(model="m", provider="p").fanout_models(task, 5) == []


# --- the pipeline as it is now: plan, explore, build ------------------------
#
# These replace seventeen tests that described the previous pipeline (survey,
# aspect, collect, propose, tune, evaluate, execution-plan). Those stages are
# gone, so their tests went with them — but the invariants several of them
# guarded are still invariants, and this is where they live now.

def test_the_pipeline_is_three_stages_in_order():
    """plan -> explore -> build-solution, and nothing in between."""
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        stdout = \"\".join(transcripts)")]

    order = [flow.index(s) for s in ('stage("plan"', 'stage(f"explore:',
                                     'stage("build-solution"')]
    assert order == sorted(order), "the stages are out of pipeline order"

    # The removed stages must not creep back in under their old names.
    for gone in ('stage("survey', 'stage("collect"', 'stage("propose"',
                 'stage(f"tune:', 'stage(f"evaluate:', 'stage("execution-plan"'):
        assert gone not in flow, gone


def test_exploring_is_bounded_and_building_is_not():
    """The two halves of the clock, and why they differ.

    Exploring will consume whatever it is given — an agent reads the whole
    repository if allowed — so it is bounded. Building writes up what exploring
    found: its input is fixed, it is forbidden from exploring, and cutting it
    throws away every minute spent producing that input.
    """
    from tests.benchmark.arms import PhronixArm as Arm

    assert Arm.STAGE_BUDGETS["plan"] == 300        # five minutes, three ideas
    assert Arm.STAGE_BUDGETS["explore"] == 120     # two minutes, all at once
    assert "build-solution" not in Arm.STAGE_BUDGETS
    # The correctors are unbudgeted too: they read what a budgeted stage
    # produced and write a judgement, so there is nothing to run away into.
    assert set(Arm.UNTIMED_STAGES) == {"build-solution", "validate-ideas",
                                       "validate-exploration", "complete-plan"}


def test_a_retry_gets_more_time_than_the_try_before_it():
    """Time goes where the task turns out to be hard.

    A task solved on the first attempt never pays for this; one that has failed
    has shown the cheap reading of the problem does not work.
    """
    from phronix.tuning import get

    per_try = float(get("research.retry_budget_multiple", 1.5))
    stuck = float(get("research.stuck_budget_multiple", 1.5))
    assert per_try > 1.0 and stuck > 1.0

    def scale(attempt, same_failures):
        out = per_try ** max(0, attempt - 1)
        return out * (stuck if same_failures >= 2 else 1.0)

    assert scale(2, 0) > scale(1, 0)          # a retry gets more
    assert scale(2, 2) > scale(2, 0)          # a repeated failure more again


def test_every_stage_prompt_is_a_pointer_to_a_skill():
    """The method is a skill; the prompt carries only the per-run input.

    A prompt in code is a method the system cannot edit — the learner improves
    skills, the graph indexes them, and reconcile keeps one copy of each fact,
    none of which reaches a string literal in a benchmark harness.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    skills = Path(__file__).parent.parent / "src" / "phronix" / ".phronix" / "skills"
    for prompt, skill in ((Arm.PLAN_PROMPT, "phronix-research-plan"),
                          (Arm.EXPLORE_PROMPT, "phronix-explore-idea"),
                          (Arm.BUILD_SOLUTION_PROMPT, "phronix-build-solution"),
                          (Arm.FINALIZE_PROMPT, "phronix-stage-finalize")):
        assert skill in prompt, f"{skill} is never loaded"
        assert (skills / skill / "SKILL.md").is_file(), skill
        # A pointer, not a second copy of the method. The shared notes are
        # not part of the pointer — they are appended to every stage alike.
        # `PATCHED_TREE_NOTE` is one of them: it describes the STATE OF THE
        # CHECKOUT on a retry, which is true of every stage that reads it and
        # is not method content belonging in a skill.
        from tests.benchmark.arms import OBSERVE_NOTE, PhronixArm as _Arm
        pointer = prompt.replace(OBSERVE_NOTE, "").replace(
            _Arm.PATCHED_TREE_NOTE, "")
        assert len(pointer) < 1200, f"{skill}'s prompt is carrying the method"


def test_building_the_solution_prefers_tools_over_prose():
    """A deterministic step becomes an MCP tool; only judgement stays prose.

    A pipeline of tool calls runs in seconds on the next task. The same pipeline
    written as paragraphs costs a later agent a multi-step derivation per step,
    and it will get one of them subtly wrong.
    """
    from pathlib import Path

    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-build-solution" / "SKILL.md").read_text()
    assert "capability_new" in skill
    assert "pipeline" in skill.lower()
    # And the result has to be findable by a later task.
    assert "graph_ensure" in skill


def test_a_remembered_skill_is_tried_before_solving_from_scratch(tmp_path):
    """Retrieval-first is the point of carrying a store between runs.

    `topic_skill` matches only the task's own topic, so a SECOND task on a
    repository already researched found nothing and began from zero — the store
    held a pipeline for exactly its subject and nothing asked for it.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm, _bundled_skill_names

    arm = PhronixOpenCodeArm(model="m", provider="p")
    calls = {}

    def fake_search(query, *a, **k):
        calls["query"] = query
        return [{"name": "phronix-context-economy"},   # bundled: not a memory
                {"name": "pylint-ignore-paths"}]       # learned: this one

    import phronix.layers as layers_module
    import phronix.skills as skills_module
    # `skill_dirs` is what `--fresh` filters on, and it reads the LAYERS on
    # this machine — including the gitignored project layer. So this asserted
    # logic but passed on ambient state: when that layer was emptied the test
    # failed, having tested nothing about the code. The allowance is stated
    # here instead.
    original, skills_module.search = skills_module.search, fake_search
    was_dirs = layers_module.skill_dirs
    layers_module.skill_dirs = lambda *a, **k: [
        "phronix-context-economy", "pylint-ignore-paths"]
    try:
        arm._in_store = lambda root, fn, *a, **k: fn(*a, **k)
        got = arm.recalled_skill(tmp_path, {"repo": "pylint-dev/pylint"})
    finally:
        skills_module.search = original
        layers_module.skill_dirs = was_dirs

    assert got == "pylint-ignore-paths"
    assert "pylint" in calls["query"]           # searched by subject, not id
    # A bundled skill is not a memory: it ships with the framework and would
    # announce a "remembered solution" that was never learned here.
    assert "phronix-context-economy" in _bundled_skill_names()

    # No repo, nothing to recall — and no crash.
    assert arm.recalled_skill(tmp_path, {}) == ""


def test_recall_refuses_a_hit_that_is_not_about_this_subject(tmp_path):
    """Search always answers; a store with nothing relevant still ranks something.

    Measured: a pylint task was told to try a remembered skill called `status`.
    Requiring the subject in the name is crude and checkable, which is what a
    corrector has to be.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm

    arm = PhronixOpenCodeArm(model="m", provider="p")
    arm._in_store = lambda root, fn, *a, **k: fn(*a, **k)

    import phronix.skills as skills_module
    original = skills_module.search
    skills_module.search = lambda *a, **k: [{"name": "status"},
                                            {"name": "notes-parsing"}]
    try:
        assert arm.recalled_skill(tmp_path, {"repo": "pylint-dev/pylint"}) == ""
    finally:
        skills_module.search = original


def test_a_plan_must_record_three_ideas():
    """The pipeline explores exactly what the plan records.

    A plan with two ideas is a pipeline that explores two, and the solution is
    built from the ideas — so a missing idea is a direction never considered.
    Asking again is the cheapest corrector there is, and each retry gets the
    FULL plan budget rather than what the first attempt left over.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    assert Arm.MIN_ASPECTS >= 3
    assert Arm.MAX_PLAN_RETRIES >= 3

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        # Explore every idea at once.")]
    assert "while tries_at_plan < self.MAX_PLAN_RETRIES" in flow
    # Predict, then correct: the validator decides which ideas survive, and
    # the COUNT of survivors decides whether the plan runs again.
    assert 'stage("validate-ideas"' in flow
    # The count is a floor on INDEPENDENT ideas: enough ideas is not the same
    # as enough different ones, and a set aimed at one function used to pass
    # this check and cost three tries to disprove.
    assert "if len(ideas) >= self.MIN_ASPECTS and not clashes:" in flow
    # "Plan MORE", not "plan again": the ideas the validator kept stay, and
    # the next round is asked only for the shortfall — with the validator's
    # report so it does not put up what was just rejected.
    assert "PLAN_MORE_PROMPT" in flow
    assert "kept_n=len(ideas)" in flow and "needed=needed" in flow
    assert "report=" in flow
    # And it gets MORE time, because the previous budget was demonstrably not
    # enough for what it was asked.
    assert "round_budget_multiple" in flow


def test_the_plan_correctors_actually_resolve():
    """Every name the plan's fallback path uses must exist at runtime.

    Both were wrong at once and neither showed up until a live run: the salvage
    called a bare `_aspects_from_text` (a staticmethod on the class) and the
    fallback a bare `DEFAULT_ASPECTS` (a class attribute). Each is a NameError
    raised only when a plan records too few ideas — which is exactly the moment
    the correctors exist to handle, so the failure path failed.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    assert callable(getattr(Arm, "_aspects_from_text", None))
    assert len(Arm.DEFAULT_ASPECTS) >= 3
    assert isinstance(Arm.PLAN_MORE_PROMPT, str) and Arm.PLAN_MORE_PROMPT
    assert isinstance(Arm.EXPLORE_MORE_PROMPT, str) and Arm.EXPLORE_MORE_PROMPT

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        # Explore every idea at once.")]
    # Bare references to class members are the bug; they must be qualified.
    assert "self._aspects_from_text(" in flow
    assert "self.DEFAULT_ASPECTS" in flow
    assert "= _aspects_from_text(" not in flow
    assert "list(DEFAULT_ASPECTS)" not in flow


def test_two_tasks_in_one_arm_do_not_share_a_topic(tmp_path):
    """Tasks run concurrently in threads within ONE arm object.

    `research_topic_binding` was a plain attribute, so task A set it, task B
    overwrote it, and A's next store read resolved under B's topic. Measured
    live: `pallets__flask-4045` explored `note_parsing`, which is
    `pylint-dev__pylint-5859`'s idea, while its own ideas read back as zero.
    """
    import threading
    from tests.benchmark.arms import PhronixOpenCodeArm

    arm = PhronixOpenCodeArm(model="m", provider="p")
    seen, ready = {}, threading.Barrier(2)

    def work(name):
        arm.research_topic_binding = name
        ready.wait(timeout=5)          # both threads have now set theirs
        seen[name] = arm.research_topic_binding

    threads = [threading.Thread(target=work, args=(n,))
               for n in ("task-a", "task-b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert seen == {"task-a": "task-a", "task-b": "task-b"}, seen


def test_the_store_env_is_mutated_by_one_thread_at_a_time():
    """`os.environ` is process-global; save-and-restore is not thread safety.

    It only makes the corruption harder to see: the restore writes back
    whichever value that thread happened to capture, which may be another
    thread's.
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("    def _in_store(self, store_root"):
                  source.index("    def _in_store_locked(")]
    assert "_STORE_ENV_LOCK" in body, "the env mutation is not serialised"


def test_every_stage_has_a_corrector_and_correctors_are_unbudgeted():
    """Predictor/corrector, applied to research itself.

    Each budgeted stage is a PREDICTION — that these are the right questions,
    that two minutes answers one. Each is followed by a check that says whether
    the prediction held, and the check is unbudgeted: it reads what an earlier
    stage produced and cannot run away into exploring.

    Putting a clock on a corrector could only ever cut the cheap half of the
    loop, which is the half that decides whether the expensive half runs again.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    # The predictors have budgets.
    assert set(Arm.STAGE_BUDGETS) == {"plan", "explore"}
    # The correctors do not.
    for corrector in ("validate-ideas", "validate-exploration"):
        assert corrector in Arm.UNTIMED_STAGES
        assert corrector not in Arm.STAGE_BUDGETS

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        stdout = \"\".join(transcripts)")]

    # Both correctors are issued with an explicit zero budget, which is what
    # `stream_opencode` reads as "no watchdog at all".
    for corrector, prompt in (("validate-ideas", "VALIDATE_IDEAS_PROMPT"),):
        issued = f'stage("{corrector}", self.{prompt}, 0'
        assert issued in flow, corrector
        # And as the validator agent, which has no way to read files or run
        # commands — the instruction not to explore was ignored in practice.
        assert flow[flow.index(issued):flow.index(issued) + 200].count(
            "agent=self.validator_agent_name") == 1, corrector

    # Exploration is judged PER IDEA, so the corrector is issued inside the
    # idea's own thread with its name in the stage label. Judging a list is
    # bounded by the list, and a list of one is the smallest useful unit: an
    # idea that answered its question is complete whatever the others are
    # still doing.
    per_idea = 'stage(f"validate-exploration:{name}",'
    assert per_idea in flow
    assert "VALIDATE_ONE_EXPLORATION_PROMPT" in flow
    assert flow[flow.index(per_idea):flow.index(per_idea) + 320].count(
        "agent=self.validator_agent_name") == 1

    # And each loop can actually go round again.
    assert "MAX_PLAN_RETRIES" in flow
    assert "MAX_EXPLORE_ROUNDS" in flow


def test_a_thin_finding_carries_its_gap_not_just_a_flag():
    """A corrector's verdict must be data.

    Recovering it by reading the validator's English is a corrector that fails
    quietly the first time it phrases itself unusually.
    """
    from tests.benchmark.arms import PhronixArm as Arm

    import phronix.research as research_module
    original = research_module.status
    research_module.status = lambda topic: {
        "notices": [{"kind": "thin", "what": "relative-form",
                     "detail": "the relative form was never tried"},
                    {"kind": "note", "what": "something else"},
                    {"kind": "thin", "what": "relative-form",
                     "detail": "restated"}]}                        # duplicate
    try:
        got = Arm._thin_gaps("t")
    finally:
        research_module.status = original

    # The DETAIL travels with it: a pass told only "thin" repeats the first
    # one; a pass told what was missing closes the gap.
    assert got == {"relative-form": "the relative form was never tried"}, got


def test_both_loops_are_incremental_and_buy_more_time_each_round():
    """A round that fell short is asked for the SHORTFALL, not for the lot.

    Re-planning from scratch throws away the ideas the validator just kept,
    re-derives them at full cost, and often produces the same weak ones again
    because nothing told it which they were. Re-exploring from scratch discards
    what the first pass established.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        stdout = \"\".join(transcripts)")]

    # Plan: keep what survived, ask for the difference, carry the report.
    # Over-asked, because the validator culls: a request for exactly the
    # missing one is lost entirely to a single rejection.
    assert "max(self.MIN_ASPECTS - len(ideas), self.PLAN_OVERASK)" in flow
    assert "PLAN_MORE_PROMPT" in flow
    assert 'report = last_output.get("validate-ideas", "") or report' in flow

    # Explore: an idea that came back thin is re-explored on its own, told
    # what was missing, without waiting for or disturbing the others.
    assert "EXPLORE_MORE_PROMPT" in flow
    assert "self._thin_gaps, topic)" in flow and ".get(name, \"\")" in flow
    assert "do not redo it" in Arm.EXPLORE_MORE_PROMPT.lower()

    # Both rounds get more time than the one before.
    assert flow.count("round_budget_multiple") >= 2


def test_every_stage_is_bound_to_its_own_task_even_in_a_pool_thread():
    """`TOPIC_ENV` binds a research call to one record whatever key is passed.

    It has to be set for EVERY stage, and the fanout stages run in pool
    threads. Reading it from a thread-local looked right and was not: a pool
    worker inherits nothing, so the explore agents ran unbound and the
    descriptive keys they invent were resolved fuzzily into whatever record
    matched.

    Measured: `sympy__sympy-24066`'s idea `exp-dimension-fix` was filed under
    `pallets__flask-5063`, and sympy-24066 finished its plan with zero ideas.
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("        def stage(name: str, prompt: str"):
                  source.index("        # The pipeline, in full.")]

    # From the enclosing call's local, which every thread the closure reaches
    # sees correctly — not from anything per-thread or per-arm.
    assert 'stage_env["PHRONIX_RESEARCH_TOPIC"] = topic' in body
    # Strip comments: the code must not read the thread-local, but the comment
    # explaining why is allowed to name it.
    code = "\n".join(line for line in body.splitlines()
                     if not line.lstrip().startswith("#"))
    assert "self.research_topic_binding" not in code, \
        "a stage must not take its topic from thread-local state"


def test_recall_reads_the_search_envelope_not_its_keys(tmp_path):
    """`skills.search` returns {status, query, count, results}.

    Iterating the dict yields those four KEYS, so the first "skill name" it
    produced was `status` — which is what a pylint task was told to try as a
    remembered solution. The subject filter then rejected every key, so recall
    silently returned nothing from then on and retrieval-first never fired.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm

    arm = PhronixOpenCodeArm(model="m", provider="p")
    arm._in_store = lambda root, fn, *a, **k: fn(*a, **k)

    import phronix.layers as layers_module
    import phronix.skills as skills_module
    # `skill_dirs` is what `--fresh` filters on, and it reads the LAYERS on
    # this machine — including the gitignored project layer. So this asserted
    # logic but passed on ambient state: when that layer was emptied the test
    # failed, having tested nothing about the code. The allowance is stated
    # here instead.
    original = skills_module.search
    skills_module.search = lambda *a, **k: {
        "status": "ok", "query": "q", "count": 1,
        "results": [{"skill": "pylint-fixme-notes-regex-boundary",
                     "subject": "pylint-fixme-notes-regex-boundary"}]}
    was_dirs = layers_module.skill_dirs
    layers_module.skill_dirs = lambda *a, **k: [
        "pylint-fixme-notes-regex-boundary"]
    try:
        got = arm.recalled_skill(tmp_path, {"repo": "pylint-dev/pylint"})
    finally:
        skills_module.search = original
        layers_module.skill_dirs = was_dirs

    assert got == "pylint-fixme-notes-regex-boundary", got


def test_a_skill_from_another_issue_is_not_named_as_this_task_s():
    """`topic_skill` falls back to fuzzy resolution, and two issues in one
    repository resolve to each other.

    Measured: both `pylint-dev__pylint-5859` (fixme notes) and
    `pylint-dev__pylint-7080` (recursive ignore-paths) returned
    `normalize-ignore-paths`. The prompt states "this task has been researched
    already, and the result is a single skill", so the planner put up
    `ignore_type_behavior` and `ignore_recursion` for a punctuation-regex bug.

    Wrong-and-confident is worse than absent: an empty answer costs a fresh
    start; this costs a plan round the corrector then has to undo.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    assert callable(getattr(Arm, "_skill_is_for", None))

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("            skill = self.best_skill_for(store_root, topic)"):]
    body = body[:body.index("files = self.attachments(")]
    assert "self._skill_is_for(store_root, skill, topic)" in body
    # Offered as knowledge rather than dropped: a skill for a neighbouring bug
    # still knows where the behaviour lives and what was refuted.
    assert "offered as knowledge" in body


def test_the_plan_is_checked_for_a_metric_and_a_corpus_too():
    """The ideas had a corrector; the plan's other two outputs did not.

    So a task could reach `build-solution` with `0 inst` and `fom=-` — a
    solution built with nothing to measure it against, and no signal anything
    was missing. Measured across one six-task run: three of six.

    The check is arithmetic over the record rather than a judgement, which is
    what lets it be trusted. A corrector that can be talked out of its verdict
    is not a corrector.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    import phronix.research as research_module
    original = research_module.status
    try:
        research_module.status = lambda topic: {}
        gaps = Arm._plan_gaps("t", 8)
        assert any("figure of merit" in g for g in gaps)
        assert any("corpus" in g for g in gaps)

        research_module.status = lambda topic: {
            "fom": {"name": "failed_tests"},
            "instances": list(range(8))}
        assert Arm._plan_gaps("t", 8) == []

        # A corpus that is present but too thin is still a gap, and the
        # message says how many there are.
        research_module.status = lambda topic: {
            "fom": {"name": "x"}, "instances": [1, 2]}
        thin = Arm._plan_gaps("t", 8)
        assert len(thin) == 1 and "there are 2" in thin[0]
    finally:
        research_module.status = original

    # And the corrector that closes them runs with no clock.
    assert "complete-plan" in Arm.UNTIMED_STAGES
    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        stdout = \"\".join(transcripts)")]
    assert 'stage("complete-plan"' in flow
    # Re-checked afterwards, with a settle: the corrector's write and this
    # read race, and a false "still incomplete" reports the corrector as
    # broken exactly when it worked.
    assert flow.count("self._plan_gaps") >= 3
    assert "time.sleep" in flow
    assert "still incomplete after the corrector" in flow


def test_an_attempt_records_whether_it_used_phronix_at_all():
    """Research with zero phronix calls is fatal; an attempt was only traced.

    Both are the same state — a plain agent under a phronix label — and the
    attempt version scored identically to one that used its memory, because
    the difference lived in a trace line nobody aggregates.
    """
    from pathlib import Path
    from tests.benchmark.arms import AttemptOutcome

    assert hasattr(AttemptOutcome(), "phronix_calls")

    runner = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    assert "attempt.phronix_calls = tracer.tools(" in runner
    assert "it is a plain agent result" in runner

    # And the census returns its count rather than only tracing it.
    trace = (Path(__file__).parent / "benchmark" / "trace.py").read_text()
    body = trace[trace.index("    def tools(self, phase: str"):]
    body = body[:body.index("\ndef ")]
    assert "return 0" in body and "return sum(counts.values())" in body


def test_an_empty_record_is_not_reported_as_a_failure_to_mark():
    """Nothing to mark is not a failure to mark.

    Under research-on-retry try 1 runs with research withheld, so no approach
    was proposed and the record is legitimately empty. The corrector fired on
    every first attempt, warning that "the next attempt will still see this
    approach as live" — about an approach that does not exist.

    A corrector that cries wolf on the normal path teaches everyone to ignore
    it, which costs exactly the times it is right.
    """
    from pathlib import Path

    runner = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    body = runner[runner.index("    def _mark_outcome("):]
    body = body[:body.index("\n    @staticmethod", 10) if "\n    @staticmethod" in body[10:]
                else len(body)]

    # An empty record gets its own, non-alarming event...
    assert 'elif decided.get("status") == "empty":' in body
    assert '"approach-none"' in body
    # ...and the alarm is reserved for a record that exists and did not update.
    alarm = body.index('"approach-unmarked"', body.index('"approach-none"'))
    assert "will still see this approach as live" in body[alarm:alarm + 400]


def test_the_plan_loop_keeps_asking_and_then_uses_what_it_has():
    """The planner proposes a third idea; the validator rejects it as filler.

    Measured: `2 good idea(s) kept, asking for 1 more` four rounds running, at
    an escalating budget each time. Neither side is misbehaving — there simply
    is no good third idea for that task — so the harness accepts what there is.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    # Bounded by the number of rounds, not by giving up early: it keeps
    # asking (differently) and then explores whatever survived.
    assert Arm.MAX_PLAN_RETRIES >= 5

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        # Explore every idea at once.")]
    assert "while tries_at_plan < self.MAX_PLAN_RETRIES" in flow
    # Two real ideas are explored as they are; the generic angles are only for
    # a plan that produced nothing at all.
    assert "if not ideas:" in flow
    assert "rather than padding to" in flow


def test_the_agent_definition_reaches_the_harness_not_just_its_name():
    """A restriction in a file nobody passes is not a restriction.

    `--agents {"name": {"description": name}}` gave Claude Code an agent with
    default tools, so `phronix-validator` — which declares no Read, Edit or
    Bash — read and edited files 67 times in one run.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    spec = Arm._agent_spec("phronix-validator")
    tools = spec.get("tools") or []
    # The whole list, not the first wrapped line: a half-passed tool list is
    # worse than none, because it looks configured.
    assert len(tools) >= 6, tools
    # The line is at CHANGING things, not seeing them: denying reading too made
    # the validator ask the user for the files it had been handed.
    for forbidden in ("Edit", "Bash", "Write"):
        assert forbidden not in tools
    assert spec.get("prompt"), "the agent's own instructions must be passed too"

    # An unknown agent degrades to a name rather than raising.
    assert Arm._agent_spec("no-such-agent") == {"description": "no-such-agent"}


def test_a_stalled_plan_is_asked_differently_rather_than_abandoned():
    """Four rounds of `2 kept, asking for 1 more` is a bad question, not a
    task with only two ideas.

    So the ask changes shape: the kept ideas go in as one-sentence summaries,
    the request is for what they do not cover, and it asks for MORE than the
    shortfall because the validator culls.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    # Over-ask: a request for exactly the missing one is lost to a single
    # rejection.
    assert Arm.PLAN_OVERASK >= 3

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        # Explore every idea at once.")]
    assert "max(self.MIN_ASPECTS - len(ideas), self.PLAN_OVERASK)" in flow
    # It keeps asking; a flat round changes the ask rather than ending it.
    assert "stuck_rounds >= self.MAX_PLAN_STALLS" not in flow
    assert "Change the axis, do not rephrase." in flow

    # The kept ideas are compressed, so the planner cannot elaborate on them.
    assert Arm._one_sentence("First. Second.") == "First."
    assert Arm._one_sentence("x" * 300).endswith("…")

    # And the method for finding a genuinely different angle is in the skill.
    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-research-plan" / "SKILL.md").read_text()
    assert "axis" in skill
    # Independence is now the requirement, stated for the FIRST list rather
    # than only when topping one up.
    assert "INDEPENDENT" in skill
    assert "it is the first one again" in skill


def test_two_bugs_in_one_repository_do_not_share_a_solution_skill():
    """Naming a harvested skill after the AREA is what lets knowledge
    accumulate — but the area has to be narrower than the repository.

    Measured: `pallets__flask-4045` (a blueprint name containing a dot) and
    `pallets__flask-5063` (a domain column in `flask routes`) both harvested to
    a skill called `flask`, and `pylint-dev__pylint-5859` to one called `note`.
    `topic_skill` then handed each attempt the other's pipeline as its own.

    One repeated token is the repository, not a subject.
    """
    from phronix.research import _subject_of

    shared_word_only = {"approaches": [{"name": "flask-routes-fix"},
                                       {"name": "flask-domain-fix"}]}
    a = _subject_of(shared_word_only, "pallets__flask-5063")
    b = _subject_of(shared_word_only, "pallets__flask-4045")
    assert a != b, (a, b)
    assert a == "pallets-flask-5063"

    # Two shared words is a real area, and both tasks in it may share a skill.
    area = {"approaches": [{"name": "normalize-ignore-paths"},
                           {"name": "normalize-ignore-recursive"}]}
    assert _subject_of(area, "pylint-dev__pylint-7080") == "ignore-normalize"

    # And with nothing to go on, the task's own slug — never the repo's, which
    # every task in the split would share.
    assert _subject_of({}, "sympy__sympy-24066") == "sympy-sympy-24066"


def test_a_restricted_agent_is_actually_denied_the_built_in_tools():
    """Declaring an agent's tools does not take the built-in ones away.

    `--agents {... "tools": [...]}` says which MCP tools the agent may reach.
    Measured after passing the full definition: `phronix-validator`, which
    declares only phronix tools and is told "judging is not investigating",
    still read and edited files 18 times. `--disallowedTools` is what removes
    them.
    """
    from pathlib import Path
    from tests.benchmark.arms import ClaudePhronixArm, ClaudeArm

    for cls in (ClaudePhronixArm, ClaudeArm):
        arm = cls(model="m", provider="tuolumne",
                  base_url="http://h:4000/v1", api_key="k")
        cmd = arm.agent_command("p", Path("/tmp"), [],
                                agent="phronix-validator")
        assert "--disallowedTools" in cmd, cls.__name__
        denied = cmd[cmd.index("--disallowedTools") + 1]
        for gone in ("Edit", "Bash", "Write"):
            assert gone in denied, (cls.__name__, denied)
        assert "Read" not in denied.split(","), (cls.__name__, denied)
        # And the definition itself still travels.
        spec = cmd[cmd.index("--agents") + 1]
        assert "mcp__phronix__research_set_aspects" in spec, cls.__name__

    # An agent with no declared tools keeps its BUILT-IN defaults: the
    # restriction applies only where one was actually expressed.
    #
    # The schema-breaking pair is denied regardless, which is a different
    # concern — `Artifact` and `RemoteTrigger` carry JSON Schemas llama.cpp
    # cannot compile, and the server rejects the whole request when they are
    # present, so every call fails rather than only one that would use them.
    arm = ClaudePhronixArm(model="m", provider="tuolumne",
                           base_url="http://h:4000/v1", api_key="k")
    cmd = arm.agent_command("p", Path("/tmp"), [], agent="no-such-agent")
    denied = cmd[cmd.index("--disallowedTools") + 1].split(",")
    # The schema-breaking pair, plus the off-task reporter that lets an
    # agent finish without a patch.
    assert sorted(denied) == ["Artifact", "RemoteTrigger", "ReportFindings"]
    for kept in ("Edit", "Bash", "Write", "Read"):
        assert kept not in denied

    # And exactly one such flag, whatever the arm: Claude Code keeps the last,
    # so a second would silently undo the first.
    for cls in (ClaudePhronixArm, ClaudeArm):
        one = cls(model="m", provider="tuolumne",
                  base_url="http://h:4000/v1", api_key="k")
        for which in ("phronix-validator", "no-such-agent", ""):
            argv = one.agent_command("p", Path("/tmp"), [], agent=which)
            assert argv.count("--disallowedTools") == 1, (cls.__name__, which)


def test_an_approach_is_always_chosen_so_the_outcome_can_be_marked(isolated_layers):
    """`choose` is willing to fail; the ledger cannot be.

    Without `tune` there are no measured trials, so `choose` returns
    `inconclusive` forever and `chosen` stays empty. `mark_attempt_outcome`
    marks the approach that was FOLLOWED, so it then returns `empty` and
    burn-and-refine sits inert. Measured: two approaches recorded, both
    `status: None`, after two attempts.
    """
    from phronix import research

    topic = "acme__widget-1"
    research.add_approach(topic, name="first", summary="s", hypothesis="h")
    research.add_approach(topic, name="second", summary="s", hypothesis="h")

    settled = research.settle_choice(topic)
    assert settled["status"] in ("ok", "kept")
    assert settled["chosen"] in ("first", "second")

    # Whatever it settles on, it settles on for good — the ledger has to point
    # at the same approach the next time it is asked, or an outcome is marked
    # against one approach and read off another.
    again = research.settle_choice(topic)
    assert again["status"] == "kept"
    assert again["chosen"] == settled["chosen"]

    # And with nothing recorded there is nothing to settle.
    #
    # A deliberately unrelated name: `acme__widget-2` fuzzy-resolves to
    # `acme__widget-1`'s record and reports its choice, which is the same
    # collision that had two Flask bugs sharing one skill.
    assert research.settle_choice("zeta__unrelated-9")["status"] == "empty"


def test_the_pipeline_ends_with_the_candidates_and_chooses_nothing():
    """The pass stops at the candidates; the target tests do the choosing.

    `settle_choice` used to run last, naming one approach as "followed" so the
    ledger had something to mark. That was a guess made before anything was
    tried — announced in the trace as "of 1, no measured ranking" — and it is
    now replaced by marking each plan with what its own trial did against the
    real tests.
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        # The pipeline, in full."):
                  source.index("        stdout = \"\".join(transcripts)")]
    assert 'stage("build-solution"' in flow
    assert "settle_choice" not in flow

    runner = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    assert "attempt.trials" in runner, "outcomes are marked from the trials now"


def test_a_finished_research_pass_is_never_sent_back_to_the_start():
    """A pass that produced candidates goes to the tests, not round again.

    Measured on pylint-7080: three ideas explored, three solution skills
    written, and eleven seconds later `research_verify` returned "fail" and the
    whole pass was re-run before the attempt. Its bar is the figure of merit
    and the trials on the corpus research built for itself — a proxy, and one
    nothing satisfies once candidates are measured against the task's own
    tests instead.
    """
    from pathlib import Path

    runner = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    body = runner[runner.index("def run_attempt"):runner.index("def _mark_outcome")]
    assert "corrector rejected the plan" not in body
    assert body.count("arm.research(") == 1, (
        "research runs once per attempt: no revision pass before the tests")


def test_the_validator_is_told_not_to_narrate_patches():
    """Denying the tools stopped the edits and not the writing.

    Measured: thirty-five `*** Begin Patch *** Update File: ...` blocks from a
    single `validate-exploration` pass. The model could not edit, so it
    narrated edits instead — an unbudgeted stage producing output nobody
    applies while the verdict went unrecorded.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    assert "patches" in Arm.VALIDATE_EXPLORE_PROMPT
    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-validate-exploration" / "SKILL.md").read_text()
    assert "Do not write the fix" in skill
    assert "already complete enough" in skill


def test_one_shared_word_is_not_enough_to_resolve_a_topic(isolated_layers):
    """A single shared token matched, so tasks read each other's records.

    `sympy__sympy-24066` matched `sympy-sympy-21847` on `sympy` and inherited
    its ideas, approaches and skill. The instance id carries its own
    discriminator — the issue number — so it has to be the thing that matches.
    """
    from phronix import research

    research.add_approach("sympy__sympy-21847", name="itermonomials",
                          summary="s", hypothesis="h")
    research.define_fom("sympy__sympy-21847", name="m", direction="max",
                        measure="how", target=1.0)

    # A different issue in the same project must NOT resolve to it.
    assert research.resolve_topic("sympy__sympy-24066") == "sympy__sympy-24066"
    # And no topic resolves to the OTHER one, whichever spelling comes back.
    assert "21847" not in research.resolve_topic("sympy__sympy-24066")
    assert "24066" not in research.resolve_topic("sympy__sympy-21847")


def test_the_plan_corrector_is_told_the_corpus_is_counted():
    """It fired, produced four instances where eight were required, and the
    stage after it measured against four.
    """
    from tests.benchmark.arms import PhronixArm as Arm

    assert "the count is checked" in Arm.COMPLETE_PLAN_PROMPT
    assert "research_add_instances" in Arm.COMPLETE_PLAN_PROMPT


def test_a_skill_states_what_it_solved_and_the_agent_decides():
    """Matching is the reader's job, not the retrieval's.

    Every heuristic that decided FOR the agent got it wrong the same way: one
    shared token, two Flask bugs, one skill, and a prompt asserting "this task
    has been researched already" about a different bug's pipeline.

    So the skill states the problem it solved, and the agent — the only reader
    that can see both problems — decides whether to apply it or mine it.
    """
    from pathlib import Path
    from tests.benchmark import arms

    suffix = arms.PHRONIX_PLAN_SUFFIX
    assert "may cover this task" in suffix
    assert "Read what it says it solved" in suffix
    # Both outcomes are spelled out, including the useful non-match.
    assert "It is your problem" in suffix
    assert "different problem in the same area" in suffix
    assert "knowledge" in suffix
    assert "cannot be delegated to the retrieval" in suffix

    # And the writer is told to make that decision possible.
    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-build-solution" / "SKILL.md").read_text()
    assert "symptom" in skill and "failing test" in skill and "cause" in skill


def test_the_failed_patch_reaches_the_plan_as_evidence():
    """The planner saw a claim and a verdict, but never the change itself.

    Without the diff it has to infer what was tried from "Implemented the fix
    for handling dimensionless exponents" and "target 0/1" — so it re-proposes
    the change that just failed, because nothing told it what that change was.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm
    import inspect

    notes = inspect.getsource(Arm._attempt_notes)
    assert '"patch.diff"' in notes
    assert "The change that was tried" in notes
    # An empty diff is a different failure from a wrong one, and is named.
    assert "Nothing was changed." in notes

    # And the plan is told to read it before planning.
    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-research-plan" / "SKILL.md").read_text()
    # And summarising that artifact is the plan's FIRST step, before the
    # metric, the corpus or any idea — everything downstream works from the
    # plan's reading of the problem.
    assert "### I1 — First, summarise the problem from the artifact" in skill
    assert "Read the diff before you plan" in skill
    assert skill.index("summarise the problem") < skill.index("research_define_fom")


def test_the_whole_exchange_is_kept_as_an_artifact_for_the_plan(tmp_path):
    """The harness used to hand research its own digest of the attempt.

    That is a summary written by the component least able to judge what
    matters: it cannot tell which half-sentence in a transcript is the clue. So
    the full exchange is written down and the PLAN summarises it, which makes
    the summary the plan's own reading of the problem rather than one it
    inherited.
    """
    import json
    from tests.benchmark.arms import PhronixOpenCodeArm

    work = tmp_path / "attempt-1"
    work.mkdir()
    (work / "prompt.md").write_text("fix the issue in issue.md")
    (work / "opencode.jsonl").write_text(json.dumps(
        {"message": {"role": "assistant",
                     "content": [{"type": "text",
                                  "text": "I changed the regex."}]}}) + "\n")

    out = PhronixOpenCodeArm.write_exchange(
        work,
        verdict={"resolved": False, "fail_to_pass_passed": 0,
                 "fail_to_pass_total": 1,
                 "fail_to_pass_failing": ["tests/test_misc.py::test_note"],
                 "failure_detail": "AssertionError: expected W0511"},
        patch="--- a/x.py\n+++ b/x.py\n@@\n-old\n+new\n")

    text = out.read_text()
    # All four halves of the exchange, not a selection from them.
    assert "fix the issue in issue.md" in text          # what it was asked
    assert "I changed the regex." in text               # what it said
    assert "+new" in text                               # what it changed
    assert "tests/test_misc.py::test_note" in text      # how it was judged
    assert "AssertionError: expected W0511" in text     # what the tests printed
    # And it says what to do with it.
    assert "Summarise it" in text

    # An empty diff is named rather than left blank: nothing changed is a
    # different failure from a wrong change.
    empty = PhronixOpenCodeArm.write_exchange(work, verdict={}, patch="")
    assert "**Nothing.** The diff was empty." in empty.read_text()


def test_a_corrector_gets_a_shorter_guard_than_the_write_up():
    """A corrector that runs for fifteen minutes has stopped judging.

    Measured: `validate-ideas` — which has no file tools and judges a list of
    three ideas — ran the full 900s guard and was killed. Denied files, it
    wandered through `skill list`, `memory recall`, three `skill load`s and a
    probe, and recorded nothing.

    The guard is not a work budget; it is the point at which "judging" has
    clearly become "investigating by other means".
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm

    assert Arm.CORRECTOR_GUARD_S < Arm.MUST_FINISH_GUARD_S
    assert Arm.CORRECTOR_GUARD_S <= 300

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("        def stage(name: str, prompt: str"):
                  source.index("        # The pipeline, in full.")]
    # The long guard is for the write-up only; correctors get the short one.
    assert 'head == "build-solution"' in body
    assert "CORRECTOR_GUARD_S" in body

    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-validate-ideas" / "SKILL.md").read_text()
    assert "record it and finish" in skill


def test_the_plan_corrector_is_told_not_to_fix_the_bug():
    """An unbudgeted corrector doing the attempt's job.

    Measured: `complete-plan` spent twenty minutes on one task — ten
    `apply_patch` calls and eight edits to `blueprints.py` — while doing the
    thing it was asked for, splitting the dataset, three times. Every edit was
    reverted afterwards, because research may not change the code.
    """
    from tests.benchmark.arms import PhronixArm as Arm

    assert "Do not fix the bug" in Arm.COMPLETE_PLAN_PROMPT
    assert "apply_patch" in Arm.COMPLETE_PLAN_PROMPT
    # And it is a corrector, so the short guard bounds it.
    assert "complete-plan" in Arm.UNTIMED_STAGES
    assert Arm.CORRECTOR_GUARD_S <= 300


def test_a_task_keeps_one_conversation_across_all_its_calls(tmp_path):
    """A task is a dozen calls, not one exchange.

    Several attempts, an evaluation after each, research between them — and
    each was starting from the issue with no idea what the previous ones had
    established, so the third attempt could repeat the first's change.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    Arm.append_turn(tmp_path, "attempt attempt-1",
                    asked="fix the issue", said="I changed the regex.")
    Arm.record_verdict(tmp_path, "evaluation of attempt 1",
                       verdict={"resolved": False,
                                "fail_to_pass_passed": 0,
                                "fail_to_pass_total": 1,
                                "fail_to_pass_failing": ["t.py::test_note"],
                                "failure_detail": "AssertionError: no W0511"},
                       patch="--- a/misc.py\n+++ b/misc.py\n@@\n-a\n+b\n")
    summary = Arm.append_turn(tmp_path, "attempt attempt-2",
                              asked="try again", said="I widened the pattern.",
                              skill="pylint-fixme-regex")

    # The full record keeps everything, in order.
    log = (tmp_path / "conversation.md").read_text()
    assert log.count("## Turn ") == 3
    assert "I changed the regex." in log and "+b" in log

    # The rolling summary is what the next call reads: small, ordered, and
    # carrying what was judged rather than what was said.
    digest = summary.read_text()
    assert digest.index("Turn 1") < digest.index("Turn 2") < digest.index("Turn 3")
    assert "changed misc.py" in digest
    assert "judged NOT resolved" in digest
    assert "t.py::test_note" in digest
    assert "AssertionError: no W0511" in digest
    # And the solution skill, when there is one.
    assert "pylint-fixme-regex" in digest
    # Small enough to attach to every later call.
    assert len(digest) < 4000, len(digest)


def test_every_attempt_is_given_what_was_already_tried():
    """Attached to all of them, including the first, where it does not exist."""
    from pathlib import Path
    from tests.benchmark import arms

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    assert 'self.conversation_dir(workdir) / "conversation-summary.md"' in source
    assert "context.append(history)" in source
    # Two levels: this task's own record, and the subject's across tasks.
    assert 'shared_dir / "subject-conversation.md"' in source
    # And the prompt tells the agent what it is for.
    assert "conversation-summary.md" in arms.TASK_PROMPT
    assert "has been measured" in arms.TASK_PROMPT


def test_a_failed_attempt_does_not_falsify_the_approach():
    """The store recorded the correct fix as refuted.

    `pallets__flask-4045` researched three angles and found the accepted one —
    validate the blueprint name, raise where endpoint names are already
    validated. The attempt implemented it and the check did not fire, so the
    learner wrote "dot validation attempt falsified … should no longer be
    considered a valid approach" and retired the lesson pointing at it.

    An idea wrongly kept costs one attempt; an idea wrongly retired costs every
    future task that would have used it.
    """
    from pathlib import Path

    root = Path(__file__).parent.parent / "src" / "phronix" / ".phronix" / "skills"

    reconcile = (root / "phronix-learning-reconcile" / "SKILL.md").read_text()
    assert "does not falsify the approach it was attempting" in reconcile
    assert "the implementation failed" in reconcile
    assert "keep the lesson and record the doubt" in reconcile

    capture = (root / "phronix-learning-capture" / "SKILL.md").read_text()
    assert "Say what failed, not what to abandon" in capture

    build = (root / "phronix-build-solution" / "SKILL.md").read_text()
    assert "Say what failed, not what to abandon" in build


def test_every_idea_is_attempted_against_the_real_tests():
    """Ideas were explored in throwaway worktrees and never attempted.

    The research metric is a proxy — measured on a corpus research built
    itself — so the idea it favours is the most promising, not the correct one.
    Attempts are independent and the fleet has capacity, so N candidates cost
    one attempt's wall clock and the target tests settle it.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    # The three ideas count as candidates, not just the recorded approaches —
    # a task with three good ideas was racing one candidate, which is no race.
    import inspect
    source = inspect.getsource(Arm.candidate_plans)
    assert 'record.get("aspects")' in source
    assert "if len(out) < limit:" in source

    # Each candidate gets its own attempt AND its own evaluation.
    runner = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    race = runner[runner.index("    def _race_plans("):]
    race = race[:race.index("\n    def ", 10)]
    assert "arm.generate(" in race
    assert "evaluate(" in race
    assert "baseline_failures(" in race
    assert "ThreadPoolExecutor" in race

    # Racing is on by default in the benchmark script.
    bench = (Path(__file__).parent.parent / "scripts" / "swe-agent-bench.sh").read_text()
    assert "CANDIDATES=${CANDIDATES:-3}" in bench
    # Through EXTRA: `run-benchmark.sh` parses with an allow-list, so a flag
    # the CLI supports is still refused unless both layers name it.
    assert 'EXTRA+=(--attempt-candidates "$CANDIDATES")' in bench
    forward = (Path(__file__).parent.parent / "scripts" / "run-benchmark.sh").read_text()
    assert "--attempt-candidates) EXTRA+=" in forward

    # And several passing is a distinct case from one passing.
    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-trial-reconcile" / "SKILL.md").read_text()
    assert "Several passed" in skill
    assert "confirmed by more than one candidate" in skill


def test_the_conversation_has_a_task_level_and_a_subject_level(tmp_path):
    """Two levels, answering different questions.

    The task's own conversation is what THIS task has tried — what stops
    attempt three repeating attempt one. The subject's is what every task in
    the area has tried, which is what stops a second bug in the same subsystem
    rediscovering the first's dead ends, often in the same run.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    task = tmp_path / "task"; task.mkdir()
    subject = tmp_path / "store" / "conversations" / "flask-blueprints"
    subject.mkdir(parents=True)

    Arm.append_turn(task, "attempt attempt-1", asked="fix it",
                    said="I edited blueprints.py",
                    patch="--- a/b.py\n+++ b/b.py\n@@\n-a\n+b\n",
                    subject_dir=subject)

    # The task level keeps the detail.
    assert "I edited blueprints.py" in (task / "conversation.md").read_text()

    # The subject level keeps a line and a link — it is read by tasks that are
    # NOT this one, which need "somebody tried this here", not the transcript.
    shared = (subject / "subject-conversation.md").read_text()
    assert "What has been tried on this subject" in shared
    assert "changed b.py" in shared
    assert "conversation.md" in shared            # the link back
    assert "I edited blueprints.py" not in shared  # not the transcript

    # A second task in the same subject appends to the same file.
    other = tmp_path / "other"; other.mkdir()
    Arm.append_turn(other, "attempt attempt-1", asked="a different bug",
                    said="I looked elsewhere", subject_dir=subject)
    assert (subject / "subject-conversation.md").read_text().count("- **Turn") == 2


def test_only_the_arms_with_memory_keep_a_conversation():
    """The bare arm is the control.

    It carries nothing between attempts by design, and a record of what it had
    already tried is the one capability the comparison exists to measure. It
    wrote none of these anyway, through which class overrides `generate` — an
    accident, not a guarantee.
    """
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    call = source.index("self.append_turn(self.conversation_dir(workdir)")
    before = source[max(0, call - 600):call]
    assert "if self.uses_phronix:" in before, "the bare arm must not record turns"


def test_every_arm_can_reach_the_conversation_helpers():
    """They lived on the phronix class while the caller lived on the base one.

    `generate` is defined on `OpenCodeArm` and calls `append_turn`; the helper
    was defined on `PhronixOpenCodeArm`. `ClaudeArm` extends the former, so
    every bare attempt raised `AttributeError: 'ClaudeArm' object has no
    attribute 'append_turn'` and the whole control arm reported
    `steps=0 tok=0/0` — a benchmark with no baseline, from a method on the
    wrong class.
    """
    from tests.benchmark.arms import (Arm, OpenCodeArm, ClaudeArm,
                                      PhronixOpenCodeArm, ClaudePhronixArm)

    for cls in (Arm, OpenCodeArm, ClaudeArm, PhronixOpenCodeArm,
                ClaudePhronixArm):
        for helper in ("append_turn", "record_verdict", "conversation_dir",
                       "subject_dir", "write_exchange", "_narrative"):
            assert hasattr(cls, helper), (cls.__name__, helper)


def test_a_failed_conversation_write_is_reported_not_swallowed():
    """A bare `except: pass` hid an AttributeError for an entire run.

    Every evaluation turn was silently missing, so the conversations held one
    turn each instead of two and nothing said so. Bookkeeping must not fail a
    task — but it must not fail invisibly either, because what it records is
    what the next attempt reads.
    """
    from pathlib import Path

    runner = (Path(__file__).parent / "benchmark" / "runner.py").read_text()
    block = runner[runner.index("arm.record_verdict("):]
    block = block[:block.index("attempt.phronix_calls")]
    assert "except Exception as exc:" in block
    assert "conversation-unrecorded" in block
    assert "\n                    pass" not in block


def test_learning_is_a_skill_and_a_pass_writes_the_solution():
    """A pass was the most valuable thing the system could record, and it was
    thrown away.

    Every win so far came on the first attempt, where no research runs — so
    nothing wrote down how the task was actually solved and the next task on
    that subject started from nothing.
    """
    from pathlib import Path
    from tests.benchmark.arms import PhronixArm as Arm, OBSERVE_NOTE

    # A pointer, not the method.
    pointer = Arm.LEARN_PROMPT.replace(OBSERVE_NOTE, "")
    assert "phronix-learn-from-attempt" in pointer
    assert len(pointer) < 1200, len(pointer)
    assert "PASSED" in pointer and "solution" in pointer

    skill = (Path(__file__).parent.parent / "src" / "phronix" / ".phronix"
             / "skills" / "phronix-learn-from-attempt" / "SKILL.md").read_text()
    # A pass writes the solution, and updates rather than forks.
    assert "It passed: write the solution" in skill
    assert "update it" in skill
    # What works and what does not, in ONE skill.
    assert "approaches that work for this task" in skill
    assert "lessons learned" in skill
    assert "SAME skill" in skill
    # And the evaluation's own output is evidence, not just the verdict.
    assert "what the tests printed" in skill

    # The learn step is actually handed that output.
    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    assert 'workdir / "exchange.md"' in source


def test_fresh_serves_core_plus_this_session_and_no_earlier_run(tmp_path, monkeypatch):
    """`--fresh` isolates capabilities the way it already isolated research.

    Research is isolated at the storage layer: without reuse a read sees the
    current session's folder and nothing else. Capabilities were not, and the
    gap was filled by seeding every `probe_`-prefixed tool on the reasoning
    that a method tool carries nothing about any task. The prefix is chosen by
    whichever agent wrote the tool, and one of them was
    `probe_fix_max_to_sum_powers_filter` — a tool that applies one benchmark
    task's fix outright. The run could call it without knowing it had been
    handed anything.

    So the visible set under `--fresh` is core plus current: what ships with
    the framework, and what this process authored. Nothing from an earlier
    run's layer.
    """
    from phronix import capabilities

    monkeypatch.setattr(capabilities, "_SESSION_AUTHORED", {}, raising=False)
    earlier = tmp_path / "probe_from_last_run.py"
    earlier.write_text("def register(mcp):\n    pass\n")
    mine = tmp_path / "probe_built_just_now.py"
    mine.write_text("def register(mcp):\n    pass\n")

    monkeypatch.setattr("phronix.layers.capability_files",
                        lambda *a, **k: {earlier.name: earlier, mine.name: mine})
    monkeypatch.setattr("phronix.layers.which_layer", lambda path, *a, **k: "project")

    # Not fresh: everything an agent can reach is fair game.
    monkeypatch.delenv(capabilities.FRESH_ENV, raising=False)
    assert set(capabilities.visible_files()) == {earlier.name, mine.name}

    # Fresh: only what this session built.
    monkeypatch.setenv(capabilities.FRESH_ENV, "1")
    capabilities._SESSION_AUTHORED[mine.stem] = str(mine)
    assert set(capabilities.visible_files()) == {mine.name}


def test_fresh_still_serves_the_bundled_tools(tmp_path, monkeypatch):
    """Core is not withheld: `--fresh` is a claim about learning, not tooling."""
    from phronix import capabilities

    shipped = tmp_path / "probe_shipped.py"
    shipped.write_text("def register(mcp):\n    pass\n")
    monkeypatch.setattr(capabilities, "_SESSION_AUTHORED", {}, raising=False)
    monkeypatch.setattr("phronix.layers.capability_files",
                        lambda *a, **k: {shipped.name: shipped})
    monkeypatch.setattr("phronix.layers.which_layer", lambda path, *a, **k: "bundled")
    monkeypatch.setenv(capabilities.FRESH_ENV, "1")

    assert set(capabilities.visible_files()) == {shipped.name}


def test_a_task_capability_is_filed_under_its_task(tmp_path, monkeypatch):
    """A tool is filed by what it is ABOUT, and never beside the methods.

    It used to be filed under the one task that happened to need it, which is
    backwards for a deterministic procedure: a tool found only by its
    originating task is a tool nothing reuses, and reuse is the entire reason
    to write code instead of prose. `tools/<category>/` groups them, and the
    topic supplies the category when nothing better is given — so a tool built
    while solving one task still lands somewhere meaningful.

    It also keeps the catalogue navigable: `capability_list` returned 195 flat
    names, which is not a list anyone chooses from.
    """
    from phronix import capabilities

    store = tmp_path / "project" / ".phronix"
    (store / "capabilities").mkdir(parents=True)
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(store.parent))

    source = "def register(mcp):\n    pass\n"
    method = capabilities.new("probe_run_pytest_here", "run pytest", source=source)
    bound = capabilities.new(
        "probe_fix_this_one_bug", "apply the fix",
        # Materially different, not a comment apart: identical procedures are
        # refused as duplicates, which is a rule this test is not about.
        source="def register(mcp):\n    return 'applies one task's fix'\n"
               .replace("'applies", '"applies').replace("fix'", 'fix"'),
        topic="pylint-dev__pylint-7080")

    assert method["status"] == "ok" and bound["status"] == "ok"
    # Uncategorised and unbound: `tools/general/`, which is honest about not
    # knowing and still somewhere the filter and the layout check can see.
    # Never loose at the top of the tree — that is what defeated `--fresh`.
    assert Path(method["file"]).parent.name == capabilities.DEFAULT_TOOL_CATEGORY
    assert Path(method["file"]).parent.parent.name == capabilities.TOOL_DIR
    # Bound to one task: beside the SOLUTION it implements, where the reader
    # who loaded that skill already is — not shelved with the shared tools
    # under a task-shaped category nothing else will ever look in.
    assert Path(bound["file"]).parent.name == "pylint-dev-pylint-7080"
    assert Path(bound["file"]).parent.parent.name == capabilities.SOLUTION_DIR

    # An explicit category beats the topic: what the tool is about is a better
    # grouping than who first needed it.
    grouped = capabilities.new(
        "probe_run_pytest_subset", "run a subset of pytest",
        source="def register(mcp):\n    return \"subset\"\n",
        topic="pylint-dev__pylint-7080", category="pytest")
    assert grouped["status"] == "ok"
    assert Path(grouped["file"]).parent.name == "pytest"
    assert Path(grouped["file"]).parent.parent.name == capabilities.TOOL_DIR


def test_the_solution_skill_is_the_way_in_to_the_candidates(tmp_path):
    """One skill per subject, linking every candidate — not replacing them.

    Each idea is written up as its own skill so its racer has something
    executable to follow, and every one of those is kept: "was X tried, and
    what happened?" is the question a later task on this subject arrives with,
    and a rejected idea recorded with the check that killed it costs the next
    task a sentence instead of an attempt.

    What the merge produces is the way IN to them: the answer, plus a `[[name]]`
    link to each candidate. That is the one status reports, because it is the
    one somebody opens.
    """
    from pathlib import Path as P
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    # The reconcile input names the candidate skills and points at the rule.
    assert "{skills}" in Arm.TRIAL_RECONCILE_PROMPT
    assert "R2b" in Arm.TRIAL_RECONCILE_PROMPT

    skill = (P(__file__).parent.parent / "src" / "phronix" / ".phronix" / "skills"
             / "phronix-trial-reconcile" / "SKILL.md").read_text()
    assert "### R2b" in skill
    assert "[[name]]" in skill
    assert "Do not copy the candidates in" in skill

    # And a candidate is told its write-up is kept and linked, not discarded.
    candidate = (P(__file__).parent.parent / "src" / "phronix" / ".phronix"
                 / "skills" / "phronix-solution-candidate" / "SKILL.md").read_text()
    assert "### R3" in candidate


def test_status_lists_the_solution_skill_not_its_ideas():
    """Four near-identical names bury the one that holds the answer.

    A raced task writes `solution-<subject>-<plan>` per candidate and merges
    them into `solution-<subject>`. Status lists the merged skill and counts the
    candidates on the same line; they stay reachable through its [[name]] links.
    A candidate with no merged parent still prints on its own — an unreconciled
    trial is a gap worth seeing.
    """
    from pathlib import Path as P

    status = (P(__file__).parent.parent / "scripts" / "status.sh").read_text()
    assert 'name.startswith(p + "-")' in status
    assert '"ideas"' in status

    # And the learner eventually merges sibling SUBJECTS into one topic, which
    # per-subject reconciliation cannot see.
    skill = (P(__file__).parent.parent / "src" / "phronix" / ".phronix" / "skills"
             / "phronix-learning-reconcile" / "SKILL.md").read_text()
    assert "### I1b" in skill
    assert "superseded, merged into" in skill
    assert "are **not** siblings to" in skill   # candidates stay under theirs

    # A topic is discoverable like a capability: the answer first, then one case
    # per instance — what worked with what, and what settled it — inline while
    # short, split into a linked skill when long.
    assert "### I1c" in skill
    assert "what worked, with what" in skill
    assert "move it to its own skill" in skill


def test_status_reports_the_solution_skill_and_every_trial():
    """A verdict says a task passed; this says what was tried and where it went.

    Measured on pylint-7080: three plans raced, two solved it, and the run
    reported one line saying the task passed. Which readings of the problem
    were tried, which the tests agreed with, and the skill holding the answer
    were all on disk and none of them were shown.
    """
    from pathlib import Path as P

    status = (P(__file__).parent.parent / "scripts" / "status.sh").read_text()
    assert 'a.get("trials")' in status
    assert 'a.get("solution_skill")' in status

    from tests.benchmark.metrics import Attempt

    assert Attempt(index=1).solution_skill == ""
    assert Attempt(index=1).trials == []


def test_reuse_tries_what_was_built_before_researching_again():
    """Reuse means calling the tools earlier sessions authored, not re-deriving.

    Two halves, and neither works alone. The runner used to research before
    every attempt including the first, so a task the store already answered
    paid for a full plan-explore-build pass before anything looked at the
    answer — measured on pylint-7080, whose merged solution skill and three
    candidates were all seeded in and never consulted. And the attempt prompt
    named a skill but never the capabilities, which under a carried store are
    already registered on the server the agent is talking to.
    """
    from pathlib import Path as P

    runner = (P(__file__).parent.parent / "tests" / "benchmark" / "runner.py").read_text()
    # Research is the fallback, not the opening move.
    assert 'not getattr(self.config, "research_first", False)' in runner
    assert "research_first: bool = False" in runner

    cli = (P(__file__).parent.parent / "tests" / "benchmark" / "cli.py").read_text()
    assert "--research-first" in cli

    arms = (P(__file__).parent.parent / "tests" / "benchmark" / "arms.py").read_text()
    assert "PHRONIX_REUSE_SUFFIX" in arms
    assert "capability_list()" in arms
    # Offered, never forced onto a neighbouring bug.
    assert "If nothing in the list fits" in arms


def test_the_task_opens_with_the_merged_solution_skill():
    """The answer, not the older subject skill that predates it.

    `reconcile_trials` writes `solution-<topic>` — the fix plus a link to every
    candidate tried. The research record's `topic_skill` still names the subject
    skill written before the merge, so a task whose answer was already on disk
    was handed the vaguer one and had to re-find the rest.
    """
    from pathlib import Path as P
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    store = P(__file__).parent / "_solskill" / ".phronix"
    (skill_home_under(store, "solution-pylint-dev-pylint-7080")).mkdir(parents=True,
                                                                exist_ok=True)
    (skill_home_under(store, "solution-pylint-dev-pylint-7080") / "SKILL.md").write_text(
        "---\nname: solution-pylint-dev-pylint-7080\n---\n")
    try:
        arm = Arm.__new__(Arm)
        assert (arm.best_skill_for(store, "pylint-dev__pylint-7080")
                == "solution-pylint-dev-pylint-7080")
    finally:
        import shutil
        shutil.rmtree(store.parent, ignore_errors=True)


def test_status_classifies_what_a_run_accumulated():
    """"5 learned" is a number about three different things.

    Core framework skills, what solves a task (a merged `solution`, the `idea`
    candidates linked under it), and what a research pass established are
    produced by different parts of the loop and answer different questions — a
    run yielding only research skills has learned about problems and not how to
    solve them, which reads as healthy under a single count. Tools share the
    table because they are the other half of what a run produces, with the type
    named on every row: a skill is read, a tool is called.
    """
    from pathlib import Path as P

    status = (P(__file__).parent.parent / "scripts" / "status.sh").read_text()
    assert 'ORDER = ["capability", "research", "core"]' in status
    for kind in ("solution", "idea", "method", "research", "core", "other"):
        assert f'"{kind}"' in status
    # One table, both asset types, a count where a sentence used to be.
    assert '("type", 5), ("kind", 9)' in status
    assert 'note = "never retrieved"' not in status   # a count, not a word
    # Terminal by default, markdown on request — same rows either way.
    assert "STATUS_MARKDOWN" in status
    # A candidate is `solution-<subject>-<plan>`; matching any name-extends-name
    # pair folded whole research subjects into each other.
    assert 'p.startswith("solution-")' in status


def test_recall_is_a_visible_step_before_the_attempt():
    """The first move of the flow was the one nothing recorded.

    Look for what the store holds, attempt, research only on failure — but the
    lookup ran inside the prompt build, so a run handed the answer and one that
    found nothing produced identical traces, both opening at "attempt". The only
    way to tell them apart was to read the prompt out of a transcript.
    """
    from pathlib import Path as P

    runner = (P(__file__).parent.parent / "tests" / "benchmark" / "runner.py").read_text()
    assert '"search-skill"' in runner
    # Research is not announced before try 1 because it does not happen there.
    assert "research-on-retry mode" not in runner
    assert "attempt.recalled_skill = arm.best_skill_for(" in runner
    # And it happens before the attempt begins.
    assert runner.index("attempt.recalled_skill = arm.best_skill_for(") < runner.index(
        "tracer.begin(stage,")

    from tests.benchmark.metrics import Attempt

    assert Attempt(index=1).recalled_skill == ""

    status = (P(__file__).parent.parent / "scripts" / "status.sh").read_text()
    assert 'a.get("recalled_skill")' in status
    assert "no stored skill covered this task" in status
    # The attempt carries the skill it is working from, like a raced plan.
    assert 'f"attempt>{attempt.recalled_skill}"' in runner


def test_every_attempt_line_says_which_skill_it_is_working_from():
    """The opening line scrolls away; the two hundred after it must still say.

    `attempt>solution-...>` was written once, and every step line under it read
    `attempt>` — so the question the trace is watched for, is this solving from
    a stored skill or from scratch, was answerable only by scrolling back to the
    start of the attempt.
    """
    from pathlib import Path as P

    runner = (P(__file__).parent.parent / "tests" / "benchmark" / "runner.py").read_text()
    assert "def _labelled(phase: str, text: str) -> None:" in runner
    assert 'text = f"[{skill}] {text}"' in runner
    # A raced plan already labels its own lines; two prefixes push the message
    # out of its column.
    assert 'not text.lstrip().startswith("[")' in runner
    # Read when the line is written, not frozen when the closure is made: the
    # baseline narrator is wired up before the lookup has run.
    assert 'skill = getattr(attempt, "recalled_skill", "")' in runner
    # The evaluation that judges the attempt is labelled too.
    assert runner.count('_labelled("evaluate", text)') == 2
    assert '_labelled("attempt", text)' in runner

    # The tracer lifts a leading [stage] into the label column, and a skill name
    # is a legal stage there — dashes allowed, under the length cap. Read from
    # the file: `step` is wrapped by @_guard, so getsource returns the wrapper.
    step = (P(__file__).parent.parent / "tests" / "benchmark" / "trace.py").read_text()
    assert "len(name) <= 40" in step
    assert len("solution-pylint-dev-pylint-7080") <= 40


def test_a_capability_lists_with_what_it_says_it_does(tmp_path):
    """A name alone cannot be chosen between; 63 of them cannot be read at all.

    `listing()` read the MODULE docstring, which is where the template puts a
    summary and not where an agent-written capability puts it — those open with
    `import os` and document the tool function. Measured, and it cost a task: a
    reuse run called `capability_list`, got 63 tools with empty descriptions —
    `apply_normpath_ignore_fix` among them, which was exactly the fix it needed
    — solved from scratch instead, and failed the target test.
    """
    import textwrap
    from phronix.capabilities import listing

    # Written here rather than read from whatever this machine's layers hold.
    #
    # The catalogue is a live directory: it was full of learned tools when
    # this was written, and empty once carried knowledge moved out of the
    # packaged layer and into the carry root. A test that asserts on ambient
    # content passes or fails on the state of the box, not on the code — so
    # the two shapes that matter are written out and the assertion is made
    # against those.
    import phronix.capabilities as caps

    made = tmp_path / "capabilities"
    made.mkdir(parents=True, exist_ok=True)
    # The template's shape: a module docstring.
    (made / "documented_module.py").write_text(textwrap.dedent('''
        """Apply the normpath fix to the ignore check."""


        def register(mcp):
            @mcp.tool()
            def apply_normpath_ignore_fix(where: str) -> str:
                return where
        ''').lstrip(), encoding="utf-8")
    # What an agent actually writes: imports first, docstring on the function.
    (made / "documented_function.py").write_text(textwrap.dedent('''
        import os


        def register(mcp):
            @mcp.tool()
            def grep_usage_sites(where: str) -> str:
                """Find every call site of a symbol in the repository."""
                return where
        ''').lstrip(), encoding="utf-8")

    was = caps.visible_files
    caps.visible_files = lambda: {p.name: p for p in sorted(made.glob("*.py"))}
    try:
        rows = listing()
    finally:
        caps.visible_files = was

    described = [r for r in rows if r["description"]]
    assert described, "no capability lists a description at all"
    by_name = {r["name"]: r["description"] for r in rows}
    # The module-docstring shape, which always worked.
    assert "normpath" in by_name["documented_module"]
    # The agent-written shape, which is the one that was coming back blank.
    assert "call site" in by_name["documented_function"]

    # A function docstring, on a module that has none of its own.
    import re

    source = textwrap.dedent('''
        import os


        def register(mcp):
            @mcp.tool()
            def do_thing(where: str) -> str:
                """Do the thing. And then say more about it."""
        ''')
    match = re.search(r'\n\s+def\s+\w+\([^)]*\)[^:]*:\s*"""(.*?)"""', source, re.S)
    assert match and match.group(1).startswith("Do the thing")


def test_a_solved_task_is_recognised_by_a_later_run(tmp_path, monkeypatch):
    """Reuse must find the skill for the task it is about to attempt.

    Measured: `pallets__flask-4045` was SOLVED, `skills/pallets-flask-4045/` was
    carried into the project layer, and the next run reported "no skill covers
    this task; solving from scratch" — then recalled
    `flask-routes-subdomain-display`, which belongs to a different bug.

    The cause was that both lookup paths went through the research record, and a
    record does not survive a run unless its session was folded into the common
    folder.
    """
    from tests.benchmark import arms

    arm = arms.PhronixOpenCodeArm.__new__(arms.PhronixOpenCodeArm)
    skills = tmp_path / "skills"
    # No record at all: exactly the state a fresh run inherits.
    monkeypatch.setattr(arm, "_in_store", lambda root, fn, *a, **k: "")

    (skills / "pallets-flask-4045").mkdir(parents=True)
    (skills / "pallets-flask-4045" / "SKILL.md").write_text("# topic skill\n")
    assert arm.best_skill_for(tmp_path, "pallets__flask-4045") == "pallets-flask-4045"

    # The task's OWN skill outranks a candidate from the parallel pipeline.
    #
    # It used to be the other way round, on the reasoning that a candidate was
    # actually raced against the tests. The tracked loop changed what the bare
    # name means: it is the skill research updates between attempts and the
    # snapshot closes out, so it is the most current thing there is — where a
    # candidate is a frozen artefact of one earlier pass.
    cand = skills / "solution-pallets-flask-4045-reject-dotted-name"
    cand.mkdir(parents=True)
    (cand / "SKILL.md").write_text("# candidate\n")
    assert arm.best_skill_for(tmp_path, "pallets__flask-4045") == "pallets-flask-4045"

    # The merged solution is found when the task has no skill of its own —
    # which is the parallel pipeline's shape, where the merge IS the output.
    # With a task skill present that one wins, for the same reason it beats a
    # candidate: it is what the tracked loop keeps current.
    merged = skills / "solution-pallets-flask-4045"
    merged.mkdir(parents=True)
    (merged / "SKILL.md").write_text("# merged\n")
    assert arm.best_skill_for(tmp_path, "pallets__flask-4045") == "pallets-flask-4045"
    shutil.rmtree(skills / "pallets-flask-4045")
    assert arm.best_skill_for(tmp_path, "pallets__flask-4045") == merged.name

    # A different problem must still find nothing — this is a lookup by the
    # naming convention, not a fuzzy match on words the tasks share.
    assert arm.best_skill_for(tmp_path, "pallets__flask-5063") == ""

    # An explicit record pointer still wins over convention.
    monkeypatch.setattr(arm, "_in_store", lambda root, fn, *a, **k: "")
    assert arm.best_skill_for(tmp_path, "pallets__flask-4045") == merged.name


def test_the_session_is_folded_from_the_run_store_before_promotion():
    """Fold, then promote. The order is what carries research between runs.

    `promote_store` skips `research/sessions/` on purpose, on the understanding
    that the fold has already moved those records into the run store's common
    `research/` folder. The fold ran against the CARRY root, which has no
    sessions, so it returned "no such session" every time — and promotion then
    carried a folder nothing had been written into.
    """
    import inspect

    from tests.benchmark.runner import Runner

    sync = inspect.getsource(Runner._sync_research_session)
    # Folds where the records actually are.
    assert "store_root" in inspect.signature(Runner._sync_research_session).parameters
    assert "store_root if store_root is not None" in sync

    # And the caller folds BEFORE promoting, or the promotion is a step early.
    caller = inspect.getsource(Runner.run_task)
    assert caller.index("_sync_research_session(quiet=True, store_root=") < \
        caller.index("promote_store(store_root")


def test_a_run_stops_starting_tasks_at_its_spend_ceiling():
    """A cap on dollars, checked BEFORE each task rather than after.

    `--limit` bounds the task count and cannot bound the bill: one measured task
    cost $2.34 with three tries, while a first-try pass costs a third of that.
    And a ceiling checked after the work is a report, not a control — checking at
    the door bounds the overrun by one task instead of by the whole queue.
    """
    import threading

    from tests.benchmark.runner import Runner, RunConfig

    runner = Runner.__new__(Runner)
    runner._spent_usd = 0.0
    runner._spend_lock = threading.Lock()

    # No ceiling configured: never blocks, whatever has been spent.
    runner.config = RunConfig(out="/tmp/x", tasks=[])
    assert runner.config.max_spend_usd == 0.0
    runner._spent_usd = 10_000.0
    assert runner._over_budget() == ""

    runner.config = RunConfig(out="/tmp/x", tasks=[], max_spend_usd=50.0)
    runner._spent_usd = 49.99
    assert runner._over_budget() == ""          # under, so the next task starts
    runner._spent_usd = 50.0
    stop = runner._over_budget()
    assert stop and "50.00" in stop and "skipped" in stop


def test_the_spend_ceiling_counts_the_whole_bill():
    """`cost_usd` is the solve agent alone; research is the larger half.

    Measured on one task: solve $0.70 of a $2.34 total, because research ran
    4.5M tokens against solve's 1.3M. An earlier version of the ceiling read
    `getattr(result, "cost_total_usd", 0.0)` on a TaskResult that had no such
    property — so it defaulted to 0.0, never accumulated, and never tripped.
    """
    from tests.benchmark.metrics import Attempt, TaskResult

    task = TaskResult(instance_id="x", repo="r", arm="a")
    first = Attempt(index=1)
    first.cost_usd, first.research_cost_usd = 0.40, 1.10
    second = Attempt(index=2)
    second.cost_usd, second.research_cost_usd = 0.30, 0.54
    task.attempts = [first, second]

    # The property exists — the bug was that it did not.
    assert hasattr(task, "cost_total_usd")
    assert round(task.cost_usd, 2) == 0.70          # solve alone
    assert round(task.cost_total_usd, 2) == 2.34    # what was actually billed

    # And it reaches results.jsonl, so a grouped report reads the bill.
    assert round(task.to_dict()["cost_total_usd"], 2) == 2.34


def test_an_oversized_command_does_not_blow_the_exec_limit(tmp_path):
    """A long command must travel as a file, not as an argv element.

    `bash -lc <command>` puts the whole script in one argument, and over ssh that
    argument shares the exec limit with the ssh command line. Measured on
    `psf__requests-863`, whose PASS_TO_PASS names hundreds of tests:
    `OSError: [Errno 7] Argument list too long: 'ssh'` — the task failed with no
    patch, for a reason that had nothing to do with the agent.
    """
    from pathlib import Path as P

    from tests.benchmark.isolation import Container

    class FakeRuntime:
        def __init__(self):
            self.calls = []

        def run(self, args, timeout=300, check=False):
            self.calls.append(list(args))
            class Done:
                returncode = 0
                stdout = ""
                stderr = ""
            return Done()

    session = Container.__new__(Container)
    session.runtime = FakeRuntime()
    session.name = "c1"
    session.workdir = "/testbed"
    session.copied = []
    session.copy_in = lambda src, dest: session.copied.append((P(src).name, dest))

    # Short commands still go inline — the common path must not change.
    session.exec("pytest -q tests/test_x.py")
    assert session.runtime.calls[-1][-1] == "pytest -q tests/test_x.py"
    assert session.copied == []

    # A command past the limit is copied in and run by name; the huge text
    # never appears in argv.
    huge = "pytest -q " + " ".join(f"tests/test_{n}.py::test_case" for n in range(9000))
    assert len(huge) > Container.MAX_INLINE_COMMAND
    session.exec(huge)
    argv = session.runtime.calls[-1]
    assert len(session.copied) == 1
    assert max(len(part) for part in argv) < Container.MAX_INLINE_COMMAND
    assert huge not in " ".join(argv)
    # And it still reports the script's own exit code, not the cleanup's.
    assert "rc=$?" in argv[-1] and "exit $rc" in argv[-1]


def test_a_task_is_not_credited_with_its_neighbours_skills():
    """A shared store makes a before/after diff credit everyone's writes to one.

    Measured at 30 tasks in parallel: `sympy__sympy-21379` reported creating
    `astropy-astropy-14182`, `pallets-flask-4045`, `pytest-dev-pytest-5227` and
    six more, alongside its own real skill. Every passing task listed the same
    nine names, because all thirty diffs saw all thirty sets of writes — which
    makes `skills_created` useless as a measure of what a task produced.
    """
    from tests.benchmark.runner import Runner

    before = {"skills": ["phronix-context-economy"]}
    after = {"skills": [
        "phronix-context-economy",
        # This task's own work.
        "sympy-21379-fix-piecewise-generator-polynomialerror",
        # Its neighbours', taken verbatim from the measured run.
        "astropy-astropy-14182", "pallets-flask-4045", "pytest-dev-pytest-5227",
        "scikit-learn-scikit-learn-11040",
        # Named for a subject rather than an instance: not attributable by name.
        "dpi-unpickle-bug",
    ]}

    got = Runner._diff_created(before, after, "sympy__sympy-21379")
    assert "sympy-21379-fix-piecewise-generator-polynomialerror" in got
    for foreign in ("astropy-astropy-14182", "pallets-flask-4045",
                    "pytest-dev-pytest-5227", "scikit-learn-scikit-learn-11040"):
        assert foreign not in got
    # Honest about the limit: a subject-named skill cannot be attributed by name
    # and is still included rather than silently dropped.
    assert "dpi-unpickle-bug" in got
    # Nothing already present is ever reported as created.
    assert "phronix-context-economy" not in got

    # With no instance id — and in a sequential run, where the diff was already
    # correct — the behaviour is unchanged.
    assert Runner._diff_created(before, after) == sorted(
        set(after["skills"]) - set(before["skills"]))


def test_every_researched_plan_can_be_built_attempted_and_evaluated(
        tmp_path, monkeypatch):
    """`--attempt-candidates 0` means all of them, not none.

    A cap is right when each candidate costs an agent and a container, but it
    makes "try what research actually proposed" impossible to ask for: with five
    ideas and a cap of three, two are written up during the pass and never
    tested, and nothing records that they were skipped.
    """
    import inspect

    from tests.benchmark import arms
    from tests.benchmark.runner import Runner

    arm = arms.PhronixOpenCodeArm.__new__(arms.PhronixOpenCodeArm)
    record = {"approaches": [
        {"name": f"idea-{n}", "summary": f"do thing {n}",
         "hypothesis": f"h{n}"} for n in range(5)], "aspects": []}
    monkeypatch.setattr(arm, "_in_store", lambda root, fn, *a, **k: record)

    # A cap still caps.
    assert len(arm.candidate_plans(tmp_path, "x__y-1", limit=3)) == 3
    # 0 means every one of them.
    assert len(arm.candidate_plans(tmp_path, "x__y-1", limit=0)) == 5

    # ALL is the default, everywhere. A default of 1 pays for research to
    # explore several ideas and then tests only the top-ranked one, so the rest
    # are written up and never tried and the ranking is never checked against
    # the task's own tests.
    from tests.benchmark.runner import RunConfig
    assert RunConfig(out="/tmp/x", tasks=[]).attempt_candidates == 0
    assert arms.PhronixOpenCodeArm.attempt_candidates == 0

    # And nothing clamps it back: `max(1, ...)` would make research write one
    # merged skill while the runner raced, leaving the race one candidate.
    import inspect
    research_src = inspect.getsource(arms.PhronixOpenCodeArm.research)
    assert "max(1, int(self.attempt_candidates))" not in research_src

    # And the runner races on anything except exactly 1 — 0 must not fall
    # through to the single-attempt path, which is what "0 = none" would do.
    source = inspect.getsource(Runner.run_attempt)
    assert "wanted != 1" in source

    # Each candidate gets its own skill name, so three writers and a reader can
    # agree without negotiating.
    names = {p["skill"] for p in arm.candidate_plans(tmp_path, "x__y-1", limit=0)}
    assert len(names) == 5


def test_a_stages_budget_is_not_spent_while_it_waits_in_the_queue(monkeypatch,
                                                                  tmp_path):
    """The budget bounds work, not waiting.

    Wall-clock budgets punish a task for the size of the run it happens to be
    in. Measured at 6x oversubscription: research passes killed at `rc=-9` after
    1241s, stages reporting "out of time at 180s" having done almost nothing —
    because the fleet was serving somebody else for most of the allowance.
    """
    import json as _json

    from tests.benchmark import arms

    root = tmp_path / "llm"
    samples = root / "logs" / "sessions" / "current"
    samples.mkdir(parents=True)
    monkeypatch.setenv("LLM_ROOT", str(root))

    def write(rows):
        (samples / "samples.jsonl").write_text(
            _json.dumps({"t": 1.0, "r": rows}) + "\n")
        arms._DEFERRED_CACHE["at"] = 0.0        # defeat the cache for the test

    # `[host, up, running, deferred]` — nobody waiting.
    write([["h:1", 1, 1.0, 0.0], ["h:2", 1, 1.0, 0.0]])
    assert arms.deferred_fraction() == 0.0

    # Half the fleet has a request queued.
    write([["h:1", 1, 1.0, 1.0], ["h:2", 1, 1.0, 0.0]])
    assert arms.deferred_fraction() == 0.5

    # Everything queued: the clock should stop entirely.
    write([["h:1", 1, 1.0, 2.0], ["h:2", 1, 1.0, 1.0]])
    assert arms.deferred_fraction() == 1.0

    # No sampler at all — a hosted run has no queue of ours, and the budget must
    # behave exactly as it did before.
    (samples / "samples.jsonl").unlink()
    arms._DEFERRED_CACHE["at"] = 0.0
    assert arms.deferred_fraction() == 0.0

    # A truncated final line (the sampler writes continuously) must not raise.
    (samples / "samples.jsonl").write_text('{"t": 1.0, "r": [["h:1", 1, 1.0, 1.0]]}\n{"t": 2.0, "r": [[')
    arms._DEFERRED_CACHE["at"] = 0.0
    assert arms.deferred_fraction() == 1.0

    # And the watchdog charges by service, with a hard ceiling so a permanently
    # queued stage still ends.
    import inspect
    source = inspect.getsource(arms.stream_opencode)
    assert "charged += tick * (1.0 - waiting)" in source
    assert "hard_timeout_s" in source


def test_backend_aliases_come_from_the_gateway_not_the_deploy_file():
    """A count is not a list, and only the gateway knows which numbers exist.

    `deploy.sh` numbers aliases `@0..@N` from the host x GPU loop it INTENDS to
    launch, and writes them before knowing what came up: asked for 8 nodes x 4
    GPUs it wrote @0..@31 while 23 servers ever registered. Every agent asking
    for a missing one got `400: anthropic_messages: Invalid model name passed
    in`, once per fanned-out agent, for a whole run.
    """
    from tests.benchmark.cluster import ClusterConfig

    stale = ["gpt-oss-120b@%d" % n for n in range(32)]
    live = ["gpt-oss-120b@0", "gpt-oss-120b@1", "gpt-oss-120b@31"]

    cfg = ClusterConfig({"pinned_models": stale})
    # The gateway wins over the file, holes and all — the survivors keep their
    # original numbers, so a client counting 0..N still lands in a gap.
    cfg._aliases_from_gateway = lambda: list(live)
    assert cfg.pinned_models() == live

    # Unreachable gateway falls back to the file rather than turning affinity
    # off, which would cost the prompt cache and half the fleet's GPU time.
    cfg._aliases_from_gateway = lambda: []
    assert cfg.pinned_models() == stale

    # Neither available: empty, not an exception.
    bare = ClusterConfig({})
    bare._aliases_from_gateway = lambda: []
    assert bare.pinned_models() == []


def test_backends_are_dealt_in_turn_rather_than_hashed():
    """Hashing is stable but collides; dealing in turn is stable AND even.

    Under the `solo` profile a backend has ONE slot, so a second task hashed
    onto an occupied server queues while a neighbour idles — which is most of
    what the deferred count measures. With 30 keys over 24 backends a hash
    leaves some holding three and others none.
    """
    from tests.benchmark.cluster import ClusterConfig

    cfg = ClusterConfig({"pinned_models": [f"m@{n}" for n in range(24)]})
    cfg._aliases_from_gateway = lambda: [f"m@{n}" for n in range(24)]

    picks = [cfg.model_for(f"task-{n}") for n in range(24)]
    # Every backend used exactly once before any is used twice.
    assert sorted(picks) == sorted(f"m@{n}" for n in range(24))

    # Stable: the same key returns the same backend, so a retry lands on the
    # server that still holds its history and two arms share a warm prefix.
    assert cfg.model_for("task-7") == picks[7]
    assert cfg.model_for("task-0") == picks[0]

    # Only past the backend count does anything double up, and then evenly.
    more = [cfg.model_for(f"task-{n}") for n in range(24, 36)]
    assert len(set(more)) == 12
    counts = {m: (picks + more).count(m) for m in set(picks + more)}
    assert max(counts.values()) - min(counts.values()) <= 1

    # No pinned aliases at all: fall back to the shared name, which
    # load-balances, rather than raising.
    bare = ClusterConfig({"model": "gpt-oss-120b"})
    bare._aliases_from_gateway = lambda: []
    assert bare.model_for("task-1") == "gpt-oss-120b"


def test_the_super_idea_is_built_recorded_and_raced():
    """One more candidate: the combination of every idea, tried like the rest.

    A task is often not one bug. An attempt can put the right check in the right
    function and still fail because the same issue needed two more sites
    changed — each idea holds a piece and no single idea holds the task. So
    after the singles are written up, one further candidate combines them, and
    it is attempted and evaluated like any other.
    """
    import inspect

    from tests.benchmark import arms

    src = inspect.getsource(arms.PhronixOpenCodeArm.research)
    body = src[src.index('super_name = "super-idea"'):]

    # Built after the singles, from all of them.
    assert "SUPER_IDEA_PROMPT" in body
    assert "findings" in body
    # Recorded as an approach, or `candidate_plans` cannot see it and the skill
    # is built at full cost and never run.
    assert "add_approach" in body
    # With a falsifiable hypothesis, so the race tests the combination rather
    # than crowning it.
    assert "no more" in body and "target tests" in body

    # The prompt itself demands specificity, because a weaker model implements it.
    prompt = arms.PhronixOpenCodeArm.SUPER_IDEA_PROMPT
    assert "files, functions, line numbers" in prompt
    assert "phronix-skill-authoring" in prompt
    # And it must be willing to say the ideas do NOT combine.
    # The steps are assembled into a method; when they genuinely do not
    # compose, saying so beats manufacturing a merge.
    assert "turn out not to compose" in prompt

    # It is an ADDITIONAL racer: the singles are written before it, not replaced.
    assert body.index("add_approach") > 0
    assert "write_candidate" in src[:src.index('super_name = "super-idea"')]


def test_the_ledgers_file_lists_are_not_raced_as_ideas(tmp_path, monkeypatch):
    """An attempt's list of changed files is not a plan.

    Taken from `pylint-dev__pylint-7114`: the ledger records one entry per try
    whose NAME is the files that changed, and `a/__init__.py, a/a.py` became
    `trial-1-a-init-py-a-a-py` — a container, an agent and an evaluation spent
    on a file list, which also displaced a real idea from the limit.
    """
    from tests.benchmark import arms

    arm = arms.PhronixOpenCodeArm.__new__(arms.PhronixOpenCodeArm)
    record = {"aspects": [], "approaches": [
        {"name": "a/__init__.py, a/a.py", "source": "benchmark attempt"},
        {"name": "src/pylint/lint.py", "source": ""},        # path-shaped
        {"name": "(no files changed)", "source": ""},
        {"name": "super-idea", "summary": "the combination", "status": "potential"},
        {"name": "module_resolution", "summary": "resolve modules differently"},
    ]}
    monkeypatch.setattr(arm, "_in_store", lambda root, fn, *a, **k: record)

    names = [p["name"] for p in
             arm.candidate_plans(tmp_path, "pylint-dev__pylint-7114", limit=0)]
    assert names == ["super-idea", "module_resolution"]


def test_a_task_recognises_its_own_skill_and_rejects_a_neighbours(
        tmp_path, monkeypatch):
    """The record's pointer is written last; the skill exists throughout.

    Measured on `pylint-dev__pylint-7114`: while `build-solution` was still
    running, every racer was told `pylint-dev-pylint-7114` "was written for
    another problem in this area" — the task's own answer demoted to background
    reading, because no pointer had been set yet.
    """
    from tests.benchmark import arms

    arm = arms.PhronixOpenCodeArm.__new__(arms.PhronixOpenCodeArm)
    topic = "pylint-dev__pylint-7114"
    # Mid-pass: real content, no pointer yet.
    monkeypatch.setattr(arm, "_in_store", lambda root, fn, *a, **k:
                        {"aspects": [{"name": "create_init"}],
                         "approaches": [{"name": "super-idea"}]})

    assert arm._skill_is_for(tmp_path, "pylint-dev-pylint-7114", topic) is True
    assert arm._skill_is_for(
        tmp_path, arm.candidate_skill_name(topic, "super-idea"), topic) is True
    assert arm._skill_is_for(
        tmp_path, arm.candidate_skill_name(topic, "create_init"), topic) is True

    # A DIFFERENT pylint bug is still rejected — that is what the check is for.
    assert arm._skill_is_for(tmp_path, "pylint-dev-pylint-7080", topic) is False
    assert arm._skill_is_for(tmp_path, "solution-sympy-sympy-21847-x", topic) is False


def test_synthetic_entries_do_not_become_research_ideas():
    """`super_idea` and `no_files_changed` are bookkeeping, not ideas.

    Measured on `pylint-dev__pylint-7114` try 3, whose idea list came back as
    `a_init_py, rename_a_py, super_idea, no_files_changed,
    pylint_auto_init_helper` — the candidate the previous try synthesised, and
    the ledger's note that an attempt changed nothing, both queued for
    exploration.
    """
    from tests.benchmark import arms

    arm = arms.PhronixOpenCodeArm
    for junk in ("super_idea", "super-idea", "no_files_changed",
                 "(no files changed)", "a/__init__.py, a/a.py", "src/lint.py"):
        assert arm._is_synthetic_idea(junk), junk
    for real in ("create_init", "module_resolution", "namespace_pkg_handling",
                 "file_collection_order", "rename_a_py"):
        assert not arm._is_synthetic_idea(real), real


def test_ideas_that_look_in_the_same_place_are_not_independent():
    """Several readings of one function are one reading with several names.

    Measured on `pylint-dev__pylint-7114`: four ideas survived validation —
    `module-name-conflict-resolution`, `init-file-fallback`,
    `module-search-order`, `expand_modules` — and every resulting patch changed
    `get_python_path` in `pylint/lint/expand_modules.py`. The super idea built
    from them rewrote the same loop. Three tries, five containers each, every
    candidate scoring 0.
    """
    from tests.benchmark import arms

    overlap = arms.PhronixOpenCodeArm.overlapping_ideas

    # The measured case: four names, one file.
    clashes = overlap([
        {"name": "module-name-conflict-resolution",
         "where": "pylint/lint/expand_modules.py get_python_path"},
        {"name": "init-file-fallback", "where": "pylint/lint/expand_modules.py"},
        {"name": "module-search-order",
         "where": "line 40 of pylint/lint/expand_modules.py"},
    ])
    assert "pylint/lint/expand_modules.py" in clashes
    assert len(clashes["pylint/lint/expand_modules.py"]) == 3

    # Genuinely different places are not a clash.
    assert overlap([
        {"name": "caller", "where": "pylint/lint/pylinter.py"},
        {"name": "producer", "where": "pylint/lint/expand_modules.py"},
        {"name": "config", "where": "pylintrc"},
    ]) == {}

    # An idea with no `where` is its own island: the remedy is to ask for one,
    # not to guess that it overlaps.
    assert overlap([{"name": "a"}, {"name": "b"}]) == {}


def test_the_plan_loop_asks_again_when_the_ideas_overlap():
    """Enough ideas is not the same as enough DIFFERENT ideas.

    The loop counted them and stopped, so a set aimed entirely at one function
    passed and cost three tries to disprove.
    """
    import inspect

    from tests.benchmark import arms

    src = inspect.getsource(arms.PhronixOpenCodeArm.research)
    assert "clashes = self.overlapping_ideas(ideas)" in src
    # The count alone must no longer be sufficient to break out.
    assert "if len(ideas) >= self.MIN_ASPECTS and not clashes:" in src
    # And the ask names the overlap — "be more diverse" gets a rename.
    assert "all look in" in src


def test_a_task_earns_another_try_by_getting_further_through_the_method(
        isolated_layers, monkeypatch):
    """Progress is a position in the method, not a passing test.

    "0 target tests passing" reads the same on try 1 and try 3. Failing at step 2
    and then at step 4 is a task closing in, and stopping it at a fixed ceiling
    throws that away.
    """
    from phronix import research

    directory = isolated_layers["store"] / "research"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "t.json").write_text(json.dumps({
        "topic": "t", "slug": "t",
        "aspects": [{"name": "decide-package-kind"}, {"name": "compute-name"},
                    {"name": "choose-root"}, {"name": "keep-passing"}]}))
    monkeypatch.setenv(research.TOPIC_ENV, "t")

    # Nothing recorded yet: no progress to reward.
    assert research.furthest_step("t")["advanced"] is False

    research.record_step_reached("t", "decide-package-kind", "wrong branch")
    first = research.furthest_step("t")
    assert first["furthest"] == 0 and first["of"] == 4
    assert first["advanced"] is False          # one data point is not a trend

    # Failing at a LATER step is progress.
    research.record_step_reached("t", "choose-root", "root was the parent")
    assert research.furthest_step("t")["advanced"] is True
    assert research.furthest_step("t")["furthest"] == 2

    # Failing EARLIER again is not.
    research.record_step_reached("t", "compute-name")
    assert research.furthest_step("t")["advanced"] is False
    assert research.furthest_step("t")["furthest"] == 2   # the best still stands

    # A step nobody planned cannot count as progress.
    research.record_step_reached("t", "invented-step")
    assert research.furthest_step("t")["advanced"] is False


def test_the_retry_loop_can_award_the_earned_try():
    """The ceiling has to be able to move, or the signal changes nothing."""
    import inspect

    from tests.benchmark.runner import Runner

    src = inspect.getsource(Runner.run_task)
    assert "while attempt_index < ceiling + earned:" in src
    assert "furthest_step" in src
    # Bounded: a long method must not earn a try per step forever.
    assert "MAX_EARNED" in src


def test_ways_of_doing_one_step_must_differ_from_each_other_too():
    """The independence rule governs ways within a step, not only the steps.

    Two ways that touch the same line are one way described twice, and the
    pipeline races them as if they were two — a container and an evaluation
    each. Measured shape, from `pylint-dev__pylint-7114`: "return the parent
    when __init__.py is absent" and "walk up while __init__.py exists" are the
    same line inverted.
    """
    from tests.benchmark import arms

    overlap = arms.PhronixOpenCodeArm.overlapping_ideas

    # Ways carry `summary`/`hypothesis` rather than `where`; the same check
    # must see them.
    clashes = overlap([
        {"name": "return-parent",
         "summary": "in pylint/lint/expand_modules.py return the parent"},
        {"name": "walk-up",
         "hypothesis": "in pylint/lint/expand_modules.py walk up instead"},
    ])
    assert "pylint/lint/expand_modules.py" in clashes

    # Genuinely different places stay distinct — caller, callee, config.
    assert overlap([
        {"name": "from-package-chain", "summary": "pylint/lint/expand_modules.py"},
        {"name": "ask-astroid", "summary": "astroid/modutils.py"},
        {"name": "caller-passes-root", "summary": "pylint/lint/pylinter.py"},
    ]) == {}


def test_ideas_are_salvaged_from_any_planning_round(monkeypatch):
    """A planner that names its steps in a LATER round must still be heard.

    Salvage read `last_output["plan"]` alone. Measured on
    `pylint-dev__pylint-7114`: `plan` wrote "Problem Summary (from exchange.md
    and issue.md)" and recorded nothing, then `plan-more-1` wrote "Three new
    research aspects for pylint-dev__pylint-7114" and also recorded nothing. The
    steps existed in prose, in the output salvage did not read, while the
    validator judged an empty list round after round for twenty minutes.
    """
    import inspect

    from tests.benchmark import arms

    src = inspect.getsource(arms.PhronixOpenCodeArm.research)
    salvage = src[src.index("Salvage from EVERY planning stage"):]

    # Every planning stage is read, not just `plan`.
    assert 'name.startswith(("plan-more"' in salvage
    assert 'name == "plan"' in salvage
    # Later rounds first: the planner's most considered answer, written after
    # being told what was missing.
    assert "sorted(last_output.items()," in salvage and "reverse=True" in salvage
    # Deduplicated by name, so one idea named twice is not two.
    assert "seen" in salvage

    # And the silent case is now loud.
    assert "recorded NOTHING" in src
    assert "not researching THIS problem" in src


def test_budget_scale_is_explicit_measured_or_tuned(tmp_path, monkeypatch):
    """The stage budgets scale to the machine, and say which source decided it.

    A stage budget is a number of seconds, but what a stage needs is a number
    of tool calls — so a budget only means something paired with the decode
    rate it was measured at. Left at 1.0 on a slow fleet, every planning agent
    is killed mid-investigation and the run is scored as though the research
    happened, which is the failure this resolver exists to prevent.
    """
    import json as _json

    from tests.benchmark import arms

    arms._BUDGET_SCALE_CACHE["value"] = None

    # An explicit number wins outright, and is clamped: a scale below 1.0 would
    # make budgets tighter than the calibration, which no measurement justifies.
    monkeypatch.setenv("PHRONIX_BUDGET_SCALE", "12")
    assert arms.budget_scale() == 12.0
    monkeypatch.setenv("PHRONIX_BUDGET_SCALE", "0.1")
    assert arms.budget_scale() == arms.BUDGET_SCALE_BOUNDS[0]
    monkeypatch.setenv("PHRONIX_BUDGET_SCALE", "9999")
    assert arms.budget_scale() == arms.BUDGET_SCALE_BOUNDS[1]

    # `auto` derives it from what the fleet is actually decoding.
    config = tmp_path / "cluster.json"
    config.write_text(_json.dumps(
        {"servers": [{"host": "h1", "port": 1}, {"host": "h2", "port": 2}]}))
    monkeypatch.setenv("PHRONIX_CLUSTER", str(config))
    monkeypatch.setenv("PHRONIX_BUDGET_SCALE", "auto")

    monkeypatch.setattr(arms, "measured_decode_rate", lambda: 40.0)
    arms._BUDGET_SCALE_CACHE["value"] = None
    assert arms.budget_scale() == arms.CALIBRATION_TOKENS_PER_S / 40.0

    # No fleet to measure is a HOSTED endpoint — faster than the calibration,
    # not equal to it, so it gets its own scale below 1.0. Holding hosted runs
    # at 1.0 spends minutes per stage on agents that finished thinking long
    # before the clock did.
    monkeypatch.setattr(arms, "measured_decode_rate", lambda: None)
    # HOSTED means no fleet at all. An unmeasurable rate alone no longer
    # implies it: a local fleet reads 0 tok/s until it has served something,
    # which is true of every batch run at t=0, and calling that "hosted"
    # halved every budget on the slowest hardware we own. See
    # `test_a_local_fleet_that_has_not_served_yet_is_not_mistaken_for_hosted`.
    monkeypatch.setattr(arms, "has_local_fleet", lambda: False)
    arms._BUDGET_SCALE_CACHE["value"] = None
    hosted = arms.budget_scale()
    assert hosted == float(arms._tuned("research.hosted_budget_scale", 0.5))
    assert hosted < 1.0
    # And the floor allows it: budgets tighter than the calibration are the
    # point on hardware the calibration was not measured on.
    assert arms.BUDGET_SCALE_BOUNDS[0] < 1.0

    # Unset falls back to tuning.yaml, the pin-it-by-hand path.
    monkeypatch.delenv("PHRONIX_BUDGET_SCALE", raising=False)
    arms._BUDGET_SCALE_CACHE["value"] = None
    assert arms.budget_scale() == float(arms._tuned("research.budget_scale", 1.0))


def test_measured_decode_rate_ignores_replicas_that_served_nothing(tmp_path, monkeypatch):
    """A replica reporting 0 tok/s has not served yet — it is not a slow fleet.

    `predicted_tokens_seconds` only advances when a request FINISHES, so a
    freshly-deployed fleet reads zero everywhere. Averaging those in would
    drive the derived scale to its ceiling and give every stage hours it has no
    reason to need.
    """
    import json as _json

    from tests.benchmark import arms

    config = tmp_path / "cluster.json"
    config.write_text(_json.dumps({"servers": [
        {"host": "h1", "port": 1}, {"host": "h2", "port": 2},
        {"host": "h3", "port": 3}]}))
    monkeypatch.setenv("PHRONIX_CLUSTER", str(config))

    bodies = {
        "http://h1:1/metrics": "llamacpp:predicted_tokens_seconds 0\n",
        "http://h2:2/metrics": "llamacpp:predicted_tokens_seconds 30.5\n",
        "http://h3:3/metrics": "llamacpp:predicted_tokens_seconds 34.5\n",
    }

    class _Response:
        def __init__(self, text): self.text = text
        def read(self): return self.text.encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(arms.urllib.request, "urlopen",
                        lambda url, timeout=5: _Response(bodies[url]))
    # Median of the two that answered — 0 is dropped, not averaged in.
    assert arms.measured_decode_rate() == 34.5

    # Nothing has served anything: unknowable, not "infinitely slow".
    for key in bodies:
        bodies[key] = "llamacpp:predicted_tokens_seconds 0\n"
    assert arms.measured_decode_rate() is None


def test_aspects_must_be_steps_of_a_method_not_a_list_of_fixes(tmp_path, monkeypatch):
    """The aspects slot holds the STEPS. Filling it with ways is silent damage.

    Measured on django__django-13551 under Haiku: the planner recorded
    `A1: Direct email with getattr() fallback` and `A2: Model method factoring`
    as its aspects — four rival edits to one function, not a method. Every
    count in the record read healthy, so nothing reported it, while the
    decomposition the pipeline is built on had not happened:
    `record_step_reached` had no real position to report and
    `research_add_approach(aspect=...)` attached ways to something that was
    already a way.

    The `A1:`/`A2:` shape is not a coincidence — `research_add_approach` hands
    back keys with exactly those names, so it is easy to echo back.
    """
    from phronix import research

    monkeypatch.setattr(research, "RESEARCH_DIR", tmp_path)

    ways = research.set_aspects("t", [
        {"name": "A1: Direct email with getattr() fallback",
         "question": "does reading the field directly work?",
         "where": "django/contrib/auth/tokens.py"},
        {"name": "A2: Model method factoring",
         "question": "should the model expose the value?",
         "where": "django/contrib/auth/base_user.py"}])
    assert ways["status"] == "error"
    assert "not STEPS" in ways["error"]
    assert "I5b" in ways["error"]

    # `I6` applied to steps: ANY repeated `where` means those two are one step
    # with two ways, whatever the rest of the list is doing.
    #
    # Not a unanimous test. Measured on django-13551 once the naming rule went
    # in: the planner dropped the `A1:`/`A2:` shape and produced
    # `safe-email-field-access-with-classmethod` /
    # `try-except-email-field-access` / `factor-token-data-to-model-method` —
    # still three rival implementations, two in the same method, and an
    # "all in one place" test would have let it straight through.
    same_place = research.set_aspects("t", [
        {"name": "safe access via classmethod", "question": "q1",
         "where": "django/contrib/auth/tokens.py _make_hash_value"},
        {"name": "try/except around the field", "question": "q2",
         "where": "django/contrib/auth/tokens.py _make_hash_value"},
        {"name": "factor onto the model", "question": "q3",
         "where": "django/contrib/auth/models.py"}])
    assert same_place["status"] == "error"
    assert "same place are ONE step" in same_place["error"]

    # A genuine method is recorded untouched: named after what must become
    # true, each step somewhere different.
    method = research.set_aspects("t", [
        {"name": "locate the inputs the token hashes", "question": "which fields?",
         "where": "django/contrib/auth/tokens.py _make_hash_value"},
        {"name": "include the user's current email", "question": "how is it read?",
         "where": "django/contrib/auth/base_user.py get_email_field_name"},
        {"name": "keep tokens valid for users with no email", "question": "what then?",
         "where": "tests/auth_tests/test_tokens.py"}])
    assert method["status"] == "ok"
    assert len(method["aspects"]) == 3


def test_an_approach_is_told_which_step_it_belongs_to(tmp_path, monkeypatch):
    """A way that names no step cannot be attributed when a try fails.

    Guidance rather than rejection: approaches also arrive from the benchmark's
    own attempt ledger, which has no steps to cite. But once a method exists, a
    floating way defeats the reason for decomposing — "failed at step 3" says
    which step to redo, "the approach failed" says start again.
    """
    from phronix import research

    monkeypatch.setattr(research, "RESEARCH_DIR", tmp_path)

    research.set_aspects("t", [
        {"name": "locate the inputs the token hashes", "question": "which?",
         "where": "tokens.py"},
        {"name": "include the user's current email", "question": "how?",
         "where": "base_user.py"}])

    floating = research.add_approach(
        "t", "read the field directly", "getattr on the email field",
        hypothesis="the field is present on the base model; absent means None")
    assert floating["status"] == "ok"
    assert "attach this to the step" in floating.get("next", "")

    # A way recorded when NO method exists at all. The steps gate cannot catch
    # this — there is nothing to reject — so it is said as the way goes in.
    # Observed live on django-13551: the planner skipped `set_aspects` and went
    # straight to recording approaches.
    research.set_aspects("fresh", [{"name": "placeholder", "question": "q",
                                    "where": "x.py"}])
    empty = research.load("fresh")
    empty["aspects"] = []
    research._save(empty)
    first = research.add_approach("fresh", "a way", "does a thing", hypothesis="h")
    assert "no method has been recorded" in first.get("next", "")

    # The benchmark's own ledger has no steps to cite and must not be nagged.
    ledger = research.add_approach("fresh", "some/file.py", "attempted by editing",
                                   hypothesis="h", source="benchmark attempt")
    assert "no method has been recorded" not in ledger.get("next", "")

    unknown = research.add_approach(
        "t", "another way", "does something else", hypothesis="h",
        aspect="a step nobody planned")
    assert "not one of the planned steps" in unknown.get("next", "")

    attached = research.add_approach(
        "t", "a third way", "does a third thing", hypothesis="h",
        aspect="include the user's current email")
    assert "next" not in attached


def test_a_planning_stage_that_recorded_nothing_is_asked_to_file_its_ideas():
    """Finding ideas and not recording them is the same as finding none.

    Measured on django-13551 under Haiku: two scouts ran `ToolSearch` for
    `research_add_aspects`, then used Bash to "create JSON with research aspects
    to explore". The ideas existed, in a file nobody reads; the record stayed
    empty; the trace showed every stage completing normally; and the whole
    exploration phase was skipped in silence.

    The round-level retry re-runs the WHOLE planning cycle when the count is
    short, by which time this pass's ideas are gone. The re-ask happens while
    the agent still has them.
    """
    from tests.benchmark.arms import ClaudePhronixArm

    # Normalised: these prompts are hard-wrapped, so a phrase that reads as one
    # line in the file is split by a newline in the string.
    flat = lambda text: " ".join(text.split())

    prompt = flat(ClaudePhronixArm.RECORD_ASPECTS_PROMPT)
    # It must not send the agent back to investigate — the work is done, and
    # re-investigating is what the budget was already spent on.
    assert "Do not investigate anything further" in prompt
    assert "research_add_aspects" in prompt
    # It has to name the specific wrong place the ideas went, or the agent has
    # no reason to believe its file did not count.
    assert "Writing JSON to a file" in prompt
    # And it carries the two rules the tool will reject on, so the re-ask does
    # not simply fail the gate a second time.
    assert "not how you" in prompt
    assert "DIFFERENT" in prompt

    # And it runs as the FILER, which can read and record and nothing else.
    #
    # Asking more firmly does not work. Measured on django-13551: this exact
    # prompt, which says "Do not investigate anything further", was handed to a
    # stage holding file tools — which spent its whole turn reading tests,
    # editing tokens.py and diffing the result, and never called the tool. The
    # only reliable way to make the call unavoidable is to leave nothing else
    # the agent CAN do.
    from tests.benchmark.arms import ClaudePhronixArm as _Arm

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    reask = source[source.index('stage(f"{name}-record"'):]
    assert "agent=self.filer_agent_name" in reask[:400]

    arm = _Arm.__new__(_Arm)
    tools = set(_Arm._agent_spec(_Arm.filer_agent_name).get("tools") or [])
    denied = set(" ".join(
        arm._denial_flags(_Arm.filer_agent_name)).split()[-1].split(","))
    # It can file both kinds of record — aspects for a planning stage, ways for
    # a scout — because one agent rescues every stage.
    assert {"mcp__phronix__research_add_aspects",
            "mcp__phronix__research_add_approach"} <= tools
    # And it cannot edit, run, or delegate its way back to the tools withheld.
    assert not tools & {"Bash", "Edit", "Write", "Agent", "Task"}
    assert {"Bash", "Edit", "Write", "Agent", "Task"} <= denied

    # The scout prompt closes the same door up front: the re-ask is the net.
    scout = flat(ClaudePhronixArm.PLAN_SCOUT_PROMPT)
    assert "The tool call is the only thing that records an idea" in scout
    assert "never for the ideas themselves" in scout


def test_where_is_compared_by_the_place_it_names_not_its_wording():
    """Three descriptions of one function are one place, not three.

    The same-place rule is what stops ways being recorded as steps, and
    comparing `where` literally hands the planner an easy way around it.
    Measured on django-13551 after the rule went in — eight aspects were
    accepted, three of them pointing at the same method:

        django/contrib/auth/tokens.py _make_hash_value() method
        django/contrib/auth/tokens.py _make_hash_value() implementation
        django/contrib/auth/tokens.py:_make_hash_value()
    """
    from phronix.research import _looks_like_alternatives, _where_key

    a = _where_key("django/contrib/auth/tokens.py _make_hash_value() method")
    b = _where_key("django/contrib/auth/tokens.py _make_hash_value() implementation")
    c = _where_key("django/contrib/auth/tokens.py:_make_hash_value()")
    assert a == b == c

    # Different functions in one file stay different places.
    assert _where_key("tokens.py:check_token()") != a
    # As do different files.
    assert _where_key("base_user.py:AbstractBaseUser") != a

    # A `where` naming neither a file nor an identifier says nothing about
    # collision, so it is not compared — two vague ones are not "the same place".
    assert _where_key("Test subtests with email=None parameter") == ""
    vague = [{"name": "one", "where": "somewhere in the auth code"},
             {"name": "two", "where": "around the token logic"}]
    assert _looks_like_alternatives(vague) == ""

    # The live eight-aspect list is caught.
    assert "same place are ONE step" in _looks_like_alternatives([
        {"name": "Safe Attribute Access Pattern",
         "where": "django/contrib/auth/tokens.py _make_hash_value() implementation"},
        {"name": "modify-make-hash-value",
         "where": "django/contrib/auth/tokens.py:_make_hash_value()"}])


def test_the_search_for_more_steps_is_bounded_once_the_floor_is_met():
    """`min_aspects` is a floor, not a target, and past it the clock runs.

    Measured on django-13551: the loop kept eight independent steps, asked for
    three more, and was still asking twenty-five minutes into a task the bare
    arm had already finished twice. Nothing was failing — the search simply had
    no reason to stop. When the clock runs out the pass finalises with what it
    found and continues, rather than trading an unbounded amount of wall-clock
    for ideas it does not need.
    """
    from phronix.tuning import get

    # A clock, not a round cap: rounds are not the cost, an agent reading the
    # repository for one more idea is.
    assert int(get("research.extra_ideas_seconds", 240)) > 0

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # Scaled like every other research clock, so a slow endpoint is not cut off
    # mid-idea for being slow.
    assert 'int(_tuned("research.extra_ideas_seconds", 240)' in source
    assert "* budget_scale())" in source
    # And the floor still has to be MET before the clock starts.
    assert "if len(ideas) >= self.MIN_ASPECTS and not clashes:" in source


def test_the_method_is_written_first_and_the_ways_fan_out_over_its_steps():
    """One writer for the decomposition; the parallelism moves to the ways.

    The old shape was one bag: the planner and every angle scout proposed ideas
    at once, the validator filtered, and a count decided when to stop. That
    cannot produce a method, because nobody is asked for one — four agents each
    answering "what could fix this?" return four rival fixes however the prompt
    is worded, and a gate downstream can only reject the wrong shape, never
    supply the missing one. Four successive tightenings on django-13551 each
    caught their evasion and were met by the same shape in new clothes.
    """
    from tests.benchmark.arms import ClaudePhronixArm

    flat = " ".join(ClaudePhronixArm.REFINE_IDEA_PROMPT.split())

    # A scout owns ONE step and is told which steps are not its own, so two
    # scouts cannot produce two ways of the same thing.
    assert "You own one idea" in flat
    assert "which are NOT yours" in flat
    # Ways attach to their step, or they cannot be attributed on failure.
    assert 'aspect="{step}"' in ClaudePhronixArm.REFINE_IDEA_PROMPT
    # Different means "fails differently", not "worded differently".
    assert "SEQUENCE OF STEPS your idea takes" in flat
    # Finding only one workable way is a real answer, not a shortfall to pad.
    assert "makes the idea refutable" in flat

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # The method is recorded before any ways scout starts — they read it.
    assert (source.index('recording_stage("plan", still_failing + self.PLAN_PROMPT')
            < source.index("def ways(job)"))
    # The angle scouts remain only for the case where no method was recorded.
    assert "if not method:" in source


def test_a_stage_rescue_can_only_record_never_continue_the_stage():
    """Every rescue runs as the filer, whatever the stage it is rescuing was.

    `FINALIZE_PROMPT` has always said "you are not continuing the stage; do not
    read files, run commands or search", and asking has never been enough.
    Measured on django-13551: a ways-scout rescue ran `git diff`, announced
    "the fix is complete and correct", verified the tests, and recorded no
    approach at all — confirming the very patch that had scored 1/2 and lost
    the task.

    Inheriting the stage's own agent was the previous fix and was not enough:
    most stages run unrestricted, so most rescues did too.
    """
    from tests.benchmark.arms import ClaudePhronixArm as _Arm

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    start = source.index('stage(f"{name}-finalize"')
    # The whole call, not up to the first ")" — the prompt's own .format(...)
    # closes a paren long before the argument list does.
    call = source[start:source.index("except Exception", start)]
    assert "agent=self.filer_agent_name" in call, (
        "a rescue must run restricted, or it continues the stage instead of "
        "filing it")


def test_exploration_starts_as_ideas_are_kept_not_after_the_plan_finishes():
    """The plan emits; exploration consumes. No barrier between them.

    The plan used to have to finish before any idea was explored — rounds of
    proposing and judging, then a barrier, then the fan-out — so the first
    idea, often the good one recorded in the first minute, sat idle for as long
    as the planner spent looking for its third. Measured on scikit-learn-25570:
    four steps recorded at 20:48, still in `plan-more-1` at 21:13, none of them
    explored.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    # The consumer exists before the plan loop, and the loop feeds it.
    assert source.index("def drain_ideas()") < source.index("while tries_at_plan <")
    loop = source[source.index("while tries_at_plan <"):source.index("# The plan's OTHER two outputs")]
    assert "drain_ideas()" in loop, "the plan loop must hand ideas over as it keeps them"

    # Submitted exactly once, keyed by name: the validator rewrites the record
    # each round, and re-submitting would explore an idea twice and pay twice.
    assert "if not name or name in submitted:" in source
    # And still bounded — streaming is not a licence to explore everything.
    assert "if len(submitted) >= self.max_parallel_aspects:" in source


def test_research_can_test_a_candidate_while_it_is_still_generating():
    """The seam between research and evaluation, and what it is for.

    Research and evaluation used to be strictly sequential: research ran to
    completion, the runner then raced every candidate, and only then did anyone
    learn whether any of them worked. So a pass kept generating and combining
    ideas long after one had already solved the task, and the idea recorded in
    the first minute was tested last.
    """
    import inspect

    from tests.benchmark.arms import Arm, ClaudePhronixArm
    from tests.benchmark.runner import Runner

    # Every arm accepts the seam; arms that do no research ignore it.
    assert "trial" in inspect.signature(Arm.research).parameters
    assert "trial" in inspect.signature(ClaudePhronixArm.research).parameters
    assert hasattr(Runner, "trial_runner")

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    # A candidate is tested as it is written, not after the whole set is.
    assert "def write_and_try(job)" in source
    # A pass that succeeds stops generating — that is the point of the seam.
    assert "stop_generating.set()" in source
    plan_loop = source[source.index("while tries_at_plan <"):]
    assert "if stop_generating.is_set():" in plan_loop[:900]
    # And the combination is skipped, being a bet that is pointless once one
    # idea fixes the whole task on its own.
    assert "skipping the combination" in source

    runner_source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    # The runner uses what research measured rather than racing it again: a
    # second race costs a container and an agent per plan to re-derive a
    # verdict already on file.
    assert 'measured = (research or {}).get("trials") or []' in runner_source
    # A trial never raises — one candidate lost is not the pass lost.
    trial_body = runner_source[runner_source.index("def trial_runner"):
                               runner_source.index("def _race_plans")]
    assert "except Exception as exc:" in trial_body


def test_a_restricted_agent_cannot_delegate_its_way_out_of_the_restriction():
    """Denying Bash means nothing if the agent can spawn one that has it.

    A sub-agent is a fresh session with the DEFAULT tool set, so delegation
    hands back everything the parent was denied. Measured on django-13551:
    `plan-record` runs as the validator, denied Bash precisely so the re-ask
    files its ideas rather than going off to fix the code — and the trace shows
    it running the Django token tests anyway, via "Background agent is running.
    I'll continue when it completes".
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    arm = Arm.__new__(Arm)
    denied = set(" ".join(arm._denial_flags("phronix-validator")).split()[-1].split(","))

    # The tools the restriction is about.
    assert {"Bash", "Edit", "Write"} <= denied
    # And every way to obtain them second-hand.
    assert {"Agent", "Task"} <= denied

    # The agent can still do its job: read, and record what it found.
    spec = Arm._agent_spec("phronix-validator")
    tools = set(spec.get("tools") or [])
    assert "mcp__phronix__research_add_aspects" in tools, (
        "the re-ask runs as this agent — without the recording tool it is "
        "denied every way to act, which is worse than not restricting it")
    assert {"Read", "Grep", "Glob"} <= tools
    assert not tools & denied


def test_retry_prompts_say_the_tree_holds_the_failed_attempt():
    """A revision pass reads a patched tree, and nothing used to say so.

    The checkout handed to a retry still holds the edits of the attempt that
    just FAILED, so the fix often looks as though it is already there — because
    it is, and it did not work. Measured on django-13551 under Haiku: `plan`
    read `tokens.py`, concluded "the implementation is complete and correct",
    and recorded no steps; its re-ask read the same file and agreed. Two full
    stages spent confirming a patch that had scored 1/2 and lost the task.

    The agent was not being lazy. It was handed a workspace that argues there
    is nothing to do, and believed it.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    note = " ".join(Arm.PATCHED_TREE_NOTE.split())
    # It has to say what the tree IS, not merely "check exchange.md".
    assert "The working tree is NOT the original code" in note
    # And name the trap in the words the model actually used.
    assert "implementation is complete" in note
    assert "exchange.md" in note

    # Every stage that reads the retry checkout carries it.
    for name in ("PLAN_PROMPT", "PLAN_SCOUT_PROMPT", "REFINE_IDEA_PROMPT",
                 "RECORD_ASPECTS_PROMPT"):
        assert "working tree is NOT the original code" in getattr(Arm, name), name


def test_each_idea_is_carried_to_a_verdict_on_its_own_thread():
    """An idea is a way of solving the WHOLE problem, and it finishes alone.

    Building every solution and then racing them made the first workable idea
    wait for the slowest one to finish being explored — and exploring the
    others is exactly the work a success makes unnecessary. Measured on
    django-13551: 64 minutes in the plan phase, 300 validator calls, zero
    trials, because nothing reached a verdict until everything had.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    # Explored -> written up -> put in front of the tests, in one thread.
    assert "def finish_idea(idea" in source
    assert source.count("return finish_idea(idea)") == 2   # both exits
    assert "def build_and_try(plan" in source

    # Two tried ideas are combined immediately, not after the last one lands.
    assert "def combine_if_ready()" in source
    assert "if len(have) < 2:" in source

    # A pass stops the plan and lets the rest file what they have.
    assert "stop_generating.set()" in source
    assert "the ones in flight will file what they" in source
    # Nothing is built or tried twice, however many ideas name the same plan.
    assert 'if name in built:' in source
    # And an idea that lands while a solve is in flight does not start a build.
    assert "if trial is None or stop_generating.is_set():" in source


def test_the_remaining_failure_is_the_subject_of_the_next_research_pass():
    """A partial pass leaves data; research must build on it, not restart.

    Measured on django-13551 at 1 of 2: `exchange.md` carried the verdict at
    line 299 of a 403-line file, under the whole transcript and above eighty
    `Destroying test database for alias 'other'...` lines. The pass recorded a
    single step — "Email included in token hash" — which is the half that
    ALREADY PASSES, and never touched `test_token_with_different_secret`, the
    one that does not.
    """
    from tests.benchmark.arms import (ClaudePhronixArm as Arm,
                                      _useful_test_output)

    note = " ".join(Arm.STILL_FAILING_NOTE.split())
    assert "{failing}" in Arm.STILL_FAILING_NOTE
    # It has to say the fixed half is DONE, or the pass re-derives it.
    # It names what already WORKS as well as what is broken. A partial pass is
    # evidence in both directions, and only one was being carried.
    assert "{working}" in Arm.STILL_FAILING_NOTE
    assert "already got RIGHT, confirmed by the tests" in note
    assert "re-derives them costs this pass and changes no verdict" in note
    # And says why abandoning the working half is not neutral.
    assert "regresses a target test the run has already banked" in note
    assert "Decompose against the failing tests" in note

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # Injected into every stage that plans against the failure — an attachment
    # is not an instruction, and the stage told to "summarise the problem from
    # exchange.md" summarised the ISSUE.
    assert source.count("still_failing + self.") >= 3
    # Read from the measured verdict, not from a summary of it.
    assert 'seen.get("fail_to_pass_failing")' in source

    # And the teardown noise no longer occupies the end of the captured output,
    # which is the position a skimming reader weights most.
    cleaned = _useful_test_output(
        "FAIL: test_x\nAssertionError: 1 != 2\n"
        + "Destroying test database for alias 'other'...\n" * 80)
    assert cleaned.startswith("FAIL: test_x")
    assert "Destroying test database" not in cleaned
    assert "80 test-database setup/teardown line(s) removed" in cleaned


def test_a_solved_task_leaves_a_skill_the_next_run_can_look_up():
    """A pass must leave something findable, not only something recorded.

    `best_skill_for` does not search — it LOOKS UP `solution-<topic>` before
    the attempt starts. Measured on django-13551: the attempt passed 2 of 2,
    the learner wrote a memory holding the correct fix and the corner case that
    broke the earlier version, and no skill. The store held the answer and the
    one mechanism that asks for it saw nothing.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    # The writer is told the exact name the reader will use, so the two cannot
    # disagree about it.
    assert 'skill_write(name="{solution}"' in Arm.LEARN_PROMPT
    assert 'skill_write(name="{solution}"' in Arm.SOLUTION_SKILL_FROM_PASS_PROMPT
    learn = " ".join(Arm.LEARN_PROMPT.split())
    # The prompt points at the rule; the rule itself lives in the skill, where
    # the pointer-length guard keeps it.
    assert "Memory is THIS session; a skill is what survives it" in learn

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # Checked rather than trusted, and only on a pass — a failed attempt has no
    # solution to file and demanding one would invent it.
    assert 'if (verdict or {}).get("resolved") and not self.best_skill_for(' in source
    # The fallback writer runs restricted: the task is already solved, so there
    # is nothing left to do but file what solved it.
    assert "agent=self.filer_agent_name)" in source[source.index("_write_solution_skill"):]

    # And the filer can write a skill without gaining any way to change code.
    tools = set(Arm._agent_spec(Arm.filer_agent_name).get("tools") or [])
    assert "mcp__phronix__skill_write" in tools
    assert not tools & {"Bash", "Edit", "Write", "Agent", "Task"}


def test_a_partial_pass_is_reported_as_partial_success_not_as_failure():
    """1 of 2 says one half is CORRECT. Only the other half was being carried.

    Measured on django-13551: the attempt had correctly added the user's email
    to the token hash and that target test passed. The feedback opened "your
    previous attempt did NOT succeed ... do not repeat the same approach" and
    named only the test still failing — advice that, followed literally, points
    the next attempt away from the one part the tests had confirmed.
    """
    from tests.benchmark.runner import _feedback_note

    partial = _feedback_note(2, {
        "fail_to_pass_passing": ["Updating the user email invalidates the token."],
        "fail_to_pass_failing": ["test_token_with_different_secret"],
        "failure_detail": "ERROR: x\nTypeError: boom"})
    assert "got PART of this task right" in partial
    assert "do not repeat the same approach" not in partial
    assert "ALREADY fixed — keep it" in partial
    # The banked half comes BEFORE the missing half: it is the constraint on
    # everything the next attempt does.
    assert partial.index("ALREADY fixed") < partial.index("still do not")

    # A change that achieved nothing keeps the blunt instruction, because there
    # it is correct.
    nothing = _feedback_note(2, {
        "fail_to_pass_passing": [],
        "fail_to_pass_failing": ["test_a", "test_b"],
        "failure_detail": "ERROR: x"})
    assert "do not repeat the same approach" in nothing
    assert "ALREADY fixed" not in nothing


def test_the_learner_is_told_which_store_a_finding_belongs_in():
    """Lifetime decides the store, not importance.

    Measured on django-13551: the attempt passed 2 of 2 and the fix — with the
    corner case that had broken three earlier runs — was written as a memory.
    It was correct, well written, and died with the run, because the
    pre-attempt lookup reads skills.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixArm as Arm

    assert "`I9`" in Arm.LEARN_PROMPT

    skill = (Path("src/phronix/.phronix/skills/phronix-learn-from-attempt")
             / "SKILL.md").read_text(encoding="utf-8")
    rule = skill[skill.index("### I9"):]
    # The discriminator is a question about the NEXT run, not about value.
    assert "would a run that never saw this session want it?" in rule
    # Both directions are named, or the rule only ever moves things one way.
    assert "the exchange, the transcript, the diff of this attempt | memory" in rule
    assert "the change that made the target tests pass | **skill**" in rule
    # And why getting it backwards is not symmetric.
    assert "A durable finding written as a memory is gone" in " ".join(rule.split())


def test_judging_has_one_budget_across_every_path_that_asks_for_it():
    """The corrector is unbudgeted per call, so the PASS has to bound it.

    Measured on django-13551 with `MAX_JUDGEMENTS` already in place:
    `validate-ideas` ran 300 times on one task and its finalize 303, for 64
    minutes in the plan phase and no steps recorded. Almost none of it was a
    stage running out of time — fifteen budget events in the whole hour. It was
    the NUMBER of calls, and the loop that counted them was not the loop making
    most of them: the scouts call the validator too, pipelined, so each scout's
    ideas are judged as they land.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    # Exactly one place runs the corrector, and it counts.
    assert source.count('stage("validate-ideas", self.VALIDATE_IDEAS_PROMPT') == 1
    assert "def judge():" in source
    assert "if judgements[0] >= self.MAX_JUDGEMENTS:" in source
    # Both callers go through it — the plan loop and the scouts.
    assert source.count("judge()") >= 3

    # And a corrector's overrun does not earn a rescue: it judges a list
    # someone else wrote, so a truncated verdict is the next round's job, not
    # findings that need filing.
    assert 'corrector = name.startswith(("validate-ideas"' in source
    assert "not finalizing and not corrector:" in source


def test_the_ways_fan_out_runs_on_whatever_produced_the_steps():
    """Evaluation is unreachable if the ways scouts are gated on the first read.

    `method` was read once, straight after the plan stage, and the ways fan-out
    was gated on that reading. A pass whose planner recorded nothing — which is
    every pass measured so far — skipped the ways scouts, recorded no approach,
    built no candidate, and therefore never evaluated anything. The fallback
    scouts did their job and the work they produced had nowhere to go.

    Measured on django-13551: 64 minutes in the plan phase, 300 validator
    calls, zero trials.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    fallback = source.index("if not method:")
    fan_out = source.index("if method:\n            if on_call:")
    # The fallback runs FIRST, so the fan-out has something either way.
    assert fallback < fan_out
    # And the method is re-read after it, or the fan-out is gated on a reading
    # taken before the work that produced the steps.
    between = source[fallback:fan_out]
    assert "method = self._in_store(store_root, self._load_aspects, topic)" in between


def test_a_run_cannot_write_into_the_frameworks_own_layer(tmp_path, monkeypatch,
                                                          real_bundled_layer):
    """`--fresh` means nothing if a run can edit the skeleton later runs seed from.

    Redirecting the project and user layers is not enough. phronix is installed
    editable from a clone in development, which leaves the BUNDLED layer
    writable inside a git worktree — so anything resolving a write to it edits
    the repository. Measured: a `--fresh --no-carry` run working on a django
    task wrote `sympy-itermonomials-degree-filter` into
    `src/phronix/.phronix/skills/`, and the six near-duplicate `column-domain`
    skills that reached later runs arrived in the bundle the same way. Every
    from-scratch comparison after that measured a skeleton earlier runs had
    edited.
    """
    from phronix.layers import bundled_layer, resolve_write_layer
    from tests.benchmark.isolation import isolated_env

    # The benchmark closes the boundary for every process it launches — agents,
    # sub-agents and the always-on learner resolve layers for themselves, so
    # this cannot be done at one call site.
    env = isolated_env(tmp_path / "store", tmp_path / "cache")
    assert env["PHRONIX_BUNDLED_READONLY"] == "1"

    project = tmp_path / "proj"
    (project / ".git").mkdir(parents=True)
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(project))
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PHRONIX_BUNDLED_READONLY", "1")

    assert bundled_layer().writable is False
    # Writes fall through to the run's own store, not into the framework.
    assert resolve_write_layer().root == project / ".phronix"
    # And asking for it by name is refused rather than silently redirected —
    # a silent downgrade is how this stayed invisible.
    with pytest.raises(PermissionError):
        resolve_write_layer("bundled")

    # Without the guard the framework's layer is writable from a checkout,
    # which is the condition that made the leak possible.
    monkeypatch.delenv("PHRONIX_BUNDLED_READONLY")
    assert bundled_layer().writable is True


def test_the_planner_is_given_the_evidence_and_not_the_repository():
    """Remove what produces the wrong conclusion, rather than arguing with it.

    A revision pass runs against a checkout holding the failed attempt's edits,
    and the planner reads them as proof there is nothing to plan. Measured
    across five runs and five successive gates — a prompt instruction, a
    restricted agent, a dedicated filer with no editing tools, an explicit
    re-ask, and a standing note saying the tree is patched — it still answered
    "the implementation is correct" and recorded no ideas: 67 plan rounds on
    one task, 68 re-asks, zero ideas.

    Every one of those gates argued with the conclusion. None removed what
    produces it. The planner does not need the source to name the ideas worth
    exploring; it needs the failure, the verdict and the test still red.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    # A directory holding the evidence files and nothing else.
    assert 'evidence = workdir / "evidence"' in source
    assert "shutil.copy2(source, evidence / Path(source).name)" in source
    # The plan stage and its scouts run there, not in the checkout.
    assert 'recording_stage("plan", still_failing + self.PLAN_PROMPT,\n' \
           '                        budgets["plan"], evidence)' in source
    assert 'budgets["plan"], evidence)' in source


def test_the_refined_unit_is_an_idea_not_a_step_of_one():
    """An idea solves the whole problem; the steps live inside it.

    The per-STEP fan-out asked several agents for rival ways of doing one step
    of one method — a finer grain than anything downstream could use, since the
    thing built, tried and combined is an idea.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    assert not hasattr(Arm, "WAYS_SCOUT_PROMPT")
    flat = " ".join(Arm.REFINE_IDEA_PROMPT.split())
    assert "You own one idea" in flat
    assert "SEQUENCE OF STEPS your idea takes" in flat
    # The result is attributable to the idea that produced it.
    assert 'aspect="{step}"' in Arm.REFINE_IDEA_PROMPT
    # And it still knows the tree is patched.
    assert "working tree is NOT the original code" in Arm.REFINE_IDEA_PROMPT


def test_the_tracked_pipeline_is_a_loop_over_one_task_record():
    """Two skills, no prompts carrying the method, and a record per task.

    The pipeline: check for a skill, attempt, evaluate, fold the result into
    this task's record, then either write the solution (it passed) or hand the
    open failure to research (it did not), which updates the skill the next
    attempt loads. Sequential, until progress stops.
    """
    from pathlib import Path as _P

    from tests.benchmark.arms import ClaudePhronixArm as Arm
    from tests.benchmark.runner import RunConfig

    # Sequential is the default; the parallel pipeline stays reachable.
    assert RunConfig(tasks=[], arms=[]).pipeline == "sequential"

    skills = _P("src/phronix/.phronix/skills")
    for name in ("phronix-task-tracker", "phronix-task-research"):
        assert (skills / name / "SKILL.md").is_file(), name

    # The prompts are POINTERS at those skills, not the method itself.
    for prompt, skill in ((Arm.TRACK_PROMPT, "phronix-task-tracker"),
                          (Arm.TASK_RESEARCH_PROMPT, "phronix-task-research")):
        assert skill in prompt
        assert len(prompt) < 900, len(prompt)

    # The tracker is its own stage, run by an agent that can WRITE the record
    # and do nothing else. The filer was tried first and could not: it has
    # `skill_write` and no `Write`, so the stage ran, said "folding into
    # tracker.md", and produced no file.
    source = _P("tests/benchmark/arms.py").read_text(encoding="utf-8")
    track = source[source.index("    def track(self"):]
    # The stage is run by the always-on tracker, not by `track` — which now
    # pushes an event and returns. `_fold_events` is what invokes the agent.
    assert "self.note_event(" in track[:2500]
    fold = source[source.index("    def _fold_events("):]
    fold = fold[:fold.index("\n    def ", 10)]
    assert "agent=self.tracker_agent_name" in fold
    # And in the TASK directory, not the checkout — the source is not evidence
    # of what happened, and it is what convinced five earlier stages the task
    # was already done.
    # In `_fold_events` now, with the rest of the invocation: the agent is
    # run from the TASK directory, not the checkout, so the source is not
    # in front of it at all.
    assert "cwd=state.tracker.parent" in fold

    tools = set(Arm._agent_spec(Arm.tracker_agent_name).get("tools") or [])
    arm = Arm.__new__(Arm)
    denied = set(" ".join(
        arm._denial_flags(Arm.tracker_agent_name)).split()[-1].split(","))
    assert "Write" in tools                       # it can write the record
    assert {"Bash", "Edit", "Agent", "Task"} <= denied   # and nothing else

    # It runs after the attempt AND after the evaluation: a verdict says a test
    # failed, the attempt's own diff says what was tried.
    runner_source = _P("tests/benchmark/runner.py").read_text(encoding="utf-8")
    # Every stage goes into the record — attempt, evaluate, research — or the
    # next pass cannot see that a diagnosis has already been made and rejected.
    assert runner_source.count("arm.track(") == 3
    assert 'phase="research"' in runner_source
    assert 'phase="attempt"' in runner_source
    assert 'phase="evaluate"' in runner_source

    # Per task, and spanning attempts — an attempt-local record could not carry
    # what the last attempt found to the next one.
    assert 'tracker = Path(workdir).parent / self.TRACKER_FILE' in source

    # Research is bounded and the bound grows with each try.
    assert Arm.RESEARCH_BUDGET_S == 300
    assert Arm.RESEARCH_BUDGET_MULTIPLE > 1.0
    assert "self.RESEARCH_BUDGET_MULTIPLE ** max(0, attempt_index - 2)" in source

    # And the record becomes a skill when the task ends, whichever way it went.
    snapshot = source[source.index("    def snapshot_tracker(self"):]
    assert "resolved" in snapshot[:1200]
    # The final skill has a fixed shape, built from the fix AND the record:
    # what it solves, the key idea, the instructions, the constraints, and the
    # pitfalls — that last one is the part only this task can write.
    snap = " ".join(Arm.SNAPSHOT_PROMPT.split())
    for section in ("What problem it solves", "The key idea",
                    "Instructions to solve it", "Constraints and rules",
                    "Pitfalls and lessons"):
        assert section in snap, section
    assert "Write it whether the task passed or not" in snap


def test_research_retrieves_the_conversation_instead_of_attaching_it():
    """Research must not repeat work the task has already done.

    The record is compacted by design — problem, approaches, what worked, what
    did not — and compaction loses detail a diagnosis sometimes needs. The
    conversation holds that detail, but attaching it whole is what runs the
    context window out: it is append-only, so it is largest exactly when the
    window is tightest. So the record and a summary are attached, and the
    conversation is RETRIEVED a turn at a time through the MCP tools.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    prompt = " ".join(Arm.TASK_RESEARCH_PROMPT.split())
    # The REASON not to repeat prior work now lives in the skill (`I7`), and
    # the retrieval method in `I8`. The prompt points at both. Prose in the
    # prompt describing what an attached file says is what the limit catches.
    assert "{tracker}" in prompt and "I7" in prompt and "I8" in prompt

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    research = source[source.index("    def research_from_tracker(self"):]
    # The whole method, not a byte window of its start: comments explaining
    # WHY an attachment is there are not a behaviour change.
    whole = research[:research.index("\n    def ", 10)]
    # The unbounded file is not attached. Retrieval replaces it.
    assert 'Path(workdir).parent / "conversation.md"' not in whole

    # And the method it is retrieved by is written down where a method
    # belongs: in the skill, not restated in the prompt.
    skill = Path(
        "src/phronix/.phronix/skills/phronix-task-research/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "### I8" in skill
    for tool in ("conversation_outline", "conversation_search", "conversation_turn"):
        assert tool in skill


def test_the_record_is_organised_as_problem_approach_worked_and_not():
    """Every stage leaves the record in a shape the next stage can act on.

    Not a log of what happened: the PROBLEM as it now stands, how it has been
    approached, what worked, what did not. By the second attempt the problem is
    no longer the issue text — a phase that starts from the issue when half of
    it is solved re-solves the half that is done.
    """
    skill = (Path("src/phronix/.phronix/skills/phronix-task-tracker")
             / "SKILL.md").read_text(encoding="utf-8")

    for heading in ("## The problem", "## How it has been approached",
                    "## What worked", "## What did not work"):
        assert heading in skill, heading
    # Order matters: the next phase reads from the top and may not finish.
    assert (skill.index("## The problem")
            < skill.index("## How it has been approached")
            < skill.index("## What worked")
            < skill.index("## What did not work"))
    # "What did not work" carries the reason, or it reads as "not tried hard
    # enough" and gets tried again.
    assert "it needs\nthe *why*" in skill


def test_a_standalone_stage_that_cannot_start_says_so():
    """A stage that never ran must not look like one that ran and found nothing.

    `standalone_stage` runs the tracker, the tracked research pass and the
    end-of-task snapshot. It swallowed every exception and returned "", so a
    `NameError` on its first line was reported as a completed stage: measured
    live, `research> diagnosing the open failure, 300s` and the tracker call
    after it both landed in the same second, three times, and no record was
    ever written.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def standalone_stage(self"):
                  source.index("    def research_from_tracker(self")]

    # The runner streams (see stream_opencode, which closes stdin itself) —
    # the two faults this test was written for were a missing `subprocess`
    # import and an inherited stdin, and moving to the shared runner removes
    # both by construction.
    assert "stream_opencode(" in body
    # And both failure modes are reported, not swallowed.
    assert "could not run:" in body
    assert "exited rc=" in body


def test_the_tracked_stages_report_what_they_are_doing():
    """A five-minute stage that prints nothing is indistinguishable from a dead one.

    `standalone_stage` used `subprocess.run`, which returns nothing until the
    process exits. Measured live: the trace showed `diagnosing the open
    failure, 300s` and then silence — the stage was working and there was no
    way to see it, or to see it stop.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def standalone_stage(self"):
                  source.index("    def research_from_tracker(self")]

    # The same streaming runner every research stage already uses.
    assert "stream_opencode(" in body
    assert "subprocess.run(" not in body

    # And every caller passes its narrator through, or the stream has nowhere
    # to go.
    for caller in ("def track(self", "def research_from_tracker(self",
                   "def snapshot_tracker(self"):
        chunk = source[source.index(caller):]
        head = chunk[:chunk.index("\n    def ", 10)]
        assert "on_call=on_call" in head, caller


def test_research_reports_its_problem_approach_and_answer():
    """A pass has to be auditable from its trace, not from a transcript.

    `research> diagnosing the open failure, 300s` and then silence says nothing
    about whether the pass had one subject or three, what it checked, or why it
    concluded what it did. Three lines make a wrong answer traceable to the step
    that produced it — and make a loop going in circles visible as the same
    APPROACH twice in different words.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    prompt = Arm.TASK_RESEARCH_PROMPT
    for key in ("PROBLEM:", "APPROACH:", "ANSWER:"):
        assert key in prompt, key
    assert "{report}" in prompt
    # The prompt stays short, and the CONTEXT comes from attachments.
    #
    # Not a token diet: the pass is handed the record, the conversation, the
    # skill and its lessons as FILES, and the method lives in
    # `phronix-task-research`. Prose in the prompt describing what those files
    # say is the one thing this limit is here to catch — it duplicates the
    # attachment, ages separately from it, and is the first thing to drift.
    #
    # This was 900, on the rule that the prompt carries the harness's parsing
    # contract while the REASONING lives in the skill the pass loads. That
    # rule still holds for the method: `phronix-task-research` is where "how
    # to diagnose" belongs, and `I7` is where the lessons discipline is
    # written.
    #
    # But the owner's preference is explicit: give the pass as much of its
    # input as possible, in front of it, rather than relying on it to load a
    # skill to find out what it was handed. What lives here now is the INPUTS
    # and what to do with them — the record, the conversation, the skill and
    # its lessons, and the two writes owed back. The limit exists to catch the
    # method being pasted in wholesale, which is a different failure.
    assert len(prompt) < 900, len(prompt)
    skill = (Path("src/phronix/.phronix/skills/phronix-task-research")
             / "SKILL.md").read_text(encoding="utf-8")
    assert "### I6" in skill
    assert "cannot be audited" in skill
    assert "ANSWER: could not confirm" in skill

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    research = source[source.index("    def research_from_tracker(self"):]
    # Echoed once at the end, so the pass reads off the trace even when its
    # narration has scrolled past.
    # PROBLEM and ANSWER once; every APPROACH in sequence, numbered — the
    # sequence is the audit, and keeping only the first threw away exactly what
    # shows a pass going in circles.
    # The whole method: byte windows break whenever a comment is added, which
    # is not a behaviour change.
    research = research[:research.index("\n    def ", 10)]
    assert 'APPROACH {n}/{len(steps)}' in research
    assert '[research] PROBLEM:' in research
    # And a pass that reported none of them says so, rather than looking like
    # one that simply had nothing to report.
    assert "reported no PROBLEM/APPROACH/ANSWER" in research


def test_one_task_one_skill_named_after_the_task():
    """A fix filed under a name nothing reads is a fix that was never made.

    There is no second kind of skill for a task to distinguish itself from, so
    a `solution-` prefix only created ways for the writer and the reader to
    disagree — and they did. Research wrote `solution-<topic>-solution` while
    `best_skill_for` looked up `solution-<topic>`. Measured live: try 2 loaded
    the skill the LEARN pass had left after try 1, re-applied the same change,
    and the harness reported "try 2 re-applies the change from try 1 — the
    diagnosis did not move". The diagnosis had moved. It was filed where no
    reader would look.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    assert Arm.task_skill_name("django__django-13551") == "django-django-13551"

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    marker = "\n    def "
    for who in ("    def research_from_tracker(self",
                "    def snapshot_tracker(self"):
        chunk = source[source.index(who):]
        assert "self.task_skill_name(topic)" in chunk[:chunk.index(marker, 10)], who

    # The reader checks the task's own skill FIRST.
    reader = source[source.index("    def best_skill_for(self, store_root"):]
    assert reader.index("if on_disk(here):") < reader.index('merged = f"solution-{here}"')

    # Research reads code but writes only the skill: it proposes a fix for the
    # next attempt to execute, it does not become the next attempt.
    chunk = source[source.index("    def research_from_tracker(self"):]
    assert "agent=self.filer_agent_name" in chunk[:chunk.index(marker, 10)]
    tools = set(Arm._agent_spec(Arm.filer_agent_name).get("tools") or [])
    arm = Arm.__new__(Arm)
    denied = set(" ".join(
        arm._denial_flags(Arm.filer_agent_name)).split()[-1].split(","))
    assert "mcp__phronix__skill_write" in tools and "Read" in tools
    assert {"Bash", "Edit", "Write"} <= denied


def test_the_record_travels_with_the_task_between_stages():
    """Each stage starts from what the last one established, not from scratch.

    The record is written after every phase; passing it forward is what makes
    that worth doing. A retry that has to rediscover its own last attempt
    spends its opening turns on work an hour old.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    # The retry attempt is handed it, with a note saying how to read it.
    assert "tracker = workdir.parent / self.TRACKER_FILE" in source
    note = " ".join(Arm.TRACKER_NOTE.split())
    assert "What is under **What worked** is banked" in note
    assert "repeating it costs an attempt and changes nothing" in note

    # Research gets it too, alongside the unabridged conversation.
    research = source[source.index("    def research_from_tracker(self"):]
    whole = research[:research.index("\n    def ", 10)]
    assert "tracker," in whole

    # And it stays phronix's OWN product: the raw harness judgement remains the
    # baseline's channel, or the arm scores on a prompt injection rather than
    # on its memory.
    retry = source[source.index("        feedback = workdir / \"feedback.md\""):]
    bare = retry[retry.index("            else:"):retry.index("        if plan:")]
    assert "self.attachments([feedback])" in bare


def test_the_audit_lines_are_reports_not_the_instruction_echoed_back():
    """A restatement of what it was asked to do is not a report of what it did.

    `if marker in line` matched the agent quoting the format spec. Measured
    live, the trace showed ``APPROACH: `, `ANSWER:`\\n6. I have 300`` — the
    instruction itself, parsed and displayed as a finding.
    """
    import textwrap

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    start = source.index("        found: Dict[str, str] = {}")
    block = textwrap.dedent(source[start:source.index("        if on_call:", start)])

    # The parser reads the agent's WORDS, so feed it the same stream shape the
    # harness does.
    from tests.benchmark.arms import ClaudePhronixArm as _Arm

    said = ("Let me follow the format: `PROBLEM:`, `APPROACH:`, `ANSWER:`\n"
            "PROBLEM: test_token_with_different_secret fails on a None email\n"
            "- APPROACH: check whether get_email_field_name exists on the base user\n"
            "ANSWER: use getattr(user, user.get_email_field_name(), '')")
    stream = json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": said}]}})
    scope = {"Dict": dict, "stdout": stream, "self": _Arm}
    exec(block, scope)                                  # noqa: S102 - the code under test
    found = scope["found"]

    assert found["PROBLEM"].startswith("test_token_with_different_secret")
    # A leading bullet is still a report.
    assert found["APPROACH"].startswith("check whether")
    assert found["ANSWER"].startswith("use getattr")
    # And the echoed spec contributed nothing.
    for value in found.values():
        assert "`" not in value and "ANSWER:" not in value


def test_only_the_agents_own_words_are_parsed_for_the_audit_lines():
    """The stream is JSON; only `text` blocks are what the agent said.

    Reading raw stdout put envelope fragments into the trace and into the
    record. Measured live:

        PROBLEM: `, `ANSWER:`\\n6. I have 300 seconds to
        complete this","signature":"EosHCrIBCBEYAipA...

    — a base64 signature displayed as a finding, and written into `tracker.md`
    as the diagnosis the next attempt was handed.
    """
    import json as _json

    from tests.benchmark.arms import ClaudePhronixArm as Arm

    stream = "\n".join([
        _json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "PROBLEM: token fails for CustomEmailField"}]}}),
        _json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {}}]}}),
        '{"signature":"EosHCrIBCBEYAipAlWquqv8h6J9pQ","type":"thinking"}',
        "not json at all",
        _json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "ANSWER: use get_email_field_name()"}]}}),
    ])

    said = Arm.assistant_text(stream)
    assert said == ("PROBLEM: token fails for CustomEmailField\n"
                    "ANSWER: use get_email_field_name()")
    assert "signature" not in said and "tool_use" not in said

    # And the audit parser reads that, not the raw stream.
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert "for raw in self.assistant_text(stdout).splitlines():" in source


def test_every_tracked_stage_is_given_what_it_is_asked_to_record():
    """A tracker with no evidence is recording a stage it cannot see.

    `track:research` was called with none: the report research wrote and the
    skill it updated are the whole output of that pass, and both were withheld
    from the one agent whose job is writing down what happened.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")

    # The attempt: what it changed, and what it was asked.
    assert 'attempt_dir / "attempt-diff.patch"' in source
    # The evaluation: what the tests PRINTED and every target test by outcome.
    # The digest alone says a test failed; these say which, and why.
    assert 'attempt_dir / "exchange.md"' in source
    assert 'attempt_dir / "evaluation.json"' in source
    # Research: its report and the skill it wrote.
    research_call = source[source.index('phase="research"') - 900:
                           source.index('phase="research"') + 400]
    assert '(research or {}).get("report", "")' in research_call
    assert "solution_skill_path(" in research_call


def test_the_record_reorganises_and_never_discards():
    """The task's memory grows; what must not grow is disorder.

    Compaction was the wrong instruction: a detail recorded three phases ago is
    one the next phase does not have to rediscover, and nothing can know in
    advance which detail that will be. An error message, a line number, a flag
    that did not work — cheap to keep, expensive to re-derive.
    """
    skill = (Path("src/phronix/.phronix/skills/phronix-task-tracker")
             / "SKILL.md").read_text(encoding="utf-8")

    assert "### I2 — Reorganise every time. Never discard." in skill
    assert "**Nothing is dropped.**" in skill
    # Merging keeps both facts, rather than choosing between them.
    assert "become ONE entry holding both facts" in skill
    # A contradicted belief MOVES between sections, carrying its evidence.
    assert "moves from **What worked** to **What did not work**" in skill
    # And the rule that a long record is not a reason to delete.
    assert "not to delete" in skill

    # The prompt and the agent ask for the same thing.
    from tests.benchmark.arms import ClaudePhronixArm as Arm
    assert "reorganised" in Arm.TRACK_PROMPT
    agent = (Path("src/phronix/.phronix/agents/phronix-tracker.yaml")
             ).read_text(encoding="utf-8")
    assert "never shortened" in agent


def test_the_record_shape_is_checked_not_merely_requested():
    """A rule stated in a skill and checked nowhere is followed when convenient.

    Measured on the first live record: it wrote `## Problem Statement`,
    `## Attempts`, `### Attempt 1`, `## Key Notes` — good content, organised by
    WHEN things happened rather than by what they mean, which is the transcript
    shape the record exists to replace. A per-attempt heading is the tell: the
    next one gets `### Attempt 2`, and a reader asking "what has been ruled
    out?" has to read every section and work it out.
    """
    import tempfile

    from tests.benchmark.arms import ClaudePhronixArm as Arm

    scratch = Path(tempfile.mkdtemp())
    wrong = scratch / "wrong.md"
    wrong.write_text("# t\n## Problem Statement\n## Attempts\n### Attempt 1\n")
    assert Arm.missing_sections(wrong) == list(Arm.TRACKER_SECTIONS)

    right = scratch / "right.md"
    right.write_text("\n".join(Arm.TRACKER_SECTIONS))
    assert Arm.missing_sections(right) == []

    # A record that does not exist is missing all of them, not an error.
    assert Arm.missing_sections(scratch / "absent.md") == list(Arm.TRACKER_SECTIONS)

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    track = source[source.index("    def track(self"):]
    # Sent back once, naming what is missing...
    assert "missing = self.missing_sections(tracker)" in track[:4000]
    assert "self.RESHAPE_PROMPT.format(" in track[:4000]
    # ...and a second failure is reported, not looped on: the content is there
    # either way, and a record in the wrong shape beats no record.
    assert "still = self.missing_sections(tracker)" in track[:4000]

    reshape = " ".join(Arm.RESHAPE_PROMPT.split())
    assert "this is a reorganisation, not a rewrite from evidence" in reshape
    assert "`### Attempt 1` is the shape to remove" in reshape


def test_the_task_skill_is_filed_under_the_name_the_lookup_asks_for():
    """Told the exact name and given the tool, agents still invent their own.

    Measured in one run: `django-django-13551` and `matplotlib-matplotlib-24970`
    were written correctly, and beside them sat
    `django-password-reset-token-email-invalidation` and
    `matplotlib-24970-numpy-deprecation` — good content under names the lookup
    will never ask for. matplotlib-24970 then opened its next attempt with "no
    skill covers this task; solving from scratch" while its own diagnosis sat
    in the store.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    rename = " ".join(Arm.RENAME_PROMPT.split())
    # It says why a descriptive name fails, not just that it is wrong.
    assert "A later run does not search for a skill" in rename
    # And asks for a merge rather than a re-derivation.
    assert "one task, one skill" in rename

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    check = source[source.index("    def ensure_task_skill(self"):]
    # It only acts when the lookup would MISS, and finds what to merge.
    assert "if self.best_skill_for(store_root, topic) == wanted:" in check[:3000]
    assert "if not found:" in check[:3000]
    # A second failure is reported, because the consequence is silent: the next
    # run starts from scratch with the answer sitting in the store.
    # In the method, not within some byte window of its start: a comment
    # added above it is not a behaviour change.
    body = check[:check.index("\n    def ", 10)]
    assert "will start from scratch" in body

    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    # Checked after research — before the next attempt looks it up — and again
    # when the task ends.
    assert runner.count("arm.ensure_task_skill(") == 2


def test_a_run_always_saves_into_the_source_tree_and_fresh_still_reads_clean(tmp_path):
    """Saving and reading are different questions.

    Everything a run learned went to `/.phronix`, which is gitignored — so it
    lived exactly as long as the checkout it was learned in, and a clone
    started from nothing. `promote_root` fixes that: every run writes what it
    learned there whatever its mode, and it sits outside the checkout.

    Promotion into the PACKAGED layer was the first answer to the same
    problem, and it is now opt-in. It never stopped being correct about
    `--fresh` — a task answer lands under `tasks/` and the read filter hides
    it — but it edits the framework the benchmark is measuring. Measured: one
    5-task run added five answers to `src/phronix/.phronix` mid-run, left the
    tree dirty, and failed the corrector that walks every bundled artifact on
    a promoted 29-character description. A bulk promotion into the same place
    broke seven tests and took the suite from 27s to 356s.
    """
    import os

    from phronix.capabilities import TASK_CAPABILITY_DIR, visible_files
    from tests.benchmark.isolation import SOURCE_DIRS, promote_to_source

    # Answers and the research behind them — research is the expensive half.
    assert SOURCE_DIRS == ("capabilities", "research")

    source = Path("tests/benchmark/isolation.py").read_text(encoding="utf-8")
    body = source[source.index("def promote_to_source("):]
    # It never edits what the framework ships; a run ADDS to the source tree.
    assert "Never overwrite what the framework ships" in body

    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    # The unconditional save is the carry root, and it is NOT behind the read
    # flags: `--fresh` and `--no-carry` both empty `carry_root`.
    assert "promote_into = self.config.promote_root or self.config.carry_root" in runner
    assert "promote_store(store_root, Path(promote_into))" in runner
    # The packaged copy is the opt-in one, and defaults to off. Asserted by
    # ORDER rather than by a byte window: a window around the call breaks
    # whenever the comment above it is edited, which is not a behaviour change.
    guard = runner.index('os.environ.get("PHRONIX_PROMOTE_TO_PACKAGE"')
    assert guard < runner.index("into_src = promote_to_source(")
    # A fragment that survives line-wrapping: the full sentence is split
    # across two comment lines, so matching it whole tests the formatter.
    assert "a benchmark run should not edit the" in runner

    # And the read side: a bundled TASK ANSWER is hidden from a fresh run,
    # while the framework's own tools stay — which is what `--fresh` means.
    caps = Path("src/phronix/capabilities.py").read_text(encoding="utf-8")
    assert "def is_task_answer(path: Path) -> bool:" in caps
    assert "any(d in parts for d in LEARNED_DIRS)" in caps
    assert "and not is_task_answer(path)" in caps


def test_every_task_leaves_exactly_one_skill_however_it_ended():
    """Pass on try 1, pass on try 3, or never pass — all owe a skill.

    An absent skill is indistinguishable from a subject nobody has tried, so a
    later run pays full price for work already done. And a task that leaves
    FIVE splits every later retrieval: measured in one run, four tasks produced
    fifteen skills, django alone contributing `django-django-13551` plus four
    descriptively-named copies of the same answer.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")

    # The copies are removed once the merge has landed — and only then.
    check = source[source.index("    def ensure_task_skill(self"):]
    body = check[:check.index("\n    def ", 10)]
    assert body.index("if not landed:") < body.index("shutil.rmtree(stray)")
    assert "Two skills for one subject split every read" in body

    # A missing record is not a reason to leave nothing behind.
    snap = source[source.index("    def snapshot_tracker(self"):]
    assert "from the attempt evidence instead" in snap[:2000]

    # And the snapshot runs whatever the outcome was.
    assert "Write it whether the task passed or not" in " ".join(
        Arm.SNAPSHOT_PROMPT.split())
    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    # The reasoning sits with the call, in the same block — not within some
    # byte window of it. This was `- 600` and broke the moment another comment
    # was added between the two, which says nothing about the behaviour.
    at = runner.index("arm.snapshot_tracker(")
    why = runner.index("# Written whether the task passed or not.")
    assert why < at, "the reasoning must sit with the call it explains"
    block = runner[why:at]
    # Same function: nothing declares a new one between the two.
    assert "\n    def " not in block
    assert "A task that failed after four" in block

    # And nothing in that block narrates through a name it does not own —
    # `_say` belongs to `run_attempt`, and using it here raised `NameError`
    # on every task, swallowed as "could not snapshot the record".
    assert "_say(" not in block


def test_a_second_pass_on_a_subject_reconciles_rather_than_replaces(tmp_path):
    """What a run knows about a subject only grows.

    The canonical name means every pass at one task lands on one path, so a
    plain copy makes each pass ERASE the one before it. That is backwards: a
    run that failed after four attempts holds four ruled-out approaches, and
    they stay true after a later run passes. The expensive half of a run is
    exactly the half a copy throws away.
    """
    from tests.benchmark.isolation import merge_skill_text, promote_to_source

    def skill(*blocks: str) -> str:
        # A REAL skill: promotion refuses one whose index does not match its
        # content, so the fixture has to satisfy that too.
        head = ["---", "name: sub", "description: d", "subject: sub",
                "type: skill", "---", "", "## Index", "",
                "| Label | Section | Covers |", "| --- | --- | --- |"]
        head += [f"| `I{n}` | Instructions | {t} |"
                 for n, t in enumerate(blocks, 1)]
        body = ["", "## Instructions", ""]
        for number, title in enumerate(blocks, 1):
            body += [f"### I{number} — {title}", "", f"body of {title}", ""]
        return "\n".join(head + body)

    first = skill("Pad the degree tuple to the variable count")
    second = skill("Never sort monomials before padding")
    merged = merge_skill_text(first, second)
    # BOTH, because neither makes the other's point.
    assert "Pad the degree tuple" in merged
    assert "Never sort monomials" in merged
    # Rebuilt labels and index over the union.
    assert "| `I1` |" in merged and "| `I2` |" in merged
    assert "### I2 — " in merged

    # Two wordings of ONE point collapse, and the newer wins.
    same = merge_skill_text(skill("Pad the degree tuple to the variable count"),
                            skill("Pad the degree tuple to variable count"))
    assert same.count("### I") == 1

    # End to end: promoting twice accumulates instead of overwriting.
    store = tmp_path / "store"
    home = store / "capabilities" / "skills" / "sub"
    home.mkdir(parents=True)
    target = tmp_path / "dest" / "capabilities" / "skills" / "sub"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(first)
    (home / "SKILL.md").write_text(second)
    import phronix.layers as layers
    original, layers.bundled_root = layers.bundled_root, lambda: tmp_path / "dest"
    try:
        promote_to_source(store)
    finally:
        layers.bundled_root = original
    landed = (target / "SKILL.md").read_text()
    assert "Pad the degree tuple" in landed and "Never sort monomials" in landed


def test_research_carried_into_the_source_tree_is_merged_not_copied(tmp_path):
    """Same rule, one level out: a ruled-out approach stays ruled out."""
    import json

    from tests.benchmark.isolation import promote_to_source

    store = tmp_path / "store"
    (store / "research").mkdir(parents=True)
    dest = tmp_path / "dest"
    (dest / "research").mkdir(parents=True)
    (dest / "research" / "sub.json").write_text(json.dumps(
        {"slug": "sub", "topic": "sub", "approaches": [{"name": "old", "id": 1}]}))
    (store / "research" / "sub.json").write_text(json.dumps(
        {"slug": "sub", "topic": "sub", "approaches": [{"name": "new", "id": 2}]}))
    # Per-run working state is NOT promoted; it is folded in as a task ends.
    (store / "research" / "sessions" / "run-1").mkdir(parents=True)
    (store / "research" / "sessions" / "run-1" / "sub.json").write_text("{}")

    import phronix.layers as layers
    original, layers.bundled_root = layers.bundled_root, lambda: dest
    try:
        promote_to_source(store)
    finally:
        layers.bundled_root = original

    landed = json.loads((dest / "research" / "sub.json").read_text())
    names = {a.get("name") for a in landed.get("approaches", [])}
    assert names == {"old", "new"}, names
    assert not (dest / "research" / "sessions").exists()


def test_fresh_hides_a_promoted_answer_from_the_layer_it_was_promoted_into(tmp_path, monkeypatch):
    """`--fresh` means from scratch, and promotion is what put the answer there.

    The fresh filter exempted the BUNDLED layer, which is correct for the
    framework's method skills and backwards for `capabilities/tasks/`, where
    every entry is an answer to one task. It cost nothing while the bundled
    tree held no answers. Promotion puts them there by design, and the next
    fresh run opened a task with `attempt>recall> trying remembered skill
    scikit-learn-column-transformer-empty-columns` — a run reported as
    from-scratch, reading a previous run's answer.
    """
    import phronix.layers as layers_module
    from phronix.capabilities import TASK_CAPABILITY_DIR

    bundled = tmp_path / "bundled"
    answer = bundled / "capabilities" / TASK_CAPABILITY_DIR / "sub" / "prior-answer"
    answer.mkdir(parents=True)
    (answer / "SKILL.md").write_text(
        "---\nname: prior-answer\ntype: skill\n---\n\n## Instructions\n")

    monkeypatch.setattr(layers_module, "bundled_root", lambda: bundled)
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path / "project"))

    # Carried run: the answer is exactly what it is there to reuse.
    monkeypatch.delenv("PHRONIX_FRESH_CAPABILITIES", raising=False)
    assert "prior-answer" in layers_module.task_skill_dirs()

    # Fresh run that did not write it: invisible, bundled or not.
    monkeypatch.setenv("PHRONIX_FRESH_CAPABILITIES", "1")
    assert "prior-answer" not in layers_module.task_skill_dirs()


def test_a_fresh_run_still_sees_the_skill_it_wrote_itself(tmp_path, monkeypatch):
    """The other half of the fresh rule, and the one that breaks the pipeline.

    Hiding prior answers is only correct if a run's OWN answer stays visible:
    try 2 attempts with the skill research wrote after try 1, and a filter that
    could not tell "written here" from "found here" would take that away.
    """
    import phronix.layers as layers_module
    from phronix.capabilities import TASK_CAPABILITY_DIR

    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path / "project"))
    monkeypatch.setenv("PHRONIX_FRESH_CAPABILITIES", "1")
    # The USER layer too: without it `write_block` picks the real `~/.phronix`
    # and the test writes into the person running it.
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(layers_module, "bundled_root", lambda: tmp_path / "bundled")

    from phronix.skills import write_block

    result = write_block("sub-answer", "instruction", "Do the thing",
                         "The body of the instruction.")
    assert result["status"] == "ok", result

    # Written this session, so this session can read it back.
    assert "sub-answer" in layers_module.task_skill_dirs()
    del TASK_CAPABILITY_DIR


def test_recall_cannot_reach_what_fresh_hides_from_the_lookup(tmp_path, monkeypatch):
    """One filter, two readers — and only one of them was filtered.

    The harness asks `search-skill` before an attempt; the arm ALSO asks
    `recalled_skill`, which goes through `skills.search` instead. That path
    excluded the framework's own `skills/` and nothing else, so a promoted task
    ANSWER was invisible to the first reader and retrievable by the second:

        search-skill     no skill covers this task; solving from scratch
        attempt>recall>  trying remembered skill `scikit-learn-column-...`

    Both readers must agree about what a run is entitled to see.
    """
    import phronix.layers as layers_module

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def recalled_skill("):]
    body = body[:body.index("\n    def ", 10)]
    # It consults the filtered listing, not just the bundled-skills exclusion.
    assert "skill_dirs" in body, "recall does not apply the fresh filter"

    # And the filter it consults really does hide a bundled task answer.
    bundled = tmp_path / "bundled"
    answer = bundled / "capabilities" / "skills" / "prior-answer"
    answer.mkdir(parents=True)
    (answer / "SKILL.md").write_text(
        "---\nname: prior-answer\ntype: skill\n---\n\n## Instructions\n")
    monkeypatch.setattr(layers_module, "bundled_root", lambda: bundled)
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path / "project"))
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))

    monkeypatch.setenv("PHRONIX_FRESH_CAPABILITIES", "1")
    assert "prior-answer" not in set(layers_module.skill_dirs())
    monkeypatch.delenv("PHRONIX_FRESH_CAPABILITIES", raising=False)
    assert "prior-answer" in set(layers_module.skill_dirs())


def test_fresh_is_told_to_the_library_and_not_only_to_the_harness(tmp_path):
    """A filter nothing switches on is not a filter.

    `capabilities.session_only()` reads `PHRONIX_FRESH_CAPABILITIES`, and
    NOTHING in the harness ever set it — so the from-scratch visibility filter
    had never once been active in a real run, while passing its own unit tests
    the whole time. It was invisible for as long as the bundled tree held no
    task answers. Promotion put them there, and a `--fresh` run began reading
    the previous run's answer for the task it was about to attempt.
    """
    from phronix.capabilities import FRESH_ENV
    from tests.benchmark.isolation import isolated_env

    on = isolated_env(tmp_path / "store", tmp_path / "cache", fresh=True)
    assert on[FRESH_ENV] == "1"
    off = isolated_env(tmp_path / "store", tmp_path / "cache", fresh=False)
    assert FRESH_ENV not in off

    # And the runner actually passes the run's own setting through.
    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert "arm.fresh = bool(self.config.fresh)" in runner

    # Every agent-launching call site opts in, or the arm it launches is not
    # the run it was told to be.
    arms = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert arms.count("isolated_env(") == arms.count("fresh=self.fresh"), (
        "an isolated_env call site does not pass the run's fresh setting")

    # The harness's OWN in-process reads too — that is the path `recalled_skill`
    # used to reach around the filter.
    assert 'os.environ["PHRONIX_FRESH_CAPABILITIES"] = "1"' in arms
    assert '("PHRONIX_FRESH_CAPABILITIES", previous_fresh)' in arms


def test_no_module_in_the_harness_reads_a_name_nothing_defines():
    """Undefined names, caught here instead of mid-run.

    Every one of these is a latent `NameError` that only fires on the path that
    reaches it, and every one of them was wrapped in an `except Exception` that
    turned it into a plausible-looking message. Found in one sweep:

    * `run_attempt` timed its stages from a `started` that did not exist —
      "could not record the attempt: name 'started' is not defined".
    * `run_task` narrated the end-of-task learn stage with `_say`, a closure
      belonging to `run_attempt`, so `ensure_task_skill` and `snapshot_tracker`
      raised on their first line and were reported as "could not snapshot the
      record". The skill a task leaves for the next run was never written.
    * `_write_solution_skill` called `subprocess` without importing it, inside
      `except Exception: return` — the solution skill silently never appeared.
    * `MiniArm.generate` carried a block of the PLANNER's evidence-staging code
      referencing `context_paths`, while `research`, where it belongs, used the
      `evidence` directory that block was supposed to create.

    A blanket `except` around a stage is the right call — a stage that fails
    must not fail the task — which is exactly why the names have to be checked
    somewhere the exception handler cannot hide them.
    """
    import subprocess
    import sys

    modules = ["tests/benchmark/runner.py", "tests/benchmark/arms.py",
               "tests/benchmark/isolation.py", "tests/benchmark/cluster.py"]
    try:
        proc = subprocess.run([sys.executable, "-m", "pyflakes", *modules],
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        pytest.skip("pyflakes is not installed")
    if "No module named" in (proc.stderr or ""):
        pytest.skip("pyflakes is not installed")

    undefined = [line for line in (proc.stdout or "").splitlines()
                 if "undefined name" in line]
    assert undefined == [], "\n".join(undefined)


def test_backend_pins_are_spread_evenly_not_hashed_into_collisions():
    """A pin has to be stable. It does not have to be arbitrary.

    `sha256(key) % N` is balls-in-bins, and at the sizes this runs at it does
    not spread. Measured on group 1 with 14 arms across 16 backends: it used
    EIGHT of them — one drew three arms, several drew two, and half the fleet
    drew nothing. The fleet reported it as `8/16 replica(s) active`,
    `work 0.227 (IMBALANCED)`, and zero deferred requests while half the GPUs
    sat idle: not a capacity problem, a distribution one.

    Round-robin keeps the one property that was actually needed — the same
    task returns to the backend holding its conversation — and adds the one
    that was missing.
    """
    from collections import Counter

    from tests.benchmark.arms import Arm

    pins = [f"m@{i}" for i in range(16)]
    tasks = [f"repo__repo-{n}" for n in range(7)]
    seen = Counter()
    for arm_name in ("claude-bare", "claude-phronix"):
        arm = Arm()
        arm.arm_name = arm_name
        arm.pinned_models = pins
        for task in tasks:
            seen[arm._pin_index({"instance_id": task})] += 1

    # 14 arms over 16 backends: one each, nothing doubled while a peer idles.
    assert max(seen.values()) == 1, dict(seen)
    assert len(seen) == len(tasks) * 2

    # Stable: a retry must return to the backend that still holds the prefix.
    arm = Arm()
    arm.arm_name = "claude-bare"
    arm.pinned_models = pins
    once = arm._pin_index({"instance_id": tasks[0]})
    assert once == arm._pin_index({"instance_id": tasks[0]})

    # And the two arms of one task are still kept APART — they share no prefix,
    # and one slot serving both makes each wait for the other.
    other = Arm()
    other.arm_name = "claude-phronix"
    other.pinned_models = pins
    assert other._pin_index({"instance_id": tasks[0]}) != once


def test_agents_run_on_the_compute_node_that_holds_their_container(tmp_path):
    """The allocation is for the whole run, not just for containers.

    Agents were launched wherever the harness ran, which on this cluster is a
    SHARED LOGIN NODE. Measured at 12 tasks: 60 `claude` processes and a load
    average of 10.8 on 48 cores, while all six allocated compute nodes sat at
    load 0.00 with zero containers. The ceiling on parallelism was a machine
    outside the allocation that seventeen other people were also using.

    Each task's agents now go to the node already holding its container, so
    reasoning and test runs share a host, a page cache and a checkout.
    """
    from tests.benchmark.arms import remote_agent_command
    from tests.benchmark.isolation import Runtime

    # The runtime says where it is, rather than hiding it in an argv tuple.
    remote = Runtime(name="podman", binary="/usr/bin/podman").with_remote("node42")
    assert remote.host == "node42"

    env = {"PATH": "/usr/bin", "KEEP": "a value with spaces",
           "QUOTE": "it's quoted", "SSH_AUTH_SOCK": "/must/not/travel"}
    argv = remote_agent_command(["claude", "-p", "fix the bug"],
                                tmp_path, env, "node42", 1800, scratch=tmp_path)
    assert argv[0] == "ssh" and "node42" in argv

    # A file per LAUNCH: a fixed name is a race the moment two agents start
    # from one directory, which the research fan-out does by design — the
    # second writer would replace the first one's command and environment.
    again = remote_agent_command(["claude", "-p", "other"], tmp_path, env,
                                 "node42", 1800, scratch=tmp_path)
    assert again[-1] != argv[-1]

    # Read the script THIS argv names, rather than whatever is in the
    # directory — there is deliberately more than one.
    script = Path(argv[-1]).read_text()
    # Carried, and quoted well enough to survive the remote shell.
    assert "export KEEP='a value with spaces'" in script
    assert "QUOTE=" in script and "quoted" in script
    # Local-only names do NOT travel: an agent socket that means nothing there
    # is worse than absent, because it fails as an auth error.
    assert "SSH_AUTH_SOCK" not in script
    # It lands in the right directory and bounds itself on the far side —
    # killing ssh does not reliably kill what it started.
    assert f"cd {tmp_path}" in script
    assert "exec timeout" in script and "1860" in script

    # And the runner puts the agent on the container's node, not somewhere else.
    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert 'arm.agent_host = getattr(self._local.runtime, "host", "") or ""' in runner

    # Every agent launch honours it; one that did not would quietly stay local.
    arms_src = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    launches = arms_src.count("stream_opencode(") - 1      # minus the def
    assert arms_src.count("host=self.agent_host") == launches, (
        f"{launches} launch site(s), "
        f"{arms_src.count('host=self.agent_host')} pass the host")


def test_per_task_settings_do_not_leak_between_concurrent_tasks():
    """One `Arm` object, many tasks at once — so per-task state cannot live on it.

    The runner reuses an arm for every task that arm runs and runs many at
    once in threads. A per-task value written onto the arm as a plain attribute
    is a data race whose result looks plausible: the last task to start
    overwrites it for every task already running.

    Measured the first time agents were placed on compute nodes: 25 of them
    landed on ONE node of five, two nodes got none, and fifteen stayed on the
    login node — every task reading whichever host was written last. The
    container runtime had always avoided this with a thread-local; these two
    had not, and `pinned_for_env` was racing silently, sending a task's
    conversation to another task's backend and destroying the prompt-cache
    locality the pinning exists to create.
    """
    import threading

    from tests.benchmark.arms import Arm

    arm = Arm()
    arm.agent_host = "node-a"
    arm.pinned_for_env = "model@1"

    seen = {}

    def other_task():
        # A second task starting must not see the first task's node...
        assert arm.agent_host == ""
        assert arm.pinned_for_env == ""
        arm.agent_host = "node-b"
        arm.pinned_for_env = "model@2"
        seen["host"] = arm.agent_host
        seen["pin"] = arm.pinned_for_env

    thread = threading.Thread(target=other_task)
    thread.start()
    thread.join()

    assert seen == {"host": "node-b", "pin": "model@2"}
    # ...and must not have overwritten it either.
    assert arm.agent_host == "node-a"
    assert arm.pinned_for_env == "model@1"


def test_research_fanout_agents_inherit_their_task_node():
    """Placement has to survive the fan-out, or most of it never happens.

    `_TASK_LOCAL` is thread-local — which is what stops concurrent tasks
    overwriting each other — and that means a fresh worker thread starts with
    nothing. Research fans out through six pools, so every one of THOSE agents
    read an empty host and ran on the login node: placement worked for the
    attempt and silently did not for the research around it, which is the
    larger half of the work.
    """
    from tests.benchmark.arms import Arm, task_pool

    arm = Arm()
    arm.agent_host = "node-x"
    arm.pinned_for_env = "model@9"

    with task_pool(3) as pool:
        seen = list(pool.map(lambda _: (arm.agent_host, arm.pinned_for_env),
                             range(3)))
    assert seen == [("node-x", "model@9")] * 3, seen

    # Every fan-out in the arms module goes through it. A plain pool would
    # strand its agents on whatever machine drove the run.
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("class Arm"):]
    assert "ThreadPoolExecutor(max_workers=" not in body, (
        "an agent fan-out builds a bare pool; its workers inherit no task")


def test_kill_reaches_agents_on_the_compute_nodes():
    """A kill that leaves work running is worse than no kill.

    It reads as a clean slate. Once agents moved onto the allocated nodes the
    process table stopped being local to the harness, and `kill.sh` reported
    "all stopped" while the previous run's agents kept calling the fleet:
    measured at 208 orphans across five nodes, the oldest 267s old, skewing
    every number the next run produced.
    """
    script = Path("scripts/kill.sh").read_text(encoding="utf-8")
    assert "agent_nodes()" in script
    # Matched on the RUN PATH, never the binary name — an interactive session
    # on the same machine has to survive this.
    assert "/proc/[0-9]*/cmdline" in script
    assert "remote agents reaped" in script
    # Piped to `bash -s` rather than inlined: inlining needed four levels of
    # escaping and silently matched nothing.
    assert "bash -s" in script


def test_the_container_reaper_cleans_every_node_and_every_store():
    """Leftover containers exhaust the kernel keyring, and the next run dies.

    Two independent defaults each made the reaper a no-op:

    * it looped over `${BENCH_NODES:-$(hostname)}`, so it only ever cleaned the
      machine `kill.sh` ran on — while the containers are on the COMPUTE nodes;
    * it pruned the store that resolves on whichever host it ran on, but the
      RUNNER resolves the store in its own process (login node, `/tmp`) and
      hands those paths to podman over ssh, where the same call resolves to
      `/l/ssd`. The reaper cleaned a store the run had never written to.

    Measured after a day of starting and killing runs: ~110 leftover containers
    on each of five nodes, the per-user keyring at 200/200, and every new
    container dying with "unable to join session keyring: disk quota exceeded"
    — an error naming neither containers nor keys, which reads like a full
    disk and failed every task in seconds.
    """
    script = Path("scripts/kill.sh").read_text(encoding="utf-8")

    # Cleans the run's nodes, not just this host.
    assert "${BENCH_NODES:-$(agent_nodes) $(hostname)}" in script
    # And every candidate store, so it does not matter which side resolved it.
    assert "/tmp/$USER/phronix-images" in script
    assert "/l/ssd/$USER/phronix-images" in script
    # Reports what it removed, per store: a prune that silently does nothing
    # is what let this run for a day.
    assert "containers removed: $n ($S)" in script


def test_recording_stages_get_a_hang_guard_not_a_work_budget():
    """Recording is not exploring, so it cannot run away — and must not be cut.

    `track`, `ensure_task_skill` and `snapshot_tracker` read what already
    happened and write it down. Cutting one throws away the attempt, the
    evaluation and the research that were paid for to produce its input.

    They ran on `FINALIZE_BUDGET_S`, a 150s WORK budget, and hit it:

        track>  KILLED at the 150s hard ceiling after 150s
        track>  exited rc=-9: d":"0be2fb67-6a4c-46ea-b8bd-4a1907...
        track>  the record is missing ## The problem, ## How it ...

    Killed mid-write, leaving a truncated record, which then failed the shape
    check and cost a second full pass to re-ask. The budget did not save time;
    it spent it twice and lost the record in between.

    A guard rather than no timeout at all: a wedged agent must still end.
    """
    from tests.benchmark.arms import PhronixArm

    assert PhronixArm.RECORD_GUARD_S >= 900
    assert PhronixArm.RECORD_GUARD_S > PhronixArm.FINALIZE_BUDGET_S

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # The stages that still invoke a recording agent get the guard.
    # `ensure_task_skill` is absent on purpose: it no longer invokes an agent
    # at all. Re-filing a skill is a directory move, not a judgement, and
    # making it one made the pipeline depend on a model staying up — measured
    # on sympy-19254, the re-file agent died on API retries (`exited rc=255`)
    # and left a real diagnosis on disk under a name no reader asks for.
    for name in ("def _fold_events(", "def snapshot_tracker(",
                 "def _reshape_if_needed("):
        body = source[source.index(f"    {name}"):]
        body = body[:body.index("\n    def ", 10)]
        assert "FINALIZE_BUDGET_S" not in body, (
            f"{name} still runs on a work budget; it files, it does not explore")
        assert "RECORD_GUARD_S" in body, f"{name} has no hang-guard"

    # And `track` itself no longer runs a stage at all: it records an event and
    # returns, which is the stronger form of "no budget". The cost of keeping
    # the record is now amortised across the phases that produce it.
    track = source[source.index("    def track(self, instance"):]
    track = track[:track.index("\n    def ", 10)]
    assert "standalone_stage" not in track


def test_an_agent_cannot_install_into_the_benchmarks_own_virtualenv(tmp_path, monkeypatch):
    """A task's source must never end up in the harness's site-packages.

    The harness runs under its own virtualenv, so `dict(os.environ)` handed
    every agent a `VIRTUAL_ENV` and put that venv's `bin` first on PATH — and
    an agent exploring a Python repository runs `pip install -e .` as a matter
    of course.

    Measured: seven SWE-bench repos (django, flask, matplotlib, pylint, sphinx,
    xarray, pytest) were editable-installed into the shared venv, shadowing the
    real packages for everything that used it. The benchmark's own suite then
    imported `_pytest` out of a task checkout and died with "required field
    lineno missing from alias" — and one `.pth` pointed into a run from the
    previous day, so it had been changing what every later task imported,
    silently, across runs.
    """
    from tests.benchmark.isolation import isolated_env

    monkeypatch.setenv("VIRTUAL_ENV", "/bench/venv")
    monkeypatch.setenv("PATH", "/bench/venv/bin:/usr/bin:/bin")

    env = isolated_env(tmp_path / "store", tmp_path / "cache")

    assert "VIRTUAL_ENV" not in env
    assert "/bench/venv/bin" not in env["PATH"].split(":")
    assert "/usr/bin" in env["PATH"].split(":")      # the rest survives
    # And an install attempted anyway fails where it can be seen, rather than
    # succeeding into whatever site-packages happens to be writable.
    assert env["PIP_REQUIRE_VIRTUALENV"] == "1"


def test_the_tracker_cannot_go_looking_for_its_own_inputs():
    """Remove what produces the behaviour, rather than instructing against it.

    The tracker is handed the record's path, the evidence and the phase that
    just ran; searching the filesystem is no part of rewriting one file it was
    given. With `Grep` and `Glob` it searched anyway — measured on
    scikit-learn-25570, the stage read `tracker.md` and then spent the rest of
    its clock on "looking for files named like tracker.md", over and over,
    until the hard ceiling killed it having written nothing. Research then ran
    with no record at all (`fom=NONE approaches=0, called no research tools`),
    so the loop cost the diagnosis as well as the record.

    Raising the budget made it worse rather than better — the same loop, for
    longer — which is the tell that the tools were the problem, not the clock.
    """
    import yaml

    spec = yaml.safe_load(
        Path("src/phronix/.phronix/agents/phronix-tracker.yaml").read_text())
    tools = set(spec["tools"])

    assert "Grep" not in tools and "Glob" not in tools
    # It still has to read what it was handed and write the record.
    assert {"Read", "Write"} <= tools
    # And the things it was never allowed: running anything, editing source,
    # or handing the job to a fresh session with the default toolset.
    assert not ({"Bash", "Edit", "Agent", "Task"} & tools)


def test_ssh_multiplexing_is_available_but_not_the_default():
    """Multiplexing is opt-in, and this records why.

    It was added to avoid `MaxStartups` — ten concurrent unauthenticated
    connections — which cost about one failure in sixty. It trades that for
    `MaxSessions`, ten multiplexed sessions per connection, and that refusal
    does not queue and does not silently downgrade: it FAILS, and surfaces as
    `isolation: could not start <image>`.

    Sharding over several masters only moves the cliff — measured on one host
    at 40 simultaneous commands, 4 masters gave 39/40 and 8 gave 36/40, thread
    ids not spreading evenly over a small modulus. Retrying the refusal gives
    40/40, so that is the mechanism and this stays off until a mux refusal
    degrades instead of failing.
    """
    import os

    from tests.benchmark.isolation import ssh_options

    plain = ssh_options()
    assert "ControlMaster=auto" not in plain
    assert "BatchMode=yes" in plain

    os.environ["PHRONIX_SSH_MUX"] = "1"
    try:
        muxed = ssh_options()
        assert "ControlMaster=auto" in muxed
        control = [o for o in muxed if o.startswith("ControlPath=")]
        assert control, "no control socket path"
        path = control[0].split("=", 1)[1]
        # A unix socket: node-local, and short — the limit is about 100
        # characters and a run directory alone can exceed it.
        assert not path.startswith("/p/lustre"), path
        assert len(path) < 90, len(path)
    finally:
        os.environ.pop("PHRONIX_SSH_MUX", None)

    # Every ssh in the harness goes through the one options builder.
    for name in ("tests/benchmark/arms.py", "tests/benchmark/isolation.py"):
        source = Path(name).read_text(encoding="utf-8")
        assert 'ssh", "-n", "-o", "BatchMode=yes"' not in source, (
            f"{name} builds an ssh command that bypasses ssh_options()")


def test_the_agent_binary_is_resolved_to_something_that_exists():
    """A path that was valid a minute ago is not a path that exists.

    The Claude binary was taken from the VS Code extension directory, newest
    match first, unchecked. VS Code updates the extension in place and deletes
    the old directory: measured live, the harness had baked
    `anthropic.claude-code-2.1.246-.../native-binary/claude` into its command,
    the extension became 2.1.247 mid-run, and every stage started afterwards
    died instantly with `exited rc=127` — which names neither the binary nor
    the version and reads like a broken agent.
    """
    import os

    from tests.benchmark.arms import find_claude_bin

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("def find_claude_bin("):]
    body = body[:body.index("\nclass ")]
    # PATH first: a stable location that survives an extension update.
    assert 'shutil.which("claude")' in body
    assert body.index('shutil.which("claude")') < body.index("glob.glob")
    # And every candidate is checked to be an executable FILE — the directory
    # survived the update that removed the binary inside it, so the glob
    # still matched.
    assert "os.access(match, os.X_OK)" in body

    resolved = find_claude_bin()
    if resolved != "claude":
        assert os.path.isfile(resolved) and os.access(resolved, os.X_OK), resolved


def test_the_remote_wrapper_skips_environment_entries_a_shell_cannot_export(tmp_path):
    """A bash FUNCTION in the environment corrupts the whole script.

    Lmod exports `module` and `ml` as `BASH_FUNC_module%%` and `BASH_FUNC_ml%%`,
    whose values are multi-line function bodies. `export BASH_FUNC_ml%%=...` is
    not a valid identifier, so the export fails — and the body then runs on
    past the failed line, so the shell reads `case "$-" in` and the rest of the
    function as commands and the script is corrupted from there.

    Measured: every `track` fold produced no record and no output whatsoever,
    and the same function bodies surfaced as the tail of unrelated error
    messages (`try 1: unset __lmod_sh_dbg;`), which reads like a broken agent
    rather than a broken script.
    """
    from tests.benchmark.arms import remote_agent_command

    env = {
        "PATH": "/usr/bin",
        "KEEP": "ordinary value",
        "BASH_FUNC_module%%": "() {  echo hi\n}",     # exactly what Lmod exports
        "BASH_FUNC_ml%%": "() {  eval x\n}",
        "1BAD": "starts with a digit",
        "has-dash": "not an identifier either",
    }
    argv = remote_agent_command(["true"], tmp_path, env, "node42", 30,
                                scratch=tmp_path)
    script = Path(argv[-1]).read_text()

    assert "export KEEP=" in script
    for bad in ("BASH_FUNC_module", "BASH_FUNC_ml", "1BAD", "has-dash"):
        assert f"export {bad}" not in script, bad

    # Every export line must be one a shell would accept.
    for line in script.splitlines():
        if line.startswith("export "):
            name = line[len("export "):].split("=", 1)[0]
            assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name), line


def test_research_files_its_diagnosis_or_is_asked_again():
    """A diagnosis nobody wrote down is a diagnosis the next try cannot use.

    The pass was judged on its TRANSCRIPT — PROBLEM/APPROACH/ANSWER — and
    nothing checked that the skill it was told to write exists. Measured on
    matplotlib-26011: research read the record, the conversation and the issue,
    reported `PROBLEM:`, called `skill_load` on a skill that was not there yet,
    and stopped at 159s of its 300s having called no writing tool at all:

        tools         research-2: no phronix tools called
        search-skill  no skill covers this task; solving from scratch
        attempt>      agent working on try 2 from scratch

    So try 2 started over while the diagnosis sat in a transcript. And
    `ensure_task_skill` does not cover it — that re-files a skill written under
    the WRONG NAME, and here there was no skill at all.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def research_from_tracker("):]
    body = body[:body.index("\n    def ", 10)]

    # The pass checks its own output before returning — and checks for
    # CONTENT, not mere existence: `skill_write` creates the scaffold, so a
    # pass that named the skill and wrote nothing still left a file behind.
    assert "_skill_has_content(store_root, skill)" in body
    assert "FILE_DIAGNOSIS_PROMPT" in body
    # Asked to FILE, not to diagnose again — the budget went on the diagnosis.
    from tests.benchmark.arms import PhronixArm
    prompt = " ".join(PhronixArm.FILE_DIAGNOSIS_PROMPT.split())
    assert "Do not diagnose again" in prompt
    assert "skill_write(name=" in prompt
    # And a second failure is reported rather than looped on.
    assert "is still empty" in body


def test_a_run_records_whether_the_attempt_actually_used_the_skill():
    """Offered and used are different things; only one says the store worked.

    The trace announced `found X — the attempt solves with it` the moment the
    lookup hit, which reports what the HARNESS did, not what the agent did. An
    attempt that was handed a skill and ignored it, and one that read it and
    applied it, produced identical lines — so the question the whole store
    exists to answer could not be read off a run at all.
    """
    from tests.benchmark.metrics import Attempt

    # Recorded per attempt, and `None` when nothing was offered — "not used"
    # and "nothing to use" are different states.
    assert Attempt(index=1).skill_loaded is None

    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    body = runner[runner.index("    def _trace_skill_use("):]
    body = body[:body.index("\n    def ", 10)]

    # Measured against what THIS attempt retrieved, not the task's history —
    # otherwise an earlier try's load counts for a later one.
    assert "if name not in before" in body
    # Both outcomes are traced. The silent one is the one that matters.
    assert "loaded `" in body and "never loaded it" in body
    assert '"loaded": True' in body and '"loaded": False' in body

    # And the snapshot is taken BEFORE the attempt runs.
    assert "retrieved_before = set(read_retrievals(retrieval_log))" in runner
    assert (runner.index("retrieved_before = set(read_retrievals(retrieval_log))")
            < runner.index("self._trace_skill_use("))


def test_ssh_refusals_are_retried_rather_than_voiding_a_task():
    """sshd refusing a connection is not the task failing.

    Both of sshd's limits are hit at this concurrency and both are transient:
    `MaxStartups` (ten concurrent unauthenticated connections) and, with
    multiplexing on, `MaxSessions` (ten sessions per connection). Measured on
    one host at 40 simultaneous container commands, plain ssh managed 35/40 and
    multiplexed 39/40 — and every loss surfaced as

        isolation: could not start docker.io/swebench/...:latest

    which names an image and reads as a broken one. With the retry: 40/40.

    Multiplexing is off by default for the same reason it was added and then
    withdrawn: it trades `MaxStartups` for `MaxSessions`, and a mux refusal
    FAILS rather than degrading to a direct connection.
    """
    from tests.benchmark.isolation import (SSH_RETRIES, _transient_ssh,
                                           ssh_options)

    # Refusals retry...
    assert _transient_ssh("kex_exchange_identification: Connection closed")
    assert _transient_ssh("mux_client_request_session: Session open refused by peer")
    # ...and real failures do not, or a missing image would be retried four
    # times before anyone was told.
    assert not _transient_ssh("Error: no such image: docker.io/swebench/x:latest")
    assert not _transient_ssh("")
    assert SSH_RETRIES >= 2

    # Off unless asked for.
    assert "ControlMaster=auto" not in ssh_options()

    # The retry wraps the ONE place container commands are run, so nothing
    # reaches ssh by a path that does not retry.
    source = Path("tests/benchmark/isolation.py").read_text(encoding="utf-8")
    body = source[source.index("    def run(self, args: List[str]"):]
    body = body[:body.index("\n    def available(")]
    assert "for attempt in range(SSH_RETRIES)" in body
    assert "_transient_ssh(result.stderr)" in body


def test_refiling_a_skill_never_takes_another_tasks():
    """Two tasks on one repository are two tasks, not one subject.

    Strays were matched on a name STEM — `wanted.split("-")[0]`, so "pydata"
    for `pydata-xarray-3364` — which matches every other pydata task in the
    group. The task then merged a NEIGHBOUR's skill into its own and `rmtree`d
    it. Measured in one run: `pydata-xarray-3364` and `pydata-xarray-4493` are
    different tasks, each matched the other, 3364's skill was destroyed by
    4493's re-file, and 4493's real instructions (about `dtypes.py` and
    `GroupBy.__repr__`) were offered to 3364, whose bug is in `concat.py`.

    The issue number is what makes two names the same task.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def ensure_task_skill("):]
    body = body[:body.index("\n    def ", 10)]

    # The CODE, not the comment that explains why it went.
    assert 'stem = wanted.split' not in body, "still matching on a name stem"
    assert "and stem in d.name" not in body
    assert "def belongs(" in body

    # The rule itself, checked rather than described.
    def belongs(wanted: str, name: str) -> bool:
        issue = (re.findall(r"\d+", wanted) or [""])[-1]
        if name == wanted:
            return False
        if issue and issue in name:
            return True
        return not re.search(r"\d", name)

    # Same issue, misnamed: merged.
    assert belongs("pydata-xarray-3364", "pydata-xarray-3364-fix")
    # A different task on the same repository: LEFT ALONE. This is the one
    # that was destroying work.
    assert not belongs("pydata-xarray-3364", "pydata-xarray-4493")
    assert not belongs("sympy-sympy-19254", "sympy-sympy-24102")
    # Named after the bug rather than the ticket: it cannot belong to another
    # numbered task, so it is recovered rather than stranded.
    assert belongs("sympy-sympy-19254", "sympy-mignotte-bound-fix")


def test_research_is_not_satisfied_by_an_empty_skill(tmp_path):
    """`skill_write` creates the scaffold, so existing proves nothing.

    The check after a research pass asked whether the skill EXISTED. Creating a
    subject writes the file with its headings, so a pass that named the skill
    and wrote no blocks left `## Instructions` and `## Rules` empty and every
    later check satisfied — the lookup reported `found ... — the attempt solves
    with it`, and `skill-use` recorded tries 2 and 3 as having worked from it.

    Measured on pydata-xarray-3364: `SKILL.md` 220 bytes, zero blocks, and a
    `LESSONS.md` reading "Attempt to ignore missing variables ... failed –
    agent produced no patch". Try 3 was revising an empty file and nothing said
    so. Across that run, 6 of 11 stored skills were scaffolds.

    Lessons deliberately do not count: a lesson is "the last attempt failed",
    an instruction is what to do instead, and only the second is a diagnosis
    the next attempt can apply.
    """
    from tests.benchmark.arms import PhronixArm

    arm = PhronixArm.__new__(PhronixArm)
    tasks = tmp_path / "capabilities" / "tasks"

    def write(name: str, body: str, lessons: str = "") -> None:
        home = tasks / name / name
        home.mkdir(parents=True, exist_ok=True)
        (home / "SKILL.md").write_text(
            f"---\nname: {name}\nsubject: {name}\ntype: skill\n---\n\n"
            f"## Index\n\n| Label | Section | Covers |\n| --- | --- | --- |\n"
            f"{body}\n## Rules\n\n## References\n")
        if lessons:
            (home / "LESSONS.md").write_text(lessons)

    # The scaffold `skill_write` leaves behind, with a lesson beside it.
    write("empty-one", "\n## Instructions\n",
          "## Lessons\n\n### L1 — The last attempt failed\n\nIt produced no patch.\n")
    assert not arm._skill_has_content(tmp_path, "empty-one")

    # A real diagnosis.
    write("filled-one",
          "| `I1` | Instructions | Pad the degree tuple |\n\n## Instructions\n\n"
          "### I1 — Pad the degree tuple\n\nIn `monomials.py`, sum the powers.\n")
    assert arm._skill_has_content(tmp_path, "filled-one")

    # And the pass re-asks on emptiness, not on absence.
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def research_from_tracker("):]
    body = body[:body.index("\n    def ", 10)]
    assert "_skill_has_content(store_root, skill)" in body
    assert "is empty" in body


def test_a_failed_evaluation_hands_research_the_lessons_and_the_record(tmp_path):
    """A revision needs to know what has already been tried and failed.

    That lived in two places research was never handed: the skill it is about
    to rewrite, and the `LESSONS.md` beside it. The two files are one skill and
    are retrieved separately — `skill_load` returns `SKILL.md` unless asked for
    lessons BY NAME — so a reader had no way to know lessons existed.

    Measured on pydata-xarray-3364: `SKILL.md` was an empty scaffold and the
    one sentence describing what try 1 had attempted, and why it failed, sat
    unread in `LESSONS.md`. Tries 2 and 3 both loaded that skill and got
    nothing; research re-derived the problem from the tracker each time.
    """
    from tests.benchmark.arms import PhronixArm

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def research_from_tracker("):]
    body = body[:body.index("\n    def ", 10)]

    # The skill AND its lessons are attached, beside the record.
    assert 'f"*/{skill}/SKILL.md"' in body
    assert 'f"*/{skill}/LESSONS.md"' in body
    assert "tracker," in body

    # And the prompt tells it what they are for, and to write BOTH halves back.
    prompt = " ".join(PhronixArm.TASK_RESEARCH_PROMPT.split())
    assert "LESSONS.md" in prompt                   # attached, by name
    assert "I7" in prompt                          # the method, in the skill
    assert "skill_write_lesson" in prompt          # record this failure too
    assert "BROKE" in prompt                       # name the regressions


def test_a_skill_points_at_its_own_lessons(tmp_path, monkeypatch):
    """One skill, two files, and only one of them was findable.

    Writing a lesson now names it in the skill's `## References`, and loading
    the skill returns the lesson TITLES — enough to decide whether to spend a
    call on them, without the reader having to know they exist.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))

    from phronix.skills import load, write_block, write_lesson

    write_block("demo-subject", "instruction", "Do the thing",
                "Edit concat.py and sum the powers.")
    write_lesson("demo-subject", "Ignoring missing variables broke 7 tests.",
                 title="Ignoring missing variables")

    skill_file = next(Path(tmp_path).rglob("demo-subject/SKILL.md"))
    text = skill_file.read_text()
    assert "LESSONS.md" in text.split("## References")[1]

    found = load("demo-subject")
    assert found["lessons"]["titles"] == ["Ignoring missing variables"]
    assert "LESSONS.md" in found["lessons"]["load"]

    # Written once, however many lessons follow.
    write_lesson("demo-subject", "And a second one.", title="Second")
    assert skill_file.read_text().count("LESSONS.md") == 1


def test_a_traceback_naming_a_relative_path_still_blames_the_patch():
    """pytest names the culprit as `pkg/mod.py:3278:` — path AND line number.

    `_blamed_files` captured absolute `/testbed/` paths and bare basenames, and
    that shape is neither: it has slashes, so the basename branch skipped it,
    and no `/testbed/` prefix, so the path branch skipped it too. Nothing was
    blamed, so a patch that broke the module read as an ENVIRONMENT fault and
    aborted the task with its remaining tries unused.

    Measured on sympy-18057: the patch put a `SyntaxError` in
    `sympy/core/function.py`, the traceback said so on every line, and the task
    was thrown away after try 1 — the one failure a retry reliably fixes, and
    the one the skill loop exists to learn from.
    """
    from tests.benchmark.runner import _blamed_files, _blames_patch

    real = (
        "RUNNER FAILED — no test produced a result; the runner did not start: "
        "E   SyntaxError: invalid syntax\n"
        "    from .function import (_coeff_isneg, expand_complex,\n"
        "sympy/core/function.py:3278: in <module>\n"
        "    from sympy.core.symbol import Dummy, Symbol")

    assert "sympy/core/function.py" in _blamed_files(real)
    assert _blames_patch(real, ["sympy/core/function.py"]) == "sympy/core/function.py"
    # A patch elsewhere is NOT blamed — a false "the patch broke it" costs a
    # retry, but it must not be handed out for free.
    assert _blames_patch(real, ["sympy/polys/monomials.py"]) == ""

    # The shapes that already worked still work.
    conftest = ("ConftestImportFailure: SyntaxError: invalid syntax "
                "(blueprints.py, line 1)")
    assert _blames_patch(conftest, ["src/flask/blueprints.py"])
    absolute = "  File \"/testbed/xarray/core/concat.py\", line 12"
    assert _blames_patch(absolute, ["xarray/core/concat.py"])


def test_an_error_tail_always_names_the_file_it_blames():
    """The exception says what broke; only the file line says where.

    "Where" is what decides whether a broken testbed is the harness's fault or
    the patch's, and trimming by size dropped it whenever the traceback was
    long. The trace then read `cannot run pytest: IndentationError: expected an
    indented block` with no path — nothing to blame, so the task was aborted as
    an environment fault although its own patch had just mis-indented a file.

    Measured across one night: 12 tasks lost that way, every one of them a
    patch error and every one the kind a retry reliably fixes.
    """
    from tests.benchmark.runner import _blames_patch, _error_tail

    raw = "\n".join(
        [f"noise line {i}" for i in range(40)]
        + ['  File "/testbed/astropy/units/format/utils.py", line 12',
           "    return x",
           "IndentationError: expected an indented block"])

    tail = _error_tail(raw)
    assert "IndentationError" in tail                    # the what, first
    assert "utils.py" in tail                            # and the where
    assert _blames_patch(tail, ["astropy/units/format/utils.py"])

    # It does not invent one when the output names no file at all.
    bare = _error_tail("something went wrong\nand then stopped")
    assert ".py" not in bare


def test_the_batch_job_waits_for_the_run_it_started():
    """`run-group.sh` returns when the run STARTS, not when it finishes.

    It launches the runner with `nohup ... &` and exits as soon as it has a
    pid. Treating that exit as completion made the batch script tear down the
    fleet eleven seconds after starting the run:

        [00:51:27] running: size=30 index=1 parallel=30
        [00:51:38] run finished: .../claude-0827-005137
        [00:52:17] batch group1 done

    The run directory did not survive the cleanup that followed.
    """
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")

    # It reads the runner's pid out of the launch log and waits on it.
    assert 'grep -E "^pid " "$rlog"' in batch
    assert 'while kill -0 "$runner" 2>/dev/null; do' in batch
    # And has a fallback for the case where no pid was printed.
    assert 'pgrep -f "benchmark.cli run"' in batch
    # The teardown must come AFTER the wait, or it kills what it waited for.
    assert batch.index('while kill -0 "$runner"') < batch.index("scripts/kill.sh")

    # `run-group.sh` really does background the runner — the premise above.
    launcher = Path("scripts/run-benchmark.sh").read_text(encoding="utf-8")
    assert "nohup" in launcher


def test_a_gateway_model_is_told_when_to_compact():
    """The CLI cannot know a gateway model's context window.

    Left to itself it sizes auto-compaction to the model's ADVERTISED limit,
    and `gpt-oss-120b` is not a name it ships one for — so it never compacted,
    and an agent that kept exploring hit the wall instead. Measured on
    sphinx-10451: 215 steps in a single attempt, then `400
    ContextWindowExceededError`, the whole try lost with no patch and no usable
    transcript. Eight of one run's nineteen pipeline faults were this.

    Only for a redirected endpoint: against real Anthropic models the default
    knows the window better than a fixed number does, and forcing this would
    compact a 200k context at half its size.
    """
    from tests.benchmark.arms import ClaudeArm

    arm = ClaudeArm.__new__(ClaudeArm)

    arm.provider, arm.base_url = "tuolumne", "http://tuolumne1016:4000/v1"
    assert arm._is_redirected()

    arm.provider, arm.base_url = "anthropic", "https://api.anthropic.com/v1"
    assert not arm._is_redirected()
    # An unset provider means "not chosen", which is Anthropic.
    arm.provider, arm.base_url = "", "http://somewhere/v1"
    assert not arm._is_redirected()

    # The floor the CLI accepts is 100k; the models served here train to
    # 131072, so this has to sit between the two.
    assert 100_000 <= ClaudeArm.autocompact_tokens < 131_072

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert '"--autocompact", str(self.autocompact_tokens)' in source
    assert "if self._is_redirected() and self.autocompact_tokens:" in source


def test_a_failed_command_records_what_it_said():
    """`CalledProcessError` prints the argv and swallows the reason.

    Its `__str__` is the command and the exit status; stdout and stderr are on
    the exception and are not shown. So the trace recorded

        CalledProcessError: Command '['ssh', '-n', ... ]' returned non-zero
        exit status 1

    — a hundred characters of argv and not one word about the cause. Every
    such failure had to be reproduced by hand to learn anything, and a
    pipeline fault you cannot read is one you will not fix.
    """
    import subprocess

    from tests.benchmark.runner import _error_tail

    exc = subprocess.CalledProcessError(
        1, ["ssh", "node", "podman", "run"],
        output="", stderr="Error: OCI runtime error: no space left on device")

    message = f"{type(exc).__name__}: {exc}"
    said = _error_tail((getattr(exc, "stderr", "") or "")
                       + (getattr(exc, "output", "") or ""), 300)
    assert said and "no space left on device" in said

    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert 'said = _error_tail(' in runner
    assert 'attempt.error = f"{attempt.error} — {said}"' in runner


def test_a_patch_that_does_not_parse_is_a_verdict_not_a_runner_fault():
    """Zero passes and zero failures CAN be produced by a patch.

    `_runner_failure` rests on the claim that "a patch that breaks everything
    still makes the tests RUN". True of a patch that is merely wrong, false of
    one that is not valid Python: the module cannot be imported, nothing is
    collected, and the result looks exactly like a missing pytest.

    Measured on django-14155 — the agent wrote diff markers into the file:

        File "/testbed/django/urls/resolvers.py", line 68
            +            return (
        SyntaxError: invalid syntax

    and the harness reported RUNNER FAILED. That is a model error dressed as a
    harness fault: it inflates the pipeline count, and the attempt is told the
    runner broke rather than that its own patch will not parse, so the next
    try has nothing to correct.
    """
    from tests.benchmark.runner import _files_in_patch, patch_broke_the_source

    patch = ("diff --git a/django/urls/resolvers.py b/django/urls/resolvers.py\n"
             "--- a/django/urls/resolvers.py\n"
             "+++ b/django/urls/resolvers.py\n"
             "@@ -60,6 +60,7 @@\n"
             "+            return (\n")
    assert _files_in_patch(patch) == ["django/urls/resolvers.py"]

    broke = ('  File "/testbed/django/urls/resolvers.py", line 68\n'
             "    +            return (\n"
             "SyntaxError: invalid syntax")
    assert "django/urls/resolvers.py" in patch_broke_the_source(broke, patch)

    # A syntax error in a file the agent never touched IS a runner fault: the
    # testbed is broken and the patch says nothing about it.
    elsewhere = broke.replace("django/urls/resolvers.py", "django/db/models/query.py")
    assert patch_broke_the_source(elsewhere, patch) == ""

    # And a patch that is merely wrong still runs the tests.
    assert patch_broke_the_source("2 failed, 3 passed", patch) == ""

    # The verdict it produces has the SAME shape as every other verdict, so
    # the feedback, the metrics and the ledger read it without special-casing.
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    block = source[source.index("        broken = patch_broke_the_source("):]
    block = block[:block.index("        return _runner_failure(")]
    for key in ("failure_detail", "output_tail", "fail_to_pass_total",
                "pass_to_pass_total", "regressions"):
        assert f'"{key}"' in block, key
    # NOT flagged as a runner failure — the runner was fine.
    assert '"runner_failed"' not in block


def test_a_failed_ssh_says_why_not_just_which_command():
    """`CalledProcessError` renders the command and the exit code, not the cause.

    A container failure arrived in the trace as a hundred characters of podman
    arguments and nothing about why — indistinguishable between sshd refusing
    the connection, a missing image, and a full disk. The stderr tail is the
    one thing that separates them, and it was carried on the exception where
    nothing ever printed it.
    """
    import subprocess

    from tests.benchmark.isolation import Runtime

    runtime = Runtime(name="podman", binary="/bin/false").with_remote("nosuchhost-xyz")
    try:
        runtime.run(["ps"], check=True, timeout=20)
    except subprocess.CalledProcessError as failure:
        assert "Could not resolve hostname" in str(failure), str(failure)
    else:
        pytest.skip("that host unexpectedly resolved")


def test_images_come_from_the_pfs_archive_before_the_registry():
    """The registry is the last resort, not the first.

    Every image is archived on the PFS by `prefetch`, and the node-local
    podman store is a cache a fresh node does not have. The container session
    pulled first regardless, so a group scheduled onto nodes that had not run
    before went to Docker Hub for thirty images at once — and Docker Hub rate
    limits unauthenticated pulls:

        toomanyrequests: You have reached your unauthenticated pull rate limit

    Measured: that failed ALL 60 task-arms of a group within four minutes,
    surfacing as `isolation: could not start <image>`, which reads as a
    missing or broken image rather than as a quota. The archives were on the
    same filesystem the whole time.
    """
    from tests.benchmark.isolation import archive_for

    source = Path("tests/benchmark/isolation.py").read_text(encoding="utf-8")
    body = source[source.index("def ensure_image("):]
    body = body[:body.index("\ndef ", 10)]
    # Cache, then archive, then registry — in that order.
    assert body.index('"image", "exists"') < body.index("archive_for(")
    assert body.index("archive_for(") < body.index('"pull"')

    # And the session uses it rather than pulling directly.
    session = source[source.index("    def __enter__(self) -> Container:"):]
    session = session[:session.index("\n    def ", 10)]
    assert "ensure_image(" in session
    assert '["pull", self.image]' not in session

    # `_1776_` is how SWE-bench spells `__` in an image tag.
    got = archive_for("docker.io/swebench/sweb.eval.x86_64.pallets_1776_flask-4992:latest")
    if got is not None:                      # only where the archives exist
        assert got.name == "pallets__flask-4992.tar"
    # An image with no archive falls through rather than raising.
    assert archive_for("docker.io/swebench/sweb.eval.x86_64.nosuch_1776_thing-1:latest") is None


def test_concurrent_batch_jobs_do_not_share_a_fleet_config():
    """Two jobs running together must not point at one another's fleet.

    `deploy.sh` writes its fleet description to `$RUNDIR/cluster.json` and then
    copies it to the shared `<fleet>/cluster.json`. That copy is a convenience
    for interactive use and is last-writer-wins by construction — so a batch
    job that reads it (`run-group.sh --local`) gets whichever fleet came up
    most recently, not its own.

    With two 300-task runs queued behind each other that is silent corruption:
    the first job's tasks are sent to the second job's gateway, one fleet
    serves twice its load while the other sits idle, and the manifest records
    the wrong gateway so the trace does not show it either.
    """
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")
    deploy = Path("tuolumne-llm/deploy.sh").read_text(encoding="utf-8")
    group = Path("scripts/run-group.sh").read_text(encoding="utf-8")

    # The job owns a RUNDIR, named for the job rather than the clock: two jobs
    # starting in the same second would collide on a timestamp.
    assert "export RUNDIR=$LLM_ROOT/logs/run-$NAME-" in batch
    # `deploy.sh` honours it instead of always inventing one.
    assert "RUNDIR=${RUNDIR:-$LLM_ROOT/logs/run-$(date" in deploy
    # And the run is pointed at THAT file, never the shared one.
    assert '--cluster "$CLUSTER_JSON"' in batch
    assert "CLUSTER_JSON=$RUNDIR/cluster.json" in batch
    # The invocation itself, not the prose around it: `--local` is named in
    # the comment that explains why it is not used.
    invocation = [line for line in batch.splitlines()
                  if "run-group.sh" in line and not line.lstrip().startswith("#")]
    assert invocation, "bench-batch no longer calls run-group.sh"
    assert not any("--local" in line for line in invocation)

    # The task-list slice is shared too: its path comes from --size and --index
    # alone, so several runs of the same slice write it at once. Renamed into
    # place so a reader never sees it half-written.
    assert 'mv -f "$FILE.$$" "$FILE"' in group


def test_a_local_fleet_that_has_not_served_yet_is_not_mistaken_for_hosted():
    """`budget_scale` halved every budget on every batch run.

    The rate comes from `predicted_tokens_seconds`, which is the rate of
    FINISHED requests — so it reads 0 on a fleet deployed seconds ago, which is
    every batch run, because the job brings up the fleet and starts the run
    immediately. `measured_decode_rate` then returns None, and None was read as
    "no fleet, therefore hosted", which takes the hosted scale of 0.5.

    Measured across two 300-task runs on 64 nodes: `budget_scale = 0.5` in both
    manifests and 778 stages killed at their ceiling between them — 563 of them
    research, the stage the next attempt depends on.
    """
    import json
    import tests.benchmark.arms as arms

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("def budget_scale("):]
    body = body[:body.index("\ndef ", 10)]
    # Neutral, not hosted, when a fleet exists but cannot be measured yet...
    assert "has_local_fleet()" in body
    # ...and NOT cached, so a later caller measures once traffic exists and
    # the budgets correct themselves mid-run.
    assert body.index("has_local_fleet()") < body.index("hosted_budget_scale")

    def scale_with(servers, tmp):
        config = tmp / "cluster.json"
        config.write_text(json.dumps({"servers": servers}))
        os.environ["PHRONIX_CLUSTER"] = str(config)
        os.environ["PHRONIX_BUDGET_SCALE"] = "auto"
        arms._BUDGET_SCALE_CACHE["value"] = None
        return arms.budget_scale()

    import os
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    previous = os.environ.get("PHRONIX_CLUSTER"), os.environ.get("PHRONIX_BUDGET_SCALE")
    try:
        # A fleet is configured but has served nothing: GENEROUS, and uncached.
        #
        # Above 1.0 on purpose. The two errors are not symmetric: a budget
        # that is too long costs wall-clock on a stage that would have
        # finished anyway, while one that is too short throws the stage's work
        # away and leaves the next attempt with no skill to start from.
        unmeasured = scale_with([{"host": "nosuch", "port": 8050}], tmp)
        assert unmeasured == float(
            arms._tuned("research.local_unmeasured_budget_scale", 2.0))
        assert unmeasured > 1.0
        assert arms._BUDGET_SCALE_CACHE["value"] is None
        # No fleet at all really is hosted, and keeps the hosted scale.
        assert scale_with([], tmp) == 0.5
    finally:
        for name, value in zip(("PHRONIX_CLUSTER", "PHRONIX_BUDGET_SCALE"), previous):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        arms._BUDGET_SCALE_CACHE["value"] = None


def test_a_finished_batch_job_releases_nodes_when_its_siblings_are_queued():
    """The hold is right for one run and wrong for a queue.

    Holding keeps the fleet and containers alive to be looked at, and time
    already granted cannot be got back. But measured on a 300-task run: it
    finished in 2h05m of its 24h and then sat on 64 idle nodes for the
    remaining 21h50m while two more jobs of the same batch waited in SCHED.
    The hold that exists to avoid wasting an allocation was wasting three.
    """
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")
    assert "releasing the nodes now" in batch
    # And even with nothing queued the hold is BOUNDED: over-asking for wall
    # time should buy the run a margin to finish in, not a right to sit on
    # idle nodes for the surplus.
    assert "HOLD_S=${HOLD_S:-1200}" in batch
    assert "then releasing" in batch
    # Only OUR jobs count: cancelling because a stranger is queued would hand
    # the nodes to the scheduler rather than to the work this is part of.
    assert '"^tuo-\\|^bench-\\|^corona-"' in batch
    hold = batch[batch.index("# ...unless somebody else is waiting"):]
    assert hold.index("limit=0") < hold.index('limit=$(seconds_of "$WALL")')


def test_a_failed_node_moves_the_task_instead_of_killing_it():
    """A node that dies should cost one retry, not a task.

    A task's container host was fixed for its lifetime, so a node that stopped
    accepting containers took every task placed on it: both isolation attempts
    were spent proving the same node was still dead, and the task aborted with
    `environment unavailable`. Every later task round-robined onto that node
    did the same.

    Measured: a 64-node run lost 105 in-flight tasks when one node failed. Flux
    kills the whole job when a node dies outright and nothing here can catch
    that — but a node that is merely unreachable, out of disk, or has lost its
    podman takes tasks down one at a time, and those are recoverable.
    """
    from tests.benchmark.isolation import Runtime
    from tests.benchmark.runner import Runner

    runner = Runner.__new__(Runner)
    runner._runtimes = [Runtime(name="podman", binary="/x").with_remote(h)
                        for h in ("n1", "n2", "n3", "n4")]
    Runner._BAD_HOSTS.clear()
    try:
        # New tasks skip a node already known bad, and stay evenly spread over
        # the survivors — a fixed modulus would keep sending every fourth task
        # to the dead one.
        assert [runner.runtime_for(i).host for i in range(4)] == ["n1", "n2", "n3", "n4"]
        runner.note_bad_host("n2", "unreachable")
        placed = [runner.runtime_for(i).host for i in range(6)]
        assert "n2" not in placed
        assert set(placed) == {"n1", "n3", "n4"}

        # A task already on the bad node is MOVED rather than retried there.
        moved = runner.another_runtime(runner._runtimes[1])
        assert moved is not None and moved.host != "n2"

        # And if every node looks bad — more often a transient than a truth —
        # it still moves off the current one rather than refusing to place.
        for host in ("n1", "n3", "n4"):
            runner.note_bad_host(host)
        anywhere = runner.another_runtime(runner._runtimes[0])
        assert anywhere is not None and anywhere.host != "n1"
    finally:
        Runner._BAD_HOSTS.clear()

    # The retry path does not count a try that never ran on a working node.
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    block = source[source.index("            except IsolationError as exc:"):]
    block = block[:block.index("            except (ResearchCollapsed")]
    assert "another_runtime(" in block
    assert "isolation_failures -= 1" in block


def test_a_cut_short_run_can_be_continued_instead_of_repeated(tmp_path):
    """Results are already a checkpoint; this is what makes them read.

    A node failure kills the whole Flux job. Measured: one dead node took 105
    in-flight tasks — and the ~500 task-arms the job had ALREADY finished went
    with it, because `run` deletes `results.jsonl` and starts from nothing. The
    resubmission then repeated hours of completed work.

    `append_result` writes one line per task as it finishes, so the file is a
    checkpoint already. Resuming reads it, carries those results into the new
    run so its report covers the whole list, and skips the tasks behind them.
    """
    import json

    from tests.benchmark.runner import RunConfig, Runner

    tasks = ["a__a-1", "b__b-2", "c__c-3"]
    dead = tmp_path / "runs" / "claude-old"
    (dead / "arm1").mkdir(parents=True)
    (dead / "manifest.json").write_text(json.dumps({"tasks": tasks, "model": "m1"}))
    (dead / "arm1" / "results.jsonl").write_text(
        json.dumps({"instance_id": "a__a-1", "resolved": True}) + "\n"
        + json.dumps({"instance_id": "b__b-2", "resolved": False}) + "\n"
        + '{"instance_id": "c__c-3", "reso')          # died mid-write

    new = tmp_path / "runs" / "claude-new"
    new.mkdir(parents=True)
    runner = Runner.__new__(Runner)
    runner.out = new
    runner.config = RunConfig(tasks=tasks, arms=["arm1"], model="m1",
                              resume_from="auto")

    source = runner.resume_source()
    assert source is not None and source.name == "claude-old"

    done = runner.finished_already(source, "arm1")
    assert sorted(done) == ["a__a-1", "b__b-2"]
    # The torn last line is dropped rather than crashing the resume — a job
    # killed mid-write always leaves one.
    assert "c__c-3" not in done

    # `auto` will not continue a DIFFERENT experiment: same list and model, or
    # the results file would be neither run's.
    runner.config = RunConfig(tasks=tasks, arms=["arm1"], model="other",
                              resume_from="auto")
    assert runner.resume_source() is None

    # And the batch job resumes by default, so a resubmission costs only what
    # was actually lost.
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")
    assert "--resume auto" in batch
    # It also re-derives the live nodes each pass and retries, rather than
    # launching once and losing everything to one bad node.
    assert "ATTEMPTS=${ATTEMPTS:-4}" in batch
    assert "is not reachable; leaving it out" in batch


def test_the_plain_agent_alarm_needs_an_attempt_that_actually_worked():
    """"Used no phronix tools" is only a finding if the attempt did something.

    A phronix arm that runs, produces a patch and never consults what it knows
    IS a serious state — its number is not a phronix number. But an attempt
    that produced no patch never reached that state: it failed before there was
    anything to record, and on a fresh task `search-skill` has already said
    there is nothing to retrieve.

    Raising it anyway turned one model failure into two findings, one of them
    pointing at this repository. Measured on a 30-task run: 11 of 11 "phronix
    unused" reports came from attempts that produced no patch, and they were
    the only pipeline faults the run had.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    at = source.index('"** this attempt used NO phronix "')
    block = source[at - 1200:at]

    # Gated on the attempt having produced something.
    assert "produced" in block
    assert "and produced:" in block
    # Read from disk via `_patch_text`. `Attempt` has no `patch` field, and
    # reading `attempt.patch` raised AttributeError on every evaluation turn
    # of every run before it was noticed — the same bug twice would be
    # careless.
    assert "_patch_text(" in block
    # Code lines only: the comment above it names `attempt.patch` precisely to
    # explain why it is not used.
    code = [l for l in block.splitlines() if not l.lstrip().startswith("#")]
    assert not any("attempt.patch" in l for l in code)

    from tests.benchmark.metrics import Attempt
    assert "patch" not in Attempt.__dataclass_fields__


def test_a_task_always_ends_a_pass_with_a_skill_even_when_nothing_worked(tmp_path, monkeypatch):
    """The skill must EXIST whether or not anything worked.

    It is what the next attempt looks up, what the next research pass reads
    before it starts, and what a later run finds. "Nothing worked" is a fact
    about the subject worth carrying, not an absence.

    Measured across one 300-task run: 356 research passes, 65 attempts that
    found a skill, and 489 that opened with "no skill covers this task;
    solving from scratch". Research was asked for a skill and the request was
    all that stood behind it — when a pass produced nothing, nothing noticed
    until the task had ended.

    Written by the HARNESS rather than by asking an agent again: a re-ask has
    the same failure mode as the ask, and existence is the one property that
    can be guaranteed without a model.
    """
    from tests.benchmark.arms import PhronixArm
    from tests.benchmark.isolation import _has_substance

    store = tmp_path / "store" / ".phronix"
    store.mkdir(parents=True)
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(store.parent))
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))

    arm = PhronixArm.__new__(PhronixArm)
    arm.arm_name = "claude-phronix"
    instance = {"instance_id": "matplotlib__matplotlib-25079",
                "repo": "matplotlib/matplotlib"}

    said = []
    name = arm.ensure_task_skill(instance, store, tmp_path / "task" / "attempt-1",
                                 on_call=said.append)
    assert name == "matplotlib-matplotlib-25079"
    assert any("opened" in line and "empty" in line for line in said), said

    written = list(store.rglob("SKILL.md"))
    assert len(written) == 1, written
    # Structurally real, so promotion keeps it rather than discarding it as an
    # empty shell — see `_has_substance`.
    assert _has_substance(written[0])

    # It must not claim knowledge it does not have: a later pass reads this
    # before deciding what to try.
    text = written[0].read_text()
    assert "Nothing is established" in text
    assert "untried" in text

    # Called again, it does not make a second one: one skill per task.
    again = arm.ensure_task_skill(instance, store, tmp_path / "task" / "attempt-1")
    assert again == name
    assert len(list(store.rglob("SKILL.md"))) == 1

    # And the runner asks for it after EVERY research pass, not only at the end.
    runner = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert runner.count("arm.ensure_task_skill(") == 2


def test_harness_supplied_files_are_capped_before_a_stage_reads_them(tmp_path):
    """Stay inside the model's window by not contributing to filling it.

    The models here are trained to 131072 and the CLI compacts at 100k — its
    floor — leaving ~31k for whatever the turn adds. One large file read can
    exceed that alone: measured on pytest-5495, the agent read
    `test_conftest.py, lines 1 to 2001` and the request came back
    `400 ContextWindowExceededError`, killing the attempt outright.

    The harness cannot cap what the AGENT chooses to read. It can stop handing
    it unbounded files: `conversation.md` is every turn in full, appended and
    never rewritten — correct for a durable record, and largest exactly when
    the context is tightest.
    """
    from tests.benchmark.arms import PhronixArm

    arm = PhronixArm.__new__(PhronixArm)

    small = tmp_path / "conversation-summary.md"
    small.write_text("x" * 5_000)
    assert arm.capped(small) == small          # under budget: handed as-is

    big = tmp_path / "conversation.md"
    big.write_text("HEAD-MARKER\n" + "y" * 60_000 + "\nTAIL-MARKER")
    trimmed = arm.capped(big)

    assert trimmed != big
    text = trimmed.read_text()
    assert len(text) <= arm.ATTACH_BUDGET_B + 200
    # Head AND tail: the head says what the task is and what was first tried,
    # the tail says what just failed. Cutting either loses more than the middle.
    assert "HEAD-MARKER" in text and "TAIL-MARKER" in text
    assert "elided from the middle" in text
    # The durable record is untouched.
    assert big.stat().st_size == 60_024

    # Research, which attaches the unabridged conversation, goes through it.
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    body = source[source.index("    def research_from_tracker("):]
    body = body[:body.index("\n    def ", 10)]
    assert "self.capped(p)" in body


def test_a_byte_the_harness_cannot_decode_costs_that_byte_not_the_try():
    """`text=True` decodes STRICTLY, and a repository under test has binary in it.

    One undecodable byte in the agent's stdout raised UnicodeDecodeError inside
    the read loop and took the whole try with it:

        attempt-void try 3 did not run (UnicodeDecodeError: 'utf-8' codec
        can't decode byte 0xac in position 7449808)
    """
    import subprocess

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    at = source.index("process = subprocess.Popen(launch")
    call = source[at:at + 400]
    assert 'errors="replace"' in call

    # The behaviour itself, so this is not only a spelling check.
    strict = subprocess.Popen(["printf", "\\xac"], stdout=subprocess.PIPE, text=True)
    with pytest.raises(UnicodeDecodeError):
        for _ in strict.stdout:
            pass
    lenient = subprocess.Popen(["printf", "\\xac"], stdout=subprocess.PIPE,
                               text=True, errors="replace")
    assert "".join(lenient.stdout) == "�"


def test_the_conversation_is_retrieved_in_turns_not_handed_over_whole(tmp_path, monkeypatch):
    """The record stays whole on disk; only the turn that is needed enters context.

    `conversation.md` is every turn in full, appended and never rewritten —
    right for a durable record, wrong to attach. It grows with the task and is
    largest exactly when the context is tightest, and attaching it is what
    produced `400 ContextWindowExceededError` mid-attempt on pytest-5495,
    killing a try that had already run forty steps.

    Head-and-tail truncation bounds the size but decides for the reader which
    parts matter. Retrieval inverts that: the stage asks.
    """
    import json

    from phronix.mcp_tools import register_all
    from phronix.mcp_tools.tools import conversation_service

    (tmp_path / "conversation.md").write_text(
        "## turn 1 — attempt\nTried widening the dtype in concat.py\n\n"
        "## turn 2 — evaluate\ntarget 0/2, regressions 0\n\n"
        "## turn 3 — attempt\nTried casting in dtypes.py instead\n")

    class Recorder:
        def __init__(self):
            self.fn = {}

        def tool(self):
            def register(function):
                self.fn[function.__name__] = function
                return function
            return register

    # Registered with the rest, so the server actually serves them.
    served = Recorder()
    assert not register_all(served)["failed"]
    assert {"conversation_outline", "conversation_turn",
            "conversation_search"} <= set(served.fn)

    mcp = Recorder()
    conversation_service.register(mcp)
    monkeypatch.setenv("PHRONIX_TASK_DIR", str(tmp_path))

    outline = json.loads(mcp.fn["conversation_outline"]())
    assert [t["n"] for t in outline["turns"]] == [1, 2, 3]
    # The outline is the CHEAP read: titles and sizes, no bodies.
    assert all("text" not in t for t in outline["turns"])

    # `-1` is what a revision pass wants: it says what just failed.
    assert "dtypes.py" in json.loads(mcp.fn["conversation_turn"](-1))["text"]

    # And the question a revision pass actually has — has this been tried?
    hit = json.loads(mcp.fn["conversation_search"]("dtypes casting"))
    assert [t["n"] for t in hit["turns"]] == [3]

    # Without a task it reports unavailable rather than guessing: a
    # conversation from the WRONG task is worse than none, because nothing in
    # the text says which task it belongs to.
    monkeypatch.delenv("PHRONIX_TASK_DIR")
    assert json.loads(mcp.fn["conversation_outline"]())["status"] == "unavailable"

    # The harness sets it per stage, and research no longer attaches the file.
    arms = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert 'env["PHRONIX_TASK_DIR"]' in arms
    body = arms[arms.index("    def research_from_tracker("):]
    body = body[:body.index("\n    def ", 10)]
    attach = body[body.index("attachments = ["):body.index(") if p.is_file()]")]
    assert "conversation.md" not in attach
    assert "conversation-summary.md" in attach


def test_reuse_actually_turns_freshness_off():
    """`--reuse` produced a from-scratch run that reported itself as fresh.

    The CLI derives freshness from ONE flag — `fresh=not args.no_fresh` — so
    `--fresh` is accepted and ignored, and omitting it leaves fresh True.
    `run-benchmark.sh --reuse` cleared `--fresh` and passed nothing, which
    changes nothing.

    Measured on the reuse half of a fresh/reuse pair, which is the entire
    comparison the pair exists to make: its header read `fresh` and its
    manifest recorded `fresh = True`. The run could not read anything the
    fresh run had learned, so "is it learning?" had no way to be answered yes.
    """
    from tests.benchmark.cli import build_parser

    parser = build_parser()
    assert parser.parse_args(["run"]).no_fresh is False            # fresh
    assert parser.parse_args(["run", "--fresh"]).no_fresh is False  # still fresh
    assert parser.parse_args(["run", "--no-fresh"]).no_fresh is True

    script = Path("scripts/run-benchmark.sh").read_text(encoding="utf-8")
    assert 'FRESHNESS="--no-fresh"' in script
    # And the banner says which mode plainly, rather than echoing a flag whose
    # meaning is the opposite of how it reads.
    assert "reuse (reads what earlier runs learned)" in script


def test_a_resumed_result_round_trips_as_dataclasses_not_dicts():
    """Resume must rebuild attempts, not hand JSON dicts back to the dataclass.

    `TaskResult(**row)` type-checks and runs, and is wrong: `attempts` comes
    back from JSON as plain dicts, so the field promises `Attempt`s and holds
    dicts. Nothing notices until `to_dict` calls `asdict` on one, which is
    inside `append_result` — the first thing resume does. The mix30-reuse run
    died there sixty seconds in, both arms, `asdict() should be called on
    dataclass instances`, zero tasks attempted.

    So the round trip is the assertion: a row written by `to_dict` must come
    back through `from_dict` as something `to_dict` can write again.
    """
    from tests.benchmark.metrics import Attempt, TaskResult

    original = TaskResult(
        instance_id="django__django-13551",
        repo="django/django",
        arm="claude-phronix",
        order=3,
        attempts=[Attempt(index=1), Attempt(index=2)],
    )
    row = json.loads(json.dumps(original.to_dict()))

    rebuilt = TaskResult.from_dict(row)
    assert [type(a) for a in rebuilt.attempts] == [Attempt, Attempt]
    assert rebuilt.instance_id == original.instance_id
    assert rebuilt.order == original.order
    # The bug in one line: this is what append_result does next.
    assert rebuilt.to_dict()["instance_id"] == "django__django-13551"

    # Derived columns are written but are properties, so reading must drop
    # them rather than raise on an unexpected keyword.
    assert "resolved" in row
    assert TaskResult.from_dict(row).instance_id == original.instance_id


def test_a_reuse_run_credits_skills_learned_in_earlier_runs():
    """The reuse half of a fresh/reuse pair must be able to SEE the fresh half.

    `Ledger.classify` drops any skill it has no creation record for, and the
    ledger is built per run. So a skill the fresh run wrote and the reuse run
    loads reads as `created is None` and is dropped, and `skills_reused` comes
    back 0 for the whole arm — reported as a result rather than as blindness.
    That is exactly the number the pair is run to produce.

    Framework skills must still be excluded: they shipped, they were not
    learned, and counting them would make every arm look like it was learning
    from its first task.
    """
    from tests.benchmark.runner import Ledger

    ledger = Ledger()
    ledger.record_inherited("pylint-discover-files-ignore", "pylint-dev/pylint")
    ledger.record_inherited("sympy-degree-padding")        # origin unknown
    ledger.record_creation("learned-here", 0, "pallets/flask")

    out = ledger.classify(
        ["pylint-discover-files-ignore", "sympy-degree-padding",
         "learned-here", "phronix-diagnosis-pivot"],
        order=4, repo="pallets/flask")

    # Inherited skills count as reuse from the very first task, and are also
    # reported separately: reuse WITHIN a run and reuse ACROSS runs are
    # different claims.
    assert "pylint-discover-files-ignore" in out["reused"]
    assert "sympy-degree-padding" in out["reused"]
    assert out["inherited"] == ["pylint-discover-files-ignore",
                                "sympy-degree-padding"]
    # Learned earlier in THIS run: reuse, but not prior-run reuse.
    assert "learned-here" in out["reused"]
    assert "learned-here" not in out["inherited"]
    # Never recorded as created by anything: the framework's own. Excluded.
    assert "phronix-diagnosis-pivot" not in out["reused"]

    # Known different repo is cross-repo; UNKNOWN origin is not, or every
    # carried skill would be reported as generalising across repositories.
    assert out["cross_repo"] == ["pylint-discover-files-ignore"]


def test_an_inherited_skill_counts_as_reuse_for_the_very_first_task():
    """Order 0 is a real task, so the inherited sentinel must sit below it."""
    from tests.benchmark.runner import Ledger

    ledger = Ledger()
    ledger.record_inherited("from-the-fresh-run")
    assert ledger.INHERITED < 0
    assert ledger.classify(["from-the-fresh-run"], order=0, repo="x")["reused"]


def test_the_session_registry_separates_fresh_from_reuse(tmp_path, monkeypatch):
    """Which tools a run was SERVED is the only thing that separates the modes.

    Capabilities accumulate on disk across every run that ever executed, so
    "which tools exist" answers the same for a fresh run and a reuse one. The
    distinction is which of them this process was allowed to see, and that is
    held in memory for the life of the MCP server rather than written down —
    so it cannot be confused with the disk state it is describing.

    Without this the modes were indistinguishable from inside a run, which is
    how `--reuse` ran for weeks while seeding nothing and reporting nothing
    wrong.
    """
    import phronix.capabilities as caps

    monkeypatch.setenv(caps.FRESH_ENV, "1")
    assert caps.session_only() is True
    monkeypatch.setenv(caps.FRESH_ENV, "")
    assert caps.session_only() is False

    # The registry is in memory, and a skill this run wrote counts as its own.
    monkeypatch.setattr(caps, "_SESSION_AUTHORED", {}, raising=False)
    caps.note_session_authored("a-thing-this-run-wrote")
    assert "a-thing-this-run-wrote" in caps.session_authored()
    # A copy, so a caller cannot edit the registry by holding it.
    caps.session_authored()["smuggled"] = "x"
    assert "smuggled" not in caps.session_authored()

    # Under --fresh, a task ANSWER from an earlier run is not served, while
    # this session's own work still is.
    monkeypatch.setenv(caps.FRESH_ENV, "1")
    answer = tmp_path / "capabilities" / caps.TASK_CAPABILITY_DIR / "sympy-19254"
    answer.mkdir(parents=True)
    carried = answer / "apply_mignotte_fix.py"
    carried.write_text("def register(mcp):\n    pass\n", encoding="utf-8")
    mine = tmp_path / "capabilities" / "a-thing-this-run-wrote.py"
    mine.write_text("def register(mcp):\n    pass\n", encoding="utf-8")

    monkeypatch.setattr(caps, "capability_files",
                        lambda: {p.name: p for p in
                                 (tmp_path / "capabilities").rglob("*.py")},
                        raising=False)
    import phronix.layers as layers_module
    monkeypatch.setattr(layers_module, "capability_files",
                        lambda: {str(p.relative_to(tmp_path / "capabilities")): p
                                 for p in (tmp_path / "capabilities").rglob("*.py")})
    monkeypatch.setattr(layers_module, "which_layer", lambda p: "bundled")

    visible = caps.visible_files()
    names = {Path(n).stem for n in visible}
    assert "a-thing-this-run-wrote" in names
    # The earlier run's answer is filtered: this is what --fresh means.
    assert "apply_mignotte_fix" not in names


def test_a_fresh_run_writes_what_it_learned_even_though_it_reads_nothing():
    """Always promoted, never discoverable under `--fresh`.

    Writing and reading are different questions, and conflating them cost the
    fresh/reuse pair its meaning. `--fresh` and `--no-carry` both empty
    `carry_root`, promotion was gated on `carry_root`, so a from-scratch run
    contributed nothing to the runs after it. Measured on the 5-task pair: the
    fresh half learned 10 answers, none reached the carry root, and the reuse
    half would have inherited only what runs from days earlier left behind.

    So the write is unconditional, and the read filter decides who sees it.
    """
    from tests.benchmark.runner import RunConfig

    fresh = RunConfig(tasks=["a"], fresh=True, carry_root="",
                      promote_root="/carry/.phronix")
    # Reads nothing...
    assert fresh.carry_root == ""
    # ...writes anyway.
    assert fresh.promote_root == "/carry/.phronix"

    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    # The promotion block keys on the write path, not the read path.
    assert "promote_into = self.config.promote_root or self.config.carry_root" in source
    assert "if promote_into:" in source
    assert "promote_store(store_root, Path(promote_into))" in source
    # Seeding still keys on the READ path, or --fresh would stop meaning
    # anything at all.
    assert "seed_store(store_root, Path(self.config.carry_root))" in source


def test_a_promoted_capability_is_always_filed_where_fresh_can_hide_it():
    """`--fresh` filters on the directory, so a loose promotion defeats it.

    `visible_files` hides a bundled capability only when its path contains
    `tasks/`. A capability promoted loose into `capabilities/` is therefore
    served to every from-scratch run for good. Measured: 195 sat at the top of
    the packaged layer, `probe_fix_max_to_sum_powers_filter` among them, which
    applies one benchmark task's fix outright.
    """
    from tests.benchmark.isolation import (FILED_SUBDIRS, SOLUTION_SUBDIR,
                                           TOOL_SUBDIR, UNATTRIBUTED_SLUG)

    source = Path("tests/benchmark/isolation.py").read_text(encoding="utf-8")
    # Every directory the filter recognises, not just one: naming only
    # `tasks/` made a correctly-filed `capabilities/skills/` solution look
    # unfiled, and promotion moved it to `unattributed/`.
    assert set(FILED_SUBDIRS) == {"skills", "tools", "tasks"}
    # Re-filed on the way in, rather than trusted to have been filed right.
    assert 'if kind == "capabilities" and not _already_filed(relative):' in source
    assert SOLUTION_SUBDIR == "skills" and TOOL_SUBDIR == "tools"
    # Filed together under one name rather than guessed into somebody's task:
    # a wrong guess hands one task another task's answer.
    assert UNATTRIBUTED_SLUG == "unattributed"

    from phronix.capabilities import LEARNED_DIRS
    # The writer and the read filter must agree, or the filter looks in a
    # place nothing is written to.
    assert set(LEARNED_DIRS) == set(FILED_SUBDIRS)


def test_a_finished_run_is_not_resumed_into():
    """`auto` continues a job that DIED, not an experiment that ended.

    The docstring always said "did not finish"; the code never tested it. So a
    deliberate re-run of the same task list picked up the previous run's rows
    — measured on the 5-task pair: eight results for five tasks, with
    `psf__requests-3362` recorded both resolved and unresolved, and carried
    rows showing `promoted=0` beside the new ones showing `promoted=11`. Two
    experiments in one file, reported as one.

    `report.json` is written once the arms return, so it is the test.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    resume = source[source.index("    def resume_source(self)"):]
    resume = resume[:resume.index("\n    def ", 10)]
    assert 'if (candidate / "report.json").is_file():' in resume
    assert "continue" in resume


def test_the_resume_skip_is_not_shadowed_by_the_seed_list():
    """Two locals called `carried` in one function, and the second won.

    The resume recorded a result for every finished task and then ran them all
    again, because the skip tested an instance id for membership in a list of
    SEEDED FILENAMES. Both were named `carried`, thirty lines apart, same
    scope. Nothing raised; the run just held two rows per task.

    Named for what they hold, so the collision cannot come back.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert "already_done: Dict[str, Any] = {}" in source
    assert "if instance_id in already_done:" in source
    # The seed list keeps the old name, and the two must not meet again.
    assert "carried = seed_store(" in source
    assert "if instance_id in carried:" not in source


def test_task_results_have_exactly_one_from_dict():
    """A second definition thirty lines down silently replaced the first.

    Python keeps the LAST definition, so the careful one was dead code and the
    live one was `Attempt(**a)` — which raises TypeError the moment a row
    carries a column this build does not know, which is exactly what a resume
    reads.
    """
    from tests.benchmark.metrics import Attempt, TaskResult

    source = Path("tests/benchmark/metrics.py").read_text(encoding="utf-8")
    assert source.count("    def from_dict(") == 1

    # And the survivor is the tolerant one, on both levels.
    row = json.loads(json.dumps(
        TaskResult(instance_id="x", attempts=[Attempt(index=1)]).to_dict()))
    row["a_column_from_a_newer_build"] = 1
    row["attempts"][0]["an_attempt_column_too"] = 2
    rebuilt = TaskResult.from_dict(row)
    assert [type(a) for a in rebuilt.attempts] == [Attempt]
    rebuilt.to_dict()


def test_the_layout_is_checked_rather_than_assumed():
    """A solution that is correct and misfiled is a solution nothing reuses.

    Every filing failure so far has been silent: the write succeeds and the
    next run's lookup returns nothing. Answers written loose where `--fresh`
    could not hide them; a slug nested inside itself; a diagnosis under a name
    no reader asks for. So the layout is a tool the research agent calls on its
    own work, and every issue names the move that fixes it.
    """
    import tempfile

    from phronix.mcp_tools.tools import layout_service

    class _Mcp:
        def __init__(self): self.tools = {}
        def tool(self, *a, **k):
            def take(fn): self.tools[fn.__name__] = fn; return fn
            return take

    mcp = _Mcp()
    layout_service.register(mcp)
    check = mcp.tools["layout_check"]

    root = Path(tempfile.mkdtemp())
    caps = root / "capabilities"
    (caps / "skills" / "good-task").mkdir(parents=True)
    (caps / "skills" / "good-task" / "SKILL.md").write_text(
        "# s\nsee [notes](notes.md)\n", encoding="utf-8")
    (caps / "skills" / "good-task" / "notes.md").write_text("linked", encoding="utf-8")
    (caps / "tools" / "pytest").mkdir(parents=True)
    (caps / "tools" / "pytest" / "run_subset.py").write_text("x", encoding="utf-8")
    clean = json.loads(check(root=str(root)))
    assert clean["ok"] is True, clean["issues"]

    # Now each wrong shape, and each must be named.
    (caps / "loose_tool.py").write_text("x", encoding="utf-8")
    (caps / "skills" / "no-skill").mkdir(parents=True)
    (caps / "skills" / "good-task" / "orphan.md").write_text("x", encoding="utf-8")
    (caps / "tools" / "uncategorised.py").write_text("x", encoding="utf-8")
    dirty = json.loads(check(root=str(root)))
    assert dirty["ok"] is False
    problems = {i["path"]: i for i in dirty["issues"]}
    assert "capabilities/loose_tool.py" in problems
    assert "capabilities/skills/no-skill/" in problems
    assert "capabilities/skills/good-task/orphan.md" in problems
    assert "capabilities/tools/uncategorised.py" in problems
    # Every issue says what to DO, or it is a complaint rather than a check.
    assert all(i["fix"] for i in dirty["issues"])
    # The linked helper is not flagged; the unlinked one is.
    assert "capabilities/skills/good-task/notes.md" not in problems

    # `research/` is the same shape, keyed on what was SEARCHED FOR.
    assert layout_service.TREES == ("capabilities", "research")


def test_a_repeated_phase_is_folded_once_with_a_count():
    """Three runs of one stage are one fact, not three.

    The fold handed the tracker `attempt, attempt, attempt` and it wrote the
    finding down three times. A later attempt then cannot tell three
    approaches from one approach tried three times — which is the question it
    opens the record to answer.
    """
    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    fold = source[source.index("    def _fold_events(self"):]
    fold = fold[:fold.index("\n    def ", 10)]
    # Collapsed where the events still have structure, not asked of a model.
    assert "counted[key] = counted.get(key, 0) + 1" in fold
    assert 'f"{name} x{n} ({costs[name]})"' in fold

    # And the rule is in the tracker's SKILL, not restated in the prompt —
    # the prompt is a pointer and is length-capped for exactly that reason.
    skill = Path(
        "src/phronix/.phronix/skills/phronix-task-tracker/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "Nothing appears twice" in skill


def test_research_is_filed_by_subject_and_filtered_like_everything_else(
        isolated_layers, monkeypatch):
    """`research/` has the same shape as `capabilities/`, keyed differently.

    A subject outlives the task that raised it — "how does this project
    discover test files" is asked by every task in the repository — so filing
    it under the first task to ask makes it findable by that one alone. The
    record sits beside the skill it produced, so a subject is one directory
    rather than a file here and a skill elsewhere.

    And the isolation still holds: a fresh run sees none of it.
    """
    from phronix import research

    _session(monkeypatch, "old-run")
    research.add_approach("discover-files", "normalise-paths",
                          "normalise before the check", hypothesis="paths differ")
    research.sync_session("old-run")

    common = isolated_layers["store"] / "research"
    assert (common / "skills" / "discover-files" / "record.json").is_file()
    # Never `research/record.json`: every subject's record shares a filename,
    # so folding on the name alone would collapse a whole session into one
    # file with each subject overwriting the last.
    assert not (common / "record.json").exists()

    # Fresh sees nothing; reuse sees the subject.
    _session(monkeypatch, "new-run", reuse=False)
    assert research.list_topics() == []
    _session(monkeypatch, "new-run", reuse=True)
    assert "discover-files" in research.list_topics()


def test_a_record_written_by_an_older_run_is_still_read_and_still_written_to():
    """The flat `<subject>.json` layout keeps working.

    A research corpus is not worth invalidating over a directory name, and a
    session that INHERITED a flat record has to keep writing to that file
    rather than starting a second copy beside it under the new layout — two
    records for one subject is the split-read failure, not a migration.
    """
    from phronix import research

    source = Path("src/phronix/research.py").read_text(encoding="utf-8")
    # Both readers and both writers go through the same candidate list.
    assert "def _record_candidates(" in source
    write = source[source.index("def _write_path("):]
    write = write[:write.index("\ndef ", 10)]
    assert "for candidate in _record_candidates(slug, root):" in write
    assert "return candidate" in write

    # And a flat glob would have stopped seeing anything, silently.
    assert "def _records_under(" in source
    assert 'found += sorted(root.glob("*.json"))' in source


def test_the_research_record_is_validated_against_what_a_later_run_needs():
    """A record is not a diary; it is read by the next attempt on this subject.

    Every field checked here exists because its absence cost something. A
    metric with no `measurement` is a prediction being read as a result —
    measured live, two runs of one task, one asserting 1.0 for an approach it
    never ran. An approach with no `hypothesis` cannot be falsified, so
    nothing it "showed" counts. A `chosen` that is not in `approaches` is a
    plan pointing at nothing.
    """
    from phronix.mcp_tools.tools.schema_service import _check

    bad = {
        "topic": "t", "slug": "t",
        "approaches": [
            {"name": "a", "summary": "s"},
            {"name": "a", "summary": "s", "hypothesis": "h",
             "metrics": {"correctness": 1.0}},
            {"name": "c", "summary": "s", "hypothesis": "h",
             "status": "confirmed"},
        ],
        "plan": [{"kind": "deterministic", "title": "do it"},
                 {"kind": "judgement"}],
        "chosen": "not-there",
    }
    issues = _check(bad)
    problems = {(i["where"], i["problem"]) for i in issues}
    assert ("approaches[a]", "no `hypothesis`") in problems
    assert ("approaches[a]", "two approaches share a name") in problems
    assert ("approaches[a]", "has metrics but no `measurement`") in problems
    assert ("approaches[c]", "status `confirmed` with nothing behind it") in problems
    assert ("chosen", "`not-there` is not one of the approaches") in problems
    assert ("fom", "no figure of merit") in problems
    assert ("plan[0]", "a deterministic step with no capability") in problems
    # Every issue names a MOVE, or it is a complaint rather than a check.
    assert all(i["fix"] for i in issues)

    # A complete record raises nothing, or the check is noise and gets ignored.
    good = {
        "topic": "t", "slug": "t",
        "approaches": [{"name": "a", "summary": "s", "hypothesis": "h",
                        "metrics": {"c": 1.0}, "measurement": "ran the suite"}],
        "plan": [{"kind": "deterministic", "title": "x", "capability": "probe_x"}],
        "chosen": "a", "fom": {"metric": "c"},
    }
    assert _check(good) == []

    # And research is told to run both checks before it finishes.
    skill = Path(
        "src/phronix/.phronix/skills/phronix-task-research/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "research_validate()" in skill and "layout_check()" in skill


def test_a_capability_is_filed_by_who_it_is_for():
    """Three homes, and the difference is who the tool is FOR.

    A categorised tool is shared work and the next kind-of-work like this one
    calls it. A tool bound to one task is part of that task's ANSWER and
    belongs beside the solution it implements, where the reader who loads the
    skill already is. Filing it at `tools/<task-slug>/` was the worst of both:
    shelved with the shared tools, findable only by the one task, so the
    catalogue grew without anything gaining a tool it could use.
    """
    import os
    import tempfile

    from phronix import capabilities

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        src = "def register(mcp):\n    return %r\n"
        shared = capabilities.new("probe_run_subset", "run a subset",
                                  source=src % "a", category="tests")
        bound = capabilities.new("apply_mignotte_fix", "apply the fix",
                                 source=src % "b", topic="sympy__sympy-19254")
        neither = capabilities.new("probe_read_region", "read a region",
                                   source=src % "c")
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    def where(result):
        text = Path(result["file"]).as_posix()
        return text[text.index("capabilities/"):]

    assert where(shared) == "capabilities/tools/tests/probe_run_subset.py"
    # Beside its solution, not shelved under tools/<task>/.
    assert where(bound) == (
        "capabilities/skills/sympy-sympy-19254/apply_mignotte_fix.py")
    # Honest about not knowing, and still somewhere the filter can see.
    assert where(neither) == "capabilities/tools/general/probe_read_region.py"


def test_the_learner_writes_to_the_kind_of_work_not_to_itself():
    """Measured across every run: the learner only ever wrote to its own skills.

    `wrote lesson phronix-learning-capture` and `wrote lesson
    phronix-learning-reconcile`, run after run, and not one capability in any
    of them. Every lesson went into the description of the learner's own
    method, where no task will look for it — the reader searching for how to
    parse subprocess output does not search the learner.
    """
    skill = Path(
        "src/phronix/.phronix/skills/phronix-learning-capture/SKILL.md"
    ).read_text(encoding="utf-8")

    # The target is the kind of work, and its own skills are named as wrong.
    assert "phronix-learning-capture" in skill and "phronix-learning-reconcile" in skill
    assert "The skill you were HANDED is not the skill you write to" in skill
    # Creating the kind-of-work skill is the normal first case, not a fallback.
    assert "an absent skill is the normal state" in skill

    # And a tool it builds carries the category, which it is uniquely able to
    # supply: the kind of work is exactly what it was handed.
    assert 'category="<the kind of work you were handed>"' in skill
    assert "capabilities/tools/tests/probe_" in skill


def test_research_fills_the_research_tree_and_everything_else_fills_capabilities():
    """Two trees, two writers, and the reader sees both.

    `capabilities/` is what a task NEEDED: its solution, and the tools the
    learner builds from what repeats across tasks. `research/` is what was
    SEARCHED FOR, and a subject outlives the task that raised it — "how does
    this project discover test files" is asked by every task in the repo, so
    filing it under the first task to ask makes it findable by that one alone.

    The tree is set by the HARNESS around the research stage, not inferred
    from the skill's name: an agent picks the name, and no naming convention
    has survived contact with one yet.
    """
    import os
    import tempfile

    from phronix import skills
    from phronix.layers import skill_dirs

    root = tempfile.mkdtemp()
    was = {k: os.environ.get(k) for k in
           ("PHRONIX_PROJECT_ROOT", skills.SKILL_TREE_ENV)}
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        os.environ[skills.SKILL_TREE_ENV] = ""
        skills.write_block("sympy-19254", "instruction", "Pad it", "b",
                           description="the task's own answer")
        os.environ[skills.SKILL_TREE_ENV] = "research"
        skills.write_block("how-discovery-works", "instruction", "Walk it", "b",
                           description="how this project discovers test files")
        os.environ[skills.SKILL_TREE_ENV] = ""

        assert (Path(root) / ".phronix" / "capabilities" / "skills"
                / "sympy-19254" / "SKILL.md").is_file()
        assert (Path(root) / ".phronix" / "research" / "skills"
                / "how-discovery-works" / "SKILL.md").is_file()

        # One lookup finds both: a reader must not have to know which tree a
        # run happened to file a skill under.
        found = skill_dirs()
        assert "sympy-19254" in found
        assert "how-discovery-works" in found
    finally:
        for key, value in was.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    # And the harness is what sets it, only around research.
    arms = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert ('env["PHRONIX_SKILL_TREE"] = "research" if phase == "research" else ""'
            in arms)


def test_the_first_pass_of_a_batch_never_resumes_someone_elses_run():
    """Resume is for a pass that lost a node, not for pass one.

    On pass 1 there is nothing of ours to continue, and `auto` will happily
    continue somebody ELSE's unfinished run. Measured: a fresh 5-task batch
    picked up a cancelled run's five rows, skipped every task, and wrote a
    report over results it had never measured — its trace held one line, and
    the numbers looked entirely plausible.
    """
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")
    assert 'RESUME=()' in batch
    assert '[ "$pass" -gt 1 ] && RESUME=(--resume auto)' in batch
    # And no unconditional `--resume auto` survives on the run lines.
    for line in batch.splitlines():
        if "run-group.sh" in line or "--parallel" in line:
            assert "--resume auto" not in line, line


def test_the_filing_checks_are_run_by_the_harness_not_requested():
    """An instruction to self-check competes with finishing, and finishing wins.

    `layout_check` and `research_validate` were wired into the research skill
    and called ZERO times in every run that had them. So the harness runs them
    — deterministic, free when the work is already right, and the same
    post-hoc check plus one re-ask already used when a diagnosis lands in an
    empty skill.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    research = source[source.index("    def research_from_tracker(self"):]
    research = research[:research.index("\n    def ", 10)]
    # Run at the end of research, before the result is returned.
    assert "self._enforce_checks(" in research

    enforce = source[source.index("    def _enforce_checks(self"):]
    enforce = enforce[:enforce.index("\n    @staticmethod", 10)]
    # One re-ask, then report. A check that loops is a budget with no bound.
    assert enforce.count("self.standalone_stage(") == 1
    assert "left = self._check_findings(store_root)" in enforce
    assert "problem(s) remain" in enforce

    # Both checks, against this run's own store.
    findings = source[source.index("    def _check_findings("):]
    findings = findings[:findings.index("\n    def ", 10)]
    assert "from phronix.mcp_tools.tools.layout_service import _issues_for" in findings
    assert "from phronix.mcp_tools.tools.schema_service import _check" in findings
    # A check that cannot run is not a fault: it must never cost the run.
    assert findings.count("except Exception:") == 2

    # And every line handed back names the move, not just the fault.
    assert "-> {issue['fix']}" in findings
    assert "{issues}" in Arm.CHECK_PROMPT
    assert "do not research anything new" in Arm.CHECK_PROMPT


def test_the_learner_states_a_tool_verdict_for_every_finding():
    """Zero tools across every run, with capability_new available throughout.

    `I4` said *prefer a tool where the procedure is deterministic*, which
    leaves the default at prose — and prose is always cheaper in the moment.
    Not one finding was ever judged deterministic. A preference nothing
    records is a preference nothing follows.

    The verdict does not force a tool. It forces the choice to be made once
    per finding and be visible, so "no tool was ever right" and "the question
    was never asked" stop looking identical.
    """
    skill = Path(
        "src/phronix/.phronix/skills/phronix-learning-capture/SKILL.md"
    ).read_text(encoding="utf-8")

    assert "TOOL: <name>" in skill and "NO-TOOL: <why not>" in skill
    # Declining is legitimate and cheap to say, or the rule becomes pressure
    # to build tools nobody needs.
    assert "is a complete reason" in skill
    assert "built **zero** tools" in skill
    # It goes into the observation stream, where reconcile can generalise it.
    assert 'research_observe(topic="learning")' in skill


def test_the_inventory_counts_every_filed_directory_not_one_of_them(tmp_path):
    """The same silent failure, twice, in the same function.

    First it listed only FILES under `capabilities/`, so the 30-task run
    reported `skills_created = []` for all 29 tasks while its store gained 32
    task answers. That was fixed by naming `tasks/`. Then solutions moved to
    `capabilities/skills/` and the count went to zero again — a run reporting
    `created=0` with `promoted=20` in the row beside it.

    Reading the list of filed directories, rather than naming one, is what
    stops a third time.
    """
    from tests.benchmark.isolation import FILED_SUBDIRS, store_inventory

    store = tmp_path / ".phronix"
    (store / "capabilities" / "skills" / "psf-requests-3362").mkdir(parents=True)
    (store / "capabilities" / "tools" / "pytest").mkdir(parents=True)
    # The pre-flattening layout nests one level deeper and must still count.
    (store / "capabilities" / "tasks" / "old-slug" / "old-name").mkdir(parents=True)

    seen = set(store_inventory(store)["capabilities"])
    assert "skills/psf-requests-3362" in seen
    assert "tools/pytest" in seen
    assert "tasks/old-slug/old-name" in seen

    # Derived from the shared constant, so a new filed directory is counted
    # the day it is added rather than the day someone notices it is not.
    source = Path("tests/benchmark/isolation.py").read_text(encoding="utf-8")
    assert "for sub in FILED_SUBDIRS:" in source
    assert set(FILED_SUBDIRS) == {"skills", "tools", "tasks"}


def test_a_pair_runs_both_halves_in_one_allocation():
    """Two jobs cannot run a fresh/reuse pair honestly.

    The reuse half must start from what the fresh half learned, so it has to
    run after it — and a second job queues. On a contended queue that means
    the halves land hours apart on different nodes, or the second never runs:
    measured, a chained reuse job sat in DEPEND until its fresh half's
    allocation expired, and a separately-submitted pair was cancelled before
    the second half started, three times over.

    One allocation, two ordered phases, the fleet deployed once and shared.
    """
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")

    assert "--pair)     PAIR=1; shift;;" in batch
    # Ordered and not interchangeable: reuse reads what fresh promoted.
    assert 'PHASES="fresh reuse"' in batch
    assert "for phase in $PHASES; do" in batch
    # The phase decides the flag, so the fresh half cannot inherit --reuse.
    assert 'if [ "$phase" = "reuse" ]; then REUSE=1; else REUSE=""; fi' in batch
    # Each phase gets its own run name, built from the ORIGINAL name — not
    # from the previous phase's, which would compound.
    assert "BASE_NAME=$NAME" in batch
    assert 'NAME="${BASE_NAME}-${phase}"' in batch
    # And the flag reaches the job that actually runs inside the allocation.
    assert "${PAIR:+--pair}" in batch
    # A reuse phase with no room measures nothing; the fresh result still
    # counts, so the pair stops rather than starting a half it cannot finish.
    assert "stopping after the $phase phase" in batch


def test_the_task_solution_lands_in_capabilities_even_when_research_wrote_it():
    """Routing by stage alone filed solutions where nothing looks for them.

    The research stage writes BOTH: the task's solution, and whatever it
    learned about the subject. Only the second belongs in `research/`. Filed
    under `research/`, a solution is invisible to the next attempt, which asks
    `capabilities/` for the task it is about to attempt — the retrieval-first
    path that the whole tracked loop depends on.

    The harness names the task's skill, so the exception is exact rather than
    a guess about which names look task-shaped.
    """
    import os
    import tempfile

    from phronix import skills

    root = tempfile.mkdtemp()
    keys = ("PHRONIX_PROJECT_ROOT", skills.SKILL_TREE_ENV, skills.TASK_SKILL_ENV)
    was = {k: os.environ.get(k) for k in keys}
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        # Mid-research: the tree says research, one name is exempt.
        os.environ[skills.SKILL_TREE_ENV] = "research"
        os.environ[skills.TASK_SKILL_ENV] = "psf-requests-3362"
        skills.write_block("psf-requests-3362", "instruction", "t", "b",
                           description="the task's own answer")
        skills.write_block("how-iter-content-decodes", "instruction", "t", "b",
                           description="a subject worth keeping")
    finally:
        for key, value in was.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    store = Path(root) / ".phronix"
    assert (store / "capabilities" / "skills" / "psf-requests-3362"
            / "SKILL.md").is_file()
    assert (store / "research" / "skills" / "how-iter-content-decodes"
            / "SKILL.md").is_file()

    arms = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert 'env["PHRONIX_TASK_SKILL"] = self.task_skill_name(' in arms


def test_a_procedure_written_as_prose_is_reported_as_a_missing_tool():
    """Preferring a tool leaves the default at prose, and prose always wins.

    Across every run to date the system wrote lessons steadily and built ZERO
    tools, with `capability_new` available throughout. A fenced block in a
    solution is commands someone will run: a tool costs one call, while prose
    is read, interpreted and re-acted-on by every task that loads the skill —
    differently each time, which is where drift comes from.

    Flagged only when nothing executable sits beside it, so a solution that
    already built its tool is left alone and the check stays quiet on good
    work.
    """
    import tempfile

    from phronix.mcp_tools.tools.layout_service import _issues_for

    root = Path(tempfile.mkdtemp())
    prose = root / "capabilities" / "skills" / "prose-only"
    prose.mkdir(parents=True)
    (prose / "SKILL.md").write_text(
        "# s\n\nRun this:\n\n```bash\npytest -k foo\n```\n", encoding="utf-8")
    built = root / "capabilities" / "skills" / "has-tool"
    built.mkdir(parents=True)
    (built / "SKILL.md").write_text("# s\n\n```bash\npytest -k foo\n```\n",
                                    encoding="utf-8")
    (built / "run_it.py").write_text("def register(mcp): pass\n", encoding="utf-8")
    facts = root / "capabilities" / "skills" / "just-facts"
    facts.mkdir(parents=True)
    (facts / "SKILL.md").write_text("# s\n\nThe constructor raises TypeError.\n",
                                    encoding="utf-8")

    flagged = {i["path"] for i in _issues_for(root, "capabilities")}
    assert "capabilities/skills/prose-only/SKILL.md" in flagged
    # Already built its tool: silent.
    assert not any("has-tool" in p for p in flagged)
    # A fact is not a procedure: silent.
    assert not any("just-facts" in p for p in flagged)


def test_a_skill_the_attempt_proved_it_loaded_counts_as_retrieved():
    """The reuse metric read a log the attempt agent never writes to.

    `retrievals.jsonl` is written by the MCP server, and the attempt agent's
    `skill_load` never reaches it — which the `skill-use` event already works
    around by checking the transcript. That workaround set
    `attempt.skill_loaded` and stopped there, so the metrics went on reading
    the empty log.

    Measured on the first reuse run that ever seeded: `sphinx-8595` passed on
    try 1 where fresh had needed 3, the trace said ``loaded
    `sphinx-doc-sphinx-8595` and worked from it``, and the row said
    retrieved=0 reused=0 prior-run=0 — the one number the fresh/reuse pair
    exists to produce, reported as zero on a task that had just demonstrated
    reuse.
    """
    from tests.benchmark.metrics import Attempt, TaskResult
    from tests.benchmark.runner import Ledger

    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert 'proven = [str(getattr(a, "recalled_skill", "") or "")' in source
    # Unioned into `retrieved` BEFORE classification, or the ledger never
    # sees it and prior-run reuse stays zero.
    assert source.index("retrieved.append(name)") < source.index(
        "classified = ledger.classify(retrieved, order, repo)")

    # And the classification then credits it as prior-run reuse.
    result = TaskResult(instance_id="sphinx-doc__sphinx-8595")
    result.attempts = [Attempt(index=1)]
    result.attempts[0].recalled_skill = "sphinx-doc-sphinx-8595"
    result.attempts[0].skill_loaded = True

    retrieved = []
    for attempt in result.attempts:
        if attempt.skill_loaded and attempt.recalled_skill:
            retrieved.append(attempt.recalled_skill)
    assert retrieved == ["sphinx-doc-sphinx-8595"]

    ledger = Ledger()
    ledger.record_inherited("sphinx-doc-sphinx-8595")
    out = ledger.classify(retrieved, order=0, repo="sphinx-doc/sphinx")
    assert out["reused"] == ["sphinx-doc-sphinx-8595"]
    assert out["inherited"] == ["sphinx-doc-sphinx-8595"]


def test_the_filing_is_checked_once_more_before_anything_is_promoted():
    """The research-time check cannot cover the whole task.

    The final try's solution and everything the learn stage writes land after
    research has run for the last time. Measured: four solutions carried a
    procedure as prose with no tool beside them and not one was re-asked,
    because every one was written after the last check.

    Before promotion nothing else will write, so what passes there is exactly
    what the next run inherits.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    gate = source.index("arm._enforce_checks(")
    promote = source.index("promoted = promote_store(store_root, Path(promote_into))")
    assert gate < promote, "the check must run BEFORE promotion, not after"
    # Unfixed problems are said out loud rather than swallowed: they become
    # the next run's inheritance.
    assert "the next run inherits" in source
    # And a check that cannot run never costs the task its promotion.
    tail = source[gate:promote]
    assert "except Exception as exc:" in tail


def test_a_duplicate_tool_is_caught_across_categories():
    """The duplicate check globbed a directory nothing writes to any more.

    `capabilities/*.py` matched nothing once tools moved into
    `tools/<category>/` and task fixes into `skills/<TaskName>/`, so the check
    silently stopped checking. One run wrote `flask_cli_routes.py`,
    `add_flask_cli_routes.py` and `flask_cli_routes_fix.py` across three
    categories — the same procedure four times, each of them then needing to
    be maintained, verified and chosen between.
    """
    import os
    import tempfile

    from phronix import capabilities

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        body = ("def register(mcp):\n    @mcp.tool()\n"
                "    def run(where: str) -> str:\n        return where\n")
        first = capabilities.new("flask_cli_routes", "list routes",
                                 source=body, category="flask")
        # Same body, different name, DIFFERENT category — the shape that got
        # through, four times, in one run.
        second = capabilities.new("add_flask_cli_routes", "list routes again",
                                  source=body, category="flask-cli")
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    assert first["status"] == "ok"
    assert second["status"] == "duplicate"
    # The existing name comes back, so the caller can just use it.
    assert second["existing"][0]["name"] == "flask_cli_routes"

    source = Path("src/phronix/capabilities.py").read_text(encoding="utf-8")
    assert 'for path in sorted(directory.rglob("*.py")):' in source


def test_a_skill_that_learned_something_stops_saying_it_has_not():
    """The placeholder was meant to be replaced, and nothing enforced it.

    A task skill is opened with a "nothing is established" rule so that a
    skill always EXISTS — the next pass needs somewhere to write, and
    existence is the one property obtainable without a model.

    Measured on `sphinx-doc-sphinx-8595`: the carried skill held the exact
    diff that had made the task PASS, under `I1`, and kept alongside it
    `R1 — Nothing is established about this subject yet` plus the description
    "What is known about sphinx-doc__sphinx-8595. Nothing yet." The next run
    loaded that skill, ran 44 steps and 2.7M tokens, and produced no patch.

    A skill that hands over the answer and twice tells its reader nothing is
    known is worse than either alone — and the description is the main
    retrieval signal.
    """
    import os
    import tempfile

    from phronix import skills
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    # A name no real layer holds. `write_block` resolves through the
    # layers, so a skill of the same name in the packaged layer is found
    # and written to instead — which made this test pass or fail on
    # whether an unrelated run had polluted the checkout.
    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        arm = Arm.__new__(Arm)
        store = Path(root) / ".phronix"
        skills.write_block("a-subject-no-layer-holds", "rule",
                           Arm.PLACEHOLDER_TITLE, "nothing yet",
                           description="What is known about it. Nothing yet.")

        # An EMPTY skill keeps its placeholder: that is what makes it valid.
        assert arm.retire_placeholder(store, "a-subject-no-layer-holds") is False

        skills.write_block("a-subject-no-layer-holds", "instruction",
                           "Handle empty __all__ in autodoc", "return False, []")
        assert arm.retire_placeholder(store, "a-subject-no-layer-holds") is True

        text = (Path(skills.existing_home("a-subject-no-layer-holds"))
                / "SKILL.md").read_text(encoding="utf-8")
        assert Arm.PLACEHOLDER_TITLE not in text
        # The description names what is known, rather than denying it.
        assert "Nothing yet" not in text
        assert "Handle empty __all__" in text
        # Idempotent: nothing left to retire on a second pass.
        assert arm.retire_placeholder(store, "a-subject-no-layer-holds") is False
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    # And it runs before promotion, so the next run inherits the corrected one.
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert source.index("arm.retire_placeholder(") < source.index(
        "promoted = promote_store(store_root, Path(promote_into))")


def test_an_empty_skill_is_a_miss_not_a_hit():
    """Every task is guaranteed a skill, so existing says nothing about content.

    `open_task_skill` writes a valid but empty skill so a later pass has
    somewhere to write. Offering one back announces "found X — the attempt
    solves with it" over a file whose only content is "nothing is established
    about this subject yet", and then scores the attempt as having DECLINED to
    use it.

    Measured on the reuse run: two of five carried skills were placeholders,
    and both tasks were logged `was given it and never loaded it` — a reuse
    failure recorded against the agent for ignoring an empty file.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    lookup = source[source.index('tracer.begin("search-skill"'):]
    lookup = lookup[:lookup.index("retrieved_before", 10)] if "retrieved_before" in lookup[10:] else lookup[:4000]

    assert "if attempt.recalled_skill and not arm._skill_has_content(" in source
    # Cleared BEFORE the trace announces a hit, or the announcement lies.
    assert source.index("not arm._skill_has_content(") < source.index(
        "the attempt solves with it")


def test_what_already_failed_reaches_the_attempt_not_only_research():
    """Trying something new each time is the point, and it starts at try 1.

    `feedback.md` says what the LAST TRY got wrong and dies with the run.
    `LESSONS.md` is where a failed approach is written down so it is not paid
    for twice — and it was attached to research and to nothing else. The
    attempt, which is the thing that would retry a dead approach, never saw
    it: a reuse run whose carried skill named the exact fix still spent 44
    steps rediscovering the problem, with the earlier run's pitfalls sitting
    unread beside it.
    """
    import tempfile

    from tests.benchmark.arms import ClaudePhronixArm as Arm

    store = Path(tempfile.mkdtemp()) / ".phronix"
    home = store / "capabilities" / "skills" / "sphinx-doc-sphinx-8595"
    home.mkdir(parents=True)
    (home / "SKILL.md").write_text("# s\n", encoding="utf-8")
    (home / "LESSONS.md").write_text(
        "# Lessons\n\n## Pitfalls\n\n### P1 — returning True, [] still "
        "documents members\n\n" + "x" * 300, encoding="utf-8")
    assert Arm._lessons_for(store, "sphinx-doc-sphinx-8595") is not None

    # An EMPTY lessons file is worse than none: it costs an attachment and
    # tells the reader nothing has been ruled out, which is a claim rather
    # than an absence.
    (home / "LESSONS.md").write_text("# Lessons\n", encoding="utf-8")
    assert Arm._lessons_for(store, "sphinx-doc-sphinx-8595") is None
    assert Arm._lessons_for(store, "") is None

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # Attached to the ATTEMPT, before the plan note, on every try.
    assert "lessons = (self._lessons_for(store_root, for_task)" in source
    # Keyed on the task's CANONICAL skill, not on whether the lookup hit: a
    # task whose skill is empty is exactly the one with nothing to reuse and
    # everything to avoid repeating.
    assert "for_task = self.task_skill_name(self.research_topic(instance))" in source
    assert "files += self.attachments([lessons])" in source
    assert source.index("prompt += self.LESSONS_NOTE") < source.index(
        "prompt += self.PLAN_NOTE.format(")
    # A ruled-out approach is a RESULT, not a forbidden idea — saying so is
    # what stops the note being read as a rule to obey blindly.
    assert "it is a result" in Arm.LESSONS_NOTE
    assert "Do not spend a step re-deriving one of them" in Arm.LESSONS_NOTE


def test_skill_content_is_judged_in_the_layout_that_is_actually_written():
    """The one check separating "a skill exists" from "a skill says something".

    It globbed `capabilities/tasks/*/<skill>/SKILL.md` — the pre-flattening
    path — so a skill at `capabilities/skills/<skill>/`, where everything is
    written now, was invisible to it. And it counted the PLACEHOLDER as
    content, so every task looked covered from the moment it started:
    sympy-19254 carried a placeholder-only skill into a reuse run and the
    lookup announced "found ... — the attempt solves with it".
    """
    import os
    import tempfile

    from phronix import skills
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        store = Path(root) / ".phronix"
        skills.write_block("placeholder-only", "rule", Arm.PLACEHOLDER_TITLE,
                           "none", description="d")
        skills.write_block("has-content", "instruction", "Return False, []",
                           "do it", description="d")
        skills.write_block("both", "rule", Arm.PLACEHOLDER_TITLE, "none",
                           description="d")
        skills.write_block("both", "instruction", "Return False, []", "do it")

        # The scaffold alone is not substance.
        assert Arm._skill_has_content(store, "placeholder-only") is False
        # Real content, in the layout writes actually use.
        assert Arm._skill_has_content(store, "has-content") is True
        # The placeholder does not disqualify a skill that also says something.
        assert Arm._skill_has_content(store, "both") is True
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # Both trees and both layouts, derived rather than named one at a time.
    assert 'for tree in ("capabilities", "research")' in source
    assert 'for sub in ("skills", "tasks")' in source


def test_a_partial_result_records_both_halves_into_the_skill():
    """A verdict at 1 of 2 is a pass and a fail at once.

    Only the failing half was ever carried forward. `feedback.md` was taught
    to say both — and it dies with the run, so the next RUN inherited "this
    task failed" and nothing about the half already working. A later attempt,
    told the task failed, then rewrites the code that was already correct.

    Written by the harness because it is not a judgement: the evaluator knows
    exactly which named tests passed. One block, replaced each time, so the
    skill says where the task IS rather than accumulating a diary.
    """
    import os
    import tempfile

    from phronix import skills
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        arm = Arm.__new__(Arm)
        store = Path(root) / ".phronix"
        skills.write_block("sympy-19254", "rule", Arm.PLACEHOLDER_TITLE,
                           "none", description="d")
        verdict = {
            "fail_to_pass_passing": ["test_mignotte_bound_poly"],
            "fail_to_pass_failing": ["test_mignotte_bound_multivar"],
            "regressions": ["test_factor_list"],
        }
        assert arm.record_partial_progress(store, "sympy-19254", verdict, 2)
        text = (Path(skills.existing_home("sympy-19254"))
                / "SKILL.md").read_text(encoding="utf-8")

        # What WORKS, named, and protected from being rewritten.
        assert "Already passing (1 of 2)" in text
        assert "test_mignotte_bound_poly" in text
        assert "Do not rewrite the code that makes these pass" in text
        # What is left, named, and scoped: the whole task is not left.
        assert "Still failing (1)" in text
        assert "test_mignotte_bound_multivar" in text
        # And what an earlier attempt broke, which says an approach was too broad.
        assert "test_factor_list" in text

        # Replaced, not appended: the skill says where the task IS.
        verdict["fail_to_pass_passing"] = ["test_mignotte_bound_poly",
                                           "test_mignotte_bound_multivar"]
        verdict["fail_to_pass_failing"] = []
        arm.record_partial_progress(store, "sympy-19254", verdict, 3)
        text = (Path(skills.existing_home("sympy-19254"))
                / "SKILL.md").read_text(encoding="utf-8")
        # Once as a heading (the index lists it too, which is not a copy).
        assert text.count(f"### R2 — {Arm.PROGRESS_TITLE}") <= 1
        assert text.count(Arm.PROGRESS_TITLE) == 2
        assert "Already passing (2 of 2)" in text
        # The superseded measurement is GONE, not stacked beneath it.
        assert "Measured after try 3" in text
        assert "Measured after try 2" not in text
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    # Recorded after EVERY verdict, not only a final one.
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert "arm.record_partial_progress(" in source
    assert source.index("last_verdict = attempt.verdict") < source.index(
        "arm.record_partial_progress(")

    # And the agent is told the half it must supply: WHY the failing half fails.
    skill = Path(
        "src/phronix/.phronix/skills/phronix-task-research/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "A partial result is evidence twice" in skill


def test_the_placeholder_is_retired_in_the_store_the_run_actually_writes():
    """`existing_home` resolves against the asking process's layers.

    The runner's layers are the checkout's, not the store the run writes to,
    so the retirement looked in the wrong tree and silently did nothing:
    sympy-19254 gained a real instruction, kept "Nothing is established about
    this subject yet" beside it, and was promoted that way into the carry root
    for the next run to read.

    Both questions — where does this skill live, and does it say anything —
    are asked about the same file and must not disagree about where it is.
    """
    import os
    import tempfile

    from phronix import skills
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    arm = Arm.__new__(Arm)
    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        # Built the way the code builds it, so the fixture cannot drift from
        # the real file shape.
        skills.write_block("sympy-sympy-19254", "rule", Arm.PLACEHOLDER_TITLE,
                           "none", description="What is known. Nothing yet.")
        skills.write_block("sympy-sympy-19254", "instruction",
                           "Fix dup_zz_mignotte_bound", "raise the bound")
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    store = Path(root) / ".phronix"
    home = store / "capabilities" / "skills" / "sympy-sympy-19254"
    assert (home / "SKILL.md").is_file()

    # Found in the STORE, with no layer lookup involved — the environment
    # variable is restored above, so a layer lookup here would find nothing.
    assert arm._skill_home_in(store, "sympy-sympy-19254") == home
    assert arm._skill_home_in(store, "not-here") is None

    assert arm.retire_placeholder(store, "sympy-sympy-19254") is True
    text = (home / "SKILL.md").read_text(encoding="utf-8")
    assert Arm.PLACEHOLDER_TITLE not in text
    assert "Fix dup_zz_mignotte_bound" in text
    assert "Nothing yet" not in text

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert "home = self._skill_home_in(store_root, skill)" in source


def test_a_runner_failure_with_a_patch_gets_one_more_try():
    """The blame check reads the file the traceback NAMES.

    An import-time break shows up in the importer, not in the patched module.
    astropy-14182 patched `io/ascii/rst.py`; collection died in
    `io/ascii/tests/test_rst.py` with `'NoneType' object has no attribute
    'index'`; and the blame check — correctly, on its own terms — said the
    agent never touched that file. The task was written off after one try,
    42 steps and $2.53, with its retry budget untouched.

    One more try, not the whole ceiling. The protection being relaxed is real:
    sympy-24066 spent three attempts against a suite that could not execute
    and produced three byte-identical diffs. A second consecutive runner
    failure still aborts, so the relaxation costs one attempt, not a task.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")

    # Counted per task, and a second failure still aborts.
    assert "runner_failures = 0" in source
    assert "runner_failures < 1" in source
    assert "runner_failures += 1" in source

    # Only when the attempt actually produced a patch: an empty attempt
    # against a dead suite is the case the abort exists for.
    guard = source[source.index("elif (_patch_text(workdir"):]
    guard = guard[:guard.index("else:", 10)]
    assert '_patch_text(workdir / f"attempt-{attempt_index}").strip()' in guard

    # The abort is still reachable, and still says why.
    assert "the test runner never started, so no attempt at this" in source
    assert 'tracer.event("ABORT", result.stopped_early)' in source

    # Order: the self-inflicted branch is tried FIRST, since a patch that
    # broke a file it touched is the clearest failed attempt there is.
    assert source.index("attempt.verdict[\"broke_testbed\"] = blamed") < source.index(
        "runner_failures += 1")


def test_the_progress_block_is_written_into_the_run_store():
    """Third instance of one confusion: a path resolved for the wrong process.

    `write_block` resolves a skill's home through the layers of whoever calls
    it, and the runner's layers are the checkout's. So the progress block
    landed in `src/phronix/.phronix` — the packaged layer — while the trace
    said `recorded 0 passing / 1 still failing into the skill` and the run's
    own copy never gained it. After `retire_placeholder` and
    `_skill_has_content`, this is the third place that mistake was made.
    """
    import os
    import tempfile

    from phronix import skills
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        skills.write_block("t", "instruction", "Use iter_lines", "b",
                           description="d")
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    # The layers no longer point anywhere near this store: a layer-based
    # write would go somewhere else entirely, which is the bug.
    store = Path(root) / ".phronix"
    arm = Arm.__new__(Arm)
    target = store / "capabilities" / "skills" / "t" / "SKILL.md"

    assert arm.record_partial_progress(
        store, "t", {"fail_to_pass_passing": [], "regressions": [],
                     "fail_to_pass_failing": ["test_a"]}, 1) is True
    assert "What has been achieved" in target.read_text(encoding="utf-8")

    assert arm.record_partial_progress(
        store, "t", {"fail_to_pass_passing": ["test_a"], "regressions": [],
                     "fail_to_pass_failing": []}, 2) is True
    text = target.read_text(encoding="utf-8")
    # Replaced, and the superseded measurement is gone.
    assert "Measured after try 2" in text and "Measured after try 1" not in text
    assert "Already passing (1 of 1)" in text
    # One heading, and the label is STABLE across rewrites — a reference to it
    # must not silently come to mean different content next try.
    assert text.count(f"### R1 — {Arm.PROGRESS_TITLE}") == 1
    # The other blocks survive.
    assert "### I1 — Use iter_lines" in text


def test_a_passing_run_records_the_diff_that_passed():
    """A skill written from a passing run described the fix instead of carrying it.

    `psf-requests-3362` PASSED and recorded "Replace uses of
    `iter_content(..., decode_unicode=True)` with `iter_lines(...)`" — advice,
    with no diff, no file and no line. The next reuse run had to re-derive the
    patch from that description, and failed.

    Across five tasks the correlation was exact. `sphinx-doc-sphinx-8595` is
    the only skill holding a real diff, and the only task that passes in every
    reuse run; the four prose-only skills produce coin flips. So the harness
    writes the patch, because it is not a judgement — what passed is known
    exactly. The agent's job is why it works, not reconstructing what it was.
    """
    import os
    import tempfile

    from phronix import skills
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        skills.write_block("psf-requests-3362", "instruction",
                           "Use iter_lines", "advice only", description="d")
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    store = Path(root) / ".phronix"
    arm = Arm.__new__(Arm)
    target = store / "capabilities" / "skills" / "psf-requests-3362" / "SKILL.md"
    patch = ("--- a/requests/models.py\n+++ b/requests/models.py\n"
             "@@ -1,3 +1,3 @@\n-    return chunk\n+    return chunk.decode(enc)\n")

    assert arm.record_winning_patch(store, "psf-requests-3362", patch, 1) is True
    text = target.read_text(encoding="utf-8")
    # The diff itself, verbatim — file, hunk and both sides.
    assert "requests/models.py" in text
    assert "chunk.decode(enc)" in text
    assert "@@" in text
    # And it says not to re-derive it, which is the whole point.
    assert "do not re-derive it from scratch" in text

    # Written again, the block is replaced rather than duplicated.
    assert arm.record_winning_patch(store, "psf-requests-3362", patch, 2) is True
    text = target.read_text(encoding="utf-8")
    assert text.count(f"### I2 — {Arm.SOLUTION_TITLE}") == 1
    assert "### I1 — Use iter_lines" in text

    # An empty patch records nothing: a skill claiming a fix it does not hold
    # is worse than one that admits it has none.
    assert arm.record_winning_patch(store, "psf-requests-3362", "   ", 3) is False

    # Only on a PASS, and before the partial-progress block.
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")
    assert "and attempt.resolved):" in source
    assert source.index("arm.record_winning_patch(") < source.index(
        "arm.record_partial_progress(")


def test_a_block_title_never_carries_its_own_label():
    """Blocks render as `### I1 — Title`, and agents write that back as a title.

    The store then holds both `I1 — Use iter_lines` and
    `I4 — I1 — Use iter_lines`: the same point twice, and the copy is
    invisible to every same-point check because its title no longer matches.
    Three of sixteen carried skills had doubled that way, and the doubling
    survives promotion — psf-requests-3362 reached a reuse run carrying five
    instructions where it had three, two of them duplicates.

    Stripped rather than rejected: the content is right and only the title is
    wrong, and rejecting it would lose the block.
    """
    import os
    import tempfile

    from phronix import skill_schema, skills

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        skills.write_block("a-subject-no-layer-holds", "instruction",
                           "Use iter_lines", "body", description="d")
        # The same point, written back with its rendered label in the title.
        skills.write_block("a-subject-no-layer-holds", "instruction",
                           "I1 — Use iter_lines", "better body")
        home = Path(root) / ".phronix" / "capabilities" / "skills" \
            / "a-subject-no-layer-holds"
        titles = [str(b.get("title") or "")
                  for b in skill_schema.parse_skill(home).get("blocks") or []]
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    # No title carries a label, so the same-point check can still see them.
    assert not any(t.startswith("I1 —") for t in titles), titles
    assert "Use iter_lines" in titles

    source = Path("src/phronix/skills.py").read_text(encoding="utf-8")
    assert 'title = re.sub(r"^\\s*[A-Z]{1,2}\\d+\\s*[—–-]\\s*"' in source


def test_an_edit_is_refused_until_the_task_s_skill_has_been_read():
    """Retrieval was never the failure; reading was.

    The store found the skill and handed it over on every single attempt, and
    the agent declined to open it in 8 of 14 — including on the task that had
    PASSED from that very skill in an earlier run. A skill that is merely
    available competes with getting started, and getting started wins.

    Refused, not injected. Injecting the content would measure "does the
    answer help" instead of "can it use a store", and those are different
    experiments. And it fires ONCE: a gate that can block a whole attempt is
    a gate that can lose one.
    """
    import json
    import os
    import subprocess
    import sys
    import tempfile

    from phronix import hooks

    root = Path(tempfile.mkdtemp())
    hooks.install_hook_scripts(root)
    guard = root / ".claude" / "hooks" / hooks.GUARD_SCRIPT_NAME
    assert guard.is_file()
    state = root / "state"

    def decide(payload, wanted="psf-requests-3362"):
        env = dict(os.environ, PHRONIX_REQUIRED_SKILL=wanted,
                   PHRONIX_GUARD_STATE=str(state))
        run = subprocess.run([sys.executable, str(guard)],
                             input=json.dumps(payload), capture_output=True,
                             text=True, env=env)
        assert run.returncode == 0, run.stderr
        if not run.stdout.strip():
            return "allow"
        return json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"]

    edit = {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}}

    assert decide(edit) == "deny"
    state.unlink(missing_ok=True)

    # Reading it satisfies the gate, however it was read.
    assert decide({"tool_name": "mcp__phronix__skill_load",
                   "tool_input": {"name": "psf-requests-3362"}}) == "allow"
    assert decide(edit) == "allow"
    state.unlink(missing_ok=True)

    # Nothing else is gated: a stage that is not editing must not be refused.
    assert decide({"tool_name": "Bash", "tool_input": {"command": "ls"}}) == "allow"
    state.unlink(missing_ok=True)
    # No skill named — the bare arm, and research — is never gated.
    assert decide(edit, wanted="") == "allow"
    state.unlink(missing_ok=True)
    # Fires once, then proceeds either way.
    decide(edit)
    assert decide(edit) == "allow"

    # The harness names the skill, and only for the attempt.
    arms = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert 'env["PHRONIX_REQUIRED_SKILL"] = (' in arms
    assert 'if phase in ("", "attempt") else ""' in arms


def test_the_mechanical_faults_in_a_skill_are_repaired_not_just_reported():
    """A check that names a mechanical fault for someone else to fix is ignored.

    Three of the five things `solution_check` reports need no judgement: a
    title carrying the label the renderer adds, two blocks making one point,
    and a description that says nothing. Across the live corpus those were 10
    of 35 issues, and every one of them is a rewrite of content that is
    already correct.

    The other two must NOT be faked. A skill with no diff needs the patch that
    passed; one with nothing established needs a run to establish something.
    Inventing either would be worse than reporting it.
    """
    import os
    import tempfile

    from phronix import skills
    from phronix.mcp_tools.tools.solution_service import check_skill, repair_skill

    root = tempfile.mkdtemp()
    was = os.environ.get("PHRONIX_PROJECT_ROOT")
    os.environ["PHRONIX_PROJECT_ROOT"] = root
    try:
        skills.write_block("a-subject-no-layer-holds", "instruction",
                           "Use iter_lines", "the short body",
                           description="Nothing yet.")
    finally:
        if was is None:
            os.environ.pop("PHRONIX_PROJECT_ROOT", None)
        else:
            os.environ["PHRONIX_PROJECT_ROOT"] = was

    home = (Path(root) / ".phronix" / "capabilities" / "skills"
            / "a-subject-no-layer-holds")
    # Hand-corrupt it the way a run does: the rendered label copied into a
    # title, which the same-point merge can no longer see as a duplicate.
    text = (home / "SKILL.md").read_text(encoding="utf-8")
    text = text.replace(
        "### I1 — Use iter_lines",
        "### I1 — Use iter_lines\n\nbody\n\n### I2 — I1 — Use iter_lines")
    text = text.replace("| `I1` | Instructions | Use iter_lines |",
                        "| `I1` | Instructions | Use iter_lines |\n"
                        "| `I2` | Instructions | I1 — Use iter_lines |")
    (home / "SKILL.md").write_text(text, encoding="utf-8")

    kinds = {i["problem"] for i in check_skill(home)}
    assert any("carries its own label" in k for k in kinds)

    changed = repair_skill(home)
    assert changed, "nothing was repaired"
    fixed = (home / "SKILL.md").read_text(encoding="utf-8")
    # The label is out of the title, and the duplicate it hid is merged away.
    assert "I1 — Use iter_lines" not in fixed.replace("### I1 — Use iter_lines", "")
    assert fixed.count("Use iter_lines |") == 1
    # And the description now names what the skill covers.
    assert "Nothing yet" not in fixed
    assert "Use iter_lines" in fixed

    # Idempotent: a repaired skill needs no second pass.
    assert repair_skill(home) == []

    # What it must never invent.
    remaining = {i["problem"] for i in check_skill(home)}
    assert any("carries no diff" in k for k in remaining), \
        "a missing patch must still be reported, not fabricated"


def test_the_skill_is_repaired_before_it_is_promoted():
    """A run corrupts its own skills as it writes them.

    An agent reads the rendered `### I1 — Title` and writes a block titled
    `I1 — Title`, which the same-point merge can no longer see as a duplicate.
    Repaired by hand once, the very next run put it back — three of sixteen
    carried skills, and psf-requests-3362 reached a reuse run holding five
    instructions where it had three, two of them copies competing with its own
    diff.

    So the repair runs in the pipeline, at promotion: the moment a fault stops
    being this run's problem and becomes every later run's.
    """
    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")

    assert "from phronix.mcp_tools.tools.solution_service import repair_skill" in source
    assert "fixed = repair_skill(home) if home else []" in source

    # Before promotion, or the corrupted copy is what everything inherits.
    assert source.index("repair_skill(home)") < source.index(
        "promoted = promote_store(store_root, Path(promote_into))")
    # And before the placeholder retirement, which re-renders the same file:
    # repairing after it would leave the repair unwritten.
    assert source.index("repair_skill(home)") < source.index(
        "arm.retire_placeholder(store_root")
    # A repair that cannot run never costs the task its promotion.
    window = source[source.index("repair_skill(home)"):]
    assert "except Exception as exc:" in window[:600]


def test_the_code_review_reporter_is_denied_to_every_agent():
    """A tool whose output is a report is a way to finish without a patch.

    `ReportFindings` takes a list of defects and returns them. An agent told
    to fix a bug reaches for it, reports what it found, and stops — having
    answered a question nobody asked, and having satisfied itself that it
    finished.

    Measured on a whole run: all five tasks called `ReportFindings` on try 1
    and made ZERO edits between them. `git diff` was empty in every checkout
    and the harness recorded "agent produced no patch" five times, which reads
    as a model that could not solve the task. It is a benchmark that scores a
    diff; nothing that finishes without one should be reachable.
    """
    from tests.benchmark.arms import ClaudePhronixArm as Arm

    arm = Arm.__new__(Arm)
    assert Arm.OFF_TASK_TOOLS == ("ReportFindings",)

    # The UNRESTRICTED solve agent is the one that reached for it, so scoping
    # this to restricted agents would miss the case it exists for.
    plain = Arm._denial_flags(arm, "")[1]
    assert "ReportFindings" in plain

    # And still denied alongside the schema-breaking ones, in ONE flag —
    # Claude Code keeps only the last `--disallowedTools`.
    assert "Artifact" in plain and "RemoteTrigger" in plain
    assert Arm._denial_flags(arm, "").count("--disallowedTools") == 1


def test_an_attempt_that_described_a_change_is_asked_to_make_it():
    """Not a model that cannot solve the task — one that answered another.

    Measured on flask-5063: ten turns, $1.00, three `Skill` calls and ZERO
    edit tools, exiting `subtype: success` with "Here's a concise plan for the
    required changes: 1. Validate `name` in `Blueprint.__init__` — insert a
    check right after...". It knew the file, the function and the change, and
    described them instead of making them.

    This is an intervention, and it is worth naming as one: it moves the arm
    from "can it solve the task" toward "can it solve the task when told to
    actually edit". The BASELINE gets the same prompt on the same trigger, so
    the arms stay comparable — an intervention applied to one arm is a
    difference between the arms, not a measurement.
    """
    from tests.benchmark.runner import Runner

    source = Path("tests/benchmark/runner.py").read_text(encoding="utf-8")

    # Only when there is NO diff: an attempt that produced something has
    # answered the question, however badly.
    assert 'if not (outcome.patch or "").strip():' in source
    assert "outcome = self._ask_for_the_edit(" in source

    prompt = Runner.EDIT_PROMPT
    # It must name the failure exactly, or it reads as generic encouragement.
    assert "You did not change any file" in prompt
    assert "judged on a diff" in prompt
    # And rule out the three shapes that read as finishing.
    assert "do not summarise it, do not plan it" in prompt
    # A genuine no-change answer stays available, or the re-ask forces a patch
    # where none is warranted.
    assert "no change is warranted" in prompt

    body = source[source.index("    def _ask_for_the_edit(self"):]
    body = body[:body.index("\n    def ", 10)]
    # Once. A loop here is a budget with no bound.
    assert body.count("arm.generate(") == 1
    # It can only ADD a diff, never lose one.
    assert "return outcome" in body
    assert 'if (getattr(again, "patch", "") or "").strip():' in body
    # The cost of both halves belongs to the attempt that spent it.
    assert 'for field in ("steps", "tokens_input", "tokens_output", "cost_usd")' in body

    # Every arm accepts it, so the baseline is treated identically.
    arms = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    assert arms.count("extra_prompt: str = \"\"") == 3


def test_the_packaged_store_is_git_tracked():
    """`.phronix` unanchored ignores the store that ships in the wheel.

    Without a leading slash the pattern matches `.phronix` at ANY depth, so
    `src/phronix/.phronix/` was ignored along with the repo-root scratch
    layer — and every skill and record promoted into it was invisible to git.
    The comment directly above the pattern said the opposite, and was believed
    for a whole session: `git status` stayed clean while eight files
    accumulated on disk.

    The point of keeping the store under the package is that a finding
    survives a clone. Ignored, it survives exactly as long as one checkout,
    which is the failure the layout was chosen to prevent.
    """
    import subprocess

    text = Path(".gitignore").read_text(encoding="utf-8")
    # Anchored to the repo root, not floating.
    assert "\n/.phronix\n" in text
    assert "\n.phronix\n" not in text

    # And the packaged store is genuinely visible to git.
    for tree in ("capabilities", "research"):
        path = f"src/phronix/.phronix/{tree}"
        if not Path(path).is_dir():
            continue
        ignored = subprocess.run(
            ["git", "check-ignore", path],
            capture_output=True, text=True).returncode
        assert ignored != 0, f"{path} is ignored by git"


def test_two_concurrent_runs_cannot_share_a_directory_or_kill_each_other():
    """Two batches, one machine, and each destroyed the other.

    The run directory was named to the SECOND, so two batches that started a
    run in the same second got the same directory and wrote their manifests,
    traces and results over each other. `top` reported one job's model and
    mode for the other's run, which is how it was noticed:
    `claude-0901-175544` appears in both batch logs with different runner pids.

    And every run swept stray agents with `kill.sh` before starting, which is
    right when a run starts alone and catastrophic when one does not: a hosted
    Haiku batch started at 17:53 and the gpt-oss batch running since 14:44
    lost its runner two minutes later. A stray agent left behind is cheap; a
    killed run is an hour of GPU time.
    """
    script = Path("scripts/run-benchmark.sh").read_text(encoding="utf-8")

    # Unique per process, not merely per second.
    assert 'OUT=$BENCH/runs/$TAG-$(date +%m%d-%H%M%S)-$$' in script

    # The sweep is skipped while another runner is alive.
    assert 'if pgrep -f "benchmark.cli run" >/dev/null 2>&1; then' in script
    assert "another benchmark runner is active; not sweeping stray agents" in script
    # And the guard has to come BEFORE the kill, not after it.
    assert script.index('pgrep -f "benchmark.cli run"') < script.index(
        '"$SCRIPTS/kill.sh"')


def test_a_hosted_run_is_bounded_by_the_account_not_the_nodes():
    """`Not logged in · Please run /login` is what an exhausted quota looks like.

    `run-group.sh` drops a subscription run to one task at a time because the
    constraint is the account's allowance rather than dollars or GPUs — and
    that guard only fires when nobody passed `--parallel`, which `bench-batch`
    always does. So `--hosted --parallel 30` put 60 task-arms on the
    subscription at once, the five-hour allowance went in minutes, and every
    agent exited rc=1 reporting a login failure.

    That message cost an hour of diagnosis: network reachable, credentials
    symlinked correctly into the private home, eight concurrent agents fine by
    hand, and the harness's exact command authenticating on the same node. The
    only thing wrong was how many were asked for at once.
    """
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")
    group = Path("scripts/run-group.sh").read_text(encoding="utf-8")

    # Gated on the SUBSCRIPTION, not on hosted: a site gateway is hosted too
    # and has its own capacity, so capping it to 4 makes a 30-task run crawl
    # for a reason that does not apply to it.
    assert 'if [ -n "$HOSTED" ] && [ -z "$GATEWAY" ] \\' in batch
    assert '&& [ "$PARALLEL" -gt "${HOSTED_PARALLEL_CAP:-4}" ]; then' in batch
    assert '[ "$arg" = "--provider" ] && GATEWAY=1' in batch
    assert "PARALLEL=${HOSTED_PARALLEL_CAP:-4}" in batch
    # Capped, not forced to 1: thirty tasks one at a time does not finish in a
    # working day either.
    assert "Capped rather than forced to 1" in batch
    # The cap has to be applied BEFORE the value is forwarded to the job.
    assert batch.index("HOSTED_PARALLEL_CAP") < batch.index(
        '"$0" --size "$SIZE" --index "$INDEX" --parallel "$PARALLEL"')

    # And a subscription run uses the account's own auth, not the site gateway
    # that --base-url defaults to.
    assert 'EXTRA+=(--base-url "")' in group


def test_a_model_sweep_can_keep_its_carry_roots_apart():
    """Six models chained through one store is a transfer experiment.

    Model two reads what model one promoted, so every later model looks better
    partly because the earlier ones ran — which is worth measuring on purpose
    and misleading by accident. `PHRONIX_CARRY` names the store; the default
    is the shared one, so a single run behaves as before.
    """
    group = Path("scripts/run-group.sh").read_text(encoding="utf-8")
    batch = Path("scripts/bench-batch.sh").read_text(encoding="utf-8")

    # One place decides, and both the read and the write use it.
    assert 'CARRY_STORE=${PHRONIX_CARRY:-$PBENCH/carry}/.phronix' in group
    assert 'CARRY=(--no-carry --promote-root "$CARRY_STORE")' in group
    assert 'CARRY=(--carry-root "$CARRY_STORE")' in group
    # No path left hardcoded, or half a sweep shares a store.
    assert "$PBENCH/carry/.phronix" not in group

    # Exported rather than passed: run-group is invoked from more than one
    # branch here, and a flag added to one of them is exactly that bug.
    assert '--carry)    CARRY_NAME="$2"; shift 2;;' in batch
    assert 'export PHRONIX_CARRY="$PBENCH/carry-$CARRY_NAME"' in batch
    # And it reaches the job that actually runs inside the allocation.
    assert '${CARRY_NAME:+--carry "$CARRY_NAME"}' in batch


def test_only_the_subscription_is_paced():
    """Hosted is the wrong question; having a usage WINDOW is the right one.

    The Claude account has a five-hour window that, once rejected, fails every
    agent for the rest of it, so its draw has to be spaced. A site gateway is
    hosted too and has none of that — its own key, its own capacity, no
    allowance to exhaust. Pacing it cost wall-clock for a reason that did not
    apply: measured on a livai run, 196 `waiting for one of 8 agent slots` in
    the first minute, against a gateway that had not complained once.

    And a gateway publishes no capacity, so there is no number to respect.
    The bound that remains is not a throttle — it stops this process spawning
    subprocesses until the node dies. The gateway can queue or refuse and say
    so; a client-side cap says nothing to anyone.
    """
    import os

    import tests.benchmark.arms as arms_mod

    keys = ("PHRONIX_HOSTED_MODEL", arms_mod.PACED_ENV)
    was = {k: os.environ.get(k) for k in keys}
    try:
        for k in keys:
            os.environ.pop(k, None)
        # A local fleet: not paced, capped at the replica count.
        assert arms_mod._paced_run() is False

        os.environ["PHRONIX_HOSTED_MODEL"] = "1"
        os.environ[arms_mod.PACED_ENV] = "1"
        assert arms_mod._paced_run() is True          # the subscription

        os.environ.pop(arms_mod.PACED_ENV)
        assert arms_mod._hosted_run() is True         # a gateway is hosted...
        assert arms_mod._paced_run() is False         # ...and not paced
    finally:
        for k, v in was.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    source = Path("tests/benchmark/arms.py").read_text(encoding="utf-8")
    # Three regimes, decided in one place.
    assert 'key, default = "llm.max_concurrent_agents", 8' in source
    assert 'key, default = "llm.max_concurrent_agents_local", 64' in source
    assert 'key, default = "llm.max_concurrent_agents_gateway", 256' in source

    # And only the subscription is marked as paced, by provider.
    cli = Path("tests/benchmark/cli.py").read_text(encoding="utf-8")
    assert 'if provider in ("", "anthropic", "claude"):' in cli
    assert 'os.environ.setdefault("PHRONIX_PACED_LLM", "1")' in cli
