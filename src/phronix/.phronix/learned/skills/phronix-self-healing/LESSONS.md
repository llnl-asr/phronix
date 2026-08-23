# Lessons — phronix-self-healing

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Editing a rendered agent file

The change works until the next `agents_sync`, then silently disappears. The window between those two events produces the most confusing bug reports in the system. Check for the `generated-by: phronix` marker before editing anything.

### P2 — Assuming a write failed when it went to another layer

A lesson written to the `user` layer while the team reads the `project` layer looks exactly like a tool that silently did nothing. `phronix_status()` first.

### P3 — Working around a broken tool under time pressure

The workaround always outlives the pressure. It is then load-bearing, undocumented, and subtly different from what the tool would have done — and the tool is still broken for everyone else.

## Lessons

### L1 — Knowledge graph rebuild fails with OSError (ENOTEMPTY under learner-cache/graph/knowledge/stage)

**2026-08-22 (updated)** — standing defect, not a rare flake: `graph_query`/`graph_get_node`/`skill_search`'s internal rebuild raises `OSError: [Errno 39] Directory not empty` when it tries to remove/replace a directory under `<workdir>/learner-cache/graph/knowledge/stage/...` (seen at `graphify-out/cache/ast` and at `phronix/.phronix/learned/memory`) — a concurrent or previously-interrupted rebuild leaves files behind that the next rebuild's remove/replace can't clear. The leaf path varies; match on OSError/ENOTEMPTY plus the `learner-cache/graph/knowledge/stage/` prefix, not one fixed path.

**New this cycle:** the same race also surfaces as a plain `FileNotFoundError` (reported by the `mcp-server` stage, same "knowledge graph failed to rebuild" symptom, same trigger point) instead of `OSError`/ENOTEMPTY. Both are the identical race — one process's remove/replace pass observes the directory mid-mutation by another; timing decides whether that reads as ENOTEMPTY or FileNotFoundError. Treat `FileNotFoundError` on the same path prefix, from the same stages (`mcp-server`, `skill_search`), as this defect — same repair.

Recurred 9+ times (pylint-dev__pylint-7080, pallets__flask-4045 x3+, the reconcile stage itself, skill_search calls, and now one FileNotFoundError on mcp-server) with only the exception class varying. Root cause unconfirmed: standing hypothesis is a concurrent/crashed rebuild leaving partial state; nobody has checked whether multiple mcp-server processes touch the same cache path concurrently — that's the diagnostic worth doing next. If confirmed, fix is serializing rebuilds or a private cache tmpdir per process, not another retry.

Handling (confirmed stopgap, now confirmed to also cover FileNotFoundError): retry the same call once — it frequently succeeds. If it fails twice in a row, stop calling graph tools for the rest of the stage and fall back to `skill_load`/`memory_recall`. This is a tooling-layer flake, not a signal the underlying knowledge is wrong — never delete or rewrite content based on a failed rebuild alone.

Duplicate of L1 in the (layer-unreachable) mcp-server-tooling/LESSONS.md, recorded here since that skill doesn't resolve from this project layer. (Merged 2026-08-22 from four near-identical entries L1–L4, and again from a duplicate L2, that restated this fact on each recurrence instead of updating one.)
