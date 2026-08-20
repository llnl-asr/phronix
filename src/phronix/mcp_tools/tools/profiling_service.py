"""Profiling tools: what each step of a session actually cost.

The framework claims that converting judgment into deterministic tools makes
sessions cheaper. These tools are what turns that claim into a number you can
check — per step, with the model level recorded next to the cost.

All five degrade to ``disabled`` when no collector is running. Profiling observes
the work; it must never be the reason a session fails.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional


def register(mcp: Any) -> None:
    @mcp.tool()
    def profile_bind(run_id: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Start profiling this session. Call once, as early as possible.

        Everything before the bind is unattributed, so bind at the moment the
        session gets an identity rather than at the first expensive step.

        Rebinding to the SAME `run_id` is a safe no-op that keeps the profile so
        far — call it defensively if you are unsure. Binding to a DIFFERENT id
        starts a fresh profile and abandons the previous one.

        Args:
            run_id: a stable identifier for this session.
            tags: free-form labels recorded on the MLflow parent run — project,
                branch, workload, whatever you will want to filter by later.

        Returns JSON: {status, run_id, raw_capture} or {status: "disabled", hint}.
        ``disabled`` means no collector is listening; the session is unaffected.
        """
        from phronix.profiling import client

        return json.dumps(client.bind(run_id, tags), indent=2)

    @mcp.tool()
    def profile_step_begin(step: str, agent: str = "", model_level: str = "") -> str:
        """Open a step window. Every event until `profile_step_end` is attributed here.

        **Use the step's exact name consistently.** Beginning a step id that has
        run before is recorded as a *retry* of that step, not as a new one — which
        is what makes "this step cost $4 across three attempts" visible instead of
        looking like three cheap steps.

        **Pass `model_level`.** Recording the level alongside the cost is the whole
        point: it is what lets you check afterwards whether the level the
        complexity tier recommended was actually the right call, rather than
        assuming it.

        Args:
            step: a stable step id — reuse it exactly on a retry.
            agent: which agent runs this step.
            model_level: the level it is running at (level_1 … level_4).

        Returns JSON: {status, step, attempt, retry}. ``retry: true`` means this id
        had already run.
        """
        from phronix.profiling import client

        return json.dumps(client.step_begin(step, agent, model_level), indent=2)

    @mcp.tool()
    def profile_step_end(step: str, status: str = "ok", notes: str = "") -> str:
        """Close a step window and return what it cost.

        **Report the real status.** A step that failed and is recorded as `ok`
        makes the profile agree with a story that did not happen, and the retry
        that follows then looks like a first attempt. Use `failed`, `partial`, or
        `skipped` honestly — the profile is evidence, and laundering it destroys
        the only record of what the work actually took.

        Args:
            step: the id passed to `profile_step_begin`.
            status: ok | failed | partial | skipped.
            notes: anything worth knowing when reading the profile later.

        Returns JSON: the step's totals — cost_usd, tokens, api_calls, tool_calls,
        duration_s, attempts.
        """
        from phronix.profiling import client

        return json.dumps(client.step_end(step, status, notes), indent=2)

    @mcp.tool()
    def profile_status() -> str:
        """Cheap running totals: cost, tokens, steps, and which are still open.

        Safe to call often — it reads in-memory state and touches no disk. Use it
        mid-session to see what the work is costing before it is finished, and to
        catch a step you forgot to close (`open_steps`).

        ``cross_check`` compares the event-derived total against Claude Code's
        independent metric counters. If ``events_dropped`` is true, some telemetry
        was lost in transit and the per-step costs understate the real bill —
        reported rather than papered over, because a quietly wrong cost report is
        worse than an obviously missing one.

        Returns JSON: {status, run_id, bound, steps, open_steps, totals, cross_check}.
        """
        from phronix.profiling import client

        return json.dumps(client.status(), indent=2)

    @mcp.tool()
    def profile_report(mlflow: bool = True) -> str:
        """Write the session profile and push it to MLflow. Call once, at the end.

        Produces `profile.md` (a per-step cost table, most expensive first) and
        `profile.json`, and — when MLflow is configured — one parent run with a
        nested run per step, so you can sort by cost in the UI.

        Read the result before you report the session as done:

        - **Unattributed cost** means work fell outside every step window: steps
          that were never begun, or main-thread work between them.
        - **Retries** show which steps ran more than once and what that cost.
        - **`cross_check.events_dropped`** means the numbers are incomplete.

        Args:
            mlflow: also push to MLflow. Set False for a local-only report.

        Returns JSON: {status, run_id, report, json, totals, cross_check, mlflow}.
        A `mlflow.status` of "unavailable" just means the extra is not installed —
        the on-disk report is unaffected.
        """
        from phronix.profiling import client

        return json.dumps(client.report(mlflow), indent=2)
