"""A controlled benchmark: does phronix's self-learning measurably help?

Four arms on SWE-bench, one model (`livai/claude-sonnet-4.5`), one fixed task
order, podman isolation per attempt:

===========================  ==========================================
mini                         mini-swe-agent's own agent (reference)
opencode-bare                opencode alone (baseline)
opencode-phronix-frozen      phronix scaffolding, store read-only (control)
opencode-phronix             phronix scaffolding, store accumulating
===========================  ==========================================

The control arm is what makes the result interpretable: phronix changes two
things at once — it adds scaffolding *and* it learns — and only a frozen-store
arm separates them. See ``README.md`` for the methodology and the threats to
validity.

Modules are split so that the part most likely to be subtly wrong — the
statistics — is pure and directly testable, independent of containers, network
and harnesses:

``metrics``    per-task records, slopes, reuse rate, the comparison verdict
``tasks``      pinning and loading the instance list
``isolation``  podman containers per attempt, fresh skill store per run
``arms``       what each arm actually executes
``runner``     the loop, and the ledger that makes reuse checkable
``report``     tables a person can argue with
``cli``        ``phronix-bench tasks|run|report``
"""
from __future__ import annotations

__all__ = ["arms", "cli", "isolation", "metrics", "report", "runner", "tasks"]
