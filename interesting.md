# Run log — overnight batch, 2026-08-27

Groups 1–10 of SWE-bench lite (30 tasks each), Tuolumne, gpt-oss-120b on 32
replicas. Each group gets its own 60-minute `pdebug` allocation: fleet on all 8
nodes, containers co-located on the same 8.

Read this top-down; the newest group is appended at the bottom.

## How to look at a run

```bash
scripts/top.sh <run-dir>            # live/final tree, per-task
scripts/top.sh <run-dir> --once     # one frame, pipeable
```

The three lines worth grepping in any task's `trace.log`:

| line | what it tells you |
|---|---|
| `search-skill found \`X\`` | the store had an answer before the attempt |
| `skill-use try N: loaded \`X\`` | the attempt actually opened it (vs `** never loaded it`) |
| `re-filed N skill(s) into \`X\`` | research misnamed its skill and the harness recovered it |

## What was fixed tonight, and what to distrust

Fixed and now live: research must leave a skill (re-asked to file if it did
not); re-filing is a deterministic directory move, not an agent, so it cannot
be lost to an API retry; strays are matched on the ISSUE NUMBER, after a bug
where `pydata-xarray-3364` merged and then deleted `pydata-xarray-4493` — a
different task — and inherited its instructions; ssh refusals are retried,
which was voiding tasks as `could not start <image>`; `skill-use` reads the
attempt transcript rather than `retrievals.jsonl`, which gave false negatives.

Still unreliable, do not read too much into it: `tools research-N: no phronix
tools called` fires even when research demonstrably wrote a skill — the
transcript miner does not recognise `skill_write`.

## Fixed after the index was first written

These landed after group 1 started, so **group 1 does not have them** and
groups 2+ do. Worth knowing when comparing.

**A patch that does not parse no longer throws the task away.** The harness
already told "the patch broke the testbed" apart from "the environment is
broken" — the first is a failed attempt worth retrying, the second is fatal.
But it recognised the culprit only in `/testbed/...` paths and bare basenames,
and pytest names it as `sympy/core/function.py:3278:` — a relative path with a
line number, which matched neither. So a `SyntaxError` the agent had just
written read as an environment fault and aborted the task with its tries
unused. Separately, the message was trimmed by size and the line naming the
file was the first thing dropped, so even a recognisable path often never
reached the check. Across one night that was ~12 tasks, every one a patch error
and every one the kind a retry reliably fixes.

**The skill's lessons are now reachable.** A skill is two files and they are
retrieved separately: `skill_load` returns `SKILL.md` unless asked for
`LESSONS.md` by name, so a reader had no way to know lessons existed. Writing
a lesson now names it in the skill's `## References`, and loading a skill
returns the lesson titles. Research is handed both files, and its method skill
(`phronix-task-research#I7`) says to read the lessons before diagnosing and to
write one back naming the tests the last patch broke.

**Research is no longer satisfied by an empty skill.** `skill_write` creates
the scaffold, so a pass that named the skill and wrote no blocks left
`## Instructions` empty and every later check content. The lookup then reported
`found ... — the attempt solves with it`, and the attempt loaded a file with
nothing in it. Measured in one run: **6 of 11 stored skills were scaffolds**.
The check now asks for instructions or rules, and lessons deliberately do not
count — a lesson is "the last attempt failed", an instruction is what to do
instead.

**Cross-task skill theft.** Strays were matched on a name stem, so
`pydata-xarray-3364` merged and then DELETED `pydata-xarray-4493` — a different
task — and inherited its instructions about the wrong file. Matched on the
issue number now.

## Known, not fixed — worth a look in the morning

**Attempts that run until the context overflows.** Ten attempts died with
`API Error: 400 litellm.ContextWindowExceededError`. On sphinx-10451 that was
after **215 steps** in one attempt: the agent kept searching and reading until
the conversation itself exceeded 128k, then lost the turn and produced nothing.
There is a wall-clock budget (1800s) but no step ceiling, so an agent that
neither finishes nor gives up spends the whole try and leaves no diff. A cap
would not make it write a patch, but it would leave a usable transcript and a
lesson instead of an API error.

**`tools research-N: no phronix tools called` is unreliable.** It fires on
passes that demonstrably wrote a skill — the transcript miner does not
recognise `skill_write`. Do not read it as evidence a pass did nothing.

**The pass rate is small-sample.** Across tonight's runs, resolved counts are
in the 2-6 range per 30-task group. The difference between 6 and 2 is not
outside noise at that size; treat single-run comparisons with suspicion and
prefer the error-class table, which is much less noisy.

## Runs

## Running one yourself

`scripts/bench-batch.sh` is both the submitter and the payload — one file, so
what you submit and what runs cannot drift apart.

```bash
# the full list, 24 hours, 32 nodes
scripts/bench-batch.sh --submit -N 32 -t 24h -q pbatch --size 300 --parallel 60

# one group, one hour
scripts/bench-batch.sh --submit -N 8 -t 60m -q pdebug --size 30 --index 4
```

It brings up the fleet on every node, runs the slice with containers and agents
co-located on those same nodes, then stops the fleet and appends its result
here.

`-t` has no default on purpose. It is the one number that decides whether the
tail of a run completes or is cut off mid-attempt, and a run cut off reports
`Access denied: user has no active jobs on this node` for every remaining try —
which looks like task failures and is not. Budget ~5 minutes of fleet load plus
~20 minutes per task at three tries.

`--parallel` wants about one agent per replica. A node serves four replicas, so
32 nodes is 128, and 60 tasks (120 arms) fits. Measured on a smaller fleet:
four requests sharing one replica cut each agent from 27 to 7 tokens/second and
attempts stopped finishing inside their budget at all — more concurrency bought
less work.

<!-- Groups 2..10 are appended below by scripts/overnight.sh as each finishes. -->

**If nothing appears below this line**, the driver stopped. Check, in order:

```bash
tail -40 /p/lustre5/haridev/phronix-bench/overnight.log      # what the driver did
tail -20 /p/lustre5/haridev/phronix-bench/overnight-driver.log
pgrep -af start-overnight.sh                                  # is it still alive
flux jobs -a | head                                           # did pdebug grant anything
```

The most likely reason is that `flux alloc -N 8 -t 60 -q pdebug --bg` stopped
being granted — pdebug is shared and eight nodes is a large ask overnight. The
driver records that as "no allocation granted" and stops rather than spinning.

To pick up by hand from wherever it stopped:

```bash
scripts/overnight.sh 5 10        # or whichever group is next
```

