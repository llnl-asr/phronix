# Lessons — matplotlib-matplotlib-25498

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Incorrect fix introduced AttributeError and TypeError in Colorbar.update_normal

**2026-08-29** — Attempted to fix Colorbar.update_normal but introduced new failures. The added call to `set_cmap` does not exist on Colorbar, causing AttributeError. Additionally, syncing the norm without handling missing `autoscale_None` on non-ScalarMappable objects leads to TypeError when `mappable` lacks an array. The fix also failed to address the core issue: `update_normal` must ensure the mappable's norm is valid and trigger a redraw without assuming methods. This broke multiple tests: test_colorbarbase, test_mappable_no_alpha, and others, resulting in 12 regressions.
