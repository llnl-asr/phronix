#!/usr/bin/env python3
"""The three reported models as one table, regenerated from the runs.

    scripts/model-matrix.py              # print it
    scripts/model-matrix.py --write      # splice it into interesting.md

Hand-maintained run tables go stale the moment a sweep lands, and a stale
table is worse than none: it reads as a record of what happened. So this is
derived every time from the run directories themselves, and written back
between markers so re-running it replaces the table rather than appending a
second one.

Iteration comes from the batch log, which is the only place the two names
meet: a run directory is `claude-<date>-<pid>` and says nothing about which
repeat it is, while the batch is named `livai-5.4-r3` and records the run
directories it started, one per phase. Where no batch log claims a run --
anything launched before the matrix -- the iteration is left blank rather
than guessed.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")
#: The models the paper reports. Others still run; they are not in this table.
MODELS = ["gpt-5.4", "gpt-5.5", "gpt-5.6-sol"]
ARMS = [("claude-bare", "bare"), ("claude-phronix", "phronix")]

#: When learned capabilities stopped being one MCP tool each (`547269e`,
#: "reach learned capabilities through a dispatcher instead of 1150 tools").
#:
#: This is a REUSE-only cutoff, and the asymmetry is the whole reason it
#: exists. Before it, every learned capability was its own tool in the list a
#: task saw. A fresh run starts with an empty store and so saw almost none; a
#: reuse run seeds from the carry store and saw up to 1150. The handicap
#: scaled with the store, which only a reuse run has, so it hit one arm of
#: every pair and not the other -- and it shows: every pre-dispatcher reuse
#: run scored below its own fresh twin (5.4 21->20, 5.5 22->20, sol 26->20)
#: and every post-dispatcher one scored above it.
#:
#: Excluded rather than annotated because the number is not a weak
#: measurement of reuse, it is a measurement of something else.
DISPATCHER_EPOCH = "2026-09-09T09:24:29-07:00"

START = "<!-- model-matrix:start -->"
END = "<!-- model-matrix:end -->"


def batch_index(bench: Path) -> dict[str, dict]:
    """run directory name -> which batch, phase and submission produced it.

    Two things this has to disentangle, both of which put phantom rows in the
    table when they were ignored.

    A job emits SEVERAL run directories. `pass N` is a resume: a pass that
    loses a node is re-run with `--resume auto`, carrying forward what earlier
    passes measured. So the passes of one phase are one attempt at one thing,
    and only the last of them is the result -- listing each pass separately
    reported a five-pair matrix as twenty-odd rows, most of them partial.

    And a resubmitted job REUSES its name: `livai-5.4-r1` has been submitted
    three times through cancellations. Keying on the name alone merged a live
    run with the cancelled attempts it replaced. The log's own file name
    carries the submission timestamp, so it is what identifies an attempt.
    """
    out: dict[str, dict] = {}
    for log in sorted(bench.glob("batch-*.log")):
        got = re.match(r"^batch-(.*)-(\d{4}-\d{6})$", log.stem)
        if not got:
            continue
        name, stamp = got.groups()
        phase, seq = "", 0
        for line in log.read_text(errors="replace").splitlines():
            found = re.search(r"=== phase: (\w+) ===", line)
            if found:
                phase = found.group(1)
                continue
            found = re.search(r"pass (\d+) started: (\S+)", line)
            if found:
                seq = int(found.group(1))
                out[Path(found.group(2)).name] = {
                    "batch": name, "phase": phase, "submission": stamp,
                    "pass": seq,
                }
    return out


#: What `finalize-run.py` writes into `error` on a task-arm that never came
#: back. Matching on this rather than on `stopped_early` alone, because the
#: RUNNER sets that field too, for an entirely ordinary reason: the bare arm
#: has no retry loop, so every one of its thirty tasks is marked
#: `stopped_early: "hit the 1-attempt ceiling"`. Counting the field's presence
#: made every bare arm look like a timed-out run.
FINALIZED_REASONS = ("never returned", "run cap", "work outstanding")


def stopped_early(run: Path) -> int:
    """Task-arms the FINALIZER recorded as never having returned.

    Not the runner's own single-attempt marker — see FINALIZED_REASONS.
    """
    total = 0
    for arm, _ in ARMS:
        results = run / arm / "results.jsonl"
        if not results.is_file():
            continue
        for line in results.read_text(errors="replace").splitlines():
            if '"stopped_early": true' not in line.lower():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            reason = str(row.get("error") or "")
            if any(r in reason for r in FINALIZED_REASONS):
                total += 1
    return total


def tally(run: Path, arm: str) -> tuple[int, int]:
    """(passed, failed) for one arm, from the durable per-task record."""
    results = run / arm / "results.jsonl"
    if not results.is_file():
        return (0, 0)
    passed = failed = 0
    for line in results.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("resolved"):
            passed += 1
        else:
            failed += 1
    return (passed, failed)


#: An unfinished run silent for longer than this was killed, not slowed. Set
#: well above a slow task: the runner writes a trace line per tool call, so
#: minutes of silence is already abnormal, and a cancelled sweep would
#: otherwise sit in the table as "running" for ever -- the exact way a status
#: table starts lying.
STOPPED_AFTER_S = 30 * 60


def quiet_for(run: Path) -> float:
    """Seconds since anything in this run was last written."""
    newest = 0.0
    for arm, _ in ARMS:
        for name in ("trace.log", "results.jsonl"):
            path = run / arm / name
            if path.exists():
                newest = max(newest, path.stat().st_mtime)
    if not newest:
        newest = (run / "manifest.json").stat().st_mtime
    return time.time() - newest


def rows(bench: Path) -> list[dict]:
    index = batch_index(bench)
    cutoff = datetime.fromisoformat(DISPATCHER_EPOCH).timestamp()
    out = []
    for run in sorted((bench / "runs").iterdir()):
        manifest = run / "manifest.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text())
        except ValueError:
            continue
        model = data.get("model", "").replace("svc-dldl-", "")
        if model not in MODELS:
            continue
        fresh = bool(data.get("fresh"))
        started = manifest.stat().st_mtime
        if not fresh and started < cutoff:
            continue
        meta = index.get(run.name, {})
        batch = meta.get("batch", "")
        # `livai-5.4-r3` and `m2-5.4-reuse-3` both end in the iteration; the
        # first spells it `r3` because a pair had no mode in its name, the
        # second `3` because the mode is already there. One pattern for both,
        # or the second matrix reports every run as un-numbered.
        got = re.search(r"-r?(\d+)$", batch)
        out.append({
            "model": model,
            # `fresh` in the manifest is the run's own knowledge policy, which
            # is the ground truth; the batch phase agrees but is a label.
            "mode": "fresh" if fresh else "reuse",
            "iteration": got.group(1) if got else "",
            "run": run.name,
            "batch": batch,
            "submission": meta.get("submission", ""),
            "pass": meta.get("pass", 0),
            "started": started,
            # A run with no report.json has not finished. Its arm tallies are
            # still real -- they are what has landed so far -- so they are
            # shown, marked, rather than withheld.
            "done": (run / "report.json").is_file(),
            "quiet_s": quiet_for(run),
            # What the run was ASKED to do, from its own manifest. An arm that
            # measured fewer tasks than this did not finish, whatever the
            # batch log claimed -- which matters because a run truncated by a
            # filesystem failure still gets a report.json and still reads as
            # "done".
            "expected": len(data.get("tasks") or []),
            "stopped_early": stopped_early(run),
            **{label: tally(run, arm) for arm, label in ARMS},
        })
    return sorted(newest(out), key=lambda r: (MODELS.index(r["model"]),
                                              int(r["iteration"] or 0),
                                              r["mode"], r["run"]))


def _better(a: dict, b: dict) -> bool:
    """Is pass `a` a truer record of its run than pass `b`?

    NOT simply the later pass, which is what this used to assume. A resume
    re-runs only what is still outstanding, so its directory holds only those
    few task-arms -- measured on one 5.4 run, pass 2 held the whole thing
    (bare 30, phronix 17, and the report.json) while pass 3 finished in 61
    seconds holding three bare rows and no phronix at all. Keeping the highest
    pass number put that 61-second scrap in the table as the run's result.

    So: the pass that MEASURED MORE task-arms wins, then a report.json breaks
    the tie, then the later pass.

    Coverage outranks the report deliberately. `report.json` says only that
    the runner exited cleanly, which the FIRST pass often does while covering
    almost nothing -- 5.4 reuse-1 pass 1 wrote a report with 5 phronix tasks
    measured, while passes 2-4 carried 29 and wrote none because the wall
    killed them mid-pass. Ranking the report first put `1/5` in the table for
    a run that had actually measured `18/29`.
    """
    ka = (sum(sum(a[label]) for _arm, label in ARMS), a["done"], a["pass"])
    kb = (sum(sum(b[label]) for _arm, label in ARMS), b["done"], b["pass"])
    return ka > kb


def newest(data: list[dict]) -> list[dict]:
    """One row per thing actually attempted, keeping the live attempt.

    Collapsed twice. First the passes of one phase of one submission, keeping
    the last -- it is the one carrying every earlier pass's results forward.
    Then the submissions of one (model, iteration, mode), keeping the latest,
    because an earlier one exists only where it was cancelled and replaced.

    Runs no batch log claims keep their own identity: they predate the matrix
    and there is nothing to collapse them against.
    """
    best: dict[tuple, dict] = {}
    loose: list[dict] = []
    for row in data:
        # An attempt that was killed before it measured anything is not a
        # result and not a gap -- it is an event in the scheduler. Cancelled
        # submissions left five such rows, all reading `-- / -- / stopped`,
        # which is noise that looks like missing data. A row still RUNNING
        # with nothing yet is kept: that one is genuinely in progress.
        measured = sum(row[label][0] + row[label][1] for _arm, label in ARMS)
        stalled = not row["done"] and row["quiet_s"] > STOPPED_AFTER_S
        if not measured and stalled:
            continue
        if not row["batch"]:
            loose.append(row)
            continue
        key = (row["batch"], row["submission"], row["mode"])
        if key not in best or _better(row, best[key]):
            best[key] = row

    live: dict[tuple, dict] = {}
    for row in best.values():
        # Keyed by the batch NAME, never by the iteration number.
        #
        # Only a resubmission of the same name is a supersession. Keying on the
        # iteration instead made `m4-5.4-reuse-1` supersede `m3-5.4-reuse-1` --
        # separate batch series that both number their runs from one -- and a
        # completed 26/30 run silently vanished from the table, taking the
        # cell's count DOWN from 2 to 1 while the sweep was still adding to it.
        key = (row["model"], row["batch"], row["mode"])
        if key not in live or row["submission"] > live[key]["submission"]:
            live[key] = row
    return loose + list(live.values())


def render(data: list[dict]) -> str:
    head = ("| Model | Iter | Mode | Run folder | Bare | Phronix | Status | Note |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |")
    lines = [head]
    for r in data:
        def cell(got: tuple[int, int], expected: int = 0) -> str:
            """Passed out of what the run was GIVEN, not what it got through.

            A task-arm the run never finished is a failure, not a smaller
            denominator: scoring 18/29 quietly rebases the result on the
            tasks that happened to complete, which flatters every run that
            lost one. The shortfall is named in the Note column instead.
            """
            passed, failed = got
            total = expected or (passed + failed)
            return f"{passed}/{total}" if (passed + failed) else "--"
        # A row the finalizer WROTE as a timeout is still a timeout.
        #
        # Finalising makes measured == expected, which is the point -- the run
        # reports 30 of 30 attempted. But it must not thereby read as a clean
        # iteration: `m4-5.4-reuse-1` had all 60 task-arms marked
        # `stopped_early`, scored 0/30 on both arms, and counted as `done`.
        short = (r["stopped_early"] > 0) or (r["expected"] and any(
            0 < sum(r[label]) < r["expected"] for _arm, label in ARMS))
        if short:
            # A task-arm that never came back is a timeout, whether the batch
            # exited cleanly or the wall killed it. Named as such rather than
            # as "done", because the run did not cover its task list.
            status = "timeout"
        elif r["done"]:
            status = "done"
        elif r["quiet_s"] > STOPPED_AFTER_S:
            status = "stopped"
        else:
            status = "running"
        missing = max((r["expected"] - sum(r[label]) for _arm, label in ARMS
                       if sum(r[label])), default=0) if r["expected"] else 0
        missing = missing or r["stopped_early"]
        note = f"{missing} timed out" if missing > 0 else ""
        lines.append(
            f"| `{r['model']}` | {r['iteration'] or '--'} | {r['mode']} "
            f"| `{r['run']}` | {cell(r['bare'], r['expected'])} "
            f"| {cell(r['phronix'], r['expected'])} | {status} | {note} |")
    lines.append("")
    lines.append(
        "Reuse runs started before the capability dispatcher landed "
        "(`547269e`, 2026-09-09 09:24) are omitted: until then every learned "
        "capability was its own MCP tool, so a reuse run saw ~1150 of them "
        "and a fresh run saw almost none. That handicapped one arm of each "
        "pair and not the other. Fresh runs from before it are kept -- their "
        "store was empty, so there was nothing to bloat the tool list with.")
    return "\n".join(lines)


def splice(notes: Path, table: str) -> None:
    text = notes.read_text()
    block = f"{START}\n\n{table}\n\n{END}"
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), block,
                      text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n## The reported matrix\n\n" + block + "\n"
    notes.write_text(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--notes", type=Path,
                    default=Path(__file__).resolve().parents[1] / "interesting.md")
    ap.add_argument("--write", action="store_true",
                    help="splice into the notes instead of printing")
    args = ap.parse_args()

    table = render(rows(args.bench))
    if args.write:
        splice(args.notes, table)
        print(f"wrote the matrix into {args.notes}")
    else:
        print(table)


if __name__ == "__main__":
    main()
