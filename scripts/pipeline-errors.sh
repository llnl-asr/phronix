#!/bin/bash
# Split a run's failures into MODEL faults and PIPELINE faults.
#
#   scripts/pipeline-errors.sh                 # the newest run
#   scripts/pipeline-errors.sh <run-dir> ...   # named runs
#
# The distinction is the whole point of watching a run: a model that cannot
# solve a task is the experiment working, and a harness that loses a task is a
# bug. They look identical in the totals — both are `fail` — and only the error
# text tells them apart.
#
# MODEL: the agent ran, was measured, and did not solve it.
# PIPELINE: the agent never ran, or ran and was not measured, or was stopped by
#           something that is not about the task.
set -uo pipefail
PROJECT=/usr/WS2/haridev/phronix
source "$PROJECT/scripts/bench-root.sh"
PBENCH=$(bench_root)

runs=("$@")
[ ${#runs[@]} -gt 0 ] || runs=("$(ls -dt "$PBENCH"/runs/*/ 2>/dev/null | head -1)")

"$PBENCH/venv/bin/python" - "${runs[@]}" <<'PY'
import pathlib, re, sys
from collections import Counter

# Ordered: the first pattern that matches decides, so put the specific ones
# first. Anything unmatched is reported separately rather than assumed benign —
# an unclassified error is the one most likely to be a new bug.
MODEL = [
    (r"agent produced no patch",            "gave up without editing"),
    (r"target \d+/\d+, regressions",        "patch measured, did not resolve"),
    (r"the patch broke .*, so the test",    "patch broke the suite (self-inflicted)"),
]
PIPELINE = [
    (r"Access denied: user .* no active jobs", "allocation ended mid-run"),
    (r"could not start docker\.io",            "container would not start"),
    (r"kex_exchange_identification|Session open refused|mux_client",
                                               "ssh refused (MaxStartups/MaxSessions)"),
    (r"CalledProcessError.*ssh",               "ssh command failed"),
    (r"cannot run pytest",                     "testbed cannot run pytest"),
    (r"no test produced a result",             "runner never started"),
    (r"ContextWindowExceeded",                 "agent overflowed its context"),
    (r"unrecognized_model",                    "model name the CLI rejects"),
    (r"InternalServerError|502|503",           "gateway error"),
    (r"Content block not found",               "gateway stream translation"),
    (r"rc=127",                                "agent binary not found"),
    (r"name '\w+' is not defined|AttributeError|TypeError",
                                               "harness exception"),
]

def classify(line):
    for pattern, label in MODEL:
        if re.search(pattern, line):
            return "model", label
    for pattern, label in PIPELINE:
        if re.search(pattern, line):
            return "pipeline", label
    return "unclassified", line[:60]

for arg in sys.argv[1:]:
    run = pathlib.Path(arg.rstrip("/"))
    if not run.is_dir():
        continue
    buckets = {"model": Counter(), "pipeline": Counter(), "unclassified": Counter()}
    tasks = set()
    for log in run.glob("*/tasks/*/trace.log"):
        for line in log.read_text(errors="replace").splitlines():
            if "ERROR" not in line and "ABORT" not in line:
                continue
            kind, label = classify(line)
            buckets[kind][label] += 1
            if kind == "pipeline":
                tasks.add(log.parent.name)
    total = sum(sum(c.values()) for c in buckets.values())
    print(f"\n=== {run.name}   ({total} error line(s))")
    for kind in ("pipeline", "unclassified", "model"):
        counts = buckets[kind]
        if not counts:
            continue
        print(f"  {kind.upper()}")
        for label, n in counts.most_common(10):
            print(f"    {n:4d}  {label}")
    if tasks:
        print(f"  tasks touched by a pipeline fault: {len(tasks)}")
PY
