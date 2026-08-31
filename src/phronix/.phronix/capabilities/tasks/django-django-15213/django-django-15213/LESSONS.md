# Lessons — django-django-15213

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L1 — P1 - Previous fix approach failed

Simply wrapping the compiled SQL in NOT (...) caused 'near )' syntax error. This happened because the compiler's output for negated Q objects may be empty or have params that make NOT (...) invalid. Future attempts must avoid this naive wrapping approach.

### L2 — P2 - Compiler handles negation differently

The SQL compiler may already handle the negated flag for Q objects in some cases but not others (e.g., with empty pk__in=[] lists). The fix must account for this inconsistent handling rather than assuming the compiler always handles it correctly.

### L3 — P3 - Test three target tests fail

The three target tests (test_aggregate_over_full_expression_annotation, test_full_expression_annotation, test_full_expression_annotation_with_aggregation) all fail with the current implementation. Any fix must make all three pass while keeping 71 regression tests passing.
