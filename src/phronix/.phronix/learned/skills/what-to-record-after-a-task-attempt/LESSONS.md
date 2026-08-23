# Lessons — what-to-record-after-a-task-attempt

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Multi-level FilteredRelation with select_related may set wrong related

**2026-08-22** — Multi-level FilteredRelation with select_related may set wrong related object; the check did not fire for the path the test uses. AssertionError: <Tournament: Tournament object (1)> != <PoolStyle: PoolStyle object (1)>. The test expects p[0].pool.tournament == p[0].tournament_pool.tournament but select_related on tournament_pool returned a PoolStyle object, not the related Tournament.
