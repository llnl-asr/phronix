# Lessons — phronix-capability-authoring

Pitfalls and dated lessons for the **authoring MCP tools the framework builds for itself** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — A capability that only works in one repository, written to `bundled`

Everyone else gets a tool that always fails, and it looks like a framework bug
rather than a mis-scoped contribution.

### P2 — Silent defaults for things that matter

A tool that quietly picks a version, a path or a mode produces results nobody can
reproduce, and the choice is invisible in the output.

### P3 — Expecting a new tool to be callable immediately

A running MCP server holds tool closures captured at registration time. The tool
does not exist until the server restarts — say so rather than letting the caller
discover it by calling something that is not there.

## Lessons
