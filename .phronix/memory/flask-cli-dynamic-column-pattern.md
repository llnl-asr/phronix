---
name: flask-cli-dynamic-column-pattern
description: Pattern for extending Flask CLI table output with dynamic column count using list-based rows
metadata:
  type: reference
---

## Flask CLI Dynamic Column Extension Pattern

The Flask `routes_command` in src/flask/cli.py uses a hardcoded 3-column format that must be refactored to support variable columns.

**Current hardcoded pattern (lines 988-1034):**
```python
headers = ("Endpoint", "Methods", "Rule")  # Tuple, fixed 3
widths = (max(...), max(...), max(...))  # Tuple, fixed 3
row = "{{0:<{0}}}  {{1:<{1}}}  {{2:<{2}}}".format(*widths)  # Hardcoded 3
```

**Dynamic pattern (confirmed working via prototype):**
```python
# 1. Build headers as list (variable length)
headers = ["Endpoint", "Methods", "Rule"]
if condition:
    headers.append("NewColumn")

# 2. Build rows as lists (variable length)
rows = []
for item in items:
    row = [value1, value2, value3]
    if condition:
        row.append(value4)
    rows.append(row)

# 3. Calculate widths dynamically
widths = [
    max(len(headers[i]), max(len(str(row[i])) for row in rows))
    for i in range(len(headers))
]

# 4. Build format string dynamically
row_format = "  ".join(f"{{:<{w}}}" for w in widths)

# 5. Output
click.echo(row_format.format(*headers).strip())
click.echo(row_format.format(*["-" * w for w in widths]))
for row in rows:
    click.echo(row_format.format(*row).rstrip())
```

**Why:** This pattern enables conditional column display without breaking existing output. When condition=False, produces identical 3-column output.

**Key details:**
- Format string uses `{:<width}` not `{0:<width}` (no positional indices needed)
- Double space "  " separator between columns
- `.strip()` on header, `.rstrip()` on rows (trailing space handling)
- Empty values use `or ""` to convert None → empty string for display

**Tested:** Prototype confirmed 3-column and 4-column both align correctly.

**How to apply:** Use this pattern when extending Flask CLI commands with optional columns based on runtime conditions.
