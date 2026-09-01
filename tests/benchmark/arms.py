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
import hashlib
import json
import os
import urllib.request
import re
import shlex
import shutil
import sys
import threading
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from phronix import bus as bus_module
from phronix import capabilities as capabilities_module

from .isolation import (Container, isolated_env, ssh_options,
                        without_harness_venv)

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
code and tests live, and how your work is judged.

If `conversation-summary.md` is attached, read it first: it is every attempt and
evaluation already made on this task, oldest first, with what each changed and
what the tests said. A change judged there has been measured — making it again
produces the same verdict. Fix the issue by editing the
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
PHRONIX_REUSE_SUFFIX = """

## First: has this already been built?

Earlier sessions turned procedures they had to repeat into MCP tools, and those
tools are loaded and callable right now. Your first action:

    capability_list()

Read the descriptions — each one is the first sentence of what that tool
documents itself as doing. A tool that names this repository's behaviour, this
file or this fix is a previous session's answer to your task, already written
and already checked: call it and then run the target tests, rather than
rebuilding what it does by hand.

They are deterministic code, not advice: a tool either applies its change or
tells you it could not. If one applies cleanly and the tests pass, you are done,
and that is the cheapest possible outcome rather than a shortcut.

If nothing in the list fits, say so and solve the task yourself. Do not stretch
a tool built for a neighbouring bug onto this one — it will apply somewhere
plausible and wrong, and the tests will take longer to say so than solving it
directly would have taken.
"""

PHRONIX_PLAN_SUFFIX = """

A skill in the store may cover this task:

    {skill}

**Read what it says it solved before you follow it.** A skill opens with the
problem it was written for — the symptom, the failing case, and where the
behaviour comes from. Two things can happen, and both are useful:

* **It is your problem.** Then the skill IS the plan: the pipeline to run, the
  approaches in the order to try them, how a change here is measured, and what
  was already tried and refuted. Follow it.
* **It is a different problem in the same area.** Then it is not your solution
  and applying it will not work — but what it establishes about this code still
  holds. Use it as knowledge: where the behaviour lives, what the tests assert,
  which directions were refuted and why. Then work out your own fix.

Deciding this is your job and cannot be delegated to the retrieval. Nothing
that hands you this name knows your problem; the skill says what IT solved, and
you are the one who can see both.

**Read the skill itself. Your first action:**

    skill_load("{skill}")

Not a graph query, and not a search. The skill is named above because the
harness resolved it for this task; anything that goes looking again can only
find something else. Measured, and it cost a task: the attempt opened with
`graph_query(question="steps to solve {topic}")`, got back three stage notes
from an earlier run — one of them about a DIFFERENT bug in this repository —
judged them useful enough, never loaded the skill it had been handed, and
reinvented a fix the skill's own rules had already recorded as failing.

Use `graph_query` afterwards, to reach what the skill links to or to explore
wider. It is how you find things you have not been told about; it is not the
way in to something you have.

This is not fastidiousness. Whatever you load is re-read on every subsequent
step of this attempt, because each api call carries the whole conversation
again: a block loaded once and never used is paid for once per step, and these
attempts run to dozens of steps. Locate, fetch the section, act.

If the skill turns out not to cover your problem, say so plainly and work out
your own fix — that is a real outcome and worth knowing about. What is not
worth doing is quietly substituting a search for the skill you were given.

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
OBSERVE_NOTE = """
## Report what you learn, as you learn it

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)`
whenever something turns out to work or not: a technique that fixed a class of
cases, a tool whose output needed massaging, an approach that looked right and
was not.

`kind` says what sort of work it was about — `bash`, `python`, `traversal`,
`tests`, `patch`, `matching`, `config`, `git`, `measurement`, `tooling` — and it
is how the finding is filed. Something learned about walking a directory tree
goes with everything else learned about walking directory trees, where the next
task in any repository will find it.

It costs nothing and nothing waits on it. A learner running in the background
drains these, looks for what repeats across tasks, and turns the repeats into
lessons and tools — so a thing you report once may save every later task the
discovery. **`worked=false` is the more valuable report** and the one nobody
writes down: a dead end recorded costs the next task a sentence, unrecorded it
costs an attempt.
"""

SKILL_NOTE = """
SKILLS — load each one ONCE.

A skill stays in your context after the first load. Loading it again re-reads
the whole document and re-sends every earlier turn with it, which is the most
expensive thing you can do for no new information.

There are two ways to reach the same skill — the `Skill` tool and
`skill_load` — and they return the same text. Use `skill_load`, once, and not
the other. Measured in one research pass: the same skill fetched eighteen times
through each, for one document that never changed.
"""

TOOLS_NOTE = """
TOOLS — before you do anything by hand.

Call `capability_list` first. If a `probe_` tool already answers your question,
call it; one call replaces the five it takes to derive the same fact, and under
a hard budget those five are most of your stage.

When you are about to repeat something you have already done in this pass, build
it with `capability_new` instead of doing it a second time. Deterministic
procedures only — a measurement, a reproduction, a check — never a judgement.

The method is the `phronix-research-as-tools` skill. Load it when you are
deciding whether something should become a tool.
"""

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


#: Serialises every in-process phronix call that has to set env vars.
#: Backend pins handed out so far, key -> position. See `Arm._pin_index`.
#:
#: Module level, not per arm: two arms and every task in the process draw from
#: one sequence, which is what makes the spread even across everything running
#: at once. Never pruned — a task that finished still owns its pin, so a retry
#: returns to the backend that still holds its conversation.
#: Per-task settings that must NOT be shared between concurrent tasks.
#:
#: An `Arm` instance is reused for every task that arm runs, and the runner
#: runs many at once in threads. Writing a per-task value onto the arm as a
#: plain attribute is therefore a data race with a plausible-looking result:
#: the last task to start overwrites it for every task already running.
#:
#: Measured the first time agents were placed on compute nodes: 25 agents
#: landed on ONE node of five, two nodes got none, and fifteen stayed on the
#: login node — every task reading whichever host was written last. The
#: runtime already avoided this with a thread-local; these two did not.
#:
#: `pinned_for_env` had the same race silently: a task could send its
#: conversation to another task's backend, which is exactly the prompt-cache
#: locality the pinning exists to create.
_TASK_LOCAL = threading.local()


#: The always-on trackers, keyed by the record they keep.
#:
#: One per TASK, not one per job like the learner: the record belongs to one
#: task and two tasks sharing a writer would merge two histories. Keyed on the
#: record's path because that is what makes two callers the same task —
#: the arm object is shared and its thread is not the tracker's.
_TRACKERS: Dict[str, "_TrackerState"] = {}
_TRACKER_LOCK = threading.Lock()


@dataclass
class _TrackerState:
    """What one task's always-on tracker needs to keep going."""

    tracker: Path
    stop: Any                       # threading.Event
    thread: Any = None
    pending: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    #: Events folded into the record so far. `note` returns the sequence
    #: number of the event it queued, so a caller that must not read a stale
    #: record can wait for `folded >= mine` rather than for a fixed delay.
    queued: int = 0
    folded: int = 0
    lock: Any = field(default_factory=threading.Lock)
    moved: Any = field(default_factory=threading.Condition)
    cycles: int = 0


def task_pool(max_workers: int) -> ThreadPoolExecutor:
    """A thread pool whose workers inherit the calling TASK's settings.

    `_TASK_LOCAL` is thread-local, which is what keeps concurrent tasks from
    overwriting each other — and it means a worker thread starts with nothing.
    Research fans out through six pools, so every one of those agents read an
    empty `agent_host` and ran on the login node: the placement worked for the
    attempt and silently did not for the research that surrounds it.

    Inherited at thread START, from the thread that builds the pool, which is
    the task's own. Anything a task changes afterwards does not propagate, and
    nothing here changes after the task begins.
    """
    parent = (getattr(_TASK_LOCAL, "agent_host", ""),
              getattr(_TASK_LOCAL, "pinned_for_env", ""))

    def adopt(host: str, pin: str) -> None:
        _TASK_LOCAL.agent_host = host
        _TASK_LOCAL.pinned_for_env = pin

    return ThreadPoolExecutor(max_workers=max_workers,
                              initializer=adopt, initargs=parent)

_PIN_ASSIGNED: Dict[str, int] = {}
_PIN_LOCK = threading.Lock()

_STORE_ENV_LOCK = threading.Lock()


def _slug(text: str) -> str:
    """A filesystem-safe key for a subject."""
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "subject"


def _bundled_skill_names() -> set:
    """Skills that ship with the framework, so "remembered" means learned.

    Read from the source of truth rather than listed here: a constant tracking
    a directory in another repository is a constant that will be wrong and be
    believed.
    """
    root = Path("/usr/WS2/haridev/phronix/src/phronix/.phronix/skills")
    try:
        return {p.name for p in root.iterdir() if p.is_dir()}
    except OSError:
        return set()


#: Decode rate the stage budgets in STAGE_BUDGETS were measured against.
#:
#: Every budget in this file is a number of SECONDS, but what a stage actually
#: needs is a number of TOKENS — so a budget is only meaningful paired with the
#: rate that produced it. These were measured against a model decoding about
#: this fast; on anything slower the same seconds buy proportionally fewer tool
#: calls, and stages are cut off mid-investigation while the run is scored as
#: though the research happened.
CALIBRATION_TOKENS_PER_S = 1000.0

#: Bounds on the derived scale.
#:
#: The floor is below 1.0 on purpose. The calibration is a LOCAL model at
#: ~1000 tok/s, and a hosted endpoint is not merely as fast — a Claude cloud
#: model answers a stage's turns in seconds where the calibrated model took
#: tens of them, so the same seconds buy several times the tool calls. Holding
#: hosted runs at 1.0 spends minutes per stage on agents that finished
#: thinking long before the clock did.
#:
#: The ceiling stops one bad reading — a fleet that answered once, slowly,
#: while still loading — turning a ten-minute stage into a five-hour one.
BUDGET_SCALE_BOUNDS = (0.2, 50.0)

_BUDGET_SCALE_CACHE: Dict[str, Any] = {"value": None}


def has_local_fleet() -> bool:
    """Is a local fleet configured at all?

    The distinction `measured_decode_rate` cannot make: it returns None both
    when there is no cluster config (a hosted endpoint) and when there is one
    whose replicas have not served anything yet (a fleet deployed seconds ago).
    Those want opposite budgets, and conflating them halved every budget on
    every batch run — see `budget_scale`.
    """
    try:
        from .cluster import DEFAULT_CONFIG

        config = Path(os.environ.get("PHRONIX_CLUSTER") or DEFAULT_CONFIG)
        return bool(json.loads(config.read_text(encoding="utf-8")).get("servers"))
    except Exception:
        return False


def measured_decode_rate() -> Optional[float]:
    """Tokens/second the fleet is actually decoding, or None if unknowable.

    Read from the replicas' own `/metrics`, which llama-server exports and
    which is already how status.sh reports throughput — so this costs a couple
    of HTTP gets rather than a generation of our own. `predicted_tokens_seconds`
    is the rate of finished requests, so it reads 0 on a fleet that has not
    served anything yet; those are skipped rather than averaged in, because a
    zero here would scale the budgets to the ceiling for no reason.
    """
    try:
        from .cluster import DEFAULT_CONFIG

        config = Path(os.environ.get("PHRONIX_CLUSTER") or DEFAULT_CONFIG)
        servers = json.loads(config.read_text(encoding="utf-8")).get("servers") or []
    except Exception:
        return None
    if not servers:
        return None

    def rate(server: Dict[str, Any]) -> Optional[float]:
        url = f"http://{server.get('host')}:{server.get('port')}/metrics"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read().decode("utf-8", "replace")
        except Exception:
            return None
        for line in body.splitlines():
            if line.startswith("llamacpp:predicted_tokens_seconds"):
                try:
                    value = float(line.rsplit(" ", 1)[-1])
                except ValueError:
                    return None
                return value if value > 0 else None
        return None

    with ThreadPoolExecutor(max_workers=min(8, len(servers))) as pool:
        seen = [r for r in pool.map(rate, servers[:8]) if r]
    if not seen:
        return None
    seen.sort()
    return seen[len(seen) // 2]          # median: one slow replica is not the fleet


#: The most the TRACKED pipeline's budgets are stretched for slow hardware.
#:
#: `budget_scale` is clamped at 50, which is right for the parallel research
#: pipeline where a stage that overruns costs only itself. The tracked loop is
#: sequential — research blocks the next attempt, a fold blocks research — so a
#: 50x stretch would put a single stage at four hours and the task would never
#: reach try 2.
#:
#: Six is derived from what a stage needs in TOKENS rather than seconds. A
#: diagnosis is ~8-15k output tokens; at the 13.5 tok/s measured on corona that
#: is 600-1100s against a 300s budget, so 4-6x is the range that lets it finish
#: without letting it run away. Measured before this: 178 of one run's 314
#: pipeline faults were stages killed at their ceiling, and research reported
#: `no PROBLEM/APPROACH/ANSWER` — it had been cut off mid-diagnosis, so try 2
#: began from scratch with no skill.
TRACKED_SCALE_CAP = 6.0

#: A hard ceiling on the record guard however slow the hardware is.
#:
#: A fold that needs longer than this is not slow, it is not converging, and
#: the events stay queued for the next fold either way.
RECORD_GUARD_MAX_S = 1800


def tracked_budget_scale() -> float:
    """`budget_scale`, bounded for the sequential loop. See TRACKED_SCALE_CAP."""
    return max(1.0, min(TRACKED_SCALE_CAP, budget_scale()))


def budget_scale() -> float:
    """Multiplier on every research stage budget, for THIS system.

    Three sources, most explicit first:

      PHRONIX_BUDGET_SCALE=<number>   use exactly this
      PHRONIX_BUDGET_SCALE=auto       measure the fleet and derive it
      unset                           `research.budget_scale` from tuning.yaml

    `auto` exists because the right value is a property of the hardware, not of
    the experiment, and getting it wrong is silent in the direction that
    matters. Measured on corona (MI50): the fleet decodes ~34 tok/s against a
    calibration of 1000, so every planning agent was killed at its 450s ceiling
    still reading source files, and the task recorded zero research steps while
    the run reported it as a normal failure.
    """
    raw = (os.environ.get("PHRONIX_BUDGET_SCALE") or "").strip().lower()
    if raw and raw != "auto":
        try:
            return max(BUDGET_SCALE_BOUNDS[0],
                       min(BUDGET_SCALE_BOUNDS[1], float(raw)))
        except ValueError:
            pass
    if raw == "auto":
        if _BUDGET_SCALE_CACHE["value"] is None:
            rate = measured_decode_rate()
            # No fleet to measure means a HOSTED endpoint, and hosted is not
            # the calibration — it is faster than it.
            #
            # The budgets were measured against a local model at ~1000 tok/s.
            # A Claude cloud model turns a stage's tool calls around in
            # seconds, so the same budget buys several times the work and the
            # clock stops being the binding constraint: measured on the Haiku
            # run, `plan` spent its full five minutes and its re-ask a further
            # five, on a task whose attempt stage had finished in three.
            #
            # So hosted gets its own scale, below 1.0, rather than inheriting a
            # number derived for hardware it has nothing to do with.
            if not rate and has_local_fleet():
                # A local fleet that has not served anything YET.
                #
                # `predicted_tokens_seconds` is the rate of finished requests,
                # so it reads 0 on a fleet deployed seconds ago — which is
                # every batch run, because the job deploys the fleet and
                # starts the run immediately. Treating that as "hosted" gave
                # it the hosted scale of 0.5 and HALVED every budget on the
                # slowest hardware in the fleet.
                #
                # Measured across two 300-task runs: `budget_scale = 0.5` in
                # both manifests, and 778 stages killed at their ceiling
                # between them — 563 of them research, which is the stage the
                # next attempt depends on.
                #
                # GENEROUS for now, and NOT cached, so the next caller
                # measures once traffic exists and the budgets correct
                # themselves mid-run.
                #
                # Deliberately above 1.0 rather than merely neutral. The two
                # errors are not symmetric: a budget that is too long costs
                # wall-clock on a stage that would have finished anyway, while
                # one that is too short throws the stage's work away entirely
                # and, for research, leaves the next attempt with no skill to
                # start from. A run that takes longer and finishes beats one
                # that is fast and measures nothing.
                return float(_tuned("research.local_unmeasured_budget_scale", 2.0))
            scale = (float(_tuned("research.hosted_budget_scale", 0.5))
                     if not rate else CALIBRATION_TOKENS_PER_S / rate)
            _BUDGET_SCALE_CACHE["value"] = max(
                BUDGET_SCALE_BOUNDS[0], min(BUDGET_SCALE_BOUNDS[1], scale))
        return float(_BUDGET_SCALE_CACHE["value"])
    return float(_tuned("research.budget_scale", 1.0))


def _useful_test_output(text: str) -> str:
    """Test output with the teardown noise dropped.

    Django's runner prints one `Destroying test database for alias ...` line
    per database per parallel worker, and on this suite that is eighty
    identical lines — which land at the END of the captured output, the part a
    skimming reader weights most. The signal (the assertion that failed) is
    above them and gets pushed out of view.

    Dropped rather than truncated: these lines carry no information at any
    length, and keeping the first of each kind would still spend the position
    that matters.
    """
    noise = ("Destroying test database for alias",
             "Creating test database for alias",
             "Cloning test database for alias",
             "Operations to perform:",
             "Synchronizing apps without migrations:")
    kept: List[str] = []
    dropped = 0
    for line in str(text).splitlines():
        if line.strip().startswith(noise):
            dropped += 1
            continue
        kept.append(line)
    if dropped:
        kept.append(f"[{dropped} test-database setup/teardown line(s) removed]")
    return "\n".join(kept).strip()


#: How long a queue reading is trusted before it is taken again.
_DEFERRED_CACHE: Dict[str, Any] = {"at": 0.0, "value": 0.0}
_DEFERRED_TTL = 5.0


def _fleet_samples_path() -> Path:
    """The live fleet session's sampler file.

    LLM_ROOT names it directly when the fleet's env.sh has been sourced. It
    usually has not been — the benchmark runs in its own process tree — and the
    old default pointed at Tuolumne's lustre unconditionally. On corona that
    path does not exist, so this returned 0.0 forever and the budget silently
    lost its queue-time correction: stages were charged for time spent waiting
    in a queue rather than being served, which is the exact thing
    `deferred_fraction` exists to prevent. A missing file is indistinguishable
    from an idle fleet, so nothing reported the mistake.

    cluster.json is the fallback because it is written by whichever deploy
    brought the fleet up, and its `run_dir` is inside that cluster's own
    LLM_ROOT — so the sessions directory beside it is the right one by
    construction, whichever machine this is.
    """
    root = os.environ.get("LLM_ROOT")
    if root:
        return Path(root) / "logs" / "sessions" / "current" / "samples.jsonl"
    try:
        from .cluster import DEFAULT_CONFIG
        config = Path(os.environ.get("PHRONIX_CLUSTER") or DEFAULT_CONFIG)
        run_dir = json.loads(config.read_text(encoding="utf-8")).get("run_dir")
        if run_dir:
            return Path(run_dir).parent / "sessions" / "current" / "samples.jsonl"
    except Exception:
        pass
    return Path("/p/lustre5/haridev/llm-tuolumne/logs/sessions/current/samples.jsonl")


def deferred_fraction() -> float:
    """Share of the fleet's replicas with a request WAITING, 0.0-1.0.

    Read from the session sampler's newest line — the fleet already writes one
    every few seconds, so this costs a short file read rather than a scrape of
    every replica. Each row is `[host:port, up, running, deferred]`.

    Returns 0.0 when there is no sampler: a hosted run has no queue of ours to
    measure, and the budget must behave exactly as it did before.
    """
    now = time.time()
    if now - _DEFERRED_CACHE["at"] < _DEFERRED_TTL:
        return float(_DEFERRED_CACHE["value"])
    _DEFERRED_CACHE["at"] = now
    _DEFERRED_CACHE["value"] = 0.0
    path = _fleet_samples_path()
    try:
        lines = tail_text(path, 4096).splitlines()
        while lines:
            try:
                rows = json.loads(lines[-1]).get("r") or []
            except ValueError:
                lines.pop()
                continue
            break
        else:
            return 0.0
        if not rows:
            return 0.0
        waiting = sum(1 for row in rows if len(row) > 3 and float(row[3]) > 0)
        _DEFERRED_CACHE["value"] = waiting / len(rows)
    except Exception:
        _DEFERRED_CACHE["value"] = 0.0
    return float(_DEFERRED_CACHE["value"])


def tail_text(path: Path, limit: int) -> str:
    """The last *limit* bytes of a file, or "" — the file may be mid-write."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - limit))
            return handle.read().decode("utf-8", "replace")
    except OSError:
        return ""


#: Environment names that must NOT be shipped to a compute node.
#:
#: Everything else is carried verbatim — the agent needs its PATH, its store
#: pointers and its model settings, and they all name paths on the shared
#: filesystem, which is the same filesystem there.
_LOCAL_ONLY_ENV = ("SSH_", "XDG_", "DISPLAY", "TERM", "SHLVL", "_", "OLDPWD",
                   "SLURM_", "FLUX_URI", "FLUX_JOB", "HOSTNAME", "PWD")

#: What a shell will accept on the left of `export NAME=`.
_SHELL_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def remote_agent_command(command: List[str], cwd: Path, env: Dict[str, str],
                         host: str, timeout_s: int,
                         scratch: Optional[Path] = None) -> List[str]:
    """Wrap an agent invocation so it runs on *host* instead of here.

    The agents were launched with a plain `Popen` on whatever machine drove the
    run, which on this cluster is a SHARED LOGIN NODE. Measured at 12 tasks:
    60 `claude` processes and a load average of 10.8 on 48 cores, while every
    one of the six allocated compute nodes sat at load 0.00 — the benchmark
    used its allocation for containers and for nothing else, and the ceiling on
    parallelism was a machine that was not even part of the allocation, shared
    with seventeen other users.

    The agent is sent to the node that already holds its container, so a task's
    reasoning and its test runs share a host and a page cache.

    Passed as a SCRIPT on the shared filesystem rather than as an ssh command
    line: the environment is dozens of variables including paths with spaces,
    and every one of them would otherwise have to survive two levels of shell
    splitting. The script is written where the run can be inspected afterwards.

    `timeout` runs on the far side too. Killing ssh closes the connection but
    does not reliably kill what it started, so the remote process bounds itself;
    the local timeout in `stream_opencode` stays as the backstop.
    """
    import shlex

    directory = Path(scratch or cwd)
    # NEVER inside the checkout's own tree.
    #
    # `scratch` defaults to the working directory, which is the repository the
    # agent is judged on — so a 525-line launcher appeared as a NEW FILE in
    # every `attempt-diff.patch`, was applied to the testbed at evaluation, was
    # listed as the attempt's changed file, and was picked up as the researched
    # approach ("attempted by editing agent-on-node-3f63cbcf0ba8.sh"). It also
    # carries the whole environment, gateway key included, into the artifacts.
    #
    # SCRATCH_DIR is already excluded from the patch via .git/info/exclude, so
    # a checkout gets its launchers there and everything else is unchanged.
    if (directory / ".git").exists():
        directory = directory / SCRATCH_DIR
    directory.mkdir(parents=True, exist_ok=True)
    # One file per LAUNCH, not per directory.
    #
    # A fixed name is a race as soon as two agents start from the same
    # directory, which the research fan-out does by design: the second writer
    # replaces the first one's command and environment, and the first can end
    # up executing the second's prompt against the second's model pin. Nothing
    # downstream could detect it — both are valid scripts.
    script = directory / f"agent-on-node-{uuid.uuid4().hex[:12]}.sh"
    lines = ["#!/bin/bash", "# Written by the harness; runs one agent on one compute node.", ""]
    for key, value in sorted(env.items()):
        if any(key.startswith(skip) or key == skip for skip in _LOCAL_ONLY_ENV):
            continue
        # Only names a shell can actually export.
        #
        # The environment on this cluster carries bash FUNCTIONS — Lmod
        # exports `module` and `ml` as `BASH_FUNC_module%%` and
        # `BASH_FUNC_ml%%`, whose values are multi-line function bodies. Those
        # are not valid identifiers, so the `export` fails, and worse the body
        # runs on past the failed line: the shell then reads `case "$-" in`
        # and the rest of the function as commands, and the script is
        # corrupted from that point on.
        #
        # Measured: every `track` fold produced no record and no output at
        # all, and the same function bodies surfaced as the tail of unrelated
        # error messages (`try 1: unset __lmod_sh_dbg;`), which read like a
        # broken agent rather than a broken script.
        #
        # The functions are no loss: `module`/`ml` are for interactive shells,
        # and everything the agent needs is already in the exported PATH.
        if not _SHELL_NAME.match(key):
            continue
        lines.append(f"export {key}={shlex.quote(str(value))}")
    lines += ["", f"cd {shlex.quote(str(cwd))} || exit 97", ""]
    # `exec` so the shell is replaced: one fewer process for a signal to have
    # to traverse, and the agent's exit status is the script's.
    inner = " ".join(shlex.quote(part) for part in command)
    lines.append(f"exec timeout --signal=TERM --kill-after=30 {int(timeout_s) + 60} {inner}")
    script.write_text("\n".join(lines) + "\n")
    script.chmod(0o755)
    # Multiplexed: thirty agents on five nodes is thirty key exchanges
    # otherwise, and sshd drops them past `MaxStartups`. See `ssh_options`.
    return ["ssh", "-n", *ssh_options(), "-o", "ServerAliveInterval=30",
            host, "bash", str(script)]


def stream_opencode(command: List[str], cwd: Path, env: Dict[str, str],
                    timeout_s: int, on_call=None,
                    root: Optional[Path] = None,
                    stats: Optional[Dict[str, Any]] = None,
                    host: str = "") -> Any:
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

    # On a compute node when this task has one; here when it does not.
    launch = command
    if host:
        launch = remote_agent_command(command, cwd, env, host, timeout_s,
                                      scratch=root or cwd)
    # `errors="replace"`, because `text=True` alone decodes STRICTLY.
    #
    # The agent's stdout is whatever the tools it ran printed, and a repository
    # under test contains binary: one byte of it raised UnicodeDecodeError
    # inside the read loop and took the whole try with it —
    # `attempt-void try 3 did not run (UnicodeDecodeError: 'utf-8' codec can't
    # decode byte 0xac in position 7449808)`. A byte the harness cannot decode
    # must cost that byte, not the attempt.
    process = subprocess.Popen(launch, cwd=str(cwd), env=env, text=True,
                               errors="replace",
                               stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Drain stderr continuously, or the whole thing deadlocks.
    #
    # A pipe holds about 64 KB. This function reads stdout line by line and used
    # to never read stderr at all, so an agent chatty enough to fill that buffer
    # blocked writing to it — and a process blocked on stderr writes no more
    # stdout, so the reader below waited for a line that could not come. Neither
    # side could move and the timeout was the only thing that ever ended it.
    #
    # Observed: seven of ten tasks stalled with the fleet serving only three
    # requests, every stalled thread parked on `for line in process.stdout`.
    # They looked like slow model calls; nothing was being asked of the model.
    errors: List[str] = []

    def drain_stderr() -> None:
        try:
            for line in process.stderr or []:
                errors.append(line)
                # Bounded: a runaway agent must not turn a stall into an OOM.
                if len(errors) > 2000:
                    del errors[:1000]
        except Exception:
            pass

    stderr_reader = threading.Thread(target=drain_stderr, daemon=True)
    stderr_reader.start()

    finished = threading.Event()
    killed = threading.Event()
    over_budget = threading.Event()

    # The budget notifies; a far larger ceiling is what actually kills.
    #
    # Killing at the budget threw away work that was still progressing: every
    # survey stage in a six-task run was cut off at 180s having run 300-400s,
    # and research then continued on partial findings while the arm was scored
    # as though it had researched properly. The budgets are measured against a
    # model roughly six times faster than the one serving this run, so they are
    # a poor kill signal and a good "this is taking longer than expected" one.
    #
    # The hard ceiling still exists, because a wedged agent must not hold a task
    # forever — it is just set where it means "this is broken", not "this is
    # slow".
    # The budget IS the deadline.
    #
    # It used to be advice, with the real stop at 8x — so a 600s `tune` warned
    # at ten minutes and kept working until eighty, and a six-task arm spent
    # fifty minutes without reaching one attempt. Letting a slow stage finish
    # sounds generous and is not: every stage after it waits, and the pass has
    # a deadline of its own.
    #
    # What makes stopping safe is that the work is no longer lost. A stopped
    # stage is followed by a finalize pass that files what it found, and the
    # pipeline moves on. Multiple > 1.0 exists only for a harness that needs a
    # moment to shut down cleanly.
    hard_timeout_s = max(
        timeout_s,
        int(timeout_s * float(_tuned("research.hard_timeout_multiple", 1.0))))

    def kill_later() -> None:
        # The budget bounds WORK, not waiting.
        #
        # It was wall-clock, so a stage queued behind a busy fleet spent its
        # whole allowance without being served: measured at 6x oversubscription,
        # research passes were killed at `rc=-9` after 1241s and stages reported
        # "out of time at 180s" having done almost nothing. That penalises a
        # task for the size of the run it happens to be in, which is not a
        # property of the task.
        #
        # So each tick is charged in proportion to how much of the fleet was
        # actually serving. With every replica queueing, the clock stops; with
        # none, it runs exactly as before. `hard_timeout_s` still bounds the
        # real elapsed time, so a permanently-deferred stage ends rather than
        # becoming immortal.
        tick = 5.0
        charged = 0.0
        began = time.time()
        while charged < timeout_s:
            if finished.wait(min(tick, timeout_s - charged)):
                return
            waiting = deferred_fraction()
            charged += tick * (1.0 - waiting)
            if time.time() - began >= hard_timeout_s:
                break                       # queued the entire time; stop anyway
        over_budget.set()
        if on_call is not None:
            try:
                on_call(f"hit its {timeout_s}s budget — stopping it here and "
                        f"filing what it found")
            except Exception:
                pass
        if hard_timeout_s > timeout_s and finished.wait(
                hard_timeout_s - timeout_s):
            return
        killed.set()
        process.kill()

    # timeout_s <= 0 means no clock at all.
    #
    # Used by the finalize pass, whose whole job is to take what the stopped
    # stage did and produce the result the next stage needs. There is nothing
    # sensible to do with a half-finished handoff, so there is no ceiling to
    # interrupt it — what bounds it is its instruction, which forbids reading
    # files, running commands and searching. It can only write up what is
    # already in front of it.
    watchdog = None
    if timeout_s > 0:
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
        was_killed = killed.is_set()
        finished.set()
        if stats is not None:
            # Truncation has to reach the caller, not just the log. A stage cut
            # off at its budget and a stage that finished early look identical
            # in the totals, and they mean opposite things: one is a stage with
            # time to spare, the other is findings thrown away at full price.
            stats["truncated"] = was_killed
            # Ran long but finished: worth knowing when tuning budgets, and
            # NOT the same as having findings cut off.
            stats["over_budget"] = over_budget.is_set() and not was_killed
            stats["elapsed_s"] = round(time.time() - started_at, 1)
            stats["budget_s"] = timeout_s
            stats["hard_budget_s"] = hard_timeout_s
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
        stderr_reader.join(timeout=5)
        if stats is not None and errors:
            # The agent's own error output, which was previously collected into
            # a pipe nobody read and then thrown away. A harness that hides the
            # error message reports "produced no patch" for a stack trace.
            stats["stderr"] = "".join(errors)[-4000:]
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
                on_call(f"KILLED at the {hard_timeout_s}s hard ceiling after "
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
    # NODE only, not the whole virtualenv.
    #
    # This used to prepend the venv's entire `bin`, which hands the agent the
    # harness's `pip` AND its `python` — and `python` is how you find
    # site-packages. Agents used both: `pip install -e .` put seven task repos
    # in there, and where pip was blocked they wrote `.pth` files by hand
    # (`ourrepo.pth`, `pylint_repo.pth`, `repopath.pth`, each pointing at a
    # task checkout). Every one of those changed what later tasks imported.
    #
    # Measured, the corona venv has no node in it at all, so the exposure
    # bought nothing there whatsoever.
    #
    # A directory of symlinks to node and its friends gives what this function
    # is actually for, and nothing else: the agent's `python` is then the
    # system one, whose site-packages is not the harness's.
    current = env.get("PATH", os.environ.get("PATH", ""))
    node_dir = _node_shim_dir()
    if node_dir and node_dir not in current.split(os.pathsep):
        env["PATH"] = os.pathsep.join([node_dir, current])
    # Belt and braces: `pip` refuses even if some other path reaches one.
    #
    # This function exists for node, and it hands over the whole venv to get
    # it — including `pip`, which is how the harness's own site-packages kept
    # being rewritten by the tasks it was running. `without_harness_venv`
    # strips the venv, and then this puts it straight back, so stripping alone
    # never worked: measured, `pytest 4.6.1.dev145` from a task checkout was
    # editable-installed over the real one and dragged `pluggy` down to
    # 0.13.1, after which the benchmark's own suite could not start.
    #
    # `PIP_REQUIRE_VIRTUALENV` does not help here either — that pip IS in a
    # virtualenv, its own, which is exactly the one being protected.
    #
    # So the guard is a shim earlier on PATH that refuses and says why. Node
    # keeps working, `python` keeps working, and an agent that tries to
    # install gets a message naming the container instead of a silent success
    # in a shared directory.
    env["PATH"] = os.pathsep.join([_pip_guard_dir(), env["PATH"]])
    return env


_PIP_GUARD_LOCK = threading.Lock()


def _node_shim_dir() -> str:
    """A directory linking node/npx/npm from this venv, and nothing else.

    Empty string when the venv has no node — then there is nothing to expose
    and the harness's directory stays off the agent's PATH entirely.
    """
    source = Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin")
    wanted = [name for name in ("node", "npx", "npm")
              if (source / name).exists()]
    if not wanted:
        return ""
    shim = Path(os.environ.get("TMPDIR") or "/tmp") / f"phronix-node-{os.getuid()}"
    with _PIP_GUARD_LOCK:
        try:
            shim.mkdir(parents=True, exist_ok=True)
            for name in wanted:
                link = shim / name
                if not link.exists():
                    link.symlink_to(source / name)
        except OSError:
            return str(source)          # exposure beats a broken agent
    return str(shim)


def _pip_guard_dir() -> str:
    """A directory holding `pip` shims that refuse, made once per process."""
    guard = Path(os.environ.get("TMPDIR") or "/tmp") / f"phronix-pipguard-{os.getuid()}"
    with _PIP_GUARD_LOCK:
        try:
            guard.mkdir(parents=True, exist_ok=True)
            for name in ("pip", "pip3"):
                shim = guard / name
                if not shim.exists():
                    shim.write_text(
                        "#!/bin/sh\n"
                        "echo \"pip is disabled here: this is the benchmark's own\" >&2\n"
                        "echo \"environment, shared by every task. Install inside the\" >&2\n"
                        "echo \"task container instead.\" >&2\n"
                        "exit 1\n")
                    shim.chmod(0o755)
        except OSError:
            return str(guard)
    return str(guard)


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
              base_url: str = DEFAULT_BASE_URL,
              api_key: str = "") -> Dict[str, str]:
    """Model/endpoint settings shared by every arm.

    Raises if the key is absent rather than letting a run start and fail 30 tasks
    later — the failure would look like a benchmark bug rather than a missing
    credential.
    """
    # An explicit key wins: it came from the cluster's own config, and the
    # ambient variable is whatever the shell happened to have.
    key = api_key or os.environ.get(api_key_var, "")
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
    #: Phronix tool calls this attempt made.
    #:
    #: Zero on a phronix arm means the attempt was a plain agent under a
    #: phronix label — the state research treats as fatal, and which scored
    #: identically here because the difference lived only in a trace line.
    phronix_calls: int = 0
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
    #: Is this a from-scratch run?
    #:
    #: Set by the runner from `--fresh`, and passed to the library through
    #: `PHRONIX_FRESH_CAPABILITIES` so that what a run may SEE matches what it
    #: was told to be. Defaults False so an arm built by a test or by hand
    #: behaves like an ordinary carried run.
    fresh: bool = False

    #: Which arm this is, and where its conversation is kept.
    #:
    #: Declared here with empty defaults because the RUNNER assigns them, and an
    #: arm that has not been through the runner — one built by a test, or the
    #: mini arm, which brings its own sandbox — would otherwise raise
    #: `AttributeError` on the first thing that reads them. Every reader already
    #: uses `getattr` with a default, which is the same fix applied one call
    #: site at a time and forgotten at the next one.
    arm_name: str = ""
    conversation_root: Optional[Path] = None
    conversation_subject: str = ""

    #: How many ranked plans the attempt will race against the real tests.
    #:
    #: Set by the runner from `--attempt-candidates`. Research needs it because
    #: what the pass should produce depends on it: with a race coming, the
    #: solution is built AFTER the trials, from what the target tests said.
    #: 0 = every researched plan (the default), N = the top N, 1 = one merged.
    attempt_candidates: int = 0

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
                 base_url: str = DEFAULT_BASE_URL, timeout_s: int = 1800,
                 api_key: str = "") -> None:
        self.model = model
        self.provider = provider
        self.base_url = base_url
        # Carried on the arm rather than read from the environment, because a
        # self-hosted cluster ships its own key in its own config and the
        # ambient OPENAI_API_KEY belongs to a different service entirely.
        self.api_key = api_key
        #: Every model the endpoint serves. One entry is the ordinary case; more
        #: than one turns the candidate-generating stages into a mixture, which
        #: is the only cheap source of genuine diversity when the servers decode
        #: greedily and one model repeats itself.
        self.models: List[str] = [model] if model else []
        #: Model aliases that each resolve to one backend, so a task's turns
        #: stay on the server holding its conversation. Empty means the endpoint
        #: cannot pin and every turn pays full prefill.
        self.pinned_models: List[str] = []
        self.timeout_s = timeout_s
        #: Set per task by the runner. One arm object per arm, so this stays
        #: correct with arms running concurrently.
        self.retrieval_log: Optional[Path] = None

    #: A plan is incomplete without something to measure and something to
    #: measure it on.
    MIN_CORPUS = _tuned("research.min_corpus", 8)

    @staticmethod
    def _one_sentence(text: str, limit: int = 140) -> str:
        """One sentence of an idea's question, for listing what is already held.

        The kept ideas are context for asking about a NEW one, not the subject
        of the request. Passing them in full re-sends paragraphs the planner
        wrote itself and invites it to elaborate on them — which is exactly the
        loop that stalled, four rounds of variations on the same two ideas.
        """
        first = re.split(r"(?<=[.!?])\s", (text or "").strip(), maxsplit=1)[0]
        first = " ".join(first.split())
        return first[:limit].rstrip() + ("…" if len(first) > limit else "")

    @staticmethod
    def _plan_gaps(topic: str, minimum: int) -> List[str]:
        """What the plan still owes, as a list of plain names. Deterministic.

        The ideas had a corrector and the plan's other two outputs did not,
        which is why tasks reached `build-solution` with `0 inst` and `fom=-` —
        a solution built with nothing to measure it against, and no signal that
        anything was missing. Measured across one six-task run: three of six.

        This is arithmetic over the record, not a judgement, so it belongs in
        the harness rather than in an agent: a corrector that can be talked out
        of its verdict is not a corrector.
        """
        from phronix import research as research_module

        record = research_module.status(topic) or {}
        gaps = []
        if not (record.get("fom") or {}):
            gaps.append("a figure of merit (`research_define_fom`)")
        if len(record.get("instances") or []) < minimum:
            have = len(record.get("instances") or [])
            gaps.append(f"a corpus of at least {minimum} instances "
                        f"(`research_declare_corpus`, `research_add_instances`, "
                        f"`research_split`) — there are {have}")
        return gaps

    @staticmethod
    def _thin_gaps(topic: str) -> Dict[str, str]:
        """Idea name -> what the exploration validator said was missing.

        The DETAIL matters as much as the name: a second pass told only that it
        was "thin" repeats the first one, and a second pass told "the relative
        form was never tried" closes the gap. So the verdict travels as data —
        a corrector whose reasoning has to be recovered by reading English
        fails quietly the first time it phrases itself oddly.
        """
        from phronix import research as research_module

        record = research_module.status(topic) or {}
        out: Dict[str, str] = {}
        for note in record.get("notices") or []:
            if (note.get("kind") or "") != "thin":
                continue
            name = (note.get("what") or "").strip()
            if not name:
                continue
            detail = (note.get("detail") or "").strip()
            # First notice wins: a later one is usually the same gap restated.
            out.setdefault(name, detail or "no detail was given")
        return out

    def _skill_is_for(self, store_root: Path, skill: str, topic: str) -> bool:
        """Does this skill actually belong to this task's research record?

        Checked against the record rather than by comparing names: a skill is
        the right one when the topic's own record points at it, and a fuzzy
        name match is precisely the thing that went wrong.
        """
        from phronix import research as research_module

        record = self._in_store(store_root, research_module.status, topic) or {}
        for key in ("skill", "topic_skill", "pipeline_skill"):
            named = (record.get(key) or "")
            if isinstance(named, str) and named and named == skill:
                return True
        # The NAMING CONVENTION, which is available before the pointer is.
        #
        # Those pointers are written when a pass finishes; skills are written
        # throughout it. So there is a window — long, because each idea is
        # written up as it lands — where the skill exists and nothing points at
        # it. Measured on `pylint-dev__pylint-7114`: while `build-solution` was
        # still running, every racer was told
        #
        #   [recall] `pylint-dev-pylint-7114` was written for another problem
        #            in this area — offered as knowledge, not as the plan
        #
        # about a skill named for THIS problem, demoting the task's own answer
        # to background reading.
        #
        # Not fuzzy matching: `candidate_skill_name` DERIVES these names so that
        # several writers and a reader agree without negotiating, and reading
        # that back is deterministic.
        mine = self.candidate_skill_name(topic, "")
        prefix = mine[:-1] if mine.endswith("-") else mine
        if skill == prefix or skill.startswith(f"{prefix}-"):
            return True

        # Same PROBLEM, differently spelled.
        #
        # The issue NUMBER is the discriminator: `pylint-dev__pylint-7114` and
        # `-7080` are both pylint and both about module resolution, and they are
        # not the same bug. A plain substring test is what gets this right — a
        # cleverer pattern matched `1379` inside `21379` and rejected a task's
        # own skill, the one answer that was certainly correct.
        number = re.sub(r"[^0-9]", " ", str(topic)).split()
        if number and number[-1] in skill:
            return True

        # No record yet is not a mismatch: nothing has claimed the skill, so
        # the ordinary lookup stands.
        return not record.get("aspects") and not record.get("approaches")

    def recalled_skill(self, store_root: Path, instance: Dict[str, Any]) -> str:
        """A skill from an earlier session that covers this task's subject.

        Retrieval-first is the whole point of carrying a store between runs: if
        a previous session solved something on this repository and wrote the
        pipeline down, the next task should start from it rather than
        rediscover it. Without this the store grew and was never read except by
        the task that wrote it.

        Bundled skills are excluded. They ship with the framework and are
        retrieved through the ordinary context, so naming one here would
        announce a "remembered solution" that is nothing of the kind.
        """
        repo = str(instance.get("repo", "") or "")
        subject = repo.split("/")[-1] if repo else ""
        if not subject:
            return ""
        try:
            from phronix import skills as skills_module

            found = self._in_store(store_root, skills_module.search,
                                   f"how to solve a {subject} task") or {}
        except Exception:
            return ""
        # `search` returns an ENVELOPE: {status, query, count, results}.
        #
        # Iterating it directly yields those four keys, so the first "skill
        # name" it produced was `status` — which is exactly what was recalled
        # for a pylint task, and why the subject filter below then rejected
        # everything and recall silently never fired again. The names live in
        # `results[*]["skill"]`.
        hits = found.get("results") if isinstance(found, dict) else found
        bundled = _bundled_skill_names()
        # What `--fresh` allows this run to see.
        #
        # `skills.search` is its OWN read path: it indexes every layer and
        # knows nothing about the fresh filter, so excluding `bundled` — which
        # is the framework's `skills/` directory — let a bundled TASK ANSWER
        # through. Measured after promotion started writing answers into the
        # packaged tree: a `--fresh` run reported "no skill covers this task;
        # solving from scratch" on the harness path and then, one line later,
        # "trying remembered skill `scikit-learn-column-transformer-empty-
        # columns`" on this one. Two retrieval paths, one filter between them.
        #
        # `skill_dirs` applies that filter, so a name it does not list is a
        # name this run is not entitled to.
        try:
            from phronix.layers import skill_dirs

            allowed = set(skill_dirs())
        except Exception:
            allowed = set()
        for hit in hits or []:
            name = (hit.get("skill") or hit.get("name") or "") if isinstance(
                hit, dict) else str(hit)
            if not name or name in bundled:
                continue
            if allowed and name not in allowed:
                continue
            # The hit has to be ABOUT this subject. Search ranks by relevance
            # and always returns its best guess, so a store with nothing for
            # this repository still answers.
            if subject.lower() in name.lower():
                return name
        return ""

    def model_for_task(self, instance: Dict[str, Any]) -> str:
        """Which model name this task should ask for.

        Hashed on the instance id so it is stable: a retry returns to the
        backend that still holds the conversation, and both arms of one task
        share a backend and therefore its warm prefix.
        """
        if not self.pinned_models:
            return ""
        return self.pinned_models[self._pin_index(instance)]

    def _pin_index(self, instance: Dict[str, Any]) -> int:
        """Which backend this arm's turns go to. Stable, and evenly spread.

        Keyed on the ARM as well as the task. The two arms of one task were
        deliberately given the same backend, on the reasoning that they would
        share a warm prefix. They do not: the bare and phronix arms send
        different system prompts and diverge from the first token, so there is
        no prefix to share — and once a backend has a single slot, sending both
        there means each arm waits for the other.

        Assigned ROUND-ROBIN rather than by hashing the key.

        `sha256(key) % N` is balls-in-bins, and at the sizes that matter here
        it does not spread: measured on this group with 14 arms across 16
        backends, it used 8 of them — one backend drew three arms, several drew
        two, and half the fleet drew nothing. The fleet reported it exactly:
        `8/16 replica(s) active`, `work 0.227 (IMBALANCED)`, and zero deferred
        requests while half the GPUs idled. Hashing gives an arbitrary but
        stable answer, and stability is the only property actually needed —
        so the assignment is handed out in order and then remembered, which is
        stable AND even.

        The counter is shared by every arm in the process, because the spread
        that matters is across everything running at once, not within one arm.
        """
        if not self.pinned_models:
            return 0
        key = f"{getattr(self, 'arm_name', '')}:{instance.get('instance_id', '')}"
        with _PIN_LOCK:
            if key not in _PIN_ASSIGNED:
                _PIN_ASSIGNED[key] = len(_PIN_ASSIGNED)
            return _PIN_ASSIGNED[key] % len(self.pinned_models)

    def fanout_models(self, instance: Dict[str, Any], width: int) -> List[str]:
        """Distinct backends for `width` agents that run at the same time.

        A task's pin keeps its OWN turns on one backend, which is what makes
        the prompt cache work. Applied to a fanout it does the opposite: eight
        aspect agents are eight separate conversations, and sending them all to
        the task's single backend serialises them behind one another.

        That is harmless when a backend has four slots and fatal when it has
        one — which is exactly the trade the `solo` profile makes. So a fanout
        walks outward from the task's own pin: neighbouring backends, distinct
        per position, stable across retries because the starting point is the
        task hash rather than a counter.

        Each agent keeps ONE alias for its whole stage, so its own turns still
        land together and still hit a warm prefix. What is spread is agents,
        not turns.
        """
        if not self.pinned_models or width <= 1:
            return []
        start = self._pin_index(instance)
        total = len(self.pinned_models)
        return [self.pinned_models[(start + offset) % total]
                for offset in range(min(width, total))]

    @property
    def qualified_model(self) -> str:
        return f"{self.provider}/{self.model}"

    def solution_skill_path(self, *_args, **_kwargs) -> str:
        """No solution skill on an arm that writes no skills."""
        return ""

    def best_skill_for(self, *_args, **_kwargs) -> str:
        """Nothing to recall on an arm with no store to recall from."""
        return ""

    def reconcile_trials(self, *_args, **_kwargs) -> None:
        """No trials to reconcile on an arm that does not research."""

    def candidate_plans(self, *_args, **_kwargs) -> List[Dict[str, str]]:
        """No researched plans on an arm that does not research.

        Defined here rather than guarded at the call site, for the same reason
        as `start_learning` below: the runner calls this on whatever arm it has,
        and an attribute only some arms carry is a `hasattr` in the caller that
        quietly does nothing the day the name changes.
        """
        return []

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

    #: How often the always-on tracker folds what it has been handed.
    #:
    #: The same shape as the learner's clock, and for the same reason: several
    #: events fold in one invocation instead of one invocation per event.
    TRACK_CYCLE_S = float(_tuned("tracking.cycle_seconds", 30.0))

    #: How long a stage will wait for its own event to reach the record.
    #:
    #: Only the stages that READ the record need this — research, and the
    #: snapshot at the end. Everything else pushes and carries on, which is
    #: what makes the cost amortised rather than per-phase.
    TRACK_WAIT_S = float(_tuned("tracking.wait_seconds", 240.0))

    def _tracker_state(self, task_dir: Path) -> "_TrackerState":
        """The always-on tracker for this task.

        Takes the TASK directory, never an attempt directory. The record is
        per task and the key is its path, so a caller that passed an attempt
        dir would silently get a second tracker writing a second record one
        level down — two histories for one task, and neither complete. The
        methods that are handed an attempt dir convert it at the call.
        """
        tracker = Path(task_dir) / self.TRACKER_FILE
        key = str(tracker)
        with _TRACKER_LOCK:
            found = _TRACKERS.get(key)
            if found is None:
                found = _TrackerState(tracker=tracker, stop=threading.Event())
                _TRACKERS[key] = found
        return found

    def start_tracking(self, instance: Dict[str, Any], store_root: Path,
                       task_dir: Path, on_call=None) -> None:
        """Run one tracker for this task, folding events on a clock.

        The record used to be written by a STAGE: an agent invoked after every
        phase, which re-read everything and rewrote the file. That cost a whole
        session per phase, and when the agent flailed it burned its entire
        clock and produced nothing — measured on scikit-learn-25570, 900s spent
        on "looking for files named like tracker.md" and an empty record, after
        which research ran with nothing to read (`fom=NONE approaches=0`).

        So the tracker becomes what the learner already is: always on, fed by
        events, reconciling on its own clock. A phase pushes what it did and
        carries on; several events fold in one invocation; and by the time a
        stage needs the record it is already in order.

        It never blocks the pipeline. A cycle that fails loses that cycle, the
        events stay queued for the next one, and the thread is a daemon so a
        wedged tracker cannot hold the run open.
        """
        state = self._tracker_state(task_dir)
        with state.lock:
            if state.thread is not None:
                return

            def cycle() -> None:
                while not state.stop.is_set():
                    state.stop.wait(self.TRACK_CYCLE_S)
                    self._fold_events(instance, store_root, task_dir, state,
                                      on_call=on_call)

            state.thread = threading.Thread(target=cycle, daemon=True,
                                            name=f"tracker-{state.tracker.parent.name}")
            state.thread.start()
        if on_call:
            on_call(f"[track] running: folding every {self.TRACK_CYCLE_S:.0f}s")

    def note_event(self, task_dir: Path, phase: str, cost: str = "",
                   evidence: Optional[List[Path]] = None) -> int:
        """Hand the tracker what just happened. Returns this event's number.

        Deterministic and cheap — a list append, no model, no file. The number
        is what lets a stage that must read the record wait for its own event
        to have landed rather than for a fixed delay.
        """
        state = self._tracker_state(task_dir)
        with state.lock:
            state.queued += 1
            state.pending.append({"phase": phase, "cost": cost or "not measured",
                                  "at": time.strftime("%H:%M:%S"),
                                  "n": state.queued})
            for path in (evidence or []):
                if Path(path).is_file() and str(path) not in state.evidence:
                    state.evidence.append(str(path))
            return state.queued

    def _fold_events(self, instance: Dict[str, Any], store_root: Path,
                     workdir: Path, state: "_TrackerState", on_call=None) -> None:
        """Fold everything queued into the record, in one invocation."""
        with state.lock:
            events = list(state.pending)
            evidence = list(state.evidence)
            state.pending = []
        if not events:
            return

        highest = max(int(e["n"]) for e in events)
        # One line per DISTINCT phase, with a count.
        #
        # A fold of "attempt (12s), attempt (12s), attempt (11s)" hands the
        # tracker the same fact three times, and it writes it down three
        # times. A later attempt reading the record then cannot tell whether
        # it is looking at three findings or one, and pays three reads to
        # learn one thing. Collapsed here, where the events still have
        # structure, rather than asked of a model afterwards.
        counted: Dict[str, int] = {}
        costs: Dict[str, str] = {}
        for event in events:
            key = str(event["phase"])
            counted[key] = counted.get(key, 0) + 1
            costs.setdefault(key, str(event["cost"]))
        phases = ", ".join(
            f"{name} ({costs[name]})" if n == 1 else f"{name} x{n} ({costs[name]})"
            for name, n in counted.items())
        files = [Path(p) for p in evidence if Path(p).is_file()]
        if state.tracker.is_file():
            files.append(state.tracker)
        prompt = self.TRACK_PROMPT.format(
            topic="{topic}", phase=phases, tracker=str(state.tracker),
            cost=f"{len(events)} phase(s) since the last fold")
        if on_call:
            on_call(f"[track] folding {len(events)} event(s): {phases}")
        try:
            self.standalone_stage(
                instance, store_root, workdir, prompt,
                attachments=[str(f) for f in files],
                timeout_s=self.RECORD_GUARD_S, agent=self.tracker_agent_name,
                phase="track", cwd=state.tracker.parent, on_call=on_call)
        except Exception as exc:
            # A cycle that fails loses the cycle, not the events: they are
            # already out of `pending`, so they are put back for the next one.
            with state.lock:
                state.pending = events + state.pending
            if on_call:
                on_call(f"[track] fold failed, {len(events)} event(s) requeued: "
                        f"{type(exc).__name__}: {exc}")
            return

        with state.lock:
            state.cycles += 1
            state.folded = max(state.folded, highest)
        with state.moved:
            state.moved.notify_all()

    def await_record(self, task_dir: Path, upto: int = 0, on_call=None) -> bool:
        """Wait until the record includes event *upto*. True if it does.

        Bounded, and the caller proceeds either way: an out-of-date record is
        worse than a current one and far better than a stage that never runs.
        """
        state = self._tracker_state(task_dir)
        target = upto or state.queued
        deadline = time.time() + self.TRACK_WAIT_S
        with state.moved:
            while state.folded < target and time.time() < deadline:
                if state.pending or state.thread is not None:
                    state.moved.wait(timeout=min(5.0, max(0.1, deadline - time.time())))
                else:
                    break
        current = state.folded >= target
        if not current and on_call:
            on_call(f"[track] the record is behind ({state.folded}/{target} "
                    f"event(s) folded) — reading it as it stands")
        return current

    def stop_tracking(self, task_dir: Path, instance: Optional[Dict[str, Any]] = None,
                      store_root: Optional[Path] = None, on_call=None) -> None:
        """Fold what is left and stop this task's tracker."""
        state = self._tracker_state(task_dir)
        state.stop.set()
        if instance is not None and store_root is not None:
            self._fold_events(instance, store_root, task_dir, state, on_call=on_call)
        thread = state.thread
        if thread is not None:
            thread.join(timeout=5.0)
        with _TRACKER_LOCK:
            _TRACKERS.pop(str(state.tracker), None)

    def track(self, instance: Dict[str, Any], store_root: Path, workdir: Path,
              phase: str, evidence: Optional[List[Path]] = None,
              on_call=None, cost: str = "", wait: bool = False) -> Path:
        """Hand what just happened to this task's tracker. Returns the record.

        A PUSH, not a stage. This used to invoke an agent after every phase,
        which re-read everything and rewrote the record from scratch — a whole
        session per phase, per task. It was the most expensive thing in the
        pipeline and the least reliable: measured across one run, 163 of 241
        stage kills were `track` hitting its ceiling, and raising the ceiling
        only made each failure longer. On scikit-learn-25570 it spent 900s on
        "looking for files named like tracker.md" and wrote nothing, after
        which research ran with no record at all.

        Now the phase records an EVENT — a list append, no model, no file —
        and the always-on tracker folds several of them per invocation on its
        own clock. The cost is amortised across the phases instead of charged
        to each one, and the record is already in order by the time anything
        reads it.

        `wait=True` is for the stages that READ the record — research, and the
        snapshot at the end. They wait for their own event to have landed, and
        proceed on a stale record rather than not at all if it has not.

        The record lives beside the task and never leaves it. Two tasks that
        look alike are still two tasks: an established fact from one is an
        assumption in the other, and an assumption presented as established is
        worse than nothing, because the next phase will not re-check it.
        """
        task_dir = Path(workdir).parent
        state = self._tracker_state(task_dir)
        mine = self.note_event(task_dir, phase, cost=cost, evidence=evidence)
        if on_call:
            on_call(f"[track:{phase}] recorded ({cost or 'not measured'})")
        if wait:
            # Fold now rather than waiting out the clock: the reader is here.
            self._fold_events(instance, store_root, workdir, state,
                              on_call=on_call)
            self.await_record(task_dir, upto=mine, on_call=on_call)
            self._reshape_if_needed(instance, store_root, workdir,
                                    state.tracker, phase, on_call=on_call)
        return state.tracker

    def _reshape_if_needed(self, instance: Dict[str, Any], store_root: Path,
                           workdir: Path, tracker: Path, phase: str,
                           on_call=None) -> None:
        """Ask once for the shape the next phase reads, if it is not there.

        Checked rather than merely asked for, and asked again only ONCE: the
        content is there either way, and a record in the wrong shape is worth
        more than no record.
        """
        missing = self.missing_sections(tracker)
        if not missing:
            return
        if on_call:
            on_call(f"[track:{phase}] the record is missing "
                    f"{', '.join(missing)} — asking for it in the shape "
                    f"the next phase reads")
        self.standalone_stage(
            instance, store_root, workdir,
            self.RESHAPE_PROMPT.format(
                tracker=str(tracker), missing=", ".join(missing),
                sections="\n".join(f"    {s}" for s in self.TRACKER_SECTIONS)),
            attachments=[str(tracker)], timeout_s=self.RECORD_GUARD_S,
            agent=self.tracker_agent_name, phase="track",
            cwd=tracker.parent, on_call=on_call)
        still = self.missing_sections(tracker)
        if still and on_call:
            on_call(f"[track:{phase}] ** still missing {', '.join(still)} "
                    f"— the record is organised by something other than "
                    f"what the next phase reads")

    @classmethod
    def missing_sections(cls, tracker: Path) -> List[str]:
        """Which required headings the record does not have."""
        try:
            text = Path(tracker).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return list(cls.TRACKER_SECTIONS)
        return [s for s in cls.TRACKER_SECTIONS if s not in text]

    def standalone_stage(self, instance: Dict[str, Any], store_root: Path,
                         workdir: Path, prompt: str,
                         attachments: Optional[List[str]] = None,
                         timeout_s: int = 300, agent: str = "",
                         phase: str = "", cwd: Optional[Path] = None,
                         on_call=None) -> str:
        """Run one agent outside the research flow, and return what it said.

        `research()` has its own `stage()` closure bound to a pass's budgets and
        trees. The tracked loop runs stages that are not part of a pass — the
        tracker after every phase, the research pass between attempts — so they
        need an invocation of their own rather than a closure lifted out of a
        function that also owns the plan loop.
        """
        checkout = Path(cwd) if cwd is not None else Path(workdir) / "repo"
        if not checkout.is_dir():
            checkout = Path(workdir)
        self.research_topic_binding = self.research_topic(instance)
        env = self.phronix_env(
            tool_path_env(isolated_env(store_root, Path(workdir) / "cache", fresh=self.fresh)))
        env.update(model_env(base_url=self.base_url, api_key=self.api_key))
        env["PHRONIX_WRITE_LAYER"] = "project"
        if phase:
            env["PHRONIX_PHASE"] = phase
        # Which TREE this stage's skills belong in.
        #
        # The research stage is investigating a SUBJECT, and a subject outlives
        # the task that raised it — "how does this project discover test files"
        # is asked by every task in the repository. Its findings go to
        # `research/skills/<subject>/`. Everything else is working on the task
        # at hand and writes to `capabilities/`, which is also where the
        # learner files what repeats across tasks.
        #
        # Set by the harness rather than inferred from the skill's name: the
        # agent picks the name, and no naming convention has survived contact
        # with one yet.
        env["PHRONIX_SKILL_TREE"] = "research" if phase == "research" else ""
        # ...with the task's own solution exempted by NAME.
        #
        # The research stage writes both: the task's solution, and whatever it
        # learned about the subject. Only the second belongs in `research/` —
        # a solution filed there is invisible to the next attempt, which asks
        # `capabilities/` for the task it is about to attempt.
        try:
            env["PHRONIX_TASK_SKILL"] = self.task_skill_name(
                self.research_topic(instance))
        except Exception:
            env["PHRONIX_TASK_SKILL"] = ""
        # Which task's conversation the `conversation_*` tools serve.
        #
        # Set per stage rather than per run: the record is per task, and a
        # conversation from the wrong task is worse than none, because nothing
        # in the text says which task it belongs to.
        env["PHRONIX_TASK_DIR"] = str(Path(workdir).parent)
        if self.store_readonly:
            env["PHRONIX_BENCH_FROZEN"] = "1"
        import subprocess

        command = self.agent_command(prompt, checkout, list(attachments or []),
                                     agent=agent)
        try:
            with private_home(dict(env)) as run_env:
                # STREAMED, not captured.
                #
                # `subprocess.run` returns nothing until the process exits,
                # which for a five-minute research pass is five minutes in
                # which a working agent and a dead one look identical. The
                # trace showed `diagnosing the open failure, 300s` and then
                # nothing at all — the stage was working and there was no way
                # to see it, or to see it stop.
                #
                # `stream_opencode` reads the event stream line by line and
                # reports each tool call, which is what every stage in the
                # research flow already does. It closes stdin for the same
                # reason `subprocess.run` had to.
                stdout, code = stream_opencode(
                    command, checkout, run_env, timeout_s, on_call=on_call,
                    host=self.agent_host)
        except Exception as exc:
            # SAID, not swallowed.
            #
            # This returned "" on any failure, which made a stage that could
            # not start indistinguishable from one that ran and produced
            # nothing. Measured on the tracker's first live run: the stage
            # announced "folding into tracker.md", the next stage began in the
            # same second, and no record appeared — a zero-second stage
            # reported as a completed one.
            if on_call:
                on_call(f"[{phase or 'stage'}] could not run: "
                        f"{type(exc).__name__}: {str(exc)[:160]}")
            return ""
        if code and on_call:
            on_call(f"[{phase or 'stage'}] exited rc={code}: "
                    f"{(stdout or '').strip()[-300:]}")
        return stdout or ""

    SNAPSHOT_PROMPT = """\
This task is finished. Build the skill a later run on this subject will load
before it starts.

`skill_load("phronix-learn-from-attempt")` is the method — `I7` on naming, `I9`
on what belongs in a skill rather than a memory.

Task: `{topic}`
The record: `{tracker}` — the problem, how it was approached, what worked, what
did not. Everything the task learned is in there; the fix alone is half of it.
Outcome: **{outcome}**

    skill_write(name="{skill}", ...)

That exact name. A later run looks it up rather than searching.

Five things, in this order:

1. **What problem it solves** — the symptom a later run would recognise, not
   the issue text. Someone arrives with a failing test; this is how they tell
   whether this skill is about their problem.
2. **The key idea** — the one insight the whole fix turns on, in a sentence.
   For this subject that is a claim like "the email field is not always called
   `email`", not a description of the diff.
3. **Instructions to solve it** — the change, precisely enough to apply: file,
   function, what the line becomes. Numbered, in order.
4. **Constraints and rules** — what must stay true while solving it. What must
   keep passing, what must not be touched, the invariant the obvious fix
   breaks. Take these from **What worked**: those are banked and a later run
   must not regress them.
5. **Pitfalls and lessons** — take these from **What did not work**, with the
   reason each failed. This is the most valuable section and the one only this
   task can write: a later run gets the ruled-out approaches for free instead
   of spending an attempt each rediscovering them.

Write it whether the task passed or not. A task that failed after four attempts
knows more about its subject than one that passed on the first — sections 1, 2,
4 and 5 are all still true, and section 3 says how far it got and what remains.
"""

    @staticmethod
    def assistant_text(stdout: str) -> str:
        """The agent's own words, with the event envelopes stripped out.

        The stream is JSON lines: tool calls, results, signatures, usage. Only
        the `text` blocks are what the agent SAID, and only those can carry a
        report. Reading raw stdout instead put envelope fragments into the
        trace and into the record — measured live, a base64 thinking signature
        was parsed and displayed as a finding.
        """
        said: List[str] = []
        for line in (stdout or "").splitlines():
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(event, dict):
                continue
            blocks = ((event.get("message") or {}).get("content")
                      or event.get("content") or [])
            if isinstance(blocks, str):
                said.append(blocks)
                continue
            for block in blocks if isinstance(blocks, list) else []:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = (block.get("text") or "").strip()
                    if text:
                        said.append(text)
        return "\n".join(said)

    @staticmethod
    def task_skill_name(topic: str) -> str:
        """The one skill this task owns, named after the task.

        Every writer and the reader derive it here, because a name computed in
        two places is a name they will eventually disagree about — and a skill
        filed under a name nothing reads is a skill that was never written.
        """
        return re.sub(r"[^a-z0-9]+", "-", str(topic).lower()).strip("-")

    RENAME_PROMPT = """\
The skill for this task has to be filed under one name, and it is not.

Expected: `{skill}`
Found instead: {found}

A later run does not search for a skill — it looks up `{skill}` and takes what
is there. A descriptive name is invisible to it however good the content is.

Write the content under the right name now:

    skill_write(name="{skill}", ...)

Take everything from the skill(s) named above; nothing needs re-deriving. If
there are several, merge them — one task, one skill.
"""

    def _refile_task_skill(self, store_root: Path, wanted: str,
                           found: List[str], on_call=None) -> bool:
        """Move what this task wrote under other names to the canonical one.

        Deterministic: reads the stray files, merges them, rewrites the
        frontmatter name, and writes the result where the lookup will find it.
        Returns whether the canonical skill now exists.
        """
        from tests.benchmark.isolation import merge_skill_text

        tasks = Path(store_root) / "capabilities" / "tasks"
        target = None
        try:
            from phronix.capabilities import task_slug

            target = tasks / task_slug(wanted) / wanted / "SKILL.md"
        except Exception:
            target = tasks / wanted / wanted / "SKILL.md"

        merged = target.read_text(errors="replace") if target.is_file() else ""
        for name in found:
            for stray in sorted((tasks).glob(f"*/{name}/SKILL.md")):
                try:
                    merged = merge_skill_text(merged, stray.read_text(errors="replace"))
                except (OSError, ValueError):
                    continue
        if not merged.strip():
            return False

        # The frontmatter has to name the skill the reader asks for, or the
        # file is in the right place under the wrong identity.
        merged = re.sub(r"(?m)^name:.*$", f"name: {wanted}", merged, count=1)
        merged = re.sub(r"(?m)^subject:.*$", f"subject: {wanted}", merged, count=1)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(merged)
        except OSError as exc:
            if on_call:
                on_call(f"[skill] could not write `{wanted}`: {exc}")
            return False
        if on_call:
            on_call(f"[skill] re-filed {len(found)} skill(s) into `{wanted}`")
        return True

    #: The placeholder a skill is opened with, matched to retire it later.
    PLACEHOLDER_TITLE = "Nothing is established about this subject yet"

    def retire_placeholder(self, store_root: Path, skill: str) -> bool:
        """Drop the "nothing is established" rule once something is.

        The placeholder exists so a skill always exists — a later pass needs
        somewhere to write, and existence is the one property obtainable
        without a model. It was meant to be replaced as soon as anything was
        learned, and nothing enforced that.

        Measured on `sphinx-doc-sphinx-8595`: the skill carried the exact
        diff that had made the task PASS, under `I1`, and alongside it kept
        `R1 — Nothing is established about this subject yet` and the
        description `What is known about sphinx-doc__sphinx-8595. Nothing
        yet.` The next run loaded it, ran 44 steps and 2.7M tokens, and
        produced no patch. A skill that hands over the answer and twice tells
        its reader nothing is known is worse than either alone, and the
        description is the main retrieval signal.

        Deterministic, because retiring a placeholder is not a judgement.
        """
        from phronix import skill_schema, skills as skills_module

        home = skills_module.existing_home(skill)
        if home is None or not (Path(home) / "SKILL.md").is_file():
            return False
        parsed = skill_schema.parse_skill(Path(home))
        blocks = list(parsed.get("blocks") or [])
        real = [b for b in blocks
                if str(b.get("title") or "") != self.PLACEHOLDER_TITLE]
        # Only when something real is actually there. An empty skill keeps
        # its placeholder: that is what makes it a valid skill at all.
        if len(real) == len(blocks) or not real:
            return False
        subject = str(parsed.get("subject") or skill)
        described = str(parsed.get("description") or "")
        if "Nothing yet" in described or not described.strip():
            titles = ", ".join(str(b.get("title") or "") for b in real[:2])
            described = f"What is known about {subject}: {titles}"[:300]
        try:
            (Path(home) / "SKILL.md").write_text(
                skill_schema.render_skill(skill, described, subject, real),
                encoding="utf-8")
        except OSError:
            return False
        return True

    #: Told to the attempt when a lessons file comes with the skill.
    LESSONS_NOTE = """

`LESSONS.md` is attached: approaches that have already been tried on this
subject and what each one cost. Do not spend a step re-deriving one of them.
An entry there is not a forbidden idea — it is a result, and the reason to
try something else unless you have a specific reason it was wrong.
"""

    @staticmethod
    def _lessons_for(store_root: Path, skill: str) -> Optional[Path]:
        """This skill's `LESSONS.md`, if it exists and says anything.

        An empty lessons file is worse than none: it costs an attachment and
        tells the reader that nothing has been ruled out, which is a claim
        rather than an absence.
        """
        if not skill:
            return None
        try:
            from phronix import skills as skills_module

            home = skills_module.existing_home(skill)
        except Exception:
            home = None
        candidates = []
        if home is not None:
            candidates.append(Path(home) / "LESSONS.md")
        candidates += list(Path(store_root).glob(f"*/*/{skill}/LESSONS.md"))
        candidates += list(Path(store_root).glob(f"*/*/*/{skill}/LESSONS.md"))
        for path in candidates:
            try:
                if path.is_file() and len(path.read_text(errors="replace").strip()) > 200:
                    return path
            except OSError:
                continue
        return None

    def open_task_skill(self, instance: Dict[str, Any], store_root: Path,
                        workdir: Path, on_call=None) -> str:
        """Make sure this task HAS a skill, writing an empty one if it does not.

        The skill must exist whether or not anything worked. It is what the
        next attempt looks up, what the next research pass reads before it
        starts, and what a later run finds — and "nothing worked" is a fact
        about the subject worth carrying, not an absence.

        Measured across one 300-task run: 356 research passes, 65 attempts that
        found a skill, and 489 that opened with "no skill covers this task;
        solving from scratch". Research was being asked for a skill and the
        request was all that stood behind it: when the pass produced nothing,
        nothing noticed until the task ended.

        Written by the HARNESS, not by asking an agent again. A re-ask has the
        same failure mode as the ask — the run above shows what that is worth —
        and existence is the one property that can be guaranteed without a
        model. The file is deliberately thin: a rule saying nothing is
        established yet, which later passes replace as they learn something.
        `skill_write` appends and reorganises, so an empty skill is a place to
        put knowledge rather than something to be worked around.
        """
        topic = self.research_topic(instance)
        wanted = self.task_skill_name(topic)

        def create() -> Any:
            from phronix import skills as skills_module

            return skills_module.write_block(
                wanted, "rule",
                "Nothing is established about this subject yet",
                "No attempt has produced a passing fix, and no diagnosis has "
                "been recorded. Treat every approach as untried: there is no "
                "ruled-out list here to trust, and nothing below has been "
                "verified against the tests.\n\n"
                f"Subject: `{topic}`. Replace this rule as soon as anything is "
                "actually established — it exists so that the next pass has "
                "somewhere to write, not because it says anything.",
                description=f"What is known about {topic}. Nothing yet.")

        try:
            outcome = self._in_store(store_root, create) or {}
        except Exception as exc:                  # a missing skill is not a failed task
            if on_call:
                on_call(f"[skill] could not open `{wanted}`: "
                        f"{type(exc).__name__}: {exc}")
            return ""
        if str(outcome.get("status")) not in ("ok", "already_present"):
            if on_call:
                on_call(f"[skill] ** `{wanted}` still does not exist "
                        f"({outcome.get('status')}) — the next attempt will "
                        f"start from scratch")
            return ""
        if on_call:
            on_call(f"[skill] nothing was recorded for this task; opened "
                    f"`{wanted}` empty so the next pass has somewhere to write")
        return wanted

    def ensure_task_skill(self, instance: Dict[str, Any], store_root: Path,
                          workdir: Path, on_call=None) -> str:
        """Make sure this task's skill exists under the name the reader uses.

        Told the exact name and given the tool, agents still invent their own.
        Measured in one run: `django-django-13551` and
        `matplotlib-matplotlib-24970` were written correctly, and beside them
        sat `django-password-reset-token-email-invalidation` and
        `matplotlib-24970-numpy-deprecation` — good content under names the
        lookup will never ask for. matplotlib-24970 then opened its next
        attempt with "no skill covers this task; solving from scratch" while
        its own diagnosis sat in the store.
        """
        topic = self.research_topic(instance)
        wanted = self.task_skill_name(topic)
        if self.best_skill_for(store_root, topic) == wanted:
            return wanted
        # Anything this task wrote under another name, so the re-ask can merge
        # rather than re-derive.
        tasks = Path(store_root) / "capabilities" / "tasks"
        # Matched on THIS TASK's issue number, not on a name stem.
        #
        # The stem was `wanted.split("-")[0]` — "pydata" for
        # `pydata-xarray-3364` — which matches every other pydata task in the
        # group. So a task merged a NEIGHBOUR's skill into its own and then
        # `rmtree`d it. Measured in one run: `pydata-xarray-3364` and
        # `pydata-xarray-4493` are different tasks, each matched the other,
        # and 3364's skill was destroyed by 4493's re-file while 4493's
        # content — real instructions about `dtypes.py` and `GroupBy.__repr__`
        # — ended up offered to 3364, whose bug is in `concat.py`.
        #
        # The issue number is what makes two names the same TASK. A skill the
        # agent misnamed with a different number is left alone rather than
        # absorbed: losing one misfiled skill costs this task a diagnosis,
        # while stealing one costs another task its answer AND gives this one
        # the wrong instructions.
        digits = re.findall(r"\d+", wanted)
        issue = digits[-1] if digits else ""
        def belongs(name: str) -> bool:
            if name == wanted:
                return False
            if issue and issue in name:
                return True          # same issue, misnamed variant
            # A name carrying NO issue number cannot belong to another
            # numbered task, and this is the shape the agent reaches for when
            # it names a skill after the bug instead of the ticket —
            # `sympy-mignotte-bound-fix` was the real diagnosis for
            # sympy-19254 and would otherwise be stranded.
            return not re.search(r"\d", name)

        found = sorted(d.name for d in tasks.glob("*")
                       if d.is_dir() and belongs(d.name))
        if not found:
            return self.open_task_skill(instance, store_root, workdir,
                                        on_call=on_call)
        if on_call:
            on_call(f"[skill] this task's skill is filed as "
                    f"{', '.join(found)} — the lookup asks for `{wanted}`; "
                    f"re-filing it")

        # Re-filed by the HARNESS, not by an agent.
        #
        # Renaming a directory is not a judgement, and making it one made the
        # whole pipeline depend on a model staying up. Measured on
        # sympy-19254: research diagnosed the bug and wrote it as
        # `sympy-mignotte-bound-fix`, the re-file agent was asked to move it to
        # `sympy-sympy-19254`, and it died on API retries —
        # `exited rc=255 ... "api_retry","attempt":4` — leaving the trace to
        # report "still does not exist; the next run will start from scratch"
        # while the diagnosis sat on disk under a name no reader asks for.
        #
        # So the content is moved here, deterministically, and the agent is
        # not involved. `merge_skill_text` is the same reconciliation used when
        # promoting into the source tree, so two strays for one task combine
        # rather than the last one winning.
        moved = self._refile_task_skill(store_root, wanted, found, on_call=on_call)
        landed = moved or self.best_skill_for(store_root, topic) == wanted
        if not landed:
            if on_call:
                on_call(f"[skill] ** `{wanted}` still does not exist — the next "
                        f"run on this subject will start from scratch")
            return ""

        # Merged, so the copies GO.
        #
        # Guaranteeing the canonical name exists does nothing about the names
        # beside it: measured in one run, four tasks produced fifteen skills —
        # django alone had `django-django-13551` plus
        # `django-password-reset-token-fix`, `django-13551-email-hash-fix`,
        # `django-django-13551-reconciliation` and
        # `django-13551-reconciliation-summary`. Every one of those is
        # promoted into the source tree and kept for good, and a later
        # retrieval that matches one fragment gets that fragment instead of
        # the whole answer. Two skills for one subject split every read.
        #
        # Only after the merge landed, and only what this task wrote.
        for name in found:
            stray = tasks / name
            try:
                shutil.rmtree(stray)
                if on_call:
                    on_call(f"[skill] merged `{name}` into `{wanted}` and "
                            f"removed the copy")
            except OSError:
                continue
        return wanted

    def snapshot_tracker(self, instance: Dict[str, Any], store_root: Path,
                         workdir: Path, resolved: bool = False,
                         on_call=None) -> str:
        """Write this task's record into a skill, as the task ends.

        The tracker is per task and dies with it. This is the one moment its
        contents are allowed to cross that boundary, and they cross as a SKILL —
        named by the convention the pre-attempt lookup reads, so the next run
        on this subject finds it rather than starting again.
        """
        topic = self.research_topic(instance)
        tracker = Path(workdir) / self.TRACKER_FILE
        if not tracker.is_file():
            # No record is not a reason to leave nothing behind. A task that
            # passed on try 1 may never have needed a second phase, and one
            # that died early still knows its subject failed — both are worth
            # more to a later run than an absent skill, which is
            # indistinguishable from a subject nobody has ever tried.
            if on_call:
                on_call("[learn] no record to snapshot — writing the skill "
                        "from the attempt evidence instead")
        skill = self.task_skill_name(topic)
        if on_call:
            on_call(f"[learn] snapshotting the task record into `{skill}` "
                    f"({'solved' if resolved else 'not solved'})")
        prompt = self.SNAPSHOT_PROMPT.format(
            topic="{topic}", tracker=str(tracker), skill=skill,
            outcome="SOLVED" if resolved else "NOT SOLVED")
        evidence = [p for p in (tracker,
                                Path(workdir) / "attempt-1" / "attempt-notes.md",
                                Path(workdir) / "attempt-1" / "exchange.md")
                    if p.is_file()]
        self.standalone_stage(instance, store_root, workdir, prompt,
                              attachments=[str(p) for p in evidence],
                              timeout_s=self.RECORD_GUARD_S,
                              agent=self.filer_agent_name, phase="learn",
                              on_call=on_call)
        return skill

    @staticmethod
    def _skill_has_content(store_root: Path, skill: str) -> bool:
        """Does this skill say anything, or is it just the scaffold?

        Existence is not substance, and the difference is invisible from the
        outside: `skill_write` on a new subject creates the file with its
        headings, so a research pass that names the skill and writes no blocks
        leaves `## Instructions` and `## Rules` empty and every later check
        satisfied.

        Measured on pydata-xarray-3364: 220 bytes, zero blocks, created after
        try 1 and never filled. `best_skill_for` found it, the lookup reported
        `found ... — the attempt solves with it`, tries 2 and 3 both loaded it
        and `skill-use` recorded them as having worked from it. Try 3 was
        revising an empty file, and nothing in the run said so.
        """
        from phronix.skill_schema import parse_skill

        tasks = Path(store_root) / "capabilities" / "tasks"
        for path in tasks.glob(f"*/{skill}/SKILL.md"):
            try:
                found = parse_skill(path.parent)
            except Exception:
                continue
            # INSTRUCTIONS and RULES, not lessons.
            #
            # A lesson is "the last attempt failed"; an instruction is what to
            # do instead. Counting lessons satisfied this check with exactly
            # the former: pydata-xarray-3364 had an empty `SKILL.md` and a
            # `LESSONS.md` reading "Attempt to ignore missing variables ...
            # failed – agent produced no patch", and on that basis tries 2 and
            # 3 were handed a skill containing no fix at all.
            if found.get("blocks"):
                return True
        return False

    #: Most bytes of any one harness-supplied file a stage is handed.
    #:
    #: ~24 KB is roughly 6k tokens, so the whole attachment set stays well
    #: inside the headroom compaction leaves. The models here are trained to
    #: 131072 and the CLI compacts at 100k — its floor — which leaves ~31k for
    #: everything the turn adds. One large file read can exceed that on its
    #: own: measured on pytest-5495, the agent read `test_conftest.py, lines 1
    #: to 2001` and the request came back
    #: `400 ContextWindowExceededError`, killing the attempt outright.
    #:
    #: The harness cannot cap what the AGENT chooses to read, but it can stop
    #: contributing to the problem.
    ATTACH_BUDGET_B = int(_tuned("agent.attachment_budget_bytes", 24_000))

    def capped(self, path: Path) -> Path:
        """*path*, or a bounded copy of it beside it.

        `conversation.md` is every turn in full, appended and never rewritten —
        correct for a durable record and wrong to hand a model: it grows with
        the task and is largest exactly when the context is tightest. This
        keeps the record intact and gives the stage the head and the tail with
        the middle marked as elided.

        Head AND tail because both ends carry the information: the head says
        what the task is and what the first attempt tried, the tail says what
        just failed. Cutting either end loses more than cutting the middle.
        """
        try:
            raw = Path(path).read_bytes()
        except OSError:
            return Path(path)
        if len(raw) <= self.ATTACH_BUDGET_B:
            return Path(path)
        half = self.ATTACH_BUDGET_B // 2
        head, tail = raw[:half], raw[-half:]
        elided = len(raw) - len(head) - len(tail)
        note = (f"\n\n... {elided:,} bytes elided from the middle; the full "
                f"record is {Path(path).name} ...\n\n").encode()
        trimmed = Path(path).with_suffix(".capped.md")
        try:
            trimmed.write_bytes(head + note + tail)
        except OSError:
            return Path(path)
        return trimmed

    #: One re-ask, then report. A check that loops is a budget with no bound.
    CHECK_PROMPT = """\
What you just filed has problems. Fix them; do not research anything new.

{issues}

Each line says where the problem is and what to do about it. Apply the moves,
then stop. `layout_check` and `research_validate` will tell you if anything is
still wrong.
"""

    def _enforce_checks(self, instance: Dict[str, Any], store_root: Path,
                        workdir: Path, on_call=None) -> List[str]:
        """Run the layout and schema checks; re-ask once if either fails.

        Returns whatever is still wrong after the re-ask, so the trace can say
        so rather than the run reporting a solution nothing can read.
        """
        issues = self._check_findings(store_root)
        if not issues:
            return []
        if on_call:
            on_call(f"[research] ** {len(issues)} filing problem(s) — "
                    f"asking once for them to be fixed")
        listing = "\n".join(f"- {line}" for line in issues[:12])
        try:
            self.standalone_stage(
                instance, store_root, workdir,
                self.CHECK_PROMPT.format(issues=listing),
                timeout_s=self.RECORD_GUARD_S, agent=self.filer_agent_name,
                phase="research", on_call=on_call)
        except Exception as exc:
            if on_call:
                on_call(f"[research] ** could not ask for the fix: {exc}"[:180])
        left = self._check_findings(store_root)
        if left and on_call:
            on_call(f"[research] ** {len(left)} problem(s) remain: "
                    f"{left[0][:110]}")
        return left

    @staticmethod
    def _check_findings(store_root: Path) -> List[str]:
        """`layout_check` and `research_validate` against this run's store."""
        found: List[str] = []
        try:
            from phronix.mcp_tools.tools.layout_service import _issues_for

            for tree in ("capabilities", "research"):
                for issue in _issues_for(Path(store_root), tree):
                    found.append(f"{issue['path']}: {issue['problem']} "
                                 f"-> {issue['fix']}")
        except Exception:
            pass                      # a check that cannot run is not a fault
        try:
            import json as _json

            from phronix.mcp_tools.tools.schema_service import _check

            subjects = (Path(store_root) / "research" / "skills")
            for subject in sorted(subjects.glob("*/record.json")):
                record = _json.loads(subject.read_text(encoding="utf-8"))
                for issue in _check(record):
                    found.append(f"{subject.parent.name}/{issue['where']}: "
                                 f"{issue['problem']} -> {issue['fix']}")
        except Exception:
            pass
        return found

    def research_from_tracker(self, instance: Dict[str, Any], store_root: Path,
                              workdir: Path, attempt_index: int = 1,
                              on_call=None) -> Dict[str, Any]:
        """Diagnose the open failure and write the fix into the task's skill.

        The sequential pipeline's research: one pass, one subject — whatever the
        tracker has under `Open`. It does not plan, fan out, or generate
        candidates. It reads the record, works out the fix, and updates the
        skill the next attempt will load.

        Bounded, and the bound grows. A first pass gets five minutes because a
        diagnosis that needs longer has usually lost its subject; a pass that
        runs out reports where it got to and the next one is given more, which
        is a better trade than starting long and never learning whether long was
        needed.
        """
        topic = self.research_topic(instance)
        tracker = Path(workdir).parent / self.TRACKER_FILE
        # The record has to be CURRENT before it is read.
        #
        # The tracker folds on its own clock, so the events from the attempt
        # and the evaluation that just ran may still be queued. The reader
        # waits — bounded — rather than every writer paying for a fold it does
        # not need. If the wait runs out, this reads the record as it stands:
        # a slightly stale record is worth far more than a diagnosis that
        # never runs, which is what the old per-phase stage produced whenever
        # it hit its ceiling.
        task_dir = Path(workdir).parent
        state = self._tracker_state(task_dir)
        self._fold_events(instance, store_root, workdir, state, on_call=on_call)
        self.await_record(task_dir, on_call=on_call)

        # THE name the next attempt looks up: the task's own slug.
        #
        # One skill per task, named after the task — there is no second kind to
        # distinguish it from, so a `solution-` prefix only creates ways for
        # the writer and the reader to disagree. They did: research wrote
        # `solution-<topic>-solution` while `best_skill_for` looked up
        # `solution-<topic>`, and measured live, try 2 loaded the skill the
        # LEARN pass had left after try 1, re-applied the same change, and the
        # harness reported `try 2 re-applies the change from try 1 — the
        # diagnosis did not move`. The diagnosis had moved; it was filed where
        # no reader would look.
        skill = self.task_skill_name(topic)
        budget = int(self.RESEARCH_BUDGET_S
                     * (self.RESEARCH_BUDGET_MULTIPLE ** max(0, attempt_index - 2))
                     * tracked_budget_scale())
        if on_call:
            on_call(f"[research] diagnosing the open failure, {budget}s, "
                    f"writing into `{skill}`")
        report = Path(workdir) / f"research-{attempt_index}.md"
        prompt = self.TASK_RESEARCH_PROMPT.format(
            topic="{topic}", tracker=str(tracker), skill=skill, budget=budget,
            report=str(report))
        # The record AND the task's whole conversation.
        #
        # The record is the organised view — problem, approaches, what worked,
        # what did not — and it is what research reads first. The conversation
        # is the unabridged one, and it is attached so that a diagnosis can go
        # back to what was actually said rather than re-deriving it. Without
        # it, research repeats work the task has already done: the record is
        # organised by design rather than exhaustive in order, so the
        # conversation is where a diagnosis goes for the exact wording of
        # something the record has summarised.
        # The record, the conversation — AND the skill with its lessons.
        #
        # A revision pass is asked to fix a diagnosis that has already been
        # tried and failed, so what it most needs is what was tried. That
        # lived in two places it was never handed: the skill it is about to
        # rewrite, and the LESSONS.md beside it, which is where every earlier
        # attempt's failure was recorded. Measured on pydata-xarray-3364: the
        # one sentence describing what try 1 had attempted and why it failed
        # sat in `LESSONS.md`, unread, while research re-derived the problem
        # from the tracker and wrote a skill with no instructions in it.
        skill_files = [path for pattern in (f"*/{skill}/SKILL.md",
                                            f"*/{skill}/LESSONS.md")
                       for path in (Path(store_root) / "capabilities" /
                                    "tasks").glob(pattern)]
        # The unabridged conversation is NOT attached.
        #
        # It is reachable instead through `conversation_outline`,
        # `conversation_turn` and `conversation_search`, which return one turn
        # at a time. The record is largest exactly when the context is
        # tightest, and handing it over whole is what produced
        # `400 ContextWindowExceededError` mid-attempt. The summary still is
        # attached: it is bounded and it is the map.
        attachments = [str(self.capped(p)) for p in (
            tracker,
            Path(workdir).parent / "conversation-summary.md",
            *skill_files,
        ) if p.is_file()]
        started = time.time()
        # Runs as the FILER: it can read the code and the record, and its one
        # write is the skill. It cannot patch the repository, which is the
        # difference between "propose a fix for the next attempt to execute"
        # and "become the next attempt".
        stdout = self.standalone_stage(
            instance, store_root, workdir, prompt, attachments=attachments,
            timeout_s=budget, phase="research", agent=self.filer_agent_name,
            on_call=on_call)
        outcome = self.parse_events(stdout, AttemptOutcome())
        # The three lines, echoed once at the end so the pass can be read off
        # the trace even when its narration scrolled past.
        # Matched at the START of a line, and only when it reads as a report.
        #
        # `if marker in line` matched the agent QUOTING the instruction back:
        # measured live, the trace showed ``APPROACH: `, `ANSWER:`\n6. I have
        # 300`` — the format spec itself, parsed as a finding. A restatement of
        # what it was asked to do is not a report of what it did.
        found: Dict[str, str] = {}
        steps: List[str] = []
        for raw in self.assistant_text(stdout).splitlines():
            # `**PROBLEM:**` is the same report as `PROBLEM:` — markdown
            # emphasis is how a model writes a heading, and stripping only the
            # left side left every value starting `** `.
            line = raw.strip().lstrip("*-# ").strip()
            for key in ("PROBLEM", "APPROACH", "ANSWER"):
                if not line.startswith(f"{key}:") and not line.startswith(
                        f"{key}**:"):
                    continue
                value = line.split(":", 1)[1].strip().lstrip("*").strip()
                value = value.strip('"\'`,')
                # A value that names another marker, or is mostly punctuation,
                # is the spec being echoed rather than an answer.
                if not value or len(value) < 8:
                    continue
                if any(other + ":" in value
                       for other in ("PROBLEM", "APPROACH", "ANSWER")):
                    continue
                # PROBLEM and ANSWER are stated once; APPROACH is stated before
                # each thing tried, and the SEQUENCE is the audit. Keeping only
                # the first threw away exactly what shows a pass going in
                # circles — the same approach twice in different words.
                if key == "APPROACH":
                    steps.append(value[:200])
                elif key not in found:
                    found[key] = value[:200]
        if steps:
            found["APPROACH"] = steps[0]
        if on_call:
            if found.get("PROBLEM"):
                on_call(f"[research] PROBLEM: {found['PROBLEM']}")
            for n, step in enumerate(steps, 1):
                on_call(f"[research] APPROACH {n}/{len(steps)}: {step}")
            if found.get("ANSWER"):
                on_call(f"[research] ANSWER: {found['ANSWER']}")
            if not found and not steps:
                on_call("[research] ** reported no PROBLEM/APPROACH/ANSWER — "
                        "the pass cannot be audited from its trace")
            if not found:
                on_call("[research] ** reported no PROBLEM/APPROACH/ANSWER — "
                        "the pass cannot be audited from its trace")

        # Did the diagnosis actually get FILED?
        #
        # The pass is judged on its transcript — PROBLEM/APPROACH/ANSWER — and
        # nothing checked that the skill it was told to write exists. Measured
        # on matplotlib-26011: research read the record, the conversation and
        # the issue, reported `PROBLEM:`, called `skill_load` on a skill that
        # was not there yet, and stopped at 159s of its 300s having called no
        # writing tool at all. The trace said `research-2: no phronix tools
        # called`, and the next line said `no skill covers this task; solving
        # from scratch` — try 2 started over, with the diagnosis sitting in a
        # transcript nobody reads.
        #
        # `ensure_task_skill` does not cover this: it re-files a skill written
        # under the WRONG NAME, and there was no skill at all.
        #
        # Asked again ONCE, and only to file — not to diagnose again, which is
        # what the budget was already spent on.
        if not self._skill_has_content(store_root, skill):
            if on_call:
                on_call(f"[research] ** `{skill}` is empty — asking for the "
                        f"diagnosis to be filed into it")
            self.standalone_stage(
                instance, store_root, workdir,
                self.FILE_DIAGNOSIS_PROMPT.format(
                    topic="{topic}", skill=skill, report=str(report)),
                attachments=[str(report)] if report.is_file() else [],
                timeout_s=self.RECORD_GUARD_S, agent=self.filer_agent_name,
                phase="research", on_call=on_call)
            if on_call and not self._skill_has_content(store_root, skill):
                on_call(f"[research] ** `{skill}` is still empty — try "
                        f"{attempt_index + 1} will load it and learn nothing")

        # The two checks, RUN rather than requested.
        #
        # Both are wired into the research skill and were called zero times in
        # every run that has them: an instruction to self-check competes with
        # finishing, and finishing wins. The harness runs them instead, which
        # is deterministic and costs nothing when the work is already right —
        # the same post-hoc check plus one re-ask used for the empty skill
        # above, and for the same reason.
        self._enforce_checks(instance, store_root, workdir, on_call=on_call)

        return {
            "attempt": attempt_index,
            "kind": "tracked",
            "report": str(report),
            "problem": found.get("PROBLEM", ""),
            "approach": found.get("APPROACH", ""),
            "approaches": steps,
            "answer": found.get("ANSWER", ""),
            "stages": ["research"],
            "steps": outcome.steps,
            "tokens_total": outcome.tokens_total,
            "cost_usd": outcome.cost_usd,
            "stage_seconds_total": round(time.time() - started, 1),
            "skill": skill,
            "budget_s": budget,
        }

    def research(self, instance: Dict[str, Any], store_root: Path,
                 workdir: Path, attempt_index: int = 1,
                 notes: Optional[Path] = None, on_call=None,
                 trial=None) -> Dict[str, Any]:
        """Establish how the task should be approached. No-op without a researcher.

        ``trial`` is the runner's seam (see ``Runner.trial_runner``): a callable
        that puts one candidate in front of the task's own tests and reports
        back. Arms that do no research ignore it.
        """
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
    #: Which topic this THREAD is working on.
    #:
    #: A plain attribute here was shared by every task the arm was running:
    #: task A set it to its topic, task B overwrote it, and A's next store read
    #: resolved under B's. Measured live — `pallets__flask-4045` explored
    #: `note_parsing`, which is `pylint-dev__pylint-5859`'s idea, and its own
    #: ideas read back as zero.
    #:
    #: Tasks run concurrently in threads within one arm, so anything naming
    #: "the current task" has to be thread-local.
    _topic_binding = threading.local()

    @property
    def research_topic_binding(self) -> str:
        return getattr(self._topic_binding, "topic", "")

    @research_topic_binding.setter
    def research_topic_binding(self, value: str) -> None:
        self._topic_binding.topic = value
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

    @property
    def agent_host(self) -> str:
        """Compute node this THREAD's task runs its agents on.

        Thread-local: see `_TASK_LOCAL`. Empty means "right here".
        """
        return getattr(_TASK_LOCAL, "agent_host", "") or ""

    @agent_host.setter
    def agent_host(self, value: str) -> None:
        _TASK_LOCAL.agent_host = value or ""

    @property
    def pinned_for_env(self) -> str:
        """The pinned model alias for the task running on THIS thread.

        Claude Code takes its model from the environment rather than argv, so
        it has to be readable from the arm rather than passed. Thread-local for
        the same reason as `agent_host`.
        """
        return getattr(_TASK_LOCAL, "pinned_for_env", "") or ""

    @pinned_for_env.setter
    def pinned_for_env(self, value: str) -> None:
        _TASK_LOCAL.pinned_for_env = value or ""

    #: Files each previous attempt changed, set by the runner before an attempt
    #: so feedback can say which locations have already failed.
    attempt_history: List[Dict[str, Any]] = []

    #: Consecutive attempts that failed with the SAME signature, set by the
    #: runner. Two is the pivot threshold: the diagnosis stops asking what was
    #: missing and starts asking what was assumed.
    same_failure_count: int = 0

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
        else:
            # Capabilities get the same isolation research already had.
            #
            # Research is isolated at the storage layer — without reuse a read
            # sees this session's folder and nothing else — and capabilities
            # were not, so a from-scratch run started with every probe every
            # earlier run had written. That included tools that carry a task's
            # answer outright, and the run could call one without ever knowing
            # it had been handed anything.
            #
            # With this set the server serves core plus what this session
            # builds. Writing is unaffected: the run still authors tools, still
            # keeps them, and still learns from them — it just cannot see
            # another run's.
            env[capabilities_module.FRESH_ENV] = "1"
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

    # The task's conversation, on the base class.
    #
    # These lived on `PhronixOpenCodeArm` while the `generate` that
    # calls them lives on `OpenCodeArm` — so `ClaudeArm`, which
    # extends the latter, raised `AttributeError: 'ClaudeArm' object
    # has no attribute 'append_turn'` on every bare attempt and the
    # whole control arm reported `steps=0 tok=0/0`.
    @staticmethod
    def _narrative(stdout: str) -> str:
        """What the agent said, out of a stream-json transcript."""
        said = []
        for line in (stdout or "").splitlines():
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            for block in ((event.get("message") or {}).get("content") or []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text = (block.get("text") or "").strip()
                    if text:
                        said.append(text)
        return "\n\n".join(said)

    @classmethod
    def record_verdict(cls, task_dir: Path, phase: str,
                       verdict: Optional[Dict[str, Any]] = None,
                       patch: str = "", skill: str = "",
                       subject_dir: Optional[Path] = None) -> Path:
        """The evaluation's turn: what was changed and what the tests said."""
        return cls.append_turn(task_dir, phase, verdict=verdict, patch=patch,
                               skill=skill, subject_dir=subject_dir)

    #: How much of one turn's own detail the running summary keeps.
    #:
    #: Small on purpose. The summary is read by EVERY later call, so a turn
    #: that spends 2 KB here costs that on all fifteen of them; the full text
    #: stays in `conversation.md` for anything that needs it.
    TURN_SUMMARY_CHARS = int(_tuned("research.turn_summary_chars", 700))

    def subject_dir(self, workdir: Path) -> Optional[Path]:
        """Where the SUBJECT's conversation lives, or None if there is no store.

        Keyed on the subject so tasks that share one learn from each other. Two
        bugs in the same area are worked by different tasks, often in the same
        run, and each was starting with no idea what the other had established:
        the same file read twice, the same dead end taken twice, the same
        reproduction built twice.

        In the STORE rather than the run directory, for the same reason skills
        are: a conversation that dies with the task teaches only that task, and
        the store is what carries between runs.

        Two levels, because they answer different questions. The task's own
        conversation is what THIS task has tried — precise, and the thing that
        stops attempt three repeating attempt one. The subject's is what every
        task in this area has tried, which is what stops a second task
        rediscovering the first's dead end.

        The subject level lives in the STORE, for the same reason skills do: a
        conversation that dies with the task teaches only that task.
        """
        subject = getattr(self, "conversation_subject", "") or ""
        root = getattr(self, "conversation_root", None)
        if not (subject and root):
            return None
        out = Path(root) / "conversations" / _slug(subject)
        try:
            out.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        return out

    def conversation_dir(self, workdir: Path) -> Path:
        """The task's own conversation directory."""
        return Path(workdir).parent

    @classmethod
    def append_turn(cls, task_dir: Path, phase: str, asked: str = "",
                    said: str = "", verdict: Optional[Dict[str, Any]] = None,
                    patch: str = "", skill: str = "",
                    subject_dir: Optional[Path] = None) -> Path:
        """Add one call to the task's conversation, and re-write its summary.

        A task is not one exchange, it is a dozen: several attempts, an
        evaluation after each, research between them. Each was starting from
        the issue with no idea what the previous ones had established — so the
        third attempt could repeat the first's change, and did.

        Two files, because they are read by different things and at different
        sizes:

        * ``conversation.md`` — every turn in full, appended, never rewritten.
          The record.
        * ``conversation-summary.md`` — a few lines per turn, rewritten each
          time. This is what goes INTO the next call, so it has to stay small
          enough to attach to all of them.

        The summary is built here rather than by a model: it is the same three
        facts every time — what the turn was, what it changed, what happened —
        and a deterministic digest cannot decide to leave one out.
        """
        task_dir = Path(task_dir)
        task_dir.mkdir(parents=True, exist_ok=True)
        log = task_dir / "conversation.md"
        summary = task_dir / "conversation-summary.md"

        turn = len([l for l in (log.read_text(errors="replace").splitlines()
                                if log.is_file() else []) if l.startswith("## ")]) + 1

        full = [f"## Turn {turn}: {phase}", ""]
        if asked.strip():
            full += ["### asked", "", asked.strip()[:4000]]
        if said.strip():
            full += ["", "### said", "", said.strip()[:8000]]
        if patch.strip():
            full += ["", "### changed", "", "```diff", patch[:6000], "```"]
        if verdict:
            full += ["", "### judged", "",
                     f"resolved={verdict.get('resolved')} "
                     f"target={verdict.get('fail_to_pass_passed')}/"
                     f"{verdict.get('fail_to_pass_total')} "
                     f"regressions={len(verdict.get('regressions') or [])}"]
            detail = (verdict.get("failure_detail") or "").strip()
            if detail:
                full += ["", "```", detail[:4000], "```"]
        with log.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(full) + "\n\n")

        # The rolling digest: what a later call actually needs to not repeat
        # what happened.
        line = [f"**Turn {turn} — {phase}.**"]
        if patch.strip():
            touched = sorted({ln.split("/", 1)[-1].strip()
                              for ln in patch.splitlines()
                              if ln.startswith("+++ ") and "/dev/null" not in ln})
            line.append("changed " + (", ".join(touched[:4]) or "something"))
        elif said.strip():
            line.append("no change made")
        if verdict:
            line.append("judged NOT resolved" if not verdict.get("resolved")
                        else "judged RESOLVED")
            failing = verdict.get("fail_to_pass_failing") or []
            if failing:
                line.append("still failing: " + ", ".join(failing[:3]))
            detail = (verdict.get("failure_detail") or "").strip()
            if detail:
                line.append("because: " + " ".join(
                    detail.split())[:cls.TURN_SUMMARY_CHARS])
        block = " ".join(line)

        previous = (summary.read_text(errors="replace")
                    if summary.is_file() else "")
        head = ("# What has already been tried on this task\n\n"
                "Every attempt and evaluation so far, oldest first. Do not "
                "repeat a change that was already judged.\n")
        body = previous.split("\n\n", 1)[1] if "\n\n" in previous else ""
        body = "\n\n".join([b for b in [body.strip(), block] if b])
        if skill:
            body += (f"\n\nA solution skill exists for this task: `{skill}`. "
                     f"Read what it says it solved before following it.")
        summary.write_text(head + "\n" + body + "\n", encoding="utf-8")

        # And the same turn, linked into the SUBJECT's conversation.
        #
        # Two levels: this task's own record, and what every task in the area
        # has tried. A second bug in the same subsystem otherwise rediscovers
        # the first's dead ends — the same file read twice, the same
        # reproduction built twice, in the same run.
        #
        # The subject level keeps one line and a link, not the text: it is read
        # by tasks that are NOT this one, and what they need is "somebody tried
        # this here, and here is where to look", not the transcript.
        if subject_dir is not None:
            try:
                shared = Path(subject_dir) / "subject-conversation.md"
                first = not shared.is_file()
                with shared.open("a", encoding="utf-8") as handle:
                    if first:
                        handle.write(
                            "# What has been tried on this subject\n\n"
                            "One line per turn, across every task in this "
                            "area, oldest first. Follow the link for the "
                            "detail.\n\n")
                    handle.write(f"- {block}  \n  _{log}_\n")
            except OSError:
                pass
        return summary

    @staticmethod
    def write_exchange(workdir: Path, verdict: Optional[Dict[str, Any]] = None,
                       patch: str = "") -> Path:
        """Everything the attempt was asked, said and was judged on, in one file.

        The harness used to pick out the parts it thought research would need —
        a few verdict counts and the agent's narrative — and hand it those. That
        is a summary written by the component least able to judge what matters:
        it has no idea which half-sentence in the transcript is the clue.

        So the whole exchange is written down instead, and the plan stage
        summarises it. What the plan keeps is then the plan's own reading of the
        problem, which is what it goes on to work from, rather than a digest it
        inherited.

        Large by design and never attached to the exploring stages: one file,
        read once, by the stage whose whole job is to understand the problem.
        """
        parts = ["# The attempt that failed, in full", "",
                 "This is the complete exchange: what the agent was asked, what "
                 "it did, what it changed, and how that was judged. Summarise "
                 "it — do not quote it back."]

        # The verdict goes FIRST, before the transcript it explains.
        #
        # It used to sit at line 299 of a 403-line file, under the agent's whole
        # transcript and above eighty lines of `Destroying test database for
        # alias 'other'...`. The one fact the next pass needs — which target
        # test is still failing — was in the least-read position in the file.
        #
        # The consequence was not that research ignored the failure; it is that
        # research refined the wrong half of it. Measured on django-13551 at
        # 1 of 2: the pass recorded a single step, "Email included in token
        # hash", which is the half that ALREADY PASSES, and never touched
        # `test_token_with_different_secret`, which is the one that does not.
        if verdict:
            passed = verdict.get("fail_to_pass_passed")
            total = verdict.get("fail_to_pass_total")
            failing = verdict.get("fail_to_pass_failing") or []
            parts += ["", "## START HERE: what is still broken", ""]
            if failing:
                parts += [
                    f"The last attempt passed {passed} of {total} target "
                    f"test(s). **These are still failing, and they are what "
                    f"this pass is for:**", "",
                    "\n".join(f"- `{name}`" for name in failing[:20]), "",
                    "Plan against THESE, not against the issue text. The part "
                    "of the issue the last attempt already fixed is done — "
                    "re-deriving it costs a pass and changes no verdict. What "
                    "is left is whatever makes the tests above fail.",
                ]
            else:
                parts += [f"The last attempt passed {passed} of {total} target "
                          f"test(s) and left none of them failing by name; the "
                          f"failure is in the regressions or the run itself."]
            regressed = verdict.get("regressions") or []
            if regressed:
                parts += ["", f"It also BROKE {len(regressed)} test(s) that "
                          f"passed before:", "",
                          "\n".join(f"- `{name}`" for name in regressed[:10])]

        asked = workdir / "prompt.md"
        if asked.is_file():
            parts += ["", "## What the agent was asked", "",
                      asked.read_text(errors="replace").strip()]

        said = []
        transcript = workdir / "opencode.jsonl"
        if transcript.is_file():
            for line in transcript.read_text(errors="replace").splitlines():
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                for block in ((event.get("message") or {}).get("content") or []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = (block.get("text") or "").strip()
                        if text:
                            said.append(text)
        if said:
            parts += ["", "## What the agent said as it worked", "",
                      "\n\n".join(said)[:20000]]

        if patch.strip():
            parts += ["", "## What it actually changed", "",
                      "```diff", patch[:12000], "```"]
        else:
            parts += ["", "## What it actually changed", "",
                      "**Nothing.** The diff was empty."]

        if verdict:
            parts += ["", "## How it was judged", "",
                      f"Resolved: {'YES' if verdict.get('resolved') else 'NO'}",
                      f"Target tests: {verdict.get('fail_to_pass_passed')} of "
                      f"{verdict.get('fail_to_pass_total')}",
                      f"Regression tests: {verdict.get('pass_to_pass_passed')} "
                      f"of {verdict.get('pass_to_pass_total')}"]
            failing = verdict.get("fail_to_pass_failing") or []
            if failing:
                parts += ["", "Still failing:", "```",
                          "\n".join(failing[:20]), "```"]
            detail = _useful_test_output(verdict.get("failure_detail") or "")
            if detail:
                parts += ["", "### What the tests actually printed", "",
                          "```", detail[:20000], "```"]

        out = workdir / "exchange.md"
        out.write_text("\n\n".join(parts), encoding="utf-8")
        return out


    def _in_store(self, store_root: Path, call, *args, **kwargs):
        """Run a phronix call against the run's store, restoring the env after.

        The library resolves its layer from the environment, and the harness is a
        long-lived process serving two arms concurrently — leaving
        ``PHRONIX_PROJECT_ROOT`` set would let one arm's bookkeeping land in the
        other's store, which is the one corruption no downstream check would
        catch.
        """
        # One thread at a time in here.
        #
        # `os.environ` is process-global; save-and-restore does not make it
        # thread-safe, it only makes the corruption harder to see. Two tasks
        # interleaving leaves one reading under the other's topic, and the
        # restore then writes back whichever value it happened to capture.
        #
        # These calls are short store reads and writes, so serialising them
        # costs little next to the agent turns around them.
        with _STORE_ENV_LOCK:
            return self._in_store_locked(store_root, call, *args, **kwargs)

    def _in_store_locked(self, store_root: Path, call, *args, **kwargs):
        previous_root = os.environ.get("PHRONIX_PROJECT_ROOT")
        previous_topic = os.environ.get("PHRONIX_RESEARCH_TOPIC")
        previous_session = os.environ.get("PHRONIX_RESEARCH_SESSION")
        previous_reuse = os.environ.get("PHRONIX_RESEARCH_REUSE")
        previous_fresh = os.environ.get("PHRONIX_FRESH_CAPABILITIES")
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
            # The harness's OWN reads obey `--fresh` too.
            #
            # The agents get this through `isolated_env`; these in-process
            # calls did not, so `recalled_skill` searched with the filter off
            # and offered the attempt a bundled answer that the harness's own
            # `search-skill` had just correctly refused to return.
            if getattr(self, "fresh", False):
                os.environ["PHRONIX_FRESH_CAPABILITIES"] = "1"
            else:
                os.environ.pop("PHRONIX_FRESH_CAPABILITIES", None)
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
                               ("PHRONIX_RESEARCH_REUSE", previous_reuse),
                               ("PHRONIX_FRESH_CAPABILITIES", previous_fresh)):
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
        env.update(model_env(base_url=self.base_url, api_key=self.api_key))
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

    #: A real binary, not the `npx` wrapper, when one has been installed.
    #:
    #: `~/.local/bin/opencode` is one line: `npx --yes opencode-ai@latest "$@"`.
    #: That resolves and extracts the package on every invocation, into a cache
    #: the private HOMEs all symlink — so concurrent agents race on one
    #: `~/.npm/_npx` directory, and one of them execs a half-written binary.
    #:
    #: Measured: every attempt in a six-task run returned rc=126 ("cannot
    #: execute") in three seconds with zero steps, and was recorded as "agent
    #: produced no patch" — a startup race reported as a model that did nothing.
    #: The same command run alone returns 0.
    #:
    #: Set PHRONIX_OPENCODE_BIN to an installed binary to take npx out of the
    #: hot path entirely.
    DEFAULT_OPENCODE_BIN = os.environ.get("PHRONIX_OPENCODE_BIN") or "opencode"

    #: Which harness's config directory this arm needs linked into a checkout.
    harness_name = "opencode"

    def __init__(self, *args: Any, opencode_bin: str = "", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.opencode_bin = opencode_bin or self.DEFAULT_OPENCODE_BIN

    def attachments(self, paths: List[Path]) -> List[str]:
        """How this harness is handed supporting files."""
        return [f"--file={path}" for path in paths]

    def stage_agents(self, checkout: Path) -> int:
        """Make this harness's agents visible from the task's checkout.

        Delegates to `phronix.agents.link_harness`, which is the harness setup
        step: it symlinks the project's harness directory, idempotently, so
        anything added to it later — a new agent, a skill, an MCP declaration —
        arrives without this code knowing about it.

        Here rather than once per run because a checkout is created per attempt,
        and the link has to exist in each of them.
        """
        try:
            from phronix.agents import link_harness

            return 1 if link_harness(checkout, self.harness_name)["linked"] else 0
        except Exception:
            # The default agent is how this behaved before the link existed.
            return 0

    def agent_command(self, prompt: str, checkout: Path, files: List[str],
                      agent: str = "", model: str = "") -> List[str]:
        """The argv that runs one agent session over *checkout*.

        A seam, so a second harness is a command and a parser rather than a
        second copy of the attempt loop: everything around this — the checkout,
        the patch extraction, evaluation, research, the ledger — is
        harness-agnostic and stays shared.

        *model* overrides which model answers. That is what lets one stage be
        asked of several models at once: the fleet serves them behind one
        endpoint, so the only thing that varies is this argument.
        """
        # The agent definition has to be where opencode will look, and it looks
        # in the directory it was pointed at.
        if agent:
            self.stage_agents(checkout)
        chosen = f"{self.provider}/{model}" if model else self.qualified_model
        command = [self.opencode_bin, "run", prompt,
                   "--dir", str(checkout), "--auto",
                   "--format", "json", "--model", chosen,
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
                 on_call=None, plan: Optional[Dict[str, str]] = None
                 ) -> AttemptOutcome:
        """One attempt. *plan* pins it to a specific researched approach.

        Without a plan the agent chooses; with one it implements the candidate
        it was handed. That is what makes parallel trials a comparison of
        APPROACHES rather than N samples of the same prompt.
        """
        import subprocess

        if container is None:
            return AttemptOutcome(error="opencode arms need a work container")

        checkout = self.prepare_checkout(container, store_root, workdir)

        self.research_topic_binding = self.research_topic(instance)
        env = (isolated_env(store_root, workdir / "cache", fresh=self.fresh)
               if self.uses_phronix else without_harness_venv(dict(os.environ)))
        env = self.phronix_env(tool_path_env(env))
        env.update(model_env(base_url=self.base_url, api_key=self.api_key))
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
            # What previous sessions BUILT, before what they wrote down.
            #
            # Reuse is not only skills: a run that solved this area authored
            # deterministic tools for it, and under a carried store those tools
            # are already registered on the server this agent is talking to.
            # Nothing used to point at them, so a task whose fix existed as a
            # callable tool re-derived it from prose.
            prompt += PHRONIX_REUSE_SUFFIX
            topic = self.research_topic(instance)
            # Name the skill outright. Asking the agent to find it costs a search
            # and, when the search is ambiguous, a wrong answer — and the harness
            # already knows the answer, because research pinned it in the record.
            from phronix import research as research_module

            skill = self.best_skill_for(store_root, topic)
            # Verify it is THIS task's skill before naming it as such.
            #
            # `topic_skill` falls back to fuzzy resolution, and two issues in
            # one repository resolve to each other: measured, both
            # `pylint-dev__pylint-5859` (fixme notes) and
            # `pylint-dev__pylint-7080` (recursive ignore-paths) returned
            # `normalize-ignore-paths`. The prompt then states "this task has
            # been researched already, and the result is a single skill" —
            # naming another bug's pipeline with full authority. The planner
            # believed it and put up `ignore_type_behavior` and
            # `ignore_recursion` for a punctuation-regex bug.
            #
            # Wrong-and-confident is worse than absent: an empty answer costs
            # a fresh start, this costs a whole plan round the corrector then
            # has to undo.
            # Offered, not withheld — and never asserted to be the answer.
            #
            # This used to drop a skill that did not belong to this topic,
            # because naming another bug's pipeline as "the result" of this
            # task sent the planner after the wrong problem. The prompt no
            # longer asserts that: it says a skill MAY cover the task, tells
            # the agent to read what the skill says it solved, and to use it as
            # knowledge when it turns out to be a different problem in the same
            # area.
            #
            # That is worth more than dropping it. A skill for a neighbouring
            # bug still knows where the behaviour lives, what the tests assert,
            # and which directions were refuted — and the only reader who can
            # see both problems is the agent.
            if skill and not self._skill_is_for(store_root, skill, topic):
                if on_call:
                    on_call(f"[recall] `{skill}` was written for another "
                            f"problem in this area — offered as knowledge, "
                            f"not as the plan")
            # Then look wider, because a remembered solution is worth more than
            # a fresh start and the topic key is narrower than memory is.
            #
            # `topic_skill` matches only THIS task's topic, so a second task on
            # a repository we have already researched found nothing and began
            # from zero — the store held a pipeline for exactly its subject and
            # nothing asked for it. The search is by subject, which is what a
            # later task actually shares with an earlier one.
            if not skill:
                skill = self.recalled_skill(store_root, instance)
                if skill and on_call:
                    on_call(f"[recall] trying remembered skill `{skill}` "
                            f"before solving from scratch")
            prompt += (PHRONIX_PLAN_SUFFIX
                       .replace("{topic}", topic)
                       .replace("{repro}", f"{RESEARCH_SCRATCH}/repro")
                       .replace("{skill}", skill or "(none written yet)"))
        # Everything already tried on this task, so a later attempt does not
        # repeat an earlier one's change. Attached to EVERY attempt, including
        # the first, where it simply does not exist yet.
        context = [issue_file, brief_file]
        history = self.conversation_dir(workdir) / "conversation-summary.md"
        if history.is_file():
            context.append(history)
        # And what every task in this area has tried, which this task has not.
        shared_dir = self.subject_dir(workdir)
        if shared_dir is not None:
            shared = shared_dir / "subject-conversation.md"
            if shared.is_file():
                context.append(shared)
        files = self.attachments(context)
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
                # The task's OWN record travels with it.
                #
                # Not the harness's raw judgement — that is the baseline's
                # channel, and injecting it here would hand phronix the answer
                # through the prompt and then credit its memory for it. The
                # tracker is phronix's own product: what it worked out about
                # this task, organised as the problem, how it has been
                # approached, what worked and what did not.
                #
                # Passed rather than retrieved because it is THIS task's
                # memory, not the library. A retry that has to go and find its
                # own last attempt spends its opening turns rediscovering what
                # it did an hour ago, and the record exists precisely so the
                # next stage starts from what the last one established.
                tracker = workdir.parent / self.TRACKER_FILE
                if tracker.is_file():
                    files += self.attachments([tracker])
                    prompt += self.TRACKER_NOTE
            else:
                prompt = TASK_PROMPT + RETRY_SUFFIX
                files += self.attachments([feedback])

        # What has already been RULED OUT, across runs.
        #
        # `feedback.md` says what the last try got wrong, and it dies with the
        # run. `LESSONS.md` is where a failed approach is written down so it is
        # not paid for twice, and it was attached to RESEARCH and to nothing
        # else — so the attempt, which is the thing that would retry a dead
        # approach, never saw it. Measured: a reuse run whose carried skill
        # named the exact fix still spent 44 steps rediscovering the problem,
        # with the pitfalls from the earlier run sitting unread beside it.
        #
        # Attached whenever the skill has one, on every try including the
        # first: trying something new each time and recording what worked and
        # what did not is the point, and it does not start at try 2.
        lessons = self._lessons_for(store_root, getattr(self, "recalled_skill", "")
                                    or (plan or {}).get("skill", ""))
        if lessons is not None:
            files += self.attachments([lessons])
            prompt += self.LESSONS_NOTE

        if plan:
            prompt += self.PLAN_NOTE.format(name=plan.get("name", "?"),
                                            summary=plan.get("summary", ""))
            # Only when research actually wrote one. Naming a skill that does
            # not exist sends the racer looking for its plan instead of
            # implementing the summary it was given.
            if plan.get("skill"):
                prompt += self.PLAN_SKILL_NOTE.format(skill=plan["skill"])

        # Ask for this task's pinned backend, so the conversation stays with the
        # server that already holds its history.
        pinned = self.model_for_task(instance)

        command = self.agent_command(LOG_NOTE + prompt, checkout, files,
                                     self.agent_name, pinned)

        started = time.time()
        if on_call is not None:
            # Same reasoning as the research pass: a thirty-minute attempt that
            # reports nothing until it exits is indistinguishable from a hung
            # one, and the interesting part — which files it opened, which tests
            # it ran — is exactly what the event stream carries. stream_opencode
            # enforces the timeout itself and keeps partial output.
            launch: Dict[str, Any] = {}
            stdout, code = stream_opencode(command, checkout, env,
                                           self.timeout_s, on_call,
                                           stats=launch, host=self.agent_host)
            # The agent's own error output, which this branch used to discard.
            #
            # `stream_opencode` drains stderr into `stats`; hardcoding "" here
            # threw it away, so an agent that exited in 1.1 seconds with rc=1
            # was recorded as `stderr: ""` and reported as "produced no patch".
            # The message that would have named the cause was captured and then
            # dropped one frame later.
            stderr = str(launch.get("stderr") or "")
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
        # The prompt, kept beside the transcript.
        #
        # The transcript records what the agent DID; without the prompt nobody
        # can see what it was asked, which skill it was pointed at, or what the
        # retry told it. Research then reasons about a failed attempt with half
        # the exchange missing, and the harness has to guess which parts
        # mattered and hand-summarise those.
        (workdir / "prompt.md").write_text(prompt, encoding="utf-8")
        # Only the arms that have memory keep a conversation.
        #
        # The bare arm is the control: it carries nothing between attempts by
        # design, and handing it a record of what it already tried would give
        # it the one capability the comparison exists to measure. It happened
        # to write none of these anyway, through which class overrides
        # `generate` — an accident, not a guarantee, so it is now a condition.
        if self.uses_phronix:
            self.append_turn(self.conversation_dir(workdir),
                             f"attempt {workdir.name}",
                             asked=prompt, said=self._narrative(stdout),
                             subject_dir=self.subject_dir(workdir))
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

    #: The pointer, not the method. The method is `phronix-learn-from-attempt`.
    LEARN_PROMPT = """\
The attempt on `{topic}` just finished. Record what it taught this system. Do
not edit any source.

`skill_load("phronix-learn-from-attempt")` is your first action and that skill
is the method; this message is only the input.

Your evidence is attached: `attempt-diff.patch` is exactly what changed,
`attempt-notes.md` is how it was judged, and `exchange.md` is the whole
exchange including **what the tests actually printed**. The assertion and the
traceback are where the reason lives — "it did not pass" is a verdict, "it did
not fire for the path the test uses" is a lesson.

**If the attempt PASSED, write the solution skill, and it has a NAME:**

    skill_write(name="{solution}", ...)

That exact name — a later run looks it up rather than searching, and the skill
covers why the form that worked beat the obvious one.

Memory is THIS session; a skill is what survives it — `I9` has the test.

**A PARTIAL pass is evidence too** — record the half the tests confirmed as
established, not only the half that failed. If the attempt achieved nothing,
record what failed: the implementation, not the idea.
""" + OBSERVE_NOTE

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

    #: The report footer both survey halves share.
    OBSERVE_FOOTER = """\
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

    #: Survey, half one: what the library already knows.
    #:
    #: Every one of these is a query against our own store, so it needs neither
    #: the checkout nor the issue text — which is what makes it separable from
    #: the half below and safe to run at the same time.
    SURVEY_PRIOR_PROMPT = """\
Find out what is ALREADY known about this task. Do not edit anything, do not
read the repository, and do not propose a fix.

Topic key: `{topic}`

1. `research_prior(question=...)` — describe this task in your own words and
   see what is on record: skills covering it, earlier research, which
   approaches were tried, which worked, which were refuted, which aspects are
   settled. Research carries across runs, so this is often not empty.
2. `graph_query` for the same subject. The graph indexes every layer's skills
   and research, so it reaches related subjects that share no vocabulary with
   your question — exactly the ones you would otherwise rediscover.
3. `research_assess(task=...)` — if the library already covers this, say so.
4. `research_backups(topic="{topic}")` and `research_ruled_out(topic="{topic}")`
   — what earlier rounds of THIS topic found and what they disproved.

Report which parts of the problem are already answered and which are genuinely
open. Another agent is reading the issue and the code at the same time; your job
is only the library. Anything you list as open will be investigated at full
price, so be precise about the split.
""" + OBSERVE_FOOTER

    #: Survey, half two: what the task actually is.
    #:
    #: Reads the issue and the checkout. Knows nothing about our store, which is
    #: the other half's job.
    SURVEY_ISSUE_PROMPT = """\
Work out what this task IS. Do not edit anything and do not propose a fix yet.

Topic key: `{topic}`

1. Read the issue, and state the behaviour in your own words: what happens, what
   should happen, and under what conditions.
2. Find where it plausibly lives in this checkout — the module, the function,
   the test that would cover it. Read, do not change.
3. Look the problem up outside this checkout: the project's issue tracker,
   whether it was fixed upstream, the shape of that fix.

Report what the task is and where it lives. Another agent is checking what the
library already knows at the same time; do not duplicate that — establish the
question, do not answer it.
""" + OBSERVE_FOOTER

    #: Closing a gap the harness FOUND, so it names it exactly.
    COMPLETE_PLAN_PROMPT = """\
The plan for `{topic}` is missing things the stages after it need:

{gaps}

Add exactly those, in full. Do not revisit the ideas — they have been judged
and are settled — and do not re-plan anything that is already recorded.

**The corpus is a count, and the count is checked.** A corpus of four when
eight are asked for fails the same check that sent you here, and the stage
after you measures against whatever you leave. Add instances until the number
is met, in one `research_add_instances` call if you can — enumerating eight
cases is quicker than explaining why four is enough.

`skill_load("phronix-research-plan")` is the method for what a good metric and
a good corpus look like: the metric must state how it is obtained, and the
corpus must vary along the axes you declare, including the cases that should
NOT match.

**Do not fix the bug.** No edits, no patches, no `apply_patch`. This stage
declares how a fix will be MEASURED; the fixing happens later, in a worktree,
by a stage that is judged on it. Measured: this stage spent twenty minutes
applying patches to `blueprints.py` and split the dataset three times — the
work it was asked for was the small part of what it did, and every edit was
reverted afterwards because research may not change the code.

Enumerating cases is quicker than fixing anything: a corpus instance is an
input and an expected outcome, not a working patch.

Everything downstream reads what you write here — with no metric and no
instances, the solution is built from opinion.
"""

    #: Asking for MORE ideas, not for the list again.
    #:
    #: A retry that re-plans from scratch throws away the good ideas the
    #: validator just kept and re-derives them at full cost — and often
    #: produces the same weak ones again, because nothing told it which they
    #: were. This carries the kept ideas, the count still needed, and the
    #: validator's own report of what it rejected and why.
    PLAN_MORE_PROMPT = """\
You already have {kept_n} idea(s) for `{topic}`, judged good and KEPT:

{kept}

Propose {needed} more that those do not already cover. Keep the ones above
exactly as they are — call `research_set_aspects` with them AND your new ones.

The point is a DIFFERENT angle, not another wording of the same one. The list
above is deliberately one line each: it is there so you can tell what is
already covered, not to be elaborated on.

`skill_load("phronix-research-plan")` — the section on finding an idea the
existing ones do not cover names the axes worth moving along when the obvious
ideas are taken.{stuck}

Why more are needed, from the last round's judgement:

{report}

Do not re-propose anything rejected there for the reason given.
"""

    #: Exploring one idea AGAIN, told exactly what was missing.
    EXPLORE_MORE_PROMPT = """\
Explore the idea **{name}** for `{topic}` again. It was explored once and came
back incomplete.

What is missing, from the check on the last pass:

{gap}

Close that gap specifically. What the last pass established is already recorded
— do not redo it, and do not start over. `skill_load("phronix-explore-idea")` is
the method.

You have {budget} seconds — more than the first pass had, because this one has a
narrower question. Your worktree is `{workspace}`; write your finding to
`{dump}`.
""" + OBSERVE_NOTE

    #: How many times the exploring may be sent back for more.
    #:
    #: Two: one round, a check, and at most one more. A third would cost
    #: another full phase to close gaps the validator has already judged small
    #: enough to name, and the build stage is required to work from partial
    #: evidence and mark what is unverified.
    MAX_EXPLORE_ROUNDS = _tuned("research.max_explore_rounds", 2)

    #: The pointer, not the method. The method is `phronix-validate-ideas`.
    VALIDATE_IDEAS_PROMPT = """\
Judge the ideas recorded for `{topic}`: which are actually worth exploring?

`skill_load("phronix-validate-ideas")` is your first action and that skill is
the method; this message is only the input. It covers what makes an idea worth
two minutes, what to do with a bad one, and why you must not pad the list to
reach a number.

Write the surviving ideas back with `research_set_aspects`, in priority order —
that list IS what gets explored. Then say how many good ideas remain.

You have no time limit. Do not explore and do not solve: you are judging the
questions, not answering them.
"""

    #: The pointer, not the method. The method is
    #: `phronix-validate-exploration`.
    VALIDATE_EXPLORE_PROMPT = """\
Judge what the exploring found for `{topic}`: did each idea answer its question?

`skill_load("phronix-validate-exploration")` is your first action and that skill
is the method; this message is only the input. It covers when a finding is
complete, why a negative result is complete, and how to name a gap so the next
pass is not a repeat of the last.

For any idea that needs another pass, call
`research_notice(kind="thin", what="<idea name>", detail="<what is missing>")`.
Name only what would change the solution — every pass costs the clock the
budgets exist to bound.

You have no time limit. Do not fill the gaps yourself: that is exploring, it is
budgeted, and doing it here hides the cost in a stage that reports none.

Do not write patches, diffs or code. You have no editing tools and a patch
written as text is output nobody applies — if you are reaching for one, the
finding is already complete enough to build from.
"""

    #: One idea judged, while the others are still being explored.
    #:
    #: The whole-plan version made every finished idea wait for the slowest,
    #: and then made the ones with nothing missing wait again while the thin
    #: one was re-explored. Judging a list is bounded by the list, and a list
    #: of one is the smallest useful unit — so this runs the moment its own
    #: idea reports, and its own second pass starts immediately after.
    VALIDATE_ONE_EXPLORATION_PROMPT = """\
Judge ONE idea's exploration for `{topic}`: did it answer its question?

`skill_load("phronix-validate-exploration")` is your first action and that skill
is the method; this message is only the input. It covers when a finding is
complete, why a negative result is complete, and how to name a gap so the next
pass is not a repeat of the last.

Idea: **{name}**

The question it was asked to answer:

{question}

Judge this idea and no other. The others are still being explored and are not
yours to assess — a verdict on an idea whose findings are half-written is the
one verdict that cannot be right.

If it needs another pass, call
`research_notice(kind="thin", what="{name}", detail="<what is missing>")` with
the name spelled exactly as above; that string is what routes the gap back to
this idea's next pass, and a gap filed under a name nobody recognises is a pass
nobody gets. Name only what would change the solution — the next pass costs the
clock the budgets exist to bound.

If it answered its question, including by answering NO, say so and notice
nothing. A negative result is complete.

You have no time limit. Do not fill the gap yourself: that is exploring, it is
budgeted, and doing it here hides the cost in a stage that reports none. Do not
write patches, diffs or code — you have no editing tools, and a patch written as
text is output nobody applies.
"""

    #: The pointer, not the method. The method is `phronix-explore-idea`.
    EXPLORE_PROMPT = """\
Explore ONE idea for `{topic}`, and report what you find.

`skill_load("phronix-explore-idea")` is your first action and that skill is the
method; this message is only the input. It covers trying the idea rather than
describing it, reaching for a `probe_` tool before deriving anything by hand,
and what a finding has to contain — including when the idea did not work, which
is a result and not a wasted stage.

Step: **{name}**
Question: {question}
{where}

This is ONE STEP of a method, not the whole fix. The skill's `I0` says what that
means for what you record and why more than one way is worth having.

You have {budget} seconds and a worktree of your own at `{workspace}`; nothing
you do there reaches the patch. Write your finding to `{dump}` as well as
recording it.

Other agents are working the other steps right now. Do not build the whole
solution — the stage that assembles the steps sees every finding, and yours
alone cannot tell how they compose.
""" + OBSERVE_NOTE

    #: Asked when a task is solved and left no skill the next run can find.
    SOLUTION_SKILL_FROM_PASS_PROMPT = """\
This task is SOLVED. The change that solved it is attached as
`attempt-diff.patch`, and `exchange.md` holds what the tests printed.

Write it down as a skill the next run can execute:

    skill_write(name="{solution}", ...)

That exact name. A later run does not search for the solution — it looks this
name up before the attempt starts, and a skill filed anywhere else is invisible
to it however good it is.

What belongs in it:

* the change that worked, precisely enough to apply — the file, the function,
  and what the line became;
* WHY that form and not the obvious one. If an earlier attempt failed first,
  the difference between the two is the most valuable thing you can write:
  "use `get_email_field_name()` rather than `user.email`, because a custom user
  model has no `email` attribute and the naive form raises `TypeError: must be
  str, not NoneType`" is worth more than any description of the bug;
* what the tests checked, so the next run knows when it is done.

Do not describe the issue. The next run has the issue; what it does not have is
the answer. You cannot edit or run anything here — the task is already solved,
and the only thing left is to file what solved it.
"""

    #: The remaining failure, injected into every stage that plans against it.
    #:
    #: `exchange.md` carries the verdict, and an attachment is not the same as
    #: an instruction: a stage told to "summarise the problem from exchange.md"
    #: summarised the ISSUE, planned a step for the half that already passed,
    #: and never opened the section naming the test that did not. Putting the
    #: failing tests in the prompt makes them the subject rather than something
    #: the agent has to go and find.
    STILL_FAILING_NOTE = """
**What the last attempt already got RIGHT, confirmed by the tests:**

{working}

Those are established. A step that re-derives them costs this pass and changes
no verdict, and a solution that abandons them regresses a target test the run
has already banked.

**What is still broken, from the same test run:**

{failing}

The last attempt passed {passed} of {total} target test(s). Decompose against
the failing tests: what has to become true for THOSE to pass, on top of what
already works.
"""

    #: What the working tree actually contains on a retry, said out loud.
    #:
    #: The checkout handed to a revision pass still holds the edits of the
    #: attempt that just FAILED. Nothing said so, and the consequence is not
    #: subtle: measured on django-13551 under Haiku, `plan` read `tokens.py`,
    #: found the fix already present, concluded "the implementation is complete
    #: and correct", and recorded no steps at all. Its re-ask read the same
    #: file and reached the same conclusion. Two full stages spent confirming a
    #: patch that had scored 1/2 and lost the task.
    #:
    #: The agent was not being lazy. It was handed a workspace that argues
    #: there is nothing to do, and believed it.
    PATCHED_TREE_NOTE = """
**The working tree is NOT the original code.** It holds the edits made by the
attempt that just failed, so the fix will often look as though it is already
there — because it is, and it did not work.

Source that reads correctly is NOT evidence on a retry. The evidence is in
`exchange.md`: which target tests still failed, and what they printed. An
attempt that scores 1 of 2 leaves code that looks finished and is not.

If you find yourself concluding that the implementation is complete, you have
read the tree instead of the verdict. Go back to `exchange.md`, find the test
that is still failing, and plan from THAT.
"""

    #: The pointer, not the method. The method is `phronix-research-plan`.
    PLAN_PROMPT = """\
Write the research plan for `{topic}`. Do not edit anything and do not fix
anything.

`skill_load("phronix-research-plan")` is your first action and that skill is the
method; this message is only the input.

**On a retry, your first real step is to summarise the problem from
`exchange.md`** — the full record of the attempt that failed: what it was
asked, what it said, what it changed, what the tests printed. Everything you
plan afterwards depends on that reading, so make it before the metric, the
corpus or any idea.
""" + PATCHED_TREE_NOTE + """

The skill covers what to record and in what order — `research_define_fom`, then `research_declare_corpus` with
`research_add_instances` and `research_split`, then `research_set_aspects` — and
why each one is worthless without the others.

Topic key: `{topic}`

Three ideas is the floor, not the target — the skill's `R3` says why, and why
scouts are appending theirs to your plan while you work.
""" + OBSERVE_NOTE

    #: Where the scouts look, so the ideas differ by ANGLE and not by phrasing.
    #:
    #: Unassigned parallel searchers produce several versions of the first
    #: reading — the same failure, the same file, the same sentence reworded.
    #: Naming the place each one looks is what makes the third idea worth as
    #: much as the first.
    PLAN_ANGLES = [
        {"name": "upstream-history",
         "look": "the project's own history and issue tracker: has this been "
                 "fixed, attempted or discussed upstream, and what did that "
                 "change touch? A fix somebody already wrote is the cheapest "
                 "idea available and the one nobody proposes."},
        {"name": "producer-side",
         "look": "the code path that PRODUCES the value that ends up wrong — "
                 "where it is built, defaulted or normalised. The failing "
                 "assertion is where it surfaced, which is usually not where it "
                 "was decided."},
        {"name": "assumption-check",
         "look": "what every obvious reading of this failure assumes, and "
                 "whether that assumption holds. State the assumption, then the "
                 "idea that follows from it being false — a test that never "
                 "runs, a branch that never fires, a config that is not the one "
                 "in effect."},
    ]

    #: A scout adds ideas. It does not write the metric or the corpus.
    PLAN_SCOUT_PROMPT = """\
Find ideas worth exploring for `{topic}`. Do not edit anything, do not fix
anything, and do not write the metric or the corpus — another agent is doing
that right now and you would be overwriting its work.

`skill_load("phronix-research-plan")` is the method for what makes an idea worth
a slot; this message is only where to look.

**Look here, and not where the obvious reading looks:**

{angle}

Read the failure in `exchange.md` first — what was asked, what was changed, what
the tests printed — then go to your angle and come back with what you find.

Record what you find with `research_add_aspects`, which APPENDS: several agents
are writing to this plan at once and `research_set_aspects` would erase theirs.
Each idea is a `{{name, question, where}}` — the question is what exploring it
would answer, phrased so a negative answer is as useful as a positive one.

**The tool call is the only thing that records an idea.** Writing JSON to a
file, echoing it, or listing your ideas in your reply does not record anything:
the next stage reads the research record and nothing else. A scout that
investigates well and then files its ideas anywhere but the tool has produced
nothing, and the exploration phase it was feeding is skipped in silence. The
scratch space below is for your own notes, never for the ideas themselves.
""" + PATCHED_TREE_NOTE + """

Ideas that repeat one already recorded are dropped and named back to you. That
is not a rejection of the count, it is a request for a different axis: propose
as many distinct ideas as your angle supports.

Scratch space: `{workspace}`
""" + OBSERVE_NOTE
    #: One agent, one IDEA, refined into the sequence of steps that carries it out.
    #:
    #: An idea is a way of solving the WHOLE problem, and it is not executable
    #: until someone has said what it actually does — in order, in named
    #: places. That refinement is what the solution is written from and what
    #: the trial then puts in front of the tests, so it happens per idea and in
    #: parallel: one idea being refined does not wait on another.
    #:
    #: This replaced a per-STEP fan-out. That shape asked several agents for
    #: rival ways of doing one step of one method, which is a finer grain than
    #: anything downstream could use: the thing built, tried and combined is an
    #: idea, not a step of one.
    REFINE_IDEA_PROMPT = """\
You own one idea for `{topic}`, and your job is to make it executable.

**The idea:** {step}

What it has to establish: {question}

Where it applies: {where}

The other ideas, which are NOT yours — do not work on them, do not propose
variations of them, and do not re-open whether yours is the right one: {others}

Work out the SEQUENCE OF STEPS your idea takes to solve the problem, then
record it:

    research_add_approach(
        name="<the idea, named after what it does>",
        summary="<step 1, step 2, step 3 — what changes, where, in order>",
        hypothesis="<what you believe is true, and what would show it false>",
        aspect="{step}")

`aspect` must be your idea's name exactly as written above, so the result of
trying it can be attributed to the idea that produced it.

Three to six steps. Fewer means a step is really several; more means you are
writing the patch rather than the method. Each step names WHERE it happens —
the file and the function — because a step nobody can locate cannot be carried
out or checked.

The hypothesis is what makes the idea refutable. "Including the email in the
hash invalidates the token; false if a user model without an `email` attribute
raises instead" is worth more than a restatement of the idea.

Read the code before you commit to the steps. An idea that turns out to be
impossible costs a trial to discover, and you can rule it out here for nothing
— recording that as the hypothesis of the idea you keep.

Scratch space: `{workspace}`
""" + PATCHED_TREE_NOTE + OBSERVE_NOTE

    #: Sent to a planning stage that finished having recorded nothing.
    #:
    #: The failure it corrects is not laziness and not a refusal — the agent
    #: does the work and then files it in the wrong place. Measured on
    #: django-13551 under Haiku: two scouts ran `ToolSearch` for
    #: `research_add_aspects`, then used Bash to "create JSON with research
    #: aspects to explore" and "format research aspects as JSON for adding to
    #: plan". The ideas existed, in a file nobody reads, and the record stayed
    #: empty while the trace showed the stage completing normally.
    #:
    #: So the re-ask assumes the thinking is DONE and asks only for the call.
    RECORD_ASPECTS_PROMPT = """\
You finished without recording anything, so nothing you found exists yet.

`research_add_aspects` is the ONLY thing that records an idea. Writing JSON to a
file, printing it, or describing it in your reply does not — the next stage
reads the research record and nothing else, so ideas that never went through the
tool are simply lost, and the pipeline continues as though you had found none.

Do not investigate anything further. You already did the work; this is the
filing. Take what you just found — including anything you wrote to a file — and
call `research_add_aspects` with it now.

Each idea is `{{name, question, where}}`:

* `name`  — what must become TRUE for the problem to be solved, not how you
            would make it true. `A1: use getattr` is a way; `the token hash
            includes the user's current email` is a step.
* `question` — what exploring it would answer, phrased so a negative answer is
            as useful as a positive one.
* `where` — the file and function. Every idea needs a DIFFERENT one: two ideas
            carried out in the same place are one idea with two ways of doing
            it, and the tool will reject the list.

If you genuinely found nothing worth exploring, call it with the one idea you
would try next. An empty record is the one outcome that helps nobody.
""" + PATCHED_TREE_NOTE + """
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

    #: Appended to the diagnosis when the failure has stopped moving.
    #:
    #: A pointer, not a method: `phronix-diagnosis-pivot` holds what to do, so
    #: the learner can improve it and the graph can find it. The ordinary
    #: diagnose prompt asks what was missing, which assumes the last attempt was
    #: close — the assumption two identical failures are evidence against.
    PIVOT_NOTE = """\

## Two attempts have now failed in exactly the same way

Same tests, same reason, same text missing. Stop and
`skill_load("phronix-diagnosis-pivot")` before going further: it is the method
for a failure that has stopped moving, and refining this change again will
produce the same failure a third time.
"""
    BUILD_SOLUTION_PROMPT = """\
Build the solution for `{topic}` out of what the explored ideas found.

`skill_load("phronix-build-solution")` is your first action and that skill is
the method; this message is only the input. It covers what the output is (a
skill holding a PIPELINE of steps, not an essay), that every deterministic step
must be built as an MCP tool with `capability_new` and only judgement left as
prose, and how to attach the result so a later task retrieves it.

You have no time limit. Do not explore: the findings are your input, and if they
are thin, build what they support and say what is unverified.
"""

    #: Stages that must be allowed to finish.
    #:
    #: The flow has two kinds of stage. The parallel ones — aspect, evaluate —
    #: explore: three run at once, and one cut short costs that branch and
    #: nothing else. The sequential ones are connective tissue. `plan` decides
    #: what the parallel investigation will even look at; `collect` is where
    #: three investigations become one account; `propose` turns that account
    #: into candidates; `solution-skill` writes the skill that is the entire
    #: durable output of the pass.
    #:
    #: Truncating one of those does not lose a branch, it loses the flow. A
    #: `collect` cut off half way discards what three investigators spent 700
    #: seconds finding, and `propose` then works from a partial summary — so the
    #: expensive stages were paid for and their findings thrown away. That is
    #: the worst outcome available, and it was happening at 60s budgets.
    #: Stages that must run to completion: they FILE what earlier stages
    #: established rather than exploring. Cutting one throws away everything
    #: upstream of it, because the budget was spent to produce its output.
    #: These get `MUST_FINISH_GUARD_S` as a hang-guard and ignore the deadline.
    MUST_FINISH_STAGES = ("plan", "build-solution")

    #: Stages exempt from the pipeline clock entirely.
    #:
    #: Narrower than MUST_FINISH_STAGES, which is a reporting category. `plan`
    #: files aspects and is must-finish, but it also THINKS — it works out what
    #: the task is — and giving it a 900s guard would spend the whole pass on
    #: its first stage. What belongs here is the write-up: no exploration left
    #: to bound, and every earlier stage's budget was spent to produce it.
    #: Stages with no clock at all: the correctors, and the build.
    #:
    #: Every one of them reads what an earlier stage produced and writes a
    #: judgement or a write-up. None can run away — there is nothing to explore
    #: into — and cutting one costs the budgeted stage that fed it.
    UNTIMED_STAGES = ("build-solution", "validate-ideas",
                      "validate-exploration", "complete-plan")

    #: The hang-guard for the write-up. Reaching it means wedged, not slow.
    MUST_FINISH_GUARD_S = int(_tuned("research.must_finish_guard_s", 900))

    #: The hang-guard for RECORDING a task's record and its skill.
    #:
    #: Recording is not exploring. `track`, `ensure_task_skill` and
    #: `snapshot_tracker` all read what already happened and write it down;
    #: none of them can run away, because there is nothing to run away into.
    #: Cutting one throws away the attempt, evaluation and research that were
    #: paid for to produce its input.
    #:
    #: They ran on `FINALIZE_BUDGET_S` (150s), which is a WORK budget, and hit
    #: it:
    #:
    #:     track>  KILLED at the 150s hard ceiling after 150s
    #:     track>  exited rc=-9: d":"0be2fb67-6a4c-46ea-b8bd-4a1907...
    #:     track>  the record is missing ## The problem, ## How it ...
    #:
    #: — killed mid-write, leaving a truncated record, which then failed the
    #: shape check and cost a second full pass to re-ask. The budget did not
    #: save time; it spent it twice and lost the record in between.
    #:
    #: A guard rather than no timeout at all: a wedged agent must still end.
    RECORD_GUARD_S = int(_tuned("research.record_guard_s", 900))

    @property
    def record_guard_s(self) -> int:
        """`RECORD_GUARD_S`, stretched for slow hardware and then capped.

        A property rather than a constant because the right number depends on
        the fleet, which is not known at import: on corona the same fold that
        fits in 900s against a 1000 tok/s model needs several times that at
        13.5 tok/s, and on a hosted endpoint it needs less.
        """
        return int(min(RECORD_GUARD_MAX_S,
                       self.RECORD_GUARD_S * tracked_budget_scale()))

    #: A much shorter guard for the correctors.
    #:
    #: They have no file tools and their input is a list someone else wrote, so
    #: a judgement should cost a couple of minutes. Measured: `validate-ideas`
    #: ran the full 900s and was killed — denied files, it wandered through
    #: `skill list`, `memory recall`, three `skill load`s and a probe instead.
    #:
    #: The guard is not a work budget; it is the point at which "judging" has
    #: clearly become "investigating by other means". Fifteen minutes of that
    #: costs more than the exploring it was checking.
    CORRECTOR_GUARD_S = int(_tuned("research.corrector_guard_s", 180))

    #: Per-stage budgets in seconds.
    #:
    #: The connective stages get room to finish. Their ceilings are hang-guards,
    #: not work budgets — a stage reaching one means something is wrong, and
    #: status.sh reports it as a defect rather than as normal truncation.
    #: The exploratory stages keep real budgets: they are where an agent will
    #: happily read the whole repository, and cutting one short is survivable.
    #: Aspects a plan must produce before the investigation is worth running.
    #: Below this the fan-out has nothing to spread across and the phase
    #: degenerates into one agent repeating the survey.
    #: Three ideas, and the plan stage does not finish with fewer.
    #:
    #: Two was the old floor, from when the phase was "as many angles as we can
    #: afford" and a thin plan was survivable. The pipeline now explores exactly
    #: what the plan records, so a plan with two ideas is a pipeline that
    #: explores two — measured live: `2 idea(s) at once`, with the third idea
    #: simply never asked for. The solution is built from the ideas, so a
    #: missing idea is a direction the solution never considers.
    MIN_ASPECTS = _tuned("research.min_aspects", 3)

    #: How many times to ask again before salvaging or falling back. Each retry
    #: is a full agent invocation, so this trades tokens for the investigation
    #: phase existing at all — which is worth several retries.
    #: How many times to ask again for a plan that records too few ideas.
    #:
    #: Generous, because each retry gets the FULL plan budget rather than a
    #: slice: asking again is the cheapest corrector there is, and the stage
    #: after it can only explore what this one wrote down. Falling back to
    #: generic angles is the last resort, not the second one.
    MAX_PLAN_RETRIES = _tuned("research.max_plan_retries", 5)

    #: How many times the validator may be asked within one plan phase.
    #:
    #: It has no budget of its own — judging a list is bounded by the list, so
    #: a clock there could only cut the cheap half of the loop. That reasoning
    #: holds per call and not in aggregate: measured on django-13551,
    #: `validate-ideas` was invoked 83 times on a single task.
    MAX_JUDGEMENTS = int(_tuned("research.max_judgements", 8))

    #: Ideas to ask for per round, whatever the shortfall is.
    #:
    #: Three. The validator rejects filler, so an ask for exactly the missing
    #: one is lost entirely to a single rejection; an ask for three survives
    #: two rejections and still closes the gap.
    PLAN_OVERASK = _tuned("research.plan_overask", 3)

    #: Rounds without a new idea before the plan is accepted as it stands.
    #:
    #: Three tries and then go with what there is. Measured: `2 good idea(s)
    #: kept, asking for 1 more` four times running — the planner proposes a
    #: third, the validator rejects it as filler, and the loop asks again at an
    #: escalating budget. Neither side is misbehaving; there simply is no good
    #: third idea for that task.
    #:
    #: Exploring two real ideas beats spending three more rounds to obtain a
    #: third that would be padding.
    MAX_PLAN_STALLS = _tuned("research.max_plan_stalls", 3)
    DEFAULT_ASPECTS = [
        {"name": "reproduce",
         "question": "Reproduce the reported failure exactly, and record the "
                     "smallest command that shows it."},
        {"name": "locate",
         "question": "Find the code that produces the reported behaviour, and "
                     "the test that covers it."},
        {"name": "minimal-change",
         "question": "Establish the smallest change that could make the "
                     "reported behaviour correct, and what it would break."},
    ]

    #: Seconds per stage, in the shape the pipeline was redesigned to have.
    #:
    #: The pass is five stages now, and each is a phase of one argument:
    #:
    #:   plan            2 min   work out what the task is, and name the angles
    #:   aspect          4 min   investigate every angle, all at once
    #:   propose          ~0     turn findings into named approaches
    #:   tune            2 min   measure the approaches against the corpus
    #:   solution-skill  untimed  build the solution from what measured best
    #:
    #: `survey` is gone: it asked what the store knows and what the issue says,
    #: and the planner must read the issue anyway and holds the same retrieval
    #: tools, so the stage bought a barrier and an extra prefill to produce a
    #: summary the planner then read instead of the source.
    #:
    #: `collect`, `propose` and `evaluate` are reconciliation, not
    #: investigation — they read what the stage before them recorded and write
    #: one record. They get the floor, which is what "one second" means once a
    #: model has to emit a tool call to say anything at all.
    STAGE_BUDGETS = {
        # Five minutes to work out what the task is and put up three ideas.
        "plan": 300,
        # Two minutes per idea, and the three run at once — so the phase costs
        # two minutes, not six. Plan plus explore is the seven minutes the
        # pipeline gets before it starts building.
        "explore": 120,
        # `build-solution` is deliberately absent: it has no time limit. It
        # writes up what the exploring found, and cutting it wastes every
        # minute spent producing its input. See UNTIMED_STAGES.
    }


    #: Seconds allowed for a stage to file what it found after being stopped.
    #:
    #: Bounded by the skill, not by the clock.
    #:
    #: This was 45s, on the reasoning that filing is cheap. Filing is cheap;
    #: READING is not. A finalize pass must take in the whole transcript of the
    #: stage it is rescuing before it can write anything, and that is prefill
    #: of a context the stage spent minutes building. Measured: every finalize
    #: reported `KILLED at the 45s hard ceiling`, so the mechanism that exists
    #: to stop a stopped stage losing its findings was losing them itself.
    #:
    #: What keeps this bounded is the skill: `phronix-stage-finalize` forbids
    #: reading files, running commands and searching, so a finalize cannot go
    #: exploring however long its ceiling is. The ceiling only has to be longer
    #: than "read what is already in front of you and write it down".
    #: What a finalize is EXPECTED to cost, used to reserve room before the
    #: deadline. Not a cap: see the `finalizing` branch in `stage`.
    FINALIZE_BUDGET_S = int(_tuned("research.finalize_budget_s", 150))

    #: The pointer, not the method. The method is the skill.
    FINALIZE_PROMPT = """\
The `{stage}` stage of research on {topic} has stopped. Its work is in the
transcript above.

Produce its result from what was done. Everything that stage established is
already in front of you — record it, so the next stage receives a complete
handoff rather than a partial one.

You are not continuing the stage. Do not read files, run commands or search:
nothing you could look up now belongs in this record, and the stage's findings
are complete as they stand. Take your time over the writing; there is no clock
on this.

If the stage established nothing, say so in one line and record nothing. An
invented finding is worse than an absent one — the next stage cannot tell it
from a real one, and will spend its budget pursuing it.

The method is the `phronix-stage-finalize` skill: it says which record each
phase owes and how to mark a partial measurement as partial.
""" + PATCHED_TREE_NOTE

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
    #: The corrector's agent. Withholds Read, Grep, Bash and the editors.
    #:
    #: "Do not explore, you are judging the questions" was in the skill and was
    #: ignored — the validator was observed reading `issue.md` and
    #: `task-brief.md` in full. A rule an agent can break is one it will break
    #: under time pressure, and this stage is unbudgeted, so the cost lands
    #: where nothing reports it. Withholding the tools makes it structural.
    validator_agent_name = "phronix-validator"
    #: Runs every stage rescue, and every "you recorded nothing" re-ask.
    filer_agent_name = "phronix-filer"

    #: How many surviving ideas are explored at once.
    #:
    #: Three was the number the plan stage was asked for, so the floor and the
    #: ceiling were the same number and a fourth good idea had nowhere to go.
    #: The planner and its scouts now look for as many distinct ideas as the
    #: failure supports, and each one that survives validation is explored,
    #: written up and tried against the real tests — so this is a concurrency
    #: bound, not a target. The launcher lowers it when several tasks share a
    #: node, which is the only reason to keep it small.
    max_parallel_aspects = int(os.environ.get("PHRONIX_BENCH_ASPECTS") or 5)

    #: Approaches tuned and evaluated at once.
    #:
    #: Same argument as the aspects above, and the same measurement behind it:
    #: tune and evaluate are fused per approach, so the phase costs its slowest
    #: candidate whether there are three or six. Three was chosen when the
    #: fleet was one server; with 32 backends and 28 of them idle, the cap was
    #: throwing away the parallelism the cluster exists to provide.
    max_parallel_evaluations = int(
        os.environ.get("PHRONIX_BENCH_EVALUATIONS") or 6)

    #: The headings the record must have, in this order.
    #:
    #: Known strings, so the shape is checkable rather than merely requested.
    #: Every other layer of this pipeline learned the same lesson today: a rule
    #: stated in a skill and checked nowhere is a rule the model follows when
    #: it happens to. Measured on the first live record: it wrote `## Problem
    #: Statement`, `## Attempts`, `### Attempt 1`, `## Key Notes` — good
    #: content, and organised by WHEN things happened rather than by what they
    #: mean, which is the transcript shape the record exists to replace.
    TRACKER_SECTIONS = ("## The problem", "## How it has been approached",
                        "## What worked", "## What did not work")

    FILE_DIAGNOSIS_PROMPT = """\
You diagnosed this task and did not write the diagnosis down. Write it now.

Task: `{topic}`
The skill to write: `{skill}`

    skill_write(name="{skill}", ...)

That exact name. The next attempt looks it up by that name and by nothing else,
so a diagnosis filed anywhere is a diagnosis nobody reads.

What you found is in `{report}` and in what you already said. Do not diagnose
again, do not read the source again, do not attempt the task: take what is
there and file it.

If the diagnosis is incomplete, write what you have. A partial fix the next
attempt can build on is worth more than a complete one it never sees.
"""

    RESHAPE_PROMPT = """\
The record at `{tracker}` is written, and it is not in the shape the next phase
reads. Rewrite it — same content, correct headings.

It must have these four, spelled exactly, in this order:

{sections}

Missing now: {missing}

Keep every fact that is already there; this is a reorganisation, not a rewrite
from evidence. Put each existing item under the heading it belongs to:

* what is being solved, as it now stands -> **The problem**
* one line per attempt or pass, what it tried -> **How it has been approached**
* anything confirmed, with what confirmed it -> **What worked**
* anything tried that failed, with WHY -> **What did not work**
* everything else worth a line -> **Notes**

A per-attempt heading like `### Attempt 1` is the shape to remove: it organises
by when things happened, and the next phase needs them organised by what they
mean.
"""

    #: Told to a retry that is handed the task's record.
    TRACKER_NOTE = """

`tracker.md` is attached: this task's own record, kept across attempts. It has
the problem as it now stands, how it has been approached, what worked and what
did not.

Read it before you touch anything. What is under **What worked** is banked —
keep it working. What is under **What did not work** has been tried, and the
reason it failed is there; repeating it costs an attempt and changes nothing.
"""

    #: Where one task's running record lives. Per task, never shared.
    TRACKER_FILE = "tracker.md"

    #: Keeps the record. Can read and write ONE file; no Bash, Edit or Agent.
    tracker_agent_name = "phronix-tracker"

    #: Seconds the research pass gets on its first try, and the multiple each
    #: later try earns.
    #:
    #: Short on purpose. A diagnosis that needs an hour has usually lost its
    #: subject, and the loop is sequential — every minute here is a minute the
    #: next attempt is not running. A pass that runs out says where it got to
    #: and the next one is given longer, which is a better trade than starting
    #: long and never learning whether long was needed.
    RESEARCH_BUDGET_S = int(_tuned("research.task_research_seconds", 300))
    RESEARCH_BUDGET_MULTIPLE = float(
        _tuned("research.task_research_multiple", 1.5))

    TRACK_PROMPT = """\
Fold what just happened into this task's record.

`skill_load("phronix-task-tracker")` is your first action and that skill is the
method; this message is only the input.

Task: `{topic}`
Phase that just ran: **{phase}** ({cost})
The record: `{tracker}` — create it if it is not there yet.

Note what this phase COST under **How it has been approached**, beside what it
tried: a stage that took twelve minutes to reach the same place as one that
took two is a fact about the approach, and only the record can hold it.

Everything else you need is attached. Rewrite the whole record, reorganised
so nothing is lost and everything is where the next phase will look. Do
not attempt the task, do not fix anything, do not research.
"""

    TASK_RESEARCH_PROMPT = """\
This task attempted and did not fully succeed. Diagnose the open failure and
write the fix into the task's solution skill.

`skill_load("phronix-task-research")` is your first action and that skill is the
method; this message is only the input.

Task: `{topic}`

Attached, and all input rather than description: the record `{tracker}`, a
conversation summary, and `{skill}` with its `LESSONS.md`. Read the record and
the lessons first — `I7`. The full conversation is retrieved a turn at a
time — `I8`.

Write BOTH: `skill_write` with the corrected fix, and `skill_write_lesson`
with what just failed and the tests it BROKE.

You have {budget}s. `I5` says what to do if that is not enough.

Say what you are doing as you do it — `PROBLEM:` first, `APPROACH:` before
each thing you try, `ANSWER:` last — and write the same three into `{report}`.
`I6` says why the trace needs them.
"""

    def research(self, instance: Dict[str, Any], store_root: Path,
                 workdir: Path, attempt_index: int = 1,
                 notes: Optional[Path] = None, on_call=None,
                 trial=None) -> Dict[str, Any]:
        """Run the research flow, returning what it cost and what it concluded.

        Plan (three ideas, recorded), explore (every idea at once), then one
        solution skill per candidate, written in parallel.

        There is no collect and no propose. Both existed to hand the next stage
        a summary of records the store already held, and both were barriers: N
        investigations stopped so one agent could read them and write down what
        they said. What replaced them is that each idea files its own finding
        and each candidate is written up on its own, so the pass ends with as
        many executable plans as it had ideas.

        Ranking them is not this pass's job either. The attempt races the
        candidates against the task's own tests, which is a judge no proxy
        metric can stand in for, and `reconcile_trials` builds the subject's
        skill from what actually passed.

        A retry re-enters at *plan*, which reads the failure first: the record
        carries the previous round's approaches and its ruled-out locations, so
        planning again produces different ideas rather than the same ones at
        full price.
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
            isolated_env(store_root, workdir / "cache", fresh=self.fresh)))
        env.update(model_env(base_url=self.base_url, api_key=self.api_key))
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

        # The planner gets the EVIDENCE, not the repository.
        #
        # A revision pass runs against a checkout holding the failed attempt's
        # edits, and the planner reads them as proof there is nothing to plan.
        # Measured across five runs and five successive gates — a prompt
        # instruction, a restricted agent, a dedicated filer with no editing
        # tools, an explicit re-ask, and a standing note saying the tree is
        # patched — it still answered "the implementation is correct" and
        # recorded no ideas: 67 plan rounds on one task, 68 re-asks, zero
        # ideas.
        #
        # Every one of those gates argued with the conclusion. None removed
        # what produces it. The planner does not need the source to name the
        # ideas worth exploring — it needs the failure, the verdict and the
        # test that is still red, all of which are files — so it is given a
        # directory containing exactly those and nothing else.
        evidence = workdir / "evidence"
        evidence.mkdir(parents=True, exist_ok=True)
        for source in context_paths:
            try:
                shutil.copy2(source, evidence / Path(source).name)
            except OSError:
                pass

        started = time.time()
        transcripts: List[str] = []
        last_output: Dict[str, str] = {}
        answered_by: Dict[str, str] = {}
        stages: List[str] = []
        stage_detail: List[Dict[str, Any]] = []
        code = 0

        def stage(name: str, prompt: str, budget: int,
                  attachments: Optional[List[str]] = None,
                  workdir_override: Optional[Path] = None,
                  model: str = "", finalizing: bool = False,
                  agent: str = "") -> None:
            # `finalizing` stops the rescue rescuing itself: a finalize pass
            # that overran would otherwise spawn its own, forever.
            # A stage that WRITES UP what has been collected is not on a
            # clock at all.
            #
            # The deadline exists to stop exploration running away — an agent
            # will read the whole repository if you let it. The last phase does
            # no exploring: the corpus is measured, the trials are recorded,
            # the ranking is arithmetic that already happened, and its whole
            # job is to turn that into the solution skill. Cutting it is the
            # one cut that wastes everything upstream of it, because the ten
            # minutes were spent to produce exactly this output.
            #
            # So must-finish stages get a hang-guard instead of a budget: large
            # enough that reaching it means something is wedged rather than
            # slow, and exempt from both the deadline and the skip.
            # No overall cap: each stage is bounded by its OWN budget and
            # nothing else.
            #
            # A whole-pass deadline was tried and removed. It made the stage
            # budgets advisory, because every stage got the smaller of its
            # share and whatever the earlier ones had left — so an overrun in
            # `plan` was paid for by whatever came last. Measured: `propose`,
            # deliberately widened to 60s, ran with 10s and was stopped
            # part-way through recording its approaches. The stage that
            # overspends should be the stage that is cut.
            head = name.split(":", 1)[0]
            if head in self.UNTIMED_STAGES:
                # The write-up gets the long guard; the correctors get a short
                # one, because a corrector that runs for fifteen minutes has
                # stopped judging and started investigating.
                budget = max(budget, self.MUST_FINISH_GUARD_S
                             if head == "build-solution"
                             else self.CORRECTOR_GUARD_S)
            elif not finalizing:
                pass                      # its own budget, exactly as given
            else:
                # A finalize has no work budget at all — only a hang-guard.
                #
                # It runs past the deadline on purpose: refusing it would throw
                # away the very findings the deadline exists to protect. And it
                # must not be CUT either, which is the mistake this replaces —
                # every finalize reported `KILLED at the 45s hard ceiling`, so
                # the rescue was losing what it was rescuing, and each stopped
                # stage handed the next one a partial record or none.
                #
                # Its job is a clean handoff: take everything the stage did and
                # pass it on. That is not a thing to interrupt halfway.
                #
                # What bounds it is `phronix-stage-finalize`, which forbids
                # reading files, running commands and searching. A pass that
                # cannot look anything up cannot run away; it can only write up
                # what is already in front of it. So there is no ceiling — a
                # guard here would only ever fire mid-handoff, which is the one
                # outcome worse than a slow one.
                budget = 0
            nonlocal code
            label = f"{name}@{model}" if model else name
            narrate = ((lambda text: on_call(f"[{label}] {text}"))
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
            # and solution-skill loading one mean different things: the first is
            # orientation, the second is the plan actually being built out of it.
            stage_env["PHRONIX_STAGE"] = str(name)

            # The topic, from THIS pass's closure — never from a thread-local.
            #
            # `research.TOPIC_ENV` binds every research call to one record
            # "whatever string the caller passed", which is what stops agents
            # filing under the descriptive names they invent. It has to be set
            # for every stage, and the fanout stages run in pool threads.
            #
            # Reading it from `self.research_topic_binding` looked right and was
            # not: that is thread-local, a pool worker inherits nothing, so the
            # explore agents ran UNBOUND and their invented keys were resolved
            # fuzzily into whatever record matched. Measured: sympy-24066's
            # `exp-dimension-fix` filed under `pallets__flask-5063`, and
            # sympy-24066 left with zero ideas.
            #
            # `topic` is a plain local of the enclosing `research` call, so it
            # is correct in every thread that closure reaches.
            stage_env["PHRONIX_RESEARCH_TOPIC"] = topic

            stats: Dict[str, Any] = {}
            stage_started = time.time()
            # On a retry every stage opens with the checkpoint, so no stage
            # rebuilds a picture the last attempt already paid for.
            resume = ""
            if attempt_index > 1:
                pinned = self.best_skill_for(store_root, topic)
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
                    LOG_NOTE + TOOLS_NOTE + SKILL_NOTE + SCRATCH_NOTE
                    + resume
                    + prompt.replace("{topic}", topic),
                    where,
                    full_context if attachments is None else attachments,
                    agent or self.research_agent_name, model),
                where, stage_env, budget, narrate, root=where, stats=stats,
                host=self.agent_host)
            if rc != 0:
                code = rc
            transcripts.append(out)
            # Keep the last output per stage, so a stage that was supposed to
            # RECORD something and did not can still be salvaged from what it
            # said. An agent that narrates its plan in prose has done the
            # thinking; only the filing is missing.
            last_output[name] = out
            if model:
                answered_by[name] = model
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

            # A stopped stage still owes the next one its input.
            #
            # Before this, a stage that ran out of time simply vanished: the
            # thinking happened, nothing was filed, and the stage after it read
            # an empty record and behaved as though nothing had been found.
            # That is what made budgets unusable — the only safe budget was one
            # nothing could exceed, so a `tune` stage was given 600s and then
            # 4800s of hard ceiling, and a six-task arm spent fifty minutes
            # without reaching a single attempt.
            #
            # The finalize pass is short, forbidden from investigating, and
            # writes only what the transcript already established. It is what
            # makes a tight budget safe: overrunning now costs one filing pass
            # instead of the pipeline.
            # A CORRECTOR's overrun does not earn a rescue.
            #
            # A budgeted stage that runs out has findings worth filing, and
            # that is what the rescue is for. `validate-ideas` produces a
            # verdict, not findings — it judges a list someone else wrote, and
            # a truncated verdict is simply the next round's job. Rescuing it
            # doubled the most-invoked stage in the pass: measured on
            # django-13551, 300 validator calls and 303 finalizes, an hour in
            # the plan phase with fifteen budget events in the whole of it.
            corrector = name.startswith(("validate-ideas", "validate-exploration"))
            if stats.get("truncated") and not finalizing and not corrector:
                if on_call:
                    on_call(f"[{name}] out of time at {budget}s — filing what "
                            f"it found, then moving on")
                try:
                    # The rescue runs as the FILER, whatever the stage was.
                    #
                    # Its prompt has always said "you are not continuing the
                    # stage; do not read files, run commands or search", and
                    # asking has never been enough. Measured on django-13551:
                    # a ways-scout rescue ran `git diff`, announced "the fix is
                    # complete and correct", verified the tests and recorded no
                    # approach at all — confirming the very patch that had
                    # scored 1/2 and lost the task.
                    #
                    # The filer cannot edit, run or delegate, so the only
                    # actions left are the ones this stage is for. Inheriting
                    # the stage's own agent was the previous fix and was not
                    # enough: most stages run unrestricted, so most rescues did
                    # too.
                    #
                    # It did not, and the consequence undid the reason some
                    # stages have restricted agents at all. `validate-ideas`
                    # runs as the validator, which has no Bash and no Edit
                    # precisely so that judging cannot quietly become
                    # investigating — and then its finalize was spawned with
                    # the default agent and every tool back. Measured on
                    # scikit-learn-25570: `validate-ideas-finalize` spent its
                    # rescue reading source and applying a fix to
                    # `_update_fitted_transformers`. A pass that exists to FILE
                    # what was found had become the one doing the work, with
                    # none of the restrictions the stage was given.
                    stage(f"{name}-finalize",
                          self.FINALIZE_PROMPT.format(stage=name,
                                                      topic="{topic}"),
                          self.FINALIZE_BUDGET_S,
                          attachments=attachments,
                          workdir_override=workdir_override,
                          model=model, finalizing=True,
                          agent=self.filer_agent_name)
                except Exception as exc:      # a rescue must not break the run
                    if on_call:
                        on_call(f"[{name}] could not finalise: {exc}")

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

        # -- the pipeline --
        #
        # Scaled for the model actually serving this run.
        #
        # The numbers below were measured against a model that decodes around
        # 1000 tok/s. Nemotron on the local fleet does ~150, so every stage runs
        # roughly six times longer for the same work — and every survey stage in
        # a six-task run was killed at its 180s budget having done maybe a third
        # of the investigation. Research then proceeded on partial findings and
        # the arm was measured as though it had researched properly.
        #
        # A multiplier rather than new constants: the RELATIVE sizes encode real
        # measurements about which stages are expensive, and those hold whatever
        # the model is. Only the clock rate changes.
        # A wall-clock target for the whole pipeline, not a per-stage guess.
        #
        # "Research should take five minutes" is the thing anyone actually
        # wants to say, and it is not expressible as nine separate numbers
        # without redoing the arithmetic every time one of them changes. So the
        # total is the input and the stage budgets are derived from it, keeping
        # their relative sizes — those encode which stages are expensive, and
        # that stays true whatever the clock rate.
        # Time goes where the task is hard, and "hard" is something the run
        # already knows rather than something anyone has to declare.
        #
        # Two signals, and they compound because they mean different things:
        #
        #   a later try     the first pass did not solve it, so the cheap
        #                   reading of the problem has been tried and failed
        #   the same error  twice the same signature means the pass is not
        #                   merely wrong, it is wrong in a way that repeats —
        #                   which is the case that needs thinking, not speed
        #
        # An easy task still finishes in ten minutes; only the ones that have
        # earned it get longer.
        stuck = int(getattr(self, "same_failure_count", 0) or 0)
        scale = (budget_scale()
                 * float(_tuned("research.retry_budget_multiple", 1.5))
                 ** max(0, attempt_index - 1))
        if stuck >= 2:
            scale *= float(_tuned("research.stuck_budget_multiple", 1.5))
        # A floor, because a stage too short to make one tool call is not a
        # fast stage, it is a stage that always finalises.
        floor = int(_tuned("research.min_stage_s", 30))
        budgets = ({name: max(floor, int(value * scale))
                    for name, value in self.STAGE_BUDGETS.items()}
                   if scale != 1.0 else dict(self.STAGE_BUDGETS))
        if stuck >= 2:
            # The extra time goes to `plan`, because `plan` is now the stage
            # that reads the failure. A pass producing the same error twice
            # does not need a wider search — it needs a better reading of why
            # its understanding of the problem is wrong, and that happens
            # before any idea is put up.
            budgets["plan"] = int(
                budgets["plan"]
                * float(_tuned("research.stuck_diagnose_multiple", 2.0)))

        def fanout(steps: List[Tuple[str, str]], budget: int) -> None:
            """Issue several independent stages at once, then wait for all.

            The pipeline is a chain of dependencies, but not every link is one:
            two stages that read different things and write different records
            can run at the same time, and running them in sequence costs the sum
            of their latencies for no reason.

            That cost is what this exists to remove. Against a model decoding
            ~150 tok/s a stage takes minutes, so overlapping two halves of the
            survey halves its wall clock — and it doubles the requests in
            flight, which matters when the fleet has 128 slots and a six-task
            run was leaving 28 of 32 backends idle.

            Issue-and-wait rather than fire-and-forget: the stage after this one
            reads what these wrote, so all of them must have landed before it
            starts. A stage that raises drops out of the results and is reported
            like any other failure; it does not take the others with it.
            """
            if len(steps) == 1:
                name, prompt = steps[0]
                stage(name, prompt, budget)
                return
            with task_pool(len(steps)) as pool:
                # list() forces the wait: the barrier IS the point.
                list(pool.map(lambda step: stage(step[0], step[1], budget),
                              steps))

        # The pipeline, in full.
        #
        #   plan            5 min      three ideas, recorded
        #   explore         2 min      each idea, all at once
        #   build-solution  untimed    the solution skill, from what they found
        #
        # Research runs AFTER an attempt has failed, so the plan is given the
        # task, its inputs and the error, and it is planning against a concrete
        # failure rather than against a description.
        #
        # What this replaces: survey, plan, aspect, aspect-record, collect,
        # propose, tune, evaluate and execution-plan. Each of those was a real
        # step, and together they were a pass that took fifty minutes without
        # reaching an attempt. Most of them existed to hand the next stage a
        # summary of records the store already held.
        # The plan, and scouts looking for ideas beside it.
        #
        # One planner produced exactly the ideas one reading of the failure
        # suggests, and the floor of three became the target: it proposed
        # three, the validator kept two, and a round was spent asking for one
        # more. But an idea nobody proposes cannot win, and every idea that
        # survives is explored, written up and TRIED against the real tests —
        # so the cost of a surplus idea is bounded and the cost of a missing
        # one is the task.
        #
        # So the scouts run beside the planner, each told to look somewhere
        # else, and they append through `research_add_aspects` — `set_aspects`
        # replaces the list, and with several writing at once that would leave
        # only whoever saved last. Duplicates are dropped on the way in, so
        # "more ideas" cannot become "the same idea three times".
        #
        # Each is validated as it lands rather than at a barrier: the validator
        # judges a list, so it can run against what has arrived while the rest
        # are still looking.
        def aspect_count() -> int:
            return len(self._in_store(store_root, self._load_aspects, topic) or [])

        def recording_stage(name: str, prompt: str, budget: int,
                            tree: Optional[Path] = None) -> None:
            """Run a planning stage, and make it record before it is allowed to end.

            A stage that recorded nothing is not a stage that found nothing —
            it is usually one that filed its ideas somewhere the pipeline does
            not read. Measured on django-13551: scouts selected
            `research_add_aspects`, then wrote their ideas to JSON files with
            Bash. The record stayed empty, the trace showed every stage
            completing, and the whole exploration phase was skipped in silence.

            The round-level retry already re-runs planning when the count is
            short, but it re-runs the WHOLE cycle — investigation included —
            and the ideas from this pass are gone by then. Asking here, while
            the agent still has them in context, costs one short turn and
            recovers work that has already been paid for.
            """
            before = aspect_count()
            stage(name, prompt, budget, brief_only, tree)
            if aspect_count() > before:
                return
            if on_call:
                on_call(f"[{name}] recorded nothing — its ideas, if it found "
                        f"any, are not in the record. Asking it to file them.")
            # Run as the VALIDATOR, which has no Bash and no Edit.
            #
            # Asking more firmly does not work. Measured on django-13551: the
            # re-ask stage was told "Do not investigate anything further. You
            # already did the work; this is the filing" — and spent its whole
            # turn reading the tests, editing tokens.py and diffing the result,
            # never calling the tool. An agent holding file tools does what
            # agents do. The only reliable way to make the call unavoidable is
            # to leave nothing else it CAN do: this agent can read, and it can
            # record aspects.
            stage(f"{name}-record", self.RECORD_ASPECTS_PROMPT,
                  self.FINALIZE_BUDGET_S, brief_only, tree, finalizing=True,
                  agent=self.filer_agent_name)
            if aspect_count() == before and on_call:
                on_call(f"[{name}] ** still nothing recorded after being asked "
                        f"directly — this stage contributed no ideas at all")

        # What the last attempt left failing, read from its own evaluation.
        #
        # The runner already writes `evaluation.json` beside each attempt, so
        # this is the verdict as measured rather than a summary of it. Empty on
        # the first try, which is correct: there is no remaining failure yet.
        still_failing = ""
        if attempt_index > 1:
            previous_dir = workdir.parent / f"attempt-{attempt_index - 1}"
            try:
                seen = json.loads(
                    (previous_dir / "evaluation.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                seen = {}
            names = seen.get("fail_to_pass_failing") or []
            working = seen.get("fail_to_pass_passing") or []
            if names:
                still_failing = self.STILL_FAILING_NOTE.format(
                    failing="\n".join(f"- `{name}`" for name in names[:20]),
                    working=("\n".join(f"- `{name}`" for name in working[:20])
                             if working else
                             "- nothing yet: no target test passes because of "
                             "the last change"),
                    passed=seen.get("fail_to_pass_passed", "?"),
                    total=seen.get("fail_to_pass_total", "?"))
                if on_call:
                    on_call(f"[research] planning against {len(names)} test(s) "
                            f"still failing: {', '.join(names[:3])}")

        # ONE budget for judging, across every path that asks for it.
        #
        # `MAX_JUDGEMENTS` counted only the plan loop, and the scouts call the
        # validator too — pipelined, so each scout's ideas are judged as they
        # land. Measured on django-13551 with the cap already in place:
        # `validate-ideas` ran 300 times on one task and its finalize 303, for
        # 64 minutes in the plan phase and no steps recorded. Almost none of
        # that was a stage running out of time; fifteen budget events in the
        # whole hour. It was the NUMBER of calls, and the loop that counted
        # them was not the loop making most of them.
        judgements = [0]

        def judge():
            """Run the corrector, or None when the pass has judged enough."""
            if judgements[0] >= self.MAX_JUDGEMENTS:
                return None
            judgements[0] += 1
            stage("validate-ideas", self.VALIDATE_IDEAS_PROMPT, 0,
                  agent=self.validator_agent_name)
            return judgements[0]

        def scout(job) -> None:
            position, angle = job
            tree, unavailable = private_tree(f"plan-{position}")
            if unavailable and on_call:
                on_call(f"[plan:{angle['name']}] worktree unavailable "
                        f"({unavailable}); working in place")
            try:
                recording_stage(f"plan:{angle['name']}",
                      still_failing + self.PLAN_SCOUT_PROMPT.format(
                          topic="{topic}", angle=angle["look"],
                          workspace=str(tree)),
                      budgets["plan"], evidence)
                # Pipelined, not barriered: this scout's ideas are judged now,
                # while the others are still looking.
                judge()
            finally:
                drop_tree(tree)

        # The METHOD first, then ways for each of its steps.
        #
        # This used to be one bag: the planner and every scout proposed ideas
        # in parallel, the validator filtered, and the count decided when to
        # stop. That structure cannot produce a method, because nobody is ever
        # asked for one — four agents each answering "what could fix this?"
        # produce four rival fixes however the prompt is worded, and the gates
        # downstream can only reject the shape, never create the missing one.
        # Measured across four successive tightenings on django-13551: numbered
        # candidates, then hyphenated implementation names, then three
        # phrasings of one function. Each gate caught its evasion and the next
        # round produced the same wrong shape in new clothes.
        #
        # So the decomposition gets a single writer with nothing else to do,
        # and the parallelism moves to where it was always wanted: several ways
        # for each step, found independently, no two scouts on the same step.
        recording_stage("plan", still_failing + self.PLAN_PROMPT,
                        budgets["plan"], evidence)
        method = self._in_store(store_root, self._load_aspects, topic) or []

        def approach_count() -> int:
            """Ways on record. The thing `candidate_plans` builds from."""
            return len(self._in_store(store_root, research_mod.load, topic)
                       .get("approaches") or [])

        # Candidates already built and tried, so nothing is tried twice.
        # Set the moment any candidate passes the task's own tests. Every other
        # stage checks it, so a success stops the plan asking for more ideas and
        # the ideas in flight file what they have instead of running on.
        stop_generating = threading.Event()
        solved: List[Dict[str, Any]] = []
        tried: List[Dict[str, Any]] = []
        tried_lock = threading.Lock()
        built: Dict[str, Dict[str, Any]] = {}
        built_lock = threading.Lock()

        def build_and_try(plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Write one candidate up and put it in front of the task's tests."""
            if trial is None or stop_generating.is_set():
                return None
            name = str(plan.get("name") or "")
            with built_lock:
                if name in built:
                    return None
                built[name] = plan
            tree, unavailable = private_tree(
                "solution-" + re.sub(r"[^a-z0-9]+", "-", name.lower())[:24])
            if unavailable and on_call:
                on_call(f"[build-solution:{name}] worktree unavailable "
                        f"({unavailable}); working in place")
            try:
                stage(f"build-solution:{name}",
                      self.SOLUTION_SKILL_PROMPT.format(
                          topic="{topic}", name=name,
                          skill=self.candidate_skill_name(topic, name),
                          summary=plan.get("summary", "")),
                      0, brief_only, tree)
            finally:
                drop_tree(tree)
            if stop_generating.is_set():
                return None
            result = trial(plan)
            with tried_lock:
                tried.append(result)
                if result.get("resolved"):
                    solved.append(result)
            if result.get("resolved"):
                stop_generating.set()
                if on_call:
                    on_call(f"[trial:{name}] SOLVED the task — no more ideas "
                            f"needed; the ones in flight will file what they "
                            f"have and the pass finalises")
            return result

        def combine_if_ready() -> None:
            """Once two ideas have been tried, try what they are TOGETHER.

            A task is often not one bug: an idea can put the right check in the
            right place and still fail because two more sites needed changing.
            Each idea holds a piece and none holds the task, so the combination
            is a real candidate rather than a tie-breaker — and it is built as
            soon as there are two to combine, not after the last idea lands,
            because waiting for the slowest is what the whole pass is avoiding.
            """
            if trial is None or stop_generating.is_set():
                return
            with finished_lock:
                have = [n for n, r in finished.items() if r]
            if len(have) < 2:
                return
            super_name = "super-" + "-".join(
                re.sub(r"[^a-z0-9]+", "-", n.lower())[:12] for n in sorted(have)[:3])
            with built_lock:
                if super_name in built:
                    return
            build_and_try({
                "name": super_name,
                "summary": "the combination of " + ", ".join(sorted(have)),
                "aspect": ""})

        def ways(job) -> None:
            position, step = job
            label = str(step.get("name") or f"step-{position}")[:32]
            tree, unavailable = private_tree(f"refine-{position}")
            if unavailable and on_call:
                on_call(f"[refine:{label}] worktree unavailable "
                        f"({unavailable}); working in place")
            try:
                before = approach_count()
                stage(f"refine:{label}",
                      still_failing + self.REFINE_IDEA_PROMPT.format(
                          topic="{topic}", step=step.get("name", ""),
                          question=step.get("question", ""),
                          where=step.get("where", "") or "not stated",
                          others="; ".join(
                              str(other.get("name") or "") for other in method
                              if other is not step) or "none",
                          workspace=str(tree)),
                      budgets["plan"], brief_only, tree)
                # A step with no ways attached produces no candidate, so
                # nothing is built and nothing is tried. Same enforcement as
                # the planning stages, one stage later and mattering more.
                if approach_count() == before:
                    if on_call:
                        on_call(f"[refine:{label}] recorded nothing — asking it to "
                                f"file the steps it worked out")
                    stage(f"refine:{label}-record",
                          self.RECORD_WAYS_PROMPT.format(
                              step=step.get("name", "")),
                          self.FINALIZE_BUDGET_S, brief_only, tree,
                          finalizing=True, agent=self.filer_agent_name)
                    if approach_count() == before and on_call:
                        on_call(f"[refine:{label}] ** still nothing recorded — "
                                f"this idea has nothing to try")
            finally:
                drop_tree(tree)

        # The angle scouts are the FALLBACK, and they run first when the
        # planner gave nothing — so that the ways fan-out below has something
        # to work on either way.
        if not method:
            if on_call:
                on_call(f"[plan] no method recorded — falling back to "
                        f"{len(self.PLAN_ANGLES)} scout(s) looking for ideas at "
                        f"once: " + ", ".join(a["name"] for a in self.PLAN_ANGLES))
            jobs = [(lambda job=job: scout(job))
                    for job in enumerate(self.PLAN_ANGLES, 1)]
            with task_pool(len(jobs)) as pool:
                list(pool.map(lambda run: run(), jobs))
            # Re-read: whatever the fallback recorded IS the method now.
            #
            # This was read once, straight after the plan stage, and the ways
            # fan-out was gated on that one reading. So a pass whose planner
            # recorded nothing — which is every pass measured so far — skipped
            # the ways scouts, recorded no approach, built no candidate, and
            # therefore never evaluated anything. The fallback did its job and
            # the work it produced had nowhere to go.
            method = self._in_store(store_root, self._load_aspects, topic) or []

        if method:
            if on_call:
                on_call(f"[plan] method of {len(method)} step(s); finding ways "
                        f"for each, in parallel: "
                        + ", ".join(str(s.get("name") or "?") for s in method))
            with task_pool(max(1, len(method))) as pool:
                list(pool.map(ways, enumerate(method, 1)))

        ideas = self._in_store(store_root, self._load_aspects, topic) or []

        # Planning must produce ideas. Keep at it until it does.
        #
        # The pipeline is a protocol: `plan` records what to explore, and the
        # exploration fans out over what it recorded. A model that reads the
        # repository and narrates instead of calling `research_set_aspects`
        # leaves the record empty — and an empty list reads as "nothing to
        # explore", so the whole phase is skipped in silence while the trace
        # shows research advancing through its stages. Measured: five phronix
        # tool calls across a six-task run, all `research_prior`, with zero
        # ideas in every record, and the arm scored as having researched.
        # Predictor and corrector, once per round.
        #
        # `plan` predicts which questions are worth two minutes each; the
        # validator judges that list and writes back only the ideas that could
        # actually change what we do. Then the count decides: three good ideas
        # and the loop ends, fewer and the plan runs again knowing what was
        # rejected.
        #
        # The asymmetry is deliberate. Generating ideas is open-ended — an
        # agent will read the whole repository looking for one — so it gets a
        # clock. Judging a list of three is bounded by the list, so it gets
        # none: a ceiling there could only ever cut the cheap half of the loop.
        # Exploration is a CONSUMER, started before the plan is finished.
        #
        # The plan used to have to finish before any idea was explored: rounds
        # of proposing and judging, then a barrier, then the fan-out. So the
        # first idea — often the good one, recorded in the first minute — sat
        # idle for as long as the planner spent looking for its third. Measured
        # on scikit-learn-25570: four steps recorded at 20:48 and the pass was
        # still in `plan-more-1` at 21:13, having explored none of them.
        #
        # Now the planner emits and the exploration consumes: an idea is picked
        # up as soon as the validator has kept it, and later ideas join a pool
        # that is already working. `max_parallel_aspects` still bounds how many
        # run at once, and each is submitted exactly once.
        roster = list(getattr(self, "models", None) or [])
        if len(roster) <= 1:
            spread = self.fanout_models(instance, self.max_parallel_aspects)
            if spread:
                roster = spread

        # Each idea explored and judged in its own thread, to its own end.
        #
        # Explore and validate used to be phases with a barrier between them:
        # every idea explored, then everything stopped while one validator read
        # all of them, then whichever came back thin was explored again. The
        # barrier cost the difference between the slowest idea and the fastest,
        # twice — and it cost it to ideas that were finished and had nothing to
        # wait for.
        #
        # Now one idea's second pass starts while another is still on its
        # first. The validator judges a list and there is no reason it has to
        # be the whole list: an idea that answered its question is complete on
        # its own, and one that ran out has a gap of its own to close.
        #
        # The clock still bounds it. Two minutes is a PREDICTION that a
        # question fits in two minutes, and MAX_EXPLORE_ROUNDS is how many
        # times that prediction may be wrong before the pass moves on with
        # what it has.
        # One idea, carried from explored to JUDGED BY THE TESTS.
        #
        # An idea is a way of solving the whole problem — a sequence of steps —
        # and it is complete when the task's own tests have seen it. Building
        # every solution, then racing them, made the first workable idea wait
        # for the slowest one to finish being explored, and the exploring of
        # the others is exactly the work a success makes unnecessary.
        #
        # So each idea finishes on its own thread: write it up, put it in front
        # of the tests, and if it passes, say so — `stop_generating` is what
        # every other stage checks, so the plan stops asking for more and the
        # ideas still in flight file what they have instead of running on.
        finished: Dict[str, Dict[str, Any]] = {}
        finished_lock = threading.Lock()

        def finish_idea(idea: Dict[str, Any]) -> None:
            name = str(idea.get("name") or "")
            if not name or trial is None or stop_generating.is_set():
                return
            with finished_lock:
                if name in finished:
                    return
                finished[name] = {}
            plan = next(
                (p for p in (self.candidate_plans(
                    store_root, topic, int(self.attempt_candidates)) or [])
                 if str(p.get("name") or "") == name
                 or str(p.get("aspect") or "") == name), None)
            if plan is None:
                plan = {"name": name, "summary": str(idea.get("question") or "")}
            result = build_and_try(plan)
            with finished_lock:
                finished[name] = result or {}
            combine_if_ready()

        def pursue(job) -> None:
            position, idea = job
            mine = roster[position % len(roster)] if len(roster) > 1 else ""
            name = idea.get("name", "?")
            safe = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            dump = checkout / RESEARCH_SCRATCH / f"idea-{safe}.md"
            dump.parent.mkdir(parents=True, exist_ok=True)
            gap = ""

            for round_no in range(1, self.MAX_EXPLORE_ROUNDS + 1):
                tree, unavailable = private_tree(f"idea-{position}-{round_no}")
                if unavailable and on_call:
                    on_call(f"[explore:{name}] worktree unavailable "
                            f"({unavailable}); working in place")
                # A second pass is not a repeat: it is told what was missing
                # and given longer, because closing a named gap is worth more
                # than the first open-ended look and the question is now
                # narrower.
                budget = int(budgets["explore"]
                             * (float(_tuned("research.round_budget_multiple", 1.5))
                                ** (round_no - 1)))
                try:
                    if gap:
                        stage(f"explore:{name}",
                              self.EXPLORE_MORE_PROMPT.format(
                                  topic="{topic}", name=name, gap=gap[:800],
                                  budget=budget, dump=dump, workspace=str(tree)),
                              budget, brief_only, tree, model=mine)
                    else:
                        stage(f"explore:{name}",
                              self.EXPLORE_PROMPT.format(
                                  topic="{topic}", name=name,
                                  question=idea.get("question", name),
                                  where=(f"Where to look: {idea['where']}"
                                         if idea.get("where") else ""),
                                  budget=budget, dump=dump,
                                  workspace=str(tree)),
                              budget, brief_only, tree, model=mine)
                finally:
                    drop_tree(tree)

                if round_no >= self.MAX_EXPLORE_ROUNDS:
                    return finish_idea(idea)
                # This idea judged now, on its own, while the others are still
                # being explored. The validator has no budget and sends back
                # only what would change the solution; a negative result is
                # complete and stays complete.
                stage(f"validate-exploration:{name}",
                      self.VALIDATE_ONE_EXPLORATION_PROMPT.format(
                          topic="{topic}", name=name,
                          question=idea.get("question", name)),
                      0, agent=self.validator_agent_name)
                gap = (self._in_store(store_root, self._thin_gaps, topic)
                       or {}).get(name, "")
                if not gap:
                    return finish_idea(idea)
                if on_call:
                    on_call(f"[explore:{name}] came back thin: {gap[:90]}")


        # Set the moment any candidate passes the task's own tests.
        #
        # "Stop generating ideas once one works" is the whole point of giving
        # research a trial seam: everything after a solved task — more rounds
        # of planning, more explores, more combinations — is spend against a
        # question that has been answered.

        # --- the consumer, fed by the plan loop below -----------------------
        explore_pool = task_pool(self.max_parallel_aspects)
        explore_futures: List[Any] = []
        submitted: Dict[str, int] = {}

        def drain_ideas() -> int:
            """Start exploring every idea the validator has kept and we have not.

            Called after each planning round, so an idea recorded in round one
            is being explored while round two is still being asked for. Names
            are the key because the record is rewritten each round — the
            validator writes back the kept list — and re-submitting an idea
            would explore it twice and pay for it twice.
            """
            started = 0
            for idea in self._in_store(store_root, self._load_aspects, topic) or []:
                name = str(idea.get("name") or "").strip()
                if not name or name in submitted:
                    continue
                if len(submitted) >= self.max_parallel_aspects:
                    break
                position = len(submitted)
                submitted[name] = position
                explore_futures.append(
                    explore_pool.submit(pursue, (position, idea)))
                started += 1
            if started and on_call:
                on_call(f"[explore] started {started} idea(s) as they were kept "
                        f"— {len(submitted)} exploring, the plan is still going")
            return started

        # Past the floor, looking for more is on a CLOCK.
        #
        # The floor is a floor, not a target: three independent steps is enough
        # to proceed on, and everything after that is opportunistic. Left
        # unbounded it does not read as opportunistic — measured on
        # django-13551, the loop kept eight good steps, asked for three more,
        # and was still asking twenty-five minutes into a task the bare arm had
        # already finished twice. Nothing was wrong; it simply had no reason to
        # stop.
        #
        # So once the floor is met the search continues only while this budget
        # lasts, and when it runs out the pass finalises with what it has and
        # moves on. A clock rather than a round cap because rounds are not the
        # cost — an agent reading the repository for one more idea is.
        extra_search_s = max(0, int(_tuned("research.extra_ideas_seconds", 240)
                                    * budget_scale()))
        floor_met_at = 0.0
        tries_at_plan = 0
        report = ""
        last_count, stuck_rounds = -1, 0
        # The corrector has no clock, so the LOOP has to bound how often it is
        # asked. Measured on django-13551: `validate-ideas` ran 83 times on one
        # task — judging far more often than there was anything new to judge,
        # and it is the unbudgeted half of the loop, so nothing else stopped it.
        while tries_at_plan < self.MAX_PLAN_RETRIES:
            if judge() is None:
                if on_call:
                    on_call(f"[plan] the validator has judged "
                            f"{judgements[0]} time(s) — taking the "
                            f"{len(ideas)} idea(s) on record and moving on")
                break
            if stop_generating.is_set():
                if on_call:
                    on_call("[plan] a candidate already solved the task — "
                            "stopping the search for more ideas")
                break
            # The validator writes back only the ideas worth exploring, so the
            # store now holds the KEPT ones — this read is the running total,
            # not a fresh count.
            ideas = self._in_store(store_root, self._load_aspects, topic) or []
            report = last_output.get("validate-ideas", "") or report
            # Kept ideas go to the consumer NOW, not after the loop ends.
            drain_ideas()
            # Enough ideas is not the same as enough DIFFERENT ideas.
            #
            # This counted them and stopped. Five ideas all aimed at one
            # function passed that test and cost three tries to disprove — so
            # the count is now a floor on INDEPENDENT ideas, and an overlapping
            # set is sent back with the overlap named.
            clashes = self.overlapping_ideas(ideas)
            if len(ideas) >= self.MIN_ASPECTS and not clashes:
                # The floor is met. Look for more only while the clock allows,
                # then finalise with what is there.
                if extra_search_s <= 0:
                    break
                if not floor_met_at:
                    floor_met_at = time.time()
                    if on_call:
                        on_call(f"[plan] {len(ideas)} independent step(s) — "
                                f"enough to proceed. Looking for more for up to "
                                f"{extra_search_s}s, then finalising with "
                                f"whatever is found.")
                elif time.time() - floor_met_at >= extra_search_s:
                    if on_call:
                        on_call(f"[plan] out of time looking for more — "
                                f"finalising with {len(ideas)} step(s) and "
                                f"moving on")
                    break
            if clashes and on_call:
                on_call("[plan] " + "; ".join(
                    f"{', '.join(names)} all look in {place}"
                    for place, names in list(clashes.items())[:3])
                    + " — asking for an idea somewhere else")
            # A flat round is a signal to ask DIFFERENTLY, not to stop.
            #
            # Measured: `2 good idea(s) kept, asking for 1 more` four rounds
            # running. The planner kept offering variations of the two it
            # already had and the validator kept rejecting them as filler.
            # Asking the same question again gets the same answer.
            #
            # So the ask changes shape: the kept ideas go in as one-sentence
            # summaries and the request is for something those two do not
            # cover. Giving up would explore a thinner plan; this explores the
            # same plan after a better question.
            if len(ideas) <= last_count:
                stuck_rounds += 1
            else:
                stuck_rounds = 0
            last_count = len(ideas)
            tries_at_plan += 1
            # Ask for MORE than the shortfall, because the validator culls.
            #
            # Asking for exactly one more, when one more is what is missing,
            # means a single rejection costs the whole round. Asking for three
            # and keeping whatever survives converges in the rounds where the
            # narrow ask stalled.
            needed = max(self.MIN_ASPECTS - len(ideas), self.PLAN_OVERASK)
            if on_call:
                on_call(f"[plan] {len(ideas)} good idea(s) kept, asking for "
                        f"{needed} more (round {tries_at_plan})")
            # More time each round, for the same reason a retry of the whole
            # task gets more: the cheap reading of the problem has been tried
            # and did not produce enough.
            more_budget = int(budgets["plan"]
                              * (float(_tuned("research.round_budget_multiple",
                                              1.5)) ** tries_at_plan))
            stage(f"plan-more-{tries_at_plan}",
                  self.PLAN_MORE_PROMPT.format(
                      topic="{topic}", kept_n=len(ideas), needed=needed,
                      kept="\n".join(
                          f"  {n}. {i.get('name')} — "
                          f"{self._one_sentence(i.get('question', ''))}"
                          for n, i in enumerate(ideas, 1)) or "  (none yet)",
                      stuck=("\n\nThe last round added nothing. Every idea you "
                             "just proposed was judged a variation of these. "
                             "Change the axis, do not rephrase."
                             if stuck_rounds else ""),
                      report=(report or "(the first plan recorded too few)")[-1500:]),
                  more_budget)

        # The plan's OTHER two outputs, checked deterministically.
        #
        # Ideas had a corrector and the metric and corpus did not, so a task
        # could reach `build-solution` with `0 inst` and `fom=-` — a solution
        # built with nothing to measure it against and no signal anything was
        # missing. This check is arithmetic over the record rather than a
        # judgement, which is what lets it be trusted: a corrector that can be
        # talked out of its verdict is not a corrector.
        gaps = self._in_store(store_root, self._plan_gaps, topic,
                              self.MIN_CORPUS) or []
        if gaps:
            if on_call:
                on_call("[plan] incomplete: " + "; ".join(g.split(" (")[0]
                                                          for g in gaps))
            stage("complete-plan",
                  self.COMPLETE_PLAN_PROMPT.format(
                      topic="{topic}",
                      gaps="\n".join(f"  - {g}" for g in gaps)),
                  0)
            # Re-read with a settle, because the write and the check race.
            #
            # Measured: the corrector filled the record to 25 instances with a
            # figure of merit, the record's mtime was 17:40:09.000, and the
            # re-check ran in that same second and reported "still incomplete".
            # The agent writes through its own process and the harness reads
            # in-process, over Lustre, so the two can miss each other by less
            # than a second.
            #
            # A false "still incomplete" is the wolf-crying failure again: it
            # reports the corrector as broken exactly when it worked.
            still = self._in_store(store_root, self._plan_gaps, topic,
                                   self.MIN_CORPUS) or []
            for _ in range(3):
                if not still:
                    break
                time.sleep(1.0)
                still = self._in_store(store_root, self._plan_gaps, topic,
                                       self.MIN_CORPUS) or []
            if still and on_call:
                # Said, not hidden: the build stage is about to work without
                # this, and a thin result should be explained rather than
                # discovered later.
                on_call("[plan] ** still incomplete after the corrector: "
                        + "; ".join(g.split(" (")[0] for g in still))

        # Salvage before falling back: a planner that named its ideas in prose
        # has done the thinking, and only the recording is missing.
        if len(ideas) < self.MIN_ASPECTS:
            # Salvage from EVERY planning stage, not just `plan`.
            #
            # This read `last_output["plan"]` alone, so a planner that opened
            # with a summary and named its steps in a LATER round left nothing
            # to salvage. Measured on `pylint-dev__pylint-7114`: `plan` wrote
            # "Problem Summary (from exchange.md and issue.md)" and recorded
            # nothing; `plan-more-1` wrote "Three new research aspects for
            # pylint-dev__pylint-7114" and also recorded nothing. The steps
            # existed in prose, in the output this line did not read, while the
            # validator judged an empty list round after round.
            #
            # Later rounds first: they are the planner's most considered answer,
            # and the ones written after being told what was missing.
            texts = [text for name, text in sorted(last_output.items(),
                                                   reverse=True)
                     if name == "plan" or name.startswith(("plan-more",
                                                           "plan:"))]
            salvaged = []
            seen = set()
            for text in texts:
                for idea in self._aspects_from_text(text) or []:
                    key = str(idea.get("name") or "").strip().lower()
                    if key and key not in seen:
                        seen.add(key)
                        salvaged.append(idea)
            if salvaged:
                if on_call:
                    on_call(f"[plan] salvaged {len(salvaged)} idea(s) from "
                            f"what the planner wrote but did not record")
                self._in_store(store_root, research_mod.set_aspects, topic,
                               salvaged)
                ideas = self._in_store(store_root, self._load_aspects, topic) or []
        # Fewer than three after five rounds: explore what there is.
        #
        # The generic angles are for a plan that produced NOTHING, not for one
        # that produced two real ideas — replacing two task-specific questions
        # with `source-location` and `minimal-repro` throws away the only part
        # of the plan that was worth anything.
        if not ideas:
            # Loud, because this is the failure that looks like success.
            #
            # There is a check for a research pass making ZERO tool calls, which
            # catches a dead endpoint. There was none for a pass that ran, used
            # its tools, and recorded nothing — and that one is silent: the
            # validator judges an empty list, the loop asks for more, and the
            # trace shows research advancing through its stages.
            #
            # Measured: two full planning rounds on `pylint-dev__pylint-7114`,
            # both narrating their aspects in prose, `set_aspects` never called,
            # zero steps in the record, twenty minutes spent.
            if on_call:
                on_call("[plan] ** the planner recorded NOTHING — it ran and "
                        "used tools, but `research_set_aspects` was never "
                        "called and nothing could be salvaged from its text. "
                        "Falling back to the default angles, which are generic: "
                        "this pass is not researching THIS problem.")
            ideas = list(self.DEFAULT_ASPECTS)
        elif len(ideas) < self.MIN_ASPECTS and on_call:
            on_call(f"[plan] {len(ideas)} idea(s) after {tries_at_plan} "
                    f"round(s) — exploring these rather than padding to "
                    f"{self.MIN_ASPECTS}")

        # Explore every idea at once. Two minutes each, so two minutes in all.
        # Whatever the salvage or the fallback added, plus everything the plan
        # loop already handed over. Then wait for the pool to drain.
        drain_ideas()
        chosen = [idea for idea in ideas
                  if str(idea.get("name") or "") in submitted] or ideas[:1]
        if on_call:
            on_call(f"[explore] {len(submitted)} idea(s) exploring, each judged "
                    f"and re-explored on its own: "
                    + ", ".join(sorted(submitted)))
        try:
            for future in explore_futures:
                try:
                    future.result()
                except Exception as exc:      # noqa: BLE001 - one idea, not the pass
                    if on_call:
                        on_call(f"[explore] an idea failed: {exc}")
        finally:
            explore_pool.shutdown(wait=True)

        # One solution skill PER candidate, not one merged skill for the pass.
        #
        # The attempt races every ranked plan against the task's own target
        # tests, concurrently, and each racer is told to follow one specific
        # plan. That only works if the plan arrives as something executable —
        # otherwise three agents are handed three one-line summaries and the
        # difference between the candidates lives in a sentence.
        #
        # A single merged skill was worse than useless here: written from a
        # figure of merit measured on a corpus research built for itself, it
        # committed to an answer before any idea had met the real tests, and
        # all three racers loaded the same one — so the slot where the ideas
        # are supposed to differ held the same text three times.
        #
        # The merge happens AFTER, in `reconcile_trials`, where the table of
        # what actually passed decides which spine the skill is built on.
        #
        # With a single candidate there is no race and nothing to compare, so
        # the merged write-up stays the pass's durable output.
        # NOT `max(1, ...)`: 0 means every plan, and clamping it to 1 would make
        # this stage write a single merged skill while the runner went on to
        # race — leaving the race with one candidate and nothing to compare.
        plans = self.candidate_plans(
            store_root, topic, int(self.attempt_candidates))
        if len(plans) > 1:
            if on_call:
                on_call(f"[build-solution] {len(plans)} candidate(s), one "
                        "skill each so the attempt can race them: "
                        + ", ".join(p["name"] for p in plans))

            def write_candidate(job) -> None:
                position, plan = job
                tree, unavailable = private_tree(f"solution-{position}")
                if unavailable and on_call:
                    on_call(f"[build-solution:{plan['name']}] worktree "
                            f"unavailable ({unavailable}); working in place")
                try:
                    stage(f"build-solution:{plan['name']}",
                          self.SOLUTION_SKILL_PROMPT.format(
                              topic="{topic}", name=plan["name"],
                              skill=self.candidate_skill_name(topic,
                                                              plan["name"]),
                              summary=plan.get("summary", "")),
                          0, brief_only, tree)
                finally:
                    drop_tree(tree)

            # Each candidate written, then TESTED, without waiting for the rest.
            #
            # Writing every skill, then combining, then handing the whole set to
            # the runner meant nothing met the real tests until research was
            # over — so a pass went on generating and combining long after one
            # of its ideas had already solved the task, and the idea recorded
            # first was tested last. The trial seam removes that wait: a
            # candidate is judged by the task's own tests the moment it is
            # executable, which is the only judge that settles anything.
            def write_and_try(job) -> None:
                write_candidate(job)
                if trial is None or stop_generating.is_set():
                    return
                _, plan = job
                result = trial(plan)
                with tried_lock:
                    tried.append(result)
                    if result.get("resolved"):
                        solved.append(result)
                if result.get("resolved"):
                    stop_generating.set()
                    if on_call:
                        on_call(f"[trial:{plan['name']}] SOLVED the task — "
                                f"no more ideas needed; reconciling what is in")

            with task_pool(len(plans)) as pool:
                list(pool.map(write_and_try, list(enumerate(plans, 1))))

            # THE SUPER IDEA: one more candidate, combining what every idea found.
            #
            # Skipped entirely when something has already passed. A combination
            # is a bet that several partial fixes belong together, and that bet
            # is pointless once one of them fixes the whole task on its own —
            # building it there costs an agent and a container to test an idea
            # nobody needs.
            # A combination is not a combination until the pieces are in, so it
            # is built once, from whatever is in when the singles are done.
            #
            # It earns its place because a task is often not one bug: an attempt
            # can put the right check in the right function and still fail
            # because the same issue needed two more sites changed. Each idea
            # holds a piece; no single idea holds the task.
            #
            # An ADDITIONAL racer, never a replacement. Combining is a bet that
            # the pieces belong together, and the singles stay in the race for
            # when they do not — `reconcile_trials` then folds the table of what
            # passed and what did not into one skill.
            # Skipped when something has already passed. A combination is a
            # bet that several partial fixes belong together, and that bet is
            # pointless once one of them fixes the whole task on its own —
            # building it there costs an agent and a container to test a
            # candidate nobody needs.
            if stop_generating.is_set():
                if on_call:
                    on_call(f"[build-solution] skipping the combination — "
                            f"{solved[0]['plan']} already solved it")
            else:
                super_name = "super-idea"
                findings = "\n".join(
                    f"- {plan['name']}: {(plan.get('summary') or '')[:200]}"
                    for plan in plans)
                tree, unavailable = private_tree("solution-super")
                if unavailable and on_call:
                    on_call(f"[build-solution:{super_name}] worktree unavailable "
                            f"({unavailable}); working in place")
                try:
                    if on_call:
                        on_call(f"[build-solution:{super_name}] combining "
                                f"{len(plans)} idea(s) into one candidate: "
                                + ", ".join(p["name"] for p in plans))
                    stage(f"build-solution:{super_name}",
                          self.SUPER_IDEA_PROMPT.format(
                              topic="{topic}", findings=findings,
                              skill=self.candidate_skill_name(topic, super_name)),
                          0, brief_only, tree)
                    # Recorded as an approach, or `candidate_plans` cannot see it and
                    # the skill is built at full cost and never run.
                    self._in_store(
                        store_root, research_mod.add_approach, topic, super_name,
                        "the combination of " + ", ".join(p["name"] for p in plans),
                        "Each idea fixes part of this task; applied together they fix "
                        "the whole of it. False if the combined change passes no more "
                        "target tests than the best single idea.")
                except Exception as exc:      # noqa: BLE001 - reported, not raised
                    if on_call:
                        on_call(f"[build-solution:{super_name}] could not "
                                f"combine: {exc}")
                finally:
                    drop_tree(tree)
        else:
            stage("build-solution", self.BUILD_SOLUTION_PROMPT, 0)

        # What the trials found, for the runner and for the record.
        trial_report: Dict[str, Any] = {}
        if trial is not None and tried:
            best = max(tried, key=lambda r: int(r.get("target_tests_passed") or 0))
            trial_report["trials"] = [
                {"plan": r.get("plan"), "resolved": bool(r.get("resolved")),
                 "target_tests_passed": int(r.get("target_tests_passed") or 0),
                 "error": r.get("error", "")}
                for r in tried]
            trial_report["solved_by"] = [r["plan"] for r in tried if r.get("resolved")]
            trial_report["best_outcome"] = best.get("outcome")
            if on_call:
                on_call("[trials] " + ", ".join(
                    f"{r['plan']}={r.get('target_tests_passed', 0)}"
                    for r in tried)
                    + (f" — SOLVED by {', '.join(trial_report['solved_by'])}"
                       if trial_report["solved_by"] else " — none solved it"))

        # No `choose`. The pass ends with the candidates, and the tests pick.
        #
        # It existed to name one approach as "followed" so the ledger had
        # something to mark an outcome against — a guess, made before anything
        # was tried, and announced as "of 1, no measured ranking". Every plan
        # is now tried against the task's own tests and each result is marked
        # against the plan that produced it, so the guess has been replaced by
        # a measurement and there is nothing left for this stage to settle.
        #
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
            # Empty unless the runner handed this pass a trial seam. When it
            # did, these are candidates already measured against the task's own
            # tests — so the runner can use the verdict rather than racing them
            # a second time.
            **trial_report,
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
            # No ranking any more: `tune` is gone, so there are no recorded
            # trials to rank. The solution is built from what the ideas found,
            # not from a leaderboard over candidates nobody committed to.
            "ranking": [],
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
    def _aspects_from_text(output: str) -> List[Dict[str, str]]:
        """Aspects from a plan the agent wrote in prose instead of filing.

        A planner that narrates has done the thinking and skipped the
        bookkeeping; throwing that away and substituting generic angles loses
        the one thing it got right. So the numbered or bulleted lines of its
        own plan become the aspects.

        Deliberately dumb: it takes list items that read like questions or
        directives and gives each a slug. Anything cleverer would be guessing
        at intent, and a wrong aspect costs an investigation.
        """
        import json as _json

        found: List[Dict[str, str]] = []
        seen = set()
        for raw in (output or "").splitlines():
            # Agent stdout is a JSON event stream; the prose is inside it.
            text = raw
            if raw.lstrip().startswith("{"):
                try:
                    event = _json.loads(raw)
                except ValueError:
                    continue
                part = event.get("part") or {}
                text = str(part.get("text") or "")
                if not text:
                    message = event.get("message") or {}
                    blocks = message.get("content")
                    if isinstance(blocks, list):
                        text = " ".join(str(b.get("text") or "")
                                        for b in blocks
                                        if isinstance(b, dict))
            for line in str(text).splitlines():
                line = line.strip()
                item = re.match(r"^(?:[-*+]|\d+[.)])\s+(.{15,200})$", line)
                if not item:
                    continue
                question = re.sub(r"\*\*|`", "", item.group(1)).strip(" .:")
                slug = re.sub(r"[^a-z0-9]+", "-",
                              question.lower())[:40].strip("-")
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                found.append({"name": slug, "question": question})
                if len(found) >= 5:
                    return found
        return found

    def reconcile_trials(self, instance: Dict[str, Any], store_root: Path,
                         workdir: Path, trials: List[Dict[str, Any]],
                         on_call=None) -> None:
        """Turn the results of parallel trials into one skill, or a better question.

        Two very different situations, and treating them alike is what wastes
        the information. Something worked: the ranking has now been TESTED, so
        merge the winner with whatever the losers did better. Nothing worked: N
        independent approaches failing is evidence about the subject, and
        picking the least-bad one to refine is the single move that cannot find
        what they all assumed.

        Which of the two applies is decided in `phronix-trial-reconcile`, not
        here — the harness supplies the table and the skill supplies the method.
        """
        if len(trials) < 2:
            return

        checkout = workdir / "repo"
        if not checkout.is_dir():
            return

        table = "\n".join(
            f"- **{t['plan']}**: "
            + ("SOLVED it" if t.get("resolved")
               else f"{t.get('target_tests_passed', 0)} target test(s) passing")
            + (f" (trial error: {str(t['error'])[:80]})" if t.get("error") else "")
            for t in trials)
        solved = [t for t in trials if t.get("resolved")]
        label = "merge-skills" if solved else "optimise-candidates"
        if on_call:
            on_call(f"[{label}] {len(trials)} trial(s): "
                    + (f"{len(solved)} solved — merging what worked"
                       if solved else
                       "none solved it — questioning what they all assumed"))

        env = self.phronix_env(tool_path_env(
            isolated_env(store_root, workdir / "cache", fresh=self.fresh)))
        env.update(model_env(base_url=self.base_url, api_key=self.api_key))
        env["PHRONIX_WRITE_LAYER"] = "project"
        env["PHRONIX_PHASE"] = "research"
        env["PHRONIX_STAGE"] = label
        if self.store_readonly:
            env["PHRONIX_BENCH_FROZEN"] = "1"

        topic = self.research_topic(instance)
        prompt = (self.TRIAL_RECONCILE_PROMPT
                  .replace("{topic}", topic)
                  .replace("{results}", table)
                  .replace("{skills}", "\n".join(
                      f"- `{self.candidate_skill_name(topic, t['plan'])}`"
                      for t in trials)))
        try:
            stream_opencode(
                self.agent_command(LOG_NOTE + SCRATCH_NOTE + prompt, checkout,
                                   self.attachments([]),
                                   self.research_agent_name),
                # No work budget, only a hang-guard: this is now where the
                # pass's solution skill is written, from the one input that
                # settles it. Cutting it half way discards N attempts and N
                # evaluations, which is the most expensive thing in the pass.
                checkout, env, self.MUST_FINISH_GUARD_S, on_call,
                host=self.agent_host)
        except Exception as exc:
            # Reconciliation is bookkeeping over work already done; losing it
            # must not lose the trials themselves.
            if on_call:
                on_call(f"[{label}] FAILED: {type(exc).__name__}: {exc}")

    def candidate_plans(self, store_root: Path, topic: str,
                        limit: int = 3) -> List[Dict[str, str]]:
        """The ranked plans research produced, best first.

        Research already measures rival approaches against a figure of merit and
        ranks them; until now only the winner was ever attempted. But the metric
        is a proxy — it is measured on a corpus the research built, not on the
        task's own target tests — so the top-ranked plan is the most promising
        one, not the correct one.

        Trying several against the real tests is the cheap way to find out which
        the metric got right, and the fleet has the capacity: attempts are
        independent, so N plans cost wall-clock once rather than N times.
        """
        from phronix import research as research_mod

        record = self._in_store(store_root, research_mod.load,
                                research_mod.resolve_topic(topic)) or {}
        # `limit <= 0` means EVERY candidate, not none.
        #
        # A cap is the right default when each candidate costs an agent and a
        # container, but it makes "try what research proposed" impossible to ask
        # for: with five ideas and a cap of three, two are written up during the
        # pass and never tested, and nothing records that they were skipped.
        if limit is None or limit <= 0:
            limit = 1 << 30
        out: List[Dict[str, str]] = []
        for entry in (record.get("pipelines") or []) + (record.get("approaches") or []):
            name = str(entry.get("name") or entry.get("approach") or "").strip()
            summary = str(entry.get("summary") or entry.get("hypothesis")
                          or entry.get("steps") or "").strip()
            if not name or any(o["name"] == name for o in out):
                continue
            # A falsified approach is not a candidate: it has already been
            # measured and lost.
            if str(entry.get("status") or "") in ("falsified", "failed"):
                continue
            # Nor is the LEDGER's own record of an attempt. It writes one entry
            # per try whose NAME is the files that changed, which is not an idea:
            # measured on `pylint-dev__pylint-7114`, `a/__init__.py, a/a.py`
            # became `trial-1-a-init-py-a-a-py` and was raced like a plan —
            # spending a container, an agent and an evaluation on a file list,
            # and displacing a real idea from the limit.
            if str(entry.get("source") or "") == "benchmark attempt":
                continue
            # Belt and braces: a name that is a path is a file list however it
            # came to be recorded.
            if name.endswith(".py") or "/" in name or name.startswith("("):
                continue
            out.append({"name": name, "summary": summary[:600],
                        "skill": self.candidate_skill_name(topic, name)})
            if len(out) >= limit:
                break

        # The IDEAS count as candidates too.
        #
        # `plan` is asked for three ideas and the validator keeps the ones
        # worth exploring, so they are the best-understood set the pass has —
        # each explored in its own worktree, each with a finding. Approaches
        # are often fewer and, on a bad pass, are recorded as bare file paths.
        #
        # Reading only approaches meant a task with three good ideas raced one
        # candidate, which is not a race.
        if len(out) < limit:
            for idea in record.get("aspects") or []:
                name = str(idea.get("name") or "").strip()
                if not name or any(o["name"] == name for o in out):
                    continue
                out.append({"name": name,
                            "summary": str(idea.get("question") or "")[:600],
                            "skill": self.candidate_skill_name(topic, name)})
                if len(out) >= limit:
                    break
        return out

    #: The method for each of these lives in a skill, not here.
    #:
    #: A prompt in code is a method the system cannot edit: the learner improves
    #: skills, the graph indexes them, and reconcile keeps one copy of each
    #: fact — none of which reaches a string literal in a benchmark harness.
    #: What stays here is the INPUT, which is genuinely per-run.
    SUPER_IDEA_PROMPT = """\
Every idea for `{topic}` has been explored and written up on its own. Your job is
the one candidate none of them can be: the SUPER IDEA — the single coherent
change that takes what is right in each and puts it together.

The ideas, and what each concluded:

{findings}

Write one solution skill named `{skill}` describing the combined change.

The ideas above are STEPS of a method, not rival guesses at the whole fix — see
[[phronix-research-plan]] `I5b`. Each explored step has one or more ways of being
done. Your job is to ASSEMBLE them: choose the best-supported way for each step
and write the ordered result as one change.

This exists because a task is often not one bug. An attempt that adds a check in
one place can be correct and still fail, because the same issue needed two more
sites changed; each step holds a piece and no single step holds the task.

How to assemble them:

1. Take every step that found a way to do it. A step whose finding was "there is
   nothing to do here" contributes nothing — say so and leave it out, rather than
   padding the skill with it. A step that found NO way is a hole: name it, because
   a method with a hole is what an attempt will fall into.
2. Where two ideas touch the same code, reconcile them into ONE change. Two edits
   to the same function are a conflict to resolve now, not two steps for the
   attempt to discover.
3. Where they touch different code, order them so the result is coherent: the
   shared helper first, then its callers.
4. Say what the assembled method achieves that no single step does, and in what
   ORDER the steps must be carried out. If the steps turn out not to compose —
   two of them are the same edit, or one contradicts another — say so plainly and
   write the skill for the strongest one alone, with the reason the others did
   not join it.

Be specific: files, functions, line numbers, the actual edit, the exact exception
type or return value. This skill is handed to an agent that will implement it
without seeing any of the exploring, and it may be a smaller model than you —
see [[phronix-skill-authoring]] `R0c` for what that demands.
"""

    SOLUTION_SKILL_PROMPT = """\
Write the solution skill for ONE approach.
`skill_load("phronix-solution-candidate")` is your first action and the skill is
the method; this message is only the input. Do not edit source files.

Topic key: `{topic}`
Approach: **{name}**

{summary}

Write it with `skill_write` under exactly this name, which is not yours to vary:

    {skill}
"""

    TRIAL_RECONCILE_PROMPT = """\
Several approaches were tried against the task's real tests.
`skill_load("phronix-trial-reconcile")` is your first action and the skill is the
method; this message is only the results. Do not edit source files.

Topic key: `{topic}`

{results}

Each candidate's own skill is what its attempt actually followed — load them by
name, and link every one of them from what you write (`R2b`):

{skills}
"""

    #: Pinned to one plan, so parallel trials differ by approach rather than by
    #: sampling. Without this each trial is the same prompt at temperature 0.7
    #: and the fleet spends N times to explore one idea.
    PLAN_NOTE = """\

## Follow THIS plan, not another

Research measured several approaches and ranked them. You are implementing one
specific candidate, and other agents are implementing the others at the same
time — so do not weigh it against alternatives or pick what seems best. Your job
is to give this one its fairest possible attempt.

**{name}**

{summary}

If it turns out to be wrong, say so plainly in your final message rather than
quietly switching to a different idea: a candidate that fails cleanly is worth
more than one that was never really tried.
"""

    #: The plan as something executable, written by research one skill per
    #: candidate. Appended only when that skill exists: pointing an attempt at
    #: a skill nobody wrote costs it the steps it takes to find that out.
    PLAN_SKILL_NOTE = """\
`skill_load("{skill}")` before you touch anything. Research wrote this plan up as
that skill — the steps, the tool for each one, and what proves each step worked.
It is the plan itself, not background reading.
"""

    def solution_skill_path(self, store_root: Path, topic: str) -> str:
        """The file `reconcile_trials` wrote the merged solution into, if any.

        Reported with the result because it is what somebody opens: the verdict
        says a task passed, and this says where the fix that passed it — and
        the lessons from the candidates that did not — were written down.

        Best effort by design. Reconciliation is bookkeeping over work already
        done, and a missing skill must not turn a measured result into an error.
        """
        from phronix import research as research_mod

        def slug(text: str) -> str:
            return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")

        name = f"solution-{slug(research_mod.resolve_topic(topic))}"
        path = Path(store_root) / "skills" / name / "SKILL.md"
        if path.is_file():
            return str(path)
        # The subject's own skill, when the merge wrote there instead — which
        # is what `phronix-trial-reconcile` asks for when one already exists.
        subject = Path(store_root) / "skills" / slug(
            research_mod.resolve_topic(topic)) / "SKILL.md"
        return str(subject) if subject.is_file() else ""

    def best_skill_for(self, store_root: Path, topic: str) -> str:
        """The skill a task should open with: the merged solution, or the topic's.

        `solution-<topic>` is what `reconcile_trials` writes — the answer plus a
        link to every candidate that was tried. The research record's own
        `topic_skill` predates it and points at the subject skill, so a task
        whose answer had already been merged was handed the older, vaguer one.
        Prefer the merged solution when it is there; fall back otherwise.
        """
        from phronix import research as research_mod

        def slug(text: str) -> str:
            return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")

        here = slug(research_mod.resolve_topic(topic))
        # Two homes: the framework's method in `skills/`, a problem's ANSWER
        # under `capabilities/skills/<TaskName>/`. A solution is an answer, so
        # this reads both rather than assuming the store it used to live in.
        #
        # `capabilities/tasks/<slug>/<name>/` is the pre-flattening layout and
        # is still read: a carry root of 348 answers is not worth invalidating
        # over a directory rename.
        capabilities = Path(store_root) / "capabilities"
        roots = [Path(store_root) / "skills", capabilities / "skills"]
        roots += sorted(d for d in (capabilities / "tasks").glob("*")
                        if d.is_dir())

        def on_disk(name: str) -> bool:
            return bool(name) and any((root / name / "SKILL.md").is_file()
                                      for root in roots)

        # 1. The task's OWN skill. One task, one skill, named after the task.
        #
        # Checked before anything else because it is what the tracked loop
        # writes — research updates it between attempts and the snapshot closes
        # it out — so it is both the most current and the only one guaranteed
        # to exist by convention rather than by a pass having happened to run.
        if on_disk(here):
            return here

        # 2. The merged solution from the parallel pipeline, when that ran.
        merged = f"solution-{here}"
        if on_disk(merged):
            return merged

        # 3. What the record points at — only useful once a record exists.
        named = self._in_store(store_root, research_mod.topic_skill, topic) or ""
        if named:
            return named

        # 4. THE CANDIDATES, found by NAME.
        #
        # Steps 1 and 2 both depend on a research record, and a record does not
        # survive a run unless its session was folded into the common folder.
        # So a reusing run could hold the skill for its exact task and still
        # report "no skill covers this task" — measured: `pallets__flask-4045`
        # was SOLVED, `skills/pallets-flask-4045/` was carried into the project
        # layer, and the next run opened from scratch and then recalled
        # `flask-routes-subdomain-display`, which belongs to a different bug.
        #
        # The naming convention is the system's own claim of ownership and it
        # needs no record: `candidate_skill_name` derives `solution-<topic>-
        # <plan>` precisely so several writers and a reader can agree. Reading
        # it back is deterministic, not a fuzzy name match.
        candidates = sorted(
            {d.name for root in roots for d in root.glob(f"solution-{here}-*")
             if d.is_dir() and (d / "SKILL.md").is_file()})
        if candidates:
            return candidates[0]
        return here if on_disk(here) else ""

    @staticmethod
    def candidate_skill_name(topic: str, plan: str) -> str:
        """The skill one candidate's write-up goes to, and its racer loads.

        Derived rather than chosen, because three separate agents write these
        and a fourth has to find them. An author picking the name means the
        racer cannot be told it in advance, and the reconcile pass cannot list
        what it is merging.
        """
        from phronix import research as research_mod

        def slug(text: str) -> str:
            return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")

        return f"solution-{slug(research_mod.resolve_topic(topic))}-{slug(plan)}"

    @staticmethod
    def _covered_aspects(topic: str) -> set:
        """Aspects that have already produced an approach."""
        from phronix import research

        record = research.load(research.resolve_topic(topic)) or {}
        return {a.get("aspect") for a in record.get("approaches", []) if a.get("aspect")}

    @staticmethod
    def overlapping_ideas(ideas: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """Ideas that would be investigated in the same place, grouped by place.

        Independence is what makes several ideas worth exploring: three readings
        of one function are one reading with three names, and the combination
        built from them is a no-op.

        Measured on `pylint-dev__pylint-7114`. Four ideas —
        `module-name-conflict-resolution`, `init-file-fallback`,
        `module-search-order`, `expand_modules` — plus the super idea built from
        them, and every patch changed `get_python_path` in
        `pylint/lint/expand_modules.py`. Three tries, five containers each,
        every candidate scoring 0, and the super idea's diff was the original
        loop rewritten. The names differed; the target did not.

        Judged on `where`, which the plan is asked to state and `explore` already
        passes through. An idea with no `where` is counted as its own island: the
        remedy for that is to ask for one, not to guess.
        """
        seen: Dict[str, List[str]] = {}
        for idea in ideas:
            # `where` for a step, `summary`/`hypothesis` for a way of doing one:
            # the same question — would these be carried out in the same place —
            # asked of both, so one rule covers steps and the ways within a step.
            where = str(idea.get("where")
                        or idea.get("summary")
                        or idea.get("hypothesis") or "").strip().lower()
            if not where:
                continue
            # The FILE is the unit of overlap, not the whole phrase: "line 40 of
            # expand_modules.py" and "get_python_path in expand_modules.py" are
            # the same place described twice.
            for token in re.findall(r"[\w./-]+\.py\b", where) or [where]:
                seen.setdefault(token, []).append(str(idea.get("name") or "?"))
        return {place: names for place, names in seen.items() if len(names) > 1}

    #: Idea names that are bookkeeping rather than ideas.
    #
    # The planner is shown what the record already holds so it does not repeat
    # itself, and it reads back whatever is in there — including entries nothing
    # ever proposed. Measured on `pylint-dev__pylint-7114` try 3:
    #
    #   5 idea(s): a_init_py, rename_a_py, super_idea, no_files_changed,
    #              pylint_auto_init_helper
    #
    # `super_idea` is the candidate the PREVIOUS try synthesised from all the
    # others, and `no_files_changed` is the ledger's note that an attempt changed
    # nothing. Exploring either spends a worktree and a clock on a word, and the
    # combination is rebuilt from whatever the real ideas find anyway.
    SYNTHETIC_IDEAS = ("super-idea", "super_idea", "superidea",
                       "no-files-changed", "no_files_changed",
                       "(no files changed)")

    @classmethod
    def _is_synthetic_idea(cls, name: str) -> bool:
        flat = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
        if flat in {re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
                    for n in cls.SYNTHETIC_IDEAS}:
            return True
        # A name that is a path is a file list, however it got recorded.
        return name.endswith(".py") or "/" in name

    @classmethod
    def _load_aspects(cls, topic: str) -> List[Dict[str, str]]:
        from phronix import research

        aspects = (research.load(research.resolve_topic(topic))
                   or {}).get("aspects", [])
        return [a for a in aspects
                if not cls._is_synthetic_idea(str(a.get("name") or ""))]

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
            isolated_env(store_root, workdir / "learner-cache", fresh=self.fresh)))
        env.update(model_env(base_url=self.base_url, api_key=self.api_key))
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
                            self.LEARNING_BUDGET,
                            host=self.agent_host)
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
                    with task_pool(len(groups)) as pool:
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
        # And the raw exchange beside it, for the plan stage to summarise.
        self.write_exchange(workdir, verdict, outcome.patch or "")

        self.research_topic_binding = self.research_topic(instance)
        env = self.phronix_env(tool_path_env(isolated_env(store_root, workdir / "cache", fresh=self.fresh)))
        env.update(model_env(base_url=self.base_url, api_key=self.api_key))
        env["PHRONIX_WRITE_LAYER"] = "project"
        # The post-attempt harvest, which reads to write rather than to solve.
        env["PHRONIX_PHASE"] = "learn"
        if self.store_readonly:
            env["PHRONIX_BENCH_FROZEN"] = "1"

        # The name the pre-attempt lookup will search for, computed here so the
        # writer and the reader cannot disagree about it.
        topic = self.research_topic(instance)
        solution = self.task_skill_name(topic)
        command = self.agent_command(
            self.LEARN_PROMPT.format(topic="{topic}", solution=solution),
            checkout,
            # The evaluation's own output too, not just the harness's digest
            # of it. `exchange.md` carries what the tests actually printed —
            # the assertion, the traceback — which is where the reason a change
            # failed is written down. Learning from the verdict alone produces
            # "it did not pass"; learning from the output produces "it did not
            # fire for the path the test uses".
            self.attachments([f for f in (diff_file, notes_file,
                                          workdir / "exchange.md")
                              if Path(f).is_file()]),
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

        # A solved task must leave something the NEXT run can look up.
        #
        # The prompt has always said "if the attempt passed, the main thing to
        # write is the solution", and instruction alone has not been enough:
        # measured on django-13551, the attempt passed 2 of 2, the learner
        # wrote a memory holding the correct fix and the corner case that broke
        # the earlier version, and no skill — so `best_skill_for` found nothing
        # and the store's own record of a solved task was invisible to the one
        # mechanism that asks for it.
        #
        # Checked rather than trusted, and only on a PASS: a failed attempt has
        # no solution to file, and demanding one would invent it.
        if (verdict or {}).get("resolved") and not self.best_skill_for(
                store_root, self.research_topic(instance)):
            self._write_solution_skill(instance, store_root, workdir,
                                       solution, outcome, run_env, checkout)

    def _write_solution_skill(self, instance: Dict[str, Any], store_root: Path,
                              workdir: Path, solution: str,
                              outcome: AttemptOutcome, run_env: Dict[str, str],
                              checkout: Path) -> None:
        """Ask, once, for the skill a solved task owes the next run.

        Runs as the FILER: it can read the evidence and write a skill, and it
        cannot edit the repository, run anything, or delegate. The task is
        already solved — there is nothing left for this pass to do except file
        what solved it, and every earlier attempt to secure that by asking
        politely was answered by an agent going off to do something else.
        """
        prompt = self.SOLUTION_SKILL_FROM_PASS_PROMPT.format(
            topic="{topic}", solution=solution)
        command = self.agent_command(
            prompt, checkout,
            [str(workdir / name) for name in
             ("attempt-diff.patch", "attempt-notes.md", "exchange.md")
             if (workdir / name).is_file()],
            agent=self.filer_agent_name)
        # Imported HERE for the same reason it is in the other stage runners:
        # the module-level name is not in scope in this file.
        import subprocess

        try:
            result = subprocess.run(command, cwd=checkout, env=run_env,
                                    capture_output=True, text=True,
                                    timeout=self.FINALIZE_BUDGET_S)
        except OSError:                   # a missing skill is not a failed task
            return
        except subprocess.SubprocessError:
            return
        wrote = self.parse_events(result.stdout, AttemptOutcome())
        outcome.tokens_learn += wrote.tokens_total
        outcome.cost_usd += wrote.cost_usd
        outcome.raw.setdefault("learn", {})["solution_skill"] = (
            solution if self.best_skill_for(
                store_root, self.research_topic(instance)) else "")

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

            # The patch itself, which is the one artifact the rest of this
            # cannot substitute for.
            #
            # Without it the planner reads a claim ("Implemented the fix for
            # handling dimensionless exponents") and a verdict (target 0/1) and
            # has to infer what was actually changed from the two. The diff is
            # the only place the attempt's real reading of the problem is
            # written down: which file, which branch, which condition. A plan
            # built without it re-proposes the change that just failed, because
            # nothing told it what that change was.
            patch = ""
            try:
                candidate = Path(workdir) / "patch.diff"
                if candidate.is_file():
                    patch = candidate.read_text(errors="replace").strip()
            except OSError:
                patch = ""
            if patch:
                parts += ["", "### The change that was tried", "",
                          "```diff", patch[:6000], "```"]
                if len(patch) > 6000:
                    parts.append(f"(diff truncated at 6000 of {len(patch)} "
                                 f"characters)")
            elif not verdict.get("error"):
                # An empty diff with no harness error means the agent changed
                # nothing — a different failure from a wrong change, and the
                # plan should not treat it as one.
                parts += ["", "### The change that was tried", "",
                          "**Nothing was changed.** The attempt produced an "
                          "empty diff, so the tests below judged the original "
                          "code. Whatever the plan proposes, the first problem "
                          "is that no edit was made."]

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
    """Resolve the Claude Code executable. A STABLE path, and one that exists.

    PATH first. The extension's copy was preferred because there was no other
    install, and it moves: VS Code updates the extension in place and deletes
    the old directory, so a path resolved a minute ago can be gone. Measured
    live — the harness had baked
    `anthropic.claude-code-2.1.246-.../native-binary/claude` into its command,
    the extension became 2.1.247 mid-run, and every stage that started
    afterwards died instantly with `exited rc=127`, which names neither the
    binary nor the version and reads like a broken agent.

    The glob remains as a fallback, and every candidate is now checked to be
    an executable FILE rather than merely a matching name — the directory
    survived the update that removed the binary inside it, so the glob still
    matched.
    """
    import glob
    import shutil

    on_path = shutil.which("claude")
    if on_path:
        return on_path
    for match in sorted(glob.glob(os.path.expanduser(CLAUDE_BIN_GLOB)),
                        reverse=True):
        if os.path.isfile(match) and os.access(match, os.X_OK):
            return match
    return "claude"


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
    harness_name = "claude"

    #: Low by default. The benchmark measures whether research changes the
    #: outcome; paying for extended reasoning on every call would confound that
    #: with a second variable and cost several times as much.
    effort = "low"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("opencode_bin", find_claude_bin())
        super().__init__(*args, **kwargs)

    def phronix_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """Point Claude Code at a self-hosted endpoint, when there is one.

        Claude Code speaks the Anthropic wire format and reads a different set
        of variables than the OpenAI-compatible arms — pointing it at a cluster
        by setting ``OPENAI_BASE_URL`` does nothing at all, which is the kind of
        misconfiguration that looks like a working run against the wrong model.

        ``ANTHROPIC_BASE_URL`` wants the server ROOT: Claude Code appends
        ``/v1/messages`` itself, so passing the ``/v1`` we use for the OpenAI
        arms would produce ``/v1/v1/messages``. The gateway in front of the
        cluster is what translates between the two formats; a bare llama.cpp
        server does not speak Anthropic, so a direct backend URL will not work
        here even though it works for opencode.

        Left alone when the endpoint IS Anthropic, so ordinary Claude runs keep
        their normal credentials and routing.
        """
        env = super().phronix_env(env)

        # Redirect only when this run actually chose another endpoint.
        #
        # Gated on the PROVIDER, not on the URL. `base_url` defaults to the
        # livai gateway whatever the provider is, so a `--provider anthropic`
        # run was being pointed at livai — with no credential for it — and
        # every call came back 401 Authentication Error. The URL cannot answer
        # "was this chosen or inherited"; the provider can.
        if str(self.provider or "").lower() in ("anthropic", "", "claude"):
            return env

        base = str(self.base_url or "")
        if not base or "anthropic.com" in base:
            return env

        root = base.rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3].rstrip("/")
        env["ANTHROPIC_BASE_URL"] = root
        if self.api_key:
            # Both spellings: the CLI has moved between them across versions and
            # the wrong one fails as an auth error rather than as a config one.
            env["ANTHROPIC_AUTH_TOKEN"] = self.api_key
            env["ANTHROPIC_API_KEY"] = self.api_key
        # `pinned_for_env` is set per task before the agent runs, so the CLI
        # asks for the alias that resolves to one backend rather than the shared
        # name that load-balances across all of them.
        wanted = getattr(self, "pinned_for_env", "") or self.model
        env["ANTHROPIC_MODEL"] = wanted
        env["ANTHROPIC_SMALL_FAST_MODEL"] = wanted
        return env

    #: Compact at this many tokens when talking to a gateway model.
    #:
    #: The floor the CLI accepts is 100k and the models served here are trained
    #: to 131072, so this leaves room for the turn that triggers it.
    autocompact_tokens: int = int(_tuned("agent.autocompact_tokens", 100000))

    def _is_redirected(self) -> bool:
        """Is this talking to our own gateway rather than to Anthropic?

        The same test `phronix_env` uses to decide whether to override
        `ANTHROPIC_BASE_URL`, and for the same reason: the provider says
        whether an endpoint was CHOSEN, while the URL cannot.
        """
        if str(self.provider or "").lower() in ("anthropic", "", "claude"):
            return False
        base = str(self.base_url or "")
        return bool(base) and "anthropic.com" not in base

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
                      agent: str = "", model: str = "") -> List[str]:
        """Claude Code's argv. *model* overrides which model answers.

        The parameter exists on the base class so a stage can be asked of a
        different model, and an override that drops it is a TypeError at the
        first research stage — "takes from 4 to 5 positional arguments but 6
        were given" — which surfaces as a research pass that produced nothing.
        """
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
                   "--model", model or self.qualified_model]
        if self.effort:
            command += ["--effort", self.effort]
        # Compact before the window ends, rather than dying at it.
        #
        # Left to itself the CLI sizes its auto-compaction to the model's
        # ADVERTISED context, and it has no way to know what a gateway model's
        # really is: `gpt-oss-120b` is not a name it ships a limit for. So it
        # never compacted, and an agent that kept exploring simply hit the
        # wall — measured on sphinx-10451, 215 steps in one attempt and then
        # `400 ContextWindowExceededError`, the whole try lost with no patch
        # and no usable transcript. Eight of one run's nineteen pipeline
        # faults were this.
        #
        # Only for a REDIRECTED endpoint. Against real Anthropic models the
        # default knows better than this number does, and forcing it would
        # compact a 200k window at half its size.
        if self._is_redirected() and self.autocompact_tokens:
            command += ["--autocompact", str(self.autocompact_tokens)]
        command += self._denial_flags(agent)
        if agent:
            # The agent's REAL definition, not just its name.
            #
            # This passed `{"description": agent}` and nothing else, so Claude
            # Code received an agent with a description and default tools — and
            # the rendered definition, with its tool list and its system
            # prompt, was never read. The restriction existed in a file nobody
            # passed.
            #
            # Measured: `phronix-validator` declares no Read, Edit or Bash and
            # is told "judging is not investigating"; it read and edited files
            # 67 times in one run, because it had every tool the default agent
            # has.
            command += self._agent_flags(agent)
        return command

    def _agent_flags(self, agent: str) -> List[str]:
        """`--agents` with the real definition, and `--disallowedTools`.

        Two flags, because they do different jobs and only together restrict
        anything. `--agents {... "tools": [...]}` says which MCP tools the
        agent may reach; it does NOT take the built-in tools away. Measured
        after passing the full definition: `phronix-validator`, which declares
        only phronix tools and is told "judging is not investigating", still
        read and edited files 18 times.

        `--disallowedTools` is what removes them. An agent that declares no
        built-in tools should not have any.
        """
        spec = self._agent_spec(agent)
        flags = ["--agents", json.dumps({agent: spec})]
        wanted = spec.get("tools") or []
        # Merged into ONE `--disallowedTools`, never two.
        #
        # The base argv already denies the tools whose schema breaks a llama.cpp
        # grammar; a second flag here would be the one Claude Code keeps, and
        # those two tools would come back for exactly the restricted agents that
        # run most of the research.
        # No `--disallowedTools` here: `agent_command` emits one merged flag,
        # because a second would be the one Claude Code keeps.
        return flags

    def _denial_flags(self, agent: str = "") -> List[str]:
        """ONE `--disallowedTools`, built from both reasons to deny a tool.

        Two flags would mean Claude Code keeps the last, and the
        schema-breaking tools would come back for exactly the restricted agents
        that run most of the research.

        Shared by both Claude arms. Putting it in one of them left the other
        sending `Artifact` and `RemoteTrigger` — and since the server rejects the
        WHOLE request when they are present, that arm failed every call.
        """
        denied = list(self.SCHEMA_BREAKING_TOOLS)
        if agent:
            wanted = self._agent_spec(agent).get("tools") or []
            if wanted:
                denied += [name for name in self.BUILT_IN_TOOLS
                           if name not in wanted]
        return ["--disallowedTools", ",".join(dict.fromkeys(denied))]

    #: Tools whose JSON Schema llama.cpp cannot compile into a grammar.
    #
    # The server rejects the WHOLE request — "Failed to initialize samplers:
    # failed to parse grammar" — so every call fails, not only one that would
    # have used them. Measured by replaying a captured request: 100 tools
    # failed, the same 100 without these two succeeded, and each failed alone.
    SCHEMA_BREAKING_TOOLS = ("Artifact", "RemoteTrigger")

    #: The built-in tools a restricted agent has to be denied by name.
    #
    # `Agent`/`Task` are on this list because delegation defeats every other
    # entry on it. A restricted agent that can spawn a sub-agent gets an
    # UNRESTRICTED one — the child is a fresh session with the default tool set,
    # so denying the parent Bash accomplishes nothing.
    #
    # Measured on django-13551: `plan-record` runs as the validator, which is
    # denied Bash precisely so the re-ask files its ideas instead of going off
    # to fix the code. The trace shows it running the Django token tests
    # anyway — "Background agent is running. I'll continue when it completes" —
    # because it delegated. The restriction was real and it was routed around.
    BUILT_IN_TOOLS = ("Bash", "Edit", "Write", "Read", "Grep", "Glob",
                      "NotebookEdit", "WebFetch", "WebSearch",
                      "Agent", "Task", "TaskOutput", "TaskStop")

    @staticmethod
    def _agent_spec(agent: str) -> Dict[str, Any]:
        """The rendered agent's description, tools and prompt.

        Read from the file the sync step writes, so there is one definition
        rather than a YAML template, a rendered file, and a third inline copy
        that quietly wins.
        """
        spec: Dict[str, Any] = {"description": agent}
        path = (Path("/usr/WS2/haridev/phronix/.claude/agents") /
                f"{agent}.md")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return spec
        if not text.startswith("---"):
            return spec
        head, _, body = text[3:].partition("\n---")
        # Parsed as YAML, because the renderer WRAPS long values.
        #
        # A line-by-line reader took `tools:` up to the first newline and got
        # three of the six — silently handing the agent half its tool list,
        # which is worse than none: it looks configured.
        try:
            import yaml

            front = yaml.safe_load(head) or {}
        except Exception:
            front = {}
        if isinstance(front, dict):
            if front.get("description"):
                spec["description"] = str(front["description"])
            tools = front.get("tools")
            if isinstance(tools, str):
                tools = [x.strip() for x in tools.split(",") if x.strip()]
            if tools:
                spec["tools"] = list(tools)
        if body.strip():
            spec["prompt"] = body.strip()
        return spec

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
                      agent: str = "", model: str = "") -> List[str]:
        command = ClaudeArm.agent_command(self, prompt, checkout, files,
                                          agent="", model=model)
        # The base builder emitted its own `--disallowedTools` for `agent=""`;
        # this one re-emits it with the agent's restrictions, and Claude Code
        # keeps the LAST flag. Drop the base pair so exactly one survives.
        if "--disallowedTools" in command:
            at = command.index("--disallowedTools")
            del command[at:at + 2]

        # The phronix MCP server, declared inline rather than written into the
        # checkout: a config file inside the repository would show up as an
        # untracked addition in the patch this arm is judged on.
        #
        # `-P` keeps the CHECKOUT off sys.path. The server is started with the repository
        # under test as its working directory, and python prepends the working
        # directory to sys.path — so on `psf__requests` the repo's own
        # `requests/` package shadowed the one fastmcp imports, `from fastmcp
        # import FastMCP` came back with no such name, and Claude Code recorded
        # `mcp_servers: [{"name": "phronix", "status": "failed"}]` and carried
        # on. The whole phronix arm then ran as a plain agent: no skill_search
        # (so "no skill covers this task" on every task), no research_* (so
        # every revision pass recorded 0 aspects and 0 approaches), and the
        # agent reporting it "couldn't find a capability_list command". Nothing
        # in the trace named the cause; the arm merely looked ineffective.
        config = {"mcpServers": {"phronix": {
            "command": sys.executable,
            "args": ["-P", "-m", "phronix.mcp_server"],
        }}}
        command += ["--mcp-config", json.dumps(config)]
        command += self._denial_flags(agent)

        if agent:
            # The same flags the plain Claude arm builds. This declared only a
            # description, so the phronix arm — the one that actually uses
            # `phronix-validator` — passed neither its tools nor its prompt,
            # and a fix applied to the other builder did nothing here.
            command += self._agent_flags(agent)
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
