# Lessons — phronix-learn-from-attempt

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Attempt produced no diff – the agent made no actual code change

Attempt produced no diff – the agent made no actual code change. This indicates that the attempted fix did not modify any files, so future attempts should verify that a diff is produced before concluding success.

### P2 — Attempt failed due to internal server error – the model could not conn

Attempt failed due to internal server error – the model could not connect to the inference gateway, causing a 500 error. Future attempts should include retry logic or check service health before proceeding.

## Lessons

### L1 — Attempt produced no patch; the diff was empty and the harness reported

**2026-08-22** — Attempt produced no patch; the diff was empty and the harness reported "agent produced no patch". No source changes were made, so the task did not solve the issue. This indicates that the attempted fix was ineffective and should be avoided in future attempts.

### L2 — Inference gateway connectivity error aborts attempts

**2026-08-22** — Inference gateway connection failures cause attempts to abort without any code changes. When such a 500 InternalServerError occurs, the attempt does not provide a useful solution; record the failure and retry after ensuring the inference service is reachable.

### L3 — IndentationError and incorrect skip logic when modifying autosummary g

**2026-08-22** — IndentationError and incorrect skip logic when modifying autosummary generate.py.

The patch added a guard for `imghdr.tests` in `sitecustomize.py` and changed the imported‑member skipping condition in `sphinx/ext/autosummary/generate.py`. However, the indentation of the new block introduced an unexpected indent, causing a collection error (`IndentationError: unexpected indent`). Additionally, the logic `if not imported and getattr(value, '__module__', None) != obj.__name__:` incorrectly skips imported members when they should be included, leading to missing members in the generated docs.

**Lesson**: When adjusting code, ensure indentation aligns with surrounding blocks and verify the semantics of conditional checks, especially when toggling import‑member handling.

**Next steps**: Restore proper indentation, review the skip logic to match the intended behavior (`autosummary_imported_members = False` should keep imported members out), and run tests again.

### L4 — sitecustomize broken sys.path

**2026-08-22** — sitecustomize sys.path manipulation broke Flask context variable handling, causing ContextVar lookup failures in many tests

### L5 — Flask globals LocalProxy changes broke context handling

**2026-08-22** — modifying Flask globals LocalProxy definitions broke context variable behavior, leading to errors

### L6 — Attempted to make BlockMatrix rowblocksizes/colblocksizes handle Zero 

**2026-08-22** — Attempted to make BlockMatrix rowblocksizes/colblocksizes handle Zero objects and convert scalar Zeros to ZeroMatrix in _blockmul, but the target tests still failed. The failure was actually due to a pytest collection error caused by importing 'py.test' (AttributeError: module 'py' has no attribute 'test'), not the BlockMatrix bug. Hence, fixing BlockMatrix alone does not resolve the issue; the test environment must be corrected.
