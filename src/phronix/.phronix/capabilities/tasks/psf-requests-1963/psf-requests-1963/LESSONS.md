# Lessons — psf-requests-1963

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The original code always copied from the original req on every redirec

**2026-08-29** — The original code always copied from the original req on every redirect iteration, so any method modification (POST→GET for 303 See Other) was lost immediately, and the next redirect iteration would resend the original method instead of using the converted one. This is the primary pitfall that the skill's fix addresses.
