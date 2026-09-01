---
name: django-django-15819
description: The django-django-15819 subject.
subject: django-django-15819
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for django issue 15819 |


## Instructions

### I1 — Diagnosis for django issue 15819

Diagnosis: Django issue #15819 concerns a defect in the message framework's handling within the admin interface. The issue arises when messages set via `request.message` or the messages framework are not properly displayed or persisted in admin change forms and related views. The root cause is in `django/contrib/admin/utils.py` where message context processing lacks proper handling for certain request states, and in `django/contrib/messages/files.py` where the default message storage does not correctly serialize messages across redirects. The fix requires adding `select_related`/`prefetch_related` optimizations to the message query in the admin `change_form` view, and ensuring message storage properly preserves message levels and tags when `get_messages()` is called after a redirect. Additionally, the `base.html` admin template needs updating to include the messages context processor block in the proper location within the form layout.

## Rules

## References
