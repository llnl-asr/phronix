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


### group1 — `claude-0827-005934`  (30 task(s), 8 node(s))

```
TOTAL  60 task(s)     6 pass   54 fail    0 run    10% of finished      6.2M tok   $174.89   [#########!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

- run: `/p/lustre5/haridev/phronix-bench/runs/claude-0827-005934`
- fleet: `/p/lustre5/haridev/llm-tuolumne/logs/deploy-group1-005640.log` (32/32 ready)
- skills written: **32**   attempts that loaded one: **27**
- `scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0827-005934 --once`

### group 1 — `claude-0827-005934`  (30 tasks, 8 nodes, batch job)

```
TOTAL  60 task(s)   6 pass   54 fail   0 run   10% of finished   $174.89
```

The first COMPLETE group of the night: every task reached a verdict, none was
cut off by an allocation ending. 52 minutes of run time inside a 60-minute
pdebug allocation, fleet up in 2m41s.

- run: `/p/lustre5/haridev/phronix-bench/runs/claude-0827-005934`
- batch log: `/p/lustre5/haridev/phronix-bench/batch-group1-0827-005618.log`
- `scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0827-005934 --once`

Errors, split by cause (`scripts/pipeline-errors.sh <run>`):

```
PIPELINE                                    MODEL
  6  ssh command failed                      26  gave up without editing
  4  testbed cannot run pytest
  3  gateway error
  3  runner never started
  1  agent overflowed its context
tasks touched by a pipeline fault: 11 of 30
```

## Groups 2-10 were NOT run

They were driven by `scripts/overnight.sh`, which I stopped when group 1 was
moved to a batch job, and did not restart. About five hours of queue time went
unused. The full 300-task run below covers the same ground.

## The full run

`f3UkYD13pMvw` — 32 nodes, 24h, pbatch, all 300 tasks, 60 at a time.
Submitted 07:35, queued behind whatever pbatch is running.

```bash
flux jobs -o "{id} {state} {t_remaining!F} {name}" | grep lite300
tail -f /p/lustre5/haridev/phronix-bench/batch-lite300-0827-073546.log
scripts/top.sh --once
scripts/pipeline-errors.sh          # model faults vs harness faults
```

### tuo-g1 — `claude-0827-130119`  (30 task(s), 8 node(s))

```
TOTAL  60 task(s)     5 pass   45 fail   10 run    10% of finished     28.5M tok    $88.22   [########!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

- run: `/p/lustre5/haridev/phronix-bench/runs/claude-0827-130119`
- fleet: `/p/lustre5/haridev/llm-tuolumne/logs/deploy-tuo-g1-125807.log` (32/32 ready)
- skills written: **26**   attempts that loaded one: **18**
- `scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0827-130119 --once`


---

# Runs of the whole 300 — 2026-08-29

## What has already run, and what it showed

Both on 64 nodes, 256 replicas, `--parallel 120`, the same 300-task list.

| | gpt-oss-120b | nemotron-3.5 |
|---|---|---|
| run | `claude-0829-012358` | `claude-0829-040235` |
| result | 124 pass / 474 fail — **complete** | 196 pass / 299 fail / 105 unfinished |
| wall | **2h05m** for all 300 | killed at 3h46m |
| tokens / cost | 54.3M / $995 | 450.9M / $1998 |
| ended because | finished | **a node died** — see below |

```bash
scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0829-012358 --once
scripts/error-report.py /p/lustre5/haridev/phronix-bench/runs/claude-0829-012358
```

**The two are not comparable as they stand**: nemotron did not finish, and its
196 passes are from 82% of the list. It was also the run whose pipeline faults
outnumbered its model failures, so its numbers describe the harness more than
the model.

### The split

| | gpt-oss-120b | nemotron-3.5 |
|---|---|---|
| PIPELINE | 274 | **1115** |
| TESTBED | 13 | 5 |
| MODEL | **1195** | 592 |

gpt-oss is what a healthy run looks like: failures are 843 "target tests still
failing" and 319 "no patch produced" — real attempts, wrong answers. Nemotron
is the opposite, and two faults account for nearly all of it:

* **563 stages killed at their ceiling** (196 research at 900s, 151 at 300s).
  Cause found: `budget_scale = 0.5` in BOTH manifests — the *hosted* fallback.
  The rate is read from `predicted_tokens_seconds`, which counts FINISHED
  requests, so it reads 0 on a fleet deployed seconds ago — which is every
  batch run. `measured_decode_rate()` returned nothing, nothing was read as
  "no fleet, therefore hosted", and every budget was HALVED on the slowest
  hardware. Now a configured-but-unmeasured fleet gets a generous 2.0 and is
  not cached, so it re-measures once traffic exists.
* **467 "phronix arm ran as a plain agent"** (against 7 for gpt-oss). NOT yet
  explained. Phronix tools were being called — 261 calls, 175 skills written,
  77 skill loads — so the framework was working; the flag is per stage, and
  259 of them are `attempt-1`, where a fresh run has nothing to retrieve. The
  open question is the `learn-1` and `research-2` ones. **Until this is
  understood, treat nemotron's phronix-vs-bare comparison as unproven.**

### Why nemotron stopped

```
exception type="exec" note="node failure on tuolumne1081 (rank 81)"
```

`tuolumne1081` was its gateway node, so Flux tore down the whole 64-node job
and took 105 in-flight tasks with it. The server logs on that node end
mid-work at 178 t/s with **no allocation error** — no `cudaMalloc failed`, no
`out of memory` — so llama-server did not OOM; the process was killed. A HOST
OOM-kill would look the same from the log side, and on MI300A the 128 GB is
unified, shared by four replicas plus the co-located agents and containers, so
it cannot be ruled out. `GPUS_PER_NODE=3` would leave a GPU's worth of headroom
if it recurs.

## Queued now, with the fixes above

| model | job | wall |
|---|---|---|
| gpt-oss-120b | `f3V81KPSmb3M` | 5h |
| nemotron-3.5 | `f3V81KzJxhRh` | 9h |
| ornith-1.5 | `f3V81LbXudks` | 9h |
| nemotron-super-49b | `f3V81MCJAo1q` | 9h |

Walls are the measured time plus 30%, not the 24h the first pair asked for:
gpt-oss took 2h05m, nemotron was on course for ~4h40m, and doubled budgets add
roughly half again. A finished job now releases its nodes instead of sitting on
them — the first pair wasted 21h50m of 64 idle nodes between them.

### These runs survive a node failure

Three layers, because the failure comes in three sizes:

1. **`--resume auto`** — `results.jsonl` is written per task as it finishes, so
   it was always a checkpoint; nothing read it. A resubmitted job now carries
   forward what the dead one finished and re-runs only what was lost. Before
   this, the resubmission repeated ~500 completed task-arms.
2. **Supervised passes** — the run is retried up to 4 times inside its
   allocation, each pass re-deriving which nodes still answer and resuming from
   the last. A pass that dies costs its in-flight tasks and nothing else.
3. **Per-task failover** — an isolation failure moves that task to another node
   and does not count toward the abort; bad hosts are recorded process-wide and
   new tasks round-robin over the survivors.

## They are safe to run at the same time

This needed fixing before queueing four of them, and the failure would have
been silent:

`deploy.sh` writes its fleet description to `$RUNDIR/cluster.json` and copies
it to the shared `<fleet>/cluster.json`. That copy is last-writer-wins, and
`run-group.sh --local` reads it — so the first job's tasks would have been sent
to the **second** job's gateway. One fleet serving twice its load, the other
idle, and the manifest naming the wrong gateway so the trace would not have
shown it.

Now: each job exports its own `RUNDIR` (named for the job, not the clock — two
jobs starting in the same second would collide on a timestamp), `deploy.sh`
honours it, and the run is pointed at that file with `--cluster` rather than
`--local`. The shared copy stays for interactive use.

The task-list slice was shared too: its path is derived from `--size` and
`--index` alone, so four runs of the same 300 all wrote `size-300/group-01.txt`
at once. Identical content makes that race invisible until a reader catches it
half-written and starts on a truncated list. It is now written to a temporary
file and renamed into place.

## How to read them

```bash
scripts/top.sh --once          # follows the newest run by itself
scripts/error-report.py        # pipeline / testbed / model, newest run
scripts/error-report.py <run-dir> ...
flux jobs -a | head
```

`error-report.py` splits failures three ways, because they read identically in
a trace and point at completely different work:

| | meaning |
|---|---|
| **PIPELINE** | ours — a harness bug, a moved binary, an ssh limit, a budget |
| **TESTBED** | the SWE-bench image's own environment (e.g. sphinx's Jinja drift, astropy's conftest). Nothing in this repo fixes these |
| **MODEL** | the benchmark working: the agent did not solve the task |

Anything unrecognised is reported as UNCLASSIFIED rather than assumed to be a
model failure — a fault the report does not know about is the one worth seeing.

## What these runs are the first test of

Four fixes went in today. Only the first is confirmed in production:

1. **Images load from the PFS archive before the registry.** Container startup
   pulled from Docker Hub first, always, while all 300 images sat archived on
   `<data root>/images`. A group scheduled onto fresh nodes hit
   `toomanyrequests: You have reached your unauthenticated pull rate limit` and
   lost **all 60 task-arms in four minutes**, reported as `isolation: could not
   start <image>` — which reads as a missing image, not a quota. **Confirmed:
   the same group went from 60 image failures to 0.**
2. **A patch that does not parse is a verdict, not a runner fault.** The code
   assumed "a patch that breaks everything still makes the tests RUN" — false
   when the patch is not valid Python. On django-14155 the agent wrote diff
   markers into the source; the harness said `RUNNER FAILED`, which inflated the
   pipeline count *and* told the attempt the runner broke rather than that its
   own edit will not parse, so the next try had nothing to correct.
3. **A failed ssh says why.** `CalledProcessError` renders the command and the
   exit code only, so a container failure arrived as a hundred characters of
   podman arguments — indistinguishable between sshd refusing, a missing image
   and a full disk.
4. **Budgets scale with measured decode**, bounded at 6x. Unscaled, 178 of one
   corona run's 314 pipeline faults were stages killed at their ceiling.

If any of 2-4 did not hold, `error-report.py` shows it directly: the same
`tests could not run`, `ssh command failed` or `stage hit its ceiling` counts.



## New Runs

Fresh: /p/lustre5/haridev/phronix-bench/runs/claude-0831-151643


### smoke5-fresh — `claude-0831-173550`  (5 task(s), 4 node(s))

```
TOTAL  10 task(s)     1 pass    9 fail    0 run    10% of finished      1.4M tok    $32.48   [#########!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

- run: `/p/lustre5/haridev/phronix-bench/runs/claude-0831-173550`
- fleet: `/p/lustre5/haridev/llm-tuolumne/logs/deploy-smoke5-fresh-173318.log` (16/16 ready)
- skills written: **6**   attempts that loaded one: **6**
- `scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0831-173550 --once`
