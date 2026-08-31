#!/usr/bin/env python3
"""`top` for a benchmark run: overall stats, arms, and tasks as processes.

Launched by `scripts/top.sh`, which is the documented entry point.

Why this exists next to `status.sh` rather than inside it. `status.sh` prints
EVERYTHING it knows, which is the right shape for a report and the wrong one
for watching: a 30-task run scrolls past a screen several times over, so the
one thing a watcher wants — what is stuck, what failed — is never on screen at
the same time as the totals. This shows the whole run in a screenful and lets
the reader open only the part they care about, the way `top` shows a machine.

The hierarchy is the display:

    run header          what this run is, and how the whole thing is going
      arm               one row per arm — pass/fail/running, cost, rate
        task            one row per task, like a process row
          detail        opened on demand: tries, research, trials, skills

Nothing is computed that is not on screen. A task's transcripts are only read
when its row is expanded, because reading them for 60 tasks on lustre costs
more than the frame budget and answers a question nobody asked.
"""

from __future__ import annotations

import curses
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

def _bench_root() -> Path:
    """The workspace on THIS machine — see scripts/bench-root.sh for the why.

    top.sh exports PHRONIX_BENCH before exec'ing this, so the probe below is
    for the case where bench_top.py is run directly: the clusters do not share
    a parallel filesystem, and defaulting to Tuolumne's on corona reports "no
    runs" for a run that is going fine on a mount this host cannot see.
    """
    override = os.environ.get("PHRONIX_BENCH")
    if override:
        return Path(override)
    user = os.environ.get("USER") or "haridev"
    first = None
    for base in ("/p/lustre5", "/p/lustre4", "/p/lustre3", "/p/lustre2", "/p/lustre1"):
        root = Path(base) / user / "phronix-bench"
        if not root.is_dir():
            continue
        if first is None:
            first = root
        if any((root / "runs").glob("*")):
            return root
    return first or Path("/p/lustre5") / user / "phronix-bench"


BENCH = _bench_root()
RUNS = BENCH / "runs"

#: How often the screen is rebuilt. Two seconds is the same fuse `top` uses and
#: is far below the rate at which anything here changes; the cost is a few
#: hundred stats on lustre, not a walk of the checkouts.
REFRESH_S = float(os.environ.get("PHRONIX_TOP_REFRESH", "2"))

#: Silence in a task's trace past this is worth a mark. Long, because the trace
#: only ticks when an event lands and a single model turn is minutes of nothing.
QUIET_S = int(os.environ.get("PHRONIX_QUIET_SECONDS", "900"))

#: `... (12 steps, 1,738,990 tok)` in a trace line.
TOKENS_IN_TRACE = re.compile(r"\(\d+ steps?, ([\d,]+) tok\)")


# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------

def human(seconds) -> str:
    """45s | 12m30s | 2h05m — the same shape status.sh writes."""
    try:
        s = int(seconds or 0)
    except (TypeError, ValueError):
        return "-"
    if s >= 3600:
        return f"{s // 3600}h{s % 3600 // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s}s"


def human_hms(seconds) -> str:
    """45s | 12m30s | 2h05m30s — like `human`, but never drops the seconds.

    `human` rounds an hour-long run to the minute, which is right for a column
    that has to stay narrow. The run header is not that: it is the one place
    somebody reads the elapsed time directly, and a run that has been going
    "2h05m" for a minute at a time looks stalled.
    """
    try:
        s = int(seconds or 0)
    except (TypeError, ValueError):
        return "-"
    if s >= 3600:
        return f"{s // 3600}h{s % 3600 // 60:02d}m{s % 60:02d}s"
    if s >= 60:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s}s"


def short(n) -> str:
    """A token count at a glance: 940, 12.5k, 243k, 1.6M."""
    try:
        n = max(0, int(n or 0))
    except (TypeError, ValueError):
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 100_000:
        return f"{n / 1000:.0f}k"
    if n >= 1_000:
        return f"{n / 1000:.1f}k"
    return str(n)


def money(value) -> str:
    return f"${value:.2f}" if value else ""


# --------------------------------------------------------------------------
# reading the run off disk
# --------------------------------------------------------------------------

def tail_lines(path: Path, limit: int = 65536):
    """The last chunk of a file, without reading the whole thing.

    A live trace grows without bound and is on lustre; the display only ever
    wants its last event, so the read is bounded from the end.
    """
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - limit))
            data = handle.read()
    except OSError:
        return []
    text = data.decode("utf-8", "replace")
    if size > limit:
        text = text.split("\n", 1)[-1]      # drop the half line at the front
    return text.splitlines()


def first_line(path: Path) -> str:
    try:
        with path.open("r", errors="replace") as handle:
            return handle.readline().rstrip("\n")
    except OSError:
        return ""


def parse_clock(stamp: str, now: float) -> float:
    """A trace timestamp (`00:21:12`) as an epoch second.

    The trace writes time of day with no date, so a run that crossed midnight
    parses as later today; anything in the future is yesterday.
    """
    try:
        when = datetime.strptime(stamp, "%H:%M:%S").time()
    except ValueError:
        return 0.0
    today = datetime.fromtimestamp(now).date()
    got = datetime.combine(today, when).timestamp()
    if got > now + 60:
        got = (datetime.combine(today, when) - timedelta(days=1)).timestamp()
    return got


def split_event(line: str):
    """`00:21:12 [arm:pid:task] stage>  message` -> (stage, message).

    The bracketed prefix is the marker of a real event; a continuation line
    carrying only detail has none, and returning it as a stage is how the
    display ended up showing "budget 1800s" as a stage name.
    """
    _, sep, rest = line.partition("] ")
    if not sep:
        return "", ""
    stage, _, message = rest.strip().partition(" ")
    message = message.strip()
    # A fanout member names itself inside the message — `[aspect:foo] text` —
    # rather than in the stage column, so lift the label to where it belongs.
    if message.startswith("["):
        label, close, tail = message[1:].partition("]")
        if close:
            stage = f"{stage}{label}>"
            message = tail.strip()
    # `research>aspect:change_risk@gpt-oss-120b>` spends the whole column on a
    # backend alias. The aspect name is already in the message.
    if ":" in stage:
        head, _, tail = stage.partition(":")
        stage = f"{head}:{tail.split('@', 1)[0].rstrip('>')}>"
    return stage, message


#: The phases a live task moves through, in order, and how a stage names them.
#
# The stage column is the task's own account of where it is — `research>plan`,
# `attempt>`, `evaluate>` — so the phase is a prefix match rather than anything
# this file has to track. Order matters: the list is rendered in it, so a reader
# sees the pipeline's shape rather than an alphabetical accident.
PHASES = (
    ("research", ("research",)),
    ("attempt", ("attempt", "search-skill", "recall")),
    ("evaluate", ("evaluate", "promoted", "trial", "approach-")),
    # The tracker: its own stage, run after every other one, folding what just
    # happened into the task's record. Without an entry here it matched no
    # prefix and fell through to "not started" — so a task actively recording
    # read as a task that had not begun, which is the one thing this column
    # exists to distinguish.
    ("track", ("track",)),
    # Everything before the first real stage: exporting the checkout, waiting
    # for a slot, or nothing reported yet. A task sitting here for a long time
    # is queued, which at 6x oversubscription is most of them.
    ("not started", ()),
)


def phase_of(task) -> str:
    """Which phase a running task is in, by the stage it last reported."""
    stage = (getattr(task, "stage", "") or "").lower()
    if not stage:
        return "not started"
    for name, prefixes in PHASES:
        if any(stage.startswith(prefix) for prefix in prefixes):
            return name
    return "not started"


class Task:
    """One task in one arm — a row in the process list."""

    def __init__(self, arm: "Arm", path: Path, now: float):
        self.arm = arm
        self.path = path
        self.now = now
        # `000-sphinx-doc__sphinx-11445` -> `sphinx-doc__sphinx-11445`. The
        # ordinal is the runner's, and it is already implied by the row order.
        self.name = path.name.split("-", 1)[-1]
        self.key = f"{arm.name}/{path.name}"

        self.result = None
        try:
            self.result = json.loads((path / "result.json").read_text())
        except (OSError, ValueError):
            pass

        self.tries = len(list(path.glob("attempt-*"))) or 1
        trace = path / "trace.log"
        self.trace = trace
        self.stage, self.message, self.started, self.idle = "", "", 0.0, 0.0
        #: Tokens reported by attempts that have already ENDED, for a task that
        #: is still going. Read from the trace tail this loop is reading anyway.
        self.live_tokens = 0
        if trace.is_file():
            lines = tail_lines(trace)
            # `attempt      try 2: fail (7 steps, 336,433 tok)` — the only live
            # token figure there is.
            #
            # `Task.tokens` reads `result.json`, which is written when the TASK
            # finishes, so an arm with nothing finished showed `0 tok` however
            # long it had been running. Measured: the phronix arm sat at 0 for
            # eight minutes while its research burned 1.7M tokens on one task,
            # next to a bare arm reading 408k — which invites exactly the wrong
            # conclusion about which arm is expensive.
            #
            # Bounded by the same tail, so an old attempt scrolled out of it is
            # not counted: this is a floor, not a total.
            for line in lines:
                found = TOKENS_IN_TRACE.search(line)
                if found:
                    self.live_tokens += int(found.group(1).replace(",", ""))
            events = [l for l in lines if "] " in l]
            if events:
                self.stage, self.message = split_event(events[-1])
            head = first_line(trace)
            if head:
                self.started = parse_clock(head.split(" ", 1)[0], now)
            try:
                self.idle = now - trace.stat().st_mtime
            except OSError:
                self.idle = 0.0

        # Finished is not the same as having a result file: a run whose results
        # are batched to the end still traces `promoted` as its last act.
        self.done = self.result is not None
        if not self.done and self.stage.startswith(("promoted", "task-done")):
            self.done = True

    # -- derived ---------------------------------------------------------
    @property
    def state(self) -> str:
        if not self.done:
            return "run"
        return "pass" if (self.result or {}).get("resolved") else "fail"

    @property
    def elapsed(self) -> float:
        if self.done and self.result:
            attempts = self.result.get("attempts") or []
            wall = sum(float(a.get("wall_s") or 0) for a in attempts)
            if wall:
                return wall
        return self.now - self.started if self.started else 0.0

    @property
    def attempts(self):
        return (self.result or {}).get("attempts") or []

    @property
    def skills(self) -> str:
        """What this task left in the store, by name, for the finished line.

        A finished task's line said only `resolved`, which is the outcome and
        not the point: the benchmark asks whether the work makes the NEXT task
        cheaper, and that is answered by what was written and what was picked
        up. `+` is new, `~` is reused from an earlier task.
        """
        result = self.result or {}
        parts = [f"+{name}" for name in (result.get("skills_created") or [])]
        parts += [f"~{name}" for name in (result.get("skills_reused") or [])]
        return " ".join(parts)

    @property
    def tokens(self) -> int:
        recorded = sum(int(a.get("tokens_input") or 0)
                       + int(a.get("tokens_output") or 0)
                       for a in self.attempts)
        # A finished task's own record is authoritative; a running one has none,
        # so fall back to what its trace has reported so far.
        return recorded or self.live_tokens

    @property
    def cost(self) -> float:
        return sum(float(a.get("cost_usd") or 0)
                   + float(a.get("research_cost_usd") or 0) for a in self.attempts)

    @property
    def steps(self) -> int:
        return sum(int(a.get("steps") or 0) for a in self.attempts)

    def detail(self):
        """The lines shown when this row is opened.

        Read lazily, and only for the row the reader asked about: the same walk
        across 60 tasks is seconds of lustre per frame.
        """
        out = []
        result = self.result or {}
        if self.done:
            passes = ((result.get("research") or {}).get("passes_detail") or [])
            out.append(("dim", f"tries={result.get('tries', len(self.attempts))}"
                               f"   steps={self.steps}   tok={short(self.tokens)}"
                               f"   {human(self.elapsed)}   {money(self.cost)}"))
            for a in self.attempts:
                index = int(a.get("index") or 0)
                outcome = ("PASS" if a.get("resolved")
                           else (str(a.get("error") or "")[:34] or "fail"))
                trend = a.get("failure_trend") or ""
                mark = ("moved" if trend == "moved"
                        else f"SAME x{a.get('same_failure_count') or 2}"
                        if trend == "same" else "")
                wall = max(0.0, float(a.get("wall_s") or 0)
                           - float(a.get("research_s") or 0)
                           - float(a.get("learn_s") or 0))
                out.append(("pass" if a.get("resolved") else "fail",
                            f"try{index} {outcome:<34} {mark:<9}"
                            f" steps={int(a.get('steps') or 0):<3}"
                            f" {short(int(a.get('tokens_input') or 0) + int(a.get('tokens_output') or 0)):>7}"
                            f" {human(wall):>7}"))
                # The stages INSIDE the try, as a tree.
                #
                # A try's totals say it took nine minutes; they do not say
                # whether that was the attempt thinking, the evaluation running
                # tests, or research diagnosing. Those are different problems
                # with different fixes, and the totals hide which one you have.
                last = len(a.get("stages") or []) - 1
                for n, st in enumerate(a.get("stages") or []):
                    elbow = "└─" if n == last and not a.get("recalled_skill") else "├─"
                    steps = int(st.get("steps") or 0)
                    tok = int(st.get("tokens_input") or 0) + int(st.get("tokens_output") or 0)
                    out.append(("dim",
                                f"  {elbow} {str(st.get('name', '?'))[:14]:<14}"
                                f" steps={steps:<3}"
                                f" {short(tok):>7}"
                                f" {human(float(st.get('elapsed_s') or 0)):>7}"
                                + (f"  {st['note']}" if st.get("note") else "")))
                if a.get("recalled_skill"):
                    out.append(("dim", f"  └─ skill: {a['recalled_skill']} (solved with it)"))
                for trial in a.get("trials") or []:
                    won = "SOLVED" if trial.get("resolved") else "failed"
                    out.append(("pass" if trial.get("resolved") else "dim",
                                f"  {won:<7} {str(trial.get('plan', '?'))[:46]:<46}"
                                f" {trial.get('target_tests_passed', 0)} target test(s)"))
                if a.get("solution_skill"):
                    out.append(("dim", f"  solution: {a['solution_skill']}"))
            if passes:
                spent = sum(float(p.get("elapsed_s") or 0) for p in passes)
                tok = sum(int(p.get("tokens_input") or 0)
                          + int(p.get("tokens_output") or 0) for p in passes)
                out.append(("dim", f"research: {len(passes)} pass(es), "
                                   f"{human(spent)}, {short(tok)}tok"))
            elif result:
                out.append(("dim", "research: none ran"))
        else:
            # In flight: the recent trace is the only thing that exists, and it
            # is exactly what somebody opening this row wants to read.
            for line in tail_lines(self.trace)[-12:]:
                if "] " not in line:
                    continue
                stage, message = split_event(line)
                out.append(("dim", f"{line.split(' ', 1)[0]}  {stage[:30]:<30} "
                                   f"{message[:90]}"))
        out.append(("dim", f"tail -f {self.trace}"))
        return out


class Arm:
    """One arm of the comparison — the group tasks are listed under."""

    def __init__(self, path: Path, now: float, planned=()):
        self.path = path
        self.name = path.name
        self.key = path.name
        #: Every instance the run intends this arm to attempt, started or not.
        self.planned = list(planned)
        # A task directory with neither a trace nor a result has not started
        # and may never: a run leaves empty shells behind (`.../tasks/...`, a
        # truncated duplicate of a real id). Counting them inflates the
        # denominator every percentage on this screen is divided by.
        self.tasks = [t for t in
                      (Task(self, p, now) for p in sorted((path / "tasks").glob("*"))
                       if p.is_dir())
                      if t.trace.is_file() or t.result is not None]

    @property
    def queued(self):
        """Planned instances this arm has not started yet, in run order.

        A task directory is named `<index>-<instance_id>`, so the instance is
        what survives the split; matching on it rather than on the directory
        name is what makes this survive a change to the numbering.
        """
        started = {t.path.name.split("-", 1)[-1] for t in self.tasks}
        return [name for name in self.planned if name not in started]

    @property
    def passed(self):
        return sum(1 for t in self.tasks if t.state == "pass")

    @property
    def failed(self):
        return sum(1 for t in self.tasks if t.state == "fail")

    @property
    def running(self):
        return sum(1 for t in self.tasks if t.state == "run")

    @property
    def cost(self):
        return sum(t.cost for t in self.tasks)

    @property
    def tokens(self):
        return sum(t.tokens for t in self.tasks)

    @property
    def finished_time(self):
        done = [t for t in self.tasks if t.done]
        return sum(t.elapsed for t in done) / len(done) if done else 0.0


class Run:
    """Everything on screen, read fresh each refresh."""

    def __init__(self, path: Path):
        self.path = path
        self.reload()

    def reload(self):
        now = time.time()
        self.now = now
        # The manifest FIRST, because it is the only place the run's plan lives.
        #
        # Arms discover their tasks from directories on disk, and a directory
        # appears only when a task starts — so a six-task run showed two rows
        # and read as a two-task run. What is queued is as much a part of the
        # picture as what is running: without it there is no way to tell a run
        # that is nearly done from one that has barely begun.
        try:
            self.manifest = json.loads((self.path / "manifest.json").read_text())
        except (OSError, ValueError):
            self.manifest = {}
        planned = [str(t) for t in (self.manifest.get("tasks") or [])]

        self.arms = [a for a in
                     (Arm(p, now, planned) for p in sorted(self.path.iterdir())
                      if p.is_dir() and (p / "tasks").is_dir())
                     if a.tasks]

        # Liveness from the two files the runner touches on every stage, not
        # from a walk: a walk of a live run is 100k files and 20s on lustre.
        stamps = []
        for pattern in ("*/trace.log", "*/results.jsonl", "manifest.json"):
            for p in self.path.glob(pattern):
                try:
                    stamps.append(p.stat().st_mtime)
                except OSError:
                    pass
        for arm in self.arms:
            for task in arm.tasks[:200]:
                if task.idle:
                    stamps.append(now - task.idle)
        self.age = now - max(stamps) if stamps else None

        start = 0.0
        try:
            start = datetime.fromisoformat(self.manifest["created_at"]).timestamp()
        except (KeyError, ValueError, TypeError):
            start = min(stamps) if stamps else now
        # Measured to NOW while the run is live, and to the last write once it
        # is not. `max(stamps) - start` is the span of the writing, which stops
        # advancing the moment every agent is mid-turn — so a busy run's
        # elapsed time froze exactly when it was working hardest.
        last = max(stamps) if stamps else now
        # Same test the state uses, so a run cannot read ACTIVE with a frozen
        # elapsed time.
        end = now if self.active else last
        self.wall = max(0.0, end - start)

    @property
    def tasks(self):
        return [t for arm in self.arms for t in arm.tasks]

    #: Silence after which a run is called INACTIVE, in seconds.
    #:
    #: The trace only ticks when an EVENT lands, and one agent turn is one
    #: event. On a local fleet a turn is routinely several minutes — measured
    #: on a live 30-task run, every task in flight and the runner healthy, the
    #: newest trace write was 11m44s old. Three minutes therefore reported a
    #: working run as dead, which is the same mistake the fleet view made when
    #: it called a busy replica down for missing one probe.
    #:
    #: Taken from the run's OWN attempt budget rather than fixed here.
    #:
    #: An attempt is the longest a single stage may run, so silence shorter
    #: than one attempt budget cannot distinguish "mid-turn" from "wedged" —
    #: and a fixed number is wrong the moment the budget changes. Measured on a
    #: live run: the job RUN for 40 minutes, every task in flight, and the
    #: newest trace write 15m36s old. Three minutes, and then fifteen, both
    #: called it dead.
    QUIET_S = 1800

    @property
    def quiet_limit(self) -> float:
        """Silence tolerated before INACTIVE, from the manifest where it says."""
        try:
            budget = float(self.manifest.get("timeout_s") or 0)
        except (TypeError, ValueError):
            budget = 0.0
        # A margin over the budget: a stage that ends exactly on its ceiling
        # still has to write the line that says so.
        return max(self.QUIET_S, budget * 1.25)

    @property
    def active(self) -> bool:
        """Whether anything wrote recently, or the runner is still alive.

        The process is the direct signal and the trace is an inference from it,
        so the process wins where both are available. It is only available when
        this is watching a run on the same machine, which is the common case.
        """
        if self.finished:
            return False
        if self.runner_alive:
            return True
        return self.age is not None and self.age < self.quiet_limit

    @property
    def finished(self) -> bool:
        """Has this run written its report — i.e. reached its end?

        A definite terminal signal, and it has to be checked FIRST, because
        the two live signals both say "active" for a run that is over. The
        pid check needs a `trace.log`, which a run that died before its first
        task never wrote, so it reports 0 and abstains; the silence threshold
        then sees a directory touched fifteen minutes ago against a thirty
        minute limit and calls it ACTIVE. That is exactly what mix30-reuse
        did: both arms died sixty seconds in, and top showed `ACTIVE 14m42s`
        over a run that had been dead the whole time.

        `report.json` is written once, after the arms return — whether they
        returned results or exceptions. So it means finished, not succeeded.
        """
        return (self.path / "report.json").exists()

    @property
    def runner_alive(self) -> bool:
        """Is THIS run's runner process still going on this machine?

        Its pid, not any runner's: several runs go at once on this cluster, and
        `pgrep -f "benchmark.cli run"` would report every one of them alive
        because a sibling was. The pid is in the trace — every line carries
        `[<arm>:<pid>...]` — so it costs a read of one line.

        False when the run is on another machine, which is correct: this
        cannot know, and the silence threshold decides instead.
        """
        pid = self.runner_pid
        if not pid:
            return False
        try:
            os.kill(pid, 0)          # signal 0: does it exist and is it ours
            return True
        except (ProcessLookupError, ValueError):
            return False
        except PermissionError:
            return True              # exists, owned by somebody else

    @property
    def runner_pid(self) -> int:
        """The pid recorded in this run's trace, or 0."""
        if getattr(self, "_runner_pid", None) is not None:
            return self._runner_pid
        self._runner_pid = 0
        for trace in sorted(self.path.glob("*/trace.log")):
            try:
                with trace.open(encoding="utf-8", errors="replace") as handle:
                    first = handle.readline()
            except OSError:
                continue
            found = re.search(r"\[[^:\]]+:(\d+)", first)
            if found:
                self._runner_pid = int(found.group(1))
                break
        return self._runner_pid

    @property
    def state(self) -> str:
        # ACTIVE / INACTIVE rather than ALIVE / stopped: "stopped" claims to
        # know that somebody stopped it, and this only knows that nothing has
        # been written. The two are different — and one of them is a fault.
        if self.age is None:
            return "INACTIVE (nothing written yet)"
        # The number is the run's OWN elapsed time.
        #
        # It used to be the age of the last write, which reads as the run's
        # age and is not: a healthy run mid-turn showed `ACTIVE 1s` however
        # long it had been going, and the only real elapsed figure sat at the
        # far end of the line as `wall`. Silence is still worth knowing, so it
        # is named as silence, and only when there is some.
        if self.active:
            return f"ACTIVE {human_hms(self.wall)}"
        # A finished run is not silent, it is over, and saying "silent 14m"
        # invites waiting for it to speak again.
        if self.finished:
            return f"DONE {human_hms(self.wall)}"
        return (f"INACTIVE {human_hms(self.wall)} "
                f"(silent {human(self.age)})")


# --------------------------------------------------------------------------
# the panels: agent, client, task
# --------------------------------------------------------------------------
#
# These are the three expensive questions, and each is off by default because
# each costs something the per-task rows do not:
#
#   agent    walks every transcript in the run — tens of thousands of json
#            lines on lustre — to count what the agents are actually DOING.
#            A task is not the unit of work: a run that finishes nothing can
#            still be working hard, and only the action rate says which.
#   client   asks every backend behind the gateway for its own counters. This
#            is a network round trip per GPU, and it answers the one question
#            the local files cannot: is the FLEET busy, or is the run too
#            small to fill it.
#   task     free — it is the rows already on screen, aggregated.
#
# The first two run on a background thread on a slow clock. Computed inline
# they would freeze the display for as long as the walk takes, which on a live
# 60-task run is seconds, and a status tool that stops repainting is
# indistinguishable from the hang it exists to diagnose.

#: How often the background panels recompute. Far slower than the frame rate:
#: neither answer changes meaningfully in two seconds, and both cost real work.
PANEL_REFRESH_S = float(os.environ.get("PHRONIX_TOP_PANEL_REFRESH", "20"))

CLUSTER_JSON = Path(os.environ.get(
    "PHRONIX_CLUSTER",
    "/usr/workspace/haridev/phronix/%s/cluster.json"
    % os.environ.get("PHRONIX_FLEET", "tuolumne-llm")))


def agent_stats(root: Path):
    """What the agents are doing, per second, from their own transcripts.

    Counted by assistant MESSAGE ID rather than by event: a streamed message
    arrives as several events carrying the same id, and counting events
    reported several times the turns that happened.
    """
    import collections

    tools = collections.Counter()
    calls = 0
    turns = set()
    agent_seconds = 0.0
    files = 0
    for transcript in root.glob("*/tasks/*/attempt-*/*.jsonl"):
        files += 1
        stamps = []
        try:
            text = transcript.read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            when = event.get("timestamp")
            if isinstance(when, str):
                try:
                    stamps.append(datetime.fromisoformat(
                        when.replace("Z", "+00:00")).timestamp())
                except ValueError:
                    pass
            message = event.get("message") or {}
            if message.get("role") == "assistant":
                turns.add((transcript.parent, message.get("id") or id(event)))
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls += 1
                    name = block.get("name") or "?"
                    # The phronix tools as one group: fifteen separate rows
                    # would crowd out Bash and Read, which is the comparison.
                    tools["mcp__phronix__*" if name.startswith("mcp__phronix__")
                          else name] += 1
        # From the transcript's own timestamps. On lustre st_ctime moves on
        # every append, so mtime - ctime is ~0 and per-agent time vanishes.
        if len(stamps) > 1:
            agent_seconds += max(stamps) - min(stamps)
    return {"calls": calls, "turns": len(turns), "agent_seconds": agent_seconds,
            "tools": tools.most_common(8), "transcripts": files}


def client_stats(manifest):
    """The endpoint's own counters, read rather than probed.

    A synthetic request measures the probe and adds to the queue it is trying
    to describe. llama.cpp already publishes what it has done, so this is one
    cheap GET per backend and reports the RUN's traffic instead of its own.
    """
    import concurrent.futures
    import urllib.request

    base = str(manifest.get("base_url") or "")
    # Claude Code against Anthropic reaches it directly and the manifest still
    # carries a gateway URL, so these numbers would describe an endpoint this
    # run never used.
    if not base or manifest.get("provider") == "anthropic":
        return {"skipped": "this run talks to Anthropic, not a local endpoint"}
    try:
        config = json.loads(CLUSTER_JSON.read_text())
    except (OSError, ValueError):
        return {"skipped": f"no cluster config at {CLUSTER_JSON}"}
    gateway = config.get("gateway") or {}
    if f"{gateway.get('host')}:{gateway.get('port')}" not in base:
        return {"skipped": f"{base} is not the cluster in {CLUSTER_JSON.name}"}
    fleet = [(s.get("host"), s.get("port")) for s in config.get("servers") or []
             if s.get("host") and s.get("port")]
    if not fleet:
        return {"skipped": "the cluster config lists no servers"}

    def one(where):
        host, port = where
        try:
            with urllib.request.urlopen(
                    f"http://{host}:{port}/metrics", timeout=6) as response:
                text = response.read().decode("utf-8", "replace")
        except Exception:
            return None
        got = {}
        for line in text.splitlines():
            if line.startswith("llamacpp:"):
                name, _, value = line.partition(" ")
                try:
                    got[name] = float(value)
                except ValueError:
                    pass
        return got

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        seen = [g for g in pool.map(one, fleet) if g is not None]
    if not seen:
        return {"skipped": f"none of the {len(fleet)} backend(s) answered"}

    def total(name):
        return sum(g.get(f"llamacpp:{name}", 0) for g in seen)

    busy = sum(1 for g in seen
               if g.get("llamacpp:requests_processing", 0) > 0)
    return {"fleet": len(fleet), "reachable": len(seen), "busy": busy,
            "idle": len(seen) - busy,
            "inflight": total("requests_processing"),
            "deferred": total("requests_deferred"),
            "generated": total("tokens_predicted_total"),
            "prompt": total("prompt_tokens_total"),
            "rate": total("predicted_tokens_seconds"),
            "prompt_rate": total("prompt_tokens_seconds")}


def node_stats(manifest):
    """Memory, load and process count on the nodes holding the containers.

    This exists because a runner can die with no traceback and an empty log,
    and from the run's own files that is indistinguishable from somebody
    stopping it. Memory pressure is the difference, and it is only visible on
    the node: each task is a container, each container runs an agent that
    spawns sub-agents, and the product — not the task count — is what a node
    actually has to hold.

    One ssh per node, in parallel, with a short timeout. `free` and `uptime`
    are cheap enough that this can run on the panel clock.
    """
    import concurrent.futures

    listed = str(manifest.get("nodes") or manifest.get("node") or "")
    nodes = [n for n in listed.replace(",", " ").split() if n]
    if not nodes:
        return {"skipped": "the manifest names no nodes"}

    # One shell per node rather than four: each ssh is a second of handshake,
    # and asking four questions down one connection costs the same as one.
    # `podman ps` gets its own timeout and comes LAST.
    #
    # Measured: `free` answers in 0.4s and `podman ps` takes over six seconds
    # on a node under load — it walks the container store on lustre. Ungated it
    # blew the whole ssh budget and every node reported "did not answer", so
    # the panel showed nothing while the cheap numbers were sitting right
    # there. A container count that times out prints as `?`; memory does not.
    probe = ("free -m | awk 'NR==2{print $2, $3, $7}'; "
             "uptime | sed 's/.*load average: //'; "
             "(pgrep -c -f 'claude|opencode' 2>/dev/null || echo 0); "
             "(ps -e --no-header | wc -l); "
             "(timeout 6 podman ps -q 2>/dev/null | wc -l || echo -1)")

    def one(host):
        try:
            out = subprocess.run(
                ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                 host, probe],
                capture_output=True, text=True, timeout=40).stdout.split("\n")
        except (subprocess.SubprocessError, OSError):
            return host, None
        try:
            total, used, available = (int(x) for x in out[0].split())
            load = out[1].split(",")[0].strip()
        except (IndexError, ValueError):
            return host, None
        # Everything after memory is optional: a node that answers about its
        # memory and not about its containers is still worth showing, because
        # memory is the question this panel exists for.
        def maybe(index):
            try:
                return int(out[index])
            except (IndexError, ValueError):
                return -1
        return host, {"total": total, "used": used, "available": available,
                      "load": float(load), "agents": maybe(2),
                      "procs": maybe(3), "containers": maybe(4)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        seen = dict(pool.map(one, nodes))
    if not any(seen.values()):
        return {"skipped": f"none of {len(nodes)} node(s) answered"}
    return {"nodes": seen}


class Panels:
    """The background worker behind the toggles.

    One thread, one lock, and results that may be stale — which is stated on
    screen rather than hidden, because a number whose age is unknown is worse
    than one that says it is 18 seconds old.
    """

    def __init__(self, run_path: Path):
        import threading

        self.run_path = run_path
        self.wanted = set()
        self.data = {}
        self.at = {}
        self.busy = set()
        self.lock = threading.Lock()
        self.threading = threading

    def want(self, name, manifest):
        """Ask for a panel; recompute in the background if it has gone stale."""
        self.wanted.add(name)
        with self.lock:
            fresh = time.time() - self.at.get(name, 0) < PANEL_REFRESH_S
            if fresh or name in self.busy:
                return
            self.busy.add(name)
        worker = self.threading.Thread(target=self._compute, args=(name, manifest),
                                       daemon=True)
        worker.start()

    def _compute(self, name, manifest):
        try:
            if name == "agent":
                got = agent_stats(self.run_path)
            elif name == "client":
                got = client_stats(manifest)
            elif name == "node":
                got = node_stats(manifest)
            else:
                got = {}
        except Exception as exc:                      # never kill the display
            got = {"skipped": f"{type(exc).__name__}: {exc}"}
        with self.lock:
            self.data[name] = got
            self.at[name] = time.time()
            self.busy.discard(name)

    def get(self, name):
        with self.lock:
            return self.data.get(name), self.at.get(name, 0), name in self.busy


# --------------------------------------------------------------------------
# the screen
# --------------------------------------------------------------------------

SORTS = ("state", "time", "name", "cost")
FILTERS = ("all", "running", "failed", "passed")


class Top:
    def __init__(self, screen, run_path: Path, pinned: bool = False):
        self.screen = screen
        self.run = Run(run_path)
        #: True when the reader NAMED a run, which turns following off.
        self.pinned = pinned
        self._followed = 0.0
        self.open_arms = {arm.key for arm in self.run.arms}   # groups open
        self.open_tasks = set()
        #: Group keys already offered their default open/closed state.
        #
        # `open_tasks` records what the READER has opened, so a group that
        # should start open cannot simply be seeded once at startup: arms and
        # their groups appear as the run goes on, and a group created later
        # would come up closed. Recording which keys have been defaulted lets a
        # new group open itself the first time it is drawn and stay under the
        # reader's control from then on — closing it must not spring back open
        # on the next refresh.
        self._defaulted = set()
        self.cursor = 0
        self.top = 0
        self.sort = 0
        self.filter = 0
        self.selected_key = None
        self.last = 0.0
        self.message = ""
        #: Which of the three stat panels are showing. All off at start: two of
        #: them cost real work, and the reason to open one is a question about
        #: the run that the task rows have already raised.
        self.panels = {name for name in
                       os.environ.get("PHRONIX_TOP_PANELS", "").split(",") if name}
        self.workers = Panels(self.run.path)
        #: Set whenever the layout changes shape, so the next frame is a full
        #: repaint rather than a diff against a screen curses has stale beliefs
        #: about. Starts true: the first frame has nothing to diff against.
        self.repaint = True
        #: The height of the pinned block last frame. A panel arriving from the
        #: background thread changes it without any key being pressed, and that
        #: frame needs the same hard repaint a keypress would have earned.
        self.head_height = 0

    # -- layout ----------------------------------------------------------
    def rows(self, width):
        """The whole display as a flat list of (kind, key, colour, text).

        Flat because the cursor moves through it linearly; the hierarchy lives
        in the indentation and in which rows are emitted at all.
        """
        out = []
        run, now = self.run, self.run.now
        tasks = run.tasks
        passed = sum(1 for t in tasks if t.state == "pass")
        failed = sum(1 for t in tasks if t.state == "fail")
        running = sum(1 for t in tasks if t.state == "run")
        cost = sum(t.cost for t in tasks)
        tokens = sum(t.tokens for t in tasks)

        # The FULL path, not just the name.
        #
        # The run is auto-picked, so the first question any reader has is
        # "which one am I looking at" — and the answer has to be something they
        # can paste into a `tail -f` or a `status.sh`, not a name they then
        # have to go and resolve.
        # The gateway HOST, not the provider key, when there is one.
        #
        # `provider` is a protocol identifier the arms pass to opencode as
        # `--model <provider>/<alias>`; it reads "tuolumne" for every local
        # fleet including corona's, so as a label it names the wrong machine.
        # The base_url is the fleet that is actually answering.
        base = run.manifest.get("base_url") or ""
        provider = str(run.manifest.get("provider", "") or "")
        where = provider or "?"
        # base_url is only where the traffic went for a LOCAL fleet.
        #
        # With provider `anthropic` the arms deliberately leave the endpoint
        # alone so Claude Code uses the account's own credentials, and the
        # base_url in the manifest is an unused default — it read
        # "livai-api.llnl.gov" for a run going to Anthropic on a subscription.
        # Naming the wrong endpoint is worse than naming none.
        if base and provider.lower() not in ("anthropic", "claude", ""):
            host = base.split("//", 1)[-1].split("/", 1)[0]
            where = host.split(":", 1)[0] or where
        head = (f"{run.path}  {run.state}   "
                f"{run.manifest.get('model', '?')} "
                f"({where})   "
                f"{'fresh' if run.manifest.get('fresh') else 'reuse'}   "
                f"tries<={run.manifest.get('max_tries', '?')}")
        # Green when the run is writing, red when it is not. This is the first
        # thing anybody looks at and it is the one line that says whether what
        # follows is a live picture or an autopsy.
        out.append(("head", None, "alive" if run.active else "dead", head))

        done = passed + failed
        rate = f"{100.0 * passed / done:.0f}%" if done else "  -"
        bar = self.bar(passed, failed, running, max(20, width - 62))
        out.append(("head", None, "total",
                    f" TOTAL {len(tasks):>3} task(s)   "
                    f"{passed:>3} pass  {failed:>3} fail  {running:>3} run   "
                    f"{rate:>4} of finished   {short(tokens):>7} tok  "
                    f"{money(cost) or '-':>8}   {bar}"))
        for line in self.panel_rows(width):
            out.append(line)
        out.append(("head", None, "dim", "-" * (width - 1)))

        for arm in run.arms:
            open_ = arm.key in self.open_arms
            done_arm = arm.passed + arm.failed
            rate = f"{100.0 * arm.passed / done_arm:.0f}%" if done_arm else "-"
            out.append(("arm", arm.key, "arm",
                        f"{'v' if open_ else '>'} {arm.name:<20} "
                        f"{arm.passed:>3} pass {arm.failed:>3} fail "
                        f"{arm.running:>3} run   {rate:>4}   "
                        f"{short(arm.tokens):>7} tok  {money(arm.cost) or '-':>8}   "
                        f"avg {human(arm.finished_time):>7}/task"
                        + (f"   {len(arm.queued)} queued" if arm.queued else "")))
            if not open_:
                continue
            # Four groups, one per stage of a task's life.
            #
            # Every row on this screen used to be a task, so a run packing six
            # tasks an arm showed twelve task rows plus whatever had finished,
            # and the live ones were pushed off the bottom by the settled ones.
            # Grouping puts the arm's shape on one line each — how many are
            # moving, how many landed, how many are left — and only `running`
            # is expanded, because it is the only group whose contents change.
            buckets = {"run": [], "pass": [], "fail": []}
            for task in self.ordered(arm.tasks):
                # Anything not settled is live, whatever stage it reports.
                buckets[task.state if task.state in ("pass", "fail")
                        else "run"].append(task)

            for state, label, default_open in (("run", "running", True),
                                               ("pass", "passed", False),
                                               ("fail", "failed", False)):
                members = buckets[state]
                if not members:
                    continue
                group = f"{arm.key}/{state}"
                shown = self.group_open(group, default_open)
                out.append(("task", group, state,
                            f"  {'v' if shown else '>'} {label} "
                            f"({len(members)})"))
                if not shown:
                    continue
                # Running is split by PHASE; settled groups are a flat list.
                #
                # "20 running" says nothing about whether the arm is thinking or
                # testing. Twelve in research and one in evaluate is a different
                # picture from the reverse, and at high parallelism a pile in
                # "not started" is the queue made visible — which is the number
                # that explains a slow run.
                if state == "run":
                    by_phase = {name: [] for name, _ in PHASES}
                    for task in members:
                        by_phase[phase_of(task)].append(task)
                    for name, _ in PHASES:
                        here = by_phase[name]
                        if not here:
                            continue
                        # Each phase is a group of its own, on the same toggle
                        # as everything else — the key carries a "/" so
                        # `toggle` files it with the tasks rather than the arms.
                        #
                        # Open by default, except the queue. "not started" is
                        # every task waiting for a slot, and at high
                        # parallelism it is the longest list on the screen while
                        # being the one with least to say per row: the COUNT is
                        # the finding, and the names are there when wanted.
                        key = f"{arm.key}/run/{name.replace(' ', '-')}"
                        shown = self.group_open(key, name != "not started")
                        out.append(("task", key, "dim",
                                    f"    {'v' if shown else '>'} {name} "
                                    f"({len(here)})"))
                        if not shown:
                            continue
                        for task in here:
                            out.append(("task", task.key, task.state,
                                        self.task_row(task, width)))
                            if task.key in self.open_tasks:
                                for colour, text in task.detail():
                                    out.append(("detail", None, colour,
                                                "        " + text))
                    continue

                for task in members:
                    out.append(("task", task.key, task.state,
                                self.task_row(task, width)))
                    if task.key in self.open_tasks:
                        for colour, text in task.detail():
                            out.append(("detail", None, colour,
                                        "        " + text))
            # What has not started yet, folded into ONE collapsible row.
            #
            # The screen's vertical space belongs to what is moving: a run
            # packing six tasks an arm would spend most of the list on rows that
            # say only "queued", pushing the running ones off the bottom. So the
            # queued set gets a single group row, closed by default, and opens
            # on the same key as everything else when the reader wants the names.
            #
            # The key carries a "/" so `toggle` files it with the tasks rather
            # than the arms, which is what makes it start closed and stay
            # independent of whether its arm is expanded.
            if arm.queued:
                group = f"{arm.key}/queued"
                shown = group in self.open_tasks
                out.append(("task", group, "dim",
                            f"  {'v' if shown else '>'} queued "
                            f"({len(arm.queued)})"))
                if shown:
                    for name in arm.queued:
                        out.append(("detail", None, "dim", "        " + name))
        return out

    def panel_rows(self, width):
        """The optional stat panels, in a fixed order under the totals.

        Each is a heading plus a few wide lines rather than a table: these are
        run-wide quantities read across, not columns compared down.
        """
        out = []
        run = self.run

        def title(text, at, busy):
            age = f"  ({human(time.time() - at)} old)" if at else ""
            if busy and not at:
                age = "  (reading...)"
            elif busy:
                age += " refreshing"
            out.append(("head", None, "arm", f" {text}{age}"))

        if "task" in self.panels:
            tasks = run.tasks
            done = [t for t in tasks if t.done]
            steps = sum(t.steps for t in done)
            retried = sum(1 for t in done if t.tries > 1)
            slowest = max(tasks, key=lambda t: t.elapsed, default=None)
            title("TASKS", run.now, False)
            spent = sum(t.elapsed for t in done)
            out.append(("head", None, "dim",
                        f"   {len(done)} finished of {len(tasks)}   "
                        f"{human(spent / len(done)) if done else '-'} each on average   "
                        f"{steps / len(done):.0f} steps each   " if done else
                        f"   nothing finished yet of {len(tasks)}   "))
            out.append(("head", None, "dim",
                        f"   {retried} needed a retry   "
                        f"{short(sum(t.tokens for t in done))} tok   "
                        f"{money(sum(t.cost for t in done)) or '$0'} so far   "
                        + (f"slowest {slowest.name} {human(slowest.elapsed)}"
                           if slowest else "")))
            for arm in run.arms:
                finished = [t for t in arm.tasks if t.done]
                out.append(("head", None, "dim",
                            f"   {arm.name:<18} "
                            f"{human(arm.finished_time):>7}/task   "
                            f"{(sum(t.steps for t in finished) / len(finished)) if finished else 0:.0f} steps   "
                            f"{short(arm.tokens):>7} tok   "
                            f"{money(arm.cost) or '-':>8}   "
                            f"{sum(1 for t in arm.tasks if t.tries > 1)} retried"))

        if "agent" in self.panels:
            self.workers.want("agent", run.manifest)
            data, at, busy = self.workers.get("agent")
            title("AGENTS", at, busy)
            if not data:
                out.append(("head", None, "dim", "   reading the transcripts..."))
            elif data.get("skipped"):
                out.append(("head", None, "dim", f"   {data['skipped']}"))
            else:
                wall = max(1.0, run.wall)
                actions = data["calls"] + data["turns"]
                seconds = data["agent_seconds"]
                out.append(("head", None, "dim",
                            f"   {actions / wall:.2f} agent action/s   "
                            f"({data['calls']} tool call(s) at {data['calls'] / wall:.2f}/s, "
                            f"{data['turns']} model turn(s) at {data['turns'] / wall:.2f}/s)"
                            f"   {data['transcripts']} transcript(s)"))
                if seconds > 0:
                    # The two halves of the run-wide rate. A slow run is either
                    # a slow agent (a model or harness problem) or too few
                    # agents (a concurrency one), and the fix differs.
                    out.append(("head", None, "dim",
                                f"   {actions / seconds:.2f} action/s PER AGENT  x  "
                                f"{seconds / wall:.1f} agent(s) in flight on average  =  "
                                f"{actions / wall:.2f}/s   "
                                f"one action every {seconds / max(actions, 1):.1f}s per agent"))
                if data["tools"]:
                    out.append(("head", None, "dim", "   what they do: " + "   ".join(
                        f"{name} {n}" for name, n in data["tools"])[:width - 20]))

        if "node" in self.panels:
            self.workers.want("node", run.manifest)
            data, at, busy = self.workers.get("node")
            title("NODES", at, busy)
            if not data:
                out.append(("head", None, "dim", "   asking the nodes..."))
            elif data.get("skipped"):
                out.append(("head", None, "dim", f"   {data['skipped']}"))
            else:
                out.append(("head", None, "dim",
                            f"   {'node':<14} {'memory used':>18} {'free':>8}"
                            f" {'load':>7} {'containers':>11} {'agents':>7}"
                            f" {'procs':>7}"))
                for host, got in data["nodes"].items():
                    if not got:
                        out.append(("head", None, "dim",
                                    f"   {host:<14}  did not answer"))
                        continue
                    share = 100.0 * got["used"] / max(1, got["total"])
                    # The mark is on FREE memory, not on the percentage used:
                    # a node with 8% free is minutes from the OOM killer
                    # whatever fraction that is of what it started with.
                    tight = ("  ** low memory" if got["available"] < 0.1 * got["total"]
                             else "")
                    out.append(("head", None,
                                "fail" if tight else "dim",
                                f"   {host:<14} "
                                f"{got['used'] / 1024:>8.0f}/{got['total'] / 1024:<4.0f} GB"
                                f" {share:>4.0f}%"
                                f" {got['available'] / 1024:>7.0f}G"
                                f" {got['load']:>7.1f}"
                                f" {(got['containers'] if got['containers'] >= 0 else '?'):>11}"
                                f" {(got['agents'] if got['agents'] >= 0 else '?'):>7}"
                                f" {(got['procs'] if got['procs'] >= 0 else '?'):>7}{tight}"))

        if "client" in self.panels:
            self.workers.want("client", run.manifest)
            data, at, busy = self.workers.get("client")
            title("CLIENTS", at, busy)
            if not data:
                out.append(("head", None, "dim", "   asking the fleet..."))
            elif data.get("skipped"):
                out.append(("head", None, "dim", f"   {data['skipped']}"))
            else:
                # The headline is how much of the fleet the run is USING. A
                # mostly idle fleet is the most actionable thing here: it means
                # the run has too few concurrent agents to fill what is served.
                warn = ("   ** most of the fleet is idle — not enough concurrent "
                        "agents to fill it" if data["idle"] > data["reachable"] / 2
                        else "")
                out.append(("head", None, "dim",
                            f"   {data['reachable']}/{data['fleet']} backend(s) reachable   "
                            f"{data['busy']} busy / {data['idle']} idle{warn}"))
                out.append(("head", None, "dim",
                            f"   {data['inflight']:.0f} request(s) in flight, "
                            f"{data['deferred']:.0f} queued   "
                            f"generate {data['rate']:,.0f} tok/s   "
                            f"prompt {data['prompt_rate']:,.0f} tok/s"))
                out.append(("head", None, "dim",
                            f"   {data['generated']:,.0f} generated + "
                            f"{data['prompt']:,.0f} prompt token(s) across the fleet "
                            f"since the servers booted"))
        return out

    def ordered(self, tasks):
        """Rows in the order the current sort asks for, filtered."""
        want = FILTERS[self.filter]
        if want != "all":
            tasks = [t for t in tasks
                     if t.state == {"running": "run", "failed": "fail",
                                    "passed": "pass"}[want]]
        key = SORTS[self.sort]
        if key == "state":
            # Running first, then failures: what is still moving and what went
            # wrong are the two reasons anybody opens this.
            order = {"run": 0, "fail": 1, "pass": 2}
            return sorted(tasks, key=lambda t: (order[t.state], -t.elapsed))
        if key == "time":
            return sorted(tasks, key=lambda t: -t.elapsed)
        if key == "cost":
            return sorted(tasks, key=lambda t: -t.cost)
        return sorted(tasks, key=lambda t: t.name)

    def task_row(self, task, width):
        """One task as one line, spending whatever width the terminal has.

        The fixed columns are sized first and the stage/message pair takes the
        rest, because that pair is the only part that distinguishes one live
        task from another and it is what got truncated in the old display.
        """
        glyph = {"pass": "+", "fail": "x", "run": "."}[task.state]
        mark = ""
        if task.state == "run" and task.idle > QUIET_S:
            mark = " ** quiet"
        left = (f"  {'v' if task.key in self.open_tasks else ' '}{glyph} "
                f"{task.name[:34]:<34} "
                f"{('try' + str(task.tries)) if task.tries > 1 else '':<5}")
        # A running task has no token count yet — they are written with the
        # result — and printing 0 there says "this agent has done nothing",
        # which is the opposite of what is true.
        counted = short(task.tokens) if task.done else "-"
        right = (f" {counted:>7} {human(task.elapsed):>7}"
                 f" {money(task.cost):>7}{mark}")
        room = max(10, width - len(left) - len(right) - 1)
        if task.done:
            middle = ("resolved" if task.state == "pass"
                      else str((task.result or {}).get("error") or "not resolved"))
            # The skills go after the outcome, and only in the room left over:
            # the outcome must never be pushed off the line to make space for
            # them, and a task that wrote nothing shows exactly what it did
            # before.
            skills = task.skills
            if skills and len(middle) + 2 < room:
                middle = f"{middle}  {skills}"
            middle = f"{middle[:room]:<{room}}"
        else:
            stage = task.stage[:28]
            gap = max(4, room - len(stage) - 2)
            middle = f"{stage:<28.28} {task.message[:gap]:<{gap}}"[:room]
            middle = f"{middle:<{room}}"
        return left + middle + right

    @staticmethod
    def bar(passed, failed, running, width):
        """Progress as one bar: what passed, what failed, what is still out."""
        total = max(1, passed + failed + running)
        cells = max(10, width)
        p = int(cells * passed / total)
        f = int(cells * failed / total)
        r = cells - p - f
        return "[" + "#" * p + "!" * f + "." * r + "]"

    # -- drawing ---------------------------------------------------------
    def draw(self):
        screen = self.screen
        height, width = screen.getmaxyx()
        rows = self.rows(width)

        # The cursor lives on a KEY, not an index: a refresh reorders rows
        # (a task finishes, the sort moves it) and an index would jump the
        # selection to an unrelated task under the reader's hands.
        selectable = [i for i, row in enumerate(rows) if row[0] in ("arm", "task")]
        if self.selected_key is not None:
            for i in selectable:
                if rows[i][1] == self.selected_key:
                    self.cursor = i
                    break
            else:
                self.cursor = selectable[0] if selectable else 0
        elif selectable:
            self.cursor = selectable[0]
        if selectable:
            self.selected_key = rows[self.cursor][1]

        # Head and body are two separate lists, not one list with an index
        # into it.
        #
        # They were one list, and the pinned block was clamped so a panel could
        # not eat the screen — but the clamp only moved where the body STARTED,
        # so with the panels open the head rows past the clamp were drawn once
        # at the top and then again as the first rows of the scrolling body.
        # Two copies of the same lines, interleaved with task rows: the display
        # read as garbage and stopped tracking the run.
        split = next((i for i, row in enumerate(rows) if row[0] != "head"),
                     len(rows))
        head, body = rows[:split], rows[split:]

        # A panel must never eat the screen: the task rows are the point. What
        # does not fit is DROPPED with a line saying so — never spilled into
        # the body, and never silently, because a panel showing three of its
        # five lines with no mark is a panel that is quietly lying.
        room = max(3, height - 8)
        if len(head) > room:
            head = head[:room - 1] + [
                ("head", None, "dim",
                 f"   ... {len(head) - room + 1} more panel line(s) — close a "
                 f"panel or use a taller window")]

        body_top = len(head)
        # Panel data lands from a background thread between keypresses, so the
        # block can change height with no input at all.
        if body_top != self.head_height:
            self.repaint = True
            self.head_height = body_top
        body_height = max(1, height - body_top - 1)
        # The cursor indexes `rows`; the body starts `split` rows in.
        cursor_in_body = self.cursor - split
        if cursor_in_body < self.top:
            self.top = max(0, cursor_in_body)
        if cursor_in_body >= self.top + body_height:
            self.top = cursor_in_body - body_height + 1
        self.top = max(0, min(self.top, max(0, len(body) - body_height)))

        # A layout change gets a hard repaint, not a diff.
        #
        # `erase()` + `refresh()` updates only the cells curses believes are
        # stale, and after the pinned block changes height its belief and the
        # terminal disagree — leaving fragments of the previous layout behind.
        if self.repaint:
            screen.clear()
            self.repaint = False
        # No `erase()` on an ordinary frame — that is what made it blink.
        #
        # `erase()` blanks every cell, and the redraw then fills them back in;
        # on a remote terminal the empty state is visible, so a screen that
        # changes one number flashes whole. `put` already pads each row to the
        # full width, so writing over the old frame leaves nothing behind, and
        # the only rows needing explicit blanking are the ones the new frame is
        # too short to reach. A layout change still gets the hard `clear()`
        # above.
        for i, (kind, key, colour, text) in enumerate(head):
            self.put(i, text, colour, width)
        drawn = 0
        for offset, (kind, key, colour, text) in enumerate(
                body[self.top:self.top + body_height]):
            chosen = (self.top + offset) == cursor_in_body
            self.put(body_top + offset, text, colour, width, chosen)
            drawn = offset + 1
        for row in range(body_top + drawn, height - 1):
            self.put(row, "", "dim", width)

        # The panel toggles are named with their state, so the footer says what
        # is ON as well as what the key does.
        marks = " ".join(f"[{k}]{name}{'*' if name in self.panels else ''}"
                         for k, name in (("1", "agent"), ("2", "client"),
                                         ("3", "task"), ("4", "node")))
        footer = (f" {SORTS[self.sort]}-sorted  filter:{FILTERS[self.filter]}"
                  f"   {marks}   [enter] open  [s] sort  [f] filter  [a] all"
                  f"  [c] collapse  [l] log  [q] quit")
        if self.message:
            footer = f" {self.message}"
        self.put(height - 1, footer[:width - 1], "footer", width)
        screen.refresh()

    def put(self, row, text, colour, width, selected=False):
        attr = COLOURS.get(colour, 0)
        if selected:
            attr = curses.A_REVERSE | curses.A_BOLD
        try:
            self.screen.addnstr(row, 0, text.ljust(width - 1), width - 1, attr)
        except curses.error:
            pass                            # the last cell of the last line

    # -- input -----------------------------------------------------------
    def move(self, delta):
        rows = self.rows(self.screen.getmaxyx()[1])
        selectable = [i for i, row in enumerate(rows) if row[0] in ("arm", "task")]
        if not selectable:
            return
        here = min(range(len(selectable)),
                   key=lambda i: abs(selectable[i] - self.cursor))
        here = max(0, min(len(selectable) - 1, here + delta))
        self.cursor = selectable[here]
        self.selected_key = rows[self.cursor][1]

    def group_open(self, key, default_open=False):
        """Whether a group is expanded, opening it once if it starts open.

        The default is applied the FIRST time the group is drawn, not at
        startup: arms and their groups appear as a run goes on, and a group
        created later would otherwise come up closed against its own default.
        After that the reader owns it — `_defaulted` is what stops a group the
        reader just closed from springing open again on the next refresh.
        """
        if key not in self._defaulted:
            self._defaulted.add(key)
            if default_open:
                self.open_tasks.add(key)
        return key in self.open_tasks

    def toggle(self, want=None):
        key = self.selected_key
        if key is None:
            return
        target = self.open_arms if "/" not in key else self.open_tasks
        if want is False or (want is None and key in target):
            target.discard(key)
        else:
            target.add(key)
        # Expanding or collapsing changes how many rows the body has, and a
        # diffing refresh leaves the tail of the previous layout on screen —
        # the same reason the pinned block forces one. Without this, opening a
        # group redrew the group's own line and left every line below it stale.
        self.repaint = True

    def open_log(self):
        """Hand the selected task's trace to a pager, then come back.

        The row can only ever show a screenful; when that is not enough the
        answer is the file itself, and making the reader leave and find the
        path by hand is the thing this display exists to avoid.
        """
        key = self.selected_key
        if not key or "/" not in key:
            return
        arm, _, task = key.partition("/")
        path = self.run.path / arm / "tasks" / task / "trace.log"
        if not path.is_file():
            self.message = f"no trace yet for {task}"
            return
        curses.endwin()
        subprocess.call([os.environ.get("PAGER", "less"), "+G", str(path)])
        self.screen.clear()
        curses.doupdate()

    #: How often to look for a run that started after this one, in seconds.
    #:
    #: Not every refresh: this stats the trace of a dozen run directories, and
    #: the question it answers changes on the scale of whole runs.
    FOLLOW_EVERY_S = 20

    def follow_newest(self):
        """Move to a run that started after the one on screen.

        `top.sh` with no argument means "the current run", and it resolved that
        once at startup — so killing a run and starting the next left the
        screen pinned to the dead one, showing a finished run's final frame
        while the new one was minutes in. Named a run explicitly and this does
        nothing, because then the argument is the answer.
        """
        if getattr(self, "pinned", False):
            return
        now = time.time()
        if now - getattr(self, "_followed", 0.0) < self.FOLLOW_EVERY_S:
            return
        self._followed = now
        try:
            newest = newest_run()
        except OSError:
            return
        if newest is None or newest.resolve() == Path(self.run.path).resolve():
            return
        self.run = Run(newest)
        # The open/selected state belonged to the OLD run's rows and none of
        # its keys exist here; carrying it over selects nothing and silently
        # collapses everything.
        self.open_arms = {arm.key for arm in self.run.arms}
        self.open_tasks, self._defaulted = set(), set()
        self.selected_key = None
        self.workers = Panels(newest)
        self.repaint = True
        self.message = f"followed the new run: {newest.name}"

    def loop(self):
        while True:
            if time.time() - self.last > REFRESH_S:
                self.follow_newest()
                self.run.reload()
                self.last = time.time()
            # A frame that raises must not reach curses.wrapper: it would end
            # the program by printing a traceback over the display, which is
            # indistinguishable from the garbled screen it caused. Say what
            # broke on the footer and keep painting.
            try:
                self.draw()
            except curses.error:
                self.repaint = True
            except Exception as exc:
                self.message = f"draw failed: {type(exc).__name__}: {exc}"
                self.repaint = True
            try:
                key = self.screen.getch()
            except KeyboardInterrupt:
                return
            if key == -1:
                continue
            self.message = ""
            if key in (ord("q"), 27):
                return
            elif key in (curses.KEY_DOWN, ord("j")):
                self.move(1)
            elif key in (curses.KEY_UP, ord("k")):
                self.move(-1)
            elif key in (curses.KEY_NPAGE, ord(" ")):
                self.move(10)
            elif key == curses.KEY_PPAGE:
                self.move(-10)
            elif key in (curses.KEY_HOME, ord("g")):
                self.move(-10000)
            elif key in (curses.KEY_END, ord("G")):
                self.move(10000)
            elif key in (curses.KEY_RIGHT, ord("\n"), curses.KEY_ENTER, 10, 13):
                self.toggle(True) if key == curses.KEY_RIGHT else self.toggle()
            elif key == curses.KEY_LEFT:
                self.toggle(False)
            elif key == ord("s"):
                self.sort = (self.sort + 1) % len(SORTS)
            elif key == ord("f"):
                self.filter = (self.filter + 1) % len(FILTERS)
            elif key == ord("a"):
                self.open_arms = {arm.key for arm in self.run.arms}
                self.open_tasks = {t.key for t in self.run.tasks}
                # "open all" means all, including each arm's collapsed groups —
                # otherwise they are the one thing on the screen that no key
                # would reach.
                self.open_tasks |= {f"{arm.key}/{group}"
                                    for arm in self.run.arms
                                    for group in ("run", "pass", "fail",
                                                  "queued")}
                self.open_tasks |= {f"{arm.key}/run/{name.replace(' ', '-')}"
                                    for arm in self.run.arms
                                    for name, _ in PHASES}
                self.repaint = True
            elif key == ord("c"):
                self.open_tasks.clear()
                # Collapsing must not let `running` default itself back open on
                # the next draw: "collapse all" means all.
                self._defaulted |= {f"{arm.key}/run" for arm in self.run.arms}
                self._defaulted |= {f"{arm.key}/run/{name.replace(' ', '-')}"
                                    for arm in self.run.arms
                                    for name, _ in PHASES}
                self.repaint = True
            elif key == curses.KEY_RESIZE:
                self.repaint = True
            elif key in (ord("1"), ord("2"), ord("3"), ord("4")):
                name = {ord("1"): "agent", ord("2"): "client",
                        ord("3"): "task", ord("4"): "node"}[key]
                self.repaint = True          # the pinned block changes height
                if name in self.panels:
                    self.panels.discard(name)
                else:
                    self.panels.add(name)
                    # Ask immediately rather than waiting for the panel's own
                    # clock: a toggle that shows nothing for twenty seconds
                    # reads as a key that did not work.
                    if name in ("agent", "client", "node"):
                        self.workers.want(name, self.run.manifest)
                        self.message = f"{name} stats: reading, this can take a moment"
            elif key == ord("l"):
                self.open_log()
            elif key == ord("r"):
                self.last = 0.0
            self.last = min(self.last, time.time())


COLOURS = {}


def start(screen, run_path, pinned=False):
    curses.curs_set(0)
    screen.nodelay(True)
    screen.timeout(int(REFRESH_S * 1000))
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for index, (name, fg) in enumerate((
                ("pass", curses.COLOR_GREEN), ("fail", curses.COLOR_RED),
                ("run", curses.COLOR_CYAN), ("arm", curses.COLOR_YELLOW),
                ("alive", curses.COLOR_GREEN), ("dead", curses.COLOR_RED),
                ("title", curses.COLOR_WHITE), ("total", curses.COLOR_WHITE),
                ("dim", curses.COLOR_BLUE), ("footer", curses.COLOR_BLACK)), 1):
            curses.init_pair(index, fg, -1)
            COLOURS[name] = curses.color_pair(index)
        COLOURS["arm"] |= curses.A_BOLD
        COLOURS["alive"] |= curses.A_BOLD
        COLOURS["dead"] |= curses.A_BOLD
        COLOURS["title"] |= curses.A_BOLD
        COLOURS["total"] |= curses.A_BOLD
        COLOURS["footer"] = curses.A_REVERSE
    Top(screen, run_path, pinned).loop()


def once(run_path: Path, panels=(), width: int = 0):
    """One frame to stdout, for a pipe or a `watch`.

    A curses program in a pipe draws nothing at all, and the first thing
    anybody does with a status tool is redirect it.
    """
    width = width or int(os.environ.get("COLUMNS") or 0) or 160
    top = Top.__new__(Top)
    top.run = Run(run_path)
    top.open_arms = {arm.key for arm in top.run.arms}
    top.open_tasks = set()
    # `Top.__new__` skips `__init__`, so every field the row builder reads has
    # to be set here too — a group's default open state included.
    top._defaulted = set()
    top.sort, top.filter, top.selected_key = 0, 0, None
    top.pinned, top._followed = True, 0.0
    top.panels = set(panels)
    top.workers = Panels(run_path)
    if panels:
        # No event loop here to come back on, so the background work has to be
        # waited for — otherwise the panel prints "reading..." forever and the
        # flag looks broken.
        for name in ("agent", "client", "node"):
            if name in top.panels:
                top.workers.want(name, top.run.manifest)
        deadline = time.time() + 120
        while time.time() < deadline and top.workers.busy:
            time.sleep(0.3)
    for _, _, _, text in top.rows(width):
        print(text.rstrip())


def newest_run(candidates: int = 12):
    """The run that WROTE most recently, not the newest directory.

    A run directory's own mtime stops moving early — the arm directories are
    created once and everything after that is written inside them — so ranking
    by directory age can open a run that has been finished for hours while a
    live one sits below it in the list. What is actually wanted is "the run
    whose trace is newest", so that is what this measures.

    Bounded to the most recent handful of directories: the runs directory
    accumulates, and stat-ing every trace in every run of the last month to
    answer "which one is live" is a walk nobody asked for.
    """
    dirs = sorted((p for p in RUNS.glob("*/") if p.is_dir()),
                  key=lambda p: p.stat().st_mtime, reverse=True)[:candidates]
    if not dirs:
        return None

    def touched(run: Path) -> float:
        stamps = [run.stat().st_mtime]
        for pattern in ("*/trace.log", "*/results.jsonl", "manifest.json",
                        "*/tasks/*/trace.log"):
            for path in run.glob(pattern):
                try:
                    stamps.append(path.stat().st_mtime)
                except OSError:
                    pass
        return max(stamps)

    return max(dirs, key=touched)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    flags = {a for a in argv[1:] if a.startswith("-")}
    if args:
        want = Path(args[0])
        run = want if want.is_dir() else RUNS / args[0]
    else:
        run = newest_run()
        if run is None:
            print(f"no runs under {RUNS}", file=sys.stderr)
            return 1
    if not run.is_dir():
        print(f"no such run: {run}", file=sys.stderr)
        return 1
    panels = {name for name in ("agent", "client", "task", "node")
              if f"--{name}" in flags}
    if "--all-stats" in flags:
        panels = {"agent", "client", "task", "node"}
    if "--once" in flags or not sys.stdout.isatty():
        once(run, panels)
        return 0
    if panels:
        os.environ["PHRONIX_TOP_PANELS"] = ",".join(sorted(panels))
    curses.wrapper(start, run, bool(args))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
