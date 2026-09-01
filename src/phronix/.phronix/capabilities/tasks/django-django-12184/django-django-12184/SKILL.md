---
name: django-django-12184
description: Widgets become unresponsive when clearing and redrawing the figure inside a RangeSlider on_changed callback.
subject: django-django-12184
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions to Apply the Fix |
| `R1` | Rules | Constraints and Rules |





## Instructions

### I1 — Problem

Optional URL parameters cause a TypeError in view functions when a named group is missing, leading to "modules() takes from 1 to 2 positional arguments but 3 were given".

### I2 — Key Idea

When a URL pattern includes an optional named group, Django passes `None` for the missing parameter; the view should provide a default value or accept `None` to avoid a TypeError.

### I3 — Instructions to Apply the Fix

1. Open the view module `views.py` where the `modules` function is defined.
2. Change the function signature to accept a default value for `format`:
```python
def modules(request, format='html'):
    # existing code
```
   This ensures when the URL does not provide `format`, Django passes `None` and the default `'html'` is used.
3. Update the URL pattern to make the `format` group optional without capturing an empty string:
```python
re_path(r'^module/(?P<format>(html|json|xml))?/?$', views.modules, name='modules')
```
   The pattern already marks the group as optional; no change needed beyond the view signature.
4. Run the test suite to confirm the TypeError is resolved and all tests pass.

## Rules

### R1 — Constraints and Rules

* The view must retain its original functionality for provided `format` values.
* Changing the default must not alter behavior when `format` is explicitly passed.
* All existing tests that depend on other view arguments must continue to pass.
* Do not modify the URL pattern beyond ensuring it remains optional; the regex is correct.
* Ensure the default `'html'` is appropriate for all code paths that use `format`.

## References

- `skill_load(name="matplotlib-range-slider-bug", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

