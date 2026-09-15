#!/usr/bin/env python3
"""Re-score stored evaluations whose pytest output was misread.

    scripts/rescore.py --dry-run            # what would change
    scripts/rescore.py                      # apply
    scripts/rescore.py --runs <dir> ...     # limit to some runs

`_passed_node_ids` matched pytest's summary with `startswith("PASSED ")`, and
pytest colours that summary when it believes it has a terminal:

    '\\x1b[32mPASSED\\x1b[0m astropy/...::\\x1b[1mtest_rst_with_header_rows\\x1b[0m'

So for every coloured run the parser found NO passing tests and scored the
whole suite as failed. Measured across 1,443 stored evaluations: 185 coloured,
100 of them recording a target test as failing that their own captured output
names as PASSED. `astropy__astropy-14182` and
`scikit-learn__scikit-learn-25500` account for all of them -- two instances
that looked unsolvable and were being solved repeatedly.

The transcripts were captured in full, so nothing needs re-running: the same
verdict rule applied to the same output gives the score the run should have
had. Rewritten records carry `rescored_by`, and the original verdict is kept
under `original` so the correction is always visible as a correction.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

BENCH = Path("/p/lustre3/haridev/phronix-bench")


def verdict(evaluation: dict) -> dict | None:
    """Re-derive the verdict from the captured output, or None if unchanged."""
    from tests.benchmark.runner import _passed_node_ids

    output = evaluation.get("output_tail") or ""
    passed_ids = _passed_node_ids(output)
    if not passed_ids:
        return None

    # The obligations, recovered from what the record already names. A test is
    # either in the passing list or the failing one, and their union is the
    # instance's FAIL_TO_PASS set.
    # FAIL_TO_PASS is fully recoverable: the record lists both halves.
    f2p_names = sorted(set(evaluation.get("fail_to_pass_failing") or [])
                       | set(evaluation.get("fail_to_pass_passing") or []))
    if not f2p_names:
        return None

    # PASS_TO_PASS is NOT. A record enumerates only the ones that FAILED --
    # regressions and pre-existing — and says nothing about which passed, so
    # rebuilding the list from those names gives a total of zero for a suite
    # where everything passed. The stored total is the only witness to how
    # many there were, so it is kept and only the named failures are re-judged.
    p2p_failed_before = sorted(set(evaluation.get("regressions") or [])
                               | set(evaluation.get("pre_existing_failures") or []))
    p2p_total = int(evaluation.get("pass_to_pass_total") or 0)

    def passed(name: str) -> bool:
        # Same rule as the runner: sympy stores bare function names while
        # pytest reports full node ids.
        if "::" in name:
            return any(a.startswith(name) for a in passed_ids)
        return any(a.startswith(name) or a.split("::")[-1].startswith(name)
                   for a in passed_ids)

    # A pass already on the record STAYS a pass.
    #
    # `output_tail` is a TAIL -- capped at 2000 characters, and observed
    # starting mid-word -- so a target whose PASSED line scrolled off the top
    # is invisible here. Absence of evidence is not evidence of failure, and a
    # rescorer that treated it that way turned a resolved pylint record into
    # `1/1 -> 0/1` on nothing but a truncated buffer. This correction exists to
    # find passes the parser could not see; it may never take one away.
    already_passing = set(evaluation.get("fail_to_pass_passing") or [])
    f2p = {n: (n in already_passing or passed(n)) for n in f2p_names}
    # Of the ones previously recorded as failing, which does the output
    # actually name as passing? Everything else in the suite was passing
    # already and is untouched by this correction.
    still_failing = sorted(n for n in p2p_failed_before if not passed(n))
    p2p_passed = max(0, p2p_total - len(still_failing))
    regressions = still_failing
    resolved = all(f2p.values()) and not regressions
    # Unchanged means unchanged in EVERY number, not just the verdict. A
    # record can have the right resolved flag and still be wrong about which
    # pass-to-pass tests survived — and those wrong entries are what get
    # cached as "pre-existing failures" and poison later runs of the instance.
    same = (resolved == bool(evaluation.get("resolved"))
            and sum(f2p.values()) == (evaluation.get("fail_to_pass_passed") or 0)
            and p2p_passed == (evaluation.get("pass_to_pass_passed") or 0))
    if same:
        return None

    return {
        "resolved": resolved,
        "fail_to_pass_passed": sum(f2p.values()),
        "fail_to_pass_total": len(f2p),
        "pass_to_pass_passed": p2p_passed,
        "pass_to_pass_total": p2p_total,
        "fail_to_pass_failing": sorted(n for n, ok in f2p.items() if not ok),
        "fail_to_pass_passing": sorted(n for n, ok in f2p.items() if ok),
        "regressions": regressions,
        "pre_existing_failures": [],
    }


def apply_to(path: Path, dry: bool) -> tuple[bool, str]:
    try:
        evaluation = json.loads(path.read_text())
    except (ValueError, OSError):
        return False, ""
    if evaluation.get("rescored_by"):
        return False, ""
    fixed = verdict(evaluation)
    if fixed is None:
        return False, ""
    was = f"{evaluation.get('fail_to_pass_passed')}/{evaluation.get('fail_to_pass_total')}"
    now = f"{fixed['fail_to_pass_passed']}/{fixed['fail_to_pass_total']}"
    note = (f"{'RESOLVED' if fixed['resolved'] else 'not resolved'}  "
            f"target {was} -> {now}")
    if not dry:
        merged = dict(evaluation)
        merged["original"] = {k: evaluation.get(k) for k in
                              ("resolved", "fail_to_pass_passed",
                               "fail_to_pass_failing", "pass_to_pass_passed",
                               "pre_existing_failures")}
        merged.update(fixed)
        merged["rescored_by"] = "rescore.py (coloured pytest output)"
        path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return True, note


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--runs", nargs="*", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roots = ([args.bench / "runs" / r for r in args.runs] if args.runs
             else [args.bench / "runs"])
    changed = 0
    by_instance: dict[str, int] = {}
    for root in roots:
        # An explicit pattern, not `**`. Recursive globbing walks every task's
        # cache and store-after tree -- hundreds of thousands of files per run
        # -- and never reaches the evaluations; the same sweep with the shape
        # spelled out finishes in seconds.
        pattern = ("claude-*/tasks/*/attempt-*/evaluation.json"
                   if root.name == "runs" else "*/tasks/*/attempt-*/evaluation.json")
        paths = (sorted(root.glob(f"*/{pattern}")) if root.name == "runs"
                 else sorted(root.glob(pattern)))
        for path in paths:
            did, note = apply_to(path, args.dry_run)
            if not did:
                continue
            changed += 1
            task = str(path).split("/tasks/")[-1].split("/")[0]
            by_instance[task] = by_instance.get(task, 0) + 1
            if changed <= 6:
                print(f"  {task}: {note}")
    print(f"\n{'would rescore' if args.dry_run else 'rescored'} {changed} evaluation(s)")
    for task, n in sorted(by_instance.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>3}  {task}")


if __name__ == "__main__":
    main()
