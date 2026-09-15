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


#: The dispatcher every learned capability is reached through since the tool
#: surface was collapsed (`547269e`). Before that a learned tool appeared in
#: the trace under its own name; after it, the name is an ARGUMENT and the
#: MCP call is always this one.
DISPATCH = "capability_call"


def tools_reused(run: Path, learned: set[str]) -> dict[str, int]:
    """Calls to learned tools during a run, charged to the calling task.

    Two call shapes, because the framework changed underneath this metric.

    A run from before the capability tool surface was collapsed into a
    dispatcher calls `mcp__phronix__apply_flask_4992_binary_config_fix`
    directly, and the name matches a promoted module. A run from after it
    calls `mcp__phronix__capability_call` and passes the name as an argument,
    so NO learned name ever appears as an MCP tool name -- and this function,
    matching on names alone, returned zero for every such run while the trace
    plainly showed the capabilities being used. Counting only the first shape
    would report the dispatcher change as a collapse in reuse.
    """
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
                if name in learned or name == DISPATCH:
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
    table: dict[tuple[str, str, str, str], dict] = {}

    # Keyed by RUN as well as model and mode, so repeats of one condition stay
    # separate rows. Summed, five runs look like one large run and the figure
    # can no longer say how stable any of it is.
    def cell(model: str, mode: str, rid: str, cat: str) -> dict:
        key = (model, mode, rid, cat)
        if key not in table:
            table[key] = {
                "model": model, "mode": mode, "run": rid, "category": cat,
                "tasks": 0, "resolved": 0, "skills_created": 0,
                "tools_created": 0, "skills_retrieved": 0,
                "skills_reused": 0, "tools_reused": 0,
                "resolved_first_try": 0,
                # Denominator and numerator of the determinism rate. Filled
                # in by a second pass, because they need BOTH runs of a model.
                "eligible": 0, "first_try_eligible": 0,
            }
        return table[key]

    for run in runs:
        got = read_run(run)
        if got is None:
            continue
        manifest, rows = got
        model = manifest.get("model", "?").replace("svc-dldl-", "")
        mode = "fresh" if manifest.get("fresh") else "reuse"
        rid = run.name

        for r in rows:
            cat = r.get("repo") or category_of(r["instance_id"])
            c = cell(model, mode, rid, cat)
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
            cell(model, mode, rid, cat)["tools_created"] += n
        for cat, n in tools_reused(run, learned).items():
            cell(model, mode, rid, cat)["tools_reused"] += n

    pair_up(runs, table)
    return sorted(table.values(),
                  key=lambda r: (r["model"], r["mode"], r["run"], r["category"]))


def pair_up(runs: list[Path], table: dict) -> None:
    """Join each model's fresh and reuse runs task by task.

    Asking whether a reuse run got it right first time is only meaningful for
    a task some earlier run actually solved: if nothing ever worked, there is
    no successful skill to reuse and a first-try miss says nothing about
    determinism. So the denominator is tasks the FRESH run solved -- every one
    of which leaves a skill directory in the store, checked here rather than
    assumed -- and the numerator is how many of those the reuse run then
    solved on its first attempt.
    """
    # What every FRESH run of a model solved and left a skill for, pooled.
    #
    # Pooled rather than paired run-to-run: with repeats there is no natural
    # pairing between fresh repeat 3 and reuse repeat 3, and inventing one
    # would make eligibility depend on submission order. A task is eligible if
    # some fresh run of that model actually left a working skill for it, which
    # is the condition the rate is asking about.
    solved_with_skill: dict[str, dict[str, str]] = defaultdict(dict)
    reuse_runs: list[tuple[str, str, dict]] = []
    for run in runs:
        got = read_run(run)
        if got is None:
            continue
        manifest, rows = got
        model = manifest.get("model", "?").replace("svc-dldl-", "")
        mode = "fresh" if manifest.get("fresh") else "reuse"
        skills_dir = run / ARM / "store" / ".phronix" / "capabilities" / "skills"
        have = {d.name for d in skills_dir.iterdir()} if skills_dir.is_dir() else set()
        seen = {
            r["instance_id"]: {
                "repo": r.get("repo") or category_of(r["instance_id"]),
                "resolved": bool(r.get("resolved")),
                "tries": r.get("tries"),
                # The skill the successful attempt left behind.
                "skill": r["instance_id"].replace("__", "-") in have,
            }
            for r in rows
        }
        if mode == "fresh":
            for task, f in seen.items():
                if f["resolved"] and f["skill"]:
                    solved_with_skill[model][task] = f["repo"]
        else:
            reuse_runs.append((model, run.name, seen))

    # Charged to the reuse RUN that did it, so the rate has a spread too.
    for model, rid, seen in reuse_runs:
        for task, repo in solved_with_skill.get(model, {}).items():
            u = seen.get(task)
            if u is None:
                continue
            key = (model, "reuse", rid, repo)
            if key not in table:
                continue
            table[key]["eligible"] += 1
            table[key]["first_try_eligible"] += int(u["resolved"] and u["tries"] == 1)


FIELDS = ["model", "mode", "run", "category", "tasks", "resolved",
          "skills_created", "tools_created", "skills_retrieved",
          "skills_reused", "tools_reused", "resolved_first_try",
          "eligible", "first_try_eligible"]


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
