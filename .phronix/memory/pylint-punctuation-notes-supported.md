---
name: pylint-punctuation-notes-supported
description: Pylint now supports punctuation-only note tags via --notes
metadata:
  type: project
---

The `EncodingChecker` builds its regex without a word‑boundary anchor, allowing tags such as `???` to be matched when listed in `--notes`. This fixes the earlier bug where such tags were ignored. Confirmed by running `pylint tmp_test_notes.py --notes=???` which emits a W0511 warning.
