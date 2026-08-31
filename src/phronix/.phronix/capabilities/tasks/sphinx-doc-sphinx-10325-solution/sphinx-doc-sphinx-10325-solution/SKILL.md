---
name: sphinx-doc-sphinx-10325-solution
description: The sphinx-doc-sphinx-10325-solution subject.
subject: sphinx-doc-sphinx-10325-solution
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix inherited_members_option ordering |


## Instructions

### I1 — Fix inherited_members_option ordering

Update `inherited_members_option` in `sphinx/ext/autodoc/__init__.py` to return a list preserving the order of class names instead of a set. Replace the implementation with:
```python
def inherited_members_option(arg: Any) -> Union[object, List[str]]:
    """Convert the :inherited-members: option.

    Accepts a comma‑separated list of class names to ignore inherited members
    from those classes. ``True`` retains the historic behavior of inheriting all
    members (treated as the sentinel ``'object'``).
    """
    if arg in (None, True):
        return 'object'
    # Preserve order while stripping whitespace and ignoring empty entries.
    items = []
    for x in str(arg).split(','):
        x = x.strip()
        if x and x not in items:
            items.append(x)
    return items
```

## Rules

## References
