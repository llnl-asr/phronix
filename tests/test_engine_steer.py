"""A steer message reaches the agent while a long tool runs: the call returns at once, the tool goes on."""
import threading
import time

import pytest

from phronix.engine import steer


@pytest.fixture()
def ib(tmp_path, monkeypatch):
    p = tmp_path / "chat.inbox"
    monkeypatch.setenv(steer.ENV, str(p))
    monkeypatch.setattr(steer, "POLL_S", 0.02)
    steer.reset(p)
    return p


def test_without_an_inbox_the_tool_is_just_called(monkeypatch):
    monkeypatch.delenv(steer.ENV, raising=False)
    assert steer.call("t", lambda x: x + 1, {"x": 1}) == 2


def test_a_quick_tool_returns_its_result(ib):
    assert steer.call("t", lambda: {"ok": 1}) == {"ok": 1} and not steer.busy()


def test_errors_are_raised_as_before(ib):
    def boom():
        raise ValueError("bad")
    with pytest.raises(ValueError):
        steer.call("t", boom)


def test_a_steer_returns_at_once_and_the_tool_goes_on(ib):
    release = threading.Event()

    def slow():
        release.wait(10)
        return {"built": True}

    out = {}
    th = threading.Thread(target=lambda: out.update(r=steer.call("build", slow)))
    th.start()
    time.sleep(0.1)
    mid = steer.post(ib, "use 4 nodes instead")
    assert steer.wait_claimed(ib, mid, 2) is True            # the web UI sees the tool took it
    th.join(2)
    r = out["r"]
    assert r["status"] == "still_running" and r["user_messages"] == ["use 4 nodes instead"] and steer.busy()
    assert any(c["call_id"] == r["call_id"] for c in steer.calls())
    release.set()
    assert steer.wait(r["call_id"], 5) == {"built": True} and not steer.busy()
    assert steer.wait(r["call_id"])["status"] == "error"      # given once


def test_an_unclaimed_message_is_withdrawn_for_stdin(ib):
    mid = steer.post(ib, "hello")
    t0 = time.time()
    assert steer.wait_claimed(ib, mid, 5) is False and time.time() - t0 < 0.5   # no tool running: stdin, no wait
    assert steer.call("t", lambda: 5) == 5                   # a later tool does not take it again
    got, _ = steer.take_new(ib, 0)
    assert got == []


def test_a_message_is_claimed_by_one_call_only(ib):
    release = threading.Event()
    outs = []
    ths = [threading.Thread(target=lambda: outs.append(steer.call("t", lambda: release.wait(10) and 1))) for _ in range(2)]
    for t in ths:
        t.start()
    time.sleep(0.1)
    steer.post(ib, "once")
    time.sleep(0.3)
    release.set()
    for t in ths:
        t.join(5)
    detached = [o for o in outs if isinstance(o, dict) and o.get("status") == "still_running"]
    assert len(detached) == 1 and outs.count(1) == 1
