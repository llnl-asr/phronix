# phronix

A self-learning, self-healing agentic framework. Install it with `pip`, point it
at a project, and everything the agents learn — skills, capabilities, memory,
agent definitions — is committed with that project and inherited by whoever
clones it next.

```bash
pip install phronix
cd your-project
phronix init
```

## The idea

Most agentic setups start with the agent. phronix builds in the opposite order,
and the order is the whole thesis:

**1. Capabilities first.** Anything deterministic becomes an MCP *tool*, not a
paragraph of prose an agent re-derives every run. Prose gets re-interpreted, and
re-interpretation is where drift comes from. Agents author these themselves with
`capability_new` — the framework builds tools for itself as it goes.

**2. Then intelligence.** What genuinely needs judgment becomes a *skill*: a
markdown document with the caveats, orderings and exact fixes past sessions
discovered. Skills grow through `skill_write`, and are retrieved a section at a
time rather than whole.

**3. Then agents.** Specialized actors that scope down to the skills and tools
their task needs — each carrying a standing instruction to **self-heal** (fix the
broken tool, never work around it) and **self-learn** (write the lesson back
before finishing).

**And underneath all three: correctors.** Learning and healing are *predictions*.
Every one of them is anchored by a deterministic check.

## Predictor and corrector

An agent that records a root cause, writes a fix, or builds a tool is making a
**prediction** about the world. Predictions from a model are useful and,
individually, unreliable — being right most of the time still means writing a
confidently wrong lesson often enough to poison a shared knowledge base, silently,
because a wrong lesson reads exactly like a right one.

A **corrector** is the deterministic counterpart: a fixed algorithm, no model in
the loop, giving the same verdict on every machine every time.

```python
verify_run(target="...")     # after every write and every heal
verify_coverage()            # before you finish
verify_new(kind=..., target=..., claim=...)
```

**Built-in structural correctors** apply to every skill, capability and agent with
no authoring at all — frontmatter parses, names match, `include:`s resolve,
modules compile and register documented tools, templates render for all four
harnesses, nothing identifies a person. Coverage there is total by construction.

**Authored verifiers** check the claim about the world that structure cannot
settle. A verifier is a spec with five facets, each checked and reported
separately, because "it failed" is not actionable and "it passed" is not
trustworthy:

| facet | holds | a failure means |
|---|---|---|
| `assumptions` | preconditions the claim presumes | **inconclusive** — could not run here |
| `inputs` | what the check operates on, and whether each resolves | **inconclusive** |
| `constraints` | the substantive conditions the claim asserts | **fail** |
| `invariants` | what must hold before AND after, sampled twice | **fail**, and the run is invalid |
| `outputs` | what must be produced, and its shape | **fail** |

Separating assumptions from constraints is what keeps the signal alive: collapse
them and every machine missing a dependency reports red, everyone learns to ignore
the red, and the genuine failures go with it.

## Retrieval: two questions, two tools

An agent facing a task needs two different things, and mixing them means the
stronger lexical match wins regardless of which was asked:

```python
context_skills(task="...")   # HOW DO I DO THIS   -> exact skill sections
context_memory(topic="...")  # WHAT HAPPENED LAST TIME -> lessons + linked neighbours
context_for_task(task="...") # both, in one call
```

A **skill** is verified learning about performing a specific task. A **memory** is
a lesson from past experience on a topic. Both are graph-backed and both return
the exact `## ` section **with its text** — never the whole document. Handed a
bare pointer, an agent will load the whole skill anyway, and a whole skill costs
what a whole source file costs.

Every bundled agent carries this as a standing instruction.

## Skills are a relational store

A skill library that grows without a schema becomes a pile of overlapping essays.
phronix applies relational discipline: **one subject per skill, stable keys, and
explicit foreign keys instead of duplication.**

| relational | phronix |
|---|---|
| table | one skill = one subject, and only one |
| primary key | a labelled block (`R1`, `I2`) unique within its skill |
| foreign key | `[[other-skill#R3]]` — a reference to a specific block |
| join table | an **association skill**: only the links between two subjects |
| schema catalogue | the `## Index` table every file carries |

Two files per subject, because they answer different questions and are retrieved
by different tools:

```text
SKILL.md     Index │ Instructions (I*) │ Rules (R*) │ References (X*)   → context_skills
LESSONS.md   Pitfalls (P*) │ Lessons (L*)                              → context_memory
```

Authoring is declarative and idempotent — `skill_define` and `agent_define` take
the whole intended structure, render it deterministically, and write only if the
bytes differ. Labels survive edits, and dropping one that another skill cites is
refused rather than silently stranding the reference.

## Complexity decides the model level

Agents declare a capability level (`level_1`…`level_4`), and the level a given
agent *needs* moves as the store grows. That is measured, not guessed:

```text
complexity_assess(agent="...")   complexity_reassess()   complexity_impact(skill="...")
```

| Signal | Direction | Why |
|---|---|---|
| rules ×2 + instructions | up | constraints must be weighed against each other |
| pitfalls + lessons | up | the naive path is wrong in non-obvious ways |
| unverified subjects | up | unfalsifiable claims must be reasoned about, not checked |
| subjects + references | up | holding two subjects and their interaction |
| prompt length | up | more internal structure to keep consistent |
| **MCP share of tools** | **down** | deterministic tools are judgment the model no longer supplies |

Only one signal points down, and it is the lever the whole framework aims at:
every procedure converted into a capability reduces the model an agent needs.
Scope-derived measurement is combined with a declared `intrinsic:` floor, so an
agent whose difficulty is inherent to its function — planning, synthesis — is
never demoted for loading few skills.

The loop closes automatically: every skill write reports which agents it affects
and whether their level requirement moved.

## What ships in the box

Seven agents (`router`, `planner`, `learner`, `healer`, `capability-builder`,
`verifier`, `privacy-guard`), nine meta-skills covering how the framework grows
itself, two working verifiers, and eight families of MCP tools:

| Tools | What they are for |
|---|---|
| `context_skills` `context_memory` `context_for_task` | **start here** — the two retrieval questions, answered in labelled blocks |
| `skill_define` `agent_define` | declarative, idempotent authoring in the required structure |
| `verify_run` `verify_coverage` `verify_new` `verify_list` | the corrector tier — prove what was learned still holds |
| `complexity_assess` `complexity_reassess` `complexity_impact` | measure the model level the work actually needs |
| `skill_list` `skill_index` `skill_search` `skill_load` `skill_write` `skill_write_lesson` | browse and grow the intelligence tier |
| `memory_list` `memory_recall` `memory_read` `memory_write` | durable facts, portable across every harness |
| `graph_ensure` `graph_query` `graph_get_node` | locate code instead of reading it |
| `privacy_scan` `privacy_redact` `privacy_suspects` `privacy_add_pattern` | keep shared knowledge anonymous |
| `capability_list` `capability_new` | build new deterministic tools at runtime |
| `agents_sync` `skills_sync` `permissions_sync` `hooks_sync` `phronix_status` | push the store out to the harnesses |

The framework itself is domain-neutral. Domain packs — an HPC performance-analysis
pack, a web-service pack — are layers on top.

## Deploying and running it

```bash
phronix deploy            # idempotent: writes only what differs
phronix deploy --check    # writes nothing; exits non-zero if out of date (CI gate)

phronix_stack start       # deploy, then start three daemons
eval "$(phronix_stack env)" && claude
```

`phronix_stack` supervises MLflow, the profile collector and the MCP server.
`start` doubles as `refresh`: it compares each running daemon against the current
configuration — same command, ports, env, hashed into a signature — and bounces
only what actually changed. A configured port held by someone else is swapped for
a free one and persisted, so `status`, `stop` and `env` all agree on it
afterwards. A healthy collector is deliberately never bounced for a config change:
its profile lives in memory.

Deploy is additive. Your `CLAUDE.md` gets a delimited block inserted or refreshed;
a file that collides with a generated name but was not generated by phronix is
reported as a conflict and left alone.

## Profiling: what a session actually cost

The framework's bet is that converting judgment into deterministic tools makes
sessions cheaper. That is measurable, and this is what measures it.

```text
profile_bind(run_id=...)                            # once, early
profile_step_begin(step=..., agent=..., model_level=...)
profile_step_end(step=..., status=...)              # report the REAL status
profile_report()                                    # per-step table + MLflow
```

Claude Code exports OTLP telemetry; a stdlib collector receives it and attributes
each event to whichever step window contains it. Steps aggregate into a run
profile — with retries folded into the step they retried — rendered to markdown
and pushed to MLflow as one parent run with a nested run per step, so you can sort
by cost.

The **model level is recorded next to the cost**. That pairing is what makes the
complexity tier falsifiable: it turns "this agent should be `level_3`" from an
assertion into something you can check against what `level_3` actually spent.

Three figures matter more than the headline number: **unattributed** cost (work
outside every step window — the brackets are wrong), **retries**, and
**`cross_check.events_dropped`** (the event totals disagree with Claude Code's
independent counters, so the bill is understated).

MLflow is an optional extra — `pip install 'phronix[mlflow]'`. Without it the
profile is still captured, aggregated and written to disk; it just has no UI.

## Where learning goes

This is the part that makes `pip install` and self-learning coexist. The store is
three layers, and which one a lesson lands in decides who inherits it:

| Layer | Location | Travels to |
|---|---|---|
| `bundled` | inside the package | everyone who installs phronix |
| `user` | `~/.phronix/` | you, across your own projects |
| `project` | `<repo>/.phronix/` | **everyone who clones your repository** |

Higher layers shadow lower ones by name, so a project can override a bundled
skill or agent entirely.

New learning goes to `project` by default when you are working in one — which is
what makes it a committed artifact rather than something stranded in
`site-packages` and lost on the next upgrade. `phronix status` shows the active
target; `phronix contribute` promotes a project lesson up into the bundled layer
via a reviewed pull request, with a privacy scan in front of it.

For Claude Code specifically, `phronix init` symlinks the per-project memory
directory (`~/.claude/projects/<slug>/memory/`) into `.phronix/memory/`. That is
what makes memory written natively by the harness land in version control instead
of an untracked directory under your home.

## Capabilities are bundles

A capability is a directory, not a loose module:

```
<name>/tool.py         the MCP tools: register(mcp)
<name>/capability.json name, description, version, history, and pvc: which tools predict, which validate
<name>/SKILL.md        Rules, Constraints, Corner cases, Parallel plan, Corrector, Self-heal, Self-learn, What works
<name>/LESSONS.md      what use taught it
<name>/WORKED.md       what finally worked, step by step
<name>/agent.json      the agent that runs it: its tools, skills and level
<name>/checks.json     known input -> expected output, run sandboxed on every change
<name>/versions/vN/    every earlier version
```

`capability_new` writes one; a module from before bundles still loads. The engine
behind them (`phronix.engine`: validation, sandboxed checks, approval, versions,
lessons, the knowledge graph, the verdict and the corrector's budget) is what
projects built on phronix use for their own capabilities.

phronix's bundled layer carries the capabilities that belong to no single project:
workloads, software, systems, tooling and process (`.phronix/capabilities/<topic>/`).

### Projects built on phronix

Projects form a chain, each loading its own capabilities over everything upstream:
phronix <- dftracer-agents (performance engineering) <- moirai-agents (provenance)
and rabbit-agent (Rabbits). A capability has one home, decided by
`phronix.engine.scopes.owner`: the project whose package its code imports, else the
project whose name prefix it carries, else phronix.

A project uses its upstreams from clones in its own `vendor/`. When it learns
something about a capability another project owns (a lesson, a new version, a new
capability in that project's scope), the change is written to a worktree of that
clone, `vendor/contrib/<upstream>`, and committed on the branch
`contrib/<project>`. The project loads that worktree, so the change is in use at
once. Nothing is pushed for you:

```bash
python -m phronix.engine update --bootstrap <the project's configure hook>
```

fast-forwards the clones, rebases each contribution branch on its upstream, and
prints the push command and the pull-request link.

## The background learner

Whatever the agent works out by hand becomes a capability. Hooks
(`phronix.engine.explore_hook`) record every manual call in the foreground — a
shell command, a Python script, a read, an edit — per chat, across turns and
sub-agents, and queue it at its success point (the agent calls
`exploration_complete`, or the turn ends with the last steps passing). Every
foreground turn is queued too: what the user said there is learning as well.

Two background agents (`phronix.engine.background`) work through that:

* the **learner** claims a batch of the queue and turns each record into a new or
  updated capability or a lesson, then closes it with `exploration_mark`; it also
  reviews tools whose calls are slow and makes their capabilities parallelize;
* **consolidation** runs when `phronix.engine.consolidate.report` finds new overlap
  or conflict among lessons or capabilities, and merges them.

By default they are automatic: what passes its checks is applied, the store is
kept consistent (one copy of each fact, no contradicting rules), and the user is
asked only what the evidence cannot decide. `PHRONIX_LEARN_APPROVAL=review`
(`<PREFIX>_LEARN_APPROVAL` in a project) makes everything wait for approval.

A plain install runs them itself: `phronix sync hooks` installs the recorder,
whose Stop hook starts `phronix-learner kick` (headless Claude Code) when work is
due, at most every `PHRONIX_LEARN_S` seconds. `phronix-learner status` shows the
queue and the runs; `PHRONIX_LEARNER=0` leaves the hooks out. A project with a
web UI (moirai-agents, rabbit-agent) renders the same hooks with its own
bootstrap and starts the runs from its server; only the panels are its own.

## Four harnesses, one definition

Agents are defined once, as harness-neutral YAML, and rendered into each
harness's dialect:

| Harness | Agents | Permissions | Prompt-level memory |
|---|---|---|---|
| Claude Code | `.claude/agents/*.md` | `settings.json` | `UserPromptSubmit` hook |
| OpenCode | `.opencode/agents/*.md` | `opencode.jsonc` | `chat.message` plugin |
| Copilot | `.github/agents/*.agent.md` | per-agent tools only | instructions file |
| Codex CLI | `.codex/agents/*.toml` | `sandbox_mode` only | `hooks.json` (opt-in) |

Rendered files are build artifacts — gitignored, stamped, and regenerated by
`phronix sync agents`. Edit the YAML template, never the rendered copy.

Agents declare a capability *level* (`level_1`…`level_4`) rather than a model id,
so one definition runs everywhere and a model upgrade is a one-line edit in
`models.yaml`.

## Context economy

The dominant cost in a session is input — the files read to get oriented. phronix
ships a tree-sitter knowledge graph over code **and markdown headings**, indexing
its own skills, agents and memory alongside your source:

```python
graph_query(question="where is retry handled", scope="project")   # -> file:line
graph_query(mode="docs", question="capability layer choice")      # -> skill section
graph_query(mode="affected", symbol="validate", depth=2)          # blast radius
```

Locating costs a few hundred tokens; reading the files it names costs tens of
thousands. The rule is *locate before you read* — and it applies to skills as much
as to source.

## Privacy

Everything persisted is committed and published, so none of it may identify a
person, machine or run. Usernames, home paths, job ids and hostnames are redacted
automatically on write. `privacy_scan` verifies deterministically;
`privacy_suspects` surfaces the leak *classes* no rule covers yet, and
`privacy_add_pattern` teaches the redactor permanently rather than fixing one
file. `type: user` memories are refused outright.

## Commands

```text
phronix init                 # bootstrap a project end to end
phronix status               # layers, counts, and where new learning is written
phronix sync [what]          # push skills/agents/permissions/hooks to the harnesses
phronix verify     run|list|coverage|new
phronix complexity reassess|agent|task
phronix skills   list|search|load|write
phronix memory   list|recall|read|write
phronix graph    query|ensure|node
phronix privacy  scan|redact|suspects
phronix capability list|new
phronix contribute --list    # what could be promoted into the bundled layer
phronix serve                # run the MCP server
phronix-learner status|kick  # the background learner and consolidation
```

Each also exists as its own console script (`phronix-install-skills`,
`phronix-sync-hooks`, …) for scripting.

## License

phronix is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](LICENSE) and [NOTICE](NOTICE) for details.

SPDX-License-Identifier: MIT

LLNL-CODE-2024514 — Applied Storage Research (ASR)
