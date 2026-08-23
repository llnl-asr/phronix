---
name: backend-figure-matplotlib
description: Research on backend figure matplotlib. Covers does Figure.__setstate__ correctly restore the figure.dpi attribute from the pickle; does backend_macosx.FigureCanvas __init__ compute pixel dimensions using int conversion that overflows for high DPI values; is a retina scaling factor applied in the MacOSX backend during unpickling, causing DPI to double. Approaches tried: lib/matplotlib/_c_internal_utils.py, lib/matplotlib/_path.py, lib/matplotlib/cbook/__init__.py, lib/matplotlib/figure.py, lib/matplotlib/ft2font.py, tmpfig.pickle, tmpfig2.pickle.
subject: backend-figure-matplotlib
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to backend figure matplotlib |
| `X1` | References | Where research on this subject stands |












## Instructions

### I1 — How to evaluate a change to backend figure matplotlib

Figure of merit: **test_pass** (max, target 1.0).

Measured by: 1 if target test passes else 0

Cases differ along: backend, dpi, platform.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **test_pass** (max, target 1.0).

**Still open**
- lib/matplotlib/_c_internal_utils.py, lib/matplotlib/_path.py, lib/matplotlib/cbook/__init__.py, lib/matplotlib/figure.py, lib/matplotlib/ft2font.py, tmpfig.pickle, tmpfig2.pickle (potential)
- aspect not yet answered: dpi_stability
- aspect not yet answered: backend_effect
- aspect not yet answered: platform_variation

**Where the detail is**
- lib/matplotlib/_c_internal_utils.py, lib/matplotlib/_path.py, lib/matplotlib/cbook/__init__.py, lib/matplotlib/figure.py, lib/matplotlib/ft2font.py, tmpfig.pickle, tmpfig2.pickle: benchmark attempt
- full record: research topic `matplotlib__matplotlib-23476` (via research_status, only if this summary is not enough)