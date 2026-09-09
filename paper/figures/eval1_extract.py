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


CALL_RE = re.compile(r"mcp__phronix__([A-Za-z0-9_]+?)x(\d+)")


def learned_tool_names(runs: list[Path]) -> set[str]:
    """Module names of every tool the corpus built, across all runs.

    A phronix MCP call is either a framework tool or one the system wrote for
    itself, and only the second kind is evidence of a capability being reused.
    Rather than maintain a list of framework tool names -- which would go stale
    the moment a service gains a method -- the learned names are taken from the
    tool modules the runs actually promoted.
    """
    names: set[str] = set()
    for run in runs:
        for store in ((run / ARM / "store" / ".phronix"),):
            root = store / "capabilities" / "tools"
            if root.is_dir():
                names |= {t.stem for t in root.rglob("*.py")
                          if not t.name.startswith("__")}
    return names


def tools_reused(run: Path, learned: set[str]) -> dict[str, int]:
    """Calls to learned tools during a run, charged to the calling task."""
    trace = run / ARM / "trace.jsonl"
    out: dict[str, int] = defaultdict(int)
    if not trace.is_file():
        return out
    for line in trace.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("kind") != "tools":
            continue
        task = rec.get("task") or ""
        # The task is the ground truth for the category here, unlike a tool
        # sitting in the store: we know who made the call.
        cat = category_of(task)
        for chunk in rec.get("detail", []):
            if not isinstance(chunk, str) or chunk.startswith("REJECTED"):
                continue
            for name, count in CALL_RE.findall(chunk):
                if name in learned:
                    out[cat] += int(count)
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
    learned = learned_tool_names(runs)
    table: dict[tuple[str, str, str], dict] = {}

    def cell(model: str, mode: str, cat: str) -> dict:
        key = (model, mode, cat)
        if key not in table:
            table[key] = {
                "model": model, "mode": mode, "category": cat,
                "tasks": 0, "resolved": 0, "skills_created": 0,
                "tools_created": 0, "skills_retrieved": 0,
                "skills_reused": 0, "tools_reused": 0,
                "resolved_first_try": 0,
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
            # Solved on the first attempt, with no retry: the run went
            # straight to a working patch. Against a reuse run this is the
            # determinism claim -- the corpus told it what to do rather than
            # it searching for the answer again.
            c["resolved_first_try"] += int(
                bool(r.get("resolved")) and r.get("tries") == 1)
            # `skills_created` mixes skill directories with the tool
            # directories a task wrote into; only the former are one-per-skill.
            c["skills_created"] += sum(
                1 for s in r.get("skills_created", []) if s.startswith("skills/")
            )
            c["skills_retrieved"] += len(r.get("skills_retrieved", []))
            # Reuse of a LEARNED skill is the claim being tested. The
            # framework's own skills (`phronix-*`) are loaded on every task by
            # design, so counting them would report the harness working rather
            # than the corpus paying off.
            c["skills_reused"] += sum(
                1 for s in r.get("skills_retrieved", [])
                if not s.split("/")[0].startswith("phronix-")
            )

        for cat, n in tools_promoted(rows).items():
            cell(model, mode, cat)["tools_created"] += n
        for cat, n in tools_reused(run, learned).items():
            cell(model, mode, cat)["tools_reused"] += n

    return sorted(table.values(), key=lambda r: (r["model"], r["mode"], r["category"]))


FIELDS = ["model", "mode", "category", "tasks", "resolved",
          "skills_created", "tools_created", "skills_retrieved",
          "skills_reused", "tools_reused", "resolved_first_try"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "eval1_capabilities.csv")
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
                      f"skills_reused={sum(r['skills_reused'] for r in sel):3d} "
                      f"tools_reused={sum(r['tools_reused'] for r in sel):3d}")


if __name__ == "__main__":
    main()
