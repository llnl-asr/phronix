"""Complexity tools: choose the model level from what the work actually requires.

Agents declare a capability level, not a model id. As the store grows — rules
accumulate, pitfalls pile up, procedures become tools — the level an agent needs
moves. These tools measure that, deterministically, so the answer can be checked
rather than guessed.

The direction of each signal is the framework's thesis in numbers: knowledge
accumulating in prose raises the requirement, and knowledge converted into
deterministic tools lowers it.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional


def register(mcp: Any) -> None:
    @mcp.tool()
    def complexity_assess(agent: str = "", task: str = "",
                          skills: Optional[List[str]] = None,
                          tools: Optional[List[str]] = None) -> str:
        """Recommend a model level from the measured complexity of an agent or a task.

        **Use before dispatching non-trivial work**, and whenever you are unsure
        which level something needs. The answer is computed from counts over the
        store — no model in the loop — so it is the same on every machine and you
        can check the arithmetic.

        Pass `agent` to assess a defined agent against its declared level, or
        `task` (with optional `skills` and `tools`) to assess ad-hoc work.

        What raises the requirement:

        - **reasoning_demand** — rules and instructions in the subjects involved.
          Rules count double: an instruction says what to do next, a rule says
          what would make an otherwise-reasonable action wrong, and weighing those
          against each other is the thinking a stronger model buys.
        - **failure_surface** — pitfalls and lessons. Many recorded traps means the
          naive path is wrong in ways that are not locally visible.
        - **unverified_fraction** — subjects with no corrector. Where a claim can
          be checked, an agent can act and verify; where it cannot, it has to be
          right by reasoning.
        - **integration_breadth** — distinct subjects plus cross-references.
        - **instruction_load** — length of the agent's own prompt.

        What lowers it:

        - **tool_coverage** — the fraction of tools that are MCP capabilities. This
          is the lever the framework is built around: every deterministic procedure
          turned into a tool is judgment the model no longer supplies. An agent
          that mostly calls well-specified tools is doing orchestration.

        Args:
            agent: name of a defined agent to assess.
            task: free-text description of ad-hoc work.
            skills: subjects the task touches (inferred from `task` when omitted).
            tools: tools that will be available to it.

        Returns JSON: {status, recommended_level, recommended_effort, score,
        declared_level, drift, raw, signals, drivers}. Read `drivers` — it lists
        each signal's contribution largest-first with the counts behind it, so a
        recommendation you disagree with can be argued with rather than overridden
        blindly.
        """
        from phronix.complexity import assess_agent, assess_task

        try:
            if agent:
                return json.dumps(assess_agent(agent), indent=2)
            if task:
                return json.dumps(assess_task(task, skills, tools), indent=2)
            return json.dumps({"status": "error",
                               "error": "pass either agent= or task="})
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})

    @mcp.tool()
    def complexity_reassess() -> str:
        """Re-assess every agent and report which have drifted from their declared level.

        **Run this at the end of any session that changed the store** — recorded a
        lesson, added a rule, built a capability. Those are exactly the events that
        move an agent's requirement, and without reassessment it keeps running at
        whatever level it was written with, indefinitely.

        Two directions, and both matter:

        - **Drift upward** — the subject accumulated rules and pitfalls, so there is
          more to weigh. The agent is now under-powered for its own scope.
        - **Drift downward** — enough of the work became MCP capabilities that the
          agent is mostly orchestrating. This is the outcome to aim for, and it is
          a real saving that goes unclaimed unless something notices.

        Returns JSON: {status, assessed, drifted, drift: [{agent, declared,
        recommended, score, top_driver}], all, next}. Read the drivers before
        changing a level; then apply with `agent_define(model_level=...)`.
        """
        from phronix.complexity import reassess_all

        try:
            return json.dumps(reassess_all(), indent=2)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})

    @mcp.tool()
    def complexity_impact(skill: str) -> str:
        """After changing a subject, report which agents may now need a different level.

        Call this straight after `skill_write`, `skill_write_lesson` or
        `skill_define`. A lesson recorded into a subject changes the judgment
        burden of every agent that loads it — this names them and says whether the
        change moved any of their assessed levels.

        This is the step that closes the self-learning loop. Without it, learning
        accumulates in the skills and the agents that depend on them silently fall
        out of calibration.

        Returns JSON: {skill, agents_affected, level_drift, note}.
        """
        from phronix.complexity import impact_of

        try:
            return json.dumps(impact_of(skill), indent=2)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
