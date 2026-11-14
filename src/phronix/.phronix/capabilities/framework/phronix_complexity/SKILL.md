---
name: phronix_complexity
description: Measure (never guess) the model level an agent or ad-hoc task needs: complexity_assess, its drivers (reasoning_demand, failure_surface, unverified_fraction, integration_breadth, instruction_load, tool_coverage), the intrinsic floor, and reassessment after the store grows. Load when choosing an agent.json level, when an agent's level has drifted up or down, after lessons/rules/capabilities changed a subject, or when tempted to pin a model id to buy a level.
---
Cross-references: [[phronix_agent_authoring]], [[phronix_self_learning]], [[phronix_capability_authoring]], [[phronix_verification]], [[capability_builder]]

# Measuring the model level an agent or task needs

Converted from the dftracer-agents skill `phronix-complexity` (subject: measuring task complexity and choosing the model level). Source description: How the model level for an agent or a task is measured rather than guessed: the signals that raise and lower it, the intrinsic floor, and how to reassess after the store grows. Load when choosing a level, or when an agent's level has drifted.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder's Constraints say agent.json declares level_1|2|3, never a model; this skill is how that level is chosen and re-measured. Not a duplicate; the level rule could be merged into capability_builder.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Assess before you dispatch |
| `I2` | Instructions | Read the drivers, not just the verdict |
| `I3` | Instructions | Reassess after every session that changed the store |
| `I4` | Instructions | Apply a drift, in the right direction |
| `I5` | Instructions | Set the intrinsic floor when function outweighs scope |
| `R1` | Rules | Levels are measured, not guessed |
| `R2` | Rules | Thinking raises the level; tools lower it |
| `R3` | Rules | Rules count double against instructions |
| `R4` | Rules | Never pin a model id to buy a level |
| `R5` | Rules | A downward drift is a result worth claiming |
| `X1` | References | What creates a drift |
| `X2` | References | Where the level is declared |
| `X3` | References | Why unverified subjects cost a level |

## Instructions

### I1 — Assess before you dispatch

```
complexity_assess(agent="phronix-learner")            # a defined agent
complexity_assess(task="...", skills=[...], tools=[...])   # ad-hoc work
```

The result is computed from counts over the store — no model in the loop — so it
is the same on every machine and the arithmetic can be checked.

### I2 — Read the drivers, not just the verdict

`drivers` lists each signal's contribution largest-first, with the counts behind
it:

```
+0.300  reasoning_demand (1.00) — 15 rules + 12 instructions
-0.226  tool_coverage (0.90) — 19/21 tools are MCP capabilities
+0.200  unverified_fraction (1.00) — 2/2 subjects unverified
```

A recommendation nobody can interrogate gets overridden or ignored. If you
disagree with one, argue with the number that produced it.

### I3 — Reassess after every session that changed the store

```
complexity_impact(skill="<what you just changed>")   # who is affected
complexity_reassess()                                 # every agent
```

Recording a lesson, adding a rule or building a capability all move the
requirement. Without reassessment an agent keeps running at whatever level it was
written with, indefinitely.

### I4 — Apply a drift, in the right direction

- **Drift up** — the subject accumulated rules and pitfalls; there is more to
  weigh. The agent is under-powered for its own scope. Raise it with
  `agent_define(model_level=...)`.
- **Drift down** — enough of the work became MCP capabilities that the agent is
  mostly orchestrating. **This is the outcome to aim for**, and it is a real
  saving that goes unclaimed unless something notices.

### I5 — Set the intrinsic floor when function outweighs scope

Some agents are hard because of what they DO, not what they load. A planner
synthesising from sparse information is doing `level_4` work while declaring one
skill and calling well-specified tools.

Declare `intrinsic: low | moderate | high | max` in the template. Measurement can
raise a level above the floor; it can never lower it below.

## Rules

### R1 — Levels are measured, not guessed

An agent's requirement changes as the store grows, so a level chosen once and
never revisited is wrong shortly afterwards. The measurement is deterministic and
explainable precisely so it can be argued with rather than trusted blindly.

### R2 — Thinking raises the level; tools lower it

The signals encode the framework's thesis:

| Signal | Direction | Why |
|---|---|---|
| `reasoning_demand` (rules ×2 + instructions) | up | constraints must be weighed against each other |
| `failure_surface` (pitfalls + lessons) | up | the naive path is wrong in non-obvious ways |
| `unverified_fraction` | up | unfalsifiable claims must be reasoned about, not checked |
| `integration_breadth` (subjects + references) | up | holding two subjects and their interaction |
| `instruction_load` (prompt length) | up | more internal structure to keep consistent |
| `tool_coverage` (MCP share of tools) | **down** | deterministic tools are judgment the model no longer supplies |

`tool_coverage` is the only signal that lowers the requirement, and converting
work into capabilities is how you move it.

### R3 — Rules count double against instructions

An instruction says what to do next; a rule says what would make an
otherwise-reasonable action wrong. Recognising which constraint applies in context
is judgment, and judgment is what a stronger model buys.

### R4 — Never pin a model id to buy a level

Change `model_level`. The level is what lets one definition run on all four
harnesses and what makes a model upgrade a one-line edit — see
[[phronix-agent-authoring#R3]].

### R5 — A downward drift is a result worth claiming

When capabilities absorb enough of a subject, the agent that used to need judgment
now needs orchestration. Leaving it at the old level wastes the work that made the
reduction possible.

### Using the tools (capability)

- Render the procedure with `phronix_complexity_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `subject`, `measured_level`, `drivers`, `declared_level`, `intrinsic`, `drift`, `action`, `model_id`) to `phronix_complexity_check`; a step is done only when the check passes.

## References

### X1 — What creates a drift

Recording lessons and rules: [[phronix-self-learning#I3]]. Converting procedures
into tools: [[phronix-capability-authoring#R1]].

### X2 — Where the level is declared

The template's `model_level` and `intrinsic` fields:
[[phronix-agent-authoring#I2]].

### X3 — Why unverified subjects cost a level

A claim with no corrector cannot be checked, only reasoned about:
[[phronix-verification#R1]].

## Constraints

- agent.json declares a level, never a model id (R4).
- Measurement can raise a level above the declared intrinsic floor, never lower it below (I5).
- Reassess after every session that changed the store; a level chosen once is wrong shortly afterwards (R1, I3).

## Corner cases

- The store's agent.json allows level_1..level_3 only; a measured level_4 maps to level_3 there.
- Signals (R2): reasoning_demand (rules x2 + instructions) up; failure_surface (pitfalls + lessons) up; unverified_fraction up; integration_breadth (subjects + references) up; instruction_load (prompt length) up; tool_coverage (MCP share of tools) down.
- P1 (source pitfall) — Assessing an agent whose difficulty is intrinsic to its function: A planner or synthesiser scores low on scope-derived signals — it loads few skills and calls well-specified tools — and a purely measured verdict will confidently demote it. Declare `intrinsic: max` so measurement can only raise it.
- P2 (source pitfall) — Raising a level instead of building the capability: A rising score usually means a subject accumulated procedure that should have become code. Buying a stronger model treats the symptom and leaves the drift compounding.
- P3 (source pitfall) — Never reassessing: The measurement is only worth anything if it is re-run. An agent assessed once at authoring time and never again is exactly the fixed level the mechanism exists to replace.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_complexity_plan`, validator `phronix_complexity_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `subject_named` failed: name the agent or task that was assessed
- `measured_level` failed: run complexity_assess and record its level (level_1..level_4)
- `drivers_read` failed: record the drivers (signal, contribution, counts) from complexity_assess, not just the verdict (I2)
- `declared_level` failed: record the agent's declared model_level
- `drift_named` failed: drift is up, down or none
- `drift_acted_on` failed: apply the drift: agent_define(model_level=...) (or build the capability on a drift up, P2); a downward drift is worth claiming (R5)
- `no_model_id` failed: never pin a model id to buy a level; change model_level (R4)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A verdict that looks wrong: argue with the driver number that produced it (I2), and fix the counts or the signal, not the verdict.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A subject whose level keeps rising is procedure waiting to become code: build the capability (P2, X1).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- complexity_assess -> read drivers -> agent_define(model_level=...) after a drift, reassessing after every store change (phronix-complexity I1-I4, 2026-09-15).
- `phronix_complexity_plan` -> follow the checklist -> `phronix_complexity_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
