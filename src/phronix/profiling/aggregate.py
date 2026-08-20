"""Aggregate OTLP events into a per-step profile.

Telemetry knows nothing about phronix's notion of a step. It knows
``agent.name``, timestamps, and how much each API call cost. The bridge is
wall-clock: an agent brackets its work with ``profile_step_begin`` /
``profile_step_end``, and every event whose timestamp falls inside that window is
attributed to that step.

That attribution is approximate in one specific way, and it is better to say so
than to imply a precision the data does not have: **concurrent steps overlap**.
If two subagents run in parallel, an event lands in whichever open step's window
contains it, and with two open windows the earlier-opened one wins. Cost totals
stay correct — no event is double-counted or dropped — but a per-step split
across genuinely parallel work is an estimate. Sequential pipelines, which is
what the step model is for, are exact.

A **retry** is a step id that is begun more than once. Recording it as a retry
rather than a new step is what makes "this step cost $4 across three attempts"
visible instead of appearing as three cheap steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from phronix.profiling.otlp import as_num


def _bump(counter: Dict[str, int], key: Optional[str], amount: int = 1) -> None:
    if key:
        counter[str(key)] = counter.get(str(key), 0) + amount


@dataclass
class StepProfile:
    """Everything measured for one step, across all of its attempts."""

    step: str
    agent: str = ""
    model_level: str = ""
    started_ns: int = 0
    ended_ns: int = 0
    status: str = "running"
    attempts: int = 1
    notes: str = ""

    cost_usd: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_cache_read: int = 0
    tokens_cache_creation: int = 0

    api_calls: int = 0
    api_errors: int = 0
    api_duration_ms: float = 0.0
    tool_calls: int = 0
    tool_failures: int = 0
    tool_duration_ms: float = 0.0
    mcp_tool_calls: int = 0
    compactions: int = 0
    prompts: int = 0

    models: Dict[str, int] = field(default_factory=dict)
    agents: Dict[str, int] = field(default_factory=dict)
    tools: Dict[str, int] = field(default_factory=dict)
    skills: Dict[str, int] = field(default_factory=dict)

    @property
    def tokens_total(self) -> int:
        return (self.tokens_input + self.tokens_output
                + self.tokens_cache_read + self.tokens_cache_creation)

    @property
    def duration_s(self) -> float:
        if not self.started_ns:
            return 0.0
        end = self.ended_ns or self.started_ns
        return max(0.0, (end - self.started_ns) / 1e9)

    def contains(self, ts_ns: int) -> bool:
        """Whether *ts_ns* falls in this step's window.

        An open step (no end yet) extends to now, so events arriving during a
        running step are attributed immediately rather than only on close —
        ``profile_status`` is meant to be useful mid-run.
        """
        if not ts_ns or not self.started_ns:
            return False
        return ts_ns >= self.started_ns and (not self.ended_ns or ts_ns <= self.ended_ns)

    def absorb(self, record: Dict[str, Any]) -> None:
        """Fold one parsed OTLP event into this step's totals."""
        name = record.get("name")

        if name == "claude_code.api_request":
            self.api_calls += 1
            self.cost_usd += as_num(record.get("cost_usd"))
            self.api_duration_ms += as_num(record.get("duration_ms"))
            self.tokens_input += int(as_num(record.get("input_tokens")))
            self.tokens_output += int(as_num(record.get("output_tokens")))
            self.tokens_cache_read += int(as_num(record.get("cache_read_tokens")))
            self.tokens_cache_creation += int(as_num(record.get("cache_creation_tokens")))
            _bump(self.models, record.get("model"))
            _bump(self.agents, record.get("agent.name") or record.get("query_source"))

        elif name in ("claude_code.api_error", "claude_code.api_retries_exhausted"):
            self.api_errors += 1
            self.api_duration_ms += as_num(record.get("duration_ms"))

        elif name == "claude_code.tool_result":
            tool = str(record.get("tool_name") or "unknown")
            self.tool_calls += 1
            _bump(self.tools, tool)
            self.tool_duration_ms += as_num(record.get("duration_ms"))
            if tool.startswith("mcp__"):
                self.mcp_tool_calls += 1
            # OTLP hands booleans through as strings often enough that testing the
            # string form is the reliable check.
            if str(record.get("success", "true")).lower() not in ("true", "1"):
                self.tool_failures += 1

        elif name == "claude_code.user_prompt":
            self.prompts += 1
        elif name == "claude_code.compaction":
            self.compactions += 1
        elif name == "claude_code.skill_activated":
            _bump(self.skills, record.get("skill.name"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step, "agent": self.agent, "model_level": self.model_level,
            "status": self.status, "attempts": self.attempts, "notes": self.notes,
            "duration_s": round(self.duration_s, 2),
            "cost_usd": round(self.cost_usd, 6),
            "tokens_total": self.tokens_total,
            "tokens_input": self.tokens_input, "tokens_output": self.tokens_output,
            "tokens_cache_read": self.tokens_cache_read,
            "tokens_cache_creation": self.tokens_cache_creation,
            "api_calls": self.api_calls, "api_errors": self.api_errors,
            "api_duration_s": round(self.api_duration_ms / 1000.0, 2),
            "tool_calls": self.tool_calls, "tool_failures": self.tool_failures,
            "mcp_tool_calls": self.mcp_tool_calls,
            "tool_duration_s": round(self.tool_duration_ms / 1000.0, 2),
            "compactions": self.compactions, "prompts": self.prompts,
            "models": self.models, "agents": self.agents,
            "tools": dict(sorted(self.tools.items(), key=lambda kv: -kv[1])[:10]),
            "skills": self.skills,
        }


@dataclass
class RunProfile:
    """A whole session: its steps, its totals, and the events that missed a step."""

    run_id: str
    started_ns: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    steps: List[StepProfile] = field(default_factory=list)

    #: Events arriving outside any step window. Counted, never discarded: a large
    #: unattributed cost means the step brackets are wrong, and silently dropping
    #: it would make the profile look complete while under-reporting the bill.
    unattributed: StepProfile = field(
        default_factory=lambda: StepProfile(step="(unattributed)", status="n/a"))

    #: Independent totals from the metric stream, for the cross-check.
    metric_cost_usd: float = 0.0
    metric_tokens: int = 0
    #: Whether a metric stream arrived at all. Without this, a setup exporting
    #: only logs shows metric totals of zero and the cross-check reports every
    #: session as "events dropped" — a permanent false alarm, which is the fastest
    #: way to train people to ignore a warning that will one day be real.
    metric_records: int = 0

    def open_step(self, step: str, agent: str = "", model_level: str = "",
                  ts_ns: int = 0) -> StepProfile:
        """Begin *step*, or reopen it as a retry if it has run before."""
        existing = self.find(step)
        if existing is not None:
            existing.attempts += 1
            existing.status = "running"
            existing.ended_ns = 0
            if agent:
                existing.agent = agent
            if model_level:
                existing.model_level = model_level
            return existing
        profile = StepProfile(step=step, agent=agent, model_level=model_level,
                              started_ns=ts_ns)
        self.steps.append(profile)
        return profile

    def close_step(self, step: str, status: str = "ok", notes: str = "",
                   ts_ns: int = 0) -> Optional[StepProfile]:
        profile = self.find(step)
        if profile is None:
            return None
        profile.ended_ns = ts_ns
        profile.status = status
        profile.notes = notes
        return profile

    def find(self, step: str) -> Optional[StepProfile]:
        for profile in self.steps:
            if profile.step == step:
                return profile
        return None

    def absorb(self, record: Dict[str, Any]) -> None:
        """Attribute one record to whichever step window contains it."""
        if record.get("kind") == "metric":
            self.metric_records += 1
            if record.get("name") == "claude_code.cost.usage":
                self.metric_cost_usd += as_num(record.get("value"))
            elif record.get("name") == "claude_code.token.usage":
                self.metric_tokens += int(as_num(record.get("value")))
            return

        ts_ns = int(record.get("ts_ns") or 0)
        for profile in self.steps:
            if profile.contains(ts_ns):
                profile.absorb(record)
                return
        self.unattributed.absorb(record)

    def totals(self) -> Dict[str, Any]:
        total = StepProfile(step="(total)")
        for profile in [*self.steps, self.unattributed]:
            for attr in ("cost_usd", "tokens_input", "tokens_output",
                         "tokens_cache_read", "tokens_cache_creation",
                         "api_calls", "api_errors", "api_duration_ms",
                         "tool_calls", "tool_failures", "tool_duration_ms",
                         "mcp_tool_calls", "compactions", "prompts"):
                setattr(total, attr, getattr(total, attr) + getattr(profile, attr))
            for source, target in ((profile.models, total.models),
                                   (profile.agents, total.agents),
                                   (profile.tools, total.tools),
                                   (profile.skills, total.skills)):
                for key, count in source.items():
                    _bump(target, key, count)
        return total.to_dict()

    def drift(self) -> Dict[str, Any]:
        """Compare event-derived totals against the independent metric counters.

        A gap means events were dropped in transit, which understates the bill.
        Reported rather than reconciled: quietly substituting the larger number
        would hide a broken telemetry path.
        """
        totals = self.totals()
        event_cost = totals["cost_usd"]

        if not self.metric_records:
            return {
                "event_cost_usd": round(event_cost, 6),
                "metric_cost_usd": 0.0,
                "gap_usd": 0.0,
                "events_dropped": False,
                "checked": False,
                "note": ("No metric stream arrived, so the event totals could not be "
                         "cross-checked. Set OTEL_METRICS_EXPORTER=otlp (the stack's "
                         "`env` does) to enable the check."),
            }

        gap = self.metric_cost_usd - event_cost
        significant = abs(gap) > max(0.01, 0.05 * max(event_cost, self.metric_cost_usd))
        return {
            "event_cost_usd": round(event_cost, 6),
            "metric_cost_usd": round(self.metric_cost_usd, 6),
            "gap_usd": round(gap, 6),
            "events_dropped": significant,
            "checked": True,
            "note": ("Event and metric totals disagree by more than 5% — events were "
                     "dropped in transit and the per-step costs understate the real "
                     "bill." if significant else "Event and metric totals agree."),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "tags": self.tags,
            "steps": [s.to_dict() for s in self.steps],
            "unattributed": self.unattributed.to_dict(),
            "totals": self.totals(),
            "cross_check": self.drift(),
        }
