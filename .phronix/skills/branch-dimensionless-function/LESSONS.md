# Lessons — branch-dimensionless-function

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Function-branch-only fix (marked "working") misses sqrt(x): sqrt is Pow, not Function

The research pipeline's X11 record marks approach "collapse-dimensionless-in-function-branch" as working, based on the issue's literal exp() repro. But that fix only patches UnitSystem._collect_factor_and_dimension's `elif isinstance(expr, Function)` branch, and sqrt(x) is represented as `Pow(x, S.Half)`, not a `Function` instance — so it never reaches the patched branch. The existing Pow branch (~line 167-172) already collapses a dimensionless *exponent*, but never checks whether the *base* itself is dimensionless, so `sqrt(<dimensionless-but-not-literal-1 expr>)` still raises/misbehaves the same way exp() did before the fix. A complete fix needs the Pow branch to also collapse when the base's dimension is_dimensionless, not just when the exponent is — the Function-branch fix alone is real but incomplete, and "working" here means "fixes the exp() case," not "fixes the general bug."

Sharper detail confirmed since (2026-08-21): the Pow-branch base-dimension collapse must run *before* the branch computes `dim**(exp_factor*exp_dim)`, not after — because `sqrt(a/b)` auto-evaluates/distributes into `Mul(Pow(a,1/2), Pow(b,-1/2))` before `_collect_factor_and_dimension` ever sees a single `Pow(a/b, 1/2)` node. A per-factor Pow collapse (collapsing each factor's base after the fact) therefore only fixes the non-distributed case (`Pow(expr, 1/2, evaluate=False)`); it silently misses the distributed-sqrt case that sympy actually produces by default, because by the time each `Pow` factor is visited its base is already the smaller `a` or `b`, not the dimensionless-but-not-literal-1 combination — the collapse must happen on the base's collected dimension inside the same Pow-branch pass, before the exponentiation step combines it into the returned dimension.

### P2 — fix-total-degree-check-in-itermonomials does not work

**Tried**: fix-total-degree-check-in-itermonomials

**Hypothesis**: Hypothesized the reported bug was a max-vs-total-degree check in itermonomials. Falsified by inspection: base commit already uses sum(powers.values())>=min_degree (fixed since 2021 commit 813f666edc), and powers[S.One] is always 0 because the loop explicitly skips incrementing it (`if variable != 1`), so subtracting it is a no-op. The real sympy-24066 bug is in sympy/physics/units/unitsystem.py _c

**Refuted by**: test 0/1. Do not re-propose this without new evidence.

## Lessons
