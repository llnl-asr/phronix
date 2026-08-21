---
name: aspect-pylint-contamination
description: Aspect briefs named non_recursive_reference_behavior, windows_path_separator_interaction, discovery_ignore_check_scope, root_path_regex_mismatch, upstream_fix_reference describe pylint's ignore-paths/expand_modules machinery and get cross-assigned to unrelated topics. Load before investigating any of these aspect names on a non-pylint repo.
subject: aspect-pylint-contamination
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Verify pylint exists before investigating these five aspect names |
| `X1` | References | Confirmed cross-assignment across four unrelated topics |
| `X2` | References | Two more independent confirmations this cycle — no new fact, widen counts only |
| `X3` | References | Reconcile: this cycle's reports are re-confirmations, no new mechanism |
| `X4` | References | Correction: X3's pallets-flask-4045 link was dangling, now fixed |
| `X5` | References | Capture-cycle re-confirmation: werkzeug-removal and reverse-contamination blocks still correct |






## Instructions

## Rules

### R1 — Verify pylint exists before investigating these five aspect names

Aspect names `non_recursive_reference_behavior`, `windows_path_separator_interaction`, `discovery_ignore_check_scope`, `root_path_regex_mismatch`, `upstream_fix_reference` all describe the same pylint ignore-paths/expand_modules machinery, valid only on pylint topics.

Before investigating any of them, grep/find the checkout for `pylint/lint/expand_modules.py` or `pylint/lint/pylinter.py`. If absent, stop immediately: flag the aspect as mismatched for this topic and ground work in the topic's real issue.md/task-brief.md instead. Do not re-derive the same negative result each time.

## References

### X1 — Confirmed cross-assignment across four unrelated topics

Zero-applicable-code cross-assignment confirmed on: pallets__flask-4045, pallets__flask-5063, sympy__sympy-21847, sympy__sympy-24066 — 8+ independent failed attempts, each re-discovering the mismatch via its own grep/find for expand_modules.py/pylinter.py/os.walk. Aspect generation appears to template these five names from one pylint task's aspect set and dispatch them onto unrelated topics without checking the target repo. See [[pallets-flask-4045#R3]], [[pallets-flask-5063#R1]], [[sympy-sympy-21847#R1]], [[sympy-sympy-24066#R1]] for the per-topic confirmations this generalizes.

### X2 — Two more independent confirmations this cycle — no new fact, widen counts only

This cycle's reports are further confirmations of facts already recorded — no new mechanism, just more independent hits. Check topic R-blocks first before re-deriving.

- `append_sep_to_root_before_ignore_check` mis-assigned to pallets__flask-5063 and sympy__sympy-21847: already covered by [[pallets-flask-5063#R4]] and [[filter-root#X1]].
- Same approach mis-assigned to pylint-dev__pylint-5859 is a *same-family* variant (wrong pylint subsystem, not wrong repo): see [[pylint-dev-pylint-5859#R1]] and [[pylint-dev-pylint-5859#R3]] (real issue is a `--notes` punctuation-tag regex bug).
- `raise-valueerror-in-blueprint-init` mis-assigned onto a pylint-dev/pylint checkout is a third independent hit (this time from the measurement stage) on the reverse-contamination pattern at [[pylint-dev-pylint-7080#R9]] (was "observed twice").

Why record here instead of new topic blocks: the detail already exists and is cross-linked; re-filing it under new titles would recreate the near-duplicate this skill prevents.

### X3 — Reconcile: this cycle's reports are re-confirmations, no new mechanism

All incoming reports this cycle restate facts already single-copy elsewhere:
- `raise-valueerror-in-blueprint-init` mis-assigned onto pylint-dev/pylint, and pylint-7080's 24-instance corpus being Flask Blueprint dot-validation content: both already [[pylint-dev-pylint-7080#R9]] (reverse contamination).
- bare `import flask`/pytest failing pre-test in flask-4045, and its research store returning a sympy approach under key A2: same symptom-family as [[pallets-flask-4045#X2]] (wrong corpus/approach handed to a topic key) — env-failure/wrong-tool-return variants, not a new mechanism.
- `root_path_regex_mismatch` applied to a sympy fix, mislabelled as topic `pallets__flask-4045` in the incoming report but actually the sympy-21847 checkout: matches [[filter-root#X1]] verbatim.

No merges needed, nothing retired. Widening counts only.

A later cycle re-verified a neighbouring set (root_path_regex_mismatch, itermonomials/direct_exponent_generation_total_degree, flask routes-command cross-assignment, `as_tuple`) against [[filter-root#X3]], [[pallets-flask-4045#X5]]/[[pallets-flask-4045#X7]]/[[pallets-flask-4045#X11]]/[[pallets-flask-4045#R8]], and [[aspect-pylint-contamination#X1]]/[[aspect-pylint-contamination#X2]]/[[aspect-pylint-contamination#X4]]/[[pylint-dev-pylint-7080#R9]]: same outcome, all single-copy and correctly cross-linked, no new block written. This pattern — a reconcile cycle re-confirming the same neighbourhood verbatim — has now recurred across independent cycles, so treat a fresh "re-verified, no new mechanism" report on this neighbourhood as expected rather than as something to re-investigate from scratch.

### X4 — Correction: X3's pallets-flask-4045 link was dangling, now fixed

X3 previously cited `[[pallets-flask-4045#X2]]` for the "bare import flask fails" / "research store returns sympy data under key A2" facts, but X2 in that skill only covers the aspect-mismatch pattern — those two facts were never actually written there, so the link resolved to the wrong content. They are now recorded at [[pallets-flask-4045#X4]]; use that label going forward.

### X5 — Capture-cycle re-confirmation: werkzeug-removal and reverse-contamination blocks still correct

A capture and a reconcile cycle both checked [[pallets-flask-4045#R6]]/[[pallets-flask-4045#R7]] (werkzeug 3.1.8 venv skew) and [[pylint-dev-pylint-7080#R9]]/[[pylint-dev-pylint-7080#R12]] (reverse corpus contamination) against fresh reports and found all four blocks already accurate, with cross-links to [[flask-blueprint-dot-names#L1]] intact. No edits needed — same reconfirm-only pattern as X2/X3, now spanning both the werkzeug-skew and reverse-contamination facts together.

Third capture-cycle pass (this cycle) checked the same two report pairs again — identical facts, no drift, no new mechanism. Recorded here as a count-widen rather than a new X6, since a fourth reconfirmation carries no information beyond "still holds"; further identical reconfirmations should keep widening this block, not add new ones.
