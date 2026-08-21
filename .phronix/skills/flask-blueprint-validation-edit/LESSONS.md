# Lessons — flask-blueprint-validation-edit

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Blueprint dot name validation failure

**2026-08-21** — Symptom: tests `test_dotted_name_not_allowed` and `test_route_decorator_custom_endpoint_with_dots` fail because blueprint names, endpoints, or view function names containing a dot are not rejected. Root cause: `src/flask/blueprints.py` lacks validation for dots in blueprint name, endpoint, and view function name. Fix: Add checks that raise `ValueError` if a dot is present in `name` (Blueprint.__init__), `endpoint` (Blueprint.add_url_rule), or `view_func.__name__` (Blueprint.add_url_rule). See instruction `I1` in this skill for exact code changes.
