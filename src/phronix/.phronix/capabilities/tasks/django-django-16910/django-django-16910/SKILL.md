---
name: django-django-16910
description: The django-django-16910 subject.
subject: django-django-16910
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | The key idea - field name vs object identity in select_mask |
| `I3` | Instructions | What problem it solves - QuerySet.only() + select_related() reverse OneToOneField |
| `I4` | Instructions | Instructions to solve it - targeted name-based comparison in compiler.py |
| `I5` | Instructions | Constraints and rules - preserve regression tests, minimal change |
| `I6` | Instructions | Pitfalls and lessons - name-based comparison too broad |
| `R1` | Rules | Constraints |

## Instructions

### I1 — Problem description

When using `QuerySet.only()` together with `select_related()` on a reverse `OneToOneField` lookup, Django 4.2 includes all fields from the related model in the SQL instead of limiting them, causing unexpected data fetching.

### I2 — The key idea - field name vs object identity in select_mask

The key insight: when select_mask keys are field objects from a different model context (e.g., root model field objects vs related model field objects), the `field in select_mask` object identity check fails. A name-based fallback `key.name == field.name` is needed, but was applied too broadly - matching field names across ALL related models instead of just the specific field being processed.

### I3 — What problem it solves - QuerySet.only() + select_related() reverse OneToOneField

When QuerySet.only() is used with select_related() on a reverse OneToOneField relation, the generated SQL includes ALL fields from the related model instead of just the selected fields. The symptom: someone has a failing test where only() + select_related('reverse_relation') produces a query with all related model fields present. The test expects only the specified fields but gets all of them.

### I4 — Instructions to solve it - targeted name-based comparison in compiler.py

In compiler.py get_default_columns() at line 993-999: Replace the blanket name-based comparison with a context-aware check. The name-based `key.name == field.name` should only apply when processing fields from a related model context (i.e., when the select_mask keys belong to a different model than the current field's model). Check that the field's model matches a select_mask key's model before applying name-based restriction. Specifically: before the `if not any(key.name == field.name for key in select_mask): continue` line, verify that `field.model != key.model` for at least one key in select_mask - only then apply the name-based fallback. If the field's model is the same as the select_mask model keys, keep the original object identity check.

### I5 — Constraints and rules - preserve regression tests, minimal change

Constraints: (1) All 36 existing regression tests must continue passing. (2) The two target tests (test_inheritance_deferred2, test_reverse_one_to_one_relations) must now pass. (3) No test files may be modified - only source code changes allowed. (4) The change must be minimal - only adjust the name-based comparison logic in get_default_columns() to be context-aware. (5) Do not alter the select_mask building logic in query.py - only the consumption in compiler.py.

### I6 — Pitfalls and lessons - name-based comparison too broad

Pitfall: The applied fix added `if not any(key.name == field.name for key in select_mask): continue` as a blanket check that matched field names across ALL related models. This caused the .only() restriction to suppress ALL fields of related models when ANY field name matched, resulting in 0 queries executed instead of the expected count (tests observed: "0 != 2" and "0 != 1"). Lesson: name-based comparison in select_mask must be context-gated - only apply when field's model differs from select_mask key models. Do not apply name-based matching universally across all related model field processing. The too-aggressive name check must be gated on cross-model context detection.

## Rules

### R1 — Constraints

Do not modify existing model fields or relationships; the fix must be query‑level only. Ensure tests that rely on the existing model schema still pass.

## References
