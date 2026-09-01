---
name: sphinx-doc-sphinx-8713
description: The sphinx-doc-sphinx-8713 subject.
subject: sphinx-doc-sphinx-8713
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix _parse_other_parameters_section to check napoleon_use_param |
| `I2` | Instructions | Actual bug: method ignores config flag |
| `I3` | Instructions | Root cause: missing conditional logic |
| `I4` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix _parse_other_parameters_section to check napoleon_use_param

Fix _parse_other_parameters_section (sphinx/ext/napoleon/docstring.py:684-685) to check self._config.napoleon_use_param, mirroring _parse_parameters_section pattern (lines 687-694). When True: use _consume_fields(multiple=True) and _format_docutils_params. When False: use _consume_fields() and _format_fields(_('Other Parameters'), fields).

### I2 — Actual bug: method ignores config flag

The _parse_other_parameters_section method (line 684-685) always uses self._consume_fields() without the multiple parameter and always uses _format_fields with 'Other Parameters', completely ignoring self._config.napoleon_use_param. Unlike _parse_parameters_section (lines 687-694) which conditionally uses the flag to switch between docutils format and Napoleon format, _parse_other_parameters_section has no conditional logic at all.

### I3 — Root cause: missing conditional logic

Root cause: _parse_other_parameters_section lacks the if/else conditional on self._config.napoleon_use_param that _parse_parameters_section implements. It unconditionally calls self._consume_fields() (without multiple=True) and _format_fields(), so it never switches to docutils param formatting even when napoleon_use_param=True.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sphinx/ext/napoleon/docstring.py b/sphinx/ext/napoleon/docstring.py
index 755088ca5..055c42e6b 100755
--- a/sphinx/ext/napoleon/docstring.py
+++ b/sphinx/ext/napoleon/docstring.py
@@ -682,7 +682,12 @@ class GoogleDocstring:
         return self._parse_generic_section(_('Notes'), use_admonition)
 
     def _parse_other_parameters_section(self, section: str) -> List[str]:
-        return self._format_fields(_('Other Parameters'), self._consume_fields())
+        if self._config.napoleon_use_param:
+            # reuse same handling as parameters
+            fields = self._consume_fields(multiple=True)
+            return self._format_docutils_params(fields)
+        else:
+            return self._format_fields(_('Other Parameters'), self._consume_fields())
 
     def _parse_parameters_section(self, section: str) -> List[str]:
         if self._config.napoleon_use_param:
```

## Rules
