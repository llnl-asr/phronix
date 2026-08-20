---
name: phronix-privacy
description: Everything phronix persists is committed and published. How to redact usernames, home paths, hostnames, email addresses and job ids from anything written to the store; what must NOT be stripped; how to verify deterministically; and how to teach the redactor a leak class it does not know. Load before any commit, pull request, or promotion.
subject: redacting usernames, home paths, hostnames and job ids from shared knowledge
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Scan, then redact, then re-scan |
| `I2` | Instructions | Hunt for what the rules miss |
| `I3` | Instructions | Teach the redactor, do not patch the file |
| `I4` | Instructions | Report what you dismissed |
| `R1` | Rules | Keep the lesson, drop the provenance |
| `R2` | Rules | Never store a profile of a person |
| `R3` | Rules | Do not over-redact |
| `R4` | Rules | Verify deterministically, never by reading |
| `R5` | Rules | Promotion is publication |
| `R6` | Rules | Write examples with placeholders, not plausible names |
| `X1` | References | When the sweep runs |

## Instructions

### I1 — Scan, then redact, then re-scan

```
privacy_scan()      # what would change under redaction. Anything but "clean" blocks.
privacy_redact()    # apply it
privacy_scan()      # confirm — do not assume the redaction covered what it reported
```

### I2 — Hunt for what the rules miss

`privacy_suspects()` subtracts everything the existing rules already handle, so
what comes back is precisely the leak classes nobody has taught the redactor yet.

Several probes are deliberately noisy, because a missed leak costs far more than a
false positive. Review each one honestly: most will be a version string that looks
like a hostname or a hex hash that looks like a token. Some will not be, and those
are exactly the ones a scan alone would never find.

### I3 — Teach the redactor, do not patch the file

```
privacy_add_pattern(regex=..., replacement=..., reason=..., structure_safe=True)
```

Fixing the one file leaves the class open and the next session reintroduces it.
The rule ships to everyone who gets that layer.

Set `structure_safe=False` when the rule changes a path's component count: those
rules are skipped for `.patch` and `.diff`, where they would break `patch -pN`.

### I4 — Report what you dismissed

A dismissed suspect with a stated reason is a decision someone can revisit; an
undocumented one gets re-reviewed from scratch on every sweep.

## Rules

### R1 — Keep the lesson, drop the provenance

We learn from experience; we never record whose experience it was. "This compiler
miscompiles that construct" is the knowledge. Who ran it, on which node, under
which job id, is not.

Strip: usernames, real names, emails, account handles; absolute user paths
(`$HOME`, `$PROJECT_ROOT`, `$SCRATCH_ROOT` instead); job ids and session UUIDs
(`<job-id>`, `<uuid>`); hostnames with node numbers (`<cluster><node>`); and any
secret outright.

### R2 — Never store a profile of a person

`type: user` memories are rejected. No amount of redaction makes one safe, because
the whole document *is* the identity.

### R3 — Do not over-redact

Over-redaction makes knowledge unusable and trains people to disable the guard —
which is how the real leaks get through. Published citations, software names
carrying digits, loopback and private-range addresses, `uid=0`, and existing
placeholders are all left alone by design.

### R4 — Verify deterministically, never by reading

Judging that a file "looks fine" does not scale and does not catch the classes a
regex does. `privacy_scan()` is the check.

### R5 — Promotion is publication

`phronix contribute` refuses to proceed on findings rather than quietly redacting
them: silently rewriting text on its way out means nobody ever reviews what was in
it.

### R6 — Write examples with placeholders, not plausible names

A realistic username in an illustrative example trips the redactor and fails the
skill's own privacy check. Write `<user>` — angle-bracket placeholders are exempt.

## References

### X1 — When the sweep runs

After every self-learning write: [[phronix-self-learning#I6]]. Before promotion:
[[phronix-verification#X2]].
