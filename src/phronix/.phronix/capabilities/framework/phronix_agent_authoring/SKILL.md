---
name: phronix_agent_authoring
description: The harness-neutral agent template: schema, shared sections, capability levels instead of model ids, tool scoping, the four harness dialects, and why rendered files must never be edited. Load before creating an agent or changing how one behaves, when an edit to .claude/agents/*.md (or .opencode/.github/.codex) was silently reverted, when a template names a skill that does not exist, when a template pins a model id, or when a rule must reach every agent.
---
Cross-references: [[capability_builder]], [[phronix_self_learning]], [[phronix_self_healing]], [[phronix_complexity]]

# Authoring and evolving agent definitions

Converted from the dftracer-agents skill `phronix-agent-authoring` (subject: authoring and evolving agent definitions). Source description: The harness-neutral agent template: schema, shared sections, capability levels instead of model ids, tool scoping, the four harness dialects, and why rendered files must never be edited. Load before creating an agent or changing how one behaves.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder already rules agent.json: a level (level_1|2|3), never a model; Bash scoped. Here the same rule (R3, I2) for the dftracer-agents YAML templates, plus the rendered-copy and common-sections rules that the store does not have. agent.json in this store has only level_1..level_3; the source's level_4 maps to level_3.

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

### Using the tools (capability)

- Render the procedure with `phronix_agent_authoring_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `name`, `file_stem`, `description`, `model_level`, `tools`, `skills`, `missing_skills`, `edited_rendered_files`, `behaviour_change`, `user_confirmed`, `synced`) to `phronix_agent_authoring_check`; a step is done only when the check passes.

## References

### X1 — Where a shared rule belongs

Generic rules propagate through the shared section library, not through one skill:
[[phronix-self-learning#R8]].

### X2 — Repairing stale rendered files

[[phronix-self-healing#R2]].

## Constraints

- Rendered agent files are build artifacts (gitignored, stamped generated-by: phronix): never edit them (R1).
- No model id in a template; capability levels only (R3). In this store agent.json allows level_1..level_3.
- A behaviour change needs the user's confirmation; appending a lesson does not (R5).

## Corner cases

- Codex has no per-tool allow/deny: it renders no tools key, and its boundary is sandbox_mode, which it will not accept from a repo-tracked file (R6).
- Only a change that is synced (agents_sync) and reloaded reaches the harness; until then it exists only in the template (I4).
- Stale rendered files: repair as phronix-self-healing R2 says (X2).
- P1 (source pitfall) — A template referencing a skill that does not exist: The agent is told to load something that is not there, and behaves as if the guidance were simply absent. The built-in corrector catches this.
- P2 (source pitfall) — Overriding a bundled agent instead of extending it: A project template of the same name replaces the bundled one entirely, so you stop receiving its future improvements. Consider a project-specific shared section `include:`d into the bundled agent instead.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_agent_authoring_plan`, validator `phronix_agent_authoring_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `name_matches_stem` failed: name the agent; it must match the filename stem (I1)
- `description_dispatchable` failed: say what it does AND when to dispatch to it; 'Reviews code' is unusable (R2)
- `level_not_model` failed: use model_level level_1..level_4, never a model id (R3, I2)
- `no_model_id` failed: remove the pinned model id; a model upgrade is a one-line edit in models.yaml (R3)
- `tools_scoped` failed: list only what the agent needs: every tool schema sits in context for the whole session (I3)
- `tools_present` failed: list the tools the agent needs, with neutral (Claude) names (I3)
- `skills_exist` failed: create or fix the referenced skill; a missing skill is silently absent guidance (P1)
- `no_rendered_edits` failed: revert the edit to the rendered file and change the template, then agents_sync (R1)
- `behaviour_change_confirmed` failed: ask the user to confirm the behaviour change before applying it (R5)
- `synced` failed: run agents_sync and ask the user to reload the harness; an unsynced change exists only in the template (I4)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A rendered agent behaves differently from its template: re-run agents_sync (phronix_self_healing R2), never patch the rendered copy.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A generic rule learnt for one agent propagates through the shared section library, not one skill (phronix-self-learning R8, X1).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Template -> level -> scoped tools -> common-sections include -> agents_sync -> user reload (phronix-agent-authoring I1-I4, 2026-09-15).
- `phronix_agent_authoring_plan` -> follow the checklist -> `phronix_agent_authoring_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
