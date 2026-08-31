---
name: pytest-dev-pytest-7373
description: The pytest-dev-pytest-7373 subject.
subject: pytest-dev-pytest-7373
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what-problem-it-solves |
| `I2` | Instructions | the-key-idea |
| `I3` | Instructions | instructions-to-solve-it |
| `I4` | Instructions | pitfalls-and-lessons-part1 |
| `I5` | Instructions | pitfalls-and-lessons-part2 |
| `I6` | Instructions | pitfalls-and-lessons-part3 |
| `I7` | Instructions | pitfalls-and-lessons-part4 |
| `R1` | Rules | R1 Constraint |
| `R2` | Rules | constraints-and-rules-part1 |
| `R3` | Rules | constraints-and-rules-part2 |

## Instructions

### I1 — what-problem-it-solves

When a later run starts and sees `@pytest.mark.skipif("cond")` or `@pytest.mark.xfail("cond")` where the condition string references a variable that may have different values in different test modules, this skill is about whether the caching of condition evaluation is causing incorrect results. The symptom: two test files with the same marker expression but different global variable values both get the same cached result, causing one (or both) to be incorrectly skipped or marked xfail. The specific pattern: `skip = True` in module A makes `test_A` skip; `skip = False` in module B makes `test_B` should NOT skip, but both get skipped because the cache only keyed on the expression string "skip", not the globals dict.

### I2 — the-key-idea

The one insight: the caching key for skipif/xfail condition evaluation was only the expression string, but evaluation depends on the item's runtime globals dict — making the cache fundamentally broken across test modules with different variable values.

### I3 — instructions-to-solve-it

1. Open src/_pytest/mark/evaluate.py
2. Remove the `evalcache_key = StoreKey[Dict[str, Any]]()` line (was line 18, after the imports)
3. Remove the entire `cached_eval(config: Config, expr: str, d: Dict[str, object]) -> Any` function (was lines 21-31, including its blank line after)
4. In the `MarkEvaluator._istrue` method, replace `result = cached_eval(self.item.config, expr, d)` (was line 101) with:
   ```
   import _pytest._code
   exprcode = _pytest._code.compile(expr, mode="eval")
   result = eval(exprcode, d)
   ```
5. Verify the file syntax is valid (import py_compile; py_compile.compile("src/_pytest/mark/evaluate.py", doraise=True))
6. Run the test suite to confirm 1 target test newly passes and all 81 regression tests keep passing.

### I4 — pitfalls-and-lessons-part1

Pitfall P1: Attempting to make the cache "context-aware" by including the globals dict in the cache key. This was unnecessarily complex and still had the problem of potentially infinite key space. The simpler and correct approach was to remove the cache entirely.

Pitfall P2: Trying to patch the cache to clear it per-item rather than removing it. The root problem was conceptual — the cache key was fundamentally wrong for the use case, not just a missing clear mechanism.

### I5 — pitfalls-and-lessons-part2

Pitfall P3: Not realizing the evaluation depends on item globals until running tests across multiple test files with different variable values. The bug only manifests when the same expression string is evaluated in different global contexts.

Lesson L1: When caching depends on runtime state that varies per call (here, the item's globals), the cache is likely incorrect. If the value can differ between calls with the same key, the cache should not be used or must include all varying keys.

### I6 — pitfalls-and-lessons-part3

Lesson L2: Removing an incorrect cache is often simpler and correcter than trying to make it smarter. The 359s across 62 steps of investigation confirmed that inlining the eval was the direct fix.

Lesson L3: The fix eliminates 9 lines of cache management code (the evalcache_key definition and cached_eval function) and replaces 1 line (cached_eval call) with 3 lines of direct eval/compile/eval — a net simplification.

### I7 — pitfalls-and-lessons-part4

Lesson L4: Always test the caching behavior across multiple test files with the same marker expression but different global variable values — this is where the bug surfaces.

## Rules

### R1 — R1 Constraint

All existing regression tests (81) must continue to pass after the change.

### R2 — constraints-and-rules-part1

What must stay true while solving it:
- The _istrue method must still evaluate the expression using eval() with the item's globals
- The MarkEvaluator class structure and __init__ method must remain unchanged
- No other files should be modified; only src/_pytest/mark/evaluate.py what the fix changes
- The evalcache_key and cached_eval were the only cache mechanisms; removing them is the fix
- The _getglobals method produces the dict of globals for evaluation (os, sys, platform, config, and module's __globals__)

What must not be touched:
- Do not modify test files (per task instructions)
- Do not change the MarkEvaluator.__init__ method signature
- Do not add new caching mechanisms that still key only on the expression string

### R3 — constraints-and-rules-part2

What must not be touched:
- Do not modify test files (per task instructions)
- Do not change the MarkEvaluator.__init__ method signature
- Do not add new caching mechanisms that still key only on the expression string
- Do not remove the import _pytest._code that is now needed inline

The invariant the obvious fix breaks: the original cache assumed the expression string alone was sufficient to determine the result, but this was incorrect because the same expression can evaluate differently with different globals. The fix must ensure each evaluation uses the current item's globals at call time.

## References
