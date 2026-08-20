# Lessons — column-domain-rule

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — add-subdomain-column-only does not work

**Tried**: add-subdomain-column-only

**Hypothesis**: Adding a "Subdomain" column showing only rule.subdomain value (without SERVER_NAME) is simpler and handles missing SERVER_NAME gracefully. Falsified if: users need full domain reconstruction, or column is confusing without context.

**Refuted by**: test 0/1, validate 0/1. Do not re-propose this without new evidence.

## Lessons
