#!/usr/bin/env python3
"""Extract per-category capability counts from benchmark runs into a CSV.

One row per (model, mode, category). `mode` is the arm's knowledge policy:
a `fresh` run starts with an empty store and can only use what it writes
during the run; a `reuse` run reads what earlier runs promoted. The two
therefore measure different things and must not be summed -- a reuse run
creates almost nothing precisely because the capability it would have written
is already there to be loaded.

Category is the upstream repository the task came from, which is the closest
thing SWE-bench has to a task type: `django/django` tasks are ORM and
migrations work, `sympy/sympy` is symbolic algebra, and a capability written
for one is not obviously useful to the other. That is the question the figure
asks.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")
ARM = "claude-phronix"

# Tools are filed by subject (`tools/django/...`), not by the task that wrote
# them, so the directory alone cannot say which category paid for the tool.
# The filename usually can: the writer names it after the instance. Match the
# repo token in the filename first and fall back to the directory.
REPO_TOKENS = {
    "django": "django/django",
    "sympy": "sympy/sympy",
    "matplotlib": "matplotlib/matplotlib",
    "seaborn": "mwaskom/seaborn",
    "requests": "psf/requests",
    "pytest": "pytest-dev/pytest",
    "pylint": "pylint-dev/pylint",
    "sphinx": "sphinx-doc/sphinx",
    "xarray": "pydata/xarray",
    "astropy": "astropy/astropy",
    "flask": "pallets/flask",
    "sklearn": "scikit-learn/scikit-learn",
    "scikit_learn": "scikit-learn/scikit-learn",
    "scikit-learn": "scikit-learn/scikit-learn",
}
# A tool nothing in the corpus claims is still a capability that was built;
# it is charged here rather than dropped, so the totals reconcile.
CROSS_CUTTING = "general"


def category_of(text: str) -> str:
    """Repo a filename or directory belongs to, or `general`."""
    low = text.lower()
    # Longest token first: `scikit_learn` must not lose to a bare `learn`, and
    # `seaborn-scales` must resolve to seaborn rather than falling through.
    for token in sorted(REPO_TOKENS, key=len, reverse=True):
        if token in low:
            return REPO_TOKENS[token]
    return CROSS_CUTTING


def tools_promoted(rows: list[dict]) -> dict[str, int]:
    """Count distinct tool modules a run WROTE, charged to a category.

    Counted from what the tasks promoted, not from what sits in the store: a
    reuse run's store arrives already full of the previous run's tools, so
    listing the directory would credit this run with capabilities it merely
    inherited. `promoted` is per task but names the whole store each time, so
    the paths are de-duplicated across the run before counting.
    """
    seen: set[str] = set()
    for r in rows:
        for path in r.get("promoted", []):
            if path.startswith("capabilities/tools/") and path.endswith(".py"):
                seen.add(path)

    out: dict[str, int] = defaultdict(int)
    for path in seen:
        parts = Path(path).parts
        cat = category_of(Path(path).stem)
        if cat == CROSS_CUTTING and len(parts) > 2:
            cat = category_of(parts[2])
        out[cat] += 1
    return out


def read_run(run: Path) -> tuple[dict, list[dict]] | None:
    report = run / "report.json"
    results = run / ARM / "results.jsonl"
    if not report.is_file() or not results.is_file():
        return None
    manifest = json.loads(report.read_text()).get("manifest", {})
    rows = [json.loads(line) for line in results.read_text().splitlines() if line.strip()]
    return manifest, rows


def collect(runs: list[Path]) -> list[dict]:
    table: dict[tuple[str, str, str], dict] = {}

    def cell(model: str, mode: str, cat: str) -> dict:
        key = (model, mode, cat)
        if key not in table:
            table[key] = {
                "model": model, "mode": mode, "category": cat,
                "tasks": 0, "resolved": 0, "skills_created": 0,
                "tools_created": 0, "skills_retrieved": 0, "skills_reused": 0,
            }
        return table[key]

    for run in runs:
        got = read_run(run)
        if got is None:
            continue
        manifest, rows = got
        model = manifest.get("model", "?").replace("svc-dldl-", "")
        mode = "fresh" if manifest.get("fresh") else "reuse"

        for r in rows:
            cat = r.get("repo") or category_of(r["instance_id"])
            c = cell(model, mode, cat)
            c["tasks"] += 1
            c["resolved"] += int(bool(r.get("resolved")))
            # `skills_created` mixes skill directories with the tool
            # directories a task wrote into; only the former are one-per-skill.
            c["skills_created"] += sum(
                1 for s in r.get("skills_created", []) if s.startswith("skills/")
            )
            c["skills_retrieved"] += len(r.get("skills_retrieved", []))
            # Reuse across sessions is the claim being tested. Within-run
            # reuse is counted too but it is the easy case.
            c["skills_reused"] += len(r.get("skills_reused", []))

        for cat, n in tools_promoted(rows).items():
            cell(model, mode, cat)["tools_created"] += n

    return sorted(table.values(), key=lambda r: (r["model"], r["mode"], r["category"]))


FIELDS = ["model", "mode", "category", "tasks", "resolved",
          "skills_created", "tools_created", "skills_retrieved", "skills_reused"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "capabilities_by_category.csv")
    ap.add_argument("--runs", nargs="*", default=None,
                    help="run directory names; default is every run under --bench/runs")
    args = ap.parse_args()

    names = args.runs or sorted(p.name for p in (args.bench / "runs").iterdir() if p.is_dir())
    rows = collect([args.bench / "runs" / n for n in names])
    if not rows:
        raise SystemExit("no runs with both report.json and results.jsonl")

    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{args.out}: {len(rows)} rows")
    for model in sorted({r['model'] for r in rows}):
        for mode in ("fresh", "reuse"):
            sel = [r for r in rows if r["model"] == model and r["mode"] == mode]
            if sel:
                print(f"  {model:16s} {mode:5s}  tasks={sum(r['tasks'] for r in sel):3d} "
                      f"skills={sum(r['skills_created'] for r in sel):3d} "
                      f"tools={sum(r['tools_created'] for r in sel):3d} "
                      f"reused={sum(r['skills_reused'] for r in sel):3d}")


if __name__ == "__main__":
    main()
