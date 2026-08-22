---
name: flask-cli-format-string-escaping
description: Flask CLI format string pattern using double-brace escaping vs modern f-string approach
metadata:
  type: reference
---

## Flask Routes Command Format String Double-Brace Escaping

The current Flask `routes_command` uses a tricky double-format pattern that appears confusing but is standard Python format string escaping.

**Current pattern in src/flask/cli.py:**
```python
row = "{{0:<{0}}}  {{1:<{1}}}  {{2:<{2}}}".format(*widths)
```

**How it works:**
1. Double braces `{{` and `}}` are literal braces in the string
2. Single braces `{0}` are .format() substitution points
3. First .format(*widths) with widths=[20, 15, 30] produces: `"{0:<20}  {1:<15}  {2:<30}"`
4. Second .format(endpoint, methods, rule) fills in actual data

**Why this exists:** Historical pattern for pre-computing column widths.

**Modern replacement (simpler):**
```python
row_format = "  ".join(f"{{:<{w}}}" for w in widths)
# Produces: "{:<20}  {:<15}  {:<30}"
# No positional indices needed
```

**Why modern is better:**
- More readable (single f-string instead of double-brace escaping)
- Works with variable column count (loop-generated)
- Only one .format() call needed (at output time)

**When to use:** The modern pattern is preferred for new code or refactoring. The double-brace pattern only made sense when widths were computed inline with format string construction.

**Pitfall:** Do not mix up the double-brace escaping. `{{{0}}}` means literal brace + substitution + literal brace.
