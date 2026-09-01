---
name: scikit-learn-scikit-learn-14983
description: Fix __repr__ for RepeatedKFold and RepeatedStratifiedKFold
subject: scikit-learn-scikit-learn-14983
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem description

RepeatedKFold and RepeatedStratifiedKFold have unhelpful default __repr__ output (`<object at 0x…>`). Tests expect a descriptive string like `RepeatedKFold(n_splits=5, n_repeats=10, random_state=None)`.

### I2 — Key idea

The subclass constructors must store `n_splits` and `n_repeats` on the instance and `__repr__` must output arguments in the order `n_splits, n_repeats, random_state`.

### I3 — Instructions to solve

1. Open `sklearn/model_selection/_split.py`.
2. In class `RepeatedKFold`, add an `__init__` that calls `super().__init__(*args, **kwargs)` and then stores `self.n_splits = self.cvargs.get('n_splits', 5)` and `self.n_repeats = self.cvargs.get('n_repeats', 10)`.
3. Implement `__repr__` as:
   ```python
   def __repr__(self):
       return f"RepeatedKFold(n_splits={self.n_splits}, n_repeats={self.n_repeats}, random_state={self.random_state})"
   ```
4. In class `RepeatedStratifiedKFold`, similarly add an `__init__` storing `self.n_splits` and `self.n_repeats`.
5. Implement `__repr__` for `RepeatedStratifiedKFold`:
   ```python
   def __repr__(self):
       return f"RepeatedStratifiedKFold(n_splits={self.n_splits}, n_repeats={self.n_repeats}, random_state={self.random_state})"
   ```
6. Ensure the argument order in the formatted string is exactly `n_splits, n_repeats, random_state`.
7. Run the test suite; both `test_repeated_cv_repr` cases should now pass.

## Rules

### R1 — Constraints

* Do not change the public API of RepeatedKFold or RepeatedStratifiedKFold other than adding __init__ and __repr__.
* Preserve existing behavior of other methods and attributes.
* Ensure the __repr__ string matches exactly the expected format and argument order.
* Keep regression tests passing (105/105).

## References

- `skill_load(name="scikit-learn-scikit-learn-14983", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

