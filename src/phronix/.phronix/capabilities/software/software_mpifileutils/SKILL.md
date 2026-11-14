---
name: software_mpifileutils
description: mpifileutils (dcp, dsync, drm, dwalk, dcmp, dtar, dchmod, dstripe, ddup, dfind, dreln, dbcast, dbz2): MPI-parallel replacements for cp/rsync/rm/find/diff/tar/chmod on Lustre/GPFS/VAST. Load whenever a copy, sync, delete, compare, archive, permission change, restripe or inventory touches more than a few GB or ~10k files on a shared parallel filesystem; on `ml mpifileutils` failing (ambiguous default), a verified move whose `du` byte totals mismatch although file counts match (FAIL verify ... bytes:X/Y), or a drm aimed at a session workspace (blocked by the guard_rm_drm hook).
---
Cross-references: [[system_tuolumne]] [[software_flux]] [[tools_dftracer_utils]] [[dftracer_profiling]] [[software_hdf5]] [[capability_builder]]

# software_mpifileutils

Converted from dftracer-agents skill `software-mpifileutils`. Tools: `software_mpifileutils_recipe` (predictor) and `software_mpifileutils_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Use the mpifileutils equivalent instead of the serial tool whenever an operation touches more than a few GB or more than ~10k files on a shared parallel filesystem; below that the serial tool wins (MPI launch overhead).
- Load with a pinned version: `module load mpifileutils/0.12` (0.11.1 and 0.12 exist; `ml mpifileutils` alone fails - ambiguous default).
- Launch every tool through the scheduler: `flux run -n <N> -q pdebug <tool> [flags] <args>`. -n 8 to -n 16 is plenty for TB-range metadata/copy work; use a real allocation only for >10 TB or >10M-file trees.
- Scope first with `dwalk --text <tree>` on an unknown tree (file count, total size) before choosing scale; cache the walk with --output/--input for reuse by dcp/dsync/drm/dfind.
- Verify, don't assume: `dcmp` after dcp/dsync; `quota -v` / `du -sh` after drm. Exit code 0 is necessary but not sufficient.
- Never verify a cross-filesystem copy by comparing `du` totals (`du -sb` / `--apparent-size` counts directory inodes, which differ per filesystem). Compare regular-file bytes and counts, then `rsync -a --dry-run --itemize-changes src/ dst/` (0 lines matching ^[<>ch] = clean) or `dcmp` at scale.
- Run verification while the source still exists and delete only after it passes; diagnose a mismatch before loosening the check.
- Pre-existing corruption (e.g. traces truncated by a killed run) surfaces at the destination and reads like the copy broke it: distinguish the two before deleting the source (tools_dftracer_utils).
- `drm` only on paths OUTSIDE `workspaces/<session>/` (e.g. /p/lustre5/<user>/...). Workspace-local bulk deletes use ordinary `rm -rf` through the normal permission flow. The PreToolUse hook `.claude/hooks/guard_rm_drm.sh` blocks drm outside the allowed roots (session workspace or /p/lustre5).
- `lfs setstripe` only affects new files; `dstripe` rewrites existing files to a new stripe layout.

## Constraints
- dcp/dsync/dwalk/etc. have no path restriction; only drm (destructive) is restricted.
- Launching via flux run/submit is a job submission, not a raw rm/cp, so it is not subject to the Bash destructive-action classifier the way raw `rm -rf` is.
- Experimental tools (less battle-tested): dgrep, dparallel, dsh, dfilemaker.
- Tool reference source: https://mpifileutils.readthedocs.io/en/v0.11.1/tools.html

## Corner cases
### `FAIL verify ... files:96/96 bytes:69681208681/69681196393` (counts match, bytes differ) (2026-08-27)
Cause: `du -sb --apparent-size` sums directory inodes; NFS reported 20480 B and VAST 8192 B for the same 2-dir tree; 1756 dirs gave a 111 MB phantom delta. Fix: compare `find -type f -printf '%s\n'` sums and counts, then rsync --dry-run --itemize-changes or dcmp. Verify: 0 pending items.

### `ml mpifileutils` fails
Cause: two versions installed, no default. Fix: module load mpifileutils/0.12.

### drm on a session-workspace path is blocked
Cause: guard_rm_drm.sh hook restricts drm to the session workspace or /p/lustre5 roots and policy keeps drm off workspaces. Fix: rm -rf via the normal permission flow, or ask the user.

### Copied traces fail to decompress at the destination
Cause: often pre-existing truncation from a killed run, not the copy. Fix: check the source with dftracer trace utils before deleting it.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_mpifileutils_recipe` renders the recipe; validator `software_mpifileutils_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `pin_mpifileutils_version` fails: module load mpifileutils/0.12 Then render with `software_mpifileutils_recipe` and validate again.
- `launch_via_scheduler` fails: Prefix with flux run -n 8 -q pdebug (or srun on Slurm). Then render with `software_mpifileutils_recipe` and validate again.
- `no_drm_in_session_workspace` fails: Use rm -rf through the normal permission flow for workspace paths; drm only on scratch like /p/lustre5/$USER. Then render with `software_mpifileutils_recipe` and validate again.
- `no_du_byte_verify` fails: Compare find -type f -printf '%s' sums and counts, then rsync --dry-run --itemize-changes or dcmp. Then render with `software_mpifileutils_recipe` and validate again.
- `verify_after_copy` fails: Add flux run -n 16 dcmp <src> <dst> (or rsync -a --dry-run --itemize-changes) before deleting the source. Then render with `software_mpifileutils_recipe` and validate again.

## Self-heal
- If a verify step fails, keep the source, re-run the per-file rsync --dry-run / dcmp to find the real differing files, and only then decide.

## Self-learn
- Record new filesystem-specific verification pitfalls and measured node-count/time for large dcp/dsync/drm runs.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_mpifileutils via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated) dwalk --text to scope -> dcp/dsync at -n 8..16 on pdebug -> dcmp to verify -> drm the source (outside workspaces) -> quota -v.
- (2026-08-27) Cross-filesystem verified move: compare regular-file byte sums + file counts + `rsync -a --dry-run --itemize-changes src/ dst/ | grep -cE '^[<>ch]'` == 0 while the source exists; then delete.

## Source: dftracer-agents `software-mpifileutils` (verbatim, headings demoted)
_Original description:_ > mpifileutils (dcp/dsync/drm/dwalk/dcmp/dtar/dchmod/dstripe/etc.) — parallel, MPI-based replacements for serial Linux filesystem utilities (cp/rsync/rm/ find/diff/tar/chmod) on HPC parallel filesystems. Load this skill whenever a filesystem operation (copy, sync, delete, compare, archive, permission change, restripe, inventory) touches a large (multi-GB to TB-scale) dataset on a cluster/shared parallel filesystem — prefer these over standard serial Linux utilities at that scale.

Cross-references: [[system-tuolumne]] [[dftracer-profiling]] [[feedback_data_cleanup_quota]]

#### Why mpifileutils

Serial Linux utilities (`cp`, `rsync`, `rm -rf`, `find`, `diff -r`, `tar`, `chmod -R`, `du`)
walk a directory tree from a SINGLE client with a SINGLE metadata stream. On a large parallel
filesystem (Lustre, GPFS) with millions of files or TB-scale trees, that single-stream walk is
the bottleneck regardless of how fast the underlying storage is. mpifileutils reimplements the
same operations as MPI programs that parallelize both the directory walk AND the data
movement/metadata-op across many ranks/nodes — the same operation that takes hours serially
often takes minutes with a handful of nodes.

**Rule of thumb: reach for the mpifileutils equivalent instead of the serial tool whenever an
operation will touch more than a few GB or more than ~10k files on a cluster/shared parallel
filesystem.** Below a few GB / a few thousand files, the serial tool's simplicity wins and the
MPI job-launch overhead isn't worth it.

In this harness, launching via `flux run`/`flux submit` is also a normal job submission, not a
raw `rm`/`cp`, so it is NOT subject to the Bash tool's destructive-action permission classifier
the way a raw `rm -rf` sometimes is — an added practical benefit here, not just a performance one.

#### Loading

```bash
module load mpifileutils/0.12    # two versions exist (0.11.1, 0.12) — pin the version,
                                  # `ml mpifileutils` alone fails (ambiguous default)
```

All tools below are then on `PATH` and are launched the same way:

```bash
flux run -n <N> -q pdebug <tool> [flags] <args>
```

`-n 8` to `-n 16` tasks is plenty for most metadata/copy operations in the TB range — these are
mostly metadata/IO-bound, not compute-bound, so they don't need a large allocation. `pdebug`
queue is fine for most invocations; use a real allocation only for very large (>10TB or
>10M-file) trees.

#### Tool reference

Production tools (source: https://mpifileutils.readthedocs.io/en/v0.11.1/tools.html):

| Tool | Replaces | Purpose |
| --- | --- | --- |
| `dcp` | `cp -r` | Parallel copy of files/directory trees. |
| `dsync` | `rsync -a` | Parallel synchronize source → destination (only transfers deltas); `--batch-files` enables checkpoint/restart for very long syncs. |
| `drm` | `rm -rf` | Parallel remove. See restriction section below — the one tool in this set with an extra usage rule in this harness. |
| `dwalk` | `find` + manual summarize | Parallel list/sort/profile a tree — file counts, size histograms, `--output`/`--input` to cache a walk for reuse across dcp/dsync/drm without re-walking, `--sort`, `--text` for human-readable summaries. Use this FIRST to scope an operation before running dcp/dsync/drm on an unknown-size tree. |
| `dcmp` | `diff -r` / `cmp` | Parallel compare contents between two directories or files — use to verify a dcp/dsync copy actually matches the source before trusting it. |
| `dchmod` | `chmod -R` / `chown -R` | Parallel change owner/group/permissions (`--group`, `--mode`). |
| `dtar` | `tar` | Parallel create/extract of tar archives — much faster than serial `tar` for large trees. |
| `dstripe` | `lfs migrate` / manual restripe | Restripe existing files on Lustre in parallel (change stripe count/size after the fact — `lfs setstripe` only affects newly-created files, `dstripe` rewrites existing ones to a new layout). |
| `ddup` | fdupes-style tools | Find duplicate files in parallel across a large tree. |
| `dfind` | `find` | Parallel filtered file search (`--user`, `--size`, `--type`, `--atime`, `--input`/`--output` to reuse a `dwalk` cache). |
| `dreln` | manual symlink fixup | Parallel update of symlinks to point at a new path (e.g. after relocating a tree). |
| `dbcast` | manual copy-to-every-node | Broadcast a single file to every compute node's local storage (e.g. staging a shared input file/container image before a job). |
| `dbz2` | `bzip2`/`bunzip2` | Parallel compress/decompress a single large file with bz2. |

Experimental (available but less battle-tested): `dgrep`, `dparallel`, `dsh`, `dfilemaker`.

##### Practical workflow

1. **Scope first with `dwalk`** on an unfamiliar/large tree — get file count and total size
   before deciding node count or committing to an operation:
   ```bash
   flux run -n 8 -q pdebug dwalk --text /path/to/tree
   ```
2. **Run the actual operation** (`dcp`/`dsync`/`drm`/`dtar`/etc.) at the same or a larger node
   count if `dwalk` showed it's genuinely huge (>10M files or >10TB).
3. **Verify, don't assume** — `dcmp` after a `dcp`/`dsync`, `quota -v` or `du -sh` after a
   `drm`. Job exit code 0 is necessary but not sufficient evidence of correctness at this scale.
   For the copy-verification step itself, do NOT compare `du` totals — see the next section.

#### Never verify a cross-filesystem copy by comparing `du` (2026-08-27, measured)

**Symptom.** A verified move (copy → compare → delete source) reported a byte mismatch on
*every* directory even though file counts matched exactly, so nothing was ever deleted:

```
FAIL verify .../ygm_bench_4n/traces   files:96/96      bytes:69681208681/69681196393
FAIL verify .../h5bench/baseline      files:86167/86167 bytes:42640987464/42529817928
```

**Root cause.** `du -sb --apparent-size` sums **directory inodes as well as file data**, and
different filesystems report directory sizes differently. The same 2-directory tree read
20480 bytes on the NFS workspace and 8192 bytes on the VAST target — a 12288-byte phantom
delta. It scales with directory count, not data: a tree with 1756 directories showed a
111 MB phantom delta. The file data was byte-identical in every case.

**Fix — compare regular-file bytes only, then let rsync do the per-file check:**

```bash
filebytes() { find "$1" -type f -printf '%s\n' | awk '{s+=$1} END{print s+0}'; }

[ "$(filebytes "$src")" = "$(filebytes "$dst")" ]          # data bytes, no dir inodes
[ "$(find "$src" -type f | wc -l)" = "$(find "$dst" -type f | wc -l)" ]
[ "$(rsync -a --dry-run --itemize-changes "$src/" "$dst/" \
       | grep -cE '^[<>ch]')" = 0 ]                        # per-file size+mtime, 0 = clean
```

The `rsync --dry-run --itemize-changes` pass is the strongest of the three and the one worth
keeping: it compares **every file individually** against the still-present source, so a
partial or truncated transfer shows up as a pending transfer. `dcmp` is the mpifileutils
equivalent and is preferable at genuine scale.

**How to apply.**
- Never gate a delete on a `du` comparison across two different filesystems.
- Always run the verification **while the source still exists**, and delete only after it
  passes — a verifier that fails safe (source kept) costs one re-run; one that fails open
  costs the data.
- Expect the first verification pass to be the thing that's wrong, not the data. Diagnose a
  mismatch before "fixing" it by loosening the check.
- Pre-existing file corruption (e.g. traces truncated by a killed run) surfaces at the
  destination and reads like the copy broke it. Distinguish the two *before* deleting the
  source — see [[dftracer-trace-utils]].

#### Restriction: `drm` never targets the session workspace

**Only use `drm` on paths OUTSIDE `workspaces/<session>/`** — e.g. Lustre scratch/output
directories like `/p/lustre5/<user>/...`. Do not run `drm` against anything under the active
session workspace. (This restriction is specific to `drm`/destructive deletes in this harness;
`dcp`/`dsync`/`dwalk`/etc. have no such restriction — use them anywhere large-scale copy/sync/
inventory work is needed, including inside a session workspace.)

**Why:** the session workspace already has a narrower, reviewable Bash permission surface
(`Write(workspaces/*)`, `Edit(workspaces/*)`, explicit `cp`/`mv`/`find` allowlist entries in
`.claude/settings.json`). `drm` is a parallel, MPI-launched bulk-delete with no per-file
confirmation — routing session-workspace cleanup through it would bypass the deliberate safety
surface that scope was designed to have, for no benefit (workspace directory trees in this
harness are small enough that a normal `rm -rf` — approved via the standard permission flow —
is sufficient there).

**How to apply:** before invoking `drm`, confirm the target path resolves outside
`workspaces/<session>/`. If a workspace-local path needs bulk deletion, use ordinary `rm -rf`
through the normal permission flow (or ask the user to run it) instead of reaching for `drm`.
A `PreToolUse` hook (`.claude/hooks/guard_rm_drm.sh`) enforces this restriction for both `rm`
and `drm` — it will block a `drm` call outside the allowed roots (session workspace or
`/p/lustre5`) regardless.

See also [[feedback_data_cleanup_quota]] (quota crisis this tool was introduced to resolve).
