---
name: django-django-13321
description: The django-django-13321 subject.
subject: django-django-13321
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Change details |
| `R1` | Rules | Do not modify other session handling logic |





## Instructions

### I1 — Problem description

Corrupt session data causes AttributeError when accessing sessions, leading to failing tests such as `test_actual_expiry` and `test_clear` across multiple session backends.

### I2 — Key idea

Add a guard in `SessionBase._get_session` to ensure `_session_cache` exists before it is accessed, preventing AttributeError on corrupt session data.

### I3 — Change details

In file `django/contrib/sessions/backends/base.py` modify the `_get_session` method:
```python
def _get_session(self, no_load=False):
    # Ensure _session_cache exists to avoid AttributeError on bad data
    if not hasattr(self, "_session_cache"):
        self._session_cache = {}
    """
    Lazily load session from storage (unless "no_load" is True, when only
    an empty dict is stored) and store it in the current instance.
    """
```

## Rules

### R1 — Do not modify other session handling logic

Any fix must preserve existing session serialization/deserialization behavior; only add guards for missing `_session_cache` without altering data structures.

## References

- `skill_load(name="django-django-13321", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

