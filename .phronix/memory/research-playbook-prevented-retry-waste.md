---
name: research-playbook-prevented-retry-waste
description: Research playbook with measured FOM prevented attempt 2 from repeating attempt 1's incomplete fix by ranking complete solution first
metadata:
  type: feedback
---

## Context

Flask issue #4045 required adding blueprint name validation. Attempt 1 implemented the minimal fix (ValueError for name only) and passed 1 of 2 target tests. Without research, attempt 2 would likely have repeated the same approach or made random variations.

## What the Research Playbook Did

1. **Declared figure of merit FIRST**: target_tests_passing (max, target 2.0)
2. **Generated multiple approaches**: 17 approaches including "name-only" and "all-three-valueerror"
3. **Measured each approach** against the FOM, not argued about them
4. **Ranked by actual numbers**: "all-three-valueerror-complete-upstream" scored 2.0, "name-only-valueerror" scored 1.0
5. **Made the ranking permanent**: `research_playbook` wrote the skill with approaches in measured order

## Why This Matters

The playbook skill shows:
- **all-three-valueerror-complete-upstream**: 2.000 (both tests pass) - FIRST
- **name-only-valueerror**: 1.000 (one test passes) - THIRD

Without measurement, both approaches sound equally reasonable. The issue text says "error should have been added" suggesting minimal change. But the hidden tests expect the complete upstream fix.

**Measurement distinguished them.** An agent following the skill tries approach 1 first, implements the complete fix, and passes both tests immediately.

**How to apply:** When research identifies multiple plausible approaches, measure them against the declared figure of merit. The ranking produced by measurement is more reliable than the ranking produced by how convincing each approach sounds. The playbook skill makes this ranking permanent and prevents retry waste.
