---
name: sympy-sympy-16106
description: The sympy-sympy-16106 subject.
subject: sympy-sympy-16106
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |





## Instructions

### I1 — What problem it solves

A failing SymPy test accesses `user.email`, but the custom user model stores the email under the attribute `email_address`. The missing `email` attribute raises a `TypeError`.

### I2 — The key idea

The email field is actually named `email_address`, not `email`. Use that attribute instead of the nonexistent one.

### I3 — Instructions to solve it

1. Locate the code accessing `user.email` (e.g., in `tokens.py` line 99).\n2. Replace `user.email` with `user.email_address`.\n3. Update any similar references to the email field.\n4. Run the test suite to confirm the `TypeError` is resolved and no other tests fail.

## Rules

### R1 — Constraints and rules

- Do not modify other user fields or functionality of the custom user model.\n- Ensure all existing tests continue to pass after the change.\n- Preserve backward compatibility for any code that may have relied on the old `email` name (if any), by updating all references consistently.

## References

- `skill_load(name="sympy-sympy-16106", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

