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

    assert "aspect-record" in PhronixArm.MUST_FINISH_STAGES
    assert "aspect" not in PhronixArm.MUST_FINISH_STAGES
    # The connective stages too: each one turns several paid-for stages into the
    # input for the next, so truncating one discards all of them.
    for stage in ("plan", "collect", "propose", "execution-plan"):
        assert stage in PhronixArm.MUST_FINISH_STAGES, stage


def test_every_stage_the_driver_runs_has_a_budget():
    """A missing budget is a KeyError in the middle of a research pass."""
    from tests.benchmark.arms import PhronixArm

    for stage in ("survey", "plan", "aspect", "aspect-record", "aspect-recheck",
                  "collect", "propose", "evaluate", "execution-plan"):
        assert stage in PhronixArm.STAGE_BUDGETS, stage


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


def test_the_early_stages_actually_consult_prior_work():
    """Wiring the lookup up is the whole point; a tool nobody calls is inert."""
    from tests.benchmark.arms import PhronixArm as arm

    assert "research_prior" in arm.SURVEY_PROMPT
    assert "graph_query" in arm.SURVEY_PROMPT      # reaches subjects terms miss
    assert "research_prior" in arm.PLAN_PROMPT     # so aspects are not wasted
    assert "research_prior" in arm.PROPOSE_PROMPT  # so approaches are not re-proposed


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

    It fails quietly: the stage exits in about two seconds, the ranking still
    reports scores, and those scores are the predictions the propose stage wrote
    rather than measurements. A real run showed three evaluators at `max 2s`
    with a ranking of 1.0 / 1.0 / 0.9 — an argmax over guesses, which is exactly
    what the figure of merit exists to prevent.
    """
    import re
    from pathlib import Path

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    block = source[source.index("tree = checkout / SCRATCH_DIR"):]
    block = block[:block.index("stage(f\"evaluate:")]

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
    """
    from phronix.layers import bundled_root
    from tests.benchmark.isolation import fresh_store

    store = tmp_path / "run" / ".phronix"
    fresh_store(store)

    shipped = {p.name for p in (bundled_root() / "skills").glob("*") if p.is_dir()}
    seeded = {p.name for p in (store / "skills").glob("*") if p.is_dir()}
    assert shipped and shipped <= seeded
    assert not list((store / "research").glob("*.json"))


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


def test_execution_plan_records_the_plan_before_verifying():
    """A pass that found the fix, measured it at 1.0 and wrote the playbook
    still verified as `invariants fail: no plan recorded`, because the agent
    did the work and skipped the bookkeeping. The corrector only knows what is
    on record, so successful research reported as failed.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm

    prompt = PhronixOpenCodeArm.EXECUTION_PLAN_PROMPT
    assert "research_write_plan" in prompt
    assert prompt.index("research_write_plan") < prompt.index("research_verify")


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


def test_retry_research_is_told_to_classify_the_failure_first():
    """Refining and abandoning are opposite moves, and the test output is what
    distinguishes them — so the prompt must ask for the classification before it
    asks for approaches, not offer refinement as an afterthought.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    note = Arm.RESUME_NOTE
    assert "research_refine_approach" in note
    assert "attempt-notes.md" in note
    assert note.index("classify") < note.index("research_refine_approach")
    assert "research_refine_approach" in Arm.PROPOSE_PROMPT

    # Both placeholders are filled, or the agent is handed a literal "{topic}".
    filled = note.replace("{skill}", "s").replace("{topic}", "t")
    assert "{" not in filled


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
    assert "worked=True" in tail[:900]
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


def test_a_retry_diagnoses_instead_of_re_proposing():
    """The revision pass ran `propose` again — the whole candidate space, a
    second time — so a pass holding a specific failure output spent its budget
    re-deriving alternatives instead of reading the one piece of evidence the
    first pass did not have. Measured on pylint-7080: the attempt failed by a
    missing normalisation and the revision answered with four fresh candidates
    rather than the one-line fix to the approach that had everything else right.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index('        budgets = self.STAGE_BUDGETS'):
                  source.index('        stage("execution-plan"')]
    assert 'stage("propose"' in flow and 'stage("diagnose"' in flow
    # Propose belongs to the first pass; diagnose to every one after it.
    assert flow.index("attempt_index <= 1") < flow.index('stage("propose"')
    assert flow.index('stage("diagnose"') > flow.index('stage("propose"')

    prompt = Arm.DIAGNOSE_PROMPT
    assert "research_refine_approach" in prompt
    assert "attempt-notes.md" in prompt
    # It must build the failing case before concluding: the last attempt's own
    # reproduction passed, which is why it shipped a fix that did not work.
    assert "reproduction" in prompt and "{scratch}" in prompt
    assert prompt.index("reproduction") < prompt.index("research_refine_approach")
    # And it must be told not to re-research.
    assert "Do not re-survey" in prompt

    # Must-finish and budgeted like the other connective stages.
    assert "diagnose" in Arm.MUST_FINISH_STAGES
    assert Arm.STAGE_BUDGETS["diagnose"] >= 300


def test_the_reproduction_survives_into_the_next_attempt():
    """A diagnosis the next attempt cannot run is a note, not a corrector.

    The rule the whole retry path exists to enforce is that a task must not fail
    twice the same way. That needs an executable check crossing the boundary:
    the diagnosis writes a reproduction of the exact failure, and the attempt
    runs it and may not report done while it still fails.
    """
    from tests.benchmark.arms import (PHRONIX_PLAN_SUFFIX, RESEARCH_SCRATCH,
                                      PhronixOpenCodeArm as Arm)

    # One agreed location, or the two halves never meet.
    where = f"{RESEARCH_SCRATCH}/repro"
    assert "{scratch}" in Arm.DIAGNOSE_PROMPT
    assert "{repro}" in PHRONIX_PLAN_SUFFIX
    filled = (PHRONIX_PLAN_SUFFIX.replace("{topic}", "t").replace("{skill}", "s")
              .replace("{repro}", where))
    assert where in filled and "{" not in filled

    # And the attempt is told the one thing that makes it a corrector.
    assert "Do not report done" in filled
    assert "fail before your change and pass after" in filled


def test_tuning_and_the_final_score_use_different_instances(tmp_path, monkeypatch):
    """Refinement moved OUT of the evaluation stage.

    Putting it there was the obvious choice and the wrong one: an approach
    adjusted in response to the held-out set has been tuned on it, and nothing
    downstream can falsify anything afterwards. Tuning gets its own stage, its
    own instances (train + validate, 80%) and the right to refine; evaluation
    sees `test` only, once, and may not change anything.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm
    from phronix import research

    assert research.TUNING_PHASES == ("train", "validate")
    ratios = research.DEFAULT_SPLIT
    tuning = sum(ratios[p] for p in research.TUNING_PHASES)
    assert abs(tuning - 0.8) < 1e-9 and abs(ratios["test"] - 0.2) < 1e-9

    tune, evaluate = Arm.TUNE_PROMPT, Arm.EVALUATE_PROMPT
    # Only tuning may refine, and only it may see the tuning instances.
    assert "research_refine_approach" in tune
    assert "research_refine_approach" not in evaluate
    assert "**train** and\n   **validate**" in tune or "train" in tune
    assert "held out" in tune
    # Evaluation is the final measurement and says so.
    assert "ONLY the **test**" in evaluate
    assert "FINAL measurement" in evaluate

    # The flow runs tune before evaluate, in the same worktree.
    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("def tune_one("):source.index("Ranking is arithmetic")]
    assert body.index('stage(f"tune:') < body.index('stage(f"evaluate:')
    assert "final_revision" in body


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
    assert "twenty instances" in Arm.PLAN_PROMPT
    assert "Negative cases" in Arm.PLAN_PROMPT


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


def test_a_retry_measures_the_revision_not_the_whole_field():
    """The first pass explores; a retry already knows where the answer is and
    holds a reproduction of the exact failure. Re-tuning unrelated candidates
    spends the budget that should measure the one informed by what the task did
    — and lets a fresh corpus-scored approach outrank the revision.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("        pending = [a for a in"):
                  source.index("Ranking is arithmetic")]
    assert "attempt_index > 1" in body and 'a.get("refines")' in body
    # Narrower, not weaker: the revision still goes through tune then evaluate.
    assert body.index('stage(f"tune:') < body.index('stage(f"evaluate:')
    # And a retry reconciles the parallel repairs before any of them is scored.
    assert body.index("REPAIR_COLLECT_PROMPT") < body.rindex("evaluate_one")

    # And the failure that lost the attempt becomes a corpus instance, or the
    # revision can score 1.0 without fixing it.
    assert "research_add_instances" in Arm.DIAGNOSE_PROMPT
    assert "**test**-phase instance" in Arm.DIAGNOSE_PROMPT


def test_aspects_try_what_they_find_instead_of_only_theorising():
    """Aspects were read-only, so every candidate reached the ranking as a
    prediction and the first measurement happened stages later.

    Measured repeatedly: a research pass ended with its top-ranked approach
    scoring 0.0 and every other candidate unmeasured, so the attempt
    implemented the only thing carrying a number — a number that said it did
    not work. The aspect stage is where a measured candidate is cheapest to
    produce: the agent is already in the code, with the corpus declared.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    prompt = Arm.ASPECT_PROMPT
    assert "{workspace}" in prompt                    # its own worktree
    assert "research_record_trial" in prompt
    assert "research_add_approach" in prompt
    # Tuning instances only. `test` is held out here as everywhere else.
    assert "**train** and\n  **validate**" in prompt or "held out" in prompt
    assert "research_refine_approach" in prompt       # short is a finding, not an end

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("def investigate(aspect"):
                  source.index("with ThreadPoolExecutor(max_workers=len(chosen))")]
    assert "private_tree(f\"aspect-" in body and "drop_tree(tree)" in body

    # Trying takes longer than reading — but not as long as was assumed. The
    # ceiling was 540s against a measured 118s wall for three aspects, and the
    # aspects are a barrier, so an over-generous ceiling is what a straggler
    # holds `collect` open for.
    assert 180 <= Arm.STAGE_BUDGETS["aspect"] <= 300


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


def test_the_measured_change_is_kept_as_evidence_not_as_the_method(
        tmp_path, monkeypatch):
    """The patch is what the method produced ONCE, on one instance.

    Keeping it is worth doing — it is evidence the approach was really applied
    and measured, and a reference if a step turns out ambiguous. It is not the
    solution: a diff solves one instance, while the skill is filed under a
    subject and has to solve the next one too. So it lives in a file, is
    referenced rather than carried, and the attempt is pointed at the STEPS.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from pathlib import Path

    from phronix import research
    from tests.benchmark.arms import PHRONIX_PLAN_SUFFIX

    topic = "carry-the-diff"
    research.add_approach(topic, "fix", "s", hypothesis="h")
    key = research.load(topic)["approaches"][0]["key"]

    diff = "--- a/pylint/lint/pylinter.py\n+++ b/pylint/lint/pylinter.py\n@@\n-old\n+new"
    noted = research.record_change(topic, key, diff)
    assert noted["status"] == "ok"
    assert noted["files"] == ["pylint/lint/pylinter.py"] and noted["lines"] == 2

    patch = Path(noted["patch"])
    assert patch.is_file() and patch.read_text().startswith("--- a/pylint")

    # Referenced, never carried: nothing on the approach is patch-sized.
    entry = research.approach_detail(topic, key)["approach"]
    assert entry["change_patch"] == str(patch)
    assert all(len(str(v)) < 200 for v in entry.values() if isinstance(v, str))

    huge = research.record_change(topic, key, "x" * (research.CHANGE_LIMIT + 1))
    assert huge["status"] == "error" and "debris" in huge["error"]

    # Captured by the harness with git diff, not written out by an agent.
    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("def tune_one("):source.index("Ranking is arithmetic")]
    assert '["git", "diff"], cwd=target' in body and "record_change" in body

    # And the attempt follows the METHOD. It is never told to replay a diff.
    collapsed = " ".join(PHRONIX_PLAN_SUFFIX.split())
    assert "Follow the skill's `Steps to solve ...` block" in collapsed
    assert "a method, not a recording" in collapsed
    assert "git apply" not in collapsed


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


def test_every_stage_of_the_pipeline_is_wired_end_to_end():
    """The flow, as specified: survey, plan, aspects in parallel, collect,
    propose approaches AS pipelines, tune each in place in parallel, evaluate
    against held-out data, write the solution file with every approach ranked
    and a tool for every deterministic step, run the task, and on failure
    diagnose with a deterministic test case and refine across approaches.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("        budgets = self.STAGE_BUDGETS"):
                  source.index("        stdout = \"\".join(transcripts)")]
    order = [flow.index(f'stage("{name}"') if f'stage("{name}"' in flow
             else flow.index(f'stage(f"{name}')
             for name in ("survey", "plan", "aspect:", "collect", "propose",
                          "tune:", "evaluate:", "execution-plan")]
    assert order == sorted(order), "the stages are no longer in pipeline order"

    # Approaches arrive as pipelines, not as prose.
    assert "research_record_pipeline" in Arm.PROPOSE_PROMPT
    assert "research_record_pipeline" in Arm.TUNE_PROMPT
    # The solution file adopts the winner and builds tools across ALL of them.
    assert "research_adopt_pipeline" in Arm.EXECUTION_PLAN_PROMPT
    assert "not only the winner's" in Arm.EXECUTION_PLAN_PROMPT
    # A retry diagnoses with a deterministic case and fixes the other pipelines.
    assert "research_rank" in Arm.DIAGNOSE_PROMPT
    assert "deterministic test" in Arm.DIAGNOSE_PROMPT


def test_the_attempt_fetches_one_block_through_the_graph():
    """Loading the whole solution skill is paid for on every subsequent step.

    Each api call carries the entire conversation again, so a block loaded once
    and never used costs its tokens once per step — and these attempts run to
    dozens of steps. The graph resolves a heading to exactly its markdown
    section, so the attempt locates, fetches that section, and acts.
    """
    from tests.benchmark.arms import (PHRONIX_PLAN_SUFFIX,
                                      PhronixOpenCodeArm as Arm)

    collapsed = " ".join(PHRONIX_PLAN_SUFFIX.split())
    assert "graph_query(question=" in collapsed
    assert "graph_get_node" in collapsed
    # Locate before loading: the query must come before the whole-skill fallback.
    assert collapsed.index("graph_query") < collapsed.index("Fall back to")
    # The fallback still exists — a graph miss must not strand the attempt.
    assert 'skill_load("{skill}")' in PHRONIX_PLAN_SUFFIX
    # And the reason is stated, because a rule without one gets optimised away.
    assert "re-read on every subsequent step" in collapsed

    # The graph is refreshed at the moment the skill changes, or the first
    # query pays for a rebuild or misses the block entirely.
    assert "graph_ensure" in Arm.EXECUTION_PLAN_PROMPT
    assert (Arm.EXECUTION_PLAN_PROMPT.index("research_playbook")
            < Arm.EXECUTION_PLAN_PROMPT.index("graph_ensure"))


def test_a_retry_repairs_in_parallel_then_reconciles_then_scores():
    """The retry mirrors the research pass, because the problem is the same:
    several agents work in parallel on separate approaches, and what each learns
    about the failing case bears on the others.

    Fusing tune into evaluate here would score each revision before anybody had
    reconciled what the repairs found — and the case that defeated the last
    attempt is precisely what every candidate now has to answer.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    body = source[source.index("        if pending:"):
                  source.index("        # Ranking is arithmetic")]

    # First pass fuses; a retry has a barrier in the middle.
    assert "tune_then_evaluate" in body
    assert body.index("REPAIR_COLLECT_PROMPT") < body.rindex("evaluate_one")

    # Nothing is re-explored: repairs work on pipelines that already exist.
    assert "Nothing is re-explored" in body

    collect = Arm.REPAIR_COLLECT_PROMPT
    assert "converge" in collect and "contradict" in collect
    assert "no new approaches are\nproposed" in collect


def test_method_tools_survive_a_fresh_run(tmp_path):
    """`--fresh` withholds what earlier runs LEARNED, not what they built.

    A `probe_` capability knows how to run one area's tests, or set a fixture up
    in a given shape. It carries nothing about any particular task, so seeding
    it does not pre-train the run — it hands it the shell scripting every
    previous run had to derive from nothing. Excluding it would make "from
    scratch" mean "without tools", which is a claim about tooling rather than
    about learning.
    """
    from tests.benchmark.isolation import METHOD_CAPABILITY_PREFIX, seed_store

    carry = tmp_path / "carry"
    for kind, names in (("capabilities", ["probe_run_area_tests.py",
                                          "apply_ignore_paths_fix.py"]),
                        ("skills", ["pylint-ignore-paths.md"]),
                        ("research", ["pylint-dev-pylint-7080.json"])):
        (carry / kind).mkdir(parents=True)
        for name in names:
            (carry / kind / name).write_text("x")

    store = tmp_path / "store" / ".phronix"
    store.mkdir(parents=True)
    seeded = seed_store(store, carry, kinds=("capabilities",),
                        method_tools_only=True)["seeded"]

    assert seeded == ["capabilities/probe_run_area_tests.py"], seeded
    # The task-specific capability, the skill and the research stay behind.
    assert not (store / "capabilities" / "apply_ignore_paths_fix.py").exists()
    assert not (store / "skills").exists()
    assert not (store / "research").exists()

    # A full carry-over still takes everything.
    everything = seed_store(store, carry)["seeded"]
    assert len(everything) == 4

    # The prefix is what the execution-plan stage asks for, so the two cannot
    # drift apart into a rule nothing satisfies.
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm
    assert f"`{METHOD_CAPABILITY_PREFIX}` prefix" in Arm.EXECUTION_PLAN_PROMPT


def test_research_tools_are_built_at_the_end_not_during():
    """Building tools mid-investigation interrupts the investigation.

    The end of the pass costs one stage and pays back on every task that
    follows — and by then the pass knows which steps it actually repeated,
    which is the only reliable way to tell a reusable tool from a guess.
    """
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    plan = Arm.EXECUTION_PLAN_PROMPT
    assert "capability_new" in plan and "capability_list" in plan
    assert "would I write this again" in " ".join(plan.split())   # hard-wrapped
    # Not bolted onto every stage: exploration stays exploration.
    for prompt in (Arm.ASPECT_PROMPT, Arm.PROPOSE_PROMPT, Arm.TUNE_PROMPT):
        assert "capability_list()" not in prompt


def test_the_same_procedure_is_not_built_twice_under_two_names(tmp_path,
                                                               monkeypatch):
    """Solution tools are task-shaped, so a step in one task's pipeline is a
    step in another's — and research passes that never see each other author
    the same procedure repeatedly.

    Each copy then has to be maintained, verified and chosen between, and an
    agent facing three tools with the same body and different names has been
    handed a decision nobody meant to give it.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from phronix import capabilities

    body = ('def register(mcp):\n'
            '    @mcp.tool()\n'
            '    def {name}(path: str) -> str:\n'
            '        """{doc}"""\n'
            '        return path.strip()\n')

    first = capabilities.new("normalise_path_for_match", "normalise a path",
                             source=body.format(name="normalise_path_for_match",
                                                doc="Normalise a path."))
    assert first["status"] == "ok"

    # Same procedure, different name, different prose, extra comment.
    twin = ('def register(mcp):\n'
            '    @mcp.tool()\n'
            '    def strip_leading_dot(path: str) -> str:\n'
            '        """Quite different wording here."""\n'
            '        # and a comment the other one lacks\n'
            '        return path.strip()\n')
    second = capabilities.new("strip_leading_dot", "strip ./ from a path",
                              source=twin)
    assert second["status"] == "duplicate"
    assert second["use"] == "normalise_path_for_match"
    assert not (tmp_path / ".phronix" / "capabilities"
                / "strip_leading_dot.py").exists()

    # A genuinely different procedure is unaffected.
    other = capabilities.new("count_matches", "count matches", source=body.format(
        name="count_matches", doc="Count matches.").replace(
            "return path.strip()", "return str(len(path))"))
    assert other["status"] == "ok"

    # And the execution-plan stage is told to reuse rather than re-author.
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm
    collapsed = " ".join(Arm.EXECUTION_PLAN_PROMPT.split())
    assert "capability_list()` FIRST" in collapsed
    assert "answers `duplicate`" in collapsed


def test_the_learner_survives_the_revert(tmp_path, monkeypatch):
    """The research flow went back to the committed one; the learner did not.

    It is orthogonal to the flow — it reads observations rather than stages, so
    nothing about it depended on the shape that was removed. Two clocks: every
    ten seconds it NOTICES, which is arithmetic over what has been reported;
    every minute it RECONCILES, which is one agent turning what repeated into
    lessons and tools. Aggressive capture, periodic compaction.
    """
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    from pathlib import Path

    from phronix import research
    from tests.benchmark.arms import PhronixOpenCodeArm as Arm, build

    # The channel: an append, so reporting cannot block the stage reporting.
    monkeypatch.setenv("PHRONIX_RESEARCH_TOPIC", "task-a")
    assert research.observe("normalising the path before matching fixed cases",
                            worked=True, stage="tune")["status"] == "ok"
    monkeypatch.setenv("PHRONIX_RESEARCH_TOPIC", "task-b")
    research.observe("normalizing paths before the match fixed nine cases",
                     worked=True, stage="aspect")
    research.observe("the green test masked the bug", worked=False,
                     stage="survey")

    # Noticing is arithmetic, and it groups by what a report CLAIMS: two agents
    # describing one finding never word it the same way.
    noticed = research.notice()
    assert noticed["new"] == 3
    assert len(noticed["repeats"]) == 1
    assert noticed["candidates"][0]["across_tasks"] is True

    # Two clocks, and the fast one cannot be a model call: an invocation costs
    # the better part of a minute before it does anything.
    assert Arm.LEARNING_NOTICE_INTERVAL <= 10
    assert Arm.LEARNING_RECONCILE_INTERVAL >= 6 * Arm.LEARNING_NOTICE_INTERVAL

    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    loop = source[source.index("    def start_learning(self, store_root: Path"):
                  source.index("    def _learning_products(")]
    assert "daemon=True" in loop
    assert "research_mod.notice" in loop            # fast tier, no agent
    assert "stream_opencode(" in loop               # slow tier, one agent
    assert "[learner] running:" in loop             # says it started

    # Every stage reports, and every arm answers the runner's calls.
    for const in ("SURVEY_PROMPT", "PLAN_PROMPT", "ASPECT_PROMPT",
                  "PROPOSE_PROMPT", "TUNE_PROMPT"):
        assert "research_observe(" in getattr(Arm, const), const
    for name in ("claude-phronix", "opencode-bare", "mini"):
        assert build(name, model="m", provider="p",
                     base_url="u").stop_learning() == []


def test_the_aspect_phase_is_wide_and_bounded():
    """Aspects fan out with no merge above them, which changes what width costs.

    The tuning tree pays a merge level per doubling, so widening it made the
    pass slower — measured, six merge levels cost 840s against 444s for both
    fan-outs together. Aspects have no such tax: they investigate, write
    findings, and `collect` reads all of them, so the phase costs its slowest
    member whether there are three or eight. Widening buys coverage and costs
    only tokens.

    The ceiling is the other half. Aspects are a barrier, so one straggler holds
    `collect` and everything after it for as long as its budget allows —
    measured, three aspects took 118s wall against a 540s ceiling, which never
    bound the common case and bound the bad one far too late.
    """
    from pathlib import Path

    from tests.benchmark.arms import PhronixOpenCodeArm as Arm

    assert Arm.max_parallel_aspects >= 5
    # Near the measured maximum, so the barrier is predictable.
    assert Arm.STAGE_BUDGETS["aspect"] <= 300
    assert Arm.STAGE_BUDGETS["aspect-record"] <= 180

    # Filing findings is still must-finish: a write-up cut half way loses
    # everything the investigation paid for.
    assert "aspect-record" in Arm.MUST_FINISH_STAGES
    assert "aspect" not in Arm.MUST_FINISH_STAGES

    # And they genuinely run at once.
    source = (Path(__file__).parent / "benchmark" / "arms.py").read_text()
    flow = source[source.index("            aspects = self._in_store("):
                  source.index('stage("collect"')]
    assert "ThreadPoolExecutor(max_workers=len(chosen))" in flow
    assert "pool.map(investigate, chosen)" in flow


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

    gate = _LlmGate()
    started = time.time()
    with gate.slot():
        pass
    with gate.slot():
        pass
    # Two starts cannot be simultaneous: spacing is what turns a burst into a
    # sustainable draw, and concurrency alone does not bound the rate.
    assert time.time() - started >= 1.0

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
