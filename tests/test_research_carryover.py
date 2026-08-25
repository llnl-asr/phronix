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
from pathlib import Path

import pytest


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
    (first / "skills" / "learned-here").mkdir(parents=True, exist_ok=True)
    (first / "skills" / "learned-here" / "SKILL.md").write_text("# learned\n")

    promoted = promote_store(first, carry)["promoted"]
    assert "research/topic.json" in promoted
    assert "skills/learned-here/SKILL.md" in promoted

    shipped = sorted(p.name for p in (bundled_root() / "skills").glob("*")
                     if p.is_dir())
    assert shipped, "expected the framework to ship skills"
    assert not any(f"skills/{name}/" in entry for entry in promoted
                   for name in shipped), promoted

    second = tmp_path / "run2" / ".phronix"
    fresh_store(second)
    seed_store(second, carry)
    assert (second / "research" / "topic.json").is_file()
    assert (second / "skills" / "learned-here" / "SKILL.md").is_file()


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
    (carry / "skills" / "from-an-earlier-run").mkdir(parents=True)
    (carry / "skills" / "from-an-earlier-run" / "SKILL.md").write_text("# earlier\n")

    store = tmp_path / "run" / ".phronix"
    fresh_store(store)
    (store / "skills" / "from-this-run").mkdir(parents=True, exist_ok=True)
    (store / "skills" / "from-this-run" / "SKILL.md").write_text("# now\n")

    promote_store(store, carry)
    assert (carry / "skills" / "from-an-earlier-run" / "SKILL.md").is_file()
    assert (carry / "skills" / "from-this-run" / "SKILL.md").is_file()


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

    text = (isolated_layers["store"] / "skills" / result["skill"] / "SKILL.md").read_text()
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

    existing = isolated_layers["store"] / "skills" / "normalize-ignore-paths"
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
    assert (common / "pylint-ignore.json").is_file()
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
        (isolated_layers["store"] / "research" / "shared.json").read_text())
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
    alpha = json.loads((sessions / "run-alpha" / "shared.json").read_text())
    assert [a["name"] for a in alpha["approaches"]] == ["approach-a"]
    assert (sessions / "run-beta" / "shared.json").is_file()


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
    (earlier / "skills" / "learned-last-time").mkdir(parents=True, exist_ok=True)
    (earlier / "skills" / "learned-last-time" / "SKILL.md").write_text("# learned\n")
    (earlier / "research").mkdir(parents=True, exist_ok=True)
    (earlier / "research" / "topic.json").write_text('{"topic": "topic"}')
    promote_store(earlier, carry)

    # Fresh: fresh_store only, no seed_store — what the runner does when
    # research_reuse is off.
    store = tmp_path / "fresh-run" / ".phronix"
    fresh_store(store)
    assert not (store / "skills" / "learned-last-time").exists()
    assert not list((store / "research").glob("*.json"))

    # Reuse: the same carry root, seeded.
    reusing = tmp_path / "reusing-run" / ".phronix"
    fresh_store(reusing)
    seed_store(reusing, carry)
    assert (reusing / "skills" / "learned-last-time" / "SKILL.md").is_file()
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

    skills = [p.name for p in (isolated_layers["store"] / "skills").glob("*")
              if p.is_dir()]
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

    text = (isolated_layers["store"] / "skills" / result["skill"] / "SKILL.md").read_text()
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

    text = (isolated_layers["store"] / "skills"
            / research.topic_skill(topic) / "SKILL.md").read_text()
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

    text = (isolated_layers["store"] / "skills"
            / research.topic_skill(topic) / "SKILL.md").read_text()
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
    assert "ThreadPoolExecutor(max_workers=len(groups))" in loop
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
    gate = _LlmGate()
    monkey = {"llm.min_seconds_between_starts": 1.0,
              "llm.max_concurrent_agents": 4}
    import tests.benchmark.arms as arms_mod

    real = arms_mod._tuned
    arms_mod._tuned = lambda key, fallback: monkey.get(key, fallback)
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

    notes = []
    gate.rejected_until(time.time() + 10_000, notes.append)
    assert any("resets in" in note for note in notes)

    # Past the cap it proceeds rather than sitting silently for hours — a
    # visible failure beats an invisible stall.
    waited = time.time()
    gate._wait_for_window(notes.append)
    assert time.time() - waited < 5
    assert any("going ahead" in note for note in notes)


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
        from tests.benchmark.arms import OBSERVE_NOTE
        pointer = prompt.replace(OBSERVE_NOTE, "")
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

    import phronix.skills as skills_module
    original, skills_module.search = skills_module.search, fake_search
    try:
        arm._in_store = lambda root, fn, *a, **k: fn(*a, **k)
        got = arm.recalled_skill(tmp_path, {"repo": "pylint-dev/pylint"})
    finally:
        skills_module.search = original

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

    import phronix.skills as skills_module
    original = skills_module.search
    skills_module.search = lambda *a, **k: {
        "status": "ok", "query": "q", "count": 1,
        "results": [{"skill": "pylint-fixme-notes-regex-boundary",
                     "subject": "pylint-fixme-notes-regex-boundary"}]}
    try:
        got = arm.recalled_skill(tmp_path, {"repo": "pylint-dev/pylint"})
    finally:
        skills_module.search = original

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
    assert sorted(denied) == ["Artifact", "RemoteTrigger"]
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
    """A tool that knows a task goes under that task, not beside the methods."""
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
    assert Path(method["file"]).parent.name == "capabilities"
    assert Path(bound["file"]).parent.name == "pylint-dev-pylint-7080"
    assert Path(bound["file"]).parent.parent.name == capabilities.TASK_CAPABILITY_DIR


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
    (store / "skills" / "solution-pylint-dev-pylint-7080").mkdir(parents=True,
                                                                exist_ok=True)
    (store / "skills" / "solution-pylint-dev-pylint-7080" / "SKILL.md").write_text(
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


def test_a_capability_lists_with_what_it_says_it_does():
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

    described = [r for r in listing() if r["description"]]
    assert described, "no capability lists a description at all"
    # The learned tools are the ones that were blank, and they are the point.
    by_name = {r["name"]: r["description"] for r in listing()}
    if "apply_normpath_ignore_fix" in by_name:
        assert "normpath" in by_name["apply_normpath_ignore_fix"]

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

    # A candidate written by a previous pass outranks the bare topic skill: it
    # is the one that was actually raced against the tests.
    cand = skills / "solution-pallets-flask-4045-reject-dotted-name"
    cand.mkdir(parents=True)
    (cand / "SKILL.md").write_text("# candidate\n")
    assert arm.best_skill_for(tmp_path, "pallets__flask-4045") == cand.name

    # The merged solution outranks both — it carries the answer plus links to
    # every candidate tried.
    merged = skills / "solution-pallets-flask-4045"
    merged.mkdir(parents=True)
    (merged / "SKILL.md").write_text("# merged\n")
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
    assert "do not combine" in prompt

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
