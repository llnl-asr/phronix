# Lessons — column-command-domain

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — full-domain-column-always-shown does not work

**Tried**: full-domain-column-always-shown

**Hypothesis**: The issue's desired output shows the FULL domain (e.g. "admin.test.local") not just the subdomain fragment ("admin"). Building this requires combining rule.subdomain with app.config['SERVER_NAME'] (e.g. f"{rule.subdomain}.{server_name}" if rule.subdomain else server_name or ""), and the Domain column should always be shown as a 4th column regardless of whether subdomains are used. False if target 

**Refuted by**: test 0/1, train 0/4, validate 0/1. Do not re-propose this without new evidence.

## Lessons
