#!/usr/bin/env python3
"""Does the revision pass convert a failed try 1 into a passing try 2?

    scripts/try2.sh                  # the newest run
    scripts/try2.sh <run-dir>
    scripts/try2.sh --watch          # refresh every 10s
    scripts/try2.sh --all            # every task, not just the ones that retried

Only the phronix arm retries — the bare arm is given one attempt on purpose,
because an arm with no memory learns nothing from a second sample — so this is a
within-arm measurement, not an arm comparison. `status.sh` answers "where is
each task", `research-progress.sh` answers "is research recording anything at
all". Neither answers the question the retry exists for:

    try 1 failed, research ran a revision pass, did try 2 then PASS?

That is the whole claim of research-on-retry, and it is the number that has been
read off by hand out of trace.log every time.

Read from `<arm>/trace.jsonl`, not from trace.log: the same events are there as
records with `attempt`, `resolved`, `target_passed` and `regressions` already
parsed, so a verdict is never recovered by matching on prose that changes.

The `plan`/`appr` columns come from the research record in the run's OWN session
store. They separate the two ways a try 2 can fail:

  * a revision pass that recorded nothing — no plan, no researched approach —
    means try 2 re-ran on feedback alone and the research budget bought nothing.
    Approaches with `source: benchmark attempt` are written BY the harness from
    the attempt's own diff, so they are counted apart from researched ones; a
    row showing `0/1 appr` recorded no approach of its own.
  * a recorded plan whose try 2 still fails is research that ran and was wrong,
    which is a different problem and a more interesting one.
"""
import glob
import json
import os
import sys
import time

BENCH = os.environ.get("PBENCH", "/p/lustre5/haridev/phronix-bench")
BOLD, DIM, RED, GREEN, YELLOW, RESET = (
    "\033[1m", "\033[2m", "\033[31m", "\033[32m", "\033[33m", "\033[0m")


def newest_run():
    runs = sorted(glob.glob(os.path.join(BENCH, "runs", "*", "")),
                  key=os.path.getmtime)
    return runs[-1].rstrip("/") if runs else None


def events(arm_dir):
    """Every trace record for an arm, oldest first, bad lines skipped.

    The file is appended to while this reads it, so the last line is regularly
    half-written. That is not an error condition — it is the live tail.
    """
    path = os.path.join(arm_dir, "trace.jsonl")
    out = []
    if not os.path.exists(path):
        return out
    with open(path, errors="replace") as handle:
        for line in handle:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def research_record(run, task):
    """The run's own research record for a task, or {}.

    Topics are slugged from the instance id with `__` collapsed to `-`. Only the
    run's session store is consulted: the project layer at .phronix/research
    holds records from every earlier run on the same task, and reading those
    reported plans this run never produced.
    """
    slug = task.replace("__", "-")
    hits = [f for f in glob.glob(f"{run}/*/store/.phronix/research/**/*.json",
                                 recursive=True)
            if os.path.basename(f)[:-5] == slug]
    if not hits:
        return {}
    try:
        with open(max(hits, key=os.path.getmtime)) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def collect(run, arm_dir):
    """One row per task: what each try returned, and what research had to show."""
    tasks = {}
    for event in events(arm_dir):
        task = event.get("task") or ""
        if not task:
            continue
        row = tasks.setdefault(task, {"tries": {}, "revisions": {}, "last": ""})
        kind = event.get("kind") or ""
        summary = event.get("summary") or ""
        if kind == "attempt" and event.get("attempt"):
            row["changed"] = next(
                (d.split("changed: ", 1)[1] for d in event.get("detail") or []
                 if d.startswith("changed: ")), "")
            row["error"] = next(
                (d.split("error: ", 1)[1] for d in event.get("detail") or []
                 if d.startswith("error: ")), row.get("error", ""))
            row["tries"][int(event["attempt"])] = {
                "resolved": bool(event.get("resolved")),
                "passed": event.get("target_passed"),
                # "target tests 1/2, regressions 0" — the denominator is only
                # ever in the detail, and it is what makes 1 meaningful.
                "target": next((d.split("target tests ")[1].split(",")[0]
                                for d in event.get("detail") or []
                                if "target tests " in d), "?"),
                "regressions": event.get("regressions"),
                # The harness compares a retry against the try before it. Kept
                # verbatim: BETTER/WORSE/SAME is its judgement, not this
                # script's, and re-deriving it here would let the two disagree.
                # "vs try 1: BETTER (target 0->1, ...)" — kept verbatim after
                # the try number, because BETTER/WORSE/SAME is the harness's
                # judgement and re-deriving it here would let the two disagree.
                "vs": next((d.split(":", 1)[1].strip() for d in event.get("detail") or []
                            if d.startswith("vs try ")), ""),
            }
        elif kind == "ABORT":
            row["abort"] = summary
        elif kind == "attempt" and (event.get("detail") or []):
            pass
        elif "revision pass for try" in summary:
            row["revisions"][int(summary.rsplit("try", 1)[1])] = event.get("at")
        if kind:
            row["last"] = kind.rstrip(">") or row["last"]
    for task, row in tasks.items():
        last = max(row["tries"]) if row["tries"] else 0
        for path in glob.glob(os.path.join(arm_dir, "tasks", f"*-{task}",
                                           f"attempt-{last}", "evaluation.json")):
            try:
                with open(path) as handle:
                    row["evaluation_error"] = json.load(handle).get("error") or ""
            except (OSError, ValueError):
                pass
        record = research_record(run, task)
        approaches = record.get("approaches") or []
        row["appr_total"] = len(approaches)
        # An approach the harness wrote from the attempt's own diff is not a
        # researched candidate; counting it as one made every task look as
        # though research had proposed something.
        row["appr_researched"] = sum(
            1 for a in approaches if (a.get("source") or "") != "benchmark attempt")
        row["plan"] = bool(record.get("plan"))
        row["chosen"] = (record.get("chosen") or "") or ""
        row["achieved"] = record.get("achieved")
    return tasks


#: Import-time breakages, which is what an agent patch produces when it is
#: syntactically or semantically wrong: the suite cannot even be collected.
ROOT_CAUSE = ("SyntaxError", "NameError", "ImportError", "IndentationError",
              "AttributeError", "ModuleNotFoundError", "TypeError")


def root_cause(error):
    """The line that actually says what broke, out of a truncated error blob.

    The harness quotes the TAIL of the testbed's output — `[-400:]`, `[-300:]`
    — and a tail cut by character count starts mid-token: the recorded cause of
    a lost task reads `the runner did not start: rning`, which is the end of
    the word "warning" from a pip notice. The exception line is in there; it is
    just not at the end. Pull it out rather than reprint the slice.
    """
    lines = [l.strip() for l in (error or "").splitlines() if l.strip()]
    for line in reversed(lines):
        if any(line.startswith(name) or f" {name}:" in line for name in ROOT_CAUSE):
            return line.split(" (install said")[0][:96]
    return (lines[-1][:96] if lines else "")


def blamed_file(error):
    """The last /testbed path named in the traceback — the file that broke."""
    hits = [w.strip('",') for w in (error or "").replace("\n", " ").split()
            if w.strip('",').startswith("/testbed/")]
    return hits[-1][len("/testbed/"):] if hits else ""


def cut_short(rows):
    """Tasks the retry loop abandoned, and whether the agent caused it.

    `runner_failed` aborts the task outright — no further try — and it exists
    for a real reason: sympy-24066 spent three attempts producing byte-identical
    diffs against a suite that could not execute. But it does not distinguish
    the two ways the suite can fail to execute:

      env   the testbed is broken independently of the patch. Abort is right.
      self  the AGENT'S OWN patch broke it — a stray `+` in
            `pylint/lint/__init__.py` is a SyntaxError, so conftest cannot
            import and nothing runs. That is a perfectly judgeable failure
            ("your patch does not import") and exactly the case a retry fixes,
            but it is being aborted as though the harness were at fault.

    Told apart here by asking whether the file named in the traceback is one
    the attempt changed. Cheap, and right in every case measured so far.
    """
    out = []
    for task in sorted(rows):
        row = rows[task]
        if not row.get("abort"):
            continue
        # The full error, from the attempt's own evaluation.json. The trace
        # event carries the harness's already-truncated copy, and truncating
        # that again is how the cause came out as `ImportErr`.
        error = row.get("evaluation_error") or row.get("error") or row.get("abort") or ""
        blamed = blamed_file(error)
        changed = [c.strip() for c in (row.get("changed") or "").split(",")]
        # The harness writes its own launcher into the working tree, so
        # `agent-on-node-*.sh` is in every changed list and is never the cause.
        changed = [c for c in changed if c and not c.startswith("agent-on-node-")]
        self_inflicted = bool(blamed) and any(
            blamed == c or blamed.endswith("/" + c) or c.endswith(blamed)
            for c in changed)
        out.append((task, max(row["tries"] or [0]), self_inflicted, blamed,
                    root_cause(error)))
    return out


def pad(text, width):
    """Left-justify by VISIBLE width. Colour codes occupy no columns, and
    padding against len() put every coloured cell short by the length of its
    escape sequences — the table sheared one column further right per row."""
    visible = len(text)
    index = 0
    while index < len(text):
        if text[index] == "\033":
            end = text.find("m", index)
            if end == -1:
                break
            visible -= end - index + 1
            index = end + 1
            continue
        index += 1
    return text + " " * max(0, width - visible)


def verdict(entry, fallback_total=""):
    """Colourised outcome plus the target-test fraction.

    A try that changed nothing has no "target tests" line at all — the harness
    prints only the comparison — so the fraction is recovered from `target
    a->b` and the denominator borrowed from the try that did report one.
    Otherwise a real 0/1 and an unreported one both showed as `?`.
    """
    if entry is None:
        return DIM + "-" + RESET, "-"
    target = entry["target"]
    if target == "?" and "target " in (entry["vs"] or ""):
        after = entry["vs"].split("target ")[1].split(")")[0].split(",")[0]
        if "->" in after:
            target = after.split("->")[1].strip() + "/" + (fallback_total or "?")
    mark = GREEN + "PASS" + RESET if entry["resolved"] else RED + "fail" + RESET
    return mark, target


def report(run, show_all):
    print(f"run: {run}")
    for arm_dir in sorted(glob.glob(os.path.join(run, "*", ""))):
        arm = os.path.basename(arm_dir.rstrip("/"))
        tasks = collect(run, arm_dir.rstrip("/"))
        if not tasks:
            continue
        # A bare arm has one attempt by design; printing a try-2 table for it
        # would be a page of dashes implying something is missing.
        retried = {t: r for t, r in tasks.items() if r["revisions"] or 2 in r["tries"]}
        if not retried and not show_all:
            print(f"\n=== {arm}: no task has reached a revision pass "
                  f"({len(tasks)} task(s) on try 1)")
            continue
        rows = tasks if show_all else retried
        print(f"\n=== {arm}   {len(retried)} of {len(tasks)} task(s) into try 2")
        print(f"{BOLD}  {'task':<34}{'try1':<12}{'revision':<10}{'plan':<6}{'appr':<7}"
              f"{'try2':<12}{'vs try 1':<34}{'later'}{RESET}")
        converted = improved = flat = still_running = barren = 0
        for task in sorted(rows):
            row = rows[task]
            one, one_t = verdict(row["tries"].get(1))
            total = one_t.split("/")[1] if "/" in one_t else ""
            two_entry = row["tries"].get(2)
            two, two_t = verdict(two_entry, total)
            if row["revisions"]:
                pass_state = GREEN + "ran" + RESET
            else:
                pass_state = DIM + "-" + RESET
            if 2 in row["revisions"] and two_entry is None:
                two, two_t = YELLOW + "…run" + RESET, "-"
                still_running += 1
            elif two_entry is not None:
                if two_entry["resolved"]:
                    converted += 1
                elif "BETTER" in (two_entry["vs"] or ""):
                    improved += 1
                else:
                    flat += 1
            researched = row.get("appr_researched", 0)
            if 2 in row["revisions"] and not row.get("plan") and not researched:
                barren += 1
                appr = RED + f"{researched}/{row.get('appr_total', 0)}" + RESET
            else:
                appr = f"{researched}/{row.get('appr_total', 0)}"
            plan = "yes" if row.get("plan") else DIM + "no" + RESET
            # Tries past the second are rare and are the same question asked
            # again; the last one is shown rather than a column per try.
            later = ""
            if row["tries"] and max(row["tries"]) > 2:
                last = max(row["tries"])
                mark, frac = verdict(row["tries"][last], total)
                later = f"try {last} {mark} {frac}"
            vs = (two_entry or {}).get("vs", "")
            vs = vs[:31] + "…" if len(vs) > 32 else vs
            print("  " + pad(task, 34) + pad(one, 6) + pad(one_t, 6)
                  + pad(pass_state, 10) + pad(plan, 6) + pad(appr, 7)
                  + pad(two, 6) + pad(two_t, 6)
                  + pad(DIM + vs + RESET, 34) + later)
        done = converted + improved + flat
        print()
        print(f"  reached try 2      : {len(retried)}"
              f"   ({still_running} still running)")
        if done:
            print(f"  {GREEN}try 2 PASSED{RESET}       : {converted}/{done} "
                  f"resolved   ({100.0 * converted / done:.0f}% of finished retries)")
            print(f"  closer but failing : {improved}")
            print(f"  no better          : {flat}")
        aborted = cut_short(tasks)
        if aborted:
            print()
            print(f"  {YELLOW}cut short by a runner failure{RESET} — "
                  f"{len(aborted)} task(s) left the retry loop early")
            for task, last, mine, blamed, cause in aborted:
                tag = (RED + "self " + RESET if mine else DIM + "env  " + RESET)
                print(f"    {tag} {pad(task, 34)}after try {last}  "
                      f"{DIM}{blamed or '?'}{RESET}  {cause}")
            if any(a[2] for a in aborted):
                print(f"    {DIM}self = the agent's own patch broke the testbed;"
                      f" retrying is what fixes that, and it was aborted{RESET}")
        if barren:
            # The failure research-progress.sh exists to surface, scoped to the
            # retry: a revision pass that recorded neither a plan nor an
            # approach spent its budget and left try 2 with feedback.md alone.
            print(f"  {RED}revision recorded nothing{RESET}: {barren} "
                  f"— those try 2s ran on feedback alone, not on research")


def main():
    args = [a for a in sys.argv[1:]]
    watch = "--watch" in args
    show_all = "--all" in args
    args = [a for a in args if not a.startswith("--")]
    run = (args[0] if args else newest_run() or "").rstrip("/")
    if not run or not os.path.isdir(run):
        sys.exit(f"no run directory: {run or '(none found)'}")
    if not watch:
        report(run, show_all)
        return
    try:
        while True:
            print("\033[H\033[J", end="")
            report(run, show_all)
            sys.stdout.flush()
            time.sleep(10)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
