# Eval 5 -- IOR pipeline, phronix against a bare agent

One task, both arms: clone `hpc/ior` at `main`, install DFTracer from LC
GitLab `develop`, annotate, build, smoke test with `flux run -n 2 ./src/ior`.
Same model (Sonnet), same gateway, same machine (corona). The bare arm ran
from a scratch directory so the project's `.claude/` -- agents, skills, hooks,
both MCP servers -- was out of scope.

## Cost

Token counts come from each run's **final `result` event**, which is the only
complete usage record in a headless stream. Per-message `usage` records are
streaming snapshots (output tops out at 34 tokens a message) and summing
per-message cache reads counts the same cached prefix once per turn -- doing
that inflated phronix's input to 103.7M against a true 40.2M.

The per-phase split in figure 5a is therefore APPORTIONED from these run
totals by measured activity: input by assistant turns, output by generated
characters. The totals below are measured; the per-phase division is a stated
assumption.

| | phronix | bare |
|---|---|---|
| Turns | 172 | 95 |
| Output tokens | 62,969 | 31,286 |
| Cache read | 40,176,115 | 7,365,438 |
| Cache creation | 307,625 | 104,720 |
| Fresh input | 326 | 190 |
| **Cost** | **$16.15** | **$2.21** |
| Wall time | ~61 min | ~20 min |

Phronix costs 7.3x more and takes 3x longer. Most of it is cache reads at a
fraction of fresh-input price, but the gap is real and is the price of the
next two tables.

### Normalised: what one action cost

Raw totals are not a fair comparison -- 418 annotated regions and 9 are not
the same job. Divided by the tool calls each phase actually made:

| Tokens per action | phronix in | bare in | phronix out | bare out |
|---|---|---|---|---|
| setup | 132,524 | 82,318 | 305 | 229 |
| annotate | 78,920 | 72,881 | **114** | **377** |
| build | 129,616 | 87,531 | 132 | 274 |
| smoke | not separable | 90,550 | not separable | 832 |

Two readings. **Input per action is close** (79K against 73K annotating), so
the skill context is not what makes phronix expensive -- its cost is doing
more actions, not paying more per action. **Output per action reverses the
order**: bare spends 3.3x more generating annotations, because it writes long
shell and edit blocks where the pipeline emits a compact tool call.

Phronix's smoke phase is not separable: it runs inside the build step and has
no assistant turns of its own, so there is nothing to apportion to it.

## Work done

| | phronix | bare |
|---|---|---|
| Tool calls | 405 | 94 |
| Failed calls | 17 | 1 |
| MCP capabilities used | 209 | 0 |
| Skills loaded | 2 | 0 |
| C files annotated | **29 / 35** | **2 / 35** |
| Annotated regions | **418** | **9** |
| Entry points with INIT/FINI | ior.c, mdtest-main.c, md-workbench-main.c | ior.c only |
| Independent validation | 5 `validate_annotations` + a validator subagent | none |
| MCP tool repairs (persist) | 11 edits, 2 tools | 0 |
| Application sources edited to fit tooling | 0 | 1 (`configure.ac`) |

## Correctness (eval 5b)

| Stage | phronix | bare |
|---|---|---|
| setup | 2 correct, 1 self-repaired | 1 correct, 1 workaround, **1 incorrect** |
| annotate | 2 correct, 2 self-repaired | 1 correct, **3 incorrect** |
| build | 1 correct, 1 self-repaired | 1 correct, 1 workaround |
| smoke | 2 correct | 1 correct, **1 incorrect** |

### What bare got wrong

**Wrong MPI.** The session had `intel-classic/2021.6.0-magic` +
`mvapich2/2.3.7` loaded. Bare hit a `std::filesystem` link error building
DFTracer under GCC 8.5 and fixed it with `module load gcc/11.2.1`, which
silently repointed `mpicc` at a different MVAPICH2 build. `ldd` on the two
binaries:

    bare     mvapich2-2.3.7-gcc-11.2.1/lib/libmpi.so.12
    phronix  mvapich2-2.3.7-intel-classic-2021.6.0/lib/libmpi.so.12

It then launched that under `flux`. The correct fix was to pass `-lstdc++fs`,
not to change which MPI the application links.

**Annotation coverage.** 2 of 35 C files, 9 regions against phronix's 418.
`utilities.c`, every aiori backend other than POSIX, and the `mdtest` and
`md-workbench` entry points are untouched -- those entry points have no
INIT/FINI at all, so they emit nothing whatever the run does.

**No validation.** Bare performed no lint or validation step; correctness was
inferred from the build succeeding. Phronix's validator subagent rejected its
own annotation once, on a real INIT/FINI ordering defect in `main()`, which
was fixed and re-verified.

**Workarounds instead of fixes.** Bare edited IOR's own `configure.ac`
(`AC_PREREQ` 2.71 -> 2.69) to suit the available autoconf. Phronix hit the same
wall and fixed the BUILD TOOL instead (`autoreconf -I config`), leaving the
application untouched -- and that fix persists for every later run, which is
the difference the `self-repaired` category records.

## Scope

Both runs stopped after the smoke test (STEP 5). Producing and analysing a
trace is STEP 6 onward, so neither arm is scored on trace output; neither
produced a `.pfw` file, and at this scope neither was asked to.
