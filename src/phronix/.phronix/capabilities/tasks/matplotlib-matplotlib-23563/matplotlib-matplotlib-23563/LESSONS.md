# Lessons — matplotlib-matplotlib-23563

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfall: Guarding _verts3d alone insufficient

**2026-08-29** — Adding a guard for missing `_verts3d` fixed the AttributeError but did not address the broadcasting `ValueError` caused by Nx1 input shapes. Without handling the shape, the test `test_draw_single_lines_from_Nx1` still fails. Future attempts must consider both issues together.
