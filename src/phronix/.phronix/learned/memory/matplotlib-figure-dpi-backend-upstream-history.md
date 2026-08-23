---
name: matplotlib-figure-dpi-backend-upstream-history
description: Summary of research on backend figure DPI doubling issue for matplotlib 3.5 on macOS
metadata:
  type: project
---

The upstream‑history stage for the DPI‑doubling bug (matplotlib__matplotlib-23476) was completed. The research identified several open aspects:
- `lib/matplotlib/_c_internal_utils.py`, `lib/matplotlib/_path.py`, `lib/matplotlib/cbook/__init__.py`, `lib/matplotlib/figure.py`, `lib/matplotlib/ft2font.py`
- Potential files `tmpfig.pickle`, `tmpfig2.pickle`
- Unanswered aspects: `dpi_stability`, `backend_effect`, `platform_variation`
Details of what was examined are recorded in the skill `backend-figure-matplotlib` (see its References section). No definitive fix was found in this stage.

**Why:** This record captures what has been investigated and what remains open, enabling the next research stage to focus on the unanswered aspects without re‑probing already examined files.

**How to apply:** When planning the next approach, prioritize addressing the three open aspects (`dpi_stability`, `backend_effect`, `platform_variation`) and explore the listed source files. Link to the skill `backend-figure-matplotlib` for full context.
