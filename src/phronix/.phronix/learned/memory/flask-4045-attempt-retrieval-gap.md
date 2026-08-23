---
name: flask-4045-attempt-retrieval-gap
description: A fresh flask-4045 attempt re-implemented the known-insufficient name-only fix despite the complete fix already being recorded in memory
metadata:
  type: lesson
---

**Symptom:** attempt-1 (2026-08-22, commit "SWE-bench") on pallets__flask-4045 applied only the blueprint-name ValueError check and failed `test_route_decorator_custom_endpoint_with_dots`, 1/2 target tests — exactly the outcome already documented in [[flask-4045-incomplete-fix-analysis]] and [[flask-4045-minimal-fix-insufficient]], which also record the verified complete fix (all three validations: name, endpoint, view_func) that passed 2/2 in a prior attempt.

**Root cause:** Not a new implementation bug — a retrieval gap. This attempt's session queried `memory_recall("flask blueprint name dot validation")` and got `no_match`; the existing lesson files were only reachable by walking the raw knowledge-graph output or reading `$HOME/phronix/src/phronix/.phronix/learned/memory/*.md` directly by guessed name. The agent working the task apparently never surfaced these before writing its patch.

**Why:** Confirms the fix in [[flask-4045-minimal-fix-insufficient]] is correct and repeatedly rediscovered the hard way when the existing lesson isn't found at task start.

**How to apply:** For this subject, the complete fix is already known — don't re-derive it. If `memory_recall` misses a memory that clearly exists (e.g. by exact-name file read), that's worth flagging as a recall/indexing issue for `phronix-learning-reconcile` rather than re-running research from scratch.
