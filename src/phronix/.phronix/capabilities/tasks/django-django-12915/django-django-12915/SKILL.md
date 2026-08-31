---
name: django-django-12915
description: Fix sympy vector pretty printing where unit vectors (e.g., i_C) appear in the middle of coefficient-expression sequences instead of at the end. The core issue is in _print_BasisDependent method in sympy/printing/pretty/pretty.py where formatted component strings are concatenated incorrectly, placing unit vectors between coefficients and what follows them.
subject: django-django-12915
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add async response method to StaticFilesHandlerMixin |
| `I2` | Instructions | Problem: Async support missing for ASGIStaticFilesHandler |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Apply async get_response_async in StaticFilesHandlerMixin |
| `R1` | Rules | Do not modify other handler methods |
| `R2` | Rules | Unit vector positioning in _print_BasisDependent |
| `R3` | Rules | Component iteration order matters |
| `R4` | Rules | Fix requires reordering the assembly |

## Instructions

### I1 — Add async response method to StaticFilesHandlerMixin

Import `sync_to_async` from `asgiref.sync` and implement `async def get_response_async(self, request): return await sync_to_async(self.get_response)(request)`. This enables ASGI static files handling.

### I2 — Problem: Async support missing for ASGIStaticFilesHandler

When using Django's ASGIStaticFilesHandler, tests fail with a TypeError because the handler lacks an async `get_response_async` method, causing a `'NoneType' object is not callable` error.

### I3 — Key idea

Add an async `get_response_async` method in `StaticFilesHandlerMixin` that delegates to the existing sync `get_response`, enabling ASGIStaticFilesHandler to work correctly.

### I4 — Apply async get_response_async in StaticFilesHandlerMixin

In `django/contrib/staticfiles/handlers.py`:
1. Add `from asgiref.sync import sync_to_async` at the top.
2. Inside `StaticFilesHandlerMixin` add:
```python
    async def get_response_async(self, request):
        return await sync_to_async(self.get_response)(request)
```
This delegates the async call to the existing sync `get_response` method.

## Rules

### R1 — Do not modify other handler methods

Only add the async method; keep existing sync logic unchanged to avoid regression.

### R2 — Unit vector positioning in _print_BasisDependent

The _print_BasisDependent method in sympy/printing/pretty/pretty.py (around line 1095-1193) assembles formatted component strings for vector pretty printing. The bug causes unit vectors (i_C, j_C, k_C) to appear in the middle of coefficient-expression sequences rather than at the end. When formatting a term like 2*sin(pi/10)*cos(10*t)*i_C, the output incorrectly places i_C between the coefficient and cos(10*t) instead of after it.

### R3 — Component iteration order matters

In _print_BasisDependent, components are iterated via `for k, v in inneritems:` where `inneritems = list(vect.components.items())` and sorted by `key=lambda x: x[0].__str__()`. The unit vector's _pretty_form (k._pretty_form) is appended to vectstrs at line 1130 separately from the coefficient+basis string at line 1129. The assembly logic at lines 1132-1193 then uses both o1 (coefficient+formatted) and vectstrs (just the vector form) to build the final output, but the ordering between them is broken - the vectstrs entries get inserted in the wrong positions relative to their corresponding o1 entries.

### R4 — Fix requires reordering the assembly

The fix must ensure that when a term has both a coefficient and a basis vector, the complete formatted string (coefficient + basis vector _pretty_form) stays together as a unit, and the basis vector form does not get intercalated between coefficient and expression parts. The o1 list at line 1129 already correctly creates `arg_str + ' ' + k._pretty_form` for general expressions, but the subsequent assembly logic at lines 1132-1193 must preserve this ordering rather than splitting apart the coefficient and vector form.

## References
