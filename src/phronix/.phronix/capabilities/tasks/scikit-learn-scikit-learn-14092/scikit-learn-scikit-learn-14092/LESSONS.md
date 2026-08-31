# Lessons — scikit-learn-scikit-learn-14092

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — numpy scalars fail isinstance checks against Python types

numpy integer types (np.int64, np.int32) do NOT inherit from Python int, so isinstance(np.int64(5), int) returns False. This is the root cause of the GridSearchCV failure - numpy scalars from array indexing are rejected by strict type checks.

## Lessons

### L1 — numpy float32 fails isinstance check against Python float

**2026-08-29** — numpy float32 and shorter float types do NOT inherit from Python float, so isinstance(np.float32(1.0), float) returns False. The fix using (float, np.floating) handles all numpy float types including np.float32.
