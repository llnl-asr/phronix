---
name: pallets-flask-4045
description: The pallets-flask-4045 subject.
subject: pallets-flask-4045
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Unresolved gap: Flask.register_blueprint (app.py) not inspected |
| `R1` | Rules | Existing dot-check style template in this file |
| `R2` | Rules | Do not add a blanket dot-rejection check on Blueprint(name=...) |
| `R3` | Rules | Blueprint name/endpoint/view_func dot checks must raise ValueError, not assert |
| `R4` | Rules | The registration-time name-collision assert was deliberately NOT converted to ValueError |
| `X1` | References | Blueprint.__init__ has no name validation currently |
| `X2` | References | How name_prefix concatenation works for nested blueprints |
| `X3` | References | Real upstream issue number is 4041, not 4045; CHANGES.rst wording available |









## Instructions

### I1 — Unresolved gap: Flask.register_blueprint (app.py) not inspected

The validation_site investigation deliberately scoped to Blueprint.__init__/add_url_rule/register in src/flask/blueprints.py and did not check Flask.register_blueprint in src/flask/app.py for any competing or duplicate name-dot validation. Before finalizing the fix location, confirm app.py's register_blueprint has no pre-existing dot check that would make the blueprints.py change redundant or conflicting.

## Rules

### R1 — Existing dot-check style template in this file

Blueprint.add_url_rule (lines 353-369) is the in-file precedent for dot-in-identifier checks: `assert "." not in endpoint, "Blueprint endpoints should not contain dots"` and `assert "." not in view_func.__name__, "Blueprint view function name should not contain dots"`. Both are asserts, placed at the top of the method before other logic, worded "X should not contain dots", and guarded by truthiness checks only because those params are optional (name in __init__ is required/positional, so no truthiness guard needed for a new check there). This is the strongest local style precedent, though it was not cross-checked against the actual upstream flask-4045 fix (no GitHub fetch performed) — treat the assert-vs-raise choice as unresolved, see approaches A3/A4.

### R2 — Do not add a blanket dot-rejection check on Blueprint(name=...)

tests/test_blueprints.py::test_dotted_names (line 256-273) intentionally constructs Blueprint names containing literal dots ("myapp.frontend", "myapp.backend") and registers them directly on the app. Blueprint.__init__ currently does zero validation on `name` (plain `self.name = name` at blueprints.py:191). Any fix for flask-4045 that adds unconditional "no dots allowed in Blueprint name" validation at construction time will break this existing/passing regression test. If a name check is needed at all, it must be scoped/conditional (e.g. only for self-nesting scenarios), not a blanket check in __init__.

### R3 — Blueprint name/endpoint/view_func dot checks must raise ValueError, not assert

Real Flask 2.0.2 (the actual next patch release after this task's base commit, fixing the real upstream issue #4041) converts ALL dot-related validation in src/flask/blueprints.py from bare `assert` to `raise ValueError(...)`, including the pre-existing endpoint and view_func checks in add_url_rule (previously `assert "." not in endpoint, "..."` and `assert "." not in view_func.__name__, "..."`). Asserts are stripped under `python -O`/`-OO` and are wrong for user-supplied input validation. Exact wording convention: `"'<param>' may not <condition>."` (single-quoted param name, trailing period). Exact strings confirmed in shipped source:
- `"'name' may not be empty."`
- `"'name' may not contain a dot '.' character."`
- `"'endpoint' may not contain a dot '.' character."`
- `"'view_func' name may not contain a dot '.' character."`
The new name-dot check goes in `Blueprint.__init__`, right after `super().__init__(...)`, before `self.name = name`.

### R4 — The registration-time name-collision assert was deliberately NOT converted to ValueError

In blueprints.py there's a separate `assert app.blueprints[self.name] is self, ("A name collision occurred between blueprints" ...)` check at registration time (~line 271 at base commit). Unlike the dot-related checks, upstream Flask 2.0.2 did NOT turn this into `ValueError` — it became an explicit `raise AssertionError(...)` (still AssertionError, just not a bare `assert` statement, likely to keep working under `python -O`). Don't assume every assert→exception conversion in this file should end up as ValueError; this one stays an AssertionError.

## References

### X1 — Blueprint.__init__ has no name validation currently

src/flask/blueprints.py lines 171-201: Blueprint.__init__ assigns `self.name = name` unconditionally at line 191 with zero validation. No other blueprint code re-validates self.name after construction — register() (lines 270-277) only asserts identity on name collision (`assert app.blueprints[self.name] is self`), not dot-in-name. This makes __init__ the single natural choke point for a dot-in-name check; register() is a weaker fallback site that fails later (at registration, not construction).

### X2 — How name_prefix concatenation works for nested blueprints

In src/flask/blueprints.py: BlueprintSetupState.add_url_rule (line ~101) builds endpoint as f"{self.name_prefix}{self.blueprint.name}.{endpoint}". Blueprint.register's self-nesting loop (line ~342-351) sets bp_options["name_prefix"] = options.get("name_prefix", "") + self.name + "." before recursing into child.register(app, bp_options). This is pure string concatenation — it does not crash or misbehave with dotted names, it just produces multi-segment/ambiguous endpoint strings. Separately, app.blueprints dict (collision check at blueprints.py:270-280) is keyed by the blueprint's own bare `.name`, not by the nested/prefixed full name — so two different parents nesting same-named children could collide in app.blueprints even though final endpoint prefixes differ; this edge case is unconfirmed/untested (no test found exercising it), flagged as adjacent-but-unverified, not the aspect's main answer.

### X3 — Real upstream issue number is 4041, not 4045; CHANGES.rst wording available

Task title "4045" is this benchmark's synthetic numbering — the actual Flask GitHub issue is #4041. If CHANGES.rst needs an entry, real wording (Flask 2.0.2 CHANGES.rst line 44-46): "Show an error when a blueprint name contains a dot. The ``.`` has special meaning, it is used to separate (nested) blueprint names and the endpoint name. :issue:`4041`". Don't write `:issue:`4045`` — use 4041 if matching upstream exactly matters.
