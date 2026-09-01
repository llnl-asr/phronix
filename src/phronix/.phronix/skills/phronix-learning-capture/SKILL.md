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
| `R0` | Rules | A skill that solves a problem must say how to solve it |
| `R1` | Rules | Capture is additive; merging is the other tier's job |
| `R2` | Rules | Write for the kind of work, not for the task — in a METHOD skill |
| `R3` | Rules | Say what failed, not what to abandon |
| `R4` | Rules | Write it small rather than not at all |
| `R5` | Rules | Never block the pipeline |
| `R6` | Rules | Never write into your own skills; the kind of work is the target |
| `R7` | Rules | A tool is filed under the kind of work it belongs to |
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

`capability_list()` first, then `capability_new(name="probe_...", category="<the kind of work you were handed>")` if it is genuinely new — the category is required, see `R7`. A tool is called; a lesson has to be read, interpreted and re-acted-on by every task that loads it. Prefer the tool wherever the procedure is deterministic.

A tool written now is live within the minute: the MCP server re-scans capabilities on its refresh, so tasks already running pick it up without a restart.

### I5 — Report your own cycle, so the learner can improve

**Say what you did about a tool for every finding, one line each.** `TOOL: <name>` when you built one, or `NO-TOOL: <why not>` when you did not — and "it is a fact, not a procedure" is a complete reason. Write these into the same observation.

This exists because the alternative was measured. `I4` said *prefer a tool where the procedure is deterministic*, which leaves the default at prose — and prose is always the cheaper option in the moment. Across every run to date the learner built **zero** tools while writing lessons steadily, with `capability_new` available and never called. Not one finding was ever judged deterministic. A preference nothing records is a preference nothing follows.

Stating the verdict does not force a tool. It forces the CHOICE to be made once per finding and be visible afterwards, so "no tool was ever right" and "the question was never asked" stop looking identical.

End every cycle with `research_observe(topic="learning")`: the tool verdicts above, what you wrote, what you found already covered, what you decided was too thin, and whether the graph lookup in `I2` actually found the block you later discovered by hand.

That last one is the point. The learner is subject to its own method, and its own behaviour has to arrive in the same stream as everything else or nothing can generalise about it. `phronix-learning-reconcile` reads these back and turns what repeats across cycles into blocks on this skill — so a way of capturing that keeps producing lessons nobody retrieves becomes a rule about what not to capture.

Report it as you would any observation: `worked=false` when the cycle went wrong, and specifically enough that a pattern could form. "wrote three blocks" generalises to nothing.

## Rules

### R0 — A skill that solves a problem must say how to solve it

[[phronix-skill-authoring]] `R0` is the rule and carries the evidence, and `R0b` is its companion: every label you cite must resolve — a bare `X15` means a section of THIS skill, and a research record's approach identifier is not one. In short:
whatever else you record, the `## Instructions` must contain the steps that fix
the problem — file, function, line, and what to change it to. Not a description
of the bug, not an argument about which finding is current.

Measured: a skill written for `pallets__flask-4045` held the complete correct
answer inside 7,433 characters of Rules and References with an EMPTY
Instructions section, and cited an `I1` that did not exist. The model handed it
scored 0/2; the same task from scratch scored 1/2 on its first try. Reuse was
worse than nothing.

Read it back before you finish: could someone fix this from the Instructions
alone?

### R0c — A solution skill is as specific as you can make it

[[phronix-skill-authoring]] `R0c` is the rule. For anything you write about ONE
problem: the exact file, the exact function, the line it goes before or after,
the exact code, the exact message string. A reader should never have to decide
something you already decided.

Then name every way it can still go wrong — the construct that looks equivalent
and is not, the subset that looks sufficient and is not, the neighbouring style
that will be copied, the passing test a CORRECT fix breaks. You know these
because you watched the attempts; nobody downstream does.

Measured: a skill carrying the literal correct code was read by a smaller model,
which reproduced its message string verbatim and still wrote `assert` where the
test wanted `raise ValueError` — 0/2, the right change in the right places in
the wrong construct. Nothing had said "it must be `ValueError`, and the
`assert`s beside it are the trap."

### R1 — Capture is additive; merging is the other tier's job

You run every ten seconds. Write the block, update the block you found, move on. Do not restructure a skill, do not merge two blocks that overlap, do not reorganise an index — `phronix-learning-reconcile` runs every minute and that is its work.

Splitting it this way is what lets capture be aggressive: nothing you add can accumulate, because a compaction pass is always a minute behind you.

### R2 — Write for the kind of work, not for the task — in a METHOD skill

"A subprocess whose output you parse needs stderr merged, or the parse loses the error" is a lesson about `bash` that every later task inherits. "pylint-7080 needed stderr merged" helps one instance and is already recorded in that task's own skill.

**This is about WHICH skill a lesson goes in, not about writing vaguely.** A
method skill covers a kind of work and generalises. A solution skill covers ONE
problem and must not: there, generality is the defect — see `R0c`. The same
finding is written twice in different registers, and the mistake is putting the
general form in the problem's own skill, where a reader needs the specific one.

### R3 — Say what failed, not what to abandon

A failing attempt tells you the code that was written did not work. It does not
tell you the idea was wrong, and those are different claims with very different
costs when recorded.

Write the specific thing: *"validation added to `Blueprint.__init__` did not
fire for the construction path the test uses"*. Do not write the general
verdict: *"dot validation is falsified; no longer a valid approach"*.

Measured on `pallets__flask-4045`: the research found the accepted fix, the
attempt implemented it badly, and the store recorded the correct approach as
refuted — so the next task on that repository starts with the right answer
already ruled out, and nothing downstream can tell it was ruled out for the
wrong reason.

The asymmetry is the whole point. A lesson that is too specific wastes a little
context; a lesson that retires a working idea costs every future task that
would have used it.

### R4 — Write it small rather than not at all

Every block is read on every future retrieval of its skill, so length is the thing to be sparing with — not the writing itself. A finding worth one sentence gets one sentence.

The failure mode this guards against is accretion: enough long, almost-relevant entries and agents stop reading any of them. Note that the defence is *brevity and precision*, not silence. Withholding a finding does not keep the library clean, it keeps it incomplete, and the cost lands on the next task rather than on you.

Two things still deserve nothing: an observation that says only that a tool was called, and one you cannot state without naming a single task's specifics. Those are not findings yet. Everything else gets written.

### R5 — Never block the pipeline

Research and attempts proceed while you run and nothing waits for you. No long analyses, no held locks, no rewriting a skill another stage is mid-way through reading.

If a cycle runs out of time the observations are still on file and the next cycle sees them. Losing a cycle costs nothing; stalling a pass costs the run.

### R6 — Never write into your own skills; the kind of work is the target

The skill you were HANDED is not the skill you write to. `phronix-learning-capture` and `phronix-learning-reconcile` describe your job; they are not where a finding about `bash` or `tests` belongs.

Measured across every run so far: the learner wrote `lesson phronix-learning-capture` and `lesson phronix-learning-reconcile` and nothing else. Every lesson it produced went into the description of its own method, where no task will ever look for it — the reader searching for how to parse subprocess output does not search the learner.

The target is the KIND OF WORK you were handed: `bash`, `python`, `traversal`, `tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling`. Write to that skill by name, and create it with `skill_write` if it does not exist yet — an absent skill is the normal state the first time a kind of work repeats, not a reason to fall back to your own.

### R7 — A tool is filed under the kind of work it belongs to

When you build a tool, pass `category=` — the same kind of work you were handed. `capability_new(name="probe_...", description=..., source=..., category="tests")` files it at `capabilities/tools/tests/probe_....py`.

Without a category a tool is filed under whatever task happened to be running when you built it, and is then found by that task and by nothing else — which defeats the entire reason to write code instead of prose. The value of a tool is that the NEXT kind-of-work like this one calls it.

You are the one caller that always knows the right category, because the kind of work is what you were handed.

## References

### X1 — Where the two tiers divide

Capture (this skill, ten seconds) turns new repeats into blocks and tools. Reconcile (`phronix-learning-reconcile`, sixty seconds) keeps one true copy of each fact and links the rest.

Two clocks because the costs differ: noticing what repeated is arithmetic, and deciding whether two blocks say the same thing is a judgement. Aggressive capture, periodic compaction.
