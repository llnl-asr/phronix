"""Research tools: work out how a task should be done before attempting it.

The step that goes missing when an agent is capable enough to start immediately.
Given an unfamiliar problem it opens the file it first suspects, writes a
plausible fix, and — with a learning loop attached — records ever more detailed
notes about that same file. What it never does is ask *how is this class of
problem approached*, because nothing forces the question.

These tools force it, and gate it: :func:`research_assess` is deterministic, so
"do I already know this?" is a catalogue lookup rather than a matter of the
model's confidence, which is exactly the signal that is wrong in the case that
matters.

The output is infrastructure, not an answer. A figure of merit fixed in advance,
approaches measured against it, an argmax rather than an argument, and a plan
split into deterministic steps (which become MCP capabilities) and judgement
steps (which become skill blocks).
"""
from __future__ import annotations

import json
from typing import Any


def register(mcp: Any) -> None:
    @mcp.tool()
    def research_assess(task: str) -> str:
        """Does the library already cover this task, or must it be researched first?

        **Call this before starting any unfamiliar task.** Deterministic: it
        searches the skill catalogue and counts matching blocks, so the answer
        does not depend on how confident the model feels — an agent that failed
        the same task three ways was confident on every attempt.

        A ``gap`` verdict means research the subject before attempting it. A
        ``covered`` verdict names the skills to load and proceed with.

        Returns JSON: {status, covered, verdict, matched_skills, blocks, reason}.
        """
        from phronix import research

        return json.dumps(research.assess(task), indent=2)

    @mcp.tool()
    def research_define_fom(topic: str, name: str, direction: str,
                            target: float, measure: str) -> str:
        """Declare the figure of merit BEFORE comparing approaches.

        The one number that decides which approach wins, which way is better
        (``direction`` is ``max`` or ``min``), the ``target`` it must reach, and
        ``measure`` — exactly how the number is obtained.

        Declared first on purpose: a criterion chosen after the results are in is
        a justification, not a test. ``measure`` is mandatory because a figure of
        merit nobody can re-measure cannot be checked by a corrector, and an
        unfalsifiable criterion lends the appearance of rigour to an unmeasured
        choice.

        Returns JSON: {status, fom, next}.
        """
        from phronix import research

        return json.dumps(
            research.define_fom(topic, name, direction, target, measure), indent=2)

    @mcp.tool()
    def research_add_approach(topic: str, name: str, summary: str,
                              hypothesis: str = "", metrics: str = "",
                              source: str = "", tools: str = "",
                              measurement: str = "", aspect: str = "") -> str:
        """Record one candidate way of doing the task, with what you measured.

        ``metrics`` is a JSON object of numbers you actually obtained, and must
        include the figure of merit if this approach is to be selectable.
        ``source`` says where the approach came from — upstream docs, an issue,
        an experiment you ran. ``tools`` is a comma-separated list of tools it
        needs, so alternatives can be compared on cost as well as outcome.

        ``hypothesis`` is required: what you believe is true and what would show
        it false. An approach without one cannot be refuted, only abandoned — and
        the next session re-derives it because nothing records what was ruled out.
        ``aspect`` names which part of the research plan turned it up.

        ``measurement`` states HOW you obtained the numbers — the command you
        ran, the prototype you applied. **Leave it empty only when the numbers
        are predictions**, and expect that to matter: ``research_choose`` will
        not select on predictions alone, because an argmax over predictions
        returns the approach you already preferred. Two runs of one task
        demonstrated this exactly — each asserted 1.0 for a different approach,
        each was its own argmax, and only one of the patches fixed anything.

        Record the approaches you rejected too. An approach with a measured, poor
        number is what stops a later session re-trying it.

        Returns JSON: {status, approach, approaches, file}.
        """
        from phronix import research

        parsed = {}
        if metrics.strip():
            try:
                loaded = json.loads(metrics)
                if not isinstance(loaded, dict):
                    raise ValueError("metrics must be a JSON object")
                parsed = loaded
            except (ValueError, json.JSONDecodeError) as exc:
                return json.dumps({
                    "status": "error",
                    "error": f"metrics must be a JSON object of numbers: {exc}",
                    "example": '{"fail_to_pass_passed": 1, "steps": 12}',
                }, indent=2)
        tool_list = [t.strip() for t in tools.split(",") if t.strip()]
        return json.dumps(
            research.add_approach(topic, name, summary, hypothesis, parsed, source,
                                  tool_list, measurement=measurement, aspect=aspect),
            indent=2)

    @mcp.tool()
    def research_refine_approach(topic: str, key: str, diagnosis: str,
                                 change: str, hypothesis: str = "") -> str:
        """Carry a FAILED approach forward as a revision, rather than dropping it.

        Use this when the test output shows the idea was right and the change
        incomplete — it ran, in the right place, and missed a case. Use
        ``research_add_approach`` with something genuinely different when the
        output shows the idea itself was wrong.

        The distinction is the whole point, and the evidence decides it, not
        preference. A patch that put the ignore check in exactly the right
        function and never normalised the path failed by one call; abandoning
        that sent the next attempt looking somewhere else, away from an answer
        it was a line from having. Equally, refining forever is how one wrong
        idea eats every remaining attempt — so a lineage may be refined twice,
        and after that the diagnosis is what is wrong.

        ``diagnosis`` must say what the failure output actually showed: which
        test, what it printed, and why that means right-but-incomplete.
        ``change`` must name what will be different. Both are checked for
        substance, because without them this is a rename.

        Returns JSON: {status, approach, key, refines, depth,
        remaining_refinements}.
        """
        from phronix import research

        return json.dumps(
            research.refine_approach(topic, key, diagnosis, change, hypothesis),
            indent=2)

    @mcp.tool()
    def research_record_pipeline(topic: str, key: str, steps: str) -> str:
        """The ordered steps this approach runs. Its real content.

        ``steps`` is a JSON array of ``{title, kind, detail, capability?}``,
        where ``kind`` is ``deterministic`` or ``judgement``.

        An approach is a way of solving the problem, and the honest expression
        of a way is a sequence of steps rather than a name and a paragraph. Call
        this from the stage that TUNED the approach: it has just run those steps
        to measure it, so that is the one place the pipeline is known to be real
        rather than imagined.

        The winning approach's pipeline becomes the topic's plan, and the
        playbook renders it into the skill — so the skill is not written about
        the best approach, it *is* the best approach in executable form.

        Returns JSON: {status, key, steps, deterministic, next}.
        """
        from phronix import research

        try:
            parsed = json.loads(steps)
            if not isinstance(parsed, list):
                raise ValueError("steps must be a JSON array")
        except (ValueError, json.JSONDecodeError) as exc:
            return json.dumps({
                "status": "error",
                "error": f"steps must be a JSON array of objects: {exc}",
                "example": ('[{"title": "Find every ignore-pattern comparison", '
                            '"kind": "deterministic", "capability": '
                            '"find_ignore_comparisons"}]'),
            }, indent=2)
        return json.dumps(research.record_pipeline(topic, key, parsed), indent=2)

    @mcp.tool()
    def research_adopt_pipeline(topic: str, key: str = "") -> str:
        """Make the chosen approach's pipeline the topic's plan.

        The execution plan is not fresh writing at the end of research — it is
        the winning approach's own steps, promoted. Writing it again by hand
        produces a fourth version of something already established three times,
        and the version typed at the end is the one nobody measured.

        Defaults to the top live candidate carrying a pipeline, which is the one
        the attempt will try.

        Returns JSON: {status, key, approach, steps, needs_capability}.
        """
        from phronix import research

        return json.dumps(research.adopt_pipeline(topic, key), indent=2)

    @mcp.tool()
    def research_choose(topic: str, metric: str = "", prefer: str = "",
                        min_margin: float = 0.0) -> str:
        """Pick the best approach by the numbers. Arithmetic, not opinion.

        Defaults to the declared figure of merit. Returns ``inconclusive`` rather
        than a winner when fewer than two approaches carry the metric, or when
        the margin is within ``min_margin`` — a comparison that cannot separate
        two options should say so, because "we evaluated the alternatives" must
        not become attachable to a choice that was never made.

        Returns JSON: {status, chosen, metric, value, margin, runner_up, ranking}.
        """
        from phronix import research

        return json.dumps(
            research.choose(topic, metric, prefer, min_margin), indent=2)

    @mcp.tool()
    def research_write_plan(topic: str, steps: str) -> str:
        """Record the plan: ordered steps, each tagged deterministic or judgement.

        ``steps`` is a JSON array of
        ``{title, kind, detail, capability?, skill?}``, where ``kind`` is
        ``deterministic`` or ``judgement``.

        The tag decides what the step becomes. Deterministic steps become MCP
        capabilities via ``capability_new`` — same inputs, same outputs, every
        run. Judgement steps become skill blocks via ``skill_write``. A step left
        untagged is rejected rather than defaulted: defaulting to judgement turns
        mechanical work into prose that drifts, and defaulting to deterministic
        promises a repeatability the step cannot deliver.

        Returns JSON: {status, steps, deterministic, judgement, next}.
        """
        from phronix import research

        try:
            parsed = json.loads(steps)
            if not isinstance(parsed, list):
                raise ValueError("steps must be a JSON array")
        except (ValueError, json.JSONDecodeError) as exc:
            return json.dumps({
                "status": "error",
                "error": f"steps must be a JSON array of objects: {exc}",
                "example": ('[{"title": "Run the failing test and read the '
                            'assertion", "kind": "deterministic", "capability": '
                            '"run_target_tests"}]'),
            }, indent=2)
        return json.dumps(research.write_plan(topic, parsed), indent=2)

    @mcp.tool()
    def research_record_achieved(topic: str, value: float, note: str = "") -> str:
        """Record the figure of merit the finished work actually delivered.

        Kept separate from an approach's predicted number, because the gap
        between the two is the most useful thing a corrector can report:
        research that read convincingly and did not hold.

        Returns JSON: {status, achieved, target, meets_target}.
        """
        from phronix import research

        return json.dumps(research.record_achieved(topic, value, note), indent=2)

    @mcp.tool()
    def research_verify(topic: str) -> str:
        """Check the research record deterministically. The corrector for research.

        Five facets: a figure of merit exists and is measurable (assumptions);
        at least two approaches carry it (inputs); the recorded choice is the
        argmax rather than the best-argued (constraints); every deterministic
        step names a capability (invariants); and the achieved figure of merit
        meets its target (outputs).

        Run it before acting on a plan and again after executing it.

        Returns JSON: {status, verdict, facets: [{facet, verdict, detail}]}.
        """
        from phronix import research

        return json.dumps(research.verify_plan(topic), indent=2)

    @mcp.tool()
    def research_declare_corpus(topic: str, dimensions: str,
                                target: int = 100, rationale: str = "") -> str:
        """Declare what varies across this task's instances, and how many to build.

        ``dimensions`` is a JSON object of axis -> list of values, e.g.
        ``{"path_form": ["relative", "absolute", "dotted"],
        "target": ["file", "directory", "package"]}``.

        Diversity is task-specific, which is why it is declared rather than
        assumed. Instances generated without stated axes cluster around whatever
        the author was already thinking about, so the held-out set ends up
        testing the same idea the approach came from and confirms it for free.

        ``target`` below 100 requires a ``rationale``: some tasks genuinely admit
        few distinct cases, but shrinking the corpus until it matches what you
        already built is not one of those cases.

        Returns JSON: {status, target, dimensions, distinct_combinations, next}.
        """
        from phronix import research

        try:
            axes = json.loads(dimensions)
            if not isinstance(axes, dict):
                raise ValueError("dimensions must be a JSON object")
        except (ValueError, json.JSONDecodeError) as exc:
            return json.dumps({
                "status": "error",
                "error": f"dimensions must be a JSON object of axis -> values: {exc}",
                "example": '{"path_form": ["relative", "absolute"]}'}, indent=2)
        return json.dumps(
            research.declare_corpus(topic, axes, target, rationale), indent=2)

    @mcp.tool()
    def research_add_instances(topic: str, instances: str) -> str:
        """Add many task instances at once, without phases.

        ``instances`` is a JSON array of ``{name, behaviour, command?, expected?,
        dimensions?, source?}``. ``dimensions`` places the case on the axes
        declared for the corpus.

        Build them with a generator rather than by hand — a script that emits the
        combinations is deterministic, is worth registering with
        ``capability_new``, and gets you a hundred cases for the cost of writing
        one. An instance taken from the upstream issue or its discussion is worth
        several invented ones: record its ``source``.

        Phases are NOT set here. ``research_split`` assigns them by hash, because
        an author choosing what to hold out tends to hold out what already works.

        Returns JSON: {status, added, total, target, next}.
        """
        from phronix import research

        try:
            rows = json.loads(instances)
            if not isinstance(rows, list):
                raise ValueError("instances must be a JSON array")
        except (ValueError, json.JSONDecodeError) as exc:
            return json.dumps({
                "status": "error",
                "error": f"instances must be a JSON array of objects: {exc}",
                "example": ('[{"name": "relative-dir-posix-1", "behaviour": '
                            '"ignore-paths on a relative directory", '
                            '"dimensions": {"path_form": "relative"}}]')}, indent=2)
        return json.dumps(research.add_instances(topic, rows), indent=2)

    @mcp.tool()
    def research_split(topic: str, seed: int = 0) -> str:
        """Assign every instance to train / validate / test. Deterministic.

        Stratified by the declared dimensions, so each phase covers the axes
        instead of, say, putting every Windows case in train. The assignment is a
        hash of instance name and seed, so the same corpus always splits the same
        way — a split that moves between calls makes "held out" meaningless.

        Returns JSON: {status, seed, counts, strata, next}.
        """
        from phronix import research

        return json.dumps(research.split(topic, seed), indent=2)

    @mcp.tool()
    def research_coverage(topic: str) -> str:
        """How well the corpus covers the declared axes, and where it is thin.

        Per-value counts rather than one diversity score: a score hides which
        axis is unrepresented, and an axis with a single value is a constant that
        happens to be written down.

        Returns JSON: {status, instances, target, meets_target, by_dimension,
        uncovered_values, instances_without_dimensions}.
        """
        from phronix import research

        return json.dumps(research.coverage(topic), indent=2)

    @mcp.tool()
    def research_add_instance(topic: str, name: str, behaviour: str,
                              command: str = "", expected: str = "",
                              source: str = "") -> str:
        """Author a task instance in one of: train, validate, test.

        Instances are small, cheap, concrete cases that exhibit the behaviour —
        a reproducer, an input with a known result, a command whose output you
        can check. They are how an approach gets evidence without being built
        for real.

        The phases are not interchangeable:

        - **train** — discovery. Poke the behaviour, find out what governs it,
          derive candidate approaches. Failing here means nothing.
        - **validate** — refinement. Tune and compare approaches against these.
          Rework as much as you like; that is what the phase is for.
        - **test** — correctness, on cases the approach was never shaped
          against. Touched once, at the end. **Only this phase falsifies**, and
          an approach that skips it has shown only that it can be tuned.

        One case at a time. For a corpus, use ``research_add_instances``.

        Returns JSON: {status, added, total, target, next}.
        """
        from phronix import research

        return json.dumps(
            research.add_instance(topic, name, behaviour, command, expected,
                                  source=source), indent=2)

    @mcp.tool()
    def research_observe(what: str, worked: bool, detail: str = "",
                         topic: str = "", stage: str = "") -> str:
        """Report that something worked, or did not. Costs a file append.

        **Call this whenever you learn something the next task would want.** A
        technique that fixed a class of cases, a tool whose output needed
        massaging, an approach that looked right and was not.

        A background learner drains these, looks for what repeats across tasks,
        and turns the repeats into skill lessons and `probe_` tools. It never
        blocks you: writing is an append, and nothing waits on the learner.

        ``worked=false`` is the more valuable report and the one nobody writes
        down. An approach recorded as a dead end costs the next task a sentence;
        unrecorded it costs an attempt.

        Returns JSON: {status, recorded, worked}.
        """
        from phronix import research

        return json.dumps(
            research.observe(what, worked, detail, topic, stage), indent=2)

    @mcp.tool()
    def research_notice(since: float = 0.0, limit: int = 200) -> str:
        """What has been reported lately, grouped by what repeated.

        The read side of ``research_observe``. Arithmetic, not a model call:
        observations are grouped by shape, so this answers "has this been said
        before, and by how many different stages" without spending an agent.

        Read this before writing a lesson. A finding that appears once is an
        anecdote; the same finding from two stages or two tasks is a pattern,
        and the group tells you which you have.

        Args:
            since: unix time; 0 for everything on record.
            limit: how many raw observations to consider.

        Returns JSON: {status, groups, repeats, latest, considered}.
        """
        from phronix import research

        return json.dumps(
            research.notice(since, research.observations(since, limit)),
            indent=2)

    @mcp.tool()
    def research_record_trial(topic: str, approach: str, instance: str,
                              passed: bool, detail: str = "") -> str:
        """Record how one approach fared on one instance.

        Record the failures too. An approach whose record contains no failed
        trial anywhere has usually not been tried hard enough to be believed,
        and the failures are what stop a later session re-deriving a dead end.

        Returns JSON: {status, approach, instance, phase, passed}.
        """
        from phronix import research

        return json.dumps(
            research.record_trial(topic, approach, instance, passed, detail),
            indent=2)

    @mcp.tool()
    def research_evaluate_approach(topic: str, approach: str) -> str:
        """Aggregate an approach's trials and set its status. Deterministic.

        ``confirmed`` (passes validate and the unseen test set) is the only
        status that licenses writing the approach up as a skill and using it.
        ``validated`` means tuned but not yet checked against unseen instances.
        ``falsified`` means it failed the unseen set. ``potential`` means the
        evidence is not there yet.

        Returns JSON: {status, approach_status, phases, reason}.
        """
        from phronix import research

        return json.dumps(research.evaluate_approach(topic, approach), indent=2)

    @mcp.tool()
    def research_set_aspects(topic: str, aspects: str) -> str:
        """Record the research plan: which aspects to investigate, before starting.

        ``aspects`` is a JSON array of ``{name, question, where?}``. Each aspect
        is a distinct place the answer could be — the project's own history, the
        code path that consumes the value, the one that produces it, the
        configuration that governs it.

        Naming them first is what makes parallel investigation productive rather
        than duplicative: investigators without assigned angles produce several
        versions of the same first idea. It also makes an uninvestigated aspect
        visible as a gap instead of an absence nobody noticed.

        Returns JSON: {status, aspects, next}.
        """
        from phronix import research

        try:
            rows = json.loads(aspects)
            if not isinstance(rows, list):
                raise ValueError("aspects must be a JSON array")
        except (ValueError, json.JSONDecodeError) as exc:
            return json.dumps({
                "status": "error",
                "error": f"aspects must be a JSON array of objects: {exc}",
                "example": ('[{"name": "upstream-history", "question": "was this '
                            'fixed upstream, and in which function?"}]')}, indent=2)
        return json.dumps(research.set_aspects(topic, rows), indent=2)

    @mcp.tool()
    def research_prior(question: str, limit: int = 4) -> str:
        """What is ALREADY on record about this. Call this before researching.

        Research carries across runs now, so by the third task on a subsystem
        the store holds earlier records, a playbook skill and a set of
        approaches that have been tried. Every other lookup here is keyed on the
        current topic — which is new by construction — so without this one a
        pass opens by surveying a subject the library already covers.

        Searches the skill index, every research record's own vocabulary, and
        which aspects are settled. Returns what was tried, what worked, what was
        refuted, and which ground only needs re-checking.

        Use `graph_query` alongside it to reach related subjects this does not
        name — the graph indexes every layer's skills and research, so it finds
        neighbours that share no vocabulary with your question.

        Returns JSON: {status, skills, topics, already_tried, known_working,
        known_refuted, settled_aspects, advice}.
        """
        from phronix import research

        return json.dumps(research.prior_work(question, limit), indent=2)

    @mcp.tool()
    def research_playbook(topic: str, skill: str = "") -> str:
        """Write the execution plan as the skill that solves this task. Final stage.

        The plan is not a document — it is a skill, built from everything the
        research collected: the figure of merit and how to measure it, the
        sources, the aspects investigated, the approaches tried and refuted, and
        the surviving approaches in measured order.

        A document is scoped to one task and dies with the run. A skill is filed
        under the *subject*, so the next task in the same area retrieves it
        instead of paying for the same survey, the same aspects and the same
        evaluation again.

        Every approach is written as *potential*, the leader included. Ranking
        well on a corpus this same session authored is a reason to try it first,
        not evidence that it is correct. `research_mark_working` promotes one
        once a task has actually passed with it.

        Deterministic: it reads the record and writes the blocks. Call it once
        the evaluation stage has finished.

        Returns JSON: {status, skill, ordered: [approach names, best first]}.
        """
        from phronix import research

        return json.dumps(research.playbook(topic, skill), indent=2)

    @mcp.tool()
    def research_approach(topic: str, key: str) -> str:
        """One approach in full, by its key (A1, A2, ...) or its name.

        The plan lists candidates by key with a one-line summary. Ask for the
        detail of the one you are ON — hypothesis, where the change goes, the
        evidence behind it — and not the others. You will only ever need the
        next one if this one fails, and most tasks are solved by the first.

        Returns JSON: {status, approach: {...}}.
        """
        from phronix import research

        return json.dumps(research.approach_detail(topic, key), indent=2)

    @mcp.tool()
    def research_dead_approaches(topic: str) -> str:
        """Approaches that must never be proposed again for this topic.

        Anything a real task tried and lost with, plus anything evaluation
        falsified. `research_add_approach` refuses these names outright — this
        tool is how you find out what they are before wasting a proposal on one.

        A failure here means the *class* of fix was wrong, so the useful response
        is to look somewhere genuinely different: a different layer, a different
        mechanism, a different reading of the issue, or how the project fixed it
        upstream. Renaming a dead approach costs another full attempt to
        rediscover the same result.

        Returns JSON: {topic, dead: [names]}.
        """
        from phronix import research

        return json.dumps({"topic": topic,
                           "dead": research.dead_approaches(topic)}, indent=2)

    @mcp.tool()
    def research_mark_working(topic: str, approach: str = "") -> str:
        """Record that a task actually passed using this approach.

        The one promotion the playbook withholds, because it is the only
        evidence that distinguishes "scored well on cases we wrote ourselves"
        from "solved the real problem". Defaults to the top-ranked approach.

        Returns JSON: {status, approach, new_status}.
        """
        from phronix import research

        return json.dumps(research.mark_working(topic, approach), indent=2)

    @mcp.tool()
    def research_rank(topic: str) -> str:
        """Order the approaches by their measured score. Arithmetic, no judgement.

        Unscored approaches sort last — an approach nobody evaluated is unknown,
        not promising. Use this after the evaluation stage and before writing the
        execution plan, so the plan is written for the approach that actually led
        rather than the one that read best.

        Returns JSON: {status, metric, ranking: [{name, score, status,
        hypothesis}], best, unscored}.
        """
        from phronix import research

        return json.dumps(research.rank_approaches(topic), indent=2)

    @mcp.tool()
    def research_select(topic: str) -> str:
        """Which approach to act on now. Always answers when any candidate exists.

        Returns the best available with its status and what that status is worth:
        ``confirmed`` passed the held-out instances, ``validated`` passed tuning
        only, ``potential`` is the best current evidence and not yet confirmed.

        "No approach selected" is not a usable answer to "what do I do now" — the
        attempt implements *something* regardless, and refusing to name a
        candidate just moves the decision somewhere unrecorded.

        When every candidate has been falsified it returns ``exhausted`` with a
        direction: the unexplored aspects and the hypotheses already ruled out.
        That is a cue to widen the search, never to give up — each falsified
        hypothesis has narrowed where the cause can be.

        Returns JSON: {status, selected, approach_status, hypothesis, confidence,
        alternatives} or {status: exhausted, unexplored_aspects, next}.
        """
        from phronix import research

        return json.dumps(research.select(topic), indent=2)

    @mcp.tool()
    def research_backups(topic: str) -> str:
        """Approaches still worth trying, best-first — what a retry starts from.

        **Call this before researching anything on a retry.** Previous research
        already found and partly evaluated alternatives; starting over rederives
        the same ideas at full cost. Confirmed and falsified approaches are
        excluded — one is finished and the other is settled.

        Returns JSON: {status, count, backups: [{name, summary, status, trials}]}.
        """
        from phronix import research

        found = research.backups(topic)
        return json.dumps({"status": "ok", "count": len(found),
                           "backups": found}, indent=2)

    @mcp.tool()
    def research_ruled_out(topic: str) -> str:
        """Where NOT to look: locations already tried that did not work.

        **Call this before choosing where to edit on any retry.** Derived from
        recorded facts — the files each attempt changed and the number the tests
        returned — so it stays correct however many attempts have run and
        regardless of what anyone remembers.

        Several failed attempts against one location is the signal that the
        approach is wrong rather than the execution. Treat it as evidence to look
        at the surrounding code paths: the helper being called, the caller, or
        where the inputs are normalised.

        Returns JSON: {status, ruled_out: [{locations, attempts, best}], worked,
        total_attempts, advice}.
        """
        from phronix import research

        return json.dumps(research.ruled_out(topic), indent=2)

    @mcp.tool()
    def research_status(topic: str = "") -> str:
        """What has been researched, and what is still missing.

        With no topic, lists every topic on record. With one, reports approaches,
        the choice, and the gaps — unmeasured approaches, deterministic steps
        with no capability built. A half-finished record that looks complete is
        worse than none, because the next session trusts it and skips the work.

        Returns JSON: {status, topic, approaches, chosen, steps, complete, ...}.
        """
        from phronix import research

        if not topic.strip():
            topics = research.list_topics()
            return json.dumps({"status": "ok", "count": len(topics),
                               "topics": topics}, indent=2)
        return json.dumps(research.status(topic), indent=2)
