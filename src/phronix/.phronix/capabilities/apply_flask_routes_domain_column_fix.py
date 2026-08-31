import os

OLD = '''    rule_methods = [
        ", ".join(sorted(rule.methods - ignored_methods))  # type: ignore
        for rule in rules
    ]

    headers = ("Endpoint", "Methods", "Rule")
    widths = (
        max(len(rule.endpoint) for rule in rules),
        max(len(methods) for methods in rule_methods),
        max(len(rule.rule) for rule in rules),
    )
    widths = [max(len(h), w) for h, w in zip(headers, widths)]
    row = "{{0:<{0}}}  {{1:<{1}}}  {{2:<{2}}}".format(*widths)

    click.echo(row.format(*headers).strip())
    click.echo(row.format(*("-" * width for width in widths)))

    for rule, methods in zip(rules, rule_methods):
        click.echo(row.format(rule.endpoint, methods, rule.rule).rstrip())'''

NEW = '''    rule_methods = [
        ", ".join(sorted(rule.methods - ignored_methods))  # type: ignore
        for rule in rules
    ]
    host_matching = current_app.url_map.host_matching
    rule_domains = [
        (rule.host if host_matching else rule.subdomain) or "" for rule in rules
    ]
    has_domain = any(rule_domains)
    domain_header = "Host" if host_matching else "Subdomain"

    headers = ["Endpoint", "Methods", "Rule"]
    widths = [
        max(len(rule.endpoint) for rule in rules),
        max(len(methods) for methods in rule_methods),
        max(len(rule.rule) for rule in rules),
    ]
    if has_domain:
        headers.insert(2, domain_header)
        widths.insert(2, max(len(domain) for domain in rule_domains))

    widths = [max(len(h), w) for h, w in zip(headers, widths)]
    row = "  ".join(f"{{{i}:<{w}}}" for i, w in enumerate(widths))

    click.echo(row.format(*headers).strip())
    click.echo(row.format(*("-" * width for width in widths)))

    for rule, methods, domain in zip(rules, rule_methods, rule_domains):
        fields = [rule.endpoint, methods, rule.rule]
        if has_domain:
            fields.insert(2, domain)
        click.echo(row.format(*fields).rstrip())'''


def register(mcp):
    @mcp.tool()
    def apply_flask_routes_domain_column_fix(repo_path: str) -> str:
        """Patch src/flask/cli.py's routes_command to add a conditional
        Host/Subdomain column to `flask routes` output.

        repo_path: path to a Flask checkout (the directory containing
        'src/flask/cli.py').

        Idempotent: if the fix is already applied, reports that instead of
        erroring. Returns a JSON string {status, detail}.
        """
        import json

        target = os.path.join(repo_path, "src", "flask", "cli.py")
        if not os.path.isfile(target):
            return json.dumps({"status": "error", "detail": f"not found: {target}"})

        with open(target, "r") as f:
            content = f.read()

        if NEW in content:
            return json.dumps({"status": "ok", "detail": "already applied"})

        if OLD not in content:
            return json.dumps(
                {
                    "status": "error",
                    "detail": "expected old routes_command body not found; "
                    "the file may already differ from the base commit",
                }
            )

        content = content.replace(OLD, NEW, 1)
        with open(target, "w") as f:
            f.write(content)

        return json.dumps({"status": "ok", "detail": "patched"})
