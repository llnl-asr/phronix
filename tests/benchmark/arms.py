"""The four arms — what each one actually runs, and how they are kept comparable.

Every arm receives the same instance, the same container image, the same model
and the same attempt budget. The *only* thing that varies is the scaffolding:

===========================  ==========================================
mini                         mini-swe-agent's own agent
opencode-bare                opencode, no phronix
opencode-phronix-frozen      opencode + phronix, store mounted read-only
opencode-phronix             opencode + phronix, store read-write
===========================  ==========================================

The frozen arm is the control. It runs byte-identical scaffolding to the full
arm — same MCP server, same agents, same standing rules — with the skill store
mounted ``:ro``. Read-only at the mount, not merely by convention: an arm that
*could* write is not a control, and a single accidental write would invalidate
the comparison silently.

Model configuration is shared by every arm through :func:`model_env`, because a
benchmark whose arms differ in model or endpoint is measuring the model.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shlex
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from phronix import bus as bus_module

from .isolation import Container, isolated_env

#: The one model every arm uses. LivAI is OpenAI-compatible, so mini-swe-agent
#: (litellm) and opencode (ai-sdk openai-compatible) can both reach it.
def _tuned(key: str, fallback):
    """A tuning value, falling back to what the code shipped with.

    The learner's clocks belong in the same file as everything else tunable: a
    node packing six tasks wants a different cadence from a laptop running one,
    and that is a deployment decision rather than a code change.
    """
    try:
        from phronix.tuning import get

        return get(key, fallback)
    except Exception:
        return fallback


DEFAULT_MODEL = "claude-sonnet-4.5"
DEFAULT_PROVIDER = "livai"
DEFAULT_BASE_URL = "https://livai-api.llnl.gov/v1"

#: Scratch directory inside the checkout where research does its work.
#:
#: Research needs somewhere to apply a candidate change, run it, and throw it
#: away. Doing that in the checkout itself has two costs: the work shows up in
#: the diff the agent is judged on, and — worse — parallel evaluators share one
#: working tree, so each one measures a mixture of everybody's edits.
#: The arm that owns this job's learner, and the lock that decides.
#:
#: One learner for the whole benchmark job: arms run concurrently, tasks may
#: too, and every one of them reaches `start_learning`. Two consumers of one
#: stream is how two reconcilers come to work the same findings.
_LEARNER_LOCK = threading.Lock()
_LEARNER_OWNER = None

SCRATCH_DIR = "tmp"
RESEARCH_SCRATCH = f"{SCRATCH_DIR}/research"

# Prepended to every research prompt.
#
# Research agents write things: probe scripts, generated corpora, captured
# output. Without somewhere named they scatter attempts across the checkout
# root, /tmp and the store, most of which are read-only or outside the sandbox,
# and the run fills with permission errors that look like reasoning failures.
SCRATCH_NOTE = f"""
SCRATCH SPACE — read this first.

Write every temporary file to `{RESEARCH_SCRATCH}/` relative to the directory you
were started in. Scripts, generated instances, captured output, notes: all of it
goes there. That directory exists, is writable, and is excluded from git, so
nothing you put in it can contaminate the patch you are judged on.

Do not write anywhere else. The repository is under test, the skill store is
managed through MCP tools rather than files, and the system temp directory is
not yours. A write outside the scratch directory will be refused, and the
refusal costs you a step.

"""

#: MCP servers that may be registered in the user's GLOBAL opencode config and
#: must not leak into a benchmark arm. One of these pointed at a server that was
#: not running, with a 24-hour timeout, and opencode hung rather than failing.
_FOREIGN_MCP_SERVERS = ("dftracer", "phronix")

#: The prompt every opencode arm receives. Identical across arms — any difference
#: here would be scaffolding smuggled in as instructions.
#:
#: The issue text is **attached as a file** rather than interpolated here, and
#: that is a correctness fix, not a style choice. ``opencode`` is a wrapper around
#: ``npx``, which re-interprets its arguments through a shell; a problem statement
#: containing backticks or ``$(`` — pylint's, for instance, quotes shell
#: transcripts — gets partially executed instead of delivered. The symptom is
#: brutal to read: ``sh: command substitution: syntax error`` and an agent that
#: fails in seconds having never seen its task. Keeping this string free of shell
#: metacharacters makes the hazard structurally impossible rather than a property
#: of whichever instances happen to be in the task list.
TASK_PROMPT = """\
You are working in a checked-out repository. The issue to fix is in the attached
file issue.md, and task-brief.md states the repository, its version, where the
code and tests live, and how your work is judged. Fix the issue by editing the
source. Do not modify any test files.

Verify narrowly. Run the tests covering the code you changed, not the project's
whole suite: it is slow, most of it cannot be affected by your change, and its
output is large enough to crowd out what you are actually trying to read. A
measured attempt spent most of its tokens re-running unrelated suites against a
two-line fix that was already correct.

A failing test outside the area you touched was most likely failing before you
started; this benchmark measures pre-existing failures separately and discounts
them, so do not chase one and do not revert a correct fix because of one.

When you are done, the repository's own tests for this issue must pass. Make the
smallest change that genuinely fixes the described problem.
"""


#: Appended to the task prompt on a retry. Identical for every arm.
RETRY_SUFFIX = """

A previous attempt at this task failed. The attached file feedback.md states
exactly which tests still fail, which tests your predecessor's change broke, and
the test output explaining why. Read it first and diagnose what was wrong with
that approach before making any edit. Do not simply repeat it.
"""


#: Appended to EVERY phronix attempt, first included. Research produced a plan;
#: this is what makes the attempt follow it. Without this the research pass was a
#: pure cost: a plan written, verified, and then ignored by the agent that was
#: supposed to execute it — which is a more expensive way to fail than not
#: researching at all.
PHRONIX_PLAN_SUFFIX = """

This task has been researched already, and the result is a single skill:

    {skill}

The skill IS the plan: the pipeline to run, the approaches in the order to try
them, how a change here is measured, and what was already tried and refuted.

**Fetch the part you need, not the whole file.** Your first action:

    graph_query(question="steps to solve {topic}", scope="knowledge")

then `graph_get_node(node=...)` on the `Steps to solve ...` block it names. That
returns exactly that section. `skill_load("{skill}")` pulls every block — the
evaluation notes, the fallbacks, the aspects investigated, everything tried and
refuted — and you need one of them to start.

This is not fastidiousness. Whatever you load is re-read on every subsequent
step of this attempt, because each api call carries the whole conversation
again: a block loaded once and never used is paid for once per step, and these
attempts run to dozens of steps. Locate, fetch the section, act.

Fall back to `skill_load("{skill}")` only if the graph returns nothing useful —
and say so, because that is a defect worth knowing about.

## One approach at a time

The plan lists candidates by key — `A1`, `A2`, ... — best-measured first, each
with a one-line summary.

1. Take the FIRST one. `research_approach(topic="{topic}", key="A1")` gives you
   its hypothesis, where the change goes, and the evidence behind it.
2. **Follow the skill's `Steps to solve ...` block.** That is the method:
   an ordered sequence, each step either a tool to call or — only where the work
   genuinely needs judgement — an instruction to carry out.

   Run the steps in order. Where a step names a capability, CALL IT: it is
   deterministic, it was built for this, and doing that work by hand instead
   costs the full working context to reach the same answer. Where a step is
   marked judgement, that is the part that needs you.

   The steps are a method, not a recording. They solve this class of problem,
   so expect to supply the particulars — this file, this pattern, this value —
   while the sequence stays the same. If a step turns out not to fit this
   instance, say which one and why; that is a finding about the method.

   This is the whole reason research runs first: the expensive thinking is done
   and the attempt should be close to mechanical. Every step spent
   re-establishing a conclusion research already reached costs the full working
   context again, which is how a researched attempt quietly becomes as expensive
   as an unresearched one.
3. Implement only that, and measure it the way the skill says.
4. If it works, you are done. Say which key worked.
5. Only if it fails: say so, then fetch the `Fallback approaches` block —
   `graph_get_node` again, same reason — and take the next key from it.

Do not read all the approaches before starting. Most tasks are solved by the
first one, and on those the rest is context you paid for and never used — which
is why a researched attempt has been costing as much as an unresearched one.
Context should grow only when the cheap answer turns out to be wrong.

State the key you are working on as you go, and the key that finally worked or
the keys that did not. That is what gets recorded against the approach.

**Do not read the research record.** Do not call `research_status`, and do not go
looking for the research with `ls`, `find` or `cat` — it lives in a store
reachable only through the tools above, and the record itself runs to tens of
kilobytes of working detail that the skill already summarises. A measured
attempt spent seven steps searching directories for a plan it had loaded a
minute earlier, then read the raw record anyway.

`research_ruled_out(topic="{topic}")` is worth one call, and only if the skill
does not already list what previous attempts changed without success. Do not
edit those locations again without new evidence.

Follow the plan. Its deterministic steps have capabilities built for them: use
those tools rather than redoing the work by hand.

## Verify against the figure of merit

The skill states how work on this subject is measured. Run THAT — it is what the
approaches were scored on, so it is also the fastest way to find out whether the
chosen one actually held.

## When a verifier fails, that is a verdict — act on it, do not argue with it

A verifier is deterministic: same inputs, same answer, every run. If one fails
after your change, the overwhelmingly likely reading is that **your change is
incomplete**, and the failing case is telling you exactly which case it misses.
Fix the change and run it again.

Two doors, and you must go through one of them. Investigating in prose and
carrying on is not a third:

**The verifier is right.** Revise your change to handle the case it names. This
is almost always the answer. A measured example: an attempt made the correct
edit in six steps, its verifier failed on a path with a leading `./`, and the
attempt spent forty more steps establishing that the fix "works when targeting
`src` directly" — which is to say, it rediscovered the verifier's point and
dismissed it. The task then failed on precisely that case.

**The verifier is genuinely wrong** — it checks behaviour the issue does not
require, or its setup does not match the real conditions. Then FIX IT, do not
narrate it:

1. `verify_new(...)` with the corrected check, saying in the description what
   was wrong with the old one;
2. `skill_write_lesson(...)` recording what the broken check asserted and why it
   was wrong.

A wrong corrector left in place misleads every future attempt on this subject,
and a conclusion you only reach in conversation is gone the moment this session
ends. That is the difference between healing something and complaining about it.

**Spend at most a few steps deciding which door you are in.** If you cannot show
concretely that the verifier is wrong, it is right. The skill you loaded is the
plan and the approach it names is a concrete fix — when the check disagrees with
the fix, the gap is in the fix.

## If a previous attempt left a reproduction, run it

Look in `{repro}`. When an earlier attempt on this task failed, the diagnosis
that followed built a script that reproduces exactly how it failed, and the
approach you are implementing exists to fix that.

Run it before you finish. It must fail before your change and pass after — that
is the whole point of it existing, and it is the only check available here that
speaks to the specific way this task has already been lost. **Do not report done
while it still fails.** Failing again the same way is the one outcome a retry
must not produce; finding a different problem is fine, and worth saying.

If the plan turns out to be wrong, say so explicitly and record why — a plan that
survives contact with the code untested is worth less than one that was
falsified.
"""

#: Appended on a retry for arms **with** phronix. Deliberately carries no detail
#: about the failure: the detail is in the store, and retrieving it is the
#: capability under test.
PHRONIX_RETRY_SUFFIX = """

A previous attempt at this task failed. What went wrong was recorded as a lesson
in the project's knowledge store. Search it before you plan anything, and act on
what you find rather than starting from the same assumptions again.

Also call `research_ruled_out(topic=...)` with this task's instance id. It lists,
from recorded fact, every location previous attempts already changed without
success. Do not edit those again unless you have new evidence.

If what you find describes a fix that was already tried and still failed, do not
refine it. Take it as evidence that the cause lies somewhere you have not looked
— the helper being called, the caller, or where inputs are normalised — and go
find that instead.
"""


def _as_text(stream: Any) -> str:
    """Decode a subprocess stream that may be bytes, str, or absent.

    ``TimeoutExpired.stdout`` is bytes even when the call passed ``text=True``,
    which is a well-known wart; normalising here keeps the timeout path from
    throwing a second, more confusing error on top of the first.
    """
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return str(stream)


#: How long the agent's one-line summary of a call may be.
#:
#: Eighty characters is what fits on a log line after the timestamp, arm, pid
#: and stage prefix. Longer summaries are not more informative in a log; they
#: are the same summary with the end cut off by the terminal instead of by us.
LOG_SUMMARY_CHARS = 80

#: Prepended to every agent prompt.
#:
#: Without it the log records what was spelled, not what was meant: `run python
#: -c "import os; print(os.walk(...))"` says nothing about which hypothesis is
#: being tested. The agent is the only party that knows, and it costs it one
#: short line per call to say so.
LOG_NOTE = f"""
LOGGING — applies to every tool call you make.

Pass a `description` with every call: one line, at most {LOG_SUMMARY_CHARS}
characters, in plain language, saying what this call is FOR. Not what it does
mechanically — what you are trying to find out or achieve.

  bad:  "run pytest -k ignore_path"
  good: "check whether ignore-paths is applied before recursive discovery"

Somebody is reading these as they happen to understand what you are doing. A
call without a description shows up as a command line and tells them nothing.

"""


def say(text: str) -> str:
    """One line of an agent's own commentary, as plain prose.

    The model writes markdown: headings, bullets, bold, code spans, tables. In a
    trace that is noise with a shape — `## Analysis` and `**Found it**` and
    `- [ ] check the parser` all say something, and none of it survives being
    read at a glance next to eighty other lines. So the markup comes off, the
    first real sentence is kept, and it is cut to the width of everything else
    in the column.

    Returns an empty string when nothing worth showing is left, which is the
    common case for a heading or a lone code fence.
    """
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("```") or set(line) <= set("-=*_ |"):
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)            # headings
        line = re.sub(r"^[-*+]\s+(\[[ xX]\]\s*)?", "", line)  # bullets, checkboxes
        line = re.sub(r"^\d+[.)]\s+", "", line)            # numbered steps
        line = re.sub(r"^>\s*", "", line)                  # quotes
        line = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", r"\1\2", line)  # bold
        line = re.sub(r"(?<!\w)[*_](.+?)[*_](?!\w)", r"\1", line)   # italics
        line = line.replace("`", "")                       # code spans
        line = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", line)          # links
        line = " ".join(line.split())
        if len(line) <= 12:
            # A fragment — "Analysis", "Next:" — carries no more than the stage
            # label already does.
            continue
        if len(line) > LOG_SUMMARY_CHARS:
            # Cut at a word, and only say it was cut when something was.
            line = line[:LOG_SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
        return line
    return ""


def describe_tool_call(name: str, args: Dict[str, Any],
                       output: str = "", root: Optional[Path] = None) -> str:
    """What one tool call was FOR, in a sentence, for every harness.

    One copy, two adapters. This was written twice — once for opencode's event
    shape and once for Claude's — and the two drifted immediately: a fix to how
    a `grep` reads landed in one and not the other, so the same agent doing the
    same thing produced different trace lines depending on which harness ran it,
    and the runs stopped being comparable by eye. The harness-specific part is
    only how a call is spelled in its stream, so that is all the adapters do:
    normalise to (name, args, output) and hand it here.

    The line is a statement of intent and never the mechanics. `bash` arrives as
    ``cd /p/lustre5/.../attempt-1/repo && python -m pytest -x -q tests/...`` and
    eighty characters of path and flags push the one informative word off the
    end; what a reader of a live trace needs is "running the test suite in
    test_cli.py". Paths shrink to a basename for the same reason — every line in
    a task's trace shares a directory, so it carries no information and costs
    the width that does.
    """
    args = args if isinstance(args, dict) else {}
    spoken = _spoken_call(name, args, output, root)
    # A sentence assembled from arguments that turned out to be absent reads as
    # "proposing : " — an elaboration of nothing, and worse than the plain
    # intent it was elaborating. Observed live on `research_add_approach`, whose
    # branch names two arguments that a caller supplying only `topic` does not
    # have.
    trimmed = spoken.strip().rstrip(":,-—").strip()
    if len(trimmed) > 12:
        return trimmed
    short = str(name or "?").replace("mcp__phronix__", "").replace("phronix_", "")
    return _PHRONIX_INTENT.get(short) or short.replace("_", " ") or "a step"


def _spoken_call(name: str, args: Dict[str, Any],
                 output: str = "", root: Optional[Path] = None) -> str:
    """The sentence itself; :func:`describe_tool_call` guards the result."""
    # Longest prefix first. The other order eats the middle of the longer one —
    # `phronix_` matches inside `mcp__phronix__`, leaving `mcp__research_add_
    # approach`, which then spoke as "mcp  research add approach".
    short = str(name or "?").replace("mcp__phronix__", "").replace("phronix_", "")

    def shorten(value: Any, limit: int = LOG_SUMMARY_CHARS) -> str:
        text = " ".join(str(value).split())
        if root is not None:
            # Both spellings: /tmp is a symlink to /var/tmp here, so the literal
            # prefix often does not match. At a path boundary only, longest base
            # first — "/tmp/x/repo/" also occurs inside "/var/tmp/x/repo/", and a
            # plain replace there turned an edit of calc.py into "/varcalc.py".
            for base in sorted({str(root), str(Path(root).resolve())},
                               key=len, reverse=True):
                text = re.sub(r"(?<![\w/])" + re.escape(base) + "/", "", text)
                if text == base:
                    text = "."
        return text[:limit]

    def arg(*names: str, limit: int = 200) -> str:
        for key in names:
            if args.get(key):
                return shorten(args[key], limit)
        return ""

    def leaf(value: Any, limit: int = 44) -> str:
        text = str(value).strip().strip("'\"")
        return (text.rsplit("/", 1)[-1] or text)[:limit]

    # The agent's own words, whenever it supplied any.
    #
    # A derived description says what a call *was* and never why. The agent
    # knows why, every tool here takes a ``description``, and the prompts require
    # one — so where it exists it wins, because reconstructing intent from a
    # command line is a guess and the agent's own sentence is not. Unprefixed
    # and lowercased so it runs on from the stage label: "Bash: " in front of it
    # adds the one thing the reader does not need, in the column the eye hits
    # first.
    stated = str(args.get("description") or "").strip()
    if stated:
        return shorten(stated[0].lower() + stated[1:])

    lowered = str(name or "").lower()
    if "websearch" in lowered:
        return f"looking something up online: {arg('query', limit=50)}"
    if "webfetch" in lowered:
        return f"reading a page online: {arg('url', limit=50)}"

    if short in ("bash", "Bash"):
        return _command_intent(arg("command", limit=400))
    if short in ("read", "Read"):
        offset, limit_ = args.get("offset"), args.get("limit")
        where = leaf(arg("file_path", "filePath", "path"))
        if offset or limit_:
            first = int(offset or 1)
            span = (f"lines {first} to {first + int(limit_)}" if limit_
                    else f"from line {first} on")
            return f"reading {where}, {span}"
        return f"reading all of {where}"
    if short in ("glob", "Glob"):
        return f"looking for files named like {leaf(arg('pattern', 'path'))}"
    if short in ("grep", "Grep"):
        where = leaf(arg("path", "glob", "include"), 30)
        return (f"searching the source for {leaf(arg('pattern'))}"
                + (f", under {where}" if where and where != "." else ""))
    if short in ("edit", "Edit", "NotebookEdit", "write", "Write"):
        verb = "writing" if short.lower() == "write" else "editing"
        return f"{verb} {leaf(arg('file_path', 'filePath', 'path'))}"
    if short in ("task", "Task"):
        return f"delegating a sub-task: {arg('prompt', 'description', limit=54)}"
    if short in ("todowrite", "TodoWrite"):
        todos = args.get("todos")
        if isinstance(todos, list):
            for item in todos:
                if isinstance(item, dict) and item.get("status") == "in_progress":
                    return f"planning, now working on {shorten(item.get('content'), 50)}"
        return "planning, revising its list of steps"

    # Research tools: report the decision, not the payload.
    if short == "research_assess":
        verdict = ("gap" if '"verdict": "gap"' in output
                   else "covered" if '"verdict": "covered"' in output else "?")
        return f"deciding whether this is already covered -> {verdict}"
    if short == "research_define_fom":
        return (f"fixing the metric: {arg('name', limit=40)} "
                f"({arg('direction', limit=10)}, target {arg('target', limit=10)})")
    if short == "research_set_aspects":
        return f"planning which aspects to study: {arg('aspects', limit=46)}"
    if short == "research_declare_corpus":
        return f"declaring the dataset axes: {arg('dimensions', limit=50)}"
    if short == "research_add_instances":
        return f"adding cases to the dataset: {arg('instances', limit=48)}"
    if short == "research_split":
        return "splitting the dataset into train, validate and test"
    if short == "research_add_approach":
        return (f"proposing {arg('name', limit=24)}: "
                f"{arg('hypothesis', 'summary', limit=44)}")
    if short == "research_record_trial":
        passed = str(args.get("passed", "")).lower()
        return (f"trying {arg('approach', limit=24)} on "
                f"{arg('instance', limit=24)} -> "
                f"{'it worked' if passed in ('true', '1') else 'it did not'}")
    if short == "research_evaluate_approach":
        return f"scoring {arg('approach', limit=40)} against the metric"
    if short == "research_rank":
        return "ranking the approaches by the metric"
    if short == "research_write_plan":
        return f"writing the execution plan: {arg('steps', limit=50)}"

    if short in _PHRONIX_INTENT:
        return _PHRONIX_INTENT[short]

    failed = '"status": "error"' in output
    spoken = short.replace("_", " ")
    if args:
        first = next(iter(args.values()))
        return (f"{spoken}: {shorten(first, 50)}"
                + (" — REJECTED" if failed else ""))
    return spoken


def describe_call(part: Dict[str, Any], root: Optional[Path] = None) -> str:
    """opencode's event shape, normalised for :func:`describe_tool_call`."""
    state = part.get("state") or {}
    return describe_tool_call(str(part.get("tool") or "?"),
                              state.get("input") or {},
                              str(state.get("output") or ""), root)


def describe_claude_call(block: Dict[str, Any], root: Optional[Path] = None) -> str:
    """Claude Code's event shape, normalised for :func:`describe_tool_call`."""
    return describe_tool_call(str(block.get("name") or "?"),
                              block.get("input") or {}, "", root)


#: What each phronix tool is FOR, in the words someone reading a trace would
#: use. The tool name says which function ran; this says why it was worth
#: running, which is the only thing a reader of a live trace can act on.
_PHRONIX_INTENT = {
    "skill_search": "looking for a skill that already covers this",
    "skill_read": "reading a skill it found",
    "skill_write": "writing down what it learned as a skill",
    "memory_search": "checking memory for related work",
    "memory_write": "recording something worth remembering",
    "research_observe": "reporting an observation to the learner",
    "research_notice": "checking which observations have repeated",
    "research_verify": "checking a claim against the repository",
    "research_record": "recording a research finding",
    "research_status": "checking where the research stands",
    "research_select": "choosing the approach to carry forward",
    "research_backups": "noting which approaches are held in reserve",
    "research_ruled_out": "ruling an approach out",
    "capability_write": "building itself a tool for this step",
    "capability_run": "running a tool it built earlier",
}

#: How a shell command reads as an intention. Ordered, first match wins, so the
#: specific patterns come before the general ones.
_COMMAND_INTENTS = (
    (r"\bpytest\b|\bunittest\b|\btox\b", "running the test suite"),
    (r"\bgit\s+apply\b|\bpatch\b", "applying a patch"),
    (r"\bgit\s+diff\b", "reviewing its own changes"),
    (r"\bgit\s+(log|show|blame)\b", "reading the project's history"),
    (r"\bgit\s+(checkout|stash|reset)\b", "putting the working tree back"),
    (r"\bgrep\b|\brg\b|\back\b", "searching the source"),
    (r"\bfind\b|\bls\b", "looking around the tree"),
    (r"\bpip\b|\bnpm\b|\bconda\b", "installing a dependency"),
    (r"\bpython[0-9.]*\s+-c\b", "running a short probe script"),
    (r"\bpython[0-9.]*\b", "running a script"),
    (r"\bcat\b|\bhead\b|\btail\b|\bsed\s+-n\b", "reading a file"),
    (r"\bmkdir\b|\bcp\b|\bmv\b|\brm\b", "moving files around"),
)


def _command_intent(command: str) -> str:
    """A shell command as a sentence, never as the command.

    The agent's own `description` is preferred over this everywhere it exists;
    this is the fallback, and a fallback rather than an echo because a trace full
    of flags is a trace nobody reads. Where a file is named it is kept, since
    "the test suite" and "the test suite in test_cli.py" are different amounts
    of progress.
    """
    text = " ".join(str(command or "").split())
    text = re.sub(r"^cd\s+\S+\s*&&\s*", "", text)
    if not text:
        return "a command"

    for pattern, phrase in _COMMAND_INTENTS:
        if re.search(pattern, text):
            named = re.search(r"[\w./-]+\.(py|txt|cfg|toml|json|md)\b", text)
            if named:
                return f"{phrase} in {named.group(0).rsplit('/', 1)[-1]}"
            return phrase
    return f"running a shell step ({text.split()[0]})"


def private_opencode_home(env: Dict[str, str]) -> Any:
    """Give one opencode invocation its own state directory, on local disk.

    opencode keeps a SQLite event store at ``~/.local/share/opencode``. On this
    site that is NFS, the database had grown to 353 MB with a 4.4 MB WAL, and it
    is shared by every process the user runs. SQLite in WAL mode needs shared
    memory the filesystem cannot provide over NFS, so once the benchmark started
    running several agents at once every one of them began failing with::

        Failed query: insert into "event" (...)

    which surfaced as agents that produced no patch — indistinguishable, again,
    from agents that ran and did nothing.

    So each invocation gets a fresh HOME on node-local disk. Configuration,
    credentials and the npm cache are symlinked back to the real home because
    they are read-mostly and expensive to duplicate; only the state directory,
    which is the contended one, is private.

    Returns the directory, for the caller to remove afterwards.
    """
    import shutil
    import uuid

    real = Path.home()
    base = Path(f"/tmp/{os.environ.get('USER', 'phronix')}/ochome")
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    home = base / uuid.uuid4().hex[:10]
    try:
        (home / ".local" / "share" / "opencode").mkdir(parents=True, exist_ok=True)
        # Read-mostly: provider config, credentials and caches, for whichever
        # harness is running.
        #
        # ``.claude`` and ``.claude.json`` matter as much as the opencode ones:
        # without them Claude Code comes up unauthenticated in the private home
        # and exits after a second with no output, which the harness would have
        # recorded as an agent that produced no patch.
        for relative in (".opencode", ".claude", ".claude.json", ".config",
                         ".npm", ".cache", ".bun"):
            source = real / relative
            target = home / relative
            if source.exists() and not target.exists():
                target.symlink_to(source)
        auth = real / ".local" / "share" / "opencode" / "auth.json"
        if auth.is_file():
            (home / ".local" / "share" / "opencode" / "auth.json").symlink_to(auth)
    except OSError:
        shutil.rmtree(home, ignore_errors=True)
        return None

    env["HOME"] = str(home)
    return home


@contextlib.contextmanager
def private_home(env: Dict[str, str]):
    """``private_opencode_home`` for the paths that call subprocess.run directly."""
    import shutil

    home = private_opencode_home(env)
    try:
        yield env
    finally:
        if home is not None:
            shutil.rmtree(home, ignore_errors=True)


class _LlmGate:
    """Paces every agent invocation in the job, and waits out a rejected window.

    The binding limit here is not the node, it is the account. A five-hour usage
    window, once rejected, fails every subsequent agent instantly: the harness
    emits one `rate_limit_event` and exits 1, so a stage that would have taken
    six minutes returns nothing in four seconds. Observed: six tasks of four
    stage agents each emptied the window in under an hour, and the run then
    spent its remaining time producing empty transcripts and reporting them as a
    collapsed research pipeline.

    Two levers, because they bound different things. The semaphore bounds how
    many calls are in flight; the spacing bounds how many are *started* per
    minute, which is what actually draws down a window — eight agents finishing
    in twenty seconds each still start a hundred and forty an hour.

    One gate for the whole process, so packing more tasks onto a node does not
    multiply the draw. Tasks share the account whether or not they share a
    thread pool.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_start = 0.0
        self._reset_at = 0.0
        self._semaphore: Optional[threading.Semaphore] = None
        self._size = 0
        self._announced = 0.0

    def _limit(self) -> threading.Semaphore:
        if self._semaphore is None:
            with self._lock:
                if self._semaphore is None:
                    self._size = max(1, int(_tuned("llm.max_concurrent_agents", 8)))
                    self._semaphore = threading.Semaphore(self._size)
        return self._semaphore

    def rejected_until(self, resets_at: float, on_note=None) -> None:
        """Record that the window is closed until *resets_at* (unix seconds)."""
        with self._lock:
            if resets_at > self._reset_at:
                self._reset_at = float(resets_at)
                announce = on_note and (time.time() - self._announced > 60)
                if announce:
                    self._announced = time.time()
        if on_note and announce:
            wait = max(0.0, resets_at - time.time())
            on_note(f"[llm] usage window rejected; it resets in "
                    f"{wait / 60:.0f} min — holding every agent until then "
                    f"rather than launching ones that cannot run")

    @contextlib.contextmanager
    def slot(self, on_note=None):
        """Hold a slot for one agent invocation."""
        self._wait_for_window(on_note)
        limit = self._limit()
        # Say so when this has to wait.
        #
        # The gate is taken BEFORE the subprocess starts, so a stage held here
        # writes nothing at all — no stage line, no tool call, no output. In a
        # six-task run two tasks sat at "initial pass for try 1" for fourteen
        # minutes and read as hung, while the server they were waiting for
        # reported five free slots and nothing deferred. A queue nobody can see
        # is worse than a slower queue.
        if not limit.acquire(blocking=False):
            waiting_since = time.time()
            if on_note:
                on_note(f"waiting for one of {self._size} agent slots — the "
                        f"client's own limit, not the server's")
            limit.acquire()
            if on_note:
                on_note(f"got a slot after {time.time() - waiting_since:.0f}s")
        try:
            spacing = float(_tuned("llm.min_seconds_between_starts", 2.0))
            with self._lock:
                delay = max(0.0, self._last_start + spacing - time.time())
                self._last_start = time.time() + delay
            if delay > 0:
                time.sleep(delay)
            yield
        finally:
            limit.release()

    def _wait_for_window(self, on_note=None) -> None:
        if not _tuned("llm.wait_for_reset", True):
            return
        while True:
            with self._lock:
                remaining = self._reset_at - time.time()
            if remaining <= 0:
                return
            cap = float(_tuned("llm.max_wait_seconds", 1800))
            if remaining > cap:
                # A job that silently sits for hours is worse than one that
                # proceeds and fails loudly: the failure is at least visible in
                # the trace, and the operator can decide to stop.
                if on_note:
                    on_note(f"[llm] window does not reset for "
                            f"{remaining / 60:.0f} min, past the "
                            f"{cap / 60:.0f} min cap — going ahead; expect "
                            f"this stage to be rejected")
                return
            time.sleep(min(30.0, remaining))


#: One gate for the process. Tasks share an account whether or not they share a
#: thread pool, so the cap cannot live on the arm or the task.
LLM_GATE = _LlmGate()


def stream_opencode(command: List[str], cwd: Path, env: Dict[str, str],
                    timeout_s: int, on_call=None,
                    root: Optional[Path] = None,
                    stats: Optional[Dict[str, Any]] = None) -> Any:
    """Run opencode, reporting each tool call as it happens.

    ``subprocess.run`` returns nothing until the process exits, which for a
    seven-minute research pass means seven minutes in which a working agent and a
    dead one look identical. Reading the event stream line by line costs nothing
    and turns the pass into a narrative.

    Returns ``(stdout, returncode)``. A timeout kills the process and returns
    what it had produced — a partial transcript is still evidence, and its token
    counts are real.
    """
    import subprocess
    import threading

    # Private state directory per invocation: several of these run at once.
    env = dict(env)
    home = private_opencode_home(env)

    # Wait here, before spending anything, if the account's window is closed or
    # the job is already running as many agents as it is allowed.
    gate = LLM_GATE.slot(on_call)
    gate.__enter__()

    process = subprocess.Popen(command, cwd=str(cwd), env=env, text=True,
                               stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = threading.Event()

    def kill_later() -> None:
        if not timed_out.wait(timeout_s):
            timed_out.set()
            process.kill()

    watchdog = threading.Thread(target=kill_later, daemon=True)
    watchdog.start()
    started_at = time.time()

    collected: List[str] = []
    try:
        for line in process.stdout or []:
            collected.append(line)
            if on_call is None:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            # The account's usage window, reported by the harness itself.
            #
            # A rejected window is not a failure of this stage — it is every
            # later stage failing too, four seconds at a time, until the window
            # resets. The event carries the reset time, so the gate can hold the
            # whole job instead of each thread rediscovering it.
            if event.get("type") == "rate_limit_event":
                info = event.get("rate_limit_info") or {}
                if str(info.get("status") or "").lower() == "rejected":
                    if stats is not None:
                        stats["rate_limited"] = True
                        stats["resets_at"] = info.get("resetsAt")
                    LLM_GATE.rejected_until(float(info.get("resetsAt") or 0),
                                            on_call)
                continue

            # Claude Code speaks a different stream. Handle it first, since an
            # unrecognised event would otherwise fall through as silence — and a
            # silent trace is exactly what makes a working agent and a dead one
            # look the same, which is the thing this function exists to prevent.
            if event.get("type") == "assistant":
                try:
                    for block in (event.get("message") or {}).get("content") or []:
                        if block.get("type") == "tool_use":
                            on_call(describe_claude_call(block, root or cwd))
                        elif block.get("type") == "text" and block.get("text"):
                            spoken = say(block["text"])
                            if spoken:
                                on_call(spoken)
                except Exception:
                    pass
                continue

            part = event.get("part") or {}
            if not isinstance(part, dict):
                continue
            try:
                if (part.get("type") == "tool"
                        and (part.get("state") or {}).get("status") == "completed"):
                    on_call(describe_call(part, root or cwd))
                elif part.get("type") == "text" and part.get("text"):
                    # The agent's own account of what it is about to do. The
                    # clearest statement of intent available — a tool call says
                    # what was run, this says why. First line only: the full
                    # reasoning belongs in the transcript, not the log.
                    spoken = say(part["text"])
                    if spoken:
                        on_call(spoken)
            except Exception:
                pass  # commentary must never break the pass it narrates
    finally:
        was_killed = timed_out.is_set()
        timed_out.set()
        if stats is not None:
            # Truncation has to reach the caller, not just the log. A stage cut
            # off at its budget and a stage that finished early look identical
            # in the totals, and they mean opposite things: one is a stage with
            # time to spare, the other is findings thrown away at full price.
            stats["truncated"] = was_killed
            stats["elapsed_s"] = round(time.time() - started_at, 1)
            stats["budget_s"] = timeout_s
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
        if home is not None:
            import shutil

            shutil.rmtree(home, ignore_errors=True)
        gate.__exit__(None, None, None)
        if was_killed and on_call is not None:
            # A stage cut off at its budget looks exactly like a slow one from
            # the outside. Observed: an investigator ran 55 tool calls into a
            # 300s budget, was killed mid-investigation, and the trace showed
            # only that it had gone quiet.
            try:
                on_call(f"TRUNCATED at the {timeout_s}s budget after "
                        f"{time.time() - started_at:.0f}s — this stage did not "
                        "finish; its findings are partial")
            except Exception:
                pass
    return "".join(collected), (-1 if process.returncode is None else process.returncode)


def tool_path_env(env: Dict[str, str]) -> Dict[str, str]:
    """Ensure the running interpreter's ``bin/`` is on PATH for subprocesses.

    ``opencode`` is a one-line wrapper around ``npx --yes opencode-ai@latest``, so
    it needs node on PATH — and node is installed into this venv via ``nodejs-bin``
    because the machine has none. Without this the arm fails with
    ``npx: command not found``, which surfaces as an agent that produced no patch
    rather than as a missing dependency.

    Prepended, not appended: a system node of the wrong major version would
    otherwise win and fail in a much less obvious way.
    """
    bin_dir = str(Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin"))
    current = env.get("PATH", os.environ.get("PATH", ""))
    if bin_dir not in current.split(os.pathsep):
        env["PATH"] = os.pathsep.join([bin_dir, current])
    return env


def _needs_key(base_url: str) -> bool:
    """Whether an endpoint authenticates at all.

    A gateway does; a llama.cpp server on a lab host does not, and demanding a
    key for one blocks a run on a credential that has no meaning there. Decided
    by scheme and host rather than by a list of known-good URLs, so a new local
    endpoint works without editing this.
    """
    from urllib.parse import urlparse

    parsed = urlparse(str(base_url or ""))
    if parsed.scheme == "http":
        # Plain HTTP is not something a credential should be sent over anyway,
        # so an endpoint offering it is one that does not expect one.
        return False
    return True


def model_env(api_key_var: str = "OPENAI_API_KEY",
              base_url: str = DEFAULT_BASE_URL) -> Dict[str, str]:
    """Model/endpoint settings shared by every arm.

    Raises if the key is absent rather than letting a run start and fail 30 tasks
    later — the failure would look like a benchmark bug rather than a missing
    credential.
    """
    key = os.environ.get(api_key_var, "")
    if not key:
        if _needs_key(base_url):
            raise RuntimeError(
                f"{api_key_var} is not set. {base_url} needs it; see "
                "dftracer-agents/.env.example. Every arm uses the same key, so "
                "this blocks the whole run.")
        # A local, unauthenticated endpoint still wants the variable SET: the
        # OpenAI client libraries refuse to construct without one, and the
        # server ignores whatever it is given. Failing here instead would block
        # a run on a credential that does not exist for this endpoint.
        key = "not-required"
    return {
        api_key_var: key,
        "OPENAI_API_KEY": key,
        "OPENAI_BASE_URL": base_url,
        "OPENAI_API_BASE": base_url,   # litellm reads this spelling
    }


@dataclass
class AttemptOutcome:
    """What one arm produced for one attempt, before the tests are run."""

    patch: str = ""
    steps: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_cache: int = 0
    #: Tokens spent by the learning pass, kept OUT of the fields above.
    #:
    #: Solving, learning and researching are three different activities with
    #: three different justifications, and adding them into one number makes the
    #: interesting question unanswerable: a first attempt looks expensive and
    #: nothing says whether that was the agent working or the framework thinking
    #: about itself.
    tokens_learn: int = 0
    cost_usd: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def tokens_total(self) -> int:
        """Solve tokens only. Learning and research are reported separately."""
        return self.tokens_input + self.tokens_output + self.tokens_cache


class Arm:
    """Base class. An arm turns an instance into a **patch** plus telemetry.

    Every arm returns a unified diff as text and nothing else. The runner then
    evaluates that patch identically for all arms — fresh container, apply patch,
    apply the official test patch, run FAIL_TO_PASS and PASS_TO_PASS.

    That uniformity is the point. An arm that evaluated itself could be judged by
    a different standard than its competitors, and the whole comparison would
    turn on a difference nobody could see in the results.
    """

    name: str = "base"
    uses_phronix: bool = False
    store_readonly: bool = True

    #: Whether this arm gets the full retry budget.
    #:
    #: False for a plain baseline: nothing carries between its attempts, so a
    #: second try is an independent re-roll of the same dice. Six tries there
    #: measures sampling, not capability, and pass@6 against pass@1 is not a
    #: like-for-like comparison.
    #:
    #: True for BOTH phronix arms, including the frozen control — and the frozen
    #: case is the subtle one. It cannot learn either, so its retries are also
    #: resamples; it keeps the full budget anyway because it exists to isolate
    #: *learning* from *attempt count*. Cut its budget and the only remaining
    #: comparison confounds the two again, which is the thing the control was
    #: introduced to prevent.
    full_retry_budget: bool = False

    #: Off by default, and both are recorded in the run manifest when on.
    #: Published SWE-bench numbers are produced without maintainer hints and
    #: without revealing the grading test names; a run that included either
    #: silently would not be comparable to them, or to a previous run of this
    #: benchmark.
    include_hints: bool = False
    reveal_target_tests: bool = False

    #: True when the arm creates its own sandbox and must NOT be handed one.
    #: mini-swe-agent ships its own SWE-bench environment handling; wrapping it in
    #: our container would both nest containers and measure our harness rather
    #: than the reference agent as its authors intend it to run.
    generates_own_environment: bool = False

    def __init__(self, model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER,
                 base_url: str = DEFAULT_BASE_URL, timeout_s: int = 1800) -> None:
        self.model = model
        self.provider = provider
        self.base_url = base_url
        self.timeout_s = timeout_s
        #: Set per task by the runner. One arm object per arm, so this stays
        #: correct with arms running concurrently.
        self.retrieval_log: Optional[Path] = None

    @property
    def qualified_model(self) -> str:
        return f"{self.provider}/{self.model}"

    def start_learning(self, *_args, **_kwargs) -> None:
        """No learner on an arm that does not research.

        Defined here rather than guarded at the call site: the runner calls this
        on whatever arm it has, and an attribute only some arms carry is a
        `hasattr` in the caller that quietly does nothing when the name changes.
        """

    def drain_learning(self) -> List[str]:
        return []

    def stop_learning(self, timeout: float = 60.0) -> List[str]:
        return []

    def mounts(self, store_root: Path) -> Dict[Path, str]:
        """Host->guest mounts. Only the phronix arms mount the store."""
        return {}

    def generate(self, instance: Dict[str, Any], store_root: Path, workdir: Path,
                 container: Optional[Container] = None,
                 on_call=None) -> AttemptOutcome:
        """Produce a patch for *instance*.

        *container* is a clean work container, or ``None`` for arms that make
        their own (see :attr:`generates_own_environment`).
        """
        raise NotImplementedError

    def research(self, instance: Dict[str, Any], store_root: Path,
                 workdir: Path, attempt_index: int = 1,
                 notes: Optional[Path] = None, on_call=None) -> Dict[str, Any]:
        """Establish how the task should be approached. No-op without a researcher."""
        return {}

    def record_attempt(self, instance: Dict[str, Any], store_root: Path,
                       patch: str, verdict: Optional[Dict[str, Any]]) -> None:
        """File an attempt into the research ledger. No-op without one."""

    def learn(self, instance: Dict[str, Any], store_root: Path, workdir: Path,
              outcome: "AttemptOutcome",
              verdict: Optional[Dict[str, Any]] = None) -> None:
        """Record what this attempt taught the system, given how it was judged.

        *verdict* is the evaluation result — which tests passed, which failed.
        No-op for arms without a learning mechanism.
        """

    #: Set per task by the arms, so every research call lands in one record
    #: regardless of what the agent calls the topic.
    research_topic_binding: str = ""
    #: Consecutive tasks that could not get a container. Two means the host is
    #: gone, not that the tasks are hard — see EnvironmentGone in runner.py.
    tasks_without_environment: int = 0

    #: This run's research session. Records go to research/sessions/<id>/ and
    #: are invisible to reads unless reuse is on. Set by the runner.
    research_session: str = ""

    #: Read research across every session and the common folder.
    research_reuse: bool = False

    #: Research seconds spent on the current task, across every pass. Reset by
    #: the runner at the start of each task.
    research_spent_s: float = 0.0

    #: Research seconds allowed PER ATTEMPT. The budget for a task is this
    #: times the number of attempts it has made, so a task on its fifth try has
    #: had five times the research time of one that passed first.
    #:
    #: A flat per-task budget said the opposite: the tasks that needed research
    #: most — the ones still failing after four attempts — were the ones with
    #: none left. sympy-24066 spent its whole allowance early, then made three
    #: more attempts with no ability to revise the approach that had already
    #: failed three times.
    research_budget_s: float = 1200.0

    def research_allowance(self, attempt_index: int) -> float:
        """Total research seconds this task may have spent by ``attempt_index``."""
        return self.research_budget_s * max(1, int(attempt_index))

    #: Files each previous attempt changed, set by the runner before an attempt
    #: so feedback can say which locations have already failed.
    attempt_history: List[Dict[str, Any]] = []

    #: Whether the finalise stage has already run for the current task.
    research_finalised: bool = False

    @staticmethod
    def research_topic(instance: Dict[str, Any]) -> str:
        """The research record key for an instance. Stable across attempts.

        Defined on the base class, not on the phronix arms, because the shared
        ``generate`` path sets the binding for every opencode arm. When it lived
        on the subclass the baseline raised ``AttributeError`` before its agent
        started and reported six tasks of ``0 steps, 0 tokens`` — which reads as
        an agent that did nothing rather than as a harness that never called one.
        """
        return str(instance.get("instance_id") or "task")

    def phronix_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """Add the per-arm phronix variables to a subprocess environment.

        ``retrieval_log`` is per-arm state rather than a process-global, so that
        two arms running concurrently each record their own retrievals. Reuse is
        computed from these files, so crossing them would corrupt the headline
        learning metric in a way no downstream check would catch.
        """
        if getattr(self, "retrieval_log", None):
            env["PHRONIX_RETRIEVAL_LOG"] = str(self.retrieval_log)
        # Session isolation and reuse travel with every phronix invocation:
        # research, solve and learn all resolve the same folders, or they would
        # disagree about what exists.
        if getattr(self, "research_session", ""):
            env["PHRONIX_RESEARCH_SESSION"] = self.research_session
        if getattr(self, "research_reuse", False):
            env["PHRONIX_RESEARCH_REUSE"] = "1"
        # Every producer publishes to this run's bus.
        #
        # Inherited from the harness rather than derived, so a second run on the
        # same host cannot consume this one's observations: the endpoint is per
        # run, and a stage that inherits the wrong one would report its findings
        # into somebody else's learner.
        if os.environ.get(bus_module.ENDPOINT_ENV):
            env[bus_module.ENDPOINT_ENV] = os.environ[bus_module.ENDPOINT_ENV]
        if getattr(self, "research_topic_binding", ""):
            # One task, one research record. Without this the scope stage, the
            # aspect investigators and the harness each pick their own name for
            # the same topic and the findings never meet.
            env["PHRONIX_RESEARCH_TOPIC"] = self.research_topic_binding
        return env

    # -- shared helpers ----------------------------------------------------

    @staticmethod
    def diff_checkout(checkout: Path) -> str:
        """The diff the agent produced: source changes only.

        Two families of exclusion, for two different reasons.

        **Test files**, because SWE-bench applies its own test patch on top. An
        agent that edited tests would otherwise be scored against tests it wrote,
        which is the easiest possible way to fake a pass and would look like a
        genuine solve in every metric recorded here.

        **The harness's own scaffolding** — ``.opencode/``, ``AGENTS.md``, core
        dumps — because the benchmark put those files there, not the agent. Left
        in, they were 114 KB of a 118 KB "fix": every rendered phronix agent
        travelled into the evaluation container as part of the patch under test.
        That is wrong three times over. It is not the agent's work, so it does not
        belong in a diff used to judge the agent; it is asymmetric, since the
        phronix arms deploy scaffolding and the bare arm does not, so the arms
        were being scored on different things; and a crashed process's core dump
        landing in the checkout produced a binary hunk that made ``git apply``
        reject the *whole* patch, failing a task whose real fix was fine.
        """
        import subprocess

        exclusions = [":(exclude)tests", ":(exclude)test", ":(exclude)*/tests/*",
                      ":(exclude)*_test.py", ":(exclude)test_*.py",
                      ":(exclude)*/test_*.py", ":(exclude)conftest.py",
                      # Harness scaffolding: ours, not the agent's.
                      ":(exclude).opencode", ":(exclude).opencode/*",
                      ":(exclude)AGENTS.md", ":(exclude).phronix",
                      ":(exclude).phronix/*", ":(exclude)*.core",
                      # The scratch directory. Already excluded via
                      # .git/info/exclude, but that write can fail silently on a
                      # read-only .git, and scratch reaching the patch would fail
                      # the whole apply.
                      f":(exclude){SCRATCH_DIR}", f":(exclude){SCRATCH_DIR}/*"]
        subprocess.run(["git", "add", "-A", "--", ".", *exclusions],
                       cwd=checkout, capture_output=True, text=True)
        # The exclusions are repeated on the diff, not just the add. Excluding a
        # path from `git add` does nothing about a path already in the index —
        # and these are, because this runs more than once per attempt and the
        # first call staged everything. Filtering only at `add` looked correct
        # and shipped 114 KB of scaffolding anyway.
        result = subprocess.run(["git", "diff", "--cached", "--", ".", *exclusions],
                                cwd=checkout, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else ""

    def _in_store(self, store_root: Path, call, *args, **kwargs):
        """Run a phronix call against the run's store, restoring the env after.

        The library resolves its layer from the environment, and the harness is a
        long-lived process serving two arms concurrently — leaving
        ``PHRONIX_PROJECT_ROOT`` set would let one arm's bookkeeping land in the
        other's store, which is the one corruption no downstream check would
        catch.
        """
        previous_root = os.environ.get("PHRONIX_PROJECT_ROOT")
        previous_topic = os.environ.get("PHRONIX_RESEARCH_TOPIC")
        previous_session = os.environ.get("PHRONIX_RESEARCH_SESSION")
        previous_reuse = os.environ.get("PHRONIX_RESEARCH_REUSE")
        try:
            os.environ["PHRONIX_PROJECT_ROOT"] = str(Path(store_root).parent)
            # In-process phronix calls resolve the same folders the subprocess
            # agents do, or the harness and the agents disagree about what
            # research exists.
            if getattr(self, "research_session", ""):
                os.environ["PHRONIX_RESEARCH_SESSION"] = self.research_session
            if getattr(self, "research_reuse", False):
                os.environ["PHRONIX_RESEARCH_REUSE"] = "1"
            else:
                os.environ.pop("PHRONIX_RESEARCH_REUSE", None)
            if getattr(self, "research_topic_binding", ""):
                os.environ["PHRONIX_RESEARCH_TOPIC"] = self.research_topic_binding
            return call(*args, **kwargs)
        except Exception:
            return None
        finally:
            # Every variable this touched, restored. Two arms share the
            # process; one leaving its session set would make the other read and
            # write the wrong folder, and nothing downstream would notice.
            for key, value in (("PHRONIX_PROJECT_ROOT", previous_root),
                               ("PHRONIX_RESEARCH_TOPIC", previous_topic),
                               ("PHRONIX_RESEARCH_SESSION", previous_session),
                               ("PHRONIX_RESEARCH_REUSE", previous_reuse)):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class MiniArm(Arm):
    """mini-swe-agent's own agent, run through its own SWE-bench harness.

    Uses ``minisweagent.run.benchmarks.swebench_single``, which resolves the
    instance, builds its own environment and returns the patch in the trajectory
    as ``info.submission``. Running mini through *its* harness rather than
    reimplementing it is what makes this a fair reference: any gap then reflects
    the agents, not our integration of one of them.

    Its patch is still evaluated by our evaluator, identically to every other
    arm — mini's runner produces predictions and deliberately does not score
    them.
    """

    name = "mini"
    generates_own_environment = True

    def __init__(self, *args: Any, subset: str = "lite", split: str = "test",
                 cost_limit: float = 0.0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.subset = subset
        self.split = split
        self.cost_limit = cost_limit

    def generate(self, instance: Dict[str, Any], store_root: Path, workdir: Path,
                 container: Optional[Container] = None) -> AttemptOutcome:
        import subprocess

        env = tool_path_env(dict(os.environ))
        env.update(model_env(base_url=self.base_url))
        # litellm addresses an OpenAI-compatible gateway with the openai/ prefix.
        env["MSWEA_MODEL_NAME"] = f"openai/{self.model}"
        env["MSWEA_CONFIGURED"] = "true"

        trajectory = workdir / "mini.traj.json"
        command = [
            "python", "-m", "minisweagent.run.benchmarks.swebench_single",
            "--subset", self.subset, "--split", self.split,
            "--instance", instance["instance_id"],
            "--model", f"openai/{self.model}",
            "--yolo", "--cost-limit", str(self.cost_limit),
            "-o", str(trajectory),
        ]
        started = time.time()
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=self.timeout_s, env=env, cwd=workdir)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as expired:
            # Same reasoning as the opencode arm: a timed-out attempt's telemetry
            # is real data, and mini writes its trajectory incrementally.
            stdout = _as_text(expired.stdout)
            stderr = _as_text(expired.stderr) or f"timed out after {self.timeout_s}s"
            code = -1

        outcome = AttemptOutcome(raw={"stdout": stdout[-4000:], "returncode": code,
                                      "elapsed_s": round(time.time() - started, 1)})
        if code != 0:
            outcome.error = (stderr or stdout)[-800:]
        return self._read_trajectory(trajectory, outcome)

    @staticmethod
    def _read_trajectory(path: Path, outcome: AttemptOutcome) -> AttemptOutcome:
        """Pull the patch and telemetry out of mini's trajectory.

        Defensive about the schema: mini's trajectory format is versioned
        (`trajectory_format`) and is not a stable API. A rename upstream must
        degrade to "no telemetry" rather than lose the whole run, so every field
        is optional and the file is kept for inspection either way.
        """
        if not path.is_file():
            outcome.error = outcome.error or "mini wrote no trajectory"
            return outcome
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            outcome.error = outcome.error or f"unreadable trajectory: {exc}"
            return outcome

        info = data.get("info") or {}
        outcome.patch = info.get("submission") or ""
        stats = info.get("model_stats") or {}
        outcome.cost_usd = float(stats.get("instance_cost") or 0.0)
        outcome.steps = int(stats.get("api_calls") or 0) or sum(
            1 for m in (data.get("messages") or [])
            if isinstance(m, dict) and m.get("role") == "assistant")

        # Token counts live in the model's own serialization when it reports them.
        for key, target in (("prompt_tokens", "tokens_input"),
                            ("input_tokens", "tokens_input"),
                            ("completion_tokens", "tokens_output"),
                            ("output_tokens", "tokens_output")):
            value = stats.get(key) or data.get(key)
            if value and not getattr(outcome, target):
                setattr(outcome, target, int(value))

        outcome.raw.update({
            "trajectory": str(path),
            "exit_status": info.get("exit_status", ""),
            "usage_source": "trajectory",
        })
        if not outcome.patch and not outcome.error:
            outcome.error = f"mini exited {info.get('exit_status', '?')} with no patch"
        return outcome


class OpenCodeArm(Arm):
    """opencode driven non-interactively, with or without phronix.

    opencode runs on the HOST with the repository checked out from the container,
    rather than inside it. Two reasons: the SWE-bench images carry neither node
    nor opencode, and installing them per attempt would dominate the runtime; and
    the phronix MCP server has to reach the run's skill store, which lives on the
    host. The *repository* is still exactly the container's, so the isolation that
    matters — the code and its test environment — is unaffected.

    Three invocation details are load-bearing and were each found the hard way:

    * ``stdin=DEVNULL``. opencode blocks forever on an inherited stdin. Every
      flag combination runs in seconds with stdin closed and hangs indefinitely
      without it, which would have wedged the benchmark at task 1 with no output
      to explain why.
    * ``--format json``. Gives exact token and cost figures per part, so this arm
      is measured rather than scraped — the same standard as the phronix arms.
    * ``--auto``. Without it the agent stops at the first permission prompt and
      produces no patch, which is indistinguishable from failing the task.
    """

    name = "opencode-bare"
    uses_phronix = False

    #: Empty means opencode's own default agent, which is the baseline's whole
    #: point. Overridden by the phronix arms.
    agent_name = ""

    def __init__(self, *args: Any, opencode_bin: str = "opencode", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.opencode_bin = opencode_bin

    def attachments(self, paths: List[Path]) -> List[str]:
        """How this harness is handed supporting files."""
        return [f"--file={path}" for path in paths]

    def agent_command(self, prompt: str, checkout: Path, files: List[str],
                      agent: str = "") -> List[str]:
        """The argv that runs one agent session over *checkout*.

        A seam, so a second harness is a command and a parser rather than a
        second copy of the attempt loop: everything around this — the checkout,
        the patch extraction, evaluation, research, the ledger — is
        harness-agnostic and stays shared.
        """
        command = [self.opencode_bin, "run", prompt,
                   "--dir", str(checkout), "--auto",
                   "--format", "json", "--model", self.qualified_model,
                   *files]
        if agent:
            command += ["--agent", agent]
        return command

    def mounts(self, store_root: Path) -> Dict[Path, str]:
        if not self.uses_phronix:
            return {}
        return {Path(store_root): "/phronix" + (":ro" if self.store_readonly else "")}

    def project_config(self, store_root: Path) -> Dict[str, Any]:
        """The ``.opencode/opencode.jsonc`` written into the working checkout.

        Project config merges over the user's global config, and that is exactly
        what this is for: the developer's global file may register MCP servers
        from other projects. One of them here pointed at a server that was not
        running, with a 24-hour timeout, and opencode simply hung.

        Beyond the hang, inheriting a stray server is an isolation failure: the
        bare arm is supposed to be opencode with *nothing*, and an unrelated tool
        surface silently makes it something else.
        """
        config: Dict[str, Any] = {
            "$schema": "https://opencode.ai/config.json",
            # Explicitly disabled rather than omitted: omitting leaves the global
            # entry active, since project config merges rather than replaces.
            "mcp": {name: {"enabled": False} for name in _FOREIGN_MCP_SERVERS},
        }
        return config

    def write_scaffold(self, checkout: Path) -> None:
        """Deploy the arm's harness files into the checkout.

        The bare arm deploys nothing: it is opencode with an unmodified working
        tree, which is the whole point of the baseline.
        """

    #: Instance fields that must NEVER reach an agent, at any setting.
    #:
    #: ``patch`` is the reference solution and ``test_patch`` contains the
    #: grading test's source. An agent shown either is not solving the task, and
    #: a benchmark that leaks them measures nothing.
    FORBIDDEN_FIELDS = ("patch", "test_patch")

    def task_brief(self, instance: Dict[str, Any], checkout: Path) -> str:
        """Facts about the task the dataset already knows, so nobody re-derives them.

        The research pass was spending minutes grepping for the repository
        layout, the test directory and the version in play — all of which are
        fields on the instance. Time spent rediscovering context is time not
        spent on the thing research exists for, which is comparing approaches.

        What this deliberately does NOT include is as important. The reference
        patch and the test patch never appear at any setting: an agent shown
        either is not solving the task. The grading test *names* and the
        maintainer hints are available but off by default, because published
        SWE-bench numbers are produced without them and a run that quietly
        included them would not be comparable to anything.

        It does state plainly that the grading tests are not visible. Without
        that, an agent hunts for a test it cannot see and draws conclusions from
        the absence — one run recorded "this test does not exist, it is a
        placeholder name" as a durable lesson. The test existed; it arrives with
        the evaluation.
        """
        lines = [
            f"# Task brief — {instance.get('instance_id', '?')}",
            "",
            "## The repository you are working in",
            "",
            f"- repository: `{instance.get('repo', '?')}`",
            f"- version at issue: `{instance.get('version', '?')}`",
            f"- base commit: `{instance.get('base_commit', '?')[:12]}`",
            "",
            "The issue to fix is in the attached `issue.md`.",
            "",
        ]

        layout = self._repo_orientation(checkout)
        if layout:
            lines += ["## Repository layout", "", *layout, ""]

        lines += [
            "## How this task is judged",
            "",
            "A hidden set of tests decides the outcome:",
            "",
            "- **target tests** — currently failing, must pass after your change;",
            "- **regression tests** — currently passing, must still pass.",
            "",
            "**You cannot see these tests.** They are applied from the benchmark "
            "after your work, not present in this checkout. Do not go looking for "
            "them, and do not conclude from their absence that they do not exist "
            "— a previous session recorded exactly that as a lesson and it was "
            "wrong. Infer the required behaviour from the issue, and validate "
            "with the repository's own existing tests.",
            "",
            "Do not modify test files. Changes under test directories are stripped "
            "before grading, so a fix that lives in a test is scored as no fix.",
        ]

        if self.reveal_target_tests:
            targets = instance.get("FAIL_TO_PASS")
            lines += ["", "## Target tests (revealed by configuration)", "",
                      "```", str(targets)[:1500], "```"]
        if self.include_hints and instance.get("hints_text"):
            lines += ["", "## Maintainer discussion from the issue", "",
                      str(instance["hints_text"])[:4000]]

        return "\n".join(lines)

    @staticmethod
    def _repo_orientation(checkout: Path) -> List[str]:
        """Where the source and the tests live — read once, not grepped for."""
        try:
            # Our own scaffolding is not part of the repository being described.
            ours = {"AGENTS.md", "issue.md", "task-brief.md", "feedback.md"}
            entries = sorted(p.name for p in Path(checkout).iterdir()
                             if not p.name.startswith(".") and p.name not in ours)
        except OSError:
            return []
        tests = [name for name in entries if name in ("tests", "test", "testing")]
        packages = [name for name in entries
                    if (Path(checkout) / name / "__init__.py").is_file()]
        lines = [f"- top level: {', '.join(entries[:18])}"]
        if packages:
            lines.append(f"- python package(s): {', '.join(packages[:6])}")
        if tests:
            lines.append(f"- tests live in: {', '.join(tests)} "
                         "(do not edit these; they are stripped before grading)")
        return lines

    def prepare_checkout(self, container: Container, store_root: Path,
                         workdir: Path) -> Path:
        """Export the container's /testbed to the host and lay the scaffolding.

        Split out of :meth:`generate` because the research pass needs the code
        too, and research runs first. While the export lived inside ``generate``,
        every research pass found no checkout and returned ``skipped`` — the
        trace showed a pass that took no time and called no tools, which is what
        surfaced it. Silent, and it would have read as "research did not help".

        Idempotent: a second call reuses the existing export rather than paying
        the copy again.
        """
        checkout = workdir / "repo"
        if not (checkout / ".git").exists():
            checkout.mkdir(parents=True, exist_ok=True)
            container.runtime.run(
                ["cp", f"{container.name}:/testbed/.", str(checkout)], timeout=900)

        config_dir = checkout / ".opencode"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "opencode.jsonc").write_text(
            json.dumps(self.project_config(store_root), indent=2) + "\n")
        self.write_scaffold(checkout)

        # A scratch area inside the checkout for research to work in.
        #
        # Kept out of git via .git/info/exclude rather than .gitignore: the
        # repository's own .gitignore is content under test, and adding a line to
        # it would show up in the patch the agent is judged on.
        scratch = checkout / SCRATCH_DIR
        scratch.mkdir(parents=True, exist_ok=True)
        (checkout / RESEARCH_SCRATCH).mkdir(parents=True, exist_ok=True)
        exclude = checkout / ".git" / "info" / "exclude"
        try:
            exclude.parent.mkdir(parents=True, exist_ok=True)
            existing = exclude.read_text() if exclude.is_file() else ""
            if SCRATCH_DIR not in existing:
                exclude.write_text(existing.rstrip("\n") + f"\n{SCRATCH_DIR}/\n")
        except OSError:
            pass
        return checkout

    def generate(self, instance: Dict[str, Any], store_root: Path, workdir: Path,
                 container: Optional[Container] = None,
                 on_call=None) -> AttemptOutcome:
        import subprocess

        if container is None:
            return AttemptOutcome(error="opencode arms need a work container")

        checkout = self.prepare_checkout(container, store_root, workdir)

        self.research_topic_binding = self.research_topic(instance)
        env = (isolated_env(store_root, workdir / "cache") if self.uses_phronix
               else dict(os.environ))
        env = self.phronix_env(tool_path_env(env))
        env.update(model_env(base_url=self.base_url))
        if self.uses_phronix:
            env["PHRONIX_WRITE_LAYER"] = "project"
            # The phase every retrieval in this environment belongs to.
            # 'solve' is the one that matters most: research can load a skill
            # and then hand over a plan that never mentions it, and the attempt
            # then solves without the knowledge ever reaching it.
            env["PHRONIX_PHASE"] = "solve"
            if self.store_readonly:
                # Belt and braces alongside the :ro mount, so the tools report a
                # clear refusal rather than an opaque OSError from the kernel.
                env["PHRONIX_BENCH_FROZEN"] = "1"

        # The solve agent gets the same writable temp as research, for the same
        # reason: it shells out, and the system temp directory is not writable
        # from where it runs.
        for name in ("TMPDIR", "TMP", "TEMP"):
            env[name] = str(checkout / SCRATCH_DIR)

        # Written outside the checkout: a file inside it would show up as an
        # untracked addition in the patch this arm is measured on.
        issue_file = workdir / "issue.md"
        issue_file.write_text(instance.get("problem_statement", ""), encoding="utf-8")
        brief_file = workdir / "task-brief.md"
        brief_file.write_text(self.task_brief(instance, checkout), encoding="utf-8")

        # Message first, flags after. ``--file`` is declared as an array option,
        # so anything positional following it is swallowed as another filename
        # and opencode dies with "File not found: <the entire prompt>" — true of
        # both the ``--file x`` and ``--file=x`` spellings.
        prompt = TASK_PROMPT
        if self.uses_phronix:
            topic = self.research_topic(instance)
            # Name the skill outright. Asking the agent to find it costs a search
            # and, when the search is ambiguous, a wrong answer — and the harness
            # already knows the answer, because research pinned it in the record.
            from phronix import research as research_module

            skill = self._in_store(store_root, research_module.topic_skill,
                                   topic) or ""
            prompt += (PHRONIX_PLAN_SUFFIX
                       .replace("{topic}", topic)
                       .replace("{repro}", f"{RESEARCH_SCRATCH}/repro")
                       .replace("{skill}", skill or "(none written yet)"))
        files = self.attachments([issue_file, brief_file])
        feedback = workdir / "feedback.md"
        if feedback.is_file():
            # A retry knows it is a retry — but the two arms learn what went
            # wrong through different channels, and that difference IS the
            # experiment.
            #
            # The baseline is handed the raw judgement in its prompt. It has no
            # memory, so the only way it can know anything about the last attempt
            # is for the harness to put it in front of the model, where it lasts
            # exactly one session and is gone.
            #
            # The phronix arm is handed nothing but the fact that an attempt
            # failed. The same failure reached its learner, which distilled it
            # into a stored lesson; this attempt has to *retrieve* that. Injecting
            # the raw output here too would hand phronix the answer through the
            # prompt and then credit its memory for it — the arm would score well
            # with the memory subsystem entirely broken, which is precisely the
            # bug the earlier runs had and precisely what this benchmark exists
            # to detect.
            if self.uses_phronix:
                prompt += PHRONIX_RETRY_SUFFIX
            else:
                prompt = TASK_PROMPT + RETRY_SUFFIX
                files += self.attachments([feedback])

        command = self.agent_command(LOG_NOTE + prompt, checkout, files,
                                     self.agent_name)

        started = time.time()
        if on_call is not None:
            # Same reasoning as the research pass: a thirty-minute attempt that
            # reports nothing until it exits is indistinguishable from a hung
            # one, and the interesting part — which files it opened, which tests
            # it ran — is exactly what the event stream carries. stream_opencode
            # enforces the timeout itself and keeps partial output.
            stdout, code = stream_opencode(command, checkout, env,
                                           self.timeout_s, on_call)
            stderr = ""
        else:
            try:
                with private_home(dict(env)) as run_env:
                    result = subprocess.run(
                        command, cwd=checkout, env=run_env, capture_output=True,
                        text=True, timeout=self.timeout_s,
                        # See the class docstring: without this opencode never returns.
                        stdin=subprocess.DEVNULL)
                stdout, stderr, code = result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired as expired:
                # Keep what the agent produced before the clock ran out. A
                # timed-out attempt still consumed tokens and took steps, and
                # those are the measurements the benchmark exists to collect;
                # discarding them reports a real, expensive attempt as a blank
                # row and biases every token average downward.
                stdout = _as_text(expired.stdout)
                stderr = (_as_text(expired.stderr)
                          or f"timed out after {self.timeout_s}s")
                code = -1

        (workdir / "opencode.jsonl").write_text(stdout)
        outcome = AttemptOutcome(raw={"returncode": code, "stderr": stderr[-2000:],
                                      "elapsed_s": round(time.time() - started, 1)})
        if code != 0:
            outcome.error = (stderr or stdout)[-800:]
        outcome = self.parse_events(stdout, outcome)
        outcome.patch = self.diff_checkout(checkout)
        return outcome

    @staticmethod
    def parse_events(stdout: str, outcome: AttemptOutcome) -> AttemptOutcome:
        """Mine opencode's JSON event stream for exact usage.

        Tokens are reported per assistant part and are cumulative *within* a part,
        so the totals take the maximum seen rather than a sum — adding them would
        multiply the real figure by the number of update events, which for a long
        task is a large and entirely invented number.
        """
        tokens = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0,
                  "cache_write": 0}
        cost = 0.0
        tools = set()
        parts = 0

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            part = event.get("part") or {}
            if not isinstance(part, dict):
                continue
            parts += 1
            usage = part.get("tokens") or {}
            if isinstance(usage, dict):
                cache = usage.get("cache") or {}
                for key, value in (("input", usage.get("input")),
                                   ("output", usage.get("output")),
                                   ("reasoning", usage.get("reasoning")),
                                   ("cache_read", cache.get("read")),
                                   ("cache_write", cache.get("write"))):
                    if isinstance(value, (int, float)):
                        tokens[key] = max(tokens[key], int(value))
            if isinstance(part.get("cost"), (int, float)):
                cost = max(cost, float(part["cost"]))
            if part.get("type") == "tool":
                tools.add(part.get("id") or part.get("callID") or len(tools))

        outcome.tokens_input = tokens["input"]
        outcome.tokens_output = tokens["output"] + tokens["reasoning"]
        outcome.tokens_cache = tokens["cache_read"] + tokens["cache_write"]
        outcome.cost_usd = cost
        outcome.steps = len(tools) or parts
        outcome.raw["usage_source"] = "opencode-json"
        outcome.raw["events"] = parts
        return outcome


class PhronixOpenCodeArm(OpenCodeArm):
    """Shared config for both phronix arms — identical but for store writability.


    These arms deploy ``AGENTS.md`` into the checkout, and that is load-bearing
    rather than incidental. Registering the MCP server only makes the tools
    *available*; a model given an unfamiliar tool surface and no reason to touch
    it will do the task the way it always would. The first smoke run showed
    exactly that — the server was connected, and ``retrievals.jsonl`` was empty
    for the whole task. The arm was measuring bare opencode under another name.

    The text is not written here. It is :func:`phronix.bootstrap.instructions_block`
    — the same block ``phronix deploy`` writes into a real project — so the arm
    tests the framework as shipped rather than a prompt tuned for the benchmark.

    This does mean the phronix arms see instruction text the bare arm does not,
    so ``opencode-bare`` vs ``opencode-phronix`` confounds *scaffolding* with
    *learning*. That is what :class:`PhronixFrozenArm` is for: identical
    instructions, identical tools, read-only store. bare→frozen is the cost of
    the scaffold; frozen→learning is the claim.
    """

    uses_phronix = True

    #: Both phronix arms retry to the full budget. In the writable arm a retry
    #: reads what the last failure taught the store; in the frozen control it
    #: does not, which is precisely the difference being measured.
    full_retry_budget = True

    #: The agent opencode is launched as.
    #:
    #: The healer, not the router, and the distinction is not cosmetic. Phronix
    #: agents carry a scoped allowlist (``'*': deny`` plus named tools), which is
    #: right for delegated specialists but decides what a *primary* agent can do
    #: at all. The router is a scoping agent: Read/Grep/Glob, no Bash, Edit or
    #: Write, so launched as primary it cannot change a line of code — the first
    #: run under it failed both tasks in seconds. The healer is phronix's
    #: fix-and-learn actor and holds the full implementation set alongside 21
    #: phronix tools, which is exactly a SWE-bench instance's shape: diagnose,
    #: edit, verify, record what was learned.
    agent_name = "phronix-healer"

    #: The agent that runs the learning pass. Phronix ships one whose entire
    #: purpose is turning a finished piece of work into stored knowledge; it was
    #: present in the store and never invoked.
    learn_agent_name = "phronix-learner"

    #: Learning is a short, bounded pass — read the diff, write it up. It gets a
    #: fraction of the task budget so a runaway learner cannot dominate a run.
    learn_timeout_s = 240

    #: The agent that researches an uncovered subject before the first attempt.
    research_agent_name = "phronix-researcher"


    #: One research pass, and a short one. Measured: the three-stage design cost
    #: ~10 minutes for a first pass against a ~6 minute baseline attempt, which
    #: is more than the thing it advises.
    research_timeout_s = 240

    def write_scaffold(self, checkout: Path) -> None:
        """Deploy the instruction block *and* render the phronix agents.

        Rendering the agents is the part that was missing, and its absence made
        the arm meaningless: the store held seven agent definitions, none reached
        the checkout, and opencode ran its own default agent. Phronix's whole
        design is that an agent carries the standing instructions and a scoped
        tool list; without this the arm was bare opencode plus an unread-looking
        markdown file, and it used zero phronix tools across a full task.
        """
        from phronix.agents import install_agents
        from phronix.bootstrap import instructions_block

        (checkout / "AGENTS.md").write_text(instructions_block() + "\n")
        install_agents(target_root=checkout, harnesses=["opencode"])
        self._retarget_agents(checkout / ".opencode" / "agents")

    #: Prompt for the learning pass. Deliberately insists on a written artefact
    #: and names the exact tools, because the failure mode measured here was not
    #: an agent that refused to learn — it was an agent that meant to and never
    #: got round to it while absorbed in the fix.
    #: The learner's own agent, carrying the two learning skills.
    #:
    #: Named rather than prompted: the method — what counts as a pattern, where
    #: a block goes, when to build a tool instead — lives in
    #: `phronix-learning-capture` and `phronix-learning-reconcile`, which the
    #: learner can improve for itself. A method pasted into a prompt here is a
    #: method the learner cannot edit, and this learner is supposed to get
    #: better at learning.
    learner_agent_name = "phronix-always-on-learner"

    LEARNER_PROMPT = """\
Run one **{cycle}** cycle. `skill_load("{skill}")` is your first action and the
skill is the method; this message is only the input.

Since the last cycle, these were reported:

{observations}

Each line opens with the KIND of work it is about. You have been given one
kind's worth and another worker has the others, so nothing you write can collide
with theirs.

Lines marked **repeated** were said more than once. That is a reason to widen
and firm up what is already written, not a filter on what is worth writing —
everything here gets recorded.
"""

    LEARN_PROMPT = """\
The task attempt just finished. Your only job now is to record what it taught
this system, so the next session does not rediscover it. Do not edit any source.

Two files are attached and they are your evidence:

- `attempt-diff.patch` — exactly what the agent changed.
- `attempt-notes.md` — the issue, the agent's own account of what it tried, and
  **how the attempt was judged**: which target tests still fail, which
  regressions it caused, and the locations previous attempts already tried.

Read them. They are the record of the attempt; the repository alone will not
tell you what was investigated or why.

**Write short, actionable entries. This is the constraint that matters most.**

- A rule or instruction is at most a few sentences and states a *directive*:
  what to do or not do, and where. Not a plan, not a checklist, not a debugging
  walkthrough. If you find yourself writing "Step 1... Step 2... investigate
  whether...", you are writing a research note, and it will be retrieved by a
  future session that then has to redo your reasoning to extract the point.
- One idea per block. Split rather than combine.
- Lead with the directive, then one line of why.

Measured consequence of ignoring this: a previous run wrote a 12 KB skill whose
buried third bullet of one instruction contained the correct fix. Three later
attempts retrieved that skill and none acted on it. Length destroyed it.

**Only record what the evidence supports.**

- If you verified it — the test output shows it, the diff shows it — state it
  plainly.
- If you are inferring, write it as `Hypothesis:` and say what would confirm it.
  Never write a guess as a Rule. A previous run recorded "this test does not
  exist, it is a placeholder name" as fact; the test existed and the claim became
  permanent, confidently wrong knowledge.

**If several attempts failed in the same place, record that as an exclusion.**
"The cause is not in X — N attempts changed it and the target test still failed"
is often the most valuable thing you can leave behind. Knowledge that only ever
accumulates about the area already being tried makes the next attempt more
confident and no more correct.

Then write it down. At minimum, make ONE of these calls:

- `skill_write(skill=..., kind="lesson", title=..., body=...)` — symptom, root
  cause, exact fix. Use this for anything that cost you time to work out; it is
  filed under the skill's lessons automatically.
- `skill_write(skill=..., kind="instruction"|"rule", ...)` — a procedure or
  constraint that will hold next time.
- `memory_write(...)` — a durable fact about this codebase.

Name the skill after the *subject*, not the task: `sympy-units-dimensions`, not
`fix-issue-24066`. A skill that names one instance is never retrieved again.

Finish by stating which calls you made. If you truly learned nothing reusable,
say that explicitly and why — but that is rare after a real debugging session.
"""

    # ---------------------------------------------------------------------
    # The research flow. Eight stages, parallel at exactly two of them.
    #
    # A parallel stage costs its SLOWEST member and every member costs tokens,
    # so parallelism is spent only where the work genuinely splits: independent
    # questions in stage 3, independent approaches in stage 6. Everything else
    # is one short sequential pass.
    #
    # This replaced a design that ran scope -> four parallel aspects ->
    # reconcile before every attempt. Measured, that took ten minutes for a
    # first pass against a six-minute baseline attempt, and produced sixteen
    # approaches with zero trials between them: proposing is cheap, evaluating
    # is not, and nothing forced the second.
    # ---------------------------------------------------------------------

    SURVEY_PROMPT = """\
Get oriented on this task. Do not edit anything and do not propose a fix yet.

Topic key: `{topic}`

1. `research_prior(question=...)` — describe this task in your own words and
   see what is ALREADY on record: skills covering it, earlier research, which
   approaches were tried, which worked, which were refuted, which aspects are
   settled. Research carries across runs, so this is often not empty.
2. `graph_query` for the same subject. The graph indexes every layer's skills
   and research, so it reaches related subjects that share no vocabulary with
   your question — exactly the ones you would otherwise rediscover.
3. `research_assess(task=...)` — if the library already covers this, say so and
   stop.
4. `research_backups(topic="{topic}")` and `research_ruled_out(topic="{topic}")`
   — what earlier rounds of THIS topic found and what they disproved.
5. Read the issue, then look the problem up outside this checkout: the
   project's issue tracker, whether it was fixed upstream, the shape of the fix.

Report what this task IS — the behaviour, where it plausibly lives, what is
already known. You are establishing the question, not answering it.

Say explicitly which parts are already answered by steps 1 and 2 and which are
genuinely open. The next stage plans around that split, and anything you list as
open will be investigated at full price.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    PLAN_PROMPT = """\
Write the research plan. Do not edit anything and do not fix anything.

Topic key: `{topic}`

Three things, in this order:

1. **The metric.** `research_define_fom(...)` — the number that decides which
   approach is better, derived from THIS task and what the survey found, with
   `measure` stating exactly how it is obtained.
2. **The dataset.** `research_declare_corpus(...)` with the axes along which
   cases differ here, then `research_add_instances(...)` and
   `research_split(...)`.

   **At least twenty instances**, each checkable in seconds. Twenty is not
   arbitrary: the split holds back 20% as the unseen set, so a corpus of ten
   decides everything on two cases, and two cases can be passed by accident.

   They must be genuinely diverse — spread across the axes you just declared,
   not twenty spellings of one case. A corpus that varies in one dimension
   measures that dimension and reports it as correctness. Cover the boring
   directions too: the relative form as well as the absolute, the nested case as
   well as the top level, the one that should NOT match as well as the one that
   should. Negative cases matter most, because a change that ignores everything
   passes every positive case there is.

   This is the step that most often does not happen: declaring the axes is quick
   and satisfying, and then the instances never get written, so the evaluation
   stage has nothing to measure against and spends its budget discovering that.
   Add the instances in the same breath as the axes, and call `research_split`
   before you finish.
3. **The aspects.** `research_set_aspects(...)` — the independent questions to
   investigate, in priority order. Each must be answerable without waiting on
   the others, because they are investigated in parallel.

   Plan around what is already known. Call `research_prior(question=...)` again
   if the survey did not hand you its result. An aspect the record already
   settles will be re-checked rather than re-investigated, which is cheap — so
   it costs you nothing to list it, and listing it is how the re-check happens.
   But do not spend a NEW aspect on ground that is already covered: aspects are
   the expensive stage, only a few run, and one spent re-deriving a known answer
   is one not spent on the part nobody has looked at.

Do not propose approaches yet. This stage decides how the question gets
answered, not what the answer is.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    ASPECT_PROMPT = """\
Investigate ONE aspect of a task already under research, and try what you find.

Topic key: `{topic}`

## Your aspect

**{name}**

{question}

{where}

Stay on this aspect. The others are being investigated in parallel and the
findings are collected afterwards: straying duplicates their work and leaves
yours undone.

Search outside the checkout where the aspect calls for it, then ground what you
find in this code at THIS version.

## Try what you find — do not stop at a theory

You have your own private git worktree at `{workspace}`. Edit it freely; it is
discarded when you finish and it is not the checkout the attempt is diffed from.

When this aspect turns up a plausible cause, **change the code and see**. Then:

- `research_status(topic="{topic}")` for the corpus. Run the **train** and
  **validate** instances only — `test` is held out and there is no way to un-see
  it;
- `research_record_trial(topic="{topic}", approach=..., instance=..., passed=...)`
  for each, failures included;
- `research_add_approach(...)` with `measurement` saying exactly how you got the
  numbers — the commands you ran, the change you applied.

An approach recorded with real trials behind it is worth more than three
theories, and the difference is not stylistic: `research_choose` will not select
on predictions, because an argmax over predictions returns whatever the agent
already believed. Measured here, repeatedly: a research pass ended with its
top-ranked approach scoring **0.0** and every other candidate unmeasured, so the
attempt implemented the only thing carrying a number — a number that said it did
not work.

If the change falls short, that is a finding too. Record the trials, say what
failed, and — when the idea was right and merely incomplete — refine it with
`research_refine_approach` and measure again rather than abandoning it.

Investigating without trying is what leaves the whole decision to a later stage
that has less context than you do right now.

## You are on a clock, and the write-up is not

This stage has a {budget}s budget and it is for INVESTIGATING. Spend it looking.

When you are done — or when you judge the time nearly gone — write everything
you learned to `{dump}`. Raw notes are fine: findings, the code paths you
confirmed, what you ruled out, what you were still unsure about, URLs. Do not
polish it and do not summarise it away. Nobody reads it for style; a separate
step reads it to file the findings, and that step is not on a clock.

The one outcome to avoid is being cut off mid-investigation with nothing
written down. Everything in that file survives. Everything only in your head
does not.

Report what you established AND what you ruled out — a dead end recorded is
worth more than a dead end rediscovered.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    ASPECT_RECHECK_PROMPT = """\
Earlier research already settled this aspect. Confirm it still applies. Do not
re-investigate it, and do not edit any source.

Topic key: `{topic}`
Aspect: **{name}**

The question it answered:

{question}

What was established:

{findings}

Your job is narrow. Check that the claims above still hold for the code at THIS
version — the file still exists, the function still looks the way the finding
says, the behaviour still reproduces. Read the specific places the findings
name; do not go looking for new ones.

Then write to `{dump}`:

- `STILL APPLIES` and which claims you checked, or
- `NO LONGER APPLIES` and exactly which claim broke and what the code does now.

A finding that has drifted is the most valuable thing you can report here, so
say so plainly rather than reinterpreting it to fit. If it has drifted badly
enough that the aspect needs real investigation again, say that too.

This is deliberately a small job. Re-deriving what is already on file costs the
full price of the original investigation and tends to produce a second,
slightly different account of the same thing.
"""

    ASPECT_RECORD_PROMPT = """\
File the findings from one aspect investigation. Do not edit any source. Do not
investigate anything new.

Topic key: `{topic}`
Aspect: **{name}**

The investigation's raw notes are at `{dump}`. Read that file.

Your whole job is to get what is in it onto the record:

- `research_add_approach(...)` for each candidate it identified, with the
  `hypothesis` it gives and the `source` it cites. Record the ones the notes
  argue AGAINST too, with what refuted them in the summary — a candidate
  recorded as refuted is what stops the next session proposing it again.
- `skill_write` for anything durable about the subject that is not a candidate:
  a dead end worth not repeating, a constraint, how something actually works.

This step is deliberately separate from the investigation and is NOT on a
budget. The investigation was, and a stage that is cut off while writing up
loses everything the investigation found — the search was paid for and the
findings evaporate. So take the time to file all of it.

If the notes file is missing or empty, say so plainly and stop. Do not
reconstruct findings you do not have; an invented finding is worse than a
missing one, because the next session cannot tell the difference.
"""

    COLLECT_PROMPT = """\
Summarise what the parallel investigations found. Nothing else.

Topic key: `{topic}`

**Do not investigate.** Do not read source files, do not search the web, do not
run commands. The investigation already happened; your job is to state its
result. Measured: given a free hand, this stage made 58 tool calls and ran to its
budget re-doing the work that had just been done in parallel.

Call `research_status(topic="{topic}")` once. Then write, in a few lines each:

- what each aspect established, and what it ruled out;
- where they agree, and where they contradict;
- which questions remain open.

Then stop. Do not propose approaches — the next stage does that, from this.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    RESUME_NOTE = """\

## This is a retry — start from the checkpoint

Earlier attempts on this task already researched it. `skill_load("{skill}")`
and read the block **Where research on this subject stands**: what is
established, what is still open, what has been ruled out, and where the detail
lives if you need it.

Continue from there. Do not re-establish what it lists as established, and do
not re-propose what it lists as ruled out — the previous attempts paid for those
findings and repeating them is how a task spends five tries making the same
discovery.

The open items are your work. If the checkpoint is thin it is because an earlier
pass was cut short, and the references tell you where to pick up.

## First, read the failure and decide which kind it was

`attempt-notes.md` has the judged result of the last attempt: the target test
that still fails, and its actual output. Read that BEFORE proposing anything,
and classify what it shows. There are two kinds of failure and they lead
opposite ways:

**The idea was right, the change was incomplete.** The edit was in the right
function, it ran, and it missed a case — a path that was not normalised, a
branch that was not covered, a condition that was too narrow. The evidence is
that the mechanism engaged and the outcome was still wrong in a specific,
nameable way.

  -> `research_refine_approach(topic="{topic}", key=..., diagnosis=..., change=...)`

  This keeps the ground the last attempt won. Abandoning a right-but-incomplete
  approach is how a task walks away from an answer it was one line from having.

**The idea was wrong.** Nothing changed, the mechanism never engaged, or the
failure is unrelated to what was edited.

  -> propose something genuinely different: a different layer, a different
  mechanism, a different reading of what the reporter observed, or how the
  project itself fixed it upstream.

`research_add_approach` refuses a failed name, and the refusal tells you the key
to refine if refining is what the evidence supports. Do not rename a failed
approach to get around the refusal — that is neither of the two paths above, and
it costs a full attempt to rediscover the same result. A lineage can be refined
twice; after that the diagnosis is the thing that is wrong, so look elsewhere.

"""

    DIAGNOSE_PROMPT = """\
An attempt just failed. Work out why, and make sure it cannot fail that way
again. Do not edit source files.

Topic key: `{topic}`

`attempt-notes.md` is attached: the target test that still fails and its actual
output. That output is the job. You are not researching this subject again — the
last pass did that, and the attempt it produced was close enough to be judged.
You are reading one failure and deciding what was missing.

## 1. Build the failing case, as something you can run

Before diagnosing anything, turn the failure output into a reproduction, and
write it to `{scratch}`:

- set up the conditions the output shows — the same working directory, the same
  arguments, the same configuration;
- run it against the current checkout, with the last attempt's change in place,
  and confirm it fails **the way the output says**;
- keep it small enough to run in seconds.

If your reproduction passes, your reading of the failure is wrong and everything
built on it will be wrong too. Go back to the output until it fails for the
reason it claims.

This is the most valuable thing you produce here. The last attempt had its own
reproduction, that reproduction passed, and it shipped a fix that did not work —
because the case it built was easier than the case it was judged on. Make this
one match what actually failed, including the details that look incidental: the
directory you run from, whether the path is relative, how the pattern is
anchored. Those details are usually the bug.

## 2. Say which kind of failure it was

**Did the change engage?** Did the code it edited run, in the right place, and
produce a wrong result in a specific, nameable way?

**Yes — the idea was right and incomplete.** The common case for a near miss,
and the one worth taking seriously: the ground the attempt won is real. Name the
missing case exactly — an unnormalised value, a branch not covered, a condition
too narrow — and record it:

    research_refine_approach(topic="{topic}", key=<the failed key>,
                             diagnosis=<what the output showed>,
                             change=<what will be different, and the path to
                                     the reproduction that proves it>)

**No — nothing engaged, or the failure is unrelated to what was edited.** Then
the idea was wrong. `research_add_approach` one or two genuinely different
candidates: a different layer, a different mechanism, a different reading of
what the reporter observed, or how the project fixed it upstream.

## 3. Put the failing case into the corpus, as a deterministic test

`research_add_instances(topic="{topic}", instances=[...])` with the case you
just reproduced, as a **test**-phase instance: name it, say what correct
behaviour looks like, and give the command that checks it.

This is what connects the diagnosis to the measurement. The revision is tuned
and scored by the same pipeline as any other candidate, so unless the failure
that actually lost the last attempt is IN the corpus, a revision can score 1.0
without fixing it — which is how an approach measured on a corpus the session
wrote for itself keeps beating the one that knows what went wrong.

## 4. Fix the OTHER pipelines against the same case too

The failing case is now a test instance, and it tests the *problem*, not the one
approach that lost. Every live approach in the skill is a fallback the next
attempt may reach, and one that has never been run against this case is a
fallback that will lose to it in exactly the same way.

`research_rank(topic="{topic}")` lists them. For each live approach with a
pipeline, decide from what you have just learned whether its steps handle this
case — and where they plainly do not, refine that approach too, or record a
trial showing it fails. A fallback known to fail the case is worth more than an
untested one: it stops the retry spending an attempt on it.

Do not re-tune them all by hand here; that is the tuning stage's job and it will
run against the enlarged corpus. What you are doing is making sure the case you
just found is one every candidate has to answer.

## 5. Leave the test behind, not just the diagnosis

Put the reproduction path in the `change` text and in the skill, so the next
attempt runs it instead of re-deriving it. The rule for the next attempt is
simple and you are writing the thing that enforces it: **it must not fail again
the way this one did.** A revision that cannot demonstrate the old failure is
now fixed is not a revision.

Finding something else on the way is fine and worth recording. Failing the same
way twice is not.

Do not re-survey the repository, re-plan aspects, or re-propose the whole space.
That work is done and on record; repeating it costs a full pass to arrive back
where the last one left off. One targeted revision beats four fresh candidates,
because the failure output is evidence no amount of fresh proposing has.

Report: which of the two it was, the key you recorded, the reproduction path,
and the instance you added.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    PROPOSE_PROMPT = """\
Propose the approaches, from what the investigation found. Do not edit anything.

Topic key: `{topic}`

Before proposing anything, `research_prior(question=...)`. Approaches under
`already_tried` have been proposed on this subject before — do not re-propose
one unless this round produced evidence the earlier attempt did not have, and
say what that evidence is. Ones under `known_refuted` are dead; ones under
`known_working` solved a real task and should be your first candidate here.

Re-proposing a tried approach is the specific failure this guards against: it
reads as convergence, it costs a full evaluation to rediscover the same result,
and the record ends up with two entries for one idea.

Record **two to four** approaches with `research_add_approach`, each carrying:

- `hypothesis` — what you believe is true and what would show it false;
- `source` — the issue, commit or documentation it came from;
- `summary` — concretely WHERE the change goes;
- `aspect` — which investigation produced it.

Then, for each one, `research_record_pipeline(topic="{topic}", key=..., steps=[...])`:
**the ordered steps that approach runs.** That is what an approach *is* — a way
of solving the problem, and a way is a sequence of steps. A name and a paragraph
is a description of one.

Tag every step `deterministic` (same inputs, same outputs — it becomes a
capability the attempt calls by name) or `judgement` (it genuinely needs a
model). Prefer deterministic: when a step feels like judgement, ask what it
would take to make it a tool, because usually it is judgement about *which*
inputs wrapped around something mechanical.

The pipelines are what get tuned, measured and — for the winner — written into
the skill. An approach without one cannot be run, only argued about.

Two to four, and genuinely different. Each one costs the next stage a full
evaluation, and an approach nobody can afford to evaluate is not a candidate.
If the investigation supports only one, record one rather than padding.

## When an earlier approach has already failed

`research_add_approach` will REFUSE a name that a real task tried and lost with.
That refusal is not an obstacle to work around by renaming — the same idea under
a new name costs another full attempt to rediscover the same result.

First ask what the failure actually showed. If the change ran, in the right
place, and missed a specific case, the idea was right and incomplete: call
`research_refine_approach(topic="{topic}", key=..., diagnosis=..., change=...)`
with what the test output said and what will be different. Walking away from a
right-but-incomplete approach loses ground the last attempt paid for.

Otherwise the *class* of fix was wrong, so look somewhere genuinely different:

- a different layer — if the fix was tried where the value is used, look where
  it is produced, and vice versa;
- a different mechanism — if normalisation failed, is the comparison itself
  wrong? is the value even reaching the code you changed?
- a different reading of the issue — re-read what the reporter actually
  observed, not what the last approach assumed they meant;
- upstream — how did the project itself fix this, if it did? A failing local
  theory is the moment to go back to the issue tracker rather than press on.

`research_select(topic="{topic}")` names aspects nobody has investigated yet.
Those are where the next approach usually is.

Never conclude that no approach exists. If everything on record has failed, the
search has been too narrow, and the correct response is to widen it — not to
re-propose a loser with more detail attached.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    EVALUATE_PROMPT = """\
Measure ONE approach. Be quick: you have a few minutes, and two other approaches
are being measured at the same time.

Topic key: `{topic}`
Approach: **{name}**

{summary}

Hypothesis under test: {hypothesis}

You are working in your own private checkout at `{workspace}` — a git worktree
made for this measurement alone. Edit it freely: nothing you do here reaches the
patch under test, and no other evaluator can see it. Do not copy the repository
and do not revert at the end; the worktree is discarded for you.

**The research data lives behind the phronix tools, not on disk.** Call
`research_status(topic="{topic}")` to see the instances. Do NOT go looking for
files: there is no `.research/` directory, nothing under `~/.local/share`, and
searching for one wastes the whole budget. Measured: evaluators spent their
entire allocation running `find` and `ls` for a store that is only reachable
through the tools.

Then:

1. Apply the approach directly to the working tree. **It is yours** — a private
   git worktree, not the shared checkout — so edit freely and do not copy
   anything anywhere. It is discarded when you finish.
2. Run ONLY the **test** instances — the held-out set. Skip train and validate:
   those are the tuning surface, they were used to refine this approach, and an
   approach measured on what it was tuned against reports how well it was tuned.
   If `research_status` shows no test instances at all, say so and record
   nothing — a score with no held-out evidence behind it is worse than no score,
   because everything downstream treats it as measurement.
3. Record each outcome with `research_record_trial(topic="{topic}",
   approach="{name}", instance=..., passed=...)`, failures included.
4. `research_evaluate_approach(topic="{topic}", approach="{name}")`.

This is the FINAL measurement. Do not refine, do not adjust, do not re-run after
a change: the moment this approach is altered in response to what the held-out
set said, the held-out set has been tuned on and there is nothing left that can
falsify anything. Tuning had its own stage and its own instances.

Report the score and whether the hypothesis survived. A refuted hypothesis is a
result; do not rescue it by turning this into a different approach.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    TUNE_PROMPT = """\
Tune ONE approach against the tuning instances. This is where it is allowed to
improve; the next stage measures it and nothing may change after that.

Topic key: `{topic}`
Approach: **{name}** (key `{key}`)

{summary}

Hypothesis under test: {hypothesis}

You are in your own private git worktree at `{workspace}`. Edit freely; it is
discarded when you finish.

1. `research_status(topic="{topic}")` for the instances. Use the **train** and
   **validate** ones ONLY. The `test` instances are held out — running them here
   is what a held-out set exists to prevent, and there is no way to un-see them.
2. Apply the approach and run the tuning instances. Record every outcome with
   `research_record_trial(topic="{topic}", approach="{name}", instance=...,
   passed=...)`, failures included.
3. **If instances fail, that is the point of this stage — improve it.** Read why
   they failed and ask: did the change engage and miss a case, or was the idea
   wrong?

   **Engaged and missed a case** — name the case and call:

       research_refine_approach(topic="{topic}", key="{key}",
                                diagnosis=<what the failing instances showed>,
                                change=<what will be different>)

   Then apply the revision here, record its trials under the NEW name, and run
   the tuning instances again. Up to two revisions; a third means the diagnosis
   is what is wrong, not the implementation.

   **The idea was wrong** — stop and say so. An approach that cannot be made to
   pass its own tuning set is a finding, and a cheap one.

## Record the pipeline you just ran

`research_record_pipeline(topic="{topic}", key=<the final key>, steps=[...])`
with the ordered steps you actually carried out to apply and check this
approach. Tag each `deterministic` (same inputs, same outputs — it becomes a
capability the next attempt calls) or `judgement` (it genuinely needs a model).

You are the only stage that knows these steps are real: you just ran them. An
approach is a *way of solving the problem*, and a way is a sequence of steps —
a name and a paragraph of summary is a description of one. If this approach
wins, these steps become the skill, verbatim, so write them as the method for
this class of problem rather than a transcript of this instance.

Prefer deterministic. When a step feels like judgement, ask what it would take
to make it a tool: usually it is judgement about *which* inputs wrapped around
something mechanical, and the mechanical part is the capability.

Failing here does not refute anything: train is where approaches are discovered
and validate is where they are tuned, so a failure is unfinished work rather
than a refutation. That is exactly why refinement belongs here and not in the
stage that scores.

Report: the final key, what changed across the revisions, and the tuning result.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    REPAIR_COLLECT_PROMPT = """\
The repairs are done. Reconcile them before anything is scored.

Topic key: `{topic}`

Several approaches were just repaired in parallel against the same failing case,
each by an agent that could not see the others. `research_rank(topic="{topic}")`
lists them.

Answer three questions, briefly, and record what you find:

1. **Did they converge?** If two repairs made the same change for the same
   reason, that agreement is evidence about the CAUSE, not a coincidence — say
   so, because it is the strongest signal this pass produces.
2. **Did any repair contradict another?** One agent normalising a value while
   another rejects it means the two disagree about what correct behaviour is.
   That disagreement has to be settled here, not left for the held-out set to
   arbitrate by accident.
3. **Does any repair now cover a case another still misses?** Record a trial
   showing it, so the ranking reflects it.

Keep this short. Nothing is re-investigated here and no new approaches are
proposed — the repairs are done, this is the moment they stop being three
private conclusions and become one account.

Report: what agreed, what conflicted, and anything you recorded.
"""

    EXECUTION_PLAN_PROMPT = """\
Turn the research into the skill that solves this task. Do not edit source.

Topic key: `{topic}`

1. `research_rank(topic="{topic}")` — the ordering by measured score.
2. `research_adopt_pipeline(topic="{topic}")` — promote the winning approach's
   own pipeline to be the plan.

   The tuning stage recorded the steps it actually ran for each approach it
   measured, so the plan already exists and has been executed. Adopting it beats
   writing a fourth version of something established three times — the version
   typed at the end is the one nobody measured.

   Only if that returns `empty` does anything need writing:
   `research_write_plan(topic="{topic}", steps=[...])` — **the method**: the
   ordered steps that solve this class of problem, not a recording of the one
   change you happened to make.

   Write them so they would work on the next instance of this problem too. "Find
   every place the value is compared against the pattern" is a step; "edit line
   604" is a transcription. The particulars belong to the task; the sequence
   belongs to the subject, and the subject is what this skill is filed under.

   Tag each step:

   - `deterministic` — same inputs, same outputs, every time. **Build it**:
     `capability_new(...)` gives it a name the next attempt can simply call.
     Locating call sites, normalising a path, running the corpus, checking a
     regex against a set of inputs: all of these are tools, and each one built
     is work no future attempt pays for again.
   - `judgement` — a real decision that needs a model. Keep these few. Every
     step left as prose is read, interpreted and acted on afresh by every task
     that loads this skill.

   Prefer deterministic. When a step feels like judgement, ask what it would
   take to make it a tool — usually it is judgement about *which* inputs, wrapped
   around something mechanical, and the mechanical part is the capability.

   Do not skip this because the work already feels done. The corrector only
   knows what is on record: a pass that found the fix, measured it and never
   wrote the plan down verifies as `invariants fail: no plan recorded`, and one
   that tagged steps deterministic without building them fails as
   `N deterministic step(s) have no capability`. Both read as research that
   failed when it succeeded.
3. `research_playbook(topic="{topic}")` — this writes the skill. It is
   deterministic and it does the whole job: the steps as an ordered pipeline
   naming the tool for each, the ranked approaches, the figure of merit, the
   sources, the aspects investigated, what was tried and refuted. You do not
   need to write any of that out yourself.

   What comes out is the deliverable — the **solution file**: the leading
   pipeline in full, then the other measured approaches as fallbacks in ranked
   order, each as its own sequence of steps. An attempt that exhausts the first
   one finds the second one's steps, not a sentence about it.

4. **Build the tools, across every approach.** `capability_new(...)` for each
   deterministic step in each live pipeline — not only the winner's. The
   fallbacks are the path a retry takes, and a fallback whose steps have no
   tools is prose the next attempt has to interpret at the exact moment the
   cheap answer has already failed.

   `capability_list()` FIRST, and reuse what is there. These tools are
   task-shaped, so a step in this pipeline is often a step in one built for
   another task — under a different name, doing the same thing. If
   `capability_new` answers `duplicate` it is telling you a tool already exists:
   put that name in the step and move on. Three copies of one procedure have to
   be maintained, verified and chosen between, and choosing is a decision
   nobody meant to hand the next attempt.

   `research_verify` fails `invariants` while any deterministic step lacks a
   capability, so this is checked rather than hoped for.
5. **Build the research tools you wish you had had.** Look back over this
   pass: which steps did you carry out by hand that you would carry out again
   on any task in any repository? Setting up a fixture directory in a given
   shape, running one area's tests and parsing what failed, applying a
   candidate and reporting the figure of merit, finding every place a value is
   compared or normalised.

   `capability_list()` first, then `capability_new(...)` for each one, **named
   with a `probe_` prefix** — `probe_run_area_tests`, `probe_apply_and_score`.
   That prefix marks them as method rather than answer: they carry no knowledge
   about this task, so they are reused by every later run including the ones
   that deliberately start from nothing.

   This is the end of the pass on purpose. Building tools mid-investigation
   interrupts the investigation; doing it here costs one stage and pays back on
   every task that follows. The bar is not "is this profound", it is "would I
   write this again".

6. `graph_ensure(scope="knowledge")` — index what you just wrote.

   The attempt does not load this skill whole; it queries the graph for the one
   block it needs and fetches that section. That only works if the graph knows
   the skill exists, and this is the moment it changed.

7. `research_verify(topic="{topic}")` and report the verdict.

The skill IS the execution plan. It is filed under the subject rather than this
task, so the next task in the same area retrieves it instead of researching the
same ground again — which is the entire point of having done this.

Every approach is recorded as *potential*, the top-ranked one included. It led on
a corpus this session authored, which is a reason to try it first and not
evidence that it is right. It becomes *working* when a task passes with it.

Report: the skill name and the approach order.

## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)` whenever
something turns out to work or not: a technique that fixed a class of cases, a
tool whose output needed massaging, an approach that looked right and was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later
task the discovery. **`worked=false` is the more valuable report** and the one
nobody writes down: a dead end recorded costs the next task a sentence,
unrecorded it costs an attempt.
"""

    #: Stages that must be allowed to finish.
    #:
    #: The flow has two kinds of stage. The parallel ones — aspect, evaluate —
    #: explore: three run at once, and one cut short costs that branch and
    #: nothing else. The sequential ones are connective tissue. `plan` decides
    #: what the parallel investigation will even look at; `collect` is where
    #: three investigations become one account; `propose` turns that account
    #: into candidates; `execution-plan` writes the skill that is the entire
    #: durable output of the pass.
    #:
    #: Truncating one of those does not lose a branch, it loses the flow. A
    #: `collect` cut off half way discards what three investigators spent 700
    #: seconds finding, and `propose` then works from a partial summary — so the
    #: expensive stages were paid for and their findings thrown away. That is
    #: the worst outcome available, and it was happening at 60s budgets.
    MUST_FINISH_STAGES = ("plan", "collect", "propose", "diagnose",
                          "execution-plan", "aspect-record")

    #: Per-stage budgets in seconds.
    #:
    #: The connective stages get room to finish. Their ceilings are hang-guards,
    #: not work budgets — a stage reaching one means something is wrong, and
    #: status.sh reports it as a defect rather than as normal truncation.
    #: The exploratory stages keep real budgets: they are where an agent will
    #: happily read the whole repository, and cutting one short is survivable.
    STAGE_BUDGETS = {
        "survey": 180,
        "plan": 600,
        # Aspects TRY what they find and measure it, not just read — but they
        # do it in about two minutes.
        #
        # Measured live: three aspects, 118s wall, and the write-up 33s. The
        # budget was 540s, which never bound the common case and bound the bad
        # one far too late: the aspects are a barrier, so one straggler holds
        # `collect` and everything after it for as long as its ceiling allows.
        # A ceiling near the measured maximum makes the barrier predictable.
        "aspect": 300,
        # Filing findings is must-finish; this is a hang-guard, not a budget.
        # Measured at 33s, so 180 is generous and still bounds a hang.
        "aspect-record": 180,
        # Confirming that a settled finding still applies at this version is a
        # much smaller job than establishing it in the first place.
        "aspect-recheck": 150,
        "collect": 480,
        "propose": 600,
        # A retry's whole job, and must-finish: it reads one failure, builds a
        # reproduction and records one revision. Narrower than `propose` and
        # far more valuable, because it is the only stage that ever sees what
        # the task actually did when it was tried.
        "diagnose": 600,
        # Tuning is where the work happens now: measure, refine, re-measure,
        # up to two revisions. Evaluation that follows it is one clean pass over
        # the held-out set and needs far less.
        "tune": 600,
        "evaluate": 240,
        "execution-plan": 600,
    }

    #: Aspects investigated at once in stage 3, approaches evaluated at once in
    #: stage 6. Small, because a parallel stage costs its slowest member.
    #: How many aspects are investigated at once.
    #:
    #: Five, not three, and this widening is nearly free where the tuning tree's
    #: was not. Aspects have no merge above them — they fan out, write findings,
    #: and `collect` reads all of them — so the phase costs its slowest member
    #: whether there are three or eight of them. Measured: three aspects, 118s
    #: wall. What widening costs is tokens, and what it buys is coverage: an
    #: aspect nobody investigated is a question nobody asked.
    max_parallel_aspects = int(os.environ.get("PHRONIX_BENCH_ASPECTS") or 5)
    max_parallel_evaluations = 3

    def research(self, instance: Dict[str, Any], store_root: Path,
                 workdir: Path, attempt_index: int = 1,
                 notes: Optional[Path] = None, on_call=None) -> Dict[str, Any]:
        """Run the research flow, returning what it cost and what it concluded.

        Survey, plan, investigate (parallel), collect, propose, evaluate
        (parallel), rank (arithmetic, no agent), write the execution plan.

        A retry re-enters at *propose*: the survey and the plan do not change,
        because the task has not changed. What has changed is the record — the
        previous round's approaches are there and its failed locations are ruled
        out — so proposing again produces different candidates rather than the
        same ones at full price.
        """
        import subprocess
        from phronix import research as research_mod

        checkout = workdir / "repo"
        if not checkout.is_dir():
            return {"skipped": "no checkout"}

        self.research_topic_binding = self.research_topic(instance)
        topic = self.research_topic_binding

        issue_file = workdir / "issue.md"
        if not issue_file.is_file():
            issue_file.write_text(instance.get("problem_statement", ""),
                                  encoding="utf-8")
        brief_file = workdir / "task-brief.md"
        brief_file.write_text(self.task_brief(instance, checkout),
                              encoding="utf-8")

        env = self.phronix_env(tool_path_env(
            isolated_env(store_root, workdir / "cache")))
        env.update(model_env(base_url=self.base_url))
        env["PHRONIX_WRITE_LAYER"] = "project"
        # See `solve` above — this is the research half.
        env["PHRONIX_PHASE"] = "research"
        if self.store_readonly:
            env["PHRONIX_BENCH_FROZEN"] = "1"
        # Anything that reaches for a temp file without being told — a helper
        # the agent shells out to, tempfile.mkstemp inside a probe script —
        # lands in the scratch directory too, not in the system temp.
        for name in ("TMPDIR", "TMP", "TEMP"):
            env[name] = str(checkout / RESEARCH_SCRATCH)
        env["PHRONIX_RESEARCH_SCRATCH"] = str(checkout / RESEARCH_SCRATCH)

        # The issue is large — 24 KB on a typical instance — and re-attaching it
        # to all eight stages costs more context than the stages that never
        # reason about it can justify. An aspect investigator has one specific
        # question, the collector summarises what others found, and an evaluator
        # tests one approach; none of them needs the whole bug report.
        context_paths = [issue_file, brief_file]
        if notes is not None and Path(notes).is_file():
            context_paths.append(Path(notes))
        full_context = self.attachments(context_paths)
        brief_only = self.attachments([brief_file])

        started = time.time()
        transcripts: List[str] = []
        stages: List[str] = []
        stage_detail: List[Dict[str, Any]] = []
        code = 0

        def stage(name: str, prompt: str, budget: int,
                  attachments: Optional[List[str]] = None,
                  workdir_override: Optional[Path] = None) -> None:
            nonlocal code
            narrate = ((lambda text: on_call(f"[{name}] {text}"))
                       if on_call else None)
            where = workdir_override or checkout
            # Each evaluator runs in its own worktree, so the scratch directory
            # it is told about has to be the one inside *its* tree.
            stage_env = dict(env)
            stage_scratch = where / RESEARCH_SCRATCH
            stage_scratch.mkdir(parents=True, exist_ok=True)
            for key in ("TMPDIR", "TMP", "TEMP", "PHRONIX_RESEARCH_SCRATCH"):
                stage_env[key] = str(stage_scratch)
            # Which research stage a retrieval came from. Survey loading a skill
            # and execution-plan loading one mean different things: the first is
            # orientation, the second is the plan actually being built out of it.
            stage_env["PHRONIX_STAGE"] = str(name)

            stats: Dict[str, Any] = {}
            stage_started = time.time()
            # On a retry every stage opens with the checkpoint, so no stage
            # rebuilds a picture the last attempt already paid for.
            resume = ""
            if attempt_index > 1:
                pinned = self._in_store(store_root, research_mod.topic_skill,
                                        topic) or ""
                if pinned:
                    resume = (self.RESUME_NOTE.replace("{skill}", pinned)
                              .replace("{topic}", topic))

            # Through the same seam the attempt uses.
            #
            # This built an opencode command inline, so the Claude arm — whose
            # attempt path was routed correctly — invoked the Claude binary with
            # `run --dir ... --auto --format json`, which it does not understand.
            # It exited in seven seconds with empty output, and the trace said
            # "no phronix tools called", which reads as an agent that ignored
            # its tools rather than one that never started.
            out, rc = stream_opencode(
                self.agent_command(
                    LOG_NOTE + SCRATCH_NOTE + resume
                    + prompt.replace("{topic}", topic),
                    where,
                    full_context if attachments is None else attachments,
                    self.research_agent_name),
                where, stage_env, budget, narrate, root=where, stats=stats)
            if rc != 0:
                code = rc
            transcripts.append(out)
            stages.append(name)

            # Per-stage cost, so "research took eleven minutes" can be answered
            # with *which* stage took them. Parsed from this stage's own
            # transcript rather than the concatenation, which is the only way to
            # attribute tokens to the stage that spent them.
            counted = self.parse_events(out, AttemptOutcome())
            must_finish = name.split(":", 1)[0] in self.MUST_FINISH_STAGES
            if must_finish and stats.get("truncated") and on_call:
                on_call(f"[{name}] ** this stage was meant to run to completion "
                        f"and hit its {budget}s guard instead — the stages that "
                        "fed it were paid for and their findings are now partial")

            stage_detail.append({
                "stage": name,
                "must_finish": must_finish,
                "elapsed_s": stats.get("elapsed_s",
                                       round(time.time() - stage_started, 1)),
                "budget_s": stats.get("budget_s", budget),
                "truncated": bool(stats.get("truncated")),
                # Set by `stream_opencode` when the harness reported the
                # account's window rejected during this stage.
                "rate_limited": bool(stats.get("rate_limited")),
                "resets_at": stats.get("resets_at"),
                "returncode": rc,
                "steps": counted.steps,
                "tokens_input": counted.tokens_input,
                "tokens_output": counted.tokens_output,
                "tokens_cache": counted.tokens_cache,
                "cost_usd": counted.cost_usd,
            })

            # Harvest after EVERY stage, not once at the end.
            #
            # A stage that is truncated, or a pass killed by the task's budget,
            # otherwise loses everything it established — and the next task on
            # the same subsystem re-derives it. Harvesting is deterministic file
            # work on a record that is already structured, and it is idempotent,
            # so running it eight times costs nothing and means the knowledge
            # survives whichever stage happens to be the last one to run.
            self._in_store(store_root, research_mod.harvest, topic)
            # And the checkpoint: what is established, what is open, what is
            # dead, plus references. Deterministic and unbudgeted, so a pass cut
            # off at any point still leaves the next one somewhere to start.
            self._in_store(store_root, research_mod.checkpoint, topic)

        def private_tree(label: str) -> Tuple[Path, str]:
            """A git worktree of its own, so parallel agents cannot collide.

            They were all editing the SAME working tree, so each measured a
            mixture of everybody's edits — three concurrent agents applying
            three different patches to one checkout and testing whatever
            happened to be on disk. A worktree is cheap (git shares the object
            store, so it is a checkout of files, not a copy of history) and it
            makes the isolation real rather than assumed.

            Returns the directory to work in and a note when it could not be
            made — falling back to the shared checkout is worse than a worktree
            and far better than not running.
            """
            tree = checkout / SCRATCH_DIR / label
            made = subprocess.run(
                ["git", "worktree", "add", "--detach", "--force",
                 str(tree), "HEAD"],
                cwd=checkout, capture_output=True, text=True)
            if made.returncode != 0:
                return checkout, made.stderr.strip()[-80:]

            # The worktree needs the harness scaffolding too.
            #
            # `git worktree add` checks out HEAD, and `.opencode/` is not in
            # HEAD — the harness writes it into the main checkout after
            # cloning. So an agent started in a bare worktree has no project
            # config, which is where the phronix MCP server is declared: it
            # comes up with none of the research tools and cannot record a
            # trial at all. That is not a loud failure — the stage exits early,
            # the ranking still reports scores, and those scores are
            # predictions rather than measurements, which is precisely what the
            # figure of merit exists to prevent.
            for item in (".opencode", "AGENTS.md"):
                source, link = checkout / item, tree / item
                if source.exists() and not link.exists():
                    try:
                        link.symlink_to(source)
                    except OSError:
                        pass
            return tree, ""

        def drop_tree(tree: Path) -> None:
            if tree is not checkout:
                subprocess.run(["git", "worktree", "remove", "--force", str(tree)],
                               cwd=checkout, capture_output=True, text=True)

        # The learner runs for the life of the arm, and starts before the
        # stages do.
        #
        # Started here because this is the first moment there is anything to
        # learn from, and left running afterwards: a pattern is a thing that
        # repeats, and repetition is only visible from above several tasks. A
        # harvest at the end of a pass can see what that pass did twice; it
        # cannot see what every pass has been doing wrong.
        self.start_learning(store_root, checkout, workdir, env=env,
                            on_learning=on_call)

        budgets = self.STAGE_BUDGETS

        if attempt_index <= 1:
            stage("survey", self.SURVEY_PROMPT, budgets["survey"])
            stage("plan", self.PLAN_PROMPT, budgets["plan"])

            aspects = self._in_store(store_root, self._load_aspects, topic) or []
            chosen = aspects[:self.max_parallel_aspects]
            if chosen:
                def investigate(aspect: Dict[str, str]) -> None:
                    name = aspect.get("name", "?")
                    safe = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                    dump = checkout / RESEARCH_SCRATCH / f"aspect-{safe}.md"
                    dump.parent.mkdir(parents=True, exist_ok=True)

                    # An aspect earlier research already settled is re-checked,
                    # not re-investigated.
                    #
                    # Research now carries across runs, so the second task on a
                    # subsystem arrives with the first task's findings in the
                    # store. Investigating them again from scratch pays the full
                    # 300s to reach a conclusion already on file — and, worse,
                    # tends to reach a slightly different one, so the store ends
                    # up with two accounts of the same thing.
                    settled = self._in_store(store_root,
                                             research_mod.settled_aspect, name)
                    if settled:
                        stage(f"aspect:{name}",
                              self.ASPECT_RECHECK_PROMPT.format(
                                  topic="{topic}", name=name,
                                  question=aspect.get("question", ""),
                                  findings=settled.get("findings", "")[:1200],
                                  dump=dump),
                              budgets["aspect-recheck"], brief_only)
                    else:
                        # Its own worktree: an aspect that may try things must
                        # not be trying them in the checkout the attempt is
                        # diffed from, nor in a tree two other aspects are
                        # editing at the same time.
                        tree, unavailable = private_tree(f"aspect-{safe}")
                        if unavailable and on_call:
                            on_call(f"[aspect:{name}] worktree unavailable "
                                    f"({unavailable}); investigating in place")
                        try:
                            stage(f"aspect:{name}",
                                  self.ASPECT_PROMPT.format(
                                      topic="{topic}", name=name,
                                      question=aspect.get("question", ""),
                                      where=(f"Where to look: {aspect['where']}"
                                             if aspect.get("where") else ""),
                                      budget=budgets["aspect"], dump=dump,
                                      workspace=str(tree)),
                                  budgets["aspect"], brief_only, tree)
                        finally:
                            drop_tree(tree)

                    # Filing what was found is a separate, unbudgeted stage.
                    # The investigation is what needs a clock; the write-up is
                    # what must not have one, because a stage cut off mid-write
                    # loses everything the investigation just paid for.
                    stage(f"aspect-record:{name}",
                          self.ASPECT_RECORD_PROMPT.format(
                              topic="{topic}", name=name, dump=dump),
                          budgets["aspect-record"], brief_only)

                with ThreadPoolExecutor(max_workers=len(chosen)) as pool:
                    list(pool.map(investigate, chosen))

            stage("collect", self.COLLECT_PROMPT, budgets["collect"], brief_only)

        if attempt_index <= 1:
            stage("propose", self.PROPOSE_PROMPT, budgets["propose"])
        else:
            # A retry diagnoses, it does not re-research.
            #
            # The revision pass used to run `propose` again, which asks for the
            # whole candidate space a second time — so a pass that had a
            # specific failure output in hand spent its budget re-deriving
            # alternatives instead of reading the one piece of evidence the
            # first pass did not have. Observed on pylint-7080: the attempt
            # failed by a missing normalisation, and the revision answered with
            # four fresh candidates rather than the one-line fix to the
            # approach that had already got everything else right.
            stage("diagnose",
                  self.DIAGNOSE_PROMPT.replace(
                      "{scratch}", f"{RESEARCH_SCRATCH}/repro"),
                  budgets["diagnose"])

        pending = [a for a in (self._in_store(store_root, research_mod.backups,
                                              topic) or [])
                   if a.get("status") in ("potential", "validated")]

        # On a retry the pipeline runs on the REVISION, not on the field.
        #
        # The first pass explores; a retry already knows where the answer is and
        # has a reproduction of the exact failure. Tuning three unrelated
        # candidates again costs the budget that should go into measuring the
        # one informed by what the task actually did — and it is how a fresh
        # approach with a corpus score keeps outranking the revision that
        # carries the diagnosis.
        #
        # Everything else about the pipeline is unchanged: the revision is
        # tuned on train+validate and scored on the held-out set exactly like
        # any other candidate. Narrower, not weaker.
        if attempt_index > 1:
            revisions = [a for a in pending if a.get("refines")]
            if revisions:
                pending = revisions
                if on_call:
                    on_call(f"[tune] retry: measuring "
                            f"{len(pending)} revision(s) only, not the field")
        pending = pending[:self.max_parallel_evaluations]
        def tune_one(indexed: Any) -> Dict[str, Any]:
            """Measure and improve ONE approach, in a worktree of its own."""
            index, approach = indexed
            name = approach.get("name", "?")
            target, unavailable = private_tree(f"tune-{index}")
            if unavailable and on_call:
                on_call(f"[tune:{name}] worktree unavailable "
                        f"({unavailable}); measuring in place")
            try:
                stage(f"tune:{name}",
                      self.TUNE_PROMPT.format(
                          topic="{topic}", name=name,
                          key=approach.get("key", ""),
                          summary=approach.get("summary", ""),
                          hypothesis=approach.get("hypothesis", ""),
                          workspace=str(target)),
                      budgets["tune"], brief_only, target)

                # Whatever tuning produced is what gets measured: a revision
                # carries a new name, and scoring the parent would grade the
                # version tuning already improved.
                final = (self._in_store(store_root, research_mod.final_revision,
                                        topic, approach.get("key", ""))
                         or approach)

                # Keep the change that was just measured. The worktree holds a
                # candidate that has been applied and run against the corpus;
                # discarding it leaves the attempt to reconstruct it.
                measured = subprocess.run(["git", "diff"], cwd=target,
                                          capture_output=True, text=True)
                if measured.returncode == 0 and measured.stdout.strip():
                    noted = self._in_store(
                        store_root, research_mod.record_change, topic,
                        final.get("key", approach.get("key", "")), measured.stdout)
                    if on_call and (noted or {}).get("status") == "ok":
                        on_call(f"[tune:{name}] recorded the measured change "
                                f"({noted['bytes']} bytes) on {noted.get('key')}")
                return final
            finally:
                drop_tree(target)

        def evaluate_one(indexed: Any) -> None:
            """Score ONE approach on the held-out set. Changes nothing."""
            index, approach = indexed
            name = approach.get("name", "?")
            target, unavailable = private_tree(f"eval-{index}")
            if unavailable and on_call:
                on_call(f"[evaluate:{name}] worktree unavailable "
                        f"({unavailable}); measuring in place")
            try:
                stage(f"evaluate:{name}",
                      self.EVALUATE_PROMPT.format(
                          topic="{topic}", name=name,
                          summary=approach.get("summary", ""),
                          hypothesis=approach.get("hypothesis", ""),
                          workspace=str(target)),
                      budgets["evaluate"], brief_only, target)
            finally:
                drop_tree(target)

        if pending:
            indexed = list(enumerate(pending, 1))
            if attempt_index <= 1:
                # First pass: tune and evaluate fuse per approach, so a fast
                # candidate is scored while a slow one is still tuning.
                def tune_then_evaluate(item: Any) -> None:
                    evaluate_one((item[0], tune_one(item)))

                with ThreadPoolExecutor(max_workers=len(pending)) as pool:
                    list(pool.map(tune_then_evaluate, indexed))
            else:
                # A retry REPAIRS, and repair has a barrier in the middle.
                #
                # The shape mirrors the research pass because the problem is the
                # same one: several agents work in parallel on separate
                # approaches, and what each learns about the failing case bears
                # on the others. Fusing tune into evaluate here would score each
                # revision before anybody had reconciled what the repairs found
                # — and the case that defeated the last attempt is precisely the
                # thing every candidate now has to answer.
                #
                # Nothing is re-explored: the repairs work on pipelines that
                # already exist, against a corpus that already exists, with the
                # diagnosis already written. That is the cheap part of research
                # and the only part a retry should be paying for.
                with ThreadPoolExecutor(max_workers=len(pending)) as pool:
                    repaired = list(pool.map(tune_one, indexed))

                stage("collect", self.REPAIR_COLLECT_PROMPT, budgets["collect"],
                      brief_only)

                with ThreadPoolExecutor(max_workers=len(repaired)) as pool:
                    list(pool.map(evaluate_one, list(enumerate(repaired, 1))))

        # Ranking is arithmetic over recorded trials: no agent, no argument.
        ranking = self._in_store(store_root, research_mod.rank_approaches,
                                 topic) or {}
        if on_call and ranking.get("ranking"):
            order = ", ".join(f"{row['name']}={row['score']}"
                              for row in ranking["ranking"][:4])
            on_call(f"[rank] {order}")

        stage("execution-plan", self.EXECUTION_PLAN_PROMPT,
              budgets["execution-plan"])

        # Research may not change the code: it shares the checkout the attempt
        # will be diffed from.
        subprocess.run(["git", "checkout", "--", "."], cwd=checkout,
                       capture_output=True, text=True)

        stdout = "".join(transcripts)
        (workdir / f"research-{attempt_index}.jsonl").write_text(stdout)
        self._in_store(store_root, research_mod.record_pass_score, topic)

        parsed = self.parse_events(stdout, AttemptOutcome())
        return {
            "attempt": attempt_index,
            "kind": "initial" if attempt_index <= 1 else "revision",
            "stages": stages,
            "stage_detail": stage_detail,
            # Wall-clock is less than the sum of the stages: the aspect and
            # evaluate stages run concurrently, and reporting the sum as elapsed
            # would overstate how long research actually held the task up.
            "stage_seconds_total": round(sum(d["elapsed_s"] for d in stage_detail), 1),
            "truncated_stages": [d["stage"] for d in stage_detail if d["truncated"]],
            # Which stage returned the non-zero code, not just that one did. A
            # pass reported as "FAILED rc=126" after 52 successful tool calls
            # tells you nothing about where to look.
            "failed_stages": [f"{d['stage']}=rc{d['returncode']}"
                              for d in stage_detail if d["returncode"]],
            # Whether the account's window was rejected during this pass. Zero
            # tool calls means the same thing on the surface whether the harness
            # is broken or the account is dry, and the two call for opposite
            # responses — stop, or wait. This is the fact that tells them apart,
            # taken off the harness's own stream rather than inferred from rc=1.
            "rate_limited": any(d.get("rate_limited") for d in stage_detail),
            "resets_at": max((d.get("resets_at") or 0)
                             for d in stage_detail) or None,
            "returncode": code,
            "steps": parsed.steps,
            "elapsed_s": round(time.time() - started, 1),
            "tokens_input": parsed.tokens_input,
            "tokens_output": parsed.tokens_output,
            "tokens_cache": parsed.tokens_cache,
            "cost_usd": parsed.cost_usd,
            "calls": self._count_research_calls(stdout),
            "ranking": ranking.get("ranking", [])[:4],
            "record": self.research_summary(instance, store_root),
        }

    def research_summary(self, instance: Dict[str, Any],
                         store_root: Path) -> Dict[str, Any]:
        """What the research record now says, in enough detail to judge it.

        Names and counts are not reviewable. "2 approaches, plan of 3 steps"
        reads identically whether the researcher weighed two real alternatives
        with measured numbers or wrote two paraphrases of one idea, and the
        second is the failure this mechanism is prone to. Carrying the metrics
        and the step kinds lets a reader tell which happened.
        """
        from phronix import research

        # Resolve before loading. `load` takes the key literally, while every
        # other reader resolves it — so this one function was reading the empty
        # ledger record while the corrector read the researched one, and the
        # trace reported "no figure of merit declared" about a record that had
        # one.
        topic = (self._in_store(store_root, research.resolve_topic,
                                self.research_topic(instance))
                 or self.research_topic(instance))
        record = self._in_store(store_root, research.load, topic) or {}
        verdict = self._in_store(store_root, research.verify_plan, topic) or {}
        excluded = self._in_store(store_root, research.ruled_out, topic) or {}

        fom = record.get("fom") or {}
        chosen = record.get("chosen") or {}
        approaches = [{
            "name": a.get("name", ""),
            "summary": str(a.get("summary", ""))[:160],
            "metrics": a.get("metrics") or {},
            "source": str(a.get("source", ""))[:80],
        } for a in record.get("approaches", [])]
        plan = [{
            "order": step.get("order"),
            "kind": step.get("kind", ""),
            "title": str(step.get("title", ""))[:110],
            "capability": step.get("capability", ""),
            "skill": step.get("skill", ""),
        } for step in record.get("plan", [])]

        return {
            "fom": fom,
            "fom_measure": str(fom.get("measure", ""))[:160],
            "approaches": approaches,
            "approach_names": [a["name"] for a in approaches],
            "chosen": chosen.get("name"),
            "chosen_value": chosen.get("value"),
            "chosen_margin": chosen.get("margin"),
            "plan": plan,
            "steps": len(plan),
            "verdict": verdict.get("verdict", ""),
            "facets": {f["facet"]: f["verdict"] for f in verdict.get("facets", [])},
            "facet_detail": {f["facet"]: f["detail"] for f in verdict.get("facets", [])},
            "ruled_out": [{"locations": e["locations"], "attempts": e["attempts"]}
                          for e in excluded.get("ruled_out", [])],
        }

    def record_attempt(self, instance: Dict[str, Any], store_root: Path,
                       patch: str, verdict: Optional[Dict[str, Any]]) -> None:
        """File this attempt's locations and score into the research ledger.

        Done by the harness rather than by an agent, because both inputs are
        facts on disk — the files the patch touched, and the number the tests
        returned. An exclusion list that depends on an agent remembering what it
        already tried is exactly as good as that memory, which is how a task ends
        up with three byte-identical patches against the same function.
        """
        from phronix import research

        topic = self.research_topic(instance)
        files = sorted({line.split(" b/")[-1].strip()
                        for line in (patch or "").splitlines()
                        if line.startswith("diff --git")})
        value = None
        resolved = False
        if verdict:
            resolved = bool(verdict.get("resolved"))
            if verdict.get("fail_to_pass_passed") is not None:
                value = float(verdict["fail_to_pass_passed"])
        # Bookkeeping must never fail the attempt it describes.
        self._in_store(store_root, research.record_attempt, topic, files, value,
                       note=(verdict or {}).get("error", "") or "",
                       resolved=resolved)

    @staticmethod
    def _covered_aspects(topic: str) -> set:
        """Aspects that have already produced an approach."""
        from phronix import research

        record = research.load(research.resolve_topic(topic)) or {}
        return {a.get("aspect") for a in record.get("approaches", []) if a.get("aspect")}

    @staticmethod
    def _load_aspects(topic: str) -> List[Dict[str, str]]:
        from phronix import research

        return (research.load(research.resolve_topic(topic)) or {}).get("aspects", [])

    @staticmethod
    def _count_research_calls(stdout: str) -> Dict[str, int]:
        """Which research tools were actually used, so the pass is measured.

        Both harnesses' stream shapes, because they disagree. opencode emits a
        flat ``{"part": {"type": "tool", "tool": ...}}``; Claude Code emits
        ``{"type": "assistant", "message": {"content": [{"type": "tool_use",
        "name": "mcp__phronix__research_rank"}]}}``. Reading only the first
        made every Claude research pass report zero calls while the trace
        showed a dozen — and "no phronix tools called" is the diagnostic for
        research that never ran, so the one harness-level failure this
        benchmark must not miss was being announced on healthy passes and
        would have been invisible on a real one.
        """
        counts: Dict[str, int] = {}

        def tally(tool: str) -> None:
            if "research" in tool or "capability_new" in tool:
                counts[tool] = counts.get(tool, 0) + 1

        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue

            part = event.get("part")
            if isinstance(part, dict) and part.get("type") == "tool":
                tally(str(part.get("tool") or ""))
                continue

            message = event.get("message")
            if isinstance(message, dict):
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tally(str(block.get("name") or ""))
        return counts

    #: How often the learner looks at what has been reported.
    #:
    #: Ten seconds, because looking is arithmetic — `research_notice` groups
    #: observations by shape and costs nothing. Generalising is the expensive
    #: half and runs on its own, slower clock.
    LEARNING_NOTICE_INTERVAL = _tuned("learning.notice_seconds", 10.0)
    #: How often it reconciles what it has noticed into lessons and tools.
    #:
    #: A minute, because this half is an agent invocation and one of those costs
    #: the better part of a minute before it does anything. Aggressive capture,
    #: periodic compaction: the fast tier never misses anything, and the slow
    #: tier keeps the library small.
    LEARNING_RECONCILE_INTERVAL = _tuned("learning.reconcile_seconds", 60.0)
    #: How many observations make a cycle worth spending.
    #:
    #: One, because everything is learned: a finding reported once and not
    #: written down is rediscovered at full price by the next task, and the
    #: block that would have prevented that costs a few lines. This exists only
    #: so a cycle is not spent on literally nothing.
    LEARNING_BATCH = _tuned("learning.batch", 1)
    #: A cycle's ceiling. Off the critical path, so this buys thoroughness
    #: rather than costing wall clock — but bounded, because a wedged learner
    #: holding a skill file open is a problem for everyone.
    LEARNING_BUDGET = _tuned("learning.budget_seconds", 300)
    #: Reconcilers running at once, each holding a disjoint set of subjects.
    #:
    #: One falls behind when many tasks report at once. More is safe only
    #: because the split is by subject: two workers never write the same skill,
    #: so "more workers" cannot become "two lessons that contradict each other
    #: in one file". Small, because each is an agent invocation.
    LEARNING_WORKERS = _tuned("learning.workers", 3)

    def _learning_env(self, store_root: Path, workdir: Path) -> Dict[str, str]:
        """The environment a learner cycle runs in.

        Built the same way a research stage's is, because the learner needs the
        same things: the store to write into, the MCP server to reach, and a
        model to call. It writes to the project layer deliberately — a lesson
        that lands in a task's session folder helps nothing after that task.

        A method rather than a call site, because the call site had this wrong:
        it named `research_env`, which does not exist, so every cycle raised
        AttributeError and the learner produced nothing for a whole run.
        """
        env = self.phronix_env(tool_path_env(
            isolated_env(store_root, workdir / "learner-cache")))
        env.update(model_env(base_url=self.base_url))
        env["PHRONIX_WRITE_LAYER"] = "project"
        # The background learner's own retrievals, kept apart from the
        # task's so they cannot be counted as a task reusing anything.
        env["PHRONIX_PHASE"] = "learner"
        return env

    def start_learning(self, store_root: Path, checkout: Path,
                       workdir: Path, env: Optional[Dict[str, str]] = None,
                       on_learning=None) -> None:
        """Start the always-on learner, if it is not already running.

        One agent per arm, for the life of the run, draining what the stages
        report. It exists because the learning that mattered was being thrown
        away: a stage would discover that a green test masked a bug, and the
        finding lived in that stage's transcript until the run ended. Nothing
        read across stages and nothing read across tasks, so the same discovery
        was made again on the next instance.

        Two clocks. Every ten seconds it *notices* — arithmetic over the
        observations, grouping them by what they claim, which is how a repeat is
        spotted the moment it happens. Every minute it *reconciles* — one agent,
        turning what repeated into lessons and tools, and compacting what is
        already there.

        It never blocks anything. The pipeline does not wait for it, a cycle
        that runs out of time loses only that cycle, and the thread is a daemon
        so a wedged learner cannot hold the run open.
        """
        # One learner for the whole job, not one per arm.
        #
        # Started from the research pass because that is the first moment there
        # is anything to learn from — but arms run concurrently and tasks may
        # too, so several of them reach this line. A per-instance guard gave one
        # learner per ARM: two consumers of one stream, each with its own idea
        # of what it had seen, which is how two reconcilers come to work the
        # same findings and write lessons that contradict each other.
        #
        # The claim is process-wide, and taken under a lock because the check
        # and the start are not atomic: two arms starting together would
        # otherwise both pass the check.
        global _LEARNER_OWNER
        with _LEARNER_LOCK:
            if _LEARNER_OWNER is not None:
                if on_learning and _LEARNER_OWNER is not self:
                    on_learning("[learner] already running for this job")
                return
            _LEARNER_OWNER = self

        self._learning_stop = threading.Event()
        self._learner_out: List[str] = []

        def cycle() -> None:
            from phronix import bus, research as research_mod

            # Binding is what makes this the consumer: a second one would fail
            # to bind and fall back to the file, which is the correct outcome
            # rather than a race — but the singleton above means there is no
            # second one.
            collector = bus.Collector()
            seen = time.time()
            pending: List[Dict[str, Any]] = []
            last_reconcile = time.time()

            if on_learning:
                on_learning(f"[learner] running: notices every "
                            f"{self.LEARNING_NOTICE_INTERVAL:.0f}s, reconciles "
                            f"every {self.LEARNING_RECONCILE_INTERVAL:.0f}s")

            while not self._learning_stop.is_set():
                if self._learning_stop.wait(self.LEARNING_NOTICE_INTERVAL):
                    collector.close()
                    return

                # The fast half: arithmetic, every ten seconds.
                try:
                    claimed = self._in_store(store_root, research_mod.claim,
                                             "learner", 200, collector) or {}
                    noticed = self._in_store(
                        store_root, research_mod.notice, seen,
                        claimed.get("observations") or []) or {}
                except Exception:
                    noticed = {}
                if noticed.get("new"):
                    seen = float(noticed.get("latest") or seen)
                    pending.extend(noticed.get("candidates") or [])
                    repeats = len(noticed.get("repeats") or [])
                    if on_learning:
                        on_learning(f"[learner] noticed {noticed['new']} "
                                    f"observation(s), {repeats} repeated")

                # Which cycle this turn is.
                #
                # Capture runs on the fast clock and fires on ANYTHING new.
                #
                # It used to wait for a shape to repeat, on the theory that one
                # report is an anecdote. That was wrong in the direction that
                # costs the most: a finding reported once and never written down
                # is lost, and the next task rediscovers it at full price —
                # while the cost of writing it is one short block. Repetition is
                # not what makes a finding true, it is what makes it *confident*,
                # so it belongs in how a block is updated rather than in whether
                # one exists at all.
                #
                # Reconcile runs on the slow clock whether or not anything
                # arrived: duplicates and falsified blocks are already on file
                # and do not need a fresh observation to be worth removing.
                enough = len(pending) >= max(1, int(self.LEARNING_BATCH))
                due = (time.time() - last_reconcile
                       >= self.LEARNING_RECONCILE_INTERVAL)
                if due:
                    cycle_name = "reconcile"
                    last_reconcile = time.time()
                elif enough:
                    cycle_name = "capture"
                else:
                    continue

                # One agent per worker, on what the fast half collected.
                ordered = sorted(pending,
                                 key=lambda c: (c.get("across_tasks"),
                                                c.get("count", 0)),
                                 reverse=True)[:30] or [
                    {"kind": "other", "what": "(nothing new since the last "
                                              "cycle — reconcile what is "
                                              "already written)", "worked": True}]
                lines = []
                for candidate in ordered:
                    mark = " **repeated**" if candidate.get("count", 1) > 1 else ""
                    outcome = ("worked" if candidate.get("worked")
                               else "did NOT work")
                    lines.append(f"- [{candidate.get('kind', 'other')}] "
                                 f"[{outcome}]{mark} {candidate.get('what', '')}"
                                 + (f"  ({', '.join(candidate.get('stages') or [])})"
                                    if candidate.get("stages") else ""))
                pending = []

                # Several reconcilers, partitioned so they cannot contradict.
                #
                # With many tasks in flight one reconciler falls behind, and the
                # obvious fix — run several — is the obvious way to get two
                # agents writing opposite lessons into one skill. So the split
                # is by TOPIC: a lesson about a subject goes to that subject's
                # skill, so workers holding disjoint topics write disjoint
                # files. Nothing needs to coordinate at run time because nothing
                # overlaps by construction.
                #
                # Findings that belong to no topic — about a stage rather than a
                # subject — all go to one worker for the same reason.
                buckets: Dict[str, List[str]] = {}
                for candidate, line in zip(ordered, lines):
                    # By KIND of operation, not by task.
                    #
                    # A lesson about running subprocesses belongs with every
                    # other thing learned about running subprocesses, and the
                    # next task in any repository retrieves it there. Split by
                    # task instead and the same lesson is written into six
                    # skills, each helping only the instance that produced it.
                    #
                    # It also keeps the workers disjoint, which is what stops
                    # two of them writing contradictory lessons into one file:
                    # one kind, one skill, one writer.
                    buckets.setdefault(candidate.get("kind") or "other",
                                       []).append(line)

                groups: List[List[str]] = []
                for topic_lines in buckets.values():
                    if len(groups) < self.LEARNING_WORKERS:
                        groups.append(list(topic_lines))
                    else:
                        # Smallest group takes the next topic, so the work is
                        # spread without ever splitting a topic across workers.
                        min(groups, key=len).extend(topic_lines)

                if on_learning:
                    on_learning(f"[learner] {cycle_name} cycle: {len(lines)} "
                                f"finding(s) across {len(groups)} worker(s), "
                                f"split by kind so none can contradict another")

                def reconcile(group: List[str],
                              cycle_name: str = "reconcile") -> Optional[str]:
                    skill = ("phronix-learning-capture" if cycle_name == "capture"
                             else "phronix-learning-reconcile")
                    try:
                        out, _ = stream_opencode(
                            self.agent_command(
                                LOG_NOTE + SCRATCH_NOTE
                                + self.LEARNER_PROMPT
                                .replace("{cycle}", cycle_name)
                                .replace("{skill}", skill)
                                .replace("{observations}", "\n".join(group)),
                                checkout, self.attachments([]),
                                self.learner_agent_name),
                            checkout,
                            self._learning_env(store_root, workdir),
                            self.LEARNING_BUDGET)
                        return out
                    except Exception as exc:
                        # A learner that dies must not take the run with it —
                        # the observations remain and the next cycle reads them.
                        #
                        # But it must SAY so. This swallowed an AttributeError
                        # for a whole run: every cycle noticed findings, called
                        # a method that did not exist, returned nothing, and the
                        # trace showed only "reconciling 7 finding(s)" — which
                        # reads exactly like a learner that is working.
                        if on_learning:
                            on_learning(f"[learner] cycle FAILED: "
                                        f"{type(exc).__name__}: {exc}")
                        return None

                if len(groups) == 1:
                    written = [reconcile(groups[0], cycle_name)]
                else:
                    with ThreadPoolExecutor(max_workers=len(groups)) as pool:
                        written = list(pool.map(
                            lambda g: reconcile(g, cycle_name), groups))

                out = "\n".join(chunk for chunk in written if chunk)
                if out:
                    self._learner_out.append(out)
                else:
                    continue

                # What came out, by name. "The learner ran" is not a result;
                # "it wrote probe_run_area_tests and a lesson on
                # phronix-research-tune" is, and it is the only evidence that
                # the loop is generalising rather than idling.
                if on_learning:
                    produced = self._learning_products(out)
                    if produced:
                        for item in produced:
                            on_learning(f"[learner] wrote {item}")
                    else:
                        # What "nothing" means depends on the cycle, and saying
                        # the wrong one reads as a fault. A capture cycle that
                        # writes nothing had nothing worth stating; a reconcile
                        # cycle that writes nothing found nothing to merge or
                        # retire, which is the healthy steady state.
                        on_learning("[learner] " + (
                            "nothing to merge or retire — the library is "
                            "already consistent"
                            if cycle_name == "reconcile"
                            else "wrote nothing — no finding worth stating"))

        self._learner = threading.Thread(target=cycle, daemon=True)
        self._learner.start()

    @staticmethod
    def _learning_products(stdout: str) -> List[str]:
        """What a learner cycle actually wrote, by name.

        Read from its tool calls rather than its prose: an agent's summary of
        what it did is a claim, and the calls are the record. Only writes count
        — a cycle that read six skills and wrote nothing produced nothing.
        """
        products: List[str] = []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue

            calls = []
            part = event.get("part")
            if isinstance(part, dict) and part.get("type") == "tool":
                calls.append((str(part.get("tool") or ""),
                              (part.get("state") or {}).get("input") or {}))
            # A plain turn carries `content` as a string; iterating it walks
            # characters and every "block" is a one-character str.
            blocks = (event.get("message") or {}).get("content")
            for block in (blocks if isinstance(blocks, list) else []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append((str(block.get("name") or ""),
                                  block.get("input") or {}))

            for tool, args in calls:
                if not isinstance(args, dict):
                    args = {}
                if "capability_new" in tool:
                    products.append(f"tool {args.get('name', '?')}")
                elif "skill_write_lesson" in tool:
                    products.append(f"lesson {args.get('skill', '?')}: "
                                    f"{str(args.get('title', ''))[:60]}")
                elif "skill_write" in tool:
                    products.append(f"block {args.get('skill', '?')}: "
                                    f"{str(args.get('title', ''))[:60]}")
                elif "skill_create" in tool:
                    products.append(f"skill {args.get('name', '?')}")
        return products

    def drain_learning(self) -> List[str]:
        """Transcripts the learner has finished with since the last drain."""
        collected = list(getattr(self, "_learner_out", []) or [])
        self._learner_out = []
        return collected

    def stop_learning(self, timeout: float = 60.0) -> List[str]:
        """Ask the learner to finish, and collect what it spent.

        Called when the arm's tasks are done. The wait is bounded because a
        cycle mid-invocation is worth a minute of patience and not more — its
        observations are already on file, so what an abandoned cycle loses is
        one write-up rather than the input to it.
        """
        global _LEARNER_OWNER
        stopper = getattr(self, "_learning_stop", None)
        if stopper is not None:
            stopper.set()
        learner = getattr(self, "_learner", None)
        if learner is not None:
            learner.join(timeout=timeout)
        self._learner = None
        with _LEARNER_LOCK:
            if _LEARNER_OWNER is self:
                _LEARNER_OWNER = None
        return self.drain_learning()

    def learn(self, instance: Dict[str, Any], store_root: Path, workdir: Path,
              outcome: AttemptOutcome,
              verdict: Optional[Dict[str, Any]] = None) -> None:
        """Run a dedicated learning pass over the finished, *judged* attempt.

        Why this is a separate invocation rather than a line in the task prompt:
        measured over three tasks, an agent told to record its learnings before
        finishing did so exactly once, and that one attempt used the wrong tool
        and was discarded. Recording competes with solving, and solving wins —
        the task is what the agent is graded on, and the write-up is the step
        that gets dropped when the context is long and the fix is finally green.

        Giving learning its own turn, with its own prompt and nothing else to do,
        is the difference between a system that learns continuously and one that
        intends to. It costs one short agent invocation per task, which is small
        beside re-deriving the same root cause on every future instance.

        Failures here are logged and swallowed: a learning pass that dies must
        not void a task attempt that succeeded.
        """
        import subprocess

        checkout = workdir / "repo"
        if not checkout.is_dir():
            return

        # Hand the learner the evidence rather than asking it to reconstruct the
        # attempt from the working tree. Given only the checkout it correctly
        # refused to write anything — "no diagnosis is visible, no fix was
        # attempted, recording 'a test failed but we don't know why' would not
        # help future sessions" — which is the right call on the information it
        # had, and the wrong outcome for the system.
        diff_file = workdir / "attempt-diff.patch"
        diff_file.write_text(outcome.patch or "(the agent produced no diff)\n",
                             encoding="utf-8")
        notes_file = workdir / "attempt-notes.md"
        notes_file.write_text(
            self._attempt_notes(instance, workdir, outcome, verdict),
            encoding="utf-8")

        self.research_topic_binding = self.research_topic(instance)
        env = self.phronix_env(tool_path_env(isolated_env(store_root, workdir / "cache")))
        env.update(model_env(base_url=self.base_url))
        env["PHRONIX_WRITE_LAYER"] = "project"
        # The post-attempt harvest, which reads to write rather than to solve.
        env["PHRONIX_PHASE"] = "learn"
        if self.store_readonly:
            env["PHRONIX_BENCH_FROZEN"] = "1"

        command = self.agent_command(
            self.LEARN_PROMPT, checkout,
            self.attachments([diff_file, notes_file]),
            self.learn_agent_name)

        started = time.time()
        try:
            with private_home(dict(env)) as run_env:
                result = subprocess.run(command, cwd=checkout, env=run_env,
                                        capture_output=True, text=True,
                                        timeout=self.learn_timeout_s,
                                        stdin=subprocess.DEVNULL)
            stdout, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as expired:
            stdout, code = _as_text(expired.stdout), -1
        except OSError as exc:
            stdout, code = "", -1
            outcome.raw["learn_error"] = str(exc)

        (workdir / "learn.jsonl").write_text(stdout)

        # Counted, but counted separately. The learning pass is a real cost of
        # this arm and must not be hidden; it is also not the agent solving the
        # task, and folding it in would misattribute both.
        pass_outcome = self.parse_events(stdout, AttemptOutcome())
        outcome.tokens_learn += pass_outcome.tokens_total
        outcome.cost_usd += pass_outcome.cost_usd
        outcome.raw["learn"] = {
            "returncode": code,
            "steps": pass_outcome.steps,
            "elapsed_s": round(time.time() - started, 1),
            "writes": self._count_write_calls(stdout),
        }

    @staticmethod
    def _attempt_notes(instance: Dict[str, Any], workdir: Path,
                       outcome: AttemptOutcome,
                       verdict: Optional[Dict[str, Any]] = None) -> str:
        """The attempt's own account of itself, for the learning pass to read.

        The agent's closing messages are the only place its reasoning survives —
        which hypothesis it tested, what the root cause turned out to be, which
        approach it abandoned. None of that is recoverable from the diff, and the
        diff without it produces lessons that restate the patch instead of
        explaining it.
        """
        parts: List[str] = [
            f"# Attempt notes — {instance.get('instance_id', 'unknown')}",
            "",
            "## The issue that was being fixed",
            "",
            (instance.get("problem_statement") or "(none recorded)")[:6000],
            "",
            "## What the agent said while working",
            "",
        ]

        texts: List[str] = []
        transcript = workdir / "opencode.jsonl"
        if transcript.is_file():
            for line in transcript.read_text(errors="replace").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                part = event.get("part") or {}
                if isinstance(part, dict) and part.get("type") == "text":
                    text = (part.get("text") or "").strip()
                    if text:
                        texts.append(text)

        if texts:
            # The last few messages carry the diagnosis and the summing-up; the
            # early ones are mostly orientation.
            parts.extend(texts[-6:])
        else:
            parts.append("(the agent produced no narrative output)")

        if outcome.error:
            parts += ["", "## The attempt ended with an error", "",
                      f"```\n{outcome.error[:1500]}\n```"]

        if verdict is not None:
            # The verdict is the whole point of learning after evaluation: it is
            # the difference between "I fixed it" and "I thought I fixed it".
            resolved = verdict.get("resolved")
            parts += ["", "## How it was judged", "",
                      f"**Resolved: {'YES' if resolved else 'NO'}**", ""]
            if verdict.get("fail_to_pass_total") is not None:
                parts.append(
                    f"- Target tests (must newly pass): "
                    f"{verdict.get('fail_to_pass_passed')} of "
                    f"{verdict.get('fail_to_pass_total')}")
                parts.append(
                    f"- Regression tests (must keep passing): "
                    f"{verdict.get('pass_to_pass_passed')} of "
                    f"{verdict.get('pass_to_pass_total')}")
            if verdict.get("error"):
                parts += ["", f"Harness error: {str(verdict['error'])[:800]}"]
            missed = verdict.get("fail_to_pass_failing") or []
            if missed:
                parts += ["", "### Target tests still failing", "",
                          "```", "\n".join(missed[:15]), "```"]
            regressions = verdict.get("regressions") or []
            if regressions:
                parts += ["", "### Regressions this patch introduced", "",
                          "```", "\n".join(regressions[:15]), "```"]

            detail = verdict.get("failure_detail") or ""
            if detail.strip():
                parts += ["", "### Why they failed (pytest output)", "",
                          "```", detail.strip()[:5000], "```"]
            if not resolved:
                parts += ["",
                          "This attempt did **not** solve the task. The most "
                          "valuable thing you can record is why the approach "
                          "above was insufficient, so the next attempt does not "
                          "repeat it."]
        return "\n\n".join(parts)

    @staticmethod
    def _count_write_calls(stdout: str) -> Dict[str, int]:
        """Which persistence tools the learning pass actually called.

        Reported per task so "did it learn?" is a measured number rather than an
        inference from the store's file count — which misses a lesson appended to
        an existing skill entirely.
        """
        counts: Dict[str, int] = {}
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            part = event.get("part") or {}
            if not isinstance(part, dict) or part.get("type") != "tool":
                continue
            tool = str(part.get("tool") or "")
            if any(mark in tool for mark in ("skill_write", "memory_write",
                                             "capability_new", "skill_create",
                                             "skill_define")):
                counts[tool] = counts.get(tool, 0) + 1
        return counts

    def _retarget_agents(self, agents_dir: Path) -> None:
        """Make the rendered agents usable by, and fair to, the benchmark.

        Two edits, each fixing something that silently broke the arm:

        ``mode: primary`` on the launched agent. Phronix renders every agent as
        ``subagent``, which is right in normal use — they are specialists a main
        agent delegates to. But ``opencode run --agent`` selects a *primary*
        agent, so passing a subagent was accepted and then ignored: the run used
        opencode's default agent and called zero phronix tools, looking exactly
        like a model that chose not to.

        **Stripping the pinned ``model:``.** This one is the difference between a
        valid experiment and a meaningless one. Agents declare a capability level,
        which the renderer resolves through the model map — here to
        ``ollama/qwen3:32b``. Left in place, the phronix arm would have run a
        different model from the baseline while reporting itself as a comparison
        of the *same* model with and without phronix. Removing the key lets the
        CLI's ``--model`` apply, which is the control the benchmark exists to hold.
        """
        if not agents_dir.is_dir():
            return
        launched = {self.agent_name, self.learn_agent_name,
                    self.research_agent_name}
        for path in sorted(agents_dir.glob("*.md")):
            text = path.read_text()
            # Both agents this arm launches directly must be primary; the rest
            # stay delegable subagents.
            if path.stem in launched:
                text = text.replace("mode: subagent", "mode: primary", 1)
            text = re.sub(r"^model:.*\n", "", text, flags=re.MULTILINE)
            path.write_text(text)

    def project_config(self, store_root: Path) -> Dict[str, Any]:
        config = super().project_config(store_root)
        # Re-enable phronix specifically, pointed at a stdio server this arm
        # spawns itself. stdio rather than http so no port is shared between
        # concurrently running arms, which would let one arm's store serve
        # another's requests.
        config["mcp"]["phronix"] = {
            "type": "local",
            "command": ["phronix-mcp-server", "--no-setup", "--quiet"],
            "enabled": True,
        }
        return config


#: Where the VS Code extension keeps the Claude Code binary.
#:
#: Not on PATH, and there is no npm install here — but the extension ships a
#: self-contained native build, and it is the same program the plugin drives.
CLAUDE_BIN_GLOB = (
    "~/.vscode-server/extensions/anthropic.claude-code-*/resources/"
    "native-binary/claude")


def find_claude_bin() -> str:
    """Resolve the Claude Code executable, newest version first."""
    import glob

    matches = sorted(glob.glob(os.path.expanduser(CLAUDE_BIN_GLOB)), reverse=True)
    return matches[0] if matches else "claude"


class ClaudeArm(OpenCodeArm):
    """The same benchmark, driven through Claude Code instead of opencode.

    Exists because the harness must not be the thing that decides whether a run
    can happen. The site's shared LiVAI key hit its spend cap mid-run — every
    request 429'd, and both arms produced attempt after attempt of "0 steps, 0
    tokens", which reads exactly like an agent that ran and did nothing. Claude
    Code bills against a different account, so the same experiment can run.

    Only two things are harness-specific: the command, and the shape of the
    event stream. Everything the benchmark actually measures — the container,
    the checkout, patch extraction, evaluation with baseline discounting, the
    research flow, the ledger — is shared with the opencode arms, so the two
    harnesses cannot silently diverge in what they score.

    **Numbers from this arm are not comparable to the opencode arms.** Different
    harness, different system prompt, different model routing. Bare-versus-
    phronix WITHIN a Claude run is the comparison that stays valid, and it is
    the one the benchmark is for.
    """

    name = "claude-bare"
    uses_phronix = False
    agent_name = ""

    #: Low by default. The benchmark measures whether research changes the
    #: outcome; paying for extended reasoning on every call would confound that
    #: with a second variable and cost several times as much.
    effort = "low"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("opencode_bin", find_claude_bin())
        super().__init__(*args, **kwargs)

    @property
    def qualified_model(self) -> str:
        """Claude Code names models directly; there is no provider prefix."""
        return self.model

    def attachments(self, paths: List[Path]) -> List[str]:
        """Claude Code has no ``--file``; the paths go in the prompt.

        ``--add-dir`` grants access, and the prompt names the files. Attaching
        by reference rather than by value also keeps the issue text out of the
        argv, which has a length limit that a 24 KB bug report would exceed.
        """
        return [str(path) for path in paths]

    def agent_command(self, prompt: str, checkout: Path, files: List[str],
                      agent: str = "") -> List[str]:
        listed = "\n".join(f"- {path}" for path in files)
        full = (f"{prompt}\n\nRead these files first — they state the task and "
                f"how it is judged:\n{listed}\n")

        command = [self.opencode_bin, "-p", full,
                   "--output-format", "stream-json", "--verbose",
                   # The agent must be able to edit without a prompt; anything
                   # else stops at the first edit and produces no patch, which
                   # is indistinguishable from failing the task.
                   "--permission-mode", "bypassPermissions",
                   "--add-dir", str(checkout),
                   "--model", self.qualified_model]
        if self.effort:
            command += ["--effort", self.effort]
        if agent:
            command += ["--agents", json.dumps({agent: {"description": agent}})]
        return command

    @staticmethod
    def parse_events(stdout: str, outcome: AttemptOutcome) -> AttemptOutcome:
        """Mine Claude Code's stream-json for usage, steps and tools.

        The ``result`` event carries authoritative cumulative usage, so it is
        taken outright rather than accumulated — the ``system`` events in the
        stream report *estimated* running totals, and summing those would invent
        a number several times the real one.

        Steps are counted as tool calls, matching what the opencode arm counts,
        so "steps" means the same thing in both harnesses.
        """
        tools = set()
        steps = 0

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            kind = event.get("type")
            if kind == "assistant":
                for block in (event.get("message") or {}).get("content") or []:
                    if block.get("type") == "tool_use":
                        steps += 1
                        name = str(block.get("name") or "")
                        if name:
                            tools.add(name)
            elif kind == "result":
                usage = event.get("usage") or {}
                outcome.tokens_input = int(usage.get("input_tokens") or 0)
                outcome.tokens_output = int(usage.get("output_tokens") or 0)
                outcome.tokens_cache = (
                    int(usage.get("cache_read_input_tokens") or 0)
                    + int(usage.get("cache_creation_input_tokens") or 0))
                outcome.cost_usd = float(event.get("total_cost_usd") or 0.0)
                if event.get("is_error"):
                    outcome.error = str(event.get("result") or "agent reported an error")[:800]

        outcome.steps = steps
        outcome.tools_used = sorted(tools)
        return outcome


class ClaudePhronixArm(PhronixOpenCodeArm, ClaudeArm):
    """Claude Code with phronix: research, learning, the full flow.

    The MRO is deliberate — the phronix behaviour (research stages, learning,
    store wiring) comes first, and ClaudeArm supplies only the command and the
    parser underneath it. So the two harnesses run the *same* phronix, which is
    what makes a result from either of them mean the same thing.
    """

    name = "claude-phronix"
    # Writable, like every non-frozen phronix arm. Inheriting the base default
    # left this arm running with PHRONIX_BENCH_FROZEN=1 and a :ro mount — the
    # CONTROL configuration — while being reported as the full claim.
    store_readonly = False
    uses_phronix = True
    effort = "low"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("opencode_bin", find_claude_bin())
        super().__init__(*args, **kwargs)

    @property
    def qualified_model(self) -> str:
        return self.model

    def agent_command(self, prompt: str, checkout: Path, files: List[str],
                      agent: str = "") -> List[str]:
        command = ClaudeArm.agent_command(self, prompt, checkout, files, agent="")

        # The phronix MCP server, declared inline rather than written into the
        # checkout: a config file inside the repository would show up as an
        # untracked addition in the patch this arm is judged on.
        config = {"mcpServers": {"phronix": {
            "command": sys.executable,
            "args": ["-m", "phronix.mcp_server"],
        }}}
        command += ["--mcp-config", json.dumps(config)]
        if agent:
            command += ["--agents", json.dumps(
                {agent: {"description": f"phronix {agent}"}})]
        return command


class PhronixFrozenArm(PhronixOpenCodeArm):
    """The control: identical scaffolding, store mounted read-only."""

    name = "opencode-phronix-frozen"
    store_readonly = True


class PhronixArm(PhronixOpenCodeArm):
    """The full claim: scaffolding plus a writable store that accumulates."""

    name = "opencode-phronix"
    store_readonly = False


ARMS: Dict[str, type] = {
    MiniArm.name: MiniArm,
    OpenCodeArm.name: OpenCodeArm,
    PhronixFrozenArm.name: PhronixFrozenArm,
    PhronixArm.name: PhronixArm,
    ClaudeArm.name: ClaudeArm,
    ClaudePhronixArm.name: ClaudePhronixArm,
}

#: The order arms are reported in — reference, then baseline, then control, then
#: the claim. Reading left to right is reading the argument.
ARM_ORDER = [MiniArm.name, OpenCodeArm.name, PhronixFrozenArm.name, PhronixArm.name,
             ClaudeArm.name, ClaudePhronixArm.name]


def build(name: str, **kwargs: Any) -> Arm:
    if name not in ARMS:
        raise KeyError(f"unknown arm {name!r}; known: {', '.join(ARM_ORDER)}")
    return ARMS[name](**kwargs)
