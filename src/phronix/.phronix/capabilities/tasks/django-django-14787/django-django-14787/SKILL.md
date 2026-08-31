---
name: django-django-14787
description: Fix attribute preservation in method_decorator
subject: django-django-14787
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix method_decorator binding to preserve attributes |
| `I2` | Instructions | Fix method_decorator to use underlying function for attribute setting |
| `I3` | Instructions | Fix method_decorator wrapper attributes |


## Instructions

### I1 — Fix method_decorator binding to preserve attributes

Update `django/utils/decorators.py`:

```python
def _multi_decorate(decorators, method):
    def _wrapper(self, *args, **kwargs):
        # Retrieve the underlying function object
        func = method.__func__
        # Apply decorators to the function, preserving any attribute assignments
        for dec in decorators:
            func = dec(func)
        # Bind the decorated function back to the instance
        bound_method = func.__get__(self, type(self))
        return bound_method(*args, **kwargs)
    return _wrapper
```

This change replaces the previous use of `method.__get__(self, type(self))` which produced a bound method lacking custom attributes. By decorating the underlying function and then rebinding, attribute assignments (e.g., `func.x = 1`) work correctly.

### I2 — Fix method_decorator to use underlying function for attribute setting

Update `django/utils/decorators.py`:
- In `_multi_decorate`, replace the binding logic. Retrieve the underlying function via `method.__func__` before applying decorators, then re-bind the decorated function to the instance.
```python
# original
# bound_method = method.__get__(self, type(self))
# for dec in decorators:
#     bound_method = dec(bound_method)
# return bound_method(*args, **kwargs)

# fixed
func = method.__func__
for dec in decorators:
    func = dec(func)
# re-bind the decorated function to the instance
bound_method = func.__get__(self, type(self))
return bound_method(*args, **kwargs)
```

### I3 — Fix method_decorator wrapper attributes

Replace the use of `functools.partial` with a direct bound method call in `_multi_decorate`:
```python
-        bound_method = partial(method.__get__(self, type(self)))
+        bound_method = method.__get__(self, type(self))
```
This preserves the original function attributes (`__name__`, `__module__`, etc.) and prevents `AttributeError` when decorators set attributes on the wrapped method. Ensure no other changes are made and all regression tests (19/20) still pass.

## References
