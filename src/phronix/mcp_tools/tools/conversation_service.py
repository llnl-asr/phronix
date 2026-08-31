"""The task's own conversation, retrieved in pieces rather than read whole.

A task's `conversation.md` is every turn in full, appended and never
rewritten. That is right for a durable record and wrong to hand a model: it
grows with the task and is largest exactly when the context is tightest.

Attaching it cost the attempt outright. Measured on pytest-5495, an agent that
had already read several large files added `test_conftest.py, lines 1 to 2001`
and the request came back `400 ContextWindowExceededError` — the try died with
no patch and nothing to show for the forty steps before it.

Truncating to head-and-tail keeps the size bounded and decides for the reader
which parts matter. These tools invert that: the record stays whole on disk,
the stage asks for the turn it needs, and only that turn enters the context.

The task is located by ``PHRONIX_TASK_DIR``, which the harness sets per stage.
Without it every tool here reports ``unavailable`` rather than guessing — a
conversation from the wrong task is worse than none, because nothing in the
text says which task it belongs to.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

#: How much of one turn to return before it is itself elided.
TURN_BUDGET_B = 8_000


def _conversation() -> Optional[Path]:
    root = (os.environ.get("PHRONIX_TASK_DIR") or "").strip()
    if not root:
        return None
    found = Path(root) / "conversation.md"
    return found if found.is_file() else None


def _turns(text: str) -> List[Dict[str, Any]]:
    """Split the record on its turn headings, keeping each heading with its body."""
    out: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    body: List[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                current["text"] = "\n".join(body).strip()
                out.append(current)
            current, body = {"n": len(out) + 1, "title": line[3:].strip()}, []
        elif current:
            body.append(line)
    if current:
        current["text"] = "\n".join(body).strip()
        out.append(current)
    return out


def _clip(text: str) -> str:
    if len(text) <= TURN_BUDGET_B:
        return text
    half = TURN_BUDGET_B // 2
    return (f"{text[:half]}\n\n... {len(text) - TURN_BUDGET_B:,} bytes elided "
            f"from this turn ...\n\n{text[-half:]}")


def register(mcp: Any) -> None:
    @mcp.tool()
    def conversation_outline() -> str:
        """Every turn of this task so far, as one line each. Start here.

        The cheap read: numbers and titles only, so a stage can see the shape
        of what has happened and then ask for the one or two turns that bear
        on its question, instead of pulling the whole record into context.

        Returns JSON: {status, task, turns:[{n, title, bytes}], total_bytes}.
        """
        found = _conversation()
        if found is None:
            return json.dumps({"status": "unavailable",
                               "reason": "PHRONIX_TASK_DIR is not set, or the "
                                         "task has no conversation yet"}, indent=2)
        text = found.read_text(errors="replace")
        turns = _turns(text)
        return json.dumps({
            "status": "ok",
            "task": found.parent.name,
            "total_bytes": len(text),
            "turns": [{"n": t["n"], "title": t["title"], "bytes": len(t["text"])}
                      for t in turns],
        }, indent=2)

    @mcp.tool()
    def conversation_turn(n: int) -> str:
        """One turn in full, by the number `conversation_outline` gave it.

        Negative numbers count from the end: `-1` is the most recent turn,
        which is what a revision pass usually wants — it says what just failed.

        Args:
            n: turn number, 1-based, or negative from the end.
        """
        found = _conversation()
        if found is None:
            return json.dumps({"status": "unavailable"}, indent=2)
        turns = _turns(found.read_text(errors="replace"))
        if not turns:
            return json.dumps({"status": "empty"}, indent=2)
        index = (len(turns) + n) if n < 0 else (n - 1)
        if not 0 <= index < len(turns):
            return json.dumps({"status": "no_such_turn", "have": len(turns)},
                              indent=2)
        turn = turns[index]
        return json.dumps({"status": "ok", "n": turn["n"], "title": turn["title"],
                           "text": _clip(turn["text"])}, indent=2)

    @mcp.tool()
    def conversation_search(query: str, limit: int = 3) -> str:
        """The turns that mention *query*, most recent first.

        For the question a revision pass actually has — "has this been tried?"
        — which the outline cannot answer and the whole record answers far too
        expensively.

        Matched on any of the query's words, scored by how many match, so a
        phrase still finds a turn that worded it differently.

        Args:
            query: what to look for, e.g. a symbol, file or approach.
            limit: how many turns to return.
        """
        found = _conversation()
        if found is None:
            return json.dumps({"status": "unavailable"}, indent=2)
        words = {w for w in re.findall(r"[A-Za-z0-9_]+", query.lower())
                 if len(w) > 2}
        if not words:
            return json.dumps({"status": "empty_query"}, indent=2)
        scored = []
        for turn in _turns(found.read_text(errors="replace")):
            haystack = f"{turn['title']} {turn['text']}".lower()
            hits = sum(1 for w in words if w in haystack)
            if hits:
                scored.append((hits, turn["n"], turn))
        # Most matches first, then most recent: a turn that mentions the whole
        # query beats a later one that mentions part of it.
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return json.dumps({
            "status": "ok",
            "matched": len(scored),
            "turns": [{"n": t["n"], "title": t["title"], "text": _clip(t["text"])}
                      for _, _, t in scored[:max(1, limit)]],
        }, indent=2)
