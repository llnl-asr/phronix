# Lessons — flask-blueprint-name-validation

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P2 — P2 — P1 is resolved: the "empty" state P1 warned about is now the intended pointer

2026-08-22 — P1 warned reconcile passes not to mistake this skill for empty/orphaned, since SKILL.md's I1 used to hold the verified fix directly. Since then, a reconcile pass (I1b) deliberately rewrote SKILL.md's I1 into a superseded pointer to [[pallets-flask-4045#R1]] and [[flask-blueprint-dot-names]], preserving this LESSONS.md content per I1b's rule. So SKILL.md is now intentionally thin — that is correct, not the mistaken-empty state P1 was warning about. Do not re-apply P1's warning to the current pointer form; check SKILL.md's actual current content (a "Superseded" description + I1 pointing elsewhere) before flagging this skill again.

### P1 — Skill is not empty/orphaned — contains verified fix, mistaken for empty by reconcile passes

A reconcile pass (2026-08-22) characterized this skill as "an empty orphaned skill not yet a proper pointer." That is stale: SKILL.md's I1 already states the verified working fix (raise ValueError on dots in Blueprint name/endpoint/view_func name, replacing asserts) with the 2/2 target + 50/50 regression result on pallets/flask-4045. Before flagging a flask-blueprint-* sibling as empty, fetch its SKILL.md content directly rather than trusting a prior reconcile summary — the confusion likely comes from this skill's similarity to true stubs among the flask-blueprint-dot-* siblings.

## Lessons

## Pitfalls

## Lessons

### L1 — L2 is stale — endpoint/view_func asserts must also convert to ValueError

2026-08-22 — L2 says the failing test test_route_decorator_custom_endpoint_with_dots is unrelated to blueprint-name validation and that endpoint validation "still uses AssertionError" by design. That is wrong. Per upstream commit 7c526140 (PR #4045), the endpoint and view_func assert checks in Blueprint.add_url_rule must ALSO be converted to raise ValueError, not left as asserts — see pallets-flask-4045#R1 for the full account. Name-only ValueError (this skill's I1 as first written, and L1/L3) is one third of the fix; leaving endpoint/view_func as asserts is exactly what makes that test fail. Do not follow L2's guidance that the assert-based endpoint checks are correct as-is.
