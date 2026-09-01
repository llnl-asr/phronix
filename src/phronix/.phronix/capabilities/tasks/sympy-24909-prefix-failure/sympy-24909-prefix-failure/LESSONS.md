# Lessons — sympy-24909-prefix-failure

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Prefix multiplication does not simplify to 1 when factors cancel (e

**2026-08-29** — Prefix multiplication does not simplify to 1 when factors cancel (e.g., milli * kilo should be 1). The test `test_prefix_operations` expects `m * k` to be `S.One` but got a Prefix product.

**Detail**: The attempted fix changed `__mul__` to handle Quantity and Prefix separately, but the simplification logic only returns 1 when the combined factor equals 1 after multiplication, not when using different prefixes that cancel out. This behavior caused the failure.

**What to avoid**: Assuming that multiplying two Prefix objects will automatically simplify to 1 if their scale factors are inverses. Need explicit check for inverse prefixes or combine logic that returns 1 when `fact == 1` after multiplication of scale_factors, which was already present but not triggered because the product of different Prefix objects yields a Prefix object, not a scalar.

**Suggested fix**: In `__mul__`, after computing `fact = self.scale_factor * other.scale_factor`, if `fact == 1` return `S.One` (or `1`) instead of just `1`. Also consider returning `S.One` to match SymPy's expectations.
