---
name: pylint-fixme-regex
description: The pylint-fixme-regex subject.
subject: pylint-fixme-regex
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Enforce word boundary after note keywords |


## Instructions

## Rules

### R1 — Enforce word boundary after note keywords

Update the notes regular expression to require a non‑word character or end of string after the note keyword. Use `rf"#\s*({notes})(?=\W|$)"` instead of `rf"#\s*({notes})\b"`. This prevents false positives when notes are followed by punctuation (e.g., `YES:`).

## References
