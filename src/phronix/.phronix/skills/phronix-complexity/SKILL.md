---
name: phronix-complexity
description: How the model level for an agent or a task is measured rather than guessed: the signals that raise and lower it, the intrinsic floor, and how to reassess after the store grows. Load when choosing a level, or when an agent's level has drifted.
subject: measuring task complexity and choosing the model level
type: skill
---

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
