---
name: pylint-fixme-regex
description: Scope constraint for the W0511 regex fix
subject: pylint-fixme-regex
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Sibling approach exists: conditional-word-boundary |
| `R1` | Rules | Fix must cover self.config.notes, not just notes_rgx |
| `X1` | References | Root cause and confirmed fix live in pylint-dev-pylint-5859 |

## Instructions

### I1 — Sibling approach exists: conditional-word-boundary

A parallel investigation on topic pylint-dev__pylint-5859 already recorded an approach named `conditional-word-boundary` in research_status before this aspect (regex_fix_strategy) ran. This aspect's investigation did not inspect its internals (stayed in its own lane) but it likely overlaps heavily with `per_tag_boundary` (per-tag conditional \b based on whether the tag ends in a word character). Before implementing, compare both approaches' recorded details rather than re-deriving from scratch.

## Rules

### R1 — Fix must cover self.config.notes, not just notes_rgx

The trailing-boundary bug affects the `notes` join itself (self.config.notes — the built-in FIXME/XXX/TODO list, and any user-supplied custom notes list), not only the `notes_rgx` branch. A fix that only special-cases `notes_rgx` misses punctuation tags supplied via a plain `notes=[...]` config (e.g. `notes=[???]`). Confirmed refuted as approach `special_case_notes_rgx_only` (topic pylint-dev__pylint-5859).

## References

### X1 — Root cause and confirmed fix live in pylint-dev-pylint-5859

See [[pylint-dev-pylint-5859#X4]] for the full root-cause analysis (why a single trailing \b breaks punctuation-only note tags) and the confirmed per-tag conditional-\b fix. Not restated here to keep one canonical copy.
