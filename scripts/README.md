# Running the benchmark

The benchmark asks one question: **does phronix's research and learning make an
agent solve more SWE-bench tasks than the same agent without it?**

Every run is a pair of arms — `<harness>-bare` and `<harness>-phronix` — on the
same tasks, in the same containers, with the same model. The only difference is
phronix. Both arms run concurrently; tasks within an arm stay in a fixed order,
because the learning arm's task N is supposed to benefit from tasks 1..N-1 and
that only means something if every arm saw the same sequence.

Scripts live here, in the repository, so they are versioned. **Data never does**
— run directories, container images and the dataset live on the PFS at
`/p/lustre5/haridev/phronix-bench`, which is where the space is.

## Quick start

`swe-agent-bench.sh` is the entry point for anything involving the local GPU
cluster; `run-benchmark.sh` underneath it is the lower-level form.

```bash
scripts/swe-agent-bench.sh                        # 6 tasks, both arms, local fleet
scripts/swe-agent-bench.sh --dry-run              # show what would run, start nothing
scripts/swe-agent-bench.sh --list-models          # what this backend serves
scripts/status.sh                                 # watch it
scripts/research-progress.sh                      # is research producing candidates?
scripts/try2.sh                                   # did the revision pass turn try 1's failures into try 2 passes?
ssh <node> bash scripts/kill.sh                   # stop it
```

**`--dry-run` matters.** Without it the script stops any benchmark already
running before starting its own, so "just checking the banner" ends a run that
was twenty minutes in. Use `--keep-running` to launch a second benchmark
alongside a first.

## Choosing a harness and a model

The **harness** is the agent; the **backend** is where the model lives. They
vary independently:

```bash
# opencode against the local GPU cluster (the default)
scripts/swe-agent-bench.sh

# opencode against the site gateway
scripts/swe-agent-bench.sh --backend livai --model claude-sonnet-4.5

# Claude Code on Sonnet 5, hosted
scripts/swe-agent-bench.sh --harness claude --backend anthropic

# Claude Code against the local cluster
scripts/swe-agent-bench.sh --harness claude --backend cluster
```

| backend | endpoint | credential | runs where |
|---|---|---|---|
| `cluster` | the fleet's own `cluster.json` | in that file | **on a compute node** |
| `livai` | `https://livai-api.llnl.gov/v1` | `OPENAI_API_KEY` | login node |
| `anthropic` | Anthropic directly | Claude Code's own auth | login node |

`--harness claude --backend cluster` works: the LiteLLM gateway serves
`/v1/messages` in Anthropic shape, so Claude Code drives the local models.
Verified end to end — `rc=0` running `gpt-oss-120b` through the gateway. Claude
Code will warn that claude.ai connectors are disabled because an auth source is
set; that is the intended effect, not a fault.

A `cluster` run must execute on a compute node: the gateway refuses connections
from the login node and answers in 7 ms from a compute node. The script arranges
that over ssh — not `flux run`, whose cgroup starves opencode into exiting 245
with no output.

**Numbers from different harnesses are not comparable** — different system
prompts, different event streams. Bare-versus-phronix *within* one harness and
one backend is the comparison the benchmark exists for.

## Sizing a run to the fleet

A task unit — one task in one arm — occupies about **half a slot**, because it
spends much of its life checking out repos, running tests and evaluating patches
rather than talking to the model. Measured against a live 12-unit run: 2, 9, 8,
7, 6 requests in flight.

So filling a fleet takes roughly `capacity / (0.53 x arms)` concurrent tasks —
about **120 tasks for a 128-slot fleet** with two arms. Six tasks use ~5% of it,
which is correct for six tasks: spare capacity is only waste when work is
waiting on it, and `0 deferred` says nothing is.

```bash
# let the script size the run to the fleet
scripts/swe-agent-bench.sh --fill-fleet --tasks lite-300.txt \
  --nodes tuolumne1183,tuolumne1207,tuolumne1239,tuolumne1264

# try the top 3 researched plans in parallel, keep whichever gets furthest
scripts/swe-agent-bench.sh --candidates 3
```

Every run prints its expected utilisation:

```
fleet    : 128 slots, this run will use ~5%  (--fill-fleet would raise this; 121 concurrent tasks fills it)
```

`--fill-fleet` is capped by `MAX_TASKS_PER_NODE` (16): a task is a container,
and containers cost cores plus about two kernel session keys against a per-user
quota of 200. That limit binds long before the GPUs do.

## The full list, in budgeted groups

300 tasks is roughly **$700–870 and 30+ hours** on the hosted models, which is
more than most allocations hold and more than anyone wants to discover from an
invoice. `run-group.sh` runs one slice at a time, sized so a slice fits a short
allocation.

```bash
scripts/run-group.sh 1 <alloc>            # group 1, hosted Sonnet
scripts/run-group.sh 4 <alloc> --spend 60 # a smaller ceiling
scripts/run-group.sh 3 <alloc> --local    # the local GPU fleet instead
scripts/run-group.sh 2 ""                 # no allocation: containers run here
```

Defaults: **30 tasks, hosted Claude Sonnet, 5 at a time, $100 ceiling** — a few
hours per group. Five rather than thirty because the hosted model is the shared
resource: a task's own turns are serialised anyway, so past a point more
concurrency only puts every stage behind rate limits. At the measured **$2.34
and 47 minutes** per task, a group lands near $70, inside the ceiling.

`--local` serves the model from the GPU fleet instead and drops the ceiling — on
your own GPUs the dollar figure is notional, and a cap there would stop a run
over a number that means nothing.

The ten group files are contiguous slices of `lite-300.txt`:

```
/p/lustre5/haridev/phronix-bench/groups/group-01.txt … group-10.txt
```

### The allocation, and what it is for

`<alloc>` must be a **running** Flux job — `flux jobs -a` and look for state
`R`. `S` is scheduled and has not started; `TO` has timed out. The script checks
this and names the state, because `flux proxy` against anything else fails with
*"Unable to resolve &lt;id&gt; to a URI"*, which reads like a typo rather than an
expired reservation. Measured the hard way: a run lost its fleet and its
container hosts mid-flight when the allocation hit its wall.

The allocation is for the evaluation **containers**, not for the model:

* **hosted** (default) — the model is Anthropic's, so the nodes only run
  containers. A small allocation is enough; five concurrent tasks need ten.
* **`--local`** — the model comes from the GPU fleet in the same allocation, so
  the container hosts are the allocation **minus** the nodes the fleet is on.
  See `tuolumne-llm/README.md` for deploying the fleet on part of an allocation.

Container hosts are derived, never hardcoded: the allocation's hostlist, minus
whatever the fleet's per-GPU records say is serving, minus anything that refuses
ssh. On one 16-node allocation that correctly excluded the 6 serving nodes and 2
that were unreachable, leaving exactly the 8 usable ones — where reading the
*intended* host list would have placed containers on two nodes that never served
and skipped two that did.

Each group is **independent** — `--fresh --no-carry` gives it its own store, so
groups can run in any order, on any allocation, and a group that dies takes
nothing with it. Within a group the learning arm still benefits from its own
earlier tasks, and that is what these runs measure; cross-group reuse is not
measured, because there is none.

Every researched plan is built, attempted and evaluated separately — that is the
default now. Research explores several ideas and writes each up; testing only the
top-ranked one pays for the rest and never tries them, and never checks the
ranking against the task's own tests. `reconcile_trials` then folds the results
into one skill: what several passing candidates agree on becomes the fix, and
each failure becomes a named lesson.

### The spend ceiling

```bash
scripts/run-benchmark.sh --max-spend 25          # on any run, not just groups
```

Checked at the door of **every task**, so an overrun is bounded by one task
(~$2.34) rather than by the whole queue — a ceiling checked after the work is a
report, not a control. Skipped tasks are recorded with `stopped_early`, so the
results say what was cut instead of silently reporting a short run:

```
[ 47] pallets__flask-5063   SKIPPED — spend ceiling reached: $25.11 of $25.00
```

It counts `cost_total_usd` — solve **and** research **and** learning. Research is
the larger half: $0.70 of that $2.34 task was the solve agent, the rest was
research, so a ceiling reading `cost_usd` overshoots about threefold.

### Grouping the results

```bash
scripts/group-batches.sh <run-dir> <run-dir> ...   # or a state dir
```

Reports several runs as one: per-arm pass/fail, the real cost, and a per-batch
line showing how the rate moved from the first slice to the last.

### Hourly pacing

```bash
scripts/hourly-batches.sh --tasks lite-300.txt --spend 25 --every 3600
```

$25 an hour, continuing where the last batch stopped, grouping at the end. The
pacing is measured from each batch's **start**, so a batch that overruns does not
push every later one later.

## Lower-level

```bash
scripts/run-benchmark.sh                     # claude, 6 tasks, fresh
scripts/status.sh                            # watch it (newest run, in detail)
scripts/running.sh                           # what is it costing right now
scripts/kill.sh                              # stop everything
```

Measure the cost on one task before committing to six:

```bash
scripts/run-benchmark.sh --tasks pilot-1.txt
```

## The scripts

| script | what it is for |
| --- | --- |
| `run-benchmark.sh` | Launch a run. Stops any previous one first |
| `status.sh` | The newest run, in detail. `--all` for every run, `--list N` for names, or a run name |
| `running.sh` | Is anything spending money right now, and what has it cost |
| `kill.sh` | Stop every benchmark process, on this node and others. `--dry-run` previews |
| `launch-when-ready.sh` | Wait for the model endpoint to accept requests, then launch |
| `run-group.sh` | One group of the 300-task list: 34 tasks, $100, ~5 hours. Takes a group index and an allocation |
| `group-batches.sh` | Report several runs as one — totals, cost, and the per-batch trend |
| `hourly-batches.sh` | Work through a long list at a fixed spend per hour |

## Check the environment before spending anything

```bash
scripts/baseline-check.sh                       # all 9 tasks, unpatched
scripts/baseline-check.sh --tasks fast-6.txt --node tuolumne1075
```

Runs every task's tests with **no patch and no agent** — one container each, no
tokens — and answers the question a run cannot: *can this instance be judged at
all?* Three faults it catches, all measured here:

* **no runner in the image.** sympy's testbed env ships without pytest, so every
  test scored not-passed. The verdict was indistinguishable from a
  catastrophically wrong patch, three retries were spent on it, and the baseline
  cached 30 tests as already broken. pytest is now installed into the
  *container* when missing — never the host venv, because the instance pins the
  dependency versions its tests are written against.
* **ids that cannot match.** SWE-bench stores sympy's ids as bare function
  names; pytest prints full node ids. Every sympy instance scored 0 of 30 on
  tests that had just printed PASSED.
* **fixtures handed to pytest as tests.** flask-4992's test patch adds
  `tests/static/config.toml`; pytest given a data file collects nothing at all.

A run that cannot execute its tests produces numbers that look like results, so
this is cheap insurance. Exit status is non-zero when any instance is unusable.

## Options that change what is measured

`run-benchmark.sh` takes these; the rest are in `--help`.

**`--harness claude|opencode`** — which agent runs the tasks. Both drive the
same phronix, so a phronix result means the same thing either way. Numbers are
**not** comparable *across* harnesses: different system prompt, different model
routing. Bare-versus-phronix *within* one run is the comparison that holds, and
it is the one the benchmark is for.

**`--fresh` (default) / `--reuse`** — `--fresh` ignores skills and research from
earlier runs and starts from the bundled framework alone. That is what makes a
result an evaluation of the approach rather than of an accumulated store. What a
fresh run finds is still synced back afterwards, so nothing is wasted.
`--reuse` is the system working as intended — research is expensive and the
point of keeping it is not paying twice — but a reusing run cannot answer "does
this approach work from scratch".

**`--research-on-retry`** — withhold research from the first attempt, so it runs
only after that attempt has failed. Try 1 is then the same first move the
baseline makes, and what gets measured is what research *recovers* rather than
what it adds up front. A narrower claim, and an easier one to defend.

**`--tries N`** — the ceiling. Retries stop early anyway when two consecutive
attempts repeat a patch, because a task that cannot change its answer is only
spending tokens.

## Reading the result

`status.sh` prints one line per task:

```text
PASS  pylint-dev__pylint-7080   steps=43 tok= 106,461 time=133s  research tok=104,239 time=963s
      research: survey 80s | plan 133s | aspect 3x max 404s !1cut | collect 72s | ...
```

Task tokens and time are separate from research tokens and time, because a first
attempt looks expensive when research runs and one combined number cannot say
whether that was the agent working on the task or the framework working out how
to. `tries=` appears only when it actually retried. Parallel stages report
**max**, not sum — three concurrent aspects cost the task their slowest member,
and summing them overstates research against solve on every line. `!Ncut` marks
stages that hit their budget: those findings are partial and were paid for in
full.

## Stopping safely

`kill.sh` never matches on the binary name. An interactive Claude Code session
uses the same `claude` executable the benchmark spawns, so `pkill -f claude`
would kill the session issuing the kill. Agents are matched on the **benchmark
run path**, which appears in every spawned agent's argv and in nothing else.

It also reads `logs/`, where `run-benchmark.sh` records the pid and host of
every run it starts. The process table is node-local — a run launched on the
login node is invisible from a compute node, so `pgrep` reports "not running"
for a runaway that is still spending. The record survives the allocation.

Finally it verifies rather than assumes: a kill that silently failed is worse
than no kill at all, because it reads as "stopped" while the account keeps being
charged.

## When a run produces nothing

Attempts reporting `0 steps, 0 tok` almost always mean the agent never started,
not that it ran and did nothing. Two causes have actually occurred:

* **The model endpoint refused every request.** The shared LiVAI key hit its
  spend cap and returned 429 to everything. `preflight` now checks the endpoint
  before a run starts and prints the provider's own message.
* **A phronix research pass never ran.** That is fatal and stops the run: an arm
  whose research never starts degrades into a plain agent with extra
  scaffolding, and every number it produces would be attributed to phronix.
