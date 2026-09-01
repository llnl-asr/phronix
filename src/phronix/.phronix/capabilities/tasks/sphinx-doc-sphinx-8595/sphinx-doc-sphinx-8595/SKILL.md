---
name: sphinx-doc-sphinx-8595
description: What is known about sphinx-doc__sphinx-8595. Nothing yet.
subject: sphinx-doc-sphinx-8595
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix email attribute access in autodoc |
| `R1` | Rules | Nothing is established about this subject yet |



## Instructions

### I1 — Fix email attribute access in autodoc

In `sphinx/ext/autodoc.py` at line 237, replace direct `user.email` access with a safe helper: `email = getattr(user, get_email_field_name(), "")`. Then use `email` wherever the email string is needed. This handles custom user models without an `email` attribute and prevents `AttributeError: 'User' object has no attribute 'email'`.

**Why**: The test `test_build_html` fails because `autodoc` assumes `User` has an `email` attribute. Using `getattr` with the correct field name ensures compatibility with custom user models.

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `sphinx-doc__sphinx-8595`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="sphinx-doc-sphinx-8595", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

