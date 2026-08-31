---
name: sympy-sympy-22840-cse-matrixsymbol
description: Skill documenting lessons learned from three attempts to fix cse() function's strange behavior for MatrixSymbol indexing in sympy. Task involved common subexpression elimination with MatrixSymbol objects, with test_command_option_inline_function_call as the recurring blocker across all attempts.
subject: sympy-cse-matrixsymbol
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints and rules |






## Instructions

### I1 — What problem it solves

The cse() function in sympy has strange behavior when handling MatrixSymbol indexing. When cse() is applied to expressions containing MatrixSymbol objects, the common subexpression elimination does not properly account for how MatrixSymbol indices are structured, leading to incorrect substitutions and unreliable results. The specific issue manifests when using test_command_option_inline_function_call which consistently fails across all three attempts, indicating a fundamental problem with how cse() processes MatrixSymbol-indexed expressions during substitution.

### I2 — The key idea

The core insight is that cse() must treat MatrixSymbol indexing as atomic units during common subexpression elimination. When building replacements, the function should not attempt to extract sub-expressions from within MatrixSymbol index references, as these indices (e.g., [0,1], [i,j]) are part of the MatrixSymbol's identity and cannot be safely isolated without breaking the matrix expression structure. The fix ensures that MatrixSymbol-involved expressions are either kept whole or substituted with properly scoped replacements that preserve the matrix indexing semantics.

### I3 — Instructions to solve it

1. When cse() encounters a MatrixSymbol in the expression tree, check if any sub-expressions within the MatrixSymbol's indexing pattern are candidates for common subexpression elimination.
2. If MatrixSymbol indexing is detected, preserve the MatrixSymbol as a whole unit - do not attempt to extract and replace individual indexed elements.
3. For expressions involving MatrixSymbol and regular symbols, apply cse() to the non-MatrixSymbol portions first, then handle the MatrixSymbol-containing portion separately.
4. The test_command_option_inline_function_call test must pass after the fix - this is the recurring blocker that validates the solution.
5. Ensure regressions test_command_option_globals and test_stdin_read_globals also pass.
6. Use explicit globals for exec() calls: exec(options['command'], {}) and exec(sys.stdin.read, {}).
7. After making exec() changes, verify all three test families pass: test_command_option_inline_function_call, test_command_option_globals, test_stdin_read_globals.

### I4 — Pitfalls and lessons

Attempt 1 failure: Agent produced no diff, harness reported "agent produced no patch". Lesson: Insufficient codebase understanding before starting.

Attempt 2 failure: exec() globals fix (exec(options['command'], {})) applied but test_command_option_inline_function_call still fails. Lesson: exec() fix is necessary but insufficient - MatrixSymbol indexing issue requires separate handling.

Attempt 3 failure: Agent produced no diff again. Lesson: Task complexity exceeds initial assessment after multiple failed attempts.

Critical: test_command_option_inline_function_call fails across ALL three attempts, even after exec() globals fix. This is the primary blocker that must be resolved.

Regression tests that must also pass: test_command_option_globals and test_stdin_read_globals.

Key finding from code analysis: cse_main.py lines 674-676 handle MatrixExpr with MatrixSymbol substitution; tree_cse() performs raw CSE on expression tree. MatrixSymbol indexing (e.g., [0,1], [i,j]) must be preserved as atomic units.

## Rules

### R1 — Constraints and rules

1. MatrixSymbol objects must be treated as atomic units during cse() - no extraction of indexed sub-expressions.
2. The exec() global fix (using exec(options['command'], {}) pattern) must be applied consistently across all command execution paths.
3. Do not break existing cse() functionality for non-MatrixSymbol expressions - the fix should only affect MatrixSymbol handling.
4. All regression tests must pass: test_command_option_inline_function_call, test_command_option_globals, test_stdin_read_globals.
5. Any replacement substitutions must preserve the original MatrixSymbol's shape and indexing structure.
6. Do not modify the core cse() algorithm for general cases - add MatrixSymbol-specific handling as a special case.
7. If a MatrixSymbol has symbolic dimensions (e.g., n x n where n is a symbol), treat it the same as fixed-size MatrixSymbols - keep whole.

## References
