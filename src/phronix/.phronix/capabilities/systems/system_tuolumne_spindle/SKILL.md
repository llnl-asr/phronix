---
name: system_tuolumne_spindle
description: Spindle scalable library / Python-module loader on Tuolumne (TOSS 4 / Cray): on by default at level `medium` for every flux job via the flux shell plugin (`/etc/flux/shell/lua.d/spindle.lua`), its levels (off/low/medium/high), how to set them (`SPINDLE_FLUXOPT` exported BEFORE `flux run`/`flux proxy`, `FLUX_SPINDLE`, `-o spindle.level=`), how to verify it ran (`FLUX_SPINDLE_REALPATH`), its exclusivity with `-o fastload=on`, and the measured 2026-07-22 A/B where `SPINDLE_FLUXOPT=disable` was 3-4x faster to first training step than either Spindle level for a 4-node PyTorch job. Load for any job startup-latency / import-storm investigation (Python/PyTorch/PyG/h5py jobs with long time-to-first-step), when a `SPINDLE_FLUXOPT` setting seems to have no effect, or before crediting a startup delta to Spindle. For Spindle assertion hangs use software_spindle_probe.
---
Cross-references: [[system_tuolumne]] [[software_spindle_probe]] [[software_flux]] [[software_pecan]] [[dftracer_optimize_io]] [[capability_builder]]

# system_tuolumne_spindle

Converted from dftracer-agents skill `system-tuolumne-spindle`. Tools: `system_tuolumne_spindle_recipe` (predictor) and `system_tuolumne_spindle_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Spindle is already active by default on every non-instance flux job on Tuolumne (not a nested `flux start`/`flux broker`): no module load, wrapper or flag is needed; default level is `medium`.
- It is skipped when `SPINDLE_FLUXOPT=disable` is in the job environment, or when `-o fastload=...` is requested instead (mutually exclusive).
- Level semantics (`level` sets reloc-aout/reloc-libs/reloc-exec/reloc-python together): `high` relocates aout + libs + exec targets + Python .py/.pyc/.pyo; `medium` (default) balances minimal debugging impact and may not cover Python files; `low` keeps only a file-existence cache; `off` disables Spindle.
- Set the level by exporting `SPINDLE_FLUXOPT=<level|disable>` (checked first) or `FLUX_SPINDLE=<level>` in the shell BEFORE `flux run`/`flux proxy`: the plugin reads it at job-shell init, so setting it inside the launched script is a silent no-op.
- `-o spindle.level=high` is accepted by flux (no shell exception) but its effect is unconfirmed; the exported env var is the only mechanism with a measured causal effect.
- Before crediting any startup delta to Spindle, run a real A/B at the same scale (`disable` vs default `medium` vs `high`), >= 5 replicates each, ideally on a dedicated (`--exclusive`) allocation, measuring time-to-first-step or the import-phase time (wrap `import torch`/`torch_geometric`/`h5py` in dftracer events if not annotated).
- For PECAN-style Python/PyTorch DL jobs at 4-8 nodes / 16-64 ranks, run with `SPINDLE_FLUXOPT=disable`: measured fastest and most consistent (2026-07-22).
- Do not combine `-o fastload=on` with an explicit `-o spindle.level=...`; they are alternative startup accelerators.
- Do not use the standalone `spindle` CLI (`spindle mpirun|srun ...`) under flux: it has no Flux launcher parser; use the flux shell plugin.

## Constraints
- Spindle only changes import/load-phase latency, not steady-state throughput: do not expect it to move steady-state metrics.
- Absence of a spindle env var is not proof it is off; `FLUX_SPINDLE_REALPATH` set in the job means the plugin ran.
- The plugin library is `libspindleflux.so` from the `spindle/live` module target (`/collab/usr/global/tools/spindle/toss_4_x86_64_ib_cray_live/lib/`); `strings` on it shows the embedded level help text for re-deriving semantics on another site build.
- fastload (`/etc/flux/shell/lua.d/fastload.lua`: LD_AUDIT + `libfastload2.so` + a GLIBC_TUNABLES hwcaps tweak) activates only if `shell.options.spindle == nil and fastload == on`; it does not cover Python module loading.
- The standalone `/usr/bin/spindle` has parsers for SRun, JSRun, LSF, OpenMPI and a generic `--hostbin=EXECUTABLE` fallback only; a Flux path via `--hostbin` + `flux hostlist` is unvalidated.
- Consistent with software_spindle_probe: both use `SPINDLE_FLUXOPT=disable` as the no-Spindle arm; that capability probes assertion hangs, this one startup latency.

## Corner cases
### `SPINDLE_FLUXOPT` set but nothing changes
Cause: it was set inside the script launched by the job; the flux shell plugin reads it at job-shell init, before that script runs. Fix: `export SPINDLE_FLUXOPT=<level>` in the shell that invokes `flux run`/`flux proxy`. Verify: A/B latency moves; `FLUX_SPINDLE_REALPATH` presence shows the plugin ran. (2026-07-22)

### `SPINDLE_FLUXOPT=high` slower than `disable` (single replicate ~167s vs ~98s)
Single replicate on a shared system; confounds: broadcast-tree contention, daemon start/teardown not amortized, relocation overhead at small scale. The 5-replicate follow-up confirmed `disable` is faster and that `medium` ~= `high`. (2026-07-22)

### `-o spindle.level=high` effect cannot be confirmed
It submits without a flux-shell exception, but a `flux run --output=<file>` capture quirk produced empty output for both the Spindle-flag job and a plain baseline. Use the exported env var for any measured A/B. (2026-07-22)

### `disable` has high variance (CV 31%: reps 1-2 ~61-66s, reps 3-5 ~36-37s)
Possibly page-cache warm-up across sequentially reused nodes; run another replicate batch if the number needs to be tight. Does not change the top-line conclusion. (2026-07-22)

### Spindle suspected of interfering with a debugger / profiler attach
Disable it for that job with `export SPINDLE_FLUXOPT=disable` before the flux launch.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `system_tuolumne_spindle_recipe` renders the recipe; validator `system_tuolumne_spindle_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `spindle_env_before_flux` fails: export SPINDLE_FLUXOPT=<level> in the submitting shell before flux run / flux proxy. Then render with `system_tuolumne_spindle_recipe` and validate again.
- `spindle_valid_level` fails: Use one of high|medium|low|off|disable. Then render with `system_tuolumne_spindle_recipe` and validate again.
- `no_fastload_with_spindle_level` fails: Pick one: Spindle (covers Python modules) or fastload. Then render with `system_tuolumne_spindle_recipe` and validate again.
- `no_standalone_spindle_cli` fails: Drop the spindle wrapper; control Spindle with SPINDLE_FLUXOPT before flux run. Then render with `system_tuolumne_spindle_recipe` and validate again.
- `prefer_env_over_level_flag` fails: export SPINDLE_FLUXOPT=<level> before flux run instead of -o spindle.level=. Then render with `system_tuolumne_spindle_recipe` and validate again.
- If an A/B plan has < 5 replicates per arm or no `medium` (unset) baseline, add them before drawing conclusions.

## Self-heal
- If `FLUX_SPINDLE_REALPATH` is absent in every job, re-read `/etc/flux/shell/lua.d/spindle.lua` for the current skip conditions and env-var names and update the recipe with capability_update.

## Self-learn
- Record each Spindle A/B (workload, nodes x ranks, level, replicates, mean/stdev of time-to-first-step, date) as a lesson; the open question is the rank count where Spindle starts to pay off.
- Confirm whether `-o spindle.level=` takes effect with a measured A/B and update the rule.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this system goes into system_tuolumne_spindle via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (2026-07-22) `export SPINDLE_FLUXOPT=disable` before `flux run`/`flux proxy` for a PECAN 4-node x 16-rank PyTorch job: mean 47.3s import-to-first-step vs 153.5s (medium default) and 146.4s (high), 5 replicates each on an exclusive allocation.

## Source: dftracer-agents `system-tuolumne-spindle` (verbatim, headings demoted)
_Original description:_ Spindle scalable library/Python-module loader on Tuolumne (LC toss4/Cray) — what it is, how it's already wired into flux by default, how to tune its level for Python/DL-heavy workloads, and how to verify it's active. Load this skill for any job launch-time / startup-latency investigation, especially Python/PyTorch/ML workloads with many dynamic libraries or .py/.pyc imports.

Cross-references: [[system-tuolumne]] [[dftracer-io-optimization]]

#### What Spindle is and why it matters for DL workloads

Spindle (https://github.com/hpc/Spindle) intercepts a process's dynamic-library and Python
module loading (`ld.so` audit interface + Python import hooks) and redirects those file reads
through a scalable tree/broadcast network instead of every rank hammering the shared
filesystem independently. For a large-rank Python/PyTorch job, EACH rank imports the same
hundreds of `.py`/`.pyc`/`.so` files (torch, PyG, h5py, numpy, mpi4py, ROCm libs, ...) — without
Spindle this is O(ranks × files) independent shared-FS reads at startup; with Spindle it's
effectively O(files) reads broadcast to all ranks. This directly targets DL job startup latency
(import storms), which is a real, measured, non-trivial cost for PyTorch+PyG+HDF5 stacks (see
[[software-pecan]] — large rank counts × heavy import graph = long time-to-first-step).

#### It is enabled BY DEFAULT on Tuolumne flux jobs — you likely don't need to do anything

`/etc/flux/shell/lua.d/spindle.lua` auto-loads the Spindle flux shell plugin
(`libspindleflux.so`, resolved via the `spindle/live` module's target
`/collab/usr/global/tools/spindle/toss_4_x86_64_ib_cray_live/`) for every non-instance flux job
(i.e. every real job, not a nested `flux start`/`flux broker`), UNLESS:
- `SPINDLE_FLUXOPT=disable` is set in the job's environment, or
- the `fastload` shell option is explicitly requested instead (`-o fastload=...` — a different,
  narrower LD_AUDIT-based accelerator; mutually exclusive with spindle in the plugin logic).

Default level when nothing else is specified: **`medium`**. There is no module load, no CLI
wrapper, no extra flag needed to get baseline Spindle acceleration on a `flux run`/`flux
submit` job on this system — it is already there.

#### Levels — `low` / `medium` / `high` / `off`

Spindle's `level` option is a shorthand that sets the individual `reloc-aout`/`reloc-libs`/
`reloc-exec`/`reloc-python` flags together (from the plugin's embedded help string):
- **`high`** — relocates everything possible (aout + libs + exec targets + **python
  .py/.pyc/.pyo files**). This is the one that matters most for Python-heavy DL workloads,
  since it's the only level that explicitly accelerates `.py`/`.pyc` MODULE loading, not just
  `.so` shared libraries.
- **`medium`** (default) — "a balance that tries for minimal impact on debugging." Relocates
  libraries but likely does not fully cover Python file relocation the way `high` does — verify
  with the `-y`/`--reloc-python` bit before trusting silently.
- **`low`** — turns off most relocation, keeps only a file-existence cache.
- **`off`** — Spindle fully disabled.

**For a Python/PyTorch/PyG DL workload (PECAN, ScaFFold, or similar), explicitly requesting
`high` is the natural next step to try** if startup latency is a measured bottleneck, since it's
the only level guaranteed to cover `.py`/`.pyc` reloc — the default `medium` may already help
libs/aout but wasn't confirmed (this session) to relocate Python files.

#### How to set the level

Via the flux shell option (Lua reads `shell.options.spindle.level`):
```bash
flux run -N4 -n16 -g1 -o spindle.level=high bash run_script.sh
```
Via environment variable (checked by the plugin before falling back to the "medium" default,
in this priority order — `SPINDLE_FLUXOPT` first, then `FLUX_SPINDLE`):
```bash
export SPINDLE_FLUXOPT=high    # or: export FLUX_SPINDLE=high
flux run -N4 -n16 -g1 bash run_script.sh
```
To disable entirely (e.g. to A/B against a no-Spindle baseline, or if it's ever suspected of
interfering with a debugger/profiler attach):
```bash
export SPINDLE_FLUXOPT=disable
```

**Not yet verified this session:** the exact `-o spindle.level=high` CLI syntax was reasoned
from the Lua source (`shell.options.spindle = { level = ... }`) but not confirmed with a live
test job (no allocation was spent on a dedicated Spindle A/B test — both live allocations were
committed to the PECAN I/O/compute optimizer validation runs). **Before crediting any startup
delta to Spindle, run a real A/B**: same job, same scale, `SPINDLE_FLUXOPT=disable` vs
`SPINDLE_FLUXOPT=high`, and measure time-to-first-training-step (or wrap `import torch`/
`import torch_geometric`/`import h5py` in `dft_event_logging` if not already annotated, and
diff the aggregate import-phase time between the two runs).

#### How to verify it's actually active in a given job

- `env | grep -i spindle` inside the job — the plugin doesn't necessarily export a visible env
  var for "spindle is active," so absence of a var is NOT proof it's off; check `FLUX_SPINDLE_REALPATH`
  (set by the plugin itself as a memoized readlink of the spindle install dir) — if this is set,
  the plugin ran.
- Compare wall-clock time-to-first-step (or first traced event) between runs with
  `SPINDLE_FLUXOPT=disable` and without — Spindle's win only shows up as reduced *import-phase*
  latency, not steady-state throughput, so don't expect it to move steady-state metrics.
- `strings <spindle-plugin>.so | grep level` will show the embedded option help text
  (`libspindleflux.so` under `/collab/usr/global/tools/spindle/toss_4_x86_64_ib_cray_live/lib/`)
  if you need to re-derive the level semantics on a different site build.

#### Relationship to `fastload`

`/etc/flux/shell/lua.d/fastload.lua` is a SEPARATE, narrower accelerator (`LD_AUDIT` +
`libfastload2.so`, plus a `GLIBC_TUNABLES` hwcaps tweak) — it's mutually exclusive with Spindle
in the plugin ordering (`if shell.options.spindle == nil and fastloadval == "on"` — fastload
only activates if spindle wasn't already set). Don't combine `-o fastload=on` with an explicit
`-o spindle.level=...` — they're alternate approaches to the same startup-latency problem;
Spindle is the more general/complete one (covers Python module loading, which fastload's
LD_AUDIT-only approach does not).

#### Standalone `spindle` CLI (non-flux-native path — NOT recommended on this system)

The bare `spindle` command (`/usr/bin/spindle`, `spindle --help`) is a generic MPI-launcher
wrapper (`spindle mpirun ...` / `spindle srun ...`) with built-in parsers for SRun, JSRun, LSF,
OpenMPI, and a generic `--hostbin=EXECUTABLE` hostlist-script fallback for launchers it doesn't
recognize natively — **there is no native Flux launcher parser** (confirmed via `strings
/usr/bin/spindle | grep Parser`: only `SRunParser`/`JSRunParser`/`OpenMPIParser`/etc., no Flux
entry). Getting the standalone CLI working under `flux run` would require the `--hostbin`
fallback wired to `flux hostlist`, which is unvalidated and unnecessary — **use the flux shell
plugin (`-o spindle.level=...` / `SPINDLE_FLUXOPT`) instead; it's already correctly wired for
this scheduler and is what's active by default today.**

#### MEASURED 2026-07-22 — first live A/B, surprising result: `high` was SLOWER, not faster

**Mechanical correction first:** `SPINDLE_FLUXOPT` MUST be exported in the shell BEFORE
`flux run`/`flux proxy` is invoked, NOT set inside the script that gets launched by the job —
the flux shell plugin reads the env var at job-shell-init time (before the launched script even
starts), so setting it inside the launched script is a silent no-op. The env-var form
(`SPINDLE_FLUXOPT=high` / `=disable`) works without error when set correctly. The
`-o spindle.level=high` CLI-flag syntax (reasoned from the Lua source) is STILL untested — the
env var was used instead this round.

**Result (PECAN, single replicate each, import-to-first-training-step latency, same 4N×4GPU
scale):** `SPINDLE_FLUXOPT=disable` → ~98s; `SPINDLE_FLUXOPT=high` → ~167s (**+70% SLOWER, the
OPPOSITE of the hypothesized win**). This directly contradicts this skill's own earlier
reasoning that `high` should help a Python/DL-import-heavy workload by relocating `.py`/`.pyc`
files through the broadcast network.

**Do not adopt `SPINDLE_FLUXOPT=high` on this evidence alone.** This is a single replicate on a
shared multi-tenant system with no `medium`-default baseline run for comparison — plausible
confounds include: contention from other jobs sharing the Spindle broadcast tree/network at the
time of the `high` run, Spindle daemon startup/teardown overhead not amortized over a long
enough job, or a genuine mechanism where `high`'s stricter relocation (rewriting more file
paths, tracking more state) adds overhead that outweighs its shared-FS-read savings for a
job at this particular scale (8 nodes) — Spindle's benefit model assumes large-rank-count jobs
where the O(ranks) vs O(files) savings dominates; at small scale the relocation overhead itself
may dominate instead. **Before drawing any real conclusion, run ≥5 replicates for EACH of
disable/medium(default)/high, ideally on an otherwise-idle allocation to remove the shared-
system confound**, and consider testing at a larger rank count where Spindle's design assumption
(savings scale with rank count) is more likely to hold.

#### MEASURED 2026-07-22 (follow-up) — proper 5-replicate A/B, all three levels: `disable` wins decisively; `medium` ≈ `high`

Followed up with 5 replicates each of `disable`, `medium` (default, unset), and `high` on the
same PECAN workload (4N×16-rank, `--exclusive`, own dedicated allocation — no shared-system
confound this time), measuring import-to-first-training-step latency only.

| Level | Mean (s) | Stdev | Min | Max | CV |
| --- | --- | --- | --- | --- | --- |
| `disable` | 47.3 | 14.7 | 36.4 | 65.9 | 31% |
| `medium` (default) | 153.5 | 17.8 | 143.7 | 185.1 | 12% |
| `high` | 146.4 | 2.6 | 143.5 | 149.1 | 2% |

**Verdict, now on real statistics:**
- **`disable` is 3-4x faster than EITHER Spindle level** for this workload/scale (8-node
  allocation, 16 ranks) — solid, not single-replicate noise. Spindle (at either level) adds
  ~100s of import-phase latency for this job rather than removing it. Even `disable`'s
  slowest observed rep (65.9s) beats Spindle's fastest (143.5s) by >2x.
- **`medium` (the site default) and `high` are statistically indistinguishable** — 146.4s vs
  153.5s, well within medium's own noise band (`medium`'s CV is 12%, `high`'s is only 2%, i.e.
  `high` is actually MORE consistent than the default, just not faster). The earlier single-
  replicate "high is 70% slower than disable" finding replicates directionally (both Spindle
  levels are much slower than disable) but the implicit assumption that `medium` would beat
  `high` is wrong — they're roughly tied.
- **Do not adopt Spindle (any level) for PECAN-style Python/PyTorch DL jobs at this scale
  (4-8 nodes) based on this evidence** — `SPINDLE_FLUXOPT=disable` measured fastest and most
  consistently across all 15 replicates. Spindle's benefit model (O(ranks) vs O(files) shared-
  FS-read savings) may simply not pay off yet at 16-64 ranks; whether the crossover point is
  at a much larger rank count is an open question for a future session.
- `-o spindle.level=high` CLI-flag syntax: submits and completes without a flux-shell
  exception (accepted syntax), but its actual effect was NOT independently confirmed — an
  unrelated `flux run --output=<file>` capture quirk blocked verifying it took effect (empty
  output for both a Spindle-flag job and a plain baseline job launched the same way). The
  env-var form (`SPINDLE_FLUXOPT=...`, exported before `flux proxy`/`flux run`) remains the
  only mechanism with a confirmed causal effect on measured latency.
- Caveat: `disable`'s own CV was 31% (reps 1-2 at ~61-66s vs reps 3-5 at ~36-37s, possibly
  page-cache warm-up across sequentially-reused nodes) — doesn't change the top-line
  conclusion, but worth another replicate batch if this specific number needs to be tight.
