# Lessons — matplotlib-matplotlib-25442

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfall: disconnect() canvas access after ref_artist.figure is None

**2026-08-29** — Pitfall: AttributeError when disconnect() accesses canvas property after ref_artist.figure is None

When implementing changes to DraggableBase in matplotlib's offsetbox.py, a common issue occurs when:
- _check_still_parented() detects self.ref_artist.figure is None
- It calls disconnect(), which then tries to access self.canvas
- The canvas property lambda returns self.ref_artist.figure.canvas
- Since self.ref_artist.figure is None, this raises AttributeError: 'NoneType' object has no attribute 'canvas'

**Fix:** Either (1) add a None guard in disconnect() before accessing canvas, or (2) check self.ref_artist is not None in _check_still_parented before calling disconnect(). The fix applied in attempt 2 used both approaches.

This is a latent bug that only surfaces when using combinations like mplcursor + matplotlib 3.7.1, where the ref_artist can become detached from its figure.

### L2 — Fix for mplcursor AttributeError with matplotlib 3.7.1

**2026-08-29** — ## L1: Pitfall - ref_artist None without guard
Accessing ref_artist.figure.canvas without checking ref_artist is None first crashes with AttributeError: 'NoneType' object has no attribute 'canvas' in matplotlib 3.7.1.

### L3 — Fix for mplcursor AttributeError with matplotlib 3.7.1

**2026-08-29** — ## L2: Pitfall - _check_still_parented missing None guard
_check_still_parented() at lines 1552-1559 only checks self.ref_artist.figure is None but not self.ref_artist is None. When ref_artist is None, accessing self.ref_artist.figure crashes with AttributeError.

### L4 — Fix for mplcursor AttributeError with matplotlib 3.7.1

**2026-08-29** — ## L3: Pitfall - disconnect() missing None guard
disconnect() at lines 1561-1571 lacks null checks for ref_artist and ref_artist.figure. When either is None, accessing self.canvas.mpl_disconnect(cid) crashes. Also, mpl_disconnect(c1) at lines 1565 and 1571 can crash if self.canvas is None.

### L5 — Fix for mplcursor AttributeError with matplotlib 3.7.1

**2026-08-29** — ## L4: Pitfall - on_motion/on_release missing canvas guard
on_motion() and on_release() call _check_still_parented() then access self.canvas.mpl_disconnect(). If canvas is None (because ref_artist was None), this crashes. Callers must also guard self.canvas is not None.

### L6 — Fix for mplcursor AttributeError with matplotlib 3.7.1

**2026-08-29** — ## L5: Lesson - Always guard ref_artist is None first
Always add `if self.ref_artist is None: return False` as the first line of _check_still_parented(). Always guard `if self.ref_artist is not None and self.ref_artist.figure is not None:` in disconnect(). Always add `and self.canvas is not None` to on_motion/on_release conditions. These null guards prevent the AttributeError cascade that breaks mplcursor in matplotlib 3.7.1.
