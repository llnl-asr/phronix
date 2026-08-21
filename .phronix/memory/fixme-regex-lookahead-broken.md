---
name: fixme-regex-lookahead-broken
description: Adding lookahead to fixme regex prevents detection of non‑alphanumeric codetags
metadata:
  type: project
---

**Why:** The change in pylint/checkers/misc.py added a lookahead `(?=\s|$)` to the regex for notes and notes_rgx. This caused the fixme detection to miss codetags without following whitespace, as the test `test_non_alphanumeric_codetag` still failed and reported no fixme message.
**How to apply:** Avoid adding the lookahead, or ensure the regex matches end‑of‑line without requiring a space. Instead, keep the original pattern `rf"#\s*({notes}|{self.config.notes_rgx})\b"` or adjust to correctly capture end‑of‑line scenarios.
