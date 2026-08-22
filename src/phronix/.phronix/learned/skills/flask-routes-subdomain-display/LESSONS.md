# Lessons — flask-routes-subdomain-display

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — add-subdomain-column-only does not work

**Tried**: add-subdomain-column-only

**Hypothesis**: Adding a "Subdomain" column showing only rule.subdomain value (without SERVER_NAME) is simpler and handles missing SERVER_NAME gracefully. Falsified if: users need full domain reconstruction, or column is confusing without context.

**Refuted by**: test 0/1, validate 0/1. Do not re-propose this without new evidence.

## Lessons

### L1 — Conditional auto-detect subdomain/host column implementation validated

**2026-08-19** — **Implementation that worked (validated in attempt 2):**

Modified `src/flask/cli.py` function `routes_command` to conditionally add domain column:

```python
# Detect which column to show
has_domain = False
domain_column = None
if current_app.url_map.host_matching:
    has_domain = True
    domain_column = "Host"
elif any(rule.subdomain for rule in rules):
    has_domain = True
    domain_column = "Subdomain"

# Branch based on has_domain
if has_domain:
    # Build domain_values list based on domain_column type
    # Use 4-column headers and format string
    # zip(rules, rule_methods, domain_values) in output loop
else:
    # Keep existing 3-column format (backward compatible)
```

Result: 2/2 target tests pass, 54/54 regression tests pass.

**Why this succeeded:** Conditional display keeps output clean when no domains exist, auto-detection handles both host_matching and subdomain modes, proper header naming satisfies tests, Endpoint-first preserves test compatibility.
