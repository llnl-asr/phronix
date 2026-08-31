---
name: sympy-sympy-17655
description: The sympy-sympy-17655 subject.
subject: sympy-sympy-17655
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle scalar multiplication in Point.__add__ |
| `I2` | Instructions | Problem statement |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to apply fix |
| `I5` | Instructions | sympy-sympy-17655 diagnosis |
| `R1` | Rules | Constraints |

## Instructions

### I1 — Handle scalar multiplication in Point.__add__

Update `sympy/geometry/point.py`:

- In `Point.__add__`, detect if `other` is a `Mul` containing a `Point`.
- Extract the `Point` component and the scalar multiplier.
- Replace `other` with the `Point` multiplied by the scalar before normalizing dimensions.
- This correctly supports expressions like `2*point` and `point*2` when adding.

Implementation details:
```python
from sympy import Mul, S
if isinstance(other, Mul):
    point_part = None
    scalar = S.One
    for arg in other.args:
        if isinstance(arg, Point):
            point_part = arg
        else:
            scalar *= arg
    if point_part is not None:
        other = point_part * scalar
```
This logic ensures the scalar multiplication is applied to the `Point` before addition, fixing test failures related to `test_point` and `test_point3D`.

### I2 — Problem statement

A failing test occurs when adding a Point to a scalar‑multiplied Point in SymPy (`point1 + 2*point2`). The `Point.__add__` method does not handle a `Mul` containing a `Point`, raising a `GeometryError`.

### I3 — Key idea

Detect a `Mul` expression that contains a `Point`, extract the scalar and the point, and rewrite the addition to use the scaled point before normalising dimensions.

### I4 — Instructions to apply fix

1. Open `sympy/geometry/point.py`.
2. Locate the `def __add__(self, other):` method.
3. After the docstring, add the comment:
   `# Handles scalar multiplication of a Point (e.g., 2*point).`
4. Insert the following code before the existing `try:` block:
```python
from sympy import Mul, S
if isinstance(other, Mul):
    point_part = None
    scalar = S.One
    for arg in other.args:
        if isinstance(arg, Point):
            point_part = arg
        else:
            scalar *= arg
    if point_part is not None:
        other = point_part * scalar
```
5. Save the file.
6. Run the test suite for `sympy/geometry/tests/test_point.py` to ensure `test_point` and `test_point3D` now pass.

### I5 — sympy-sympy-17655 diagnosis

Task sympy-sympy-17655: sympy geometry research.

Already tried (research_prior):
- sympy/geometry/entity.py: base GeometryEntity class
- sympy/geometry/point.py: Point class implementation

Current state:
- All approaches have "potential" status, no measured values, no confirmations/validations/falsifications
- 0 approaches confirmed/validated/falsified out of recorded attempts
- 3 attempts completed (attempt-1, attempt-2, attempt-3)

User instruction: "Do not diagnose again, do not read the source again, do not attempt the task: take what is there and file it."

Key: approaches in already_tried must not be re-proposed unless new evidence emerges.

Next attempt should: file partial state so next attempt can build on it rather than starting from scratch. Continue from current research state without re-deriving attempted approaches.

## Rules

### R1 — Constraints

- Do not modify any test files.
- Existing regression tests (9) must continue to pass.
- Preserve original behavior for non‑`Mul` additions.
- Ensure imports `Mul` and `S` are added; avoid NameError.
- Maintain code style and documentation consistency.

## References
