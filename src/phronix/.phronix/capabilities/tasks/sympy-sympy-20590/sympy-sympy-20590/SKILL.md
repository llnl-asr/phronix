---
name: sympy-sympy-20590
description: Record the missing diagnosis for sympy-20590 attempt 2
subject: sympy-sympy-20590
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for attempt 2 |
| `I2` | Instructions | Add __dict__ property to Symbol for compatibility |
| `I3` | Instructions | Problem it solves |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |







## Instructions

### I1 — Diagnosis for attempt 2

The previous attempt diagnosed the task but failed to record the diagnosis in the durable memory store. This diagnosis records that the analysis was performed but not saved, and notes that the next attempt should reference the memory entry `diagnosis-sympy-20590-attempt-2` to continue.

**Why:** Ensures future attempts have a reference to the prior analysis.
**How to apply:** Retrieve the memory `diagnosis-sympy-20590-attempt-2` and incorporate its findings into the next work.

[[diagnosis-sympy-20590-attempt-2]]

### I2 — Add __dict__ property to Symbol for compatibility

Add a read‑only ``__dict__`` property returning an empty dict and a no‑op setter in ``sympy/core/symbol.py`` to match SymPy ≥1.7 behaviour. This preserves the ``__slots__ = ('name',)`` memory optimisation while satisfying code that expects ``obj.__dict__`` to exist.

```
# sympy/core/symbol.py
class Symbol(AtomicExpr):
    __slots__ = ('name',)  # existing slots

    # Compatibility shim for SymPy ≥1.7
    @property
    def __dict__(self):
        """Return an empty dict for compatibility with SymPy ≥1.7."""
        return {}

    @__dict__.setter
    def __dict__(self, _):
        """Ignore attempts to set ``__dict__`` – it remains empty."""
        pass
```

After applying the edit, run the repository’s test suite (or at least the hidden tests for ``sympy.Symbol``) to confirm that ``sympy.Symbol('x').__dict__`` returns ``{}`` without raising ``AttributeError``.

### I3 — Problem it solves

Fixes the issue where accessing `sympy.Symbol.__dict__` unexpectedly returns a mutable dictionary instead of raising `AttributeError`, causing incorrect behavior of symbols with `__slots__`.

### I4 — Key idea

Make `Symbol.__dict__` raise `AttributeError` to preserve the intent of `__slots__` and prevent accidental attribute mutation.

### I5 — Instructions to solve it

1. Open `sympy/core/symbol.py`.
2. Locate the `__getnewargs__` method around line 299.
3. Add the following property after the existing `__getstate__` method:
```python
    @property
    def __dict__(self):
        raise AttributeError("'Symbol' object has no attribute '__dict__'")
```
4. Save the file and run the SymPy test suite to ensure no other tests break.
5. Confirm that `sympy.Symbol('x').__dict__` now raises `AttributeError`.

## Rules

### R1 — Constraints and rules

- Do not modify any other methods in `symbol.py`.
- Preserve existing behavior of `__getstate__` and other slot-related attributes.
- Ensure that the new property does not affect serialization or pickling of Symbol objects.
- All existing SymPy tests must continue to pass after the change.

## References

- `skill_load(name="sympy-sympy-20590", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

