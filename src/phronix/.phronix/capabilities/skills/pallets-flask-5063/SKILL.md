---
name: pallets-flask-5063
description: What is known about pallets-flask-5063: The patch that made the tests pass, What has been achieved so far, and what has not
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The patch that made the tests pass |
| `R2` | Rules | What has been achieved so far, and what has not |

## Instructions

### I1 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/src/flask/cli.py b/src/flask/cli.py
index 37a15ff2..93f16c97 100755
--- a/src/flask/cli.py
+++ b/src/flask/cli.py
@@ -1018,20 +1018,50 @@ def routes_command(sort: str, all_methods: bool) -> None:
         for rule in rules
     ]
 
-    headers = ("Endpoint", "Methods", "Rule")
-    widths = (
+    headers = ("Endpoint", "Methods", "Rule", "Host" if current_app.url_map.host_matching else "Subdomain")
+    # Determine column widths, including the optional Host/Subdomain column
+    widths = [
         max(len(rule.endpoint) for rule in rules),
         max(len(methods) for methods in rule_methods),
         max(len(rule.rule) for rule in rules),
-    )
+    ]
+    # Compute domain values for each rule when needed
+    domains = []
+    for rule in rules:
+        if current_app.url_map.host_matching:
+            domain = rule.host or current_app.config.get("SERVER_NAME", "")
+        else:
+            sub = rule.subdomain or ""
+            server = current_app.config.get("SERVER_NAME", "")
+            domain = f"{sub}.{server}" if sub and server else sub or server
+        domains.append(domain)
+    has_domain = any(bool(d) for d in domains)
+    # Add optional column header and width if any domain is present
+    if has_domain:
+        headers = ("Endpoint", "Methods", "Rule", "Host" if current_app.url_map.host_matching else "Subdomain")
+        widths.append(max(len(headers[-1]), max(len(d) for d in domains)))
+    else:
+        # Keep original headers without the extra column
+        headers = ("Endpoint", "Methods", "Rule")
     widths = [max(len(h), w) for h, w in zip(headers, widths)]
-    row = "{{0:<{0}}}  {{1:<{1}}}  {{2:<{2}}}".format(*widths)
-
-    click.echo(row.format(*headers).strip())
-    click.echo(row.format(*("-" * width for width in widths)))
-
-    for rule, methods in zip(rules, rule_methods):
-        click.echo(row.format(rule.endpoint, methods, rule.rule).rstrip())
+    # Build row format string dynamically based on number of columns
+    # Build row format string based on number of columns
+    # Build row format string with proper placeholders
+    row_parts = []
+    for i, w in enumerate(widths):
+        row_parts.append(f"{{{i}:<{w}}}")
+    row_fmt = "  ".join(row_parts)
+
+    # Print header and separator
+    click.echo(row_fmt.format(*headers).strip())
+    click.echo(row_fmt.format(*["-" * w for w in widths]).strip())
+
+    # Print each rule row, including domain if present
+    for rule, methods, domain in zip(rules, rule_methods, domains):
+        if has_domain:
+            click.echo(row_fmt.format(rule.endpoint, methods, rule.rule, domain).rstrip())
+        else:
+            click.echo(row_fmt.format(rule.endpoint, methods, rule.rule).rstrip())
 
 
 cli = FlaskGroup(
```

## Rules

### R2 — What has been achieved so far, and what has not

**Already passing (2 of 2).** Do not rewrite the code that makes these pass — they are the part that works:
- `tests/test_cli.py::TestRoutes::test_host`
- `tests/test_cli.py::TestRoutes::test_subdomain`

Measured after try 3.
