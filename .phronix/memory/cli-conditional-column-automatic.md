---
name: cli-conditional-column-automatic
description: Automatic detection pattern for conditional CLI table columns vs user flags
metadata:
  type: feedback
---

## Conditional Column Display Strategy

For Flask CLI table output extension, use **automatic detection** rather than user flags for optional columns.

**Pattern:**
```python
# Detect if optional column has any data
has_optional = any(item.attribute for item in items)

# Build headers conditionally
headers = ["Required1", "Required2"]
if has_optional:
    headers.append("Optional")

# Build rows with same condition
for item in items:
    row = [item.field1, item.field2]
    if has_optional:
        row.append(item.attribute or "")  # None → ""
    rows.append(row)
```

**Why automatic detection:**
1. Keeps output clean when column would be empty
2. No user flags needed (reduces API surface)
3. Backward compatible (existing apps see unchanged output)
4. Matches user expectation (don't show empty columns)

**Why not always show column:**
- Empty column wastes terminal space
- Clutters output for majority use case (no optional data)
- Adds visual noise without information

**Why not user flag:**
- Adds complexity to command interface
- Users must know in advance whether data exists
- Easy to forget flag when it should be used

**Applied in:** Flask routes command subdomain display (shows Domain column only when any route has subdomain/host)

**Edge case:** When condition changes between invocations, column presence changes. This is correct behavior - output reflects actual content.

**How to apply:** Use automatic detection via `any()` or similar when adding optional columns that are often empty. Reserve flags for filtering behavior, not display choices.
