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

### smoke5-fresh3 — `claude-0831-192216`  (5 task(s), 4 node(s))

```
TOTAL   0 task(s)     0 pass    0 fail    0 run      - of finished         0 tok         -   [........................................................
```

- run: `/p/lustre5/haridev/phronix-bench/runs/claude-0831-192216`
- fleet: `/p/lustre5/haridev/llm-tuolumne/logs/deploy-smoke5-fresh3-191945.log` (16/16 ready)
- skills written: **0**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0831-192216 --once`

### smoke6 — `claude-0831-211616`  (5 task(s), 4 node(s))

```
TOTAL  10 task(s)     1 pass    9 fail    0 run    10% of finished      1.3M tok    $30.08   [#########!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

- run: `/p/lustre5/haridev/phronix-bench/runs/claude-0831-211616`
- fleet: `/p/lustre5/haridev/llm-tuolumne/logs/deploy-smoke6-211341.log` (16/16 ready)
- skills written: **0**   attempts that loaded one: **10**
- `scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0831-211616 --once`

### m20-gptoss120-fresh — `claude-0901-215052-1150614`  (20 task(s), 16 node(s))

```
TOTAL  40 task(s)     3 pass   37 fail    0 run     8% of finished      6.6M tok   $173.70   [#######!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

- run: `/p/lustre5/haridev/phronix-bench/runs/claude-0901-215052-1150614`
- fleet: `/p/lustre5/haridev/llm-tuolumne/logs/deploy-m20-gptoss120-fresh-214747.log` (64/64 ready)
- skills written: **0**   attempts that loaded one: **14**
- `scripts/top.sh /p/lustre5/haridev/phronix-bench/runs/claude-0901-215052-1150614 --once`

## Livai models

### Fresh runs

### livai30c-fresh — `claude-0908-084949-1507128`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4-nano (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    21 pass   39 fail    0 run    35% of finished      6.7M tok   $115.82
claude-bare 7 pass 23 fail 0 run 23% 1.1M tok $13.64 avg 4m24s/task
claude-phronix 14 pass 16 fail 0 run 47% 5.5M tok $102.18 avg 37m21s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0908-084949-1507128`
- fleet: `(none)` (hosted)
- skills written: **31**   attempts that loaded one: **22**
- the first run on corona where the MCP server actually started; every run
  before it had `mcp_servers: [{"name": "phronix", "status": "failed"}]` and
  the phronix arm was a plain agent, so earlier livai numbers are not
  comparable with this one.
- cost is the endpoint's own figure and is not verified: livai's spend API
  returns 403 for this key.
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0908-084949-1507128 --once`

### livai-gpt-5.4-mini — `claude-0908-104954-3730240`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4-mini (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    22 pass   38 fail    0 run    37% of finished      5.3M tok   $100.80
claude-bare 8 pass 22 fail 0 run 27% 980k tok $11.80 avg 3m37s/task
claude-phronix 14 pass 16 fail 0 run 47% 4.4M tok $89.00 avg 22m17s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0908-104954-3730240`
- fleet: `(none)` (hosted)
- skills written: **33**   attempts that loaded one: **40**
- errors: MODEL 75 (25 task-arms), PIPELINE 18 (6 task-arms), TESTBED 0
- the batch job was CANCELLED at 73m, so the run finished but the note block
  never ran — these numbers were added by hand from `top.sh` afterwards.
- MCP server across transcripts: 71 connected, 15 failed. The failures are the
  6 task-arms counted as PIPELINE; a phronix arm whose server did not start is
  a plain agent, so those six are not comparable.

### livai-gpt-5.4 — `claude-0908-120319-1558056`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    31 pass   29 fail    0 run    52% of finished      5.5M tok   $115.91   [##################################################!!!!!!
claude-bare 10 pass 20 fail 0 run 33% 1.1M tok $19.64 avg 7m56s/task
claude-phronix 21 pass 9 fail 0 run 70% 4.4M tok $96.27 avg 39m45s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0908-120319-1558056`
- fleet: `(none)` (hosted)
- skills written: **34**   attempts that loaded one: **37**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0908-120319-1558056 --once`

### livai-gpt-5.5 — `claude-0908-212044-1256290`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    30 pass   30 fail    0 run    50% of finished      2.3M tok    $80.59   [#################################################!!!!!!!
claude-bare 8 pass 22 fail 0 run 27% 615k tok $12.95 avg 5m58s/task
claude-phronix 22 pass 8 fail 0 run 73% 1.7M tok $67.64 avg 40m43s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0908-212044-1256290`
- fleet: `(none)` (hosted)
- skills written: **71**   attempts that loaded one: **32**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0908-212044-1256290 --once`

### livai-gpt-5.6-luna — `claude-0909-012043-3275458`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-luna (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    27 pass   33 fail    0 run    45% of finished      166k tok    $98.98   [############################################!!!!!!!!!!!!
claude-bare 11 pass 19 fail 0 run 37% 46.6k tok $13.21 avg 3m54s/task
claude-phronix 16 pass 14 fail 0 run 53% 119k tok $85.77 avg 29m16s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0909-012043-3275458`
- fleet: `(none)` (hosted)
- skills written: **35**   attempts that loaded one: **38**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0909-012043-3275458 --once`

### livai-gpt-5.6-sol — `claude-0909-044553-3251827`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    46 pass   14 fail    0 run    77% of finished      169k tok    $64.91   [########################################################
claude-bare 20 pass 10 fail 0 run 67% 59.3k tok $17.42 avg 6m06s/task
claude-phronix 26 pass 4 fail 0 run 87% 110k tok $47.49 avg 20m17s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0909-044553-3251827`
- fleet: `(none)` (hosted)
- skills written: **61**   attempts that loaded one: **12**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0909-044553-3251827 --once`

### livai-gpt-5.5-reuse3 — `claude-0909-105949-640638`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    37 pass   23 fail    0 run    62% of finished      2.1M tok    $43.65   [########################################################
claude-bare 12 pass 18 fail 0 run 40% 688k tok $12.97 avg 6m14s/task
claude-phronix 25 pass 5 fail 0 run 83% 1.4M tok $30.68 avg 18m46s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0909-105949-640638`
- fleet: `(none)` (hosted)
- skills written: **151**   attempts that loaded one: **41**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0909-105949-640638 --once`

## The reported matrix

<!-- model-matrix:start -->

| Model | Iter | Mode | Run folder | Bare | Phronix | Status | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gpt-5.4` | -- | fresh | `claude-0908-120319-1558056` | 11/30 | 22/30 | done |  |
| `gpt-5.4` | 1 | fresh | `claude-0909-182247-131224` | 5/30 | 18/30 | timeout | 1 timed out |
| `gpt-5.4` | 1 | reuse | `claude-0909-231949-2043929` | 5/30 | 18/30 | timeout | 1 timed out |
| `gpt-5.4` | 1 | reuse | `claude-0910-093114-2436945` | 8/30 | 27/30 | done |  |
| `gpt-5.4` | 1 | reuse | `claude-0910-151930-1277697` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.4` | 1 | reuse | `claude-0910-181805-325691` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.4` | 2 | reuse | `claude-0909-233332-3035551` | 9/30 | 16/30 | timeout | 13 timed out |
| `gpt-5.4` | 2 | reuse | `claude-0910-110500-870645` | 10/30 | 27/30 | done |  |
| `gpt-5.4` | 2 | reuse | `claude-0910-162557-4012779` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.4` | 2 | reuse | `claude-0910-191133-671811` | 0/30 | -- | timeout | 21 timed out |
| `gpt-5.4` | 3 | fresh | `claude-0910-132919-1166086` | 10/30 | 21/30 | timeout | 8 timed out |
| `gpt-5.4` | 3 | fresh | `claude-0910-172616-1961981` | 0/30 | -- | stopped |  |
| `gpt-5.5` | -- | fresh | `claude-0908-212044-1256290` | 9/30 | 23/30 | done |  |
| `gpt-5.5` | -- | reuse | `claude-0909-092834-1618536` | 12/30 | 26/30 | timeout | 1 timed out |
| `gpt-5.5` | -- | reuse | `claude-0909-105949-640638` | 12/30 | 26/30 | done |  |
| `gpt-5.5` | 1 | fresh | `claude-0909-172255-3798808` | 10/30 | 22/30 | done |  |
| `gpt-5.5` | 1 | fresh | `claude-0910-144431-3952093` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.5` | 1 | reuse | `claude-0909-231939-888128` | 4/30 | 25/30 | timeout | 2 timed out |
| `gpt-5.5` | 1 | reuse | `claude-0910-181435-661926` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.5` | 2 | fresh | `claude-0910-155310-352154` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.5` | 2 | reuse | `claude-0910-001054-3736231` | 10/30 | 13/30 | timeout | 17 timed out |
| `gpt-5.5` | 2 | reuse | `claude-0910-093040-3661779` | 4/30 | 27/30 | done |  |
| `gpt-5.5` | 2 | reuse | `claude-0910-191207-2051825` | 0/30 | -- | timeout | 8 timed out |
| `gpt-5.5` | 3 | fresh | `claude-0910-125509-248863` | 6/30 | 22/30 | timeout | 2 timed out |
| `gpt-5.5` | 4 | reuse | `claude-0910-132903-261665` | 5/30 | 26/30 | timeout | 3 timed out |
| `gpt-5.6-sol` | -- | fresh | `claude-0909-044553-3251827` | 20/30 | 27/30 | done |  |
| `gpt-5.6-sol` | -- | fresh | `claude-0909-130234-1320366` | 18/30 | 25/30 | done |  |
| `gpt-5.6-sol` | -- | reuse | `claude-0909-140710-1565500` | 19/30 | 27/30 | done |  |
| `gpt-5.6-sol` | 1 | fresh | `claude-0909-155241-3703869` | 21/30 | 27/30 | done |  |
| `gpt-5.6-sol` | 1 | fresh | `claude-0910-144432-4016350` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.6-sol` | 1 | reuse | `claude-0909-221630-3551411` | 13/30 | 27/30 | done |  |
| `gpt-5.6-sol` | 1 | reuse | `claude-0910-093112-2250883` | 21/30 | 27/30 | done |  |
| `gpt-5.6-sol` | 1 | reuse | `claude-0910-181436-3769438` | 0/30 | 0/30 | timeout | 30 timed out |
| `gpt-5.6-sol` | 2 | reuse | `claude-0910-001041-2285370` | 22/30 | 21/30 | timeout | 8 timed out |
| `gpt-5.6-sol` | 2 | reuse | `claude-0910-110450-3699565` | 21/30 | 27/30 | done |  |
| `gpt-5.6-sol` | 2 | reuse | `claude-0910-191218-3209404` | 0/30 | -- | timeout | 9 timed out |
| `gpt-5.6-sol` | 3 | fresh | `claude-0910-132956-4012643` | 21/30 | 25/30 | timeout | 7 timed out |
| `gpt-5.6-sol` | 3 | reuse | `claude-0910-015226-2880830` | 22/30 | 26/30 | timeout | 1 timed out |
| `gpt-5.6-sol` | 4 | reuse | `claude-0910-032851-1493617` | 20/30 | 4/30 | timeout | 26 timed out |

Reuse runs started before the capability dispatcher landed (`547269e`, 2026-09-09 09:24) are omitted: until then every learned capability was its own MCP tool, so a reuse run saw ~1150 of them and a fresh run saw almost none. That handicapped one arm of each pair and not the other. Fresh runs from before it are kept -- their store was empty, so there was nothing to bloat the tool list with.

<!-- model-matrix:end -->

### m2-5.6-sol-reuse-1 — `claude-0909-221630-3551411`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL  25 task(s)    22 pass    3 fail    0 run    88% of finished     98.7k tok    $23.68   [########################################################
claude-phronix 22 pass 3 fail 0 run 88% 98.7k tok $23.68 avg 10m50s/task 5 queued
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0909-221630-3551411`
- fleet: `(none)` (hosted)
- skills written: **240**   attempts that loaded one: **30**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0909-221630-3551411 --once`

### m2-5.4-reuse-2 — `claude-0910-001008-3141358`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL   0 task(s)     0 pass    0 fail    0 run      - of finished         0 tok         -   [........................................................

```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-001008-3141358`
- fleet: `(none)` (hosted)
- skills written: **0**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-001008-3141358 --once`

### m2-5.6-sol-reuse-2 — `claude-0910-001041-2285370`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL   0 task(s)     0 pass    0 fail    0 run      - of finished         0 tok         -   [........................................................

```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-001041-2285370`
- fleet: `(none)` (hosted)
- skills written: **221**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-001041-2285370 --once`

### m2-5.5-reuse-2 — `claude-0910-001054-3736231`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL   0 task(s)     0 pass    0 fail    0 run      - of finished         0 tok         -   [........................................................

```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-001054-3736231`
- fleet: `(none)` (hosted)
- skills written: **48**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-001054-3736231 --once`

### m2-5.6-sol-reuse-4 — `claude-0910-032851-1493617`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL   0 task(s)     0 pass    0 fail    0 run      - of finished         0 tok         -   [........................................................

```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-032851-1493617`
- fleet: `(none)` (hosted)
- skills written: **71**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-032851-1493617 --once`

### m3-5.5-reuse-1 — `claude-0910-085640-456792`  (30 task(s), 8 node(s))

- model: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-085640-456`

```
TOTAL   0 task(s)     0 pass    0 fail    0 run      - of finished         0 tok         -   [........................................................

```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-085640-456792`
- fleet: `(none)` (hosted)
- skills written: **0**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-085640-456792 --once`

### m3-5.4-reuse-1 — `claude-0910-093114-2436945`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL   7 task(s)     3 pass    4 fail    0 run    43% of finished      892k tok    $14.46   [##########################################!!!!!!!!!!!!!!
claude-phronix 3 pass 4 fail 0 run 43% 892k tok $14.46 avg 20m44s/task 23 queued
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-093114-2436945`
- fleet: `(none)` (hosted)
- skills written: **240**   attempts that loaded one: **13**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-093114-2436945 --once`

### m3-sol-reuse-1 — `claude-0910-093112-2250883`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL  11 task(s)     7 pass    4 fail    0 run    64% of finished     71.8k tok    $17.59   [########################################################
claude-phronix 7 pass 4 fail 0 run 64% 71.8k tok $17.59 avg 15m34s/task 19 queued
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-093112-2250883`
- fleet: `(none)` (hosted)
- skills written: **240**   attempts that loaded one: **17**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-093112-2250883 --once`

### m3-5.5-reuse-2 — `claude-0910-093040-3661779`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    30 pass   30 fail    0 run    50% of finished      1.7M tok    $34.17   [#################################################!!!!!!!
claude-bare 4 pass 26 fail 0 run 13% 483k tok $7.00 avg 2m05s/task
claude-phronix 26 pass 4 fail 0 run 87% 1.2M tok $27.17 avg 12m20s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-093040-3661779`
- fleet: `(none)` (hosted)
- skills written: **240**   attempts that loaded one: **36**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-093040-3661779 --once`

### m3-5.4-reuse-2 — `claude-0910-110500-870645`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL  47 task(s)    31 pass   16 fail    0 run    66% of finished      3.3M tok    $44.82   [########################################################
claude-bare 5 pass 12 fail 0 run 29% 1.0M tok $12.12 avg 6m13s/task 13 queued
claude-phronix 26 pass 4 fail 0 run 87% 2.3M tok $32.70 avg 14m54s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-110500-870645`
- fleet: `(none)` (hosted)
- skills written: **240**   attempts that loaded one: **40**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-110500-870645 --once`

### m3-sol-reuse-2 — `claude-0910-110450-3699565`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL  60 task(s)    47 pass   13 fail    0 run    78% of finished      190k tok    $47.88   [########################################################
claude-bare 21 pass 9 fail 0 run 70% 88.7k tok $12.85 avg 4m00s/task
claude-phronix 26 pass 4 fail 0 run 87% 101k tok $35.03 avg 13m36s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-110450-3699565`
- fleet: `(none)` (hosted)
- skills written: **240**   attempts that loaded one: **38**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-110450-3699565 --once`

### m3-5.5-fresh-3 — `claude-0910-125509-248863`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL   2 task(s)     0 pass    0 fail    2 run      - of finished      1.5M tok         -   [........................................................
claude-phronix 0 pass 0 fail 2 run - 1.5M tok - avg 0s/task 28 queued
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-125509-248863`
- fleet: `(none)` (hosted)
- skills written: **1**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-125509-248863 --once`

### m3-5.4-fresh-3 — `claude-0910-132919-1166086`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)    20 pass    3 fail    7 run    87% of finished     12.6M tok    $45.16   [########################################################
claude-phronix 20 pass 3 fail 7 run 87% 12.6M tok $45.16 avg 22m45s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-132919-1166086`
- fleet: `(none)` (hosted)
- skills written: **34**   attempts that loaded one: **25**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-132919-1166086 --once`

### m3-sol-fresh-3 — `claude-0910-142831-38356`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL  60 task(s)     0 pass   30 fail   30 run     0% of finished         0 tok         -   [!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!.......
claude-bare 0 pass 30 fail 0 run 0% 0 tok - avg 6m51s/task
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-142831-38356`
- fleet: `(none)` (hosted)
- skills written: **0**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-142831-38356 --once`

### m4-sol-fresh-1 — `claude-0910-144432-4016350`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-144432-4016350`
- fleet: `(none)` (hosted)
- skills written: **0**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-144432-4016350 --once`

### m4-5.5-fresh-1 — `claude-0910-144431-3952093`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-144431-3952093`
- fleet: `(none)` (hosted)
- skills written: **0**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-144431-3952093 --once`

### m3-5.5-reuse-4 — `claude-0910-145849-507494`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-145849-507494`
- fleet: `(none)` (hosted)
- skills written: **298**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-145849-507494 --once`

### m4-5.4-reuse-1 — `claude-0910-151930-1277697`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-151930-1277697`
- fleet: `(none)` (hosted)
- skills written: **298**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-151930-1277697 --once`

### m4-5.5-fresh-2 — `claude-0910-155310-352154`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-155310-352154`
- fleet: `(none)` (hosted)
- skills written: **0**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-155310-352154 --once`

### m4-5.4-reuse-2 — `claude-0910-162557-4012779`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-162557-4012779`
- fleet: `(none)` (hosted)
- skills written: **298**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-162557-4012779 --once`

### m5-sol-reuse-1 — `claude-0910-181436-3769438`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.6-sol (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-181436-3769438`
- fleet: `(none)` (hosted)
- skills written: **298**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-181436-3769438 --once`

### m5-5.5-reuse-1 — `claude-0910-181435-661926`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.5 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-181435-661926`
- fleet: `(none)` (hosted)
- skills written: **298**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-181435-661926 --once`

### m5-5.4-reuse-1 — `claude-0910-181805-325691`  (30 task(s), 8 node(s))

- model: `svc-dldl-gpt-5.4 (livai-api.llnl.gov)`

```
TOTAL  30 task(s)     0 pass    0 fail   30 run      - of finished         0 tok         -   [........................................................
claude-phronix 0 pass 0 fail 30 run - 0 tok - avg 0s/task
```

- run: `/p/lustre3/haridev/phronix-bench/runs/claude-0910-181805-325691`
- fleet: `(none)` (hosted)
- skills written: **298**   attempts that loaded one: **0**
- `scripts/top.sh /p/lustre3/haridev/phronix-bench/runs/claude-0910-181805-325691 --once`
