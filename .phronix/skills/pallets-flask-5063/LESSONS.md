# Lessons — pallets-flask-5063

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — probe_reproduce_flask_routes_domain generates a snippet with an indentation bug

`probe_reproduce_flask_routes_domain` (an MCP capability tool for this topic) generates a Python repro snippet with an indentation error, so its output cannot be trusted/run as-is. Don't lose time assuming the generated snippet is correct when a run fails — inspect and fix the snippet's indentation, or reproduce manually against `src/flask/cli.py`'s `routes_command` instead.

## Lessons
