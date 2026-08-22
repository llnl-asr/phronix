---
name: phronix-profiling
description: Session profiling: binding a run, bracketing steps, reading the per-step cost table, and what the unattributed/retry/cross-check figures mean. Load before profiling a session or interpreting a profile report.
subject: measuring what a session costs, per step
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Export the env before launching the harness |
| `I2` | Instructions | Bind once, as early as possible |
| `I3` | Instructions | Bracket every step, with its model level |
| `I4` | Instructions | Read the report, not just the total |
| `R1` | Rules | Report the real status of a step |
| `R2` | Rules | Profiling never fails a session |
| `R3` | Rules | Per-step attribution is exact only for sequential work |
| `R4` | Rules | Never restart the collector mid-session |
| `X1` | References | What the level in the report is for |
| `X2` | References | Deploying the stack that runs the collector |

## Instructions

### I1 — Export the env before launching the harness

```
eval "$(phronix_stack env)" && claude
```

This is the step that is skipped and then puzzled over. Without `OTEL_*` set in
the harness's own environment, it exports no telemetry at all — the collector
receives nothing and the profile stays empty. Exporting afterwards does not help;
the harness reads them at startup.

### I2 — Bind once, as early as possible

`profile_bind(run_id=..., tags={...})` at the moment the session gets an
identity. Everything before the bind is unattributed.

Rebinding the SAME id is a safe no-op that keeps the profile — call it
defensively. Binding a DIFFERENT id starts fresh and abandons the previous one.

### I3 — Bracket every step, with its model level

```
profile_step_begin(step="STEP 1: retrieve", agent="phronix-router", model_level="level_2")
...
profile_step_end(step="STEP 1: retrieve", status="ok")
```

Reuse the step id EXACTLY on a retry — that is what folds the attempts together
instead of showing three cheap steps where one expensive one happened.

Pass `model_level`. Recording it next to the cost is what makes the complexity
tier checkable rather than merely asserted.

### I4 — Read the report, not just the total

`profile_report()` writes a per-step table sorted by cost. Three figures matter
more than the headline number:

- **Unattributed** — work that fell outside every step window. Large means the
  brackets are wrong, and the per-step split is describing less than it appears.
- **Retries** — which steps ran more than once, and what that cost.
- **cross_check.events_dropped** — the event totals disagree with Claude Code's
  independent counters, so telemetry was lost and the bill is understated.

## Rules

### R1 — Report the real status of a step

A step that failed and is recorded as `ok` makes the profile agree with a story
that did not happen, and the retry that follows then looks like a first attempt.
Use `failed`, `partial` or `skipped` honestly — the profile is evidence.

### R2 — Profiling never fails a session

Every profile tool degrades to `disabled` when no collector is running, and the
report is written to disk whether or not MLflow is reachable. If a profiling call
ever blocks the work, that is a bug in the profiling, not a reason to skip the
step.

### R3 — Per-step attribution is exact only for sequential work

Events are attributed by wall-clock to whichever open step window contains them.
Totals are always correct — nothing is double-counted or dropped — but with two
genuinely parallel steps open, the split between them is an estimate. Say so when
reporting parallel work rather than implying a precision the data lacks.

### R4 — Never restart the collector mid-session

The profile lives in memory. `phronix_stack start` deliberately leaves a healthy
collector alone for this reason; `restart` will bounce it and discard the cost
accounting for every step so far.

## References

### X1 — What the level in the report is for

Cost next to level is what makes a level recommendation falsifiable:
[[phronix-complexity#R2]].

### X2 — Deploying the stack that runs the collector

[[phronix-deployment#I2]].
