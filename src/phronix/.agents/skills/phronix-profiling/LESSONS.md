# Lessons — phronix-profiling

Pitfalls and dated lessons for the **measuring what a session costs, per step** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — Launching the harness without the env exported

The single most common cause of an empty profile. The collector is up, the tools
answer, and nothing is ever recorded — because the harness was started before
`eval "$(phronix_stack env)"` and exports no telemetry.

### P2 — A step id that varies between attempts

Appending a timestamp or an attempt number to the step id defeats retry folding:
each attempt becomes its own cheap-looking step and the real cost of the work
disappears into the noise.

### P3 — Reading a total that has a large unattributed share

If most of the cost is unattributed, the per-step table is describing a minority
of the session. Fix the brackets before drawing conclusions from it.

## Lessons
