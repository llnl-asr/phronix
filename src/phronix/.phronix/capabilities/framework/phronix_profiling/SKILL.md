---
name: phronix_profiling
description: Profile an agent session: export the OTEL env before launching the harness, bind the run once, bracket every step with its model level (same step id on retries), and read the per-step report (unattributed share, retries, cross_check.events_dropped). Load before profiling a session or interpreting a profile_report, or when the profile is empty, most cost is unattributed, or events were dropped.
---
Cross-references: [[phronix_complexity]], [[phronix_deployment]], [[phronix_verification]]

# Profiling: what a session costs, per step

Converted from the dftracer-agents skill `phronix-profiling` (subject: measuring what a session costs, per step). Source description: Session profiling: binding a run, bracketing steps, reading the per-step cost table, and what the unattributed/retry/cross-check figures mean. Load before profiling a session or interpreting a profile report.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

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

### Using the tools (capability)

- Render the procedure with `phronix_profiling_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `run_id`, `env_exported_before_launch`, `steps`, `unattributed_fraction`, `events_dropped`, `parallel`, `parallel_noted`, `collector_restarted`) to `phronix_profiling_check`; a step is done only when the check passes.

## References

### X1 — What the level in the report is for

Cost next to level is what makes a level recommendation falsifiable:
[[phronix-complexity#R2]].

### X2 — Deploying the stack that runs the collector

[[phronix-deployment#I2]].

## Constraints

- Never restart the collector mid-session (R4); phronix_stack start leaves a healthy collector alone.
- Never record a failed step as ok (R1).
- Profiling must never block the work (R2).

## Corner cases

- Everything before profile_bind is unattributed (I2).
- Binding a DIFFERENT id starts fresh and abandons the previous profile; rebinding the SAME id is a no-op (I2).
- The report is written to disk whether or not MLflow is reachable (R2).
- P1 (source pitfall) — Launching the harness without the env exported: The single most common cause of an empty profile. The collector is up, the tools answer, and nothing is ever recorded — because the harness was started before `eval "$(phronix_stack env)"` and exports no telemetry.
- P2 (source pitfall) — A step id that varies between attempts: Appending a timestamp or an attempt number to the step id defeats retry folding: each attempt becomes its own cheap-looking step and the real cost of the work disappears into the noise.
- P3 (source pitfall) — Reading a total that has a large unattributed share: If most of the cost is unattributed, the per-step table is describing a minority of the session. Fix the brackets before drawing conclusions from it.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_profiling_plan`, validator `phronix_profiling_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `env_before_launch` failed: export with eval "$(phronix_stack env)" BEFORE launching the harness, then relaunch (I1, P1)
- `run_bound` failed: profile_bind(run_id=...) as early as the session has an identity (I2)
- `steps_bracketed` failed: bracket every step with profile_step_begin/end and pass model_level (I3)
- `status_honest` failed: status is ok, failed, partial or skipped (R1)
- `stable_step_ids` failed: reuse the step id exactly on a retry; no timestamp or attempt number in it (I3, P2)
- `unattributed_small` failed: fix the brackets before reading the per-step table: most cost fell outside every step window (I4, P3)
- `no_dropped_events` failed: telemetry was lost (cross_check.events_dropped): the bill is understated; say so and check the collector (I4)
- `parallel_flagged` failed: say the per-step split of parallel steps is an estimate (R3)
- `collector_not_restarted` failed: never restart the collector mid-session; the accounting so far is lost (R4)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- Empty profile with the collector up: the harness was launched before the env was exported; export and relaunch (P1).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A cost pattern per level (a step consistently over- or under-provisioned) feeds phronix_complexity's level recommendation (X1).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- eval "$(phronix_stack env)" && claude, profile_bind early, begin/end per step with model_level and a stable id (phronix-profiling I1-I3, 2026-09-15).
- `phronix_profiling_plan` -> follow the checklist -> `phronix_profiling_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
