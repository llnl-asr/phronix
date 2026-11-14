---
name: workload_genesis_run
description: Sweep ANY ice4hpc application across a configuration space (input x node-scale x processes-per-node) collecting full-feature dftracer traces - PAPI, GPU (ROCProfiler or CUPTI), variorum power, node utilization, MPI - into a validated, compacted, self-describing corpus under genesis/<system>/traces/<system>/, then publish it to the shared archive. System-aware: GPU vendor, scheduler, queue, compiler, GPU-per-node count and PAPI preset set are re-derived per machine, never copied. Load to plan, run, resume, validate, compact or publish a genesis sweep, or on a stalled sweep, multiplexed PAPI, 0-byte service traces, "queue X not valid for user", "Invalid generic resource (gres) specification", "chain: 1/1 jobs already live", rc=143 after "Simulation complete".
---
Cross-references: [[workload_genesis_leaf_contract]], [[software_papi]], [[software_cupti]], [[software_rocm]], [[software_flux]], [[software_mpifileutils]], [[tools_dftracer_utils]], [[tools_dftracer]], [[system_tuolumne]], [[system_tioga]], [[system_matrix]], [[system_dane]], [[workload_amg]], [[workload_laghos]], [[workload_minife]], [[workload_kripke]], [[workload_minivite]], [[workload_xsbench]]

# workload_genesis_run

Produces a **trace corpus**: the same application traced across a grid of problem sizes and parallel decompositions, with
every instrumentation layer on, every run content-validated, and the result compacted and documented. Invoke as
`genesis_run <app>` where `<app>` is the name exactly as in **column 3** of `llnl/ice4hpc_data` `data/merged.txt`
(`miniFE.x`, `laghos`, `amg`, `XSBench`, `kripke.exe`, `miniVite`, `TestDfft`).

Converted from dftracer-agents' `genesis_run` skill. **`docs/REFERENCE.md` is the full skill text, verbatim** (every
STEP with its commands, tables and measurements); the canonical scripts are in `docs/scripts/`; the earlier skill version is
`docs/SKILL.previous.md`. This file holds the rules in the capability's sections; when in doubt read the matching STEP in
REFERENCE.md. Tools: `workload_genesis_run_recipe` (predictor: step recipe JSON), `workload_genesis_run_matrix` (predictor:
GATE 3 arithmetic), `workload_genesis_run_check` (validator: a proposed command list / script lines).

> **Rule 0 - nothing in this skill is a constant.** GPU vendor, GPUs per node, scheduler, queue limits, compiler, and the
> PAPI preset set differ per machine. Every number is *derived at run time* from the target system. Copying another
> system's numbers is the single most common way to produce a corpus that looks healthy and is wrong.

## Rules

### STEP 0 - plan, then three mandatory gates
`plan -> [GATE 1] -> annotate/build/smoke -> [GATE 2] -> dimensions -> [GATE 3] -> sweep`. Nothing after a gate starts
until the user explicitly confirms it (not your own earlier message, a tool result, or silence).
- First write `genesis/<system>/PLAN.md` (in this system's folder, measured values, no placeholders): 1 app + variant and
  why (maps.sh vs merged.txt, how disagreement was resolved); 2 source session + evidence; 3 system profile (GPU vendor/arch,
  GPUs/node, cores/node, scheduler, the queue that actually schedules and its node/time limits, primary Lustre); 4 dftracer
  source + features; 5 exact folder layout; 6 PAPI plan (counter budget, preset count, derived presets, partition); 7
  aggregation rule + measured keep-rate; 8 dimensions with **total run count and node-hours**; 9 risks; 10 what is
  validated per run and what "done" means. Summarise, **stop at GATE 1**.
- GATE 1 -> run annotate/build/smoke (STEP 5) one step at a time; a build that "succeeded" is not evidence until `ldd`
  shows dftracer linked.
- GATE 2 -> after the single-rank smoke, **parse the trace** and present an event inventory: app annotation (`CPP_APP` or
  equivalent), GPU (`KERNEL_DISPATCH`/`MEMORY_COPY` or CUPTI equivalents), `papi` with counters that landed and
  `multiplex`, MPI (`collective`/`comm`/`p2p`), `POSIX`/`STDIO`, service `sys`/`io`/`net` + variorum `gpu`/power. Say which
  layers are present/absent and, per absent one, whether expected (e.g. GPU HW counters without `SYS_PERFMON`) or a defect.
- GATE 3 -> final matrix: exact inputs, node scales, ppn ladder, PAPI sets, **total run count**, node-hours, wall-clock
  estimate vs queue limits (`workload_genesis_run_matrix`). Only then launch.

### STEP 1 - inputs (exhaustive by default)
`merged.txt` is CSV `machine,procs,app,"args",seconds`. Materialise **every unique argument string** into
`genesis/<system>/inputs.txt` (args are machine-independent):
```bash
curl -sL https://raw.githubusercontent.com/llnl/ice4hpc_data/main/data/merged.txt -o merged.txt
grep ",<app>," merged.txt | sed 's/^[^,]*,[^,]*,<app>,"//; s/",[0-9.]*$//' | sort -u > genesis/<system>/inputs.txt
```
Strip the opening `"` and trailing `",<seconds>` together (else a stray quote in every case name). Fetch `scripts/maps.sh`
(`app_gpu[<app>]`=1 GPU build exists; `app_var[<app>]` / `app_var["$(key <app> <machine>)"]` variant e.g. `-openmp45` GPU,
`-ref` CPU; `app_exe`, `app_dir`, `app_mpi`, `app_omp`). **Reconcile** maps.sh and merged.txt; when they disagree (maps.sh
GPU variant, merged.txt rows all from `*-cpu` machines) say so and ask which variant (changes ppn ladder, build, ~halves or
doubles run count). **Do NOT subset**: unique args measured amg 16, XSBench 24, miniFE.x 49, laghos 186, kripke.exe 210,
miniVite 288; laghos 186x3x3x2 = 3348 runs in ~380 node-hours, tractable with the packing worker. State run count and
node-hours at GATE 3; propose a reduced list only if asked or node-hours exceed the allocation; record any trimmed inputs
and why in PLAN.md and the corpus README.

### STEP 2 - reuse a successful session (read-only)
Sweeps do not re-annotate. Qualify a session (`ls -d $PROJECT_ROOT/workspaces/<app>/*/`, newest first): `session.json`
exists; `grep -rl DFTRACER <session>/annotated --include=*.c --include=*.cpp --include=*.hpp --include=*.py | wc -l` > 0;
`ldd <binary> | grep libdftracer_core` (evidence the session was sound, not an artifact to use; rebuilt per system). Nothing
under the session root is written, so several systems can sweep it concurrently. No qualifying session -> run the normal
annotate/build pipeline first (an unannotated binary gives traces with no app events: valid files, useless science).

### STEP 3 - detect the system
Flux: `hostname` (strip digits), `flux queue list`, **`flux queue status`** (mandatory), `flux resource list` (NGPUS/NNODES =
GPU ppn ladder). Load the system capability ([[system_tuolumne]], [[system_tioga]], [[system_matrix]], [[system_dane]]);
create one if missing. Derive GPU vendor/arch (`rocminfo`/`nvidia-smi`), GPUs/node, scheduler, usable queue, compiler/MPI
(ice4hpc pins `rocmcc`/`cray-mpich`), PAPI presets. A queue fails three ways that look like a busy cluster: scheduler stopped
(`flux queue status` only), account not authorised (only a real submit says *"queue X not valid for user; valid queues for
user: ..."*), or it advertises nodes of queues it aggregates: confirm with a real 1-node submit and record usable queues.
Check **down nodes** (a full-N request on an N-node queue with one down queues forever).
Slurm: `sinfo -o "%20P %5a %10l %6D %10T %N"`, `scontrol show partition <p>` (**MaxNodes is mandatory**, invisible in
default sinfo; a 1-node cap is rejected as *"Invalid generic resource (gres) specification"*), `scontrol show node <n>`
(Gres/CPUTot/Sockets), `sbatch --test-only` for backfill ETA (creates no job); check partitions sharing nodes; pick job
shape by `--test-only`, not intuition. Full workflow: slurm-alloc.

### STEP 4 - dftracer source
Any system, GPU or CPU: latest **`develop`** of `github.com/llnl-asr/dftracer` (CUPTI merged; czgitlab is the old mirror,
SSH port 7999 only). `pip install --no-cache-dir --no-deps "git+$G/dftracer.git@develop"`, then pydftracer `@develop`, then
dftracer-utils **`@v0.0.12`** (develop HEAD fails: `ConfigTree::Node` incomplete type; fall back to newest tag, not PyPI).
`develop` carries CUDA timestamp fix `324522f` (without it many CUDA events have `ts == 0`; NVIDIA sweeps must build at/after
it; verify by sampling `ts`). No external DNS on nodes: `--no-deps`. Install order dftracer first. `pip uninstall dftracer`
wipes the shared `dftracer/bin` prefix (reinstall utils after any core reinstall) and leaves a stale cmake brahma tree that
breaks the next build with `override` errors (remove it).

### STEP 5 - self-contained system folder
`<session>/genesis/<system>/{env.sh, aggregation.yaml, dataset -> <this-system-lustre>/$USER/<app>_genesis/, annotated/ (own
copy), venv/, build/, papi_sets.txt, traces/<system>/<case>/<nodes>/<ppn>/{raw,compacted}, traces/<system>/README.md,
artifacts/}`. Per-system because: the build edits `annotated/` in place (arch flags, wrappers, dftracer -I/-L/-rpath, .o
files; sharing races silently); binaries are not portable (gfx942 vs gfx90a vs CUDA); venv links this machine's PAPI/MPI/GPU
runtime; Lustre mounts are not shared between machines (an inherited `dataset` symlink dangles and the science audit says "no
result file"; app data on Lustre, traces in the session workspace); PAPI sets differ per CPU. Bootstrap: `SYS=$(hostname |
sed 's/[0-9]*$//')`, mkdir PFS dir + `ln -sfn`, `cp -a <session>/annotated/. "$G/annotated/"`, env.sh pins the ice4hpc
toolchain (not site-default PrgEnv) and loads **`papi` on its own line** (folded into the `rocmcc` load it can drop silently,
leaving `CRAY_PAPI_PREFIX` empty), dftracer into `$G/venv`, build. Verify `ldd "$G/build/<exe>" | grep -E
"libdftracer_core|papi|rocprofiler|cupti|mpi"` and `readlink -f "$G/dataset"` (local PFS). Smoke one rank, inventory from the
trace, **stop at GATE 2**.

### STEP 6 - PAPI partition on THIS machine
`papi_avail | grep "Number Hardware Counters"` (budget), `papi_avail -a | awk '/^PAPI_/ {print $1, $3}'` ($3 Yes = derived,
2+ native events). Preset set, derived list and budget all differ per CPU (same counter count, different presets; native on
one, derived on another). Use the system capability's measured values or derive and **write them back**. Partition covers
every preset once; **probe** each set with ~10 s 1-rank runs, read `args.multiplex` (0 exact, 1 estimate), bisect until 0,
diff landed vs requested (dftracer silently drops a preset it cannot fit, e.g. `PAPI_BR_PRC`). The native=1/derived=2 model
is only a candidate: measured a 5-preset set scored 5/5 multiplexed, a 4-preset set multiplexed and dropped a counter, 3 fit;
partition grew 7 -> 8 sets. See [[software_papi]].
Porting to a NEW app: the app's input naming is hardcoded in five places: `genesis_run.sh` (run-key prefix: resume never
matches), `genesis_driver.sh` (key rebuilt by hand: every scale looks pending, allocates until `MAX_ALLOCS`),
`genesis_compact.sh` (cell key: recompacts every resume), `genesis_readme.py` (leaf glob `input_*` -> empty README; numeric
sort `int(v.split('x')[0])` raises ValueError), `genesis_audit.py` (audits nothing or crashes). Build keys with
`run_key`/`case_slug`; discover leaves by shape `*/nodes_*/ppn_*`; never assume numeric labels (lexical fallback); rewrite the
science audit per app (result file vs stdout log). After porting, grep `scripts/` for the old app's name and vocabulary.

### STEP 7 - selective aggregation (`dur < 100`)
`DFTRACER_ENABLE_AGGREGATION=1`, `DFTRACER_AGGREGATION_TYPE=SELECTIVE` (UPPERCASE), `DFTRACER_AGGREGATION_FILE=<...>/aggregation.yaml`
with top-level `inclusion:` / `exclusion:` sequences of rule strings. DSL: fields `cat name ts dur app rank`, ops `== != >= <=
> <`, `IN {a,b}`, `LIKE`, `AND/OR/NOT`; aggregated when inclusion matches and exclusion does not; `cat == "dftracer"` never
aggregated. The runner reads `GENESIS_AGG_FILE` (exports the three vars if the file exists, else **unsets** them) and logs
`aggregation=<type> file=<path>` per run. When categories of interest are all below the threshold (measured GPU miniapp: every
`dur_max` <= 99 us, `dur < 100` folded 99.96% of `KERNEL_DISPATCH`, 99.98% of `comm`) use a category exclusion:
`exclusion: - "cat IN {KERNEL_DISPATCH,MEMORY_COPY,PAGE_MIGRATION,SCRATCH_MEMORY,collective,comm,p2p,CPP_APP}"` (folds
`HIP_RUNTIME_API`, `POSIX`, `STDIO`). Have the validator fail any run where an excluded category shows `dft_cnt > 1`.

### STEP 8/9 - dimensions and layout
Input (ALL) x node scale (e.g. 1,2,4,8, bounded by the queue node limit) x ppn (CPU powers of two to cores; GPU powers of two
to this machine's GPUs/GCDs per node). Per-rank resources constant across ppn. PAPI sets are runs, not a dimension: they
collapse into one `compacted/` per leaf. Total = inputs x scales x ppns x sets. Layout
`<session>/genesis/<system>/traces/<system>/<case>/nodes_<N>/ppn_<P>/{raw/papi_<set>/, raw/validation_<set>.json, compacted/,
compacted_check.json}` + `README.md`; the repeated `<system>` level keeps the corpus self-describing and mergeable.

### STEP 10 - run each configuration
Flux, per run: (1) `flux submit` the service **detached**, pinned `-N<n> -n<n> -c1 --requires=host:<csv>
--setattr=exclusive=false`, poll per-host pid files (`dftracer_service start` under `flux run` never returns); (2) `flux run`
the app on the **same** hosts with this system's `build/<exe>`, cwd inside `dataset/`; (3) `flux submit` service `stop` on the
same hosts, let it flush. Host pinning is mandatory (else daemons profile the wrong nodes; empty service traces).
Slurm: service as a **long-lived step** `srun -N$N -n$N -c1 --nodelist="$SLICE" --overlap bash -c '"$SVC" start "$DIR"; while
[ ! -f "$FLAG" ]; do sleep 1; done; "$SVC" stop "$DIR"; for _i in $(seq 1 60); do [ -s "$OUT" ] && break; sleep 1; done' &`,
app `srun -N$N -n$((N*P)) --nodelist="$SLICE" --overlap --gres=gpu:4 -c$C --kill-on-bad-exit=1 "$BINARY" ...`, then `touch
"$FLAG"; wait "$SVC_PID"`. `--overlap` mandatory, `--nodelist` replaces `--requires=host:`, a daemon lives as long as its step
and must wait for a non-empty trace (stop only SIGINTs). Each missing gives a 0-byte service trace.
- **Leave the daemon a core**: cores/rank = `floor((cores_per_node - 1) / max_ppn)`, constant across the ladder (64-core node,
  max ppn 8: 8 deadlocks, 7 works). Symptom: healthy per-run times, collapsing throughput, one job `S` beside the service `R`
  (`flux proxy <alloc> flux jobs -a`).
- Scheduling: one queue of pending runs sorted by node count descending (first-fit decreasing); dispatch the largest that fits
  whenever hosts return; no phase barriers; **backfill** the remainder concurrently (a 4-node allocation runs one 4-node job or
  2+1+1, never one 1-node job with 3 idle); launch everything that fits, never wait for the largest cells. Host slices
  **disjoint**; each run's daemon pinned to its own slice; cap concurrency below per-node contention.
- Size allocations to what is **free now** (`flux resource list -o "{state} {queue} {nnodes}"`), with a floor of the smallest
  pending run; request **short** walltimes (a few times the longest run; 12 h requests showed a 10 h ETA with a node free, 2 h
  started at once); pick the shape from a probe (`flux submit -N64 -t 1h hostname` started instantly while N=32 t=2h never
  scheduled); re-probe when throughput drops; when only the widest rung remains, ask for a larger pool.
- Parallel drivers own **disjoint work and their own state file**: partition by node scale, and by ppn within a scale across
  queues (`ppn 1 2` vs `ppn 4 8`); size concurrent requests to the queue (1+2+4 = 7 nodes); give a small-only queue the small
  work. Verify no two live drivers share `GENESIS_STATE` via `/proc/<pid>/environ`.
- Charge every job to the project bank: `flux account list-banks | grep -i <project>`, `flux account view-user $USER`
  (membership), `flux batch -q <queue> --bank=<bank>`; project bank **`gwisdom`** (measured: gwisdom `job_usage 0.0` vs default
  bank parent `gbronze` 32.4M); probe one 1-node/5-min job first.
- Deadline: worker start + allocation budget; stop dispatching before it, exit with a distinct code, driver resumes.

### STEP 10a - checkpoint / restart
One append-only file per worker group, line `<case>_N<nodes>_ppn<ppn>_<papiset> ok dt=<s>` or `... SKIPPED <reason>`. Written
**only after content validation** (never on rc==0); key is the full coordinate; append, never rewrite; SKIPPED is first-class.
Resume = rebuild pending from the full matrix minus the checkpoint at worker startup (`grep -q "^$key " "$STATE"`, trailing
space anchors `_flop_p1` vs `_flop_p10`). Count progress as `grep -v SKIPPED "$STATE" | awk '{print $1}' | sort -u | wc -l`
against the reachable total (`matrix - skipped`), never `sort -u "$STATE" | wc -l`. One worker per checkpoint (partition by
CASE with disjoint `traces/<system>/<case>/`, or serialise with `--dependency=afterany`). Merge checkpoints by union inside the
worker at startup (`cat state_* | sort -u > state_all.new; mv`), never at submit time. Reconcile failures against the
checkpoint (`grep -qh "^$k " artifacts/state_*`): measured 201 failing keys, 182 self-healed, 19 real. Re-derive each restart:
pending set, host list, deadline, MAXOBS seed, free-node count; carry over: the checkpoint, validated traces, SKIPPED.

### STEP 10b - make the sweep FINISH
One worker per checkpoint (two produced `app trace count 32 != expected 8` and `Compressed file ended before the
end-of-stream marker`, most of ~500 failures). No login-node driver holding `flux alloc` (four multi-hour stalls; orphan
allocations keep dispatching): use a **dependency chain of `flux batch` jobs** with `--dependency=afterany:$prev` and
`--output=.../batch_${grp}_{{id}}.log` (`%j` is Slurm syntax, not expanded). No cron (node-local on multi-login sites). Kill by
PID, check other login nodes. Adaptive allocation size with a floor. Deadline guard `MAXOBS * factor + headroom` (factor 2
wastes grants; factor 1 killed 16 in-flight runs at one boundary). Detect structurally IMPOSSIBLE cells (ranks > decomposable
units, e.g. 16-zone mesh on 32 ranks -> rc=139, `Zones min/max: 0 1`; one sweep burned 53 attempts), mark `SKIPPED <reason>`,
report `total - skipped`.

### STEP 11 - validate every run
rc==0 is not evidence (a run killed during flush exits 0 with zero traces). Assert: app traces == nodes*ppn and `PR` ranks ==
`{0..n-1}`; `SH` cmdline matches the cell; every trace has `start` and trailing `end`; required categories and `end.used`;
PAPI landed == requested, all `multiplex == 0`; one service trace per distinct host with `sys`/`io`/`net` + power. Count
failures from state/failures files, never a log tail. Audit the science from the app's own output (size, ranks, finite
result); do not invent convergence thresholds (many proxies stop at an iteration cap). The audit is PFS-local.
**Gate validation on the app's completion marker** (`Energy` Laghos, `Figure of Merit` AMG, `END` Kripke, `Final Resid Norm`
miniFE, `MODS` miniVite, `Verification` XSBench): no marker -> `FAIL ... INCOMPLETE` without validating.

### STEP 11a - the back half is a pipeline
Leaf stages `sweep -> [SEALED] -> compact+verify -> publish+verify -> perms -> [DONE]`, each an idempotent resumable worker.
SEALED only when distinct validated keys == reachable keys for the leaf (from the checkpoint, excluding SKIPPED), never on
"looks populated" or a timeout. One claim per leaf per stage with atomic `mkdir "$G/artifacts/compact_claims/$leafkey"`;
per-stage state files (`state_compact`, `state_publish`). Never run a pipeline stage inside a sweep slice; give it its own
small allocation (1 node x 16 procs for dcp) sized to a wave. Publish in **waves** (tens of leaves, one dcp each), verify per
wave before deleting. Write `STATUS.md` on the first wave (in progress, target size, leaves so far), refresh per wave; the real
`README.md` only at the end, deleting STATUS.md in the same step. A leaf gaining a validated key after publication is
**unsealed** and re-flows; record every re-publish. Run `chgperm.sh` every wave.

### STEP 12 - run JSON, move raw/, then compact in place (mandatory order, user policy)
`run finishes -> write run_<set>.json -> leaf seals -> MOVE raw/ to archive -> verify bytes+count -> delete workspace raw/ ->
compact IN PLACE in the archive -> if compaction fails or never runs: COMPACTION_NOT_RUN.md in that leaf -> chgperm`.
`genesis_run.sh` writes `raw/run_<set>.json` after every run, pass or fail; `genesis_publish.sh` moves sealed `raw/` (traces +
run + validation JSON) to `$GENESIS_ARCHIVE/<case>/nodes_<N>/ppn_<P>/raw` (dcp under flux/slurm, else `cp -a`), verifies
regular-file bytes and count, deletes workspace raw/ and leaves an `ARCHIVED` symlink; compaction never gates publication;
`GENESIS_ROOT=$GENESIS_ARCHIVE genesis_compact.sh` compacts in place (staging inside the leaf); the note is removed when a later
compaction succeeds. `genesis_finalize.sh` = publish + README. The leaf must satisfy [[workload_genesis_leaf_contract]] (run
`genesis_validate_leaf.py <archive> --sets=N` before declaring complete). `summary.json` per leaf (keys: leaf, ok, app, system,
input, nodes, ppn, ranks, sets[], n_sets, n_app_traces, n_service_traces, hosts[], app_categories, service_categories, papi[],
papi_multiplex[], gpu_power_csv, gpu_power_rows, compacted{chunk: bytes}); `raw/run_<set>.json` per run (key, system, app,
case, nodes, ppn, ntasks, papi_set, papi_requested[], papi_landed[], multiplex{v:n}, ranks, app_files, service_files,
power_samples, hosts[], service_pids "<up>/<expected>", binary, start_epoch, duration_s, app_exit, validate_ok, status,
flush_wait_s, run_log (AMG's science lives only there), backfilled). Backfill reconstructs from `state_*`,
`artifacts/<key>.log`, `validation_<set>.json`, `null` for the unavailable, `backfilled: true`.
Compaction: `dftracer_split --verify` (`grep -a 'Verification: PASSED'`), assert service categories present and `hosts >=
nodes`; delete `raw/` only with two verified copies. dftracer_split does not recurse: stage a flat dir of hardlinks
(splice the set name into `service_<host>.pfw.gz`), on the same filesystem as `raw/` (else EXDEV, `staging mismatch 0/N`).
Parallel compaction: deal leaves round-robin over `FLUX_TASK_RANK` (16 tasks on 2 nodes ~20x serial) with `-o
exit-timeout=none` (default kills all 30 s after the first exit: died at 39/188); never two compaction jobs on one corpus.
Finish with `traces/<system>/README.md` (what, dimensions, stats by category/dimension, PAPI coverage, power samples, size,
per-cell inventory, validation criteria, caveats incl. silently unavailable layers).

### STEP 13 - publish to the shared archive
Destination `<group archive>/dftracer-traces/<app>/<system>/<case>/nodes_<N>/ppn_<P>/` (on LC: the genesis-wisdom workspace);
systems side by side under one app; mirror the existing layout (a stray misspelled app dir exists). `module load
mpifileutils; flux run -N1 -n16 dcp <src> <dst>` (dcp copies; no dmv). Verify before deleting the source: regular-file bytes
and counts via `find -type f -printf '%s\n' | awk`, never `du` (cross-filesystem), plus `flux run -N1 -n16 dcmp`; confirm the
destination was empty or held a different `<system>` (a larger byte total means someone else's data). Permissions: the
archive's `chgperm.sh <archive>/dftracer-traces/<app>/<system>` (group rw files, rws dirs, strip other wx, chgrp
genesis-wisdom; `newgrp genesis-wisdom` if needed), never hand chmod/chgrp. Order per wave: seal, compact+verify, dcp, verify
while source exists, delete source, chgperm, refresh STATUS.md; at the end README.md in the corpus and delete STATUS.md.
Decide raw-vs-compacted for the archive explicitly and ask (measured 1.6 TB raw vs a 94 GB existing corpus); say it in the
README.

### Canonical scripts are configured, not forked
`docs/scripts/` runs unchanged on Flux and Slurm for any app via `GENESIS_SCHED`, `GENESIS_INPUTS_FILE` /
`GENESIS_ARGS_TEMPLATE`, `GENESIS_GPU` (hip/cuda/none), `GENESIS_POWER` (variorum/nvml/none), `GENESIS_REQ_CATS`,
`GENESIS_REQ_USED`, `GENESIS_NOFOLD_CATS`, `GENESIS_APP_MARKER`, `GENESIS_OK_RCS`, `GENESIS_COPY=cp`, `GENESIS_LEAF`,
`GENESIS_CHGPERM`, `GENESIS_COMPACT_TMPDIR`. Slurm: `genesis_slurm_chain.sh <part> <nodes> <min> <depth> <name>` (afterany
chain, one `GENESIS_STATE` per node scale, worker flocks its state); publish runs from a login-node loop over the UNION of the
state files. `run_<set>.json` carries `multiplex` and `app_files` for the leaf contract.

## Constraints
- Three user gates (STEP 0); never launch past one without explicit confirmation.
- Nothing under the session root is written by a sweep; each system owns its folder.
- Application output on the machine's PFS (Lustre); dftracer traces in the session workspace, never on Lustre.
- Aggregation is capture-time only and irreversible: measure per-category keep-rate on the smoke trace and report it at GATE
  2; `dur` is microseconds (a "1 ms" threshold can fold the whole corpus); the fold count is `dft_cnt`, never `count`
  (POSIX `count`/`count_sum` are bytes: "1.59 billion folded events" in a 44 s run).
- Host slices disjoint; never run a pipeline stage on a sweep slice (contaminates PAPI and power, undetectable).
- **ONE state file = ONE worker, enforced with `flock`**: `exec 9>"${STATE}.lock"; flock -n 9 || exit 0` (released on death);
  verify both "acquired" and "already owns" messages appear. A flock protects data, not allocations: guard drivers separately
  (an inherited fd in a backoff `sleep` keeps the lock after the driver dies). On corruption: back up the state file
  (`state_backups/state_all.before_corrupt_removal`), remove only affected keys, delete their trace dirs, re-run; never repair
  traces in place.
- Delete a source only after bytes, counts and dcmp agree; delete `raw/` only with two verified copies.
- Ask before pushing `raw/` to the shared archive; ask before resubmitting long jobs.

## Corner cases
- **Diagnosing a crash in the tracing path** (GPU profiler callbacks race on their own threads): gdb hides it (3/3 bare, 0/3
  under gdb): use a post-mortem core (`ulimit -c unlimited`; cores may be `<host>-<exe>-<pid>.core`). The system gdb may not
  read clang DWARF 5 (`Cannot handle DW_FORM_strx1`): use `rocgdb`. Read the ARGUMENTS: garbage `process_id`, `rank=-1`
  (constructor defaults: published but uninitialised), null `config` (freed) locate the lifetime window.
  `DFTRACER_ENABLE_HIP_TRACING=0` is inert (rocprofiler finds `rocprofiler_configure` at load); only a rebuild with the
  feature OFF removes it. Verify a rebuild happened (timestamp of `libdftracer_core.so.*`); reinstall utils after any core rebuild.
- **Failure classes to check on every new system** (record answers in the system capability): GPU HW counters unavailable
  (`could not be locked for profiling ... (capability SYS_PERFMON)`; activity tracing still works, say so); variorum
  `DFTRACER_BUILD_VARIORUM=AUTO` finds an RPM returning `_ERROR_VARIORUM_UNSUPPORTED_PLATFORM` (use `ALWAYS`, verify a power
  event); service teardown abort `corrupted size vs. prev_size in fastbins` (two `librocm_smi64` ABIs; post-flush, no data
  lost; `HWLOC_COMPONENTS=-rsmi` does not avoid it); NVIDIA site CUDA without CUPTI (pin `DFTRACER_CUDA_PATH` at a toolkit
  with `include/cupti.h`, confirm `-- [DFTRACER] found CUPTI at ...`; one CUPTI client per process, no nsys/ncu alongside;
  [[software_cupti]]); variorum on a two-socket node with the service pinned to one core: `cores(1) mod sockets(2) != 0` ->
  `exit()` kills the daemon while its pid file looks healthy: where power is unreadable (root-only msr, no msr_safe, 0400
  RAPL) set `DFTRACER_DISABLE_VARIORUM_POWER=1`, sample GPU power via NVML/rocm-smi, record `tracing.power: off` in
  systems.yaml; the PAPI ceiling is per machine (STEP 6).
- **Resubmission/teardown path** (runs only when something ends; each cost 5-30 h idle): (1) the pending counter must fail
  loud: a `#` header containing the delimiter made it print nothing, `[ "" -gt 0 ]` false, driver looped submitting nothing:
  skip comments, `[[ "$remaining" =~ ^[0-9]+$ ]] || exit 1`; (2) deadline detection must fail safe: `squeue -h -j
  "$SLURM_JOB_ID" -o %e` returned empty, `DEADLINE=0` meant forever, a ~1680 s cell ran into the 12 h wall, the successor
  submission died, **idle a week**: fall back to `scontrol show job ... EndTime`, then now + requested walltime; `RESERVE` >
  longest cell (600 s vs a 1350 s cell dies every time); (3) self-chaining must exclude its own job from the cap (`chain: 1/1
  jobs already live; not resubmitting`): exclude `$SLURM_JOB_ID`; (4) chaining off `SLURM_JOB_PARTITION` fans out across
  queues: pin the chain target. `--signal=B:TERM@900` is belt-and-braces (a trap starves while blocked in `wait`).
- **The validator is O(events)**: `json.loads` per line: 19.6 s for one 48 MB / 6.7 M-event trace, 66 per leaf, a pack sat 4 h
  in the validator with no Slurm step. Slice `"cat":"` cheaply and parse only lines with semantics (dftracer metadata, papi,
  `dft_cnt`): 19.6 s -> 4.5 s identical counts. At 1.36 billion events (57-91 min; 165 of 200 allocations spent, rc=142): a
  substring prefilter `('"dftracer"', 'multiplex', 'PAPI_', 'dft_cnt')` and one process per trace file
  (`ProcessPoolExecutor`, picklable partials) -> 68 s. Prove equivalence on negative controls too; keep the old validator as
  `*_slow.py.bak` and diff JSON on a real cell (byte-identical on 209 MB).
- **Over-specified content assertions fail healthy data**: requiring `{CPP_APP, KERNEL_DISPATCH, MEMORY_COPY, papi}` failed
  188/188 verified leaves; `KERNEL_DISPATCH` is the proof, `MEMORY_COPY`/`PAGE_MIGRATION` informational; keep required and
  informational sets in sync across every checker (grep the category name). A failure with `verified=1` and a healthy chunk
  count is an over-strict assertion: re-check, do not recompact. Mixed variants (CPU OpenMP beside GPU CUDA in one corpus):
  200/200 CPU leaves got `COMPACTION_NOT_RUN.md` with `verified=1 content_ok=1`: optional `$GENESIS_G/req_cats.txt`
  (`<case-glob> <CAT,CAT>`, first match wins, e.g. `cpu_* C_APP,papi` then `* C_APP,CUDA_KERNEL,papi`), distinct case
  prefixes per variant. Capture the checker output before cleanup (`genesis_compact.sh` saves it to `$why`).
- **Ranks that exit non-zero by design** (XSBench XL/XXL, no reference checksum): `--kill-on-bad-exit=1` SIGTERMs ranks still
  flushing -> `rc=143`, `STEP ... CANCELLED DUE TO TASK FAILURE` after `Simulation complete`, validation `"ok": true` (seen at
  64 ppn, not 32): `GENESIS_KILL_ON_BAD_EXIT=0` for that variant; `GENESIS_APP_TIMEOUT` still bounds a hang.
- **Orphaned drivers**: one orphaned 16 days earlier kept chaining allocations: scan `ps -eo pid,lstart,args` and check
  `lstart`; trace a mystery allocation via `flux job info <id> jobspec` (cwd, command); a reappearing allocation means
  something is alive; bracket patterns (`genesis_[d]river`) and kill by PID.
- **Failing cells must back off**: 179 attempts at one OOM case; 2.7 h of node time over 11 attempts on one truncated cell:
  count failures per key, skip after N strikes (stays pending); archive the failure log when the cause is fixed.
- **Diagnose stalls from Slurm accounting**: `sacct -j <job> --format=JobID,JobName,State,Elapsed,MaxRSS`: `CANCELLED by
  <uid>` (your harness), `TIMEOUT`, `OUT_OF_MEMORY`/`oom_kill`, steps `COMPLETED` while the batch step runs on (wedged in your
  validator/compaction). No Slurm steps + live batch step = not waiting on the cluster.
- **Flush-wait amplifier**: re-testing every trace each pass is quadratic once one file is permanently truncated (715 s per
  pass on a 10 GB / 130-file leaf; 60 passes ~12 h): retest only failures, bound by wall clock (180 s; healthy flush ~1 s),
  log still-truncated files.
- Leaves span more hosts than `nodes` (several runs, different slices): assert `hosts >= nodes`.
- Compaction deferred to the end: 188 leaves, 6-10 days serial, 1.6 TB raw held: compact continuously as leaves seal.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_genesis_run_check`, fix the proposed lines, re-render with `workload_genesis_run_recipe`
(and `workload_genesis_run_matrix` for sizing) and check again; the same failure twice stops the loop for the user:
- `agg_type_uppercase` / `agg_enabled` / `in_needs_spaces`: `DFTRACER_AGGREGATION_TYPE=SELECTIVE`,
  `DFTRACER_ENABLE_AGGREGATION=1`, `cat IN {...}` with spaces; confirm folding on the smoke trace.
- `service_not_flux_run`: `flux submit` the service detached and pinned. `slurm_overlap`: `--overlap` + `--nodelist` on both steps.
- `flux_output_template`: `{{id}}`. `flux_batch_bank`: `--bank=<bank>` after a membership check and one probe job.
- `no_pkill_pattern`: kill by PID. `no_cron`: dependency chain. `count_keys_not_lines`: distinct keys excluding SKIPPED.
- `utils_not_develop`: dftracer-utils newest tag. `pip_no_deps`: `--no-deps`. `variorum_always`: `ALWAYS` (or disable power).
- `no_hip_env_ab`: rebuild with the feature OFF. `exit_timeout_none`: `-o exit-timeout=none`. `grep_a_verification`: `grep -a`.
- `split_not_raw`: hardlink staging inside the leaf. `no_du_verify`: find bytes/counts + dcmp. `no_hand_perms`: chgperm.sh.
- `no_rsync_archive`: dcp. `no_squeue_only_deadline`: scontrol EndTime fallback, then now + walltime.
- `input` (inconclusive): pass the command list.

## Self-heal
On a stalled or failing sweep: read Slurm/Flux accounting first (Corner cases), reconcile failures against the checkpoint,
`lesson_search` the error text, and match it to Corner cases / LESSONS.md / docs/REFERENCE.md. If a script in docs/scripts or
a rule here is wrong, fix it with `capability_update` (scripts are configured via GENESIS_* variables, not forked).

## Self-learn
What is explored here becomes a capability: every new machine's measured facts (usable queues, MaxNodes, PAPI partition,
derived presets, module order, power availability) go into its `system_<x>` capability; a new app's completion marker,
input count, impossible cells and science audit go into its `workload_<x>` capability; each new stall or silent failure
(symptom -> cause -> fix) is added to LESSONS.md and, if deterministic, to `workload_genesis_run_check`; verified sweeps go
to WORKED.md.

## What works
- laghos: 186 inputs x 3 node scales x 3 ppn x 2 PAPI sets = **3348 runs, ~380 node-hours**, completed with the packing
  worker (recorded 2026-10-21).
- amg/tuolumne corpus: 343/343 leaves satisfy the published-leaf contract with `--sets=9` (recorded 2026-10-21).
- Validator rewrite: prefilter + per-file processes took a 1.36 billion-event cell from 57-91 min to 68 s with byte-identical
  JSON on a 209 MB cell (recorded 2026-10-21).
- Short allocations: re-requesting a 12 h job at 2 h started it almost immediately; N=64 t=1h started instantly while N=32
  t=2h never scheduled (recorded 2026-10-21).
- XSBench/matrix sweep: first to run the unchanged scripts on Slurm via GENESIS_* variables and `genesis_slurm_chain.sh`.

## Worked references - read the neighbouring sweep before deriving anything
Every sweep lives in `$PROJECT_ROOT/workspaces/<app>/<session>/genesis/<system>/`. On a machine that already hosted one, read
its `PLAN.md`, `env.sh`, `papi_sets.txt`, `aggregation.yaml`, `traces/<system>/README.md` and any `*.patch` beside `env.sh`:
machine facts (PAPI partition, module order, usable queue, per-rank cores, dftracer patches) are reused. Re-derive per app:
the inputs and maps.sh reconciliation, the build, the tracing overhead and aggregation keep-rate (miniFE vs laghos differ
~1000x in event density), and the science audit.

## Related
[[software_papi]] · [[software_cupti]] · [[software_rocm]] · [[tools_dftracer_utils]] · [[software_flux]] (flux-alloc) ·
slurm-alloc · [[system_tuolumne]] · [[system_tioga]] · [[system_matrix]] · [[system_dane]] · [[workload_genesis_leaf_contract]]
