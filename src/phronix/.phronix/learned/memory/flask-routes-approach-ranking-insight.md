---
name: flask-routes-approach-ranking-insight
description: Top-ranked research approach may not satisfy hidden test constraints without explicit constraint checking
metadata:
  type: lesson
---

## Symptom
Research playbook for Flask routes subdomain display ranks "add-domain-column-full" highest (score 1.0), but attempt 1 using this approach failed with 0/2 target tests and 2 regressions.

## Root Cause
The corpus used for ranking did not capture the hidden test constraints:
1. Tests require specific header names ("Subdomain" or "Host", not "Domain")
2. Tests require Endpoint to remain first column (position 0)
3. These constraints were only discoverable from the hidden test failure output

The top-ranked approach satisfied the feature request (show domain info) but violated test expectations (wrong header name, wrong column position).

## Fix
**When implementing from a research playbook:**

1. Read constraints FIRST (skills like flask-routes-cli with rules)
2. Check which approaches explicitly address those constraints
3. Corpus rankings show relative merit but don't guarantee compatibility
4. Lower-ranked approaches that explicitly handle constraints (X12-X14: conditional columns with correct headers) may work better than high-scoring approaches that don't

**Why:** Research corpus is synthetic and authored within the same session. It optimizes for the corpus, not for real test requirements. Hidden tests may check things the corpus never tested.

**How to apply:** 
- Load relevant constraint skills (e.g., flask-routes-cli) before choosing approach
- Prioritize approaches that explicitly mention addressing the constraints
- Treat "validated" status as "passed author's tests", not "will pass hidden tests"
- Use rankings as a starting order, but filter by constraint satisfaction first
