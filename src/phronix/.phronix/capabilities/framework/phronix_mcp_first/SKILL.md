---
name: phronix_mcp_first
description: Never hand-roll what an MCP tool already does; when an MCP tool fails, repair the tool so the next run succeeds instead of working around it with Bash. Load before any pipeline step that calls an MCP tool, and the moment one fails ('Unsupported build tool: unknown', 'Unknown build tool', 'dftracer pip install failed', any tool error), or when tempted to drive pip/git/cmake by hand for a job a tool covers.
---
Cross-references: [[capability_builder]], [[lessons]], [[knowledge]], [[phronix_self_healing]], [[phronix_capability_authoring]]

# MCP first: repair the tool, never work around it

Converted from the dftracer-agents skill `mcp-first` (subject: repairing MCP tools instead of working around them). Source description: Never hand-roll what an MCP tool already does. When an MCP tool fails, repair the tool so the next run succeeds — do not work around it with Bash. Load before any pipeline step that calls an MCP tool.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder's Self-heal ('If a tool here is wrong, capability_update it; do not work around it in shell') states the same rule for capabilities; this skill is the dftracer-agents form (fix the tool module, the server reloads). Recording the fix uses `lesson_add` (lessons) and a memory via `memory_write` (knowledge). Candidate to merge into capability_builder.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The rule |
| `I2` | Instructions | What to do when a tool fails |
| `E1` | Evidence | What working around it cost |

## I1 — The rule

If an MCP tool exists for a job, it is the only way to do that job.

Doing it by hand with `Bash` is forbidden even when it would be faster, even
when the tool just failed, and even when you can see exactly which shell
command would work. A hand-rolled step leaves nothing behind: the next run
hits the same failure, improvises again, and the system never gets better at
the thing it does most often.

## I2 — What to do when a tool fails

A tool failure is a repair task, not a detour. In order:

1. **Read the error as a defect report.** `Unsupported build tool: unknown`
   is not a fact about this app — it is a gap in the tool's detection.
2. **Fix the tool.** Find its module under
   `src/dftracer_agents/mcp_tools/tools/`, make it handle the case, and say
   in a comment why the case exists.
3. **Re-call the tool.** The run continues through the tool, not around it.
4. **Record it** so the fix survives: a lesson on this skill, and a phronix
   memory entry if it is a fact about the workload rather than the tool.

Only if the tool cannot be repaired within the step's budget: stop and report
the tool defect. Stopping is an acceptable outcome. Silently succeeding by
hand is not — it hides the defect and reports health the system does not have.

Use `Bash` freely for what no tool covers: inspecting the tree, reading logs,
checking whether a fix worked.

## I3 — When a repair takes effect

Immediately. The dftracer MCP server runs over HTTP with `--reload`: it
watches its own source tree and re-execs when a tool file changes. An edit to
an existing tool's body is live within a second or two.

So, having fixed a tool:

1. **Re-call it.** Do not stop, do not report the run blocked, and never ask
   anyone to restart a server — the restart already happened.
2. If the very next call still fails the same way, wait a moment and try once
   more; the re-exec takes a second.
3. Only a NEW or RENAMED tool needs the client to reconnect, because the tool
   list is sent at connection time. Editing an existing tool does not.

There is never a reason to end a turn waiting for a human to restart
something.

## E1 — Evidence

Running pecan_milan on corona, three MCP calls failed in a row:

    session_configure        → "Unsupported build tool: unknown"
    session_build_install    → "Unknown build tool: unknown"
    session_install_dftracer → "dftracer pip install failed"

pecan_milan is raw research Python with no `setup.py` or `pyproject.toml`, so
detection returned `build_tool: unknown` and every builder refused it. The
agent fell back to driving `pip` and `git` by hand.

That path can even produce a working run — and it is still the wrong outcome.
The detector still does not know what a bare-Python workload is, so the next
workload of that shape fails identically, and the pipeline's own measurements
stop describing the pipeline. The fix belongs in the detector.

## Rules

- Render the procedure with `phronix_mcp_first_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `tool`, `error`, `outcome`, `fix`, `recalled`, `lesson`, `workaround_used`, `defect_report`) to `phronix_mcp_first_check`; a step is done only when the check passes.
- I1: If an MCP tool exists for a job, it is the only way to do that job; Bash for it is forbidden even when faster, even when the tool just failed.
- I2: A tool failure is a repair task, not a detour: read, fix, re-call, record.
- I3: A repair is live immediately (--reload); there is never a reason to end a turn waiting for a human to restart something.
- I1b: Use Bash freely for what no tool covers: inspecting the tree, reading logs, checking whether a fix worked.

## Constraints

- Never hand-roll with Bash a job an MCP tool covers, even when the tool just failed and the shell command is obvious.
- Never ask a human to restart the MCP server: it re-execs itself on a changed tool file.
- Stop (and report) rather than succeed by hand when the tool cannot be repaired within the step's budget.
- In the capability store, repair a capability's tool only through capability_update (user approval), never by editing its files.

## Corner cases

- The re-exec after an edit takes a second: if the very next call fails the same way, wait a moment and try once more before concluding the fix failed (I3).
- Only a NEW or RENAMED tool needs the client to reconnect; editing an existing tool's body does not (I3).
- A hand-rolled path can even produce a working run and is still the wrong outcome: the next workload of that shape fails identically and the pipeline's measurements stop describing the pipeline (E1).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_mcp_first_plan`, validator `phronix_mcp_first_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `tool_named` failed: name the MCP tool that failed
- `error_quoted` failed: quote the tool's error text: it is the defect report
- `outcome_known` failed: outcome is 'repaired' or 'stopped'; 'worked around' is not an outcome
- `no_workaround` failed: undo the Bash workaround; repair the tool and re-call it (I1)
- `fix_described` failed: say what changed in the tool and why the case exists (I2 step 2)
- `recalled_after_fix` failed: re-call the tool after the fix; the run continues through the tool, not around it (I2 step 3, I3)
- `lesson_recorded` failed: lesson_add the fix with the error text as evidence (I2 step 4)
- `defect_reported` failed: report the tool defect: tool, error, why it could not be repaired in budget
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- The repair itself failed twice the same way: stop and report the defect (I2 last paragraph); do not switch to Bash.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A tool gap met here (a workload shape a detector does not know) is fixed in the tool and recorded as a lesson; a fact about the workload goes to memory or its workload_<app> capability.
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Fix the tool's module, re-call it (live within a second or two under --reload), record a lesson (mcp-first I2/I3, 2026-09-15).
- `phronix_mcp_first_plan` -> follow the checklist -> `phronix_mcp_first_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
