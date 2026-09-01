---
name: sympy-sympy-11400
description: The sympy-sympy-11400 subject.
subject: sympy-sympy-11400
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules - file scope |
| `R2` | Rules | Constraints and rules - mapping format |
| `R3` | Rules | Constraints and rules - separate test issue |







## Instructions

### I1 — What problem it solves

When a later run calls ccode(sinc(x)), the user recognizes this as the sympy__sympy-11400 task because the output shows ccode(sinc(x)) returning '// Not supported in C\n// sinc\nsinc(x)' instead of proper C code. The key symptom is that 'sinc' is not in the known_functions dictionary in sympy/printing/ccode.py, causing CodePrinter._print_Function() to fall back to _print_not_supported().

### I2 — The key idea

The key insight is that the sinc function (sinc(x) = sin(x)/x for x≠0, sinc(0) = 1) is not in the known_functions mapping dictionary in sympy/printing/ccode.py. When ccode() encounters a Function with func name 'sinc', it has no mapping and falls back to _print_not_supported(). The fix requires adding a mapping so the code printer can output C code for sinc. The standard C representation maps sinc to "sin(x)/x" since C99/C11 has no standard sinc function, though some BSD/POSIX implementations provide it.

### I3 — Instructions to solve it

1. Open sympy/printing/ccode.py and locate the known_functions dictionary (around line 25-50).
2. Add the entry `"sinc": "sin(x)/x"` to the dictionary, after the "erf" entry (which is at line 38-39 based on the diff shown in the attempt notes).
3. The complete entry should read: `"sinc": "sin(x)/x",` alongside other mappings like `"exp": "exp"`, `"log": "log"`, `"erf": "erf"`.
4. Verify the change by checking that the dictionary syntax is correct (the file was verified to parse correctly after the change).
5. The fix follows the existing pattern: other trigonometric and special functions are mapped by name to their C equivalents. sinc maps to "sin(x)/x" because C99/C11 has no standard sinc function, but this is the commonly used approach.

## Rules

### R1 — Constraints and rules - file scope

Only sympy/printing/ccode.py may be modified; do not change test files or other printer modules.

### R2 — Constraints and rules - mapping format

The mapping value must be the string "sin(x)/x" — do not use a bare "sinc" or a different expression format.

### R3 — Constraints and rules - separate test issue

The test_ccode_Relational failure (Eq(x,y) → 'Eq(x, y)' vs 'x == y') is a separate, pre-existing issue unrelated to the sinc mapping; do not attempt to fix it as part of this skill.

## References

- `skill_load(name="sympy-sympy-11400", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

