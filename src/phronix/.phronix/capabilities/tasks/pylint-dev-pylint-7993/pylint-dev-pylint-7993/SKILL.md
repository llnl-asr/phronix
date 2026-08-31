---
name: pylint-dev-pylint-7993
description: The pylint-dev-pylint-7993 subject.
subject: pylint-dev-pylint-7993
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 – Safe placeholder handling in TextReporter |
| `I2` | Instructions | I2 — Safe placeholder handling in TextReporter |
| `I3` | Instructions | Problem description |




## Instructions

### I1 — I7 – Safe placeholder handling in TextReporter

Modify `TextReporter.write_message` to use a safe formatting approach that preserves unknown placeholders. Replace the existing `self.writeln(self._fixed_template.format(**self_dict))` with:
```python
from collections import defaultdict
# Safe formatting: missing keys are left as their placeholder
safe_template = self._fixed_template
self.writeln(safe_template.format_map(defaultdict(lambda: '{' + key + '}', self_dict)))
```
This ensures that any placeholder not present in `self_dict` (e.g., `{categ}`) remains unchanged, preventing `KeyError` while still formatting known fields.

### I2 — I2 — Safe placeholder handling in TextReporter

Update `TextReporter.write_message` to use safe formatting that preserves unknown placeholders. Replace the line `self.writeln(self._fixed_template.format(**self_dict))` with:
```python
from collections import defaultdict
# Safe formatting: missing keys are left as their placeholder
safe_template = self._fixed_template
self.writeln(safe_template.format_map(defaultdict(lambda: '{' + key + '}', self_dict)))
```
This ensures any placeholder not present in `self_dict` (e.g., `{categ}`) remains unchanged, preventing `KeyError` while still formatting known fields.

### I3 — Problem description

The pylint tool fails when using custom braces in a message template, raising a UserWarning and a KeyError.

## Rules

## References

- `skill_load(name="pylint-dev-pylint-7993", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

