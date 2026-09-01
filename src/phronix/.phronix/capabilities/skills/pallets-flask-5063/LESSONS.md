# Lessons — pallets-flask-5063

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Empty diff and no patch when adding domain column

**2026-08-31** — Attempt to add domain column to flask routes output produced no diff and was judged as not solving the task. The agent generated an empty diff and harness reported "agent produced no patch". This indicates the approach of modifying flask CLI output did not apply, possibly due to missing target files or incorrect assumptions about code location.
