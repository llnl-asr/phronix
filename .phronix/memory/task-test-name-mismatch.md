---
name: task-test-name-mismatch
description: Task issue numbers may differ from target test issue numbers - verify both test names when numbers don't match
metadata:
  type: project
---

**Pattern**: Task names and target test names don't always align. The task directory is named `sympy__sympy-24066` (issue 24066) but the target test is `test_issue_24062` (issue 24062). These are different issue numbers.

**Why this happens**: The test may have been written for a related but different issue, or the task naming/test selection has an error. The task may be fixing issue 24066 but the validation test comes from issue 24062 if they're related.

**Directive**: When the issue number in the task name differs from the target test name:
1. Search for both: `test_issue_24066` AND `test_issue_24062`
2. Check if either test exists: `grep -r "def test_issue_2406[26]" sympy/`
3. Read the issue description carefully - it may reference multiple related issue numbers
4. If target test doesn't exist, check if you need to create it from the reproducer in issue.md

Never assume the test exists just because you were told to pass it.
