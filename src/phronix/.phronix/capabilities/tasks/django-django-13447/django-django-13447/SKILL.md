---
name: django-django-13447
description: Fix IndentationError by correctly adding public alias method.
subject: django-django-13447
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Make the model class available in the admin app_list context and make _build_app_dict public |
| `I2` | Instructions | Expose _build_app_dict method |
| `I3` | Instructions | what-problem-it-solves |
| `I4` | Instructions | instructions-to-solve-it |
| `I5` | Instructions | pitfalls-and-lessons |
| `I6` | Instructions | I7 — Add public alias for _build_app_dict correctly |
| `I7` | Instructions | Expose public build_app_dict method |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | key-idea |
| `R3` | Rules | constraints-and-rules-3 |
| `R4` | Rules | Custom user model must define an email attribute |

## Instructions

### I1 — Make the model class available in the admin app_list context and make _build_app_dict public

1. Rename `_build_app_dict` to `build_app_dict` in django/contrib/admin/sites.py (line 451) to make the method public for custom admin views.

2. Add `'model': model` to the model_dict in `build_app_dict` (line 459) so the model class is available in the app dictionary context.

3. Update internal calls: change `self._build_app_dict(request)` to `self.build_app_dict(request)` in `get_app_list()` (line 467), and `self._build_app_dict(request, app_label)` to `self.build_app_dict(request, app_label)` in `app_index()` (line 476).

### I2 — Expose _build_app_dict method

Make `_build_app_dict` a public method by renaming it to `build_app_dict` (or adding a wrapper) in the same file, and update any calls to use the new name.

### I3 — what-problem-it-solves

When a later run sees a task about Django admin making the model class available in the app_list context and making `_build_app_dict` public, they should recognize this as the django-django-13447 skill. The symptom is: custom admin views need access to the model class but only get serialized model information (name, object_name, perms, admin_url, add_url, view_only). The _build_app_dict method exists but is private (underscore prefix) and the model class is not included in the model_dict.

### I4 — instructions-to-solve-it

The change, precisely enough to apply:

1. In sites.py, in the _build_app_dict method, add `'model': model` to the model_dict. The model_dict is built starting at line 456 (or wherever model_dict = { appears). Add the line `'model': model,` after `'object_name': model._meta.object_name,` and before `'perms': perms,`. The model variable is already available in the method scope — it's the model class being iterated over.

2. Rename the method from `_build_app_dict` to `build_app_dict`. Change the def line from `def _build_app_dict(self, request, label=None):` to `def build_app_dict(self, request, label=None):`.

3. Update all internal call sites that use `self._build_app_dict` to `self.build_app_dict`. There are two call sites:
   a. In get_app_list() method: find `self._build_app_dict(request)` and change to `self.build_app_dict(request)` (line 507 in the original)
   b. In app_index() method: find `self._build_app_dict(request, app_label)` and change to `self.build_app_dict(request, app_label)` (line 538 in the original)

After these three changes, the model class will be available in the app_list context via model_dict['model'], and the method will be publicly accessible as build_app_dict.

### I5 — pitfalls-and-lessons

Take these from What did not work, with the reason each failed:

1. Forgetting to update both call sites — if only get_app_list() is updated but app_index() still calls self._build_app_dict, the app_index view will break with an AttributeError. This is the most common incomplete fix.

2. Adding 'model': model with the wrong variable scope — if the model variable is not actually in scope at that point, it will raise NameError. The model variable must be the one from the for loop iterating over models.

3. Removing existing model_dict keys (name, object_name, perms, etc.) when adding the model key — the fix must only ADD 'model': model, not replace or remove any existing keys.

4. Renaming only the method definition but forgetting the underscore prefix convention — the skill is specifically about making the method public by dropping the underscore. If a later run only renames but doesn't update call sites, or vice versa, the fix is incomplete.

5. Assuming the model class should be a string — the model class in model_dict should be the actual Python class object, not a string name. Custom admin views access model._meta or model fields from this object.

### I6 — I7 — Add public alias for _build_app_dict correctly

Add the public alias method **after** the existing private `_build_app_dict` method in `django/contrib/admin/sites.py`:
```python
    def build_app_dict(self, request, label=None):
        """Public alias for the private ``_build_app_dict`` method.

        This method forwards to ``_build_app_dict`` to expose the functionality
        as a public API without altering existing behavior.
        """
        return self._build_app_dict(request, label)
```
Place this method with the same 4‑space indentation as the surrounding class
methods, ensuring there are no stray leading spaces or tabs that would cause an
`IndentationError`. No other changes are required.

### I7 — Expose public build_app_dict method

Edit `django/contrib/admin/sites.py`:
1. Locate the private method `_build_app_dict`.
2. Add a new public method `build_app_dict(self, request, label=None)` below it.
3. Implement it as:
   ```python
   def build_app_dict(self, request, label=None):
       """Public alias for building app dict"""
       return self._build_app_dict(request, label)
   ```
4. Ensure proper indentation (4 spaces) and no stray `+`/`-` characters.
5. Save the file and run the admin tests.

## Rules

### R1 — Do not modify test files

All changes must be limited to application code; tests must remain untouched.

### R2 — key-idea

The one insight the whole fix turns on: the model class is not included in the model_dict returned by _build_app_dict, so custom admin views cannot access it. The fix requires two changes: (1) add `'model': model` to the model_dict in _build_app_dict, and (2) rename _build_app_dict to build_app_dict (drop the underscore prefix) and update all internal call sites. This is the key idea — not a description of the diff but the claim about what's missing and what must change.

### R3 — constraints-and-rules-3

The two internal call sites must both be updated: (a) get_app_list() calling self._build_app_dict(request) → self.build_app_dict(request), and (b) app_index() calling self._build_app_dict(request, app_label) → self.build_app_dict(request, app_label). Both must change.

### R4 — Custom user model must define an email attribute

Any custom user model used with Django admin must include an `email` field (e.g., `email = models.EmailField(...)`). This ensures `user.email` is never None, preventing TypeError in admin site processing.

## References

- `skill_load(name="django-django-13447", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
