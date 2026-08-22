---
name: phronix-agent-authoring
description: The harness-neutral agent template: schema, shared sections, capability levels instead of model ids, tool scoping, the four harness dialects, and why rendered files must never be edited. Load before creating an agent or changing how one behaves.
subject: authoring and evolving agent definitions
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Write the template |
| `I2` | Instructions | Pick the capability level |
| `I3` | Instructions | Scope the tools |
| `I4` | Instructions | Render and reload |
| `R1` | Rules | Never edit a rendered agent file |
| `R2` | Rules | The description is the dispatch signal |
| `R3` | Rules | Never hard-code a model id in a template |
| `R4` | Rules | A rule for every agent goes in common-sections.yaml |
| `R5` | Rules | Changing agent behaviour needs the user's confirmation |
| `R6` | Rules | Codex renders no tools key, by design |
| `X1` | References | Where a shared rule belongs |
| `X2` | References | Repairing stale rendered files |

## Instructions

### I1 — Write the template

```yaml
name: phronix-learner            # must match the filename stem
description: >-                  # what it does AND when to dispatch to it
  Harvests a finished session into durable knowledge...
model_level: level_3             # capability level, never a model id
effort: medium                   # claude/codex hint; others ignore it
tools: [Read, mcp__phronix__skill_write]
skills: [phronix-self-learning]
sections:
  - title: What you do
    body: |
      ...
  - include: self-learning       # shared block from common-sections.yaml
```

### I2 — Pick the capability level

| Level | For |
|---|---|
| `level_1` | deterministic orchestration and tool plumbing |
| `level_2` | routing, planning, limited reasoning |
| `level_3` | analysis, diagnosis, stage-to-stage decisions |
| `level_4` | deep synthesis and cross-cutting reasoning |

The indirection is what lets one definition run on four harnesses and makes a
model upgrade a one-line edit in `models.yaml`.

### I3 — Scope the tools

List only what the agent needs. Every tool schema sits in context for the whole
session, and an agent with fifty tools available reaches for the wrong one.

Use neutral (Claude) names — `Read`, `Bash`, `mcp__phronix__skill_load` — and let
the converters reshape them per harness.

### I4 — Render and reload

`agents_sync` re-renders every harness copy, then ask the user to reload the
harness. A change that is not synced exists only in the template.

## Rules

### R1 — Never edit a rendered agent file

`.claude/agents/*.md`, `.opencode/agents/*.md`, `.github/agents/*.agent.md` and
`.codex/agents/*.toml` are build artifacts, gitignored and stamped
`generated-by: phronix`. An edit is silently reverted by the next sync, and the
window between produces the most confusing bug reports in the system.

### R2 — The description is the dispatch signal

It is how a router decides to use this agent. "Reviews code" is unusable; "Reviews
changed code for reuse and simplification; use after a feature lands, not for bug
hunting" is dispatchable.

### R3 — Never hard-code a model id in a template

Use `model_level`. A pinned id breaks the four-harness promise and turns every
model upgrade into an N-file sweep that will be applied to N-2 of them.

### R4 — A rule for every agent goes in common-sections.yaml

Add it once, `include:` it where needed, then `agents_sync`. Before shared
sections existed, changing a standing rule meant editing every template — which in
practice meant editing most and quietly leaving the rest behind.

### R5 — Changing agent behaviour needs the user's confirmation

Appending a lesson to a skill is additive and safe. Changing how an agent behaves
is not: an agent that quietly acquired a wrong rule is very hard to debug, because
nothing in its output says which rule caused it.

### R6 — Codex renders no tools key, by design

Codex has no per-tool allow/deny concept — the boundary is `sandbox_mode`, which
it will not accept from a repo-tracked file. Emitting a `tools` key would advertise
a permission model that does not exist.

## References

### X1 — Where a shared rule belongs

Generic rules propagate through the shared section library, not through one skill:
[[phronix-self-learning#R8]].

### X2 — Repairing stale rendered files

[[phronix-self-healing#R2]].
