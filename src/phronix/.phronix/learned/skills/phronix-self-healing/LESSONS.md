# Lessons — phronix-self-healing

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

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

### P4 — Graph rebuild fails outright instead of just going stale

Symptom: `graph_query`/`graph_ensure`/`skill_search` fail the rebuild itself — reported as `OSError` or its subclass `FileNotFoundError` (reported repeatedly, mcp-server stage, across pallets/flask, pylint-dev, sympy tasks), or `[Errno 39] Directory not empty: .../graph/knowledge/stage/graphify-out/cache`. This is not [[phronix-context-economy#P3]] (stale line numbers) — the rebuild crashes and produces no graph at all, sometimes leaving `skill_search`'s own graph lookup in the `unavailable` state.

Root cause: looks like the graphify stage's working directory (`graphify-out/cache`) is being torn down or written concurrently — a rebuild race, not a code bug in the caller. Retrying `graph_ensure(force=True)` a second time has been observed to succeed after an initial failure.

Fix / workaround: on this error, retry `graph_ensure(force=True)` once. If it still fails, do not block — fall back to `grep`/Explore/direct file reads for that lookup, and `research_observe(worked=false, kind="tooling", stage="mcp-server")` so the count keeps growing until someone with source access fixes the rebuild's directory handling. Per [[phronix-self-healing#R1]], do not hand-maintain a substitute graph — just fall back to search for that one lookup and move on.

### P5 — research_playbook crashes on stored text containing regex metacharacters

Re-calling `research_playbook` on a topic that already has a written skill can throw `bad escape \s` (or similar) when prior approach text stored for that topic contains raw regex metacharacters — e.g. a hypothesis/summary string saved from a regex-fix task containing literal `\b`, `\s`. The tool appears to interpolate stored strings into a regex/format string without escaping them. Workaround: if this throws, fall back to `research_status`/`research_rank` for the topic instead of retrying `research_playbook`, and avoid storing raw backslash-regex text in approach summaries when you can phrase the same fact without metacharacters.

## Lessons
