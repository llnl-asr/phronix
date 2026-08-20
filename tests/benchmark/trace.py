"""A running account of what phronix actually did, while it is doing it.

The benchmark's summary answers "did it pass". This answers the question that
matters while a run is still going: *is the machinery working*. Those came apart
badly during development — a run reported plausible failures for hours while the
phronix arm was silently calling no phronix tools at all, and the summary could
not have shown it.

Two files per arm, written as events happen:

``trace.log``
    Human-readable, tail-able. One line per event, indented detail under it.

``trace.jsonl``
    The same events as records, for querying after the fact.

What is deliberately recorded:

* every **phronix tool call** the agent made, and every call that came back an
  error — a rejected write is the difference between "learning happened" and
  "learning was attempted", and only one of those is visible in a store listing;
* the **research record** after each pass: figure of merit, approaches, choice,
  plan size, corrector verdict;
* what each attempt **touched and scored**, and what the ledger has ruled out;
* what was **written to the store**, by block title rather than by count.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Tool-call outputs containing any of these are treated as failures worth
#: surfacing. MCP tools return their errors in the payload rather than by
#: raising, so a failed call is invisible unless the payload is inspected.
_ERROR_MARKERS = ('"status": "error"', '"status":"error"', "is not permitted",
                  "permission denied", "Error:")


def _guard(method):
    """Never let reporting break the run it reports on.

    Learned the hard way: a tracer that assumed a field was a list of dicts met
    a list of strings, raised, and the exception propagated out through the
    attempt loop. Two attempts were recorded as "0 steps, 0 tokens" — which
    reads exactly like an agent that ran and did nothing, so the real cause
    (a formatting bug in the log) was invisible in every artefact the run
    produced.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - deliberately total
            try:
                self.event("trace-bug", f"{method.__name__} failed: "
                                        f"{type(exc).__name__}: {exc}")
            except Exception:
                pass
            return None
    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    return wrapper


class Tracer:
    """Append-only trace for one arm of one run."""

    def __init__(self, directory: Path, arm: str, echo: bool = True) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.arm = arm
        self.echo = echo
        self.text_path = self.dir / "trace.log"
        self.json_path = self.dir / "trace.jsonl"
        self._started = time.time()

    # -- writing -----------------------------------------------------------

    def event(self, kind: str, summary: str, detail: Optional[List[str]] = None,
              data: Optional[Dict[str, Any]] = None) -> None:
        stamp = time.strftime("%H:%M:%S")
        # The pid is in every line because two runner processes once wrote into
        # the same trace and it read as one run restarting itself. Cheap to
        # carry, and it turns "why did this happen twice" into a glance.
        line = f"{stamp} [{self.arm}:{os.getpid()}] {kind:<12} {summary}"
        lines = [line] + [f"{'':>9} {'':<12}   {d}" for d in (detail or [])]
        blob = "\n".join(lines) + "\n"
        try:
            with self.text_path.open("a", encoding="utf-8") as handle:
                handle.write(blob)
            with self.json_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "at": time.time(), "arm": self.arm, "pid": os.getpid(),
                    "kind": kind,
                    "summary": summary, "detail": detail or [],
                    **(data or {})}) + "\n")
        except OSError:
            pass  # tracing must never break the run it observes
        if self.echo:
            print(blob, end="", flush=True)

    # -- specific events ---------------------------------------------------

    @_guard
    def task_start(self, order: int, instance_id: str) -> None:
        self.event("task", f"[{order:3d}] {instance_id}")

    @_guard
    def begin(self, kind: str, summary: str, budget_s: Optional[int] = None) -> None:
        """Announce a long step as it starts, not only when it ends.

        Every other event here is written on completion, which is correct for
        recording what happened and useless for watching it happen: a research
        pass can run for seven minutes, and a log that stays silent for seven
        minutes is indistinguishable from one whose process has died. The budget
        is included so the reader knows how long silence is still normal.
        """
        detail = [f"budget {budget_s}s"] if budget_s else []
        self.event(f"{kind}>", summary, detail)

    @_guard
    def step(self, phase: str, text: str) -> None:
        """A single action an agent just took. The running commentary."""
        self.event(f"{phase}·", text)

    @_guard
    def research(self, attempt: int, result: Dict[str, Any]) -> None:
        """One progress line for the pass, plus a line only when something is off.

        Dense rather than complete. The full record is on disk as JSON; what a
        reader following a live run needs is whether this pass did something
        sensible, and that fits on a line: the criterion, how many real
        alternatives it weighed, what it picked, how the plan splits, and whether
        the corrector accepted it.

        The extra lines are exception-driven — no metrics, nothing chosen, a
        failing facet, no tools called. In a healthy pass there are none, so
        anything indented is worth reading.
        """
        record = result.get("record") or {}
        kind = result.get("kind", "initial")
        if result.get("returncode") not in (0, None):
            self.event("research", f"try{attempt} {kind}: FAILED "
                                   f"rc={result.get('returncode')} "
                                   f"[{result.get('elapsed_s')}s]", [], result)
            return

        approaches = record.get("approaches") or []
        plan = record.get("plan") or []
        deterministic = sum(1 for s in plan if s.get("kind") == "deterministic")
        fom = record.get("fom") or {}
        fom_bit = (f"{fom.get('name')}({fom.get('direction')},{fom.get('target'):g})"
                   if fom else "NONE")
        chosen = record.get("chosen") or "-"
        value = record.get("chosen_value")
        chosen_bit = f"{chosen}" + (f"={value:g}" if isinstance(value, (int, float)) else "")

        summary = (f"try{attempt} {kind}: fom={fom_bit} approaches={len(approaches)} "
                   f"chose={chosen_bit} plan={len(plan)}"
                   f"({deterministic}det/{len(plan) - deterministic}judge) "
                   f"verify={record.get('verdict') or '-'} [{result.get('elapsed_s')}s]")

        # Only what is wrong, or newly ruled out.
        detail: List[str] = []
        if not fom:
            detail.append("no figure of merit declared — nothing can be compared")
        unmeasured = [a["name"] for a in approaches
                      if isinstance(a, dict) and not a.get("metrics")]
        if unmeasured:
            detail.append(f"no metrics on: {', '.join(unmeasured[:3])}")
        if approaches and not record.get("chosen"):
            detail.append("no approach selected")
        for name, verdict in (record.get("facets") or {}).items():
            if verdict != "pass":
                reason = (record.get("facet_detail") or {}).get(name, "")
                detail.append(f"{name} {verdict}: {reason[:90]}")
        for entry in (record.get("ruled_out") or [])[:2]:
            detail.append(f"ruled out {', '.join(entry['locations'])} "
                          f"after {entry['attempts']} attempt(s)")
        if not (result.get("calls") or {}):
            detail.append("called no research tools")

        self.event("research", summary, detail, result)

    @_guard
    def attempt(self, attempt: int, files: List[str], verdict: Dict[str, Any],
                steps: int, tokens: int,
                previous: Optional[Dict[str, Any]] = None) -> None:
        """How the attempt was judged, and whether it beat the one before it.

        The absolute numbers alone do not answer the question a retry exists to
        ask. "0 of 1 target tests" on attempt 3 reads the same as on attempt 1,
        while "0/1 and 3 regressions" improving to "0/1 and 0 regressions" is
        real movement toward a fix, and "1/1 target but 2 new regressions" is a
        different failure from the one before. Retrying without knowing which of
        those happened is how a run spends six attempts going sideways.
        """
        resolved = bool(verdict.get("resolved"))
        target_passed = verdict.get("fail_to_pass_passed")
        target_total = verdict.get("fail_to_pass_total")
        # The DISCOUNTED count, matching the verdict line.
        #
        # Deriving it from pass_to_pass totals counts tests that were already
        # failing before the agent touched anything, so a clean pass reported
        # "regressions 1" on the same task the verdict line called "regressions
        # 0, 1 pre-existing failure(s) discounted". Two lines about one result,
        # disagreeing, and the pessimistic one is the one that looks like a
        # defect in the patch.
        regressions = len(verdict.get("regressions") or [])
        discounted = len(verdict.get("pre_existing_failures") or [])

        detail = [f"changed: {', '.join(files) if files else '(nothing)'}"]
        if target_total is not None:
            detail.append(f"target tests {target_passed}/{target_total}, "
                          f"regressions {regressions}"
                          + (f" ({discounted} pre-existing discounted)"
                             if discounted else ""))

        # The comparison, stated plainly.
        if previous and previous.get("fail_to_pass_total") is not None:
            was_target = previous.get("fail_to_pass_passed") or 0
            was_regressions = len(previous.get("regressions") or [])
            # Two axes, each scored so that +1 always means "improved": more
            # target tests passing is better, FEWER regressions is better. A
            # single combined comparison gets this wrong in both directions —
            # an attempt that fixed three regressions while the target stayed
            # failing is real progress, and one that fixed the target while
            # breaking two other tests is not simply "worse", it is a trade.
            target_delta = (target_passed or 0) - was_target
            regression_delta = regressions - was_regressions
            target_axis = (target_delta > 0) - (target_delta < 0)
            regression_axis = (was_regressions > regressions) - (was_regressions < regressions)

            if target_axis == 0 and regression_axis == 0:
                verdict_word = "no change"
            elif target_axis >= 0 and regression_axis >= 0:
                verdict_word = "BETTER"
            elif target_axis <= 0 and regression_axis <= 0:
                verdict_word = "WORSE"
            else:
                verdict_word = "mixed"
            detail.append(
                f"vs try {attempt - 1}: {verdict_word} "
                f"(target {was_target}->{target_passed or 0}, "
                f"regressions {was_regressions}->{regressions})")

        for name in (verdict.get("fail_to_pass_failing") or [])[:3]:
            detail.append(f"still failing: {name}")
        for name in (verdict.get("regressions") or [])[:3]:
            detail.append(f"broke: {name}")
        if verdict.get("error"):
            detail.append(f"error: {str(verdict['error'])[:120]}")

        self.event("attempt",
                   f"try {attempt}: {'PASS' if resolved else 'fail'} "
                   f"({steps} steps, {tokens:,} tok)", detail,
                   {"attempt": attempt, "resolved": resolved,
                    "target_passed": target_passed, "regressions": regressions})

    @_guard
    def tools(self, phase: str, transcript: Path) -> None:
        """Mine a transcript for phronix tool calls and their failures."""
        counts, errors = _mine(transcript)
        if not counts:
            self.event("tools", f"{phase}: no phronix tools called",
                       ["this is the failure mode that hid for hours — the server "
                        "was connected and nothing used it"], {"phase": phase})
            return
        detail = [", ".join(f"{k}x{v}" for k, v in sorted(counts.items()))]
        for err in errors[:4]:
            detail.append(f"REJECTED {err}")
        self.event("tools", f"{phase}: {sum(counts.values())} phronix call(s), "
                            f"{len(errors)} rejected", detail,
                   {"phase": phase, "counts": counts, "errors": errors[:10]})

    @_guard
    def learned(self, created: List[str], store_root: Path) -> None:
        if not created:
            self.event("learned", "nothing written to the store")
            return
        detail: List[str] = []
        for name in created[:4]:
            for filename in ("SKILL.md", "LESSONS.md"):
                path = Path(store_root) / "skills" / name / filename
                if not path.is_file():
                    continue
                text = path.read_text(errors="replace")
                titles = [ln[4:].strip() for ln in text.splitlines()
                          if ln.startswith("### ")]
                for title in titles[:4]:
                    detail.append(f"{name}/{filename[:-3].lower()}: {title[:80]}")
        self.event("learned", f"{len(created)} skill(s): {', '.join(created)}",
                   detail, {"created": created})

    @_guard
    def retrievals(self, path: Path) -> None:
        """What was searched for, and what came back — including empty hits."""
        if not Path(path).is_file():
            return
        rows = []
        for line in Path(path).read_text(errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if not rows:
            self.event("retrieval", "no searches recorded")
            return
        empty = sum(1 for r in rows if not r.get("skills"))
        detail = [f"{r.get('kind')}: {str(r.get('query'))[:60]} -> "
                  f"{', '.join(r.get('skills') or []) or '(nothing)'}"
                  for r in rows[-4:]]
        self.event("retrieval",
                   f"{len(rows)} search(es), {empty} returned nothing", detail)


def _mine(transcript: Path) -> Any:
    """Phronix tool counts and rejected-call summaries, from either harness.

    The two stream shapes disagree, and reading only opencode's meant every
    Claude attempt and learning pass reported "no phronix tools called" — the
    message that exists to announce an agent which never started. Announced on
    healthy passes, it trains the reader to ignore the one alarm that matters.

    Claude splits a call across two events: the `tool_use` block in an assistant
    message carries the name, and a later `tool_result` in a user message
    carries the output, joined by `tool_use_id`.
    """
    counts: Dict[str, int] = {}
    errors: List[str] = []
    path = Path(transcript)
    if not path.is_file():
        return counts, errors

    def note(tool: str, output: str) -> None:
        if "phronix" not in tool:
            return
        counts[tool] = counts.get(tool, 0) + 1
        if any(marker in output for marker in _ERROR_MARKERS):
            errors.append(f"{tool}: {output.replace(chr(10), ' ')[:150]}")

    pending: Dict[str, str] = {}          # tool_use_id -> tool name
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        part = event.get("part")
        if isinstance(part, dict) and part.get("type") == "tool":
            note(str(part.get("tool") or ""),
                 str((part.get("state") or {}).get("output") or ""))
            continue

        for block in ((event.get("message") or {}).get("content") or []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                pending[str(block.get("id") or "")] = str(block.get("name") or "")
            elif block.get("type") == "tool_result":
                tool = pending.pop(str(block.get("tool_use_id") or ""), "")
                content = block.get("content")
                if isinstance(content, list):
                    content = " ".join(str(c.get("text", "")) for c in content
                                       if isinstance(c, dict))
                note(tool, str(content or ""))

    # Calls whose result never arrived still happened.
    for tool in pending.values():
        note(tool, "")
    return counts, errors
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part") or {}
        if not isinstance(part, dict) or part.get("type") != "tool":
            continue
        tool = str(part.get("tool") or "")
        if "phronix" not in tool:
            continue
        counts[tool] = counts.get(tool, 0) + 1
        output = str((part.get("state") or {}).get("output") or "")
        if any(marker in output for marker in _ERROR_MARKERS):
            reason = output.replace("\n", " ")[:150]
            errors.append(f"{tool}: {reason}")
    return counts, errors
