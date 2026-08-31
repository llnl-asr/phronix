#!/usr/bin/env python3
"""Split a run's failures into PIPELINE faults and MODEL failures.

    scripts/error-report.py [<run-dir> ...]     # default: the newest run

The two are worth acting on differently and read identically in a trace, which
is how a day gets spent on the wrong one. A pipeline fault is ours: a binary
that moved, an ssh limit, a budget calibrated against hardware seventy times
faster. A model failure is the benchmark working — a weak model did not solve a
hard task, which is the measurement, not a defect.

Anything unrecognised is reported as UNCLASSIFIED rather than assumed to be a
model failure. A fault this does not know about is exactly the one worth seeing.
"""
import re
import sys
from collections import Counter
from pathlib import Path

#: (label, pattern, why it is ours). Ordered: first match wins, so the
#: specific patterns come before the general ones.
PIPELINE = [
    ("agent binary missing", r"rc=127",
     "the command was not found — a moved or updated binary"),
    ("ssh session refused", r"mux_client_request_session|kex_exchange_identification",
     "ssh limits: MaxSessions on a shared connection, or MaxStartups"),
    ("model name rejected", r"unrecognized_model",
     "the client or gateway would not accept the pinned alias"),
    ("container would not start", r"isolation: could not start|OCI runtime error",
     "image, keyring quota, or an unreachable container host"),
    ("keyring exhausted", r"session keyring|disk quota exceeded",
     "containers left behind by an earlier run; kill.sh reaps these"),
    ("streaming protocol", r"Content block not found",
     "the gateway's Anthropic translation emitted a bad block index"),
    ("stage hit its ceiling", r"KILLED at the \d+s hard ceiling",
     "a budget too short for this hardware, not a wedged agent"),
    ("recording failed", r"could not record|could not snapshot|could not close the record",
     "the tracker or the end-of-task snapshot did not run"),
    # Only OUTSIDE a runner-did-not-start line, which TESTBED claims first.
    # Trace lines are truncated, so an exception whose distinguishing text was
    # cut off would otherwise be blamed on this repository: exactly what
    # happened to astropy's `_xdg_config_home_orig`, which is in the TESTBED
    # list and still landed here because the line stopped short of it.
    ("harness exception", r"NameError|AttributeError|Traceback \(most recent",
     "a bug in the harness itself"),
    ("attempt never ran", r"attempt-void|did not run \(",
     "the try produced nothing and was correctly not counted"),
    ("phronix unused", r"used NO phronix tools",
     "a phronix arm that ran as a plain agent — the arms are not comparable"),
    ("api error", r"API Error",
     "the model endpoint refused or dropped the request"),
    ("ssh command failed", r"CalledProcessError: Command '\['ssh'",
     "an ssh to a compute node failed — container control or a remote agent"),
    ("patch would not apply", r"patch did not apply",
     "the diff did not apply to the checkout"),
]

#: The TASK's own environment, which is neither ours nor the model's.
#:
#: A third category because the first two both point somewhere useless for
#: these. They are not phronix bugs — nothing in this repository can be
#: changed to fix them — and they are not model failures either, because the
#: agent never got a scored answer. They are the SWE-bench image drifting
#: against its dependencies, and the remedy is pinning or a per-repo test
#: invocation, not a change to the harness.
#:
#: Measured examples:
#:   sphinx-8595   NameError: name 'environmentfilter' is not defined
#:                 (Jinja 3.1 removed it; the image installs a newer Jinja)
#:   astropy-14182 AttributeError: builtins._xdg_config_home_orig
#:                 (astropy's conftest teardown, running without its setup)
TESTBED = [
    ("testbed dependency drift", r"environmentfilter|_xdg_config_home_orig"),
    ("testbed import error", r"the testbed environment cannot run pytest"),
    # A runner that could not start is the IMAGE's problem, not ours.
    #
    # By the time this line is written, `patch_broke_the_source` has already
    # taken out the cases the agent caused — a patch that does not parse is
    # reported as a model failure. What is left is the testbed failing to
    # import its own tests: astropy's conftest tearing down without setting
    # up, a test file referencing a fixture that no longer exists, a
    # dependency that moved under the pinned image.
    #
    # It was counted as PIPELINE, which points at this repository, where there
    # is nothing to fix. Two of gpt-oss's three "pipeline" faults in one run
    # were this, both astropy.
    ("tests could not run", r"RUNNER FAILED|the runner did not start"),
]

#: The benchmark working as intended.
MODEL = [
    # Checked BEFORE the pipeline list would see it: a patch that does not
    # parse stops the tests from running, which looks exactly like a runner
    # that never started. It is the agent's own edit, not our environment.
    ("patch does not parse", r"the patch does not parse"),
    ("no patch produced", r"agent produced no patch"),
    ("target tests still failing", r"verdict: not resolved"),
    ("introduced regressions", r"regressions [1-9]"),
]


def classify(line):
    # The model list is consulted first for the few patterns that would
    # otherwise be captured by a broader pipeline one.
    for label, pattern in MODEL[:1]:
        if re.search(pattern, line):
            return "model", label
    for label, pattern in TESTBED:
        if re.search(pattern, line):
            return "testbed", label
    for label, pattern, _ in PIPELINE:
        if re.search(pattern, line):
            return "pipeline", label
    for label, pattern in MODEL:
        if re.search(pattern, line):
            return "model", label
    return "unclassified", line.strip()[:70]


def main(argv):
    roots = [Path(a) for a in argv[1:]]
    if not roots:
        from subprocess import run as sh
        base = Path(sh(["bash", "-c",
                        "source /usr/WS2/haridev/phronix/scripts/bench-root.sh; bench_root"],
                       capture_output=True, text=True).stdout.strip()) / "runs"
        found = sorted((p for p in base.glob("*/") if p.is_dir()),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        roots = found[:1]
    if not roots:
        print("no runs found")
        return 1

    for root in roots:
        traces = list(root.glob("*/tasks/*/trace.log"))
        buckets = {"pipeline": Counter(), "testbed": Counter(),
                   "model": Counter(), "unclassified": Counter()}
        tasks_hit = {"pipeline": set(), "testbed": set(), "model": set()}
        for trace in traces:
            task = trace.parent.name
            try:
                text = trace.read_text(errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                if not re.search(r"ERROR|KILLED|attempt-void|verdict:|NO phronix", line):
                    continue
                # A resolved verdict is a PASS, not a failure of any kind. It
                # matched only because it is a `verdict:` line.
                if "verdict: RESOLVED" in line or "verdict: resolved" in line:
                    continue
                kind, label = classify(line)
                buckets[kind][label] += 1
                if kind in tasks_hit:
                    tasks_hit[kind].add(task)

        print(f"\n=== {root.name}   ({len(traces)} task-arm(s))")
        for kind in ("pipeline", "testbed", "model", "unclassified"):
            total = sum(buckets[kind].values())
            extra = (f", {len(tasks_hit[kind])} task-arm(s) affected"
                     if kind in tasks_hit else "")
            print(f"\n  {kind.upper()}: {total}{extra}")
            for label, n in buckets[kind].most_common(12):
                why = next((w for lbl, _, w in PIPELINE if lbl == label), "")
                print(f"    {n:5d}  {label}")
                if why:
                    print(f"           {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
