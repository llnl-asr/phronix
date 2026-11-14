---
name: phronix_self_learning
description: Turn a session into durable knowledge: check what exists first, enumerate every error/fix, ordering, flag, user correction and repeated hand procedure, route each to its tier (capability, skill rule/instruction, pitfall, dated lesson, memory, common section), de-duplicate, read back, prove and privacy-scan. Load before recording anything and before finishing any session that discovered something; recording is mandatory, 'learned nothing' must be said explicitly.
---
Cross-references: [[lessons]], [[knowledge]], [[capability_builder]], [[phronix_memory]], [[phronix_skill_authoring]], [[phronix_verification]], [[phronix_privacy]], [[phronix_capability_authoring]]

# Self-learning: recording what a session learned

Converted from the dftracer-agents skill `phronix-self-learning` (subject: recording what a session learned so the next one inherits it). Source description: How a session turns into durable knowledge: what counts as a lesson, which tier it belongs in, how to scope and word it. Load before recording anything and before finishing any session that discovered something.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** Largely duplicates the store's framework capabilities: lessons (lesson_add, 'symptom, root cause, exact fix', evidence required, one copy of each fact = I4/R5/R6), knowledge (memory_write; knowledge_search first = I1; where a fact goes = I3) and capability_builder ('Learn from every run' / 'Learn from every interaction', deterministic -> code = R3/R4, user approval = R7). Candidate to merge into lessons + capability_builder; the tier table I3 maps skill_write/skill_write_lesson to lesson_add/capability_update there.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Check before you act |
| `I2` | Instructions | Enumerate what actually happened |
| `I3` | Instructions | Route each item to its tier |
| `I4` | Instructions | De-duplicate against what exists |
| `I5` | Instructions | Write, then read back what you wrote |
| `I6` | Instructions | Prove it, then scan it |
| `R1` | Rules | Recording is mandatory, not optional |
| `R2` | Rules | The working recipe counts as a lesson |
| `R3` | Rules | Never put a deterministic procedure in prose |
| `R4` | Rules | Never put a judgment call in a capability |
| `R5` | Rules | Lead with the symptom as it actually appears |
| `R6` | Rules | Record the root cause, not the first hypothesis |
| `R7` | Rules | Appending is safe; rewriting needs confirmation |
| `R8` | Rules | A generic rule must reach every agent |
| `X1` | References | Where the lesson physically lands |
| `X2` | References | How to shape the skill you are writing into |
| `X3` | References | Proving what you recorded |

## Instructions

### I1 — Check before you act

Run `context_skills(task=...)` and `context_memory(topic=...)` first, and act on
what comes back. What you record today is what these return tomorrow; a system
that writes lessons nobody reads is a slower way to make the same mistakes.

### I2 — Enumerate what actually happened

Before filtering, list concretely:

- every error hit, and what actually fixed it — not what you tried first;
- every non-obvious ordering, flag, version or path that mattered;
- every question the user answered and every correction they gave;
- every procedure you executed by hand more than once.

Be generous. A candidate you never wrote down cannot be filtered in.

### I3 — Route each item to its tier

| What it is | Where it goes |
|---|---|
| A fixed procedure — same inputs, same steps | `capability_new` (code, not prose) |
| A step in doing the subject | `skill_write(kind='instruction')` |
| A constraint you must follow | `skill_write(kind='rule')` |
| A trap and how to avoid it | `skill_write_lesson(kind='pitfall')` |
| A dated symptom → root cause → fix | `skill_write_lesson(kind='lesson')` |
| A durable fact, decision or constraint | `memory_write(type='project')` |
| User guidance on how to work | `memory_write(type='feedback')`, WITH the why |
| A rule every agent should follow | `common-sections.yaml`, then `agents_sync` |

### I4 — De-duplicate against what exists

Search for each item before writing it. If it is already recorded, do not restate
it — but check whether what you learned *contradicts or sharpens* the existing
entry, and say so. A skill that quietly disagrees with itself is worse than one
that is merely thin.

### I5 — Write, then read back what you wrote

After writing, load it again and confirm it says what you meant. A lesson that
reads clearly to you now, with the whole session in your head, is often
unintelligible to a session that has none. Write for that reader.

### I6 — Prove it, then scan it

Run `verify_run(target=<subject>)`. If nothing covers it, write the corrector with
`verify_new` — see [[phronix-verification#R1]]. Then `privacy_scan()`: everything
you just wrote is committed and shared.

## Rules

### R1 — Recording is mandatory, not optional

Every session records what it learned before it stops. If you genuinely learned
nothing new, **say so explicitly** — silence is indistinguishable from having
skipped the step.

### R2 — The working recipe counts as a lesson

Record the exact commands, flags, versions and paths that *succeeded*, not only
the failures. This is the most reusable thing a session produces and the least
often written down, because at the moment of success it feels obvious. It will not
be obvious in six weeks.

### R3 — Never put a deterministic procedure in prose

If two competent people following your text would produce byte-identical output,
it is code. Write the capability — see [[phronix-capability-authoring#R1]]. Prose
is re-interpreted on every read, and re-interpretation is where drift comes from.

### R4 — Never put a judgment call in a capability

If the right answer depends on reading the situation, it is a skill. A capability
that hard-codes a judgment applies it silently and confidently in cases where it
is wrong — worse than prose, because nothing signals the assumption.

### R5 — Lead with the symptom as it actually appears

Paste the error text. That is what the next person searches for; a paraphrase is
not. A lesson nobody can search for is invisible however correct it is.

### R6 — Record the root cause, not the first hypothesis

If you tried three fixes and the third worked, record why the third worked. The
first two belong in the entry only as explicitly-labelled dead ends.

### R7 — Appending is safe; rewriting needs confirmation

Add a new block without asking. Do NOT rewrite an existing entry, delete one, or
change an agent's behaviour without the user confirming the diagnosis. An
incorrect root cause persisted into a shared skill will be trusted, and will send
the next session confidently in the wrong direction.

### R8 — A generic rule must reach every agent

A lesson scoped to one subject goes in that subject. A rule that should apply to
EVERY agent goes in `common-sections.yaml`, is `include:`d by the templates that
need it, and then `agents_sync`. A generic rule filed in one corner of one skill
has not been learned by the system.

### Using the tools (capability)

- Render the procedure with `phronix_self_learning_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `checked_existing`, `nothing_learned`, `items`, `privacy_scan`) to `phronix_self_learning_check`; a step is done only when the check passes.

## References

### X1 — Where the lesson physically lands

The write layer decides the audience: `project` reaches everyone who clones the
repo, `user` reaches only you, `bundled` reaches everyone who installs phronix.
`phronix_status()` shows the active target. See [[phronix-memory#R4]].

### X2 — How to shape the skill you are writing into

Structure, labels and the one-subject rule: [[phronix-skill-authoring#R1]].

### X3 — Proving what you recorded

Every recorded claim needs a deterministic corrector:
[[phronix-verification#I1]].

## Constraints

- Every session records what it learned before it stops (R1).
- Rewriting, deleting or changing agent behaviour needs the user's confirmation (R7); lessons and capabilities go through the user's approval in the store.
- Everything written is committed and shared: privacy scan before finishing (I6).
- One subject per skill: create the second subject and link it rather than widening (P3).

## Corner cases

- A site-specific quirk goes to the specific subject (system_<x>) and is linked from the generic one (P2).
- The write layer decides the audience: project, user or bundled (X1).
- If you tried three fixes and the third worked, the first two appear only as labelled dead ends (R6).
- P1 (source pitfall) — Recording the fix without the symptom: An entry that says only "add `-fcommon` to CFLAGS" is unreachable: nobody searching for the linker error they are staring at will find it. Always lead with the error text as it actually appears.
- P2 (source pitfall) — Filing a site-specific quirk in a generic subject: A quirk that is true only on one machine, recorded in a generic skill, misleads everyone else — and is trusted, because it is in the authoritative place. Scope it to the specific subject and link from the generic one.
- P3 (source pitfall) — Widening a skill instead of creating one: When a lesson does not fit the subject, the tempting move is to widen the subject. Do not: a skill that covers two things becomes findable for neither. Create the second subject and link it — see [[phronix-skill-authoring#R1]].

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_self_learning_plan`, validator `phronix_self_learning_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `checked_existing` failed: search skills, lessons and memory first and act on what comes back (I1)
- `explicit_outcome` failed: enumerate what happened (I2), or set nothing_learned=true explicitly (R1)
- `items_routed` failed: route every item to a tier (I3 table)
- `items_have_text` failed: every item needs its tier and its text
- `lessons_lead_with_symptom` failed: a lesson is '<error text as it appears> -> root cause -> fix' (R5, R6, P1)
- `feedback_has_why` failed: user guidance goes to a feedback memory WITH the why (I3)
- `rewrites_confirmed` failed: append without asking, but a rewrite, delete or agent-behaviour change needs the user's confirmation (R7)
- `privacy_clean` failed: run privacy_scan() after writing and redact until clean (I6)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A recorded lesson turned out wrong: tell the user and record the correction (lessons Self-learn), never silently rewrite (R7).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- Any procedure done by hand more than once in the session is routed to capability_new (I2, I3, R3).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Check -> enumerate -> route by the tier table -> de-duplicate -> read back -> verify -> privacy_scan (phronix-self-learning I1-I6, 2026-09-15).
- `phronix_self_learning_plan` -> follow the checklist -> `phronix_self_learning_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
