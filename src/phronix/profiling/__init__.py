"""Session profiling: what each step of a session cost, in money, tokens and time.

The framework's central bet is that converting judgment into deterministic tools
makes sessions cheaper and more reproducible. That is a measurable claim, and
this package is what measures it.

The chain, end to end:

1. Claude Code exports OTLP telemetry when ``CLAUDE_CODE_ENABLE_TELEMETRY=1``
   (:mod:`phronix.profiling.otlp` parses it — stdlib, no protobuf).
2. The collector receives it and attributes each event to whichever step window
   contains it (:mod:`phronix.profiling.collector`).
3. Steps aggregate into a run profile, with retries folded into the step they
   retried (:mod:`phronix.profiling.aggregate`).
4. The profile is rendered to markdown and pushed to MLflow, one nested run per
   step (:mod:`phronix.profiling.mlflow_sink`).

The step's **model level** is recorded alongside its cost. That is the pairing
that makes the complexity tier falsifiable: it turns "this agent should be
``level_3``" from an assertion into something you can check against what
``level_3`` actually spent.

Everything degrades rather than fails. No collector running means the
``profile_*`` tools report ``disabled``; no MLflow means the profile is still
written to disk and still reportable. Profiling must never be the reason a
session breaks.
"""
from __future__ import annotations

__all__ = ["aggregate", "collector", "mlflow_sink", "otlp"]
