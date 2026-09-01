# Lessons — django-django-11620

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfalls

- Raising `ValueError` unconditionally prevents the converter from ever matching any value and caused a regression in `test_template_not_found_error`.
- The original implementation never saw an `Http404` because `StringConverter.to_python` does not raise it; without performing a lookup that may raise `Http404`, the catch block is never exercised.
- Adding the import `from django.http import Http404` without using it leads to dead code and does not solve the problem.
- Modifying only the `to_python` method without ensuring the lookup step can raise `Http404` results in the resolver still propagating the exception, leading to a 500 error in DEBUG mode.

## Lessons
