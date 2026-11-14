# Lessons — phronix-context-economy

Pitfalls and dated lessons for the **retrieving context without loading whole documents** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — Searching skills and memory with one query and stopping there

You get whichever store happened to match more strongly and never learn that the
other had the answer. Always call both.

### P2 — Loading a whole skill because the pointer looked inconvenient

This is the failure the tools are designed around: handed a `file:line`, an agent
often loads the file anyway. The retrieval tools return the section text directly
so there is no reason to.

### P3 — Treating a stale graph as a missing answer

A line number that does not match the file means the graph is behind, not that the
symbol moved. Force a rebuild before concluding anything.

## Lessons
