# Lessons — django-django-13551

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Using getattr with empty-string default does not handle None values

Using `getattr(user, email_field_name, '')` to retrieve an email field and provide a default does not prevent TypeError during string concatenation. The getattr() builtin only provides a default when the attribute is *missing*, not when it is *None*. Even with `getattr(user, email_field_name, '')`, if the attribute exists but its value is None, concatenating it into a string will raise `TypeError: must be str, not NoneType`. Instead, retrieve the value with `getattr(user, email_field_name, None)` and explicitly convert None to empty string with `(email or '')` before concatenation. This handles both missing attributes and explicit None values.

## Lessons
