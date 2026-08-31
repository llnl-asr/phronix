---
name: sphinx-doc-sphinx-8721
description: Fix viewcode extension to properly respect viewcode_enable_epub setting. The Sphinx viewcode extension incorrectly creates documentation pages for epub builds even when viewcode_enable_epub is disabled. The condition app.builder.name.startswith("epub") matches all epub variants but doesn't properly respect the viewcode_enable_epub configuration setting. Fix: change startswith("epub") to in {"epub"} for precise builder name matching.
subject: sphinx-doc-sphinx-8721
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Skip viewcode module pages for EPUB when disabled |
| `I2` | Instructions | I7 - Naming convention |
| `I3` | Instructions | I9 - What belongs in a skill vs memory |
| `R1` | Rules | Do not break existing viewcode functionality for HTML builds |
| `R2` | Rules | R1 - Problem recognition |
| `R3` | Rules | R2 - Fix scope |
| `R4` | Rules | R3 - Config integration |
| `R5` | Rules | R4 - Do not regress |

## Instructions

### I1 — Skip viewcode module pages for EPUB when disabled

In `sphinx/ext/viewcode.py` modify `collect_pages`:
```python
def collect_pages(app: Sphinx) -> Generator[Tuple[str, Dict[str, Any], str], None, None]:
    # Skip generating module pages for epub builds when viewcode is disabled
    if app.builder.name.startswith("epub") and not app.env.config.viewcode_enable_epub:
        return
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        return
    ...
```

### I2 — I7 - Naming convention

Skill name uses kebab-case slug matching the task: sphinx-doc-sphinx-8721

### I3 — I9 - What belongs in a skill vs memory

This skill contains: the problem symptom, key fix insight, precise file/line instructions, constraints from what worked, and pitfalls/lessons from what didn't work. Later runs will load this skill to automatically apply the fix without rediscovering it.

## Rules

### R1 — Do not break existing viewcode functionality for HTML builds

Any changes must preserve the generation of module pages when building HTML output, regardless of the viewcode_enable_epub setting.

### R2 — R1 - Problem recognition

A later run recognizing this problem will see: viewcode extension creating EPUB module pages even when viewcode_enable_epub=False is set. The symptom is EPUB module pages (_modules/...xhtml) being generated despite the setting being disabled.

### R3 — R2 - Fix scope

Only change the builder name check in sphinx/ext/viewcode.py line 9. Do not modify test files, other extensions, or the overall Sphinx architecture.

### R4 — R3 - Config integration

The viewcode_enable_epub config setting must be properly integrated with the builder name check. The fix must make test_viewcode_epub_enabled pass (enabled=True) and test_viewcode_epub_default pass (disabled=False).

### R5 — R4 - Do not regress

Must not regress the test_viewcode_epub_enabled test which confirms the fix works when viewcode_enable_epub=True. Must not affect html builder behavior.

## References

### X1 — X1 - Related task records

Tracker: $SCRATCH_ROOT/phronix-bench/runs/claude-0829-040235/claude-phronix/tasks/053-sphinx-doc__sphinx-8721/tracker.md

### X2 — X2 - Previous attempt diff

attempt-1/attempt-diff.patch shows the fix: startswith('epub') -> in {'epub'}
