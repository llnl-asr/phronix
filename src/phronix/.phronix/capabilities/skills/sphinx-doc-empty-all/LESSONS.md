# Lessons — sphinx-doc-empty-all

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Empty __all__ handling causing SyntaxError

Adding code to treat empty __all__ as ignored introduced a SyntaxError because the added lines were not correctly indented within the try block, causing Python to see an unexpected indented block. The fix must ensure proper indentation and placement within the existing code structure.

## Lessons
