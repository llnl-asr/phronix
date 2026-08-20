# Lessons — based-column-domain

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — add-subdomain-column-only does not work

**Tried**: add-subdomain-column-only

**Hypothesis**: Adding a "Subdomain" column showing only rule.subdomain value (without SERVER_NAME) is simpler and handles missing SERVER_NAME gracefully. Falsified if: users need full domain reconstruction, or column is confusing without context.

**Refuted by**: test 0/1, validate 0/1. Do not re-propose this without new evidence.

### P2 — domain-column-always-display as first column fails tests

**Tried:** domain-column-always-display with "Domain" as first column

**Implementation:** Added Domain as first column header, computed domain strings (subdomain.SERVER_NAME with fallbacks to '-'), updated table formatting to accommodate 4 columns.

**Result:** FAILED. 0/2 target tests pass, 2/54 regressions introduced.
- test_subdomain expects "Subdomain" header text, not "Domain"
- test_host expects "Host" header text, not "Domain"  
- test_simple and test_sort broke because expect_order() checks line prefixes against endpoint names, but Domain column now appears first

**Conclusion:** Putting Domain/Subdomain/Host as the first column breaks test compatibility. Tests expect Endpoint to remain the first column. The header name "Domain" doesn't satisfy tests that look for "Subdomain" or "Host" specifically.

## Lessons
