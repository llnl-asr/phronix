# Lessons — django-django-12113

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfalls - what did not work

Pitfalls (from what did not work across attempts):
1. Using persistent SQLite databases without separate NAME configuration: concurrent test processes access the same database file, causing database is locked errors
2. Running tests with --keepdb --parallel 1 without proper database isolation: same locking contention occurs
3. Assuming the default test database name is sufficient for multiple database aliases - this causes cross-process locking conflicts
4. Not including the connection alias in test_db_signature for file-based databases - different aliases share the same underlying test database file

Why these failed:
- Without unique TEST NAMEs, Django uses the default test database name for all connections
- SQLite file-level locking means only one process can write at a time
- When multiple test processes use the same database file, they block each other
- The test_db_signature method didn't include the connection alias, so all file-based test databases had the same signature

## Lessons

### L1 — Lessons - what worked

**2026-08-29** — Lessons (from what worked across attempts):
1. Adding explicit TEST options with unique NAME for each database connection prevents the database lock contention by ensuring each test run uses its own database file
2. The fix resolves the sqlite3.OperationalError: database is locked error in admin_views.test_multidb.MultiDatabaseTests.setUpTestData
3. Having separate TEST database NAMEs ensures each database connection uses a dedicated test database file, eliminating cross-process locking conflicts
4. The fix is minimal and targeted: only adds TEST configuration to existing DATABASES entries

Key insight: Timing disparity between approaches (12 min vs 2 min to same result) is a meaningful datum about approach efficiency that must be recorded for future reference.
