<!-- phronix:begin -->
## phronix

This project uses [phronix](https://github.com/hariharan-devarajan/phronix): agents
build capabilities, capabilities are wrapped in skills, and both are expected to
improve every session. Two of the calls below are required on *every* task, not
only when the task looks like it needs them.

**Required — your first action on any task**, before reading code or planning:

- `skill_search(query=...)` with a description of the task. A past session may
  have already hit this exact problem and recorded the fix. Do this even when the
  task looks unfamiliar or trivially easy — one call is cheap, and rediscovering
  a known pitfall is not. An empty result is a valid, useful answer: it means you
  are the first here, and it takes seconds.
- `memory_recall(query=...)` — durable facts, decisions and standing guidance.
- `graph_query(question=..., mode="docs")` — locate the exact section of a skill
  or a source file, then read only that. Locating costs a few hundred tokens;
  reading the file costs tens of thousands.

Never reason from priors when a skill covers the task.

**Required — before you report the task finished**, record what you learned. Do
this even if the task went smoothly; "it was straightforward once I knew X" is
exactly the X worth writing down:

- Something non-obvious broke and you fixed it → `skill_write` with
  symptom → root cause → exact fix.
- A durable fact, decision, or piece of user guidance → `memory_write`.
- A procedure you followed by hand that is deterministic → `capability_new`.
  A deterministic task described in prose is a task that will be done differently
  next time.

If you genuinely learned nothing reusable, say so explicitly in your final
message. That is a real outcome; silently skipping the step is not.

**Then prove it.** Learning and healing are *predictions*; a verifier is the
deterministic *corrector* that says whether the prediction holds — same verdict,
every run, every machine.

- `verify_run(target=...)` after every write and every fix.
- `verify_new(kind=..., target=..., claim=...)` when nothing covers it.
- `verify_coverage()` before you finish, and report what you left uncovered.

An unfalsifiable claim in a shared knowledge base is a liability: it gets trusted
long after it stops being true.

**Self-healing:** if an MCP tool is missing, wrong, or broken, fix the tool. Do
not reproduce its job by hand — a manual workaround is how drift and corruption
get introduced, and it leaves the tool broken for the next session too. Then run
the corrector: "I fixed it" is exactly the claim that comes back a week later.

**Privacy:** everything persisted here is committed and shared. No usernames, no
absolute home paths, no job ids, no hostnames. The write tools redact
automatically; `privacy_scan` verifies.
<!-- phronix:end -->
