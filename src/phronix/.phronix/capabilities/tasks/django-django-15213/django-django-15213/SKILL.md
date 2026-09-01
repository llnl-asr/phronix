---
name: django-django-15213
description: Handle negated expressions in ExpressionWrapper.as_sql(). When ExpressionWrapper wraps a negated Q object (~Q(pk__in=[])), the as_sql() method must handle the negated attribute to produce correct SQL. Without this fix, ExpressionWrapper(~Q(pk__in=[])) produces broken SQL (SELECT AS "foo" FROM "table" with no value) while ExpressionWrapper(Q(pk__in=[])) works correctly (SELECT 0 AS "foo" FROM "table").
subject: django-django-15213
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 - Skill naming convention |
| `I2` | Instructions | I9 - What belongs in a skill vs memory |
| `R1` | Rules | R1 - ExpressionWrapper negated handling |
| `R2` | Rules | R2 - Preserve working cases |
| `R3` | Rules | R3 - Avoid syntax errors |

## Instructions

### I1 — I7 - Skill naming convention

Skills are named using kebab-case slug that reflects the task/repo, e.g., 'django-django-15213'. This name is how later runs look up the skill via skill_load().

### I2 — I9 - What belongs in a skill vs memory

Skills contain procedural knowledge: step-by-step instructions, constraints, and rules for solving a class of problems. Memories contain Durable facts, decisions, and user guidance. This skill contains the fix instructions for ExpressionWrapper negated expression handling; memories would capture the specific test outcomes or user preferences.

## Rules

### R1 — R1 - ExpressionWrapper negated handling

When ExpressionWrapper.as_sql() encounters an inner expression with a 'negated' attribute (such as ~Q objects), it must handle the negation properly to produce correct SQL output. The fix must ensure that negated expressions produce valid SQL without syntax errors.

### R2 — R2 - Preserve working cases

The fix must not regress the working case: ExpressionWrapper(Q(pk__in=[])) must continue to produce SELECT 0 AS "foo" FROM "table". Any change to as_sql() must maintain backward compatibility with non-negated expressions.

### R3 — R3 - Avoid syntax errors

The fix must not produce SQL syntax errors like 'near )' which occurred when simply wrapping compiled SQL in NOT (...). The approach must handle the negation in a way that is valid SQL in all contexts.
