# Lessons — flask-routes-domain-fix

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Missing domain info in `flask routes` output

**2026-08-21** — Symptom: `flask routes` shows only endpoint, methods, rule but no subdomain/domain columns. Root cause: The Flask CLI `routes` command does not compute or display the subdomain information from each rule. Fix: Edit `src/flask/cli.py` (or `src/flask/cli.py` path in the Flask source) to compute `server_name = current_app.config.get('SERVER_NAME', '')` and for each rule, derive `domain = f"{rule.subdomain}.{server_name}"` if `rule.subdomain` else `server_name`. Add a `Domain` column to the routes table header and include the computed domain in each row output.
