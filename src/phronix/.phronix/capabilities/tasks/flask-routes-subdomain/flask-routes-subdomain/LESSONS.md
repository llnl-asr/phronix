# Lessons — flask-routes-subdomain

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The Flask CLI's "flask routes" command does not include subdomain or h

**2026-08-31** — The Flask CLI's "flask routes" command does not include subdomain or host columns even when the app enables subdomain_matching and host_matching. Tests expecting "Subdomain" or "Host" in the output will fail; additional implementation is required to expose this information.
