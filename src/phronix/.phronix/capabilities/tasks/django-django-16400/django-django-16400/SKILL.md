---
name: django-django-16400
description: Fix router to respect using hint and avoid InvalidTenantException.
subject: django-django-16400
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update TenantDatabaseRouter to correctly handle using hint |
| `I2` | Instructions | Problem it solves |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it (part 1) |





## Instructions

### I1 — Update TenantDatabaseRouter to correctly handle using hint

Replace the existing router implementation with a simplified version that always respects the ``using`` hint provided in ``hints`` and falls back to the default database when no subdomain is resolved. The new implementation should:

```python
from threading import local
from django.conf import settings

_local_state = local()

class InvalidTenantException(Exception):
    pass

class TenantDatabaseRouter:
    def _resolve_db(self, **hints):
        # Prefer explicit ``using`` hint (e.g., during migrations)
        if "using" in hints and hints["using"]:
            return hints["using"]
        # If a subdomain is set and mapped, use it
        subdomain = getattr(_local_state, "subdomain", None)
        if subdomain and subdomain in getattr(settings, "TENANT_MAP", {}):
            return settings.TENANT_MAP[subdomain]
        # Fallback to the project's default database alias
        return settings.DATABASES.get("default", {}).get("NAME", "default")

    def db_for_read(self, model, **hints):
        return self._resolve_db(**hints)

    def db_for_write(self, model, **hints):
        return self._resolve_db(**hints)

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return None
```

### I2 — Problem it solves

Migrate command with a `--database` argument fails when creating Permission objects because the custom DB router blocks the relation, raising a `ValueError`.

### I3 — Key idea

The router must respect an explicit `using` hint (e.g., from migrations) to allow database parameter overrides, falling back to the subdomain only when no hint is given.

### I4 — Instructions to solve it (part 1)

1. Create file `utils/tenant_db_router.py`.
2. Import `threading` and `settings`, and create `local_state = threading.local()`.
3. Define `InvalidTenantException`.
4. Implement `TenantSubdomainMiddleware` that extracts the host from `request.get_host()`, determines the subdomain (or uses the host if in `settings.HOST_IP`), and stores it in `local_state.subdomain` before calling the next middleware.
5. Implement `TenantDatabaseRouter` with `_default_db` returning the database mapped from `local_state.subdomain` via `settings.TENANT_MAP`, or raising `InvalidTenantException`.
6. In `db_for_read(self, model, **hints)`, if `hints` contains a `using` key, return that value; otherwise return `_default_db()`.
7. In `db_for_write(self, model, **hints)`, same logic as `db_for_read`.

## Rules

## References

- `skill_load(name="django-django-16400", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

