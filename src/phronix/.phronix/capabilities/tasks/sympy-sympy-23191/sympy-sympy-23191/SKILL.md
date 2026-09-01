---
name: sympy-sympy-23191
description: Fix sympy vector pretty printing where unit vectors (e.g., i_C) appear in the middle of coefficient-expression sequences instead of at the end. The core issue is in _print_BasisDependent method in sympy/printing/pretty/pretty.py where formatted component strings are concatenated incorrectly.
subject: sympy vector pretty printing
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | R1: Unit vector positioning in _print_BasisDependent |
| `R2` | Rules | R2: Component iteration order matters |






## Instructions

### I1 — What problem it solves

When sympy vectors are pretty-printed, unit vectors (e.g., i_C) appear in the middle of coefficient-expression sequences rather than at the end. For example, the output `⎛2⋅sin⎜───⎟ i_C⋅cos⎝10⋅t⎠⎟` should be `⎛2⋅sin⎜───⎟⋅cos⎝10⋅t⎠⎟` - the unit vector i_C is incorrectly placed between the coefficient and the expression, instead of at the end after the full expression.

### I2 — The key idea

The _print_BasisDependent method assembles vector components by separating them via expr.separate().items(), sorting by str(k), and building formatted strings. The key insight is that the o1 list at line 1129 already correctly creates arg_str + ' ' + k._pretty_form (combining coefficient and vector form together). The bug is in the assembly logic at lines 1132-1193 which incorrectly interposes bare vector forms from the vectstrs list between coefficient and expression parts, rather than keeping o1 entries intact.

### I3 — Instructions to solve it

The fix requires restructuring the assembly logic at lines 1132-1193 in sympy/printing/pretty/pretty.py to preserve o1 entries intact. Do not interpose vectstrs (bare k._pretty_form) between the coefficient and vector form. The o1 entries at line 1129 already correctly format as arg_str + ' ' + k._pretty_form for general expressions. The assembly must keep these combined strings together rather than splitting them apart via the separate vectstrs list. Specifically, modify the loop at lines 1132-1193 to append each o1 entry directly to the result without interleaving vectstrs entries in between.

## Rules

### R1 — R1: Unit vector positioning in _print_BasisDependent

Unit vectors (those with coefficient 1 or -1, or bare basis forms) must appear at the END of the pretty-printed vector component, not between the coefficient and expression. The bug manifests when i_C appears as `⋯ i_C⋅cos⋯` instead of `⋯⋅cos⋯ i_C`. Any fix must ensure the basis vector form stays attached to the end of its component string.

### R2 — R2: Component iteration order matters

The components from expr.separate().items() are sorted by str(k) (alphabetical ordering of the basis vector string). This ordering must be preserved throughout the assembly process. Any restructuring of the assembly logic must maintain the same iteration order over sorted components, or the output will have components in wrong positions.

## References
