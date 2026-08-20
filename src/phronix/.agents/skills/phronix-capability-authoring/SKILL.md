---
name: phronix-capability-authoring
description: How to write a capability — a deterministic MCP tool authored at runtime. When something should be code rather than prose, the module contract, docstrings a model can act on, error design, layer choice, and the restart requirement. Load before calling capability_new.
subject: authoring MCP tools the framework builds for itself
type: skill
---

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

## References

### X1 — When it should have been a skill instead

Judgment belongs in prose: [[phronix-skill-authoring#R1]].

### X2 — Proving the tool behaves

A tool nothing tests will drift silently while everything downstream keeps
trusting it: [[phronix-verification#I3]].
