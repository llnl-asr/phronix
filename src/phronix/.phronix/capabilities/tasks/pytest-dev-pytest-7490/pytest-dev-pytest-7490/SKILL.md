---
name: pytest-dev-pytest-7490
description: The pytest-dev-pytest-7490 subject.
subject: pytest-dev-pytest-7490
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix add_marker default to True for dynamic markers |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Steps to fix |
| `I5` | Instructions | Diagnosis for pytest-dev-pytest-7490 |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — Fix add_marker default to True for dynamic markers

Update the `add_marker` method in `src/_pytest/nodes.py` to set the default `append` parameter back to `True`. This restores the original behavior where dynamically added markers are appended, fixing the xfail test failures.

### I2 — Problem description

Tests using dynamic xfail markers fail on pytest 6 because the API `request.node.add_marker` now raises an error.

### I3 — Key idea

Replace the deprecated call with the new marker registration function compatible with pytest 6.

### I4 — Steps to fix

1. Open `src/_pytest/fixtures.py`.
2. Import the new marker registration helper if needed, e.g., `from _pytest.mark import Mark`.
3. Replace `request.node.add_marker(mark)` with the updated API, e.g., `request.node.add_marker(mark, when='setup')` or use `request.node.add_marker(mark)` compatible with pytest 6.
4. Add a compatibility shim: wrap the new call in a try/except that falls back to the old call for pytest <6.
5. Run the affected test suite to confirm the dynamic xfail now works and all other tests still pass.
6. Commit the change.

### I5 — Diagnosis for pytest-dev-pytest-7490

Diagnosis: Task to write a skill named 'pytest-dev-pytest-7490'. This is the exact name the next attempt will use to look up the diagnosis. The skill was not previously filed under this name, so this diagnosis captures what was learned from the research-2.md file and the original task context. The original research was in attempt-2 of the phronix-bench run for pytest-dev/pytest-7490. Key context: this involves pytest development work. The diagnosis should be concise and reference the task without re-reading source files. Future attempts will use skill_lookup(name="pytest-dev-pytest-7490") to retrieve this.

## Rules

### R1 — Constraints and rules

- Do not modify any test files.
- Preserve existing behaviour for pytest <6.
- Ensure all existing tests continue to pass.

## References
