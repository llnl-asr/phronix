---
name: phronix_self_healing
description: Diagnose and repair the framework when a tool, skill, agent file or harness wiring is broken, stale or missing: status first, match the symptom to its cause, verify the diagnosis, fix the class not the instance, prove the heal and record it. Load the moment something in the framework misbehaves, before working around it: skill invisible, agent behaves like an older version, edits to a rendered agent vanish, permission prompt mid-run, no memory injected, stale graph line numbers, capability missing after write or restart.
---
Cross-references: [[capability_builder]], [[lessons]], [[phronix_mcp_first]], [[phronix_verification]], [[phronix_capability_authoring]], [[phronix_self_learning]]

# Self-healing: diagnosing and repairing the framework itself

Converted from the dftracer-agents skill `phronix-self-healing` (subject: diagnosing and repairing the framework itself). Source description: How to diagnose and repair phronix when a tool, skill, agent file or harness wiring is broken, stale or missing. Load the moment something in the framework misbehaves, before working around it.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder's Self-heal (read known_lessons / lesson_search, reproduce with a check, capability_update, rollback, disable) is the capability-store form of I3-I5 and R1; recording the repair is `lesson_add` (lessons). The symptom table (skills_sync, agents_sync, permissions_sync, hooks_sync) is phronix/dftracer-agents-specific. Candidate to merge into capability_builder's Self-heal.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Start with status |
| `I2` | Instructions | Match the symptom to its cause |
| `I3` | Instructions | Verify the diagnosis before repairing |
| `I4` | Instructions | Fix the class, not just the instance |
| `I5` | Instructions | Prove the heal, then record it |
| `R1` | Rules | Fix the tool; never reproduce its job by hand |
| `R2` | Rules | Edit the source, never the generated artifact |
| `R3` | Rules | When a fix needs a server restart, stop and say so |
| `R4` | Rules | A heal is a prediction — prove it |
| `X1` | References | Turning a repeated repair into a tool |
| `X2` | References | Recording the repair |

## Instructions

### I1 — Start with status

`phronix_status()` reports which layers exist, which are writable, what each holds,
and where new learning is being written. A surprising share of "the tool is broken"
reports are really "the write went to a layer nobody is reading".

### I2 — Match the symptom to its cause

| Symptom | Likely cause | Repair |
|---|---|---|
| Skill invisible to the harness, visible to search | not linked into the discovery dir | `skills_sync` |
| Skill invisible to search too | malformed frontmatter or missing SKILL.md | fix the file, then `skills_sync` |
| Agent behaves like an older version | rendered file stale | `agents_sync` |
| Edits to a rendered agent keep vanishing | it is a build artifact | edit the YAML template, then `agents_sync` |
| Permission prompt mid-run | new tool not in the discovered allowlist | `permissions_sync` |
| No memory injected on prompts | hook script or settings entry missing | `hooks_sync` |
| Graph line numbers do not match | stale graph | `graph_ensure(force=True)` |
| Capability missing after being written | server not restarted | restart |
| Capability missing after a restart | it failed to load | read the server's stderr |

### I3 — Verify the diagnosis before repairing

Read the actual file, run the actual tool, list the actual directory. A repair
applied to a misdiagnosed problem leaves the real one in place and adds a change
nobody can explain later.

### I4 — Fix the class, not just the instance

Ask what would have caught this automatically: a check in the startup self-heal, a
capability that detects the bad state, a guard in the tool that produced it, a
privacy rule if it was a leak class. Fixing an instance is triage.

### I5 — Prove the heal, then record it

Run `verify_run(target=<what you fixed>)`. If nothing covers it, write a corrector
whose constraints encode the breakage you just fixed, so the class cannot recur
silently. Then record symptom → root cause → exact fix with
`skill_write_lesson`.

## Rules

### R1 — Fix the tool; never reproduce its job by hand

A manual workaround is how drift and corruption get introduced: an ad-hoc script
producing subtly different results, a shim papering over a real bug. It also
leaves the tool broken for the next session, which writes its own, different
workaround. "The tool didn't work so I did it manually" is a bug report you failed
to file.

### R2 — Edit the source, never the generated artifact

| Source of truth | Generated artifact |
|---|---|
| `.phronix/agents/*.yaml` | `.claude/agents/*.md`, `.opencode/agents/*.md`, `.github/agents/*.agent.md`, `.codex/agents/*.toml` |
| `.phronix/agents/common-sections.yaml` | the same rendered files |
| `<layer>/skills/<name>/` | `.claude/skills/<name>` (a symlink) |
| `workspace/permissions.yaml` | the `permissions` block in each harness config |

Every generated file carries a `generated-by: phronix` marker. If you see one, you
are in the wrong file.

### R3 — When a fix needs a server restart, stop and say so

A running MCP server holds tool closures captured at registration time, so a newly
written or edited capability cannot be spliced in. Name the exact tools you need
and wait. Do not fill the gap by hand in the meantime.

### R4 — A heal is a prediction — prove it

"I fixed it" is exactly the claim that comes back a week later. See
[[phronix-verification#R1]].

### Using the tools (capability)

- Render the procedure with `phronix_self_healing_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `symptom`, `status_checked`, `cause`, `repair`, `verified_diagnosis`, `edited_files`, `manual_workaround`, `class_fix`, `proof`, `lesson`) to `phronix_self_healing_check`; a step is done only when the check passes.

## References

### X1 — Turning a repeated repair into a tool

If you have made the same repair twice, it is deterministic:
[[phronix-capability-authoring#I1]].

### X2 — Recording the repair

Symptom → root cause → exact fix: [[phronix-self-learning#I3]].

## Constraints

- Never reproduce a tool's job by hand (R1).
- Never edit a generated artifact (R2).
- Never fill a restart gap by hand (R3).
- Rewriting an existing entry or changing an agent's behaviour needs the user's confirmation (phronix-self-learning R7).

## Corner cases

- Skill invisible to the harness but visible to search: not linked into the discovery dir -> skills_sync (I2).
- Skill invisible to search too: malformed frontmatter or missing SKILL.md -> fix the file, then skills_sync (I2).
- Agent behaves like an older version: rendered file stale -> agents_sync (I2).
- Edits to a rendered agent keep vanishing: it is a build artifact -> edit the YAML template, then agents_sync (I2).
- Permission prompt mid-run: new tool not in the discovered allowlist -> permissions_sync (I2).
- No memory injected on prompts: hook script or settings entry missing -> hooks_sync (I2).
- Graph line numbers do not match: stale graph -> graph_ensure(force=True) (I2).
- Capability missing after being written: server not restarted -> restart; missing after a restart: it failed to load -> read the server's stderr (I2).
- In the dftracer MCP server (--reload) an edited existing tool is live without a restart; only new/renamed tools need a reconnect (phronix_mcp_first I3).
- P1 (source pitfall) — Editing a rendered agent file: The change works until the next `agents_sync`, then silently disappears. The window between those two events produces the most confusing bug reports in the system. Check for the `generated-by: phronix` marker before editing anything.
- P2 (source pitfall) — Assuming a write failed when it went to another layer: A lesson written to the `user` layer while the team reads the `project` layer looks exactly like a tool that silently did nothing. `phronix_status()` first.
- P3 (source pitfall) — Working around a broken tool under time pressure: The workaround always outlives the pressure. It is then load-bearing, undocumented, and subtly different from what the tool would have done — and the tool is still broken for everyone else.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_self_healing_plan`, validator `phronix_self_healing_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `symptom_stated` failed: state the symptom as observed
- `status_first` failed: run phronix_status() first: the write may have gone to another layer (I1, P2)
- `cause_named` failed: match the symptom to its cause (I2 table)
- `repair_named` failed: name the repair (sync command, source edit, restart)
- `diagnosis_verified` failed: verify on the actual file/tool/directory before repairing (I3)
- `no_generated_edit` failed: edit the source of truth (YAML template, layer skill dir) and re-sync; rendered files are build artifacts (R2, P1)
- `no_workaround` failed: fix the tool, do not reproduce its job by hand (R1, P3)
- `class_considered` failed: say what would catch this class automatically (self-heal check, detector capability, guard, privacy rule) (I4)
- `heal_proven` failed: run verify_run / capability_verify on what you fixed; write a corrector if nothing covers it (I5, R4)
- `lesson_recorded` failed: record symptom -> root cause -> exact fix (I5)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A repair made it worse: roll back (capability_rollback) and re-diagnose from status.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A repair made twice becomes a tool (X1); a new symptom/cause pair becomes a row in the table via capability_update.
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- status -> symptom table -> verify on real state -> source edit + sync -> class guard -> verify_run -> lesson (phronix-self-healing I1-I5, 2026-09-15).
- `phronix_self_healing_plan` -> follow the checklist -> `phronix_self_healing_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
