#!/usr/bin/env python3
"""Report a set of batch runs as one result.

    scripts/group-batches.sh <state-dir>          # written by hourly-batches.sh
    scripts/group-batches.sh <run-dir> <run-dir>  # or name them directly

Batching is a scheduling decision, not an experimental one: the tasks were split
across runs to pace the spend, and every batch shares one carry root, so what
batch 3 knows includes what batches 1 and 2 learned. Reading them separately
would report the same experiment as N small ones and hide exactly the trend the
batching was arranged to produce.

Per-arm totals, then the cost, then how the pass rate moved from the first batch
to the last — which is the reuse question, asked over the whole list rather than
inside one run.
"""
import json
import sys
from pathlib import Path


def runs_from(argv):
    out = []
    for arg in argv:
        path = Path(arg)
        listing = path / "runs.txt"
        if listing.is_file():
            out += [Path(line.strip()) for line in listing.read_text().splitlines()
                    if line.strip()]
        elif path.is_dir():
            out.append(path)
    return [p for p in out if p.is_dir()]


def main(argv):
    runs = runs_from(argv or ["."])
    if not runs:
        print("no run directories found")
        return 1

    arms = {}
    order = []
    for index, run in enumerate(runs, 1):
        for results in sorted(run.glob("*/results.jsonl")):
            arm = results.parent.name
            got = arms.setdefault(arm, {"pass": 0, "fail": 0, "cost": 0.0,
                                        "tokens": 0, "reused": 0, "ids": set()})
            batch = {"pass": 0, "fail": 0}
            for line in results.read_text().splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                # A task can appear in two batches only if one was cut off
                # mid-task; count it once, and prefer the resolved verdict.
                key = row.get("instance_id", "")
                if key in got["ids"] and not row.get("resolved"):
                    continue
                got["ids"].add(key)
                bucket = "pass" if row.get("resolved") else "fail"
                got[bucket] += 1
                batch[bucket] += 1
                # `cost_total_usd` is the bill; `cost_usd` is the solve agent
                # alone and understates it about threefold, because research is
                # the larger half. Older runs carry only the latter.
                got["cost"] += float(row.get("cost_total_usd")
                                     or row.get("cost_usd") or 0.0)
                got["tokens"] += int(row.get("tokens_total") or 0)
                got["reused"] += len(row.get("skills_reused") or [])
            order.append((index, arm, batch))

    width = max(len(a) for a in arms) if arms else 10
    print(f"{len(runs)} batch(es), {sum(len(a['ids']) for a in arms.values())} "
          f"task result(s)\n")
    print(f"{'arm':<{width}}  {'pass':>5} {'fail':>5} {'rate':>6} "
          f"{'cost':>9} {'tokens':>12} {'reused':>7}")
    for arm, got in sorted(arms.items()):
        done = got["pass"] + got["fail"]
        rate = f"{100.0 * got['pass'] / done:.1f}%" if done else "-"
        print(f"{arm:<{width}}  {got['pass']:>5} {got['fail']:>5} {rate:>6} "
              f"${got['cost']:>8.2f} {got['tokens']:>12,} {got['reused']:>7}")

    # Did it get better as it went? That is what the shared carry root is for,
    # and it is invisible inside any single batch.
    print("\nper batch (pass/total):")
    for arm in sorted(arms):
        cells = [f"{b['pass']}/{b['pass'] + b['fail']}"
                 for i, a, b in order if a == arm and (b["pass"] + b["fail"])]
        if cells:
            print(f"  {arm:<{width}}  " + "  ".join(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
