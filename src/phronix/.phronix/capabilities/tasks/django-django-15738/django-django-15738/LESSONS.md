# Lessons — django-django-15738

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Migration fails when changing FK to M2M with unique_together present

ValueError: Found wrong number (0) of constraints for app_authors(project_data_set, state, start_date) when converting ForeignKey to ManyToMany with existing unique_together constraint

## Lessons
