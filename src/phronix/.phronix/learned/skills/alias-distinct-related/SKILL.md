---
name: alias-distinct-related
description: Research on alias distinct related. Covers does select_related correctly resolve the alias created by FilteredRelation when the alias name overlaps with existing fields; is the SQL join generated for the filtered relation duplicated or incorrect, causing wrong related object; would using prefetch_related instead of select_related bypass the bug and yield correct objects. Approaches tried: (no files changed).
subject: alias-distinct-related
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `X1` | References | Where research on this subject stands |



## Instructions

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

**Still open**
- (no files changed) (potential)
- aspect not yet answered: alias-resolution-bug
- aspect not yet answered: join-duplication
- aspect not yet answered: prefetch-alternative
- aspect not yet answered: distinct-needed
- aspect not yet answered: annotation-name-collision

**Where the detail is**
- (no files changed): benchmark attempt
- full record: research topic `django__django-16408` (via research_status, only if this summary is not enough)