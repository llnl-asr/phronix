"""Foreground -> background learning: the recorder (phronix.engine.explore), its hooks, and the learner scheduler."""
from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from phronix.engine import config as _cfg
from phronix.engine import explore as X
from phronix.engine import explore_hook as H
from phronix.engine import background as LR

SRC = str(Path(__file__).resolve().parents[1] / "src")


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(_cfg.S, "env_prefix", "PHRONIX")
    for k in [k for k in os.environ if k.startswith("PHRONIX_")]:
        monkeypatch.delenv(k)
    monkeypatch.setenv("PHRONIX_EXPLORATIONS_DIR", str(tmp_path / "explorations"))
    monkeypatch.setenv("PHRONIX_WEBUI_SESSION", "chat1")
    X.register(tool_capability=lambda: {})
    yield tmp_path
    X.register()


_IDS = itertools.count(1)


def _turn(prompt, calls, final="Done: it builds and the test passes.", explicit=False):
    lines = [{"type": "user", "message": {"role": "user", "content": prompt}}]
    base = next(_IDS) * 100
    for i, (tool, inp, ok) in enumerate(calls):
        i = base + i
        lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp}]}})
        lines.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}",
                                                                "is_error": not ok, "content": "out" if ok else "Exit code 1"}]}})
    if explicit:
        lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"x{base}",
                                                                     "name": "mcp__p__exploration_complete", "input": {}}]}})
    lines.append({"type": "assistant", "message": {"content": [{"type": "text", "text": final}]}})
    return lines


SCRIPT = [("Bash", {"command": "python probe.py", "description": "probe"}, False),
          ("Write", {"file_path": "/w/apps/foo/probe.py"}, True),
          ("Bash", {"command": "python probe.py --fixed"}, True),
          ("Bash", {"command": "python check.py"}, True)]


def test_a_successful_manual_exploration_is_queued_with_its_steps_and_transcript():
    r = X.capture(_turn("work out the probe", SCRIPT), transcript="/t/1.jsonl")
    assert r["completed"] and "turn" not in r                     # the exploration stands for the turn
    (e,) = X.pending()
    assert e["kind"] == "exploration" and len(e["steps"]) == 4 and e["transcripts"] == ["/t/1.jsonl"]


def test_a_turn_without_a_finished_exploration_is_queued_as_a_turn_for_the_learner():
    r = X.capture(_turn("no, always use the cached build", [("Bash", {"command": "ls"}, True)], final="ok"))
    assert r["open"] == 1 and r["turn"]
    (e,) = X.pending()
    assert e["kind"] == "turn" and e["prompts"] == ["no, always use the cached build"] and e["tools"] == {"Bash": 1}
    X.capture(_turn("build it", SCRIPT[1:]))                        # the open steps + these complete the exploration
    assert [x["kind"] for x in X.pending()] == ["exploration", "turn"]   # explorations first


def test_turn_records_can_be_switched_off_and_subagents_never_make_them(monkeypatch):
    X.capture(_turn("x", []), agent="sub1")
    assert X.pending() == []
    monkeypatch.setenv("PHRONIX_LEARN_TURNS", "0")
    X.capture(_turn("y", []))
    assert X.pending() == []


def test_background_runs_are_never_recorded(monkeypatch):
    monkeypatch.setenv("PHRONIX_BACKGROUND", "learner")
    assert X.capture(_turn("x", SCRIPT))["recorded"] == 0
    assert X.live_step({"tool_name": "Bash", "tool_input": {"command": "ls"}})["skipped"]
    assert X.pending() == [] and X.stats()["open"] == 0


def test_live_steps_are_completed_from_the_transcript_once():
    lines = _turn("go", SCRIPT)
    for b in [b for e in lines for b in (e["message"].get("content") or []) if isinstance(b, dict) and b.get("type") == "tool_use"]:
        X.live_step({"tool_name": b["name"], "tool_input": b["input"], "tool_use_id": b["id"], "tool_response": "o"})
    assert X.stats()["open"] == 1
    X.capture(lines)
    (e,) = X.pending()
    assert len(e["steps"]) == 4 and not any(s.get("live") for s in e["steps"]) and e["steps"][0]["ok"] is False


def test_an_explicit_success_point_queues_a_short_exploration():
    assert X.mark_complete("g", verification="")["status"] == "error"
    assert X.mark_complete("build foo", verification="ctest passes")["status"] == "ok"
    X.capture(_turn("go", [("Bash", {"command": "make"}, True)], explicit=True))
    (e,) = X.pending()
    assert e["how"] == "explicit" and e["completion"]["verification"] == "ctest passes"


def test_a_project_profile_routes_its_kinds_and_the_mark_must_answer_the_analysis():
    X.register(kinds=[("annotation_edit", {"Edit", "Write"}, r"/annotated/")],
               routes={"annotation_edit": ("tools_annotate", "annotation is a tool's job"),
                       "manual_build": ("workload_{app}", "the app's build")},
               self_packages=("myproj",), tool_capability=lambda: {"annotate_run": "tools_annotate"})
    X.capture(_turn("annotate", [("Edit", {"file_path": "/w/apps/foo/annotated/a.c"}, True),
                                 ("Write", {"file_path": "/w/apps/foo/annotated/b.c"}, True),
                                 ("Bash", {"command": "make -j"}, True), ("Bash", {"command": "make install"}, True),
                                 ("Edit", {"file_path": "/x/src/myproj/tool.py"}, True)]))
    (e,) = X.pending()
    a = X.analyze(e)
    assert a["app"] == "foo" and [b["capability"] for b in a["bypassed"]] == ["tools_annotate"]
    assert [g["suggest"] for g in a["gaps"]] == ["workload_foo"] and a["self_edits"] == ["/src/myproj/tool.py"]
    X.claim([e["id"]], "f1")
    r = X.mark([e["id"]], "covered", note="used it")
    assert r["status"] == "error" and "bypassed" in r["refused"][0]
    r = X.mark([e["id"]], "bypassed,new", capability="tools_annotate,workload_foo", proposal="p1,p2", note="n")
    assert "issue" in r["refused"][0]
    assert X.mark([e["id"]], "bypassed,new,issue", capability="tools_annotate,workload_foo", proposal="p1,p2",
                  note="n")["status"] == "ok"
    assert X.stats()["counts"] == {"processed": 1}


def test_the_guard_refuses_owned_manual_work_only_in_user_chats(monkeypatch):
    X.register(routes={"manual_build": ("workload_{app}", "builds go through the app's capability")},
               guarded=("manual_build",),
               guard_extra=lambda tool, inp: "no handoff" if tool == "Agent" else ("" if "make -v" in inp.get("command", "") else None))
    assert X.guard_active()
    assert "CAPABILITY-FIRST" in X.guard("Bash", {"command": "make -j8"})
    assert X.guard("Bash", {"command": "make -v && make -j"}) is None          # the project allowed it explicitly
    assert X.guard("Agent", {}) == "no handoff" and X.guard("Bash", {"command": "ls"}) is None
    monkeypatch.setenv("PHRONIX_BACKGROUND", "learner")
    assert not X.guard_active()


def _hook(cmd, ev, env):
    return subprocess.run([sys.executable, "-m", "phronix.engine.explore_hook", cmd], input=json.dumps(ev),
                          capture_output=True, text=True, env={**env, "PYTHONPATH": SRC}, timeout=60)


def test_the_hooks_record_through_the_claude_code_protocol_and_never_fail(tmp_path):
    env = {k: v for k, v in os.environ.items() if k.startswith("PHRONIX_")} | {"PATH": os.environ.get("PATH", "")}
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(x) for x in _turn("go", SCRIPT)))
    r = _hook("capture", {"hook_event_name": "Stop", "transcript_path": str(t), "session_id": "s"}, env)
    assert r.returncode == 0, r.stderr
    assert [e["kind"] for e in X.pending()] == ["exploration"]
    assert _hook("step", {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_use_id": "u"}, env).returncode == 0
    assert X.stats()["open"] == 1
    assert _hook("capture", {"transcript_path": "/nope"}, env).returncode == 0
    bad = subprocess.run([sys.executable, "-m", "phronix.engine.explore_hook", "step", "--bootstrap", "no_such_mod"],
                         input="{}", capture_output=True, text=True, env={**env, "PYTHONPATH": SRC})
    assert bad.returncode == 0 and "skipped" in bad.stderr


def test_settings_render_every_hook_event_with_the_bootstrap():
    s = H.settings(["/venv/bin/python"], "proj.boot:configure")
    assert set(s) == {"PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop", "SubagentStop"}
    assert s["PostToolUse"][0]["matcher"] == X.MANUAL_MATCHER
    assert s["Stop"][0]["hooks"][0]["command"] == \
        "/venv/bin/python -m phronix.engine.explore_hook capture --bootstrap proj.boot:configure"
    merged = H.merge({"Stop": [{"hooks": [{"command": "mine"}]}]}, s)
    assert merged["Stop"][0]["hooks"][0]["command"] == "mine" and len(merged["Stop"]) == 2
    assert "PreToolUse" not in H.settings(["py"], "", guard=False)


def _learner(tmp_path, started, live, err=None):
    def start(sid, title, ask):
        started.append((sid, title, ask))
        return {"error": err} if err else {"turn_key": f"bg/{sid}"}
    return LR.Learner(tmp_path / "learner.json", start, lambda key: live.get(key, False))


def test_the_learner_claims_a_batch_and_runs_one_background_agent_at_a_time(tmp_path):
    X.capture(_turn("build", SCRIPT))
    X.capture(_turn("prefer the cached build", [], final="ok"))
    started, live = [], {}
    lr = _learner(tmp_path, started, live)
    st = lr.watch_once()
    (sid, title, ask), = started
    assert title == "Learner: 1 exploration, 1 turn" and ask.startswith(LR.BG_RULES)
    assert all(i in ask for i in st["claimed"]) and f"forge='{sid}'" in ask and "exploration_mark" in ask
    live[st["turn_key"]] = True
    X.capture(_turn("another", [], final="ok"))
    assert "still running" in lr.watch_once()["waiting"] and len(started) == 1
    live[st["turn_key"]] = False
    lr.watch_once()
    assert len(started) == 2


def test_a_learner_run_that_does_not_start_gives_its_batch_back(tmp_path):
    X.capture(_turn("build", SCRIPT))
    started = []
    st = _learner(tmp_path, started, {}, err="no model access").watch_once()
    assert st["waiting"] == "no model access" and len(X.pending()) == 1 and X.pending()[0]["attempts"] == 0


def test_the_learner_runs_for_slow_steps_alone_and_respects_auto_learn(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    iso = lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")   # noqa: E731
    for s in (120, 130):
        X.record_timings([{"tool": "mcp__p__slow_tool", "start": 1.8e9, "seconds": s, "ok": True}], "c")
    monkeypatch.setattr(X.time, "time", lambda: 1.8e9 + 10)
    monkeypatch.setenv("PHRONIX_AUTO_LEARN", "0")
    started = []
    lr = _learner(tmp_path, started, {})
    assert lr.watch_once()["enabled"] is False and not started
    st = lr.watch_once(force=True)
    assert "1 slow step" in started[0][1] and st["claimed"] == [] and st["slow_reviewing"] == ["slow_tool"]
    assert iso                                                        # (kept for symmetry with transcript timings)


def test_the_cards_report_the_recorder_and_the_learner(tmp_path):
    X.capture(_turn("build", SCRIPT))
    lr = _learner(tmp_path, [], {})
    lr.watch_once()
    rec = LR.Learner.recorder_card()
    assert rec["id"] == "recorder" and "1 with the learner" in rec["last"]
    card = lr.learner_card({"running": True, "last": "capability_get", "tools": 3}, owner=False)
    assert card["status"] == "running" and card["last"] == "→ capability_get" and card["chat"] is None


# ---------------------------------------------------------------- consolidation
def _consolidator(tmp_path, started, live, rep, **kw):
    def start(sid, title, ask):
        started.append((title, ask))
        return {"turn_key": f"bg/{sid}"}
    return LR.Consolidator(tmp_path / "consolidation.json", start, lambda k: live.get(k, False), report=lambda: rep, **kw)


def test_consolidation_runs_once_per_new_set_of_groups_and_waits_its_gap(tmp_path):
    rep = {"lessons": [{"kind": "overlap", "ids": ["L1", "L2"]}], "capabilities": []}
    started, live = [], {}
    c = _consolidator(tmp_path, started, live, rep)
    c.watch_once()
    (title, ask), = started
    assert title == "Consolidation: lessons (1 group)" and "lesson_merge" in ask and ask.startswith(LR.BG_RULES)
    c.watch_once()                                                    # same groups: nothing new
    rep["lessons"].append({"kind": "conflict", "ids": ["L3", "L4"]})
    c.watch_once()                                                    # new groups, but inside the gap
    assert len(started) == 1 and "next automatic run" in c.auto["lessons"]["waiting"]
    live[c.auto["lessons"]["turn_key"]] = True
    c.watch_once(force="lessons")
    assert "still running" in c.auto["lessons"]["waiting"] and len(started) == 1
    live.clear()
    c.watch_once(force="all")
    assert len(started) == 2


def test_consolidation_waits_while_blocked_and_carries_the_users_answers(tmp_path, monkeypatch):
    rep = {"lessons": [{"kind": "overlap", "ids": ["L1", "L2"]}], "capabilities": [{"kind": "overlap", "ids": ["a", "b"]}]}
    started = []
    c = _consolidator(tmp_path, started, {}, rep, blocked=lambda p: "merges wait" if p == "lessons" else "",
                      extra=lambda p: "\nanswers: keep L1" if p == "capabilities" else "")
    c.watch_once()
    assert c.auto["lessons"]["waiting"] == "merges wait"
    (title, ask), = started
    assert "capabilities" in title and "answers: keep L1\n\nAPPROVAL POLICY" in ask
    cards = {x["id"]: x for x in c.cards(lambda k: {"running": True, "last": "capability_get"})}
    assert cards["consolidation-capabilities"]["status"] == "running"
    monkeypatch.setenv("PHRONIX_AUTO_CONSOLIDATE", "0")
    c2 = _consolidator(tmp_path / "x", [], {}, rep)
    c2.watch_once()
    assert c2.auto["enabled"] is False


# ---------------------------------------------------------------- approval policy and the standalone install
def test_the_background_agents_apply_by_default_and_wait_only_under_review(tmp_path, monkeypatch):
    X.capture(_turn("build", SCRIPT))
    started = []
    _learner(tmp_path, started, {}).watch_once()
    assert "APPROVAL POLICY: automatic" in started[0][2] and "capability_apply(id, confirmed=true)" in started[0][2]
    monkeypatch.setenv("PHRONIX_LEARN_APPROVAL", "review")
    rep = {"lessons": [{"kind": "overlap", "ids": ["L1", "L2"]}], "capabilities": []}
    got = []
    _consolidator(tmp_path, got, {}, rep).watch_once()
    assert "APPROVAL POLICY: review" in got[0][1]
    own = {"auto": "\nMINE auto", "review": "\nMINE review"}
    lr = LR.Learner(tmp_path / "l2.json", lambda s, t, a: got.append((t, a)) or {"turn_key": "k"}, lambda k: False,
                    policy=own)
    X.capture(_turn("again", SCRIPT))
    lr.watch_once()
    assert got[-1][1].endswith("MINE review")


def test_a_kick_runs_both_schedulers_at_most_every_learn_s(tmp_path, monkeypatch):
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("phronix.engine.consolidate.report", lambda: {"lessons": [], "capabilities": []})
    X.capture(_turn("build", SCRIPT))
    runs = []

    def runner(kind, cwd):
        return lambda sid, title, ask: runs.append((kind, cwd, title)) or {"turn_key": "pid:0"}
    r = LR.kick("/proj", runner=runner)
    assert r["status"] == "ok" and runs == [("learner", "/proj", "Learner: 1 exploration")]
    assert LR.kick("/proj", runner=runner)["status"] == "waiting"
    assert not LR.pid_running("pid:0") is None and LR.pid_running(f"pid:{os.getpid()}") and not LR.pid_running("x")


def test_the_cli_runner_starts_a_detached_headless_run_that_is_never_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("PHRONIX_HOME", str(tmp_path / "home"))
    fake = tmp_path / "claude"
    fake.write_text("#!/bin/sh\necho \"bg=$PHRONIX_BACKGROUND session=$PHRONIX_WEBUI_SESSION args=$*\"\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PHRONIX_CLAUDE_BIN", str(fake))
    r = LR.cli_runner("learner", str(tmp_path))("s1", "Learner: 1 turn", "ASK")
    pid = int(r["turn_key"][4:])
    os.waitpid(pid, 0)
    out = (tmp_path / "home" / "background" / "s1.log").read_text()
    assert "bg=learner session= args=-p ASK" in out and "--allowedTools mcp__phronix,Read,Grep,Glob" in out
    assert LR.status()["runs"][-1]["session"] == "s1"
    monkeypatch.setenv("PHRONIX_CLAUDE_BIN", str(tmp_path / "none"))
    monkeypatch.setattr(_cfg, "agent_bin", lambda: None)
    assert "no Claude Code" in LR.cli_runner("learner")("s2", "t", "a")["error"]


def test_a_plain_install_gets_the_learner_hooks_and_a_managed_project_keeps_its_own(tmp_path, monkeypatch):
    from phronix import hooks
    root = tmp_path / "proj"
    assert hooks.sync_claude_hooks(root) == "updated"
    s = json.loads((root / ".claude" / "settings.json").read_text())["hooks"]
    stop = s["Stop"][0]["hooks"][0]["command"]
    assert "phronix.engine.explore_hook capture --kick" in stop and "PostToolUse" in s
    assert hooks.sync_claude_hooks(root) != "updated"                  # idempotent
    managed = tmp_path / "managed"
    (managed / ".claude").mkdir(parents=True)
    mine = {"hooks": [{"type": "command", "command": "py -m phronix.engine.explore_hook capture --bootstrap proj.x"}]}
    (managed / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"Stop": [mine]}}))
    hooks.sync_claude_hooks(managed)
    s = json.loads((managed / ".claude" / "settings.json").read_text())["hooks"]
    assert s["Stop"] == [mine] and "PostToolUse" not in s
    monkeypatch.setenv("PHRONIX_LEARNER", "0")
    hooks.sync_claude_hooks(root)
    assert "Stop" not in json.loads((root / ".claude" / "settings.json").read_text())["hooks"]


def test_the_stop_hook_kicks_the_background_agents_only_with_kick(tmp_path, monkeypatch):
    kicked = []
    monkeypatch.setattr(LR, "spawn_kick", lambda cwd=None, bootstrap="": kicked.append(cwd))
    t = tmp_path / "t.jsonl"
    t.write_text(json.dumps({"type": "user", "message": {"content": "hi"}}))
    import io
    for argv in (["capture"], ["capture", "--kick"]):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"transcript_path": str(t), "cwd": "/p"})))
        assert H.main(argv) == 0
    assert kicked == ["/p"]
