---
name: sphinx-doc-sphinx-8713
description: The sphinx-doc-sphinx-8713 subject.
subject: sphinx-doc-sphinx-8713
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Apply fix for other parameters handling |
| `I2` | Instructions | Fix _parse_other_parameters_section to check napoleon_use_param |
| `I3` | Instructions | Actual bug: method ignores config flag |
| `I4` | Instructions | Root cause: missing conditional logic |

## Instructions

### I1 — Apply fix for other parameters handling

In `sphinx/ext/napoleon/docstring.py`, modify `_parse_other_parameters_section`:
```python
-        return self._format_fields(_('Other Parameters'), self._consume_fields())
+        if self._config.napoleon_use_param:
+            # reuse same handling as parameters
+            fields = self._consume_fields(multiple=True)
+            return self._format_docutils_params(fields)
+        else:
+            return self._format_fields(_('Other Parameters'), self._consume_fields())
```

### I2 — Fix _parse_other_parameters_section to check napoleon_use_param

Fix _parse_other_parameters_section (sphinx/ext/napoleon/docstring.py:684-685) to check self._config.napoleon_use_param, mirroring _parse_parameters_section pattern (lines 687-694). When True: use _consume_fields(multiple=True) and _format_docutils_params. When False: use _consume_fields() and _format_fields(_('Other Parameters'), fields).

### I3 — Actual bug: method ignores config flag

The _parse_other_parameters_section method (line 684-685) always uses self._consume_fields() without the multiple parameter and always uses _format_fields with 'Other Parameters', completely ignoring self._config.napoleon_use_param. Unlike _parse_parameters_section (lines 687-694) which conditionally uses the flag to switch between docutils format and Napoleon format, _parse_other_parameters_section has no conditional logic at all.

### I4 — Root cause: missing conditional logic

Root cause: _parse_other_parameters_section lacks the if/else conditional on self._config.napoleon_use_param that _parse_parameters_section implements. It unconditionally calls self._consume_fields() (without multiple=True) and _format_fields(), so it never switches to docutils param formatting even when napoleon_use_param=True.

## References
