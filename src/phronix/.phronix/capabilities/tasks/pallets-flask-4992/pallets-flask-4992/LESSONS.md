# Lessons — pallets-flask-4992

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempted to fix Config

**2026-08-29** — Attempted to fix Config.from_file by adding a mode parameter and a stub for cgi.valid_boundary, but target test `test_inline_variable_array_repr_custom` still failed with ValueError for mode string and TypeError for unexpected keyword 'text' in from_file. The change did not affect the MediaOrderConflictWarning issue. Regression tests passed.

### L2 — Attempted to add a mode parameter to Config

**2026-08-29** — Attempted to add a mode parameter to Config.from_file but used an invalid default 't' and passed it directly to open, causing ValueError for mode string and TypeError for unexpected 'text' argument in tests. Also did not validate mode, leading to regressions.

### L3 — Mode parameter mismatch in Config.from_file

**2026-08-29** — Adding a mode parameter to Config.from_file() does not solve the issue because the method signature does not accept a 'mode' argument; tests call the method with an unexpected 'text' keyword causing TypeError. The proper fix requires updating the method signature to accept the argument used by callers or adjusting caller usage.

### L4 — P1 Fallback getattr returns empty

**2026-08-29** — Using `getattr(user, 'email', '')` without ensuring the attribute exists results in missing email in output; not a viable fix when the model lacks the field.

### L5 — P2 Changing field name breaks validation

**2026-08-29** — Renaming `CustomEmailField` to `email_address` caused TypeError in `tokens.py:99` during validation of existing user records; field name changes must be backward compatible.
