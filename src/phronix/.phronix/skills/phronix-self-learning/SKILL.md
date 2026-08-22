---
name: phronix-self-learning
description: How a session turns into durable knowledge: what counts as a lesson, which tier it belongs in, how to scope and word it. Load before recording anything and before finishing any session that discovered something.
subject: recording what a session learned so the next one inherits it
type: skill
---

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
