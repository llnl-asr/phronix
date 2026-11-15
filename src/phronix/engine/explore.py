"""What the agent does in the foreground -> the background learner.

Every call the agent makes with its own hands (Bash, Read/Grep/Glob, Edit/Write, WebFetch: work no tool or capability
did for it) is recorded per chat, across turns and sub-agents, until the work SUCCEEDS. The success point is explicit
(the agent calls ``exploration_complete``) or detected at the end of a turn (enough manual steps, the last ones
succeeded, the reply reports no failure). A completed exploration is queued. A foreground turn that completed no
exploration is queued too, as a ``turn`` record (the user's message, the reply, what was called): what the user said -
a correction, a preference, a choice - is learning as much as a build procedure is.

The background learner (:mod:`phronix.engine.background`) claims a batch of the queue and turns each record into a new or
updated capability or a lesson, then gives its verdict with :func:`mark`. Nothing here changes a capability; what the
learner stages is applied by it or waits for the user, by the approval policy (phronix.engine.background).

A project tells the recorder what is specific to it with :func:`register` (the kinds of manual work it knows, the
capability that owns each kind, the guard that refuses manual work a capability owns, where its state lives); the
hooks (:mod:`phronix.engine.explore_hook`) and the MCP tools (capability ``phronix_exploration``) are the same for every
project. Environment, with <P> the project's prefix (``phronix.engine.configure``): <P>_EXPLORATIONS_DIR (the store),
<P>_WEBUI_SESSION (the chat), <P>_BACKGROUND (set in a background run: never recorded), <P>_USER, <P>_APP_DIR,
<P>_EXPLORE_MIN_STEPS, <P>_LEARN_TURNS (0: queue explorations only), <P>_CAPABILITY_FIRST (0: guard off).

Layout under the store:
    open/<chat>.json        steps of an exploration still in progress (+ a pending explicit completion)
    queue/<id>.json         records for the learner: status complete -> claimed -> processed
    timings/<day>.jsonl     slow tool calls (for the slow-step review)
Stdlib only (and the engine's config): the hooks import it on every tool call.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from . import config as _cfg

MAX_STEPS = 200
CLAIM_TTL_S = 6 * 3600          # a learner run that died: its claims expire
MAX_ATTEMPTS = 3
SLOW_REVIEW_DAYS = 7            # a reviewed slow tool comes back after this, or when it got slower
MIN_KIND_STEPS = 2              # one stray command is not a pattern

# Exploration = every call that is NOT a tool or capability call: the agent's own hands. Every MCP call is a tool.
MANUAL_TOOLS = {"Bash", "BashOutput", "Read", "Grep", "Glob", "LS", "Edit", "MultiEdit", "Write", "NotebookEdit",
                "WebFetch", "WebSearch"}
MANUAL_MATCHER = "|".join(sorted(MANUAL_TOOLS))      # hook matcher for the live recorder
FAIL_RX = re.compile(r"\b(failed|fails|could not|couldn't|unable to|did not work|didn't work|still broken|blocked|"
                     r"not working|giving up|error persists)\b", re.I)
OUTCOMES = ("new", "update", "lesson", "covered", "nothing", "bypassed", "issue")
SLOW_OUTCOMES = ("proposed", "issue", "already_parallel", "inherent")

_EDIT = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
_BUILD_RX = (r"(^|[;&|(]\s*)(make|cmake|ninja)(\s+(?!--version|--help)|$)|"
             r"\b(mpicxx|mpicc|mpic\+\+|CC|cc|gcc|g\+\+|clang\+\+|clang)\s[^|;&]*\s-(c|o)\s")
# The kinds of manual work every project shares; a project's own kinds (register) are tried first.
GENERIC_KINDS: List[Tuple[str, set, str]] = [
    ("polling", {"Bash"}, r"^\s*sleep\s+\d"),
    ("manual_build", {"Bash"}, _BUILD_RX),
    ("dep_search", {"Bash", "Glob", "LS"}, r"\bfind\s+\S+.*-i?name|\bls\b.*(lib[a-z0-9_]+\.(so|a)|Config\.cmake)|\bwhich\s"),
]


@dataclass
class Profile:
    """What the recorder needs to know about the project it serves (see :func:`register`)."""
    kinds: List[Tuple[str, set, str]] = field(default_factory=list)   # (kind, tools, regex on the step input), first match wins
    routes: Dict[str, Tuple[str, str]] = field(default_factory=dict)   # kind -> ("cap_a|cap_{app}", why it is their job)
    guarded: Tuple[str, ...] = ()                                      # kinds refused in user chats (capability-first)
    guard_extra: Optional[Callable[[str, dict], Optional[str]]] = None  # the project's own rule: reason, "" allow, None defer
    guard_matcher: str = "Bash|Edit|MultiEdit|Write|NotebookEdit"
    app_rx: str = r"/(?:workspaces|apps)/([A-Za-z0-9][A-Za-z0-9_.-]*)/"     # finds the app a step works on
    self_packages: Tuple[str, ...] = ()        # packages whose own source a chat must not patch (a tool was broken)
    tool_capability: Optional[Callable[[], Dict[str, str]]] = None      # tool name -> capability providing it
    root: Optional[Callable[[], Path]] = None                          # the store (default: state_dir/learning/explorations)
    not_manual: str = ""                                               # extra bookkeeping tools never recorded
    background_kinds: Tuple[str, ...] = ()     # values of <P>_BACKGROUND that mark a background run (default: any value)
    route_vars: Optional[Callable[[str, dict], Dict[str, str]]] = None  # extra {names} for a route, from (kind, its row)
    suggest: Dict[str, str] = field(default_factory=dict)              # kind -> capability to suggest when its route is empty
    issue_tool: str = ""                       # the tool that reports a broken non-capability tool (named in refusals)


P = Profile()


def register(**kw) -> Profile:
    """Set what is specific to the project (the fields of :class:`Profile`). Call once, after ``configure``."""
    global P, _KIND_RX
    P = Profile(**kw)
    _KIND_RX = None
    return P


def env(name: str, default: str = "") -> str:
    v = _cfg.env(name)
    return default if v is None else v


def _int(name: str, default: int) -> int:
    try:
        return int(env(name) or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(env(name) or default)
    except ValueError:
        return default


def min_steps() -> int:
    """Fewer manual steps than this is a lookup, not an exploration."""
    return _int("EXPLORE_MIN_STEPS", 3)


def learn_turns() -> bool:
    return env("LEARN_TURNS", "1") not in ("0", "false", "no")


def in_background() -> bool:
    """A background run (the learner itself, consolidation, ...): its work is not the foreground's."""
    b = env("BACKGROUND")
    return bool(b) and (not P.background_kinds or b in P.background_kinds)


# ------------------------------------------------------------------ the store
def root() -> Path:
    d = env("EXPLORATIONS_DIR")
    if d:
        return Path(d).expanduser()
    learn = env("LEARNING_DIR")              # before the project's root: a check sandbox points it at a scratch dir
    if learn:
        return Path(learn).expanduser() / "explorations"
    if P.root is not None:
        return Path(P.root())
    return _cfg.state_dir("learning") / "explorations"


def _dirs() -> Tuple[Path, Path]:
    r = root()
    for d in (r / "open", r / "queue"):
        d.mkdir(parents=True, exist_ok=True)
    return r / "open", r / "queue"


def _write(p: Path, obj: dict) -> None:
    tmp = p.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=1, default=str))
    os.replace(tmp, p)


def _read(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def chat_key(session_id: str = "", agent: str = "") -> str:
    k = re.sub(r"[^A-Za-z0-9_.-]", "_", env("WEBUI_SESSION") or session_id or "cli")[:80]
    return k + (f"--{re.sub(r'[^A-Za-z0-9_-]', '_', agent)[:40]}" if agent else "")


def _new_open(key: str) -> dict:
    return {"chat": key, "user": env("USER"), "started": time.time(), "steps": [], "prompts": [], "app_dir": env("APP_DIR")}


# ------------------------------------------------------------------ what counts as manual
def is_manual(tool: str) -> bool:
    if tool not in MANUAL_TOOLS:
        return False
    return not (P.not_manual and re.search(P.not_manual, tool))


def _summ(tool: str, inp: dict) -> str:
    inp = inp or {}
    for k in ("command", "file_path", "pattern", "url", "query", "path", "notebook_path"):
        if inp.get(k):
            s = str(inp[k])
            if k == "command" and inp.get("description"):
                s = f"{s}    # {inp['description']}"
            return s[:600]
    return json.dumps(inp, default=str)[:600]


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return json.dumps(content, default=str)


def _ts(e: dict) -> Optional[float]:
    t = e.get("timestamp")
    if not t:
        return None
    try:
        return datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ------------------------------------------------------------------ transcript -> steps
def turn_steps(lines: List[dict]) -> Dict[str, Any]:
    """The LAST turn of a Claude Code transcript (entries after the last real user prompt): its manual steps, every
    tool call with its duration, whether the agent called exploration_complete, the prompt and the final text."""
    start = 0
    for i, e in enumerate(lines):
        m = e.get("message") or {}
        if e.get("type") == "user" and isinstance(m.get("content"), str):
            start = i
    uses: Dict[str, dict] = {}
    order: List[str] = []
    calls: Dict[str, dict] = {}
    explicit, last_text, prompt = False, "", ""
    if lines and start < len(lines):
        m = lines[start].get("message") or {}
        prompt = m.get("content") if isinstance(m.get("content"), str) else ""
    for e in lines[start:]:
        for b in (e.get("message") or {}).get("content") or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                name = b.get("name", "")
                calls[b.get("id")] = {"tool": name, "start": _ts(e), "input": _summ(name, b.get("input"))[:300],
                                      "batch": sum(1 for x in (e.get("message") or {}).get("content") or []
                                                   if isinstance(x, dict) and x.get("type") == "tool_use")}
                if name.endswith("exploration_complete"):
                    explicit = True
                if is_manual(name):
                    uses[b.get("id")] = {"id": b.get("id"), "tool": name, "input": _summ(name, b.get("input")), "ok": None}
                    order.append(b.get("id"))
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                cl = calls[b["tool_use_id"]]
                end = _ts(e)
                if cl.get("start") and end:
                    cl["seconds"] = round(max(0.0, end - cl["start"]), 2)
                cl["ok"] = not b.get("is_error")
            if b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                txt = _result_text(b.get("content"))
                err = bool(b.get("is_error")) or txt.lstrip().startswith(("Error:", "Traceback"))
                if not err and re.search(r'"status"\s*:\s*"error"', txt[:400]):
                    err = True
                uses[b["tool_use_id"]].update(ok=not err, output=txt[-400:])
            elif b.get("type") == "text" and e.get("type") == "assistant":
                last_text = b.get("text", "")
    for i in order:
        if calls.get(i, {}).get("seconds") is not None:
            uses[i]["seconds"] = calls[i]["seconds"]
    tools: Dict[str, int] = {}
    for c in calls.values():
        tools[c["tool"]] = tools.get(c["tool"], 0) + 1
    return {"steps": [uses[i] for i in order], "explicit": explicit, "final_text": last_text,
            "prompt": (prompt or "")[:2000], "calls": [c for c in calls.values() if c.get("seconds") is not None],
            "tools": tools}


def succeeded(steps: List[dict], final_text: str) -> bool:
    """Auto success point: enough manual steps, the last ones that ran succeeded, the reply reports no failure."""
    done = [s for s in steps if s.get("ok") is not None]
    if len(done) < min_steps():
        return False
    if not all(s["ok"] for s in done[-2:]):
        return False
    return not FAIL_RX.search(final_text or "")


def _merge(old: List[dict], new: List[dict]) -> List[dict]:
    """Steps recorded live (PostToolUse) are completed from the transcript at the end of the turn - one step per call."""
    by = {s.get("id"): s for s in old if s.get("id")}
    out = list(old)
    for s in new:
        if s.get("id") in by:
            by[s["id"]].update({k: v for k, v in s.items() if v is not None})
            by[s["id"]].pop("live", None)
        else:
            out.append(s)
    return out[-MAX_STEPS:]


# ------------------------------------------------------------------ recording (the hooks)
def capture(lines: List[dict], session_id: str = "", agent: str = "", transcript: str = "") -> Dict[str, Any]:
    """Stop / SubagentStop hook, with the transcript: add the turn's manual steps to the chat's open exploration and
    queue it at the success point. A main-agent turn that completed no exploration is queued as a ``turn`` record."""
    if in_background():
        return {"status": "ok", "recorded": 0, "skipped": "background run (its work is not the foreground's)"}
    od, _ = _dirs()
    key = chat_key(session_id, agent)
    t = turn_steps(lines)
    record_timings(t["calls"], key)
    p = od / f"{key}.json"
    ep = _read(p) or _new_open(key)
    out: Dict[str, Any] = {"status": "ok", "recorded": len(t["steps"])}
    if t["steps"] or ep.get("completion"):
        ep["steps"] = _merge(ep["steps"], t["steps"])
        if t["prompt"]:
            ep["prompts"] = (ep.get("prompts") or [])[-9:] + [t["prompt"]]
        ep["updated"] = time.time()
        ep["final_text"] = (t["final_text"] or "")[-3000:]
        if transcript:
            ep["transcripts"] = list(dict.fromkeys((ep.get("transcripts") or []) + [transcript]))[-10:]
        explicit = bool(ep.get("completion")) or t["explicit"]
        if explicit or succeeded(ep["steps"], t["final_text"]):
            out["completed"] = complete(ep, how="explicit" if explicit else "auto")
            try:
                p.unlink()
            except OSError:
                pass
            return out
        _write(p, ep)
        out["open"] = len(ep["steps"])
    if not agent and learn_turns() and (t["prompt"] or "").strip():
        out["turn"] = queue_turn(key, t, transcript)
    return out


def live_step(ev: dict) -> Dict[str, Any]:
    """PostToolUse / PostToolUseFailure hook: one manual call goes to the chat's open exploration as it happens."""
    if in_background():
        return {"status": "ok", "skipped": "background run"}
    tool = ev.get("tool_name", "")
    if not is_manual(tool):
        return {"status": "ok", "skipped": "a tool call, not an exploration"}
    od, _ = _dirs()
    key = chat_key(ev.get("session_id", ""), ev.get("agent_id") or "")
    p = od / f"{key}.json"
    ep = _read(p) or _new_open(key)
    failed = ev.get("hook_event_name") == "PostToolUseFailure"
    resp = ev.get("tool_response")
    out = ev.get("error") if failed else (resp if isinstance(resp, str) else json.dumps(resp, default=str) if resp else "")
    step = {"id": ev.get("tool_use_id"), "tool": tool, "input": _summ(tool, ev.get("tool_input") or {}),
            "ok": not failed, "output": str(out or "")[-400:], "live": True}
    ep["steps"] = _merge(ep["steps"], [step])
    ep["updated"] = time.time()
    _write(p, ep)
    return {"status": "ok", "open": len(ep["steps"])}


def mark_complete(goal: str, subject: str = "", what_worked: str = "", commands: str = "", verification: str = "",
                  family: str = "", session_id: str = "") -> Dict[str, Any]:
    """The explicit success point (exploration_complete): attach the agent's summary to the chat's open exploration;
    the end-of-turn hook adds the turn's steps and queues it."""
    if not goal.strip() or not verification.strip():
        return {"status": "error", "error": "say what the exploration was for (goal) and how you know it worked "
                                            "(verification: the command/output/test that shows success)"}
    od, _ = _dirs()
    key = chat_key(session_id)
    p = od / f"{key}.json"
    ep = _read(p) or _new_open(key)
    ep["completion"] = {"goal": goal, "subject": subject, "what_worked": what_worked, "commands": commands,
                        "verification": verification, "family": family, "at": time.time()}
    _write(p, ep)
    return {"status": "ok", "queued_at_end_of_turn": True,
            "note": "the background learner turns it into a capability proposal; keep working"}


def _qid(*parts) -> str:
    raw = json.dumps(parts, default=str)
    return time.strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(raw.encode()).hexdigest()[:8]


def complete(ep: dict, how: str) -> str:
    _, qd = _dirs()
    qid = _qid(ep.get("chat"), ep.get("started"), len(ep.get("steps") or []))
    _write(qd / f"{qid}.json", dict(ep, id=qid, kind="exploration", status="complete", how=how, completed=time.time(),
                                    attempts=0))
    return qid


def queue_turn(key: str, t: Dict[str, Any], transcript: str = "") -> str:
    """A foreground turn for the learner: what the user said, what the agent answered and called."""
    _, qd = _dirs()
    qid = _qid(key, t.get("prompt"), time.time())
    _write(qd / f"{qid}.json", {"id": qid, "kind": "turn", "chat": key, "user": env("USER"), "app_dir": env("APP_DIR"),
                                "prompts": [t.get("prompt") or ""], "final_text": (t.get("final_text") or "")[-3000:],
                                "tools": t.get("tools") or {}, "transcripts": [transcript] if transcript else [],
                                "steps": [], "status": "complete", "how": "turn", "completed": time.time(), "attempts": 0})
    return qid


# ------------------------------------------------------------------ the queue (learner side)
def _all() -> List[dict]:
    _, qd = _dirs()
    return [e for e in (_read(f) for f in sorted(qd.glob("*.json"))) if e]


def pending(now: Optional[float] = None) -> List[dict]:
    """Records waiting for the learner (incl. expired claims of a learner run that died), explorations first."""
    now = now or time.time()
    out = [e for e in _all() if e.get("attempts", 0) < MAX_ATTEMPTS and (
        e.get("status") == "complete" or (e.get("status") == "claimed" and now - e.get("claimed", 0) > CLAIM_TTL_S))]
    return sorted(out, key=lambda e: (e.get("kind") == "turn", e.get("completed", 0)))


def claim(ids: List[str], forge: str) -> List[str]:
    _, qd = _dirs()
    got = []
    for i in ids:
        p = qd / f"{i}.json"
        e = _read(p)
        if not e or e.get("status") not in ("complete", "claimed"):
            continue
        e.update(status="claimed", claimed=time.time(), forge=forge, attempts=e.get("attempts", 0) + 1)
        _write(p, e)
        got.append(i)
    return got


def listing(status: str = "", forge: str = "", limit: int = 50, full: bool = False) -> Dict[str, Any]:
    rows = [e for e in _all() if (not status or e.get("status") == status) and (not forge or e.get("forge") == forge)]
    rows = rows[-max(1, min(int(limit or 50), 500)):]
    if full:
        rows = [dict(e, analysis=analyze(e)) for e in rows]
    else:
        rows = [{k: e.get(k) for k in ("id", "kind", "status", "how", "chat", "completed", "forge", "outcome",
                                       "capability", "proposal")}
                | {"goal": (e.get("completion") or {}).get("goal") or (e.get("prompts") or [""])[-1][:200],
                   "steps": len(e.get("steps") or [])} for e in rows]
    counts: Dict[str, int] = {}
    for e in _all():
        counts[e.get("status", "?")] = counts.get(e.get("status", "?"), 0) + 1
    return {"status": "ok", "counts": counts, "explorations": rows, "dir": str(root())}


def stats(recent: int = 5) -> Dict[str, Any]:
    """Counts for a UI: explorations in progress, queue states, the latest outcomes."""
    od, _ = _dirs()
    rows = _all()
    counts: Dict[str, int] = {}
    for e in rows:
        counts[e.get("status", "?")] = counts.get(e.get("status", "?"), 0) + 1
    done = sorted((e for e in rows if e.get("status") == "processed"), key=lambda e: e.get("processed", 0))[-recent:]
    return {"open": len(list(od.glob("*.json"))), "counts": counts,
            "recent": [{"id": e["id"], "kind": e.get("kind", "exploration"), "outcome": e.get("outcome"),
                        "capability": e.get("capability"), "at": e.get("processed")} for e in reversed(done)]}


# ------------------------------------------------------------------ what the manual steps were doing (learner input)
_KIND_RX: Optional[List[Tuple[str, set, Any]]] = None


def _kind_rx():
    global _KIND_RX
    if _KIND_RX is None:
        own: List[Tuple[str, set, str]] = []
        if P.self_packages:
            pk = "|".join(re.escape(p) for p in P.self_packages)
            own = [("self_edit", _EDIT, rf"/src/({pk})/"),
                   ("self_edit", {"Bash"}, rf"sed\s+-i[^|;&]*/src/({pk})/"),
                   ("self_inspect", {"Read", "Bash"}, rf"/src/({pk})/|import ({pk})\b|from ({pk})\b")]
        mine = {k for k, _t, _r in P.kinds}       # a project may place a generic kind itself, in its own order
        _KIND_RX = [(k, t, re.compile(r)) for k, t, r in own + list(P.kinds) + [g for g in GENERIC_KINDS if g[0] not in mine]]
    return _KIND_RX


def step_kind(tool: str, inp: str) -> str:
    for k, tools, rx in _kind_rx():
        if tool in tools and rx.search(inp or ""):
            return k
    return "inspect"


def tool_capability() -> Dict[str, str]:
    """tool name -> the capability that provides it."""
    if P.tool_capability is not None:
        try:
            return P.tool_capability()
        except Exception:
            return {}
    out: Dict[str, str] = {}
    try:
        from . import capstore
        for name, (_layer, _d, meta) in capstore.all_caps().items():
            for t in meta.get("tools") or []:
                out[t] = meta.get("name") or name
    except Exception:
        pass
    return out


def _app_of(steps: List[dict]) -> str:
    seen: Dict[str, int] = {}
    rx = re.compile(P.app_rx)
    for s in steps:
        for m in rx.finditer(str(s.get("input") or "")):
            a = m.group(1).lower()
            if not a.startswith("_"):
                seen[a] = seen.get(a, 0) + 1
    return max(seen, key=seen.get) if seen else ""


def analyze(ep: dict) -> Dict[str, Any]:
    """Deterministic read of a record for the learner: per kind of manual work its steps and examples; work a capability
    already owns that the chat did by hand (bypassed), work no capability does (gaps), and patches of the agents' own
    code made from a chat (self_edits: a tool was broken)."""
    steps = ep.get("steps") or []
    t2c = tool_capability()
    caps = set(t2c.values())
    app = _app_of(steps)
    used = {t2c.get(str(s.get("tool", "")).split("__")[-1]) for s in steps} | \
           {t2c.get(str(t).split("__")[-1]) for t in (ep.get("tools") or {})}
    used -= {None}
    wait = sorted(t for t in t2c if re.search(r"(^|_)wait(_|$)", t))
    kinds: Dict[str, dict] = {}
    self_edits: List[str] = []
    for i, s in enumerate(steps):
        tool, inp = str(s.get("tool", "")), str(s.get("input") or "")
        if not is_manual(tool):
            continue
        k = step_kind(tool, inp)
        row = kinds.setdefault(k, {"steps": 0, "failed": 0, "examples": []})
        row["steps"] += 1
        row["failed"] += s.get("ok") is False
        if len(row["examples"]) < 4:
            row["examples"].append(f"#{i} {tool}: {inp[:160]}")
        if k == "self_edit":
            m = re.search(r"(/src/[A-Za-z_]+/\S+)", inp)
            f = m.group(1) if m else inp[:120]
            if f not in self_edits:
                self_edits.append(f)
    bypassed, gaps = [], []
    for k, row in kinds.items():
        if k not in P.routes or row["steps"] < MIN_KIND_STEPS:
            continue
        pat, why = P.routes[k]
        fmt = {"app": app, "generator": "", "wait_tool": t2c.get(wait[0], "") if wait else ""}
        if P.route_vars is not None:
            fmt.update(P.route_vars(k, row) or {})
        cands = [c.format(**fmt) for c in pat.split("|")]
        cands = [c for c in cands if c and not c.endswith("_")]
        have = [c for c in cands if c in caps]
        row["should_use"] = have or cands
        row["why"] = why.format(app=app or "<app>")
        if have:
            row["capability_used_in_chat"] = any(c in used for c in have)
            bypassed.append({"kind": k, "capability": have[0], "steps": row["steps"], "why": row["why"]})
        else:
            gaps.append({"kind": k, "suggest": cands[0] if cands else P.suggest.get(k) or f"workload_{app or '<app>'}",
                         "steps": row["steps"], "why": row["why"]})
    return {"kind": ep.get("kind", "exploration"), "app": app, "manual_steps": sum(r["steps"] for r in kinds.values()),
            "kinds": kinds, "capabilities_used": sorted(used), "bypassed": bypassed, "gaps": gaps, "self_edits": self_edits}


def _check_verdict(e: dict, outs: set) -> Optional[str]:
    """The verdict must answer what analyze() found: every bypass, every gap, every self-edit."""
    a = analyze(e)
    if a["bypassed"] and "bypassed" not in outs:
        caps = sorted({b["capability"] for b in a["bypassed"]})
        return (f"{e['id']}: the chat did by hand what {', '.join(caps)} already do "
                f"({', '.join(b['kind'] for b in a['bypassed'])}) - that is not 'covered': mark it 'bypassed' with the "
                "proposal that makes the capability get used and fixes why it was avoided (capability_update / lesson)")
    if a["gaps"] and not outs & {"new", "update", "lesson", "nothing"}:
        return (f"{e['id']}: no capability exists for {', '.join(g['kind'] + ' -> ' + g['suggest'] for g in a['gaps'])}"
                " - stage it (new/update) or say why it is not reusable (nothing + note)")
    if a["self_edits"] and "issue" not in outs:
        return (f"{e['id']}: the chat edited the agents' own code ({', '.join(a['self_edits'][:4])}) - a tool was "
                "broken: report the tool issue / capability_update it and add 'issue'")
    return None


def mark(ids: List[str], outcome: str, capability: str = "", proposal: str = "", note: str = "") -> Dict[str, Any]:
    """The learner's verdict per record; outcome may combine several, comma-separated: new/update (a capability
    proposal was staged), lesson (a lesson was proposed), covered (the chat USED the existing capability), nothing (not
    reusable), bypassed (a capability existed but the chat did its work by hand), issue (the agents' own code was
    edited from the chat). Checked against analyze(): bypasses, gaps and self-edits must each be answered."""
    outs = {o.strip() for o in (outcome or "").split(",") if o.strip()}
    bad = outs - set(OUTCOMES)
    if not outs or bad:
        return {"status": "error", "error": f"outcome must be one or more (comma-separated) of {OUTCOMES}"}
    if outs & {"new", "update", "bypassed"} and not (capability and proposal):
        return {"status": "error", "error": "new/update/bypassed need the capability name(s) and the proposal id(s) staged"}
    if outs & {"covered", "lesson", "nothing", "bypassed", "issue"} and not note.strip():
        return {"status": "error", "error": "say why (note): which capability / which lesson / which issue / why not reusable"}
    _, qd = _dirs()
    done, missing, refused = [], [], []
    for i in ids:
        p = qd / f"{i}.json"
        e = _read(p)
        if not e:
            missing.append(i)
            continue
        why = _check_verdict(e, outs)
        if why:
            refused.append(why)
            continue
        e.update(status="processed", outcome=",".join(o for o in OUTCOMES if o in outs), capability=capability,
                 proposal=proposal, note=note, processed=time.time())
        _write(p, e)
        done.append(i)
    if refused:
        return {"status": "error" if not done else "partial", "marked": done, "unknown": missing, "refused": refused}
    return {"status": "ok" if not missing else "partial", "marked": done, "unknown": missing}


# ------------------------------------------------------------------ slow steps (timings -> parallelization review)
def _slow_s() -> float:
    return _float("SLOW_S", 60.0)


def record_timings(calls: List[dict], chat: str = "") -> int:
    """Append every tool call slower than <P>_TIMING_MIN_S (2 s) to timings/<day>.jsonl."""
    keep = [c for c in calls if (c.get("seconds") or 0) >= _float("TIMING_MIN_S", 2.0)]
    if not keep:
        return 0
    d = root() / "timings"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{time.strftime('%Y%m%d')}.jsonl", "a") as f:
        for c in keep:
            f.write(json.dumps({"ts": c.get("start") or time.time(), "chat": chat, "tool": c["tool"],
                                "short": c["tool"].split("__")[-1], "seconds": c["seconds"], "ok": c.get("ok"),
                                "batch": c.get("batch", 1), "input": c.get("input", "")}) + "\n")
    return len(keep)


def _reviews_file() -> Path:
    return root() / "slow_reviews.json"


def slow_steps(min_seconds: float = 0.0, days: float = 7.0, include_reviewed: bool = False) -> Dict[str, Any]:
    """Tools whose typical (median) call is slow over the last ``days``: count, median, max, total, the capability
    providing them, how often they ran alone, example inputs, and whether the learner already reviewed them (a review
    expires after SLOW_REVIEW_DAYS or when the tool got 25% slower)."""
    min_seconds = min_seconds or _slow_s()
    min_calls, once_s = _int("SLOW_MIN_CALLS", 2), _float("SLOW_ONCE_S", 300.0)
    since = time.time() - days * 86400
    agg: Dict[str, dict] = {}
    d = root() / "timings"
    for f in sorted(d.glob("*.jsonl")) if d.is_dir() else []:
        for line in f.read_text(errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ts", 0) < since:
                continue
            a = agg.setdefault(r["short"], {"tool": r["short"], "secs": [], "alone": 0, "examples": [], "failed": 0})
            a["secs"].append(float(r["seconds"]))
            a["alone"] += r.get("batch", 1) <= 1
            a["failed"] += r.get("ok") is False
            if len(a["examples"]) < 3 and r.get("input"):
                a["examples"].append(r["input"][:200])
    caps = tool_capability()
    reviews = _read(_reviews_file()) or {}
    rows = []
    for a in agg.values():
        xs = sorted(a.pop("secs"))
        med = xs[len(xs) // 2]
        if med < min_seconds or (len(xs) < min_calls and xs[-1] < max(once_s, min_seconds)):
            continue
        rv = reviews.get(a["tool"]) or {}
        fresh = rv and time.time() - rv.get("at", 0) < SLOW_REVIEW_DAYS * 86400 and med < 1.25 * rv.get("median", med)
        if fresh and not include_reviewed:
            continue
        rows.append({**a, "calls": len(xs), "median_s": round(med, 1), "max_s": round(xs[-1], 1),
                     "total_s": round(sum(xs), 1), "capability": caps.get(a["tool"]), "reviewed": rv or None})
    rows.sort(key=lambda r: -r["total_s"])
    return {"status": "ok", "slow": rows, "threshold_s": min_seconds, "days": days}


def slow_step_mark(tool: str, outcome: str, capability: str = "", proposal: str = "", note: str = "") -> Dict[str, Any]:
    """The learner's verdict on a slow tool: proposed (a capability_update that parallelizes it was staged), issue (not
    a capability: a tool issue was filed), already_parallel (note what bounds it), inherent (one indivisible job)."""
    if outcome not in SLOW_OUTCOMES:
        return {"status": "error", "error": f"outcome must be one of {SLOW_OUTCOMES}"}
    if outcome == "proposed" and not (capability and proposal):
        return {"status": "error", "error": "proposed needs the capability and the proposal id"}
    if outcome != "proposed" and not note.strip():
        return {"status": "error", "error": "say why (note)"}
    cur = {r["tool"]: r for r in slow_steps(include_reviewed=True)["slow"]}
    reviews = _read(_reviews_file()) or {}
    reviews[tool] = {"at": time.time(), "outcome": outcome, "capability": capability, "proposal": proposal,
                     "note": note, "median": (cur.get(tool) or {}).get("median_s", 0)}
    root().mkdir(parents=True, exist_ok=True)
    _write(_reviews_file(), reviews)
    return {"status": "ok", "tool": tool, "outcome": outcome}


# ------------------------------------------------------------------ capability-first guard (PreToolUse)
def guard_active() -> bool:
    """Only in a user's web UI chat, never in a background run, unless <P>_CAPABILITY_FIRST=0."""
    return bool(env("WEBUI_SESSION")) and not env("BACKGROUND") and env("CAPABILITY_FIRST", "1") != "0"


def guard(tool: str, inp: dict) -> Optional[str]:
    """The reason a manual call must not run (None = allowed): it does work a capability owns."""
    if P.guard_extra is not None:
        why = P.guard_extra(tool, inp or {})      # a reason refuses, "" allows, None leaves it to the kinds below
        if why is not None:
            return why or None
    if not P.guarded or not is_manual(tool):
        return None
    cmd = _summ(tool, inp or {}).split("    # ")[0]
    kind = step_kind(tool, cmd)
    if kind not in P.guarded:
        return None
    _pat, why = P.routes.get(kind, ("", "this is a capability's job"))
    return refusal(kind, tool, why.format(app="<app>"))


def refusal(kind: str, tool: str, why: str) -> str:
    """The capability-first refusal: use the capability; when it fails, fix it and retry it."""
    issue = f"{P.issue_tool} for a non-capability tool" if P.issue_tool else "report the tool issue"
    return (f"CAPABILITY-FIRST: refused manual {kind.replace('_', ' ')} ({tool}). {why}. Use the capability. If it "
            f"failed, FIX THE CAPABILITY (capability_get -> capability_update, or {issue}), then RETRY THE CAPABILITY - "
            "never patch its output or do its work by hand.")
