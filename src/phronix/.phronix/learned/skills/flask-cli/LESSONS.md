# Lessons — flask-cli

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Domain column addition broke existing CLI output

**2026-08-21** — Adding a 'Domain' column to the `flask routes` command changed the table header and row formatting. This caused multiple test failures: missing 'Subdomain' header, empty output, and a TypeError due to mismatched column widths. Future modifications must preserve the original output format (or update corresponding tests) and ensure width calculations and row format string include all columns consistently.
