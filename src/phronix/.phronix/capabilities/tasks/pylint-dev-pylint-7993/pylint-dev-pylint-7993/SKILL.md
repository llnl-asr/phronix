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
| `I4` | Instructions | The patch that made the tests pass |

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

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/pylint/reporters/text.py b/pylint/reporters/text.py
index 29bd46798..642a90f38 100755
--- a/pylint/reporters/text.py
+++ b/pylint/reporters/text.py
@@ -177,6 +177,11 @@ class TextReporter(BaseReporter):
         # Check to see if all parameters in the template are attributes of the Message
         arguments = re.findall(r"\{(.+?)(:.*)?\}", template)
         for argument in arguments:
+            # If the field name contains braces (e.g., nested template like { "key": "{value}" }),
+            # don't try to remove it — it's not a simple field name and str.format() will
+            # handle it (by leaving it as-is) rather than breaking the template.
+            if "{" in argument[0] or "}" in argument[0]:
+                continue
             if argument[0] not in MESSAGE_FIELDS:
                 warnings.warn(
                     f"Don't recognize the argument '{argument[0]}' in the --msg-template. "
```

## Rules
