# Lessons — mwaskom-seaborn-2848

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — pairplot fails with hue_order not containing all hue values; pandas op

**2026-08-31** — pairplot fails with hue_order not containing all hue values; pandas option 'mode.use_inf_as_null' removed causing OptionError. The fix attempted to filter hue_order does not address the pandas OptionError. Future attempts should avoid using pandas option_context with this option or adjust seaborn version.

### L2 — Pandas option_context compatibility fix

**2026-08-31** — L2 — The original hue_order filter fixed the subset case, but the test suite still failed due to a pandas OptionError for 'mode.use_inf_as_null'. Adding a guard around the pd.option_context call removes the error, allowing the hue_order logic to run and the target test to pass.

### L3 — Pitfall: No edit produces no fix

**2026-08-31** — An attempt that makes no code changes cannot resolve the failing test. Ensure the diff actually modifies the relevant file.
