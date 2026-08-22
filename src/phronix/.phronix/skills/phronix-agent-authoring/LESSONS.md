# Lessons — phronix-agent-authoring

Pitfalls and dated lessons for the **authoring and evolving agent definitions** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — A template referencing a skill that does not exist

The agent is told to load something that is not there, and behaves as if the
guidance were simply absent. The built-in corrector catches this.

### P2 — Overriding a bundled agent instead of extending it

A project template of the same name replaces the bundled one entirely, so you stop
receiving its future improvements. Consider a project-specific shared section
`include:`d into the bundled agent instead.

## Lessons
