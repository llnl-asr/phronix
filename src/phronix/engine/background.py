"""The background agents: they turn what happens in the foreground into capabilities, lessons and one copy of each fact.

* :class:`Learner` - the recorder (:mod:`phronix.engine.explore`, fed by the hooks in
  :mod:`phronix.engine.explore_hook`) queues every exploration that succeeded and every foreground turn. When records
  are waiting (or slow tools are due for review) and no learner run is going, it claims a batch and starts ONE
  background run with :data:`LEARN_ASK`, which stages capability and lesson proposals and closes each record with
  ``exploration_mark``.
* :class:`Consolidator` - when :func:`phronix.engine.consolidate.report` finds NEW overlap or conflict groups among
  lessons or capabilities, it starts one background run per part with :data:`phronix.engine.consolidate.ASK`, which
  merges what overlaps and asks the user about what conflicts.

Both only propose: the user approves. How a run is started is the project's (its web UI's turn, a CLI agent, ...): it
passes ``start(run_id, title, ask)`` returning ``{"turn_key": ...}`` (or ``{"error": ...}``) and
``running(turn_key) -> bool``; the UI around them (panels, buttons) stays in the project. Environment, with <P> the
project's prefix: <P>_AUTO_LEARN / <P>_AUTO_CONSOLIDATE (0: only when forced), <P>_LEARN_BATCH (records per run, 8),
<P>_LEARN_SLOW_GAP_H (slow-step reviews alone at most this often, 6), <P>_CONSOLIDATION_GAP_H (automatic
consolidation per part at most this often, 6).
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import explore as X

BG_RULES = ("You are a BACKGROUND run, not a chat: nobody reads your turn live and nobody can answer in it. Work on "
            "this node only: no jobs, no compute nodes, no builds. Whether what you stage is applied by you or waits for "
            "the user is the APPROVAL POLICY at the end of this message. End with a short plain report: what you changed "
            "or proposed (ids and names), and what you left for the user to decide and why.\n\n")

# What the background agents do with what they stage. Automatic is the default: they apply what passes its checks,
# keep the store consistent, and ask only what the evidence cannot decide. <P>_LEARN_APPROVAL=review: everything waits.
POLICY = {
    "auto": ("\n\nAPPROVAL POLICY: automatic. Do not leave your work waiting for the user. Once a capability proposal "
             "passes its checks (capability_verify), apply it yourself with capability_apply(id, confirmed=true); apply "
             "each lesson you added or merged with lesson_decide(id, approve=true). Keep the whole store internally "
             "consistent: one copy of each fact, no rule contradicting another, every Cross-reference resolving; when "
             "your change makes an existing lesson or rule wrong, fix or retire it in the same run. Ask the user "
             "(consolidation_ask) ONLY when the evidence cannot decide; otherwise decide from the evidence (the newer, "
             "verified fact that matches the current code wins), say in the change's why what you chose over what, and "
             "keep processing."),
    "review": ("\n\nAPPROVAL POLICY: review. Everything you stage waits for the user's approval: never apply a capability "
               "proposal or decide a lesson yourself."),
}


def approval() -> str:
    """auto (default) or review: <P>_LEARN_APPROVAL."""
    return "review" if X.env("LEARN_APPROVAL", "auto").strip().lower() in ("review", "manual", "approve", "0") else "auto"


def policy_text(policy: Optional[Dict[str, str]] = None) -> str:
    return (policy or POLICY)[approval()]

LEARN_ASK = (
    "You are the background LEARNER (skill phronix_exploration). What the agent did in the foreground is waiting for "
    "you: explorations it did by hand and finished successfully (kind exploration), and foreground turns (kind turn). "
    "Turn them into reusable capabilities and lessons so nobody has to explore them again.\n"
    "1. exploration_list(status='claimed', forge='{forge}', full=true) - your batch: ids {ids}. Each has the user's "
    "prompts, every manual step (tool, input, ok, output tail), the final reply, the transcript path(s) (Read them in "
    "parts when a step needs its context), the agent's own completion summary when it gave one, and `analysis`.\n"
    "2. Group the records by SUBJECT (one workload/software/tool/system/procedure). knowledge_search and capability_get "
    "every candidate capability first.\n"
    "3. Explorations: keep only what WORKED (the successful path; dead ends become Corner cases error -> cause -> fix). "
    "Deterministic parts (probes, exact command lines, config generation, checks of a result) become tool code with a "
    "separate validator and checks; judgement goes into SKILL.md; one-offs go to LESSONS.md. Extend the existing "
    "capability (capability_update) before creating one (capability_new, named workload_/software_/tools_/system_). A "
    "complex procedure becomes one capability per step plus a parent whose skill lists the steps in order; reuse a step "
    "that exists. Paths relative to $PROJECT_ROOT; no usernames, job ids or node names.\n"
    "4. Turns: everything the user said that teaches something - a correction, a preference, a choice, a rejection, a "
    "condition, a repeated request - becomes lesson_add on the capability it concerns, quoting the user as evidence. "
    "Skip what a lesson or capability already says (lesson_search first), chit-chat, and facts only that chat needs.\n"
    "5. `analysis` is deterministic: `bypassed` = work a capability already owns that the chat did by hand (find WHY: it "
    "failed, lacked an option, or was not known - stage the capability_update that fixes it, and a lesson so it is "
    "used); `gaps` = work no capability does (stage new/update); `self_edits` = the agents' own code patched from a "
    "chat (a tool was broken: report it).\n"
    "6. Every proposal must pass its own checks; then follow the APPROVAL POLICY below.\n"
    "7. exploration_mark every id, outcomes comma-separated: new|update (capability + proposal ids), bypassed "
    "(capability + proposal), lesson, issue, covered (ONLY when the chat used the capability), nothing (+ why). The mark "
    "is refused when a bypass, gap or self-edit is left unanswered. No id may be left unmarked. End with one line per "
    "record: id -> outcome.\n"
    "8. SLOW STEPS: slow_steps() lists tools whose typical call is slow. For each, capability_get the capability that "
    "provides it, find what is serial but independent (per-file / per-item loops, independent sub-steps, waiting "
    "instead of preparing) and stage a capability_update that runs it concurrently with identical results and errors; "
    "then slow_step_mark(tool, proposed|issue|already_parallel|inherent, capability, proposal, note) for every tool.")


def ask_for(forge: str, ids: List[str], slow: bool, template: str = LEARN_ASK) -> str:
    ask = template.replace("{forge}", forge).replace("{ids}", ", ".join(ids) or "none (skip the batch steps)")
    if not slow:
        ask += "\n(slow_steps has nothing to review now: skip the slow-step step.)"
    return ask


def enabled() -> bool:
    return X.env("AUTO_LEARN", "1") not in ("0", "false", "no")


class Learner:
    """When to start the background learner, and what the Agents panel says about it and the recorder."""

    def __init__(self, state_file: Path, start: Callable[[str, str, str], Dict[str, Any]],
                 running: Callable[[str], bool], ask: str = LEARN_ASK, title: str = "Learner",
                 batch: Optional[int] = None, slow_gap_h: Optional[float] = None,
                 auto: Optional[Callable[[], bool]] = None, rules: str = BG_RULES,
                 policy: Optional[Dict[str, str]] = None) -> None:
        self.f = Path(state_file)
        self.rules, self.policy = rules, policy
        self.start, self.running, self.ask, self.title = start, running, ask, title
        self.batch = batch or X._int("LEARN_BATCH", 8)
        self.slow_gap_h = slow_gap_h if slow_gap_h is not None else X._float("LEARN_SLOW_GAP_H", 6.0)
        self.auto = auto or enabled
        self.status: Dict[str, Any] = {}

    def _last(self) -> Dict[str, Any]:
        try:
            return json.loads(self.f.read_text())
        except (OSError, ValueError):
            return {}

    def watch_once(self, force: bool = False) -> Dict[str, Any]:
        """Start one learner run when there is work for it; force (a ▶ in a UI): now, even when automatic runs are off
        or the slow-step review is not due. Returns the status (also kept in ``self.status``)."""
        last = self._last()
        pend = X.pending()
        try:
            slow = X.slow_steps()["slow"]
        except Exception:
            slow = []
        on = self.auto()
        st = {**last, "enabled": on, "pending": len(pend), "slow": len(slow), "checked": time.time()}
        slow_due = bool(slow) and (force or time.time() - last.get("slow_at", 0) >= self.slow_gap_h * 3600)
        if (not on and not force) or not (pend or slow_due):
            if force:
                st["waiting"] = "nothing to do: no foreground work queued and no slow steps to review"
            self.status = st
            return st
        if last.get("turn_key") and self.running(last["turn_key"]):
            self.status = {**st, "waiting": "the previous learner run is still running"}
            return self.status
        sid = uuid.uuid4().hex[:12]
        ids = X.claim([e["id"] for e in pend[:self.batch]], forge=sid)
        if not ids and not slow_due:
            self.status = st
            return st
        kinds = {}
        for e in pend:
            if e["id"] in ids:
                kinds[e.get("kind", "exploration")] = kinds.get(e.get("kind", "exploration"), 0) + 1
        parts = [f"{n} {k}{'s' if n != 1 else ''}" for k, n in sorted(kinds.items())]
        if slow_due:
            parts.append(f"{len(slow)} slow step{'s' if len(slow) != 1 else ''}")
        r = self.start(sid, f"{self.title}: " + ", ".join(parts), self.rules + ask_for(sid, ids, slow_due, self.ask)
                       + policy_text(self.policy))
        if not r or r.get("error"):
            for i in ids:                                   # give the batch back: nobody is working on it
                self._unclaim(i)
            self.status = {**st, "waiting": (r or {}).get("error") or "the learner run did not start"}
            return self.status
        new = {"at": time.time(), "session": sid, "turn_key": r.get("turn_key") or sid, "claimed": ids,
               "slow_at": time.time() if slow_due else last.get("slow_at", 0),
               "slow_reviewing": [x["tool"] for x in slow] if slow_due else []}
        self.f.parent.mkdir(parents=True, exist_ok=True)
        self.f.write_text(json.dumps(new, indent=1))
        self.status = {**new, "enabled": on, "pending": len(pend) - len(ids), "slow": len(slow),
                       "checked": time.time()}
        return self.status

    @staticmethod
    def _unclaim(qid: str) -> None:
        _, qd = X._dirs()
        p = qd / f"{qid}.json"
        e = X._read(p)
        if e and e.get("status") == "claimed":
            e.update(status="complete", attempts=max(0, e.get("attempts", 1) - 1))
            e.pop("forge", None)
            X._write(p, e)

    # ------------------------------------------------------------ what a UI shows
    @staticmethod
    def recorder_card() -> Dict[str, Any]:
        try:
            st = X.stats()
        except Exception as e:
            st = {"open": 0, "counts": {}, "recent": [], "error": str(e)}
        c = st["counts"]
        return {"id": "recorder", "name": "foreground recorder", "kind": "hook", "status": "on",
                "desc": "Records everything the agent does by hand in the foreground (per chat, across turns and "
                        "sub-agents) and every turn, and queues it for the learner (explorations at their success point).",
                "last": f"{st['open']} in progress · {c.get('complete', 0)} queued · {c.get('claimed', 0)} with the "
                        f"learner · {c.get('processed', 0)} turned into capabilities/lessons",
                "recent": st.get("recent", [])}

    def learner_card(self, live: Dict[str, Any], owner: bool = True, every_s: float = 600,
                     name: str = "learner", kind: str = "background agent") -> Dict[str, Any]:
        """``live``: {running, failed, last, tools, started} of the current run, from the project's turn."""
        f = self.status or self._last()
        try:
            recent = ", ".join(f"{r['outcome']}{(' ' + r['capability']) if r.get('capability') else ''}"
                               for r in X.stats()["recent"][:3])
        except Exception:
            recent = ""
        waiting = f.get("waiting") or ((f"last: {recent}" if recent else "waiting for foreground work")
                                       + (f" · {f['slow']} slow step{'s' if f['slow'] != 1 else ''} to review"
                                          if f.get("slow") else ""))
        return {"id": "learner", "name": name, "kind": kind,
                "status": "running" if live.get("running") else ("off" if f.get("enabled") is False else "idle"),
                "desc": "Turns what the agent did in the foreground into new or updated capabilities and lessons, and "
                        "reviews slow steps so their capabilities parallelize ("
                        + ("applied automatically; it asks only what it cannot decide" if approval() == "auto"
                           else "proposals you approve") + f"); checks every {every_s / 60:g} min.",
                "last": (("→ " + live["last"]) if live.get("running") and live.get("last") else
                         "last run failed - click for what happened" if live.get("failed") else waiting),
                "tools": live.get("tools", 0), "started": live.get("started") or f.get("at"),
                "chat": f.get("session") if owner else None}


# ====================================================================== consolidation
PARTS = ("lessons", "capabilities")


def consolidate_enabled() -> bool:
    return X.env("AUTO_CONSOLIDATE", "1") not in ("0", "false", "no")


class Consolidator:
    """When to start a background consolidation run per part (lessons, capabilities), and what a UI says about it.

    ``report()`` / ``fingerprint(rep, part)`` / ``asks`` default to :mod:`phronix.engine.consolidate`'s. ``blocked(part)``
    returns why a part must wait (e.g. its merges still await the user's approval) or "". ``extra(part)`` returns text
    appended to the ask (e.g. the user's answers to earlier questions)."""

    def __init__(self, state_file: Path, start: Callable[[str, str, str], Dict[str, Any]],
                 running: Callable[[str], bool], report: Optional[Callable[[], Dict[str, Any]]] = None,
                 fingerprint: Optional[Callable[[Dict[str, Any], str], str]] = None,
                 asks: Optional[Dict[str, str]] = None, gap_h: Optional[float] = None,
                 blocked: Optional[Callable[[str], str]] = None, extra: Optional[Callable[[str], str]] = None,
                 title: str = "Consolidation", auto: Optional[Callable[[], bool]] = None,
                 rules: str = BG_RULES, policy: Optional[Dict[str, str]] = None) -> None:
        from . import consolidate as Q
        self.f = Path(state_file)
        self.start, self.running, self.title = start, running, title
        self.report_fn = report or Q.report
        self.fp_fn = fingerprint or Q.fingerprint
        self.asks = asks or Q.ASK
        self.gap_h = gap_h if gap_h is not None else X._float("CONSOLIDATION_GAP_H", 6.0)
        self.blocked, self.extra = blocked, extra
        self.enabled = auto or consolidate_enabled
        self.rules, self.policy = rules, policy
        self.report: Dict[str, Any] = {}
        self.auto: Dict[str, Any] = {}

    def _state(self) -> Dict[str, Any]:
        try:
            return json.loads(self.f.read_text())
        except (OSError, ValueError):
            return {}

    def watch_once(self, force: str = "", rep: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check (or take) the report; start a run for each part whose open groups changed since its last run. force:
        "lessons", "capabilities" or "all" - run now, no waiting period. Returns the report (also ``self.report``);
        per-part status is in ``self.auto``."""
        rep = rep if rep is not None else self.report_fn()
        self.report = rep
        auto = self._state()
        if not self.enabled() and not force:
            self.auto = {**auto, "enabled": False}
            return rep
        now = time.time()
        for part in PARTS:
            fp, last = self.fp_fn(rep, part), dict(auto.get(part, {}))
            forced = force in (part, "all")
            if not fp or (fp == last.get("fp") and not forced):
                continue
            last.pop("waiting", None)
            why = self.blocked(part) if self.blocked is not None and not forced else ""
            if last.get("turn_key") and self.running(last["turn_key"]):
                last["waiting"] = "the previous consolidation run is still running"
            elif why:
                last["waiting"] = why
            elif not forced and now - last.get("at", 0) < self.gap_h * 3600:
                last["waiting"] = ("next automatic run after "
                                   + time.strftime("%F %T", time.localtime(last["at"] + self.gap_h * 3600)))
            else:
                n = len(rep.get(part) or [])
                sid = uuid.uuid4().hex[:12]
                ask = self.asks[part] + ((self.extra(part) or "") if self.extra is not None else "")
                r = self.start(sid, f"{self.title}: {part} ({n} group{'s' if n != 1 else ''})",
                               self.rules + ask + policy_text(self.policy))
                if not r or r.get("error"):
                    last["waiting"] = (r or {}).get("error") or "the consolidation run did not start"
                else:
                    last = {"fp": fp, "at": now, "session": sid, "turn_key": r.get("turn_key") or sid, "groups": n}
            auto[part] = last
        self.f.parent.mkdir(parents=True, exist_ok=True)
        self.f.write_text(json.dumps(auto, indent=1))
        self.auto = {**auto, "enabled": True}
        return rep

    def cards(self, live: Callable[[str], Dict[str, Any]], owner: bool = True) -> List[Dict[str, Any]]:
        """One card per part. ``live(turn_key)`` -> {running, failed, last, tools, started} of that part's run."""
        auto = self.auto or self._state()
        rep = self.report or {}
        descs = {"lessons": "Merges overlapping lessons into one copy of each fact; on a conflict it asks you, with its "
                            "recommendation.",
                 "capabilities": "Moves what capabilities share to one home; conflicts are left to you."}
        out = []
        for part in PARTS:
            a = auto.get(part) or {}
            lv = live(a.get("turn_key", "")) if a.get("turn_key") else {"running": False}
            g = len(rep.get(part) or [])
            idle = a.get("waiting") or f"{g} open group{'s' if g != 1 else ''}"
            nq = len(rep.get("questions") or []) if part == "lessons" else 0
            if nq:
                idle += f" · {nq} question{'s' if nq != 1 else ''} waiting for you"
            if a.get("at"):
                idle += f" · last run {time.strftime('%F %H:%M', time.localtime(a['at']))}"
            out.append({"id": f"consolidation-{part}", "name": f"{part} consolidation", "kind": "background agent",
                        "status": "running" if lv.get("running") else ("off" if auto.get("enabled") is False else
                                                                         "failed" if lv.get("failed") else "idle"),
                        "desc": descs[part],
                        "last": ("→ " + lv["last"]) if lv.get("running") and lv.get("last") else
                                ("last run failed - click for what happened" if lv.get("failed") else idle),
                        "tools": lv.get("tools", 0), "started": lv.get("started") or a.get("at"),
                        "chat": a.get("session") if owner else None})
        return out


# ====================================================================== standalone: a plain phronix install
# Without a project's web UI to start background runs, phronix starts them itself: the Stop hook that phronix installs
# (``phronix sync hooks``; explore_hook capture --kick) spawns ``python -m phronix.engine.background kick`` detached,
# which runs the learner and the consolidation schedulers with headless Claude Code (``claude -p``) as the runner.
# <P>_LEARN_S (600): how often a kick may check; <P>_CLAUDE_BIN: the Claude Code to run.
ALLOWED_TOOLS = ("mcp__phronix", "Read", "Grep", "Glob")


def _bg_dir() -> Path:
    from . import config as _cfg
    d = _cfg.state_dir("background")
    d.mkdir(parents=True, exist_ok=True)
    return d


def cli_runner(kind: str, cwd: Optional[str] = None, allowed: Tuple[str, ...] = ALLOWED_TOOLS):
    """start(run_id, title, ask) that runs one background agent as a detached headless Claude Code process."""
    def start(sid: str, title: str, ask: str) -> Dict[str, Any]:
        import os
        import subprocess
        from . import config as _cfg
        claude = _cfg.agent_bin()
        if not claude:
            return {"error": f"no Claude Code found to run the {kind}: install it or set {_cfg.env_name('CLAUDE_BIN')}"}
        d = _bg_dir()
        log = d / f"{sid}.log"
        env = {**os.environ, _cfg.env_name("BACKGROUND"): kind}       # never recorded for the learner
        env.pop(_cfg.env_name("WEBUI_SESSION"), None)
        with open(log, "w") as out:
            p = subprocess.Popen([claude, "-p", ask, "--output-format", "stream-json", "--verbose",
                                  "--allowedTools", ",".join(allowed)], cwd=cwd or None, stdout=out,
                                 stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env, start_new_session=True)
        with open(d / "runs.jsonl", "a") as fh:
            fh.write(json.dumps({"session": sid, "kind": kind, "title": title, "pid": p.pid, "log": str(log),
                                 "cwd": cwd, "at": time.time()}) + "\n")
        return {"turn_key": f"pid:{p.pid}"}
    return start


def pid_running(key: str) -> bool:
    import os
    if not (key or "").startswith("pid:"):
        return False
    pid = int(key[4:])
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    try:                                            # a finished child not yet reaped is not running
        with open(f"/proc/{pid}/stat") as fh:
            return fh.read().split(") ", 1)[1][:1] != "Z"
    except (OSError, IndexError):
        return True


def kick(cwd: Optional[str] = None, force: bool = False,
         runner: Callable[[str, Optional[str]], Callable[[str, str, str], Dict[str, Any]]] = cli_runner) -> Dict[str, Any]:
    """Run both schedulers once (at most every <P>_LEARN_S unless forced) with headless runs."""
    d = _bg_dir()
    mark = d / "kick.json"
    try:
        last = json.loads(mark.read_text()).get("at", 0)
    except (OSError, ValueError):
        last = 0
    if not force and time.time() - last < X._float("LEARN_S", 600.0):
        return {"status": "waiting", "next_in_s": round(X._float("LEARN_S", 600.0) - (time.time() - last))}
    mark.write_text(json.dumps({"at": time.time()}))
    lr = Learner(d / "learner.json", runner("learner", cwd), pid_running)
    out: Dict[str, Any] = {"status": "ok", "learner": lr.watch_once(force=force)}
    c = Consolidator(d / "consolidation.json", runner("consolidation", cwd), pid_running)
    c.watch_once(force="all" if force else "")
    out["consolidation"] = {k: v for k, v in c.auto.items()}
    return out


def spawn_kick(cwd: Optional[str] = None, bootstrap: str = "") -> None:
    """Start a kick in a detached process: a hook must return at once."""
    import os
    import subprocess
    import sys
    argv = [sys.executable, "-m", "phronix.engine.background", "kick"] + (["--cwd", cwd] if cwd else []) + \
        (["--bootstrap", bootstrap] if bootstrap else [])
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True, env=os.environ.copy())


def status() -> Dict[str, Any]:
    """What the standalone background agents did: the queue, the last runs, the policy."""
    d = _bg_dir()
    runs = []
    try:
        runs = [json.loads(x) for x in (d / "runs.jsonl").read_text().splitlines()[-10:]]
    except (OSError, ValueError):
        pass
    for r in runs:
        r["running"] = pid_running(f"pid:{r.get('pid')}")
    return {"approval": approval(), "learning": enabled(), "consolidating": consolidate_enabled(),
            "queue": X.stats(), "runs": runs, "dir": str(d)}


def main(argv: Optional[List[str]] = None) -> int:
    """phronix-learner {kick [--force] [--cwd DIR] | status} [--bootstrap MODULE[:FN]]"""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="phronix-learner", description="phronix's background learner and consolidation")
    ap.add_argument("command", choices=("kick", "status"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--cwd", default="")
    ap.add_argument("--bootstrap", default="")
    a = ap.parse_args(argv)
    if a.bootstrap:
        from .explore_hook import _bootstrap
        _bootstrap(a.bootstrap)
    try:
        r = kick(a.cwd or None, a.force) if a.command == "kick" else status()
    except Exception as e:                             # a detached kick has nobody to tell but its exit code
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 1
    print(json.dumps(r, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
