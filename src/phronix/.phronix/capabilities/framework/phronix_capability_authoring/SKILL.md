---
name: phronix_capability_authoring
description: How to write a capability, a deterministic MCP tool authored at runtime: when something should be code rather than prose, the module contract (register(mcp)), docstrings a model can act on, error design, layer choice, and the restart requirement. Load before calling capability_new, when a tool returns a bare 'failed', hard-codes a path or a judgement, silently picks a default, wraps a single command, or is not callable right after it was created.
---
Cross-references: [[capability_builder]], [[knowledge]], [[phronix_skill_authoring]], [[phronix_verification]], [[phronix_research_as_tools]]

# Authoring MCP tools the framework builds for itself

Converted from the dftracer-agents skill `phronix-capability-authoring` (subject: authoring MCP tools the framework builds for itself). Source description: How to write a capability — a deterministic MCP tool authored at runtime. When something should be code rather than prose, the module contract, docstrings a model can act on, error design, layer choice, and the restart requirement. Load before calling capability_new.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** Largely duplicates capability_builder: the 'two people would do it identically -> code' test (I1/R1), docstrings as the only description (I3), no machine paths (R4), knowledge_search then capability_list before building (I1), checks as the corrector (I5 step 3 / X2). Differences: phronix layers (project/user/bundled) and permissions_sync/restart wiring; in this store approval and live reload replace them. Strong merge candidate into capability_builder.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Decide whether it should be code at all |
| `I2` | Instructions | Nail the interface before the implementation |
| `I3` | Instructions | Write the docstring first, for a model |
| `I4` | Instructions | Implement the module contract |
| `I5` | Instructions | Finish the wiring |
| `R1` | Rules | Deterministic work becomes code, not prose |
| `R2` | Rules | Never hard-code a judgment call in a tool |
| `R3` | Rules | Fail loudly and specifically |
| `R4` | Rules | Take paths as arguments, never hard-code them |
| `R5` | Rules | Do not wrap a single command with no added value |
| `R6` | Rules | Choose the layer by who should inherit it |
| `X1` | References | When it should have been a skill instead |
| `X2` | References | Proving the tool behaves |

## Instructions

### I1 — Decide whether it should be code at all

The honest test: **could you write the rule down such that two competent people
would produce byte-identical output?** If yes, it is a capability. If the right
answer depends on reading the situation, it is a skill.

Then check `capability_list()`. A second tool overlapping an existing one splits
usage between them and leaves both half-maintained.

### I2 — Nail the interface before the implementation

What are the inputs, what comes back, and what happens on each failure mode? A
tool whose error path returns a bare "failed" is a tool that gets worked around.

### I3 — Write the docstring first, for a model

It is the ONLY description an agent ever sees. Four parts:

1. **One line: what it does.** Concrete verb, concrete object.
2. **When to reach for it.** The trigger. This is what makes a model choose your
   tool over doing the work by hand, and it is the part most often omitted.
3. **Every argument** — meaning, format, what happens if omitted.
4. **The return shape** — name the keys. An agent that has to guess will guess
   wrong and parse defensively around your tool forever.

### I4 — Implement the module contract

```python
"""Count TODO markers in a source tree."""
import json
from pathlib import Path

def register(mcp):
    @mcp.tool()
    def count_todos(path: str) -> str:
        """Count TODO/FIXME markers under *path*, grouped by file. ..."""
        root = Path(path).expanduser()
        if not root.is_dir():
            return json.dumps({"status": "error",
                               "error": f"{path} is not a directory"})
        ...
```

`capability_new` compiles the module and checks for `register` **before** saving,
so a broken tool is rejected now rather than at the next server start with nobody
around who knows what it was for.

### I5 — Finish the wiring

1. `permissions_sync` — the MCP allowlist is discovered by scanning for registered
   tools; until this runs, the new tool interrupts unattended sessions with a
   permission prompt.
2. Say a restart is needed, explicitly.
3. `verify_new` a corrector that exercises the tool on a known input.
4. `skill_write` the reason it exists — an undocumented capability gets deleted by
   someone tidying up.

## Rules

### R1 — Deterministic work becomes code, not prose

Prose describing fixed steps is re-derived, slightly differently, on every read.
Those differences accumulate into drift, and drift is what stops an agentic system
being reproducible. Each capability removes a class of variation permanently.

### R2 — Never hard-code a judgment call in a tool

It will be applied silently and confidently in situations where it is wrong, with
nothing in the output signalling the assumption. That belongs in a skill.

### R3 — Fail loudly and specifically

`{"status": "error", "error": "path X does not exist"}` is actionable; `"failed"`
is not. Never return a partial result as a success — that teaches the agent to
trust something it should not, and the damage surfaces three steps later. Never
swallow an exception into an empty string.

### R4 — Take paths as arguments, never hard-code them

An absolute path from the authoring machine is both a leak and a bug for the next
person. The writer redacts, but it cannot invent the right path.

### R5 — Do not wrap a single command with no added value

If the agent can run it directly, the tool is pure overhead. Wrap when there is
validation, error interpretation, or a multi-step sequence worth freezing.

### R6 — Choose the layer by who should inherit it

| Layer | Audience | Use when |
|---|---|---|
| `project` | everyone who clones this repo | it assumes something about this repository — the common case |
| `user` | you, across your projects | it is about your environment |
| `bundled` | everyone who installs phronix | genuinely general, assumes nothing project-specific |

When in doubt, `project`. Promoting later is easy and reviewed; un-shipping a bad
general tool is not.

### Using the tools (capability)

- Render the procedure with `phronix_capability_authoring_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `name`, `byte_identical`, `overlapping_tools`, `docstring`, `error_examples`, `hardcoded_paths`, `judgement_calls`, `single_command_wrapper`, `layer`, `layer_reason`, `restart_stated`, `verifier`, `silent_defaults`) to `phronix_capability_authoring_check`; a step is done only when the check passes.

## References

### X1 — When it should have been a skill instead

Judgment belongs in prose: [[phronix-skill-authoring#R1]].

### X2 — Proving the tool behaves

A tool nothing tests will drift silently while everything downstream keeps
trusting it: [[phronix-verification#I3]].

## Constraints

- capability_new compiles the module and checks for register before saving; a broken tool is rejected now (I4).
- No hard-coded absolute paths; the writer redacts but cannot invent the right path (R4).
- In this store, a person approves every capability (capability_apply after a yes) and it goes live with no restart; the phronix restart/permissions_sync steps apply to the dftracer-agents server.

## Corner cases

- A tool whose error path returns a bare 'failed' is a tool that gets worked around (I2).
- Returning a partial result as success teaches the agent to trust something it should not; the damage surfaces three steps later (R3).
- When in doubt between layers, project: promoting later is easy and reviewed, un-shipping a bad general tool is not (R6).
- Until permissions_sync runs, the new tool interrupts unattended sessions with a permission prompt (I5).
- An undocumented capability gets deleted by someone tidying up: skill_write the reason it exists (I5).
- P1 (source pitfall) — A capability that only works in one repository, written to `bundled`: Everyone else gets a tool that always fails, and it looks like a framework bug rather than a mis-scoped contribution.
- P2 (source pitfall) — Silent defaults for things that matter: A tool that quietly picks a version, a path or a mode produces results nobody can reproduce, and the choice is invisible in the output.
- P3 (source pitfall) — Expecting a new tool to be callable immediately: A running MCP server holds tool closures captured at registration time. The tool does not exist until the server restarts — say so rather than letting the caller discover it by calling something that is not there.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_capability_authoring_plan`, validator `phronix_capability_authoring_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `should_be_code` failed: if two competent people would not produce byte-identical output, it is a skill, not a capability (I1, X1)
- `no_overlap` failed: extend the existing tool instead of adding a second one that splits usage (I1)
- `docstring_when` failed: the docstring must say when to reach for the tool (I3 part 2)
- `docstring_returns` failed: name the returned keys in the docstring (I3 part 4)
- `errors_specific` failed: return {status: error, error: <what and where>}, never a bare 'failed' (R3)
- `errors_given` failed: design the error path for each failure mode before implementing (I2)
- `no_hardcoded_paths` failed: take paths as arguments (R4)
- `no_judgement_calls` failed: move the judgement into a skill; the tool takes it as an argument (R2)
- `no_silent_defaults` failed: make a version/path/mode that matters an explicit argument and echo it in the output (P2)
- `adds_value` failed: do not wrap a single command with no validation, interpretation or sequence (R5)
- `layer_chosen` failed: choose project, user or bundled by who should inherit it; when in doubt, project (R6)
- `bundled_is_general` failed: say why it assumes nothing project-specific; a one-repo tool in bundled fails for everyone else (P1)
- `restart_stated` failed: say explicitly that a restart is needed before the tool is callable (I5, P3)
- `verifier` failed: add a verifier that exercises the tool on a known input (verify_new / checks.json) (I5, X2)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A tool nothing tests drifts silently: add a verifier/check that exercises it on a known input (X2, phronix-verification I3).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- Every deterministic procedure met while authoring is itself a candidate capability; judgement goes to a skill (X1).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Byte-identical test -> capability_list/knowledge_search -> interface and errors -> docstring first -> register(mcp) -> layer -> verifier (phronix-capability-authoring I1-I5, 2026-09-15).
- `phronix_capability_authoring_plan` -> follow the checklist -> `phronix_capability_authoring_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
