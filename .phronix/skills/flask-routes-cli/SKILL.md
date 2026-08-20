---
name: flask-routes-cli
description: Flask CLI routes command column header requirements
subject: flask-routes-cli
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to add conditional columns to Flask routes command |
| `R1` | Rules | Target tests expect "Subdomain" and "Host" headers, not "Domain" |
| `R2` | Rules | Column order must keep Endpoint first for test compatibility |




## Instructions

### I1 — How to add conditional columns to Flask routes command

When adding new columns to the Flask routes CLI output:

1. **Detect dynamically**: Check if the column data exists (e.g., `any(rule.subdomain for rule in rules)` or `app.url_map.host_matching`)
2. **Use separate headers**: Target tests expect specific header names ("Subdomain", "Host") not generic ones ("Domain")
3. **Keep Endpoint first**: The `expect_order()` test helper assumes endpoint names start each line (position 0)
4. **Add column as 4th**: New columns go after Endpoint, Methods, Rule to preserve test compatibility
5. **Conditional rendering**: Only add the column when the data is present to avoid clutter
6. **Build format string dynamically**: Use `"{{0:<{0}}}  {{1:<{1}}}  {{2:<{2}}}  {{3:<{3}}}".format(*widths)` for 4 columns

The pattern: detect → conditionally build headers/values → use appropriate format string → render.

## Rules

### R1 — Target tests expect "Subdomain" and "Host" headers, not "Domain"

The test_subdomain and test_host tests in tests/test_cli.py check for specific header strings: `assert "Subdomain" in result.output` and `assert "Host" in result.output`. Using "Domain" as the column header causes both target tests to fail. The exact header naming matters for test validation.

### R2 — Column order must keep Endpoint first for test compatibility

The TestRoutes.expect_order() helper in tests/test_cli.py validates output by checking `line[:len(expect)] == expect` where expect is an endpoint name. This assumes Endpoint is the first column. Adding a new first column (e.g., Domain/Subdomain/Host) breaks test_simple and test_sort because they expect endpoint names at position 0. Either keep Endpoint as the first column, or update the column position conditional on whether domain info is present.

## References
