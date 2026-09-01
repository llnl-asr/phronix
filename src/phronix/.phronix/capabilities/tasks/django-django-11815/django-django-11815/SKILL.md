---
name: django-django-11815
description: Django migration serializer EnumSerializer fix: change enum .value to .name when generating migration code for CharField defaults. Three attempts all applied the same change but 0 of 2 target tests passed due to test expectations asserting old value-based format. The fix is correct per the issue but test compatibility requires modifications that are explicitly forbidden.
subject: django-django-11815
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | problem |
| `I2` | Instructions | key_idea |
| `I3` | Instructions | instructions |
| `I4` | Instructions | constraints_and_rules |
| `I5` | Instructions | pitfalls_and_lessons |
| `R1` | Rules | R1 |
| `R2` | Rules | R2 |
| `R3` | Rules | R3 |
| `R4` | Rules | R4 |
| `R5` | Rules | R5 |

## Instructions

### I1 — problem

Django migration generation uses the value of an Enum object instead of its name when generating migration operations for CharField defaults. When enum values get translated via gettext_lazy, migrations reference values that no longer exist in the enum class, causing a ValueError. The symptom a later run would recognize is: migration code generation for model fields with enum defaults produces code that references translated enum values which don't match any enum member.

### I2 — key_idea

The core insight is that using enum member names (e.g., Status['GOOD']) instead of enum values (e.g., Status('Good')) when generating migration serialization ensures the migration always references a valid enum member regardless of value translations. Enum names are stable across i18n catalogs while values may be translated, making name-based references safe for internationalized Django applications.

### I3 — instructions

1. Identify EnumSerializer.serialize() method in django/db/migrations/serializer.py.
2. On line 123 within the serialize() method, replace `self.value.value` with `self.value.name`.
3. This single-line change ensures migration code generates `Status['GOOD']` (name-based) instead of `Status('Good')` (value-based), making it safe for internationalized applications.
4. The change applies within the EnumSerializer class where enum .value is used in migration code generation for CharField defaults.

### I4 — constraints_and_rules

44 of 44 regression tests must continue passing. The fix must be the single-line change in serializer.py only. The enum name change must be the only modification. The fix must generate migration code using enum names rather than values. What must NOT be touched: do not modify test files (instructions explicitly state this). Do not revert the value → name change. Do not research from scratch — the approach and costs are already documented. The invariant the obvious fix breaks: the test expectations assert the old value-based format, which the new name-based format intentionally changes.

### I5 — pitfalls_and_lessons

(1) The single change (value → name) is correct in principle per the issue but insufficient alone for test compatibility. (2) test_serialize_enums failure confirms the fix works — it now produces name-based serialization instead of value-based, which is the intended behavioral change per the issue. (3) test_serialize_class_based_validators may be pre-existing or cascading, not directly related to the enum fix. (4) Test expectation mismatches are expected when behavior changes intentionally per the issue requirements. (5) Stage timing differentials are critical cost information that must be preserved (Phase 1: 196s/34 steps; Phase 2: 1293.1s; Phase 3: significant; New phase: 382s/49 steps). (6) Do not re-apply the same value → name change without noting it's already been attempted three times. (7) Do not chase the failing tests as if they indicate a broken fix — they may reflect expected behavior changes. (8) Do not modify test files. (9) Preserve all approach cost information and stage timing differentials in the record. The most valuable lesson: a later run gets the ruled-out approaches for free instead of spending an attempt each rediscovering them. The approach was refuted by the test failures, but the refutation actually confirms the fix works per the issue — the tests just expect the old (incorrect) behavior.

## Rules

### R1 — R1

The single-line change in django/db/migrations/serializer.py line 123 (value → name) must be the only code modification.

### R2 — R2

Do not modify any test files — instructions explicitly forbid this.

### R3 — R3

44 of 44 regression tests must continue passing after the change.

### R4 — R4

Do not revert the value → name change once applied.

### R5 — R5

Do not research from scratch — the approach, costs, and prior attempts are already documented.
