---
name: software_papi
description: PAPI hardware-counter tracing with dftracer (DFTRACER_ENABLE_PAPI_TRACING, DFTRACER_PAPI_EVENTS, DFTRACER_PAPI_SAMPLE_INTERVAL_MS, DFTRACER_PAPI_MULTIPLEX): the real hardware-counter budget from papi_avail (not the preset count), derived presets that cost several counters and silently multiplex or get dropped, building an exact counter partition one run per set, verifying exactness from args.multiplex and the counters that landed in the trace, probing on a compute node, the family-grouped event layout (cat == 'papi'), teardown races, and the papi/7.2.0.2 site pin. Load for any DFTRACER_ENABLE_PAPI_TRACING work, or on: 'counters were requested but this machine has M hardware counters, so they are time-shared', 'PAPI counter PAPI_X is one native event subtracted from another ... dropping it', requested counters missing from the trace, args.multiplex == 1, analyses filtering cat CACHE/FLOP/BRANCH/TLB reading zero, SIGSEGV in PAPI_library_init, crash in gotcha_get_wrappee at finalize, zero-byte traces on long runs.
---
Cross-references: [[system_tuolumne]] [[system_matrix]] [[software_cupti]] [[software_rocm]] [[tools_dftracer]] [[tools_dftracer_utils]] [[workload_minife]] [[capability_builder]]

# software_papi

Converted from dftracer-agents skill `software-papi`. Tools: `software_papi_recipe` (predictor) and `software_papi_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Rule 0: the budget is the HARDWARE counter count (`papi_avail -a | head -25` -> 'Number Hardware Counters : N'), not the number of presets listed. MI300A node: 5 hardware counters, 30 presets.
- Asking for more than fits makes PAPI multiplex (time-share): values are scaled estimates with 1-6% error that is BIASED, not noisy, and worst on phase-changing workloads.
- Rule 1: a DERIVED preset (`Deriv Yes` in papi_avail -a) is computed from >= 2 native events and costs >= 2 counters. Never size a set by counting names. dftracer drops a derived preset whose family does not fit rather than report impossible (negative) values.
- Derived cost is not uniformly 2 (PAPI_L2_ICM and PAPI_L2_TCM fit alongside three native counters; four derived FLOP presets did not): measure, do not compute.
- Rule 2: get exact counts for more counters than fit by one run per set: `DFTRACER_ENABLE_PAPI_TRACING=1`, `DFTRACER_PAPI_EVENTS=<comma/semicolon list of PAPI_* names, no family prefix>`, `DFTRACER_PAPI_SAMPLE_INTERVAL_MS=100`. DFTRACER_PAPI_EVENTS overrides the build-time DFTRACER_PAPI_DETECTED_EVENTS default. DFTRACER_PAPI_MULTIPLEX only if time-sharing is deliberately wanted.
- Keep counter families together in a set; keep a shared reference counter (PAPI_TOT_CYC) in every set when normalizing across runs (costs one slot per set).
- Rule 3: probe each candidate set cheaply (a few seconds at toy size, e.g. miniFE nx=64 1 rank ~1 s) and read args.multiplex back before committing.
- Rule 4: verify exactness from the trace: `args.multiplex` (0 exact, 1 scaled estimate) AND the PAPI_* keys (excluding *_delta) that landed vs the requested set. Never quote multiplexed numbers as measurements.
- Rule 5: probe on a COMPUTE node inside an allocation: the same 4-name set was multiplex=1 on a login node and multiplex=0 on an MI300A compute node.
- Each sample records PAPI_X (cumulative) and PAPI_X_delta (since the previous sample).
- Events are family-grouped: one event per family per sample, cat == "papi", family is the event `name`, counters packed in args. The old cat values CACHE, FLOP, BRANCH, TLB, INSTRUCTION, CYCLE no longer exist; filters on them read zero.
- Teardown: the PAPI sampler must be finalized before posix unbind (PAPI_read uses read(2), which dftracer intercepts; sampling after unbind dies in gotcha_get_wrappee). Confirm the ordering in DFTracerCore::finalize() on the branch you build.
- Always count zero-byte traces AND check the trailing `end` event: the teardown race is size-dependent (short runs survive, long runs die inside PAPI_read).
- Counter plans are not portable between systems: re-derive per machine (MI300A/Cray ~30 presets vs Sapphire Rapids 17).

## Constraints
- Tuolumne: use papi/7.2.0.2; papi/7.3.0.1 ships an ABI-incompatible rocp_sdk component that SIGSEGVs in PAPI_library_init (kills dftracer's build-time probe -> fallback to two counters, and the traced app).
- Login-node probes give the wrong multiplex verdict in either direction.
- A branch carrying PAPI support does not necessarily carry the sampler-before-unbind teardown fix.

## Corner cases
### `PAPI: N counters were requested but this machine has M hardware counters, so they are time-shared ...`
Cause: set exceeds the hardware budget (derived presets count several). Fix: split into one run per set; re-probe until multiplex=0.

### `PAPI counter PAPI_BR_PRC is one native event subtracted from another and the PAPI family does not fit this machine; dropping it ...`
Cause: derived preset (BR_PRC = BR_INS - BR_MSP) whose family cannot fit. Run exits 0 with fewer counters. Fix: put it in a set where its family fits; compare landed vs requested.

### Requested 17 counters, trace has 15, all scaled (`mux=[1] want=17 got=15 missing=['PAPI_BR_UCN','PAPI_BR_PRC']`)
Sapphire Rapids, PAPI 5.6.0.0, build probe DFTRACER_PAPI_FITTING_COUNTERS 10. Fix: the measured 2-set partition (branch+instruction+cycle 10; flop 7), both exact.

### A 4-name set multiplexes while a 10-name set is exact
Sapphire Rapids: TOT_INS,TOT_CYC,FP_OPS,DP_OPS multiplexed; group-aligned sets fit. Mixing across groups overflows unpredictably: probe.

### Same set multiplex=1 on login node, 0 on compute node
multiplex is a property of the machine the counters are programmed on. Probe on the compute node inside the allocation.

### Analysis filtering `cat == "FLOP"` (or CACHE/BRANCH/TLB/INSTRUCTION/CYCLE) returns nothing
Layout changed to family-grouped: cat == "papi", family in `name`. Update the filter.

### Crash in `gotcha_get_wrappee()` at finalize / zero-byte traces on long runs
Sampler stopped after posix_instance->unbind(); next PAPI_read -> intercepted read(2). Fix: finalize the sampler first (upstream fix); verify DFTracerCore::finalize() ordering on your branch; count zero-byte traces and trailing end events.

### SIGSEGV inside `PAPI_library_init`; build-time probe falls back to two counters
papi/7.3.0.1 rocp_sdk component ABI-incompatible with installed ROCm (Tuolumne). Fix: module load papi/7.2.0.2.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_papi_recipe` renders the recipe; validator `software_papi_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_papi_7_3_on_tuolumne` fails: module load papi/7.2.0.2. Then render with `software_papi_recipe` and validate again.
- `papi_events_plain_preset_names` fails: Use e.g. DFTRACER_PAPI_EVENTS=PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_L1_DCM. Then render with `software_papi_recipe` and validate again.
- `papi_events_named_explicitly` fails: Set DFTRACER_PAPI_EVENTS to a probed set that fits (multiplex=0). Then render with `software_papi_recipe` and validate again.
- `no_papi_multiplex` fails: Unset DFTRACER_PAPI_MULTIPLEX and split the counters into one run per fitting set. Then render with `software_papi_recipe` and validate again.
- `papi_budget_checked` fails: Run `papi_avail -a | head -25` on the compute node and read 'Number Hardware Counters'. Then render with `software_papi_recipe` and validate again.
- `papi_on_compute_node` fails: Run the probe and the real run on compute nodes (flux run / srun inside an allocation). Then render with `software_papi_recipe` and validate again.
- `no_old_papi_categories` fails: Filter cat == "papi" and use the event name as the family. Then render with `software_papi_recipe` and validate again.
- After every PAPI run, read args.multiplex and the landed PAPI_* keys; if multiplex=1 or keys are missing, split the set and re-run before reporting numbers.

## Self-heal
- On any multiplex=1 or missing counter: split the set along family lines, re-probe each on a compute node, and only then launch the sweep.
- On a build whose detected counter list is suspiciously short (two counters), suspect the PAPI module (rocp_sdk crash) before the hardware.

## Self-learn
- Record per-system counter budgets (hardware counters, preset count, DFTRACER_PAPI_FITTING_COUNTERS) and measured exact partitions here, tagged with system, PAPI version and date.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_papi via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, Sapphire Rapids matrix-class, PAPI 5.6.0.0) exact 2-run partition, multiplex=0, nothing missing: set1 PAPI_BR_UCN,PAPI_BR_CN,PAPI_BR_TKN,PAPI_BR_NTK,PAPI_BR_MSP,PAPI_BR_PRC,PAPI_BR_INS,PAPI_TOT_INS,PAPI_TOT_CYC,PAPI_REF_CYC; set2 PAPI_FP_INS,PAPI_VEC_INS,PAPI_FP_OPS,PAPI_SP_OPS,PAPI_DP_OPS,PAPI_VEC_SP,PAPI_VEC_DP.
- (undated, MI300A compute node) PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS: multiplex=0, all four landed.
- (undated, miniFE 4 nodes x 4 ranks nx=768, 30 counters) family-grouped layout: PAPI events per rank 56,840 -> 11,223 (-80.3%), raw bytes -16.6%, compacted -21.7%.

## Source: dftracer-agents `software-papi` (verbatim, headings demoted)
_Original description:_ PAPI hardware-counter tracing with dftracer — how many counters actually fit, why derived presets silently multiplex or get dropped, how to build an exact counter partition across runs, and how to VERIFY exactness from the trace instead of assuming it. Load this for any DFTRACER_ENABLE_PAPI_TRACING work.

### software-papi

PAPI exposes hardware performance counters as portable *preset* names (`PAPI_TOT_CYC`,
`PAPI_L1_DCM`, ...). dftracer samples them on a timer thread and writes them into the
trace. The entire difficulty is that **the number of counters you can ask for is not the
number of names you list**, and getting it wrong degrades data silently.

Related: [[system-tuolumne]] (version pin + this node's counter budget),
[[workload-minife]], [[dftracer-trace-utils]].

#### Rule 0 — hardware counters, not counter names

```bash
papi_avail -a | head -25        # "Number Hardware Counters : N"
```

That `N` is the real budget. On an MI300A node it is **5**, while `papi_avail` lists
**30 presets**. Ask for more than fits and PAPI *time-shares* (multiplexes) them: each
counter is only live part of the time and the reported value is scaled up. dftracer says
so explicitly:

> `PAPI: N counters were requested but this machine has M hardware counters, so they are
> time-shared and every multiplexed reading is a scaled estimate (measured error 1% to 6%,
> worse on a workload with phases).`

1-6% error sounds tolerable until you remember it is **biased, not noisy**, and worst on
phase-changing workloads — which is most real applications (setup phase, then solve phase).

#### Rule 1 — a DERIVED preset costs more than one counter

This is the trap. `papi_avail -a` has a `Deriv` column:

```
PAPI_BR_MSP  0x8000002e  No   Conditional branch instructions mispredicted
PAPI_BR_PRC  0x8000002f  Yes  Conditional branch instructions correctly predicted
```

`Deriv Yes` means the preset is *computed* from two or more native events (here
`BR_PRC = BR_INS - BR_MSP`). It therefore consumes **two or more** of your hardware
counters, not one.

Consequence: **sizing a set by counting names is wrong.** Measured on MI300A with a
5-hardware-counter budget, this 5-name set multiplexed anyway because three of its members
are derived:

```
PAPI_BR_MSP, PAPI_BR_PRC(D), PAPI_FP_OPS, PAPI_FP_INS(D), PAPI_FMA_INS(D)   -> multiplex=1
```

Worse, dftracer **dropped `PAPI_BR_PRC` entirely** rather than report nonsense:

> `PAPI counter PAPI_BR_PRC is one native event subtracted from another and the PAPI family
> does not fit this machine; dropping it, because time-sharing the two would report
> impossible values such as a negative count`

So that run produced a healthy-looking trace with 4 of 5 requested counters, all of them
estimates. Nothing failed. Nothing was zero-byte. The exit code was 0.

Note the derived cost is not uniformly 2 — some derived presets still fit. `PAPI_L2_ICM`
and `PAPI_L2_TCM` (both derived) fit fine alongside three native counters; four derived
FLOP presets did not. **Do not compute the cost — measure it (Rule 3).**

#### Rule 2 — one run per set, named explicitly

The supported way to get exact counts for more counters than fit is one run per set:

```bash
export DFTRACER_ENABLE_PAPI_TRACING=1
export DFTRACER_PAPI_EVENTS=PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_L1_DCM
export DFTRACER_PAPI_SAMPLE_INTERVAL_MS=100
```

`DFTRACER_PAPI_EVENTS` takes a plain comma- or semicolon-separated list of preset names
(no family prefix — dftracer groups by family internally so a family is read at one
instant). It overrides the build-time `DFTRACER_PAPI_DETECTED_EVENTS` default.
`DFTRACER_PAPI_MULTIPLEX` exists if you deliberately want time-sharing.

Design the partition so that families stay together where possible, and keep a shared
reference counter (`PAPI_TOT_CYC`) in every set if you intend to normalize across runs —
that costs one slot per set but makes counters from different runs comparable per-cycle.

#### Rule 3 — PROBE cheaply, then commit

Do not reason about how many native events a set expands into. Run the app for a few
seconds at toy size with the candidate set and read `args.multiplex` back out. On miniFE a
`nx=64`, 1-rank probe takes ~1 s and settles the question definitively. Probing four
candidate sets took under a minute and turned a broken partition into an exact one.

#### Rule 4 — VERIFY exactness from the trace, never from the request

Two independent things must be checked, because each can fail silently:

```python
# per app trace
a = event.get("args") or {}
a["multiplex"]          # 0 = exact hardware count, 1 = scaled estimate
[k for k in a if k.startswith("PAPI_") and not k.endswith("_delta")]   # what LANDED
```

* `multiplex == 1` anywhere in a run means that run's numbers are estimates — do not quote
  them as measurements.
* The counter names present may be a **subset** of what you asked for (Rule 1). Compare
  against the requested set explicitly.

dftracer records each counter twice per sample: the raw `PAPI_X` cumulative value and a
`PAPI_X_delta` since the previous sample.

#### Rule 5 — probe on a COMPUTE node; a login-node probe reports the wrong verdict

`multiplex` is a property of the machine the counters are programmed on, not of
the request. The identical 4-name set
`PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS` measured, same binary, same
env, same day:

| where | `args.multiplex` |
| --- | --- |
| login node | **1** (MULTIPLEXED — scaled estimates) |
| compute node (MI300A, inside an allocation) | **0** (EXACT) |

All four names landed in both cases, so the counter list looks identical and
only the `multiplex` field distinguishes a measurement from an estimate. A
cheap login-node probe will therefore condemn a set that is actually exact on
the hardware you care about — and, in the other direction, could bless one that
is not. Read `multiplex` back out of a trace produced by the real run on the
real node, never from a convenience probe elsewhere.

#### Counter layout: per-counter vs family-grouped

dftracer changed from emitting **one event per counter per sample** to **one event per
counter family per sample**, with every counter in that family packed into `args` as
`value` + `_delta` pairs. Measured on miniFE at 4 nodes x 4 ranks, `nx=768`, same node set,
same 30 counters:

| per rank | per-counter | family-grouped | change |
| --- | ---: | ---: | ---: |
| PAPI events | 56,840 | 11,223 | **-80.3%** |
| app bytes (raw) | 929,972 | 775,296 | -16.6% |
| compacted bytes | 1,464,837 | 1,147,354 | -21.7% |
| counters captured | 30 | 30 | 0% |

Events drop far faster than bytes because the saving is per-event JSON envelope, not
counter payload.

**Breaking change for downstream tooling:** the old per-family categories `CACHE`, `FLOP`,
`BRANCH`, `TLB`, `INSTRUCTION`, `CYCLE` no longer exist as `cat` values. The family is now
the event **`name`** under a single `cat == "papi"`. Any analysis filtering on those
categories silently reads zero.

#### Teardown hazards

1. **PAPI sampler vs dftracer's own GOTCHA interception.** The sampler thread calls
   `PAPI_read()`, which reads its perf_event fd with `read(2)` — a call dftracer itself
   intercepts. If the sampler is stopped *after* `posix_instance->unbind()`, the next
   sample dies in `gotcha_get_wrappee()`. Fixed upstream by finalizing the sampler first;
   confirm the ordering in `DFTracerCore::finalize()` on whatever branch you build, because
   a branch carrying PAPI support does not necessarily carry this fix.
2. **A crash after the work finishes still costs you data.** It is a race, so it looks
   size-dependent: short runs exit between ticks and survive; long runs land inside
   `PAPI_read` and die. Always count zero-byte traces AND check the trailing `end` event.

#### Site pin

Use the PAPI version [[system-tuolumne]] pins (`papi/7.2.0.2`). The newest module there
(`7.3.0.1`) ships a `rocp_sdk` component that is ABI-incompatible with the installed ROCm
and SIGSEGVs inside `PAPI_library_init` — which kills both dftracer's build-time counter
probe (silently falling back to two counters) and the traced application.

---

#### Worked example: deriving an EXACT partition on an Intel Sapphire Rapids node

A concrete instance of this skill's central rule — *never size a counter set by
counting names, always read `args.multiplex` back out of the trace*.

**The node** (`matrix`-class, 2 × Xeon Platinum 8480+, system PAPI 5.6.0.0):
19 hardware counters, **17 presets available**, and the build-time probe
reported **only 10 of them fit at once** (`DFTRACER_PAPI_FITTING_COUNTERS 10`).
This is a different ceiling from the ~30 presets an MI300A/Cray node reports —
**a counter plan is not portable between systems and must be re-derived.**

The 17, as the build probe grouped them:

| group | presets |
|---|---|
| BRANCH (7) | `PAPI_BR_UCN, BR_CN, BR_TKN, BR_NTK, BR_MSP, BR_PRC, BR_INS` |
| INSTRUCTION (1) | `PAPI_TOT_INS` |
| CYCLE (2) | `PAPI_TOT_CYC, PAPI_REF_CYC` |
| FLOP (7) | `PAPI_FP_INS, VEC_INS, FP_OPS, SP_OPS, DP_OPS, VEC_SP, VEC_DP` |

##### Asking for all 17 does not error — it multiplexes AND silently drops two

```
MULTIPLEXED  samples=17 mux=[1] want=17 got=15 missing=['PAPI_BR_UCN','PAPI_BR_PRC']
```

Two counters vanish from the trace entirely, and the other 15 become scaled
estimates. Nothing in the exit status or stderr says so. This is the exact
failure the "do not over-ask" rule exists to prevent.

##### The measured exact partition — 2 runs, `multiplex=0`, nothing missing

```
set1_branch_cycle : PAPI_BR_UCN,PAPI_BR_CN,PAPI_BR_TKN,PAPI_BR_NTK,PAPI_BR_MSP,
                    PAPI_BR_PRC,PAPI_BR_INS,PAPI_TOT_INS,PAPI_TOT_CYC,PAPI_REF_CYC   (10)
set2_flop         : PAPI_FP_INS,PAPI_VEC_INS,PAPI_FP_OPS,PAPI_SP_OPS,
                    PAPI_DP_OPS,PAPI_VEC_SP,PAPI_VEC_DP                              (7)
```

Note the counter-intuitive result that made probing essential: a **4-name** set
(`TOT_INS,TOT_CYC,FP_OPS,DP_OPS`) came back **MULTIPLEXED**, while the **10-name**
set1 and the **7-name** set2 both came back **EXACT**. Derived presets expand to
several native events, and mixing across groups overflows in ways name-counting
cannot predict. Group-aligned sets fit; arbitrary small mixtures may not.

##### The probe harness

Run the real application briefly under each candidate set and classify from the
trace, not from the exit code:

```python
ks = [k for k in args if k.startswith('PAPI_') and not k.endswith('_delta')]
# EXACT  <=> multiplex == 0 AND every requested preset appears in the trace
```

A run reporting `mux=[0]` and `missing=[]` is the only evidence that a set is
exact. Budget one such probe per candidate set before committing to a sweep —
it is minutes of work against hours of unusable counter data.
