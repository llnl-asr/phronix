# Lessons — flask-cli-routes

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Domain column addition broke existing route tests

**2026-08-21** — The patch added a new `Domain` column to the `flask routes` CLI output and reordered columns to (Domain, Endpoint, Methods, Rule). The test suite expected the original ordering (Endpoint, Methods, Rule) and looked for header strings `Host` and `Subdomain`. This caused the target tests `test_host` and `test_subdomain` and regression tests `test_simple` and `test_sort` to fail. Future changes that modify CLI output must also update test expectations or retain backward‑compatible output.

### L2 — Domain column missing

**2026-08-21** — Domain column missing in routes output for subdomains and dotted blueprints

### L3 — Domain column missing in `flask routes` output for subdomains/dots

**2026-08-21** — Domain column missing in `flask routes` output for subdomains/dots. The CLI failed to show the Domain column when routes had a dot in the blueprint name, causing incorrect routing info.

**Why:** The code that builds the Domain column assumes a single subdomain string; a dot triggers split logic that drops the column.

**Fix needed:** Adjust `flask/cli.py` to handle dotted subdomains correctly, ensuring the Domain column is populated.

### L4 — Domain column missing for subdomains

**2026-08-21** — Domain column missing in flask routes output for routes with subdomains or dotted blueprints. The implementation of get_rule_domain returned empty string when subdomain was present but SERVER_NAME was not set, causing the Domain column to be omitted. Ensure SERVER_NAME is configured or fallback to subdomain when computing domain.

### L5 — Domain column works with SERVER_NAME

**2026-08-21** — Domain column correctly appears in flask routes output when SERVER_NAME is configured; the get_rule_domain helper computes the domain using subdomain and SERVER_NAME and adds the column.

### L6 — Preserve original column headers when adding Domain column

**2026-08-21** — The CLI `flask routes` command originally prints columns with headers "Endpoint", "Methods", "Rule". Tests `TestRoutes.test_host` and `TestRoutes.test_subdomain` assert that the words "Host" and "Subdomain" appear in the output (depending on host_matching or subdomain_matching mode). The previous attempt added a generic "Domain" column and renamed the existing header, which removed those expected words and caused the tests to fail even though the domain data was displayed. Solution: keep the original headers unchanged and append a separate Domain column (with its own header) only when needed, ensuring the required "Host"/"Subdomain" strings remain in the output.
