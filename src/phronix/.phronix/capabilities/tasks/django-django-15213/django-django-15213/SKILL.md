---
name: django-django-15213
description: Handle negated expressions in ExpressionWrapper.as_sql(). When ExpressionWrapper wraps a negated Q object (~Q(pk__in=[])), the as_sql() method must handle the negated attribute to produce correct SQL. Without this fix, ExpressionWrapper(~Q(pk__in=[])) produces broken SQL (SELECT AS "foo" FROM "table" with no value) while ExpressionWrapper(Q(pk__in=[])) works correctly (SELECT 0 AS "foo" FROM "table").
subject: django-django-15213
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem identification |
| `I2` | Instructions | Problem it solves |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | I7 - Skill naming convention |
| `I6` | Instructions | I9 - What belongs in a skill vs memory |
| `R1` | Rules | Do not mutate read‑only properties |
| `R2` | Rules | R1 - ExpressionWrapper negated handling |
| `R3` | Rules | R2 - Preserve working cases |
| `R4` | Rules | R3 - Avoid syntax errors |

## Instructions

### I1 — Problem identification

The email field is expected but missing, leading to AttributeError when propagating conditional flag.

### I2 — Problem it solves

Tests fail because ExpressionWrapper cannot propagate the conditional flag from its inner expression, causing AttributeError when using ~Q expressions in annotations.

### I3 — Key idea

The conditional flag should be propagated without mutating a read‑only property; instead override set_source_expressions to copy the flag.

### I4 — Instructions to solve it

1. Open `django/db/models/expressions.py`.
2. In class `ExpressionWrapper.__init__`, remove the line `self.conditional = getattr(expression, 'conditional', False)`.
3. Add a new method to `ExpressionWrapper`:
```python
def set_source_expressions(self, exprs):
    super().set_source_expressions(exprs)
    # Propagate conditional flag from the inner expression if present.
    inner = exprs[0]
    if hasattr(inner, 'conditional'):
        self.conditional = inner.conditional
```
4. Ensure the existing `set_source_expressions` body (which sets `self.expression = exprs[0]`) is retained or called via `super()` as above.
5. Run the three target tests `test_aggregate_over_full_expression_annotation`, `test_full_expression_annotation`, and `test_full_expression_annotation_with_aggregation` to verify the fix.
6. Run the full test suite to confirm no regressions.

### I5 — I7 - Skill naming convention

Skills are named using kebab-case slug that reflects the task/repo, e.g., 'django-django-15213'. This name is how later runs look up the skill via skill_load().

### I6 — I9 - What belongs in a skill vs memory

Skills contain procedural knowledge: step-by-step instructions, constraints, and rules for solving a class of problems. Memories contain Durable facts, decisions, and user guidance. This skill contains the fix instructions for ExpressionWrapper negated expression handling; memories would capture the specific test outcomes or user preferences.

## Rules

### R1 — Do not mutate read‑only properties

Never assign to attributes that are defined as read‑only properties on parent classes (e.g., `conditional`). Use proper propagation via methods instead.

### R2 — R1 - ExpressionWrapper negated handling

When ExpressionWrapper.as_sql() encounters an inner expression with a 'negated' attribute (such as ~Q objects), it must handle the negation properly to produce correct SQL output. The fix must ensure that negated expressions produce valid SQL without syntax errors.

### R3 — R2 - Preserve working cases

The fix must not regress the working case: ExpressionWrapper(Q(pk__in=[])) must continue to produce SELECT 0 AS "foo" FROM "table". Any change to as_sql() must maintain backward compatibility with non-negated expressions.

### R4 — R3 - Avoid syntax errors

The fix must not produce SQL syntax errors like 'near )' which occurred when simply wrapping compiled SQL in NOT (...). The approach must handle the negation in a way that is valid SQL in all contexts.

## References

- `skill_load(name="django-django-15213", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
