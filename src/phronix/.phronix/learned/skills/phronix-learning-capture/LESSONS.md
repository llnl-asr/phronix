# Lessons — phronix-learning-capture

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Cross-topic aspect-mismatch findings should land in one shared skill, not per-topic

**2026-08-21** — Symptom: the same aspect-mismatch fact (pylint expand_modules/ignore-paths aspect names cross-assigned to non-pylint topics) was independently captured as a duplicate rule in five separate topic skills (pallets-flask-4045, pallets-flask-5063, sympy-sympy-21847, sympy-sympy-24066, plus a repeat) before reconcile caught it. Root cause: capture writes findings under the topic key they were observed in, even when the finding is about the aspect-generation process itself rather than that topic's code. Fix: when a captured finding is phrased as "aspect X does not apply to this repo" / "aspect X is mismatched", check research_notice for the same aspect name across other topics before writing — if it already recurred elsewhere, write it once to a general skill (e.g. aspect-<name>-contamination) and reference it from the topic skill, instead of restating it per-topic. See [[aspect-pylint-contamination]] for the consolidated instance of this.
