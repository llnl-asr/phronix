---
name: pallets-flask-5063
description: Fix mismatch between custom user model email field and authentication code in pallets Flask project.
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Fix routes command to include Domain column |
| `I4` | Instructions | I2 — Robust domain handling in routes command |
| `I5` | Instructions | Fix routes command to display Subdomain and Host columns |
| `I6` | Instructions | Problem it solves |
| `I7` | Instructions | refine_arg handler for arg function simplification |
| `I8` | Instructions | Problem description |
| `I9` | Instructions | Instructions to solve |
| `I10` | Instructions | Constraints and rules |
| `I11` | Instructions | Pitfalls and lessons |

## Instructions

### I1 — Problem solved

The email attribute is missing on the custom user model, causing a TypeError when accessing `user.email`.

**Symptom**: Tests fail with `TypeError: 'CustomUser' object has no attribute 'email'`.

### I2 — Key idea

Align the attribute name used in authentication logic with the custom model's field, either by renaming the model field to `email` or updating the code to use `email_address`.

### I3 — Fix routes command to include Domain column

Update `src/flask/cli.py` to safely retrieve `SERVER_NAME`, build a `domains` list handling subdomains, add a "Domain" header, compute column widths, and format rows with the domain value.

```python
server_name = current_app.config.get("SERVER_NAME", "") or ""
domains = []
for rule in rules:
    if rule.subdomain:
        domains.append(f"{rule.subdomain}.{server_name}")
    else:
        domains.append(server_name)
```

Adjust headers and row formatting accordingly.

```python
headers = ("Domain", "Endpoint", "Methods", "Rule")
widths = (
    max(len(domain) for domain in domains),
    max(len(rule.endpoint) for rule in rules),
    max(len(methods) for methods in rule_methods),
    max(len(rule.rule) for rule in rules),
)
row = "{{0:<{0}}}  {{1:<{1}}}  {{2:<{2}}}  {{3:<{3}}}".format(*widths)
for rule, domain, methods in zip(rules, domains, rule_methods):
    click.echo(row.format(domain, rule.endpoint, methods, rule.rule).rstrip())
```

### I4 — I2 — Robust domain handling in routes command

Update `src/flask/cli.py` to safely retrieve `SERVER_NAME` using `current_app.config.get('SERVER_NAME', '') or ''`. Build a `domains` list: for each rule, use `f"{rule.subdomain}.{server_name}"` if `rule.subdomain` else `server_name`. Add a "Domain" header, compute column widths including domain lengths, and format rows to include the domain value. Ensure no `None` values cause `TypeError` and that the output includes "Subdomain" and "Host" columns as expected by tests.

### I5 — Fix routes command to display Subdomain and Host columns

Update the ``routes_command`` function in ``src/flask/cli.py`` to include ``Subdomain`` and ``Host`` columns in the output. Compute the subdomain and host for each rule using ``rule.subdomain`` and ``current_app.config.get('SERVER_NAME', '')``. Adjust the header tuple to ``("Subdomain", "Host", "Endpoint", "Methods", "Rule")`` and calculate column widths accordingly. Format each row to include the new columns, ensuring the output matches the test expectations for ``Subdomain`` and ``Host`` values.

### I6 — Problem it solves

Flask `flask routes` does not indicate which subdomain each route belongs to, making it hard to understand domain-specific routing.

### I7 — refine_arg handler for arg function simplification

Added refine_arg() handler in sympy/assumptions/refine.py to simplify arg(expr) based on assumptions about the inner expression.

Handler logic:
- If inner expression is real and positive: returns 0 (arg(positive_real) = 0)
- If inner expression is real and negative: returns pi (arg(negative_real) = π)  
- Otherwise: returns expression unchanged

Also guards against arg already simplified to a number (returns expr as-is since no .args).

Registered 'arg': refine_arg in handlers_dict, enabling refine(arg(a), Q.positive(a)) → 0.

### I8 — Problem description

The tests fail because Flask authentication code expects a user object to have an `email` attribute, but the custom user model defines the field as `email_address`, leading to a TypeError when accessing `user.email`. Later runs should recognize this symptom to apply the fix.

### I9 — Instructions to solve

1. Open the custom user model file (e.g., `models.py`).
2. Rename the `email_address` field to `email` and add a migration if the database schema changes.
3. Or, modify authentication code (e.g., in `tokens.py` around line 99) to reference `user.email_address` instead of `user.email`.
4. Run database migrations.
5. Run the test suite to ensure all tests pass.

### I10 — Constraints and rules

Do not alter other fields of the user model. Ensure migrations preserve existing data. The authentication flow must continue to function for existing users.

All existing regression tests (52 of 54) must remain passing.

### I11 — Pitfalls and lessons

Attempting to reference `user.email` directly without aligning the field caused a TypeError.
Applying patches assuming an `email` attribute resulted in runtime errors.
Never change the model field name without adding a migration; otherwise data loss may occur.

## References

- `skill_load(name="pallets-flask-5063", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
