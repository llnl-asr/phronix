---
name: phronix-self-research
description: How to work out the way an unfamiliar task should be done before attempting it: gating on catalogue coverage, fixing a figure of merit in advance, measuring rival approaches, and turning the winner into capabilities and skills. Load at the start of any task the library does not already cover.
subject: researching how a task should be done before doing it
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Gate on catalogue coverage before researching anything |
| `I2` | Instructions | Declare the figure of merit before looking at approaches |
| `I3` | Instructions | Characterise the subject before searching for it |
| `I4` | Instructions | Look it up externally before reading the code |
| `I5` | Instructions | For a tool, learn its surface: commands, flags, semantics |
| `I6` | Instructions | Ground the external findings in this codebase |
| `I7` | Instructions | Find rival approaches and measure them |
| `I8` | Instructions | Split the plan into deterministic and judgement steps |
| `I9` | Instructions | Verify the research, then record what was achieved |
| `I10` | Instructions | Build task instances: train, validate, test |
| `I11` | Instructions | Tune on validate, confirm on unseen, then write it up |
| `I12` | Instructions | Fix Function handling in UnitSystem._collect_factor_and_dimension |
| `I13` | Instructions | Edit unitsystem.py Function case |
| `I14` | Instructions | Placeholder |
| `I15` | Instructions | Edit unitsystem.py |
| `I16` | Instructions | Update Function handling in UnitSystem._collect_factor_and_dimension |
| `I17` | Instructions | Edit unitsystem Function block |
| `I18` | Instructions | Edit unitsystem.py get_dimensional_expr Function case |
| `R1` | Rules | Never compare approaches before the figure of merit exists |
| `R2` | Rules | A figure of merit must state how it is measured |
| `R3` | Rules | Record rejected approaches with their numbers |
| `R4` | Rules | Deterministic steps become capabilities, never prose |
| `R5` | Rules | Repeated failure in one location is evidence to look elsewhere |
| `R6` | Rules | Every approach records its source; at least one from outside |
| `R7` | Rules | Measure the figure of merit; a prediction cannot decide |
| `R8` | Rules | Only the unseen test instances confirm or falsify |
| `R9` | Rules | Keep unconfirmed approaches as backups; never rediscover them |








## Instructions

### I1 — Gate on catalogue coverage before researching anything

Call `research_assess(task=...)` first. It counts matching blocks in the skill
catalogue and returns `covered` or `gap`.

On `covered`, load the named skills and proceed — a second parallel account of a
subject already documented will contradict the first within a few sessions. On
`gap`, research before attempting.

Do not substitute your own sense of familiarity for this check. It is
deterministic precisely because confidence is the wrong signal here.

### I2 — Declare the figure of merit before looking at approaches

`research_define_fom(topic, name, direction, target, measure)` fixes the single
number that decides, which direction is better, the threshold to reach, and how
the number is obtained.

Prefer a number the task is already judged on over one you invent. For a bug fix
that is usually target tests passing, with regressions as a constraint.

### I3 — Characterise the subject before searching for it

Name what kind of problem this is before looking anything up, because it decides
where to look:

- **a bug in a library** — the project's own issue tracker, commits and changelog
  usually contain the fix or the discussion that leads to it;
- **using a tool** — its documentation and `--help`; the failure is normally a
  flag or a semantic you have not read yet, not a defect;
- **an algorithm or format** — the specification, then a reference
  implementation;
- **an environment or build problem** — release notes and the version in play.

Write the characterisation down in the approach summaries. A search performed
without knowing which of these it is returns the wrong kind of answer
confidently.

### I4 — Look it up externally before reading the code

Do this *first*, before mapping the local code paths. Reading the code first
anchors you to the file you happen to open, and every later search becomes a
search for confirmation.

For a known bug, the sequence that pays: the issue as filed, then whether it was
ever fixed upstream, then the commit that fixed it and what it touched. That
routinely names the exact function and turns the whole task into applying a known
change — which is the correct outcome, not a shortcut.

Use `WebSearch` for the general question and `WebFetch` for the specific page.
Record what you find with `research_add_approach(..., source=<url or reference>)`.

### I5 — For a tool, learn its surface: commands, flags, semantics

When the subject is a tool rather than a defect, spend the search budget on what
the tool actually offers:

- run its `--help` and the `--help` of the relevant subcommand;
- read the documentation for the exact option in play, including its default and
  what it interacts with;
- find how the same task was accomplished elsewhere — a worked example beats a
  parameter list, because it shows the combination that works.

Record the commands and options you confirmed. A tool's surface is durable
knowledge: it is worth a skill block, and the next task on the same tool should
not have to rediscover it.

### I6 — Ground the external findings in this codebase

Only now map the code. For each candidate the external search produced, locate
the code path it refers to in *this* checkout and at *this* version, and confirm
the code actually looks the way the source implies. Upstream moves; a fix
described against a later version may not apply here.

An external finding you could not locate in the code is not a rejected
approach — record it with what you looked for and why it did not match, so the
next session does not repeat the search.

### I7 — Find rival approaches and measure them

At least two genuinely different approaches, each recorded with
`research_add_approach` and whatever you measured.

Look past the first suspect file: upstream issues and commits via `WebSearch` and
`WebFetch`, every code path that could produce the behaviour via `Grep` and
`Read`, and actual runs via `Bash`. A measurement beats an argument.

### I10 — Build task instances: train, validate, test

Author small, cheap cases that exhibit the behaviour — a reproducer script, an
input with a known result — with `research_add_instance`, and assign each a
phase:

- **train** — discovery. These are how you work out what governs the behaviour
  and which approaches exist at all. Failing them means nothing.
- **validate** — refinement. Tune approaches against these and compare them.
  Rework as often as needed; that is the phase's purpose.
- **test** — correctness, on cases no approach was shaped against.

Write the test instances *before* you begin tuning, and do not consult them
while you work. An unseen set you looked at is a tuning set.

### I11 — Tune on validate, confirm on unseen, then write it up

Record every trial with `research_record_trial`, failures included, then call
`research_evaluate_approach`. It sets the status deterministically:

`confirmed` requires passing validate **and** the unseen test instances, and is
the only status that licenses writing the approach up as a skill.

An approach that passes validation and nothing else has demonstrated that it can
be tuned, which is not the claim being made.

### I8 — Split the plan into deterministic and judgement steps

`research_write_plan(topic, steps)` with each step tagged `deterministic` or
`judgement`. Build the deterministic ones with `capability_new` before the plan
is used; write the judgement ones as skill blocks.

Most steps that feel like judgement are not. "Run the failing test and read the
assertion" is mechanical. "Decide which layer should normalise the path" is not.

### I9 — Verify the research, then record what was achieved

`research_verify(topic)` before acting on the plan, and again after executing it
once `research_record_achieved(topic, value)` has recorded the delivered figure
of merit.

The gap between an approach's predicted number and the achieved one is the most
useful thing this loop reports.

### I12 — Fix Function handling in UnitSystem._collect_factor_and_dimension

Modify the Function case in sympy/physics/units/unitsystem.py to correctly handle dimensions. Replace the existing block:
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(
        arg) for arg in expr.args]
    return (expr.func(*(f[0] for f in fds)),
            *(d[1] for d in fds))
```
with a new implementation that ensures all argument dimensions are dimensionless, raising a ValueError otherwise, and returns a dimensionless result when appropriate:
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    # Ensure all argument dimensions are dimensionless
    for _, arg_dim in fds:
        if not self.get_dimension_system().is_dimensionless(arg_dim):
            raise ValueError(
                f'Dimension of "{expr}" argument is {arg_dim}, but it should be dimensionless')
    # Compute the factor using the function applied to the factors of arguments
    factor = expr.func(*(f[0] for f in fds))
    # Functions like exp, sin, cos are dimensionless
    return factor, Dimension(1)
```

### I13 — Edit unitsystem.py Function case

In the file sympy/physics/units/unitsystem.py, replace the block handling Function expressions (lines 192-196) with a corrected implementation that validates argument dimensions and returns a dimensionless result. The new code should be:
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    # Ensure all argument dimensions are dimensionless
    for _, arg_dim in fds:
        if not self.get_dimension_system().is_dimensionless(arg_dim):
            raise ValueError(
                f'Dimension of "{expr}" argument is {arg_dim}, but it should be dimensionless')
    # Compute the factor using the function applied to the factors of arguments
    factor = expr.func(*(f[0] for f in fds))
    # Functions like exp, sin, cos are dimensionless
    return factor, Dimension(1)
```

### I14 — Placeholder

test

### I15 — Edit unitsystem.py

Replace the block handling Function expressions in sympy/physics/units/unitsystem.py with corrected implementation:
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    # Ensure all argument dimensions are dimensionless
    for _, arg_dim in fds:
        if not self.get_dimension_system().is_dimensionless(arg_dim):
            raise ValueError(
                f'Dimension of "{expr}" argument is {arg_dim}, but it should be dimensionless')
    factor = expr.func(*(f[0] for f in fds))
    return factor, Dimension(1)
```

### I16 — Update Function handling in UnitSystem._collect_factor_and_dimension

Modify the `elif isinstance(expr, Function):` block in `sympy/physics/units/unitsystem.py` to correctly handle dimensions for functions. Replace the existing block:
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(
        arg) for arg in expr.args]
    return (expr.func(*(f[0] for f in fds)),
            *(d[1] for d in fds))
```
with a new implementation that ensures all argument dimensions are dimensionless, raising a `ValueError` otherwise, and returns a dimensionless result when appropriate:
```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    # Ensure all argument dimensions are dimensionless
    for _, arg_dim in fds:
        if not self.get_dimension_system().is_dimensionless(arg_dim):
            raise ValueError(
                f'Dimension of "{expr}" argument is {arg_dim}, but it should be dimensionless')
    # Compute the factor using the function applied to the factors of arguments
    factor = expr.func(*(f[0] for f in fds))
    # Functions like exp, sin, cos are dimensionless
    return factor, Dimension(1)
```

### I17 — Edit unitsystem Function block

[No content]

### I18 — Edit unitsystem.py get_dimensional_expr Function case

Replace the broken Function block in get_dimensional_expr with a correct implementation that validates argument dimensions and returns a dimensionless result. The new code should be:\n```python\n        elif isinstance(expr, Function):\n            fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]\n            # Ensure all argument dimensions are dimensionless\n            for _, arg_dim in fds:\n                if not self.get_dimension_system().is_dimensionless(arg_dim):\n                    raise ValueError(\n                        f'Dimension of "{expr}" argument is {arg_dim}, but it should be dimensionless')\n            # Compute the factor using the function applied to the factors of arguments\n            factor = expr.func(*(f[0] for f in fds))\n            # Functions like exp, sin, cos are dimensionless\n            return factor, Dimension(1)\n```

## Rules

### R1 — Never compare approaches before the figure of merit exists

`research_choose` refuses without one. A criterion chosen after the results are
in is a justification for the approach already preferred, not a test of it — and
the resulting record reads exactly like a rigorous comparison.

### R2 — A figure of merit must state how it is measured

A number nobody can re-derive cannot be checked by a corrector. An unfalsifiable
criterion is worse than none, because it lends the appearance of rigour to a
choice that was never measured.

### R7 — Measure the figure of merit; a prediction cannot decide

`research_choose` returns `inconclusive` when no approach measured the figure of
merit, and the corrector fails `constraints` when the winner's value was
predicted.

An argmax over predicted numbers returns whichever approach the agent already
believed in, dressed as a comparison. Apply the candidate, run the measurement
the figure of merit names, and pass it as `measurement=`.

### R8 — Only the unseen test instances confirm or falsify

Failing `train` or `validate` does not refute an approach — those phases exist
for discovery and tuning, and discarding a candidate for failing them throws
away work that only needed another iteration.

Failing `test` does refute it, permanently. That set was never used to shape the
approach, which is the entire reason its verdict counts.

### R9 — Keep unconfirmed approaches as backups; never rediscover them

An approach that is neither confirmed nor falsified stays on record with its
trials. `research_backups` returns them best-first, and a retry starts there.

Research that begins again from nothing after each failed attempt pays full
price to rederive the same set of ideas, and usually arrives at whichever one it
thought of first the last time.

### R3 — Record rejected approaches with their numbers

An approach dismissed without a measurement will be tried again by the next
session. A rejected approach carrying a poor measured result is what stops it.

### R4 — Deterministic steps become capabilities, never prose

A mechanical procedure written as prose is a procedure that will be performed
differently next time. If the step has one right answer for given inputs, it is
code — `capability_new` — not a paragraph.

### R6 — Every approach records its source; at least one from outside

`research_verify` fails the `evidence` facet when no approach says where it came
from, or when every approach came from reading the local checkout.

An unsourced approach cannot be checked and will be re-invented by the next
session. A set of approaches sourced entirely from the file in front of you is
not research; it is the same guess written down several ways, and it reads
identically to genuine investigation once it is in the record.

### R5 — Repeated failure in one location is evidence to look elsewhere

When several attempts have changed the same file and the target still fails, the
useful thing to record is the exclusion: *the cause is not here*. Knowledge that
only ever accumulates about the area already being tried makes the next attempt
more confident and no more correct.

## References
