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

### P4 — R6 occurrence count update — still transient, still self-resolving

"the knowledge graph failed to rebuild: OSError" (mcp-server stage) reported again this reconcile cycle — this is at least the 11th occurrence of the same canonical race documented in [[phronix-self-healing#R6]] (unlocked `_stage()`/`ensure_knowledge_graph()` in `knowledge_graph.py:183-204,248-292` racing on the shared per-run `PHRONIX_CACHE` stage dir). No new diagnosis was done here — per R6's own instruction, repeats of this symptom get recorded as a count bump, not a new investigation. Continue to treat it as: retry with `graph_ensure(force=True)` once, it clears every time; the underlying fix (a lock or per-topic cache dir) remains an out-of-scope phronix-source change unless a session is explicitly asked to patch phronix itself.

## Lessons
