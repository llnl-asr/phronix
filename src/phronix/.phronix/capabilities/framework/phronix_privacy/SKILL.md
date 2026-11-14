---
name: phronix_privacy
description: Redact usernames, home and user paths, hostnames with node numbers, emails, job ids and session UUIDs from anything written to the shared store, without over-redacting citations or software versions; verify deterministically with privacy_scan, hunt unencoded leak classes with privacy_suspects, and teach the redactor with privacy_add_pattern. Load before any commit, pull request, promotion or 'phronix contribute', after every self-learning write, and when a scan is not 'clean'.
---
Cross-references: [[phronix_self_learning]], [[phronix_verification]], [[phronix_memory]], [[lessons]], [[knowledge]]

# Privacy: keep shared knowledge free of identifying detail

Converted from the dftracer-agents skill `phronix-privacy` (subject: redacting usernames, home paths, hostnames and job ids from shared knowledge). Source description: Everything phronix persists is committed and published. How to redact usernames, home paths, hostnames, email addresses and job ids from anything written to the store; what must NOT be stripped; how to verify deterministically; and how to teach the redactor a leak class it does not know. Load before any commit, pull request, or promotion.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

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

### Using the tools (capability)

- Render the procedure with `phronix_privacy_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `target`, `scan_before`, `redacted`, `scan_after`, `suspects_run`, `dismissed`, `patterns_added`, `patched_files_by_hand`, `text`) to `phronix_privacy_check`; a step is done only when the check passes.

## References

### X1 — When the sweep runs

After every self-learning write: [[phronix-self-learning#I6]]. Before promotion:
[[phronix-verification#X2]].

## Constraints

- Anything but a clean privacy_scan blocks a commit, PR or promotion (I1, R5).
- Never quietly redact on the way out: promotion refuses on findings so someone reviews them (R5).
- Never store a profile of a person (R2).
- Do not over-redact citations, software versions, loopback/private addresses, uid=0 or placeholders (R3).

## Corner cases

- privacy_suspects probes are deliberately noisy: most hits are a version string that looks like a hostname or a hex hash that looks like a token (I2).
- A rule that changes a path's component count must be structure_safe=False: it is skipped for .patch and .diff where it would break patch -pN (I3).
- A realistic username in a documentation example fails the skill's own privacy check: use <user> (R6, P1).
- P1 (source pitfall) — A realistic username in a documentation example: The most common way a skill fails its own privacy check. Use `<user>`, `<host>`, `<job-id>` — placeholders are exempt from redaction by design.
- P2 (source pitfall) — Fixing the file instead of the rule: The class stays open and the next session reintroduces it, usually somewhere less visible. `privacy_add_pattern` is the fix.
- P3 (source pitfall) — Skipping `privacy_suspects` because `privacy_scan` was clean: A clean scan means the *known* rules found nothing. It says nothing about the leak classes nobody has encoded yet, and those are the ones that matter.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_privacy_plan`, validator `phronix_privacy_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `target_named` failed: name what was swept (the files or the run's additions)
- `scan_before_known` failed: record the first privacy_scan result: clean or findings (I1)
- `redacted_on_findings` failed: run privacy_redact() on findings (I1)
- `rescanned_clean` failed: re-run privacy_scan() after redacting and repeat until clean; never assume the redaction covered it (I1, R4)
- `suspects_run` failed: run privacy_suspects() even on a clean scan: a clean scan says nothing about unencoded leak classes (I2, P3)
- `dismissals_reasoned` failed: give every dismissed suspect a reason (I4)
- `class_not_file` failed: fix the rule, not the file: privacy_add_pattern for the class (I3, P2)
- `no_user_paths` failed: replace absolute user paths with $HOME / $PROJECT_ROOT / $SCRATCH_ROOT (R1)
- `no_emails` failed: remove email addresses (R1)
- `no_uuids` failed: replace session UUIDs with <uuid> (R1)
- `no_job_ids` failed: replace job ids with <job-id> (R1)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- The same leak class reappears after a fix: the file was patched instead of the rule; add a privacy_add_pattern rule (P2).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A leak class the redactor did not know becomes a privacy_add_pattern rule shipped with its layer, never a one-file fix (I3).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- privacy_scan -> privacy_redact -> privacy_scan until clean, then privacy_suspects with every dismissal reasoned (phronix-privacy I1-I4, 2026-09-15).
- `phronix_privacy_plan` -> follow the checklist -> `phronix_privacy_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
