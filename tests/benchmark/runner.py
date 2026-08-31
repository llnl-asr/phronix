"""The benchmark loop: arms × tasks × tries, with the ledger that makes reuse real.

Structure, and why:

* **Arms run in an outer loop, tasks inner, in fixed order.** The learning arm's
  task N benefits from tasks 1..N-1; that only means anything if every arm saw
  the same sequence. Task order comes from a pinned file and is never shuffled.
* **Each try is a fresh container.** A retry that inherits the last attempt's
  filesystem measures recovery, not an independent solve.
* **A creation ledger maps skill -> the task that wrote it.** This is what makes
  "reused" checkable: a skill retrieved during task N counts as reuse only if the
  ledger says an *earlier* task created it. Without the ledger, a skill written
  and read back within the same task would inflate the headline metric, and the
  benchmark would report learning that never happened.
* **Results are appended after every task**, so a run killed at task 22 keeps 21
  tasks of data rather than none.
"""
from __future__ import annotations

import itertools
import json
import os
import re
import shlex
import shutil
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .arms import ARM_ORDER, Arm, AttemptOutcome, build as build_arm
from .isolation import (
    DEFAULT_IMAGE_TEMPLATE, ContainerSession, IsolationError,
                        Runtime, fresh_store, promote_store,
                        promote_to_source, seed_store,
                        snapshot_store, store_inventory, warm_ssh)
from .metrics import Attempt, TaskResult, append_result
from .trace import Tracer


@dataclass
class RunConfig:
    """Everything that makes a run reproducible, recorded in the manifest.

    Written to disk verbatim so that a result can be attributed to the exact
    configuration that produced it. A benchmark number without its config is not
    a measurement.
    """

    tasks: List[str]
    arms: List[str] = field(default_factory=lambda: list(ARM_ORDER))
    model: str = "claude-sonnet-4.5"
    provider: str = "livai"
    base_url: str = "https://livai-api.llnl.gov/v1"
    #: Credential for `base_url`, when it is not the ambient one. A self-hosted
    #: cluster ships its own key in its own config, and OPENAI_API_KEY in the
    #: shell belongs to a different service entirely.
    api_key: str = ""
    #: How many ranked plans to attempt in parallel. 1 keeps the old behaviour
    #: of attempting only the top-ranked one.
    #: How many researched plans to build, attempt and evaluate separately.
    #
    # 0 (the default) is EVERY plan research produced — one solution skill each,
    # one attempt each, one evaluation each. N races the top N. 1 writes a single
    # merged solution and makes one attempt.
    #
    # All, by default, because the alternative silently wastes the pass. Research
    # explores several ideas, writes each up, and ranks them on a figure of merit
    # measured against a corpus it built for itself — a proxy. Testing only the
    # top-ranked one means the other ideas were paid for and never tried, and the
    # proxy is never checked against the task's own tests.
    #
    # `reconcile_trials` then folds the table of what passed and what did not
    # into the store: what several candidates agree on becomes the solution, and
    # each failure becomes a named lesson rather than work nobody sees again.
    attempt_candidates: int = 0
    #: Comma-separated aliases that each resolve to one backend.
    pinned_models: str = ""
    #: Comma-separated models the endpoint serves. More than one makes the
    #: candidate-generating stages a mixture.
    models: str = ""
    #: Comma-separated nodes to place tasks on. Empty means `node` alone.
    nodes: str = ""
    #: Concurrent tasks per node. Multiplied by the node count to size the
    #: pool, so "8 per node" means the same thing whatever the node count is.
    tasks_per_node: int = 0
    max_tries: int = 3
    timeout_s: int = 1800
    isolation: str = "podman"
    fresh: bool = True
    #: A previous run directory to continue, or "auto" to find one.
    #:
    #: A node failure kills the whole Flux job — measured, 105 in-flight tasks
    #: lost with it — and every task it had already finished was thrown away
    #: too, because a fresh run starts from an empty results file. The results
    #: are written per task as they finish, so they are already a checkpoint;
    #: this is what makes the next job READ it.
    resume_from: str = ""
    #: Durable project layer that research is promoted into and seeded from.
    #: Empty disables carry-over entirely and every run starts from the bundled
    #: skeleton, which is what makes a run comparable to published numbers.
    carry_root: str = ""
    #: Stop starting tasks once this many dollars have been charged. 0 = no cap.
    #
    # A cap on spend, not on tasks: one task here cost $2.34 with three tries
    # while a first-try pass costs a third of that, so `--limit` bounds the task
    # count and cannot bound the bill.
    max_spend_usd: float = 0.0
    pull: bool = True
    out: Path = Path("runs/latest")
    image_template: str = ""
    #: Root for all bulk data. Empty means "resolve a PFS path"; never $HOME.
    data_root: str = ""
    #: Flux job id whose allocation runs the containers. Empty runs them locally.
    #: Recorded here because it changes *where* the work happened, which is part
    #: of what makes a number reproducible.
    flux_job: str = ""
    #: Explicit node to run containers on over ssh. Overrides flux_job's lookup.
    node: str = ""
    #: Run the arms concurrently rather than one after another.
    parallel_arms: bool = False
    #: Run this many of an arm's tasks at once. 1 keeps them strictly ordered.
    #:
    #: Ordering is not incidental. The learning claim is that task N benefits
    #: from tasks 1..N-1, and it only means something if every arm saw the same
    #: sequence — so running tasks concurrently makes `reused`, the learning
    #: rate and every carry-over number unattributable. Recorded in the manifest
    #: and reported loudly for that reason, like `--with-hints`.
    #:
    #: What it is for is iteration: six tasks that take ninety minutes in order
    #: take twenty when they overlap, and finding a pipeline bug does not
    #: require the learning measurement to be sound.
    parallel_tasks: int = 1
    #: Keep retrying a task until it passes, rather than stopping at max_tries.
    #: ``max_tries`` then acts as a hard ceiling rather than the target count.
    until_pass: bool = False
    #: In until-pass mode, how many consecutive no-progress attempts end a task.
    stall_limit: int = 2
    #: Withhold research from the first attempt, so it runs only after a failure.
    #: Makes try 1 identical in shape to the baseline's single attempt, and
    #: measures what research recovers rather than what it adds up front.
    research_on_retry: bool = False
    #: Research before the first attempt, ahead of trying what the store holds.
    #: The default is the opposite: solve from a remembered skill if there is
    #: one, plainly if there is not, and research only once that has failed.
    research_first: bool = False
    #: Which research pipeline runs: "sequential" (the default) or "parallel".
    #:
    #: sequential — the tracked loop. Check for a skill, attempt, evaluate,
    #:   fold the result into this task's tracker record, and either write the
    #:   solution (it passed) or hand the open failure to research (it did not),
    #:   which updates the task's skill for the next attempt. One thing at a
    #:   time, until progress stops.
    #: parallel — the earlier pipeline: plan emits ideas, each idea is refined,
    #:   built and tried on its own thread, pairs are combined into super-ideas,
    #:   and the first pass stops production.
    #:
    #: Both are kept so the two can be compared on the same tasks. The
    #: sequential loop is the default because the parallel one has a standing
    #: dependency the measurements never satisfied: it needs the planner to
    #: record ideas, and across every run measured it recorded none.
    pipeline: str = "sequential"
    #: Isolate this run's research in its own folder, invisible to reads unless
    #: reuse is on. Empty means write straight into the common folder.
    research_session: str = ""
    #: Reuse what earlier runs learned: seed the store with their skills and
    #: read research across every session and the common folder.
    #:
    #: ON by default, because that is the system working as intended — research
    #: is expensive and the whole point of keeping it is not paying twice.
    #:
    #: ``--fresh`` turns it off, and that is the mode for evaluating an approach
    #: cleanly: task-specific skills and research are ignored, only the bundled
    #: framework is seeded, and the run has to reach its answer on its own. The
    #: session is still synced afterwards, so a clean evaluation still
    #: contributes what it found.
    research_reuse: bool = True
    #: Give agents the maintainer discussion attached to the issue. OFF by
    #: default: published SWE-bench numbers are produced without hints, so a run
    #: with them is not comparable to them. Recorded in the manifest when on.
    include_hints: bool = False
    #: Name the grading tests to the agent. OFF by default, same reason, and a
    #: stronger hint still — the test name usually describes the required
    #: behaviour. Recorded in the manifest when on.
    reveal_target_tests: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = {k: (str(v) if isinstance(v, Path) else v) for k, v in self.__dict__.items()}
        data["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return data


class UsageWindowClosed(RuntimeError):
    """The account's usage window is exhausted, not the pipeline broken.

    These look identical from the outside — every stage returns rc=1 having made
    no tool calls — and they call for opposite responses. A broken harness must
    stop the run, because everything after it is misattributed. A dry account
    must wait, because everything after it will work again when the window
    resets, and stopping throws away a run that was half finished.

    Told apart by the harness's own `rate_limit_event`, which names the reset
    time, so this is a fact off the stream rather than an inference from rc=1.
    """


class ResearchCollapsed(RuntimeError):
    """A phronix research pass did not run at all. The run cannot continue.

    Not a task-level failure — a harness-level one. A phronix arm whose research
    never starts silently degrades into a plain agent with extra scaffolding,
    and every number it then produces is attributed to phronix. That is the most
    misleading state this benchmark can be in: it looks like a result.

    It has now happened twice for two unrelated reasons — an exhausted API key,
    and a command built with the wrong harness's flags. Both times the run
    carried on and the trace said "no phronix tools called", which reads as an
    agent ignoring its tools rather than one that never started. So it stops.
    """


class EnvironmentGone(RuntimeError):
    """The container host stopped accepting work. The run cannot continue.

    A harness-level failure, like :class:`ResearchCollapsed`, and it has the
    same shape: every task after it produces a row that looks like a result.
    Measured — a flux allocation hit its 24h wall limit mid-run, and each
    remaining task spent two attempts rediscovering that no container could
    start. The rows read ``fail`` with 0 steps, and one of them had actually
    produced a patch that was simply never judged.

    One task failing to get a container is bad luck; two in a row is the node,
    and no amount of retrying will bring it back.
    """


class Ledger:
    """Which task created which skill, and what each task retrieved.

    The single source of truth for the reuse metric. Kept per arm — a skill the
    phronix arm created must never count as reuse for the frozen control, which
    by construction created none.
    """

    #: Order recorded for a skill that predates this run.
    #:
    #: Below every real task order, so `created < order` holds for task 0 and
    #: an inherited skill counts as reuse from the very first task. It is a
    #: sentinel rather than 0 because 0 is a real task.
    INHERITED = -1

    def __init__(self) -> None:
        self.created_by: Dict[str, int] = {}       # skill -> task order
        self.created_repo: Dict[str, str] = {}     # skill -> repo it was learned on

    def record_inherited(self, skill: str, repo: str = "") -> None:
        """A skill that existed BEFORE this run — learned in an earlier session.

        Without this the reuse run measures nothing. `classify` skips any name
        it has no creation record for, and the ledger is built per run, so a
        skill written by the fresh run and loaded by the reuse run reads as
        `created is None` and is dropped. `skills_reused` would come back 0
        across the whole reuse arm — which is precisely the number the
        fresh/reuse pair exists to produce, reported as if it were a result.

        `repo` is usually unknown for an inherited skill, and unknown must not
        be read as "a different repo": that would count every carried skill as
        cross-repo reuse. Empty means unknown, and `classify` excludes it.
        """
        self.created_by.setdefault(skill, self.INHERITED)
        if repo:
            self.created_repo.setdefault(skill, repo)

    def record_creation(self, skill: str, order: int, repo: str) -> None:
        # First writer wins: a skill amended by a later task was still *learned*
        # earlier, and crediting the amendment would understate how long it has
        # been paying off.
        self.created_by.setdefault(skill, order)
        self.created_repo.setdefault(skill, repo)

    def classify(self, retrieved: Sequence[str], order: int,
                 repo: str) -> Dict[str, List[str]]:
        """Split retrieved skills into reused / cross-repo-reused.

        A skill counts as reused only if an EARLIER task created it. Skills that
        shipped with the framework are excluded: they were not learned during the
        run, and counting them would make every arm look like it was learning.
        """
        reused, cross, inherited = [], [], []
        for name in retrieved:
            created = self.created_by.get(name)
            if created is None or created >= order:
                continue
            reused.append(name)
            if created == self.INHERITED:
                inherited.append(name)
            learned_on = self.created_repo.get(name)
            # Unknown origin is not a different origin. An inherited skill
            # usually has no repo recorded, and treating that as cross-repo
            # would report every carried skill as generalising.
            if learned_on and learned_on != repo:
                cross.append(name)
        return {"reused": sorted(set(reused)),
                "cross_repo": sorted(set(cross)),
                "inherited": sorted(set(inherited))}


def _transcript_loaded(task_dir: Path, attempt_index: int, skill: str) -> bool:
    """Did this attempt's transcript contain a load of *skill*?

    The transcript is the same source the trace narrates `skill load: X` from,
    so this and the trace cannot disagree — which the retrieval log did.
    """
    if not skill:
        return False
    for name in ("opencode.jsonl", "transcript.jsonl", "agent.jsonl"):
        path = Path(task_dir) / f"attempt-{attempt_index}" / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        # The skill named anywhere in a tool call is a load: the name is not
        # free text the agent would otherwise emit.
        if skill in text:
            return True
    return False


def read_retrievals(path: Path) -> List[str]:
    """Skill names from a retrieval log, de-duplicated in first-seen order."""
    if not Path(path).is_file():
        return []
    seen, out = set(), []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        for name in record.get("skills") or []:
            if name not in seen:
                seen.add(name)
                out.append(name)
    return out


def _read_patch(workdir: Path, attempt_index: int) -> str:
    path = workdir / f"attempt-{attempt_index}" / "patch.diff"
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def _digest(text: str) -> str:
    """A stable fingerprint for "is this the same patch as last time?"."""
    import hashlib

    return hashlib.sha256(text.strip().encode("utf-8", "replace")).hexdigest()


def _attempt_history(workdir: Path, upto: int) -> List[Dict[str, Any]]:
    """Which files each previous attempt touched, and whether it worked.

    Exists because of a failure mode a single attempt's feedback cannot show. On
    pylint-7080 every block the learner wrote was about ``_discover_files`` in
    ``pylinter.py`` — the wrong file entirely; the real fix was one line in
    ``expand_modules.py``. Each attempt saw only that its patch failed, never
    that *three* patches in the same function had failed, so the knowledge base
    grew more detailed and more confident about the wrong area. Learning turned
    exploration into conviction.

    Handing forward the list of already-tried locations is what lets an attempt
    conclude "not here" instead of refining the same wrong guess.
    """
    history: List[Dict[str, Any]] = []
    for index in range(1, upto):
        patch = _read_patch(workdir, index)
        files = sorted({line.split(" b/")[-1].strip()
                        for line in patch.splitlines()
                        if line.startswith("diff --git")})
        history.append({"attempt": index, "files": files,
                        "empty": not patch.strip(),
                        # What it actually changed, not just where. Files alone
                        # cannot answer "have I already tried this", and a retry
                        # that re-applies a failed edit is the most expensive
                        # thing an attempt can do.
                        "added": _patch_changes(patch)})
    return history


def _tuned(key: str, fallback):
    """A tuning value, falling back to what the code shipped with."""
    try:
        from phronix.tuning import get

        return get(key, fallback)
    except Exception:
        return fallback


#: Extra attempts a task may earn by failing differently each time. See
#: `research.extra_tries_when_moving`.
EXTRA_TRIES_WHEN_MOVING = _tuned("research.extra_tries_when_moving", 2)


def _failure_signature(verdict: Optional[Dict[str, Any]]) -> str:
    """What failed, as a comparable fingerprint.

    Two attempts that fail the same tests for the same reason should compare
    equal; two that fail differently should not. So the signature is the target
    tests still failing, the literals the assertions wanted, and how many now
    pass — and NOT the patch, because a different patch failing identically is
    the case that matters most: the idea did not move.

    A changing signature is the good sign. It means the attempt altered the
    outcome, which is what "progress" means here even when the task is not yet
    solved.
    """
    if not verdict:
        return ""
    failing = sorted(verdict.get("fail_to_pass_failing") or [])
    wanted = sorted(_missing_literals(verdict.get("failure_detail") or ""))
    passed = verdict.get("fail_to_pass_passed")
    return "|".join(["t:" + ",".join(failing),
                     "w:" + ",".join(wanted),
                     f"p:{passed}"])


def _slug(text: str) -> str:
    """A filesystem-safe name for a trial directory."""
    import re

    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40] or "plan"


#: Exception classes an import-time breakage announces itself with.
_IMPORT_ERRORS = ("SyntaxError", "IndentationError", "NameError", "ImportError",
                  "ModuleNotFoundError", "AttributeError", "TypeError",
                  "ValueError", "RuntimeError")


def _error_tail(text: str, limit: int = 400) -> str:
    """The end of a testbed's output, cut at a LINE and led by the exception.

    This was `text[-400:]`, and a tail cut by character count starts mid-token:
    the recorded cause of a lost task read `the runner did not start: rning` —
    the end of the word "warning" from a pip notice — with the actual
    `SyntaxError` sitting a few lines above, inside the same quoted blob and
    invisible to anyone reading the trace. Measured on three tasks in one run.

    So: keep whole lines, and put the exception line FIRST, because that line
    is the answer and everything else is the path that reached it.
    """
    lines = [l.rstrip() for l in (text or "").strip().splitlines() if l.strip()]
    if not lines:
        return ""
    lead = next((l.strip() for l in reversed(lines)
                 if any(name in l for name in _IMPORT_ERRORS)), "")
    kept, size = [], len(lead)
    for line in reversed(lines):
        if line.strip() == lead:
            continue
        size += len(line) + 1
        if size > limit:
            break
        kept.append(line)
    # Always keep a line that NAMES A FILE.
    #
    # The exception line says what went wrong; only the file line says where,
    # and "where" is what decides whether a broken testbed is the harness's
    # fault or the patch's. Trimming by size dropped it whenever the traceback
    # was long: the trace then read `cannot run pytest: IndentationError:
    # expected an indented block` with no path, nothing could be blamed, and
    # the task was aborted as an environment fault though its own patch had
    # just mis-indented a file. Measured, 12 tasks across one night.
    if not any(".py" in line for line in kept):
        named = next((l.strip() for l in reversed(lines) if ".py" in l), "")
        if named:
            kept.append(named)
    body = "\n".join(reversed(kept))
    return f"{lead}\n{body}".strip() if lead else body


def _blamed_files(text: str) -> List[str]:
    """Every source file a traceback names, most-recently-mentioned first.

    Not just `/testbed/...` paths. pytest reports a broken conftest import as
    `ConftestImportFailure: SyntaxError: invalid syntax (blueprints.py, line 1)`
    — the file that actually failed to parse appears as a BARE BASENAME, and
    the only absolute path in the message is `/testbed/tests/conftest.py`,
    which is the importer and not the culprit. Blaming the absolute path alone
    read that as an environment fault and aborted a task whose patch had just
    put a syntax error in `src/flask/blueprints.py`.
    """
    words = [w.strip('",\'()[]') for w in (text or "").replace("\n", " ").split()]
    out = []
    for word in words:
        # `sympy/core/function.py:3278:` — pytest's own traceback format is a
        # RELATIVE path with a line number, which is neither an absolute
        # `/testbed/` path nor a bare basename, so it matched nothing at all.
        # Measured on sympy-18057: the patch put a `SyntaxError` in
        # `sympy/core/function.py`, the traceback said so on every line, and
        # the task was aborted as an environment fault with two tries unused.
        word = word.rstrip(":")
        if ":" in word and word.split(":")[0].endswith(".py"):
            word = word.split(":")[0]
        if word.startswith("/testbed/"):
            out.append(word[len("/testbed/"):])
        elif word.endswith(".py"):
            out.append(word)
    out.reverse()
    return out


def _blames_patch(text: str, touched: Sequence[str]) -> str:
    """The patched file a traceback blames, or "".

    Matched on the full path when the traceback gives one and on the BASENAME
    otherwise. A basename can in principle collide — two `__init__.py` — and
    the asymmetry is deliberate: a false "the patch broke it" costs one retry
    that would have happened anyway, while a false "the environment broke"
    throws the whole task away with no further try. Measured, the second
    happened three times in one run and the first has not happened yet.
    """
    names = {name: PurePosixPath(name).name for name in touched}
    for blamed in _blamed_files(text):
        base = PurePosixPath(blamed).name
        for name, name_base in names.items():
            if blamed == name or blamed.endswith("/" + name) \
                    or name.endswith("/" + blamed) or base == name_base:
                return name
    return ""


def _patch_changes(patch: str) -> List[str]:
    """The lines a patch adds, normalised for comparison.

    Whitespace and diff markers are dropped so that a re-indented or re-ordered
    version of the same change compares equal to it — which is what a retry
    usually produces when it believes the idea was right and the execution was
    off.
    """
    out: List[str] = []
    for line in (patch or "").splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        text = " ".join(line[1:].split())
        if text and text not in out:
            out.append(text)
    return out


def _patch_files(patch: str) -> List[str]:
    """The paths a patch touches. `_patch_changes` returns added LINES; the
    two are not interchangeable and reading one for the other silently
    compared a filename against a line of source."""
    return sorted({m.group(1) for m in
                   re.finditer(r"^\+\+\+ b/(\S+)", patch or "", re.MULTILINE)
                   if m.group(1) != "/dev/null"})


def _repeats_earlier(patch: str, history: List[Dict[str, Any]]) -> int:
    """Which earlier attempt this patch essentially repeats, or 0.

    Judged by overlap of added lines rather than equality: an attempt that
    re-applies most of a failed change plus a cosmetic difference is repeating
    it, and that is precisely the case a strict comparison misses.
    """
    changes = set(_patch_changes(patch))
    if len(changes) < 2:
        return 0
    for entry in history:
        earlier = set(entry.get("added") or [])
        if not earlier:
            continue
        shared = len(changes & earlier)
        if shared >= max(2, int(0.8 * min(len(changes), len(earlier)))):
            return int(entry.get("attempt") or 0)
    return 0


def _pytest_probe(container, timeout: int = 300):
    """(has_pytest, why) — and the two failure modes are NOT the same thing.

    This returned a bare bool on ``returncode == 0``, which conflates "the
    testbed has no pytest" with "the probe did not finish". They are different
    facts with different remedies, and `Runtime.run` returns non-zero for BOTH:
    on timeout it kills the process group and reports a non-zero code, exactly
    like a missing module.

    That conflation cost a task. `pallets__flask-5063` was graded on a node
    running twelve containers; the probe came back non-zero, pytest was
    "installed" (pip: *Requirement already satisfied*), the probe came back
    non-zero again, and the attempt was written off as `runner_failed` — which
    aborts the task without a further try. The image had pytest 7.3.0 the whole
    time, and a direct probe of that same image returns it in under a second.

    The timeout is also raised from 120s: the first `python -m pytest --version`
    in a cold container pays interpreter start and plugin discovery, and 120s
    was measured being hit under load.
    """
    probe = container.exec("cd /testbed && python -m pytest --version",
                           timeout=timeout)
    if probe.returncode == 0:
        return True, ""
    detail = ((probe.stdout or "") + (probe.stderr or "")).strip()
    # Say which of the two it was, so the caller can act differently.
    if "No module named" in detail or "not found" in detail:
        return False, f"pytest is genuinely absent: {_error_tail(detail)}"
    return False, (f"the probe did not answer (rc={probe.returncode}): "
                   f"{_error_tail(detail)}")


def _has_pytest(container) -> bool:
    """Can this container actually run pytest? Asked, not assumed."""
    return _pytest_probe(container)[0]


def _test_files(instance: Dict[str, Any], names: Iterable[str]) -> List[str]:
    """The files to run, from the test patch first and the ids only as a fallback.

    SWE-bench stores sympy's ids as bare function names — ``test_issue_24062``,
    with no path — so deriving files by splitting on ``::`` produced the
    *function name as a filename* and handed pytest 31 paths that do not exist.
    The test patch is authoritative and always present: it is a diff, and a diff
    names the files it touches.
    """
    patch = str(instance.get("test_patch") or "")
    touched = sorted({m.group(1) for m in
                      re.finditer(r"^\+\+\+ b/(\S+)", patch, re.MULTILINE)
                      if m.group(1) != "/dev/null"})
    # Test MODULES only. A test patch also carries fixtures — flask-4992 adds
    # `tests/static/config.toml` alongside `tests/test_config.py` — and pytest
    # given a data file answers "ERROR: found no tests" and collects nothing at
    # all, so one fixture file voided the entire instance.
    files = [name for name in touched
             if name.endswith(".py")
             and ("test" in PurePosixPath(name).name or "/tests/" in f"/{name}")]
    if files:
        return files
    return sorted({name.split("::", 1)[0] for name in names
                   if "::" in name and name.split("::", 1)[0]})


def _files_in_patch(patch: str) -> List[str]:
    """Paths a diff touches, as they appear inside the container."""
    out = []
    for line in (patch or "").splitlines():
        if line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
            path = line[4:].strip()
            for prefix in ("b/", "a/", "./"):
                if path.startswith(prefix):
                    path = path[len(prefix):]
            if path:
                out.append(path)
    return out


#: Errors that mean the SOURCE will not import, whatever the tests are.
_UNPARSEABLE = ("SyntaxError", "IndentationError", "TabError")


def patch_broke_the_source(output: str, patch: str) -> str:
    """The file and reason if the agent's own patch will not parse. Else "".

    `_runner_failure` exists for a runner that never started, and rests on the
    claim that "a patch that breaks everything still makes the tests RUN".
    That is true of a patch that is merely WRONG and false of one that is not
    valid Python: the module cannot be imported, pytest collects nothing, and
    zero-passes-zero-failures looks exactly like a missing pytest.

    Measured on django-14155: the agent wrote diff markers into the file —

        File "/testbed/django/urls/resolvers.py", line 68
            +            return (
        SyntaxError: invalid syntax

    — and the harness reported RUNNER FAILED. That is a model error dressed as
    a harness fault: it inflates the pipeline-fault count, and, worse, the
    attempt is told the runner broke rather than that its patch does not
    parse, so the next try has nothing to correct.

    Only when the unparseable file is one the PATCH touched. A syntax error in
    a file the agent never edited is the testbed's problem, and that really is
    a runner fault.
    """
    if not any(marker in output for marker in _UNPARSEABLE):
        return ""
    touched = _files_in_patch(patch)
    if not touched:
        return ""
    for path in touched:
        if path in output:
            reason = next((m for m in _UNPARSEABLE if m in output), "SyntaxError")
            return f"{path} ({reason})"
    return ""


def _runner_failure(instance: Dict[str, Any], fail_to_pass: Sequence[str],
                    pass_to_pass: Sequence[str], why: str,
                    on_event=None) -> Dict[str, Any]:
    """The tests could not be run. That is a harness fault, not a task result.

    Reported as its own thing rather than as "everything failed", because the
    two are indistinguishable in the numbers and completely different in
    meaning. A patch that breaks 30 tests is a bad patch; a runner that never
    started tells you nothing about the patch at all — and if it is allowed to
    look like the former, it gets cached as 30 pre-existing failures and poisons
    every later run of the instance.
    """
    if on_event:
        on_event(f"RUNNER FAILED — {why}")
    return {
        "resolved": False,
        "runner_failed": True,
        "error": why,
        "fail_to_pass_passed": 0, "fail_to_pass_total": len(fail_to_pass),
        "pass_to_pass_passed": 0, "pass_to_pass_total": len(pass_to_pass),
        "fail_to_pass_failing": sorted(fail_to_pass),
        "regressions": [], "pre_existing_failures": [],
        "failure_detail": why, "output_tail": why,
    }


def _missing_literals(detail: str) -> List[str]:
    """Strings a containment assertion demanded and did not get.

    pytest renders these as `assert "Subdomain" in 'Domain  Endpoint ...'`, so
    both halves are on the line: what was wanted and what was produced. The
    wanted half is the actionable one and the agent never sees the test source,
    so it is worth lifting out of six thousand characters of traceback.

    Only literals genuinely absent from the produced text are returned — a line
    can mention a string for other reasons, and a false "this is missing" would
    send the next attempt after the wrong thing.
    """
    import re

    found: List[str] = []
    for line in (detail or "").splitlines():
        if "assert" not in line or " in " not in line:
            continue
        match = re.search(r"""assert\s+["']([^"']{2,60})["']\s+in\s+(.+)$""", line)
        if not match:
            continue
        wanted, haystack = match.group(1), match.group(2)
        if wanted in haystack:
            continue                      # not the failing half of the assert
        if wanted not in found:
            found.append(wanted)
    return found


def _failure_only(text: str) -> str:
    """The failing part of a test run, with the passing part dropped.

    Keeps whatever follows the first `FAIL:`/`ERROR:` banner — which is where
    unittest puts the traceback and the assertion — and drops the per-test
    `... ok` roll-call and the database setup/teardown lines around it. Those
    are the bulk of the output and none of them is in question.

    Falls back to the whole text when no banner is found, because a run that
    failed in a way this does not recognise is exactly when the raw output is
    worth reading.
    """
    from .arms import _useful_test_output

    cleaned = _useful_test_output(text)
    lines = cleaned.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.startswith(("FAIL:", "ERROR:"))
                  or line.strip().startswith(("FAIL:", "ERROR:"))), None)
    if start is None:
        return cleaned.strip()
    # Back up over the ==== rule unittest prints above the banner.
    if start and set(lines[start - 1].strip()) == {"="}:
        start -= 1
    kept = [line for line in lines[start:] if not line.strip().endswith("... ok")]
    return "\n".join(kept).strip()


def _patch_text(attempt_dir: Path) -> str:
    """What an attempt changed, read from where the runner wrote it.

    `Attempt` has no `patch` field, and `attempt.patch` raised AttributeError
    on every evaluation turn of every run — so no task conversation ever
    recorded what an attempt did, and the only sign was one trace line.
    """
    path = Path(attempt_dir) / "patch.diff"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _feedback_note(attempt_index: int, previous: Dict[str, Any]) -> str:
    """What the last attempt got wrong, written for the next one to read.

    The benchmark knows exactly why an attempt failed — which target test never
    started passing, which previously-green test the patch broke, and the
    assertion behind each. Discarding that between attempts turns a retry into a
    re-roll of the same dice: the agent starts over with no more information than
    it had the first time, and the most likely outcome is the same patch again.
    """
    # The header depends on whether anything worked.
    #
    # "Do not repeat the same approach" is right when a change achieved
    # nothing, and wrong when it achieved half the task: at 1 of 2 on
    # django-13551 the email WAS correctly added to the token hash, and an
    # agent told not to repeat its approach has been pointed away from the one
    # part the tests confirmed.
    kept = previous.get("fail_to_pass_passing") or []
    if kept:
        opening = ("Your previous attempt got PART of this task right. Here is "
                   "exactly how it was judged: keep what worked, and change "
                   "only what did not.")
    else:
        opening = ("Your previous attempt at this task did NOT succeed. Here is "
                   "exactly how it was judged. Use it — do not repeat the same "
                   "approach.")
    lines = [f"# Feedback from attempt {attempt_index - 1}", "", opening, ""]

    # What the change ALREADY achieved, before what it missed.
    #
    # A partial pass is a partial SUCCESS, and the note used to describe it as
    # a failure and nothing else. Measured on django-13551 at 1 of 2: the
    # attempt had correctly added the email to the token hash — the target test
    # for it passed — and the feedback opened "your previous attempt did NOT
    # succeed ... do not repeat the same approach", naming only the test that
    # still failed. An agent that follows that instruction rewrites the half
    # that worked.
    if kept:
        lines += ["## What your change ALREADY fixed — keep it", "",
                  "These target tests were failing before your change and pass "
                  "because of it. Whatever you do next must keep them passing; "
                  "do not rewrite the part of the change that produced them.", ""]
        lines += [f"- `{name}`" for name in kept[:15]]
        lines.append("")

    missed = previous.get("fail_to_pass_failing") or []
    if missed:
        lines += ["## Target tests that must pass and still do not", ""]
        lines += [f"- `{name}`" for name in missed[:15]]
        lines.append("")

    regressions = previous.get("regressions") or []
    if regressions:
        lines += ["## Tests that PASSED before your change and now fail", "",
                  "These are regressions you introduced. A fix that breaks them "
                  "is not a fix.", ""]
        lines += [f"- `{name}`" for name in regressions[:15]]
        lines.append("")

    if previous.get("error"):
        lines += ["## Harness error", "", f"```\n{str(previous['error'])[:800]}\n```", ""]

    # The failure, not the whole run.
    #
    # This was a raw tail-slice of the captured output, and on a Django suite
    # the tail is passing tests. Measured on django-13551: the traceback that
    # explains the failure exactly —
    #
    #   File ".../tokens.py", line 99, in _make_hash_value
    #     return str(user.pk) + user.password + ... + email + str(timestamp)
    #   TypeError: must be str, not NoneType
    #
    # — sat at line 39 of a 97-line note, under 21 lines of `... ok` from tests
    # that were never in question, in a block that began mid-word because the
    # slice cut one. Everything the next attempt needed was present and put
    # where a reader skims past it.
    detail = _failure_only(previous.get("failure_detail") or "")
    if detail:
        lines += ["## Why it failed", "", "```", detail[:6000], "```", ""]

    # The exact strings the tests want and did not find.
    #
    # A containment assertion says precisely what is missing, and the agent
    # cannot read the grading tests — so it reasons from "the test still fails"
    # and improves the mechanism instead. Measured twice, on two different
    # models: `flask routes` gained a correct, conditional, host-vs-subdomain
    # column named "Domain" while the tests asserted "Subdomain" and "Host".
    # Three attempts refined the logic and none renamed the header, because the
    # string literal never became a suspect.
    # Did the last attempt change anything? This is the first thing the next
    # attempt needs to know, so it goes near the top.
    same_count = int(previous.get("same_failure_count") or 0)
    if previous.get("failure_moved"):
        lines += ["## This is progress", "",
                  "Your last change made the task fail DIFFERENTLY — different "
                  "tests, different missing text, or more of them passing. That "
                  "means the change had an effect and the diagnosis is roughly "
                  "right. Keep going down this line: refine it, do not abandon "
                  "it.", ""]
    elif same_count >= 3:
        lines += ["## Stop. Three attempts have failed IDENTICALLY", "",
                  "Not similar — identical: the same tests, failing for the same "
                  "reason, with the same text missing. Nothing you have changed "
                  "has altered the outcome at all, so the code you are editing is "
                  "probably not the code that produces this behaviour.", "",
                  "Do not edit anything until you have: run the failing test and "
                  "read its actual output; found which function produces that "
                  "output; and confirmed by a print or a breakpoint that your "
                  "edits are even executed on this path. If they are, then the "
                  "test wants something other than what you assumed.", ""]
    elif same_count == 2:
        lines += ["## The failure has not moved", "",
                  "This attempt failed in exactly the same way as the last one — "
                  "same tests, same reason, same text missing. A second identical "
                  "failure means the idea is wrong, not the execution.", "",
                  "PIVOT. State what you assumed, name the assumption that must "
                  "be false given this result, and take a different approach — a "
                  "different file, a different mechanism, or a different reading "
                  "of what the test wants. Refining the same change again will "
                  "produce the same failure a third time.", ""]

    missing = _missing_literals(detail)
    if missing:
        lines += ["## Exact text the tests looked for and did NOT find", ""]
        lines += [f"- `{literal}`" for literal in missing[:8]]
        lines += ["",
                  "These come from `assert \"...\" in <output>` failures, so the "
                  "string itself is what is absent — not the logic that produces "
                  "it. If your change emits a near-miss (a different word for the "
                  "same concept, different capitalisation, a synonym), fix the "
                  "literal before touching anything else.", ""]

    history = previous.get("attempt_history") or []
    tried = sorted({f for h in history for f in (h.get("files") or [])})
    if len(history) >= 2 and tried:
        lines += ["## Locations already tried and already failed", ""]
        lines += [f"- `{path}`" for path in tried[:12]]
        lines += ["",
                  f"{len(history)} attempts have now changed these files and none "
                  "fixed the target test. Treat that as evidence the cause is "
                  "somewhere else. Before editing, find the other code paths that "
                  "could produce this behaviour — the helper being called, the "
                  "caller, or where the inputs are normalised — rather than "
                  "refining the same change again.", ""]

    # The edits themselves, so "do not repeat this" is checkable rather than
    # exhortatory. Locations alone let an attempt conclude "different line, so
    # different idea" while re-applying the same failed change.
    already = []
    for entry in history:
        for line in (entry.get("added") or [])[:6]:
            if line not in already:
                already.append(line)
    if already:
        lines += ["## Edits already tried and already failed", ""]
        lines += [f"- `{line[:120]}`" for line in already[:14]]
        lines += ["",
                  "Your change must not be one of these again. If your diagnosis "
                  "leads you back to the same edit, the diagnosis is what is "
                  "wrong — say what NEW evidence distinguishes your version from "
                  "the one that already failed, and if there is none, look "
                  "elsewhere.", ""]

    lines += ["Diagnose why the previous approach was insufficient before "
              "editing anything."]
    return "\n".join(lines)


def _as_list(value: Any) -> List[str]:
    """FAIL_TO_PASS is a JSON string in the HF dataset and a list in some mirrors."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return [str(v) for v in parsed] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _passed_node_ids(output: str) -> List[str]:
    """Node ids pytest reported as PASSED, from its ``-rA`` short summary.

    The summary lines look like ``PASSED tests/test_self.py::Class::test[param]``.
    Only the summary is trusted: the progress line at the top of a pytest run is
    a row of dots with no ids in it, and the failure tracebacks quote ids that
    did *not* pass.
    """
    ids: List[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("PASSED "):
            ids.append(stripped[len("PASSED "):].strip())
        elif " PASSED" in stripped and "::" in stripped:
            # Some configurations print "<nodeid> PASSED" instead.
            ids.append(stripped.split(" PASSED", 1)[0].strip())
    return ids


#: Repos whose test suite cannot be driven by bare pytest.
#:
#: Django's tests import `django.contrib.*` at module scope, which touches
#: `settings.INSTALLED_APPS` — so under plain pytest every file dies at
#: COLLECTION with `ImproperlyConfigured: Requested setting INSTALLED_APPS`,
#: before a single test runs. The damage is silent and total: measured on
#: django__django-13551, the agent produced the upstream fix byte for byte and
#: scored 0/2 target and 0/56 pass-to-pass, which reads as a catastrophic patch
#: rather than as a suite that never started. Every Django instance in the list
#: was unresolvable by any patch, including the official one.
DJANGO_REPOS = ("django/django",)


def _needs_django_runner(instance: Dict[str, Any]) -> bool:
    return str(instance.get("repo") or "") in DJANGO_REPOS


#: Bump when the way tests are INVOKED or PARSED changes.
#:
#: Cached baselines carry this, and one that does not match is re-measured
#: rather than trusted. Without it a runner fix silently inherits the verdicts
#: of the runner it replaced.
RUNNER_REVISION = "2"


def _runner_signature(instance: Dict[str, Any]) -> str:
    """Which runner would score this instance, as a cache key."""
    kind = "django-runtests" if _needs_django_runner(instance) else "pytest"
    return f"{kind}-v{RUNNER_REVISION}"


def _django_labels(ids: Iterable[str], files: Iterable[str]) -> List[str]:
    """Dotted test labels for `runtests.py`, which does not take file paths.

    Two sources, because SWE-bench stores Django ids in two shapes: the unittest
    id `test_x (auth_tests.test_tokens.TokenGeneratorTest)`, and — when the test
    has a docstring — the DOCSTRING instead, e.g. "Updating the user email
    address invalidates the token." The second carries no module at all, so the
    file list has to cover it.
    """
    labels: List[str] = []
    for raw in ids:
        match = re.search(r"\(([\w.]+)\)", str(raw))
        if not match:
            continue
        parts = match.group(1).split(".")
        # Drop the class, keep the module: running the module is cheap and
        # cannot miss a sibling test the stored id truncated.
        module = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]
        if module and module not in labels:
            labels.append(module)
    # Fixture modules are not test modules.
    #
    # `_test_files` returns everything the test patch touched, which for Django
    # includes things like `tests/auth_tests/models/__init__.py` and
    # `models/with_custom_email_field.py` — model definitions the tests import.
    # As labels those are at best empty runs and at worst an error that takes
    # the whole invocation down with them, so they are only used when nothing
    # test-shaped was found at all.
    fixtures: List[str] = []
    for path in files:
        text = str(path)
        if not text.endswith(".py"):
            continue
        if text.endswith("__init__.py"):
            continue
        stem = text[:-3]
        for prefix in ("tests/", "./tests/"):
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
                break
        else:
            continue
        module = stem.replace("/", ".")
        if not module:
            continue
        if not module.rsplit(".", 1)[-1].startswith("test"):
            if module not in fixtures:
                fixtures.append(module)
            continue
        if module not in labels:
            labels.append(module)
    return labels or fixtures


#: `test_x (a.b.C)` — the unittest id as `--verbosity 2` prints it.
_DJANGO_ID = re.compile(r"^(test\w*)\s+\(([\w.]+)\)\s*(.*)$")
_DJANGO_OUTCOMES = ("ok", "FAIL", "ERROR", "skipped", "expected failure",
                    "unexpected success")


def _django_passed_ids(output: str) -> List[str]:
    """Tests `runtests.py` reported as passing, in BOTH shapes SWE-bench stores.

    unittest at verbosity 2 prints either

        test_x (a.b.C) ... ok

    or, when the test has a docstring, the docstring on the following line

        test_x (a.b.C)
        Updating the user email address invalidates the token. ... ok

    and SWE-bench may store either form as the id to match. So a passing test
    contributes its node id AND its docstring; matching then works whichever
    form the instance recorded, instead of scoring a passing test as failed
    because the dataset happened to name it by its prose.
    """
    passed: List[str] = []
    pending = ""
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _DJANGO_ID.match(stripped)
        if match:
            node = f"{match.group(1)} ({match.group(2)})"
            rest = match.group(3).strip()
            if rest.startswith("..."):
                if rest[3:].strip().startswith("ok"):
                    passed.append(node)
                pending = ""
            else:
                pending = node        # docstring and outcome are on the next line
            continue
        if pending and "..." in stripped:
            head, _, tail = stripped.rpartition("...")
            if tail.strip().startswith("ok"):
                passed.append(pending)
                doc = head.strip()
                if doc:
                    passed.append(doc)
            pending = ""
    return passed


def _django_any_test_ran(output: str) -> bool:
    """unittest's own summary, which says nothing about pytest's keywords."""
    if re.search(r"^Ran \d+ tests?", output, re.M):
        return True
    return any(f"... {word}" in output for word in _DJANGO_OUTCOMES)


def _any_test_ran(output: str) -> bool:
    """Did the runner produce ANY per-test outcome, pass or fail?

    Distinguishes "every test failed" — which a patch can genuinely cause —
    from "no test ever started", which no patch can. pytest's short summary
    marks each outcome with a keyword, and its final line counts them.
    """
    markers = ("PASSED ", "FAILED ", "ERROR ", "SKIPPED ", "XFAIL ", "XPASS ")
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(markers) or any(m.strip() in stripped
                                               for m in ("passed", "failed")
                                               if re.search(r"\d+ " + m.strip(),
                                                            stripped)):
            return True
    return False


def baseline_failures(container: Any, instance: Dict[str, Any],
                      cache_dir: Optional[Path] = None,
                      timeout_s: int = 900,
                      on_event=None) -> Dict[str, Any]:
    """Which PASS_TO_PASS tests already fail with NO patch applied.

    SWE-bench assumes the instance's image reproduces the original environment
    exactly, so that every ``PASS_TO_PASS`` test passes before the fix. That
    assumption does not always hold: on this site pylint-7080's
    ``test_stdin[/mymodule.py]`` fails at base commit, and two ``toml_config``
    tests fail on a ``tomlkit`` version skew.

    The consequence is not a small distortion. ``resolved`` requires *all*
    PASS_TO_PASS to pass, so a single pre-existing failure makes the instance
    unresolvable by any patch whatsoever — including the official one. Measured
    here: the agent produced the upstream fix byte for byte, passed the target
    test, and scored ``fail``.

    So the baseline is measured once per instance and cached. A test that was
    already broken is reported as pre-existing rather than counted against the
    agent — visibly, never silently, because an unexplained exclusion is how a
    benchmark quietly starts flattering itself.
    """
    instance_id = str(instance.get("instance_id", "unknown"))
    cache_file = (Path(cache_dir) / f"{instance_id}.json") if cache_dir else None
    runner = _runner_signature(instance)
    if cache_file and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text())
        except (OSError, json.JSONDecodeError):
            cached = None
        # A baseline is only meaningful for the RUNNER that measured it.
        #
        # Nothing recorded how a cached baseline was produced, so when the
        # Django path moved from bare pytest to `runtests.py` every stored
        # entry stayed authoritative — and those were measured while the suite
        # could not start at all, so they claimed 56 pass-to-pass tests were
        # already broken when in fact all of them pass. A stale discount does
        # not fail a task loudly; it quietly forgives a real regression, which
        # is the direction a benchmark must never err in.
        if isinstance(cached, dict) and cached.get("runner") == runner:
            return cached
        if cached is not None and on_event:
            on_event(f"baseline for {instance_id} was measured by "
                     f"{cached.get('runner', 'an unrecorded runner')!r}, not "
                     f"{runner!r} — re-measuring rather than trusting it")

    if on_event:
        on_event(f"measuring pre-existing failures for {instance_id}")
    verdict = evaluate(container, instance, patch="", timeout_s=timeout_s,
                       known_failures=None, on_event=on_event)
    # A baseline that could not run is not a measurement of anything.
    #
    # It was written to the cache as "every PASS_TO_PASS test is already
    # broken", which is permanent, applies to every arm, and makes the instance
    # unresolvable in exactly the way this function exists to prevent. Measured:
    # sympy-24066 cached 30 pre-existing failures from a container with no
    # pytest in it.
    if verdict.get("runner_failed"):
        if on_event:
            on_event(f"baseline for {instance_id} NOT cached — the runner never "
                     f"started, so nothing was measured")
        return {"instance_id": instance_id, "pre_existing_failures": [],
                "target_already_passing": [], "runner_failed": True,
                "error": verdict.get("error", "")}

    result = {
        "instance_id": instance_id,
        "pre_existing_failures": verdict.get("regressions", []),
        "target_already_passing": [
            name for name in _as_list(instance.get("FAIL_TO_PASS"))
            if name not in (verdict.get("fail_to_pass_failing") or [])],
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runner": runner,
    }
    if cache_file:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(result, indent=2))
        except OSError:
            pass
    return result


def evaluate(container: Any, instance: Dict[str, Any], patch: str,
             timeout_s: int = 900,
             known_failures: Optional[Sequence[str]] = None,
             on_event=None) -> Dict[str, Any]:
    """Apply the agent's patch, then the official test patch, then run the tests.

    Identical for every arm — that is the whole reason arms return a patch rather
    than scoring themselves. FAIL_TO_PASS *and* PASS_TO_PASS both have to hold:
    the former alone would pass a change that fixes the bug and breaks everything
    else, which is not a fix.
    """
    fail_to_pass = _as_list(instance.get("FAIL_TO_PASS"))
    pass_to_pass = _as_list(instance.get("PASS_TO_PASS"))
    if not fail_to_pass:
        return {"resolved": False, "error": "instance declares no FAIL_TO_PASS tests"}

    if on_event:
        on_event("applying the agent's patch" if patch.strip()
                 else "no agent patch — measuring the repository as-is")
    if patch.strip():
        applied = _apply(container, patch, "agent patch")
        if applied:
            if on_event:
                on_event(f"patch did not apply: {str(applied.get('error'))[:90]}")
            return applied

    test_patch = instance.get("test_patch") or ""
    if test_patch:
        # Reset test files first: an agent that touched a test would otherwise
        # make the official test patch conflict, and the instance would score as
        # a harness error rather than as the rule violation it is.
        container.exec("cd /testbed && git checkout -- tests test 2>/dev/null || true",
                       timeout=60)
        if on_event:
            on_event("applying the benchmark's test patch")
        applied = _apply(container, test_patch, "test patch")
        if applied:
            if on_event:
                on_event(f"test patch did not apply: {str(applied.get('error'))[:90]}")
            return applied

    # The test RUNNER has to exist before any of this means anything.
    #
    # sympy's images ship a testbed env with no pytest at all, so every command
    # returned "No module named pytest" and every test scored not-passed. The
    # verdict read as a catastrophically wrong patch — target 0/1, 30 of 30
    # pass-to-pass failing — and, because the baseline measurement hit exactly
    # the same wall, all 30 were cached as PRE-EXISTING failures. Three attempts
    # and $1.94 were spent against tests that never ran once.
    #
    # Installed into the CONTAINER's env, never the host's: the instance pins
    # the dependency versions its tests are written against, and running them
    # anywhere else measures a different library.
    #
    # Skipped entirely for Django, which uses `runtests.py` — a unittest runner
    # already in the checkout. Probing for a runner it will not use cost 20s a
    # task and, on an image whose pip predates `--root-user-action`, failed the
    # instance outright.
    present, why = (True, "") if _needs_django_runner(instance) else _pytest_probe(container)
    if not present and "did not answer" in why:
        # A probe that timed out says nothing about the environment, so asking
        # again is the cheapest way to tell a loaded node from a broken image —
        # and installing over a working pytest is pure cost.
        if on_event:
            on_event(f"pytest probe was inconclusive, asking again — {why[:120]}")
        present, why = _pytest_probe(container, timeout=600)
    if not present:
        if on_event:
            on_event("testbed has no pytest — installing it into the container"
                     f" ({why[:120]})")
        # Offline first, from the wheelhouse mounted at /wheels.
        #
        # A run that needs the network to score a test is a run that fails when
        # the registry rate-limits it, which is not hypothetical here: the
        # baseline sweep lost 40 instances to Docker Hub throttling in one
        # afternoon. The wheels are pure-python and several pytest versions are
        # staged, so pip picks whichever suits the testbed's interpreter.
        install = container.exec(
            # No --root-user-action on the network fallback.
            #
            # It only silences pip's "running as root" warning, and it did not
            # exist before pip 22.1 (2022). Several SWE-bench testbeds ship an
            # older pip, which does not ignore the unknown flag — it refuses
            # the whole command:
            #
            #   no such option: --root-user-action
            #
            # So a cosmetic argument turned "install pytest" into "this task
            # cannot be graded" on exactly the images that needed the install
            # most. Measured on django__django-13551: both arms lost every
            # evaluation, and the run recorded it as a failed task rather than
            # as a broken environment.
            "cd /testbed && (python -m pip install --quiet --no-index "
            "--find-links=/wheels pytest 2>&1 || python -m pip install --quiet "
            "--disable-pip-version-check pytest 2>&1)",
            timeout=300)
        present, why = _pytest_probe(container, timeout=600)
        if not present:
            # Report what the PROBE said, not what pip printed last.
            #
            # This quoted the tail of pip's output, which on a successful
            # install is the "Running pip as the 'root' user" warning — so the
            # recorded cause of a lost task was a warning about something that
            # had worked, with the actual reason discarded by `tail -3`.
            return _runner_failure(
                instance, fail_to_pass, pass_to_pass,
                f"the testbed environment cannot run pytest: {why} "
                f"(install said: "
                f"{_error_tail(install.stdout + install.stderr, 200)})",
                on_event)

    # ``--tb=short``, not ``--tb=no``. The traceback is the only part of the
    # output that says *why* a test failed, and "why" is what the next attempt
    # needs. Scoring works either way — it reads the PASSED lines — so suppressing
    # tracebacks bought nothing and cost the whole feedback signal: the learner
    # could report that a test failed and never what it asserted.
    command = instance.get("test_cmd") or "python -m pytest -rA --tb=short -q"
    # Run the test *files*, not the individual node ids, and match results by
    # prefix afterwards.
    #
    # SWE-bench's stored ids are truncated upstream at whitespace: pylint-7080
    # lists ``test_output_of_callback_options[command0-Emittable`` with the rest
    # of the parameter — ``messages]`` — missing. Handing that to pytest makes it
    # exit with "file or directory not found" *before running anything*, so every
    # test scores as not-passed and every arm scores unresolved. The failure is
    # invisible in the summary: 0/120 PASS_TO_PASS reads like a catastrophic
    # patch rather than a run that never happened.
    #
    # Running whole files always executes the real tests, and pytest prints the
    # full untruncated id, so a stored id matching as a prefix is exactly the
    # right test. It costs running some tests the instance did not list, which is
    # a cost in seconds and never in correctness.
    files = _test_files(instance, list(fail_to_pass) + list(pass_to_pass))
    if not files:
        return _runner_failure(
            instance, fail_to_pass, pass_to_pass,
            "could not work out which test files to run: the test patch names "
            "none and the stored ids carry no path", on_event)
    # Django gets its own runner, because bare pytest cannot start its suite.
    #
    # `runtests.py` is what Django's own contributing docs use and what the
    # upstream SWE-bench harness uses: it calls `django.setup()`, points
    # DJANGO_SETTINGS_MODULE at the test settings and builds the test database,
    # none of which pytest does on its own. It also takes dotted LABELS rather
    # than file paths, and prints unittest output rather than pytest's, so the
    # command and the parser have to change together.
    django = _needs_django_runner(instance)
    if django:
        labels = _django_labels(list(fail_to_pass) + list(pass_to_pass), files)
        if not labels:
            return _runner_failure(
                instance, fail_to_pass, pass_to_pass,
                "could not work out which Django test labels to run", on_event)
        targets = " ".join(shlex.quote(label) for label in labels)
        command = (instance.get("test_cmd")
                   or "python tests/runtests.py --verbosity 2 --noinput")
        if on_event:
            on_event(f"running {len(labels)} Django test label(s) via "
                     f"runtests.py: {', '.join(labels[:3])}")
    else:
        targets = " ".join(shlex.quote(path) for path in files)
        if on_event:
            on_event(f"running {len(files)} test file(s): {', '.join(files[:3])}")
    result = container.exec(f"cd /testbed && {command} {targets}", timeout=timeout_s)
    output = result.stdout + result.stderr

    passed_ids = _django_passed_ids(output) if django else _passed_node_ids(output)

    # Nothing ran at all is a runner fault, not a verdict.
    #
    # Zero passes and zero failures cannot be produced by any patch: a patch
    # that breaks everything still makes the tests RUN. Scoring it as "all
    # tests failed" is what let a missing pytest read as a catastrophic patch,
    # three times over, and get cached as pre-existing breakage.
    ran = _django_any_test_ran(output) if django else _any_test_ran(output)
    if not passed_ids and not ran:
        # The agent's own patch may be why nothing ran. See
        # `patch_broke_the_source`: that is a VERDICT, not a runner fault, and
        # the attempt has to be told which file will not parse so the next try
        # can fix it.
        broken = patch_broke_the_source(output, patch)
        if broken:
            if on_event:
                on_event(f"verdict: not resolved — the patch does not parse: "
                         f"{broken}")
            why = (f"the patch does not parse: {broken}. Python could not "
                   f"import the file, so no test ran. Check the edit wrote "
                   f"SOURCE and not diff text — a line beginning with `+` or "
                   f"`-` inside the file is the usual cause.")
            # The SAME shape every other verdict returns, so the feedback,
            # the metrics and the ledger all read it without special-casing.
            # `runner_failed` is deliberately absent: the runner was fine.
            return {
                "resolved": False,
                "patch_unparseable": broken,
                "error": why,
                "fail_to_pass_passed": 0,
                "fail_to_pass_total": len(fail_to_pass),
                "fail_to_pass_passing": [],
                "fail_to_pass_failing": sorted(fail_to_pass),
                "pass_to_pass_passed": 0,
                "pass_to_pass_total": len(pass_to_pass),
                "regressions": [],
                "pre_existing_failures": [],
                "failure_detail": why,
                "output_tail": _error_tail(output, 600),
            }
        return _runner_failure(
            instance, fail_to_pass, pass_to_pass,
            f"no test produced a result; the runner did not start: "
            f"{_error_tail(output, 300)}", on_event)

    def passed(name: str) -> bool:
        # Prefix, not equality: the stored id may be a truncation of the real
        # one. Anchored at the start so one test cannot be credited by another
        # whose name merely contains it.
        #
        # Matched against the function part as well as the whole node id,
        # because SWE-bench stores sympy's ids as bare function names —
        # ``test_Quantity_definition`` — while pytest reports
        # ``sympy/physics/units/tests/test_quantities.py::test_Quantity_definition``.
        # A whole-id prefix test can never match one against the other, so every
        # sympy instance scored 0 of 30 on tests that had just printed PASSED.
        if "::" in name:
            return any(actual.startswith(name) for actual in passed_ids)
        return any(actual.startswith(name)
                   or actual.split("::")[-1].startswith(name)
                   for actual in passed_ids)

    f2p = {name: passed(name) for name in fail_to_pass}
    p2p = {name: passed(name) for name in pass_to_pass}

    # A test that was already failing before this patch is not this patch's
    # fault. Discounted from the verdict, but reported, so the exclusion is
    # always visible in the record rather than folded silently into a pass.
    already_broken = set(known_failures or ())
    regressions = sorted(n for n, ok in p2p.items() if not ok and n not in already_broken)
    pre_existing = sorted(n for n, ok in p2p.items() if not ok and n in already_broken)
    resolved = all(f2p.values()) and not regressions

    if on_event:
        on_event(f"verdict: {'RESOLVED' if resolved else 'not resolved'} — "
                 f"target {sum(f2p.values())}/{len(f2p)}, "
                 f"regressions {len(regressions)}"
                 + (f", {len(pre_existing)} pre-existing failure(s) discounted"
                    if pre_existing else ""))
    return {
        "resolved": resolved,
        "fail_to_pass_passed": sum(f2p.values()),
        "fail_to_pass_total": len(f2p),
        "pass_to_pass_passed": sum(p2p.values()),
        "pass_to_pass_total": len(p2p),
        # Named so the next attempt can be told which of its obligations it
        # missed: a target test that never started passing is a different problem
        # from a regression it introduced.
        "fail_to_pass_failing": sorted(n for n, ok in f2p.items() if not ok),
        # And which of them it MET. A partial pass is evidence in both
        # directions, and only one of them was being recorded: at 1 of 2 the
        # next attempt was told what it missed and nothing about what it got
        # right, under a heading saying "do not repeat the same approach" —
        # advice that, taken literally, throws away the half the tests had just
        # confirmed.
        "fail_to_pass_passing": sorted(n for n, ok in f2p.items() if ok),
        "regressions": regressions,
        "pre_existing_failures": pre_existing,
        "failure_detail": _failure_detail(output),
        "output_tail": output[-2000:],
    }


def _failure_detail(output: str, limit: int = 6000) -> str:
    """The FAILURES section of a pytest run — the part that says *why*.

    Extracted rather than passing the whole log on: a full run of a large test
    file is hundreds of kilobytes, most of it passing-test noise, and burying the
    three lines that matter in it is functionally the same as not having them.

    Falls back to the tail when pytest used a format without a FAILURES banner,
    which is better than returning nothing and claiming there was no reason.
    """
    marker = "=== FAILURES ==="
    start = output.find(marker)
    if start == -1:
        start = output.find("= FAILURES =")
    if start == -1:
        return output[-limit:]

    # Stop at the short summary, which the caller already reports structurally.
    end = output.find("=== short test summary", start)
    if end == -1:
        end = output.find("= short test summary", start)
    section = output[start:end if end != -1 else len(output)]
    if len(section) <= limit:
        return section
    # Keep the head: the first failure's traceback is the most diagnostic, and
    # truncating from the front would remove the assertion that explains it.
    return section[:limit] + "\n... (truncated)"


def _apply(container: Any, patch: str, label: str) -> Optional[Dict[str, Any]]:
    """Apply a diff inside the container. Returns an error dict, or None on success.

    Written through a heredoc rather than shell-quoted: a real patch contains
    quotes, backslashes and ``$``, and any quoting scheme that has to survive two
    shells will eventually corrupt one. ``-p1`` then ``-p0`` because SWE-bench
    patches are inconsistent about the leading path component.
    """
    script = (
        "cd /testbed && cat > /tmp/apply.patch <<'PHRONIX_PATCH_EOF'\n"
        f"{patch.rstrip()}\n"
        "PHRONIX_PATCH_EOF\n"
        "git apply -v -p1 /tmp/apply.patch 2>/tmp/apply.err "
        "|| git apply -v -p0 /tmp/apply.patch 2>>/tmp/apply.err "
        "|| patch -p1 -i /tmp/apply.patch 2>>/tmp/apply.err"
    )
    result = container.exec(script, timeout=180)
    if result.returncode != 0:
        detail = container.exec("cat /tmp/apply.err", timeout=30).stdout
        return {"resolved": False,
                "error": f"{label} did not apply: {detail[-400:] or result.stderr[-400:]}"}
    return None


class Runner:
    """Executes a :class:`RunConfig` and writes results as it goes."""

    def __init__(self, config: RunConfig, instances: Dict[str, Dict[str, Any]]) -> None:
        self.config = config
        self.instances = instances
        #: Dollars charged so far, and the lock that keeps the count honest when
        #: arms and tasks run concurrently. Both arms bill the same account, so
        #: the ceiling is per RUN rather than per arm.
        self._spent_usd = 0.0
        self._spend_lock = threading.Lock()
        self.out = Path(config.out)
        self.out.mkdir(parents=True, exist_ok=True)
        # Image store on the PFS, never $HOME — see tests/benchmark/paths.py.
        from .paths import container_storage, data_root

        # One bus per run, named after the run.
        #
        # The learner binds it and every producer connects to it. Per run rather
        # than per host because two runs sharing an endpoint would share a
        # learner, and each would be taught from the other's tasks.
        os.environ.setdefault(
            "PHRONIX_BUS",
            f"ipc://{Path(config.out).resolve() / 'learning.sock'}")

        storage = container_storage(data_root(config.data_root or None))

        # One runtime per node, and a task's containers go to the node it was
        # assigned. Spreading tasks across nodes is the only way past a single
        # node's core count, and container work is what actually consumes those
        # cores — the agents mostly wait on the model.
        #
        # `runtime` below is a property reading thread-local state, because a
        # task is a thread and the alternative is threading the runtime through
        # every call between `run_task` and the container session.
        self._local = threading.local()
        nodes = self.nodes()
        if config.isolation in ("podman", "docker"):
            self._runtimes = [
                Runtime.detect(config.isolation, storage=storage,
                               flux_job=config.flux_job, node=node)
                for node in (nodes or [config.node])]
        else:
            self._runtimes = []

    def warm_connections(self, tracer=None) -> None:
        """Open the shared ssh connection to every node, before any work.

        See `isolation.warm_ssh`: multiplexing is worth nothing until a master
        exists, and thirty tasks starting together are thirty simultaneous
        first connections that sshd refuses past `MaxStartups`.
        """
        hosts = [h for h in self.nodes() if h]
        if not hosts:
            return
        opened = warm_ssh(hosts)
        if tracer:
            missed = [h for h in hosts if h not in opened]
            tracer.event("ssh", f"shared connection open to {len(opened)}/"
                                f"{len(hosts)} node(s)"
                                + (f"; not warmed: {', '.join(missed)}" if missed else ""))

    def nodes(self) -> List[str]:
        """Every node tasks may be placed on, in assignment order."""
        listed = [n.strip() for n in str(self.config.nodes or "").split(",")
                  if n.strip()]
        if listed:
            return listed
        return [self.config.node] if self.config.node else []

    @property
    def runtime(self):
        """The runtime for the calling task's node.

        Falls back to the first when nothing has been assigned — setup and
        preflight run before any task exists and must still be able to reach a
        container.
        """
        chosen = getattr(self._local, "runtime", None)
        if chosen is not None:
            return chosen
        return self._runtimes[0] if self._runtimes else None

    #: Hosts whose containers would not start, shared by every task.
    #:
    #: A node that failed one task will fail the next: the point of recording
    #: it is that the SECOND task does not have to discover it. Flux kills the
    #: whole job when a node dies outright, which nothing here can catch — but
    #: a node that is merely unreachable, out of disk, or has lost its podman
    #: takes tasks down one at a time, and those are recoverable.
    _BAD_HOSTS: set = set()
    _BAD_HOSTS_LOCK = threading.Lock()

    def note_bad_host(self, host: str, why: str = "") -> None:
        if not host:
            return
        with self._BAD_HOSTS_LOCK:
            first = host not in self._BAD_HOSTS
            self._BAD_HOSTS.add(host)
        if first:
            print(f"  [nodes] {host} is not usable"
                  + (f": {why[:120]}" if why else "")
                  + " — tasks will be placed elsewhere", flush=True)

    def another_runtime(self, current):
        """A runtime on a DIFFERENT, not-known-bad node. None if there is none.

        Re-placing the task is what makes a node failure survivable: the try
        that failed on a dead node is retried on a live one instead of being
        spent proving the node is still dead. Without this a task burned both
        its isolation attempts on one host and gave up, and every later task
        placed there did the same.
        """
        if not self._runtimes:
            return None
        here = getattr(current, "host", "") or ""
        with self._BAD_HOSTS_LOCK:
            bad = set(self._BAD_HOSTS)
        options = [r for r in self._runtimes
                   if (getattr(r, "host", "") or "") not in bad
                   and (getattr(r, "host", "") or "") != here]
        if not options:
            # Every node is suspect. Prefer any other node over this one:
            # "all bad" is more often a transient than a truth.
            options = [r for r in self._runtimes
                       if (getattr(r, "host", "") or "") != here]
        if not options:
            return None
        return random.choice(options)

    def resume_source(self) -> Optional[Path]:
        """The run directory this one continues, if any.

        `auto` picks the newest run that used the SAME task list and model and
        did not finish. Same list and model because a resumed run has to be
        the same experiment: continuing a gpt-oss run into a nemotron one
        would produce a results file that is neither.
        """
        want = str(self.config.resume_from or "").strip()
        if not want:
            return None
        if want.lower() != "auto":
            found = Path(want)
            return found if found.is_dir() else None

        mine = (sorted(self.config.tasks), str(self.config.model))
        best = None
        for candidate in sorted(self.out.parent.glob("*/"),
                                key=lambda c: c.stat().st_mtime, reverse=True):
            if candidate.resolve() == self.out.resolve():
                continue
            try:
                manifest = json.loads((candidate / "manifest.json").read_text())
            except (OSError, ValueError):
                continue
            if (sorted(manifest.get("tasks") or []), str(manifest.get("model"))) != mine:
                continue
            best = candidate
            break
        return best

    def inherited_skills(self) -> Dict[str, str]:
        """Skills EARLIER runs recorded creating, mapped to the repo they came from.

        Read from the previous runs' `results.jsonl` rather than by inspecting
        the store, because the store cannot tell the two kinds of skill apart.
        The carried layer holds both the framework's own skills — which shipped
        and were never learned — and what earlier runs promoted into it, and
        counting the framework's would make every arm look like it was
        learning from its first task. A prefix does not separate them either:
        the name is chosen by whichever agent wrote the skill.

        `skills_created` is the precise answer. Each earlier run recorded, per
        task, exactly what that task added, so the union over earlier runs is
        the learned set and nothing else.
        """
        out: Dict[str, str] = {}

        # Task ANSWERS in the carried layer are learned by definition.
        #
        # They are the other half, and they cannot be recovered from the
        # earlier runs' `skills_created`: that column was empty for every task
        # until the inventory bug was fixed, because it diffed only `skills`
        # and a task answer is a directory under `capabilities/tasks`. Reading
        # the layer directly recovers what those runs learned but never
        # recorded. Nothing here ships with the framework — the framework's
        # own tools are not task answers — so there is no risk of crediting a
        # run with knowledge it was given.
        try:
            from phronix.layers import bundled_root
            answers = Path(bundled_root()) / "capabilities" / "tasks"
            if answers.is_dir():
                for slug in answers.iterdir():
                    if slug.is_dir():
                        out.setdefault(slug.name, "")
                        out.setdefault(f"tasks/{slug.name}", "")
        except Exception:
            pass                      # a layer that cannot be read is not fatal

        runs = sorted(self.out.parent.glob("*/"),
                      key=lambda c: c.stat().st_mtime, reverse=True)
        for candidate in runs:
            try:
                if candidate.resolve() == self.out.resolve():
                    continue
            except OSError:
                continue
            for listing in candidate.glob("*/results.jsonl"):
                try:
                    lines = listing.read_text(encoding="utf-8").splitlines()
                except OSError:
                    continue
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue      # a torn last line: the job died writing it
                    for name in (row.get("skills_created") or []):
                        out.setdefault(name, str(row.get("repo") or ""))
        return out

    def finished_already(self, source: Path, arm_name: str) -> Dict[str, Any]:
        """Instance ids the previous run RECORDED for this arm, with results.

        A recorded result is a finished task: `append_result` is called once
        per task, after its verdict. Anything that was in flight when the job
        died is simply absent, which is the correct answer — it has no result.
        """
        done: Dict[str, Any] = {}
        listing = source / arm_name / "results.jsonl"
        try:
            for line in listing.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue          # a torn last line: the job died writing it
                if row.get("instance_id"):
                    done[row["instance_id"]] = row
        except OSError:
            return {}
        return done

    def runtime_for(self, order: int):
        """Round-robin over the USABLE nodes, so consecutive tasks spread.

        Nodes already known bad are skipped rather than handed a task that
        will fail the same way. Round-robin over the survivors keeps the
        spread even as nodes drop out, which a fixed modulus would not: with
        one node of eight dead, `order % 8` still sends every eighth task to
        it.
        """
        if not self._runtimes:
            return None
        with self._BAD_HOSTS_LOCK:
            bad = set(self._BAD_HOSTS)
        usable = [r for r in self._runtimes
                  if (getattr(r, "host", "") or "") not in bad]
        # Every node suspect is more often a transient than a truth, so fall
        # back to the full list rather than refusing to place the task.
        pool = usable or self._runtimes
        return pool[order % len(pool)]

    def manifest(self) -> Dict[str, Any]:
        from phronix import __version__

        # The RESOLVED budget scale, not the request.
        #
        # `auto` is a measurement, so recording the word "auto" would leave the
        # manifest unable to answer the one question it exists for: how long
        # the research stages were actually allowed to run. A run whose stages
        # were cut off mid-investigation and one whose stages finished are not
        # comparable, and the difference is this number.
        from .arms import budget_scale, measured_decode_rate

        record = {
            "phronix_version": __version__,
            "runtime": (self.runtime.name if self.runtime else self.config.isolation),
            **self.config.to_dict(),
        }
        try:
            record["budget_scale"] = round(budget_scale(), 2)
            rate = measured_decode_rate()
            if rate:
                record["measured_decode_tok_s"] = round(rate, 1)
        except Exception:
            pass
        return record

    def preflight(self) -> str:
        """Check the container host is usable. Returns an error string, or "".

        A run whose container host has gone away does not fail loudly — every
        attempt dies in isolation before the agent starts, and the result table
        fills with ``0 steps, 0 tokens`` rows that look exactly like an agent
        that ran and did nothing. A flux allocation expiring mid-run produced
        six such tasks here before anyone could tell it was infrastructure
        rather than the framework.
        """
        model_problem = self._model_reachable()
        if model_problem:
            return model_problem

        if self.runtime is None:
            return ""
        try:
            result = self.runtime.run(["info", "--format", "{{.Host.Arch}}"],
                                      timeout=120)
        except Exception as exc:
            return f"container runtime unusable: {type(exc).__name__}: {exc}"
        if result.returncode != 0:
            where = (" on " + self.runtime.launcher[-1]) if self.runtime.launcher else ""
            return (f"container host{where} is not usable: "
                    f"{(result.stderr or result.stdout).strip()[-200:]}")
        return ""

    def _model_reachable(self) -> str:
        """One cheap call to the model endpoint before committing to a run.

        The container host was checked and the model was not, so a run whose
        provider was refusing every request started anyway and produced attempt
        after attempt of ``1 step, 0 tokens`` — indistinguishable, from the
        outside, from an agent that ran and did nothing.

        It has now happened twice. Once it took out three attempts of one task
        and was read as the agent going in circles; once it took out an entire
        run, both arms, for ten minutes before anyone looked at the trace. The
        provider says exactly what is wrong — "Budget has been exceeded ...
        Current cost: 500.85, Max budget: 500.0" — and that message is worth
        more before the run than buried in a transcript afterwards.
        """
        import json as _json
        import urllib.error
        import urllib.request

        # Only the arms that go through the shared endpoint. The Claude Code
        # arms authenticate through their own account, so probing LiVAI would
        # block a run that has nothing to do with it — which is the whole reason
        # that harness exists.
        if not any(not name.startswith("claude") for name in self.config.arms):
            return ""

        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return ("OPENAI_API_KEY is not set — every arm needs it")

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        body = _json.dumps({"model": self.config.model, "max_tokens": 4,
                            "messages": [{"role": "user", "content": "hi"}]})
        request = urllib.request.Request(
            url, data=body.encode(), method="POST",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=60):
                return ""
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                payload = _json.loads(exc.read().decode(errors="replace"))
                detail = str((payload.get("error") or {}).get("message", ""))[:220]
            except Exception:
                pass
            if exc.code in (401, 403):
                return f"the model endpoint rejected the key ({exc.code}): {detail}"
            if exc.code == 429:
                return (f"the model endpoint is refusing requests (429): {detail}\n"
                        "Every attempt would report 0 steps and 0 tokens, which "
                        "looks like an agent that did nothing.")
            # Anything else may be transient or model-specific; not worth
            # blocking a run over.
            return ""
        except Exception:
            # A probe that cannot run is not evidence the endpoint is down.
            return ""

    def run(self) -> Dict[str, List[TaskResult]]:
        problem = self.preflight()
        if problem:
            print(f"\nrefusing to start: {problem}\n"
                  "If this is a batch allocation, it has probably expired — check "
                  "`flux jobs` and pass --node for the new one.", flush=True)
            raise IsolationError(problem)
        (self.out / "manifest.json").write_text(json.dumps(self.manifest(), indent=2) + "\n")
        # Before any task: one shared ssh connection per node, opened while
        # nothing is competing for sshd. See `warm_connections`.
        try:
            self.warm_connections()
        except Exception:
            pass          # unmultiplexed connections, not no connections
        try:
            if self.config.parallel_arms and len(self.config.arms) > 1:
                return self._run_arms_parallel()

            results: Dict[str, List[TaskResult]] = {}
            for arm_name in self.config.arms:
                print(f"\n=== arm: {arm_name} ===", flush=True)
                results[arm_name] = self.run_arm(arm_name)
            return results
        finally:
            self._sync_research_session()

    def _over_budget(self) -> str:
        """Why this run must not start another task, or "" to continue.

        A cap on DOLLARS rather than on tasks, because the two are only loosely
        related: one task here cost $2.34 and took three tries, while a task that
        passes on try 1 costs a third of that. `--limit` bounds the task count
        and cannot bound the bill.
        """
        ceiling = float(getattr(self.config, "max_spend_usd", 0.0) or 0.0)
        if ceiling <= 0:
            return ""
        with self._spend_lock:
            spent = self._spent_usd
        if spent < ceiling:
            return ""
        return (f"spend ceiling reached: ${spent:.2f} of ${ceiling:.2f} — "
                f"remaining tasks skipped")

    def _sync_research_session(self, quiet: bool = False,
                               store_root: Optional[Path] = None) -> None:
        """Fold this run's research into the common, checked-in folder.

        Automatic, and in a ``finally``, because the runs whose research is most
        worth keeping are the ones that did not finish cleanly — and a sync that
        only happens on the happy path is a sync that misses exactly those.

        It runs whether or not the session could READ anything. A ``--fresh``
        run is deliberately blind to earlier work, but what it finds is still
        findings, and withholding them would mean a clean evaluation cost full
        price and contributed nothing.
        """
        session = self.config.research_session
        if not session or not self.config.carry_root:
            return

        import os

        from phronix import research

        previous = {k: os.environ.get(k) for k in
                    ("PHRONIX_PROJECT_ROOT", "PHRONIX_RESEARCH_SESSION")}
        try:
            # Where the session's records ACTUALLY are.
            #
            # They are written to the run's own store — `<run>/<arm>/store/
            # .phronix/research/sessions/<id>/` — because a session must not be
            # able to read its way out of its isolation. This pointed at the
            # carry root instead, which has no `sessions/` at all, so the fold
            # returned "no such session" every time and nothing was ever synced.
            #
            # `promote_store` then skips `research/sessions/` on purpose, on the
            # understanding that this function has already folded them into the
            # common folder. It had not. So the records were skipped by one step
            # and never reached by the other, and every run's research died with
            # its run directory: measured on `claude-0822-175928`, which SOLVED
            # its task and left the carry root with one unrelated record.
            #
            # Fold inside the run store, then let `promote_store` carry the
            # common folder up as it already does for skills.
            os.environ["PHRONIX_PROJECT_ROOT"] = str(
                store_root if store_root is not None
                else Path(self.config.carry_root).parent)
            os.environ["PHRONIX_RESEARCH_SESSION"] = session
            result = research.sync_session(session)
            if result.get("synced") and not quiet:
                print(f"\nsynced {len(result['synced'])} research record(s) from "
                      f"session {session} into {result['into']}", flush=True)
        except Exception as exc:
            print(f"\nresearch sync failed ({exc}); session {session} is still "
                  f"on disk and can be synced by hand", flush=True)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _run_arms_parallel(self) -> Dict[str, List[TaskResult]]:
        """Run every arm concurrently, one thread each.

        Arms are independent by construction — separate store, separate results
        file, separate containers — so the only thing serialising them was the
        loop. Halving a two-arm run's wall clock matters when each arm is hours.

        Threads rather than processes: every expensive thing here is a
        subprocess (opencode, podman, ssh), so the GIL is released for
        essentially the whole run.

        **What this does not change is what is measured.** Each arm still sees
        its own tasks in the same fixed order, and the learning arm's store still
        accumulates strictly in that order — parallelism is across arms, never
        across tasks within an arm, because a task's store must contain what the
        previous task learned. Per-task numbers are wall-clock independent
        (tokens, steps, resolution), so a concurrent run and a serial one are
        comparable; only elapsed-time figures shift, and nothing is scored on
        those.
        """
        from concurrent.futures import ThreadPoolExecutor

        print(f"\n=== running {len(self.config.arms)} arms concurrently: "
              f"{', '.join(self.config.arms)} ===", flush=True)
        results: Dict[str, List[TaskResult]] = {}
        collapsed: Optional[BaseException] = None
        with ThreadPoolExecutor(max_workers=len(self.config.arms)) as pool:
            futures = {pool.submit(self.run_arm, name): name
                       for name in self.config.arms}
            for future, name in futures.items():
                try:
                    results[name] = future.result()
                except (ResearchCollapsed, EnvironmentGone) as exc:
                    # The exception to "one arm failing must not void the
                    # others": if phronix research never started, the phronix
                    # numbers are meaningless and the comparison they exist for
                    # cannot be made. Finishing the baseline alone would produce
                    # a report that looks like a result.
                    print(f"\n[{name}] RESEARCH COLLAPSED — stopping the run\n"
                          f"{exc}\n", flush=True)
                    collapsed = exc
                except Exception as exc:  # one arm failing must not void the others
                    print(f"[{name}] arm failed: {exc}", flush=True)
                    results[name] = []

        if collapsed is not None:
            raise collapsed

        # Restore the configured order; futures complete in whatever order they do.
        return {name: results.get(name, []) for name in self.config.arms}

    def run_arm(self, arm_name: str) -> List[TaskResult]:
        arm = build_arm(arm_name, model=self.config.model, provider=self.config.provider,
                        base_url=self.config.base_url, timeout_s=self.config.timeout_s,
                        api_key=self.config.api_key)
        # Hand the arm every model the fleet serves, so stages that generate
        # candidates can spread across them.
        if getattr(self.config, "models", ""):
            arm.models = [m.strip() for m in str(self.config.models).split(",")
                          if m.strip()]
        # Aliases that pin a conversation to one backend. Without them every
        # turn re-processes the whole history on whichever server it lands on.
        if getattr(self.config, "pinned_models", ""):
            arm.pinned_models = [m.strip()
                                 for m in str(self.config.pinned_models).split(",")
                                 if m.strip()]
        # Which arm this is, so a task's two arms pin to DIFFERENT backends.
        # They share no prefix, and on a one-slot server sharing a backend
        # means queueing behind each other.
        arm.arm_name = arm_name
        arm.include_hints = self.config.include_hints
        arm.reveal_target_tests = self.config.reveal_target_tests
        # Research asks for this: it decides whether the solution is built
        # before the attempt or after the trials that measure it.
        # `or 0`, and 0 means ALL. Coercing to 1 here would hand the arm a cap
        # of one while the runner raced everything, so research would write a
        # single merged solution and the race would have nothing to race.
        arm.attempt_candidates = int(
            getattr(self.config, "attempt_candidates", 0) or 0)
        arm_dir = self.out / arm_name
        arm_dir.mkdir(parents=True, exist_ok=True)
        results_path = arm_dir / "results.jsonl"
        # A re-run of the same arm starts clean rather than appending to the
        # previous attempt's file, which would double-count every task.
        results_path.unlink(missing_ok=True)

        # ...unless this run is CONTINUING one that was cut short.
        #
        # Then the earlier results are copied in first, so the report covers
        # the whole list rather than only what this job managed, and the tasks
        # behind them are skipped below. Copied rather than referenced: the
        # run directory has to stand on its own once the older one is cleaned
        # up.
        carried: Dict[str, Any] = {}
        source = self.resume_source()
        if source is not None:
            carried = self.finished_already(source, arm_name)
            for row in carried.values():
                append_result(results_path, TaskResult.from_dict(row))
            if carried:
                print(f"  [{arm_name}] resuming {source.name}: "
                      f"{len(carried)} task(s) already finished, skipping them",
                      flush=True)

        # One store per arm. The frozen and full phronix arms must not share one:
        # the full arm's writes would then be visible to the control, and the
        # control would stop being a control.
        store_root = arm_dir / "store" / ".phronix"
        if self.config.fresh or not store_root.exists():
            fresh_store(store_root)

        # Carry-over: what earlier runs researched, laid over the skeleton.
        #
        # Only the arms that use phronix, and only when a carry root is
        # configured. The bare arm has no store to seed, and seeding it would
        # be the contamination the whole comparison exists to avoid.
        carried: List[str] = []
        if (self.config.carry_root and self.config.research_reuse
                and getattr(arm, "uses_phronix", False)):
            carried = seed_store(store_root, Path(self.config.carry_root))["seeded"]
            if carried:
                print(f"  [{arm_name}] seeded {len(carried)} file(s) of earlier "
                      f"research and skills from {self.config.carry_root}",
                      flush=True)
        elif getattr(arm, "uses_phronix", False):
            # Fresh seeds NO capabilities, and the store is not where that is
            # enforced.
            #
            # It used to seed every `probe_`-prefixed tool, on the reasoning
            # that a method tool carries nothing about any task. The reasoning
            # was right and the test was not: the prefix is chosen by whichever
            # agent wrote the tool, and `probe_fix_max_to_sum_powers_filter`
            # applies one benchmark task's fix outright. A from-scratch run was
            # being handed answers under a naming convention.
            #
            # What replaces it is a live filter — the MCP server serves the
            # bundled tools plus whatever this session authors, and nothing
            # from any earlier run's layer. So the run still builds and calls
            # its own tools, and there is no seeded set to get wrong.
            print(f"  [{arm_name}] fresh: the bundled framework only — no "
                  f"earlier skills, research or capabilities; tools this run "
                  f"builds are served to it and to nothing after it",
                  flush=True)

        # The session the arm writes into, and whether it may read outside it.
        arm.research_session = self.config.research_session
        # What the run was TOLD to be, handed to the library so that
        # what it may see matches. See `isolated_env`.
        arm.fresh = bool(self.config.fresh)
        arm.research_reuse = self.config.research_reuse

        # One learner for the whole arm, started before any task is.
        #
        # It was only ever stopped: `stop_learning` was called at the end of the
        # arm and `start_learning` was called nowhere, so every run drained an
        # empty bus and the observations the stages wrote — ten of them in the
        # run that exposed this — were never generalised into anything. The
        # symptom was silence, which reads exactly like a learner with nothing
        # to say.
        #
        # Before the tasks rather than inside one, because a learner per task
        # would have several agents writing the same skills, which is what the
        # partition by kind of operation exists to prevent.
        # Unguarded: the base arm defines `start_learning` as a no-op precisely
        # so the caller does not need a `hasattr` that quietly stops working
        # when a name changes.
        try:
            arm.start_learning(store_root, arm_dir, arm_dir,
                               on_learning=lambda note: tracer.event(
                                   "learner", note))
        except Exception as exc:
            # A learner that cannot start must not stop the arm, but it must say
            # so — this failed silently for a whole run once already.
            print(f"  [{arm_name}] learner did NOT start: "
                  f"{type(exc).__name__}: {exc}", flush=True)

        ledger = Ledger()
        # Everything that already existed is credited to an earlier session.
        #
        # This is what makes the fresh/reuse pair measurable. `classify` drops
        # any name with no creation record, and the ledger is per run, so a
        # skill the fresh run wrote and this one loads would read as unknown
        # and be dropped — `skills_reused` 0 across the arm, reported as a
        # result rather than as blindness.
        #
        # Only for arms that read the carried layer. A fresh arm is entitled
        # to a clean read and by construction inherits nothing, so seeding it
        # would credit it with reuse it never had.
        if getattr(arm, "uses_phronix", False) and not self.config.fresh:
            for name, repo in self.inherited_skills().items():
                ledger.record_inherited(name, repo)
            if ledger.created_by:
                print(f"  [{arm_name}] inherited {len(ledger.created_by)} "
                      f"skill(s) from earlier sessions; loads of these count "
                      f"as reuse", flush=True)
            else:
                print(f"  [{arm_name}] WARNING: reuse run, but nothing was "
                      f"inherited — there is no earlier learning to reuse",
                      flush=True)

        results: List[TaskResult] = []
        # Echo only when arms run serially; concurrent arms would interleave the
        # indented detail into unreadable soup. The file always gets everything.
        tracer = Tracer(arm_dir, arm_name, echo=not self.config.parallel_arms)

        planned = []
        for order, instance_id in enumerate(self.config.tasks):
            instance = self.instances.get(instance_id)
            if instance is None:
                prefix = f"[{arm_name}] " if self.config.parallel_arms else ""
                print(f"  {prefix}[{order:3d}] {instance_id}  SKIPPED (not in dataset)",
                      flush=True)
                continue
            if instance_id in carried:
                continue          # finished by the run this one continues
            planned.append((order, instance))

        # `--tasks-per-node` scales with the fleet; `--parallel-tasks` is a flat
        # number. The per-node form is the one that stays correct when nodes are
        # added, so it wins where both are given.
        per_node = int(getattr(self.config, "tasks_per_node", 0) or 0)
        if per_node > 0:
            width = per_node * max(1, len(self.nodes()))
        else:
            width = max(1, int(getattr(self.config, "parallel_tasks", 1) or 1))
        if width > 1:
            # Said once, at the top, because a number that is only in the
            # manifest is a number nobody reads before believing the report.
            print(f"  [{arm_name}] running {width} task(s) at once — reuse and "
                  f"learning-rate figures are NOT valid in this mode: a task "
                  f"that overlaps its predecessors cannot be said to have "
                  f"benefited from them", flush=True)

        # Appended the moment a task finishes, not when all of them do.
        #
        # Batching the writes to the end lost the property this file exists for:
        # a run killed at task 22 keeps 21 tasks of data rather than none.
        # Observed — five finished tasks, five evaluations on disk, and no
        # results.jsonl at all, so `status.sh` still called them "in flight" and
        # a kill would have thrown all five away.
        #
        # Order in the file is completion order when tasks overlap. That is
        # honest: with `--parallel-tasks` the sequence carries no learning
        # signal anyway, which is what the warning at the top of the run says.
        write_lock = threading.Lock()

        def one(job):
            order, instance = job
            # Stop before starting, not after finishing.
            #
            # A ceiling checked after the work is a report, not a control. This
            # is checked at the door of every task, so the overrun is bounded by
            # ONE task rather than by however many were still queued — measured
            # at $2.34 and 47 minutes for a single task with three tries, so the
            # difference between the two is the whole bill.
            over = self._over_budget()
            if over:
                result = TaskResult(instance_id=str(instance.get("instance_id", "")),
                                    repo=str(instance.get("repo", "")),
                                    arm=arm_name)
                result.stopped_early = over
                if tracer:
                    tracer.event("BUDGET", over)
                print(f"  [{order:3d}] {result.instance_id:38s} SKIPPED — {over}",
                      flush=True)
                return order, result

            result = self.run_task(arm, instance, order, store_root,
                                   arm_dir, ledger, tracer)
            with self._spend_lock:
                # `cost_total_usd`, never `cost_usd`: the latter is the solve
                # agent alone and research is the larger half — $0.70 of a $2.34
                # task. A ceiling fed the wrong one overshoots roughly 3x.
                self._spent_usd += float(result.cost_total_usd or 0.0)

            # The task's own result file, written by the only thread that owns
            # that directory. No lock, no shared file, nothing to interleave —
            # a task's result cannot be lost to another task's write because no
            # other task touches it.
            task_dir = arm_dir / "tasks" / f"{order:03d}-{result.instance_id}"
            try:
                task_dir.mkdir(parents=True, exist_ok=True)
                (task_dir / "result.json").write_text(
                    json.dumps(result.to_dict(), indent=2), encoding="utf-8")
            except (OSError, TypeError, ValueError):
                pass

            with write_lock:
                # The aggregate as well, because every reader and report is
                # written against it. Under a lock only because it is shared;
                # the per-task file above is the record that cannot be lost.
                append_result(results_path, result)
                label = f"[{arm_name}] " if self.config.parallel_arms else ""
                print(f"  {label}[{order:3d}] {result.instance_id:38s} "
                      f"{'PASS' if result.resolved else 'fail'} "
                      f"tries={result.tries} tok={result.tokens_total:,} "
                      f"new={len(result.skills_created)} "
                      f"reused={len(result.skills_reused)}"
                      f"(prior-run {len(result.skills_reused_prior_run)})",
                      flush=True)
            return order, result

        if width == 1:
            finished = [one(job) for job in planned]
        else:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(width, len(planned) or 1)) as pool:
                finished = list(pool.map(one, planned))

        # Kept in task order in memory for the report, whatever order they
        # finished in — the file is the durable record, this is the summary.
        for _, result in sorted(finished, key=lambda item: item[0]):
            results.append(result)

        # Let the background learner finish, then stop it.
        #
        # It has been draining what the stages reported for the whole arm. The
        # wait is bounded: a cycle mid-invocation is worth a minute of patience
        # and no more, because its observations are already on file and what an
        # abandoned cycle loses is one write-up rather than the input to it.
        try:
            left = arm.stop_learning()
            if left:
                print(f"  [{arm_name}] learner: {len(left)} final cycle(s)",
                      flush=True)
        except Exception:
            pass
        return results

    def run_task(self, arm: Arm, instance: Dict[str, Any], order: int,
                 store_root: Path, arm_dir: Path, ledger: Ledger,
                 tracer: Optional[Tracer] = None) -> TaskResult:
        # Which node this task's containers run on, for the life of the thread.
        self._local.runtime = self.runtime_for(order)
        # And its AGENTS, on that same node.
        #
        # They used to run wherever the harness did, which here is a shared
        # login node: measured at 12 tasks, 60 `claude` processes and a load
        # average of 10.8 on 48 cores while every allocated compute node sat at
        # 0.00. The allocation was being used for containers and nothing else,
        # and the ceiling on parallelism was a machine outside it that
        # seventeen other people were also using.
        #
        # The same node as the container on purpose: a task's reasoning and its
        # test runs then share a host, a page cache and a checkout.
        arm.agent_host = getattr(self._local.runtime, "host", "") or ""
        # And which backend its conversation belongs to. Set on the arm because
        # Claude Code takes its model from the environment rather than argv.
        try:
            arm.pinned_for_env = arm.model_for_task(instance)
        except Exception:
            arm.pinned_for_env = ""
        instance_id = instance["instance_id"]
        repo = instance.get("repo", "")
        result = TaskResult(instance_id=instance_id, repo=repo, arm=arm.name, order=order)

        workdir = arm_dir / "tasks" / f"{order:03d}-{instance_id}"
        workdir.mkdir(parents=True, exist_ok=True)
        before = store_inventory(store_root)
        retrieval_log = workdir / "retrievals.jsonl"
        retrieval_log.write_text("")

        # The record keeps itself, for as long as the task runs.
        #
        # Every phase pushes what it did and carries on; this folds several of
        # them per invocation on its own clock. That is what makes recording
        # amortised instead of a whole agent session charged to every phase —
        # which is what it was, and what made `track` 163 of one run's 241
        # stage kills.
        if getattr(arm, "uses_phronix", False):
            try:
                arm.start_tracking(instance, store_root, workdir,
                                   on_call=(lambda text: tracer.step("track", text))
                                   if tracer else None)
            except Exception as exc:      # a tracker that will not start is not a failed task
                if tracer:
                    tracer.event("track", f"could not start the record: {exc}")

        # Research runs ONCE per task, before any attempt.
        #
        # Before, not between: its purpose is to establish the approach, and an
        # approach decided after three attempts have already been spent is a
        # post-mortem. The gate inside is deterministic, so a task the catalogue
        # already covers costs one cheap lookup rather than a research pass.
        arm.retrieval_log = retrieval_log
        research_log: List[Dict[str, Any]] = []
        if tracer:
            # Every line this thread writes from here on names its task, which
            # is the difference between a readable trace and six interleaved
            # ones when tasks run concurrently.
            tracer.working_on(instance_id, workdir)
            tracer.task_start(order, instance_id)
            if not arm.full_retry_budget and self.config.max_tries > 1:
                tracer.event("budget", "1 attempt (this arm has no memory, so a "
                                       "retry would only be another sample)")

        # A plain baseline gets one attempt: with nothing carried between tries,
        # extra attempts measure sampling. The phronix arms — including the
        # frozen control — keep the full budget, so learning is compared against
        # the same number of attempts rather than against fewer.
        ceiling = self.config.max_tries if arm.full_retry_budget else 1
        #: Extra tries earned by getting FURTHER through the method.
        #
        # A fixed ceiling treats "failed at step 1 three times" and "failed at
        # step 1, then 3, then 5" as the same task, and stops both. The second is
        # converging, and one more try is the cheapest thing that could finish
        # it. Bounded, because a method with many steps could otherwise earn a
        # try per step forever.
        earned = 0
        MAX_EARNED = int(os.environ.get("PHRONIX_MAX_EARNED_TRIES", "2"))
        # Research budget is per TASK but spent inside attempts, so it lives on
        # the arm rather than as a local of either. One arm object per arm, and
        # tasks run in order within an arm, so this is safe with arms concurrent.
        arm.research_spent_s = 0.0
        arm.research_finalised = False
        stalls = 0
        isolation_failures = 0
        seen_patches: set = set()
        last_verdict: Optional[Dict[str, Any]] = None
        # How the FAILURE has moved, attempt to attempt. Progress is a changing
        # signature, not only a passing test.
        signatures: List[str] = []
        previous_verdict: Optional[Dict[str, Any]] = None

        attempt_index = 0
        while attempt_index < ceiling + earned:
            attempt_index += 1
            attempt = Attempt(index=attempt_index)
            started = time.time()
            skills_before = set(store_inventory(store_root).get("skills", []))
            arm.attempt_history = _attempt_history(workdir, attempt_index)

            try:
                attempt = self.run_attempt(arm, instance, attempt_index, store_root,
                                           workdir, retrieval_log, attempt,
                                           previous=last_verdict, tracer=tracer,
                                           research_log=research_log)
            except IsolationError as exc:
                attempt.error = f"isolation: {exc}"
                isolation_failures += 1
                # Move the task rather than retry into the same failure.
                here = getattr(self._local.runtime, "host", "") or ""
                self.note_bad_host(here, str(exc))
                moved = self.another_runtime(self._local.runtime)
                if moved is not None:
                    self._local.runtime = moved
                    arm.agent_host = getattr(moved, "host", "") or ""
                    if tracer:
                        tracer.event("nodes",
                                     f"container failed on {here or 'this node'}; "
                                     f"retrying on "
                                     f"{getattr(moved, 'host', '?')}")
                    # A try that never ran on a working node is not evidence
                    # about the environment, so it does not count toward the
                    # abort below.
                    isolation_failures -= 1
            except (ResearchCollapsed, EnvironmentGone):
                # Deliberately not swallowed: these are the failures that must
                # end the run rather than become rows in the results.
                raise
            except Exception as exc:  # a crashed attempt is data, not a dead run
                # The exception's OWN text, plus what the failed command
                # actually said.
                #
                # `CalledProcessError.__str__` gives the argv and the exit
                # status and drops stdout/stderr, so the trace recorded
                # `CalledProcessError: Command '['ssh', ...]' returned non-zero
                # exit status 1` — a hundred characters of argv and not one
                # word about the cause. Every such failure had to be
                # reproduced by hand to learn anything, and most never were.
                attempt.error = f"{type(exc).__name__}: {exc}"
                said = _error_tail(
                    (getattr(exc, "stderr", "") or "")
                    + (getattr(exc, "output", "") or ""), 300)
                if said:
                    attempt.error = f"{attempt.error} — {said}"
            attempt.wall_s = round(time.time() - started, 1)
            if attempt.steps or attempt.resolved:
                arm.tasks_without_environment = 0
            result.attempts.append(attempt)
            last_verdict = attempt.verdict
            signature = _failure_signature(attempt.verdict)
            if signature:
                same = signatures.count(signature)
                # Recorded on the attempt, not only fed back to the next one:
                # pass/fail cannot show the difference between a task closing in
                # and a task going in circles, and that difference is what says
                # whether more attempts are worth buying.
                attempt.same_failure_count = same + 1
                # The arm reads this when it diagnoses the next attempt: two
                # identical failures turn diagnosis from "what was missing" into
                # "what did both attempts assume".
                arm.same_failure_count = same + 1
                attempt.failure_trend = ("" if not signatures
                                         else "same" if same else "moved")
                signatures.append(signature)
                # Handed forward on the verdict, so the next attempt's feedback
                # can say whether anything moved.
                if last_verdict is not None:
                    last_verdict = dict(last_verdict)
                    last_verdict["same_failure_count"] = same + 1
                    last_verdict["failure_moved"] = bool(signatures[:-1]) and same == 0
                if tracer:
                    if same == 0 and len(signatures) > 1:
                        tracer.event("progress",
                                     f"try {attempt_index} failed DIFFERENTLY "
                                     "from the last one — the change had an "
                                     "effect; worth another attempt")
                    elif same >= 1:
                        tracer.event("no-progress",
                                     f"try {attempt_index} failed exactly as "
                                     f"try {attempt_index - 1 - same} did "
                                     f"({same + 1}x identical) — the approach "
                                     "has to change, not the details")
            if tracer and attempt.error:
                # An attempt that raised reports 0 steps and 0 tokens, which is
                # indistinguishable from an agent that ran and did nothing. The
                # exception is the whole explanation, and it was previously only
                # readable in results.jsonl once the task finished.
                tracer.event("ERROR", f"try {attempt_index}: {attempt.error[:200]}")
            if tracer:
                history = _attempt_history(workdir, attempt_index + 1)
                touched = history[-1]["files"] if history else []
                tracer.attempt(attempt_index, touched, attempt.verdict or {},
                               attempt.steps, attempt.tokens_total,
                               previous=previous_verdict)
                # Recorded on the attempt, not only traced.
                #
                # A phronix attempt that calls no phronix tools is a plain
                # agent wearing phronix's name, and it scored identically to
                # one that used its memory — the difference lived in a trace
                # line nobody aggregates. Research already treats zero calls as
                # fatal for exactly this reason; an attempt is the same state.
                # The evaluation's turn joins the task's conversation, so the
                # next attempt inherits what was changed and what the tests
                # said rather than starting from the issue again.
                # Subject and store, so the conversation is kept by AREA and
                # outlives this task — two bugs in one area are worked by
                # different tasks, often in the same run.
                arm.conversation_subject = getattr(
                    arm, "research_topic_binding", "") or instance_id
                arm.conversation_root = Path(store_root) / ".phronix"
                try:
                    arm.record_verdict(
                        workdir, f"evaluation of attempt {attempt_index}",
                        # The patch lives on the OUTCOME, not the attempt.
                        #
                        # `Attempt` has no `patch` field, so this raised
                        # AttributeError every single time — every evaluation
                        # turn was missing from every task conversation in
                        # every run, and the only sign was one trace line.
                        # The conversation is what the next attempt inherits,
                        # so this cost each retry the record of what the last
                        # one changed and what the tests said about it.
                        verdict=attempt.verdict,
                        patch=_patch_text(workdir / f"attempt-{attempt_index}"),
                        skill=getattr(arm, "pinned_skill", ""),
                        subject_dir=arm.subject_dir(
                            workdir / f"attempt-{attempt_index}"))
                except Exception as exc:     # bookkeeping never fails a task
                    # Reported, not swallowed.
                    #
                    # A bare `pass` here hid an `AttributeError` for a whole
                    # run: every evaluation turn was silently missing, the
                    # conversations held one turn each instead of two, and
                    # nothing said so. Bookkeeping must not fail a task — but
                    # it must not fail invisibly either, because the thing it
                    # records is what the next attempt reads.
                    if tracer:
                        tracer.event("conversation-unrecorded",
                                     f"could not add the evaluation turn: "
                                     f"{type(exc).__name__}: {exc}")
                attempt.phronix_calls = tracer.tools(
                    f"attempt-{attempt_index}",
                    workdir / f"attempt-{attempt_index}" / "opencode.jsonl") or 0
                tracer.tools(f"learn-{attempt_index}",
                             workdir / f"attempt-{attempt_index}" / "learn.jsonl")
                # The alarm is for an attempt that WORKED without the
                # framework, not for one that did nothing at all.
                #
                # "A plain agent result under a phronix label" is a real and
                # serious state: the arm ran, produced a patch, and never
                # consulted what it knows, so its number is not a phronix
                # number. But an attempt that produced no patch did not reach
                # that state — it failed before there was anything to record,
                # and on a fresh task `search-skill` has already said there is
                # nothing to retrieve.
                #
                # Raising it anyway turned one model failure into two
                # findings, one of them pointing at this repository: measured
                # on a 30-task run, 11 of 11 "phronix unused" reports came
                # from attempts that produced no patch, and they were the only
                # pipeline faults the run had.
                # `_patch_text`, not `attempt.patch`: `Attempt` has no such
                # field, and reading it raised AttributeError on every
                # evaluation turn of every run before it was noticed.
                produced = bool(_patch_text(
                    workdir / f"attempt-{attempt_index}").strip())
                if arm.uses_phronix and not attempt.phronix_calls and produced:
                    tracer.event("tools", "** this attempt used NO phronix "
                                          "tools — it is a plain agent result "
                                          "under a phronix label")
            # Carried outside the tracer block: the comparison must hold even
            # when tracing is off.
            previous_verdict = attempt.verdict or previous_verdict
            if attempt.resolved:
                break

            # A runner that never started cannot be fixed by trying again.
            #
            # sympy-24066 spent three attempts and $1.94 against tests that
            # never ran once: the verdict said "target 0/1, 30 regressions",
            # which is indistinguishable from a bad patch, so every retry
            # dutifully produced another patch for a test suite that could not
            # execute. All three diffs came out byte-identical.
            if (attempt.verdict or {}).get("runner_failed"):
                # ... UNLESS the attempt's own patch is what stopped it.
                #
                # The two are indistinguishable in the verdict and opposite in
                # meaning. A stray `+` in `pylint/lint/__init__.py` is a
                # SyntaxError, so conftest cannot import and no test runs — and
                # that is not a harness fault, it is the clearest possible
                # failed attempt ("your patch does not import"), the one case a
                # retry reliably fixes. Aborting it threw the task away after
                # try 1. Measured: 3 of 16 tasks in one run, every one of them
                # self-inflicted, all three aborted as "environment".
                #
                # Told apart by asking whether the file the traceback names is
                # one this attempt changed. No extra container work, and right
                # on every case seen.
                error = (attempt.verdict or {}).get("error", "")
                touched = _patch_files(
                    _patch_text(workdir / f"attempt-{attempt_index}"))
                blamed = _blames_patch(error, touched)
                if blamed:
                    # Recorded so the retry is told what to fix. Without this
                    # the next attempt inherits "0/N target tests" and no hint
                    # that the suite never ran, which is how a retry rewrites
                    # the same broken edit.
                    attempt.verdict["runner_failed"] = False
                    attempt.verdict["broke_testbed"] = blamed
                    attempt.verdict["failure_detail"] = (
                        f"the patch broke {blamed}, so the test suite could not "
                        f"even be imported and NOTHING ran: {error}")
                    if tracer:
                        tracer.event(
                            "self-inflicted",
                            f"the patch broke {blamed} — the suite could not be "
                            f"imported, so this is a failed attempt and not a "
                            f"harness fault; retrying")
                else:
                    result.stopped_early = (
                        f"the test runner never started, so no attempt at this "
                        f"task can be judged: "
                        f"{(attempt.verdict or {}).get('error', '')[:160]}")
                    if tracer:
                        tracer.event("ABORT", result.stopped_early)
                    break

            # Repeated isolation failures mean the environment is gone, not that
            # the task is hard. Retrying spends the whole ceiling producing
            # identical empty attempts and buries the real cause.
            if isolation_failures >= 2:
                result.stopped_early = (
                    f"environment unavailable after {isolation_failures} attempts: "
                    f"{(attempt.error or '')[:160]}")
                if tracer:
                    tracer.event("ABORT", result.stopped_early)
                arm.tasks_without_environment = (
                    getattr(arm, "tasks_without_environment", 0) + 1)
                break

            if not self.config.until_pass:
                continue

            # Stall detection, only in until-pass mode.
            #
            # "Retry until it passes" has to stop somewhere that is not just a
            # ceiling: a task where every attempt produces the identical patch
            # cannot converge, it only spends tokens.
            #
            # The condition is **repeated patch alone**, deliberately. It used to
            # also require "and learned nothing new", which made the rule measure
            # different things in different arms: an arm with no learning
            # mechanism satisfies "learned nothing" on every attempt, so it
            # stalled on the first repeat, while the learning arm could repeat a
            # patch indefinitely as long as its learner kept writing. Observed
            # live: bare wandered across four patches and used all 6 attempts,
            # phronix emitted one patch and was cut at 3 — the same rule handing
            # out unequal attempt budgets based on which arm it was applied to.
            # A benchmark cannot compare "tries" across arms whose stopping rule
            # depends on a capability only one of them has.
            patch_text = _read_patch(workdir, attempt_index)
            patch_digest = _digest(patch_text)
            # An attempt that never ran is not a repetition.
            #
            # On sympy-21847 the provider returned 429 "Max budget: 500.0" three
            # times running. Each attempt did one step, produced no patch, and
            # hashed to the same empty digest — so the stall detector saw two
            # identical patches and ended a task that had had exactly two real
            # attempts. Infrastructure failure was recorded as the agent going
            # in circles, which is the one conclusion the data did not support.
            never_ran = bool(attempt.error) and not (attempt.steps or patch_text.strip())
            if never_ran:
                if tracer:
                    tracer.event("attempt-void",
                                 f"try {attempt_index} did not run "
                                 f"({attempt.error[:80]}); not counted as a stall")
                continue

            repeated = patch_digest in seen_patches
            seen_patches.add(patch_digest)

            # A failure that keeps changing is a task still converging, and
            # cutting it off at the ceiling throws away the attempt most likely
            # to land. A failure that repeats identically is the opposite: more
            # attempts of the same kind cannot help.
            moved = len(signatures) > 1 and signatures[-1] != signatures[-2]
            if moved and ceiling < self.config.max_tries + EXTRA_TRIES_WHEN_MOVING:
                ceiling += 1
                if tracer:
                    tracer.event("budget",
                                 f"the failure moved, so try {ceiling} is "
                                 "allowed — progress buys an attempt")
            if len(signatures) >= 2 and signatures[-1] == signatures[-2]:
                # Identical twice is the pivot signal, whatever the patch says.
                stalls += 1

            if repeated:
                stalls += 1
                if stalls >= self.config.stall_limit:
                    result.stopped_early = (
                        f"stalled after {attempt_index} attempts: the last "
                        f"{stalls} repeated a previously-seen patch")
                    break
            else:
                stalls = 0
        else:
            if self.config.until_pass and not result.resolved:
                result.stopped_early = f"hit the {ceiling}-attempt ceiling"

        # The task is over. Turn what it learned into something that outlives it.
        #
        # The tracker is per task and dies with it — that isolation is the
        # point, because an established fact from one task is an assumption in
        # another. So the last act of a task is to snapshot the record into a
        # skill: what was established, what remained open, what was ruled out.
        #
        # Written whether the task passed or not. A task that failed after four
        # attempts knows more about its subject than one that passed on the
        # first, and throwing that away is why a later run on the same subject
        # starts from nothing.
        if (str(getattr(self.config, "pipeline", "sequential")).lower()
                != "parallel" and getattr(arm, "uses_phronix", False)):
            # The record, brought up to date and the tracker stopped.
            #
            # Before the learn stages, because they READ it: the snapshot is
            # the one moment the record crosses out of the task, and folding
            # after that would write into a record nothing will read again.
            try:
                arm.stop_tracking(workdir, instance=instance,
                                  store_root=store_root,
                                  on_call=(lambda text: tracer.step("track", text))
                                  if tracer else None)
            except Exception as exc:      # a tracker that fails is not a failed task
                if tracer:
                    tracer.event("track", f"could not close the record: {exc}")

            # `tracer.step`, not `_say` — which is a CLOSURE INSIDE
            # `run_attempt` and has never been in scope here. Both calls
            # therefore raised `NameError` on the first line of the `try` and
            # were swallowed as "could not snapshot the record", so the skill
            # a task leaves behind for the next run was never written: not on a
            # pass, not on a failure, not once. The trace said so every time
            # and read like a snapshot that had been attempted.
            def _learn(text: str) -> None:
                tracer.step("learn", text)

            try:
                arm.ensure_task_skill(
                    instance, store_root, workdir,
                    on_call=_learn if tracer else None)
                arm.snapshot_tracker(
                    instance, store_root, workdir,
                    resolved=bool((last_verdict or {}).get("resolved")),
                    on_call=_learn if tracer else None)
            except Exception as exc:      # a snapshot that fails is not a failed task
                if tracer:
                    tracer.event("learn", f"could not snapshot the record: {exc}")

        # Two tasks in a row with no container is the host, not the tasks.
        #
        # Each one costs two attempts to discover, and every row after it reads
        # as a result: `fail`, 0 steps, 0 tokens. One of those rows had a patch
        # in it that was never judged, which is worse than a missing row because
        # it looks like a measured failure of the arm.
        if getattr(arm, "tasks_without_environment", 0) >= 2:
            raise EnvironmentGone(
                f"{arm.name}: no container could be started for "
                f"{arm.tasks_without_environment} consecutive tasks. "
                f"Last error: {(last_verdict or {}).get('error') or ''}"
                f"{result.stopped_early}\n"
                f"Check the allocation is still running (`flux jobs`) and "
                f"relaunch with --node pointing at a live one.")

        # A task that PASSED marks its approach working.
        #
        # Failures are marked per attempt, as they happen, because the next
        # research pass inside the same task has to see them — see the note in
        # `run_attempt`. Doing it only here would also mark the wrong approach:
        # by the end of the task the burned candidate has already been replaced
        # at the top of the ranking by one nothing has tried.
        if arm.uses_phronix and not arm.store_readonly and result.resolved:
            topic = getattr(arm, "research_topic_binding", "")
            # Which plans solved it, when the winning attempt raced several.
            #
            # Without the names this called `attempted_approach`, which reads
            # the ranking — and on a pass whose candidates came from the ideas
            # rather than from recorded approaches there is no ranking, so a
            # task that had just been solved twice over reported "no approach
            # was followed". Measured on pylint-7080: two plans SOLVED it, one
            # failed, and only the failure reached the ledger.
            winners = [t["plan"] for t in
                       ((result.attempts or [])[-1].trials or [])
                       if t.get("resolved") and t.get("plan")]
            if topic and winners:
                for plan in winners:
                    self._mark_outcome(
                        arm, store_root, topic, worked=True, approach=plan,
                        why=(f"solved the task in {result.tries} attempt(s), "
                             f"tried against the target tests"), tracer=tracer)
            elif topic:
                self._mark_outcome(arm, store_root, topic, worked=True,
                                   why=f"passed in {result.tries} attempt(s)",
                                   tracer=tracer)

        if research_log:
            result.research = dict(research_log[-1])
            result.research["passes"] = len(research_log)
            # Every pass, not just the last: revisions are part of the cost.
            result.research["passes_detail"] = [
                {k: p.get(k) for k in ("attempt", "kind", "elapsed_s", "steps",
                                       "tokens_input", "tokens_output",
                                       "tokens_cache", "stage_seconds_total",
                                       "truncated_stages", "failed_stages",
                                       "stage_detail")}
                for p in research_log]
            (workdir / "research.json").write_text(
                json.dumps(research_log, indent=2))

        after = store_inventory(store_root)
        created = self._diff_created(
            before, after, str(instance.get("instance_id", "")))
        result.skills_created = created
        for name in created:
            ledger.record_creation(name, order, repo)

        if tracer:
            tracer.learned(created, store_root)
            tracer.retrievals(retrieval_log)

        retrieved = read_retrievals(retrieval_log)
        result.skills_retrieved = retrieved
        classified = ledger.classify(retrieved, order, repo)
        result.skills_reused = classified["reused"]
        result.skills_reused_cross_repo = classified["cross_repo"]
        result.skills_reused_prior_run = classified["inherited"]

        if arm.uses_phronix and not arm.store_readonly:
            snapshot_store(store_root, workdir / "store-after")

            # Promote after every task, not at the end of the run. A run that is
            # killed — and several have been — would otherwise contribute
            # nothing, which is precisely when the research it did is most worth
            # keeping. The frozen control is excluded: it is a control.
            # Promotion is bookkeeping, and bookkeeping must never lose a task.
            #
            # It did: an attribute that does not exist on TaskResult raised here,
            # the exception escaped to the per-ARM handler, and the phronix arm
            # died at task 0 — throwing away a task it had just PASSED, plus the
            # five it had not started. The bare arm ran to completion beside it,
            # so the run produced a report showing one arm at 1/6 and the other
            # at 0/6, which reads as a result rather than as a crash.
            if self.config.carry_root:
                # Fold FIRST, then promote. The order is load-bearing.
                #
                # `promote_store` skips `research/sessions/` by design, on the
                # understanding that the fold has already moved those records
                # into the run store's common `research/` folder. Promoting
                # before folding carries a folder this task has not been written
                # into yet, so its research is left behind by exactly one step —
                # which is what happened to every run so far.
                #
                # Sync after every task, not only at the end of the run.
                # Whatever this task learned is durable the moment it is learned;
                # holding it in the session folder until the run finishes means a
                # run that is killed — and several have been — contributes
                # nothing, which is exactly when its findings matter most. It
                # also lets task N+1 of a reusing run start from task N's work
                # through the common folder rather than only through the session.
                # Did this try get FURTHER through the method than any before?
                #
                # That is the progress signal a failing task otherwise has none
                # of: "0 target tests passing" reads the same on try 1 and try 3,
                # while failing at step 2 and then at step 4 is a task closing in.
                if arm.uses_phronix and not result.resolved and earned < MAX_EARNED:
                    try:
                        from phronix import research as _research

                        # Through the ARM's store helper: the record lives in
                        # the run's own layer, and reading it from anywhere else
                        # finds the project layer instead.
                        got = arm._in_store(store_root, _research.furthest_step,
                                            arm.research_topic(instance))
                        if (got or {}).get("advanced"):
                            earned += 1
                            if tracer:
                                tracer.event(
                                    "earned-try",
                                    f"reached step {got.get('furthest', 0) + 1} "
                                    f"of {got.get('of', 0)} — further than any "
                                    f"earlier try, so this task gets another")
                    except Exception:
                        pass    # a progress bonus must never break the task

                self._sync_research_session(quiet=True, store_root=store_root)
                # Into the SOURCE tree, always — `--fresh` and `--no-carry`
                # included. The project layer is gitignored, so everything a
                # run learned lived exactly as long as its checkout and a clone
                # started from nothing. `--fresh` is unaffected: it filters on
                # READ, keeping the framework's own tools and hiding bundled
                # task answers, so a from-scratch run still starts clean.
                try:
                    into_src = promote_to_source(store_root)
                    if into_src.get("promoted") and tracer:
                        tracer.event("promoted",
                                     f"{len(into_src['promoted'])} file(s) into "
                                     f"{into_src.get('destination', 'the source tree')}")
                except Exception as exc:
                    if tracer:
                        tracer.event("promote-failed", f"source tree: {exc}"[:200])
                try:
                    promoted = promote_store(store_root,
                                             Path(self.config.carry_root))
                    result.promoted = promoted["promoted"]
                    if promoted["promoted"] and tracer:
                        tracer.event("promoted",
                                     f"{len(promoted['promoted'])} file(s) into "
                                     f"{self.config.carry_root}")
                except Exception as exc:
                    if tracer:
                        tracer.event("promote-failed", str(exc)[:200])
        return result

    def trial_runner(self, arm, instance, store_root, attempt_dir,
                     baseline_for, tracer=None, narrate=None):
        """A callable research can use to put ONE candidate in front of the tests.

        This is the seam between research and evaluation, and it exists because
        the two used to be strictly sequential: research ran to completion, the
        runner then raced every candidate it had produced, and only then did
        anyone learn whether any of them worked. So a pass kept generating and
        combining ideas long after one of them had already solved the task, and
        an idea recorded in the first minute was not tested for another hour.

        Handing research a way to trial a candidate lets it act on the only
        judge that counts — the task's own target tests — while it is still
        working: test each idea as its solution is written, combine the ones
        that are in, and stop generating once something passes.

        Returns ``{"plan", "resolved", "target_tests_passed", "outcome",
        "verdict", "error"}``. It never raises: a trial that cannot run is one
        candidate lost, not the pass.
        """
        counter = itertools.count(1)

        def trial(plan: Dict[str, Any]) -> Dict[str, Any]:
            index = next(counter)
            name = str(plan.get("name") or f"candidate-{index}")
            work = attempt_dir / f"trial-{index}-{_slug(name)}"
            work.mkdir(parents=True, exist_ok=True)
            say = ((lambda text: narrate(f"[{name}] {text}"))
                   if narrate else None)
            try:
                with baseline_for(arm.mounts(store_root)) as container:
                    got = arm.generate(instance, store_root, work, container,
                                       on_call=say, plan=plan)
                    (work / "patch.diff").write_text(got.patch or "")
                    base = baseline_failures(container, instance,
                                             timeout_s=self.config.timeout_s)
                    verdict = evaluate(
                        container, instance, got.patch,
                        known_failures=base.get("pre_existing_failures"))
            except Exception as exc:            # one candidate, not the pass
                return {"plan": name, "resolved": False,
                        "target_tests_passed": 0, "outcome": None,
                        "verdict": {}, "error": str(exc)[:200]}
            passed = int(verdict.get("fail_to_pass_passed") or 0)
            resolved = bool(verdict.get("resolved"))
            if tracer:
                tracer.event("trial",
                             f"{name}: {'SOLVED' if resolved else 'failed'} "
                             f"({passed} target test(s) passing)")
            return {"plan": name, "resolved": resolved,
                    "target_tests_passed": passed, "outcome": got,
                    "verdict": verdict, "error": ""}

        return trial

    def _race_plans(self, arm, instance, store_root, attempt_dir, plans,
                    baseline_for, tracer=None, narrate=None):
        """Attempt every plan concurrently; return the best patch and the scores.

        "Best" is measured against the task's own target tests, which is the
        only judge that counts: a plan that makes two of them pass beats one
        that makes none, whatever the research metric said about it.

        Each trial gets its own container and its own working directory, so they
        cannot see or disturb each other's edits.
        """
        from .isolation import ContainerSession

        results: List[Dict[str, Any]] = []
        lock = threading.Lock()

        def try_plan(job):
            index, plan = job
            work = attempt_dir / f"trial-{index}-{_slug(plan['name'])}"
            work.mkdir(parents=True, exist_ok=True)
            say = ((lambda text: narrate(f"[{plan['name']}] {text}"))
                   if narrate else None)
            try:
                with baseline_for(arm.mounts(store_root)) as trial_container:
                    got = arm.generate(instance, store_root, work,
                                       trial_container, on_call=say, plan=plan)
                    (work / "patch.diff").write_text(got.patch or "")
                    # `baseline_failures`, which is what the function is
                    # called. `measure_baseline` never existed — this whole
                    # path would have raised NameError the first time a run
                    # used parallel candidates, and it was only ever exercised
                    # structurally.
                    base = baseline_failures(trial_container, instance,
                                             timeout_s=self.config.timeout_s)
                    verdict = evaluate(
                        trial_container, instance, got.patch,
                        known_failures=base.get("pre_existing_failures"))
            except Exception as exc:                       # one trial, not all
                with lock:
                    results.append({"plan": plan["name"], "error": str(exc)[:200],
                                    "score": (-1, 0), "outcome": None})
                return
            score = (int(verdict.get("fail_to_pass_passed") or 0),
                     int(verdict.get("pass_to_pass_passed") or 0))
            with lock:
                results.append({"plan": plan["name"], "outcome": got,
                                "verdict": verdict, "score": score,
                                "resolved": bool(verdict.get("resolved"))})
            if tracer:
                tracer.event("trial",
                             f"{plan['name']}: "
                             f"{'SOLVED' if verdict.get('resolved') else 'failed'} "
                             f"({score[0]} target test(s) passing)")

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=len(plans)) as pool:
            list(pool.map(try_plan, list(enumerate(plans, 1))))

        ranked = sorted(results, key=lambda r: r["score"], reverse=True)
        winner = next((r for r in ranked if r.get("outcome") is not None), None)
        if tracer:
            summary = ", ".join(f"{r['plan']}={r['score'][0]}" for r in ranked)
            solved = [r["plan"] for r in ranked if r.get("resolved")]
            tracer.event("trials",
                         f"{len(plans)} plan(s) tried: {summary}"
                         + (f" — SOLVED by {', '.join(solved)}" if solved
                            else " — none solved it; taking the furthest"))
        trials = [{"plan": r["plan"], "target_tests_passed": r["score"][0],
                   "resolved": bool(r.get("resolved")),
                   "error": r.get("error", "")} for r in ranked]
        if winner is None:
            return AttemptOutcome(error="every plan trial failed to run"), trials
        return winner["outcome"], trials


    @staticmethod
    def _trace_skill_use(tracer, attempt, retrieval_log: Path,
                         before: set, attempt_index: int) -> None:
        """Record whether the attempt loaded the skill it was given.

        Reported for BOTH outcomes, because the silent case is the one that
        matters: a skill that is written, found, handed over and then never
        opened is indistinguishable in the results from one that was used, and
        the run reads as though the store worked.
        """
        wanted = getattr(attempt, "recalled_skill", "") or ""
        if not wanted or tracer is None:
            return
        # Read from the attempt's own TRANSCRIPT, not the retrieval log.
        #
        # `retrievals.jsonl` records only what the harness-run stages loaded —
        # measured, it held `phronix-task-tracker` and
        # `phronix-learning-reconcile` and nothing from the attempt at all,
        # empty for two of three tasks. The attempt agent's `skill_load` never
        # reaches it, so reading it there reported "never loaded it" for
        # attempts whose trace plainly said `skill load: <name>` — a false
        # negative on the one question this event exists to answer.
        loaded = [name for name in read_retrievals(retrieval_log)
                  if name not in before]
        attempt.skill_loaded = wanted in loaded or _transcript_loaded(
            Path(retrieval_log).parent, attempt.index, wanted)
        if attempt.skill_loaded:
            tracer.event("skill-use",
                         f"try {attempt_index}: loaded `{wanted}` and worked "
                         f"from it",
                         data={"skill": wanted, "loaded": True})
        else:
            tracer.event("skill-use",
                         f"try {attempt_index}: ** was given `{wanted}` and "
                         f"never loaded it",
                         ["the store answered and the attempt solved from "
                          "scratch anyway — this scores as phronix and is not"],
                         data={"skill": wanted, "loaded": False,
                               "loaded_instead": loaded[:4]})

    def run_attempt(self, arm: Arm, instance: Dict[str, Any], attempt_index: int,
                    store_root: Path, workdir: Path, retrieval_log: Path,
                    attempt: Attempt,
                    previous: Optional[Dict[str, Any]] = None,
                    tracer: Optional[Tracer] = None,
                    research_log: Optional[List[Dict[str, Any]]] = None) -> Attempt:
        """Run one attempt.

        ``research_log`` is passed in rather than held on the Runner. It used to
        be an attribute, and with arms running concurrently that made it shared
        mutable state: whichever arm started a task last owned the list, and the
        other arm's research records were appended to it. The visible result was
        the *baseline* reporting 88k research tokens and a research.json full of
        the phronix arm's tool calls — a contamination that made the arm look
        like it was doing something it cannot do.
        """
        if self.runtime is None:
            raise IsolationError("worktree isolation is not implemented; use podman")

        attempt_dir = workdir / f"attempt-{attempt_index}"
        attempt_dir.mkdir(parents=True, exist_ok=True)

        # Carry the task binding into whatever thread narrates.
        #
        # `working_on` is thread-local, and stages that fan out run in pool
        # threads which inherit nothing — so their lines arrived with no task
        # name and reached only the arm log. Every per-task trace was missing
        # exactly the work that had been parallelised.
        #
        # Defined at method scope rather than inside the branch that first
        # needed it: a helper that exists only when one conditional ran is a
        # NameError waiting for the run where it does not.
        bound = tracer.binding() if tracer else None

        def _say(phase: str, text: str) -> None:
            if bound is not None:
                tracer.adopt(bound)
            tracer.step(phase, text)

        # Every line of an attempt — its own commentary AND the evaluation that
        # judges it — carries the skill it is working from, not just the line
        # that announced it.
        #
        # The opening `attempt>solution-...>` scrolls away in seconds and the
        # two hundred lines after it read `attempt>`, so the one question the
        # trace is watched for — is this solving from a stored skill or from
        # scratch — was answerable only by scrolling back. `[stage]` is the
        # prefix research already uses and the tracer lifts it into the label
        # column.
        #
        # The skill is read when the line is WRITTEN, not when this closure is
        # made: the baseline narrator is wired up before the lookup has run, and
        # a default argument would freeze it empty for the whole attempt.
        #
        # A text that already opens with a bracket is left alone — a raced plan
        # labels its own lines, and two prefixes push the message out of column.
        def _labelled(phase: str, text: str) -> None:
            text = str(text)
            skill = getattr(attempt, "recalled_skill", "")
            if skill and not text.lstrip().startswith("["):
                text = f"[{skill}] {text}"
            _say(phase, text)
        # Carried on the arm, not through os.environ. With arms running
        # concurrently, a process-global variable would be overwritten by
        # whichever arm started its task last, and both arms' retrievals — the
        # input to the reuse metric — would be attributed to one of them.
        arm.retrieval_log = retrieval_log

        # Tell this attempt why the last one failed.
        #
        # Written for EVERY arm, not just the phronix ones. Test feedback is
        # information the task itself produces, not scaffolding one arm brings —
        # withholding it from the baseline would make the comparison flattering
        # rather than informative. What still differs is memory: phronix also
        # carries a written lesson into later *tasks*, where the baseline starts
        # from nothing every time.
        if previous is not None and not previous.get("resolved"):
            previous = dict(previous)
            previous["attempt_history"] = getattr(arm, "attempt_history", []) or []
            (attempt_dir / "feedback.md").write_text(
                _feedback_note(attempt_index, previous), encoding="utf-8")

        def session(mounts: Optional[Dict[Path, str]] = None) -> ContainerSession:
            # The wheelhouse rides along read-only in every container, so a
            # testbed missing pytest can be repaired without the network.
            combined = dict(mounts or {})
            wheels = Path(self.config.data_root or ".") / "wheels"
            if wheels.is_dir():
                combined[wheels] = "/wheels:ro"
            return ContainerSession(
                self.runtime, instance["instance_id"], attempt_index,
                image_template=self.config.image_template or DEFAULT_IMAGE_TEMPLATE,
                pull=self.config.pull, mounts=combined, label=arm.name)

        # -- generate ------------------------------------------------------
        # Arms that bring their own sandbox are not handed one: nesting our
        # container inside mini's would measure our harness, not the reference
        # agent as its authors run it.
        if arm.generates_own_environment:
            outcome = arm.generate(instance, store_root, attempt_dir, container=None)
        else:
            with session(arm.mounts(store_root)) as container:
                # Research runs BEFORE the attempt but INSIDE the session: it
                # needs the code, and the code only exists once the container's
                # /testbed has been exported. Research before every attempt —
                # the plan for the first, a revision of it for each retry, since
                # a plan a test run has just falsified is the thing most in need
                # of revising, and one bounded pass is cheaper than another
                # attempt against the same wrong approach.
                if tracer:
                    tracer.begin("checkout",
                                 f"exporting /testbed for attempt {attempt_index}")
                arm.prepare_checkout(container, store_root, attempt_dir)
                # The whole exchange, not the harness's digest of it.
                #
                # `attempt-notes.md` is a summary the harness wrote, choosing
                # what it guessed research would need — a component with no way
                # to tell which half-sentence in the transcript was the clue.
                # `exchange.md` is what was asked, what was said, what changed
                # and how it was judged, and the plan stage summarises it
                # itself. Falls back to the digest where an older attempt wrote
                # no exchange.
                previous = workdir / f"attempt-{attempt_index - 1}"
                notes = None
                if attempt_index > 1:
                    exchange = previous / "exchange.md"
                    notes = (exchange if exchange.is_file()
                             else previous / "attempt-notes.md")
                # Research on retry only, when asked for.
                #
                # By default research runs before every attempt, including the
                # first — so a phronix pass and a bare pass differ from the
                # opening move, and any difference in the result includes the
                # cost and benefit of research the bare arm never had.
                #
                # This mode holds it back: attempt one is the same first move
                # both arms make, and research happens only after that attempt
                # has actually failed. What it then measures is narrower and
                # more honest — not "is phronix better", but "does research
                # recover a task that a plain attempt just lost".
                # Try what we already know FIRST; research is what happens
                # when that fails.
                #
                # Research used to run before every attempt including the first,
                # so a task the store already held the answer to paid for a full
                # plan-explore-build pass before anything looked at the answer.
                # Measured on pylint-7080: the merged solution skill and all
                # three candidates were seeded into the store, and the run
                # opened with `plan` exactly as it had on the cold task.
                #
                # The order now is: whatever the store has for this task, then a
                # plain attempt, and only then research. `--research-first`
                # restores the old shape for a comparison that needs it.
                skip = (attempt_index <= 1
                        and not getattr(self.config, "research_first", False))
                if tracer and not skip and getattr(arm, "research_agent_name", ""):
                    tracer.begin("research",
                                 f"{'initial' if attempt_index <= 1 else 'revision'} "
                                 f"pass for try {attempt_index}",
                                 getattr(arm, "research_timeout_s", None))
                narrate = ((lambda text: _say("research", text))
                           if tracer else None)
                # Research gets a way to TEST what it produces, while it is
                # still producing. See `trial_runner`: without it a pass keeps
                # generating and combining ideas long after one of them has
                # already solved the task, because nothing tells it.
                #
                # Only when candidates are being raced. With a single merged
                # attempt (`attempt_candidates == 1`) there is no per-idea
                # candidate to trial and the old sequence is exactly right.
                trial = None
                if int(getattr(self.config, "attempt_candidates", 1) or 0) != 1:
                    trial = self.trial_runner(
                        arm, instance, store_root, attempt_dir,
                        baseline_for=session, tracer=tracer, narrate=narrate)
                tracked = str(getattr(self.config, "pipeline", "sequential")
                              ).lower() != "parallel"
                if skip:
                    research = None
                elif tracked and getattr(arm, "uses_phronix", False):
                    # The tracked loop: one subject, taken from this task's own
                    # record. No plan, no fan-out, no candidates — the record
                    # says what is open and the pass fixes that.
                    research = arm.research_from_tracker(
                        instance, store_root, attempt_dir,
                        attempt_index=attempt_index, on_call=narrate)
                    attempt.stages.append({
                        "name": "research",
                        "steps": int((research or {}).get("steps") or 0),
                        "tokens_output": int((research or {}).get("tokens_total") or 0),
                        "elapsed_s": float((research or {}).get("stage_seconds_total") or 0),
                        "note": (research or {}).get("answer", "")[:40],
                    })
                    # The diagnosis is worth nothing under a name nothing
                    # reads: check before the next attempt looks it up.
                    try:
                        arm.ensure_task_skill(
                            instance, store_root, attempt_dir,
                            on_call=narrate)
                    except Exception as exc:
                        if tracer:
                            tracer.event("skill", f"could not re-file: {exc}")
                    # And record what research itself concluded. Every stage
                    # goes into the record, or the next pass cannot see that a
                    # diagnosis has already been made and rejected.
                    try:
                        # What research actually produced, or the tracker is
                        # recording a stage it cannot see. It had no evidence
                        # at all here: the report it wrote and the skill it
                        # updated are the whole output of the pass, and both
                        # were being withheld from the one agent whose job is
                        # to write down what happened.
                        seen = [Path(p) for p in
                                ((research or {}).get("report", ""),
                                 arm.solution_skill_path(
                                     store_root, arm.research_topic(instance)))
                                if p]
                        arm.track(instance, store_root, attempt_dir,
                                  phase="research",
                                  cost=f"try {attempt_index}, "
                                       f"{(research or {}).get('stage_seconds_total', '?')}s "
                                       f"of {(research or {}).get('budget_s', '?')}s",
                                  evidence=[p for p in seen if p.is_file()],
                                  on_call=((lambda text: _say("track", text))
                                           if tracer else None))
                    except Exception as exc:
                        if tracer:
                            tracer.event("track",
                                         f"could not record the research: {exc}")
                else:
                    research = arm.research(
                        instance, store_root, attempt_dir,
                        attempt_index=attempt_index, notes=notes,
                        on_call=narrate, trial=trial)
                # Research that did nothing at all is catastrophic, not a bad
                # result. Zero tool calls means the agent never started: a bad
                # command, a dead endpoint, a missing binary. A research pass
                # that ran and concluded little is a different thing entirely,
                # and is left alone.
                if (research is not None and arm.uses_phronix
                        and not (research.get("steps") or 0)):
                    # A dry account and a broken harness both produce zero tool
                    # calls; only one of them is a reason to stop. The harness
                    # says which, so ask it rather than guessing from rc=1.
                    if research.get("rate_limited"):
                        resets = research.get("resets_at")
                        raise UsageWindowClosed(
                            f"the account's usage window is exhausted, so "
                            f"research on {instance.get('instance_id')} could "
                            f"not run"
                            + (f"; it resets at {time.strftime('%H:%M', time.localtime(float(resets)))}"
                               if resets else "")
                            + ". Nothing is wrong with the pipeline — the "
                              "agents were rejected before they started.")
                    detail = str(research.get("returncode"))
                    stages = ", ".join(research.get("failed_stages") or []) or "none"
                    raise ResearchCollapsed(
                        f"research produced no tool calls at all on "
                        f"{instance.get('instance_id')} try {attempt_index} "
                        f"(rc={detail}, elapsed {research.get('elapsed_s')}s, "
                        f"failed stages: {stages}).\n"
                        f"The agent never started — check the harness command, "
                        f"the binary, and the model endpoint. Continuing would "
                        f"measure a plain agent and report it as phronix.")

                if research:
                    # Research runs inside this attempt's wall clock, so its
                    # time and cost have to be recorded against the attempt or
                    # they read as the agent solving slowly and expensively.
                    attempt.research_s += float(research.get("elapsed_s") or 0)
                    attempt.research_cost_usd += float(research.get("cost_usd") or 0)
                    if research_log is not None:
                        research_log.append(research)
                    if tracer:
                        tracer.research(attempt_index, research)
                        tracer.tools(f"research-{attempt_index}",
                                     attempt_dir / f"research-{attempt_index}.jsonl")

                    # No revision pass. The ideas go straight to the tests.
                    #
                    # `research_verify` used to be able to send a finished pass
                    # back to the start, and a second full research pass would
                    # run before the attempt. Its bar is the figure of merit
                    # and the trials on the corpus research built for itself —
                    # a proxy, and one nothing satisfies now that candidates
                    # are measured against the task's own tests instead.
                    #
                    # Measured on pylint-7080: three ideas explored, three
                    # solution skills written, and eleven seconds later the
                    # whole pass was re-run because the proxy was unhappy. The
                    # candidates were sitting there, executable, unattempted.
                    #
                    # What judges them is the next few minutes: every plan
                    # tried, every result measured against the real target
                    # tests, and each marked against the plan that produced it.

                # Measured once per instance and cached; needed here because a
                # candidate cannot be judged without knowing what was already
                # broken.
                baseline = baseline_failures(
                    container, instance,
                    cache_dir=Path(self.config.data_root or ".") / "baselines",
                    on_event=((lambda text: _labelled("evaluate", text))
                              if tracer else None))

                # Recall is a STEP, and it is the first one.
                #
                # The flow is: what does the store already hold for this task,
                # then attempt, then research only if that failed. The lookup
                # ran inside the prompt build, so it never appeared anywhere —
                # a run that was handed the answer and one that found nothing
                # opened identically at "attempt", and the only way to tell
                # them apart was to read the agent's prompt out of a transcript.
                attempt.recalled_skill = ""
                # What the store had already served, so that what THIS attempt
                # loads can be told apart from what an earlier one did.
                retrieved_before = set(read_retrievals(retrieval_log))
                if getattr(arm, "uses_phronix", False):
                    if tracer:
                        tracer.begin("search-skill",
                                     "does the store already cover this task?")
                    try:
                        attempt.recalled_skill = arm.best_skill_for(
                            store_root, arm.research_topic(instance)) or ""
                    except Exception:
                        # A lookup that fails is a miss, not a broken attempt.
                        attempt.recalled_skill = ""
                    if tracer:
                        found = attempt.recalled_skill
                        tracer.event(
                            "search-skill",
                            (f"found `{found}` — the attempt solves with it"
                             if found else
                             "no skill covers this task; solving from scratch"),
                            data={"skill": found})

                if tracer:
                    # The skill is named in the STAGE, the way a raced plan is,
                    # so what an attempt was working from can be read off the
                    # trace instead of inferred from its prompt. Everything
                    # before the colon is the stage, so these still group as
                    # "attempt" wherever attempts are totalled.
                    # `attempt>` alone, or `attempt>skill>` once there is one —
                    # the same path shape the research stages already read as.
                    stage = ("attempt" if not attempt.recalled_skill
                             else f"attempt>{attempt.recalled_skill}")
                    tracer.begin(stage,
                                 (f"agent working on try {attempt_index}"
                                  + (f" with `{attempt.recalled_skill}`"
                                     if attempt.recalled_skill else
                                     " from scratch")),
                                 self.config.timeout_s)
                narrate_attempt = ((lambda text: _labelled("attempt", text))
                                   if tracer else None)
                # When this attempt began, for the per-stage timings the record
                # and the `top.sh` tree read. Defined HERE because every branch
                # below produces an outcome — measured trials, a plan race, or
                # a plain generate — and each one is timed from the same point.
                started = time.time()
                plans = []
                # 0 means every plan research produced; 1 is the single
                # merged attempt; N is the top N.
                wanted = int(getattr(self.config, "attempt_candidates", 1) or 0)
                if wanted != 1:
                    plans = arm.candidate_plans(
                        store_root, arm.research_topic(instance), wanted)

                # Research already put these in front of the tests.
                #
                # When the trial seam is in play a candidate has been measured
                # the moment it was executable, so racing the same set again
                # costs a container and an agent per plan to re-derive a verdict
                # already on file — and would re-run the winner that made
                # research stop early in the first place.
                measured = (research or {}).get("trials") or []
                if measured and (research or {}).get("best_outcome") is not None:
                    outcome = research["best_outcome"]
                    attempt.trials = measured
                    solved = (research or {}).get("solved_by") or []
                    if tracer:
                        tracer.event(
                            "trials",
                            f"{len(measured)} candidate(s) already tried during "
                            f"research: "
                            + ", ".join(f"{r['plan']}={r['target_tests_passed']}"
                                        for r in measured)
                            + (f" — SOLVED by {', '.join(solved)}" if solved
                               else " — none solved it; taking the furthest"))
                    arm.reconcile_trials(instance, store_root, attempt_dir,
                                         measured, on_call=narrate_attempt)
                    attempt.solution_skill = arm.solution_skill_path(
                        store_root, arm.research_topic(instance))
                elif len(plans) > 1:
                    # Try every ranked plan against the REAL tests, at once.
                    #
                    # Research ranks approaches against a figure of merit
                    # measured on a corpus it built itself — a proxy. The plan
                    # that proxy ranks first is the most promising, not the
                    # correct one, and until now it was the only one ever
                    # attempted. The fleet has 32 replicas and attempts are
                    # independent, so N plans cost wall-clock once instead of N
                    # times, and the target tests settle which proxy was right.
                    outcome, trials = self._race_plans(
                        arm, instance, store_root, attempt_dir, plans,
                        baseline_for=session, tracer=tracer,
                        narrate=narrate_attempt)
                    attempt.trials = trials
                    # Merge what worked, or question what they all assumed.
                    arm.reconcile_trials(instance, store_root, attempt_dir,
                                         trials, on_call=narrate_attempt)
                    # Where the merge put it, so the result points at the
                    # solution rather than only asserting there is one.
                    attempt.solution_skill = arm.solution_skill_path(
                        store_root, arm.research_topic(instance))
                else:
                    outcome = arm.generate(instance, store_root, attempt_dir,
                                           container, on_call=narrate_attempt)
                # The record covers what the attempt DID, not only how it was
                # judged. A verdict says a test failed; the attempt's own diff
                # and account say what was tried, and "tried and did not work"
                # is what stops the next attempt trying it again.
                if (str(getattr(self.config, "pipeline", "sequential")).lower()
                        != "parallel" and getattr(arm, "uses_phronix", False)):
                    try:
                        (attempt_dir / "attempt-diff.patch").write_text(
                            outcome.patch or "(the agent produced no diff)\n",
                            encoding="utf-8")
                        attempt.stages.append({
                            "name": "attempt",
                            "steps": int(outcome.steps or 0),
                            "tokens_input": int(outcome.tokens_input or 0),
                            "tokens_output": int(outcome.tokens_output or 0),
                            "elapsed_s": round(time.time() - started, 1),
                        })
                        # Was the skill USED, or only offered?
                        #
                        # The trace said `found X — the attempt solves with it`
                        # the moment the lookup hit, which reports what the
                        # harness did, not what the agent did. An attempt
                        # handed a skill and ignoring it, and one that read it
                        # and applied it, produced identical lines — so the
                        # question the whole store exists to answer could not
                        # be read off a run.
                        self._trace_skill_use(
                            tracer, attempt, retrieval_log, retrieved_before,
                            attempt_index)
                        arm.track(instance, store_root, attempt_dir,
                                  phase="attempt",
                                  cost=f"try {attempt_index}, "
                                       f"{outcome.steps} steps, "
                                       f"{round(time.time() - started)}s",
                                  evidence=[attempt_dir / "attempt-diff.patch",
                                            attempt_dir / "prompt.md"],
                                  on_call=((lambda text: _say("track", text))
                                           if tracer else None))
                    except Exception as exc:
                        if tracer:
                            tracer.event("track",
                                         f"could not record the attempt: {exc}")

                evaluation_started = time.time()
                if tracer:
                    tracer.begin("evaluate", "running the instance's tests")

        (attempt_dir / "patch.diff").write_text(outcome.patch or "")
        (attempt_dir / "agent.json").write_text(
            json.dumps({"raw": outcome.raw, "error": outcome.error}, indent=2))

        # Did this attempt just re-apply a change that already failed?
        #
        # Recorded rather than blocked: the patch exists and evaluating it is
        # cheap, and a repeat that unexpectedly passes is information too. What
        # matters is that it stops being invisible — three attempts producing
        # the same edit read as three independent failures in the results, and
        # the retry budget is spent believing the idea is still untested.
        repeat_of = _repeats_earlier(outcome.patch or "",
                                     getattr(arm, "attempt_history", []) or [])
        if repeat_of:
            attempt.repeats_attempt = repeat_of
            if tracer:
                tracer.event("repeat",
                             f"try {attempt_index} re-applies the change from "
                             f"try {repeat_of}, which already failed — the "
                             f"diagnosis did not move")

        attempt.steps = outcome.steps
        attempt.tokens_input = outcome.tokens_input
        attempt.tokens_output = outcome.tokens_output
        attempt.tokens_cache = outcome.tokens_cache
        attempt.tokens_learn = outcome.tokens_learn
        attempt.learn_s = float((outcome.raw.get("learn") or {}).get("elapsed_s") or 0.0)
        attempt.cost_usd = outcome.cost_usd
        attempt.error = outcome.error

        if not (outcome.patch or "").strip():
            # No patch is a legitimate failure. Evaluating anyway would spend a
            # container and a test run to learn what we already know.
            attempt.error = attempt.error or "agent produced no patch"
            arm.record_attempt(instance, store_root, outcome.patch,
                               {"resolved": False, "error": attempt.error})
            arm.learn(instance, store_root, attempt_dir, outcome,
                      {"resolved": False, "error": attempt.error})
            return attempt

        # -- evaluate ------------------------------------------------------
        # A SECOND, pristine container. Evaluating in the container the agent
        # worked in would score whatever else it left behind — installed
        # packages, edited config, a stray conftest — rather than its patch.
        with session() as container:
            narrate_eval = ((lambda text: _labelled("evaluate", text))
                            if tracer else None)
            baseline = baseline_failures(
                container, instance,
                cache_dir=Path(self.config.data_root or ".") / "baselines",
                on_event=narrate_eval)
            if tracer and baseline.get("pre_existing_failures"):
                tracer.event("baseline",
                             f"{len(baseline['pre_existing_failures'])} test(s) "
                             "already failing before any patch",
                             [f"discounted: {n}" for n in
                              baseline["pre_existing_failures"][:4]])
            verdict = evaluate(container, instance, outcome.patch,
                               known_failures=baseline.get("pre_existing_failures"),
                               on_event=narrate_eval)
        (attempt_dir / "evaluation.json").write_text(json.dumps(verdict, indent=2))
        attempt.resolved = bool(verdict.get("resolved"))
        if not attempt.resolved and verdict.get("error"):
            attempt.error = attempt.error or str(verdict["error"])

        # Learn AFTER the verdict, not before it.
        #
        # The learning pass used to run straight after generation, which meant it
        # wrote up an attempt without knowing whether the attempt had worked. Its
        # most valuable input is precisely what it lacked: which tests still fail.
        # "I fixed the recursive-ignore path" and "I thought I fixed it and
        # test_ignore_path_recursive_current_dir still fails" are different
        # lessons, and only the second one heals anything.
        #
        # Running it here also makes a retry meaningfully different from a
        # re-roll: the store the next attempt reads now contains what this
        # attempt got wrong. The checkout is on the host, so it outlives the
        # container the agent worked in and is still readable here.
        arm.record_attempt(instance, store_root, outcome.patch, verdict)

        # Burn the approach that just lost, NOW — before the next research pass
        # reads the ranking.
        #
        # This was marked once per task, after every attempt had run, so within
        # a task nothing was ever on record as failed. The consequences were
        # exactly the ones the marking exists to prevent, and they were measured
        # on pylint-7080: try 1 implemented the top-ranked approach and failed;
        # nothing recorded that; try 2's research proposed a revision, but
        # `research_refine_approach` rejected it because the parent was not a
        # failure, and the ranking still led with the unrefined version — so try
        # 2 implemented the same incomplete fix and failed the same way. The
        # refusal, the refinement and the burial were all built and all inert,
        # because each of them keys off a status nothing set until too late.
        # Every plan that ran, marked by what its own trial did.
        #
        # This is what `choose` used to stand in for. It named one approach as
        # "followed" before anything was tried, so the ledger recorded a guess;
        # now each candidate was actually implemented and actually measured, and
        # a plan that failed on the real tests is the strongest evidence the
        # system can have about it. Marked whether or not the attempt as a whole
        # resolved: in a race the winner and the losers are both results.
        marked_plans = False
        if arm.uses_phronix and not arm.store_readonly:
            topic = getattr(arm, "research_topic_binding", "")
            for trial in (attempt.trials or []) if topic else []:
                if not trial.get("plan"):
                    continue
                marked_plans = True
                self._mark_outcome(
                    arm, store_root, topic, worked=bool(trial.get("resolved")),
                    approach=trial["plan"], tracer=tracer,
                    why=(f"try {attempt_index}: tried against the target tests, "
                         f"{trial.get('target_tests_passed', 0)} passing"
                         + (f"; trial error: {trial['error']}"
                            if trial.get("error") else "")))

        if (arm.uses_phronix and not arm.store_readonly
                and not attempt.resolved and not marked_plans):
            topic = getattr(arm, "research_topic_binding", "")
            if topic:
                failing = (verdict.get("fail_to_pass_failing") or [])[:2]
                self._mark_outcome(
                    arm, store_root, topic, worked=False, tracer=tracer,
                    why=(f"try {attempt_index}: target tests still failing: "
                         f"{', '.join(failing) or 'unknown'}"))

        arm.learn(instance, store_root, attempt_dir, outcome, verdict)

        # Fold this attempt into the task's own record, before the next try.
        #
        # Its own stage, and per task. `learn` above writes what crosses task
        # boundaries — a solution skill, a memory — and the always-on learner
        # keeps working across everything in the background. The tracker is
        # neither: it is this task's memory, holding what is established, what
        # is still open and what has been ruled out, so the next attempt and
        # the research pass between them read a page instead of a transcript.
        if (str(getattr(self.config, "pipeline", "sequential")).lower()
                != "parallel" and getattr(arm, "uses_phronix", False)):
            try:
                attempt.stages.append({
                    "name": "evaluate",
                    "elapsed_s": round(time.time() - evaluation_started, 1),
                    "note": f"{(verdict or {}).get('fail_to_pass_passed', '?')}"
                            f"/{(verdict or {}).get('fail_to_pass_total', '?')} target",
                })
                arm.track(instance, store_root, attempt_dir, phase="evaluate",
                          cost=f"try {attempt_index}, "
                               f"{(verdict or {}).get('fail_to_pass_passed', '?')}"
                               f"/{(verdict or {}).get('fail_to_pass_total', '?')}"
                               f" target tests",
                          # `exchange.md` carries what the tests PRINTED — the
                          # assertion and the traceback — and `evaluation.json`
                          # names every target test by outcome. The digest
                          # alone says a test failed; these say which, and why.
                          evidence=[attempt_dir / "attempt-notes.md",
                                    attempt_dir / "exchange.md",
                                    attempt_dir / "evaluation.json"],
                          on_call=((lambda text: _say("track", text))
                                   if tracer else None))
            except Exception as exc:      # a record that fails is not a failed task
                if tracer:
                    tracer.event("track", f"could not update the record: {exc}")

        attempt.verdict = verdict
        return attempt

    @staticmethod
    def _mark_outcome(arm, store_root: Path, topic: str, worked: bool,
                      why: str = "", tracer=None,
                      approach: str = "") -> Dict[str, Any]:
        """Record how a real task went for the approach that was followed.

        Through the arm's own `_in_store`, which is the only place that knows
        the whole environment a phronix call needs. Setting `PHRONIX_PROJECT_ROOT`
        by hand was not enough: a session run keeps its research under
        `research/sessions/<id>/`, so without `PHRONIX_RESEARCH_SESSION` the
        lookup resolved the empty common folder, found no record, and returned
        `empty` — silently. The attempt failed, nothing was marked, and the
        whole burn-and-refine mechanism stayed inert for a second run.

        Never able to fail the task: bookkeeping that raises would turn a
        measured result into a lost one. But it is now *reported* when it does
        not land, because the previous silence is what hid this for a run.
        """
        from phronix import research as _research

        try:
            decided = arm._in_store(store_root, _research.mark_attempt_outcome,
                                    topic, approach=approach, worked=worked,
                                    evidence=why) or {}
        except Exception as exc:  # noqa: BLE001 - reported, never raised
            if tracer:
                tracer.event("approach-unmarked",
                             f"could not record the outcome for {topic}: {exc}")
            return {}

        if not tracer:
            return decided
        if decided.get("status") == "ok":
            tracer.event("approach-" + decided["new_status"],
                         f"{decided.get('approach')} "
                         + ("solved the task" if worked else
                            f"did not solve it — {why}. It will not be "
                            f"proposed again; a revision of it can be."))
        elif decided.get("status") == "empty":
            # Nothing to mark is not a failure to mark.
            #
            # Under research-on-retry, try 1 runs with research withheld, so no
            # approach was ever proposed and the record is legitimately empty.
            # This fired on every first attempt, warning that "the next attempt
            # will still see this approach as live" — about an approach that
            # does not exist.
            #
            # A corrector that cries wolf on the normal path teaches everyone
            # to ignore it, which costs exactly the times it is right.
            tracer.event("approach-none",
                         f"no approach was followed on {topic}, so there is "
                         f"nothing to mark — no approach was ever recorded")
        else:
            # Not decoration: an unmarked failure means the next attempt sees
            # the losing approach still ranked first, which is the exact bug
            # this call exists to prevent.
            tracer.event("approach-unmarked",
                         f"outcome NOT recorded for {topic} "
                         f"(status {decided.get('status')!r}) — the next "
                         f"attempt will still see this approach as live")
        return decided

    @staticmethod
    def _diff_created(before: Dict[str, List[str]],
                      after: Dict[str, List[str]],
                      instance_id: str = "") -> List[str]:
        """Skills this task created — not everything that appeared while it ran.

        A before/after diff of a SHARED store credits a task with whatever its
        neighbours wrote. Measured at 30 tasks in parallel: `sympy__sympy-21379`
        reported creating `astropy-astropy-14182`, `pallets-flask-4045`,
        `pytest-dev-pytest-5227` and six more, alongside its own real
        `sympy-21379-fix-piecewise-generator-polynomialerror`. Every passing task
        listed the same nine names, because all thirty diffs saw all thirty sets
        of writes.

        A skill whose name carries a DIFFERENT instance id is definitionally not
        this task's, so those are dropped. That is a filter, not a fix: a skill
        named for its subject rather than its instance — `backend-figure-
        matplotlib`, `dpi-unpickle-bug` — cannot be attributed this way and is
        still credited to whoever diffed next. Attributing properly needs the
        writer recorded at write time; this removes the provably wrong entries
        and leaves the ambiguous ones.

        Sequential runs are unaffected: with one task writing at a time the diff
        was already correct, and nothing here can remove a name it should keep.
        """
        # Skills AND capabilities. The task answer written to
        # `capabilities/tasks/<slug>/` is the main thing a task learns, and
        # diffing only `skills` reported the 30-task fresh run as having
        # created nothing at all while its store gained 25 task answers.
        appeared = sorted(
            (set(after.get("skills", [])) - set(before.get("skills", [])))
            | (set(after.get("capabilities", []))
               - set(before.get("capabilities", []))))
        if not instance_id:
            return appeared

        def slug(text: str) -> str:
            return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")

        # The issue number is the identity, and a plain substring test is what
        # gets it right. A cleverer pattern here matched `1379` inside `21379`
        # and threw away the task's own skill — the one entry that was certainly
        # correct.
        number = slug(instance_id).rsplit("-", 1)[-1]
        if not number.isdigit():
            return appeared

        def foreign(name: str) -> bool:
            if number in name:
                return False            # carries this task's number: ours
            # Carries SOME issue-shaped number that is not ours: a neighbour's.
            # A skill named for its subject and not an instance has none, and
            # stays — it cannot be attributed either way, and dropping it would
            # hide real work.
            return bool(re.search(r"\d{3,6}", name))

        return [name for name in appeared if not foreign(name)]
