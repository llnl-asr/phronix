---
name: mwaskom-seaborn-3407
description: Add draggable parameter to matplotlib Legend constructor
subject: mwaskom-seaborn-3407
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | fix_singlehtml_fignumber_timing |
| `I2` | Instructions | Add dot validation to Blueprint.__init__ |
| `I3` | Instructions | I7-naming |
| `I4` | Instructions | I9-what-belongs-in-skill |
| `R1` | Rules | R1-always-backward-compatible |
| `R2` | Rules | R2-keyword-only-position |
| `R3` | Rules | R3-draggable-true-creates-instance |
| `R4` | Rules | R4-draggable-false-none-keeps-None |

## Instructions

### I1 — fix_singlehtml_fignumber_timing

In sphinx/builders/singlehtml.py, the SingleFileHTMLBuilder.write() method currently calls assemble_doctree() first (which invokes resolve_references()), then restructures toc_fignumbers via assemble_toc_fignumbers() AFTER. But get_fignumber() in sphinx/domains/std.py uses the old dictionary format {docname: {figtype: {fig_id: ...}}} for lookups. By the time the lookup runs, the dict has been restructured to {master_doc: {docname/figtype: {fig_id: ...}}} using the alias "%s/%s" % (docname, figtype), causing KeyError/ValueError and the "WARNING: no number is assigned for table" warning.

Fix: Move self.env.toc_fignumbers = self.assemble_toc_fignumbers() to BEFORE self.assemble_doctree() in the write() method. This ensures resolve_references() and all subsequent figure number lookups use the already-restructured dictionary format, so get_fignumber() finds the correct figure numbers using the new {master_doc: {docname/figtype: {fig_id: ...}}} format.

### I2 — Add dot validation to Blueprint.__init__

Add validation in Blueprint.__init__ to raise ValueError when the blueprint name contains a dot ('.'). This is required since every dot is now significant for nested blueprints, consistent with the existing endpoint name validation at blueprints.py:363-364.

Insert the following code in src/flask/blueprints.py, in Blueprint.__init__, after self.name = name and before self.url_prefix = url_prefix:

    if "." in name:
        raise ValueError("Blueprint name cannot contain dots")

This follows the exact pattern as the existing endpoint validation:
    if endpoint:
        assert "." not in endpoint, "Blueprint endpoints should not contain dots"

The ValueError is appropriate for __init__ constructor validation, raising an explicit error when an invalid blueprint name with dots is provided.

### I3 — I7-naming

Skill name uses kebab-case: matplotlib-legend-draggable

### I4 — I9-what-belongs-in-skill

Skill contains: the problem it solves (symptom a later run recognizes), the key idea (one sentence claim), precise instructions (file, function, line changes), constraints and rules (what must stay true), pitfalls and lessons (what failed and why). Do NOT include: large code diffs, test output, or conversational narrative.

## Rules

### R1 — R1-always-backward-compatible

Default draggable=None means no draggable by default. Existing code must not break.

### R2 — R2-keyword-only-position

Parameter must be after * in signature to keep positional API intact.

### R3 — R3-draggable-true-creates-instance

When draggable=True, self._draggable = DraggableLegend(self).

### R4 — R4-draggable-false-none-keeps-None

When draggable=False or None, self._draggable = None.

## References

### X1 — X1-legend-pyplot-api

Works through both ax.legend(draggable=True) and plt.legend(draggable=True).
