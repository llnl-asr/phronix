# Lessons — phronix-self-healing

Pitfalls and dated lessons for the **diagnosing and repairing the framework itself** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — Editing a rendered agent file

The change works until the next `agents_sync`, then silently disappears. The
window between those two events produces the most confusing bug reports in the
system. Check for the `generated-by: phronix` marker before editing anything.

### P2 — Assuming a write failed when it went to another layer

A lesson written to the `user` layer while the team reads the `project` layer looks
exactly like a tool that silently did nothing. `phronix_status()` first.

### P3 — Working around a broken tool under time pressure

The workaround always outlives the pressure. It is then load-bearing, undocumented,
and subtly different from what the tool would have done — and the tool is still
broken for everyone else.

## Lessons
