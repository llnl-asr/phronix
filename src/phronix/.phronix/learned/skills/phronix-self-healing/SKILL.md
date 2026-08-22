---
name: phronix-self-healing
description: How to diagnose and repair phronix when a tool, skill, agent file or harness wiring is broken, stale or missing. Load the moment something in the framework misbehaves, before working around it.
subject: diagnosing and repairing the framework itself
type: skill
---

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
| `R5` | Rules | Graph rebuild crash is retry-once-then-fallback, not a blocker |
| `X1` | References | Turning a repeated repair into a tool |
| `X2` | References | Recording the repair |
| `X3` | References | OSError from skill_search's graph fallback is the same rebuild-race pattern |

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

### R5 — Graph rebuild crash is retry-once-then-fallback, not a blocker

When `graph_ensure`/`graph_query` themselves throw (`OSError`, `FileNotFoundError`, or `[Errno 39] Directory not empty` in `graphify-out/cache`) rather than returning a stale-but-usable graph, retry `graph_ensure(force=True)` once — this has been observed to self-clear. If it fails again, fall back to `grep`/Explore for that lookup instead of blocking, and report it with `research_observe(worked=false)` so the recurring pattern stays visible. See [[phronix-self-healing#P4]] for the observed detail.

## References

### X1 — Turning a repeated repair into a tool

If you have made the same repair twice, it is deterministic:
[[phronix-capability-authoring#I1]].

### X2 — Recording the repair

Symptom → root cause → exact fix: [[phronix-self-learning#I3]].

### X3 — OSError from skill_search's graph fallback is the same rebuild-race pattern

`skill_search` falls through to `graph_query` on an empty index result (see its own docstring); when that fallback hits the rebuild race it can surface as `OSError` rather than `FileNotFoundError`. Same failure family, same handling: see [[phronix-self-healing#P4]] (symptom list, root cause, retry-once-then-fallback) and [[phronix-self-healing#R5]] (the rule). Do not write a second pitfall for this — it is a variant surface of P4, not a new cause.
