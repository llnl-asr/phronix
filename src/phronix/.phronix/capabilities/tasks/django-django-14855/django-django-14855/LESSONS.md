# Lessons — django-django-14855

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfalls for readonly foreignkey URL fix

- Without current_app, Django resolves URLs against default admin site (/admin/...) not custom site (/custom-admin/...)
- Adding current_app alone is sufficient; no other function body changes needed
- Fix follows established Django admin pattern (widgets.py, sites.py, options.py use current_app)
- All 325 regression tests must pass — this is the key invariant to preserve
- One target test (test_readonly_foreignkey_links_custom_admin_site) specifically validates custom admin site URL generation

## Lessons

### L1 — Lesson for readonly foreignkey URL fix

**2026-08-29** — When a model containing a ForeignKey field is viewed/edited in a custom Admin Site with the field in readonly_fields, the URL generated for the "View on site" link was /admin/... instead of /custom-admin/... The root cause was the get_admin_url method calling reverse() without the current_app parameter. The fix — adding current_app=self.model_admin.admin_site.name — is minimal, follows established Django admin patterns, and all 325 regression tests continue to pass.
