# Lessons — pytest-dev-pytest-5692

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Hostname and timestamp not set in JUnit XML

**2026-08-29** — Adding hostname and timestamp via config._xml.add_global_property in pytest_configure does not populate JUnit XML properties; they remain None, likely because properties must be added earlier or via different API.

### L2 — L1

**2026-08-29** — Hostname and timestamp not set in JUnit XML via config._xml.add_global_property; tests `test_hostname_in_xml`, `test_timestamp_in_xml` failed because properties were None.
