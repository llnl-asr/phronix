# Lessons — django-django-13658

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Insufficient fix: moving callback outside if emit:

1. Moving the callback emission outside if emit: block alone is insufficient — it causes the callback to fire on the originating axis but the recursion issue persists because sibling propagation with emit=False still triggers the same code path that leads to infinite recursion.

### P2 — emit=False propagation is necessary

2. The emit=False propagation from CommandParser to sibling axes is necessary; removing it would cause even more recursion, as the issue reporter noted: "Setting emit=True seems to introduce a recursion issue."

### P3 — Recursion loop in shared axis propagation

3. The core problem is that when set_xlim propagates to shared axes, it triggers _set_lim again on those axes, which then propagates further, creating a recursion loop. A more fundamental change to how shared axis limit propagation works is needed.

### P4 — Guard/flag needed beyond callback move

4. A guard/flag to prevent re-processing of already-processed axes, or changing how shared axis propagation is triggered (only propagate when the change originates directly, not when it's part of the propagation chain), may be needed beyond just moving the callback outside if emit:.

## Lessons

### L1 — Callback fix alone insufficient

**2026-08-29** — 1. The callback fix alone is insufficient - Moving the callback outside if emit: ensures it fires on the originating axis, but doesn't address the recursion problem that causes 47+ tests to fail.

### L2 — RecursionError in shared axis set_xlim

**2026-08-29** — 2. The test output shows RecursionError: maximum recursion depth exceeded when trying to set xlim on shared axes - the core issue is recursive propagation through shared axis callbacks.

### L3 — emit=False is necessary to limit recursion

**2026-08-29** — 3. emit=False propagation is necessary for preventing even worse recursion - removing it causes tests to fail more broadly, as the issue reporter confirmed: "Setting emit=True seems to introduce a recursion issue."
