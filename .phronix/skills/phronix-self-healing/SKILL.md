---
name: phronix-self-healing
description: How to diagnose and repair phronix when a tool, skill, agent file or harness wiring is broken, stale or missing. Load the moment something in the framework misbehaves, before working around it.
subject: phronix-self-healing
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
| `R5` | Rules | research_status and research_rank ignore the topic argument |
| `R6` | Rules | Knowledge-graph OSError on rebuild is a concurrent-rebuild race — retry first, it is transient |
| `R7` | Rules | No tool lists corpus instance names/phases for research_record_trial |
| `R8` | Rules | research_playbook crashes on stored regex-metachar text ("bad escape") |
| `X1` | References | Turning a repeated repair into a tool |
| `X2` | References | Recording the repair |


## Instructions

### I1 — Start with status

`phronix_status()` reports which layers exist, which are writable, what each holds, and where new learning is being written. A surprising share of "the tool is broken" reports are really "the write went to a layer nobody is reading".

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

Read the actual file, run the actual tool, list the actual directory. A repair applied to a misdiagnosed problem leaves the real one in place and adds a change nobody can explain later.

### I4 — Fix the class, not just the instance

Ask what would have caught this automatically: a check in the startup self-heal, a capability that detects the bad state, a guard in the tool that produced it, a privacy rule if it was a leak class. Fixing an instance is triage.

### I5 — Prove the heal, then record it

Run `verify_run(target=<what you fixed>)`. If nothing covers it, write a corrector whose constraints encode the breakage you just fixed, so the class cannot recur silently. Then record symptom → root cause → exact fix with `skill_write_lesson`.

## Rules

### R1 — Fix the tool; never reproduce its job by hand

A manual workaround is how drift and corruption get introduced: an ad-hoc script producing subtly different results, a shim papering over a real bug. It also leaves the tool broken for the next session, which writes its own, different workaround. "The tool didn't work so I did it manually" is a bug report you failed to file.

### R2 — Edit the source, never the generated artifact

| Source of truth | Generated artifact |
|---|---|
| `.agents/agents/*.yaml` | `.claude/agents/*.md`, `.opencode/agents/*.md`, `.github/agents/*.agent.md`, `.codex/agents/*.toml` |
| `.agents/agents/common-sections.yaml` | the same rendered files |
| `<layer>/skills/<name>/` | `.claude/skills/<name>` (a symlink) |
| `workspace/permissions.yaml` | the `permissions` block in each harness config |

Every generated file carries a `generated-by: phronix` marker. If you see one, you are in the wrong file.

### R3 — When a fix needs a server restart, stop and say so

A running MCP server holds tool closures captured at registration time, so a newly written or edited capability cannot be spliced in. Name the exact tools you need and wait. Do not fill the gap by hand in the meantime.

### R4 — A heal is a prediction — prove it

"I fixed it" is exactly the claim that comes back a week later. See [[phronix-verification#R1]].

### R5 — research_status and research_rank ignore the topic argument

Calling `research_status(topic=X)` or `research_rank(topic=X)` can silently return a different topic's data — check the result's own `"topic"` field before trusting the output.

**Why:** verified directly: `research_status(topic="sympy__sympy-24066")` and `research_rank(topic="branch-dimensionless-function")` both returned `pylint-dev__pylint-7080`'s approach list instead. Looks like session/active-topic statefulness in the tool, not prompt contamination. Distinct from approach-content contamination at [[pylint-dev-pylint-7080#R4]] (text leaking between tasks vs. the query API returning the wrong topic entirely).

**How to apply:** check the returned `"topic"` matches the request. If not, trust the target skill's own X-blocks instead, as done for [[branch-dimensionless-function#X7]].

### R6 — Knowledge-graph OSError on rebuild is a concurrent-rebuild race — retry first, it is transient

"the knowledge graph failed to rebuild: OSError" (mcp-server stage) reported 10x now across unrelated topics (pallets__flask-5063, pylint-dev__pylint-5859, pylint-dev__pylint-7080). `PHRONIX_CACHE` is fixed per benchmark run, not per topic, so concurrent task topics share one `.../learner-cache/graph/knowledge/stage`. Confirmed by direct read of `$HOME/phronix/src/phronix/knowledge_graph.py`: `_stage()` (L183-204) does `shutil.rmtree(stage)` at L191 then repopulates it, while `ensure_knowledge_graph()` (L248-292) calls `_stage()` at L270 and then `_graphify("update", str(stage), ...)` at L276, which shells out to `graphify` and reads the same stage dir — none of this is guarded by a lock. Two concurrent `ensure_knowledge_graph` calls (e.g. from separate reconcile/capture sessions sharing one run) racing there is the mechanism.

**Why:** verified `PHRONIX_CACHE` env points at the shared run-level `learner-cache/`; confirmed no lock exists anywhere in `_stage`/`ensure_knowledge_graph`. Every occurrence so far has self-resolved on a plain retry (`graph_ensure(force=True)`) within the same turn, which is consistent with a transient race rather than a permanent corruption — the count climbing (3→4→5→9→10) is repeats of the same transient symptom across many sessions, not evidence the retry stopped working or that the race is worsening.

**How to apply:** on this error, immediately call `graph_ensure(force=True)` once before doing anything else — it has cleared the error every time observed, across 10 occurrences now. Don't re-investigate each occurrence from scratch, and don't write a new skill or block for this — this is the single canonical record. This is still an unpatched source bug (missing lock or per-topic cache dir) in `knowledge_graph.py:183-204,248-292`; record it once here per [[phronix-self-healing#R1]] rather than re-diagnosing, and treat the underlying source fix as out of scope for a reconcile/capture cycle (it touches phronix's own installed package, not the project under test) unless a session is explicitly asked to patch phronix itself.

### R7 — No tool lists corpus instance names/phases for research_record_trial

Nothing enumerates instance names or their phase (train/held-out/test) for a topic's corpus, so passing the right instance name to `research_record_trial` requires guessing. Reported twice (measurement stage, pylint-dev__pylint-7080).

**Why:** confirmed no listing tool exists this session; the only way to discover a held-out/test instance name was to probe via `research_record_trial`'s own error messages, then use `research_add_instance`/`research_split` to pin one down.

**How to apply:** don't re-probe by trial-and-error each time. If a topic's instance names are unknown, try `research_status`/`research_coverage` first (they may surface names as a side effect) before resorting to the error-message probe. This is a tooling gap worth fixing at the source (a `research_list_instances`-style tool) if it keeps recurring — see [[phronix-self-healing#X1]] for turning a repeated repair into a tool.

### R8 — research_playbook crashes on stored regex-metachar text ("bad escape")

research_playbook (and likely sibling readers) can throw a Python "bad escape ..." error when earlier research_add_approach/research_write_plan text embedded a raw regex escape sequence (e.g. describing a word-boundary bug using the literal backslash-letter notation) — something downstream seems to feed stored prose through re.sub/re.compile unescaped.

**Why:** observed once (pylint-dev__pylint-5859, playbook stage), right after approach text quoted the literal escape syntax from the word-boundary root cause.

**How to apply:** when recording approach/plan text that discusses regex syntax, paraphrase instead of pasting the literal escape sequence (say "word-boundary escape" not the two-character token). On a "bad escape" failure, suspect prior stored text on the same topic before the current call's own input. Not yet root-caused in phronix's source.

## References

### X1 — Turning a repeated repair into a tool

If you have made the same repair twice, it is deterministic: [[phronix-capability-authoring#I1]].

### X2 — Recording the repair

Symptom → root cause → exact fix: [[phronix-self-learning#I3]].
