---
name: software_slurm_alloc
description: Slurm allocation and job-step workflow (counterpart of software_flux's flux-alloc): discover partitions and per-partition MaxNodes, read sbatch --test-only start estimates, allocate with salloc/sbatch, run and co-schedule steps with srun --overlap --nodelist, keep helper daemons alive as long-lived steps, pin GPUs (--gres vs --gpus-per-task), avoid env-propagation traps, cancel only your job, make long sweeps resumable, decode squeue reasons, and verify scale with sacct. Load before any allocation, launch or multi-step run on a Slurm system, or on `Invalid generic resource (gres) specification` / `Requested node configuration is not available` for multi-node jobs, `Nodes_required_for_job_are_DOWN,_DRAINED_or_reserved_for_jobs_in_higher_priority_partitions`, a second srun step that waits forever, a daemon step that exits 0 with empty/0-byte output, or `cudaErrorInvalidDevice` under --gpus-per-task.
---
Cross-references: [[software_flux]] [[system_matrix]] [[system_dane]] [[tools_dftracer]] [[ropt_alloc]] [[dftracer_pipeline]] [[capability_builder]]

# software_slurm_alloc

Converted from dftracer-agents skill `slurm-alloc`. Tools: `software_slurm_alloc_recipe` (predictor) and `software_slurm_alloc_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Policy is identical to software_flux (flux-alloc): ASK the user before allocating, prefer an existing standing allocation and check its remaining time (`squeue -h -j <id> -o %L` / `%e`), never tear down an allocation, verify scale before crediting a delta, replicate and report percentiles.
- MANDATORY: check per-partition MaxNodes (`scontrol show partition <p> | tr ' ' '\n' | grep -E 'MaxNodes|MaxTime|TotalNodes|State'`) before planning any multi-node study; a partition can cap a single job at one node, and the rejection messages do not mention MaxNodes.
- Partitions can share nodes with a priority order: compare `sinfo -h -p <p> -o %N` node lists before declaring a partition free.
- Choose the job shape from `sbatch --test-only` (creates no job, returns the backfill start estimate); measure, don't reason - start time may depend on node count and not walltime. Prefer exactly the nodes the job needs.
- Pace polling off `squeue -j <id> -o "%.10i %.8T %.20S %R"` (START_TIME is the moving estimate), not a fixed interval.
- Never block the foreground on a long job: run_in_background, or non-blocking `sbatch --parsable` and poll. `sbatch --wait` only inside a background driver.
- Run inside an allocation with `srun --jobid=<ALLOC> --overlap -N<n> -n<tasks> <cmd>`. `--overlap` is MANDATORY for co-scheduled steps (helper alongside app), otherwise the second step waits forever.
- Pin co-scheduled steps to the same nodes with `--nodelist=<slice>` (expand with `scontrol show hostnames $SLURM_JOB_NODELIST`); this also yields A/N disjoint concurrent slots.
- A daemon's lifetime is tied to its STEP: run it as a long-lived step that starts it, waits for a stop flag, stops it, then waits (e.g. up to 60 s) until its output is non-empty, because many daemons flush asynchronously after stop.
- `--gres=gpu:4` exposes all 4 devices to each task; `--gpus-per-task=1` exposes one, renumbered to 0 - apps doing cudaSetDevice(SLURM_LOCALID % n) break (cudaErrorInvalidDevice). Verify empirically before a sweep.
- One dead rank must not hang the sweep: wrap the app step in `timeout $APP_TIMEOUT srun ... --kill-on-bad-exit=1`; rc 124 = timeout.
- Env propagation: a trailing `\` followed by a comment line ends the command (prefix assignments silently lost) - use `( export FOO=1; srun ... )`. module purge/load inside `bash -lc` can roll back (login profile): put module loads in a sourced script and verify with `which`. Sourced env scripts must end with `true` (set -e callers).
- Cancel only the job id you submitted (`scancel <JOBID>`, or scoped `scancel --state=PENDING --name=<name> -u $USER`); never `scancel -u $USER`, never a job you did not submit, never the allocation.
- Do not `pkill -f <pattern>` when the pattern can match your own shell's command line; filter by pid and /proc/<pid>/cmdline.
- Long sweeps: append one line per VERIFIED unit to a state file and skip listed units on restart; checkpoint only after verifying artifacts on disk (count, non-empty), never on rc; keep a deadline guard from `squeue -h -j $SLURM_JOB_ID -o %e`; submit independent node scales concurrently instead of a --wait chain.
- Measurement policy (from flux-alloc): runs long enough that startup noise does not dominate; >= 5 replicates, escalate on high CV, report p50/p95/min/max; verify scale and completion with sacct / scontrol show job - TIMEOUT, CANCELLED, NODE_FAIL or non-zero ExitCode disqualifies a run.

## Constraints
- Mechanics differ from Flux; policy does not. Flux-side details live in software_flux.
- Measured shapes and partition limits are per cluster (e.g. a matrix-class pdebug is MaxNodes=1 with 2 nodes total; see system_matrix).

## Corner cases
### `srun -p pdebug -N2` -> `Unable to allocate resources: Invalid generic resource (gres) specification`
Cause: partition MaxNodes=1, not a GRES problem. Fix: check scontrol show partition MaxNodes; use a partition that allows the node count.

### `sbatch --test-only -N2` -> `allocation failure: Requested node configuration is not available`
Cause: per-partition MaxNodes below the request. Fix: as above.

### Pending `Reason=Nodes_required_for_job_are_DOWN,_DRAINED_or_reserved_for_jobs_in_higher_priority_partitions`
Cause: a higher-priority partition sharing the same nodes holds them; not broken hardware. Fix: compare sinfo node lists; pick another partition or wait.

### Second srun step inside an allocation never starts
Cause: missing --overlap. Fix: add --overlap to every co-scheduled step.

### Per-node daemon output empty although the app ran
Cause: steps landed on different node subsets. Fix: --nodelist=<same slice> on both steps.

### Daemon step exits 0, pid file written, output 0 bytes / truncated
Cause: daemon reaped with its step, or mid async flush after stop. Fix: long-lived step that waits for the stop flag and for non-empty output.

### `cudaErrorInvalidDevice` on rank 1
Cause: --gpus-per-task renumbers the single visible device to 0 while the app picks SLURM_LOCALID % n. Fix: --gres=gpu:4, verify CUDA_VISIBLE_DEVICES per task.

### App ran without the env vars set on the previous line
Cause: trailing backslash followed by a comment line. Fix: ( export ...; srun ... ).

### Caller under set -e dies silently after sourcing env script
Cause: trailing `[ -d $V ] && source ...` returned 1. Fix: end the file with `true`.

### Cleanup command killed itself
Cause: pkill -f pattern matched the invoking shell. Fix: filter by pid via /proc/<pid>/cmdline.

### Pending reasons Priority / Resources / QOSMaxJobsPerUserLimit / AssocMaxJobsLimit / ReqNodeNotAvail
Priority: higher-priority jobs ahead (normal); Resources: waiting for nodes; QOS/Assoc limits: too many jobs queued; ReqNodeNotAvail: often a DOWN/DRAINED node in an explicit --nodelist.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_slurm_alloc_recipe` renders the recipe; validator `software_slurm_alloc_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_scancel_all_user_jobs` fails: scancel <JOBID> you submitted, or scope with --state=PENDING --name=<jobname> -u $USER. Then render with `software_slurm_alloc_recipe` and validate again.
- `overlap_for_steps_in_allocation` fails: Add --overlap to srun --jobid=<alloc> steps. Then render with `software_slurm_alloc_recipe` and validate again.
- `no_pkill_f` fails: Find pids and check /proc/<pid>/cmdline, or use a pattern that cannot match the invoking command. Then render with `software_slurm_alloc_recipe` and validate again.
- `check_maxnodes_before_multinode` fails: Run scontrol show partition <p> (MaxNodes) and/or sbatch --test-only for the shape first. Then render with `software_slurm_alloc_recipe` and validate again.
- `kill_on_bad_exit_for_gpu_app` fails: timeout $APP_TIMEOUT srun ... --kill-on-bad-exit=1 ... Then render with `software_slurm_alloc_recipe` and validate again.
- `no_backslash_then_comment` fails: Use ( export FOO=1 BAR=2; srun ... ) or remove the comment line from the continuation. Then render with `software_slurm_alloc_recipe` and validate again.
- `no_module_in_bash_lc` fails: Put module loads in a sourced script and verify with which. Then render with `software_slurm_alloc_recipe` and validate again.

## Self-heal
- If a multi-node request is rejected with a GRES or node-configuration error, re-check MaxNodes and shared node lists before changing the GRES request.
- If a run returns rc=0 but artifacts are missing, re-check --overlap, --nodelist, daemon step lifetime and env propagation before re-running.

## Self-learn
- Record each cluster's measured partition limits and --test-only shape/start tables in its system_<machine> capability.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_slurm_alloc via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated) Long-lived daemon step: srun -N$N -n$N -c1 --nodelist=$SLICE --overlap bash -c 'start; wait for STOP_FLAG; stop; wait up to 60 s for non-empty output' & ; app in a separate --overlap step on the same slice; touch STOP_FLAG; wait.
- (undated) Shape selection: sbatch --test-only for each candidate node count; on one measured cluster 2 nodes started same day at any walltime while 4/8 nodes waited +13/+14 h.

## Source: dftracer-agents `slurm-alloc` (verbatim, headings demoted)
_Original description:_ > Slurm job allocation workflow — discover partitions and their per-partition limits, read the scheduler's own start estimates instead of guessing, allocate with salloc/sbatch, run and CO-SCHEDULE steps with srun (--overlap, --nodelist), pin GPUs correctly, keep a helper daemon alive across steps, and cancel safely. The Slurm counterpart of [[flux-alloc]]. Load this skill before any allocation, job launch, or multi-step run on a Slurm system.

Cross-references: [[flux-alloc]] [[system-matrix]] [[system-dane]] [[tools-dftracer]] [[dftracer-planning]]

This is the Slurm sibling of [[flux-alloc]]. The **policy** rules are identical on
both schedulers — ask before allocating, never tear down an allocation, verify
scale before crediting a delta, replicate and report percentiles. The
**mechanics** are entirely different. Where a rule is stated in [[flux-alloc]]
and unchanged here, it is referenced rather than repeated.

---

#### Step 1 — Discover partitions and their limits

Never assume a partition can run the job shape you have in mind. On Slurm the
binding constraint is usually a **per-partition `MaxNodes`**, which is invisible
in `sinfo`'s default output:

```bash
sinfo -o "%20P %5a %10l %6D %10T %N"            # partitions, avail, timelimit, nodes, state
scontrol show partition <name> | tr ' ' '\n' | grep -E "MaxNodes|MaxTime|TotalNodes|State"
scontrol show node <node>    | head -20          # Gres=gpu:N, CPUTot, Sockets, RealMemory
```

> **MANDATORY: check `MaxNodes` before planning any multi-node study.** A
> partition can have plenty of nodes and still cap a *single job* at one node.
> When it does, the rejection messages do **not** mention MaxNodes and are easy
> to misread as a resource or GRES problem:
>
> ```
> srun -p pdebug -N2 ...   -> "Unable to allocate resources: Invalid generic resource (gres) specification"
> sbatch --test-only -N2   -> "allocation failure: Requested node configuration is not available"
> ```
>
> Measured on a matrix-class system: `pdebug` is `MaxNodes=1` with 2 nodes
> total. A 1/2/4/8-node scaling ladder simply cannot run there, no matter how
> idle it looks. See [[system-matrix]].

##### Partitions can SHARE nodes, with a priority order between them

Two partitions may be different views of overlapping hardware:

```bash
sinfo -h -p pci    -o %N     # matrix[11-30]
sinfo -h -p pbatch -o %N     # matrix[11-30,37-51]     <- superset
```

The lower-priority partition then inherits the higher one's backlog, and its
pending jobs report:

```
Reason=Nodes_required_for_job_are_DOWN,_DRAINED_or_reserved_for_jobs_in_higher_priority_partitions
```

That message does **not** mean the nodes are broken. It means a higher-priority
partition is holding hardware the two share. Always compare node lists before
declaring one partition "free".

---

#### Step 2 — Let the scheduler tell you when it would start

`sbatch --test-only` creates **no job** and returns the backfill estimate. This
is the Slurm analogue of flux's `annotations.sched.t_estimate`, and it is the
only honest way to choose a job shape:

```bash
sbatch -p <part> -N<n> -t <min> --gres=gpu:4 --test-only --wrap="hostname"
# -> "Job N to start at 2026-08-27T19:08:52 a using ... on nodes ... in partition ..."
```

> **MEASURE the shape, don't reason about it.** On one measured cluster the
> start time depended almost entirely on **node count** and **not at all** on
> walltime:
>
> | request | est. start |
> |---|---|
> | 2 nodes, any of 60/120/240/720 min | today 19:08 |
> | 4 nodes, any walltime | +13 h |
> | 8 nodes, any walltime | +14 h |
>
> Asking for a bigger allocation to get more concurrency slots can cost a
> half-day of queue wait. Prefer **exactly the nodes the job needs** when a
> single slot still finishes the work inside the time limit — starting sooner
> usually beats finishing faster.

Pace polling off the estimate rather than a fixed interval (same rule as
[[flux-alloc]]):

```bash
squeue -j <jobid> -o "%.10i %.8T %.20S %R"     # START_TIME is the moving estimate
squeue -p <part> -h -t PENDING | wc -l          # depth of the backlog
```

---

#### Step 3 — Allocate

```bash
# Interactive allocation, no shell attached (returns once nodes are ready)
salloc -p <part> -N<n> -t <min> --gres=gpu:4 --no-shell

# Batch, non-blocking: returns a JOBID immediately, work runs when scheduled
sbatch --parsable -p <part> -N<n> -t <min> --gres=gpu:4 \
       --job-name=<name> -o <logdir>/%x_%j.log --wrap "<script> <args>"

# Batch, blocking: waits for the job to finish (use only in a background driver)
sbatch --wait -p <part> -N<n> -t <min> --wrap "<script>"
```

**Allocations: ASK the user first** — identical rule and rationale to
[[flux-alloc]]. Prefer an existing standing allocation if the user has one, and
check its remaining time before starting work that could outlive it:

```bash
squeue -h -j <jobid> -o "%L"      # time LEFT
squeue -h -j <jobid> -o "%e"      # end time
```

**Never block the foreground on a long job.** The Bash tool caps out well below
a real run. Use `run_in_background: true`, or `sbatch` (non-blocking) and poll.

---

#### Step 4 — Run inside an allocation

```bash
srun --jobid=<ALLOC_JOBID> --overlap -N<n> -n<tasks> <cmd>
```

Useful environment inside a job:

| variable | meaning |
|---|---|
| `SLURM_JOB_ID` | the allocation's id |
| `SLURM_JOB_NODELIST` | compressed nodelist — expand with `scontrol show hostnames` |
| `SLURM_LOCALID` | rank index **within the node** (what most apps use to pick a GPU) |
| `SLURM_PROCID` | global rank |

```bash
mapfile -t HOSTS < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
```

##### `--overlap` is MANDATORY for co-scheduled steps

By default Slurm will not place a second step on resources already held by a
running step. Any pattern where a helper (telemetry daemon, sampler, monitor)
runs **alongside** the application on the same nodes needs `--overlap` on the
steps that share nodes. Without it the second step simply waits forever.

##### Pin co-scheduled steps to the SAME nodes with `--nodelist`

The Slurm analogue of flux's `--requires=host:`. In an allocation larger than
the job, separate steps otherwise land on **different node subsets**, so a
per-node daemon profiles nodes the application never ran on and its output comes
back empty:

```bash
SLICE=$(IFS=,; echo "${HOSTS[*]:$((s*N)):$N}")
srun -N$N -n$N --nodelist="$SLICE" --overlap -c1 <daemon>
srun -N$N -n$((N*P)) --nodelist="$SLICE" --overlap --gres=gpu:4 <app>
```

This also gives disjoint **slots**: an allocation of `A` nodes runs `A/N`
independent `N`-node runs concurrently on non-overlapping slices.

---

#### A background daemon's lifetime is tied to its STEP, not the allocation

This is the single most common way a helper daemon "runs" and produces nothing.

A process started by `srun … daemon start` is a child of that **job step**.
`start` typically daemonises and returns, the step ends — and Slurm reaps the
daemon with the step. Everything looks fine: exit code 0, pid file written.

Run the helper as a **long-lived step** that starts it, waits for a stop
signal, stops it, and waits for its output to be complete:

```bash
srun -N$N -n$N -c1 --nodelist="$SLICE" --overlap bash -c '
   "$DAEMON" start "$DIR"
   while [ ! -f "$STOP_FLAG" ]; do sleep 1; done
   "$DAEMON" stop "$DIR"
   # Many daemons flush ASYNCHRONOUSLY after `stop` returns. If the step exits
   # now, Slurm reaps them mid-flush -> truncated/0-byte output, no error.
   for _i in $(seq 1 60); do [ -s "$OUT" ] && break; sleep 1; done
' &
SVC_PID=$!
...run the application in a separate --overlap step...
touch "$STOP_FLAG"; wait "$SVC_PID"
```

For the dftracer-specific instance of this, see [[tools-dftracer]].

---

#### GPUs: `--gres=gpu:N` and `--gpus-per-task` are NOT interchangeable

They change what the application *sees*, and the right one depends entirely on
how the application picks its device:

| flag | `CUDA_VISIBLE_DEVICES` per task | device count seen |
|---|---|---|
| `--gres=gpu:4` | all four | 4 |
| `--gpus-per-task=1` | one, **renumbered** | 1 |

An app that does `cudaSetDevice(SLURM_LOCALID % num_gpus)` breaks under
`--gpus-per-task` — rank 1 asks for device 1 while Slurm gave it a single
device numbered 0 → `cudaErrorInvalidDevice`. Verify empirically before a sweep:

```bash
srun --jobid=$J --overlap -N1 -n2 --gres=gpu:4 bash -c \
  'echo "localid=$SLURM_LOCALID CVD=$CUDA_VISIBLE_DEVICES count=$(nvidia-smi -L | wc -l)"'
```

#### One dead rank must not hang the sweep

A rank that aborts leaves its peers blocked in the next MPI collective forever.
Belt and braces:

```bash
timeout "$APP_TIMEOUT" \
  srun ... --kill-on-bad-exit=1 ... "$BINARY" ...
rc=$?; [ "$rc" -eq 124 ] && echo "TIMEOUT after ${APP_TIMEOUT}s"
```

---

#### Environment propagation traps

`srun` propagates its own environment to the tasks, so `export`ing before the
call works. Two ways it silently does not:

1. **A trailing `\` followed by a comment line breaks the continuation.**
   ```bash
   FOO=1 BAR=2 \
   # this comment silently ends the command
   srun ... app          # <- runs with NEITHER FOO nor BAR set
   ```
   The assignments become a standalone no-op, the app runs fine, and any
   behaviour gated on those variables just... does not happen. Prefer an
   explicit `export` inside a subshell over prefix assignments spanning lines:
   ```bash
   ( export FOO=1 BAR=2; srun ... app ) >> "$log" 2>&1
   ```
2. **`module purge` / `module load` inside `bash -lc` can roll back**, because
   the login profile reloads the site defaults. Put module loads in a **sourced
   script**, then verify with `which`, never assume. (Same lesson as
   `feedback-flux-proxy-wrapper`.)

Also: a sourced env script must never return non-zero — callers run under
`set -e`. A trailing `[ -d "$V" ] && source "$V/bin/activate"` returns 1 when the
directory does not exist and kills the caller silently. End such files with
`true`.

---

#### Cancelling: scope it to the job, NEVER the allocation

Identical rule to [[flux-alloc]]. Cancel the specific job id you submitted;
**never** tear down an allocation (the user's or your own long-lived one) to
clean up after a failed run. Allocations are the scarce, slow-to-acquire
resource.

```bash
scancel <JOBID>                                   # one job
squeue -h -u "$USER" -o "%i %j"                   # find ids first
scancel --state=PENDING --name=<jobname> -u $USER # scoped by name, if needed
```

Never `scancel -u $USER` (kills everything the user has, including work that is
not yours) and never cancel a job you did not submit.

**Killing stray processes:** `pkill -f <pattern>` will match **your own shell's
command line** if the pattern appears in it, killing the very command doing the
cleanup. Filter by pid and inspect `/proc/<pid>/cmdline` instead, or use a
pattern that cannot match the invoking command.

---

#### Long sweeps: checkpoint per VERIFIED unit, and make them resumable

Partition time limits force any large campaign to span multiple allocations, so
a sweep must survive being cut off:

* Append one line per completed unit to a state file; on restart, skip units
  already listed. Concurrent workers on disjoint units may share the file safely
  (short appends).
* **Checkpoint only after verifying artifacts on disk** — never on exit status.
  Runs routinely return `rc=0` while producing nothing (a mis-set env var, a
  reaped daemon, a step that ran with no tracing enabled). Count the expected
  files and check they are non-empty.
* Keep a **deadline guard**: read the allocation's real end time and stop
  cleanly while there is still room for one more unit, rather than being killed
  mid-run.
  ```bash
  END=$(squeue -h -j "$SLURM_JOB_ID" -o %e); DEADLINE=$(date -d "$END" +%s)
  [ $(( DEADLINE - $(date +%s) )) -gt $(( MAXOBS*2 + 120 )) ] || exit 7
  ```
* Drive independent node-scales **concurrently** rather than in sequence: submit
  one non-blocking job per scale and let them start whenever the scheduler
  reaches them, instead of a `--wait` chain in which a single deep-queued job
  blocks everything behind it.

---

#### Decoding `squeue` pending reasons

| Reason | What it actually means |
|---|---|
| `Priority` | higher-priority jobs are ahead; normal |
| `Resources` | waiting for enough free nodes |
| `Nodes required ... reserved for jobs in higher priority partitions` | a partition sharing these nodes outranks yours — not a hardware fault |
| `QOSMaxJobsPerUserLimit` / `AssocMaxJobsLimit` | you already have too many jobs queued |
| `ReqNodeNotAvail` | often a DOWN/DRAINED node in an explicit `--nodelist` |

---

#### Measurement policy (unchanged from [[flux-alloc]])

These are scheduler-independent standing rules; see [[flux-alloc]] for the full
statements:

* **Run length** — make the run long enough that startup noise does not dominate.
* **Replicates and percentiles (MANDATORY)** — minimum 5 replicates, escalate on
  high CV, report p50/p95/min/max, and make improvement claims on percentiles,
  never a single-sample delta.
* **Verify scale and completion before crediting ANY wall-time delta** — confirm
  the rank count actually used and that the job was not cancelled or truncated.
  On Slurm the equivalents of flux's event log are:
  ```bash
  sacct -j <jobid> -o JobID,JobName,State,ExitCode,NNodes,NTasks,Elapsed,Start,End
  scontrol show job <jobid> | grep -E "JobState|Reason|NumNodes|NumTasks"
  ```
  A `State` of `TIMEOUT`, `CANCELLED`, `NODE_FAIL` or a non-zero `ExitCode`
  disqualifies the run as a comparison point.
