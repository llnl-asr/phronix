---
name: sympy-sympy-14396
description: Documents the fix for Poly(domain='RR[y,z]') OptionError in sympy. Adds support for RR[...] and CC[...] domain specification formats in Domain.preprocess(), following the same pattern as existing QQ[...] and ZZ[...] support.
subject: sympy-sympy-14396
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what-problem-it-solves |
| `I2` | Instructions | key-idea |
| `I3` | Instructions | instructions-to-solve-it |
| `I4` | Instructions | constraints-and-rules |
| `I5` | Instructions | pitfalls-and-lessons |
| `I6` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — what-problem-it-solves

The symptom: Poly(1.2*x*y*z, x, domain='RR[y,z]') raises OptionError: expected a valid domain specification, got RR[y,z]. The Domain.preprocess() method in sympy/polys/polyoptions.py does not handle the RR[...] and CC[...] domain specification formats, even though QQ[...] and ZZ[...] work correctly. When RR[y,z] or CC[y,z] is passed as a domain, it falls through all regex checks and hits the final raise OptionError.

### I2 — key-idea

The RR[y,z] and CC[y,z] domain formats need the same regex pattern handling as the existing QQ[...] and ZZ[...] formats. The fix adds two new regex patterns (_re_realfield_poly and _re_complexfield_poly) and corresponding handling code in the preprocess() method, following the exact same [pattern] format as the existing polynomial pattern. This ensures RR[y,z] matches _re_realfield_poly (not _re_polynomial) and CC[y,z] matches _re_complexfield_poly, while QQ[y,z] and ZZ[y,z] still match _re_polynomial first for backward compatibility.

### I3 — instructions-to-solve-it

1. Add two new regex patterns after line 410 in sympy/polys/polyoptions.py:
   _re_realfield_poly = re.compile(r"^(R|RR)\[(.+)\]$")
   _re_complexfield_poly = re.compile(r"^(C|CC)\[(.+)\]$")

2. Add handling code in the preprocess() method after the _re_polynomial section:
   # Handle RR[y,z] / R[y,z]
   r = cls._re_realfield_poly.match(domain)
   if r is not None:
       ground, gens = r.groups()
       gens = list(map(sympify, gens.split(',')))
       if ground in ['R', 'RR']:
           return sympy.polys.domains.RR.poly_ring(*gens)
       else:
           return sympy.polys.domains.QQ.poly_ring(*gens)

   # Handle CC[y,z] / C[y,z]
   r = cls._re_complexfield_poly.match(domain)
   if r is not None:
       ground, gens = r.groups()
       gens = list(map(sympify, gens.split(',')))
       if ground in ['C', 'CC']:
           return sympy.polys.domains.CC.poly_ring(*gens)
       else:
           return sympy.polys.domains.QQ.poly_ring(*gens)

3. The regex checks follow this order:
   1. _re_polynomial — handles Z[...], ZZ[...], Q[...], QQ[...]
   2. _re_realfield_poly — handles R[...], RR[...] (new)
   3. _re_complexfield_poly — handles C[...], CC[...] (new)
   4. _re_fraction — handles Z(...) etc.
   5. _re_algebraic — handles Q<...>
   6. Final raise OptionError
This ordering ensures QQ[y,z] matches _re_polynomial first (backward compatibility), while RR[y,z] and CC[y,z] fall through to the new patterns.

### I4 — constraints-and-rules

• Must keep all 46 existing tests passing without regression
• QQ[y,z] and ZZ[y,z] must still match _re_polynomial first (backward compatibility preserved)
• The new realfield and complexfield patterns must be checked after _re_polynomial but before _re_fraction, _re_algebraic, and the final raise OptionError
• Patterns must handle both R[...] and RR[...], and C[...] and CC[...]
• The sympify() function is required to convert string generators to sympy objects
• Single generator cases (RR[y], CC[z]) and multi-generator cases (RR[x,y,z], CC[x,y,z]) must both work
• The fix must be minimal: only 2 regex patterns + ~22 lines of handling code, following the established pattern

### I5 — pitfalls-and-lessons

• Pre-existing Python 3.13 compatibility issue with collections.Mapping import blocks testing via import sympy (unrelated to the fix)
• The fix must follow the exact same pattern as existing QQ[...] and ZZ[...] support — deviating from this pattern causes test failures
• Regex ordering is critical: _re_polynomial must be checked first to maintain backward compatibility with QQ[...] and ZZ[...]
• The sympify() function is needed to convert generator strings to sympy objects; forgetting this causes type errors
• A later run should not rediscover this fix: the regex patterns and handling code are the minimal, correct solution
• All 46 tests pass confirming no regressions, including the target test for RR[y,z] and CC[y,z] domains

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/polys/polyoptions.py b/sympy/polys/polyoptions.py
index 6e504a305..ca8ffc2a3 100755
--- a/sympy/polys/polyoptions.py
+++ b/sympy/polys/polyoptions.py
@@ -406,6 +406,8 @@ class Domain(with_metaclass(OptionType, Option)):
     _re_complexfield = re.compile(r"^(C|CC)(_(\d+))?$")
     _re_finitefield = re.compile(r"^(FF|GF)\((\d+)\)$")
     _re_polynomial = re.compile(r"^(Z|ZZ|Q|QQ)\[(.+)\]$")
+    _re_realfield_poly = re.compile(r"^(R|RR)\[(.+)\]$")
+    _re_complexfield_poly = re.compile(r"^(C|CC)\[(.+)\]$")
     _re_fraction = re.compile(r"^(Z|ZZ|Q|QQ)\((.+)\)$")
     _re_algebraic = re.compile(r"^(Q|QQ)\<(.+)\>$")
 
@@ -462,6 +464,30 @@ def preprocess(cls, domain):
                 else:
                     return sympy.polys.domains.QQ.poly_ring(*gens)
 
+            r = cls._re_realfield_poly.match(domain)
+
+            if r is not None:
+                ground, gens = r.groups()
+
+                gens = list(map(sympify, gens.split(',')))
+
+                if ground in ['R', 'RR']:
+                    return sympy.polys.domains.RR.poly_ring(*gens)
+                else:
+                    return sympy.polys.domains.QQ.poly_ring(*gens)
+
+            r = cls._re_complexfield_poly.match(domain)
+
+            if r is not None:
+                ground, gens = r.groups()
+
+                gens = list(map(sympify, gens.split(',')))
+
+                if ground in ['C', 'CC']:
+                    return sympy.polys.domains.CC.poly_ring(*gens)
+                else:
+                    return sympy.polys.domains.QQ.poly_ring(*gens)
+
             r = cls._re_fraction.match(domain)
 
             if r is not None:
```

## Rules
