# Lessons — phronix-self-research

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Assigned approach names a different topic's subject matter

Several tune/measurement attempts were handed an approach (e.g. "normpath-before-ignore-paths-match", "expanduser-as-fix", "per_file_ignore_filter_in_else_branch" — all pylint ignore-paths fixes) against a topic whose actual bug has no such surface at all (sympy__sympy-24066's Dimension/DimensionSystem collapse bug, sympy__sympy-21847's itermonomials degree filter). Each repeated 2x before being caught. This is a task-config/assignment mismatch, not a wrong-location-within-topic problem (that's [[phronix-self-research#R5]]): tuning a mismatched approach can never succeed because it targets the wrong subject entirely.

Fix: before tuning or measuring an assigned approach, check that its name/description plausibly touches the topic's actual code path (grep the file/symbol it claims to change against the topic's real issue). If it doesn't, record the mismatch immediately as a failed observation and stop iterating on it — do not keep re-tuning variants of an approach that was never applicable.

## Lessons

### L1 — Further confirmed instances of P1 (mismatched approach/topic)

**2026-08-21** — [[phronix-self-research#P1]] recurred again this cycle with two more variants, confirming it as a systemic assignment bug rather than a one-off: approach "root-vs-file-check-inconsistency" (a pylint ignore-paths concept) was assigned to topic sympy__sympy-21847 (itermonomials degree-filter bug), and "per_file_ignore_filter_in_else_branch" was assigned to sympy__sympy-24066 (Dimension collapse bug) in addition to sympy__sympy-21847. Same fix applies: check the approach's claimed file/symbol against the topic's real issue before tuning, and stop after the first mismatch rather than re-deriving it per task.

### L2 — Further confirmed instances of P1 (mismatched approach/topic)

**2026-08-21** — **2026-08-21 (same-day update)** — [[phronix-self-research#P1]] recurred again this reconcile pass, widening the pattern beyond ignore-paths-vs-sympy mismatches: (1) "root-vs-file-check-inconsistency" was assigned to pylint-dev__pylint-5859 (a notes-regex/fixme bug), not just to sympy-21847 as noted in the prior L1 entry — so the same approach name has now been misassigned to three unrelated topics. (2) ignore-paths-family approaches ("expanduser-as-fix", "normpath-before-ignore-paths-match") were also assigned to pylint-5859, which has no ignore-paths surface at all — pylint-5859's actual bug is the fixme/notes \b word-boundary regex; ignore-paths is pylint-7080's territory. (3) A measurement stage separately confirmed "topic pylint-5859 test corpus is notes-regex only, not ignore-paths" — i.e. even the test corpus assigned doesn't match the topic. This confirms the mismatch is not confined to one approach name or one wrong-topic pair; it recurs whenever ignore-paths-flavored approaches/corpora get cross-assigned to any topic that isn't pylint-7080. Same fix as P1 applies unchanged: verify an approach's claimed file/symbol (and a corpus's claimed subject) against the topic's real issue before tuning/measuring, and record+stop at the first mismatch.

### L3 — Further confirmed instances of P1 (mismatched approach/topic/corpus)

**2026-08-21** — **2026-08-21** — [[phronix-self-research#P1]] recurred again this cycle, widening the pattern to flask topics and to corpus-level (not just approach-level) contamination: (1) approaches "fix-max-to-sum-in-commutative-filter" and "same-sum-fix-for-noncommutative-branch" (sympy itermonomials fixes) and one referencing sympy monomials_list_non_comm were assigned to pallets__flask-4045 and pallets__flask-5063 (Flask blueprint dot-name / routes-CLI-domain topics — no sympy code at all). (2) approach "conditional-word-boundary-in-notes-regex" was assigned to pylint-dev__pylint-7080, whose actual code has no notes-regex \b surface (that's pylint-5859's territory, per L2). (3) topic sympy__sympy-21847's own corpus/pipeline data came back containing unrelated dimensions (tag_composition, notes_rgx_option, position_in_comment) and pylint fixme-tag approach names (A1-A8) — i.e. the contamination now reaches research_add_instances/research_record_pipeline output, not just the approach assigned for tuning. Same fix as P1/L1/L2: verify the approach's and corpus's claimed file/symbol/subject against the topic's real issue before tuning or recording trials, and record+stop at the first mismatch rather than iterating.

### L4 — No tool lists existing task-instance names/phases by topic

**2026-08-21** — **2026-08-21** — No MCP tool enumerates existing task-instance names or their assigned phase for a given topic. `research_split`'s phase assignment is a deterministic hash with fixed small validate/test sizes that barely grow as the corpus grows, so forcing new instances into validate/test requires adding several throwaway probe instances and checking `research_record_trial`'s returned `phase` field one at a time until the desired phase comes up. This is slow but is currently the only way; no shortcut found. Worth a feature request if this recurs.

### L5 — P1 mismatch also reaches the retry prompt's checkpoint-skill field, not just approach/corpus

**2026-08-21** — 2026-08-21 — [[phronix-self-research#P1]] widens again: a retry prompt's checkpoint skill name ("degree-filter-itermonomials") and approach details were assigned to a task whose actual issue.md was unrelated (SI._collect_factor_and_dimension exp()/sqrt() dimensionless bug, not itermonomials). So the mismatch isn't confined to `research_choose`'s approach field or corpus/pipeline data (L1-L3) — it also reaches whatever assigns the checkpoint/retry-prompt skill reference. Fix is the same in kind: don't trust the prompt's named skill or approach at face value — cross-check `research_status`/`research_rank` keyed on the task's own topic id against the topic's real issue.md before acting, and treat a mismatch there as confirmation to route by the correct topic id, not by what the prompt named.
