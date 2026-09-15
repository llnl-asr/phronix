#!/usr/bin/env python3
"""Carry corrected attempt verdicts up into the task-level results.

    scripts/propagate-rescore.py --dry-run
    scripts/propagate-rescore.py

`rescore.py` fixes the evidence — each attempt's `evaluation.json`. But every
figure reads `results.jsonl`, whose one row per task carries the verdict the
runner reached at the time. Correcting the evaluations alone moves nothing.

A task counts as resolved if ANY of its attempts resolved it. That is not a
choice made here: the runner's retry loop breaks the moment `attempt.resolved`
is true, so "any attempt" is exactly what the original run meant by resolved.

Only ever upgrades. A row already marked resolved is never touched, for the
same reason `rescore.py` never revokes a pass — the correction exists to find
verdicts the parser could not see, not to relitigate ones it could.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")


def resolved_tasks(arm_dir: Path) -> dict[str, str]:
    """instance_id -> the attempt that resolved it, for rescored attempts."""
    out: dict[str, str] = {}
    for task in sorted((arm_dir / "tasks").glob("*/")):
        instance = task.name.split("-", 1)[-1] if "-" in task.name else task.name
        for attempt in sorted(task.glob("attempt-*/evaluation.json")):
            try:
                e = json.loads(attempt.read_text())
            except (ValueError, OSError):
                continue
            if e.get("rescored_by") and e.get("resolved"):
                out[instance] = attempt.parent.name
                break
    return out


def apply_to(arm_dir: Path, dry: bool) -> list[str]:
    results = arm_dir / "results.jsonl"
    if not results.is_file():
        return []
    winners = resolved_tasks(arm_dir)
    if not winners:
        return []

    changed, rows = [], []
    for line in results.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        iid = row.get("instance_id", "")
        if iid in winners and not row.get("resolved"):
            row["resolved"] = True
            row["rescored_by"] = f"propagate-rescore.py ({winners[iid]})"
            changed.append(iid)
        rows.append(row)

    if changed and not dry:
        results.write_text("".join(json.dumps(r) + "\n" for r in rows),
                           encoding="utf-8")
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total, by_instance = 0, {}
    for arm_dir in sorted((args.bench / "runs").glob("*/claude-*")):
        for iid in apply_to(arm_dir, args.dry_run):
            total += 1
            by_instance[iid] = by_instance.get(iid, 0) + 1
    verb = "would upgrade" if args.dry_run else "upgraded"
    print(f"{verb} {total} task result(s)")
    for iid, n in sorted(by_instance.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>3}  {iid}")


if __name__ == "__main__":
    main()
