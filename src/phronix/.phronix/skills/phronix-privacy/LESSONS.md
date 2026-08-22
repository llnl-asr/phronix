# Lessons — phronix-privacy

Pitfalls and dated lessons for the **keeping shared knowledge free of identifying detail** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — A realistic username in a documentation example

The most common way a skill fails its own privacy check. Use `<user>`, `<host>`,
`<job-id>` — placeholders are exempt from redaction by design.

### P2 — Fixing the file instead of the rule

The class stays open and the next session reintroduces it, usually somewhere less
visible. `privacy_add_pattern` is the fix.

### P3 — Skipping `privacy_suspects` because `privacy_scan` was clean

A clean scan means the *known* rules found nothing. It says nothing about the leak
classes nobody has encoded yet, and those are the ones that matter.

## Lessons
