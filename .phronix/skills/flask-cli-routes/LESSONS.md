# Lessons — flask-cli-routes

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Add domain column to flask routes command

**2026-08-21** — Implemented logic in src/flask/cli.py to display a 'Domain' column in the `flask routes` output when any rule has a host or subdomain. This addresses the issue where routes were listed without indicating which subdomain they belong to, allowing users to see domain/subdomain information directly in the routes command.

The implementation:
- Detects if any rule has a host or subdomain.
- Adjusts table headers and column widths accordingly.
- Includes the domain value per rule, using host if host_matching is enabled, otherwise subdomain.

This change improves the usability of the `flask routes` CLI and satisfies the feature request to view routes per subdomain.
