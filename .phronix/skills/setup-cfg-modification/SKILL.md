---
name: setup-cfg-modification
description: Update pytest configuration to ignore DeprecationWarnings
subject: setup-cfg-modification
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update pytest filterwarnings to ignore DeprecationWarning |
| `I2` | Instructions | Edit setup.cfg to ignore DeprecationWarnings |
| `I3` | Instructions | Placeholder |
| `I4` | Instructions | Edit file |
| `I5` | Instructions | test |
| `I6` | Instructions | edit |
| `I7` | Instructions | Edit setup.cfg |
| `X1` | References | apply_changes |









## Instructions

### I1 — Update pytest filterwarnings to ignore DeprecationWarning

Modify the [tool:pytest] section in setup.cfg to ignore DeprecationWarnings while still treating other warnings as errors. Replace the existing filterwarnings block with:
```
filterwarnings =
    ignore::DeprecationWarning
    error
```

### I2 — Edit setup.cfg to ignore DeprecationWarnings

Edit the setup.cfg file: replace lines 50-51 (filterwarnings block) with:
```
filterwarnings =
    ignore::DeprecationWarning
    error
```

### I3 — Placeholder

Placeholder

### I4 — Edit file

Edit the file

### I5 — test

test

### I6 — edit

edit

### I7 — Edit setup.cfg

Edit the setup.cfg file: replace the filterwarnings block with ignore DeprecationWarning.

## Rules

## References

### X1 — apply_changes

Edit the setup.cfg file to replace the filterwarnings block with ignore DeprecationWarning.

---
@@
- filterwarnings =
-    error
+ filterwarnings =
+    ignore::DeprecationWarning
+    error
---
