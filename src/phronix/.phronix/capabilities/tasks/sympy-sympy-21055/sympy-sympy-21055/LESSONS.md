# Lessons — sympy-sympy-21055

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Wrong import module for arg function

Do not import arg from sympy.functions.elementary.trigonometric - it is in sympy.functions.elementary.complexes. Using the wrong import path will cause an ImportError when the handler is called. Always verify the correct module by checking where the arg class is defined in the SymPy codebase.

### P2 — Handler key must match class name exactly

Do not use 'Arg' (uppercase) as the handler key in handlers_dict. The refine function uses expr.__class__.__name__ to look up the handler, and for the arg class this returns 'arg' (lowercase). Using the wrong case will mean the handler is never found and the fix will not work.

### P3 — Not handling already-simplified arg

Do not forget to check expr.is_Atom before accessing expr.args[0]. When arg has already been simplified to a number (e.g., arg(negative_number) = pi), it becomes an Atom with no .args attribute, causing an IndexError. Always guard with `if not expr.is_Atom:` first.

## Lessons
