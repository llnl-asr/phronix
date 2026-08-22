---
name: flask
description: Research on flask. Covers does flask routes correctly assign subdomains to endpoints; are static files correctly associated with default domain. Approaches tried: sitecustomize.py, src/flask/cli.py, src/flask/globals.py.
subject: flask
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to flask |
| `R1` | Rules | Disallow dots in blueprint names using explicit check, not assert |
| `X1` | References | Where research on this subject stands |


















## Instructions

### I1 — How to evaluate a change to flask

Figure of merit: **flask_routes_subdomain_accuracy** (max, target 1.0).

Measured by: ratio of correctly assigned subdomains in flask routes output

Cases differ along: blueprint, endpoint, subdomain_type.

## Rules

### R1 — Disallow dots in blueprint names using explicit check, not assert

**Why:** Using `assert` for input validation can be disabled with the `-O` flag and raises `AssertionError`, which may not match expected error types. This caused test failures for blueprint name validation.

**How to apply:** Replace `assert '.' not in name, 'Blueprint name should not contain dots'` with:
```python
if '.' in name:
    raise ValueError('Blueprint name must not contain dots')
```

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **passed_tests** (max, target 2.0).

**Still open**
- sitecustomize.py, src/flask/cli.py, src/flask/globals.py (potential)
- aspect not yet answered: add-host-column
- aspect not yet answered: add-subdomain-column
- aspect not yet answered: add-domain-column

**Where the detail is**
- sitecustomize.py, src/flask/cli.py, src/flask/globals.py: benchmark attempt
- full record: research topic `pallets__flask-5063` (via research_status, only if this summary is not enough)