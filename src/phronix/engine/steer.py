"""Steering a running agent while one of its tools runs.

A web UI hands the user's "steer" message to its running Claude Code turn on stdin, and Claude Code reads it between
tool calls. A tool that runs for minutes (a build, a run, a pipeline step) keeps the message waiting until it returns.
This module closes that gap for the tools of an MCP server built on it:

* The web UI's turn names a per-chat **inbox** in the agent's environment (:data:`ENV`, inherited by the MCP servers
  Claude Code starts) and :func:`post` appends each steer message to it.
* The MCP server runs every tool call through :func:`call`. With an inbox, the tool runs in a background thread while
  the call watches the inbox. When a message arrives the call **claims** it (exactly once, across concurrent calls and
  the web UI) and returns at once: the tool keeps running, and the agent gets the message plus a ``call_id``.
  :func:`wait` (the server's ``tool_wait`` tool) later gives the tool's result.
* The web UI waits a moment for a claim (:func:`wait_claimed`). Unclaimed (no tool of ours was running), it withdraws
  the message (:func:`claim`) and writes it on stdin as before, so a message is delivered exactly once.

Without an inbox (no web UI) :func:`call` just calls the tool.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ENV = "PHRONIX_STEER_INBOX"
POLL_S = float(os.environ.get("PHRONIX_STEER_POLL_S", "0.25"))
KEEP_S = 6 * 3600                    # a background call's result is kept this long for tool_wait


# ------------------------------------------------------------------ the inbox (web UI side and tool side)
def inbox() -> Optional[Path]:
    v = os.environ.get(ENV, "").strip()
    return Path(v) if v else None


def _claim_file(ib: Path, mid: str) -> Path:
    return ib.with_name(f"{ib.name}.{mid}.claimed")


def reset(ib: Path) -> None:
    """Start a turn with an empty inbox (no claims left from an earlier one)."""
    ib.parent.mkdir(parents=True, exist_ok=True)
    for f in list(ib.parent.glob(f"{ib.name}.*.claimed")) + list(ib.parent.glob(f"{ib.name}.running.*")):
        with contextlib.suppress(OSError):
            f.unlink()
    with contextlib.suppress(OSError):
        ib.unlink()


def post(ib: Path, text: str) -> str:
    """Append a steer message; returns its id."""
    mid = uuid.uuid4().hex[:12]
    ib.parent.mkdir(parents=True, exist_ok=True)
    with open(ib, "a") as f:
        f.write(json.dumps({"id": mid, "ts": round(time.time(), 3), "text": text}) + "\n")
    return mid


def claim(ib: Path, mid: str) -> bool:
    """Take message ``mid`` (atomically: exactly one taker). False when someone else has it."""
    try:
        os.close(os.open(_claim_file(ib, mid), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except FileExistsError:
        return False


def claimed_by_tool(ib: Path, mid: str) -> bool:
    return _claim_file(ib, mid).exists()


def _running_marker(ib: Path, call_id: str) -> Path:
    return ib.with_name(f"{ib.name}.running.{os.getpid()}.{call_id}")


def tools_running(ib: Path) -> bool:
    """Whether a tool watching this inbox is running now (each running call leaves a marker beside the inbox)."""
    return any(ib.parent.glob(f"{ib.name}.running.*")) if ib.parent.is_dir() else False


def wait_claimed(ib: Path, mid: str, seconds: float = 1.5) -> bool:
    """Whether a running tool claimed message ``mid`` within ``seconds``; if not, the caller claims it back (so no tool
    takes it later) and returns False, and delivers it another way. No wait when no tool is running."""
    if not tools_running(ib):
        seconds = 0.0
    end = time.time() + seconds
    while time.time() < end:
        if claimed_by_tool(ib, mid):
            return True
        time.sleep(0.05)
    return not claim(ib, mid)           # lost the race to a tool at the last moment: the tool has it


def _size(ib: Optional[Path]) -> int:
    try:
        return ib.stat().st_size if ib else 0
    except OSError:
        return 0


def take_new(ib: Path, offset: int) -> (List[Dict[str, Any]], int):
    """Messages appended after byte ``offset`` that this caller could claim, and the new offset."""
    try:
        with open(ib) as f:
            f.seek(offset)
            data = f.read()
    except OSError:
        return [], offset
    if not data.endswith("\n"):                      # a line being written: read it next time
        data = data[:data.rfind("\n") + 1]
    out = []
    for line in data.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if claim(ib, m.get("id", "")):
            out.append(m)
    return out, offset + len(data.encode())


# ------------------------------------------------------------------ tool calls that can go to the background
class Call:
    def __init__(self, name: str, args: dict) -> None:
        self.id = "call-" + uuid.uuid4().hex[:10]
        self.name, self.args = name, args
        self.started = time.time()
        self.ended: Optional[float] = None
        self.done = threading.Event()
        self.result: Any = None
        self.error: Optional[BaseException] = None
        self.detached = False

    def outcome(self) -> Any:
        if self.error is not None:
            raise self.error
        return self.result

    def brief(self) -> Dict[str, Any]:
        return {"call_id": self.id, "tool": self.name, "running": not self.done.is_set(),
                "running_s": round((self.ended or time.time()) - self.started, 1),
                "args": {k: (v if len(str(v)) < 200 else str(v)[:200] + "…") for k, v in self.args.items()}}


_CALLS: Dict[str, Call] = {}
_LOCK = threading.Lock()


def busy() -> bool:
    """Whether a tool is still running in the background (a server must not reload or exit its code under it)."""
    with _LOCK:
        return any(not c.done.is_set() for c in _CALLS.values())


def _prune() -> None:
    now = time.time()
    with _LOCK:
        for k in [k for k, c in _CALLS.items() if c.done.is_set() and c.ended and now - c.ended > KEEP_S]:
            del _CALLS[k]


def _detached(c: Call, messages: List[Dict[str, Any]], wait_tool: str) -> Dict[str, Any]:
    c.detached = True
    return {"status": "still_running", **c.brief(),
            "user_messages": [m.get("text", "") for m in messages],
            "note": (f"The user sent the message(s) above while {c.name} was running. {c.name} was NOT stopped: it "
                     f"keeps running in the background. Read the message and act on it now. Call {wait_tool}"
                     f"(call_id=\"{c.id}\") when you need {c.name}'s result - before any step that depends on it or "
                     "works on the same campaign, run or files.")}


def _watch(c: Call, ib: Path, offset: int, timeout: Optional[float], wait_tool: str) -> Any:
    end = time.time() + timeout if timeout else None
    while True:
        if c.done.wait(POLL_S):
            with _LOCK:
                _CALLS.pop(c.id, None)
            return c.outcome()
        got, offset = take_new(ib, offset)
        if got:
            return _detached(c, got, wait_tool)
        if end and time.time() >= end:
            return {"status": "still_running", **c.brief(),
                    "note": f"still running after {timeout:.0f} s; call {wait_tool}(call_id=\"{c.id}\") again"}


def call(name: str, fn: Callable[..., Any], args: Optional[dict] = None, guard: Optional[Callable[[], Any]] = None,
         wait_tool: str = "tool_wait") -> Any:
    """Run tool ``fn(**args)``. With an inbox, a steer message arriving meanwhile returns at once (see the module
    docstring) while the tool goes on. ``guard()`` is a context manager held for the tool's whole run (e.g. a
    per-resource lock), also when it goes on in the background."""
    args = dict(args or {})
    ib = inbox()
    if ib is None:
        with (guard() if guard else contextlib.nullcontext()):
            return fn(**args)
    _prune()
    c = Call(name, args)
    offset = _size(ib)

    marker = _running_marker(ib, c.id)
    with contextlib.suppress(OSError):
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()

    def run():
        try:
            with (guard() if guard else contextlib.nullcontext()):
                c.result = fn(**args)
        except BaseException as e:      # noqa: BLE001 - handed to whoever collects the result
            c.error = e
        finally:
            c.ended = time.time()
            with contextlib.suppress(OSError):
                marker.unlink()
            c.done.set()

    with _LOCK:
        _CALLS[c.id] = c
    ctx = contextvars.copy_context()
    threading.Thread(target=ctx.run, args=(run,), daemon=True, name=f"tool-{name}").start()
    return _watch(c, ib, offset, None, wait_tool)


def wait(call_id: str, timeout_s: float = 600, wait_tool: str = "tool_wait") -> Any:
    """The result of a tool call that went on in the background: waits up to ``timeout_s`` (a new steer message returns
    early again). Raises the tool's own error, as the call would have."""
    with _LOCK:
        c = _CALLS.get(call_id)
    if c is None:
        return {"status": "error", "error": f"no background call {call_id} (finished results are kept "
                                            f"{KEEP_S // 3600} h and given once): see tool_calls"}
    ib = inbox()
    if ib is None:
        c.done.wait(timeout_s)
        if not c.done.is_set():
            return {"status": "still_running", **c.brief()}
        with _LOCK:
            _CALLS.pop(c.id, None)
        return c.outcome()
    return _watch(c, ib, _size(ib), float(timeout_s), wait_tool)


def calls() -> List[Dict[str, Any]]:
    """Tool calls that went on in the background: running, or finished with a result not yet collected."""
    with _LOCK:
        return [c.brief() for c in _CALLS.values() if c.detached]


WAIT_DESCRIPTION = ("Get the result of a tool call that went on in the background because the user sent a message "
                    "while it ran (its reply had status still_running and a call_id). Waits up to wait_s seconds; "
                    "returns the tool's own result when it finishes, or still_running again (a newer user message "
                    "or the wait ran out).")
CALLS_DESCRIPTION = "Tool calls still running in the background (or finished, result not yet collected with tool_wait)."
