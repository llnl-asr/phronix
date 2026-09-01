# Lessons — django-django-16527

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Missing has_add_permission allows unauthorized save-as-new

**2026-08-29** — Without has_add_permission check, show_save_as_new button appears for users without add permission. The issue reporter's own fix in their project (adding "and has_add_permission # This line that I put!!!") confirmed this was the right approach. A missing has_add_permission check means the button is visible even though the user cannot actually add new objects via save-as-new.
