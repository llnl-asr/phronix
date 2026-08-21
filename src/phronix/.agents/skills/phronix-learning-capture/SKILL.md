---
name: phronix-learning-capture
description: The fast tier of the always-on learner, run every ten seconds: take what has just repeated across tasks and turn it into a skill lesson or a probe_ tool, immediately, so the task that needs it next can find it.
subject: capturing repeated research observations as skills and tools
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Write down everything; repetition updates, not admits |
| `I2` | Instructions | Find the one block that already covers it |
| `I3` | Instructions | Update in place, or write one new block |
| `I4` | Instructions | Build a tool when the procedure is deterministic |
| `I5` | Instructions | Report your own cycle, so the learner can improve |
| `R1` | Rules | Capture is additive; merging is the other tier's job |
| `R2` | Rules | Write for the kind of work, not for the task |
| `R3` | Rules | Write it small rather than not at all |
| `R4` | Rules | Never block the pipeline |
| `X1` | References | Where the two tiers divide |

## Instructions

### I1 — Write down everything; repetition updates, not admits

You are handed one kind of work's observations — `bash`, `python`, `traversal`, `tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and another worker has the others. Nothing you write can collide with theirs, because one kind means one skill and one writer.

**Every observation gets written down.** A finding reported once and not recorded is rediscovered at full price by the next task; the block that would have prevented that costs a few lines. Waiting for a second sighting trades a large, certain loss for a small, speculative saving.

Repetition is not what admits a finding — it is what makes it *confident*. So call `research_notice` for the counts and let them shape **how** you write, not **whether**:

| Seen | How to write it |
| --- | --- |
| Once | State it with its context — the task, the stage, the conditions under which it held |
| Again, same conditions | Update the existing block: drop the task-specific framing, widen the claim |
| Again, different task | It generalises — say so plainly, and remove the hedge |
| Contradicted | Add the condition that separates the cases, or retire it |

That progression is the point: a block starts as a specific, honest observation and becomes a general rule as evidence arrives. It does not start as nothing.

Failures count double. A `worked=false` is what the next task will get wrong too, and it is the entry nobody writes down unprompted.

### I2 — Find the one block that already covers it

Before writing anything, `graph_query` for the finding in your own words, then `graph_get_node` on the ids that come back.

Use the graph rather than a keyword search: it indexes skills and lessons down to the individual block, so it finds a block that says your finding in *different words* — which is exactly the block a keyword search misses and you would otherwise duplicate.

### I3 — Update in place, or write one new block

If a block already says it, **update that block by its label** (`L3`, `I2`). One statement of a fact, one place to correct it when it turns out to be wrong.

If your finding sharpens a neighbouring block rather than repeating it, write yours and reference theirs by label. A reference stays right when the other block changes; a copy of its content silently stops matching.

Blocks are short by construction and rejected rather than truncated when they are not. Lead with the directive, then one line of why. One idea per block — split rather than combine.

### I4 — Build a tool when the procedure is deterministic

When the repeats describe *steps* rather than a fact — building a fixture in a given shape, probing a function's raw output, comparing two variants — that is a capability, not a lesson.

`capability_list()` first, then `capability_new(name="probe_...")` if it is genuinely new. A tool is called; a lesson has to be read, interpreted and re-acted-on by every task that loads it. Prefer the tool wherever the procedure is deterministic.

A tool written now is live within the minute: the MCP server re-scans capabilities on its refresh, so tasks already running pick it up without a restart.

### I5 — Report your own cycle, so the learner can improve

End every cycle with `research_observe(topic="learning")`: what you wrote, what you found already covered, what you decided was too thin, and whether the graph lookup in `I2` actually found the block you later discovered by hand.

That last one is the point. The learner is subject to its own method, and its own behaviour has to arrive in the same stream as everything else or nothing can generalise about it. `phronix-learning-reconcile` reads these back and turns what repeats across cycles into blocks on this skill — so a way of capturing that keeps producing lessons nobody retrieves becomes a rule about what not to capture.

Report it as you would any observation: `worked=false` when the cycle went wrong, and specifically enough that a pattern could form. "wrote three blocks" generalises to nothing.

## Rules

### R1 — Capture is additive; merging is the other tier's job

You run every ten seconds. Write the block, update the block you found, move on. Do not restructure a skill, do not merge two blocks that overlap, do not reorganise an index — `phronix-learning-reconcile` runs every minute and that is its work.

Splitting it this way is what lets capture be aggressive: nothing you add can accumulate, because a compaction pass is always a minute behind you.

### R2 — Write for the kind of work, not for the task

"A subprocess whose output you parse needs stderr merged, or the parse loses the error" is a lesson about `bash` that every later task inherits. "pylint-7080 needed stderr merged" helps one instance and is already recorded in that task's own skill.

### R3 — Write it small rather than not at all

Every block is read on every future retrieval of its skill, so length is the thing to be sparing with — not the writing itself. A finding worth one sentence gets one sentence.

The failure mode this guards against is accretion: enough long, almost-relevant entries and agents stop reading any of them. Note that the defence is *brevity and precision*, not silence. Withholding a finding does not keep the library clean, it keeps it incomplete, and the cost lands on the next task rather than on you.

Two things still deserve nothing: an observation that says only that a tool was called, and one you cannot state without naming a single task's specifics. Those are not findings yet. Everything else gets written.

### R4 — Never block the pipeline

Research and attempts proceed while you run and nothing waits for you. No long analyses, no held locks, no rewriting a skill another stage is mid-way through reading.

If a cycle runs out of time the observations are still on file and the next cycle sees them. Losing a cycle costs nothing; stalling a pass costs the run.

## References

### X1 — Where the two tiers divide

Capture (this skill, ten seconds) turns new repeats into blocks and tools. Reconcile (`phronix-learning-reconcile`, sixty seconds) keeps one true copy of each fact and links the rest.

Two clocks because the costs differ: noticing what repeated is arithmetic, and deciding whether two blocks say the same thing is a judgement. Aggressive capture, periodic compaction.
