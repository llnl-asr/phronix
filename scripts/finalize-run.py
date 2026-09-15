#!/usr/bin/env python3
"""Close a capped run cleanly: record what never finished, keep what was learned.

    finalize-run.py <run-dir> [--carry <carry-root>] [--reason timeout]

A run stopped at its cap leaves task-arms simply ABSENT from `results.jsonl`.
Absent is the worst of the three states it could be in: the tracking table has
to guess the denominator, and every figure divides by the rows that happen to
be there -- so a run that finished 28 of 30 scores as if it had been asked for
28, which flatters exactly the runs that went worst.

So a task-arm that never came back is written down as a failure with
`stopped_early` set and `error` naming the reason. The run then reports 30 of
30 attempted, some of them failed, which is what actually happened.

The learning is checkpointed first, for the same reason the cap exists at all:
1.5h of attempts that discovered three dead ends is worth keeping even though
the task is unsolved, and promotion normally happens per task -- so whatever
the last, killed task learned would otherwise be dropped on the floor.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ARMS = ("claude-bare", "claude-phronix")


def tasks_of(run: Path) -> list[str]:
    """The task list this run was GIVEN, from its own manifest."""
    manifest = run / "manifest.json"
    if not manifest.is_file():
        return []
    try:
        return list(json.loads(manifest.read_text()).get("tasks") or [])
    except ValueError:
        return []


def finished(results: Path) -> set[str]:
    out: set[str] = set()
    if not results.is_file():
        return out
    for line in results.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            out.add(json.loads(line)["instance_id"])
        except (ValueError, KeyError):
            continue
    return out


def repo_of(instance: str) -> str:
    return instance.split("__")[0].replace("-", "/", 1) if "__" in instance else ""


def mark(run: Path, reason: str) -> dict:
    counts = {}
    for arm in ARMS:
        results = run / arm / "results.jsonl"
        if not (run / arm).is_dir():
            continue
        missing = [t for t in tasks_of(run) if t not in finished(results)]
        if not missing:
            counts[arm] = 0
            continue
        with results.open("a", encoding="utf-8") as fh:
            for order, instance in enumerate(missing):
                fh.write(json.dumps({
                    "instance_id": instance,
                    "repo": repo_of(instance),
                    "arm": arm,
                    "resolved": False,
                    "tries": 0,
                    "attempts": [],
                    "stopped_early": True,
                    "error": reason,
                    "order": 900 + order,
                }) + "\n")
        counts[arm] = len(missing)
    return counts


def checkpoint(run: Path, carry: Path | None) -> int:
    """Promote whatever this run learned, before the directory goes cold."""
    if carry is None:
        return 0
    root = Path(__file__).resolve().parents[1]
    # Both, or the import fails: `tests.benchmark.isolation` lives under the
    # project root while `phronix` itself is under `src/`. Missing the second
    # made every checkpoint fail with "No module named 'phronix'" -- so a
    # capped run recorded its timeouts and threw away the learning the cap
    # existed to keep.
    for path in (str(root), str(root / "src")):
        if path not in sys.path:
            sys.path.insert(0, path)
    try:
        from tests.benchmark.isolation import promote_store
    except Exception as exc:                      # pragma: no cover - diagnostic
        print(f"  checkpoint unavailable: {exc}")
        return 0
    total = 0
    for arm in ARMS:
        store = run / arm / "store" / ".phronix"
        if not store.is_dir():
            continue
        try:
            total += len(promote_store(store, carry).get("promoted", []))
        except Exception as exc:
            print(f"  checkpoint {arm} failed: {exc}")
    return total


def seal(run: Path) -> bool:
    """Write the run's `report.json` if it never got one.

    The extractors gate on `report.json` -- it is where they read the manifest
    from -- so a run killed before writing it is invisible to every figure no
    matter how complete its results are. Measured today: three runs at 22/30,
    25/30 and 23/30, all of them fully usable, all dropped for want of a
    summary file the runner never reached.

    Synthesised from what the run already holds rather than invented: the
    manifest is copied from `manifest.json`, and the per-arm summaries are
    counted from the results themselves. `sealed_by` marks it so nobody later
    mistakes this for the runner's own report.
    """
    report = run / "report.json"
    if report.is_file():
        return False
    manifest = run / "manifest.json"
    if not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text())
    except ValueError:
        return False

    summaries = {}
    for arm in ARMS:
        results = run / arm / "results.jsonl"
        if not results.is_file():
            continue
        rows = []
        for line in results.read_text(errors="replace").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
        summaries[arm] = {
            "tasks": len(rows),
            "resolved": sum(1 for r in rows if r.get("resolved")),
        }
    report.write_text(json.dumps({
        "run": str(run),
        "manifest": data,
        "summaries": summaries,
        "comparison": {},
        "sealed_by": "finalize-run.py",
    }, indent=2), encoding="utf-8")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--carry", type=Path, default=None)
    ap.add_argument("--reason", default="stopped at the run cap")
    args = ap.parse_args()

    if not args.run.is_dir():
        print(f"no run at {args.run}")
        raise SystemExit(2)

    promoted = checkpoint(args.run, args.carry)
    counts = mark(args.run, args.reason)
    sealed = seal(args.run)                    # after marking, so it counts them
    said = ", ".join(f"{arm}={n}" for arm, n in counts.items()) or "nothing"
    print(f"finalize: promoted {promoted} file(s); marked timed-out task-arms: "
          f"{said}{'; sealed report.json' if sealed else ''}")


if __name__ == "__main__":
    main()
