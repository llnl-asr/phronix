---
name: cli-sorting-source-vs-rows
description: Choosing between sorting source objects vs row lists when adding sortable columns
metadata:
  type: feedback
---

## Sorting Lists: Rule Objects vs Row Lists

When adding sortable columns to Flask CLI output, two approaches exist:

**Approach A: Sort source objects before building rows**
```python
# Sort rules (Rule objects) first
if sort == "domain":
    rules = sorted(rules, key=lambda r: r.subdomain or "")

# Then build rows from sorted rules
rows = []
for rule in rules:
    row = [rule.endpoint, rule.methods, rule.rule]
    if has_domain:
        row.append(rule.subdomain or "")
    rows.append(row)
```

**Approach B: Sort row lists after building**
```python
from operator import itemgetter

# Build all rows first
rows = []
for rule in rules:
    row = [rule.endpoint, methods, rule.rule]
    if has_domain:
        row.append(rule.subdomain or "")
    rows.append(row)

# Then sort rows by column index
if sort == "domain" and has_domain:
    rows.sort(key=itemgetter(3))
```

**When to use Approach A (recommended for Flask CLI):**
- Code already sorts source objects (Flask routes_command does this)
- Maintains existing architecture
- No new imports needed
- Cleaner code flow: sort → build → output

**When to use Approach B:**
- Sorting logic is complex and row-level is simpler
- Source objects don't support sorting key
- Multiple sort criteria need row context

**For Flask routes command:** Use Approach A. The existing code sorts rules using `attrgetter(sort)` and lambda functions. Adding domain sorting fits this pattern naturally: `key=lambda rule: (rule.host if host_matching else rule.subdomain) or ""`.

**Why:** Maintains code consistency, avoids new imports, and sorts at the correct semantic level (Rule objects, not display rows).

**How to apply:** When extending existing sorted output, follow the established pattern. Don't refactor sorting approach just to add a column.
