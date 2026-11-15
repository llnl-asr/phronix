"""The Claude Code hooks that send what the agent does in the foreground to the background learner.

    python -m phronix.engine.explore_hook step    --bootstrap MODULE[:FN]   PostToolUse / PostToolUseFailure
    python -m phronix.engine.explore_hook capture --bootstrap MODULE[:FN]   Stop / SubagentStop
    python -m phronix.engine.explore_hook guard   --bootstrap MODULE[:FN]   PreToolUse (capability-first)

The hook event is read from stdin. ``--bootstrap`` names what configures the engine for the project and registers its
recorder profile (``phronix.engine.explore.register``). A hook never blocks and never fails the call or the turn: any
error is reported on stderr and the hook exits 0. :func:`settings` renders the hook entries for a settings.json.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any, Dict, List, Optional, Sequence


def _bootstrap(spec: str) -> None:
    if not spec:
        return
    m, _, f = spec.partition(":")
    mod = importlib.import_module(m)
    if f:
        getattr(mod, f)()


def run(cmd: str, ev: dict) -> Optional[dict]:
    """Handle one hook event; returns the JSON to print (only the guard prints, and only to deny)."""
    from . import explore
    if cmd == "step":
        explore.live_step(ev)
    elif cmd == "capture":
        path = ev.get("agent_transcript_path") or ev.get("transcript_path")
        agent = ""
        if ev.get("hook_event_name") == "SubagentStop":
            agent = ev.get("agent_id") or ev.get("agent_type") or "subagent"
        try:
            with open(path) as fh:
                lines = [json.loads(x) for x in fh if x.strip()]
        except (OSError, TypeError, ValueError):
            return None
        explore.capture(lines, session_id=ev.get("session_id", ""), agent=agent, transcript=str(path or ""))
    elif cmd == "guard":
        why = explore.guard(ev.get("tool_name", ""), ev.get("tool_input") or {}) if explore.guard_active() else None
        if why:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": why}}
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m phronix.engine.explore_hook")
    p.add_argument("command", choices=("step", "capture", "guard"))
    p.add_argument("--bootstrap", default="")
    p.add_argument("--kick", action="store_true",
                   help="capture: then start the background learner/consolidation (standalone phronix, no web UI)")
    a = p.parse_args(argv)
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return 0
    try:
        _bootstrap(a.bootstrap)
        out = run(a.command, ev)
        if a.kick and a.command == "capture":
            from . import explore
            if not explore.in_background():
                from .background import spawn_kick
                spawn_kick(ev.get("cwd") or None, a.bootstrap)
    except Exception as e:  # recording must never break a call or a turn; a broken guard allows the call
        print(f"phronix explore hook ({a.command}) skipped: {type(e).__name__}: {e}", file=sys.stderr)
        return 0
    if out:
        print(json.dumps(out))
    return 0


def settings(launcher: List[str], bootstrap: str, guard: bool = True, guard_matcher: str = "",
             kick: bool = False) -> Dict[str, list]:
    """The hook entries (by event) a project adds to its settings.json. ``launcher``: how to start a python that has
    phronix and the project (e.g. [sys.executable], or [venv.sh, "python"]). ``kick``: the main agent's Stop also starts
    the background agents (a standalone install; a project whose web UI runs them leaves it off)."""
    import shlex
    from . import explore

    def cmd(c: str, timeout: int, extra: List[str] = ()) -> dict:
        argv = [*launcher, "-m", "phronix.engine.explore_hook", c] + (["--bootstrap", bootstrap] if bootstrap else []) \
            + list(extra)
        return {"type": "command", "command": " ".join(shlex.quote(str(x)) for x in argv), "timeout": timeout}

    out: Dict[str, Any] = {
        "PostToolUse": [{"matcher": explore.MANUAL_MATCHER, "hooks": [cmd("step", 10)]}],
        "PostToolUseFailure": [{"matcher": explore.MANUAL_MATCHER, "hooks": [cmd("step", 10)]}],
        "Stop": [{"hooks": [cmd("capture", 20, ["--kick"] if kick else [])]}],
        "SubagentStop": [{"hooks": [cmd("capture", 20)]}],
    }
    if guard:
        out["PreToolUse"] = [{"matcher": guard_matcher or explore.P.guard_matcher, "hooks": [cmd("guard", 10)]}]
    return out


def merge(hooks: Dict[str, list], extra: Dict[str, list]) -> Dict[str, list]:
    """hooks + extra, event by event (extra's entries after the project's own)."""
    out = {k: list(v) for k, v in hooks.items()}
    for ev, entries in extra.items():
        out.setdefault(ev, []).extend(entries)
    return out


if __name__ == "__main__":
    sys.exit(main())
