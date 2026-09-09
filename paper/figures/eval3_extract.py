#!/usr/bin/env python3
"""Eval 3 -- RL-driven research: how many attempts a task costs.

One row per category. The comparison is what a task costs in ATTEMPTS:

* Bare has no retry loop at all -- every bare task runs exactly once and is
  scored. Its column is therefore an ESTIMATE, not a measurement: the budget
  a bare agent would need is assumed to be `--bare-retries` attempts, priced
  from the single attempt that was actually run. It is drawn hatched for that
  reason and no conclusion should rest on its exact height.
* Phronix retries under its own control, so its number is measured. It is
  split by outcome, because the two say opposite things: a solved task's
  attempt count is what the research SAVED, while a failed task's is just the
  budget cap being spent.

The second measure is what the research left behind -- topics investigated
(each leaving a skill) and the MCP tools built for them.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")
PHRONIX, BARE = "claude-phronix", "claude-bare"

REPO_TOKENS = {
    "django": "django/django", "sympy": "sympy/sympy",
    "matplotlib": "matplotlib/matplotlib", "seaborn": "mwaskom/seaborn",
    "requests": "psf/requests", "pytest": "pytest-dev/pytest",
    "pylint": "pylint-dev/pylint", "sphinx": "sphinx-doc/sphinx",
    "xarray": "pydata/xarray", "astropy": "astropy/astropy",
    "flask": "pallets/flask", "sklearn": "scikit-learn/scikit-learn",
    "scikit_learn": "scikit-learn/scikit-learn",
    "scikit-learn": "scikit-learn/scikit-learn",
}
CROSS_CUTTING = "general"


def category_of(text: str) -> str:
    low = text.lower()
    for token in sorted(REPO_TOKENS, key=len, reverse=True):
        if token in low:
            return REPO_TOKENS[token]
    return CROSS_CUTTING


FIELDS = ["category", "bare_tasks", "bare_attempts_est",
          "solved_tasks", "solved_attempts_mean",
          "failed_tasks", "failed_attempts_mean",
          "research_topics", "research_tools"]


def collect(runs: list[Path], bare_retries: int) -> list[dict]:
    solved: dict[str, list[int]] = defaultdict(list)
    failed: dict[str, list[int]] = defaultdict(list)
    bare: dict[str, int] = defaultdict(int)
    # Topics and tools are named things: a run that revisits a topic has not
    # learnt a second one, so they are de-duplicated across the whole sweep
    # rather than summed per run.
    topics: dict[str, set[str]] = defaultdict(set)
    tools: dict[str, set[str]] = defaultdict(set)

    for run in runs:
        if not (run / "report.json").is_file():
            continue
        for arm in (PHRONIX, BARE):
            results = run / arm / "results.jsonl"
            if not results.is_file():
                continue
            for line in results.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                cat = r.get("repo") or category_of(r["instance_id"])
                if arm == BARE:
                    bare[cat] += 1
                elif r.get("resolved"):
                    solved[cat].append(r["tries"])
                else:
                    failed[cat].append(r["tries"])

        store = run / PHRONIX / "store" / ".phronix"
        topic_dir = store / "research" / "skills"
        if topic_dir.is_dir():
            for d in topic_dir.iterdir():
                if d.is_dir():
                    topics[category_of(d.name)].add(d.name)
        # Research itself writes no tool modules -- it emits a plan and a
        # skill, and the capability builder turns those into tools. The MCP
        # half of the stack therefore comes from the capability tree.
        results = run / PHRONIX / "results.jsonl"
        if results.is_file():
            for line in results.read_text().splitlines():
                if not line.strip():
                    continue
                for p in json.loads(line).get("promoted", []):
                    if p.startswith("capabilities/tools/") and p.endswith(".py"):
                        stem = Path(p).stem
                        cat = category_of(stem)
                        if cat == CROSS_CUTTING:
                            cat = category_of(Path(p).parts[2])
                        tools[cat].add(p)

    rows = []
    mean = lambda v: round(sum(v) / len(v), 3) if v else 0.0
    for cat in sorted(set(solved) | set(failed) | set(bare)):
        rows.append({
            "category": cat,
            "bare_tasks": bare[cat],
            "bare_attempts_est": bare_retries,
            "solved_tasks": len(solved[cat]),
            "solved_attempts_mean": mean(solved[cat]),
            "failed_tasks": len(failed[cat]),
            "failed_attempts_mean": mean(failed[cat]),
            "research_topics": len(topics[cat]),
            "research_tools": len(tools[cat]),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--bare-retries", type=int, default=5,
                    help="assumed attempt budget for the bare arm (estimate)")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "eval3_retries.csv")
    ap.add_argument("--runs", nargs="*", default=None)
    args = ap.parse_args()

    names = args.runs or sorted(p.name for p in (args.bench / "runs").iterdir() if p.is_dir())
    rows = collect([args.bench / "runs" / n for n in names], args.bare_retries)
    if not rows:
        raise SystemExit("no usable runs")

    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{args.out}: {len(rows)} rows")
    for r in sorted(rows, key=lambda r: -(r["solved_tasks"] + r["failed_tasks"]))[:8]:
        print(f"  {r['category']:28s} solved {r['solved_tasks']:2d}@{r['solved_attempts_mean']:.2f}  "
              f"failed {r['failed_tasks']:2d}@{r['failed_attempts_mean']:.2f}  "
              f"topics={r['research_topics']:2d} tools={r['research_tools']:2d}")


if __name__ == "__main__":
    main()
