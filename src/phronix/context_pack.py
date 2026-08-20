"""Build the context block injected into prompts, tool calls and tool results.

Every harness phronix supports talks to the same MCP server, but only some of
them read a memory store natively. This module is the harness-neutral producer
of the text that closes that gap, carrying three payloads:

* **memory**     — the relevant slice of the layered memory store.
* **validation** — the standing "verify, don't assume" rule.
* **learning**   — the standing "record the lesson" rule.

Why tiered and deduplicated, rather than injecting on every call
----------------------------------------------------------------
A working session issues hundreds of tool calls. Even a 1 KB digest repeated on
every result is six figures of tokens per session, almost all of it text the
model has already seen. Worse, the retrieval signal for a tool call (name plus
arguments) is thin, so most of those injections would be *irrelevant* memory —
actively crowding out the real context rather than adding to it.

So:

* the standing rules go in **once per session** (``kind="session"``);
* a given memory is injected **once per session** — :class:`SessionState` tracks
  what has been shown and later calls carry only what is new;
* when nothing new is relevant, :func:`build_pack` returns ``None`` and the
  caller injects nothing at all.

Steady-state cost stays near zero while a lesson still surfaces the moment it
becomes relevant.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from phronix.memory_graph import recall, render_digest

# Kept deliberately short: this is repeated context, and the authoritative text
# lives in the instructions files and the skills. This is a pointer, not a copy.
VALIDATION_RULES = (
    "Verify before you claim: a subagent's or a tool's success report is not "
    "evidence. Read the artifact it says it wrote, and report the real status of "
    "a failure rather than laundering it into 'ok'."
)

LEARNING_RULES = (
    "Record what you learn: when something non-obvious breaks, capture "
    "symptom -> root cause -> exact fix with skill_write, and turn anything "
    "deterministic into a capability instead of prose. Never record usernames, "
    "absolute user paths, or job ids."
)

MEMORY_USAGE = (
    "Relevant project memory (shared, cross-session). "
    "memory_read(name=...) for full text; memory_recall(query=...) to search."
)

_MAX_MEMORY_CHARS = 1200
_MAX_NEW_PER_CALL = 3

_BLOCK_TAG = "phronix-context"


def _state_dir() -> Path:
    override = os.environ.get("PHRONIX_CONTEXT_STATE_DIR")
    if override:
        return Path(override).expanduser()
    from phronix.knowledge_graph import cache_root

    return cache_root() / "context-state"


class SessionState:
    """Per-session record of what has already been injected.

    Thread-safe because an MCP server handles concurrent tool calls, and two
    calls racing here would both decide a memory was "new" and inject it twice —
    the exact duplication this class exists to prevent.

    **Optionally disk-backed.** The MCP middleware lives in one long-running
    process, so in-memory state suffices there. Prompt hooks do not: each hook
    fires as a fresh short-lived process, so without persistence every prompt
    would re-inject the standing rules and the same memories. Hook callers pass
    ``persist=True``.

    The file is best-effort — any I/O error degrades to in-memory behaviour
    rather than failing the caller, because losing dedup state is a cost problem
    and failing the turn is a correctness problem.
    """

    __slots__ = ("_seen", "_queries", "_rules_sent", "_lock", "_path")

    def __init__(self, path: Optional[Path] = None) -> None:
        self._seen: set = set()
        self._queries: set = set()
        self._rules_sent = False
        self._lock = threading.Lock()
        self._path = path
        if path is not None:
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
        except Exception:
            return
        if not isinstance(data, dict):
            return
        self._seen = set(data.get("seen") or [])
        self._queries = set(data.get("queries") or [])
        self._rules_sent = bool(data.get("rules_sent"))

    def _save(self) -> None:
        """Caller must hold ``_lock``."""
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "seen": sorted(self._seen),
                "queries": sorted(self._queries),
                "rules_sent": self._rules_sent,
            }))
            tmp.replace(self._path)  # atomic: a torn file would re-inject everything
        except Exception:
            pass

    def take_query(self, key: str) -> bool:
        """True the first time this query is seen, False on every repeat.

        Without this, an agent retrying the same tool call is fed three
        *different* memories each time — dedup on names alone only stops exact
        repeats, so a retry loop would strip-mine the whole corpus. A query
        already answered has nothing new to say.
        """
        with self._lock:
            if key in self._queries:
                return False
            self._queries.add(key)
            self._save()
            return True

    def take_new(self, names: List[str], limit: int) -> List[str]:
        """Return up to *limit* names not yet injected, marking them as seen."""
        with self._lock:
            fresh = [n for n in names if n not in self._seen][:limit]
            if fresh:
                self._seen.update(fresh)
                self._save()
            return fresh

    def take_rules(self) -> bool:
        """True exactly once per session — the standing rules go in one time."""
        with self._lock:
            if self._rules_sent:
                return False
            self._rules_sent = True
            self._save()
            return True

    def take_rules_pending(self) -> bool:
        """Peek at whether the rules still need sending, without consuming.

        Callers use this to pick the pack ``kind`` *before* calling
        :func:`build_pack`; the once-only guard is still :meth:`take_rules`.
        """
        with self._lock:
            return not self._rules_sent

    def reset(self) -> None:
        with self._lock:
            self._seen.clear()
            self._queries.clear()
            self._rules_sent = False
            self._save()


_SESSIONS: Dict[str, SessionState] = {}
_SESSIONS_LOCK = threading.Lock()


def session_state(session_id: str = "default", persist: bool = False) -> SessionState:
    """Get (or create) the dedup state for *session_id*."""
    key = f"{session_id}:{int(persist)}"
    with _SESSIONS_LOCK:
        state = _SESSIONS.get(key)
        if state is None:
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)[:120] or "default"
            path = (_state_dir() / f"{safe}.json") if persist else None
            state = _SESSIONS[key] = SessionState(path)
        return state


def reset_sessions() -> None:
    """Drop all per-session dedup state (tests, and server restart)."""
    with _SESSIONS_LOCK:
        _SESSIONS.clear()


def build_pack(
    query: str,
    session_id: str = "default",
    kind: str = "tool",
    k: int = 5,
    types: Optional[List[str]] = None,
    memories: Optional[List[Dict[str, Any]]] = None,
    persist: bool = False,
) -> Optional[str]:
    """Return the block to inject, or ``None`` when there is nothing new to say.

    Args:
        query: the text to match memory against — a user prompt, or a tool name
            plus its arguments.
        session_id: dedup scope. Distinct sessions re-inject independently.
        kind: ``"session"`` forces the standing rules in and tolerates an empty
            memory hit; ``"prompt"`` and ``"tool"`` inject only what is new.
        k: how many scored hits to consider before dedup.
        types: restrict to these memory types.
        memories: a pre-parsed corpus, for tests and caching.
        persist: back the dedup state with a file (required for prompt hooks).
    """
    state = session_state(session_id, persist=persist)
    sections: List[str] = []

    if kind == "session" and state.take_rules():
        sections.append(f"VALIDATION: {VALIDATION_RULES}")
        sections.append(f"LEARNING: {LEARNING_RULES}")

    limit = k if kind == "session" else _MAX_NEW_PER_CALL
    # Keyed on the query text ALONE, not on kind: the first call of a session is
    # kind="session" and the next is kind="tool", so folding kind into the key
    # would let the very same query through twice.
    if query.strip() and state.take_query(query.strip()[:400].lower()):
        hits = recall(query, k=k, types=types, memories=memories)
        fresh = state.take_new([h["name"] for h in hits], limit)
        if fresh:
            keep = [h for h in hits if h["name"] in set(fresh)]
            digest = render_digest(keep, budget_chars=_MAX_MEMORY_CHARS)
            if digest:
                sections.append(f"MEMORY: {MEMORY_USAGE}\n{digest}")

    if not sections:
        return None
    return f"<{_BLOCK_TAG}>\n" + "\n\n".join(sections) + f"\n</{_BLOCK_TAG}>"


def tool_query(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """Turn a tool invocation into a retrieval query.

    The tool name alone is a weak signal, so string-ish argument values are
    folded in — a ``run`` call whose arguments mention a specific framework
    should surface that framework's lessons, not just the generic run ones.
    Long values are clipped and non-scalars skipped, since both are noise.
    """
    parts = [tool_name.replace("_", " ")]
    for key, value in (arguments or {}).items():
        if isinstance(value, str) and value.strip():
            parts.append(f"{key} {value[:200]}")
        elif isinstance(value, (int, float, bool)):
            parts.append(str(key))
    return " ".join(parts)
