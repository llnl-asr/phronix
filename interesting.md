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

